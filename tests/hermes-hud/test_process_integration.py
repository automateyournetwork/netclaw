"""Faults against actual HUD, official MCP, pinned Hermes and controlled provider."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest
sys.path.insert(0,str(Path(__file__).parent/'fixtures'))
from runtime import RuntimeFixture,Bridge

@unittest.skipUnless(all(os.environ.get(k) for k in ('NETCLAW_HERMES_PYTHON','NETCLAW_HERMES_SOURCE','NETCLAW_SUBNET_PYTHON')),'real Hermes fixture interpreters required')
class ProcessTests(unittest.TestCase):
    def fixture(self,**kwargs):
        fixture=RuntimeFixture(**kwargs);self.addCleanup(fixture.close);return fixture.start()
    def test_pending_bridge_and_hud_restart_preserve_nonce_and_late_result(self):
        f=self.fixture();value=f.submit('restart','nonce','WAIT_FOR_TEST remember violet')
        request=value['requestId'];self.assertTrue(f.provider.started.wait(15))
        children=subprocess.check_output(['pgrep','-P',str(f.hud.pid)],text=True).split()
        self.assertEqual(len(children),1,'Only the test HUD private MCP child is expected')
        os.kill(int(children[0]),signal.SIGKILL)
        f.wait(lambda:f.client.get('/api/runtime').json()['readiness'].get('ready'))
        self.assertEqual(f.status(request)['state'],'running')
        f.stop_process(f.hud);f.start_hud()
        self.assertEqual(f.submit('restart','nonce','WAIT_FOR_TEST remember violet')['requestId'],request)
        self.assertEqual(len(f.provider.calls),1,[(b.get('model'),[(m['role'],str(m.get('content',''))[-120:]) for m in b.get('messages',[])][-2:]) for b in f.provider.calls])
        f.provider.release.set();self.assertEqual(f.settled(request)['state'],'completed')
        self.assertEqual(len(f.provider.calls),1,[(b.get('model'),[(m['role'],str(m.get('content',''))[-120:]) for m in b.get('messages',[])][-2:]) for b in f.provider.calls])
        self.assertEqual(sum(p==('POST','/v1/runs') for p in f.proxy_calls),1)
    def test_lost_admission_is_durable_unknown_and_explicit_fresh_does_not_replay(self):
        f=self.fixture();f.drop_submit=True
        value=f.submit('lost','nonce','WAIT_FOR_TEST lost reply');request=value['requestId']
        self.assertEqual(value['state'],'unknown');self.assertTrue(f.provider.started.wait(15))
        f.stop_process(f.hud);f.start_hud()
        self.assertEqual(f.status(request)['state'],'unknown')
        self.assertEqual(f.submit('lost','nonce','WAIT_FOR_TEST lost reply')['requestId'],request)
        self.assertEqual(f.client.post('/api/chat/conversations',json={}).status_code,409)
        fresh=f.client.post('/api/chat/conversations',json={'acknowledgedUncertainRequestId':request})
        self.assertEqual(fresh.status_code,201)
        f.provider.release.set();self.assertEqual(f.status(request)['state'],'unknown')
        self.assertEqual(sum(p==('POST','/v1/runs') for p in f.proxy_calls),1)
    def test_companion_loss_crosses_configured_deadline_without_resubmission(self):
        f=self.fixture(deadline=1000);value=f.submit('companion','nonce','WAIT_FOR_TEST companion loss')
        request=value['requestId'];self.assertTrue(f.provider.started.wait(15))
        with f.bridge.ledger.db() as db:
            row=db.execute('SELECT created,deadline FROM requests WHERE id=?',(request,)).fetchone()
        self.assertAlmostEqual(row['deadline']-row['created'],1,places=1)
        f.stop_process(f.companion,kill=True);time.sleep(1.1)
        self.assertEqual(f.status(request)['state'],'unknown')
        f.start_companion();self.assertIn(f.status(request)['state'],('unknown','interrupted','failed'))
        self.assertEqual(sum(p==('POST','/v1/runs') for p in f.proxy_calls),1)
    def test_real_stop_and_unavailable_approvals_never_grant_authority(self):
        f=self.fixture();value=f.submit('stop','nonce','WAIT_FOR_TEST stop request');request=value['requestId']
        self.assertTrue(f.provider.started.wait(15))
        for choice in ('once','deny','always','session'):
            response=f.client.post('/api/chat/requests/'+request+'/approval',json={'approvalId':'not-pending','choice':choice})
            self.assertFalse(response.is_success)
        response=f.client.post('/api/chat/requests/'+request+'/stop',json={})
        self.assertTrue(response.is_success);self.assertIn(response.json()['state'],('stopping','cancelled','interrupted'))
        f.provider.release.set();self.assertIn(f.settled(request)['state'],('cancelled','interrupted','completed'))
        self.assertEqual(sum(p[0]=='POST' and p[1].endswith('/approval') for p in f.proxy_calls),0)
        self.assertEqual(len(f.provider.calls),1,[(b.get('model'),[(m['role'],str(m.get('content',''))[-120:]) for m in b.get('messages',[])][-2:]) for b in f.provider.calls])
    def test_auth_provider_config_and_source_failures_are_observable(self):
        f=self.fixture();bad=Bridge(f.home,f.installation,key='incorrect-'+'a'*32,port=f.proxy.server_port)
        self.addCleanup(bad.client.close)
        with self.assertRaises(Exception) as caught:bad.status()
        self.assertEqual(caught.exception.code,'authentication_failed');self.assertEqual(len(f.provider.calls),0)
        f.provider.fail_auth=True
        result=f.settled(f.submit('bad-provider','nonce','hello')['requestId'])
        self.assertEqual(result['state'],'failed');self.assertFalse(result['fromGateway'])
        f.provider.fail_auth=False;before=len(f.provider.calls)
        config=f.home/'config.yaml';original=config.read_bytes();config.write_text(json.dumps({**f.config,'changed':'policy'}))
        self.assertFalse(f.client.get('/api/runtime').json()['readiness']['ready'])
        self.assertEqual(len(f.provider.calls),before);config.write_bytes(original)
        f.stop_process(f.companion)
        source=Path(os.environ['NETCLAW_HERMES_SOURCE'])/'agent/agent_init.py';saved=source.read_bytes()
        try:
            source.write_bytes(saved+b'\n# synthetic source drift\n')
            child=f.launch([os.environ['NETCLAW_HERMES_PYTHON'],str(Path(__file__).resolve().parents[2]/'mcp-servers/hermes-hud-mcp/hermes_api.py'),
                '--home',str(f.home),'--source',os.environ['NETCLAW_HERMES_SOURCE'],'--installation',f.installation,'--port',str(f.companion_port)])
            self.assertNotEqual(child.wait(timeout=15),0);self.assertEqual(len(f.provider.calls),before)
        finally:source.write_bytes(saved)
        config.rename(config.with_suffix('.saved'))
        response=f.client.post('/api/chat/requests',json={'hudThread':'missing','clientNonce':'missing','message':'never dispatch'})
        self.assertEqual(response.status_code,503);self.assertFalse(response.json()['mayHaveExecuted'])
        self.assertEqual(len(f.provider.calls),before)

if __name__=='__main__':unittest.main()
