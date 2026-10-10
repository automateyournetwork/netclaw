#!/usr/bin/env python3
"""Dedicated qualified Hermes API process. Never patches the owner's gateway."""
import argparse
import asyncio
import contextvars
import hashlib
import hmac
import json
import os
from pathlib import Path
import signal
import sys
from ledger import Ledger, HudError, identifier, private_dir
from policy import verify_source, qualified_servers, qualified_skills, ToolPolicy

REQUEST=contextvars.ContextVar('netclaw_request',default=None)

class NoMemory:
    def checkout(self,*args,**kwargs):return None
    def checkin(self,*args,**kwargs):pass
    def close_all(self):pass

async def serve(home,source,installation,port):
    manifest=verify_source(source)
    from ruamel.yaml import YAML
    yaml=YAML(typ='safe')
    original=Path(home).resolve();config_file=original/'config.yaml'
    config=yaml.load(config_file.read_text()) or {}
    config_hash=hashlib.sha256(config_file.read_bytes()).hexdigest()
    servers,entries=qualified_servers(config,home=original)
    state=private_dir(original/'netclaw-hud');shadow=private_dir(state/'hermes')
    if (shadow/'installs').exists():
        raise HudError('configuration_missing','Unexpected companion dependency overlay. Stop the test companion and preserve/move netclaw-hud/hermes/installs before relaunching the qualified environment.')
    provenance={'schemaVersion':1,'installationId':installation,'python':str(Path(sys.executable).resolve()),'source':str(Path(source).resolve()),'revision':manifest['revision'],'configurationDigest':config_hash}
    launch_file=state/'launch.json';temporary=state/('launch-'+str(os.getpid())+'.tmp')
    with open(temporary,'x',encoding='utf8') as stream:
        json.dump(provenance,stream);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,launch_file)
    # Isolated generated profile prevents upstream plugin startup/migration,
    # dynamic memory and default DB paths from touching the ordinary profile.
    model=config.get('model') or {}
    if isinstance(model,dict):model={k:v for k,v in model.items() if k in ('default','model','provider','base_url','context_length')}
    derived={'model':model,'mcp_servers':servers,'toolsets':[],
             'platform_toolsets':{'api_server':[]},'tool_search':{'enabled':'off'},
             'memory':{'memory_enabled':False,'user_profile_enabled':False},
             'security':{'allow_lazy_installs':False},
             # Auxiliary clients bypass the protected inference hook. HUD titles
             # are local metadata; long contexts must fail rather than silently
             # dispatching an unguarded title/compression provider request.
             'auxiliary':{'title_generation':{'enabled':False,'model_upgrade_enabled':False}},
             'compression':{'enabled':False},
             'plugins':{'enabled':[]},
             'agent':{'max_iterations':30},'display':{'interim_assistant_messages':False},
             'approvals':{'mode':'manual','unattended_mode':'deny'}}
    target=shadow/'config.yaml'
    import io
    buffer=io.StringIO();yaml.dump(derived,buffer)
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as stream:stream.write(buffer.getvalue())
    os.environ['HERMES_HOME']=str(shadow)
    os.environ['PYTHON_DOTENV_DISABLED']='1'
    # The protected companion must not install extras or discover optional
    # plugins during admission/provider resolution. Dependencies are explicit.
    os.environ['HERMES_DISABLE_LAZY_INSTALLS']='1'
    os.environ['HERMES_CWD']=str(shadow)
    os.chdir(shadow)
    sys.path.insert(0,str(Path(source).resolve()))
    from hermes_cli.plugins_discovery import suppress_plugin_discovery
    with suppress_plugin_discovery():
        from aiohttp import web
        import run_agent
        from gateway.platforms import api_server
        from gateway.config import PlatformConfig
        from hermes_state import SessionDB
        from tools.mcp_tool_discovery import discover_mcp_tools
        if servers:
            discovered=await asyncio.to_thread(discover_mcp_tools,list(servers))
            if set(entries)-set(discovered):
                raise HudError('policy_unverified','Qualified MCP discovery failed; check the selected component runtimes.')
        ledger=Ledger(state/'ledger.db',installation)
        policy=ToolPolicy(entries,config_file,config_hash)
        policy.runtime_source=source
        policy.skill_context=qualified_skills(original)
        from protected_agent import protected_class
        run_agent.AIAgent=protected_class(run_agent.AIAgent,policy,ledger,REQUEST)
        key=os.environ.get('NETCLAW_HERMES_HUD_API_KEY','')
        if len(key)<32:raise HudError('configuration_missing','Private companion key is missing.')
        allowed={('GET','/health/detailed'),('GET','/v1/capabilities'),('GET','/api/model/options'),
                 ('GET','/v1/skills'),('GET','/v1/toolsets'),('POST','/api/sessions'),
                 ('GET','/api/sessions/{session_id}'),('GET','/api/sessions/{session_id}/messages'),
                 ('POST','/v1/runs'),('GET','/v1/runs/{run_id}'),
                 ('POST','/v1/runs/{run_id}/approval'),('POST','/v1/runs/{run_id}/stop')}
        class Companion(api_server.APIServerAdapter):
            def _http_route_table(self):return [row for row in super()._http_route_table() if row[:2] in allowed]
            async def _handle_health_detailed(self,request):
                try:policy.check_sources()
                except HudError:return web.json_response({'ready':False,'code':'policy_unverified'},status=503)
                with ledger.db() as db: verified=db.execute("SELECT 1 FROM metadata WHERE key='verified-policy' AND value=?",(policy.fingerprint,)).fetchone() is not None
                return web.json_response({'ready':True,'runtime':'hermes','release':manifest['release'],
                    'installed':True,'authenticated':True,'providerConfigured':'unverified',
                    'revision':manifest['revision'],'installationId':installation,
                    'protected':True,'tools':sorted(entries),'toolQualification':'source-reviewed-read-only',
                    'executionVerified':verified,'qualifiedSkills':['subnet-calculator'] if policy.skill_context else [],'model':model if isinstance(model,str) else model.get('default') or model.get('model'),
                    'limitations':['write execution','attachments','model lock','effort','federation','hosted avatar']})
        # HERMES_HOME was set before imports/construction, so all default native
        # stores target the private derived profile. Explicit session DB is retained.
        adapter=Companion(PlatformConfig(enabled=True,extra={'host':'127.0.0.1','port':port,'key':key}))
        adapter._session_db=SessionDB(shadow/'state.db')
        adapter._memory_sessions=NoMemory()
        if not adapter._run_idempotency_store.durable:raise HudError('configuration_missing')
        @web.middleware
        async def auth_scope(request,handler):
            if request.path.startswith('/p/') or not hmac.compare_digest(request.headers.get('Authorization',''),'Bearer '+key):
                return web.json_response({'error':'Unavailable'},status=401)
            token=None
            if request.method=='POST' and request.path=='/v1/runs':
                try:
                    request_id=identifier(request.headers.get('X-NetClaw-Request-ID'))
                    body=await request.json()
                    with ledger.db() as db:row=db.execute('SELECT * FROM requests WHERE id=?',(request_id,)).fetchone()
                    if not row or row['state']!='submitting' or body.get('session_id')!=ledger.conversation(row['conversation'])['session']:raise HudError('owner_invalid')
                    if body.get('input')!=row['body']:raise HudError('input_invalid')
                    token=REQUEST.set(request_id)
                except Exception:return web.json_response({'error':'Invalid owned admission'},status=403)
            try:return await handler(request)
            finally:
                if token is not None:REQUEST.reset(token)
        app=web.Application(middlewares=[auth_scope],client_max_size=2*1024*1024)
        for method,route,handler in adapter._http_route_table():app.router.add_route(method,route,handler)
        runner=web.AppRunner(app,access_log=None);await runner.setup()
        await web.TCPSite(runner,'127.0.0.1',port).start()
        stopped=asyncio.Event()
        loop=asyncio.get_running_loop()
        for sig in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(sig,stopped.set)
        try:await stopped.wait()
        finally:
            await runner.cleanup();await adapter.disconnect()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--home',required=True);parser.add_argument('--source',required=True);parser.add_argument('--installation',required=True);parser.add_argument('--port',type=int,default=8643)
    args=parser.parse_args();os.umask(0o077)
    try:asyncio.run(serve(args.home,args.source,args.installation,args.port))
    except Exception as error:
        from bridge import sanitize
        detail=': '+sanitize(str(error)) if isinstance(error,HudError) else ''
        print(f'Hermes HUD companion unavailable: {getattr(error,"code",type(error).__name__)}{detail}',file=sys.stderr)
        sys.exit(1)
