import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('facts', Path(__file__).resolve().parents[2] / 'scripts/genie-worlds/facts.py')
facts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(facts)


class CounterTests(unittest.TestCase):
    def setUp(self):
        self.proof = dict(observation_id='proof', source='synthetic-fixture', command='fixture',
                          parser_version='fixture-v1', sha256='a'*64, source_path=['counter'])
        self.first = dict(id='s1', classification='private', device_id='fixture-router',
                          interface_id='fixture-port', incarnation='boot-and-counter-epoch',
                          field='in_octets', direction='in', units='bytes', width=64,
                          value=str(2**63), outcome='observed',
                          started_at='2026-11-22T00:00:00Z', sampled_at='2026-11-22T00:00:01Z',
                          finished_at='2026-11-22T00:00:02Z', evidence={**self.proof, 'observation_id':'o1'})
        self.second = {**self.first, 'id':'s2', 'value':str(2**63+1000),
                       'started_at':'2026-11-22T00:00:10Z', 'sampled_at':'2026-11-22T00:00:11Z',
                       'finished_at':'2026-11-22T00:00:12Z', 'evidence':{**self.proof, 'observation_id':'o2'}}
        self.continuity = dict(sample_ids=['s1','s2'], verdict='verified_no_reset_or_wrap', evidence=self.proof)
        self.capacity = dict(device_id='fixture-router', interface_id='fixture-port',
                             incarnation='boot-and-counter-epoch', direction='in', units='bits/s',
                             value='8000', sample_ids=['s1','s2'], evidence=self.proof)

    def rate(self):
        return facts.counter_rate(self.first, self.second, self.continuity, self.capacity)

    def test_precise_64bit_delta_provenance_and_directional_utilization(self):
        original = copy.deepcopy((self.first,self.second,self.continuity,self.capacity))
        r = self.rate()
        self.assertEqual((r['delta'],r['value'],r['utilization_percent']),('1000',100,10))
        self.assertFalse(r['hosted_eligible'])
        self.assertEqual(r['sample_ids'],['s1','s2'])
        self.assertEqual(len(r['evidence']),2)
        self.assertEqual(r['capacity']['value'],'8000')
        self.assertEqual(r['sample_intervals'][0]['sampled_at'],self.first['sampled_at'])
        self.assertEqual(original,(self.first,self.second,self.continuity,self.capacity))

    def test_matching_incarnation_alone_is_not_continuity(self):
        r = facts.counter_rate(self.first,self.second)
        self.assertEqual(r['reason'],'continuity_unverified'); self.assertIsNone(r['value'])

    def test_continuity_is_bound_to_pair_and_provenance(self):
        for change in ({'sample_ids':['other','s2']},{'evidence':{}},{'verdict':'reset'}):
            with self.subTest(change=change):
                r=facts.counter_rate(self.first,self.second,{**self.continuity,**change})
                self.assertIsNone(r['value'])

    def test_missing_unavailable_and_reset_never_zero(self):
        self.assertIsNone(facts.counter_rate(None,self.second)['value'])
        for change in ({'value':None},{'outcome':'timeout'},{'value':'1'},{'incarnation':'new-boot'}):
            with self.subTest(change=change):
                self.assertIsNone(facts.counter_rate(self.first,{**self.second,**change},self.continuity)['value'])

    def test_valid_unchanged_counter_can_be_zero(self):
        self.second['value']=self.first['value']
        self.assertEqual(self.rate()['value'],0)

    def test_width_and_integer_validation(self):
        for value in (True,1,1.5,'-1','01','nan',str(2**64)):
            with self.subTest(value=value):
                self.second['value']=value; self.assertIsNone(self.rate()['value'])
        self.second['value']='100'; self.second['width']=32
        self.assertIsNone(self.rate()['value'])

    def test_duplicate_different_port_or_direction_is_not_pair(self):
        for change in ({'id':'s1'},{'interface_id':'other'},{'direction':'out'},
                       {'evidence':self.first['evidence']},{'device_id':'other'}):
            with self.subTest(change=change):
                self.assertIsNone(facts.counter_rate(self.first,{**self.second,**change},self.continuity)['value'])

    def test_bad_overlapping_or_reversed_intervals(self):
        for change in ({'sampled_at':'2026-11-22T00:00:11'},
                       {'started_at':'2026-11-22T00:00:01Z'},
                       {'sampled_at':'2026-11-22T00:00:01Z'},
                       {'finished_at':'2026-11-22T00:00:09Z'},
                       {'sampled_at':'2026-13-22T00:00:11Z'}):
            with self.subTest(change=change):
                self.assertIsNone(facts.counter_rate(self.first,{**self.second,**change},self.continuity)['value'])

    def test_capacity_is_optional_and_requires_evidence_and_pair(self):
        r=facts.counter_rate(self.first,self.second,self.continuity)
        self.assertEqual(r['value'],100); self.assertIsNone(r['utilization_percent'])
        for change in ({'value':'0'},{'value':True},{'evidence':{}},{'direction':'out'},
                       {'sample_ids':['s1','other']},{'incarnation':'other'}):
            with self.subTest(change=change):
                self.assertIsNone(facts.counter_rate(self.first,self.second,self.continuity,
                                                     {**self.capacity,**change})['utilization_percent'])

    def test_capacity_conflict_not_clamped(self):
        self.capacity['value']='1'
        self.assertEqual(self.rate()['utilization_reason'],'capacity_conflict')
        self.assertIsNone(self.rate()['utilization_percent'])

    def test_packet_rate_is_not_bit_utilization(self):
        self.first['units']=self.second['units']='packets'
        self.assertEqual(self.rate()['units'],'packets/s')
        self.assertEqual(self.rate()['utilization_reason'],'counter_not_bytes')

    def test_raw_payload_does_not_escape_via_provenance(self):
        self.first['evidence']['raw']='must-stay-local-and-out-of-rate-record'
        r=self.rate()
        self.assertNotIn('raw',r['evidence'][0])
        r['evidence'][0]['source_path'].append('mutated-copy')
        self.assertEqual(self.first['evidence']['source_path'],['counter'])


if __name__ == '__main__': unittest.main()
