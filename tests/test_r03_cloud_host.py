"""Boundary tests: no cloud, metadata, provider, device or host network writes."""
import base64
from copy import deepcopy
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import threading


ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'labs/cloud/gcp/r03' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


guard, secret, host = [module(name) for name in ('host_guard', 'project_secret', 'render_host')]
planner = module('review_plan')
NOW = dt.datetime(2026, 11, 2, tzinfo=dt.timezone.utc)
GUARD = {'schemaVersion': 1, 'run_id': '20261102-test', 'interface': 'ens4',
         'quota_bytes': 1024, 'rate_bits': 1000000, 'expires_at': '2026-11-03T00:00:00Z'}
HOST = {'schemaVersion': 1, 'hostname': 'r03-gcp-montreal.lobsternet.automateyournetwork.com',
        'source': '/opt/netclaw-r03/source', 'home': '/var/lib/netclaw-r03/claw',
        'python': '/opt/netclaw-r03/venv/bin/python', 'node': '/opt/netclaw-r03/bin/node',
        'caddy': '/opt/netclaw-r03/bin/caddy', 'role_contract': '/var/lib/netclaw-r03/role.json',
        'hud_config': '/var/lib/netclaw-r03/hud.json', 'secret_config': '/var/lib/netclaw-r03/secret.json',
        'network_config': '/var/lib/netclaw-r03/network/config.json', 'expires_at': '2026-11-03T00:00:00Z'}


class Network:
    def __init__(self, fail_tc=False):
        self.calls, self.opened, self.exists, self.fail_tc = [], False, False, fail_tc
        self.links = [{'ifname': 'lo', 'flags': ['UP']}, {'ifname': 'ens4', 'flags': ['UP']}]
        self.qdiscs = [{'kind': 'mq'}]

    def __call__(self, command, *, input=None, check=True):
        self.calls.append((command, input))
        code, output = 0, b''
        if command[:3] == ['nft', 'list', 'table']:
            code = 0 if self.exists else 1
        elif command == ['nft', '-f', '-']:
            self.exists, self.opened = True, b'quota name egress' in input
        elif command[0] == 'ip':
            output = json.dumps(self.links).encode()
        elif command[:3] == ['tc', '-j', 'qdisc']:
            output = json.dumps(self.qdiscs).encode()
        elif command[:3] == ['tc', 'qdisc', 'replace'] and self.fail_tc:
            raise guard.Refused('injected_qdisc_failure')
        return SimpleNamespace(returncode=code, stdout=output, stderr=b'')


