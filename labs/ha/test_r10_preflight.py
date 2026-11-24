import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(__file__))
import r10_preflight as P

OK_SKU = [{'name': 'Standard_B2s', 'family': 'standardBSFamily', 'restrictions': []}]
RESTRICTED = [{'name': 'Standard_B2s', 'family': 'standardBSFamily', 'restrictions': [{'type': 'Location', 'reasonCode': 'NotAvailableForSubscription'}]}]
USAGE_OK = [{'name': {'value': 'cores'}, 'currentValue': 0, 'limit': 10}, {'name': {'value': 'standardBSFamily'}, 'currentValue': 0, 'limit': 6}]
USAGE_LOW = [{'name': {'value': 'cores'}, 'currentValue': 0, 'limit': 10}, {'name': {'value': 'standardBSFamily'}, 'currentValue': 0, 'limit': 1}]


class Preflight(unittest.TestCase):
    def rep(self, state, skus, usage, budgets=None):
        per = {'r': ({'Standard_B2s': skus}, usage)}
        return P.build(['r'], {'state': state}, per, budgets, {'godaddy': True, 'anthropic': True, 'netbox': True})

    def test_all_go(self):
        r = self.rep('Enabled', OK_SKU, USAGE_OK, [{}])
        self.assertTrue(r['go']); self.assertEqual(r['regions'][0]['size'], 'Standard_B2s'); self.assertEqual(r['budget_alert'], 'present')

    def test_warned_subscription_blocks(self):
        self.assertFalse(self.rep('Warned', OK_SKU, USAGE_OK)['go'])

    def test_restricted_size_blocks_with_reason(self):
        r = self.rep('Enabled', RESTRICTED, USAGE_OK)
        self.assertFalse(r['go']); self.assertIn('restricted', r['regions'][0]['reason'])

    def test_low_quota_blocks(self):
        r = self.rep('Enabled', OK_SKU, USAGE_LOW)
        self.assertFalse(r['go']); self.assertIn('vCPU free', r['regions'][0]['reason'])

    def test_missing_family_or_regional_quota_fails_closed(self):
        self.assertIsNone(P.quota_free(USAGE_OK[:1], 'standardBSFamily'))
        self.assertIsNone(P.quota_free(USAGE_OK[1:], 'standardBSFamily'))

    def test_real_bsv2_zero_quota_is_not_regional_ten(self):
        size = 'Standard_B2ls_v2'
        usage = [USAGE_OK[0], {'name': {'value': 'standardBsv2Family'}, 'limit': 0, 'currentValue': 0}]
        row = P.region_report('canadacentral', {size: [{'name': size, 'family': P.FAMILY[size], 'restrictions': []}]}, usage, sizes=(size,))
        self.assertEqual(row['verdict'], 'blocked')

    def test_family_case_does_not_drop_quota(self):
        self.assertEqual(P.quota_free(USAGE_OK, 'STANDARDBSFAMILY'), 6)

    def test_exact_selected_size_no_fallback(self):
        row = P.region_report('canadacentral', {'Standard_B2s': OK_SKU}, USAGE_OK, sizes=('Standard_D2als_v7',))
        self.assertEqual(row['verdict'], 'blocked')

    def test_secrets_are_booleans_only(self):
        f = os.path.join(tempfile.mkdtemp(), 'env')
        open(f, 'w').write('GODADDY_PAT=abc\nANTHROPIC_API_KEY=\nNETBOX_TOKEN="x"\n')
        s = P.secrets_present(f)
        self.assertEqual(s, {'godaddy': True, 'anthropic': False, 'netbox': True})


if __name__ == '__main__':
    unittest.main()
