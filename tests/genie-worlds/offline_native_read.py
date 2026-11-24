"""Selected-runtime qualification with synthetic text and no native connection.

Pass the selected upstream server source path. Only its validator and constants
are compiled; importing the operational server is deliberately unnecessary.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('native_read', root / 'scripts/genie-worlds/native_read.py')
native = importlib.util.module_from_spec(spec); spec.loader.exec_module(native)
source = Path(sys.argv[1]).resolve(strict=True)
tree = ast.parse(source.read_text())
names = {'_SHOW_BLOCK_CHARS', '_SHOW_BLOCK_WORDS'}
nodes = [n for n in tree.body if
         (isinstance(n, ast.FunctionDef) and n.name == 'validate_show_command') or
         (isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id in names) or
         (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets))]
assert len(nodes) == 3, 'selected validator shape changed'
server = ModuleType('selected_native_policy'); server.__file__ = str(source)
server.__dict__.update(re=re, Optional=__import__('typing').Optional, List=__import__('typing').List)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), server.__dict__)
digest = hashlib.sha256(source.read_bytes()).hexdigest()
for command in native.COMMANDS:
    native.validate_read(server, command, source_sha256=digest)
calls = []
device = SimpleNamespace(os='iosxe', mit=True, operating_mode=True, learn_os=False,
    learn_tokens=False, learn_hostname=False, reconnect=False,
    settings=SimpleNamespace(LEARN_DEVICE_TOKENS=False),
    state_machine=SimpleNamespace(current_state='enable'), is_connected=lambda: True)
for fixture, command in [('offline_interfaces.py','show interfaces'),
                         ('offline_cdp.py','show cdp neighbors detail'),
                         ('offline_lldp.py','show lldp neighbors detail')]:
    fixture_tree = ast.parse((root / 'tests/genie-worlds' / fixture).read_text())
    raw = next(ast.literal_eval(n.value) for n in fixture_tree.body if isinstance(n,ast.Assign)
               and any(isinstance(t,ast.Name) and t.id == 'raw' for t in n.targets))
    def execute(command, **kw):
        calls.append(command); return raw
    device.execute = execute
    captured = native.capture_once(server,device,command,timeout=3,source_sha256=digest)
    assert captured == raw
    parsed = native.parse_captured(command,output=captured)
    assert isinstance(parsed,dict) and parsed
assert len(calls) == 3
for module,name in native.PARSERS.values():
    assert getattr(__import__('importlib').import_module('genie.libs.parser.iosxe.'+module),name)
print(json.dumps({'result':'pass','native_policy_sha256':digest,
    'allowed_reads':len(native.COMMANDS),'synthetic_execute_calls':len(calls),
    'real_device_calls':0,'offline_parsers':3,'parser_classes':5}))
