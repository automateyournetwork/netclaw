"""Controlled source checks only. Never launch Docker, workers or host receipts."""
import asyncio
import copy
import importlib.util
from pathlib import Path
import secrets
from types import SimpleNamespace
import uuid

import pytest

SOURCE = Path(__file__).resolve().parents[2]/'labs/ha/fenced_restore_fixture.py'
spec = importlib.util.spec_from_file_location('fenced_restore_fixture_under_test',SOURCE)
fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)


@pytest.fixture
def packet(tmp_path,monkeypatch):
    from labs.ha import etcd_lab
    # In the coordinator integration tree this is the same repository. A lane
    # may load the coordinator's current production dependencies read-only.
    monkeypatch.setattr(fixture,'ROOT',etcd_lab.REPO)
    def refused(*args,**kwargs): raise AssertionError('offline preparation launched a process')
    monkeypatch.setattr(fixture.subprocess,'run',refused)
    monkeypatch.setattr(asyncio,'create_subprocess_exec',refused)
    path = tmp_path.resolve()/'packet'
    result = fixture.prepare(path)
    return path,result


def test_preparation_is_offline_fresh_generation_same_anchor_and_only_three_voters_at_once(packet):
    path,result = packet
    plan = fixture.decode(fixture.read_private(path/'plan.json'))
    old = fixture.EtcdLab(path/'old-voters').load(); new = fixture.EtcdLab(path/'new-voters').load()
    old_manifest,new_manifest = fixture.load_manifest(old),fixture.load_manifest(new)
    assert result['class'] == 'PLAN_ONLY' and result['running_resources_created'] == 0
    assert plan['limits']['maximum_running_voters'] == 3 and plan['limits']['maximum_workers'] == 4
    assert old_manifest.cluster_id == new_manifest.cluster_id and old_manifest.generation != new_manifest.generation
    assert old_manifest.anchor_key_id == new_manifest.anchor_key_id
    assert not (path/'new-voters/cluster-identity/root.key').exists()
    for key in ('node_id','installation_id','key_id'):
        assert not {node[key] for node in old_manifest.nodes} & {node[key] for node in new_manifest.nodes}
    assert old.document['prefix'] != new.document['prefix']
    assert fixture.packet_state(path,result['plan_sha256'])[1] == plan
    with pytest.raises(FileExistsError): fixture.prepare(path)


@pytest.mark.parametrize('fault',['plan','source','key','python'])
def test_every_phase_refuses_changed_reviewed_inputs(packet,monkeypatch,fault):
    path,result = packet
    if fault == 'source': monkeypatch.setattr(fixture,'closure',lambda:{'sha256':'f'*64})
    elif fault == 'key': (path/'new-voters/cluster-identity/node0.key').write_bytes(b'changed')
    elif fault == 'python': monkeypatch.setattr(fixture.sys,'executable','/unreviewed/python')
    else: result['plan_sha256'] = 'f'*64
    with pytest.raises((ValueError,FileNotFoundError)):
        fixture.packet_state(path,result['plan_sha256'])


@pytest.mark.asyncio
async def test_failed_phase_keeps_one_shot_claim_and_does_not_retry(packet,monkeypatch):
    path,result = packet; calls=[]
    def no_voters(expected): calls.append(expected); raise RuntimeError('controlled inventory unavailable')
    monkeypatch.setattr(fixture,'running_voters',no_voters)
    with pytest.raises(RuntimeError): await fixture.phase(path,result['plan_sha256'],'start-old')
    assert (path/'start-old.claim.json').exists() and (path/'start-old.failed.json').exists()
    assert not (path/'start-old.complete.json').exists()
    with pytest.raises(FileExistsError): await fixture.phase(path,result['plan_sha256'],'start-old')
    assert calls == [[]]


@pytest.mark.asyncio
async def test_new_voters_cannot_start_before_old_isolation_phase_completed(packet):
    path,result = packet
    with pytest.raises(FileNotFoundError): await fixture.phase(path,result['plan_sha256'],'start-new')
    assert not (path/'start-new.claim.json').exists()


