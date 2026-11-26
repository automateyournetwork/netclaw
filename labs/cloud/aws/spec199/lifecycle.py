#!/usr/bin/env python3
"""Spec199 exact ownership, export verification and once-only AWS API journal.

No account-wide cleanup or automatic write retry. Operator orchestration must
supply a reserved packet, immutable action set and the current account identity.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import campaign as c

WRITE_ACTIONS = {
    ('ec2', 'create-vpc'), ('ec2', 'create-subnet'), ('ec2', 'create-security-group'),
    ('ec2', 'create-internet-gateway'), ('ec2', 'attach-internet-gateway'),
    ('ec2', 'create-route-table'), ('ec2', 'create-route'), ('ec2', 'associate-route-table'),
    ('ec2', 'authorize-security-group-ingress'), ('ec2', 'authorize-security-group-egress'),
    ('ec2', 'revoke-security-group-egress'), ('ec2', 'import-key-pair'),
    ('ec2', 'run-instances'), ('ec2', 'stop-instances'), ('ec2', 'terminate-instances'),
    ('ec2', 'delete-volume'), ('ec2', 'release-address'), ('ec2', 'delete-network-interface'),
    ('ec2', 'delete-key-pair'), ('ec2', 'delete-security-group'), ('ec2', 'disassociate-route-table'),
    ('ec2', 'delete-route-table'), ('ec2', 'delete-subnet'), ('ec2', 'detach-internet-gateway'),
    ('ec2', 'delete-internet-gateway'), ('ec2', 'delete-vpc'),
    ('ec2', 'create-vpc-peering-connection'), ('ec2', 'accept-vpc-peering-connection'),
    ('ec2', 'create-tags'), ('ec2', 'delete-vpc-peering-connection'),
    ('iam', 'create-role'), ('iam', 'put-role-policy'), ('iam', 'delete-role-policy'), ('iam', 'delete-role'),
    ('scheduler', 'create-schedule-group'), ('scheduler', 'create-schedule'),
    ('scheduler', 'delete-schedule'), ('scheduler', 'delete-schedule-group'),
}
DESTRUCTIVE = {pair for pair in WRITE_ACTIONS if pair[1].startswith(('delete-', 'terminate-', 'release-'))}
ID_PATTERNS = {'instance': r'i-[0-9a-f]{8,17}', 'volume': r'vol-[0-9a-f]{8,17}',
    'vpc': r'vpc-[0-9a-f]{8,17}', 'subnet': r'subnet-[0-9a-f]{8,17}',
    'security-group': r'sg-[0-9a-f]{8,17}', 'eni': r'eni-[0-9a-f]{8,17}',
    'internet-gateway': r'igw-[0-9a-f]{8,17}', 'route-table': r'rtb-[0-9a-f]{8,17}',
    'address': r'eipalloc-[0-9a-f]{8,17}', 'vpc-peering': r'pcx-[0-9a-f]{8,17}'}


def packet_region(packet, region):
    """A regional packet freezes the complete set; old packets remain single-region."""
    allowed=packet['regions'] if packet.get('stage') in (4,5) else [packet['region']]
    c.need(region in allowed,'action_region_mismatch')
    return region


def ownership(record, observed, account, region, run_id, stage):
    c.need(record.get('account') == account and record.get('region') == region, 'owner_scope_mismatch')
    c.need(record.get('run_id') == run_id and record.get('stage') == stage, 'run_stage_mismatch')
    c.need(record.get('id') == observed.get('id') and bool(record.get('id')), 'immutable_id_mismatch')
    kind = record.get('kind')
    if kind in ID_PATTERNS: c.need(bool(re.fullmatch(ID_PATTERNS[kind], record['id'])), 'invalid_resource_id')
    c.need(observed.get('account') == account and observed.get('region') == region, 'observed_scope_mismatch')
    c.need(not record.get('baseline') and not observed.get('default') and not observed.get('baseline'), 'foreign_or_default_resource')
    tags = observed.get('tags', {})
    c.need(all(tags.get(k) == v for k,v in {'netclaw-spec': '199', 'netclaw-run': run_id,
        'netclaw-stage': str(stage)}.items()), 'ownership_tags_mismatch')
    c.need(bool(re.fullmatch(r'[0-9a-f]{64}', record.get('create_request_sha256', ''))), 'create_evidence_required')
    return True


def verify_export(root, manifest, required_ids):
    root = c.owned_directory(Path(root))
    c.need(manifest.get('schema') == 1 and manifest.get('quiescent') is True, 'quiescent_export_required')
    c.need(set(required_ids) <= set(manifest.get('resource_ids', [])), 'export_resource_coverage')
    rows = manifest.get('files')
    c.need(isinstance(rows, list) and rows, 'export_files_required')
    seen = set()
    for row in rows:
        rel = Path(row.get('path', ''))
        c.need(str(rel) not in ('', '.') and not rel.is_absolute() and '..' not in rel.parts, 'invalid_export_path')
        c.need(str(rel) not in seen, 'duplicate_export_path');seen.add(str(rel))
        path = root / rel
        c.need(path.resolve() == path and root in path.parents, 'export_symlink_refused')
        c.need(path.is_file(), 'export_file_missing')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            c.need(before.st_uid == os.getuid() and before.st_mode & 0o077 == 0, 'private_export_required')
            sha = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024*1024), b''): sha.update(chunk)
            after = os.fstat(stream.fileno())
        c.need((before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino), 'export_changed_during_read')
        c.need(sha.hexdigest() == row.get('sha256') and before.st_size == row.get('size'), 'export_digest_mismatch')
    return c.digest(manifest)


def verify_absence(observations, required_ids, minimum_separation=2):
    c.need(len(observations) >= 2, 'repeated_absence_required')
    first, last = observations[-2:]
    c.need(last['observed_at'] - first['observed_at'] >= minimum_separation, 'absence_observations_too_close')
    for sample in (first, last):
        for rid in required_ids:
            row = sample.get('resources', {}).get(rid)
            c.need(row and row.get('query_succeeded') is True and row.get('absent') is True,
                   'resource_absence_unverified')
    return True


def validate_action(action):
    pair = (action.get('service'), action.get('operation'))
    c.need(pair in WRITE_ACTIONS, 'unsupported_write_operation')
    c.need(bool(re.fullmatch(r'[A-Za-z0-9_-]{1,80}', action.get('name', ''))), 'action_name_required')
    c.need(isinstance(action.get('request'), dict), 'structured_request_required')
    c.need(isinstance(action.get('region'), str), 'region_required')
    return pair


def resolve(value, journal):
    """Resolve only prior observed outputs; definitions themselves stay frozen."""
    if isinstance(value, list): return [resolve(x, journal) for x in value]
    if not isinstance(value, dict): return value
    if set(value) == {'$ref'}:
        parts = value['$ref'].split('.')
        row = journal.get(parts[0], {})
        c.need(row.get('state') == 'observed', 'dependency_not_observed')
        output = row['response']
        c.need(c.digest(output) == row['response_sha256'], 'dependency_digest_mismatch')
        for part in parts[1:]:
            output = output[int(part)] if isinstance(output, list) else output[part]
        c.need(isinstance(output, (str, int, bool)), 'scalar_reference_required')
        return output
    if set(value) == {'$json'}: return json.dumps(resolve(value['$json'], journal), sort_keys=True, separators=(',', ':'))
    if set(value) == {'$join'}:
        pieces = resolve(value['$join'], journal)
        c.need(isinstance(pieces, list) and all(isinstance(x, str) for x in pieces), 'string_join_required')
        return ''.join(pieces)
    c.need(not any(key.startswith('$') for key in value), 'unknown_reference_operator')
    return {key: resolve(item, journal) for key,item in value.items()}


def begin_action(state, packet, action, now):
    pair = validate_action(action)
    c.validate_packet(state, packet, now)
    reservation = state['reservations'].get(packet['attempt_id'])
    c.need(reservation and reservation['packet_sha256'] == c.digest(packet), 'reservation_mismatch')
    c.need(reservation['state'] in ('reserved', 'sent'), 'reservation_not_active')
    packet_region(packet,action['region'])
    expected = packet.get('actions', {})
    if action['name'] not in expected and reservation.get('mesh_binding'):
        import mesh
        expected={**expected,**{k:c.digest(v) for k,v in mesh.authorized(reservation,packet).items() if 'service' in v}}
    c.need(expected.get(action['name']) == c.digest(action), 'action_not_frozen')
    journal = reservation.setdefault('actions', {})
    c.need(action['name'] not in journal, 'action_already_consumed_reconcile_only')
    if pair in DESTRUCTIVE:
        c.need(action.get('export_sha256') and action.get('owned_ids'), 'cleanup_custody_required')
    request = resolve(action['request'], journal)
    journal[action['name']] = {'state': 'sent', 'request_sha256': c.digest(action), 'sent_at': now,
                               'resolved_request_sha256': c.digest(request), 'request': request,
                               'service':action['service'],'operation':action['operation'],'region':action['region']}
    reservation['state'] = 'sent'
    state['revision'] += 1
    return request


def finish_action(state, packet, action, response=None, error=None):
    journal = state['reservations'][packet['attempt_id']]['actions'][action['name']]
    c.need(journal['state'] == 'sent' and journal['request_sha256'] == c.digest(action), 'action_journal_mismatch')
    if error is not None:
        journal.update(state='unknown', error_class=error)
        state['reservations'][packet['attempt_id']]['state'] = 'unknown'
    else:
        journal.update(state='observed', response_sha256=c.digest(response), response=response)
    state['revision'] += 1


def execute_once(root, packet, action, profile, actual_account, invoke=None):
    c.need(packet['account'] == actual_account, 'live_account_mismatch')
    pair = validate_action(action)
    # Generic destruction is intentionally not exposed: a specialized cleanup
    # operation must verify fresh ownership, export bytes and dependency order.
    c.need(pair not in DESTRUCTIVE, 'use_verified_cleanup_path')
    now = datetime.now(timezone.utc).timestamp()
    request = c.transaction(root, lambda state: begin_action(state, packet, action, now))
    request_path = Path(root) / ('request-' + packet['attempt_id'] + '-' + action['name'] + '.json')
    try:
        from preflight import save
        save(request_path, request)
        command = ['aws', *pair, '--cli-input-json', 'file://' + str(request_path),
                   '--profile', profile, '--region', action['region'], '--output', 'json',
                   '--no-cli-pager', '--cli-connect-timeout', '8', '--cli-read-timeout', '30']
        invoke = invoke or subprocess.run
        result = invoke(command, capture_output=True, text=True, timeout=60, check=False,
                        env=dict(os.environ, AWS_PAGER='', AWS_MAX_ATTEMPTS='1'))
        save(request_path.with_name(request_path.stem+'-result.json'),
             {'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
        if result.returncode:
            raise RuntimeError('aws_request_failed_reconcile_required')
        response = json.loads(result.stdout or '{}')
    except Exception as exc:
        c.transaction(root, lambda state: finish_action(state, packet, action, error=type(exc).__name__))
        raise
    c.transaction(root, lambda state: finish_action(state, packet, action, response=response))
    return response


def reconcile_created(state, packet, action, observed_response, observed_at, now):
    """Adopt only a positive, exact read of a possibly completed EC2 create.

    Absence never authorizes another create. Original tokens and placement remain
    consumed. Other create kinds remain unknown until a kind-specific verifier exists.
    """
    entry=state['reservations'][packet['attempt_id']]
    c.need(entry['packet_sha256']==c.digest(packet),'reservation_mismatch')
    row=entry['actions'][action['name']]
    c.need(row['state'] in ('sent','unknown') and row['request_sha256']==c.digest(action),'unknown_original_action_required')
    request=row['request'];c.need(c.digest(request)==row['resolved_request_sha256'],'original_request_changed')
    c.need(0 <= now-observed_at <= 30,'fresh_reconciliation_required')
    pair=validate_action(action)
    c.need(pair==('ec2','run-instances'),'kind_specific_reconciliation_required')
    instances=observed_response.get('Instances',[])
    c.need(len(instances)==1,'exact_single_creation_required')
    instance=instances[0]
    c.need(instance.get('ClientToken')==request['ClientToken'],'original_client_token_required')
    c.need(instance.get('ImageId')==request['ImageId'] and instance.get('InstanceType')==request['InstanceType'],'instance_request_mismatch')
    c.need(instance.get('SubnetId')==request['NetworkInterfaces'][0]['SubnetId'] and
           instance.get('Placement',{}).get('AvailabilityZone')==request['Placement']['AvailabilityZone'],'original_placement_required')
    expected=next(x['Tags'] for x in request['TagSpecifications'] if x['ResourceType']=='instance')
    tags={t['Key']:t['Value'] for t in instance.get('Tags',[])}
    c.need(all(tags.get(t['Key'])==t['Value'] for t in expected),'creation_tags_mismatch')
    c.need(instance.get('MetadataOptions',{}).get('HttpTokens')=='required' and
           instance.get('KeyName')==request['KeyName'],'instance_security_mismatch')
    c.need({g['GroupId'] for g in instance.get('SecurityGroups',[])}==set(request['NetworkInterfaces'][0]['Groups']),
           'instance_group_mismatch')
    row.update(state='observed',response=observed_response,response_sha256=c.digest(observed_response),
               reconciliation_sha256=c.digest({'observed_at':observed_at,'response':observed_response}))
    if all(x['state']=='observed' for x in entry['actions'].values()):entry['state']='sent'
    state['revision']+=1


def reconcile_free_plan_rejection(state, packet, action, returned, observations):
    """Narrow definite rejection; timeouts and ambiguous failures stay unknown."""
    entry=state['reservations'][packet['attempt_id']]
    c.need(entry['packet_sha256']==c.digest(packet),'reservation_mismatch')
    row=entry['actions'][action['name']]
    c.need(row['state']=='unknown' and row['request_sha256']==c.digest(action),'unknown_original_action_required')
    c.need(validate_action(action)==('ec2','run-instances'),'run_instances_only')
    c.need(returned.get('returncode')==254 and not returned.get('stdout'),'definite_error_response_required')
    text=returned.get('stderr','')
    c.need('An error occurred (InvalidParameterCombination) when calling the RunInstances operation' in text and
           'The specified instance type is not eligible for Free Tier.' in text,'specific_free_plan_rejection_required')
    c.need(len(observations)>=2 and observations[-1]['observed_at']-observations[0]['observed_at']>=2,'separated_rejection_observations_required')
    for observation in observations:
        c.need(observation['observed_at']>=row['sent_at'] and observation.get('query_succeeded') is True and
               observation.get('client_token')==row['request']['ClientToken'] and observation.get('instances')==[],
               'original_token_absence_required')
    row.update(state='rejected',rejection_sha256=c.digest(returned),absence_sha256=c.digest(observations))
    if all(r['state'] in ('observed','rejected') for r in entry['actions'].values()):entry['state']='sent'
    state['revision']+=1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('verb', choices=['verify-export', 'verify-absence'])
    parser.add_argument('--root')
    parser.add_argument('--input', required=True)
    parser.add_argument('--resource-id', action='append', required=True)
    args = parser.parse_args()
    data = c.read_private(args.input)
    result = verify_export(args.root, data, args.resource_id) if args.verb == 'verify-export' else verify_absence(data, args.resource_id)
    print(json.dumps({'verified': bool(result), 'manifest_sha256': result if isinstance(result,str) else None}))


if __name__ == '__main__': main()