class EgressTests(unittest.TestCase):
    def test_spent_allocation_never_reopens_on_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            wire = Network()
            guard.activate(GUARD, directory, command=wire, now=NOW)
            self.assertTrue(wire.opened)
            claim = Path(directory, 'allocation.json').read_bytes()
            with self.assertRaisesRegex(guard.Refused, 'already_spent'):
                guard.activate(GUARD, directory, command=wire, now=NOW)
            self.assertFalse(wire.opened)
            self.assertEqual(Path(directory, 'allocation.json').read_bytes(), claim)

    def test_partial_activation_stays_closed_and_spent(self):
        with tempfile.TemporaryDirectory() as directory:
            wire = Network(fail_tc=True)
            with self.assertRaises(guard.Refused):
                guard.activate(GUARD, directory, command=wire, now=NOW)
            self.assertFalse(wire.opened)
            self.assertTrue(Path(directory, 'allocation.json').exists())
            self.assertFalse(Path(directory, 'activated.json').exists())
            wire.fail_tc = False
            with self.assertRaisesRegex(guard.Refused, 'already_spent'):
                guard.activate(GUARD, directory, command=wire, now=NOW)
            self.assertFalse(wire.opened)

    def test_new_network_surface_or_owned_qdisc_collision_refuses(self):
        for case in ('links', 'qdiscs'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                wire = Network()
                if case == 'links': wire.links.append({'ifname': 'ens5', 'flags': ['UP']})
                else: wire.qdiscs = [{'kind': 'htb'}]
                with self.assertRaises(guard.Refused):
                    guard.activate(GUARD, directory, command=wire, now=NOW)
                self.assertFalse(wire.opened)
                self.assertFalse(Path(directory, 'allocation.json').exists())

    def test_expiry_or_extended_window_refuses_after_closing(self):
        for now in (NOW + dt.timedelta(days=2), NOW - dt.timedelta(days=2)):
            with tempfile.TemporaryDirectory() as directory:
                wire = Network()
                with self.assertRaisesRegex(guard.Refused, 'expiry'):
                    guard.activate(GUARD, directory, command=wire, now=now)
                self.assertFalse(wire.opened)

    def test_injection_unbounded_values_and_unknown_keys_refused(self):
        for key, value in [('interface', 'ens4; reboot'), ('quota_bytes', 10 * 1024**3 + 1),
                           ('rate_bits', 1000001), ('quota_bytes', True), ('command', 'reset')]:
            config = dict(GUARD, **{key: value})
            with self.subTest(key=key), self.assertRaises(guard.Refused): guard.validate(config)

    def test_invalid_configuration_still_closes_before_any_validation(self):
        wire = Network(); wire.opened = True; wire.exists = True
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(guard.Refused):
            guard.activate({'unexpected': 'configuration'}, directory, command=wire, now=NOW)
        self.assertFalse(wire.opened)
        self.assertEqual(wire.calls[1][0], ['nft', '-f', '-'])

    def test_all_non_loopback_output_is_metered(self):
        opened = guard.rules(GUARD, True, True).decode()
        self.assertIn('hook output priority -300', opened)
        self.assertIn('oifname "lo" accept', opened)
        self.assertIn('quota name egress drop', opened)
        self.assertNotIn('ct state', opened)  # No bypass for TLS/error replies.
        self.assertNotIn('tcp sport', opened)  # IAP also consumes the allowance.
        self.assertTrue(opened.startswith('delete table inet netclaw_r03\n'))

    def test_early_baseline_only_permits_platform_dhcp_before_closed_output(self):
        baseline = guard.rules({}, False, False, bootstrap=True).decode()
        self.assertIn('ip daddr { 169.254.169.254, 255.255.255.255 } udp sport 68 udp dport 67 accept', baseline)
        self.assertNotIn('tcp', baseline)
        self.assertNotIn('quota', baseline)
        closed = guard.rules({}, False, False).decode()
        self.assertNotIn('udp', closed)

    def test_expiry_serializes_after_inflight_activation_and_wins(self):
        with tempfile.TemporaryDirectory() as directory, ThreadPoolExecutor(2) as workers:
            wire = Network(); at_tc, release = threading.Event(), threading.Event()
            lock = str(Path(directory, 'process.lock'))
            def command(args, **kwargs):
                if args[:3] == ['tc', 'qdisc', 'replace']:
                    at_tc.set(); self.assertTrue(release.wait(3))
                return wire(args, **kwargs)
            def activate():
                with guard.serial_lock(lock): guard.activate(GUARD, directory, command=command, now=NOW)
            def expire():
                with guard.serial_lock(lock): guard.replace_rules({}, False, wire)
            first = workers.submit(activate)
            self.assertTrue(at_tc.wait(3))
            last = workers.submit(expire)
            self.assertFalse(last.done())
            release.set(); first.result(3); last.result(3)
            self.assertFalse(wire.opened)
            self.assertTrue(Path(directory, 'allocation.json').exists())

    def test_close_does_not_read_any_config_and_activate_closes_before_read(self):
        args = SimpleNamespace(action='close', config='/missing', state_dir='/missing')
        with patch.object(guard, 'replace_rules') as close, patch.object(guard, 'private', side_effect=FileNotFoundError) as read:
            guard.perform(args)
            close.assert_called_once_with({}, False, bootstrap=False)
            read.assert_not_called()
        args.action = 'activate'
        with patch.object(guard, 'replace_rules') as close, patch.object(guard, 'private', side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError): guard.perform(args)
            close.assert_called_once_with({}, False, bootstrap=False)


class SecretTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name).resolve()
        self.home.chmod(0o700)
        for name in ('netclaw-hud', 'netclaw-federation'):
            (self.home / name).mkdir(mode=0o700)
        self.installation = '62e4c7b3-6c95-4c0e-b73d-d61025b107b8'
        self.payload = {'schemaVersion': 1, 'installationId': self.installation,
                        'environment': {'NETCLAW_PROTECTED_OPERATOR_TOKEN': 'A' * 43}}
        installation = self.home / 'netclaw-hud/installation.json'
        installation.write_text(json.dumps({'schemaVersion': 1, 'installationId': self.installation}))
        installation.chmod(0o600)
        self.raw = json.dumps(self.payload).encode()
        self.config = {'schemaVersion': 1, 'installationId': self.installation, 'home': str(self.home),
                       'version': 'projects/netclaw-506315/secrets/netclaw-r03-20261102-test-operator/versions/1',
                       'payloadSha256': hashlib.sha256(self.raw).hexdigest()}
        self.calls = []

    def tearDown(self): self.temp.cleanup()

    def request(self, url, headers):
        self.calls.append((url, headers))
        if url.startswith('http://169.254.169.254/'):
            return {'access_token': 'synthetic-only-token'}
        return {'payload': {'data': base64.b64encode(self.raw).decode()}}

    def test_exact_token_projection_private_idempotent_and_no_other_state(self):
        secret.validate(self.config)
        content = secret.retrieve(self.config, self.request)
        secret.project(self.config, content)
        secret.project(self.config, content)
        target = self.home / 'netclaw-federation/protected-operator.env'
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(target.read_bytes(), b'NETCLAW_PROTECTED_OPERATOR_TOKEN=' + b'A' * 43 + b'\n')
        self.assertEqual(list(target.parent.iterdir()), [target])
        self.assertEqual(self.calls[1][0], 'https://secretmanager.googleapis.com/v1/' + self.config['version'] + ':access')

    def test_never_overwrites_live_token_or_symlink(self):
        target = self.home / 'netclaw-federation/protected-operator.env'
        target.write_bytes(b'existing'); target.chmod(0o600)
        with self.assertRaisesRegex(secret.Refused, 'changed'):
            secret.project(self.config, b'new')
        self.assertEqual(target.read_bytes(), b'existing')
        target.unlink(); target.symlink_to(self.home / 'other')
        with self.assertRaises(secret.Refused): secret.project(self.config, b'new')

    def test_cross_installation_provider_payload_and_digest_drift_refused(self):
        original = deepcopy(self.payload)
        for kind in ('identity', 'provider', 'digest'):
            self.payload = deepcopy(original)
            if kind == 'identity': self.payload['installationId'] = 'different'
            if kind == 'provider': self.payload['environment']['ANTHROPIC_API_KEY'] = 'synthetic'
            self.raw = json.dumps(self.payload).encode()
            cfg = dict(self.config)
            if kind != 'digest': cfg['payloadSha256'] = hashlib.sha256(self.raw).hexdigest()
            else: cfg['payloadSha256'] = '0' * 64
            with self.subTest(kind=kind), self.assertRaises(secret.Refused): secret.retrieve(cfg, self.request)

    def test_latest_r01_and_foreign_secret_paths_refused(self):
        for version in (self.config['version'].replace('/1', '/latest'),
                        self.config['version'].replace('r03', 'r01'), 'https://example.invalid/secret'):
            with self.subTest(version=version), self.assertRaises(secret.Refused):
                secret.validate(dict(self.config, version=version))

    def test_foreign_home_and_permissive_existing_token_refused(self):
        target = self.home / 'netclaw-federation/protected-operator.env'
        target.write_bytes(b'existing'); target.chmod(0o644)
        with self.assertRaises(secret.Refused): secret.project(self.config, b'existing')
        target.unlink()
        with self.assertRaises(secret.Refused):
            secret.project(dict(self.config, installationId='different'), b'new')


