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


def test_effect_evidence_on_a_long_running_host(tmp_path, monkeypatch):
    from bgp.federation import protected_contract as contract

    worker = object.__new__(fixture.Worker)
    worker.home = tmp_path
    (tmp_path / "effects").mkdir(mode=0o700)
    worker.journal = SimpleNamespace(incarnation="fixture")
    observed = 2**53 + 1
    monkeypatch.setattr(fixture, "time", SimpleNamespace(monotonic_ns=lambda: observed))

    evidence = worker.effect("operation", "tool", 1)
    assert contract.decode(contract.encode(evidence)) == evidence
    assert worker.effects() == [dict(evidence, observed_monotonic_ns=observed)]


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


@pytest.mark.asyncio
async def test_unavailable_cluster_listener_does_not_qualify_authentication(monkeypatch):
    from bgp.federation import exporter_tls
    async def refused(*args,**kwargs):raise ConnectionRefusedError('no listener')
    monkeypatch.setattr(exporter_tls,'open_connection',refused)
    with pytest.raises(ConnectionRefusedError):
        await fixture.rejected_cluster_tls({'host':'127.0.0.1','port':1,'server_name':'localhost'},'ca','cert','key')


def test_unavailable_etcd_listener_and_generic_http400_do_not_qualify_authentication(monkeypatch):
    import httpx
    context=SimpleNamespace(minimum_version=None,load_cert_chain=lambda *args:None)
    monkeypatch.setattr(fixture.ssl,'create_default_context',lambda **kwargs:context)
    class Client:
        answer=None
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,*args,**kwargs):
            if isinstance(self.answer,Exception):raise self.answer
            return self.answer
    monkeypatch.setattr(httpx,'Client',Client)
    Client.answer=httpx.ConnectError('connection refused')
    Client.answer.__cause__=ConnectionRefusedError('unavailable')
    with pytest.raises(ValueError,match='credential_refusal_not_observed'):
        fixture.etcd_denied('https://127.0.0.1:1','ca','cert','key')
    Client.answer=httpx.Response(400,json={'error':'invalid request','code':3})
    with pytest.raises(ValueError,match='credential_refusal_not_observed'):
        fixture.etcd_denied('https://127.0.0.1:1','ca','cert','key')
    Client.answer=httpx.Response(403,json={'error':'etcdserver: permission denied','code':7})
    assert fixture.etcd_denied('https://127.0.0.1:1','ca','cert','key')['reason']=='etcdserver: permission denied'


def test_only_nested_peer_authentication_tls_alert_qualifies():
    import ssl
    import httpx
    alert=ssl.SSLError('peer rejected client certificate');alert.reason='TLSV1_ALERT_UNKNOWN_CA'
    wrapped=httpx.ReadError('TLS read');wrapped.__cause__=alert
    assert fixture.peer_auth_alert(wrapped)=='TLSV1_ALERT_UNKNOWN_CA'
    for error in (ssl.SSLError('TLS stream truncated'),ConnectionResetError(),TimeoutError(),ConnectionRefusedError()):
        with pytest.raises(ValueError,match='credential_refusal_not_observed'):fixture.peer_auth_alert(error)


def test_tls_observer_preserves_decision_and_requires_fresh_exact_receiver_event(tmp_path):
    from bgp.federation.certs import create_self_signed
    from OpenSSL import crypto
    cert,_=create_self_signed('controlled-tls-observer')
    leaf=crypto.load_certificate(crypto.FILETYPE_PEM,cert)
    tmp_path.chmod(0o700);errors=[]
    class Context:
        callback=None
        def get_verify_mode(self):return 3
        def set_verify(self,mode,callback):assert mode==3;self.callback=callback
    ctx=Context();factory=fixture.audited_tls_context(lambda **kwargs:ctx,tmp_path,lambda:errors.append(True))
    assert factory(require_peer=True) is ctx
    assert ctx.callback(None,leaf,0,0,True) is True and not list(tmp_path.iterdir())
    assert ctx.callback(None,leaf,18,0,False) is False
    after=[fixture.decode(fixture.read_private(p)) for p in sorted(tmp_path.iterdir())]
    assert len(fixture.verify_receiver_rejection([],after,cert))==1 and errors==[]
    with pytest.raises(ValueError,match='receiver_certificate_rejection_not_observed'):
        fixture.verify_receiver_rejection(after,after,cert)
    other,_=create_self_signed('other-client')
    with pytest.raises(ValueError,match='receiver_certificate_rejection_not_observed'):
        fixture.verify_receiver_rejection([],after,other)


def test_tls_observer_storage_failure_is_latched_and_never_qualifies(tmp_path,monkeypatch):
    from bgp.federation.certs import create_self_signed
    from OpenSSL import crypto
    cert,_=create_self_signed('controlled-tls-observer')
    leaf=crypto.load_certificate(crypto.FILETYPE_PEM,cert);errors=[];tmp_path.chmod(0o700)
    class Context:
        def get_verify_mode(self):return 3
        def set_verify(self,mode,callback):self.callback=callback
    ctx=Context();fixture.audited_tls_context(lambda **kwargs:ctx,tmp_path,lambda:errors.append(True))(require_peer=True)
    def failed(*args):raise OSError('controlled disk failure')
    monkeypatch.setattr(fixture,'private',failed)
    with pytest.raises(OSError):ctx.callback(None,leaf,18,0,False)
    assert errors==[True] and not list(tmp_path.iterdir())


