import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('facts', Path(__file__).resolve().parents[2] / 'scripts/genie-worlds/facts.py')
facts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(facts)


def proof(name, device=None, protocol='lldp'):
    return dict(observation_id=name, device_ref=device or name[0], outcome='observed', source='synthetic-test', command='show '+protocol+' neighbors detail',
                parser_version='fixture', sha256='a'*64, source_path=['interfaces', name])


class NeighborsTests(unittest.TestCase):
    def setUp(self):
        self.devices = [dict(id=x, identities=[dict(kind='chassis_id', value=x, evidence=proof(x))]) for x in ('a', 'b', 'c')]
        self.ports = [dict(id=x+'1', device_id=x, identities=[dict(kind='interface_name', value='Ethernet1', evidence=proof(x+'1'))]) for x in ('a', 'b', 'c')]

    def claim(self, src='a', dst='b', name='ab', protocol='lldp'):
        return dict(id=name, device_id=src, local_interface_id=src+'1', protocol=protocol,
                    remote_identities=[dict(kind='chassis_id', value=dst)],
                    remote_port=dict(kind='interface_name', value='Ethernet1'),
                    started_at='2026-11-22T12:00:00Z', finished_at='2026-11-22T12:00:01Z',
                    expires_at='2026-11-22T12:02:00Z', evidence=proof(name, src, protocol))

    def run_claims(self, claims, now='2026-11-22T12:00:10Z'):
        return facts.resolve_neighbors(self.devices, self.ports, claims, now=now)

    def test_one_sided_and_reverse_corroboration(self):
        self.assertEqual(self.run_claims([self.claim()])['links'][0]['certainty'], 'one_sided')
        result = self.run_claims([self.claim(), self.claim('b', 'a', 'ba')])
        self.assertEqual(result['links'][0]['certainty'], 'corroborated')
        self.assertEqual(result['links'][0]['status'], 'unknown')
        self.assertFalse(result['hosted_eligible'])
        self.assertEqual(len(result['neighbor_observations'][0]['identity_evidence']), 3)

    def test_two_protocols_in_same_direction_are_not_reverse_evidence(self):
        self.assertEqual(self.run_claims([self.claim(), self.claim(name='cdp', protocol='cdp')])['links'][0]['certainty'], 'one_sided')

    def test_no_name_truncation_case_fold_or_alias_guess(self):
        for remote in ('A', 'a.example', 'a-short'):
            result = self.run_claims([self.claim(dst=remote)])
            self.assertEqual(result['links'], [])
            self.assertEqual(result['neighbor_observations'][0]['reason'], 'unmatched_identity')

    def test_ambiguous_and_disagreeing_identity_stay_unresolved(self):
        self.devices[2]['identities'] = copy.deepcopy(self.devices[1]['identities'])
        self.devices[2]['identities'][0]['evidence']['device_ref'] = 'c'
        self.assertEqual(self.run_claims([self.claim()])['neighbor_observations'][0]['reason'], 'ambiguous_identity')
        self.devices[2]['identities'][0]['value'] = 'c'
        claim = self.claim(); claim['remote_identities'].append(dict(kind='chassis_id', value='c'))
        result = self.run_claims([claim])
        self.assertEqual(result['links'], [])
        self.assertEqual(result['neighbor_observations'][0]['reason'], 'conflicting_identity')

    def test_unmatched_port_and_self_claim_do_not_make_edges(self):
        claim = self.claim(); claim['remote_port']['value'] = 'Eth1'
        self.assertEqual(self.run_claims([claim])['links'], [])
        self.assertEqual(self.run_claims([self.claim(dst='a')])['neighbor_observations'][0]['reason'], 'self_neighbor')

    def test_competing_peers_preserved_as_conflict(self):
        result = self.run_claims([self.claim(), self.claim('a', 'c', 'ac')])
        self.assertEqual(len(result['links']), 2)
        self.assertTrue(all(x['certainty'] == 'conflict' for x in result['links']))

    def test_expiry_staleness_and_missing_expiry_prevent_corroboration(self):
        claims = [self.claim(), self.claim('b', 'a', 'ba')]
        for now in ('2026-11-22T12:02:00Z', '2026-11-22T12:06:00Z'):
            result = self.run_claims(claims, now)
            self.assertEqual(result['links'][0]['certainty'], 'unknown')
            self.assertTrue(result['neighbor_observations'][0]['expired'])
        claims[0]['expires_at'] = None
        self.assertEqual(self.run_claims(claims)['links'][0]['certainty'], 'one_sided')

    def test_nonoverlapping_validity_does_not_corroborate(self):
        claims = [self.claim(), self.claim('b', 'a', 'ba')]
        claims[1].update(started_at='2026-11-22T12:03:00Z', finished_at='2026-11-22T12:03:01Z', expires_at='2026-11-22T12:04:00Z')
        self.assertNotEqual(self.run_claims(claims, '2026-11-22T12:03:10Z')['links'][0]['certainty'], 'corroborated')

    def test_determinism_no_input_mutation_and_no_raw_passthrough(self):
        claims = [self.claim(), self.claim('b', 'a', 'ba')]; before = copy.deepcopy(claims)
        first = self.run_claims(claims)
        self.assertEqual(claims, before)
        self.assertEqual(first, self.run_claims(list(reversed(claims))))
        claims[0]['evidence']['raw'] = 'not propagated'
        self.assertNotIn('not propagated', str(self.run_claims(claims)))

    def test_bad_provenance_ids_intervals_and_bounds_refused(self):
        for key, value in [('evidence', {}), ('local_interface_id', 'b1'), ('finished_at', '2026-11-22T12:10:00Z')]:
            claim = self.claim(); claim[key] = value
            with self.assertRaises(ValueError): self.run_claims([claim])
        with self.assertRaises(ValueError): self.run_claims([self.claim(), self.claim()])
        with self.assertRaises(ValueError): self.run_claims([self.claim()] * 257)

    def test_source_binding_and_independent_reverse_observation_required(self):
        claim = self.claim(); claim['evidence']['device_ref'] = 'b'
        with self.assertRaises(ValueError): self.run_claims([claim])
        claim = self.claim(); claim['evidence']['outcome'] = 'parse_failed'
        with self.assertRaises(ValueError): self.run_claims([claim])
        claim = self.claim(); claim['evidence']['command'] = 'show version'
        with self.assertRaises(ValueError): self.run_claims([claim])
        claims = [self.claim(), self.claim('b', 'a', 'ba')]
        claims[1]['evidence']['observation_id'] = claims[0]['evidence']['observation_id']
        self.assertEqual(self.run_claims(claims)['links'][0]['certainty'], 'one_sided')


if __name__ == '__main__': unittest.main()
