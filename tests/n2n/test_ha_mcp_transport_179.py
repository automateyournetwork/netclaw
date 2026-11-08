"""Controlled stdio only: no model, integration, provider or native tool process."""
import asyncio
import os
import signal
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCRequest

from bgp.federation.ha.config import HAError
from bgp.federation.ha.effect import CURRENT, EffectScope
from bgp.federation.ha.mcp_transport import HAStdioWriter, ha_stdio_client, MAX_FRAME_BYTES


def message(method='tools/call', **params):
    return SessionMessage(JSONRPCRequest.model_validate({'jsonrpc': '2.0', 'id': 1,
        'method': method, 'params': params or {'name': 'fixture', 'arguments': {}}}))


class Pipe:
    def __init__(self):
        self.transport = self
        self.buffer = 0
        self.writes = []
        self.closed = False
        self.queue_write = False
        self.drains = 0

    def is_closing(self): return self.closed
    def get_write_buffer_size(self): return self.buffer
    def write(self, data):
        self.writes.append(data)
        if self.queue_write: self.buffer = len(data)
    def close(self): self.closed = True
    def abort(self): self.closed = True; self.buffer = 0
    async def drain(self): self.drains += 1


def permit(clock):
    def fresh():
        if clock['expired']: raise HAError('admission_expired', 403)
    return EffectScope('tool', fresh)


@pytest.mark.asyncio
async def test_serialization_delay_is_checked_at_sync_pipe_handoff():
    pipe = Pipe(); writer = HAStdioWriter(pipe, atomic_limit=4096)
    clock = {'expired': False}; admitted = permit(clock)
    class Delayed:
        def model_dump_json(self, **kwargs):
            clock['expired'] = True
            return message().message.model_dump_json(**kwargs)
    token = CURRENT.set(admitted)
    try:
        with pytest.raises(HAError, match='admission_expired'):
            await writer.send(SessionMessage(Delayed()))
        assert not pipe.writes and not admitted.handed_off
        clock['expired'] = False
        with pytest.raises(HAError, match='native_handoff_spent'):
            await writer.send(message())
    finally: CURRENT.reset(token)


@pytest.mark.asyncio
async def test_direct_handoff_spends_once_without_scheduling_or_drain():
    pipe = Pipe(); writer = HAStdioWriter(pipe, atomic_limit=4096)
    clock = {'expired': False}; admitted = permit(clock)
    token = CURRENT.set(admitted)
    try:
        asyncio.get_running_loop().call_soon(lambda: clock.update(expired=True))
        await writer.send(message())
        assert len(pipe.writes) == 1 and admitted.handed_off and pipe.drains == 0
        assert clock['expired'] is False
        with pytest.raises(HAError, match='native_handoff_spent'):
            await writer.send(message())
        CURRENT.set(permit(clock))
        with pytest.raises(HAError, match='native_handoff_spent'):
            await writer.send(message())
    finally: CURRENT.reset(token)


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['no_scope', 'inactive', 'wrong_kind', 'already_spent', 'expired', 'backpressure', 'oversized', 'closed'])
async def test_refused_handoff_writes_zero_bytes(fault):
    pipe = Pipe(); writer = HAStdioWriter(pipe, atomic_limit=512)
    clock = {'expired': fault == 'expired'}; admitted = permit(clock)
    if fault == 'inactive': admitted.active = False
    if fault == 'wrong_kind': admitted.kind = 'model'
    if fault == 'already_spent': admitted.handed_off = True
    if fault == 'backpressure': pipe.buffer = 1
    if fault == 'closed': pipe.closed = True
    token = CURRENT.set(None if fault == 'no_scope' else admitted)
    try:
        with pytest.raises(HAError):
            await writer.send(message(name='fixture', arguments={'value': 'x' * (1000 if fault == 'oversized' else 1)}))
        assert pipe.writes == [] and pipe.drains == 0
    finally: CURRENT.reset(token)


@pytest.mark.asyncio
async def test_os_pipe_backpressure_aborts_queued_frame_synchronously():
    pipe = Pipe(); pipe.queue_write = True
    writer = HAStdioWriter(pipe, atomic_limit=4096)
    admitted = permit({'expired': False}); token = CURRENT.set(admitted)
    try:
        with pytest.raises(HAError, match='native_handoff_unavailable'):
            await writer.send(message())
        assert admitted.handed_off and pipe.closed and pipe.buffer == 0 and pipe.drains == 0
    finally: CURRENT.reset(token)


@pytest.mark.asyncio
async def test_setup_messages_need_no_admission_and_unexpected_methods_fail_closed():
    pipe = Pipe(); writer = HAStdioWriter(pipe, atomic_limit=4096)
    await writer.send(message('initialize')); await writer.send(message('tools/list'))
    assert len(pipe.writes) == 2 and pipe.drains == 2
    with pytest.raises(HAError, match='native_method_refused'):
        await writer.send(message('resources/read'))
    assert len(pipe.writes) == 2


CONTROLLED_SERVER = '''
import json,os,sys
from pathlib import Path
root=Path(sys.argv[1]); root.joinpath('pid').write_text(str(os.getpid()))
for line in sys.stdin:
    request=json.loads(line); method=request.get('method')
    with root.joinpath('received').open('a') as file: file.write(method+'\\n')
    if 'id' not in request: continue
    if method=='initialize': result={'protocolVersion':'2025-11-25','capabilities':{'tools':{}},'serverInfo':{'name':'controlled-stdio-fixture','version':'1'}}
    elif method=='tools/list': result={'tools':[{'name':'fixture','inputSchema':{'type':'object'}}]}
    elif method=='tools/call': result={'content':[{'type':'text','text':'controlled fixture'}]}
    else: result={}
    print(json.dumps({'jsonrpc':'2.0','id':request['id'],'result':result}),flush=True)
'''


