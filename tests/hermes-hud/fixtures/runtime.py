"""Owned real-process test fixture. All credentials and provider calls are synthetic."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import httpx
from provider import Provider

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'mcp-servers/hermes-hud-mcp'))
from bridge import Bridge

def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));return sock.getsockname()[1]

class RuntimeFixture:
    def __init__(self, deadline=60000):
        self.temp=tempfile.TemporaryDirectory(prefix='hermes-process-')
        self.base=Path(self.temp.name).resolve();self.home=self.base/'Hermes Home';self.home.mkdir(mode=0o700)
        self.installation='22222222-2222-4222-8222-222222222222'
        self.key='fixture-private-key-'+os.urandom(24).hex()
        self.provider=Provider();url=self.provider.start();self.processes=[];self.logs=[]
        self.api_port=port();self.companion_port=port();self.proxy_calls=[];self.drop_submit=False
        records=self.home/'python-runtimes/records';records.mkdir(parents=True)
        for name,interpreter in [('hermes-hud',sys.executable),('subnet-calc',os.environ['NETCLAW_SUBNET_PYTHON'])]:
            (records/name).write_text(interpreter+'\n')
        self.config={'model':{'default':'hud-fixture','provider':'custom','base_url':url},'mcp_servers':{'subnet-calc-mcp':{
            'command':'python3','args':['-u',str(ROOT/'scripts/component-launch.py'),'subnet-calc','--server','subnet-calc-mcp'],
            'env':{'NETCLAW_RUNTIME_ROOT':str(self.home/'python-runtimes'),'NETCLAW_RUNTIME_ENV':str(self.home/'.env')}}}}
        (self.home/'config.yaml').write_text(json.dumps(self.config))
        (self.home/'.env').write_text('OPENAI_API_KEY=fixture-only-key\n')
        skill=self.home/'skills/subnet-calculator';skill.mkdir(parents=True)
        shutil.copyfile(ROOT/'workspace/skills/subnet-calculator/SKILL.md',skill/'SKILL.md')
        state=self.home/'netclaw-hud';state.mkdir(mode=0o700)
        identity=state/'installation.json';identity.write_text(json.dumps({'schemaVersion':1,'installationId':self.installation}));identity.chmod(0o600)
        owner=self
        class Proxy(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def forward(self):
                owner.proxy_calls.append((self.command,self.path))
                body=self.rfile.read(int(self.headers.get('Content-Length',0)))
                headers={k:v for k,v in self.headers.items() if k.lower() in ('authorization','idempotency-key','x-netclaw-request-id','content-type')}
                try:
                    response=httpx.request(self.command,f'http://127.0.0.1:{owner.companion_port}'+self.path,content=body,headers=headers,timeout=15,trust_env=False)
                except httpx.HTTPError:
                    self.send_response(503);self.end_headers();return
                if owner.drop_submit and self.command=='POST' and self.path=='/v1/runs':
                    owner.drop_submit=False;self.close_connection=True;self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
                self.send_response(response.status_code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(response.content)
            do_GET=forward;do_POST=forward
        self.proxy=ThreadingHTTPServer(('127.0.0.1',0),Proxy)
        self.proxy_thread=threading.Thread(target=self.proxy.serve_forever,daemon=True);self.proxy_thread.start()
        self.env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','SYSTEMROOT')}
        self.env.update(HOME=str(self.base),NETCLAW_RUNTIME='hermes',HERMES_HOME=str(self.home),
            NETCLAW_HERMES_HUD_API_KEY=self.key,NETCLAW_HERMES_HUD_PORT=str(self.proxy.server_port),
            OPENAI_API_KEY='fixture-only-key',OPENAI_BASE_URL=url,PYTHON_DOTENV_DISABLED='1',
            HUD_PORT=str(self.api_port),HUD_UI_PORT=str(port()),HUD_CHAT_TIMEOUT_MS=str(deadline))
        self.bridge=Bridge(self.home,self.installation,key=self.key,port=self.proxy.server_port)
        self.client=httpx.Client(base_url=f'http://127.0.0.1:{self.api_port}',timeout=20,trust_env=False)
        self.companion=None;self.hud=None
    def launch(self,args,cwd=ROOT):
        log=open(self.base/f'process-{len(self.logs)}.log','w+');self.logs.append(log)
        child=subprocess.Popen(args,cwd=cwd,env=self.env,stdout=log,stderr=log);self.processes.append(child);return child
    def start_companion(self):
        self.companion=self.launch([os.environ['NETCLAW_HERMES_PYTHON'],str(ROOT/'mcp-servers/hermes-hud-mcp/hermes_api.py'),
            '--home',str(self.home),'--source',os.environ['NETCLAW_HERMES_SOURCE'],'--installation',self.installation,'--port',str(self.companion_port)])
        self.wait(lambda:self.bridge.status().get('ready'),child=self.companion)
    def start_hud(self):
        self.hud=self.launch(['node','server.js'],ROOT/'ui/netclaw-visual')
        self.wait(lambda:self.client.get('/api/health').is_success,child=self.hud)
    def start(self):
        self.start_companion();self.start_hud();self.client.post('/api/hud/session',json={}).raise_for_status();return self
    def wait(self,callback,timeout=25,child=None):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if child is not None and child.poll() is not None:raise AssertionError(f'Fixture child exited: {child.returncode}; private log at {self.base}')
            try:
                value=callback()
                if value:return value
            except (httpx.HTTPError,ValueError):pass
            except Exception as error:
                if not hasattr(error,'code'):raise
            time.sleep(.1)
        raise AssertionError('Timed out waiting for actual fixture state')
    def submit(self,thread,nonce,text):
        response=self.client.post('/api/chat/requests',json={'hudThread':thread,'clientNonce':nonce,'message':text})
        response.raise_for_status();return response.json()
    def status(self,request):
        response=self.client.get('/api/chat/requests/'+request);response.raise_for_status();return response.json()
    def settled(self,request):
        return self.wait(lambda:(v if (v:=self.status(request))['state'] in ('completed','failed','unknown','cancelled','interrupted') else None))
    def stop_process(self,process,kill=False):
        if process and process.poll() is None:
            process.kill() if kill else process.terminate()
            try:process.wait(timeout=8)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=8)
    def close(self):
        self.provider.release.set()
        for child in reversed(self.processes):self.stop_process(child)
        self.client.close();self.bridge.client.close();self.proxy.shutdown();self.proxy.server_close();self.proxy_thread.join();self.provider.close()
        for log in self.logs:log.close()
        self.temp.cleanup()
