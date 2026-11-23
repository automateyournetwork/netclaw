import copy
import unittest
from datetime import datetime, timezone
from facts_test import facts


class InterfaceExtractionTests(unittest.TestCase):
    def setUp(self):
        self.name = 'GigabitEthernet0/1'
        self.row = dict(enabled=True, oper_status='up', line_protocol='up',
                        counters=dict(in_octets=2**63+17, out_octets=0, in_pkts=5, out_pkts=0),
                        description='unpropagated', bandwidth=1000000)
        self.observation = dict(id='synthetic-interfaces', device_ref='synthetic-router',
            classification='private', command='show interfaces',
            started_at='2026-11-22T00:00:00Z', finished_at='2026-11-22T00:00:01Z',
            sha256='b'*64, parser_version='genie.libs.parser-25.2', outcome='observed',
            parsed={self.name:self.row})

    def result(self):
        return facts.normalize([self.observation], profile='detailed',
            now=datetime(2026,11,22,0,0,2,tzinfo=timezone.utc))

    def test_exact_counters_provenance_and_unknown_derivation_inputs(self):
        before=copy.deepcopy(self.observation)
        r=self.result(); row=r['interface_observations'][0]
        self.assertEqual(row['interface_name'],self.name)
        self.assertIsNone(row['resolved_interface_id'])
        self.assertEqual(row['started_at'],self.observation['started_at'])
        counters={c['field']:c for c in row['counter_samples']}
        self.assertEqual(counters['in_octets']['value'],str(2**63+17))
        self.assertEqual(counters['out_octets']['value'],'0')
        for c in counters.values():
            self.assertEqual(c['source_path'],[self.name,'counters',c['field']])
            for field in ('sampled_at','width','incarnation'): self.assertIsNone(c[field])
        self.assertNotIn('bandwidth',row); self.assertNotIn('description',row)
        self.assertFalse(r['hosted_eligible']); self.assertEqual(r['links'],[])
        self.assertEqual(before,self.observation)

    def test_missing_and_invalid_counters_are_not_zero(self):
        for value in (None,True,-1,1.5,'12',2**64):
            self.row['counters']['in_octets']=value
            c=self.result()['interface_observations'][0]['counter_samples'][0]
            self.assertIsNone(c['value']); self.assertEqual(c['reason'],'invalid_counter')
        self.row.pop('counters')
        for c in self.result()['interface_observations'][0]['counter_samples']:
            self.assertIsNone(c['value']); self.assertEqual(c['reason'],'field_missing')
            self.assertIsNone(c['source_path'])

    def test_state_fields_remain_separate_and_unknown_is_explicit(self):
        self.row.update(enabled=False, oper_status='down', line_protocol='up')
        state=self.result()['interface_observations'][0]['state']
        self.assertIs(state['enabled']['value'],False)
        self.assertEqual(state['oper_status']['value'],'down')
        self.assertEqual(state['line_protocol']['value'],'up')
        self.row.update(enabled='true',oper_status='unexpected')
        self.row.pop('line_protocol')
        state=self.result()['interface_observations'][0]['state']
        self.assertTrue(all(s['value'] is None for s in state.values()))

    def test_unqualified_shapes_names_and_failures(self):
        for parsed in ({},{'interface':{}},{'bad\nname':self.row},{self.name:[]},
                       {'x'*129:self.row},{self.name:{'description':'only'}},
                       {self.name:{'counters':[]}}):
            self.observation['parsed']=parsed
            r=self.result(); self.assertEqual(r['interface_observations'],[])
            self.assertEqual(r['facts'][0]['reason'],'normalization_unqualified')
        self.observation['outcome']='parse_failed'
        self.assertEqual(self.result()['facts'][0]['outcome'],'parse_failed')

    def test_size_limit_refuses_instead_of_truncating(self):
        self.observation['parsed']={f'GigabitEthernet0/{i}':self.row for i in range(257)}
        with self.assertRaisesRegex(ValueError,'interface_limit'): self.result()


if __name__ == '__main__': unittest.main()
