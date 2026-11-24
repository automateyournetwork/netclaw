"""Fresh collector subprocess + installed native stack; independent synthetic PTY.

Run with selected Python3.12 and upstream policy source argv[1]. No sockets,
production adapter marker, real credentials or SSH qualification. Only this test
substitutes PTY transport AFTER the frozen native preparation checks pass.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import socket
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import typing

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def configure(directory, policy_path, fault):
    """Called inside each fresh child by a private synthetic adapter module."""
    directory = Path(directory)
    adapter = load('synthetic_native_adapter', ROOT/'scripts/genie-worlds/native_adapter.py')
    native = adapter.connection
    source = Path(policy_path)
    tree = ast.parse(source.read_text())
    names = {'_SHOW_BLOCK_CHARS', '_SHOW_BLOCK_WORDS'}
    nodes = [n for n in tree.body if
        (isinstance(n, ast.FunctionDef) and n.name == 'validate_show_command') or
        (isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id in names) or
        (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets))]
    assert len(nodes) == 3
    server = ModuleType('synthetic_selected_policy'); server.__file__ = str(source)
    server.__dict__.update(re=re, Optional=typing.Optional, List=typing.List)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), server.__dict__)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    pin = directory/'known_hosts'
    document = {'testbed': {'name': 'synthetic', 'credentials': copy.deepcopy(native.CREDENTIALS)},
        'devices': {'Router': {'os': 'iosxe', 'platform': 'iol', 'type': 'router',
            'connections': {'defaults': {'class': 'unicon.Unicon'}, 'cli': {'protocol': 'ssh',
                'ip': '192.0.2.1', 'port': 22, 'ssh_options': native.SSH_PREFIX+str(pin)}}}}}
    endpoint = native.policy.endpoint_identity('Router', SimpleNamespace(os='iosxe',
        connections=document['devices']['Router']['connections']))
    frozen_hash = native.digest(document)
    if fault == 'inventory': document['devices']['Router']['type'] = 'switch'
    if fault == 'source': source.write_text(source.read_text()+'\n# synthetic source change\n')
    binding = adapter.FrozenCapture(document, 'Router', document_sha256=frozen_hash,
        endpoint_sha256=native.digest(endpoint), server=server, source_sha256=source_hash)
    original_prepare = native.prepare_device

    def synthetic_prepare(*args, **kwargs):
        prepared = original_prepare(*args, **kwargs)
        options = prepared.connection_options(10)
        from pyats.topology.loader import load as load_testbed
        transcript = directory/(str(os.getpid())+'.commands.jsonl')
        command = json.loads(Path(sys.argv[-1]).read_text())['command']
        arguments = [sys.executable, '-u', str(Path(__file__).with_name('synthetic_terminal.py')),
                     str(transcript), command, 'enable']
        if command == 'show lldp neighbors detail':
            arguments.append(str(directory/'lldp.txt'))
        start = shlex.join(arguments)
        device = load_testbed({'devices': {'Router': {'os': 'iosxe', 'platform': 'iol',
            'type': 'router', 'connections': {'defaults': {'class': 'unicon.Unicon'},
                'cli': {'command': start}}}}}).devices['Router']
        if fault == 'disconnect':
            disconnect = device.disconnect
            def fail():
                disconnect()
                raise RuntimeError('synthetic cleanup failure')
            device.disconnect = fail
        return SimpleNamespace(device=device, connection_options=lambda timeout:options)

    native.prepare_device = synthetic_prepare
    def no_network(*args, **kwargs): raise AssertionError('synthetic test forbids network')
    socket.socket.connect = no_network
    return binding


def main(source):
    collector = load('synthetic_collector', ROOT/'scripts/genie-worlds/collector.py')
    results = []
    for fault in ['none', 'source', 'inventory', 'disconnect']:
        with tempfile.TemporaryDirectory(dir=ROOT/'.spec200-local/tests') as temporary:
            directory = Path(temporary); directory.chmod(0o700)
            pin = directory/'known_hosts'; pin.write_text('synthetic offline trust\n'); pin.chmod(0o600)
            tree = ast.parse(Path(__file__).with_name('offline_lldp.py').read_text())
            raw = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'raw' for t in n.targets))
            (directory/'lldp.txt').write_text(raw)
            policy_copy = directory/'policy.py'; policy_copy.write_bytes(source.read_bytes())
            shim = directory/'adapter.py'
            shim.write_text('import sys\n'
                f'sys.path.insert(0, {str(Path(__file__).parent)!r})\n'
                'from offline_native_collector import configure\n'
                f'binding=configure({str(directory)!r}, {str(policy_copy)!r}, {fault!r})\n'
                'qualified_read_only_capture=True\n'
                'capture_context=binding.capture_context\n'
                'parse_captured=binding.parse_captured\n')
            result = collector.collect(['Router'], shim, 'synthetic-native', evidence_root=directory,
                                       read_timeout=30, overall_timeout=120)
            observations = result['observations']
            commands = [json.loads(line) for p in directory.glob('*.commands.jsonl')
                        for line in p.read_text().splitlines()]
            if fault == 'none':
                expected = list(collector.facts.PROFILES['initial'][0])
                assert sorted(commands) == sorted(expected), commands
                assert [o['command'] for o in observations] == expected
                assert len(observations) == 3 and result['complete']
                assert len(list(directory.glob('*.commands.jsonl'))) == 3
                # Two parser failures preserve raw without another execution;
                # the LLDP fixture also proves successful detached native parse.
                assert [o['outcome'] for o in observations] == ['parse_failed', 'parse_failed', 'observed']
                assert observations[-1]['parsed']['total_entries'] == 1
                assert all(o['raw'] and
                    not o['cleanup_outcome_unknown'] for o in observations), observations
            elif fault == 'disconnect':
                assert commands == ['show version'], commands
                assert len(observations) == 1 and not result['complete']
                assert observations[0]['outcome'] == 'raw_only'
                assert observations[0]['raw'] and observations[0]['cleanup_outcome_unknown']
                assert observations[0]['parsed'] is None
            else:
                assert commands == [], commands
                assert all(o['outcome'] == 'unavailable' and not o['raw'] for o in observations)
            assert all(p.stat().st_mode & 0o777 == 0o600 for p in directory.glob('capture-*/*') if p.is_file())
            results.append({'fault': fault, 'reads': len(observations), 'commands': len(commands),
                            'raw_preserved': sum(bool(o['raw']) for o in observations)})
    print(json.dumps({'result':'pass', 'cases':results, 'real_device_calls':0,
                      'ssh_qualification':False, 'production_capability':False}))


if __name__ == '__main__':
    for key in ('SPEC200_PYATS_USERNAME','SPEC200_PYATS_PASSWORD','SPEC200_PYATS_ENABLE_PASSWORD'):
        os.environ[key] = 'independent-synthetic-value'
    main(Path(sys.argv[1]).resolve(strict=True))
