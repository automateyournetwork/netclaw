import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/lib'))
from migration_artifacts import Rehearsal, Refused

class RehearsalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.run=Rehearsal(Path(self.temp.name).resolve(),uuid.uuid4().hex)
        self.run.begin('controlled-cml',{'isolated':True,'image':'synthetic-only'},['OSPF FULL','positive traffic','negative traffic'])
    def test_lost_create_response_retains_attempt_and_reconciles_exact_ownership(self):
        attempt=self.run.attempt('create_empty_lab','0'*64)
        record=json.loads((self.run.root/(attempt+'-attempt.json')).read_text());self.assertEqual(record['state'],'unknown')
        for ownership in ({'name':'same-display-name'},{'run_id':'other','attempt_id':attempt}):
            with self.assertRaises(Refused):self.run.reconcile(attempt,'existing-owner-lab',ownership)
        self.run.reconcile(attempt,'fixture-provider-uuid',{'run_id':self.run.root.name,'attempt_id':attempt})
        with self.assertRaises(Refused):self.run.reconcile(attempt,'another-id',{'run_id':self.run.root.name,'attempt_id':attempt})
    def test_failed_assertion_survives_recovery_and_jev_unavailable(self):
        self.run.evidence('negative traffic must fail','failed','controlled-peer',{'sha256':'1'*64})
        self.run.evidence('management recovered','passed','controlled-peer',{'sha256':'2'*64})
        self.run.evidence('Jev advisory','blocked','controlled-peer',{'reason':'disabled; no external call'})
        rows=[json.loads(p.read_text()) for p in self.run.root.glob('*-evidence.json')]
        self.assertEqual(sorted(x['verdict'] for x in rows),['blocked','failed','passed'])
        self.assertFalse(hasattr(self.run,'delete'));self.assertFalse(hasattr(self.run,'cleanup'))
    def test_scope_and_existing_manifest_cannot_be_overwritten(self):
        with self.assertRaises(Refused):self.run.begin('new-provider',{'isolated':False},['new'])
        with self.assertRaises(Refused):self.run.attempt('start','not-a-hash')

if __name__=='__main__':unittest.main()
