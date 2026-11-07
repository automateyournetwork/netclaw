"""Source/protocol checks only; never launch workers, voters, model or Docker."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest

SOURCE=Path(__file__).resolve().parents[2]/'labs/ha/process_fixture.py'
spec=importlib.util.spec_from_file_location('ha_process_fixture_under_test',SOURCE)
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


def setup(tmp_path,role='member'):
    home=tmp_path.resolve();home.chmod(0o700);(home/'commands').mkdir(mode=0o700)
    config={'schema_version':1,'role':role,'run_id':str(uuid.uuid4()),'control_token':'a'*64,'home':str(home)}
    context={'operation_id':str(uuid.uuid4()),'attempt_id':str(uuid.uuid4()),'approval_digest':'b'*64}
    request={'schema_version':1,'run_id':config['run_id'],'token':config['control_token'],'request_id':str(uuid.uuid4()),
        'method':'admit','params':{'context':context,'kind':'tool','ordinal':1,'mode':'hold','via_node_id':str(uuid.uuid4())}}
    return config,request


def test_import_does_not_execute_any_worker_or_mutate_runtime(monkeypatch):
    def refused(*args,**kwargs):raise AssertionError('import must start nothing')
    monkeypatch.setattr(asyncio,'create_subprocess_exec',refused)
    monkeypatch.setattr(os,'kill',refused)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert callable(module.run) and callable(module.worker_main)


@pytest.mark.parametrize('change',[
    {'method':'exec','params':{'command':'anything'}}, {'method':'snapshot','params':{}},
    {'method':'admit','params':{'shell':'anything'}}, {'token':'incorrect'}, {'run_id':str(uuid.uuid4())},
    {'request_id':'not-a-uuid'}, {'extra':True}, {'params':{'context':{},'kind':'tool','ordinal':2,'mode':'hold'}}])
def test_private_member_control_refuses_unrelated_role_arbitrary_exec_or_bad_binding(tmp_path,change):
    config,request=setup(tmp_path);request.update(change)
    with pytest.raises((ValueError,TypeError)):fixture.validate_request(fixture.encode(request),config)


def test_control_frames_are_exact_bounded_and_duplicate_safe(tmp_path):
    config,request=setup(tmp_path)
    assert fixture.validate_request(fixture.encode(request),config)==request
    with pytest.raises(ValueError,match='duplicate_control_key'):fixture.decode(b'{"a":1,"a":2}')
    with pytest.raises(ValueError,match='nonfinite_control_value'):fixture.decode(b'{"a":NaN}')
    with pytest.raises(ValueError,match='control_frame_bound'):fixture.decode(b' '*65537)
    request['method']='prepare';request['params']={'client_nonce':'fixed'}
    config['role']='border';assert fixture.validate_request(fixture.encode(request),config)==request
    request['method']='admit';request['params']={'context':{},'kind':'tool','ordinal':1,'mode':'hold'}
    with pytest.raises(ValueError,match='control_method_refused'):fixture.validate_request(fixture.encode(request),config)


def test_mutation_claim_is_durable_single_use_and_contains_no_control_token(tmp_path):
    config,request=setup(tmp_path)
    fixture.claim_command(config['home'],request)
    raw=fixture.read_private(tmp_path.resolve()/'commands'/(request['request_id']+'.json'))
    value=fixture.decode(raw)
    assert value['state']=='sent_or_unknown' and value['params_sha256']==fixture.digest(request['params'])
    assert request['token'].encode() not in raw and (tmp_path/'commands'/(request['request_id']+'.json')).stat().st_mode&0o777==0o600
    with pytest.raises(FileExistsError):fixture.claim_command(config['home'],request)


def test_private_paths_refuse_symlink_or_shared_permissions(tmp_path):
    home=tmp_path.resolve();home.chmod(0o700);file=home/'private.json'
    fixture.private(file,{'private':True})
    link=home/'link';link.symlink_to(file)
    with pytest.raises(ValueError,match='unsafe_control_file'):fixture.read_private(link)
    file.chmod(0o644)
    with pytest.raises(ValueError,match='unsafe_control_file'):fixture.read_private(file)


class Reader:
    def __init__(self,raw):self.raw=raw
    async def readline(self):return self.raw


class Writer:
    def __init__(self):self.raw=b'';self.closed=False
    def write(self,raw):self.raw+=raw
    async def drain(self):pass
    def close(self):self.closed=True
    async def wait_closed(self):pass


@pytest.mark.asyncio
async def test_control_lost_mutation_cannot_be_replayed_with_original_request(tmp_path):
    config,request=setup(tmp_path);worker=fixture.Worker.__new__(fixture.Worker)
    worker.config,worker.home,worker.boot=config,tmp_path.resolve(),str(uuid.uuid4());worker.control_tasks=set()
    calls=[]
    async def command(method,params):calls.append((method,params));raise RuntimeError('controlled unknown result')
    worker.command=command
    first=Writer();await worker.serve(Reader(fixture.encode(request)+b'\n'),first)
    second=Writer();await worker.serve(Reader(fixture.encode(request)+b'\n'),second)
    assert len(calls)==1 and first.closed and second.closed
    assert fixture.decode(first.raw)['error']=='RuntimeError'
    assert fixture.decode(second.raw)['error']=='FileExistsError'
    assert request['token'].encode() not in first.raw+second.raw


@pytest.mark.asyncio
async def test_unknown_control_authorization_never_reaches_command(tmp_path):
    config,request=setup(tmp_path);worker=fixture.Worker.__new__(fixture.Worker)
    worker.config,worker.home,worker.boot=config,tmp_path.resolve(),str(uuid.uuid4());worker.control_tasks=set()
    async def command(*args):raise AssertionError('unauthorized command reached handler')
    worker.command=command;request['token']='wrong'
    writer=Writer();await worker.serve(Reader(fixture.encode(request)+b'\n'),writer)
    assert fixture.decode(writer.raw)['ok'] is False and list((tmp_path/'commands').iterdir())==[]


def test_source_identity_includes_production_admission_and_actual_driver():
    identity=fixture.source_identity()
    assert len(identity['sha256'])==64
    assert 'labs/ha/process_fixture.py' in identity['files']
    assert 'mcp-servers/protocol-mcp/bgp/federation/ha/admission.py' in identity['files']
    assert 'mcp-servers/protocol-mcp/bgp/federation/ha/internal.py' in identity['files']


@pytest.mark.asyncio
async def test_worker_closes_active_member_channels_before_waiting_for_listener():
    order=[];worker=fixture.Worker.__new__(fixture.Worker)
    class Listener:
        def close(self):order.append('listener-close')
        async def wait_closed(self):
            assert 'channel-close' in order;order.append('listener-closed')
    class Channel:
        async def close(self):order.append('channel-close')
    worker.listener=Listener();worker.channels={'controlled':Channel()}
    worker.control_tasks=set();worker.tasks=set();worker.attachments=worker.node=worker.store=None
    await asyncio.wait_for(worker.close(),.2)
    assert order==['listener-close','channel-close','listener-closed']


@pytest.mark.asyncio
async def test_unexpected_worker_exit_is_a_cleanup_failure_not_complete(tmp_path):
    harness=fixture.ProcessFixture.__new__(fixture.ProcessFixture)
    harness.path=tmp_path.resolve();harness.path.chmod(0o700)
    harness.control_root=harness.path/'sockets';harness.control_root.mkdir(mode=0o700)
    harness.children={'border0':SimpleNamespace(pid=12345,returncode=1)}
    harness.configs={'border0':{'control_socket':str(harness.control_root/'border0.sock')}}
    harness.records={};harness.intentional_kills=set()
    with pytest.raises(ValueError,match='owned_process_cleanup_failed'):await harness.close()
    result=fixture.decode(fixture.read_private(harness.path/'owned-process-cleanup.json'))
    assert result['passed'] is False and result['processes'][0]['expected_returncode']==0
    assert not (harness.path/'complete.json').exists()


def test_controlled_result_is_border_only_and_requires_explicit_fixture_output(tmp_path):
    config,request=setup(tmp_path,'border')
    op=str(uuid.uuid4());request.update(method='accept-fixture-result',params={'operation_id':op,
        'envelope':{'payload':{'output':{'class':'FIXTURE','controlled_process_result':op}}}})
    assert fixture.validate_request(fixture.encode(request),config)==request
    config['role']='member'
    with pytest.raises(ValueError,match='control_method_refused'):fixture.validate_request(fixture.encode(request),config)
    config['role']='border';request['params']['envelope']['payload']['output']['class']='REAL'
    with pytest.raises(ValueError,match='controlled_result_required'):fixture.validate_request(fixture.encode(request),config)
