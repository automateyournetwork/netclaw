import json, os, subprocess, sys, unittest
sys.path.insert(0, os.path.dirname(__file__))
import r10_watchdog as w
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SCRIPT = os.path.join(ROOT, 'scripts', 'ha-r10-build-group.sh')


def build(step, **env):
    e = dict(os.environ, EV='/nonexistent-r10-ev', R10_ACME_EMAIL='x@example.invalid', R10_GUARD_DIR='/nonexistent-guard',
             AZ_SSH_KEY='/nonexistent-key', R10_SSH_ALLOW_CIDR='203.0.113.9/32', PYTHON_UNUSED='1')
    e.update(env)
    r = subprocess.run(['bash', SCRIPT, '--dry-run', step], capture_output=True, text=True, env=e)
    return r.returncode, r.stdout, r.stderr


class BuildDryRun(unittest.TestCase):
    def test_every_step_prints_and_writes_nothing(self):
        for prov in ('azure', 'gcp'):
            for step in ('plan', 'nodes', 'zone', 'bootstrap', 'prepare', 'dns', 'cert', 'policy-payload', 'image', 'provider',
                         'etcd', 'sandbox', 'authority', 'enroll-members', 'start', 'status'):
                rc, out, err = build(step, PROVIDER=prov, R10_RUN_ID='t-20261115')
                self.assertEqual(rc, 0, (prov, step, err))
                self.assertTrue(out.strip(), (prov, step))
        self.assertFalse(os.path.exists('/nonexistent-r10-ev'))

    def test_admission_default_and_azure_names(self):
        rc, out, _ = build('prepare', PROVIDER='azure', R10_RUN_ID='t-20261115')
        self.assertIn('R10_ADMISSION_MS=4500', out)
        self.assertIn('azca.r10-20261115.azure.internal', out); self.assertIn('--sandbox', out)
        rc, out, _ = build('prepare', PROVIDER='azure', R10_RUN_ID='t-20261115', R10_ADMISSION_MS='6000')
        self.assertIn('R10_ADMISSION_MS=6000', out)

    def test_gcp_uses_zonal_internal_names_and_no_private_zone(self):
        rc, out, _ = build('prepare', PROVIDER='gcp', R10_RUN_ID='t-20261115')
        self.assertIn('.c.netclaw-506315.internal', out); self.assertIn('nc198-gc-ha-nne1', out)
        rc, out, _ = build('zone', PROVIDER='gcp', R10_RUN_ID='t-20261115')
        self.assertNotIn('private-dns', out)

    def test_two_remote_voters_only_in_policy_specs(self):
        rc, out, _ = build('policy-payload', PROVIDER='azure', R10_RUN_ID='t-20261115')
        spec = [l for l in out.splitlines() if l.startswith('+ {"anthropic"')][0]
        self.assertEqual(spec.count(':12379'), 2)

    def test_no_secret_value_in_output(self):
        rc, out, _ = build('cert', PROVIDER='azure', R10_RUN_ID='t-20261115', GODADDY_PAT='SECRETVALUE1',
                           ANTHROPIC_API_KEY='sk-ant-SECRETVALUE2')
        self.assertNotIn('SECRETVALUE', out)
        rc, out, _ = build('provider', PROVIDER='azure', R10_RUN_ID='t-20261115', ANTHROPIC_API_KEY='sk-ant-SECRETVALUE2')
        self.assertNotIn('SECRETVALUE', out)

    def test_public_dns_steps_refuse_without_go(self):
        e = dict(os.environ, PROVIDER='azure', R10_RUN_ID='t-20261115', EV='/nonexistent-r10-ev', R10_ACME_EMAIL='x@example.invalid')
        e.pop('R10_GO_DNS', None)
        for step in ('dns', 'cert'):
            r = subprocess.run(['bash', SCRIPT, step], capture_output=True, text=True, env=e)
            self.assertEqual(r.returncode, 4, step)

    def test_refusals(self):
        self.assertNotEqual(build('plan', PROVIDER='azure', R10_RUN_ID='badid')[0], 0)
        self.assertNotEqual(build('plan', PROVIDER='gcp', R10_RUN_ID='t-20261115', GCP_VM_PREFIX='other')[0], 0)
        self.assertNotEqual(build('nope', PROVIDER='azure', R10_RUN_ID='t-20261115')[0], 0)
        self.assertNotEqual(build('plan', PROVIDER='aws', R10_RUN_ID='t-20261115')[0], 0)


class FakeRun:
    def __init__(self, lists): self.lists, self.calls = lists, []
    def __call__(self, argv, **kw):
        self.calls.append(argv)
        class R: returncode = 0; stdout = ''
        r = R()
        if 'list' in argv:
            r.stdout = json.dumps(self.lists[argv[2]])
        return r


MANIFEST = {'run_id': 'r1', 'deadline_at': 0, 'gcp': {'project': 'p', 'gcloud': '/bin/gcloud', 'firewalls': ['nc198-gc-ha-owner']}}


class GcpWatchdog(unittest.TestCase):
    def test_only_label_verified_nc198_resources_deleted(self):
        ok = {'name': 'nc198-gc-ha-nne1', 'zone': 'https://x/zones/europe-west1-b', 'labels': {'netclaw-spec': '198', 'run-id': 'r1'}}
        other_run = {'name': 'nc198-x', 'zone': 'z/a', 'labels': {'netclaw-spec': '198', 'run-id': 'r2'}}
        foreign = {'name': 'prod-vm', 'zone': 'z/a', 'labels': {'netclaw-spec': '198', 'run-id': 'r1'}}
        fake = FakeRun({'instances': [ok, other_run, foreign], 'addresses': []})
        ev = w.gcp_cleanup(MANIFEST, runner=fake)
        deletes = [c for c in fake.calls if 'delete' in c]
        self.assertEqual([c[4] for c in deletes if c[2] == 'instances'], ['nc198-gc-ha-nne1'])
        self.assertIn('europe-west1-b', deletes[0])
        self.assertEqual(sum('refused' in e for e in ev), 2)
        self.assertTrue(any(c[2] == 'firewall-rules' and c[4] == 'nc198-gc-ha-owner' for c in deletes))

    def test_manifest_validation(self):
        w.validate({'run_id': 'r', 'azure_groups': ['rg-nc198-x']})
        w.validate({'run_id': 'r', 'gcp': {'project': 'p', 'gcloud': '/g'}})
        for bad in ({'run_id': 'r'}, {'run_id': 'r', 'azure_groups': ['rg-other']},
                    {'run_id': 'r', 'gcp': {'project': 'p', 'gcloud': '/g', 'firewalls': ['default-allow-ssh']}},
                    {'run_id': 'r', 'gcp': {'gcloud': '/g'}}, {'azure_groups': ['rg-nc198-x']}):
            with self.assertRaises(SystemExit): w.validate(bad)

    def test_run_init_refuses_unowned_names_before_any_action(self):
        for extra in (['rg-prod'], ['--gcp-project', 'p', '--gcp-firewall', 'default-allow-ssh']):
            r = subprocess.run(['bash', os.path.join(ROOT, 'scripts', 'ha-r10-run-init.sh'), 'zz-test', '1'] + extra,
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, extra)
            self.assertFalse(os.path.exists(os.path.expanduser('~/.local/share/netclaw/r10-run-zz-test')))


if __name__ == '__main__':
    unittest.main()
