#!/usr/bin/env python3
"""Stage4 regional lifecycle: frozen graph, one send, region-bound custody.

Planning is local. Every apply consumes one journal entry, requires a fresh
account read and stops on any unresolved prior action. Cleanup remains usable
after a lease expires, but requires a quiescent export and fresh dependencies.
"""
import argparse
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
import json
import os
import subprocess
import time
import uuid
import aws_api
import campaign as c
import cleanup
import lifecycle as life
import regional
import run
from preflight import fresh_private_dir, save


def origins(graph):
    rows={}
    for node in graph['nodes']:
        namespace=node['code']+'-'
        for kind,(action,path) in aws_api.ORIGINS.items():
            key=namespace+kind
            rows[key]=dict(key=key,kind=kind,action=namespace+action,path=path,
                           region=node['region'],namespace=namespace)
            if kind=='route-table':rows[key]['vpc_cidr']=node['vpc_cidr']
    for action in graph['actions']:
        if action['operation']=='create-vpc-peering-connection':
            key=action['name']
            rows[key]=dict(key=key,kind='vpc-peering',action=key,
                path='VpcPeeringConnection.VpcPeeringConnectionId',region=action['region'],namespace='')
    return rows


def cost_components(graph, reports, pricing, seconds, now):
    ready=regional.ready_regions(graph['account'],reports,now,graph.get('qualification_scope','three-region'))
    c.need(set(pricing)==set(ready),'three_region_prices_required')
    hours=Decimal(seconds)/3600;result={}
    for node in graph['nodes']:
        region=node['region'];row=ready[region]
        quote=pricing[region]
        c.need(0<=now-quote['observed_at']<=900 and c.digest(quote['raw'])==quote['raw_sha256'],
               'fresh_pricing_receipt_required')
        rates=quote['rates']
        c.need(set(rates)=={'ipv4_usd_hour','gp3_usd_gb_month','egress_usd_gb','peering_usd_gb'},'full_regional_rates_required')
        c.need(all(c.money(v)>0 for v in rates.values()),'gross_positive_prices_required')
        # Three GB public transfer + two GB cross-region per host, plus a whole
        # day of stopped storage. Both endpoints' transfer is reserved separately.
        result[node['code']]={'compute':str(c.money(row['compute_usd_hour'])*hours),
            'ipv4':str(c.money(rates['ipv4_usd_hour'])*hours),
            'disk_and_hold':str(c.money(rates['gp3_usd_gb_month'])*40*(hours+24)/720),
            'egress':str(c.money(rates['egress_usd_gb'])*3),
            'peering':str(c.money(rates['peering_usd_gb'])*2),'scheduler_margin':'0.01'}
    return result


