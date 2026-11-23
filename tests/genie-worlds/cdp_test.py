import copy
from datetime import datetime, timezone
import unittest
from facts_test import facts


class CdpExtractionTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(device_id='synthetic-switch', local_interface='GigabitEthernet0/1',
                        port_id='GigabitEthernet0/2', hold_time=120)
        self.observation = dict(id='synthetic-cdp', device_ref='synthetic-router',
            classification='private', command='show cdp neighbors detail',
            started_at='2026-11-22T00:00:00Z', finished_at='2026-11-22T00:00:01Z',
            sha256='a'*64, parser_version='genie.libs.parser-25.2', outcome='observed',
            parsed={'total_entries_displayed':1, 'index':{'1':self.row}})

    def result(self):
        return facts.normalize([self.observation], profile='detailed',
            now=datetime(2026,11,22,0,0,2,tzinfo=timezone.utc))

    def test_exact_claim_paths_interval_and_no_invented_binding_or_expiry(self):
        before=copy.deepcopy(self.observation)
        r=self.result(); c=r['neighbor_observations'][0]
        self.assertEqual(c['remote_claim'],'synthetic-switch')
        self.assertEqual(c['remote_identity_kind'],'cdp_device_id')
        self.assertEqual(c['source_path'],['index','1'])
        self.assertEqual(c['field_paths']['remote_port'],['index','1','port_id'])
        self.assertEqual(c['started_at'],self.observation['started_at'])
        self.assertEqual(c['hold_time_seconds'],120)
        self.assertIsNone(c['expires_at']); self.assertIsNone(c['resolved_device_ref'])
        self.assertEqual(r['links'],[]); self.assertFalse(r['hosted_eligible'])
        self.assertEqual(before,self.observation)

    def test_missing_or_unsafe_identity_stays_unknown_without_lossy_matching(self):
        for value in (None, '', 'x'*129, 'switch\nother', 7):
            with self.subTest(value=value):
                self.row['device_id']=value
                c=self.result()['neighbor_observations'][0]
                self.assertIsNone(c['remote_claim'])
                self.assertEqual(c['certainty'],'unknown')
                self.assertEqual(c['reason'],'incomplete_identity')

    def test_holdtime_never_establishes_qualified_expiry(self):
        for value in (None,True,-1,'120',120):
            self.row['hold_time']=value
            c=self.result()['neighbor_observations'][0]
            self.assertEqual(c['hold_time_seconds'],120 if type(value) is int and value==120 else None)
            self.assertIsNone(c['expires_at'])

    def test_unrecognized_or_truncated_shape_is_unknown_not_empty(self):
        for parsed in ({}, {'index':[]}, {'total_entries_displayed':2,'index':{'1':self.row}},
                       {'total_entries_displayed':True,'index':{'1':self.row}}):
            self.observation['parsed']=parsed
            r=self.result(); self.assertEqual(r['neighbor_observations'],[])
            self.assertEqual(r['facts'][0]['reason'],'normalization_unqualified')

    def test_empty_and_failure_remain_distinct(self):
        self.observation['parsed']={'total_entries_displayed':0}
        r=self.result(); self.assertEqual(r['facts'][0]['value'],0)
        self.observation['outcome']='parse_failed'
        self.assertEqual(self.result()['facts'][0]['outcome'],'parse_failed')

    def test_limit_is_refused_not_silently_truncated(self):
        self.observation['parsed']={'total_entries_displayed':257,
                                   'index':{str(i):self.row for i in range(257)}}
        with self.assertRaisesRegex(ValueError,'neighbor_limit'): self.result()


if __name__ == '__main__': unittest.main()
