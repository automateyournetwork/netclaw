#!/usr/bin/env python3
"""One-shot coordinator phases for an actual, owned fenced-restore FIXTURE.

Import and prepare start no process or container. Actual phases are explicit;
unknown phases retain their claims and cannot be replayed. No model/MCP work.
"""
import argparse
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
if __name__ == '__main__':
    sys.path[:0] = [str(ROOT), str(ROOT/'mcp-servers/protocol-mcp'), str(ROOT/'scripts/lib')]

from labs.ha.etcd_lab import EtcdLab, IMAGE, command
from labs.ha.process_fixture import ProcessFixture, decode, digest, encode, need, owned_directory, private, read_private, source_identity

PHASES = ('start-old', 'exercise-isolate', 'start-new', 'restore')


def failure_code(exc):
    code = getattr(exc,'code',None)
    if code is None and isinstance(exc,ValueError) and re.fullmatch('[a-z0-9_]{1,80}',str(exc)):
        code = str(exc)
    return code


def closure():
    value = source_identity()
    for name in ('scripts/lib/ha_cluster.py', 'labs/ha/dependencies.json'):
        value['files'][name] = hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    value['sha256'] = digest(value['files'])
    return value


def load_manifest(lab):
    from bgp.federation import protected_contract as c
    from bgp.federation.ha.config import verify_manifest
    anchor = read_private(lab.root/'cluster-identity/root.crt').decode()
    return verify_manifest(read_private(lab.root/'cluster-identity/manifest.json'), anchor, expected_key_id=c.key_id(anchor))


def replacement_identity(lab, old):
    """Fresh nodes, same explicitly selected offline enrollment anchor."""
    from bgp.federation import protected_contract as c
    from bgp.federation.certs import create_self_signed
    from bgp.federation.ha.config import sign_manifest, verify_manifest
    from bgp.federation.ha.recovery import _new_generation
    identity = lab.root/'cluster-identity'; identity.mkdir(mode=0o700)
    original = load_manifest(old)
    anchor = read_private(old.root/'cluster-identity/root.crt')
    anchor_key = read_private(old.root/'cluster-identity/root.key').decode()
    private(identity/'root.crt', anchor)  # The replacement gets no enrollment private key.
    value = copy.deepcopy(original.value)
    value.update(generation=lab.document['generation'], revision=original.revision+1)
    held, used = [], set(old.document['ports'] + lab.document['ports'])
    for node in original.nodes:
        used.update(node['endpoints'][key]['port'] for key in ('cluster', 'in2n'))
        from urllib.parse import urlsplit
        used.add(urlsplit(node['endpoints']['https']).port)
    def port():
        for _ in range(32):
            listener = socket.socket(); listener.bind(('127.0.0.1', 0))
            result = listener.getsockname()[1]
            if result not in used:
                held.append(listener); used.add(result); return result
            listener.close()
        raise ValueError('fresh_endpoint_capacity')
    try:
        for index, node in enumerate(value['nodes']):
            certificate, key = create_self_signed(node['identity'], days=3)
            private(identity/f'node{index}.crt', certificate.encode())
            private(identity/f'node{index}.key', key.encode())
            node.update(node_id=str(uuid.uuid4()), installation_id=str(uuid.uuid4()),
                        key_id=c.key_id(certificate), certificate=certificate)
            for kind in ('cluster', 'in2n'): node['endpoints'][kind]['port'] = port()
            https_port = port(); host = node['endpoints']['cluster']['server_name']
            node['endpoints'].update(https=f'https://{host}:{https_port}', wss=f'wss://{host}:{https_port}/mobile/ws')
        signed = sign_manifest(value, anchor_key)
        new = verify_manifest(signed, anchor.decode(), expected_key_id=original.anchor_key_id,
                              minimum_revision=original.revision+1)
        _new_generation(original, new)
        private(identity/'manifest.json', signed)
        lab.prepare_cluster_transport()
        private(identity/'complete.json', {'schema_version':1, **new.audience,
            'manifest_sha256':c.sha256(value), 'anchor_key_id':new.anchor_key_id,
            'fresh_node_ids':[node['node_id'] for node in new.nodes], 'offline_anchor_private_key_copied':False})
    finally:
        for listener in held: listener.close()