def params(tmp_path, source=CONTROLLED_SERVER):
    script = tmp_path / 'controlled.py'; script.write_text(source)
    return StdioServerParameters(command=sys.executable, args=['-I', str(script), str(tmp_path)],
                                 env={'PYTHONDONTWRITEBYTECODE': '1'}, cwd=str(tmp_path))


def dead(pid):
    try: os.kill(pid, 0)
    except ProcessLookupError: return True
    return False


@pytest.mark.asyncio
async def test_official_sdk_setup_then_late_admission_and_single_controlled_call(tmp_path):
    async with ha_stdio_client(params(tmp_path)) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            assert [tool.name for tool in (await session.list_tools()).tools] == ['fixture']
            admitted = permit({'expired': False}); token = CURRENT.set(admitted)
            try:
                result = await session.call_tool('fixture', {})
                assert result.content[0].text == 'controlled fixture' and admitted.handed_off
            finally: CURRENT.reset(token)
    assert (tmp_path / 'received').read_text().splitlines().count('tools/call') == 1
    assert dead(int((tmp_path / 'pid').read_text()))


@pytest.mark.asyncio
async def test_delayed_official_sdk_call_never_reaches_controlled_child(tmp_path):
    async with ha_stdio_client(params(tmp_path)) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize(); await session.list_tools()
            token = CURRENT.set(permit({'expired': True}))
            try:
                with pytest.raises(HAError, match='admission_expired'):
                    await session.call_tool('fixture', {})
            finally: CURRENT.reset(token)
    assert 'tools/call' not in (tmp_path / 'received').read_text().splitlines()
    assert dead(int((tmp_path / 'pid').read_text()))


@pytest.mark.asyncio
@pytest.mark.parametrize('bad', ['malformed', 'oversized', 'partial'])
async def test_reader_bounds_malformed_frames_and_eof(tmp_path, bad):
    output = {'malformed': 'not-json\\n', 'oversized': 'x' * (MAX_FRAME_BYTES + 2) + '\\n',
              'partial': '{"jsonrpc":"2.0"}'}[bad]
    source = 'import sys\nsys.stdout.write(' + repr(output.replace('\\n', '\n')) + ');sys.stdout.flush()\n'
    async with ha_stdio_client(params(tmp_path, source)) as (reader, writer):
        result = await asyncio.wait_for(reader.receive(), 2)
        assert isinstance(result, HAError)


@pytest.mark.asyncio
async def test_cancellation_reaps_owned_child_that_ignores_term(tmp_path):
    source = '''import os,signal,sys,time
from pathlib import Path
signal.signal(signal.SIGTERM,signal.SIG_IGN)
Path(sys.argv[1],'pid').write_text(str(os.getpid()))
while True: time.sleep(1)
'''
    ready = asyncio.Event()
    async def run():
        async with ha_stdio_client(params(tmp_path, source), shutdown_seconds=.05):
            while not (tmp_path / 'pid').exists(): await asyncio.sleep(.01)
            ready.set(); await asyncio.Event().wait()
    task = asyncio.create_task(run()); await asyncio.wait_for(ready.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError): await asyncio.wait_for(task, 2)
    assert dead(int((tmp_path / 'pid').read_text()))


@pytest.mark.asyncio
async def test_real_full_os_pipe_never_flushes_a_tool_frame_later(tmp_path):
    source = '''import os,sys,time
from pathlib import Path
root=Path(sys.argv[1]);root.joinpath('pid').write_text(str(os.getpid()))
while not root.joinpath('read-now').exists(): time.sleep(.01)
root.joinpath('input').write_bytes(sys.stdin.buffer.read())
'''
    async with ha_stdio_client(params(tmp_path, source)) as (reader, writer):
        while not (tmp_path / 'pid').exists(): await asyncio.sleep(.01)
        fd = writer.transport.get_extra_info('pipe').fileno()
        # Fill the actual owned nonblocking pipe without going through asyncio's
        # userspace buffer, then attempt the admitted atomic frame.
        filled = 0
        while True:
            try: filled += os.write(fd, b'x' * writer.atomic_limit)
            except BlockingIOError: break
        admitted = permit({'expired': False}); token = CURRENT.set(admitted)
        try:
            with pytest.raises(HAError, match='native_handoff_unavailable'):
                await writer.send(message())
            assert admitted.handed_off and writer.closed
        finally: CURRENT.reset(token)
        (tmp_path / 'read-now').touch()
        for _ in range(200):
            if (tmp_path / 'input').exists(): break
            await asyncio.sleep(.01)
        assert (tmp_path / 'input').read_bytes() == b'x' * filled
    assert dead(int((tmp_path / 'pid').read_text()))


@pytest.mark.asyncio
async def test_owned_process_group_is_signalled_for_descendants(tmp_path, monkeypatch):
    groups = []
    original = os.killpg
    def record_group(group, sig):
        groups.append((group, sig)); return original(group, sig)
    monkeypatch.setattr(os, 'killpg', record_group)
    async with ha_stdio_client(params(tmp_path)) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            pid = int((tmp_path / 'pid').read_text())
            assert os.getpgid(pid) == pid and pid != os.getpgrp()
    assert (pid, signal.SIGKILL) in groups and dead(pid)