class HostTests(unittest.TestCase):
    def test_paths_cannot_inject_unit_directives_or_escape_isolation(self):
        for key, value in [('node', '/opt/netclaw-r03/bin/node\nExecStart=/bin/sh'),
                           ('source', '/opt/netclaw-r03/../r01'), ('home', '/root/.openclaw'),
                           ('network_config', '/var/lib/netclaw-r03/claw/network.json'),
                           ('hostname', 'r01-gcp-montreal.lobsternet.automateyournetwork.com')]:
            with self.subTest(key=key), self.assertRaises(host.Refused): host.render(dict(HOST, **{key: value}))

    def test_federation_hud_same_owner_edge_separate_and_no_ambient_credentials(self):
        files = host.render(HOST)
        for name in ('netclaw-r03-federation.service', 'netclaw-r03-hud.service'):
            value = files[name]
            for line in ('User=netclaw-r03\n', 'ProtectSystem=strict', 'UMask=0077', 'NoNewPrivileges=yes',
                         'CapabilityBoundingSet=\n', 'BindsTo=netclaw-r03-guard.service'):
                self.assertIn(line, value)
            self.assertNotIn('EnvironmentFile=', value)
        self.assertIn('User=netclaw-r03-edge', files['netclaw-r03-caddy.service'])
        self.assertIn('InaccessiblePaths=/var/lib/netclaw-r03', files['netclaw-r03-caddy.service'])
        self.assertIn('CapabilityBoundingSet=CAP_NET_BIND_SERVICE', files['netclaw-r03-caddy.service'])
        self.assertIn('Persistent=true', files['netclaw-r03-expiry.timer'])
        self.assertIn('OnCalendar=2026-11-03 00:00:00 UTC', files['netclaw-r03-expiry.timer'])
        self.assertIn('Requires=netclaw-r03-baseline.service', files['networkd-r03-guard.conf'])
        self.assertIn('After=network-online.target netclaw-r03-baseline.service', files['netclaw-r03-guard.service'])
        self.assertIn('/usr/bin/python3 -I -S -B', files['netclaw-r03-federation.service'])
        self.assertIn('ExecStart=/usr/bin/env -i ', files['netclaw-r03-hud.service'])

    def test_edge_preserves_owner_authority_and_has_no_open_proxy_or_public_admin(self):
        value = host.render(HOST)['Caddyfile']
        for item in ('admin off', 'persist_config off', 'protocols h1 h2', 'strict_sni_host on',
                     'max_header_size 16KiB', 'max_size 72KiB', 'header_up -Forwarded',
                     'header_up -X-Forwarded-*', 'header_up -X-Goog-*', 'reverse_proxy 127.0.0.1:13003'):
            self.assertIn(item, value)
        self.assertNotIn('header_up Host', value)
        self.assertNotIn('trusted_proxies', value)
        self.assertEqual(value.count('log {'), 1)  # Global redacted errors only; no access logger.
        self.assertIn('request delete', value)
        self.assertIn('resp_headers delete', value)


