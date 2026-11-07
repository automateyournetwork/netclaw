"""Controlled helper/pipe fixtures only; never Docker, model or DefenseClaw."""
import asyncio
import json
import os
import sys
import time
from types import SimpleNamespace

import pytest

from bgp.federation.ha.config import HAError
from bgp.federation.ha.effect import CURRENT, EffectScope
from bgp.federation.ha.model_transport import MODEL_HELPER, ha_model_forward
from bgp.federation.protected_runtime import RuntimeUnknown


def helper():
    namespace = {'__name__': 'controlled_fixture'}
    exec(MODEL_HELPER, namespace)
    return namespace


@pytest.mark.parametrize('fault', ['none', 'pause', 'wall_forward', 'wall_back', 'negative_elapsed'])
def test_helper_local_final_clock_gate(fault):
    h = helper(); clock = {'mono': 10., 'wall': 1000.}
    h['_mono'] = lambda: clock['mono']; h['_wall'] = lambda: clock['wall']
    start = (10., 1000.)
    if fault == 'pause': clock.update(mono=13., wall=1003.)
    if fault == 'wall_forward': clock['wall'] += 1
    if fault == 'wall_back': clock['wall'] -= 1
    if fault == 'negative_elapsed': clock['mono'] -= 1
    if fault == 'none': assert h['_fresh'](start, 2750) == 0
    else:
        with pytest.raises(ValueError): h['_fresh'](start, 2750)


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['none', 'expired_host', 'expired_helper', 'helper_clock', 'partial_http', 'closed_http', 'low_budget'])
async def test_controlled_model_helper_never_retries_or_sends_stale_http(tmp_path, monkeypatch, fault):
    from bgp.federation import protected_docker as docker
    captured = []
    async def controlled_guard(reader, writer):
        try:
            header = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 2)
            size = int(next(line.split(b':', 1)[1] for line in header.split(b'\r\n') if line.lower().startswith(b'content-length:')))
            body = await asyncio.wait_for(reader.readexactly(size), 2)
            captured.append((header, json.loads(body)))
            result = b'{"controlled":true}'
            writer.write(b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(result)).encode()+b'\r\nConnection: close\r\n\r\n'+result)
            await writer.drain()
        except (asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionResetError):
            pass
        finally:
            writer.close(); await writer.wait_closed()
    server = await asyncio.start_server(controlled_guard, '127.0.0.1', 0)
    port = server.sockets[0].getsockname()[1]
    launches = []
    original_create = asyncio.create_subprocess_exec
    async def create(*args, **kwargs):
        launches.append(args)
        assert args[-3:-1] == ('python3', '-c') and args[-1] == MODEL_HELPER
        prelude = 'import socket,time\noriginal=socket.create_connection\nsocket.create_connection=lambda address,timeout: original(("127.0.0.1",'+str(port)+'),timeout)\n'
        if fault in ('partial_http', 'closed_http'):
            prelude += '''class SocketProxy:
 def __init__(self,inner):self.inner=inner
 def __getattr__(self,name):return getattr(self.inner,name)
 def send(self,data):
'''
            prelude += "  raise BlockingIOError('controlled full socket')\n" if fault == 'closed_http' else "  return self.inner.send(data[:1])\n"
            prelude += 'connect=socket.create_connection\nsocket.create_connection=lambda address,timeout:SocketProxy(connect(address,timeout))\n'
        namespace = "ns={'__name__':'controlled_fixture'}\nexec("+repr(MODEL_HELPER)+",ns)\n"
        if fault == 'expired_helper': namespace += "original_read=ns['_read_input']\ndef delayed(start):\n value=original_read(start);time.sleep(.08);return value\nns['_read_input']=delayed\n"
        if fault == 'helper_clock': namespace += "original_read=ns['_read_input']\ndef delayed(start):\n value=original_read(start);ns['_wall']=lambda: start[1]+1;return value\nns['_read_input']=delayed\n"
        child = prelude + namespace + "try:ns['_run']()\nexcept BaseException:raise SystemExit(70)\n"
        return await original_create(sys.executable, '-I', '-c', child, **kwargs)
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', create)
    monkeypatch.setattr(docker, '_docker_host', lambda value: value)
    config = tmp_path/'docker'; config.mkdir(); (config/'config.json').write_bytes(b'{}')
    executor = SimpleNamespace(docker='/controlled-docker',docker_host='fixture',docker_config=config,
        config={'docker_host':'fixture'},ollama={'guard_uid':501,'model_container_id':'fixture'},guard_token='fake-capability')
    payload = {'limits':{'expires_at_ms':int(time.time()*1000)+5000,'inference_timeout_ms':3000}}
    checks = []
    def fresh():
        checks.append(True)
        if fault == 'expired_host' and launches: raise HAError('admission_expired',403)
        return 300 if fault == 'expired_helper' else 250 if fault == 'low_budget' else 3000
    admitted = EffectScope('model',fresh); token = CURRENT.set(admitted)
    try:
        if fault == 'none':
            assert json.loads(await ha_model_forward(executor,payload,{'fixture':'input'},'http://127.0.0.1:4000')) == {'controlled':True}
            assert captured[0][1] == {'fixture':'input'} and admitted.handed_off
            assert len(captured)==1 and len(launches)==1
        else:
            with pytest.raises((RuntimeUnknown,HAError)):
                await ha_model_forward(executor,payload,{'fixture':'input'},'http://127.0.0.1:4000')
            assert not captured and len(launches)==1
            assert admitted.handed_off is (fault != 'expired_host')
    finally:
        CURRENT.reset(token); server.close(); await server.wait_closed()


