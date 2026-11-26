#!/usr/bin/env python3
"""Fresh AWS runtime inputs for the existing protected Border qualification."""
import argparse
import copy
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sys
import time
from types import SimpleNamespace
import campaign as c
import lifecycle as life
import run
from preflight import save

REPO=Path(__file__).resolve().parents[4]


def acceptance_matrix(stage, groups, anchors, start_ms, deadline_ms):
    from matrix import freeze
    return freeze(stage,groups,anchors,start_ms,deadline_ms)


def verify_acceptance_matrix(matrix, matrix_sha256, assignments, assignment_digests, artifacts):
    from matrix import verify_all
    return verify_all(matrix,matrix_sha256,assignments,assignment_digests,artifacts)


def single_node(record, observed, packet, now):
    c.need(packet['stage'] in (1,2,3),'single_border_stage_required')
    life.ownership(record,observed,packet['account'],packet['region'],packet['run_id'],packet['stage'])
    c.need(observed.get('query_succeeded') and 0<=now-observed.get('observed_at',0)<=30,'fresh_host_observation_required')
    c.need(observed.get('state')=='running' and not observed.get('absent'),'running_host_required')
    raw=observed['raw'];c.need(c.digest(raw)==observed['raw_sha256'],'host_observation_changed')
    c.need(raw['Placement']['AvailabilityZone'].startswith(packet['region']),'host_region_mismatch')
    internal,public=ipaddress.ip_address(raw['PrivateIpAddress']),ipaddress.ip_address(raw['PublicIpAddress'])
    c.need(internal in ipaddress.ip_network('10.199.11.0/26') and public.is_global,'host_address_mismatch')
    c.need(raw['MetadataOptions']['HttpTokens']=='required' and raw['MetadataOptions']['HttpPutResponseHopLimit']==1,
           'imds_v2_hop_one_required')
    c.need(not raw.get('IamInstanceProfile'),'no_container_cloud_role')
    return {'code':'nne1','internal':str(internal),'public':str(public),'iname':'host.openshell.internal',
            'cloud':'aws','region':packet['region'],'border_count':1,'voter_count':1,'ha_qualified':False}


def prepare_single(root, node, organization, private_members=False):
    """No cloud, DNS, model or container call. Fresh identities/source only."""
    c.need(node.get('border_count')==node.get('voter_count')==1 and node.get('ha_qualified') is False,'single_voter_only')
    c.need(re.fullmatch(r'nc199-[a-f0-9]{12}',organization),'campaign_organization_required')
    root=Path(root).absolute()
    c.need(not root.exists() and not root.is_symlink(),'fresh_runtime_root_required')
    c.owned_directory(root.parent)
    sys.path[:0]=[str(REPO),str(REPO/'mcp-servers/protocol-mcp')]
    from labs.ha import r09_prepare
    old_state=r09_prepare.VM_STATE
    try:
        args=SimpleNamespace(root=str(root),node=[node['code']+'='+node['internal']+','+node['public']+','+node['iname']],
            witness=None,state_dir='/sandbox/nc182',sandbox=True,organization=organization,days=2,
            private_member_endpoints=private_members)
        summary=r09_prepare.prepare(args)
    finally:r09_prepare.VM_STATE=old_state
    c.need(len(summary['nodes'])==1,'unexpected_border_count')
    template=json.loads((root/'bundles'/node['code']/'contract.template.json').read_text())
    c.need(template['schemaVersion']==3 and template['role']=='border','current_protected_role_required')
    save(root/'aws-placement.json',node)
    save(root/'aws-policy-input.json',single_policy(node['code']))
    return {'border_count':1,'voter_count':1,'ha_qualified':False,'source_files':summary['source_files'],
            'schema_version':template['schemaVersion'],'cloud_calls':0,'provider_calls':0}


def single_policy(code):
    # OpenShell matches /proc/<pid>/exe, not the venv symlink. This is the
    # resolved interpreter in the pinned Python 3.12 Border image.
    return {'node':code,'etcd':['host.openshell.internal:12379'],'peers':[],
            'anthropic':True,'resolve':{'host.openshell.internal':'127.0.0.1'},
            'binaries':{'python':'/usr/local/bin/python3.12'}}


