"""Observable disclosure boundaries; all source bytes and peers are synthetic."""
import concurrent.futures
import dataclasses
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'mcp-servers/netconverter-mcp'))
from artifacts import Artifacts, Refused
from core import Config, Ledger


CAPS = {'paths': [{'source': 'cisco_asa', 'target': 'palo_alto_set', 'job_type': 'convert'}],
        'max_bytes': 20 * 1024 * 1024, 'options_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False},
        'evidence': 'synthetic-peer-v1'}


class CoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.workspace = self.root / 'workspace'; self.workspace.mkdir(mode=0o700)
        self.source = self.workspace / 'input.cfg'
        self.source.write_text('PRIVATE_CONFIG_CANARY\nhostname synthetic\n')
        self.exe = self.root / 'terminal'; self.exe.write_text('synthetic executable'); self.exe.chmod(0o700)
        self.config = Config('installation-test', 'local-terminal', self.root / 'state', self.workspace,
                             self.exe, 'synthetic-key', 'test account')
        self.ledger = Ledger(self.config)

    def prepare(self):
        return self.ledger.prepare(str(self.source), 'cisco_asa', 'palo_alto_set', 'convert', {}, CAPS)

    def approve(self, request):
        return self.ledger.approve(request['request_id'], request['review_digest'], 300)

    def test_metadata_never_returns_source_or_key(self):
        request = self.prepare(); self.approve(request)
        output = json.dumps(self.ledger.status(request['request_id']))
        self.assertNotIn('PRIVATE_CONFIG_CANARY', output)
        self.assertNotIn('synthetic-key', output)
        self.assertEqual(request['source']['bytes'], self.source.stat().st_size)
        self.assertEqual(len(request['review_digest']), 64)

    def test_no_approval_no_attempt(self):
        request = self.prepare()
        with self.assertRaisesRegex(Refused, 'approval_required'):
            self.ledger.claim(request['request_id'], CAPS)
        self.assertEqual(self.ledger.status(request['request_id'])['state'], 'prepared')

    def test_binary_or_empty_source_cannot_be_approved_as_text(self):
        for data in (b'\xff\xfe',b'a\x00b',b'  \n'):
            self.source.write_bytes(data)
            with self.assertRaisesRegex(Refused,'text_source'):self.prepare()

    def test_exact_digest_and_expiry(self):
        request = self.prepare()
        with self.assertRaisesRegex(Refused, 'review_digest'):
            self.ledger.approve(request['request_id'], '0' * 64, 300)
        self.approve(request)
        with self.ledger.connection() as db:
            db.execute('UPDATE requests SET expires = 0')
        self.assertEqual(self.ledger.status(request['request_id'])['state'],'expired')
        with self.assertRaisesRegex(Refused, 'expired'):
            self.ledger.claim(request['request_id'], CAPS)

    def test_concurrent_claim_is_single_use(self):
        request = self.prepare(); self.approve(request)
        def claim(_):
            try: return Ledger(self.config).claim(request['request_id'], CAPS)['attempt_id']
            except Refused: return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(claim, range(8)))
        self.assertEqual(sum(x is not None for x in results), 1)
        # A restarted process cannot assume that an interrupted attempt failed.
        self.assertEqual(Ledger(self.config).status(request['request_id'])['state'], 'unknown')
        with self.assertRaises(Refused): self.ledger.approve(request['request_id'], request['review_digest'], 300)

    def test_changed_source_snapshot_capabilities_or_connection_refused(self):
        for mutation in ['source', 'snapshot', 'capabilities', 'key', 'account', 'executable']:
            with self.subTest(mutation=mutation):
                request = self.prepare(); self.approve(request)
                cfg = self.config; caps = json.loads(json.dumps(CAPS))
                if mutation == 'source': self.source.write_text('changed source')
                elif mutation == 'snapshot':
                    artifact = self.ledger.request(request['request_id'])['frozen']
                    path = self.workspace / artifact['relative_path']; path.chmod(0o600); path.write_text('changed frozen bytes')
                elif mutation == 'capabilities': caps['evidence'] = 'different-schema'
                elif mutation == 'key': cfg = dataclasses.replace(cfg, key='different-key')
                elif mutation == 'account': cfg = dataclasses.replace(cfg, account='different-account')
                else: self.exe.write_text('changed executable')
                with self.assertRaises(Refused): Ledger(cfg).claim(request['request_id'], caps)

    def test_receipt_integrity_and_unknown_do_not_replay(self):
        request = self.prepare(); self.approve(request)
        attempt = self.ledger.claim(request['request_id'], CAPS)
        self.ledger.finish(request['request_id'], attempt['attempt_id'], {'job_id': 'job-1', 'sha256': '0'*64, 'bytes': 1})
        self.assertEqual(self.ledger.status(request['request_id'])['state'], 'unknown')
        with self.assertRaises(Refused): self.ledger.claim(request['request_id'], CAPS)

    def test_success_receipt_binds_job(self):
        request = self.prepare(); self.approve(request)
        attempt = self.ledger.claim(request['request_id'], CAPS)
        result = self.ledger.finish(request['request_id'], attempt['attempt_id'],
            {'job_id': 'job-123', 'sha256': request['source']['sha256'], 'bytes': request['source']['bytes']})
        self.assertEqual(result['state'], 'submitted')
        self.assertEqual(self.ledger.job(result['job_ref'])['job_id'], 'job-123')
        with self.assertRaises(Refused): Ledger(dataclasses.replace(self.config,key='new')).job(result['job_ref'])

    def test_paths_links_limits_and_no_clobber(self):
        artifacts = Artifacts(self.workspace, 'installation-test')
        for name in ['../outside', str(self.root / 'outside')]:
            with self.assertRaises(Refused): artifacts.capture(name)
        link = self.workspace / 'link'; link.symlink_to(self.source)
        with self.assertRaises(Refused): artifacts.capture(str(link))
        hard = self.workspace / 'hard'; os.link(self.source, hard)
        with self.assertRaises(Refused): artifacts.capture(str(hard))
        hard.unlink()
        with self.assertRaises(Refused): artifacts.capture(str(self.source), limit=1)
        directory_link = self.workspace / 'linked-dir'; directory_link.symlink_to(self.workspace)
        with self.assertRaises(Refused): artifacts.capture(str(directory_link / 'input.cfg'))
        fifo = self.workspace / 'fifo'; os.mkfifo(fifo)
        with self.assertRaises(Refused): artifacts.capture(str(fifo))
        artifacts.publish('test-id', b'first')
        with self.assertRaises(Refused): artifacts.publish('test-id', b'second')

    def test_unsupported_path_and_options_never_prepared(self):
        for source, target, options in [('frr','palo_alto_set',{}),('cisco_asa','scm',{}),('cisco_asa','palo_alto_set',{'config':'raw'})]:
            with self.assertRaises(Refused): self.ledger.prepare(str(self.source),source,target,'convert',options,CAPS)

    def test_readonly_mode_never_prepares(self):
        ledger = Ledger(dataclasses.replace(self.config, mode='hosted-readonly'))
        with self.assertRaisesRegex(Refused,'local_terminal_required'):
            ledger.prepare(str(self.source),'cisco_asa','palo_alto_set','convert',{},CAPS)


if __name__ == '__main__': unittest.main()
