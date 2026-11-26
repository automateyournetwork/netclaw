#!/usr/bin/env python3
"""Private Spec199 cumulative reservations and monotone stage admission."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid
from preflight import fresh_private_dir, save

CAPS = {'aws': Decimal('100'), 'external': Decimal('10')}
FLOORS = {'aws': Decimal('5'), 'external': Decimal('1')}
PAUSE = Decimal('80')
MAX_SECONDS = {1: 21600, 2: 21600, 3: 3600, 4: 21600, 5: 7200}


def need(condition, code):
    if not condition: raise ValueError(code)


def money(value):
    need(isinstance(value, (str, int)) and not isinstance(value, bool), 'money_string_or_integer_required')
    try: amount = Decimal(value)
    except InvalidOperation: raise ValueError('invalid_money') from None
    need(amount.is_finite() and amount >= 0, 'invalid_money')
    return amount


def stamp(value):
    try: dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (AttributeError, ValueError): raise ValueError('invalid_timestamp') from None
    need(dt.tzinfo is not None, 'timezone_required')
    return dt.timestamp()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def new_campaign(account, campaign_id=None):
    need(bool(re.fullmatch(r'\d{12}', account)), 'invalid_account')
    return {'schema': 1, 'campaign_id': campaign_id or str(uuid.uuid4()), 'account': account,
            'accepted_stage': 0, 'revision': 0, 'spent': {'aws': '0', 'external': '0'},
            'reservations': {}, 'receipts': {}}


def check_state(state):
    need(state.get('schema') == 1, 'schema_required')
    uuid.UUID(state['campaign_id'])
    need(bool(re.fullmatch(r'\d{12}', state['account'])), 'invalid_account')
    need(type(state['accepted_stage']) is int and 0 <= state['accepted_stage'] <= 5, 'invalid_stage')
    for domain in CAPS: money(state['spent'][domain])
    need(isinstance(state['reservations'], dict) and isinstance(state['receipts'], dict), 'invalid_ledger')


def totals(state):
    check_state(state)
    result = {}
    for domain in CAPS:
        held = sum((money(row['amounts'][domain]) for row in state['reservations'].values()
                    if row['state'] != 'settled'), Decimal('0'))
        result[domain] = {'spent': money(state['spent'][domain]), 'held': held,
                          'protected_total': money(state['spent'][domain]) + held + FLOORS[domain]}
    return result


def validate_packet(state, packet, now):
    check_state(state)
    need(packet.get('schema') == 1 and packet.get('campaign_id') == state['campaign_id'], 'campaign_mismatch')
    need(packet.get('account') == state['account'], 'account_mismatch')
    stage = packet.get('stage')
    need(type(stage) is int and stage == state['accepted_stage'] + 1 and stage in MAX_SECONDS, 'stage_order')
    need(bool(re.fullmatch(r'[0-9a-f]{40}', packet.get('source_sha', ''))), 'source_sha_required')
    need(bool(re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d', packet.get('region', ''))), 'region_required')
    if stage in (4,5):
        regions=packet.get('regions')
        scope=packet.get('qualification_scope','three-region')
        need(scope in ('three-region','ohio-three-az'),'unknown_qualification_scope')
        if scope=='ohio-three-az':
            zones=packet.get('zones',{})
            need(regions==['us-east-2'] and packet['region']=='us-east-2','ohio_only_scope')
            need(isinstance(zones,dict) and len(zones)==len(set(zones.values()))==3
                 and all(re.fullmatch(r'us-east-2[a-z]',k) and isinstance(v,str) and
                         re.fullmatch(r'use2-az[1-9][0-9]*',v) for k,v in zones.items()),'three_frozen_ohio_azs_required')
            need(bool(re.fullmatch(r'[a-f0-9]{64}',packet.get('scope_amendment_sha256',''))),'scope_amendment_required')
        else:need(isinstance(regions,list) and len(regions)==len(set(regions))==3
             and packet['region'] in regions
             and all(isinstance(r,str) and re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d',r) for r in regions),
             'three_frozen_regions_required')
    uuid.UUID(packet['attempt_id'])
    token = packet.get('client_token', '')
    need(isinstance(token, str) and bool(re.fullmatch(r'[A-Za-z0-9_-]{16,64}', token)), 'client_token_required')
    created, deadline = stamp(packet.get('created_at')), stamp(packet.get('deadline'))
    need(created <= now < deadline and deadline - created <= MAX_SECONDS[stage], 'lease_invalid_or_expired')
    need(isinstance(packet.get('resources'), list) and bool(packet['resources']), 'exact_resources_required')
    for row in packet['resources']:
        need(isinstance(row, dict) and bool(row.get('kind')) and bool(row.get('name')), 'invalid_resource')
    costs = packet.get('costs', {})
    need(set(costs) == set(CAPS), 'both_cost_domains_required')
    need(any(money(costs[d]) > 0 for d in CAPS), 'positive_reservation_required')
    if stage > 1:
        receipt = state['receipts'].get(str(stage - 1))
        need(receipt and packet.get('predecessor_sha256') == receipt['sha256'], 'predecessor_mismatch')
    return stage


def reserve(state, packet, now):
    stage = validate_packet(state, packet, now)
    attempt = packet['attempt_id']
    need(attempt not in state['reservations'], 'attempt_already_consumed')
    need(all(row['client_token'] != packet['client_token'] for row in state['reservations'].values()), 'client_token_consumed')
    balance = totals(state)
    need(balance['aws']['protected_total'] < PAUSE, 'aws_pause_reached')
    for domain in CAPS:
        bound = balance[domain]['protected_total'] + money(packet['costs'][domain])
        need(bound <= CAPS[domain], domain + '_ceiling_exceeded')
        if domain == 'aws': need(bound <= PAUSE, 'aws_pause_would_be_crossed')
    state['reservations'][attempt] = {'stage': stage, 'packet_sha256': digest(packet),
        'client_token': packet['client_token'], 'region': packet['region'],
        'deadline': packet['deadline'], 'amounts': {d: str(money(packet['costs'][d])) for d in CAPS},
        'state': 'reserved'}
    state['revision'] += 1
    return digest(packet)


def mark_sent(state, packet, now):
    validate_packet(state, packet, now)
    entry = state['reservations'].get(packet['attempt_id'])
    need(entry and entry['packet_sha256'] == digest(packet), 'reservation_mismatch')
    need(entry['state'] == 'reserved', 'already_sent_or_uncertain')
    entry['state'] = 'sent'
    state['revision'] += 1


def mark_unknown(state, attempt):
    entry = state['reservations'][attempt]
    need(entry['state'] == 'sent', 'unknown_requires_sent')
    entry['state'] = 'unknown'
    state['revision'] += 1


def settle(state, attempt, actual, disposition):
    entry = state['reservations'][attempt]
    need(entry['state'] != 'settled', 'already_settled')
    need(entry['state'] != 'unknown', 'unknown_reservation_retained')
    need(bool(re.fullmatch(r'[0-9a-f]{64}', disposition.get('evidence_sha256', ''))), 'disposition_evidence_required')
    need(disposition.get('no_open_resources') is True and disposition.get('no_uncertain_work') is True, 'obligations_remain')
    need(all(row.get('disposition') == 'absent' for row in entry.get('custody', {}).values()), 'owned_resources_remain')
    need(all(row.get('state') in ('observed','rejected') for row in entry.get('actions', {}).values()), 'unresolved_cloud_actions_remain')
    need(all(row.get('state') in ('observed','rejected') for row in entry.get('external_actions', {}).values()), 'unresolved_external_actions_remain')
    need(all(row.get('disposition')=='absent' for row in entry.get('external_custody', {}).values()), 'external_resources_remain')
    for domain in CAPS:
        amount = money(actual[domain])
        need(amount <= money(entry['amounts'][domain]), 'reservation_overrun_requires_reconciliation')
    for domain in CAPS: state['spent'][domain] = str(money(state['spent'][domain]) + money(actual[domain]))
    entry.update(state='settled', actual={d: str(money(actual[d])) for d in CAPS}, disposition=disposition)
    state['revision'] += 1


def accept(state, stage, receipt):
    need(stage == state['accepted_stage'] + 1 and stage in MAX_SECONDS, 'stage_order')
    need(receipt.get('stage') == stage and receipt.get('accepted') is True, 'acceptance_evidence_required')
    need(bool(re.fullmatch(r'[0-9a-f]{64}', receipt.get('sha256', ''))), 'receipt_digest_required')
    rows = [row for row in state['reservations'].values() if row['stage'] == stage]
    need(rows and all(row['state'] == 'settled' for row in rows), 'stage_obligations_remain')
    # This conservative implementation retires every stage's resources before advancement.
    # Retention across stage boundaries requires a separately implemented transfer contract.
    state['receipts'][str(stage)] = receipt
    state['accepted_stage'] = stage
    state['revision'] += 1


def owned_directory(root):
    root = Path(root)
    need(root.is_absolute() and not root.is_symlink(), 'private_root_required')
    info = root.stat()
    need(info.st_uid == os.getuid() and info.st_mode & 0o077 == 0, 'private_owned_root_required')
    need(root.resolve() == root, 'symlink_ancestor_refused')
    return root


@contextmanager
def locked(root):
    root = owned_directory(root)
    fd = os.open(root / 'campaign.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        need(os.fstat(fd).st_uid == os.getuid() and os.fstat(fd).st_mode & 0o077 == 0, 'private_lock_required')
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield root
    finally:
        os.close(fd)


def read_private(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        need(info.st_uid == os.getuid() and info.st_mode & 0o077 == 0, 'private_file_required')
        raw = stream.read(2 * 1024 * 1024 + 1)
        need(len(raw) <= 2 * 1024 * 1024, 'ledger_too_large')
        return json.loads(raw)


def transaction(root, action):
    with locked(root) as root:
        state = read_private(root / 'campaign.json')
        check_state(state)
        result = action(state)
        check_state(state)
        fd, temp = tempfile.mkstemp(prefix='.campaign-', dir=root)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(state, stream, sort_keys=True, indent=2, allow_nan=False)
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temp, root / 'campaign.json')
            dfd = os.open(root, os.O_RDONLY)
            try: os.fsync(dfd)
            finally: os.close(dfd)
        finally:
            if os.path.exists(temp): os.unlink(temp)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('verb', choices=['init', 'validate', 'reserve', 'status'])
    parser.add_argument('--root', required=True)
    parser.add_argument('--account')
    parser.add_argument('--packet')
    args = parser.parse_args()
    if args.verb == 'init':
        need(args.account is not None, 'account_required')
        state = new_campaign(args.account)
        root = fresh_private_dir(args.root); save(root / 'campaign.json', state)
        print(json.dumps({'campaign_id': state['campaign_id'], 'accepted_stage': 0}))
        return
    now = datetime.now(timezone.utc).timestamp()
    packet = read_private(args.packet) if args.packet else None
    if args.verb == 'reserve': result = transaction(args.root, lambda state: reserve(state, packet, now))
    elif args.verb == 'validate':
        with locked(args.root) as root: result = validate_packet(read_private(root / 'campaign.json'), packet, now)
    else:
        with locked(args.root) as root:
            state = read_private(root / 'campaign.json')
            result = {'accepted_stage': state['accepted_stage'], 'revision': state['revision'], 'totals': totals(state)}
    print(json.dumps(result, default=str, indent=2))


if __name__ == '__main__': main()