def plan(config, root):
    state=c.read_private(config['predecessor_ledger']);c.check_state(state)
    stage=config.get('stage',4)
    c.need(stage in (4,5),'regional_stage_required')
    c.need(state['account']==config['account'] and state['accepted_stage']==stage-1,'accepted_predecessor_required')
    c.need(all(row['state']=='settled' for row in state['reservations'].values()),'prior_attempt_obligations_remain')
    # Keep subsecond precision: a just-finished observation can otherwise look
    # future-dated after rounding this clock down to the previous whole second.
    now=datetime.now(timezone.utc);seconds=config['lease_seconds']
    c.need(type(seconds) is int and 900<=seconds<=c.MAX_SECONDS[stage],'bounded_lease_required')
    scope=config.get('qualification_scope','three-region')
    regional.ready_regions(config['account'],config['reports'],now.timestamp(),scope)
    root=fresh_private_dir(str(root));key=root/'ssh-key'
    subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-C','spec199-regional-ephemeral','-f',str(key)],check=True)
    os.chmod(str(key)+'.pub',0o600)
    run_id='nc199-'+uuid.uuid4().hex[:12];deadline=(now+timedelta(seconds=seconds)).isoformat()
    graph=regional.draft(config['account'],run_id,config['reports'],config['nodes'],deadline=deadline,
        operator_cidr=config['operator_cidr'],public_key=Path(str(key)+'.pub').read_text(),now=now.timestamp(),
        scope=scope,scope_amendment_sha256=config.get('scope_amendment_sha256'),stage=stage)
    costs=cost_components(graph,config['reports'],config['pricing'],seconds,now.timestamp())
    bound=c.money(config['aws_reservation'])
    c.need(sum(c.money(v) for row in costs.values() for v in row.values())<=bound,'cost_components_exceed_reservation')
    packet={'schema':1,'campaign_id':state['campaign_id'],'account':state['account'],'stage':stage,
        'region':graph['nodes'][0]['region'],'regions':sorted({n['region'] for n in graph['nodes']}),
        'qualification_scope':scope,'scope_amendment_sha256':graph['scope_amendment_sha256'],
        'zones':{n['zone']:n.get('zone_id') for n in graph['nodes']},
        'source_sha':config['source_sha'],'source_files':run.source_closure(),'run_id':run_id,
        'attempt_id':str(uuid.uuid4()),'client_token':'nc199-'+uuid.uuid4().hex,
        'created_at':now.isoformat(),'deadline':deadline,'regional_graph_sha256':c.digest(graph),
        'resource_origins':origins(graph),'baseline_ids':config['baseline_ids'],
        'resources':[{'kind':a['operation'],'name':a['name']} for a in graph['actions']],
        'actions':{a['name']:c.digest(a) for a in graph['actions']},'cost_components':costs,
        'costs':{'aws':str(bound),'external':str(c.money(config['external_reservation']))},
        'predecessor_sha256':state['receipts'][str(stage-1)]['sha256'],'predecessor_ledger_sha256':c.digest(state),
        'readiness_sha256':c.digest(config['reports']),'pricing_sha256':c.digest(config['pricing'])}
    external_plan=None
    if config.get('external_config'):
        import external,mesh
        external_plan=external.plan(graph,config['external_config'],Path(str(key)+'.pub').read_text())
        c.need(sum(c.money(v) for v in external_plan['cost_components'].values())<=c.money(packet['costs']['external']),
               'external_cost_components_exceed_reservation')
        packet.update(external_plan_sha256=c.digest(external_plan),mesh_recipe=mesh.RECIPE)
    c.reserve(state,packet,now.timestamp())
    for name,value in [('campaign',state),('packet',packet),('actions',graph['actions']),('regional',graph),
                        ('readiness',config['reports']),('pricing',config['pricing'])]:save(root/(name+'.json'),value)
    if external_plan:save(root/'external-plan.json',external_plan)
    return {'stage':stage,'run_id':run_id,'deadline':deadline,'reserved':packet['costs'],'activation_performed':False}


def load(root, allow_source_change=False):
    root,packet,definitions=run.load(root,allow_source_change)
    c.need(packet['stage'] in (4,5),'regional_stage_required')
    graph=c.read_private(root/'regional.json')
    c.need(graph['stage']==packet['stage'] and c.digest(graph)==packet['regional_graph_sha256'] and origins(graph)==packet['resource_origins'],
           'regional_graph_changed')
    c.need(graph.get('qualification_scope','three-region')==packet.get('qualification_scope','three-region'),
           'qualification_scope_changed')
    if packet.get('qualification_scope')=='ohio-three-az':
        c.need(packet['zones']=={n['zone']:n['zone_id'] for n in graph['nodes']}
               and graph['scope_amendment_sha256']==packet['scope_amendment_sha256'],'frozen_az_scope_changed')
    return root,packet,definitions,graph


def api_for(root,packet,profile,region):
    life.packet_region(packet,region);api=aws_api.ReadAPI(profile,region,root)
    account=api.account();c.need(account==packet['account'],'live_account_mismatch')
    return api,account


def seed(packet, descriptor, journal):
    action=journal[descriptor['action']]
    c.need(c.digest(action['request'])==action['resolved_request_sha256'],'creation_request_changed')
    row={'kind':descriptor['kind'],'id':life.resolve({'$ref':descriptor['action']+'.'+descriptor['path']},journal),
         'account':packet['account'],'region':descriptor['region']}
    if row['kind']=='role':row['name']=action['request']['RoleName']
    if row['kind'] in ('schedule','schedule-group'):row['name']=action['request']['Name']
    if row['kind']=='schedule':row.update(group=action['request']['GroupName'],
        group_arn=life.resolve({'$ref':descriptor['namespace']+'stop-group.ScheduleGroupArn'},journal))
    return row