def prepare(packet):
    """Offline only: two direct voter sets, only one may run at a time."""
    from bgp.federation.certs import create_self_signed
    packet = Path(packet)
    need(packet.is_absolute() and packet.resolve() == packet, 'absolute_packet_required')
    packet.mkdir(mode=0o700, exist_ok=False); owned_directory(packet)
    old = EtcdLab(packet/'old-voters').prepare()
    old.prepare_cluster_identity(organization='r08-fenced-restore-fixture')
    new = EtcdLab(packet/'new-voters').prepare(cluster_id=old.document['cluster_id'])
    replacement_identity(new, old)
    host_dir = packet/'host'; host_dir.mkdir(mode=0o700)
    certificate, key = create_self_signed('r08/owned-host-isolation', days=3)
    private(host_dir/'host.crt', certificate.encode()); private(host_dir/'host.key', key.encode())
    (packet/'isolation').mkdir(mode=0o700)
    pins = {str(path.relative_to(packet)): hashlib.sha256(read_private(path)).hexdigest()
            for path in sorted(packet.rglob('*')) if path.is_file()}
    source = closure(); private(packet/'source.json', source)
    plan = {'schema_version':1, 'class':'PLAN_ONLY', 'packet_id':str(uuid.uuid4()), 'packet':str(packet),
        'source_sha256':source['sha256'], 'pins':pins, 'requires_serial_coordinator':True,
        'old':old.document, 'new':new.document,
        'limits':{'maximum_running_voters':3, 'maximum_workers':4, 'maximum_controlled_callbacks':3,
                  'model_calls':0, 'native_tool_calls':0, 'receipt_max_age_seconds':300},
        'phases':list(PHASES), 'source_launch':{'python':str(Path(sys.executable).resolve()),
                  'python_sha256':hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
                  'worker':str(ROOT/'labs/ha/process_fixture.py'), 'command':['-I','-B','worker','--config','<exact-owned-config>']},
        'sequence':['start fresh old direct voters only', 'start three Border processes and one member process',
            'capture actual seven live owned subjects', 'complete controlled A and export stale snapshot',
            'dispatch B, consume one controlled admission, mark unknown, retain later evidence',
            'verify exact owned processes, SIGTERM, require exit 0 and close sockets',
            'stop and disconnect exact old voters with restart disabled',
            'start fresh new direct voters only; prove namespace empty',
            'issue fresh actual host receipt; install inactive; test fence; activate; test global fence'],
        'retention':'preserve both voter data sets, old journal and immutable evidence; no automatic deletion',
        'native_profile_qualified':False}
    private(packet/'plan.json', plan)
    return {'class':'PLAN_ONLY', 'packet':str(packet), 'plan_sha256':digest(plan),
            'phases':list(PHASES), 'running_resources_created':0}


def packet_state(packet, expected):
    packet = owned_directory(Path(packet))
    plan = decode(read_private(packet/'plan.json'))
    need(digest(plan) == expected and plan['packet'] == str(packet), 'reviewed_plan_changed')
    need(closure()['sha256'] == plan['source_sha256'], 'reviewed_source_changed')
    need(str(Path(sys.executable).resolve()) == plan['source_launch']['python']
         and hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest() == plan['source_launch']['python_sha256'],
         'reviewed_python_changed')
    for name, pinned in plan['pins'].items():
        path = packet/name
        need(path.is_relative_to(packet) and hashlib.sha256(read_private(path)).hexdigest() == pinned, 'prepared_input_changed')
    old, new = EtcdLab(packet/'old-voters').load(), EtcdLab(packet/'new-voters').load()
    need(old.document == plan['old'] and new.document == plan['new'], 'owned_plan_changed')
    return packet, plan, old, new


def docker_read(args):
    result = subprocess.run(['docker', *args], capture_output=True, timeout=20)
    need(result.returncode == 0 and len(result.stdout) <= 4*1024*1024, 'owned_inventory_unavailable')
    return result.stdout


