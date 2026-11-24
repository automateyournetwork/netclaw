import copy
import json
import subprocess
import unittest
import lldp_test
import cdp_graph_test
from graph_bridge_test import NODE

facts = lldp_test.facts


class LldpGraphTests(unittest.TestCase):
    def setUp(self):
        inventory = cdp_graph_test.CdpGraphTests(); inventory.setUp()
        self.catalog, self.devices, self.ports = inventory.catalog, inventory.devices, inventory.ports
        for device in self.devices:
            device['identities'][0]['kind'] = 'chassis_id'
        self.devices[1]['identities'][0]['value'] = 'synthetic-chassis'
        case = lldp_test.LldpExtractionTests(); case.setUp()
        self.observation = case.observation
        self.row = case.row
        self.observation['source'] = 'synthetic-parser'

    def result(self, observations=None):
        return facts.lldp_neighbor_graph(self.devices,self.ports,
            [self.observation] if observations is None else observations,self.catalog,
            graph_id='synthetic-lldp-graph',now='2026-11-22T00:00:10Z')

    def test_exact_binding_survives_javascript_without_health_or_expiry(self):
        before=copy.deepcopy([self.devices,self.ports,self.observation])
        result=self.result(); g=result['graph']
        self.assertEqual(len(g['links']),1); self.assertEqual(g['links'][0]['certainty'],'unknown')
        self.assertEqual(g['discovery'][0]['reason'],'expiry_unknown')
        self.assertEqual(g['discovery'][0]['remote_interface_id'],'synthetic-switch-port')
        self.assertEqual(g['links'][0]['endpoints'],sorted(p['id'] for p in self.ports))
        normalized = result['normalization']['neighbor_observations'][0]
        self.assertIsNone(normalized['chassis_id_subtype']); self.assertIsNone(normalized['port_id_subtype'])
        self.assertEqual(g['discovery'][0]['remote_identities'],[dict(kind='chassis_id',value='synthetic-chassis')])
        self.assertFalse(result['unbound_neighbors']); self.assertFalse(result['hosted_eligible'])
        self.assertTrue(all(p['status']=='unknown' for p in g['interfaces']))
        self.assertEqual(before,[self.devices,self.ports,self.observation])
        code="""import fs from 'node:fs';import {localGraph,graphLayout} from './scripts/genie-worlds/viewer/network-graph.mjs';import {selectionDetails} from './scripts/genie-worlds/viewer/selection.mjs';const g=localGraph(JSON.parse(fs.readFileSync(0,'utf8')));if(!Object.isFrozen(g)||graphLayout(g).links.length!==1||!selectionDetails(g,g.links[0].id).raw)throw Error('bridge');"""
        p=subprocess.run([NODE,'--input-type=module','-e',code],input=json.dumps(g),text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)

    def test_unmatched_ambiguous_and_missing_local_identity_never_draw(self):
        self.ports[0]['identities'][0]['value']='Gi0/1'
        r=self.result(); self.assertFalse(r['graph']['links'])
        self.assertEqual(r['unbound_neighbors'][0]['reason'],'unmatched_local_interface')
        self.ports[0]['identities'][0]['value']='GigabitEthernet0/1'
        self.ports.append(dict(copy.deepcopy(self.ports[0]),id='ambiguous'))
        self.assertEqual(self.result()['unbound_neighbors'][0]['reason'],'ambiguous_local_interface')
        del self.observation['parsed']['interfaces']['GigabitEthernet0/1']['if_name']
        self.assertEqual(self.result()['unbound_neighbors'][0]['reason'],'incomplete_identity')

    def test_remote_types_are_exact_not_hostname_or_interface_alias_guesses(self):
        self.devices[1]['identities'][0]['kind']='hostname'
        r=self.result(); self.assertFalse(r['graph']['links'])
        self.assertEqual(r['graph']['discovery'][0]['reason'],'unmatched_identity')
        self.devices[1]['identities'][0]['kind']='chassis_id'
        self.ports[1]['identities'].pop()
        self.assertEqual(self.result()['graph']['discovery'][0]['reason'],'unmatched_port')

    def test_reciprocal_unknown_expiry_never_corroborates(self):
        reverse=copy.deepcopy(self.observation)
        reverse.update(id='reverse',device_ref='synthetic-switch')
        reverse['parsed']['interfaces'] = {'GigabitEthernet0/2':{
            'if_name':'GigabitEthernet0/2','port_id':{'GigabitEthernet0/1':{
            'neighbors':{'synthetic-router':dict(chassis_id='synthetic-router',
                port_id='GigabitEthernet0/1',neighbor_id='synthetic-router')}}}}}
        r=self.result([self.observation,reverse]); g=r['graph']
        self.assertEqual(len(g['links']),1); self.assertEqual(g['links'][0]['certainty'],'unknown')
        self.assertTrue(all(c['expires_at'] is None for c in g['discovery']))
        self.assertEqual(g,self.result([reverse,self.observation])['graph'])

    def test_failed_empty_and_unqualified_captures_keep_distinct_evidence(self):
        self.observation.update(outcome='timeout',sha256=None,capture_outcome_unknown=True)
        g=self.result()['graph']; self.assertFalse(g['links'])
        self.assertTrue(next(c for c in g['coverage'] if c['id']==self.observation['id'])['capture_outcome_unknown'])
        self.observation.update(outcome='observed',sha256='a'*64,parsed={'total_entries':0})
        self.assertEqual(self.result()['normalization']['facts'][0]['value'],0)
        self.observation['parsed']={}
        self.assertEqual(self.result()['normalization']['facts'][0]['reason'],'normalization_unqualified')

    def test_bounds_duplicates_and_forged_inventory_are_refused(self):
        for rows in ([self.observation]*5,[self.observation,dict(self.observation,id='extra')],
                     [dict(self.observation,command='show interfaces')]):
            with self.assertRaises(ValueError): self.result(rows)
        self.ports[0]['identities'][0]['evidence']['sha256']='c'*64
        with self.assertRaises(ValueError): self.result()


    def test_system_name_and_chassis_format_do_not_create_aliases(self):
        self.row['chassis_id'] = '0011.2233.4455'
        self.assertEqual(self.result()['graph']['discovery'][0]['reason'], 'unmatched_identity')
        del self.row['chassis_id']
        r = self.result()
        self.assertFalse(r['graph']['links'])
        self.assertEqual(r['unbound_neighbors'][0]['reason'], 'incomplete_identity')
        self.assertIsNone(r['unbound_neighbors'][0]['chassis_id_subtype'])


if __name__ == '__main__': unittest.main()
