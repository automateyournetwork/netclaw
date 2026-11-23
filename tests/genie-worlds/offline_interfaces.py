"""Run explicitly in selected installed Genie runtime; synthetic input only."""
import hashlib
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from genie.libs.parser.iosxe.show_interface import ShowInterfaces


class OfflineOnly:
    calls = 0

    def execute(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError('device execution forbidden')


raw = '''GigabitEthernet0/1 is up, line protocol is up
  Hardware is Synthetic, address is 0000.0000.0001 (bia 0000.0000.0001)
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     5 packets input, 9223372036854775825 bytes, 0 no buffer
     0 packets output, 0 bytes, 0 underruns
GigabitEthernet0/2 is administratively down, line protocol is down
  Hardware is Synthetic, address is 0000.0000.0002 (bia 0000.0000.0002)
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
'''
device = OfflineOnly()
parsed = ShowInterfaces(device=device).parse(output=raw)
# Exercise the actual capture transport's JSON round trip too.
parsed = json.loads(json.dumps(parsed))
spec = importlib.util.spec_from_file_location('facts', Path(__file__).resolve().parents[2] / 'scripts/genie-worlds/facts.py')
facts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(facts)
observation = dict(id='synthetic-native-interfaces', device_ref='synthetic-router',
    classification='private', command='show interfaces', outcome='observed',
    started_at='2026-11-22T00:00:00Z', finished_at='2026-11-22T00:00:01Z',
    sha256=hashlib.sha256(raw.encode()).hexdigest(), parser_version=version('genie.libs.parser'),
    parsed=parsed)
result = facts.normalize([observation], profile='detailed',
    now=datetime(2026,11,22,0,0,2,tzinfo=timezone.utc))
rows = result['interface_observations']
assert len(rows) == 2 and device.calls == 0
assert rows[0]['counter_samples'][0]['value'] == '9223372036854775825'
assert rows[0]['counter_samples'][1]['value'] == '0'
assert rows[1]['state']['enabled']['value'] is False
assert rows[1]['state']['line_protocol']['value'] == 'down'
for row in rows:
    assert row['resolved_interface_id'] is None
    for sample in row['counter_samples']:
        assert sample['sampled_at'] is None and sample['width'] is None and sample['incarnation'] is None
        path = sample['source_path']
        if path is not None:
            value = parsed
            for component in path:
                value = value[component]
            assert str(value) == sample['value']
        else:
            assert sample['value'] is None and sample['reason'] == 'field_missing'
    for state in row['state'].values():
        value = parsed
        for component in state['source_path']:
            value = value[component]
        assert value == state['value']
assert result['links'] == [] and result['hosted_eligible'] is False
# Explicit synthetic inventory evidence, independent of parser-expanded names.
# This exercises binding mechanics, not qualification of any real native alias.
inventory = dict(id='synthetic-inventory', device_ref='synthetic-router',
    source='synthetic-inventory', command='inventory', parser_version='fixture',
    outcome='observed', sha256=hashlib.sha256(b'synthetic inventory').hexdigest(),
    started_at='2026-11-22T00:00:00Z', finished_at='2026-11-22T00:00:00Z')
proof = dict(inventory, observation_id=inventory['id'], source_path=['identity'])
devices = [dict(id='synthetic-router',label='Synthetic router',role='router',
    identities=[dict(kind='hostname',value='Synthetic router',evidence=proof)])]
ports = [dict(id=f'port-{i}',device_id='synthetic-router',label=name,status='unknown',
    identities=[dict(kind='interface_name',value=name,evidence=proof)])
    for i,name in enumerate(('GigabitEthernet0/1','GigabitEthernet0/2'))]
observation.update(source='synthetic-native-parser',sample_index=1)
second_raw=raw.replace('9223372036854775825','9223372036854775925')
second=dict(observation,id='synthetic-native-second',sample_index=2,
    started_at='2026-11-22T00:00:12Z',finished_at='2026-11-22T00:00:13Z',
    parsed=json.loads(json.dumps(ShowInterfaces(device=device).parse(output=second_raw))),
    sha256=hashlib.sha256(second_raw.encode()).hexdigest())
bound = facts.interface_counter_graph(devices,ports,[observation,second],[inventory],
    graph_id='synthetic-native-counters',now='2026-11-22T00:00:15Z')
assert not bound['unbound_interfaces'] and len(bound['graph']['counters']) == 8
assert all(c['value'] is None for c in bound['graph']['counters'])
counter=next(c for c in bound['graph']['counters'] if c['interface_id']=='port-0' and c['field']=='in_octets')
assert [s['value'] for s in counter['observed_samples']] == ['9223372036854775825','9223372036854775925']
assert device.calls == 0
node='/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node'
code="import fs from 'node:fs';import {localGraph} from './scripts/genie-worlds/viewer/network-graph.mjs';import {selectionDetails} from './scripts/genie-worlds/viewer/selection.mjs';const g=localGraph(JSON.parse(fs.readFileSync(0,'utf8')));if(!selectionDetails(g,'port-0').rows.some(([k,v])=>v.includes('9223372036854775825 bytes')))throw Error('parser count lost');"
check=subprocess.run([node,'--input-type=module','-e',code],input=json.dumps(bound['graph']),
    text=True,capture_output=True,cwd=Path(__file__).resolve().parents[2])
assert check.returncode == 0, 'synthetic graph boundary failed'
print(json.dumps(dict(result='pass', parser_version=version('genie.libs.parser'),
    device_execute_calls=device.calls, interface_readings=len(rows),
    graph_counters=len(bound['graph']['counters']), javascript_inspector='pass',
    raw_sha256=observation['sha256'])))
