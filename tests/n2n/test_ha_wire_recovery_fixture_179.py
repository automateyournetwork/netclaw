"""Source-only checks. Never launch workers, Docker, or a native executor."""
import asyncio
import copy
import importlib.util
from pathlib import Path
import secrets
from types import SimpleNamespace
import uuid

import pytest

SOURCE=Path(__file__).resolve().parents[2]/'labs/ha/wire_recovery_fixture.py'
spec=importlib.util.spec_from_file_location('wire_recovery_fixture_under_test',SOURCE)
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


def request(method,params,role='member'):
    config={'run_id':str(uuid.uuid4()),'control_token':secrets.token_hex(32),'role':role}
    value={'schema_version':1,'run_id':config['run_id'],'request_id':str(uuid.uuid4()),
           'method':method,'params':params,'token':config['control_token']}
    return config,value


@pytest.mark.parametrize('fault',['result-reply','ack-delivery'])
def test_loss_commands_are_exact_and_member_only(fault):
    config,value=request('arm-loss',{'operation_id':str(uuid.uuid4()),'fault':fault})
    assert fixture.validate_request(fixture.encode(value),config)==value
    for changed in [dict(value,params=dict(value['params'],retry=True)),dict(value,token='wrong'),
                    dict(value,params=dict(value['params'],fault='arbitrary-method'))]:
        with pytest.raises(ValueError):fixture.validate_request(fixture.encode(changed),config)
    with pytest.raises(ValueError):fixture.validate_request(fixture.encode(value),dict(config,role='border'))


def test_capture_validates_original_context_and_exact_ingress():
    params={'context':{'operation_id':str(uuid.uuid4()),'attempt_id':str(uuid.uuid4()),'approval_digest':'a'*64},
            'via_node_id':str(uuid.uuid4())}
    config,value=request('capture',params)
    assert fixture.validate_request(fixture.encode(value),config)==value
    for key in ('operation_id','attempt_id','approval_digest'):
        changed=copy.deepcopy(value);changed['params']['context'][key]='bad'
        with pytest.raises(ValueError):fixture.validate_request(fixture.encode(changed),config)


@pytest.mark.parametrize('method',['shell','execution/submit','n2n/cluster/edge'])
def test_topology_probe_cannot_become_generic_rpc_surface(method):
    config,value=request('wire-role',{'method':method,'via_node_id':str(uuid.uuid4())})
    with pytest.raises(ValueError):fixture.validate_request(fixture.encode(value),config)


def test_timing_records_three_separate_observations_and_refuses_reordering():
    value=fixture.timings(1_000_000,2_000_000,9_000_000,14_000_000)
    assert [value[k] for k in ('failure_to_detection_ms','failure_to_new_authority_ms','failure_to_service_recovery_ms')]==[1,8,13]
    with pytest.raises(ValueError):fixture.timings(1,3,2,4)


@pytest.mark.asyncio
async def test_stale_proofs_cannot_reach_effect_or_learn_replacement_epoch(tmp_path):
    from bgp.federation.ha.config import HAError
    worker=object.__new__(fixture.Worker);worker.held=[];worker.proof_observations=[{'epoch':4}]
    worker.home=tmp_path;tmp_path.chmod(0o700);(tmp_path/'effects').mkdir(mode=0o700)
    terminal=[]
    class Journal:
        def consume(self,*args):raise HAError('admission_expired')
        def _terminal(self,request,state):terminal.append((request['kind'],state))
    worker.journal=Journal()
    for kind in ('model','tool'):
        worker.held.append(({'kind':kind},{'payload':{'claim':{'epoch':4}}},(fixture.time.monotonic()-5,0)))
    result=await worker.command('consume-held',{})
    assert [x['code'] for x in result['refusals']]==['admission_expired']*2
    assert result['proof_observations']==[{'epoch':4}] and result['effects_before']==result['effects_after']==[]
    assert terminal==[('model','unknown'),('tool','unknown')]


@pytest.mark.asyncio
async def test_accepted_stale_proof_fails_fixture_instead_of_reporting_pass(tmp_path):
    worker=object.__new__(fixture.Worker);worker.home=tmp_path;tmp_path.chmod(0o700)
    (tmp_path/'effects').mkdir(mode=0o700);worker.proof_observations=[]
    worker.journal=SimpleNamespace(consume=lambda *args:None)
    worker.held=[({}, {}, (0,0))]*2
    with pytest.raises(AssertionError,match='paused_authority_proof_accepted'):await worker.command('consume-held',{})