def regional_nodes(packet, graph, custody, observations, now):
    """Bind all three actual hosts to the frozen graph before minting identities."""
    c.need(packet['stage'] in (4,5) and graph['stage']==packet['stage'] and c.digest(graph)==packet['regional_graph_sha256'],'frozen_regional_graph_required')
    selected=graph['nodes']
    import regional
    scope=graph.get('qualification_scope','three-region')
    c.need(packet.get('qualification_scope','three-region')==scope,'qualification_scope_changed')
    regional.validate_nodes(selected,scope)
    result=[]
    for node in selected:
        matches=[row for row in custody.values() if row['record'].get('origin_action')==node['code']+'-instance']
        c.need(len(matches)==1,'exact_regional_instance_custody_required');row=matches[0];record=row['record']
        c.need(row['record_sha256']==c.digest(record) and record['kind']=='instance','regional_custody_changed')
        obs=observations[record['id']]
        life.ownership(record,obs,packet['account'],life.packet_region(packet,node['region']),packet['run_id'],packet['stage'])
        c.need(obs.get('query_succeeded') and 0<=now-obs.get('observed_at',0)<=30
               and obs.get('state')=='running' and obs.get('absent') is False,'fresh_running_regional_host_required')
        raw=obs['raw'];c.need(c.digest(raw)==obs['raw_sha256'],'host_observation_changed')
        c.need(raw['Placement']['AvailabilityZone']==node['zone'] and raw['PrivateIpAddress']==node['private_ip']
               and raw['ImageId']==node['ami'] and raw['InstanceType']==node['instance_type'],'regional_host_changed')
        if scope=='ohio-three-az':
            c.need(raw['Placement'].get('AvailabilityZoneId')==node['zone_id'],'actual_az_id_required')
        c.need(raw['MetadataOptions']['HttpTokens']=='required' and raw['MetadataOptions']['HttpPutResponseHopLimit']==1
               and not raw.get('IamInstanceProfile'),'imds_v2_no_cloud_role_required')
        public=ipaddress.ip_address(raw['PublicIpAddress']);c.need(public.is_global,'public_host_required')
        result.append(dict(code=node['code'],internal=node['private_ip'],public=str(public),iname=node['iname'],
            cloud='aws',region=node['region'],zone=node['zone'],zone_id=node.get('zone_id'),
            qualification_scope=scope,instance_id=record['id']))
    c.need(len({n['instance_id'] for n in result})==len({n['public'] for n in result})==3,'distinct_regional_hosts_required')
    return result


def prepare_regional(root, packet, graph, custody, observations, now, admission_ms=9000):
    nodes=regional_nodes(packet,graph,custody,observations,now)
    c.need(type(admission_ms) is int and 3000<=admission_ms<=9000,'bounded_fresh_admission_window_required')
    root=Path(root).absolute();c.need(not root.exists() and not root.is_symlink(),'fresh_runtime_root_required')
    c.owned_directory(root.parent)
    sys.path[:0]=[str(REPO),str(REPO/'mcp-servers/protocol-mcp')]
    from labs.ha import r09_prepare
    old_state,old_limits=r09_prepare.VM_STATE,r09_prepare.LIMITS
    try:
        # Set only before generating a fresh signed manifest. Live manifests
        # are immutable; measured admission is still required after deployment.
        r09_prepare.LIMITS=dict(old_limits,admission_ms=admission_ms)
        args=SimpleNamespace(root=str(root),node=[n['code']+'='+n['internal']+','+n['public']+','+n['iname'] for n in nodes],
            witness=None,state_dir='/sandbox/nc182',sandbox=True,organization=packet['run_id'],days=2,
            private_member_endpoints=True)
        summary=r09_prepare.prepare(args)
    finally:r09_prepare.VM_STATE,r09_prepare.LIMITS=old_state,old_limits
    c.need(len(summary['nodes'])==3,'three_border_bundles_required')
    save(root/'aws-placement.json',nodes);save(root/'aws-policy-input.json',graph['sandbox_policy_inputs'])
    return {'border_count':3,'voter_count':3,'source_files':summary['source_files'],
            'admission_ms':admission_ms,'ha_qualified':False,'cloud_calls':0,'provider_calls':0}


def linux_member_runtime(runtime, member_root, images):
    """Bind a fresh Linux member to inspected images and a short Unix relay.

    Called before materialization. Images are immutable public build artifacts;
    credentials, identities, containers and execution journals are never reused.
    """
    root=Path(member_root)
    c.need(root.is_absolute() and root.parent==Path('/home/ubuntu')
           and re.fullmatch(r'nc199m-[a-f0-9]{8}',root.name),'fresh_short_aws_member_root_required')
    c.need(set(images)=={'agent','relay','guard'},'three_inspected_member_images_required')
    for row in images.values():
        c.need(row.get('Architecture')=='amd64' and row.get('Os')=='linux','linux_amd64_image_required')
        c.need(re.fullmatch(r'sha256:[a-f0-9]{64}',row.get('Id','')),'immutable_image_required')
        c.need(row.get('rootfs_verified') is True,'image_archive_closure_unverified')
    value=copy.deepcopy(runtime)
    value.update(docker='/usr/bin/docker',docker_host='unix:///run/docker.sock',
                 agent_image=images['agent']['Id'],relay_image=images['relay']['Id'],
                 relay_transport='unix',state_dir=str(root/'runtime'))
    value['guard']['image']=images['guard']['Id']
    c.need(len((value['state_dir']+'/'+'0'*36+'/broker/broker.sock').encode())<=103,'unix_relay_path_too_long')
    return value


