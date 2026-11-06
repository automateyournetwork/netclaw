"""Ordinary eN2N tools must execute the selected installation's registration."""
import asyncio
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from bgp.federation.channel import RpcError
from bgp.federation.invocation import Invoker
from bgp.federation.runtime import Runtime


SERVER = '''import json,os,sys,time
from pathlib import Path
if os.environ.get("PID_FILE"):
    Path(os.environ["PID_FILE"]).write_text(str(os.getpid()))
for line in sys.stdin:
    m=json.loads(line)
    if m.get("method")=="initialize":
        print(json.dumps({"jsonrpc":"2.0","id":m["id"],"result":{"protocolVersion":"2024-11-05","capabilities":{},"serverInfo":{"name":"fixture","version":"1"}}}),flush=True)
    elif m.get("method")=="tools/call":
        if os.environ.get("STALL"): time.sleep(60)
        print(json.dumps({"jsonrpc":"2.0","id":m["id"],"result":{"content":[{"type":"text","text":json.dumps({"cwd":os.getcwd(),"home":os.environ.get("OPENCLAW_STATE_DIR"),"marker":os.environ.get("MARKER"),"arguments":m["params"]["arguments"]})}],"isError":False}}),flush=True)
'''


def selected(tmp_path, shape='modern', extra_env=None):
    home = tmp_path / 'selected'; home.mkdir()
    script = home / 'native.py'; script.write_text(SERVER)
    cfg = {'command': sys.executable, 'args': ['-u', str(script)],
           'env': {'MARKER': '${OPENCLAW_STATE_DIR}', **(extra_env or {})}}
    config = {'mcp': {'servers': {'native': cfg}}} if shape == 'modern' else {'mcpServers': {'native': cfg}}
    file = home / 'openclaw.json'; file.write_text(json.dumps(config))
    runtime = Runtime('openclaw', home, file, 'b49e5aa7-63f0-4c8d-81ca-8f6304990bc9')
    svc = SimpleNamespace(runtime=runtime, manager=None, authz=None, audit=None)
    return Invoker(svc), cfg


@pytest.mark.parametrize('shape', ['modern', 'legacy'])
def test_selected_registration_and_environment(tmp_path, monkeypatch, shape):
    invoker, _ = selected(tmp_path, shape)
    monkeypatch.setenv('OPENCLAW_STATE_DIR', '/foreign-installation')
    result = asyncio.run(invoker._exec_tool_stdio('native/check', {'value': 7}))
    value = json.loads(result['content'][0]['text'])
    expected = str(invoker.service.runtime.home)
    assert value == {'cwd': expected, 'home': expected, 'marker': expected, 'arguments': {'value': 7}}


def test_missing_selected_registration_never_uses_foreign_config(tmp_path, monkeypatch):
    invoker, registration = selected(tmp_path)
    invoker.service.runtime.config.write_text('{}')
    # The old implementation consults this repository/default-home resolver.
    monkeypatch.setattr('bgp.federation.invocation._openclaw_config',
                        lambda: {'mcpServers': {'native': registration}})
    with pytest.raises(RpcError):
        asyncio.run(invoker._exec_tool_stdio('native/check', {}))


@pytest.mark.parametrize('filter_value,legacy,expected', [
    ({'include': ['subnet_calculator']}, None, ['subnet_calculator']),
    ({'include': ['subnet_calculator']}, ['subnet_calculator'], ['subnet_calculator']),
    ({'include': ['subnet_calculator']}, ['foreign_tool'], []),
    ({'include': ['*']}, None, []),
    ({'include': 'subnet_calculator'}, None, []),
])
def test_native_inventory_uses_explicit_current_tool_filter(tmp_path, filter_value, legacy, expected):
    from bgp.federation.inventory import InventoryBuilder
    invoker, registration = selected(tmp_path)
    registration['toolFilter'] = filter_value
    if legacy is not None:
        registration['tools'] = legacy
    runtime = invoker.service.runtime
    runtime.config.write_text(json.dumps({'mcp': {'servers': {'native': registration}}}))
    inventory = object.__new__(InventoryBuilder)
    inventory.runtime, inventory.config_path = runtime, runtime.config
    result = inventory._load_mcp_servers()
    assert result[0]['tools'] == expected
    assert result[0]['invocable_tools'] == expected


def test_selected_timeout_reaps_owned_child(tmp_path):
    pid = tmp_path / 'child.pid'
    invoker, _ = selected(tmp_path, extra_env={'STALL': '1', 'PID_FILE': str(pid)})
    invoker.tool_timeout = .3
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(invoker._exec_tool_stdio('native/check', {}))
    assert pid.exists()
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid.read_text()), 0)


def test_conflicting_registration_shapes_refused(tmp_path):
    invoker, registration = selected(tmp_path)
    cfg = json.loads(invoker.service.runtime.config.read_text())
    cfg['mcpServers'] = {'native': dict(registration, command='/different/command')}
    invoker.service.runtime.config.write_text(json.dumps(cfg))
    with pytest.raises(RpcError):
        asyncio.run(invoker._exec_tool_stdio('native/check', {}))


def test_registration_cannot_select_foreign_home(tmp_path):
    invoker, _ = selected(tmp_path, extra_env={'OPENCLAW_STATE_DIR': '/foreign-installation'})
    with pytest.raises(RpcError):
        asyncio.run(invoker._exec_tool_stdio('native/check', {}))