@pytest.mark.asyncio
async def test_production_member_signs_controlled_result_and_hooks_drop_once_without_ack(tmp_path,monkeypatch):
    from bgp.federation import protected_contract as c
    from bgp.federation.ha.admission import MemberAdmission
    from bgp.federation.ha.internal import border_binding
    from bgp.federation.ha.operations import OperationLedger
    from bgp.federation.ha.signatures import sign
    from ha_support_179 import cluster_with_keys
    from test_ha_execution_contract_179 import ha_approval
    store,manifest,nodes,keys=cluster_with_keys()
    _,member,payload=ha_approval()
    binding=payload['member'];home=tmp_path/'member';home.mkdir(mode=0o700)
    for name in ('audit','effects','wire-loss'):(home/name).mkdir(mode=0o700)
    fixture.private(home/'member.key',member['key_pem'].encode())
    worker=object.__new__(fixture.Worker)
    worker.home=home;worker.config={'role':'member','member_key_file':str(home/'member.key')}
    worker.manifest=manifest;worker.member={'binding':binding,'certificate':member['cert_pem']}
    worker.journal=MemberAdmission(home/'journal',manifest,binding)
    worker.loss=None;worker.held=[];worker.proof_observations=[];worker.operations=None
    ledger=OperationLedger(nodes[0]);ledger.enroll_member(binding,member['cert_pem'])
    class Channel:
        strict=trusted=True;attestation='possession';_closed=False
        cluster_node_id=nodes[0].node_id;protected_peer_binding=border_binding(manifest,nodes[0].node_id)
        writer=SimpleNamespace(get_extra_info=lambda name:'in2n-tls-exporter-v1')
        async def close(self):self._closed=True
    channel=Channel()
    class Attachments:
        handlers={};channels={nodes[0].node_id:channel}
        async def send_admission(self,request):
            claim,revision=ledger.admit(request,binding)
            return sign('admission',{'claim':claim,'commit_revision':revision},keys[0])
    worker.attachments=Attachments()
    async def no_process(_):pass
    monkeypatch.setattr(fixture.base.Worker,'start',no_process)
    await worker.start()
    try:
        review=fixture.base.fixture_review(manifest,SimpleNamespace(node_id=nodes[0].node_id,authority=nodes[0]),binding)
        row=ledger.prepare('controlled-wire-test','e'*64,review)
        approved=dict(review,approval_id=str(uuid.uuid4()),operation_id=row['operation_id'],nonce=secrets.token_urlsafe(32),
            issued_at_ms=int(fixture.time.time()*1000),review_sha256=row['review_digest'])
        envelope=c.sign(c.HA_APPROVAL,approved,keys[0])
        ledger.approve(row['operation_id'],envelope,revision=1,review_digest=row['review_digest']);row=ledger.dispatch(row['operation_id'])
        dispatch=sign('dispatch',{**manifest.audience,'operation_id':row['operation_id'],'attempt_id':row['attempt_id'],
            'approval_digest':row['approval_digest'],'issuer_node_id':nodes[0].node_id,'authority_epoch':nodes[0].epoch},keys[0])
        await worker.attachments.handlers['execution/submit'](channel,{'approval':envelope,'dispatch':dispatch})
        await asyncio.gather(*worker.operations.workers)
        member_row=worker.operations.store.get('member',row['operation_id'])
        assert member_row['state']=='result_ready',member_row['error_code']
        assert c.verify(member_row['receipt'],member['cert_pem'],c.HA_RESULT)['outcome']=='succeeded'
        assert [(e['kind'],e['ordinal']) for e in worker.effects()]==[('model',1),('model',2),('tool',1)]
        assert len(worker.proof_observations)==3
        await worker.command('arm-loss',{'operation_id':row['operation_id'],'fault':'result-reply'})
        with pytest.raises(ConnectionError):await worker.attachments.handlers['execution/result'](channel,{'operation_id':row['operation_id']})
        assert channel._closed and worker.loss is None
        retained=worker.operations.store.get('member',row['operation_id'])
        assert retained['receipt']==member_row['receipt'] and retained['ack'] is None
        channel._closed=False
        assert await worker.attachments.handlers['execution/result'](channel,{'operation_id':row['operation_id']})==retained['receipt']
        accepted=ledger.accept_result(row['operation_id'],retained['receipt'],private_key=keys[0],audit_ref='controlled-test')
        await worker.command('arm-loss',{'operation_id':row['operation_id'],'fault':'ack-delivery'})
        with pytest.raises(ConnectionError):await worker.attachments.handlers['execution/ack'](channel,{'ack':accepted['ack']})
        assert worker.operations.store.get('member',row['operation_id'])['ack'] is None
        channel._closed=False
        await worker.attachments.handlers['execution/ack'](channel,{'ack':accepted['ack']})
        assert worker.operations.store.get('member',row['operation_id'])['ack']==accepted['ack']
        assert len(worker.effects())==3
    finally:await worker.operations.close()


def test_no_import_or_parser_path_runs_a_process(monkeypatch):
    def refused(*args,**kwargs):raise AssertionError('source test tried a runtime action')
    monkeypatch.setattr(fixture.subprocess,'run',refused)
    monkeypatch.setattr(asyncio,'create_subprocess_exec',refused)
    with pytest.raises(ValueError):fixture.main(['run'])
