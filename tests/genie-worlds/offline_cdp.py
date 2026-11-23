"""Selected installed Genie parser to local graph; synthetic inputs, no execution."""
import hashlib
import json
import subprocess
from importlib.metadata import version
from pathlib import Path
from genie.libs.parser.iosxe.show_cdp import ShowCdpNeighborsDetail
from cdp_graph_test import CdpGraphTests, NODE, facts


class OfflineOnly:
    calls = 0

    def execute(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError('device execution forbidden')


raw = '''-------------------------
Device ID: synthetic-switch
Entry address(es):
Platform: cisco Synthetic, Capabilities: Router Switch
Interface: GigabitEthernet0/1, Port ID (outgoing port): GigabitEthernet0/2
Holdtime : 120 sec
Version :
Synthetic fixture
advertisement version: 2
Duplex: full
Management address(es):

Total cdp entries displayed : 1
'''
device = OfflineOnly()
parsed = json.loads(json.dumps(ShowCdpNeighborsDetail(device=device).parse(output=raw)))
fixture = CdpGraphTests(); fixture.setUp()
fixture.observation.update(parsed=parsed, parser_version=version('genie.libs.parser'),
                           sha256=hashlib.sha256(raw.encode()).hexdigest())
result = fixture.result()
claim = result['normalization']['neighbor_observations'][0]
for field, path in claim['field_paths'].items():
    value = parsed
    for part in path:
        value = value[part]
    assert value == claim[field]
graph = result['graph']
assert not result['unbound_neighbors'] and not result['hosted_eligible']
assert len(graph['links']) == 1 and graph['links'][0]['certainty'] == 'unknown'
assert graph['discovery'][0]['reason'] == 'expiry_unknown'
assert graph['links'][0]['endpoints'] == ['synthetic-router-port','synthetic-switch-port']
assert device.calls == 0
code = """import fs from 'node:fs';import {localGraph,graphLayout} from './scripts/genie-worlds/viewer/network-graph.mjs';import {selectionDetails} from './scripts/genie-worlds/viewer/selection.mjs';const g=localGraph(JSON.parse(fs.readFileSync(0,'utf8')));const d=selectionDetails(g,g.links[0].id);if(!Object.isFrozen(g)||graphLayout(g).links.length!==1||!d.raw||g.discovery[0].reason!=='expiry_unknown')throw Error('native parser graph bridge');"""
check = subprocess.run([NODE,'--input-type=module','-e',code],input=json.dumps(graph),
    text=True,capture_output=True,cwd=Path(__file__).resolve().parents[2])
assert check.returncode == 0, 'synthetic JavaScript graph boundary failed'
print(json.dumps(dict(result='pass',parser_version=version('genie.libs.parser'),
    device_execute_calls=device.calls,graph_links=len(graph['links']),
    javascript_graph_inspector='pass',expiry='unknown',raw_sha256=fixture.observation['sha256'])))
