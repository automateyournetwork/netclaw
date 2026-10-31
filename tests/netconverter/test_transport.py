"""Real SDK handshakes against controlled peers, including a genuine HTTP server."""
import asyncio
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from contextlib import asynccontextmanager
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'mcp-servers/netconverter-mcp'))
from artifacts import Artifacts, Refused
from core import Config
from server import Guard
from transport import Session, Upstream, child_environment, qualified_read, terminal_args, verify_download, response_guard, MAX_RESULT, normalize_capabilities, private_report, result_payload

PEER=Path(__file__).with_name('peer.py')


class TransportTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.workspace=self.root/'workspace';self.workspace.mkdir(mode=0o700)
        self.fixture=self.workspace/'fixture.json';self.fixture.write_text('{}')
        self.source=self.workspace/'source.cfg';self.source.write_text('PRIVATE_CONFIG_CANARY\n')
        # Operator-selected synthetic executable; no third-party code copied.
        self.exe=self.root/'terminal'
        self.exe.write_text('#!'+sys.executable+'\n'+PEER.read_text());self.exe.chmod(0o700)
        self.config=Config('transport-test','local-terminal',self.root/'state',self.workspace,self.exe,'synthetic-key','fixture account')
        self.guard=Guard(self.config)

    async def test_real_stdio_prepare_approve_submit_poll_download(self):
        status=await self.guard.status(True)
        self.assertTrue(status['authenticated']);self.assertNotIn('apply_mapping_answers',status['available_reads'])
        request=await self.guard.prepare(str(self.source),'cisco_asa','palo_alto_set')
        self.assertFalse((self.workspace/'attempts.jsonl').exists())
        self.guard.ledger.approve(request['request_id'],request['review_digest'])
        submitted=await self.guard.submit(request['request_id']);self.assertEqual(submitted['state'],'submitted')
        report=await self.guard.job_status(submitted['job_ref'])
        self.assertEqual(report['summary']['verdict'],'NEEDS REVIEW')
        self.assertNotIn('PRIVATE_CONFIG_CANARY',json.dumps(report));self.assertNotIn('synthetic-key',json.dumps(report))
        wait=await self.guard.job_status(submitted['job_ref'],1);self.assertTrue(wait['summary']['timed_out'])
        output=await self.guard.download(submitted['job_ref'])
        self.assertEqual(len(output['artifacts']),1)
        self.assertNotIn('SYNTHETIC_CANDIDATE_CANARY',json.dumps(output))
        with self.assertRaises(Refused): await self.guard.submit(request['request_id'])
        self.assertEqual(len((self.workspace/'attempts.jsonl').read_text().splitlines()),1)

    async def test_unknown_receipt_restart_never_resubmits(self):
        self.fixture.write_text(json.dumps({'fail_after_accept':True}))
        request=await self.guard.prepare(str(self.source),'cisco_asa','palo_alto_set')
        self.guard.ledger.approve(request['request_id'],request['review_digest'])
        result=await self.guard.submit(request['request_id']);self.assertEqual(result['state'],'unknown')
        with self.assertRaises(Refused): await Guard(self.config).submit(request['request_id'])
        self.assertEqual(len((self.workspace/'attempts.jsonl').read_text().splitlines()),1)
        self.assertNotIn('PRIVATE_CONFIG_CANARY',json.dumps(result))

    async def test_cancel_after_accept_persists_unknown_and_no_replay(self):
        self.fixture.write_text(json.dumps({'delay_after_accept':True}))
        request=await self.guard.prepare(str(self.source),'cisco_asa','palo_alto_set')
        self.guard.ledger.approve(request['request_id'],request['review_digest'])
        task=asyncio.create_task(self.guard.submit(request['request_id']))
        try:
            for _ in range(300):
                if (self.workspace/'attempts.jsonl').exists():break
                await asyncio.sleep(.02)
            self.assertTrue((self.workspace/'attempts.jsonl').exists())
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
            self.assertEqual(Guard(self.config).ledger.status(request['request_id'])['state'],'unknown')
            with self.assertRaises(Refused):await Guard(self.config).submit(request['request_id'])
        finally:
            if not task.done():task.cancel()

    async def test_denial_changed_capabilities_and_exposure(self):
        request=await self.guard.prepare(str(self.source),'cisco_asa','palo_alto_set')
        with self.assertRaises(Refused): await self.guard.submit(request['request_id'])
        self.guard.ledger.approve(request['request_id'],request['review_digest'])
        self.fixture.write_text(json.dumps({'exposure':'none'}))
        with self.assertRaisesRegex(Refused,'capabilities_changed'): await self.guard.submit(request['request_id'])
        self.assertFalse((self.workspace/'attempts.jsonl').exists())
        status=await self.guard.status(True);self.assertTrue(status['authenticated'])
        self.fixture.write_text(json.dumps({'exposure':'full'}))
        with self.assertRaisesRegex(Refused,'strict_exposure'): await self.guard.status(True)

    async def test_allowlist_read_schema_and_private_projection(self):
        for name,args in [('apply_mapping_answers',{}),('get_target_config',{}),('fetch',{'id':'job:123'}),
                          ('get_evidence',{'section':'unparsed_lines'}),('get_job_brief',{'focus':'target'})]:
            with self.assertRaises(Refused): qualified_read(name,args)
        with self.assertRaisesRegex(Refused,'schema'): await self.guard.read('get_evidence',{'unknown':True})
        report=await self.guard.read('get_evidence',{'job_id':'tra_synthetic123'})
        self.assertTrue(report['summary']['partial']);self.assertTrue(report['summary']['truncated'])
        self.assertNotIn('PRIVATE_CONFIG_CANARY',json.dumps(report))

    async def test_actual_http_sdk_transport(self):
        import httpx2
        from mcp.client.client import Client
        from mcp.client.streamable_http import streamable_http_client
        with socket.socket() as probe:
            probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        self.fixture.write_text(json.dumps({'transport':'http','port':port}))
        proc=subprocess.Popen([str(self.exe),*terminal_args(self.config)],env=child_environment(self.config),
                              stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                try:
                    r,w=await asyncio.open_connection('127.0.0.1',port);w.close();await w.wait_closed();break
                except OSError: await asyncio.sleep(.05)
            async with httpx2.AsyncClient(trust_env=False,follow_redirects=False,timeout=10) as http:
                async with Client(streamable_http_client(f'http://127.0.0.1:{port}/mcp',http_client=http),
                                  mode='legacy',input_required_max_rounds=0,read_timeout_seconds=10) as client:
                    session=Session(client);tools=await session.discover()
                    self.assertNotIn('apply_mapping_answers',tools)
                    self.assertEqual((await session.call('account',{}))['auth_kind'],'api_key')
        finally:
            proc.terminate();await asyncio.to_thread(proc.wait,10)

    async def test_existing_job_is_explicitly_bound_and_wait_budget_persists(self):
        result=await self.guard.read('get_job_brief',{'job_id':'existing-123'})
        ref=result['job_ref'];self.assertEqual(self.guard.ledger.job(ref)['job_id'],'existing-123')
        self.guard.ledger.reserve_poll(ref,300)
        with self.assertRaisesRegex(Refused,'budget_exhausted'): await Guard(self.config).job_status(ref,1)
        with self.assertRaisesRegex(Refused,'job_not_bound'): Guard(dataclasses.replace(self.config,key='different')).ledger.job(ref)

    async def test_validate_and_optimize_omit_absent_target_for_official_schema(self):
        for operation in ('validate','optimize'):
            request=await self.guard.prepare(str(self.source),'cisco_asa',job_type=operation)
            self.assertEqual(request['path_context']['device_class'],'firewall')
            self.guard.ledger.approve(request['request_id'],request['review_digest'])
            self.assertEqual((await self.guard.submit(request['request_id']))['state'],'submitted')

    def test_capabilities_require_explicit_consistent_class_roles_and_text_format(self):
        raw={'job_types':['convert'],'vendors':[{'code':'cisco_router','roles':['source'],'input':'text','device_type':'router'},
             {'code':'junos_router','roles':['target'],'device_type':'switch','input':'text'}],
             'paths':[{'source':'cisco_router','target':'junos_router','device_type':'router'}],'limits':{'max_config_bytes':1000}}
        account={'auth_kind':'api_key','credential_source':'api_key_environment','exposure_level':'masked','job_types':['convert']}
        tools={'submit_file':{'inputSchema':{'properties':{'options':{'type':'object'}}}}}
        self.assertEqual(normalize_capabilities(raw,tools,account)['paths'],[])
        raw['vendors'][1]['device_type']='router'
        result=normalize_capabilities(raw,tools,account);self.assertTrue(result['paths'][0]['review_required'])
        self.assertEqual(result['paths'][0]['preview_status'],'not_reported')
        raw['vendors'][0]['input']='bundle'
        self.assertEqual(normalize_capabilities(raw,tools,account)['paths'],[])

    async def test_hosted_signed_out_response_cannot_claim_authenticated(self):
        class Peer:
            @asynccontextmanager
            async def session(self):yield self
            async def discover(self):return {'get_account':{}}
            async def call(self,*args):return {'status':'signed_out'}
        config=dataclasses.replace(self.config,mode='hosted-readonly',workspace=None,executable=None)
        result=await Guard(config,Peer()).status(True)
        self.assertFalse(result['authenticated']);self.assertFalse(result['capable'])

    async def test_hosted_live_shaped_account_envelope_is_authenticated_only_on_success(self):
        class Peer:
            response={'success':True,'tool':'get_account','error':None,'data':{'auth':'api_key','view_mode':'strict'}}
            @asynccontextmanager
            async def session(self):yield self
            async def discover(self):return {'get_account':{}}
            async def call(self,*args):return self.response
        config=dataclasses.replace(self.config,mode='hosted-readonly',workspace=None,executable=None)
        peer=Peer();result=await Guard(config,peer).status(True)
        self.assertTrue(result['authenticated']);self.assertTrue(result['capable'])
        for response in ({'success':False,'data':{'auth':'api_key'}},
                         {'success':True,'tool':'different_tool','data':{'auth':'api_key'}},
                         {'success':True,'tool':'get_account','data':{'auth':'api_key','status':'signed_out'}}):
            peer.response=response;result=await Guard(config,peer).status(True)
            self.assertFalse(result['authenticated'])

    def test_enveloped_report_preserves_warnings_without_exposing_prose(self):
        value={'success':True,'tool':'get_report','truncated':True,'data':{
            'verdict':'NEEDS REVIEW','warning_count':3,'truncated':False,'report':'PRIVATE_CANARY'}}
        result=private_report(self.config,value)
        self.assertEqual(result['summary']['verdict'],'NEEDS REVIEW')
        self.assertEqual(result['summary']['warning_count'],3)
        self.assertTrue(result['summary']['truncated']);self.assertNotIn('PRIVATE_CANARY',json.dumps(result))

    def test_explicit_unsuccessful_envelope_is_never_a_successful_tool_result(self):
        from types import SimpleNamespace
        result=SimpleNamespace(is_error=False,structured_content={'success':False,'error':None,'data':{}},model_dump_json=lambda:'{}')
        with self.assertRaises(Refused):result_payload(result)

    def test_live_evidence_review_gaps_survive_direct_and_brief_envelopes(self):
        evidence={'overall_verdict':'needs-review','translation_status':'needs_review',
            'review_required':True,'manual_review_required_items':1,'manual_steps_total':1,
            'warnings_total':6,'data_quality':'partial','digest_truncated':True,
            'review_scope':'PRIVATE_CONFIG_CANARY','manual_recreation_steps':'PRIVATE_CONFIG_CANARY'}
        for data in (evidence,{'evidence':evidence}):
            result=private_report(self.config,{'success':True,'data':data,'truncated':False})
            self.assertEqual(result['summary'],{k:v for k,v in evidence.items()
                if k not in ('review_scope','manual_recreation_steps')}|{'truncated':False})
            self.assertFalse(result['deployment_approval'])
            self.assertEqual(result['evidence_completeness'],'not_established')
            self.assertNotIn('PRIVATE_CONFIG_CANARY',json.dumps(result))

    def test_absent_report_is_explicit_and_untrusted_fields_stay_private(self):
        value={'success':True,'tool':'get_report','data':{'absent':True,
            'translation_status':'needs_review','reason':'PRIVATE_CONFIG_CANARY',
            'overall_verdict':'PRIVATE_CONFIG_CANARY','data_quality':'PRIVATE_CONFIG_CANARY',
            'manual_steps_total':True,'warnings_total':-1}}
        result=private_report(self.config,value)
        self.assertEqual(result['summary'],{'absent':True,'translation_status':'needs_review'})
        self.assertNotIn('PRIVATE_CONFIG_CANARY',json.dumps(result))

    async def test_actual_guard_mcp_exposes_only_eight_owned_tools_and_no_approval_tool(self):
        from mcp.client.client import Client
        from mcp.client.stdio import StdioServerParameters,stdio_client
        env_file=self.root/'guard.env'
        env_file.write_text('\n'.join(f'{k}="{v}"' for k,v in {'NETCONVERTER_MODE':'local-terminal',
            'NETCONVERTER_INSTALLATION_ID':self.config.installation,'NETCONVERTER_DATA_DIR':self.config.state_dir,
            'NETCONVERTER_WORKSPACE':self.workspace,'NETCONVERTER_EXECUTABLE':self.exe,
            'NETCONVERTER_API_KEY':'synthetic-key','NETCONVERTER_ACCOUNT_REF':'fixture account'}.items()))
        args=[str(Path(__file__).resolve().parents[2]/'mcp-servers/netconverter-mcp/server.py'),'--env-file',str(env_file)]
        with tempfile.TemporaryFile(mode='w+') as errors:
            async with Client(stdio_client(StdioServerParameters(command=sys.executable,args=args,env={'PATH':os.defpath}),errlog=errors),mode='legacy') as client:
                tools=(await client.list_tools()).tools;self.assertEqual(len(tools),8)
                self.assertNotIn('submit_file',[t.name for t in tools]);self.assertFalse(any('approve_submission' in t.name for t in tools))
                result=await client.call_tool('netconverter_status',{'discover':False})
                self.assertFalse(result.is_error);self.assertNotIn('synthetic-key',result.model_dump_json())
                self.assertFalse((self.workspace/'attempts.jsonl').exists())

    def test_environment_and_fixed_argv(self):
        with patch.dict(os.environ,{'NETCONVERTER_AUTH':'clerk','NETCONVERTER_PROVIDER':'openai',
                                    'OPENAI_API_KEY':'MUST_NOT_PASS','HTTP_PROXY':'http://evil',
                                    'NETCONVERTER_URL':'https://evil','NETCONVERTER_TRUSTED_HOSTS':'evil'}):
            env=child_environment(self.config)
            self.assertEqual(env['NETCONVERTER_AUTH'],'key');self.assertNotIn('HTTP_PROXY',env)
            self.assertNotIn('OPENAI_API_KEY',env);self.assertNotIn('NETCONVERTER_PROVIDER',env)
            self.assertNotIn('NETCONVERTER_TRUSTED_HOSTS',env)
        argv=terminal_args(self.config)
        self.assertIn('--strict',argv);self.assertIn('https://api.netconverter.ai/mcp/v1/',argv)
        self.assertNotIn('--guided',argv)

    def test_download_corruption_and_escape_publish_nothing(self):
        artifacts=Artifacts(self.workspace,self.config.installation)
        dest=artifacts.root/'download-test';dest.mkdir(mode=0o700)
        path=dest/'file';path.write_bytes(b'candidate')
        for name,sha in [(str(path.relative_to(self.workspace)),'0'*64),('../escape','0'*64)]:
            with self.assertRaises(Refused): verify_download(self.config,{'job_id':'job-1','files':[{'name':name,'sha256':sha,'bytes':9}]},'job-1',dest,artifacts)
        self.assertEqual(list(artifacts.root.glob('*.artifact')),[])

    async def test_chunked_compressed_redirected_and_oversized_http_are_bounded(self):
        import httpx2
        class Chunks(httpx2.AsyncByteStream):
            async def __aiter__(self):
                for _ in range(35):yield b'x'*65536
        response=httpx2.Response(200,stream=Chunks())
        await response_guard(response)
        with self.assertRaises(Refused):await response.aread()
        for response in (httpx2.Response(302,headers={'Location':'https://other.invalid'}),
                         httpx2.Response(200,headers={'Content-Encoding':'gzip'}),
                         httpx2.Response(200,content=b'x'*(MAX_RESULT+1))):
            with self.assertRaises(Refused):await response_guard(response)

    async def test_stdio_supervisor_stops_unbounded_line_without_echoing_diagnostics(self):
        helper=Path(__file__).resolve().parents[2]/'mcp-servers/netconverter-mcp/bounded_terminal.py'
        proc=await asyncio.create_subprocess_exec(sys.executable,str(helper),sys.executable,'-c',
             'import sys; sys.stdout.write("x"*3000000); sys.stdout.flush()',
             stdin=asyncio.subprocess.DEVNULL,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        output,error=await asyncio.wait_for(proc.communicate(),10)
        self.assertEqual(proc.returncode,2);self.assertLessEqual(len(output),MAX_RESULT)
        self.assertNotIn(b'xxx',error)


if __name__=='__main__': unittest.main()