def running_voters(expected):
    """Global R08 cap. Unknown running spec179 roles fail closed as well."""
    ids = docker_read(['ps','--filter','label=netclaw.spec=179','--format','{{.ID}}']).decode().splitlines()
    rows = decode(docker_read(['inspect',*ids])) if ids else []
    voters = []
    for row in rows:
        need(row['Config']['Labels'].get('netclaw.spec') == '179', 'voter_inventory_changed')
        # Existing reviewed peer proxies are not voters/key holders. Everything
        # else must have the exact immutable etcd image and executable contract.
        cmd = row['Config'].get('Cmd') or []
        if row['Config']['Image'] == IMAGE and '/usr/local/bin/etcd' in cmd:
            voters.append(row['Id'])
        else:
            need(row['Config']['Labels'].get('netclaw.role') == 'peer-proxy', 'unreviewed_running_r08_resource')
    need(len(voters) <= 3 and set(voters) == set(expected), 'global_voter_bound_or_identity_changed')
    return rows


def live_voters(lab):
    rows = lab.inspect_owned()
    for row in rows:
        state = row['State']
        need(state['Running'] and not state['Paused'] and not state['Restarting'] and state['Pid'] > 0
             and row['HostConfig']['RestartPolicy']['Name'] in ('','no')
             and set(row['NetworkSettings']['Networks']) == {lab.document['name']}, 'owned_voters_not_live_direct')
    running_voters([row['Id'] for row in rows])
    return rows


def isolation_host(packet):
    from ha_cluster import HostIsolation
    return HostIsolation(packet/'isolation', packet/'host/host.crt', packet/'host/host.key')


def assert_isolated(packet):
    host = isolation_host(packet)
    inventory = decode(read_private(packet/'isolation/owned-inventory.json'))
    return host._observe(inventory, isolated=True)


def isolate_voters(lab, evidence):
    rows = live_voters(lab)
    private(evidence/'voter-isolation-baseline.json', rows)
    for index, row in enumerate(rows):
        # Every call is one-shot and its exact ID is already recorded by start.
        current = lab.inspect_owned()[index]
        need(current['Id'] == row['Id'] and current['State']['Running']
             and current['HostConfig']['RestartPolicy']['Name'] in ('','no'), 'owned_voter_state_changed')
        command(evidence, f'old-voter{index}-stop', ['docker','stop','--time','10',row['Id']], timeout=25)
        current = lab.inspect_owned()[index]
        need(not current['State']['Running'] and current['State']['Pid'] == 0
             and set(current['NetworkSettings']['Networks']) == {lab.document['name']}, 'owned_voter_stop_unproved')
        command(evidence, f'old-voter{index}-disconnect', ['docker','network','disconnect',lab.document['name'],row['Id']])
    rows = lab.inspect_owned()
    for row in rows:
        need(not row['State']['Running'] and not row['State']['Paused'] and not row['State']['Restarting']
             and row['State']['Pid'] == 0 and row['NetworkSettings']['Networks'] == {}
             and row['HostConfig']['RestartPolicy']['Name'] in ('','no'), 'owned_voter_isolation_unproved')
    running_voters([])
    private(evidence/'voter-isolation-verified.json', rows)


def signed_fixture_result(row, key):
    from bgp.federation import protected_contract as c
    review = row['review']; now = int(time.time()*1000)
    output = {'class':'FIXTURE', 'controlled_process_result':row['operation_id']}
    payload = {'receipt_id':str(uuid.uuid4()), 'operation_id':row['operation_id'], 'approval_id':row['approval_id'],
        'approval_sha256':row['approval_digest'], 'attempt_id':row['attempt_id'],
        **{name:review[name] for name in ('principal','border','member','model_profile','cluster')},
        'tool_call_sha256':c.sha256(review['tool_call']), 'started_at_ms':now, 'finished_at_ms':now,
        'outcome':'succeeded', 'effect_status':'finished', 'output':output, 'output_sha256':c.sha256(output),
        'tool_evidence_sha256':'f'*64, 'usage':{'available':False},
        'audit_refs':{'result':'controlled-process-fixture-audit'}, 'error_code':None}
    return c.sign(c.HA_RESULT, payload, key)


