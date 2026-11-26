"""Offline three-region planning and observation checks for Spec199.

This module sends no cloud request and creates no reservation. Its draft cannot
be applied by the single-Ohio runner. regional_run.py freezes a separately priced
packet and provides regional custody/cleanup. Fixture success never
substitutes for live region access, signatures, routing or successor evidence.
"""
import ipaddress
from itertools import combinations
import re
import campaign as c
import network
import preflight

PEER_PORTS=(2380,12379,7443,7444)


SCOPES=('three-region','ohio-three-az')


def ready_regions(account, reports, now, scope='three-region'):
    c.need(scope in SCOPES,'unknown_qualification_scope')
    c.need(isinstance(reports,list) and len(reports)==(1 if scope=='ohio-three-az' else 3),'three_region_reports_required')
    result={}
    for row in reports:
        region=row['region']
        c.need(re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d',region) and region not in result,'three_distinct_regions_required')
        c.need(type(row.get('observed_at')) in (int,float) and 0<=now-row['observed_at']<=900,'fresh_region_report_required')
        c.need(c.digest(row['raw'])==row.get('raw_sha256'),'regional_evidence_changed')
        summary=preflight.summarize(row['raw'],region,row['instance_type'],account)
        c.need(summary['readiness']=='read_only_checks_pass','region_preflight_denied_or_unknown')
        c.need(summary['compute_usd_hour'] is not None and c.money(summary['compute_usd_hour'])>0,'exact_regional_rate_required')
        plan_known=(row['raw'].get('credits',{}).get('ok') is True and
               summary['credit_observation'].get('accountPlanStatus')=='ACTIVE' and
               summary['credit_observation'].get('accountPlanType') in ('FREE','PAID'))
        if not plan_known:
            # The owner upgraded personally. A missing post-upgrade Free Tier
            # record is not a credit balance or proof of product eligibility.
            attestation=row.get('owner_paid_upgrade',{})
            c.need(scope=='ohio-three-az' and row['raw'].get('credits',{}).get('error')=='ResourceNotFoundException'
                   and attestation.get('account')==account and attestation.get('confirmed_by')=='owner'
                   and attestation.get('plan')=='PAID' and attestation.get('gross_budget_usd')=='100'
                   and attestation.get('credit_balance')=='unknown'
                   and c.digest(attestation)==row.get('owner_paid_upgrade_sha256'),'account_plan_unknown')
        c.need(summary['instance_vcpu']==2 and summary['memory_mib']==8192,'reviewed_regional_shape_required')
        if scope=='ohio-three-az':
            c.need(region=='us-east-2','ohio_only_scope')
            c.need(summary['free_standard_vcpu']>=3*summary['instance_vcpu'],'aggregate_three_host_quota_required')
            zones={z['ZoneName']:z['ZoneId'] for z in preflight.payload(row['raw'],'zones').get('AvailabilityZones',[])
                   if z.get('State')=='available' and z.get('RegionName')==region
                   and z.get('ZoneType')=='availability-zone' and z.get('OptInStatus') in ('opt-in-not-required','opted-in')}
            c.need(len(zones)==len(set(zones.values()))==3 and set(zones)<=set(summary['offered_zones']),
                   'three_observed_ohio_az_ids_required')
            permissions=row.get('launch_permissions',{})
            c.need(set(permissions)==set(zones),'three_zone_launch_permissions_required')
            for zone,observation in permissions.items():
                request=observation.get('request',{})
                c.need(observation.get('error')=='DryRunOperation' and observation.get('account')==account
                       and observation.get('region')==region and 0<=now-observation.get('observed_at',0)<=900
                       and request.get('DryRun') is True and request.get('InstanceType')==row['instance_type']
                       and request.get('ImageId')==summary['ami_id'] and request.get('Placement',{}).get('AvailabilityZone')==zone
                       and request.get('MinCount')==request.get('MaxCount')==1,'exact_zone_permission_required')
            summary['zone_ids']=zones
        result[region]=dict(summary,evidence_sha256=c.digest(row))
    return result


def _rename(value, code, run_id):
    if isinstance(value,list):return [_rename(x,code,run_id) for x in value]
    if not isinstance(value,dict):return value
    if set(value)=={'$ref'}:return {'$ref':code+'-'+value['$ref']}
    if value.get('Key')=='netclaw-run':return {'Key':'netclaw-run','Value':run_id}
    return {k:_rename(v,code,run_id) for k,v in value.items()}


def validate_nodes(nodes, scope):
    c.need(scope in SCOPES,'unknown_qualification_scope')
    c.need(len(nodes)==3,'three_hosts_required')
    if scope=='three-region':
        c.need(len({n['region'] for n in nodes})==3,'three_distinct_regions_required')
    else:
        c.need({n['region'] for n in nodes}=={'us-east-2'},'ohio_only_scope')
        c.need(len({n['zone'] for n in nodes})==len({n.get('zone_id') for n in nodes})==3
               and all(re.fullmatch(r'us-east-2[a-z]',n['zone']) and
                       re.fullmatch(r'use2-az[1-9][0-9]*',n.get('zone_id','')) for n in nodes),'three_distinct_ohio_azs_required')


def draft(account,run_id,reports,nodes,*,deadline,operator_cidr,public_key,now,
          scope='three-region',scope_amendment_sha256=None,stage=4):
    """Build a reviewable graph from fresh regional observations; never apply it."""
    ready=ready_regions(account,reports,now,scope)
    validate_nodes(nodes,scope)
    if scope=='ohio-three-az':c.need(bool(re.fullmatch(r'[a-f0-9]{64}',scope_amendment_sha256 or '')),'scope_amendment_required')
    c.need(re.fullmatch(r'nc199-[a-f0-9]{12}',run_id),'owned_run_required')
    c.need(stage in (4,5),'regional_stage_required')
    c.need(120<c.stamp(deadline)-now<=c.MAX_SECONDS[stage],'finite_regional_deadline_required')
    c.need(len(nodes)==3 and {n['region'] for n in nodes}==set(ready),'selected_regions_mismatch')
    c.need(len({n['code'] for n in nodes})==3 and all(re.fullmatch(r'[a-z][a-z0-9]{1,5}',n['code']) for n in nodes),'distinct_node_codes_required')
    cidrs=[ipaddress.ip_network(n['vpc_cidr'],strict=True) for n in nodes]
    c.need(all(not a.overlaps(b) for a,b in combinations(cidrs,2)),'overlapping_regional_networks')
    actions=[];selected=[]
    for node in nodes:
        row=ready[node['region']];code=node['code']
        c.need(node['zone'] in row['offered_zones'],'observed_zone_required')
        if scope=='ohio-three-az':c.need(row['zone_ids'].get(node['zone'])==node['zone_id'],'observed_zone_id_required')
        # IAM role names are global, so each node needs a distinct exact stop role.
        prefix='nc199-'+c.digest([run_id,code])[:12]
        token='nc199-'+c.digest([run_id,code,'instance'])[:40]
        host=network._border(account,node['region'],node['zone'],prefix,deadline,token,row['ami_id'],
            operator_cidr,public_key,row['instance_type'],stage,node['vpc_cidr'],node['subnet_cidr'],node['private_ip'])
        for action in host:
            action=_rename(action,code,run_id);action['name']=code+'-'+action['name'];actions.append(action)
        selected.append(dict(node,host_prefix=prefix,client_token=token,ami=row['ami_id'],
            iname=run_id+'-'+code+'.aws.internal',
            instance_type=row['instance_type'],readiness_sha256=row['evidence_sha256']))
    tags=[{'Key':k,'Value':v} for k,v in {'netclaw-spec':'199','netclaw-run':run_id,'netclaw-stage':str(stage)}.items()]
    def ref(path):return {'$ref':path}
    def add(name,region,operation,request):
        actions.append(dict(name=name,region=region,service='ec2',operation=operation,request=request))
    routes=[]
    for a,b in combinations(selected,2):
        stem='peer-'+a['code']+'-'+b['code'];peer=ref(stem+'.VpcPeeringConnection.VpcPeeringConnectionId')
        add(stem,a['region'],'create-vpc-peering-connection',{
            'VpcId':ref(a['code']+'-vpc.Vpc.VpcId'),'PeerVpcId':ref(b['code']+'-vpc.Vpc.VpcId'),
            'PeerOwnerId':account,'PeerRegion':b['region'],
            'TagSpecifications':[{'ResourceType':'vpc-peering-connection','Tags':tags}]})
        add(stem+'-accept',b['region'],'accept-vpc-peering-connection',{'VpcPeeringConnectionId':peer})
        # Peering tags are regional; requester tags do not appear on the accepter.
        add(stem+'-accepter-tags',b['region'],'create-tags',{'Resources':[peer],'Tags':tags})
        for source,target in ((a,b),(b,a)):
            name='route-'+source['code']+'-'+target['code'];destination=target['private_ip']+'/32'
            add(name,source['region'],'create-route',{'RouteTableId':ref(source['code']+'-route-table.RouteTable.RouteTableId'),
                'DestinationCidrBlock':destination,'VpcPeeringConnectionId':peer})
            routes.append(dict(source=source['code'],target=target['code'],source_region=source['region'],
                target_region=target['region'],destination=destination,peering_action=stem,
                route_action=name,requester_region=a['region'],requester_node=a['code']))
    for node in selected:
        for direction in ('ingress','egress'):
            rules=[{'IpProtocol':'tcp','FromPort':port,'ToPort':port,
                'IpRanges':[{'CidrIp':peer['private_ip']+'/32','Description':'Exact regional peer '+peer['code']}]} for peer in selected if peer!=node for port in PEER_PORTS]
            add(node['code']+'-peer-'+direction,node['region'],'authorize-security-group-'+direction,
                {'GroupId':ref(node['code']+'-security-group.GroupId'),'IpPermissions':rules})
    # The generated names are local routing aliases, never certificate identities.
    hosts={n['iname']:n['private_ip'] for n in selected}
    policies={n['code']:{'node':n['code'],'etcd':[p['iname']+':12379' for p in selected],
        'peers':[p['iname']+':7443' for p in selected if p['code']!=n['code']],
        'anthropic':True,'resolve':dict(hosts),
        'binaries':{'python':'/usr/local/bin/python3.12'}} for n in selected}
    return {'schema':1,'stage':stage,'account':account,'run_id':run_id,'deadline':deadline,
        'qualification_scope':scope,'scope_amendment_sha256':scope_amendment_sha256,
        'nodes':selected,'actions':actions,'peer_routes':routes,'hosts':hosts,'sandbox_policy_inputs':policies,
        'activation_ready':False,'remaining_gates':['full_cost_reservation','fresh_frozen_packet','actual_host_route_tls_and_deadline_checks',
            'fresh_signed_authority_and_measured_admission']}


def _fresh_raw(observation,now):
    c.need(observation.get('query_succeeded') is True and
           type(observation.get('observed_at')) in (int,float) and
           0<=now-observation['observed_at']<=30,'fresh_successful_observation_required')
    return observation['raw']


def verify_peer_route(plan,binding,peer_observation,route_observation,now):
    """Check actual readbacks against an independently recorded creation binding.

    Binding IDs must come from the private once-only create journal. This pure
    check neither records custody nor proves TLS connectivity.
    """
    matches=[r for r in plan['peer_routes'] if r['source']==binding['source'] and r['target']==binding['target']]
    c.need(len(matches)==1 and all(binding.get(k)==v for k,v in matches[0].items()),'route_plan_changed')
    for key,pattern in [('peering_id','pcx'),('route_table_id','rtb'),('source_vpc_id','vpc'),('target_vpc_id','vpc')]:
        c.need(re.fullmatch(pattern+r'-[a-f0-9]{8,17}',binding.get(key,'')),'recorded_route_identity_required')
    peer=_fresh_raw(peer_observation,now);table=_fresh_raw(route_observation,now)
    for observation in (peer_observation,route_observation):
        c.need(observation.get('account')==plan['account'] and observation.get('region')==binding['source_region'],
               'route_observation_scope_changed')
    for raw in (peer,table):
        tags={t['Key']:t['Value'] for t in raw.get('Tags',[])}
        c.need(all(tags.get(k)==v for k,v in {'netclaw-spec':'199','netclaw-stage':str(plan['stage']),'netclaw-run':plan['run_id']}.items()),'foreign_regional_network')
    c.need(peer.get('VpcPeeringConnectionId')==binding['peering_id'] and peer.get('Status',{}).get('Code')=='active','exact_active_peering_required')
    source_is_requester=binding['requester_node']==binding['source']
    for role,side in [('RequesterVpcInfo','source' if source_is_requester else 'target'),('AccepterVpcInfo','target' if source_is_requester else 'source')]:
        row=peer.get(role,{})
        c.need(row.get('OwnerId')==plan['account'] and row.get('Region')==binding[side+'_region']
               and row.get('VpcId')==binding[side+'_vpc_id'],'peering_endpoint_changed')
    c.need(table.get('RouteTableId')==binding['route_table_id'] and table.get('VpcId')==binding['source_vpc_id'],'route_table_changed')
    rows=[r for r in table.get('Routes',[]) if r.get('DestinationCidrBlock')==binding['destination']]
    c.need(len(rows)==1 and rows[0].get('VpcPeeringConnectionId')==binding['peering_id']
           and rows[0].get('State')=='active' and rows[0].get('Origin')=='CreateRoute','peer_route_changed_or_blackhole')
    c.need(not any(rows[0].get(k) for k in ('GatewayId','NatGatewayId','TransitGatewayId','NetworkInterfaceId','InstanceId')),'unexpected_route_target')
    return True


def timing_check(manifest,expected_manifest_sha256,measurements,now):
    """Assess measured admission against already-frozen limits; never widen them.

    Caller verifies the signed manifest through the existing protocol first.
    Samples are measured admission round trips, not ICMP or TCP RTT estimates.
    This check does not establish quorum health or authorize dispatch.
    """
    c.need(c.digest(manifest)==expected_manifest_sha256,'frozen_manifest_changed')
    ids=[n['node_id'] for n in manifest['nodes']]
    c.need(len(ids)==len(set(ids))==3,'three_distinct_manifest_nodes_required')
    limits=manifest['limits'];window=limits['admission_ms'];uncertainty=limits['clock_uncertainty_ms']
    c.need(type(window) is int and type(uncertainty) is int and 0<=uncertainty<window/2,'signed_timing_limits_required')
    expected={(a,b) for a in ids for b in ids if a!=b};seen=set()
    for row in measurements:
        pair=(row['source'],row['target'])
        c.need(pair in expected and pair not in seen,'exact_directed_admission_matrix_required');seen.add(pair)
        c.need(row.get('manifest_sha256')==expected_manifest_sha256 and
               type(row.get('observed_at')) in (int,float) and 0<=now-row['observed_at']<=30,'fresh_manifest_bound_measurement_required')
        duration=row.get('admission_roundtrip_ms')
        c.need(type(duration) is int and 0<duration<window-2*uncertainty,'measured_admission_exceeds_signed_window')
    c.need(seen==expected,'complete_admission_matrix_required')
    return {'manifest_sha256':expected_manifest_sha256,'measured_pairs':6,
        'manifest_wait_seconds':max(5.0,window/1000),'dispatch_authorized':False}