@pytest.mark.asyncio
@pytest.mark.parametrize('fault,code',[('not-enrolled','member_not_enrolled'),('wrong-role','attachment_proof_mismatch'),('replay','attachment_proof_mismatch')])
async def test_hello_observer_preserves_exact_production_refusal_and_proof(fault,code,tmp_path):
    from bgp.federation.ha.config import HAError
    tmp_path.chmod(0o700);errors=[];failure=HAError(code)
    async def hello(channel,params):raise failure
    def initialize(channel,*args,**options):channel.handlers=options['handlers']
    channel=SimpleNamespace(trusted=False,writer=SimpleNamespace(get_extra_info=lambda key:'in2n-tls-exporter-v1'))
    observed=fixture.audited_attachment_init(initialize,tmp_path,lambda:errors.append(True))
    observed(channel,is_border_side=True,handlers={'in2n/hello':hello})
    params={'proof':{'original':'proof'},'member':{'original':'binding'}}
    with pytest.raises(HAError) as raised:await channel.handlers['in2n/hello'](channel,params)
    assert raised.value is failure and errors==[]
    rows=[fixture.decode(fixture.read_private(path)) for path in sorted(tmp_path.iterdir())]
    attempt={'fault':fault,'params_sha256':fixture.digest(params),'proof_sha256':fixture.digest(params['proof'])}
    assert fixture.verify_hello_rejection([],rows,attempt)==rows
    with pytest.raises(ValueError,match='receiver_hello_rejection_not_observed'):
        fixture.verify_hello_rejection(rows,rows,attempt)
    with pytest.raises(ValueError,match='receiver_hello_rejection_not_observed'):
        fixture.verify_hello_rejection([],rows,dict(attempt,proof_sha256='f'*64))


@pytest.mark.asyncio
async def test_hello_unavailability_is_not_authentication_refusal(tmp_path):
    from bgp.federation.ha.config import HAError
    tmp_path.chmod(0o700)
    async def hello(channel,params):raise HAError('no_quorum')
    def initialize(channel,*args,**options):channel.handlers=options['handlers']
    channel=SimpleNamespace(trusted=False,writer=SimpleNamespace(get_extra_info=lambda key:'in2n-tls-exporter-v1'))
    fixture.audited_attachment_init(initialize,tmp_path,lambda:None)(channel,is_border_side=True,handlers={'in2n/hello':hello})
    params={'proof':{'one':'proof'}}
    with pytest.raises(HAError):await channel.handlers['in2n/hello'](channel,params)
    rows=[fixture.decode(fixture.read_private(path)) for path in sorted(tmp_path.iterdir())]
    with pytest.raises(ValueError,match='receiver_hello_rejection_not_observed'):
        fixture.verify_hello_rejection([],rows,{'fault':'not-enrolled','params_sha256':fixture.digest(params),
                                              'proof_sha256':fixture.digest(params['proof'])})


@pytest.mark.asyncio
async def test_successful_hello_and_non_border_constructor_are_unchanged(tmp_path):
    tmp_path.chmod(0o700);errors=[]
    async def hello(channel,params):return params
    def initialize(channel,*args,**options):channel.handlers=options['handlers']
    observed=fixture.audited_attachment_init(initialize,tmp_path,lambda:errors.append(True))
    border=SimpleNamespace();observed(border,is_border_side=True,handlers={'in2n/hello':hello})
    assert await border.handlers['in2n/hello'](border,{'accepted':True})=={'accepted':True}
    member=SimpleNamespace();observed(member,is_border_side=False,handlers={'in2n/hello':hello})
    assert member.handlers['in2n/hello'] is hello and errors==[] and not list(tmp_path.iterdir())


@pytest.mark.asyncio
async def test_hello_observer_storage_failure_latches_fixture_failure(tmp_path,monkeypatch):
    from bgp.federation.ha.config import HAError
    tmp_path.chmod(0o700);errors=[]
    async def hello(channel,params):raise HAError('member_not_enrolled')
    def initialize(channel,*args,**options):channel.handlers=options['handlers']
    channel=SimpleNamespace(trusted=False,writer=SimpleNamespace(get_extra_info=lambda key:'in2n-tls-exporter-v1'))
    fixture.audited_attachment_init(initialize,tmp_path,lambda:errors.append(True))(channel,is_border_side=True,handlers={'in2n/hello':hello})
    def failed(*args):raise OSError('controlled disk failure')
    monkeypatch.setattr(fixture,'private',failed)
    with pytest.raises(OSError):await channel.handlers['in2n/hello'](channel,{'proof':{}})
    assert errors==[True]
