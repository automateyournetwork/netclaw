#!/usr/bin/env python3
"""Owned guards around pinned upstream tools; registration remains official MCP."""
import argparse
import asyncio
import functools
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sys
import typing

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/lib'))
from pyats_testbeds import compose, catalog, environment_policy, TestbedError
from migration_artifacts import PrivateMigration, Refused, digest, pack
from artifacts import read_file


def encoded(value):return json.dumps(value,ensure_ascii=True)


def rejected(code):
    return encoded({'status':'error','code':code,'activeUnchanged':True})


async def private_operation(coro):
    # Upstream runs synchronous device work in an executor. Cancellation cannot
    # stop that thread: retain the inventory/connection guards and caller lock
    # until it exits, then propagate cancellation with the attempt still unknown.
    operation=asyncio.create_task(coro)
    cancelled=False
    while not operation.done():
        try: await asyncio.shield(operation)
        except asyncio.CancelledError: cancelled=True
        except Exception: break
    if cancelled:
        if not operation.cancelled(): operation.exception()
        raise asyncio.CancelledError
    return operation.result()


class ManagedTestbeds:
    def __init__(self,server,env=None):
        self.server=server;self.env=os.environ if env is None else env
        self.policy=environment_policy(self.env)
        self.lock=asyncio.Lock();self.used=set();self.candidates={};self.validated={}
        self.private_write_uncertain=False
        self.original={name:getattr(server,name) for name in dir(server) if name.startswith('pyats_') and inspect.iscoroutinefunction(getattr(server,name))}
        self.private = PrivateMigration(self.env['NETCLAW_CHANGE_ROOT']) if self.env.get('NETCLAW_CHANGE_ROOT') else None
        # The upstream operation-log tool is model-visible. Do not put private
        # configuration snippets or exception strings into it, even after errors.
        if hasattr(server, '_log_op'):
            original_log = server._log_op
            def private_log(tool, device, detail, status, error=None):
                if tool in ('pyats_configure_device','pyats_show_running_config'):
                    return original_log(tool, device, 'Private configuration operation; inspect local evidence.', status)
                return original_log(tool, device, detail, status, error)
            server._log_op = private_log

    def private_inventory(self):
        if not self.private: raise Refused('selected_private_change_root_unavailable')
        tb = self.server._load_testbed()
        entry = self.server._dynamic_testbeds.active_entry()
        raw = pack(entry.raw) if entry else read_file(Path(self.server.TESTBED_PATH))[0]
        devices=[]
        for name, device in tb.devices.items():
            connections = device.connections
            # An ambiguous/console/proxy route cannot be equated with the HUD's
            # authorized SSH endpoint. Qualify the ordinary single-cli route.
            if set(connections)-{'cli','defaults'} or 'cli' not in connections: continue
            c=connections['cli']
            if c.get('protocol')!='ssh' or c.get('proxy') or c.get('command') or c.get('via'): continue
            if connections.get('defaults',{}).get('via') not in (None,'cli'): continue
            os_name=str(device.os)
            endpoint={'id':str(name),'host':str(c.get('ip','')),'port':int(c.get('port',22)),
                      'protocol':'ssh','os':os_name,'route':'pyats_configure_device' if os_name in ('ios','iosxe','junos') else 'unqualified'}
            if endpoint['host'] and 0<endpoint['port']<65536: devices.append(endpoint)
        fingerprint=digest(raw+pack(devices))
        return self.private.inventory(fingerprint, devices),tb

    async def private_call(self,name,args):
        current,tb=self.private_inventory()
        device=next((d for d in current['devices'] if d['id']==args['device_name']),None)
        if not device or device['route']=='unqualified': raise Refused('private_device_route_unqualified')
        if getattr(self.server,'_CONN_CACHE_TTL',0)>0: raise Refused('private_route_requires_uncached_connections')
        actual=tb.devices[args['device_name']]
        connected=getattr(actual,'is_connected',False)
        is_connected=connected() if callable(connected) else connected
        if is_connected: raise Refused('private_route_requires_fresh_connection')
        connect_args=getattr(self.server,'_get_testbed_connection_args',None)
        if connect_args is None: raise Refused('private_connection_contract_unavailable')
        if any(not job.done() for job in getattr(getattr(self.server,'task_runtime',None),'jobs',{}).values()):
            raise Refused('private_route_requires_idle_inventory')
        # Hold the exact loaded inventory throughout the existing original tool.
        # This prevents static testbed cache expiry from changing its destination.
        logfile=self.private.log_path()
        load=self.server._load_testbed;self.server._load_testbed=lambda:tb
        def private_connection_args(device):
            values=dict(connect_args(device))
            values.update(init_config_commands=[],init_exec_commands=[],log_stdout=False,logfile=logfile)
            return values
        self.server._get_testbed_connection_args=private_connection_args
        try:
            if name=='pyats_configure_device':
                if self.private_write_uncertain: raise Refused('inspect_state_and_restart_uncertain_private_apply_process')
                if args.get('config_commands') is not None or not args.get('artifact_ref') or not args.get('grant_ref'):
                    raise Refused('choose_inline_or_exact_artifact_input')
                commands=self.private.claim(args['grant_ref'],args['artifact_ref'],current,device)
                self.private_write_uncertain=True
                # Preserve the original tool and its dangerous-command guards.
                try:
                    result=await private_operation(self.original[name](device_name=args['device_name'],config_commands=commands))
                    evidence=self.private.publish(result.encode(),'configuration-result')
                    success=json.loads(result).get('status')=='success'
                    if success:self.private_write_uncertain=False
                    return encoded({'status':'applied_unverified' if success else 'unknown','evidence':evidence,
                                    'replay':False,'verification':'required','grant_ref':args['grant_ref']})
                except Exception:
                    return encoded({'status':'unknown','replay':False,'grant_ref':args['grant_ref'],'code':'inspect_live_state_before_further_writes'})
            if args.get('output_mode')!='private': raise Refused('unknown_collection_output_mode')
            # Keep the original read-tool identity/error/permission boundary;
            # adapt only its fixed internal command for Junos. No caller-chosen
            # command, shell, path or alternate tool is accepted here.
            collector=getattr(self.server,'_execute_get_running_config_str',None)
            if device['os']=='junos':
                if collector is None: raise Refused('private_collection_os_unqualified')
                def junos_collection(name):
                    connected=None
                    try:
                        connected=self.server._get_device(name)
                        return connected.execute('show configuration | display set | no-more')
                    finally: self.server._disconnect_device(connected)
                self.server._execute_get_running_config_str=junos_collection
            try: result=json.loads(await private_operation(self.original[name](device_name=args['device_name'])))
            finally:
                if device['os']=='junos':self.server._execute_get_running_config_str=collector
            if result.get('status')!='completed' or not isinstance(result.get('output'),str):
                raise Refused('private_collection_failed')
            artifact=self.private.collection(result['output'],device,change_ref=args.get('change_ref'),current=current)
            return encoded({'status':'completed','device':args['device_name'],'artifact':artifact,'content':'private'})
        finally:
            self.server._load_testbed=load
            self.server._get_testbed_connection_args=connect_args

    def fingerprint(self,name):
        raw=self.server._dynamic_testbeds.get(name).raw
        return hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()

    def busy(self):
        runtime=getattr(self.server,'task_runtime',None)
        return self.lock.locked() or any(not job.done() for job in getattr(runtime,'jobs',{}).values())

    async def build(self,envelope,dry_run=False):
        if self.policy['mode']!='dynamic':raise TestbedError('select_dynamic_mode_and_sources_before_composition')
        selected=self.policy['sources'] if self.policy['mode']=='dynamic' else None
        candidate=compose(envelope,selected=selected)
        name=candidate['arguments']['name']
        if name in self.used or name in self.server._dynamic_testbeds.names():
            raise TestbedError('candidate_name_already_used')
        # Reserve before invoking upstream; interrupted/error candidates cannot
        # become a different inventory under a previously reviewed name.
        if not dry_run:self.used.add(name)
        result=json.loads(await self.original['pyats_testbed_build'](**candidate['arguments'],dry_run=dry_run))
        report=result.get('report',{})
        if result.get('status')!='completed' or report.get('devices_built')!=candidate['preview']['devices'] or report.get('devices_skipped'):
            raise TestbedError('upstream_build_incomplete')
        if not dry_run:
            self.candidates[name]={'fingerprint':self.fingerprint(name),'preview':candidate['preview']}
        return encoded({'status':'completed','stored':not dry_run,'active':self.server._dynamic_testbeds.active_name or ('static' if self.server.TESTBED_PATH else 'none'),
                        'preview':candidate['preview'],'next':'pyats_testbed_validate; then explicit pyats_testbed_activate',
                        'lifetime':'this MCP process only'})

    async def call(self,name,args):
        if name=='pyats_testbed_activate' and self.busy():return rejected('inventory_busy_retry_after_operations_complete')
        async with self.lock:
            try:
                if name=='pyats_configure_device' and (args.get('artifact_ref') or args.get('grant_ref')):
                    return await self.private_call(name,args)
                if name=='pyats_show_running_config' and (args.get('output_mode','inline')!='inline' or args.get('change_ref')):
                    return await self.private_call(name,args)
                if name=='pyats_configure_device':
                    args={k:v for k,v in args.items() if k not in ('artifact_ref','grant_ref')}
                    if args.get('config_commands') is None: raise Refused('configuration_input_required')
                if name=='pyats_show_running_config':args={k:v for k,v in args.items() if k not in ('output_mode','change_ref')}
                if name=='netclaw_testbed_compose':return await self.build(args['envelope'])
                if name=='pyats_testbed_build':
                    defaults=inspect.signature(self.original[name]).parameters
                    for key,value in args.items():
                        if key in ('name','data','source','dry_run'):continue
                        if value!=defaults[key].default:raise TestbedError('use_managed_composition_envelope')
                    if args.get('source')!='inline' or not isinstance(args.get('data'),dict) or args['data'].get('name')!=args.get('name'):
                        raise TestbedError('use_inline_composition_envelope_or_netclaw_testbed_compose')
                    return await self.build(args['data'],args.get('dry_run',False))
                if name=='pyats_testbed_sources':
                    return encoded({'status':'completed','mode':self.policy['mode'],'selected':self.policy['sources'],
                        'active':self.server._dynamic_testbeds.active_name or ('static' if self.server.TESTBED_PATH else 'none'),
                        'sources':catalog(),'managedRoute':'existing source MCP or reviewed export → netclaw_testbed_compose',
                        'nativeFetch':'upstream capability; managed raw file/REST/native fetching is disabled',
                        'lifetime':'this MCP process only; restart requires rebuild, validate and activate'})
                if name=='pyats_testbed_source_inventories':
                    raise TestbedError('discover_scoped_inventories_with_existing_source_mcp')
                candidate_name=args.get('name')
                if name in ('pyats_testbed_validate','pyats_testbed_get','pyats_testbed_activate','pyats_testbed_delete') and candidate_name!='static':
                    candidate=self.candidates.get(candidate_name)
                    if not candidate or self.fingerprint(candidate_name)!=candidate['fingerprint']:
                        raise TestbedError('candidate_missing_or_changed_rebuild_required')
                if name=='pyats_testbed_activate':
                    if candidate_name=='static':
                        if self.policy['mode']=='dynamic' or not self.server.TESTBED_PATH:raise TestbedError('no_static_fallback_in_dynamic_mode')
                    elif self.validated.get(candidate_name)!=self.fingerprint(candidate_name):
                        raise TestbedError('candidate_requires_successful_schema_and_credential_validation')
                    elif self.server.tbb.unresolved_env(self.server._dynamic_testbeds.get(candidate_name).raw):
                        raise TestbedError('device_credentials_missing')
                if name=='pyats_testbed_delete' and candidate_name==self.server._dynamic_testbeds.active_name:
                    raise TestbedError('active_candidate_cannot_be_deleted')
                result=await self.original[name](**args)
                if name=='pyats_list_devices' and self.private:
                    try:
                        current,_=self.private_inventory()
                        value=json.loads(result);value['privateMigration']={k:current[k] for k in ('harness','testbed','installation')}
                        result=encoded(value)
                    except Exception: pass  # Regular device listing remains available.
                if name.startswith('pyats_testbed_'):
                    result=json.loads(result)
                    if name=='pyats_testbed_validate':
                        missing=result.get('credential_env',{}).get('unset_on_server',[])
                        valid=result.get('status')=='completed' and str(result.get('pyats_schema','')).startswith('ok (') and not missing
                        if valid and candidate_name!='static':self.validated[candidate_name]=self.fingerprint(candidate_name)
                        else:self.validated.pop(candidate_name,None)
                        safe={'status':'completed' if valid else 'invalid','name':candidate_name,
                              'pyats_schema':'valid' if str(result.get('pyats_schema','')).startswith('ok (') else 'invalid',
                              'missingCredentialReferences':missing,'devices':result.get('devices',0),
                              'reachability':'checked' if args.get('check_reachability') else 'not_checked',
                              'login':'not_checked','execution':'not_checked'}
                        if args.get('check_reachability'):safe['reachabilityResults']=result.get('reachability',{})
                        return encoded(safe)
                    if result.get('status')!='completed':raise TestbedError('upstream_testbed_operation_failed')
                    if name=='pyats_testbed_delete':
                        self.candidates.pop(candidate_name,None);self.validated.pop(candidate_name,None)
                    if name=='pyats_testbed_get' and candidate_name!='static':result['provenance']=self.candidates[candidate_name]['preview']['sources']
                    if name=='pyats_testbed_list':result['lifetime']='this MCP process only';result['mode']=self.policy['mode']
                    return encoded(result)
                return result
            except (TestbedError,Refused) as exc:return rejected(str(exc))
            except Exception:return rejected('managed_testbed_operation_failed')

    async def register(self):
        # Keep original tool schemas/annotations while replacing their execution
        # function. Resolved annotations avoid closure globals affecting schemas.
        for tool in await self.server.mcp.list_tools():
            original=self.original.get(tool.name)
            if original is None:raise RuntimeError('Unrecognized upstream tool contract')
            signature=inspect.signature(original);hints=typing.get_type_hints(original)
            signature=signature.replace(parameters=[p.replace(annotation=hints.get(p.name,p.annotation)) for p in signature.parameters.values()],return_annotation=hints.get('return',signature.return_annotation))
            if tool.name=='pyats_configure_device':
                signature=signature.replace(parameters=[p.replace(default=None) if p.name=='config_commands' else p for p in signature.parameters.values()]+[
                    inspect.Parameter('artifact_ref',inspect.Parameter.KEYWORD_ONLY,default=None,annotation=typing.Optional[str]),
                    inspect.Parameter('grant_ref',inspect.Parameter.KEYWORD_ONLY,default=None,annotation=typing.Optional[str])])
            if tool.name=='pyats_show_running_config':
                signature=signature.replace(parameters=list(signature.parameters.values())+[
                    inspect.Parameter('output_mode',inspect.Parameter.KEYWORD_ONLY,default='inline',annotation=str),
                    inspect.Parameter('change_ref',inspect.Parameter.KEYWORD_ONLY,default=None,annotation=typing.Optional[str])])
            def factory(tool_name,fn,sig):
                @functools.wraps(fn)
                async def wrapper(*args,**kwargs):
                    bound=sig.bind(*args,**kwargs);bound.apply_defaults()
                    return await self.call(tool_name,dict(bound.arguments))
                wrapper.__signature__=sig
                return wrapper
            self.server.mcp.remove_tool(tool.name)
            description=tool.description
            if tool.name=='pyats_configure_device':description+=' Private migration: omit config_commands and supply artifact_ref plus API-issued grant_ref. Same tool authorization applies. Unknown outcomes never replay. Results contain private evidence metadata only; behavior verification is separate.'
            if tool.name=='pyats_show_running_config':description+=' Use output_mode=private for bounded local artifact metadata without model-visible configuration. Optional change_ref captures the exact record baseline during PREPARE. No caller-chosen path; fixed IOS/IOS-XE and Junos display-set collection. Live vendor qualification is separate.'
            if tool.name=='pyats_testbed_build':description='Managed build: source=inline and data=reviewed composition envelope (same name). Prefer netclaw_testbed_compose. Raw native/file/REST fetch, arbitrary mappings, static merge and activate=True are refused.'
            if tool.name=='pyats_testbed_source_inventories':description='Managed source inventories are discovered with the selected source MCP. This tool returns guidance; it does not fetch native Itential inventory.'
            self.server.mcp.add_tool(factory(tool.name,original,signature),name=tool.name,description=description,annotations=tool.annotations)
        async def netclaw_testbed_compose(envelope:dict) -> str:
            """Build an immutable candidate from scoped source records; no activation or device I/O. Envelope schema1: name, sources[{kind,owner,scope,capturedAt,complete:true,total,records,mapping?,osMap?,defaults:{port:22}?,endpoints?}], credentials? (device env references only), maxAgeSeconds?. See docs/DYNAMIC-TESTBEDS.md. Review preview, call pyats_testbed_validate(check_reachability=false), then explicitly activate. Inventory lasts for this MCP process."""
            return await self.call('netclaw_testbed_compose',{'envelope':envelope})
        self.server.mcp.add_tool(netclaw_testbed_compose,annotations=self.server._STATEFUL)


