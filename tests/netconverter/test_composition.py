"""Controlled lifecycle composition; this is not a live converter or lab."""
import json
from pathlib import Path
import sys
import unittest
import uuid
import test_private_apply as apply_fixture
from migration_artifacts import Rehearsal
from core import Config
from server import Guard

class CompositionTest(unittest.IsolatedAsyncioTestCase):
    async def test_private_collection_conversion_candidate_apply_and_failed_review_package(self):
        fixture=apply_fixture.ApplyTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        root=fixture.root
        collected=json.loads(await fixture.managed.call('pyats_show_running_config',{'device_name':'target','output_mode':'private'}))
        (root/'fixture.json').write_text('{}')
        executable=root/'terminal';executable.write_text('#!'+sys.executable+'\n'+Path(__file__).with_name('peer.py').read_text());executable.chmod(0o700)
        guard=Guard(Config('composition','local-terminal',root/'state',root,executable,'synthetic-key','controlled account'))
        request=await guard.prepare(collected['artifact']['path'],'cisco_asa','palo_alto_set')
        guard.ledger.approve(request['request_id'],request['review_digest'])  # Fixture approval, not an operator upload grant.
        job=await guard.submit(request['request_id']);output=await guard.download(job['job_ref'])
        candidate=guard.ledger.artifacts().verify(output['artifacts'][0])
        approved=fixture.issue(content=candidate.decode())
        applied=json.loads(await fixture.managed.call('pyats_configure_device',{'device_name':'target',
            'artifact_ref':approved['candidate']['artifact_ref'],'grant_ref':approved['grant']}))
        self.assertEqual(applied['status'],'applied_unverified')
        run=Rehearsal(root,uuid.uuid4().hex)
        run.begin('controlled-provider',{'isolated':True,'image':'synthetic'},['positive','negative','Jev'])
        attempt=run.attempt('create_empty_lab','a'*64)
        run.reconcile(attempt,'controlled-lab-id',{'run_id':run.root.name,'attempt_id':attempt})
        run.evidence('positive traffic','passed','controlled-peer',{'candidate':approved['candidate']['sha256']})
        run.evidence('negative control','failed','controlled-peer',{'reason':'fixture intentionally allows forbidden flow'})
        run.evidence('Jev review','blocked','controlled-peer',{'reason':'disabled; no provider call'})
        package={'collection':collected,'submission':job['state'],'download':output,'application':applied,
                 'evidence':[json.loads(p.read_text()) for p in run.root.glob('*-evidence.json')],
                 'ticket':'draft only','publication':'not sent','live_target':'not run','retention':'retain'}
        self.assertNotIn('CANARY',json.dumps(package))
        self.assertIn('failed',[e['verdict'] for e in package['evidence']]);self.assertEqual(len(fixture.calls),1)
        (root/'review-package.json').write_text(json.dumps(package))

if __name__=='__main__':unittest.main()
