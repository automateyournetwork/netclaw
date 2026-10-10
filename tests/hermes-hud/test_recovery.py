from pathlib import Path
import sys
import tempfile
import unittest
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'mcp-servers/hermes-hud-mcp'))
from bridge import Bridge
from ledger import HudError
class RecoveryTests(unittest.TestCase):
    def test_lost_post_restart_and_nonce_never_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts=[]
            def transport(request):
                if request.method=='POST':posts.append(request);raise httpx.ReadTimeout('lost response')
                return httpx.Response(404,json={})
            client=httpx.Client(base_url='http://127.0.0.1',transport=httpx.MockTransport(transport))
            bridge=Bridge(tmp,'i',key='k'*32,client=client)
            bridge.ledger.open('c');bridge.ledger.bind('c','native')
            self.assertEqual(bridge.submit('c','r','nonce','operation')['state'],'unknown')
            restarted=Bridge(tmp,'i',key='k'*32,client=client)
            self.assertEqual(restarted.submit('c','r','nonce','operation')['state'],'unknown')
            self.assertEqual(restarted.request_status('c','r')['state'],'unknown');self.assertEqual(len(posts),1)
            with self.assertRaises(HudError):restarted.submit('c','other','other','operation')
    def test_late_result_reconciles_without_post_and_stop_is_not_cancellation(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls=[];state=['running']
            def transport(request):
                calls.append(request.method)
                return httpx.Response(200,json={'status':state[0],'output':'finished'})
            bridge=Bridge(tmp,'i',key='k'*32,client=httpx.Client(base_url='http://127.0.0.1',transport=httpx.MockTransport(transport)))
            bridge.ledger.open('c');bridge.ledger.bind('c','native');bridge.ledger.admit('c','r','n','operation',10000)
            bridge.ledger.update('c','r','unknown',run_id='run')
            self.assertEqual(bridge.request_status('c','r')['state'],'running')
            self.assertEqual(bridge.stop('c','r')['state'],'stopping')
            state[0]='completed';self.assertEqual(bridge.request_status('c','r')['state'],'completed')
            self.assertEqual(calls,['GET','POST','GET'])
    def test_failed_persistence_never_posts_and_approval_is_exact(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            calls=[]
            def transport(request):
                calls.append(request.method)
                return httpx.Response(200,json={'status':'awaiting_approval','approval':{'id':'pending'}})
            bridge=Bridge(tmp,'i',key='k'*32,client=httpx.Client(base_url='http://127.0.0.1',transport=httpx.MockTransport(transport)))
            bridge.ledger.open('c');bridge.ledger.bind('c','native')
            with patch.object(bridge.ledger,'admit',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):bridge.submit('c','r','n','operation')
            self.assertEqual(calls,[])
            bridge.ledger.admit('c','r','n','operation',60000);bridge.ledger.update('c','r','running',run_id='run')
            for choice in ('always','session'):
                with self.assertRaises(HudError):bridge.approval('c','r','pending',choice)
            with self.assertRaises(HudError):bridge.approval('c','r','stale','once')
            self.assertNotIn('POST',calls)
            bridge.approval('c','r','pending','deny');self.assertEqual(calls.count('POST'),1)
            bridge.approval('c','r','pending','once');self.assertEqual(calls.count('POST'),2)
if __name__=='__main__':unittest.main()