def member_placement(packet, instance_record, metadata, member_identity, member_root):
    """Correlate actual host IMDS readback with recorded resource and fresh identity."""
    c.need(packet['stage'] in (2,3,4,5),'physical_member_stage_required')
    c.need(instance_record['kind']=='instance' and instance_record['run_id']==packet['run_id']
           and instance_record['stage']==packet['stage'],'owned_member_host_required')
    region=life.packet_region(packet,instance_record['region'])
    for key,wanted in (('accountId',packet['account']),('region',region),('instanceId',instance_record['id'])):
        c.need(metadata.get(key)==wanted,'physical_host_identity_mismatch')
    c.need(metadata.get('architecture')=='x86_64','physical_host_architecture_mismatch')
    c.need(re.fullmatch(r'nc199m-[a-f0-9]{8}',Path(member_root).name),'fresh_member_identity_required')
    binding=member_identity.get('binding',{})
    c.need(all(binding.get(k) for k in ('installation_id','member_id','key_id','enrollment_generation')),
           'complete_member_identity_required')
    return {'cloud':'aws','instance_id':instance_record['id'],'region':region,
            'run_id':packet['run_id'],'stage':packet['stage'],'member':binding,
            'member_root':str(member_root),'shares_border_host':True,
            'native_execution_verified':False}


def member_mcp_manifest(environment_manifest, executable_sha256):
    """The role and native MCP validators deliberately use different schemas."""
    c.need(set(environment_manifest)=={'schemaVersion','files','symlinks'}
           and environment_manifest['schemaVersion']==1,'role_environment_manifest_required')
    c.need(isinstance(environment_manifest['files'],dict) and 'pyvenv.cfg' in environment_manifest['files']
           and isinstance(environment_manifest['symlinks'],dict),'complete_environment_manifest_required')
    c.need(re.fullmatch('[a-f0-9]{64}',executable_sha256),'immutable_interpreter_digest_required')
    return {'files':copy.deepcopy(environment_manifest['files']),
            'symlinks':copy.deepcopy(environment_manifest['symlinks']),
            'executable_sha256':executable_sha256}


def member_readiness(validation, relay, mcp, expected_schema):
    """Require actual no-effect dependency/relay evidence before a member task."""
    c.need(validation.get('role_validate')=='valid' and validation.get('control_only') is False,
           'execution_role_validation_required')
    c.need(validation.get('closure_import')=='ok','member_lazy_dependencies_required')
    c.need(relay.get('unix_relay_passed') is True and relay.get('no_provider_or_device') is True
           and relay.get('socket_mode')=='0o600' and relay.get('response',{}).get('effect') is False,
           'actual_private_unix_relay_required')
    c.need(mcp.get('binding_validated') is True,'native_mcp_full_binding_validation_required')
    c.need(mcp.get('mcp_initialized') is True and mcp.get('tool_schema_sha256')==expected_schema
           and re.fullmatch('[a-f0-9]{64}',expected_schema),'actual_pinned_mcp_startup_required')
    c.need(type(mcp.get('tool_calls')) is int and mcp['tool_calls']==0
           and type(mcp.get('inference_calls')) is int and mcp['inference_calls']==0,
           'preflight_must_have_no_effects')
    return {'ready_for_bounded_task':True,'native_execution_verified':False}


