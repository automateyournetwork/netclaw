"""Managed private Hermes companion and official MCP execution client."""
import asyncio
import fcntl
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import time

from .execution import OutcomeUnknown, Refused, digest
from .runtime import ROOT, private_dir, write_private


async def call_stdio(command, args, env, name, arguments, timeout=30):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    async with asyncio.timeout(timeout):
        with open(os.devnull,'w') as errors:
            async with stdio_client(StdioServerParameters(command=str(command),args=list(args),env=env,cwd=str(ROOT)),errlog=errors) as (read,write):
                async with ClientSession(read,write) as session:
                    await session.initialize()
                    response=await session.call_tool(name,arguments)
                    if response.is_error:raise Refused('MCP execution refused')
                    result=response.structured_content
                    if result is None:
                        texts=[block.text for block in response.content if block.type=='text']
                        result=json.loads('\n'.join(texts)) if texts else {}
                    if isinstance(result,dict) and result.get('error'):
                        error=result['error']
                        raise Refused('private runtime refused: '+str(error.get('code','unavailable') if isinstance(error,dict) else error))
                    return result


class HermesRuntime:
    def __init__(self, runtime, broker):
        self.runtime=runtime;self.broker=broker
        self.process=None;self.lock=None;self.log=None;self.env=None;self.port=None

    async def start(self):
        if self.process and self.process.returncode is None:return
        self.runtime.fence(initialize=True)
        file=self.runtime.state/'companion.lock'
        fd=os.open(file,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        self.lock=os.fdopen(fd,'w')
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.lock.close();self.lock=None
            raise Refused('selected federation companion already owned') from None
        try:
            self.env=self.runtime.environment()
            # Read only the selected installation's literal dotenv. Never source it.
            from dotenv import dotenv_values
            if self.runtime.env_file.exists():
                values=dotenv_values(self.runtime.env_file,interpolate=False)
                # Provider configuration is needed only in this protected process.
                for key,value in values.items():
                    if value is not None and (key.endswith(('_API_KEY','_BASE_URL')) or key in ('OPENAI_BASE_URL','ANTHROPIC_BASE_URL')):
                        self.env[key]=value
            self.env.update(PYTHON_DOTENV_DISABLED='1',PYTHONUNBUFFERED='1')
            base=self.runtime.home/'python-runtimes/hermes-hud-agent'
            records=self.runtime.home/'python-runtimes/records'
            def recorded(name,default):
                file=records/name
                return file.read_text().strip() if file.exists() else default
            python=Path(self.env.get('NETCLAW_HERMES_PYTHON') or recorded('hermes-hud-agent-python',base/'venv/bin/python'))
            source=Path(self.env.get('NETCLAW_HERMES_SOURCE') or recorded('hermes-hud-agent-source',base/'source'))
            record=self.runtime.home/'python-runtimes/records/hermes-hud'
            self.bridge_python=record.read_text().strip() if record.exists() else sys.executable
            if not python.is_file() or not source.is_dir():raise Refused('Hermes companion runtime is not installed')
            # Port zero is selected locally, then authenticated readiness verifies
            # the child that acquired it. Failure never kills an existing listener.
            sock=socket.socket();sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1];sock.close()
            self.env.update(NETCLAW_HERMES_FEDERATION_API_KEY=secrets.token_urlsafe(48),NETCLAW_HERMES_FEDERATION_PORT=str(self.port))
            fd=os.open(self.runtime.state/'companion.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
            self.log=os.fdopen(fd,'a')
            self.process=await asyncio.create_subprocess_exec(str(python),str(ROOT/'mcp-servers/hermes-hud-mcp/hermes_api.py'),
                '--home',str(self.runtime.home),'--source',str(source),'--installation',self.runtime.installation,
                '--port',str(self.port),'--namespace','federation',env=self.env,stdout=self.log,stderr=self.log,start_new_session=True)
            import httpx
            async with httpx.AsyncClient(timeout=2,trust_env=False,follow_redirects=False) as client:
                deadline=time.monotonic()+60
                while time.monotonic()<deadline:
                    if self.process.returncode is not None:raise Refused('protected companion startup failed; inspect private companion.log')
                    try:
                        response=await client.get(f'http://127.0.0.1:{self.port}/health/detailed',headers={'Authorization':'Bearer '+self.env['NETCLAW_HERMES_FEDERATION_API_KEY']})
                        status=response.json()
                        if response.status_code==200 and status.get('ready') and status.get('installationId')==self.runtime.installation and status.get('namespace')=='federation':
                            write_private(self.runtime.state/'runtime.json',{'installationId':self.runtime.installation,'pid':self.process.pid,'port':self.port,'ready':True,'harness':'hermes'})
                            return
                    except (httpx.HTTPError,ValueError):pass
                    await asyncio.sleep(.2)
            raise Refused('protected companion readiness deadline exceeded')
        except BaseException:
            await self.close();raise

    @property
    def ready(self):
        return self.process is not None and self.process.returncode is None

    async def close(self):
        if self.process and self.process.returncode is None:
            import signal
            try:os.killpg(self.process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:await asyncio.wait_for(self.process.wait(),10)
            except asyncio.TimeoutError:
                try:os.killpg(self.process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                await self.process.wait()
        self.process=None
        if self.log:self.log.close();self.log=None
        if self.lock:self.lock.close();self.lock=None

    async def call(self, operation, **arguments):
        if not self.process or self.process.returncode is not None:raise Refused('selected federation companion is stopped')
        return await call_stdio(self.bridge_python,['-u',str(ROOT/'mcp-servers/hermes-hud-mcp/federation_server.py')],
                                self.env,'hermes_federation_'+operation,{'installationId':self.runtime.installation,**arguments},timeout=20)

    async def turn(self, prompt, scope, permit, *, on_dispatch=None,progress=None):
        if scope.body_digest!=digest(prompt):raise Refused('body changed after authorization')
        await self.broker.check(permit,scope.request)
        await self.call('open',conversationId=scope.conversation)
        if on_dispatch:on_dispatch()
        dispatched=False
        try:
            dispatched=True
            state=await self.call('submit',conversationId=scope.conversation,requestId=scope.request,text=prompt,
                                  scope=scope.as_dict(),permit=permit,deadlineMs=max(1000,int((scope.deadline-time.time())*1000)))
            last_progress=0
            while state.get('state') not in ('completed','failed','cancelled','interrupted','unknown'):
                if time.time()>=scope.deadline:raise OutcomeUnknown('Hermes deadline exceeded after admission')
                await asyncio.sleep(.25)
                state=await self.call('request_status',conversationId=scope.conversation,requestId=scope.request)
                if progress and time.monotonic()-last_progress>=10:
                    progress('Hermes '+str(state.get('state','working'))+'; awaiting owned result')
                    last_progress=time.monotonic()
            if state.get('state')=='unknown':raise OutcomeUnknown('Hermes outcome is unknown; reconcile owned request')
            if state.get('state')!='completed':raise Refused('Hermes run '+str(state.get('state')))
            usage=state.get('usage') or {}
            tokens=usage.get('total_tokens')
            return state.get('output',''),tokens if isinstance(tokens,int) else None
        except asyncio.CancelledError:
            if dispatched:
                try:await asyncio.shield(self.call('stop',conversationId=scope.conversation,requestId=scope.request))
                except Exception:pass
            raise
        except Refused as error:
            if dispatched and (not self.process or self.process.returncode is not None):
                raise OutcomeUnknown("Hermes companion lost after dispatch; do not resubmit") from error
            raise
        except OutcomeUnknown:raise
        except Exception as error:
            if dispatched:raise OutcomeUnknown('Hermes response unavailable after dispatch') from error
            raise


# In-process binding is established only by the selected daemon/member startup.
# Status/probing and arbitrary ingresses cannot autostart another companion.
ACTIVE = {}


async def run_turn(prompt, execution):
    if not isinstance(execution,dict):raise Refused('Hermes ingress requires trusted execution scope')
    scope=execution['scope'];runtime=ACTIVE.get(scope.installation)
    if runtime is None:raise Refused('selected Hermes federation runtime is not ready')
    return await runtime.turn(prompt,scope,execution['permit'],on_dispatch=execution.get('on_dispatch'),progress=execution.get('progress'))