def stale_gap(stale, later, first_id, unknown_id):
    from bgp.federation.ha.operations import reservation_keys
    before, after = stale['records'], later['records']
    first, second = 'operations/'+first_id, 'operations/'+unknown_id
    need(first_id != unknown_id and before[first]['value']['state'] == 'completed'
         and second not in before and after[second]['value']['state'] == 'outcome_unknown'
         and later['revision'] > stale['revision'], 'genuine_stale_operation_gap_required')
    missing = [key for key, row in after.items() if key.startswith('claims/')
               and row['value'].get('request', {}).get('operation_id') == unknown_id and key not in before]
    need(len(missing) == 1, 'genuine_stale_claim_gap_required')
    claim = after[missing[0]]['value']; request = claim['request']
    need(claim.get('state') == 'committed' and request.get('attempt_id') == after[second]['value']['attempt_id']
         and request.get('approval_digest') == after[second]['value']['approval_digest']
         and request.get('kind') == 'model' and request.get('ordinal') == 1, 'genuine_stale_claim_gap_required')
    resources = reservation_keys(after[second]['value']['review'])
    for key in resources:
        need(before[key]['value']['state'] == 'released' and before[key]['value']['operation_id'] == first_id
             and after[key]['value']['state'] == 'reserved' and after[key]['value']['operation_id'] == unknown_id,
             'genuine_stale_reservation_gap_required')
    return {'first_operation_id':first_id, 'later_unknown_operation_id':unknown_id,
        'missing_operation_key':second, 'missing_claim_keys':missing, 'changed_resource_keys':resources,
        'stale_revision':stale['revision'], 'later_revision':later['revision'],
        'missing_evidence_recovered':False, 'required_protection':'global-generation-capacity-fence'}


