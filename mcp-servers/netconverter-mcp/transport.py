"""Fixed-destination official MCP clients. No automatic mutation retry or auth fallback."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid
import sys

from artifacts import MAX_BYTES, Refused, directory, publish_file, read_file
from core import API_URL, MCP_URL, canonical, digest

MAX_RESULT = 2 * 1024 * 1024
READS = frozenset({'get_account','list_jobs','vendor_capability_lookup','get_job_brief',
                  'get_evidence','get_report','kb_search','kb_explain','fetch'})
BASE = frozenset({'submit_file','job_status','wait_for_job','account','download'})
VENDOR = re.compile(r'[a-z0-9_]{2,40}\Z')


async def response_guard(response):
    """Bound even chunked responses before JSON buffering/decompression."""
    import httpx2
    if 300<=response.status_code<400: raise Refused('upstream_redirect_refused')
    if response.headers.get('content-encoding','identity').lower() not in ('','identity'):
        raise Refused('compressed_upstream_response_refused')
    length=response.headers.get('content-length')
    if length and (not length.isdecimal() or int(length)>MAX_RESULT): raise Refused('upstream_result_too_large')
    if response.is_stream_consumed:
        if len(response.content)>MAX_RESULT: raise Refused('upstream_result_too_large')
        return
    original=response.stream
    class Bounded(httpx2.AsyncByteStream):
        async def __aiter__(self):
            size=0
            async for chunk in original:
                size+=len(chunk)
                if size>MAX_RESULT: raise Refused('upstream_result_too_large')
                yield chunk
        async def aclose(self): await original.aclose()
    response.stream=Bounded()


def child_environment(config):
    # HOME preserves the operator's license location; explicit key mode and a
    # required nonempty key prevent borrowing its stored authentication.
    if not config.key: raise Refused('credential_required')
    env={k:os.environ[k] for k in ('HOME','USERPROFILE','SYSTEMROOT','APPDATA','LOCALAPPDATA','LANG') if k in os.environ}
    env.update({'PATH':os.defpath,'PYTHON_DOTENV_DISABLED':'1','PYTHONNOUSERSITE':'1',
                'NETCONVERTER_API_KEY':config.key,'NETCONVERTER_AUTH':'key','NETCONVERTER_MCP_AUTH':'key',
                'NETCONVERTER_NO_UPDATE_CHECK':'1','NETCONVERTER_MCP_VIEW':'strict',
                'NETCONVERTER_URL':API_URL,'NETCONVERTER_MCP_URL':MCP_URL})
    return env


def terminal_args(config, operation='mcp'):
    if config.mode!='local-terminal' or not config.executable or not config.workspace:
        raise Refused('local_terminal_required')
    args=['--workspace',str(config.workspace),'--server',API_URL]
    if operation=='mcp': return args+['mcp','--auth','key','--mcp-url',MCP_URL,'--strict']
    if operation=='capabilities': return args+['capabilities']
    raise Refused('unsupported_terminal_operation')


def validate_arguments(schema, arguments):
    from jsonschema import Draft202012Validator
    if not isinstance(arguments,dict) or len(canonical(arguments))>16384: raise Refused('arguments_too_large')
    if not isinstance(schema,dict) or len(canonical(schema))>65536 or '$ref' in canonical(schema):
        raise Refused('unsupported_upstream_schema')
    if not Draft202012Validator(schema).is_valid(arguments): raise Refused('upstream_schema_mismatch')


def result_payload(result):
    if getattr(result,'is_error',False): raise Refused('upstream_tool_refused')
    if len(result.model_dump_json())>MAX_RESULT: raise Refused('upstream_result_too_large')
    value=getattr(result,'structured_content',None)
    if value is None:
        blocks=getattr(result,'content',[])
        if len(blocks)!=1 or getattr(blocks[0],'type',None)!='text': raise Refused('unstructured_upstream_result')
        try: value=json.loads(blocks[0].text)
        except (ValueError,TypeError): raise Refused('unstructured_upstream_result') from None
    if not isinstance(value,dict): raise Refused('invalid_upstream_result')
    if value.get('success') is False or value.get('status')=='error' or value.get('error'): raise Refused('upstream_tool_refused')
    return value


def account_authenticated(value):
    """Qualify explicit auth evidence in the hosted envelope or legacy shape."""
    account=value
    if 'success' in value:
        if value.get('success') is not True or value.get('tool')!='get_account' or value.get('error'):
            return False
        account=value.get('data')
    if not isinstance(account,dict) or account.get('status') in ('signed_out','not_signed_in','unauthorized'):
        return False
    return account.get('signed_in') is True or account.get('auth_kind')=='api_key' or account.get('auth')=='api_key'


def normalize_capabilities(raw, tools, account):
    """Normalize actual account paths; never construct a vendor Cartesian product."""
    if account.get('auth_kind')!='api_key' or account.get('credential_source')!='api_key_environment':
        raise Refused('managed_key_authentication_unverified')
    if account.get('exposure_level') not in ('none','masked'):
        raise Refused('strict_exposure_unverified')
    operations=set(raw.get('job_types',[])) & set(account.get('job_types',[])) & {'convert','validate','optimize'}
    paths=[]; unqualified=0
    vendors={}
    for v in raw.get('vendors',[]):
        if not isinstance(v,dict) or not isinstance(v.get('code'),str) or not VENDOR.fullmatch(v['code']): continue
        if v['code'] in vendors: raise Refused('duplicate_vendor_capability')
        vendors[v['code']]=v
    def context(source,target=None,path=None):
        s=vendors.get(source,{});t=vendors.get(target,{}) if target else s
        kind=s.get('device_type')
        if (kind not in ('firewall','router','switch') or t.get('device_type')!=kind or
            'source' not in s.get('roles',[]) or (target and 'target' not in t.get('roles',[])) or s.get('input')!='text' or
            (path and path.get('device_type')!=kind)): return None
        return {'device_class':kind,'source_input':'text','target_format_code':target,
                'review_required':True,'preview_status':(path or {}).get('preview') if type((path or {}).get('preview')) is bool else 'not_reported'}
    if 'convert' in operations:
        for p in raw.get('paths',[]):
            if not isinstance(p,dict): raise Refused('invalid_capability_catalog')
            source=p.get('source'); target=p.get('target')
            if not all(isinstance(x,str) and VENDOR.fullmatch(x) for x in (source,target)):
                raise Refused('invalid_capability_catalog')
            detail=context(source,target,p)
            if detail: paths.append({'source':source,'target':target,'job_type':'convert',**detail})
            else: unqualified+=1
    for v in vendors.values():
        if isinstance(v,dict) and 'source' in v.get('roles',[]) and isinstance(v.get('code'),str) and VENDOR.fullmatch(v['code']):
            for op in sorted(operations-{'convert'}):
                detail=context(v['code'])
                if detail: paths.append({'source':v['code'],'target':None,'job_type':op,**detail})
                else: unqualified+=1
    maximum=raw.get('limits',{}).get('max_config_bytes')
    if type(maximum) is not int or maximum<=0: raise Refused('artifact_limit_unavailable')
    schema=tools.get('submit_file',{}).get('inputSchema',{}).get('properties',{}).get('options')
    if not schema: raise Refused('submission_schema_unavailable')
    return {'paths':sorted(paths,key=canonical),'unqualified_paths':unqualified,'max_bytes':min(MAX_BYTES,maximum), 'options_schema':schema,
            'evidence':digest({'tools':tools,'exposure':account['exposure_level'],
                               'profile':account.get('profile'),'client_version':account.get('client_version')})}


class Upstream:
    def __init__(self,config): self.config=config

    @asynccontextmanager
    async def session(self):
        from mcp.client.client import Client
        from mcp.client.stdio import StdioServerParameters, stdio_client
        if not self.config.key: raise Refused('credential_required')
        # Legacy mode negotiates with the official Terminal without modern
        # HEADER_MISMATCH resend. Calls below use the session exactly once.
        if self.config.mode=='local-terminal':
            failure=None
            with tempfile.TemporaryFile(mode='w+') as diagnostics:
                params=StdioServerParameters(command=sys.executable,args=[str(Path(__file__).with_name('bounded_terminal.py')),str(self.config.executable),*terminal_args(self.config)],
                                             env=child_environment(self.config),cwd=str(self.config.workspace))
                async with Client(stdio_client(params,errlog=diagnostics),mode='legacy',
                                  read_timeout_seconds=50,input_required_max_rounds=0) as client:
                    try: yield Session(client)
                    except Exception as exc: failure=exc
            if failure: raise failure
        else:
            failure=None
            import httpx2
            from mcp.client.streamable_http import streamable_http_client
            async with httpx2.AsyncClient(trust_env=False,follow_redirects=False,timeout=50,
                    headers={'Authorization':'Bearer '+self.config.key,'X-NetConverter-View':'strict','Accept-Encoding':'identity'},
                    event_hooks={'response':[response_guard]}) as http:
                async with Client(streamable_http_client(MCP_URL,http_client=http,max_sse_event_size=MAX_RESULT),
                                  mode='legacy',read_timeout_seconds=50,input_required_max_rounds=0) as client:
                    try: yield Session(client)
                    except Exception as exc: failure=exc
            if failure: raise failure

    async def capabilities(self, session):
        if self.config.mode!='local-terminal': raise Refused('local_terminal_required')
        account=await session.call('account',{})
        # Fixed read-only official CLI action, not a general shell adapter.
        proc=await asyncio.create_subprocess_exec(str(self.config.executable),*terminal_args(self.config,'capabilities'),
               env=child_environment(self.config),cwd=str(self.config.workspace),stdin=asyncio.subprocess.DEVNULL,
               stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,limit=MAX_RESULT)
        try:
            async def capture():
                chunks=[]; size=0
                while True:
                    chunk=await proc.stdout.read(65536)
                    if not chunk: break
                    size+=len(chunk)
                    if size>MAX_RESULT: raise Refused('capability_result_too_large')
                    chunks.append(chunk)
                await proc.wait()
                return b''.join(chunks)
            raw=await asyncio.wait_for(capture(),45)
            if proc.returncode: raise Refused('terminal_capability_discovery_failed')
            try: payload=json.loads(raw)
            except ValueError: raise Refused('invalid_capability_catalog') from None
            if not isinstance(payload,dict): raise Refused('invalid_capability_catalog')
            return normalize_capabilities(payload,session.tools,account)
        finally:
            if proc.returncode is None:
                proc.kill(); await proc.wait()


class Session:
    def __init__(self,client): self.client=client; self.tools={}

    async def discover(self):
        cursor=None; observed={}
        for _ in range(4):
            page=await self.client.list_tools(cursor=cursor)
            if len(page.model_dump_json())>MAX_RESULT: raise Refused('catalog_too_large')
            for tool in page.tools:
                if tool.name in observed: raise Refused('duplicate_upstream_tool')
                if tool.name in READS|BASE:
                    observed[tool.name]={'inputSchema':tool.input_schema,'outputSchema':tool.output_schema}
            cursor=page.next_cursor
            if cursor is None:
                self.tools=observed; return observed
        raise Refused('catalog_pagination_limit')

    async def call(self,name,arguments):
        if name not in self.tools: raise Refused('upstream_tool_unavailable')
        validate_arguments(self.tools[name]['inputSchema'],arguments)
        result=await self.client.session.call_tool(name,arguments,read_timeout_seconds=50,
                                                   allow_input_required=True,allow_claimed=True)
        # Never let the SDK replay after elicitation, inputRequired or Tasks.
        if type(result).__name__!='CallToolResult': raise Refused('upstream_requires_separate_resolution')
        return result_payload(result)


def qualified_read(name,arguments):
    if name not in READS: raise Refused('read_tool_not_allowlisted')
    if name=='get_job_brief' and arguments.get('focus')=='target': raise Refused('raw_target_not_exposed')
    if name=='get_evidence' and arguments.get('section')=='unparsed_lines': raise Refused('raw_source_not_exposed')
    if name=='fetch' and not str(arguments.get('id','')).startswith('kb:'): raise Refused('only_knowledge_fetch_allowed')


def private_report(config, value):
    """Store upstream prose locally; project fixed vocabulary/counts to the model."""
    data=canonical(value).encode()
    if len(data)>MAX_RESULT: raise Refused('upstream_result_too_large')
    report_id=uuid.uuid4().hex; path=config.state_dir/'reports'/(report_id+'.json')
    publish_file(path,data)
    summary={};views=[value]
    if value.get('success') is True and isinstance(value.get('data'),dict):
        views.append(value['data'])
        # get_job_brief nests the same digest returned by get_evidence. Only
        # this known container is traversed; arbitrary prose stays in the file.
        if isinstance(value['data'].get('evidence'),dict):views.append(value['data']['evidence'])
    for view in views:
        for key in ('status','verdict','translation_status','overall_verdict'):
            val=view.get(key)
            if val in ('queued','running','processing','completed','complete','failed','error','unknown','passed',
                       'PASS','FAIL','NEEDS REVIEW','NEEDS_REVIEW','needs_review','needs-review','BLOCKED','blocked'):
                summary[key]=val
        if view.get('data_quality') in ('complete','partial','unknown'):
            summary['data_quality']=view['data_quality']
        for key in ('partial','truncated','redacted','timed_out','view_clamped','review_required','digest_truncated','absent'):
            if type(view.get(key)) is bool: summary[key]=summary.get(key,False) or view[key]
        for key in ('blocking_reason_count','review_reason_count','warning_count','error_count','bytes',
                    'manual_review_required_items','manual_steps_total','warnings_total'):
            if type(view.get(key)) is int and view[key]>=0: summary[key]=max(summary.get(key,0),view[key])
    return {'artifact_id':report_id,'path':str(path),'sha256':hashlib.sha256(data).hexdigest(),
            'bytes':len(data),'summary':summary,'evidence_completeness':'not_established',
            'content_exposure':'private_local_artifact','deployment_approval':False}


def verify_download(config,receipt,job_id,destination,artifacts):
    if receipt.get('job_id')!=job_id or not isinstance(receipt.get('files'),list) or not 0<len(receipt['files'])<=64:
        raise Refused('invalid_download_receipt')
    staged=[]; seen=set(); total=0
    for item in receipt['files']:
        if not isinstance(item,dict) or not isinstance(item.get('name'),str): raise Refused('invalid_download_receipt')
        path=artifacts.path(item['name'])
        try: path.relative_to(destination)
        except ValueError: raise Refused('download_path_escape') from None
        if path in seen: raise Refused('duplicate_download_path')
        seen.add(path)
        data,_=read_file(path); total+=len(data)
        if total>MAX_BYTES or type(item.get('bytes')) is not int or len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item.get('sha256'):
            raise Refused('download_integrity_failure')
        staged.append(data)
    # No trusted artifact is published until every downloaded item verifies.
    return [artifacts.publish(uuid.uuid4().hex,data) for data in staged]
