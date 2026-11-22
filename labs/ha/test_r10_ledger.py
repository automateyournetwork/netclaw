import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(__file__))
import r10_ledger as L


class Ledger(unittest.TestCase):
    def setUp(self):
        self.f = os.path.join(tempfile.mkdtemp(), 'l.json')

    def run_(self, *a, now=0.0):
        return L.main(['--file', self.f, '--now', str(now), *a])

    def test_accounting_and_stop(self):
        self.assertEqual(self.run_('start', 'p', 'vm1', '1.0', now=0), 0)
        d = L.load(self.f)
        self.assertAlmostEqual(L.total(d, 3600), 1.0)
        self.run_('stop', 'p', 'vm1', now=7200)
        self.assertAlmostEqual(L.total(L.load(self.f), 99999), 2.0)

    def test_pause_then_approval(self):
        self.assertEqual(self.run_('start', 'p', 'a', '10.0', now=0), 0)
        # 10 h elapsed => $100 est would exceed; use 1.4h: total 14 + burn 10 + new => over pause
        self.assertEqual(self.run_('start', 'p', 'b', '1.0', now=5040), 3)  # paused
        self.run_('approve-over-pause')
        self.assertEqual(self.run_('start', 'p', 'b', '1.0', now=5040), 3 if 14 + 10 + 1 >= 25 else 0)

    def test_hard_ceiling_ignores_approval(self):
        self.run_('approve-over-pause')
        self.assertEqual(self.run_('start', 'p', 'big', '30.0', now=0), 3)

    def test_ledger_is_private(self):
        self.run_('start', 'p', 'vm', '0.1', now=0)
        self.assertEqual(oct(os.stat(self.f).st_mode & 0o777), '0o600')

    def test_invalid_rates_are_refused(self):
        for value in ('-1', 'nan', 'inf', '0'):
            self.assertEqual(self.run_('start', 'p', 'bad', value), 3)

    def test_full_duration_and_fixed_costs_are_counted(self):
        self.assertEqual(self.run_('charge', 'all', 'provider-and-transfer-reserve', '5'), 0)
        self.assertEqual(self.run_('start', 'p', 'a', '1', '--hours', '8'), 0)
        self.assertEqual(self.run_('start', 'p', 'b', '1', '--hours', '8'), 3)

    def test_duplicate_open_entry_refused(self):
        self.assertEqual(self.run_('start', 'p', 'a', '.1'), 0)
        self.assertEqual(self.run_('start', 'p', 'a', '.1'), 3)


if __name__ == '__main__':
    unittest.main()
