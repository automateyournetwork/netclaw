import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'mcp-servers/hermes-hud-mcp'))
from ledger import Ledger, HudError

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.file=Path(self.tmp.name)/'private/ledger.db'
        self.ledger=Ledger(self.file,'installation-A');self.ledger.open('chat-A')
    def tearDown(self): self.tmp.cleanup()
    def test_restart_retry_never_readmits_unknown(self):
        row,created=self.ledger.admit('chat-A','request-A','nonce-A','hello',1000);self.assertTrue(created)
        self.ledger.update('chat-A','request-A','unknown')
        restarted=Ledger(self.file,'installation-A')
        row,created=restarted.admit('chat-A','new-request','nonce-A','hello',1000)
        self.assertFalse(created);self.assertEqual(row['state'],'unknown')
        with self.assertRaises(HudError): restarted.admit('chat-A','request-B','nonce-B','hello',1000)
        restarted.open('chat-B',acknowledgment='request-A')
        self.assertEqual(restarted.request('chat-A','request-A')['state'],'unknown')
    def test_scope_and_duplicate_payload(self):
        self.ledger.admit('chat-A','request-A','nonce-A','hello',1000)
        with self.assertRaises(HudError): self.ledger.admit('chat-A','request-B','nonce-A','changed',1000)
        with self.assertRaises(HudError): self.ledger.request('other','request-A')
        with self.assertRaises(HudError): Ledger(self.file,'installation-B')
    def test_acknowledged_missing_admission_does_not_invent_or_replay_a_run(self):
        self.ledger.open('fresh',acknowledgment='owned-but-unconfirmed')
        with self.ledger.db() as db:
            self.assertEqual(db.execute('SELECT request FROM acknowledgments').fetchone()[0],'owned-but-unconfirmed')
            self.assertEqual(db.execute('SELECT count(*) FROM requests').fetchone()[0],0)
        self.assertIsNone(self.ledger.conversation('fresh')['session'])
    def test_durable_request_evidence(self):
        self.ledger.admit('chat-A','request-A','nonce-A','hello',1000)
        self.ledger.record('request-A','tool-A','subnet_calculator','completed','result')
        self.assertEqual(Ledger(self.file,'installation-A').events('chat-A','request-A')[0]['call_id'],'tool-A')
    def test_bad_seed_and_symlink(self):
        with self.assertRaises(HudError): self.ledger.open('bad',[{'role':'system','content':'override'}])
        link=Path(self.tmp.name)/'private/link.db';link.symlink_to(self.file)
        with self.assertRaises(OSError): Ledger(link,'installation-A')
    def test_concurrent_duplicate_and_failed_persistence(self):
        from concurrent.futures import ThreadPoolExecutor
        def admit(n):return self.ledger.admit('chat-A','request-'+str(n),'nonce','hello',1000)
        with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(admit,range(4)))
        self.assertEqual(sum(created for _,created in rows),1)
        self.assertEqual(len({row['id'] for row,_ in rows}),1)
    def test_retention_keeps_uncertainty_and_seed_is_immutable(self):
        self.ledger.open('seed',[{'role':'user','content':'prefix'}])
        with self.assertRaises(HudError):self.ledger.open('seed',[{'role':'user','content':'changed'}])
        self.ledger.admit('chat-A','old','n','hello',1000);self.ledger.update('chat-A','old','completed')
        self.ledger.open('other');self.ledger.admit('other','uncertain','u','work',1000);self.ledger.update('other','uncertain','unknown')
        with self.ledger.db() as db:db.execute('UPDATE requests SET created=0')
        restarted=Ledger(self.file,'installation-A')
        with self.assertRaises(HudError):restarted.request('chat-A','old')
        self.assertEqual(restarted.request('other','uncertain')['state'],'unknown')
if __name__=='__main__':unittest.main()