async def exercise(packet, old):
    from bgp.federation.ha.authority import Authority
    from ha_cluster import process_observation
    live_voters(old)
    fixture = ProcessFixture(old, packet/'processes')
    evidence = packet/'exercise'; evidence.mkdir(mode=0o700)
    close_attempted = False
    try:
        store = old.store(0)
        try:
            need(store.read('control')[0] is None, 'dedicated_old_namespace_required')
            Authority(store,fixture.manifest,fixture.manifest.nodes[0]['node_id']).bootstrap(create=True)
        finally: store.close()
        for name in ('border0','border1','border2'): await fixture.start(name)
        await fixture.mesh(3)
        leader, _ = await fixture.leader(); await fixture.call(leader,'enroll')
        await fixture.start('member'); await fixture.attached(3)
        subjects = [{'kind':'container','role':'voter','node_id':None,'id':row['Id']} for row in live_voters(old)]
        for name, record in fixture.records.items():
            observed = process_observation(record['pid'])
            need(observed['present'] and observed['uid'] == os.getuid(), 'owned_process_baseline_missing')
            subjects.append({'kind':'process','role':'executor' if name == 'member' else 'border',
                'node_id':record.get('node_id'), 'pid':record['pid'], 'start_id':observed['start_id'],
                'command_sha256':observed['command_sha256']})
        private(evidence/'subjects.json', subjects)
        isolation_host(packet).capture(fixture.manifest,old.document['name'],subjects)
        first = await fixture.call(leader,'prepare',{'client_nonce':'restore-A-'+str(uuid.uuid4())})
        first = await fixture.call(leader,'dispatch',{'operation_id':first['operation_id']})
        context = {key:first[key] for key in ('operation_id','attempt_id','approval_digest')}
        for kind in ('model','tool'):
            result = await fixture.admit(context,kind,1,'complete')
            need(result['forwarded_over_cluster'], 'actual_follower_ingress_required')
            private(evidence/('first-'+kind+'.json'),result)
        envelope = signed_fixture_result(first,read_private(fixture.configs['member']['member_key_file']).decode())
        private(evidence/'first-result.json',envelope)
        leader, _ = await fixture.leader()
        first = await fixture.call(leader,'accept-fixture-result',{'operation_id':first['operation_id'],'envelope':envelope})
        private(evidence/'first-completed.json',first)
        stale = await fixture.call(leader,'snapshot'); private(evidence/'stale-snapshot.json',stale)
        second = await fixture.call(leader,'prepare',{'client_nonce':'restore-B-'+str(uuid.uuid4())})
        second = await fixture.call(leader,'dispatch',{'operation_id':second['operation_id']})
        context = {key:second[key] for key in ('operation_id','attempt_id','approval_digest')}
        private(evidence/'later-dispatched.json',second)
        private(evidence/'later-consumed.json',await fixture.admit(context,'model',1,'hold'))
        leader, _ = await fixture.leader()
        second = await fixture.call(leader,'unknown',{'operation_id':second['operation_id']})
        private(evidence/'later-unknown.json',second)
        later = await fixture.call(leader,'snapshot'); private(evidence/'later-snapshot.json',later)
        gap = stale_gap(stale,later,first['operation_id'],second['operation_id'])
        private(evidence/'stale-gap.json',gap)
        status = await fixture.call('member','status')
        need(len(status['effects']) == 3, 'fixture_effect_count')
        private(evidence/'member-before-stop.json',status)
        # Revalidate PID start identity immediately before the bounded graceful
        # close. Host receipt later rejects even a reused PID, without guessing.
        for subject in subjects:
            if subject['kind'] != 'process': continue
            actual = process_observation(subject['pid'])
            need(actual['present'] and actual['uid'] == os.getuid()
                 and all(actual[k] == subject[k] for k in ('start_id','command_sha256')), 'owned_process_identity_changed')
        private(evidence/'graceful-stop.claim.json',{'signal':'SIGTERM','subjects':subjects[3:]})
        close_attempted = True
        await fixture.close()
        for subject in subjects:
            if subject['kind'] == 'process': need(process_observation(subject['pid'])['present'] is False, 'owned_process_not_stopped')
        need(not fixture.control_root.exists(), 'owned_control_sockets_not_closed')
        # Closed SQLite is copied through sqlite's backup API; WAL state is never
        # dropped by an unsafe raw live-db copy. The original remains retained.
        journal_files = list((Path(fixture.configs['member']['home'])/'journal').glob('*.sqlite3'))
        need(len(journal_files) == 1, 'member_journal_identity_required'); journal = journal_files[0]
        read_private(journal,64*1024*1024)
        destination = evidence/'member-journal.sqlite3'
        fd = os.open(destination,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600); os.close(fd)
        from urllib.parse import quote
        source = sqlite3.connect('file:'+quote(str(journal),safe='/')+'?mode=ro',uri=True)
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
            rows = target.execute('SELECT operation_id,kind,ordinal,state FROM ha_admission ORDER BY operation_id,kind,ordinal').fetchall()
        finally:
            source.close(); target.close()
        unknown = [row for row in rows if row[0] == second['operation_id']]
        need(len(unknown) == 1 and unknown[0][3] == 'unknown', 'later_claim_fence_not_retained')
        private(evidence/'member-after-stop.json',{'rows':rows,'controlled_callbacks':3,'model_calls':0,'native_tool_calls':0})
        isolate_voters(old,evidence)
        private(evidence/'actual-isolation.json',assert_isolated(packet))
        paths = list(evidence.iterdir()) + [fixture.path/'owned-process-cleanup.json',fixture.path/'source.json',
            fixture.path/'member.json',fixture.path/'manifest.json',packet/'plan.json',packet/'source.json',
            packet/'isolation/owned-baseline.json',packet/'isolation/owned-inventory.json']
        for pattern in ('*/owned-*.json','*/spawn-*.json','*/launch-*.json','*/effects/*.json'):
            paths.extend(fixture.path.glob(pattern))
        paths = sorted(set(paths)); need(len(paths) <= 256,'export_artifact_capacity')
        private(packet/'exports.json',{'schema_version':1,'artifacts':[{'path':str(path),
            'sha256':hashlib.sha256(read_private(path,64*1024*1024)).hexdigest()} for path in paths if path.is_file()]})
        return {'class':'FIXTURE','actual_os_processes':4,'actual_old_voters':3,'graceful_cleanup_passed':True,
                'controlled_callbacks':3,'model_calls':0,'native_tool_calls':0,'gap':gap,'native_profile_qualified':False}
    finally:
        if not close_attempted: await fixture.close()