@pytest.mark.asyncio
async def test_model_transport_requires_live_scope_before_child_launch(tmp_path):
    with pytest.raises(HAError,match='ha_runtime_unqualified'):
        await ha_model_forward(None,{}, {},'http://127.0.0.1:4000')


@pytest.mark.asyncio
async def test_helper_response_deadline_is_total_even_when_peer_trickles(tmp_path):
    received = asyncio.Event()
    connections = []
    async def controlled_guard(reader, writer):
        connections.append(asyncio.current_task())
        try:
            await reader.readuntil(b'\r\n\r\n'); received.set()
            writer.write(b'HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n'); await writer.drain()
            for _ in range(100):
                writer.write(b' '); await writer.drain(); await asyncio.sleep(.01)
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close()
    server = await asyncio.start_server(controlled_guard,'127.0.0.1',0)
    port = server.sockets[0].getsockname()[1]
    source = 'import socket\nconnect=socket.create_connection\nsocket.create_connection=lambda address,timeout:connect(("127.0.0.1",'+str(port)+'),timeout)\n'+MODEL_HELPER
    child = await asyncio.create_subprocess_exec(sys.executable,'-I','-c',source,
        stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
    try:
        assert await asyncio.wait_for(child.stdout.readline(),1) == b'NETCLAW_HA_MODEL_READY_V1\n'
        child.stdin.write(json.dumps({'request':{},'guard_token':'fixture','admission_ms':1000,'completion_ms':80}).encode());child.stdin.close()
        await asyncio.wait_for(received.wait(),1)
        assert await asyncio.wait_for(child.wait(),.5) == 70
    finally:
        if child.returncode is None:child.kill();await child.wait()
        server.close();await server.wait_closed()
        await asyncio.gather(*connections,return_exceptions=True)


@pytest.mark.asyncio
async def test_model_cancellation_reaps_owned_client_and_sends_no_input(tmp_path, monkeypatch):
    from bgp.federation import protected_docker as docker
    original_create=asyncio.create_subprocess_exec; process=None; launched=asyncio.Event()
    async def create(*args,**kwargs):
        nonlocal process
        process=await original_create(sys.executable,'-I','-c','import time;time.sleep(60)',**kwargs)
        launched.set();return process
    monkeypatch.setattr(asyncio,'create_subprocess_exec',create)
    monkeypatch.setattr(docker,'_docker_host',lambda value:value)
    config=tmp_path/'docker';config.mkdir();(config/'config.json').write_bytes(b'{}')
    executor=SimpleNamespace(docker='/controlled-docker',docker_host='fixture',docker_config=config,
        config={'docker_host':'fixture'},ollama={'guard_uid':501,'model_container_id':'fixture'},guard_token='fake-capability')
    payload={'limits':{'expires_at_ms':int(time.time()*1000)+5000,'inference_timeout_ms':3000}}
    admitted=EffectScope('model',lambda:3000);token=CURRENT.set(admitted)
    try:
        task=asyncio.create_task(ha_model_forward(executor,payload,{},'http://127.0.0.1:4000'))
        await asyncio.wait_for(launched.wait(),1);task.cancel()
        with pytest.raises(asyncio.CancelledError):await asyncio.wait_for(task,1)
        assert process.returncode is not None and not admitted.handed_off
    finally:CURRENT.reset(token)
