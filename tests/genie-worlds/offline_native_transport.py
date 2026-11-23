"""Actual installed plugin + independent local PTY peer, no SSH or device calls.

Run with the selected Python3.12 and selected upstream server source as argv[1].
Uses the exact native read validator but never imports the operational server.
This qualifies command emission at a synthetic enable prompt, not SSH identity,
authentication, real-device behavior or collector adapter installation.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import typing

from pyats.topology.loader import load as load_testbed

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


session = load('native_session', ROOT/'scripts/genie-worlds/native_session.py')
policy = load('protected_policy', ROOT/'scripts/lib/protected_pyats.py')
policy.validate_native_policy({'devices': {'Router': {'os': 'iosxe', 'platform': 'iol'}}}, 'Router')
source = Path(sys.argv[1]).resolve(strict=True)
tree = ast.parse(source.read_text())
names = {'_SHOW_BLOCK_CHARS', '_SHOW_BLOCK_WORDS'}
nodes = [n for n in tree.body if
    (isinstance(n, ast.FunctionDef) and n.name == 'validate_show_command') or
    (isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id in names) or
    (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets))]
assert len(nodes) == 3
server = ModuleType('selected_policy'); server.__file__ = str(source)
server.__dict__.update(re=re, Optional=typing.Optional, List=typing.List)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), server.__dict__)
digest = hashlib.sha256(source.read_bytes()).hexdigest()
results = []
for command, state in [(c, 'enable') for c in sorted(session.read.COMMANDS)] + [('show interfaces', 'disable')]:
    with tempfile.TemporaryDirectory(dir=ROOT/'.spec200-local/tests') as directory:
        directory = Path(directory); directory.chmod(0o700)
        transcript = directory/'received.jsonl'
        start = shlex.join([sys.executable, '-u', str(Path(__file__).with_name('synthetic_terminal.py')),
                            str(transcript), command, state])
        # Synthetic command transport is confined to this test. Production frozen
        # preparation still permits only the pinned strict SSH endpoint contract.
        device = load_testbed({'devices': {'Router': {'os': 'iosxe', 'platform': 'iol',
            'type': 'router', 'connections': {'defaults': {'class': 'unicon.Unicon'},
                'cli': {'command': start}}}}}).devices['Router']
        prepared = SimpleNamespace(device=device, connection_options=lambda timeout: {
            **policy.connection_policy(), 'via': 'cli', 'connection_timeout': timeout})
        refused = False
        try:
            with session.connected_capture(prepared, server, command, timeout=3,
                    source_sha256=digest, logfile=directory/'native.log') as raw:
                assert state == 'enable'
                assert raw.strip() == 'SPEC200 independent synthetic raw response'
                (directory/'preserved.txt').write_text(raw)
        except session.read.ReadRefused as error:
            assert state == 'disable' and str(error) == 'connection_policy_not_applied'
            refused = True
        except Exception as error:
            # This harness contains synthetic data only; preserve useful failure
            # diagnostics before TemporaryDirectory removes the synthetic peer.
            print('SYNTHETIC FAILURE', repr(error.__context__), flush=True)
            if (directory/'native.log').exists():
                print((directory/'native.log').read_text(), flush=True)
            raise
        lines = [json.loads(line) for line in transcript.read_text().splitlines()] if transcript.exists() else []
        commands = [line for line in lines if line]
        assert commands == ([command] if state == 'enable' else []), commands
        assert not device.is_connected()
        assert refused == (state == 'disable')
        results.append({'state': state, 'capture_commands': len(commands),
                        'blank_prompt_probes': lines.count(''), 'refused': refused})
print(json.dumps({'result': 'pass', 'cases': results, 'native_policy_sha256': digest,
                  'real_device_calls': 0, 'ssh_qualification': False}))