def main():
    os.umask(0o077)  # Includes upstream/Unicon's own diagnostic files.
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--upstream',required=True,type=Path)
    args=parser.parse_args()
    choice=environment_policy(os.environ)
    os.environ['PYTHON_DOTENV_DISABLED']='1'
    if choice['mode']=='dynamic':
        os.environ.pop('PYATS_TESTBED_PATH',None);os.environ['PYATS_MCP_DYNAMIC_ONLY']='1'
    sys.path.insert(0,str(args.upstream.resolve().parent))
    spec=importlib.util.spec_from_file_location('netclaw_owned_pyats',args.upstream)
    server=importlib.util.module_from_spec(spec);sys.modules[spec.name]=server;spec.loader.exec_module(server)
    required=('pyats_testbed_build','pyats_testbed_validate','pyats_testbed_activate','pyats_testbed_sources')
    if any(not hasattr(server,name) for name in required):raise RuntimeError('Pinned dynamic upstream runtime required')
    managed=ManagedTestbeds(server);asyncio.run(managed.register())
    token=os.environ.get('NETCLAW_PYATS_HTTP_TOKEN')
    if token:
        import uvicorn
        from pyats_session import BearerAuth
        app=server.mcp.streamable_http_app(json_response=True,stateless_http=True,host='127.0.0.1')
        uvicorn.run(BearerAuth(app,token),host='127.0.0.1',port=int(os.environ['PYATS_MCP_HTTP_PORT']),log_level='warning')
    else:
        server.mcp.run(transport='streamable-http',host='127.0.0.1',port=int(os.environ['PYATS_MCP_HTTP_PORT']),json_response=True,stateless_http=True)


if __name__=='__main__':
    try:main()
    except Exception:
        print('Managed pyATS failed to start; verify the pinned runtime and selected testbed policy.',file=sys.stderr)
        raise SystemExit(1)