def observe_created(root,packet,profile):
    state=c.read_private(root/'campaign.json');entry=state['reservations'][packet['attempt_id']];captured=[]
    apis={}
    def api(region):
        if region not in apis:apis[region]=api_for(root,packet,profile,region)[0]
        return apis[region]
    journal=entry.get('actions',{})
    for descriptor in packet['resource_origins'].values():
        if journal.get(descriptor['action'],{}).get('state')!='observed':continue
        record=seed(packet,descriptor,journal)
        if record['id'] in entry.get('custody',{}):continue
        obs=api(record['region']).observe(record,packet['account'])
        c.transaction(root,lambda s:aws_api.record_creation(s,packet,record['kind'],obs,packet['baseline_ids'],descriptor))
        captured.append(record['id'])
    state=c.read_private(root/'campaign.json');entry=state['reservations'][packet['attempt_id']]
    for row in entry.get('custody',{}).values():
        record=row['record']
        if record['kind']!='instance' or row.get('dependents_recorded'):continue
        reader=api(record['region']);obs=reader.observe(record,packet['account']);raw=obs['raw']
        refs=[('volume',v['Ebs']['VolumeId']) for v in raw.get('BlockDeviceMappings',[]) if 'Ebs' in v]
        refs += [('eni',v['NetworkInterfaceId']) for v in raw.get('NetworkInterfaces',[])]
        dependent=[reader.observe(dict(record,kind=k,id=i),packet['account']) for k,i in refs]
        c.transaction(root,lambda s:aws_api.record_instance_dependents(s,packet,obs,dependent,packet['baseline_ids']))
        captured.extend(i for _,i in refs)
    return captured


def peer_guard(packet,record,observation,now):
    cleanup.fresh(observation,now)
    life.ownership(record,observation,packet['account'],record['region'],packet['run_id'],packet['stage'])
    raw=observation['raw'];c.need(c.digest(raw)==observation['raw_sha256'],'peering_observation_changed')
    for side,region,vpc in [('RequesterVpcInfo',record['region'],record['requester_vpc']),
                           ('AccepterVpcInfo',record['peer_region'],record['accepter_vpc'])]:
        v=raw.get(side,{})
        c.need(v.get('OwnerId')==packet['account'] and v.get('Region')==region and v.get('VpcId')==vpc,
               'peering_endpoint_changed')
    return raw.get('Status',{}).get('Code')


def apply_one(root,packet,definitions,name,profile):
    if packet['stage']==5:c.need(packet.get('external_plan_sha256') and packet.get('mesh_recipe'),'complete_mesh_packet_required')
    c.need(packet['source_files']==run.source_closure(),'lifecycle_source_changed')
    c.need(packet['actions']=={a['name']:c.digest(a) for a in definitions},'frozen_actions_changed')
    action=next((a for a in definitions if a['name']==name),None);c.need(action,'unknown_action')
    observe_created(root,packet,profile)
    entry=c.read_private(root/'campaign.json')['reservations'][packet['attempt_id']];journal=entry.get('actions',{})
    c.need(all(journal.get(a['name'],{}).get('state')=='observed' for a in definitions[:definitions.index(action)]),
           'prior_action_not_observed')
    api,account=api_for(root,packet,profile,action['region']);request=life.resolve(action['request'],journal)
    if name.endswith('-egress-close'):
        descriptor=packet['resource_origins'][name[:-len('egress-close')]+'security-group']
        obs=api.observe(seed(packet,descriptor,journal),account)
        c.need(obs['raw']['IpPermissionsEgress']==[{'IpProtocol':'-1','IpRanges':[{'CidrIp':'0.0.0.0/0'}],
            'Ipv6Ranges':[],'PrefixListIds':[],'UserIdGroupPairs':[]}],'unexpected_initial_egress')
    peer_id=request.get('VpcPeeringConnectionId')
    if action['operation']=='create-tags':peer_id=request['Resources'][0]
    if peer_id:
        record=entry.get('custody',{}).get(peer_id,{}).get('record')
        c.need(record and record['kind']=='vpc-peering','recorded_peering_required')
        reader,_=api_for(root,packet,profile,record['region'])
        status=peer_guard(packet,record,reader.observe(record,account),datetime.now(timezone.utc).timestamp())
        expected='pending-acceptance' if action['operation']=='accept-vpc-peering-connection' else 'active'
        c.need(status==expected,'peering_not_in_required_state')
    life.execute_once(root,packet,action,profile,account)
    return {'action':name,'state':'observed','captured':observe_created(root,packet,profile)}


