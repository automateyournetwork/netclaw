#!/usr/bin/env python3
"""Private single-stage operator CLI; one recorded AWS mutation per invocation."""
import argparse
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid
import aws_api
import campaign as c
import cleanup
import lifecycle as life
import network
from preflight import fresh_private_dir, save

SOURCE = Path(__file__).resolve().parent


def source_closure():
    return {path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(SOURCE.iterdir())
            if path.is_file() and path.suffix in ('.py','.sh')}


def verify_source(root,packet):
    current=source_closure()
    if current==packet['source_files']:return True
    # An observation-only qualification repair is separately frozen, never a
    # rewrite of a consumed packet, cloud request, identity or execution result.
    receipt=c.read_private(Path(root)/'source-observation-repair.json')
    c.need(receipt.get('packet_sha256')==c.digest(packet) and receipt.get('before')==packet['source_files']
           and receipt.get('after')==current and receipt.get('class')=='azure-empty-group-observation-only'
           and {k for k in set(current)|set(packet['source_files']) if current.get(k)!=packet['source_files'].get(k)}=={'external.py','run.py'}
           and receipt.get('actions_sha256')==c.digest(c.read_private(Path(root)/'actions.json'))
           and receipt.get('external_plan_sha256')==packet.get('external_plan_sha256'), 'lifecycle_source_changed')
    for name in ('external.py','run.py'):
        before=Path(root)/'source-before-azure-observation-repair'/name
        c.need(hashlib.sha256(before.read_bytes()).hexdigest()==packet['source_files'][name],'repair_baseline_changed')
    return True


def load(root, allow_source_change=False):
    root=c.owned_directory(Path(root));packet=c.read_private(root/'packet.json')
    definitions=c.read_private(root/'actions.json')
    if not allow_source_change:
        try:verify_source(root,packet)
        except FileNotFoundError:raise ValueError('lifecycle_source_changed') from None
    c.need(packet['actions']=={a['name']:c.digest(a) for a in definitions},'frozen_actions_changed')
    return root,packet,definitions


def plan(config, root):
    """Config includes freshly observed rates/baseline; no cloud call or activation."""
    stage=config['stage']
    c.need(config['region']=='us-east-2' and type(stage) is int and stage in (1,2,3),'single_ohio_stage_only')
    c.need(config.get('readiness_sha256') and config.get('pricing_sha256'),'fresh_readiness_price_receipts_required')
    root=fresh_private_dir(str(root))
    state=c.read_private(config['predecessor_ledger']) if config.get('predecessor_ledger') else c.new_campaign(config['account'])
    c.check_state(state)
    c.need(state['account']==config['account'] and state['accepted_stage']==stage-1,'accepted_predecessor_required')
    c.need(all(row['state']=='settled' for row in state['reservations'].values()),'prior_attempt_obligations_remain')
    key=root/'ssh-key'
    subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-C','spec199-owned-ephemeral','-f',str(key)],check=True)
    os.chmod(str(key)+'.pub',0o600)
    now=datetime.now(timezone.utc).replace(microsecond=0)
    seconds=config.get('lease_seconds',7200)
    c.need(type(seconds) is int and 900<=seconds<=c.MAX_SECONDS[stage],'bounded_lease_required')
    deadline=now+timedelta(seconds=seconds)
    attempt=str(uuid.uuid4());prefix='nc199-'+uuid.uuid4().hex[:12];token='nc199-'+uuid.uuid4().hex
    actions=network.first_border(config['account'],config['region'],config['zone'],prefix,deadline.isoformat(),
        token,config['ami'],config['operator_cidr'],Path(str(key)+'.pub').read_text(),config['instance_type'],stage=stage)
    hours=Decimal(seconds)/Decimal(3600)
    # No credit/free-tier deductions. Whole-GB transfer allocation and one day of
    # stopped root storage reserve supplement the campaign's protected cleanup floor.
    compute=c.money(config['compute_usd_hour'])*hours
    ip=c.money(config['ipv4_usd_hour'])*hours
    disk=c.money(config['gp3_usd_gb_month'])*40*(hours+24)/Decimal(720)
    transfer=c.money(config['egress_usd_gb'])*c.money(config.get('egress_gb',3))
    subtotal=compute+ip+disk+transfer+Decimal('0.01')
    bound=c.money(config.get('aws_reservation','2'))
    c.need(subtotal<=bound,'cost_components_exceed_reservation')
    packet={'schema':1,'campaign_id':state['campaign_id'],'account':state['account'],'stage':stage,
        'source_sha':config['source_sha'],'source_files':source_closure(),'region':config['region'],
        'attempt_id':attempt,'run_id':prefix,'client_token':token,'created_at':now.isoformat(),'deadline':deadline.isoformat(),
        'resources':[{'kind':a['operation'],'name':a['name']} for a in actions],
        'costs':{'aws':str(bound),'external':str(c.money(config.get('external_reservation','1')))},
        'cost_components':{'compute':str(compute),'ipv4':str(ip),'root_and_one_day_hold':str(disk),
                           'egress':str(transfer),'scheduler_margin':'0.01'},
        'baseline_ids':config['baseline_ids'],'readiness_sha256':config['readiness_sha256'],
        'pricing_sha256':config['pricing_sha256'],'actions':{a['name']:c.digest(a) for a in actions}}
    if config.get('predecessor_ledger'):packet['predecessor_ledger_sha256']=c.digest(c.read_private(config['predecessor_ledger']))
    if stage>1:packet['predecessor_sha256']=state['receipts'][str(stage-1)]['sha256']
    c.reserve(state,packet,now.timestamp())
    save(root/'campaign.json',state);save(root/'packet.json',packet);save(root/'actions.json',actions)
    return {'run_id':prefix,'stage':stage,'deadline':packet['deadline'],'reserved':packet['costs'],'activation_performed':False}