class PrivatePlanTests(unittest.TestCase):
    def test_foreign_project_run_resource_and_import_state_refused(self):
        resource = {'mode': 'managed', 'type': 'google_compute_instance',
                    'instances': [{'attributes': {'project': 'netclaw-506315', 'name': 'netclaw-r03-20261102-test'}}]}
        state = {'version': 4, 'resources': [resource]}
        planner.validate_state(json.dumps(state), 'netclaw-r03-20261102-test', 'netclaw-506315')
        for key, value in [('project', 'foreign-project'), ('name', 'netclaw-r01-20261101'),
                           ('name', 'netclaw-r03-20261102-testing')]:
            copied = deepcopy(state); copied['resources'][0]['instances'][0]['attributes'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                planner.validate_state(json.dumps(copied), 'netclaw-r03-20261102-test', 'netclaw-506315')
        state['resources'][0]['type'] = 'google_project_iam_member'
        with self.assertRaises(ValueError): planner.validate_state(json.dumps(state), 'netclaw-r03-20261102-test', 'netclaw-506315')

    def test_saved_plan_resource_addresses_are_closed(self):
        item = {'address': 'google_compute_instance.border', 'mode': 'managed', 'type': 'google_compute_instance', 'change': {'actions': ['create']}}
        self.assertEqual(planner.validate_plan({'resource_changes': [item]})[0]['actions'], ['create'])
        for kind in ('address', 'import'):
            copied = deepcopy(item)
            if kind == 'address': copied['address'] = 'google_compute_instance.r01'
            else: copied['change']['importing'] = {'id': 'existing'}
            with self.subTest(kind=kind), self.assertRaises(ValueError): planner.validate_plan({'resource_changes': [copied]})


if __name__ == '__main__': unittest.main()
