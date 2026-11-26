"""Evidence-first cleanup of recorded AWS resources, including expired leases.

Cleanup cannot create resources, release a reservation, or resolve an unknown
provider operation. Each mutation consumes its own durable journal entry.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import campaign as c
import lifecycle as life
from preflight import save

TARGETS = {
    'instance': ('ec2','terminate-instances','InstanceIds'),
    'volume': ('ec2','delete-volume','VolumeId'),
    'eni': ('ec2','delete-network-interface','NetworkInterfaceId'),
    'key-pair': ('ec2','delete-key-pair','KeyPairId'),
    'security-group': ('ec2','delete-security-group','GroupId'),
    'route-table': ('ec2','delete-route-table','RouteTableId'),
    'subnet': ('ec2','delete-subnet','SubnetId'),
    'internet-gateway': ('ec2','delete-internet-gateway','InternetGatewayId'),
    'vpc': ('ec2','delete-vpc','VpcId'),
    'vpc-peering': ('ec2','delete-vpc-peering-connection','VpcPeeringConnectionId'),
    'role': ('iam','delete-role','RoleName'),
    'schedule': ('scheduler','delete-schedule','Name'),
    'schedule-group': ('scheduler','delete-schedule-group','Name'),
}


def fresh(observed, now):
    c.need(observed.get('query_succeeded') is True, 'successful_observation_required')
    age = now - observed.get('observed_at', 0)
    c.need(0 <= age <= 30, 'fresh_observation_required')


def validate_dependencies(record, samples, now):
    for identity in record.get('depends_on_absence', []):
        sample = samples.get(identity, {})
        fresh(sample, now)
        c.need(sample.get('absent') is True, 'dependency_still_present')


def deletion(record, observed, now, journal=None):
    fresh(observed, now)
    c.need(observed.get('absent') is not True, 'already_absent_reconcile_only')
    kind = record['kind']
    c.need(kind in TARGETS, 'unsupported_cleanup_kind')
    service, operation, field = TARGETS[kind]
    value = record['id']
    journal=journal or {}
    namespace=record.get('journal_namespace','')
    if record.get('origin_action') and kind in ('route-table','vpc-peering'):
        raw=observed['raw']
        c.need(c.digest(raw)==observed.get('raw_sha256'),'cleanup_observation_changed')
        if kind=='vpc-peering':
            for side,region,vpc in [('RequesterVpcInfo',record['region'],record['requester_vpc']),
                                    ('AccepterVpcInfo',record['peer_region'],record['accepter_vpc'])]:
                row=raw.get(side,{})
                c.need(row.get('OwnerId')==record['account'] and row.get('Region')==region
                       and row.get('VpcId')==vpc,'peering_endpoint_changed')
        else:
            expected=[]
            for row in journal.values():
                request=row.get('request',{})
                if row.get('operation')=='create-route' and request.get('RouteTableId')==record['id']:
                    c.need(row.get('state')=='observed' and c.digest(request)==row['resolved_request_sha256'],
                           'unknown_route_keeps_network')
                    expected.append({k:v for k,v in request.items() if k!='RouteTableId'})
            actual=[]
            for row in raw.get('Routes',[]):
                route={k:v for k,v in row.items() if k not in ('Origin','State')}
                if route=={'DestinationCidrBlock':record['vpc_cidr'],'GatewayId':'local'}:continue
                c.need(row.get('Origin')=='CreateRoute','foreign_route_refused')
                actual.append(route)
            c.need(sorted(map(c.digest,actual))==sorted(map(c.digest,expected)),'foreign_route_refused')
    # Remove only a dependency whose exact ID came from this attempt.
    # A later invocation then observes the parent anew before deleting it.
    if kind=='route-table' and observed.get('associations'):
        association=life.resolve({'$ref':namespace+'route-association.AssociationId'},journal)
        rows=observed['associations']
        c.need(len(rows)==1 and rows[0]['RouteTableAssociationId']==association and not rows[0].get('Main'),
               'foreign_route_association_refused')
        return {'name':'detach-'+c.digest([kind,record['id']])[:24],'service':'ec2','operation':'disassociate-route-table',
                'region':record['region'],'request':{'AssociationId':association}}
    if kind=='internet-gateway' and observed.get('attachments'):
        vpc=life.resolve({'$ref':namespace+'vpc.Vpc.VpcId'},journal)
        c.need(len(observed['attachments'])==1 and observed['attachments'][0]['VpcId']==vpc,'foreign_gateway_attachment_refused')
        return {'name':'detach-'+c.digest([kind,record['id']])[:24],'service':'ec2','operation':'detach-internet-gateway',
                'region':record['region'],'request':{'VpcId':vpc,'InternetGatewayId':record['id']}}
    if kind=='role' and observed.get('inline_policies'):
        c.need(observed['inline_policies']==['StopOwnedInstance'],'foreign_inline_policy_refused')
        policy=journal.get(namespace+'stop-policy',{})
        c.need(policy.get('state')=='observed','observed_policy_creation_required')
        request=policy['request']
        c.need(c.digest(request)==policy['resolved_request_sha256'],'policy_request_changed')
        c.need(observed.get('policy_document')==json.loads(request['PolicyDocument']),'changed_role_policy_refused')
        return {'name':'detach-'+c.digest([kind,record['id']])[:24],'service':'iam','operation':'delete-role-policy',
                'region':record['region'],'request':{'RoleName':record['name'],'PolicyName':'StopOwnedInstance'}}
    if kind in ('role','schedule','schedule-group'):
        c.need(observed.get('created_at') == record.get('created_at') and bool(record.get('created_at')),
               'recreated_named_resource_refused')
        c.need(observed.get('name') == record.get('name') and bool(record.get('name')), 'resource_name_mismatch')
        value = record['name']
    if kind == 'instance': value = [value]
    if kind == 'volume':
        c.need(observed.get('state') == 'available' and observed.get('attachments') == [], 'volume_still_attached')
    if kind == 'eni':
        c.need(observed.get('state') == 'available' and not observed.get('attachment'), 'interface_still_attached')
    if kind == 'route-table':
        c.need(observed.get('associations') == [], 'route_table_still_associated')
    if kind == 'internet-gateway':
        c.need(observed.get('attachments') == [], 'gateway_still_attached')
    if kind == 'role':
        c.need(observed.get('inline_policies') == [] and observed.get('attached_policies') == []
               and observed.get('instance_profiles') == [], 'role_dependencies_remain')
    if kind == 'schedule-group':
        c.need(observed.get('schedules') == [], 'schedules_remain')
    request = {field:value}
    if kind == 'schedule':
        c.need(observed.get('group') == record.get('group') and bool(record.get('group')), 'schedule_group_mismatch')
        request['GroupName'] = record['group']
    return {'name':'retire-'+c.digest([kind,record['id']])[:24], 'service':service,'operation':operation,
            'region':record['region'],'request':request}


def begin(state, packet, record, observed, samples, export_sha, now):
    """An expired/unknown parent does not disable safe cleanup, nor authorize creates."""
    entry = state['reservations'].get(packet['attempt_id'])
    c.need(entry and entry['packet_sha256'] == c.digest(packet), 'reservation_mismatch')
    c.need(state['account'] == packet['account'] and state['campaign_id'] == packet['campaign_id'], 'campaign_mismatch')
    c.need(entry['state'] != 'settled', 'settled_attempt_refused')
    custody = entry.get('custody', {}).get(record['id'])
    c.need(custody and custody['record_sha256'] == c.digest(record), 'recorded_custody_required')
    if record['kind']=='instance':c.need(custody.get('dependents_recorded') is True,'instance_dependents_required')
    life.ownership(record, observed, packet['account'], life.packet_region(packet,record['region']), packet['run_id'], packet['stage'])
    # Keep independent stop and network access until every owned VM is absent.
    # A caller cannot omit this dependency from an individual resource record.
    if record['kind'] not in ('instance','volume','eni'):
        for name,launch in entry.get('actions',{}).items():
            if (name!='instance' and launch.get('operation')!='run-instances') or launch.get('state')=='rejected':continue
            c.need(launch.get('state')=='observed','unknown_compute_keeps_guard_and_network')
            c.need(any(row.get('record',{}).get('kind')=='instance' and
                       (name=='instance' or row['record'].get('origin_action')==name)
                       for row in entry.get('custody',{}).values()),
                   'unrecorded_compute_keeps_guard_and_network')
        for item in entry.get('custody',{}).values():
            parent=item.get('record',{})
            if parent.get('kind')=='instance':
                sample=samples.get(parent['id'],{})
                fresh(sample,now)
                c.need(sample.get('absent') is True,'owned_compute_still_present')
    if record['kind']=='vpc':
        for name,action in entry.get('actions',{}).items():
            if action.get('operation')!='create-vpc-peering-connection' or action.get('state')=='rejected':continue
            c.need(action.get('state')=='observed','unknown_peering_keeps_network')
            peers=[r['record'] for r in entry.get('custody',{}).values() if r['record'].get('origin_action')==name]
            c.need(len(peers)==1,'unrecorded_peering_keeps_network')
            sample=samples.get(peers[0]['id'],{});fresh(sample,now)
            c.need(sample.get('absent') is True,'owned_peering_still_present')
    validate_dependencies(record, samples, now)
    action = deletion(record, observed, now, entry.get('actions',{}))
    journal = entry.setdefault('cleanup', {})
    c.need(action['name'] not in journal, 'cleanup_already_sent_reconcile_only')
    journal[action['name']] = {'state':'sent','action':action,'action_sha256':c.digest(action),
        'record_sha256':c.digest(record),'observation_sha256':c.digest(observed),
        'export_sha256':export_sha,'sent_at':now}
    state['revision'] += 1
    return action


def finish(state, packet, action, response=None, error=None):
    row = state['reservations'][packet['attempt_id']]['cleanup'][action['name']]
    c.need(row['state']=='sent' and row['action_sha256']==c.digest(action),'cleanup_journal_mismatch')
    if error is None:row.update(state='returned',response=response,response_sha256=c.digest(response))
    else:row.update(state='unknown',error_class=error)
    state['revision'] += 1


def execute(root, packet, record, observed, samples, export_root, manifest, profile, actual_account, invoke=None):
    c.need(actual_account == packet['account'], 'live_account_mismatch')
    export_sha = life.verify_export(export_root, manifest, [record['id']])
    now = datetime.now(timezone.utc).timestamp()
    action = c.transaction(root, lambda state: begin(state,packet,record,observed,samples,export_sha,now))
    path = Path(root)/('cleanup-'+packet['attempt_id']+'-'+action['name']+'.json')
    try:
        save(path,action['request'])
        result = (invoke or subprocess.run)(['aws',action['service'],action['operation'],'--profile',profile,
            '--region',action['region'],'--cli-input-json','file://'+str(path),'--output','json',
            '--no-cli-pager','--cli-connect-timeout','8','--cli-read-timeout','30'],
            capture_output=True,text=True,timeout=60,check=False,
            env=dict(os.environ,AWS_PAGER='',AWS_MAX_ATTEMPTS='1'))
        save(path.with_name(path.stem+'-result.json'),
             {'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
        if result.returncode:raise RuntimeError('cleanup_response_requires_reconciliation')
        response=json.loads(result.stdout or '{}')
    except Exception as exc:
        c.transaction(root,lambda state:finish(state,packet,action,error=type(exc).__name__))
        raise
    c.transaction(root,lambda state:finish(state,packet,action,response=response))
    return response


def confirm_absence(state, packet, record, observations):
    life.verify_absence(observations,[record['id']])
    entry = state['reservations'][packet['attempt_id']]
    c.need(entry['packet_sha256']==c.digest(packet),'reservation_mismatch')
    row=entry.get('custody',{}).get(record['id'])
    c.need(row and row['record_sha256']==c.digest(record),'recorded_custody_required')
    row.update(disposition='absent',absence_sha256=c.digest(observations))
    # A deleted resource does not prove unknown remote model work never happened.
    state['revision']+=1