def api_for(root, packet, profile):
    api=aws_api.ReadAPI(profile,packet['region'],root)
    account=api.account();c.need(account==packet['account'],'live_account_mismatch')
    return api,account


def seed_record(packet, kind, journal):
    origin,path=aws_api.ORIGINS[kind]
    identity=life.resolve({'$ref':origin+'.'+path},journal)
    row={'kind':kind,'id':identity,'account':packet['account'],'region':packet['region']}
    if kind=='role':row['name']=packet['run_id']+'-stop'
    if kind=='schedule-group':row['name']=packet['run_id']+'-stop'
    if kind=='schedule':row.update(name=packet['run_id']+'-deadline',group=packet['run_id']+'-stop',
        group_arn=life.resolve({'$ref':'stop-group.ScheduleGroupArn'},journal))
    return row


def observe_created(root, packet, api, account):
    state=c.read_private(root/'campaign.json');entry=state['reservations'][packet['attempt_id']]
    captured=[]
    for kind,(origin,_) in aws_api.ORIGINS.items():
        if entry.get('actions',{}).get(origin,{}).get('state')!='observed':continue
        seed=seed_record(packet,kind,entry['actions'])
        if seed['id'] in entry.get('custody',{}):continue
        obs=api.observe(seed,account)
        record=c.transaction(root,lambda s:aws_api.record_creation(s,packet,kind,obs,packet['baseline_ids']))
        captured.append(record['kind'])
    state=c.read_private(root/'campaign.json');entry=state['reservations'][packet['attempt_id']]
    for row in entry.get('custody',{}).values():
        record=row['record']
        if record['kind']!='instance' or row.get('dependents_recorded'):continue
        instance=api.observe(record,account);raw=instance['raw']
        refs=[('volume',x['Ebs']['VolumeId']) for x in raw.get('BlockDeviceMappings',[]) if 'Ebs' in x]
        refs += [('eni',x['NetworkInterfaceId']) for x in raw.get('NetworkInterfaces',[])]
        observations=[api.observe(dict(record,kind=kind,id=identity),account) for kind,identity in refs]
        c.transaction(root,lambda s:aws_api.record_instance_dependents(s,packet,instance,observations,packet['baseline_ids']))
        captured.extend(kind for kind,_ in refs)
    return captured


def apply_one(root, packet, definitions, name, profile):
    action=next((a for a in definitions if a['name']==name),None);c.need(action,'unknown_action')
    state=c.read_private(root/'campaign.json');journal=state['reservations'][packet['attempt_id']].get('actions',{})
    index=definitions.index(action)
    c.need(all(journal.get(a['name'],{}).get('state')=='observed' for a in definitions[:index]),'prior_action_not_observed')
    api,account=api_for(root,packet,profile)
    if name=='egress-close':
        group=seed_record(packet,'security-group',journal);obs=api.observe(group,account)
        c.need(obs['raw']['IpPermissionsEgress']==[{'IpProtocol':'-1','IpRanges':[{'CidrIp':'0.0.0.0/0'}],
            'Ipv6Ranges':[],'PrefixListIds':[],'UserIdGroupPairs':[]}],'unexpected_initial_egress')
    life.execute_once(root,packet,action,profile,account)
    captured=observe_created(root,packet,api,account)
    return {'action':name,'state':'observed','captured_kinds':captured}


def retire_one(root,packet,identity,manifest_path,profile):
    manifest=c.read_private(manifest_path);export_root=Path(manifest_path).parent
    state=c.read_private(root/'campaign.json');entry=state['reservations'][packet['attempt_id']]
    c.need(identity in entry.get('custody',{}),'owned_identity_required')
    record=entry['custody'][identity]['record'];api,account=api_for(root,packet,profile)
    samples={}
    for row in entry['custody'].values():
        other=row['record']
        if other['kind']=='instance' or other['id'] in record.get('depends_on_absence',[]):
            samples[other['id']]=api.observe(other,account)
    observed=api.observe(record,account)
    if observed['absent']:return {'state':'absent_observed','requires_repeated_confirmation':True}
    cleanup.execute(root,packet,record,observed,samples,export_root,manifest,profile,account)
    return {'state':'cleanup_returned','absence_proven':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('verb',choices=['plan','apply-one','observe','retire-one','status'])
    p.add_argument('--root',required=True);p.add_argument('--config');p.add_argument('--action')
    p.add_argument('--resource-id');p.add_argument('--export-manifest');p.add_argument('--profile',default='NetClaw')
    a=p.parse_args()
    if a.verb=='plan':result=plan(c.read_private(a.config),Path(a.root))
    else:
        root,packet,definitions=load(a.root,allow_source_change=a.verb in ('observe','retire-one','status'))
        if a.verb=='apply-one':result=apply_one(root,packet,definitions,a.action,a.profile)
        elif a.verb=='observe':
            api,account=api_for(root,packet,a.profile);result={'captured_kinds':observe_created(root,packet,api,account)}
        elif a.verb=='retire-one':result=retire_one(root,packet,a.resource_id,a.export_manifest,a.profile)
        else:
            state=c.read_private(root/'campaign.json');entry=state['reservations'][packet['attempt_id']]
            result={'stage':packet['stage'],'deadline':packet['deadline'],'reservation_state':entry['state'],
                'actions':{name:row['state'] for name,row in entry.get('actions',{}).items()},
                'owned_resources':len(entry.get('custody',{})),'totals':c.totals(state)}
    print(json.dumps(result,default=str,indent=2))


if __name__=='__main__':main()
