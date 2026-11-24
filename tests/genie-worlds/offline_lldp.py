"""Installed parser qualification using only synthetic text, never device I/O."""
import hashlib
import json
import subprocess
from pathlib import Path
from importlib.metadata import version
from genie.libs.parser.iosxe.show_lldp import ShowLldpNeighborsDetail
from lldp_test import LldpExtractionTests
from lldp_graph_test import LldpGraphTests, NODE


class OfflineOnly:
    calls = 0

    def execute(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError('device execution forbidden')


raw = '''------------------------------------------------
Local Intf: Gi0/1
Chassis id: synthetic-chassis
Port id: Gi0/2
Port Description: Synthetic port
System Name: synthetic-switch
System Description:
Time remaining: 110 seconds
System Capabilities: B,R
Enabled Capabilities: B
Total entries displayed: 1
'''
device = OfflineOnly()
parsed = json.loads(json.dumps(ShowLldpNeighborsDetail(device=device).parse(output=raw)))
fixture = LldpExtractionTests(); fixture.setUp()
fixture.observation.update(parsed=parsed, parser_version=version('genie.libs.parser'),
                           sha256=hashlib.sha256(raw.encode()).hexdigest())
result = fixture.result()
claim = result['neighbor_observations'][0]
assert claim['remote_claim'] == 'synthetic-chassis'
assert claim['local_interface'] == 'GigabitEthernet0/1'
assert claim['remote_port'] == 'GigabitEthernet0/2'
for field, path in claim['field_paths'].items():
    value = parsed
    for key in path: value = value[key]
    assert value == claim[field]
assert claim['expires_at'] is None and claim['port_id_subtype'] is None
assert not result['hosted_eligible'] and not result['links'] and device.calls == 0
bridge = LldpGraphTests(); bridge.setUp()
bridge.observation.update(fixture.observation, source='synthetic-parser')
bound = bridge.result(); graph = bound['graph']
assert not bound['unbound_neighbors'] and not bound['hosted_eligible']
assert len(graph['links']) == 1 and graph['links'][0]['certainty'] == 'unknown'
assert graph['links'][0]['endpoints'] == ['synthetic-router-port','synthetic-switch-port']
assert graph['discovery'][0]['remote_identities'] == [dict(kind='chassis_id',value='synthetic-chassis')]
assert graph['discovery'][0]['reason'] == 'expiry_unknown'
code = """import fs from 'node:fs';import {localGraph,graphLayout} from './scripts/genie-worlds/viewer/network-graph.mjs';import {selectionDetails} from './scripts/genie-worlds/viewer/selection.mjs';const g=localGraph(JSON.parse(fs.readFileSync(0,'utf8')));if(!Object.isFrozen(g)||graphLayout(g).links.length!==1||!selectionDetails(g,g.links[0].id).raw||g.discovery[0].protocol!=='lldp')throw Error('LLDP bridge');"""
check = subprocess.run([NODE,'--input-type=module','-e',code],input=json.dumps(graph),
    text=True,capture_output=True,cwd=Path(__file__).resolve().parents[2])
assert check.returncode == 0, 'synthetic JavaScript graph/inspector boundary failed'
empty = ShowLldpNeighborsDetail(device=device).parse(output='Total entries displayed: 0')
fixture.observation['parsed'] = empty
assert fixture.result()['facts'][0]['value'] == 0
# The installed parser collapses repeated identical nested keys. Its reported
# total still exposes that loss; normalization must not report a complete table.
duplicate_raw = raw.replace('Total entries displayed: 1\n', '') * 2 + 'Total entries displayed: 2\n'
fixture.observation['parsed'] = json.loads(json.dumps(
    ShowLldpNeighborsDetail(device=device).parse(output=duplicate_raw)))
duplicate = fixture.result()
assert not duplicate['neighbor_observations']
assert duplicate['facts'][0]['reason'] == 'normalization_unqualified'
assert device.calls == 0
print(json.dumps(dict(result='pass', parser_version=version('genie.libs.parser'),
    device_execute_calls=device.calls, claims=1, empty_count=0, expiry='unknown',
    subtypes='unknown', duplicate_collapse='refused',
    graph_links=len(graph['links']), javascript_graph_inspector='pass',
    raw_sha256=hashlib.sha256(raw.encode()).hexdigest())))
