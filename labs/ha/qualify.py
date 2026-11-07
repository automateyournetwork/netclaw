"""Actual local etcd/NCFED fixture qualification; callbacks are explicitly synthetic.

This core phase does not qualify the iN2N member service, guarded provider, native
MCP or operating clients. Each invocation requires a fresh evidence directory.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import secrets
import time
import uuid

from bgp.federation import protected_contract as c
from bgp.federation.certs import create_self_signed
from bgp.federation.ha.admission import MemberAdmission
from bgp.federation.ha.authority import Authority
from bgp.federation.ha.config import verify_manifest, HAError
from bgp.federation.ha.node import ClusterNode
from .etcd_lab import EtcdLab, private


async def eventually(call, timeout=30):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            value = await call()
            if value:
                return value
        except Exception as exc:
            last = type(exc).__name__
        await asyncio.sleep(.2)
    raise RuntimeError('fixture_condition_timeout:' + str(last))


async def core(lab, evidence):
    evidence.mkdir(mode=0o700, exist_ok=False)
    identity = lab.root / 'cluster-identity'
    transport = lab.root / 'cluster-transport'
    root = (identity / 'root.crt').read_text()
    manifest = verify_manifest((identity / 'manifest.json').read_bytes(), root, expected_key_id=c.key_id(root))
    stores = [lab.store(i) for i in range(3)]
    nodes = [ClusterNode(Authority(stores[i], manifest, node['node_id']),
                private_key=(identity / f'node{i}.key').read_text(), ca_file=str(transport / 'transport-ca.crt'),
                cert_file=str(transport / f'node{i}.crt'), key_file=str(transport / f'node{i}.key'))
             for i, node in enumerate(manifest.nodes)]
    rows, effects, paused = [], [], set()
    private(evidence / 'scope.json', {'class': 'FIXTURE', 'actual_etcd': True, 'actual_ncfed_cluster': True,
        'actual_in2n_member': False, 'model_calls': 0, 'native_tool_calls': 0,
        'manifest_sha256': c.sha256(manifest.value), 'source': {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path('mcp-servers/protocol-mcp/bgp/federation/ha').glob('*.py')}})
    def record(case, **result):
        row = {'case': case, 'passed': True, **result}
        private(evidence / (f'{len(rows):02d}-' + case + '.json'), row)
        rows.append(row)
        print(json.dumps(row), flush=True)
    async def leader():
        value, _ = await asyncio.to_thread(nodes[1].authority.current)
        return next(n for n in nodes if n.node_id == value['node_id'] and not n.closing)
    async def mesh():
        return all(len(n.channels) == 2 for n in nodes)
    cert, _ = create_self_signed('controlled-r08-member')
    member = {'installation_id': str(uuid.uuid4()), 'member_id': 'r08/controlled-member',
              'key_id': c.key_id(cert), 'enrollment_generation': str(uuid.uuid4())}
    def review(node):
        binding = manifest.node(node.node_id)
        return {'principal': {'issuer': 'open-lab', 'subject': str(uuid.uuid5(uuid.UUID(manifest.cluster_id), 'netclaw.open-lab.operator')),
                              'display_name': 'Unauthenticated lab operator', 'roles': ['lab-operator']},
            'cluster': {**manifest.audience, 'manifest_revision': manifest.revision,
                        'issuer_node_id': node.node_id, 'authority_epoch': node.authority.epoch},
            'border': {'installation_id': binding['installation_id'], 'identity': binding['identity'],
                       'key_id': binding['key_id'], 'authority_generation': manifest.generation}, 'member': member,
            'model_profile': {'profile_id': 'controlled-fixture', 'profile_revision': '1', 'runtime_kind': 'controlled',
                              'runtime_version': 'fixture', 'provider': 'controlled', 'model': 'fixture', 'guard_policy_sha256': 'a'*64},
            'tool_call': {'tool': 'subnet_calculator', 'tool_schema_sha256': 'b'*64, 'arguments': {'cidr': '192.0.2.0/26'},
                          'arguments_sha256': c.sha256({'cidr': '192.0.2.0/26'}), 'device_ref': 'documentation-subnet',
                          'inventory_revision': 'fixture', 'endpoint_sha256': 'c'*64},
            'limits': {'expires_at_ms': int(time.time()*1000) + 180000, 'inference_timeout_ms': 60000,
                       'tool_timeout_ms': 60000, 'max_inference_calls': 2, 'max_tool_calls': 1, 'max_output_bytes': 65536},
            'change_request_ref': None}
    async def prepare(node, nonce):
        row = await asyncio.to_thread(node.ledger.prepare, nonce, 'd'*64, review(node))
        payload = dict(row['review'], approval_id=str(uuid.uuid4()), operation_id=row['operation_id'],
                       nonce=secrets.token_urlsafe(32), issued_at_ms=int(time.time()*1000), review_sha256=row['review_digest'])
        signed = c.sign(c.HA_APPROVAL, payload, node.private_key)
        return await asyncio.to_thread(node.ledger.approve, row['operation_id'], signed,
                                       revision=row['revision'], review_digest=row['review_digest'])
    try:
        await asyncio.gather(*(n.start() for n in nodes))
        await eventually(mesh)
        current = await eventually(leader)
        record('three-node-cluster', connections=[len(n.channels) for n in nodes], authority=current.node_id)
        await asyncio.to_thread(current.ledger.enroll_member, member, cert)
        row = await prepare(current, 'core-' + str(uuid.uuid4()))
        row = await asyncio.to_thread(current.ledger.dispatch, row['operation_id'])
        context = {k: row[k] for k in ('operation_id', 'attempt_id', 'approval_digest')}
        journal = MemberAdmission(evidence / 'member-journal', manifest, member)
        async def invoke():
            effects.append('controlled-callback'); return {'controlled': True}
        async def send_at(node, request):
            return await node.route('n2n/cluster/admission', {'request': request, 'member': member})
        follower = next(n for n in nodes if n is not current)
        await journal.run(context, 'model', 1, 'e'*64, lambda req: send_at(follower, req), invoke)
        record('follower-forwarded-admission', controlled_callbacks=len(effects), model_calls=0, native_tool_calls=0)
        started = time.monotonic()
        await current.close()
        successor = await eventually(leader, 40)
        assert successor.node_id != current.node_id
        record('leader-lease-expiry', old=current.node_id, new=successor.node_id,
               recovery_seconds=round(time.monotonic()-started, 3))
        try:
            await asyncio.to_thread(current.ledger.dispatch, row['operation_id'])
            raise AssertionError('stale leader dispatched')
        except HAError as exc:
            assert exc.code in ('stale_authority', 'not_leader')
            record('stale-authority-refused', code=exc.code)
        second = await prepare(successor, 'reserved-' + str(uuid.uuid4()))
        try:
            await asyncio.to_thread(successor.ledger.dispatch, second['operation_id'])
            raise AssertionError('unknown member reservation released')
        except HAError as exc:
            assert exc.code == 'resource_recovery_required'
            record('unknown-reservation-preserved', code=exc.code)
        await asyncio.to_thread(lab.fault, 0, 'pause', evidence); paused.add(0)
        async def surviving():
            value, _ = await asyncio.to_thread(successor.authority.current)
            return value['node_id'] == successor.node_id
        await eventually(surviving)
        await journal.run(context, 'tool', 1, 'f'*64, lambda req: send_at(successor, req), invoke)
        record('single-voter-loss', controlled_callbacks=len(effects))
        await asyncio.to_thread(lab.fault, 1, 'pause', evidence); paused.add(1)
        before = len(effects)
        try:
            await journal.run(context, 'model', 2, 'a'*64, lambda req: send_at(successor, req), invoke)
            raise AssertionError('no quorum admitted callback')
        except (HAError, ConnectionError) as exc:
            assert len(effects) == before
            record('quorum-loss-no-new-callback', code=getattr(exc, 'code', 'transport_unknown'), controlled_callbacks=len(effects))
        private(evidence / 'complete.json', {'passed': True, 'class': 'FIXTURE', 'rows': rows,
                 'controlled_callbacks': len(effects), 'model_calls': 0, 'native_tool_calls': 0})
    except BaseException as exc:
        private(evidence / 'failure.json', {'type': type(exc).__name__, 'code': getattr(exc, 'code', None),
                                           'completed_rows': len(rows), 'controlled_callbacks': len(effects)})
        raise
    finally:
        # Recover exactly observed owned paused voters, even if a fault command
        # completed but its response/verification was lost. No resource guessing.
        inventory = await asyncio.to_thread(lab.inspect_owned)
        for i, item in enumerate(inventory):
            if item['State']['Paused']:
                await asyncio.to_thread(lab.fault, i, 'unpause', evidence)
        await asyncio.gather(*(n.close() for n in nodes), return_exceptions=True)
        # A cancelled renewal's bounded worker may finish before closing clients.
        await asyncio.sleep(7)
        for store in stores: store.close()
        private(evidence / 'voters-restored.json', {'paused': [r['State']['Paused'] for r in lab.inspect_owned()]})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(core(EtcdLab(args.fixture).load(), args.evidence))
