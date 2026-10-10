import importlib.util
import json
import os
from pathlib import Path
import socket
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'mcp-servers/hermes-hud-mcp'))
sys.path.insert(0,str(Path(__file__).parent/'fixtures'))
from bridge import Bridge
from provider import Provider

@unittest.skipUnless(os.environ.get('NETCLAW_HERMES_PYTHON') and os.environ.get('NETCLAW_HERMES_SOURCE') and os.environ.get('NETCLAW_SUBNET_PYTHON'),'real Hermes fixture interpreters required')
class RealHermesTests(unittest.TestCase):
    def test_five_turns_real_tool_history_and_owner_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=(Path(tmp)/'Hermes Home').resolve();home.mkdir(mode=0o700)
            records=home/'python-runtimes/records';records.mkdir(parents=True,mode=0o700)
            (records/'hermes-hud').write_text(sys.executable+'\n')
            (records/'subnet-calc').write_text(os.environ['NETCLAW_SUBNET_PYTHON']+'\n')
            provider=Provider();url=provider.start()
            config={'model':{'default':'hud-fixture','provider':'custom','base_url':url},'mcp_servers':{'subnet-calc-mcp':{'command':'python3','args':['-u',str(ROOT/'scripts/component-launch.py'),'subnet-calc','--server','subnet-calc-mcp'],'env':{'NETCLAW_RUNTIME_ROOT':str(home/'python-runtimes'),'NETCLAW_RUNTIME_ENV':str(home/'.env')}}}}
            (home/'config.yaml').write_text(json.dumps(config));(home/'MEMORY.md').write_text('PRIVATE_OTHER_CONVERSATION_SENTINEL')
            original=(home/'config.yaml').read_bytes()
            installed=home/'skills/subnet-calculator';installed.mkdir(parents=True)
            shutil.copyfile(ROOT/'workspace/skills/subnet-calculator/SKILL.md',installed/'SKILL.md')
            sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
            key='fixture-'+os.urandom(32).hex()
            env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','SYSTEMROOT')}
            env.update(HOME=tmp,HERMES_HOME=str(home),OPENAI_API_KEY='fixture-only-key',OPENAI_BASE_URL=url,NETCLAW_HERMES_HUD_API_KEY=key,NETCLAW_HERMES_HUD_PORT=str(port),PYTHON_DOTENV_DISABLED='1',PYTHONUNBUFFERED='1')
            installation='11111111-1111-4111-8111-111111111111'
            (home/'netclaw-hud').mkdir(mode=0o700)
            identity=home/'netclaw-hud/installation.json';identity.write_text(json.dumps({'schemaVersion':1,'installationId':installation}));identity.chmod(0o600)
            log=open(Path(tmp)/'companion.log','w+')
            process=subprocess.Popen([os.environ['NETCLAW_HERMES_PYTHON'],str(ROOT/'mcp-servers/hermes-hud-mcp/hermes_api.py'),'--home',str(home),'--source',os.environ['NETCLAW_HERMES_SOURCE'],'--installation',installation,'--port',str(port)],env=env,stdout=log,stderr=log)
            bridge=Bridge(home,installation,port=port,key=key)
            try:
                for _ in range(120):
                    try:
                        status=bridge.status();break
                    except Exception:
                        if process.poll() is not None:break
                        time.sleep(.25)
                else:self.fail('Companion startup deadline')
                if process.poll() is not None:
                    log.seek(0);self.fail(log.read()[-12000:])
                self.assertTrue(status['protected']);self.assertTrue(status['tools'])
                bridge.open('conversation-A')
                for i,text in enumerate(['remember violet','what was the colour?','SUBNET','continue','finish']):
                    result=bridge.submit('conversation-A',f'request-{i}',f'nonce-{i}',text,60000)
                    for _ in range(240):
                        result=bridge.request_status('conversation-A',f'request-{i}')
                        if result['state'] in ('completed','failed','interrupted','unknown'):break
                        time.sleep(.1)
                    if result['state']!='completed':
                        row=bridge.ledger.request('conversation-A',f'request-{i}')
                        native=bridge.http('GET','/v1/runs/'+row['run_id']) if row['run_id'] else {}
                        log.seek(0);self.fail(str(result)+'\n'+str(native)+'\n'+log.read()[-14000:])
                    if i==1:self.assertIn('violet',result['output'])
                evidence=bridge.ledger.events('conversation-A','request-2')
                self.assertTrue(any(e['state']=='completed' and 'subnet_calculator' in e['tool'] for e in evidence))
                history=bridge.history('conversation-A');self.assertGreaterEqual(len(history['messages']),10)
                # Force real native transcript compaction: immutable invocation proof survives.
                session=bridge.ledger.conversation('conversation-A')['session']
                compact="import sys;sys.path.insert(0,sys.argv[1]);from hermes_state import SessionDB;from pathlib import Path;db=SessionDB(Path(sys.argv[2]));db.archive_and_compact(sys.argv[3],[{'role':'user','content':'COMPACTED violet'}]);db.close()"
                subprocess.run([os.environ['NETCLAW_HERMES_PYTHON'],'-c',compact,os.environ['NETCLAW_HERMES_SOURCE'],str(home/'netclaw-hud/hermes/state.db'),session],env=env,check=True,capture_output=True,text=True)
                self.assertIn('COMPACTED',json.dumps(bridge.history('conversation-A')))
                self.assertEqual(evidence,bridge.ledger.events('conversation-A','request-2'))
                bridge.open('forbidden')
                bridge.submit('forbidden','forbidden-request','forbidden-nonce','FORGED_SHELL',10000)
                for _ in range(150):
                    denied=bridge.request_status('forbidden','forbidden-request')
                    if denied['state'] in ('failed','completed','unknown'):break
                    time.sleep(.1)
                self.assertEqual(denied['state'],'failed',denied)
                self.assertEqual(bridge.ledger.events('forbidden','forbidden-request'),[])
                self.assertNotIn('PRIVATE_OTHER_CONVERSATION_SENTINEL',json.dumps(provider.calls))
                self.assertEqual(original,(home/'config.yaml').read_bytes())
                self.assertIn('Installed qualified subnet-calculator skill',json.dumps(provider.calls))
                for file in ['state.db','response_store.db','runs_idempotency.db']:self.assertFalse((home/file).exists())
                result=subprocess.run(['node',str(ROOT/'tests/hermes-hud/http_acceptance.mjs')],env=env,capture_output=True,text=True,timeout=60)
                if result.returncode:
                    with bridge.ledger.db() as db: rows=[dict(r) for r in db.execute('SELECT id,conversation,state,run_id,result FROM requests')]
                    log.seek(0);self.fail(result.stdout+result.stderr+'\n'+str([{k:r[k] for k in ('id','state','run_id')} for r in rows])+'\n'+log.read()[-10000:])
            finally:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
                provider.close();log.close()
if __name__=='__main__':unittest.main()