def model_removal_plan(owned, stop_receipt, export_root, export_manifest):
    """Stop preserves Docker objects. Removal separately requires a verified export."""
    owner=owned.get('owner_name','')
    c.need(owned.get('schema_version')==1 and owned.get('owner_spec')==199
           and re.fullmatch(r'netclaw-r08-r199-[a-f0-9]{12}-[a-f0-9]{6}',owner),'owned_199_model_required')
    c.need(owned.get('model_name')==owner+'-model'
           and owned.get('probe_name')==owner+'-model-peer'
           and owned.get('network_name')==owner+'-model-net','model_names_changed')
    ids=[owned.get(k) for k in ('probe_id','model_id','network_id')]
    c.need(all(isinstance(i,str) and re.fullmatch('[a-f0-9]{64}',i) for i in ids)
           and len(set(ids))==3,'complete_model_custody_required')
    c.need(stop_receipt.get('objects_and_evidence_preserved') is True
           and set(stop_receipt.get('stopped_container_ids',[]))==set(ids[:2])
           and stop_receipt.get('network_retained')==ids[2],'observed_stop_receipt_required')
    export_sha=life.verify_export(export_root,export_manifest,ids)
    return {'schema':1,'owner':owner,'image':owned['image'],'export_sha256':export_sha,
            'export_root':str(export_root),'export_manifest':export_manifest,
            'actions':[{'kind':'container','id':ids[0],'name':owned['probe_name']},
                       {'kind':'container','id':ids[1],'name':owned['model_name']},
                       {'kind':'network','id':ids[2],'name':owned['network_name']}]}


def remove_model_once(journal_root, plan, index, observe, invoke):
    """One exact Docker removal, with a fresh read and an irreversible send marker.

    observe(action) supplies an actual inspection/absence read; invoke(argv) is
    the local Docker adapter. An existing intent always blocks a second send.
    """
    root=c.owned_directory(Path(journal_root));action=plan['actions'][index]
    ids=[a['id'] for a in plan['actions']]
    c.need(life.verify_export(plan['export_root'],plan['export_manifest'],ids)==plan['export_sha256'],
           'model_export_changed')
    for prior in plan['actions'][:index]:
        row=observe(prior)
        c.need(row.get('query_succeeded') is True and row.get('absent') is True
               and 0<=time.time()-row.get('observed_at',0)<=30,'prior_model_object_remains')
    row=observe(action)
    c.need(row.get('query_succeeded') is True and 0<=time.time()-row.get('observed_at',0)<=30,
           'fresh_model_inspection_required')
    c.need(row.get('absent') is False,'model_absence_requires_no_removal')
    raw=row['raw'];labels=raw.get('Labels',{}) if action['kind']=='network' else raw.get('Config',{}).get('Labels',{})
    c.need(raw.get('Id')==action['id'] and raw.get('Name')==('/' if action['kind']=='container' else '')+action['name']
           and labels.get('netclaw.spec')=='199' and labels.get('netclaw.owner')==plan['owner'],'model_ownership_changed')
    if action['kind']=='container':
        c.need(raw.get('Image')==plan['image'] and raw.get('State',{}).get('Running') is False,
               'stopped_exact_model_required')
        argv=['rm',action['id']]
    else:
        c.need(raw.get('Internal') is True and not raw.get('Containers'),'owned_model_network_not_empty')
        argv=['network','rm',action['id']]
    stem='model-remove-'+str(index)
    save(root/(stem+'-intent.json'),{'plan_sha256':c.digest(plan),'action':action,'argv':argv,'at':time.time()})
    result=invoke(argv)  # Lost replies retain the intent; no automatic retry.
    save(root/(stem+'-result.json'),result)
    return result


def host_key(console, public_ip):
    """Pin only the public key returned through the authenticated EC2 console API."""
    c.need(ipaddress.ip_address(public_ip).is_global,'public_host_required')
    begin='NETCLAW_199_HOST_KEYS_BEGIN';end='NETCLAW_199_HOST_KEYS_END'
    c.need(console.count(begin)==console.count(end)==1,'unique_console_key_marker_required')
    body=console.split(begin,1)[1].split(end,1)[0].strip()
    rows=[line.strip().replace('\r','') for line in body.splitlines() if line.strip()]
    c.need(len(rows)==1 and re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/]+={0,2}(?: [^\r\n]+)?',rows[0]),'single_ed25519_host_key_required')
    key=' '.join(rows[0].split()[:2])
    return public_ip+' '+key+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('verb',choices=['prepare-single']);p.add_argument('--campaign',required=True)
    p.add_argument('--root',required=True);p.add_argument('--profile',default='NetClaw')
    a=p.parse_args();root,packet,_=run.load(a.campaign,allow_source_change=True)
    api,account=run.api_for(root,packet,a.profile)
    state=c.read_private(root/'campaign.json');entry=state['reservations'][packet['attempt_id']]
    records=[row['record'] for row in entry.get('custody',{}).values() if row['record']['kind']=='instance']
    c.need(len(records)==1,'one_owned_instance_required')
    observed=api.observe(records[0],account)
    node=single_node(records[0],observed,packet,__import__('time').time())
    print(json.dumps(prepare_single(a.root,node,packet['run_id'],private_members=packet['stage']>1),indent=2))


if __name__=='__main__':main()