def observe_record(root,packet,profile,record):
    api,account=api_for(root,packet,profile,record['region']);obs=api.observe(record,account)
    if record['kind']=='vpc-peering' and obs['absent']:
        peer=dict(record,region=record['peer_region']);api,_=api_for(root,packet,profile,peer['region'])
        other=api.observe(peer,account)
        c.need(other['absent'],'peering_other_region_still_present')
        obs.update(peer_observation=other,observed_at=datetime.now(timezone.utc).timestamp())
    return obs


def retire_one(root,packet,identity,manifest_path,profile):
    manifest=c.read_private(manifest_path);entry=c.read_private(root/'campaign.json')['reservations'][packet['attempt_id']]
    c.need(identity in entry.get('custody',{}),'owned_identity_required');record=entry['custody'][identity]['record']
    samples={}
    for row in entry['custody'].values():
        other=row['record']
        if other['kind']=='instance' or (record['kind']=='vpc' and other['kind']=='vpc-peering') or other['id'] in record.get('depends_on_absence',[]):
            samples[other['id']]=observe_record(root,packet,profile,other)
    observed=observe_record(root,packet,profile,record)
    if observed['absent']:return {'state':'absent_observed','requires_repeated_confirmation':True}
    cleanup.execute(root,packet,record,observed,samples,Path(manifest_path).parent,manifest,profile,packet['account'])
    return {'state':'cleanup_returned','absence_proven':False}


def confirm_absence(root,packet,identity,profile):
    entry=c.read_private(root/'campaign.json')['reservations'][packet['attempt_id']]
    c.need(identity in entry.get('custody',{}),'owned_identity_required');record=entry['custody'][identity]['record']
    samples=[]
    for index in range(2):
        if index:time.sleep(2.1)
        obs=observe_record(root,packet,profile,record)
        c.need(obs['absent'],'resource_still_present')
        samples.append({'observed_at':datetime.now(timezone.utc).timestamp(),'resources':{identity:obs}})
    save(root/('absence-'+str(uuid.uuid4())+'.json'),samples)
    c.transaction(root,lambda state:cleanup.confirm_absence(state,packet,record,samples))
    return {'resource_id':identity,'state':'absence_confirmed','observations':2}


def verify_routes(root,packet,graph,profile):
    entry=c.read_private(root/'campaign.json')['reservations'][packet['attempt_id']];journal=entry.get('actions',{})
    checks=[]
    for route in graph['peer_routes']:
        def ref(path):return life.resolve({'$ref':path},journal)
        binding=dict(route,peering_id=ref(route['peering_action']+'.VpcPeeringConnection.VpcPeeringConnectionId'),
            route_table_id=ref(route['source']+'-route-table.RouteTable.RouteTableId'),
            source_vpc_id=ref(route['source']+'-vpc.Vpc.VpcId'),target_vpc_id=ref(route['target']+'-vpc.Vpc.VpcId'))
        peer=entry['custody'][binding['peering_id']]['record'];table=entry['custody'][binding['route_table_id']]['record']
        api,account=api_for(root,packet,profile,route['source_region'])
        peer_obs=api.observe(dict(peer,region=route['source_region']),account);table_obs=api.observe(table,account)
        regional.verify_peer_route(graph,binding,peer_obs,table_obs,datetime.now(timezone.utc).timestamp())
        checks.append({'binding':binding,'peering':peer_obs,'route_table':table_obs})
    save(root/('routes-'+str(uuid.uuid4())+'.json'),checks)
    return {'verified_directed_routes':len(checks),'tls_or_quorum_verified':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('verb',choices=['plan','apply-one','observe','retire-one','confirm-absence','verify-routes'])
    p.add_argument('--root',required=True);p.add_argument('--config');p.add_argument('--action')
    p.add_argument('--resource-id');p.add_argument('--export-manifest');p.add_argument('--profile',default='NetClaw')
    a=p.parse_args()
    if a.verb=='plan':result=plan(c.read_private(a.config),Path(a.root))
    else:
        root,packet,definitions,graph=load(a.root,allow_source_change=a.verb!='apply-one')
        if a.verb=='apply-one':result=apply_one(root,packet,definitions,a.action,a.profile)
        elif a.verb=='observe':result={'captured':observe_created(root,packet,a.profile)}
        elif a.verb=='confirm-absence':result=confirm_absence(root,packet,a.resource_id,a.profile)
        elif a.verb=='verify-routes':result=verify_routes(root,packet,graph,a.profile)
        else:result=retire_one(root,packet,a.resource_id,a.export_manifest,a.profile)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
