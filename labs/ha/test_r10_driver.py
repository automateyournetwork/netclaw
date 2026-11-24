import os, re, subprocess, sys, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def drv(*a, env=None):
    e = dict(os.environ, **(env or {}))
    r = subprocess.run(['bash', os.path.join(ROOT, 'scripts', 'ha-cloud.sh'), *a, '--dry-run'], capture_output=True, text=True, env=e)
    return r.returncode, r.stdout, r.stderr


class Driver(unittest.TestCase):
    def test_azure_up_tags_and_nsg(self):
        rc, out, _ = drv('azure', 'up', 'p3-ha', 'ew1', '-', 'Standard_B2s', env={'R10_SSH_ALLOW_CIDR': '203.0.113.7/32'})
        self.assertEqual(rc, 0)
        self.assertIn('--location westeurope', out)
        self.assertIn('netclaw-spec=198', out); self.assertIn('phase=p3-ha', out)
        self.assertIn('--source-address-prefixes 203.0.113.7/32', out)
        self.assertNotIn('--source-address-prefixes \\*', out)       # SSH/443 never open to the world
        self.assertIn('10.198.2.0/24', out)
        self.assertNotIn('bastion', out.lower())

    def test_azure_peer_is_full_mesh(self):
        rc, out, _ = drv('azure', 'peer', 'p3-ha', 'nne1', 'ew1', 'ase1')
        self.assertEqual(out.count('peering create'), 6)

    def test_explicit_region_substitution_and_federation_ingress(self):
        rc, out, _ = drv('azure', 'up', 'p3-ha', 'ew1', '-', 'Standard_D2als_v7',
                         env={'R10_AZ_REGION_EW1': 'eastus2', 'R10_SSH_ALLOW_CIDR': '203.0.113.7/32'})
        self.assertEqual(rc, 0)
        self.assertIn('--location eastus2', out)
        self.assertNotIn('--source-address-prefixes Internet', out)

    def test_down_deletes_group_and_verifies(self):
        rc, out, _ = drv('azure', 'down', 'p3-ha')
        self.assertIn('az group delete --name rg-nc198-p3-ha --yes', out)

    def test_gcp_matches_r09_commands(self):
        rc, out, _ = drv('gcp', 'ssh', 'x', 'nne1', 'uptime')
        self.assertIn('--zone=northamerica-northeast1-b', out); self.assertIn('--tunnel-through-iap', out)
        self.assertIn('--project=netclaw-506315', out); self.assertIn('nc182-border-nne1', out)

    def test_unknown_provider_and_verb_fail(self):
        self.assertNotEqual(drv('aws', 'up')[0], 0)
        self.assertNotEqual(drv('azure', 'explode')[0], 0)

    def test_no_secret_material_in_any_driver_script(self):
        for f in ('ha-cloud.sh', 'ha-cloud-azure.sh', 'ha-cloud-gcp.sh', 'ha-r10-place-provider-key.sh'):
            text = open(os.path.join(ROOT, 'scripts', f)).read()
            self.assertIsNone(re.search(r'sk-ant-|nbt_[A-Za-z0-9]|AKIA', text), f)

    def test_phase_runner_refuses_without_go(self):
        r = subprocess.run(['bash', os.path.join(ROOT, 'scripts', 'ha-r10-phase.sh'), 'up', 'p2-single', 'nne1'],
                           capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != 'R10_GO'})
        self.assertEqual(r.returncode, 4)


if __name__ == '__main__':
    unittest.main()
