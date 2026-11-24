import copy
import json
import subprocess
import unittest
import cdp_graph_test
import lldp_test
import normalized_graph_test
from graph_bridge_test import NODE

facts = cdp_graph_test.facts


class DetailedGraphTests(unittest.TestCase):
    def setUp(self):
        c = cdp_graph_test.CdpGraphTests(); c.setUp()
        self.devices, self.ports, self.catalog = c.devices, c.ports, c.catalog
        l = lldp_test.LldpExtractionTests(); l.setUp()
        l.observation['source'] = 'synthetic-parser'
        proof = self.devices[1]['identities'][0]['evidence']
        self.devices[1]['identities'].append(dict(kind='chassis_id', value='synthetic-chassis', evidence=proof))
        i = normalized_graph_test.NormalizedGraphTests(); i.setUp()
        self.rows = [c.observation, l.observation, i.first, i.second]
        self.rows.append(dict(copy.deepcopy(i.first), id='failed-version', command='show version',
                              outcome='timeout', sha256=None, capture_outcome_unknown=True))

    def result(self, rows=None):
        return facts.detailed_collection_graph(self.devices, self.ports,
            self.rows if rows is None else rows, self.catalog,
            graph_id='synthetic-detailed', now='2026-11-22T00:00:15Z')

    def test_one_graph_preserves_both_protocols_counters_and_failed_coverage(self):
        before = copy.deepcopy([self.devices, self.ports, self.rows])
        r = self.result(); g = r['graph']
        self.assertEqual(len(g['links']), 1)
        self.assertEqual({c['protocol'] for c in g['discovery']}, {'cdp','lldp'})
        self.assertEqual(g['links'][0]['endpoints'], sorted(p['id'] for p in self.ports))
        self.assertEqual(len(g['coverage']), 7)
        self.assertTrue(next(c for c in g['coverage'] if c['id']=='failed-version')['capture_outcome_unknown'])
        counter = next(c for c in g['counters'] if c['field']=='in_octets')
        self.assertEqual([s['value'] for s in counter['observed_samples']], [str(2**63+17),str(2**63+117)])
        self.assertIsNone(counter['value'])
        self.assertTrue(all(p['status']=='unknown' for p in g['interfaces']))
        self.assertEqual(len(r['interface_states']), 2)
        self.assertEqual(g['interface_states'],r['interface_states'])
        self.assertTrue(all(s['resolved_interface_id']=='synthetic-router-port' for s in r['interface_states']))
        self.assertEqual(r['interface_states'][0]['state']['enabled']['value'], True)
        self.assertFalse(r['hosted_eligible'])
        self.assertEqual(before, [self.devices,self.ports,self.rows])
        self.assertEqual(r, self.result(list(reversed(self.rows))))
        code = """import fs from 'node:fs';import {localGraph,graphLayout} from './scripts/genie-worlds/viewer/network-graph.mjs';import {selectionDetails} from './scripts/genie-worlds/viewer/selection.mjs';const g=localGraph(JSON.parse(fs.readFileSync(0,'utf8')));if(!Object.isFrozen(g)||graphLayout(g).links.length!==1||!selectionDetails(g,'synthetic-router-port').rows.some(([k,v])=>v.includes('9223372036854775825 bytes')))throw Error('combined graph lost evidence');if(selectionDetails(g,'synthetic-router-port').raw.interfaceStates.length!==2||!selectionDetails(g,'synthetic-router-port').rows.some(([k,v])=>k==='enabled'&&v.startsWith('true')))throw Error('state observations lost');"""
        p = subprocess.run([NODE,'--input-type=module','-e',code],input=json.dumps(g),text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)

    def test_unbound_local_records_are_preserved_without_geometry(self):
        self.ports[0]['identities'][0]['value']='Gi0/1'
        r=self.result()
        self.assertFalse(r['graph']['links']); self.assertFalse(r['graph']['counters'])
        self.assertEqual(len(r['unbound_neighbors']),2)
        self.assertEqual(len(r['unbound_interfaces']),2)
        self.assertTrue(all(s['resolved_interface_id'] is None for s in r['interface_states']))
        self.assertEqual(len(r['graph']['coverage']),7)

    def test_protocol_disagreement_is_resolved_jointly_as_competing_claims(self):
        extra = copy.deepcopy(self.ports[1]); extra['id']='synthetic-other-port'
        for identity in extra['identities']: identity['value']='GigabitEthernet0/3'
        self.ports.append(extra)
        neighbor = self.rows[1]['parsed']['interfaces']['GigabitEthernet0/1']['port_id']
        row = neighbor.pop('GigabitEthernet0/2')
        row['neighbors']['synthetic-switch']['port_id']='GigabitEthernet0/3'
        neighbor['GigabitEthernet0/3']=row
        g=self.result()['graph']
        self.assertEqual(len(g['links']),2)
        self.assertTrue(all(link['certainty']=='conflict' for link in g['links']))
        self.assertTrue(all(c['reason']=='competing_peer_claims' for c in g['discovery']))

    def test_state_binding_does_not_require_a_counter_slot_or_imply_health(self):
        self.rows[2].pop('sample_index')
        self.rows[2]['parsed']['GigabitEthernet0/1']['line_protocol']='down'
        r=self.result()
        self.assertEqual(r['unbound_interfaces'][0]['reason'],'sample_slot_unknown')
        self.assertTrue(all(s['resolved_interface_id'] for s in r['interface_states']))
        self.assertEqual({s['state']['line_protocol']['value'] for s in r['interface_states']},{'up','down'})
        self.assertTrue(all(p['status']=='unknown' for p in r['graph']['interfaces']))

    def test_duplicate_cross_protocol_ids_and_excess_reads_are_refused(self):
        for rows in (self.rows+[dict(self.rows[0],id='extra')], self.rows*5,
                     [dict(self.rows[0],command='show running-config')],
                     [self.rows[0],dict(self.rows[1],id=self.rows[0]['id'])],
                     self.rows+[dict(self.rows[2],id='third')]):
            with self.assertRaises(ValueError): self.result(rows)
        self.rows[3]['sample_index']=1
        with self.assertRaises(ValueError): self.result()

    def test_empty_and_unqualified_discovery_are_not_lost(self):
        self.rows[0]['parsed']={'total_entries_displayed':0}
        self.rows[1]['parsed']={}
        r=self.result()
        self.assertFalse(r['graph']['links'])
        self.assertTrue(any(f.get('reason')=='normalization_unqualified' for f in r['normalization']['facts']))
        self.assertTrue(any(f['value']==0 for f in r['normalization']['facts']))
        self.assertEqual(len(r['graph']['counters']),4)

    def test_forged_inventory_proof_is_refused_before_binding(self):
        self.ports[0]['identities'][0]['evidence']['sha256']='f'*64
        with self.assertRaises(ValueError): self.result()


if __name__ == '__main__': unittest.main()