def test_global_cap_counts_exact_etcd_voters_and_refuses_unknown_running_roles(monkeypatch):
    rows = [{'Id':str(i)*64,'Config':{'Image':fixture.IMAGE,'Cmd':['/usr/local/bin/etcd'],
             'Labels':{'netclaw.spec':'179'}}} for i in range(1,4)]
    def read(args): return b'one\ntwo\nthree\n' if args[0] == 'ps' else fixture.encode(rows)
    monkeypatch.setattr(fixture,'docker_read',read)
    assert fixture.running_voters([row['Id'] for row in rows]) == rows
    with pytest.raises(ValueError,match='global_voter_bound'): fixture.running_voters([])
    rows.append(copy.deepcopy(rows[0])); rows[-1]['Id']='4'*64
    with pytest.raises(ValueError,match='global_voter_bound'): fixture.running_voters([row['Id'] for row in rows])
    rows.pop();rows[0]['Config']['Image']='unreviewed-image'
    with pytest.raises(ValueError,match='unreviewed_running'): fixture.running_voters([row['Id'] for row in rows])


def controlled_gap(packet):
    from bgp.federation import protected_contract as c
    from bgp.federation.certs import create_self_signed
    from bgp.federation.ha.authority import Authority
    from bgp.federation.ha.operations import OperationLedger
    from bgp.federation.ha.recovery import snapshot_document
    from labs.ha.process_fixture import fixture_review
    from test_ha_authority_179 import MemoryStore
    path,_ = packet
    lab = fixture.EtcdLab(path/'old-voters').load(); manifest = fixture.load_manifest(lab)
    store = MemoryStore(); authority = Authority(store,manifest,manifest.nodes[0]['node_id'])
    authority.bootstrap(create=True); assert authority.campaign()
    node_key = fixture.read_private(lab.root/'cluster-identity/node0.key').decode()
    cert,key = create_self_signed('r08/controlled-member')
    member = {'installation_id':str(uuid.uuid4()),'member_id':'r08/controlled-member',
              'key_id':c.key_id(cert),'enrollment_generation':str(uuid.uuid4())}
    ledger = OperationLedger(authority); ledger.enroll_member(member,cert)
    review = fixture_review(manifest,SimpleNamespace(node_id=authority.node_id,authority=authority),member)
    def dispatch():
        row = ledger.prepare(str(uuid.uuid4()),'d'*64,review)
        approval = dict(review,approval_id=str(uuid.uuid4()),operation_id=row['operation_id'],nonce=secrets.token_urlsafe(32),
                        issued_at_ms=ledger.now(),review_sha256=row['review_digest'])
        ledger.approve(row['operation_id'],c.sign(c.HA_APPROVAL,approval,node_key),revision=row['revision'],review_digest=row['review_digest'])
        return ledger.dispatch(row['operation_id'])
    incarnation = str(uuid.uuid4())
    def admit(row,kind):
        request = {**manifest.audience, **{k:row[k] for k in ('operation_id','attempt_id','approval_digest')},
                   'kind':kind,'ordinal':1,'request_digest':'a'*64,'member_incarnation':incarnation,'nonce':secrets.token_hex(32)}
        return ledger.admit(request,member)
    first = dispatch(); admit(first,'model'); admit(first,'tool')
    envelope = fixture.signed_fixture_result(first,key)
    first = ledger.accept_result(first['operation_id'],envelope,private_key=node_key,audit_ref='controlled-fixture-ack')
    assert first['state'] == 'completed' and first['ack'] is not None
    stale = snapshot_document(manifest,store.rows,store.revision)
    second = dispatch(); admit(second,'model'); second = ledger.mark_unknown(second['operation_id'])
    later = snapshot_document(manifest,store.rows,store.revision)
    return stale,later,first,second


def test_stale_gap_uses_actual_production_records_and_keeps_missing_later_claim_explicit(packet):
    stale,later,first,second = controlled_gap(packet)
    gap = fixture.stale_gap(stale,later,first['operation_id'],second['operation_id'])
    assert len(gap['missing_claim_keys']) == 1 and len(gap['changed_resource_keys']) == 2
    assert gap['missing_evidence_recovered'] is False
    assert first['ack']['payload']['operation_id'] == first['operation_id']
    assert second['state'] == 'outcome_unknown'


@pytest.mark.parametrize('fault',['no_gap','no_claim','still_reserved','unknown_not_proved'])
def test_stale_gap_rejects_synthetic_or_incomplete_gap(packet,fault):
    stale,later,first,second = controlled_gap(packet)
    if fault == 'no_gap': stale=copy.deepcopy(later)
    elif fault == 'no_claim':
        later['records']={key:value for key,value in later['records'].items()
            if not key.startswith('claims/'+second['operation_id'])}
    elif fault == 'still_reserved':
        next(value for key,value in stale['records'].items() if key.startswith('resources/'))['value']['state']='reserved'
    else: later['records']['operations/'+second['operation_id']]['value']['state']='dispatch_claimed'
    with pytest.raises(ValueError): fixture.stale_gap(stale,later,first['operation_id'],second['operation_id'])
