import copy
from datetime import datetime, timezone
import unittest
from facts_test import facts


class LldpExtractionTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(chassis_id='synthetic-chassis', port_id='GigabitEthernet0/2',
                        neighbor_id='synthetic-switch', system_name='synthetic-switch',
                        time_remaining=110)
        self.observation = dict(id='synthetic-lldp', device_ref='synthetic-router',
            classification='private', command='show lldp neighbors detail',
            started_at='2026-11-22T00:00:00Z', finished_at='2026-11-22T00:00:01Z',
            sha256='a'*64, parser_version='genie.libs.parser-25.2', outcome='observed',
            parsed={'total_entries':1, 'interfaces':{'GigabitEthernet0/1':{
                'if_name':'GigabitEthernet0/1', 'port_id':{'GigabitEthernet0/2':{
                    'neighbors':{'synthetic-switch':self.row}}}}}})

    def result(self):
        return facts.normalize([self.observation], now=datetime(2026,11,22,0,0,2,tzinfo=timezone.utc))

    def test_exact_chassis_not_system_name_and_paths(self):
        before = copy.deepcopy(self.observation)
        result = self.result(); claim = result['neighbor_observations'][0]
        self.assertEqual(claim['remote_claim'], 'synthetic-chassis')
        self.assertEqual(claim['remote_identity_kind'], 'chassis_id')
        self.assertEqual(claim['remote_port_kind'], 'port_id')
        self.assertEqual(claim['protocol'], 'lldp')
        for field, path in claim['field_paths'].items():
            value = self.observation['parsed']
            for key in path: value = value[key]
            self.assertEqual(value, claim[field])
        self.assertEqual(claim['started_at'], self.observation['started_at'])
        self.assertEqual(claim['hold_time_seconds'], 110)
        for field in ('expires_at','resolved_device_ref','chassis_id_subtype','port_id_subtype'):
            self.assertIsNone(claim[field])
        self.assertFalse(result['hosted_eligible']); self.assertEqual(result['links'], [])
        self.assertEqual(before, self.observation)

    def test_missing_unsafe_chassis_never_falls_back_to_name(self):
        for value in (None, '', 'x'*129, 'switch\nother', 7):
            self.row['chassis_id'] = value
            claim = self.result()['neighbor_observations'][0]
            self.assertIsNone(claim['remote_claim'])
            self.assertEqual(claim['reason'], 'incomplete_identity')
            self.assertEqual(claim['certainty'], 'unknown')

    def test_count_mismatch_duplicate_collapse_and_malformed_shapes_unknown(self):
        good = copy.deepcopy(self.observation['parsed'])
        for parsed in ({}, {'total_entries':True}, {'total_entries':1,'interfaces':[]},
                       {**good,'total_entries':2}, {'total_entries':0,'interfaces':{'x':{}}}):
            self.observation['parsed'] = parsed
            result = self.result()
            self.assertEqual(result['neighbor_observations'], [])
            self.assertEqual(result['facts'][0]['reason'], 'normalization_unqualified')

    def test_empty_and_failure_are_distinct(self):
        self.observation['parsed'] = {'total_entries':0}
        self.assertEqual(self.result()['facts'][0]['value'], 0)
        self.observation['outcome'] = 'parse_failed'
        self.assertEqual(self.result()['facts'][0]['outcome'], 'parse_failed')

    def test_no_expiry_or_subtype_inference(self):
        for value in (None, True, -1, '110', 110, 65536):
            self.row['time_remaining'] = value
            claim = self.result()['neighbor_observations'][0]
            self.assertIsNone(claim['expires_at'])
            self.assertEqual(claim['hold_time_seconds'], 110 if type(value) is int and value == 110 else None)

    def test_count_limit_is_refused(self):
        self.observation['parsed'] = {'total_entries':257}
        with self.assertRaisesRegex(ValueError, 'neighbor_limit'): self.result()

    def test_oversized_containers_cannot_hide_behind_zero_count(self):
        self.observation['parsed'] = {'total_entries':0,
            'interfaces':{str(i):{'port_id':{}} for i in range(257)}}
        with self.assertRaisesRegex(ValueError, 'neighbor_limit'): self.result()

    def test_conflicting_nested_identity_is_not_bound(self):
        self.row['port_id'] = 'different-port'
        self.assertEqual(self.result()['facts'][0]['reason'], 'normalization_unqualified')

    def test_missing_local_field_and_parser_placeholder_unknown(self):
        local = self.observation['parsed']['interfaces']['GigabitEthernet0/1']
        del local['if_name']
        claim = self.result()['neighbor_observations'][0]
        self.assertIsNone(claim['local_interface'])
        self.assertNotIn('local_interface', claim['field_paths'])
        self.assertEqual(claim['certainty'], 'unknown')
        self.observation['parsed']['interfaces'] = {'N/A':{**local,'if_name':'N/A'}}
        self.assertIsNone(self.result()['neighbor_observations'][0]['local_interface'])

    def test_missing_chassis_does_not_use_not_advertised_name(self):
        del self.row['chassis_id']
        self.row['system_name'] = 'not advertised'
        claim = self.result()['neighbor_observations'][0]
        self.assertIsNone(claim['remote_claim'])
        self.assertNotIn('remote_claim', claim['field_paths'])
        self.assertEqual(claim['reason'], 'incomplete_identity')


if __name__ == '__main__': unittest.main()
