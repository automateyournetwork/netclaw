"""Durable collection admission/recovery, without a device or provider call."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('collection_request', ROOT/'scripts/genie-worlds/collection_request.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CollectionRequestTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT/'.spec200-local/tests'
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.rid = str(uuid.uuid4())
        self.pin = 'a' * 64
        self.capability = {'profile': 'initial', 'parser_version': 'fixture',
                           'runtime_executable': 'synthetic-python', 'runtime_prefix': 'synthetic-runtime',
                           'inventory_sha256': 'b'*64, 'policy_sha256': 'c'*64,
                           'devices': {'r1': {'endpoint_sha256': 'd'*64}}}
        self.calls = []
        self.outcome = 'observed'
        self.unknown = False
        self.enterContext(patch.object(module, 'load_capability', return_value=self.capability))
        self.enterContext(patch.object(module, 'load_module', return_value=SimpleNamespace(
            collect=self.capture, facts=SimpleNamespace(PROFILES={'initial': (['show version'], 180)}))))

    def capture(self, devices, adapter, version, **kw):
        self.calls.append((devices, adapter, kw))
        directory = kw['evidence_root'] / 'capture-test'
        directory.mkdir(mode=0o700)
        raw = directory / 'raw'
        raw.write_text('private raw text')
        raw.chmod(0o600)
        return {'complete': True, 'facts': {'private': 'parsed secret'}, 'observations': [{
            'id': str(uuid.uuid4()), 'device_ref': 'r1', 'command': 'show version', 'command_index': 0,
            'started_at': module.utc(), 'finished_at': module.utc(), 'outcome': self.outcome,
            'parser_version': version, 'artifact_ref': directory.name, 'failure_reason': None,
            'capture_outcome_unknown': self.unknown, 'cleanup_outcome_unknown': self.unknown,
            'raw': 'private raw text', 'parsed': {'private': 'parsed secret'}}]}

    def run_request(self, rid=None, pin=None):
        return module.collect_request(self.root, rid or self.rid, self.root/'capability.json', pin or self.pin)

    def test_duplicate_and_status_return_original_without_recapture(self):
        first = self.run_request()
        self.assertEqual(first, self.run_request())
        self.assertEqual(first, module.status(self.root, self.rid))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(first['state'], 'complete')

    def test_changed_capability_same_id_conflicts(self):
        self.run_request()
        with self.assertRaisesRegex(ValueError, 'request_conflict'):
            self.run_request(pin='f'*64)
        self.assertEqual(len(self.calls), 1)

    def test_public_envelope_is_metadata_only_and_source_bound(self):
        response = self.run_request()
        text = json.dumps(response)
        for secret in ('private raw text', 'parsed secret', str(self.root), 'synthetic-python'):
            self.assertNotIn(secret, text)
        observation = response['observations'][0]
        self.assertEqual(observation['snapshot_id'], self.rid)
        self.assertEqual(observation['source']['inventory_sha256'], 'b'*64)
        self.assertEqual(observation['sha256'], module.digest(b'private raw text'))
        private = self.root / self.rid / 'private-result.json'
        self.assertIn('private raw text', private.read_text())
        self.assertEqual(private.stat().st_mode & 0o777, 0o600)

    def test_unknown_blocks_new_id_without_replaying_original(self):
        self.unknown = True
        original = self.run_request()
        self.assertEqual(original['state'], 'unknown')
        self.assertEqual(self.run_request(), original)
        with self.assertRaisesRegex(ValueError, 'prior_collection_unknown'):
            self.run_request(rid=str(uuid.uuid4()))
        self.assertEqual(len(self.calls), 1)

    def test_parent_failure_before_capture_is_retained_not_replayed(self):
        with patch.object(module, 'load_module', side_effect=RuntimeError('synthetic crash')):
            with self.assertRaises(RuntimeError):
                self.run_request()
        response = module.status(self.root, self.rid)
        self.assertEqual(response['state'], 'unknown')
        self.assertEqual(response['reason'], 'owner_lost_no_replay')
        self.assertEqual(self.run_request(), response)
        self.assertEqual(self.calls, [])

    def test_held_lock_does_not_recover_active_request_or_admit_another(self):
        db = module.Requests(self.root)
        self.addCleanup(db.close)
        self.assertTrue(db.own())
        body = {'schema_version': 1, 'request_id': self.rid, 'state': 'pending'}
        sha = module.digest(module.canonical({'capability_sha256': self.pin}))
        db.db.execute('INSERT INTO requests VALUES (?,?,?,?)',
                      (self.rid, sha, 'pending', json.dumps(body)))
        db.db.commit()
        self.assertEqual(module.status(self.root, self.rid), body)
        self.assertEqual(self.run_request(), body)
        with self.assertRaisesRegex(ValueError, 'collector_busy'):
            self.run_request(rid=str(uuid.uuid4()))
        self.assertEqual(self.calls, [])

    def test_preflight_refusal_has_zero_claims_and_zero_captures(self):
        with patch.object(module, 'load_capability', side_effect=ValueError('native_policy_changed')):
            with self.assertRaisesRegex(ValueError, 'native_policy_changed'):
                self.run_request()
        db = sqlite3.connect(self.root/'collections.sqlite')
        self.addCleanup(db.close)
        self.assertEqual(db.execute('SELECT count(*) FROM requests').fetchone()[0], 0)
        self.assertEqual(self.calls, [])

    def test_private_file_refuses_symlink_permissions_duplicate_keys_and_bad_pin(self):
        path = self.root/'private.json'
        path.write_text('{"a":1,"a":2}')
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'duplicate_json_key'):
            module.private_json(path)
        with self.assertRaisesRegex(ValueError, 'private_digest_changed'):
            module.private_bytes(path, '0'*64)
        link = self.root/'alias'
        link.symlink_to(path)
        with self.assertRaisesRegex(ValueError, 'private_path_required'):
            module.private_bytes(link)
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'private_file_required'):
            module.private_bytes(path)


class CapabilityValidationTests(unittest.TestCase):
    def test_runtime_source_inventory_and_credential_pins_are_enforced_before_capture(self):
        parent = ROOT/'.spec200-local/tests'
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temporary:
            root = Path(temporary).resolve()
            credential = root/'credentials.json'
            module.write_new(credential, {'synthetic': 'local-only'})
            policy = root/'pyats_mcp_server.py'
            policy.write_text('# Independent source-validation fixture; never imported.\n')
            document = {'synthetic': 'not a device testbed'}
            c = {'schema': 1, 'profile': 'detailed', 'runtime_executable': sys.executable,
                 'runtime_prefix': sys.prefix, 'parser_version': 'fixture', 'inventory_sha256': 'a'*64,
                 'policy_file': str(policy), 'policy_sha256': module.digest(policy.read_bytes()),
                 'source_files': {n: module.digest((module.HERE/n).read_bytes()) for n in module.SOURCE_FILES},
                 'devices': {'fixture': {'document': document,
                    'document_sha256': module.digest(module.canonical(document)), 'endpoint_sha256': 'b'*64,
                    'credential_file': str(credential), 'credential_sha256': module.digest(credential.read_bytes())}}}
            capability = root/'capability.json'
            def load(value):
                if capability.exists():
                    capability.unlink()
                module.write_new(capability, value)
                return module.load_capability(capability, module.digest(capability.read_bytes()))
            with patch.object(module.importlib.metadata, 'version', return_value='fixture'):
                self.assertEqual(load(c), c)
                for field, value, reason in [
                    ('runtime_executable', '/different/python', 'selected_runtime_changed'),
                    ('runtime_prefix', '/different/runtime', 'selected_runtime_changed'),
                    ('parser_version', 'different', 'parser_version_changed'),
                    ('source_files', {}, 'collector_source_closure'),
                    ('profile', 'arbitrary-commands', 'collection_profile'),
                    ('policy_sha256', '0'*64, 'native_policy_changed')]:
                    with self.subTest(field=field), self.assertRaisesRegex(ValueError, reason):
                        load({**c, field: value})
                credential.write_text('{"synthetic":"changed"}')
                with self.assertRaisesRegex(ValueError, 'private_digest_changed'):
                    load(c)


if __name__ == '__main__':
    unittest.main()