def restore(packet, new):
    from bgp.federation import protected_contract as c
    from bgp.federation.ha.recovery import verify_isolation, install_restored, activate_restored, _require_empty_namespace
    from labs.ha.restore_verify import verify_restore
    old = EtcdLab(packet/'old-voters').load(); old_manifest, new_manifest = load_manifest(old), load_manifest(new)
    live_voters(new); assert_isolated(packet)
    store = new.store(0)
    try:
        _require_empty_namespace(store)
        snapshot_file = packet/'exercise/stale-snapshot.json'; snapshot = decode(read_private(snapshot_file))
        gap = decode(read_private(packet/'exercise/stale-gap.json'))
        host = isolation_host(packet)
        # Receipt issued only after new voters are ready, never while spending
        # its five-minute lifetime provisioning or waiting for human input.
        proof = host.issue(old_manifest,new_manifest,snapshot_file,packet/'exports.json')
        receipt = verify_isolation(proof,host.certificate,expected_key_id=c.key_id(host.certificate),
                                   old_manifest=old_manifest,new_manifest=new_manifest,snapshot=snapshot)
        installed = install_restored(store,snapshot,old_manifest,new_manifest,receipt)
        private(packet/'restore-installed.json',installed)
        inactive = verify_restore(store,snapshot,old_manifest,new_manifest,new_manifest.nodes[0]['node_id'])
        private(packet/'restore-inactive-gates.json',inactive)
        assert_isolated(packet); live_voters(new)
        active = activate_restored(store,snapshot,old_manifest,new_manifest,receipt)
        private(packet/'restore-activated.json',active)
        verified = verify_restore(store,snapshot,old_manifest,new_manifest,new_manifest.nodes[0]['node_id'])
        private(packet/'restore-active-gates.json',verified)
        missing = store.read_many([gap['missing_operation_key'],*gap['missing_claim_keys']])
        need(all(value[0] is None for value in missing.values()), 'stale_gap_was_silently_recreated')
        need(verified['capacity_frozen'] is True, 'stale_restore_unfenced')
        assert_isolated(packet)
        return {'class':'FIXTURE','passed':True,'actual_host_isolation_receipt':True,
            'receipt_id':proof['payload']['receipt_id'],'inactive':inactive,'activated':active,'active':verified,
            'gap':gap,'missing_later_evidence_preserved_in_exports':True,'missing_evidence_recovered':False,
            'controlled_callbacks':3,'model_calls':0,'native_tool_calls':0,'native_profile_qualified':False,
            'new_voters_retained_running':3,'old_voters_retained_isolated':3,'cleanup_of_new_voters_pending':True}
    finally: store.close()


async def phase(packet, expected, name):
    need(name in PHASES, 'unknown_restore_phase')
    packet, plan, old, new = packet_state(packet,expected)
    index = PHASES.index(name)
    if index: read_private(packet/(PHASES[index-1]+'.complete.json'))
    private(packet/(name+'.claim.json'),{'schema_version':1,'phase':name,'plan_sha256':expected,
        'source_sha256':plan['source_sha256'],'state':'sent_or_unknown','claimed_at_ms':int(time.time()*1000)})
    try:
        if name == 'start-old':
            running_voters([]); old.start(); rows = live_voters(old)
            result = {'class':'FIXTURE','running_old_voters':[row['Id'] for row in rows]}
        elif name == 'exercise-isolate': result = await asyncio.wait_for(exercise(packet,old),240)
        elif name == 'start-new':
            assert_isolated(packet); running_voters([]); new.start(); rows = live_voters(new)
            from bgp.federation.ha.recovery import _require_empty_namespace
            store = new.store(0)
            try: _require_empty_namespace(store)
            finally: store.close()
            result = {'class':'FIXTURE','running_new_voters':[row['Id'] for row in rows], 'unused_namespace_verified':True}
        else: result = restore(packet,new)
        private(packet/(name+'.complete.json'),result); return result
    except BaseException as exc:
        private(packet/(name+'.failed.json'),{'class':'FIXTURE','phase':name,'type':type(exc).__name__,
            'code':failure_code(exc),'automatic_retry':False,'claim_retained':True})
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare',*PHASES)); parser.add_argument('--packet',required=True)
    parser.add_argument('--plan-sha256'); args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        if args.command == 'prepare': result = prepare(args.packet)
        else:
            need(args.plan_sha256 is not None,'reviewed_plan_hash_required')
            result = asyncio.run(phase(args.packet,args.plan_sha256,args.command))
        print(json.dumps(result,sort_keys=True)); return 0
    except BaseException as exc:
        print(json.dumps({'class':'FIXTURE','failed':True,'type':type(exc).__name__,'code':failure_code(exc)}),file=sys.stderr)
        return 1


if __name__ == '__main__': raise SystemExit(main())
