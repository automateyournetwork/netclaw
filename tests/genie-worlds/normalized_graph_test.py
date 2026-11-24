import copy
import json
import subprocess
import unittest
import interfaces_test
facts = interfaces_test.facts
from graph_bridge_test import NODE


class NormalizedGraphTests(unittest.TestCase):
    def setUp(self):
        fixture = interfaces_test.InterfaceExtractionTests(); fixture.setUp()
        self.name = fixture.name
        self.first = copy.deepcopy(fixture.observation)
        self.first.update(source='synthetic-parser', sample_index=1)
        self.second = copy.deepcopy(self.first)
        self.second.update(id='second', sample_index=2, started_at='2026-11-22T00:00:12Z',
                           finished_at='2026-11-22T00:00:13Z', sha256='c'*64)
        self.second['parsed'][self.name]['counters']['in_octets'] += 100
        self.inventory = dict(id='inventory', device_ref='synthetic-router',
            source='synthetic-inventory', command='inventory', parser_version='fixture',
            outcome='observed', sha256='a'*64, started_at='2026-11-22T00:00:00Z',
            finished_at='2026-11-22T00:00:00Z')
        proof = dict(self.inventory, observation_id='inventory', source_path=['identity'])
        self.devices = [dict(id='synthetic-router', label='Synthetic router', role='router',
            identities=[dict(kind='hostname', value='Synthetic router', evidence=proof)])]
        self.ports = [dict(id='port-a', device_id='synthetic-router', label=self.name,
            status='unknown', identities=[dict(kind='interface_name', value=self.name, evidence=proof)])]

    def result(self, observations=None):
        return facts.interface_counter_graph(self.devices, self.ports,
            observations if observations is not None else [self.first, self.second],
            [self.inventory], graph_id='synthetic-normalized', now='2026-11-22T00:00:15Z')

    def test_parser_to_graph_to_actual_js_inspector(self):
        before=copy.deepcopy([self.first,self.second,self.ports])
        result=self.result(); g=result['graph']
        self.assertEqual(len(g['counters']),4)
        row=next(c for c in g['counters'] if c['field']=='in_octets')
        self.assertEqual([s['value'] for s in row['observed_samples']], [str(2**63+17),str(2**63+117)])
        self.assertIsNone(row['value']); self.assertIsNone(row['observed_samples'][0]['sampled_at'])
        self.assertEqual(g['interfaces'][0]['status'],'unknown')
        self.assertEqual(g['links'],[]); self.assertFalse(result['hosted_eligible'])
        self.assertEqual(before,[self.first,self.second,self.ports])
        code="""import fs from 'node:fs';import {localGraph} from './scripts/genie-worlds/viewer/network-graph.mjs';import {selectionDetails} from './scripts/genie-worlds/viewer/selection.mjs';const g=localGraph(JSON.parse(fs.readFileSync(0,'utf8')));const d=selectionDetails(g,'port-a');if(!Object.isFrozen(g)||!d.rows.some(([k,v])=>v.includes('9223372036854775825 bytes')))throw Error('raw counter missing');"""
        p=subprocess.run([NODE,'--input-type=module','-e',code],input=json.dumps(g),text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)

    def test_exact_alias_only_and_ambiguity_retained(self):
        self.ports[0]['identities'][0]['value']='Gi0/1'
        result=self.result(); self.assertEqual(result['graph']['counters'],[])
        self.assertEqual({r['reason'] for r in result['unbound_interfaces']},{'unmatched_interface'})
        self.ports[0]['identities'][0]['value']=self.name
        self.ports.append(dict(copy.deepcopy(self.ports[0]),id='port-b'))
        self.assertEqual({r['reason'] for r in self.result()['unbound_interfaces']},{'ambiguous_interface'})

    def test_missing_fields_have_no_invented_proof_path(self):
        self.first['parsed'][self.name]['counters'].pop('in_octets')
        row=next(c for c in self.result()['graph']['counters'] if c['field']=='in_octets')
        self.assertEqual([s['slot'] for s in row['observed_samples']],['second'])
        self.assertIsNone(row['value'])
        self.first['parsed'][self.name]['counters']['in_octets']=-1
        row=next(c for c in self.result()['graph']['counters'] if c['field']=='in_octets')
        self.assertIsNone(row['observed_samples'][0]['value'])

    def test_sample_slots_are_explicit_unique_and_not_order_inferred(self):
        self.assertEqual(self.result()['graph'],self.result([self.second,self.first])['graph'])
        self.first.pop('sample_index')
        result=self.result(); self.assertEqual(result['unbound_interfaces'][0]['reason'],'sample_slot_unknown')
        self.first['sample_index']=2
        with self.assertRaisesRegex(ValueError,'duplicate_interface_sample'):self.result()

    def test_foreign_forged_catalog_or_identity_is_refused(self):
        self.ports[0]['identities'][0]['evidence']['sha256']='f'*64
        with self.assertRaises(ValueError):self.result()

    def test_failed_capture_keeps_coverage_without_sample(self):
        self.second.update(outcome='timeout',sha256=None,capture_outcome_unknown=True)
        result=self.result(); self.assertEqual(len(result['graph']['counters']),4)
        self.assertTrue(all(len(c['observed_samples'])==1 for c in result['graph']['counters']))
        self.assertTrue(next(c for c in result['graph']['coverage'] if c['id']=='second')['capture_outcome_unknown'])

    def test_read_bounds_and_noninterface_inputs_are_refused(self):
        third=dict(self.second,id='third')
        with self.assertRaisesRegex(ValueError,'interface_sample_limit'):
            self.result([self.first,self.second,third])
        with self.assertRaisesRegex(ValueError,'interface_observations_required'):
            self.result([dict(self.first,command='show cdp neighbors detail')])

    def test_all_missing_values_stay_unknown_without_fabricated_paths(self):
        for source in (self.first,self.second):source['parsed'][self.name].pop('counters')
        g=self.result()['graph']
        self.assertTrue(all(c['observed_samples']==[] and c['value'] is None for c in g['counters']))
        code="import fs from 'node:fs';import {localGraph} from './scripts/genie-worlds/viewer/network-graph.mjs';localGraph(JSON.parse(fs.readFileSync(0,'utf8')));"
        p=subprocess.run([NODE,'--input-type=module','-e',code],input=json.dumps(g),text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)


if __name__ == '__main__': unittest.main()
