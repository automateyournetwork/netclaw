#!/usr/bin/env python3
"""Deterministic transport contracts and real stdio MCP lifecycle; no device access."""
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'mcp-servers/convergence-read-mcp'))
import httpx
import client as connector

TOKEN = 'fixture-only-viewer-token'
START = '2026-10-25T10:00:00.000Z'
END = '2026-10-25T11:00:00.000Z'
COVERAGE = {'mode':'host','label':'Local interface traffic',
            'description':'Only the selected interface; not whole-network coverage.'}
ENV = {'CONVERGENCE_ENABLED':'true','CONVERGENCE_API_URL':'https://convergence.example',
       'CONVERGENCE_API_TOKEN':TOKEN,'CONVERGENCE_SITE':'lab',
       'CONVERGENCE_EXPORTERS':'192.0.2.1'}


def summary():
    return {'site':'lab','coverage':COVERAGE.copy(),'status':'active','range':'1h',
            'start':START,'end':END,'read_at':END,'exporter':None,'exporters':['192.0.2.1'],
            'total':{'bytes':1000,'packets':20,'records':10,'last_received':END},
            'sources':[{'src_addr':'192.0.2.10','bytes':1000,'packets':20,'records':10}],
            'destinations':[{'dst_addr':'198.51.100.20','bytes':1000,'packets':20,'records':10}],
            'conversations':[{'src_addr':'192.0.2.10','dst_addr':'198.51.100.20','bytes':1000,'packets':20,'records':10}],
            'sampling':[{'rate':1,'records':10}], 'basis':'Exported counters; sampling is not extrapolated.',
            'limitations':['Only selected observation points; records can be repeated.']}


def evidence():
    row={'_time':END,'sampler_address':'192.0.2.1','src_addr':'192.0.2.10',
         'dst_addr':'198.51.100.20','bytes':'80','packets':'2','proto':'6','dst_port':'443'}
    reverse={**row,'src_addr':row['dst_addr'],'dst_addr':row['src_addr'],'bytes':'10'}
    return {'site':'lab','coverage':COVERAGE.copy(),'address':'192.0.2.10',
            'start':START,'end':END,'limit':100,'records':[row,reverse],
            'basis':'Latest 100 retained records, both directions; not an aggregate reconstruction.'}


class SettingsTests(unittest.TestCase):
    def test_native_defaults_and_configured_references(self):
        sys.path.insert(0, str(ROOT/'scripts/lib'))
        from mcp_environment import native_entry
        entry = json.loads((ROOT/'config/openclaw.json').read_text())['mcpServers']['convergence-read-mcp']
        projected = native_entry('convergence-read-mcp',entry,{})
        expected = {key: 'false' if key in ('CONVERGENCE_ENABLED','CONVERGENCE_ALLOW_LOOPBACK_HTTP') else '' for key in entry['env']}
        self.assertEqual(projected['env'], expected)
        self.assertNotIn('${', json.dumps(projected))
        configured = native_entry('convergence-read-mcp',entry,ENV)
        for key in ENV: self.assertEqual(configured['env'][key], '${'+key+'}')
        self.assertNotIn(TOKEN, json.dumps(configured))

    def test_default_disabled_and_missing_config(self):
        for env,code in [({},'disabled'),({'CONVERGENCE_ENABLED':'true'},'not_configured')]:
            with self.assertRaises(connector.ReadError) as caught: connector.Settings.from_env(env)
            self.assertEqual(caught.exception.code,code)

    def test_endpoint_boundary(self):
        for endpoint in ['http://192.0.2.5','http://localhost','ftp://127.0.0.1','https://user:secret@example.com',
                         'https://example.com/path','https://example.com?url=private','https://example.com#secret',
                         'https://example.com:99999','https://example.com\\@other.test','https://example.com\n']:
            with self.subTest(endpoint=endpoint), self.assertRaises(connector.ReadError):
                connector.Settings.from_env({**ENV,'CONVERGENCE_API_URL':endpoint,'CONVERGENCE_ALLOW_LOOPBACK_HTTP':'true'})
        for endpoint in ['http://127.0.0.1:1234','http://[::1]:1234']:
            with self.assertRaises(connector.ReadError): connector.Settings.from_env({**ENV,'CONVERGENCE_API_URL':endpoint})
            value=connector.Settings.from_env({**ENV,'CONVERGENCE_API_URL':endpoint,'CONVERGENCE_ALLOW_LOOPBACK_HTTP':'true'})
            self.assertEqual(value.endpoint,endpoint)
        self.assertNotIn(TOKEN,repr(connector.Settings.from_env(ENV)))
        self.assertNotIn('convergence.example',repr(connector.Settings.from_env(ENV)))

    def test_fixed_site_and_exporters(self):
        for changed in [{'CONVERGENCE_SITE':'../other'},{'CONVERGENCE_EXPORTERS':'any'},
                        {'CONVERGENCE_EXPORTERS':''},{'CONVERGENCE_API_TOKEN':'secret\nleak'}]:
            with self.subTest(changed=changed), self.assertRaises(connector.ReadError):
                connector.Settings.from_env({**ENV,**changed})
        value=connector.Settings.from_env(ENV)
        self.assertEqual(value.exporter('192.0.2.1'),'192.0.2.1')
        with self.assertRaises(connector.ReadError): value.exporter('192.0.2.2')


class ClientTests(unittest.IsolatedAsyncioTestCase):
    def client(self,payload=None,status=200,headers=None,handler=None):
        self.requests=[]
        def serve(request):
            self.requests.append(request)
            return handler(request) if handler else httpx.Response(status,json=payload,headers=headers)
        return connector.ConvergenceClient(connector.Settings.from_env(ENV),httpx.MockTransport(serve))

    async def test_two_get_paths_and_fixed_scope(self):
        c=self.client(summary()); result=await c.summary()
        self.assertTrue(result['ok']); request=self.requests[-1]
        self.assertEqual(request.method,'GET'); self.assertEqual(request.url.path,'/api/flows')
        self.assertEqual(dict(request.url.params),{'site':'lab','range':'1h'})
        self.assertEqual(request.headers['authorization'],'Bearer '+TOKEN)
        self.assertNotIn(TOKEN,json.dumps(result))
        c=self.client(evidence()); result=await c.evidence('192.0.2.10',START,END)
        self.assertTrue(result['ok']); request=self.requests[-1]
        self.assertEqual(request.url.path,'/api/flows/records')
        self.assertEqual(request.url.params['start'],START); self.assertEqual(request.url.params['end'],END)
        self.assertEqual(len(result['data']['records']),2)
        self.assertEqual(result['data']['coverage'],COVERAGE)
        self.assertLess(sum(int(x['bytes']) for x in result['data']['records']),1000)

    async def test_invalid_inputs_never_send(self):
        c=self.client(summary())
        for value in ['2d','1h&site=other',None,{},True]:
            self.assertEqual((await c.summary(value))['error']['code'],'invalid_argument')
        for value in ['192.0.2.2','http://other','*']:
            self.assertEqual((await c.summary(exporter=value))['error']['code'],'invalid_argument')
        for values in [('not-an-ip',START,END),('192.0.2.10',END,START),
                       ('192.0.2.10','2026-10-25',END),('192.0.2.10',START,'2026-10-27T11:00:00Z'),
                       ('192.0.2.10',START,'9999-01-01T00:00:00Z')]:
            self.assertEqual((await c.evidence(*values))['error']['code'],'invalid_argument')
        self.assertEqual(self.requests,[])

    async def test_scope_and_shape_rejected(self):
        for changed in [{'site':'other'},{'exporters':['192.0.2.2']},{'coverage':{'mode':'unknown'}},
                        {'status':'healthy'},{'range':'24h'},{'exporter':'192.0.2.1'},
                        {'end':'2026-10-25T12:00:00Z'},{'sources':[{'src_addr':'<script>'}]},
                        {'total':{'bytes':True,'packets':3,'records':1}}, {'basis':TOKEN}]:
            with self.subTest(changed=changed):
                result=await self.client({**summary(),**changed}).summary()
                self.assertEqual(result['error']['code'],'compatibility');self.assertNotIn(TOKEN,json.dumps(result))
        source=summary();source['secret_unexpected']=TOKEN
        result=await self.client(source).summary()
        self.assertTrue(result['ok']);self.assertNotIn('secret_unexpected',result['data'])

    async def test_empty_and_unconfigured_are_successful_distinct_results(self):
        payload=summary();payload.update(status='empty',sources=[],destinations=[],conversations=[],sampling=[])
        payload['total']={'bytes':None,'packets':None,'records':None,'last_received':None}
        result=await self.client(payload).summary();self.assertEqual(result['data']['status'],'empty')
        result=await self.client({'site':'lab','coverage':COVERAGE,'status':'not_configured','exporters':[]}).summary()
        self.assertEqual(result['data']['status'],'not_configured')

    async def test_selected_exporter_must_match_response_and_records(self):
        payload=summary();payload['exporter']='192.0.2.1'
        result=await self.client(payload).summary(exporter='192.0.2.1')
        self.assertTrue(result['ok']);self.assertEqual(self.requests[0].url.params['exporter'],'192.0.2.1')
        payload=evidence();payload['records'][0]['sampler_address']='192.0.2.2'
        result=await self.client(payload).evidence('192.0.2.10',START,END,'192.0.2.1')
        self.assertEqual(result['error']['code'],'compatibility')

    async def test_evidence_scope_window_and_limit(self):
        payloads=[]
        for changed in [{'site':'other'},{'address':'192.0.2.99'},{'start':'2026-10-25T09:00:00Z'},
                        {'limit':101},{'records':evidence()['records']*51},{'basis':TOKEN}]:
            payloads.append({**evidence(),**changed})
        for field,value in [('_time','2026-10-25T09:59:59Z'),('src_addr','192.0.2.99'),('bytes','private'),('packets',-1)]:
            payload=evidence();payload['records'][0][field]=value;payloads.append(payload)
        for payload in payloads:
            with self.subTest(payload=payload):
                result=await self.client(payload).evidence('192.0.2.10',START,END)
                self.assertEqual(result['error']['code'],'compatibility')

    async def test_ipv6_identity_is_canonical_in_summary_and_evidence(self):
        env={**ENV,'CONVERGENCE_EXPORTERS':'2001:db8::1'}
        payload=summary();payload['exporters']=['2001:0db8:0000:0000:0000:0000:0000:0001']
        payload['sources'][0]['src_addr']='2001:0db8:0000:0000:0000:0000:0000:0010'
        c=connector.ConvergenceClient(connector.Settings.from_env(env),
            httpx.MockTransport(lambda r:httpx.Response(200,json=payload)))
        result=await c.summary()
        self.assertEqual(result['data']['exporters'],['2001:db8::1'])
        self.assertEqual(result['data']['sources'][0]['src_addr'],'2001:db8::10')
        payload=evidence();payload['address']='2001:0db8:0000:0000:0000:0000:0000:0010'
        for row in payload['records']:
            row['sampler_address']='2001:0db8:0000:0000:0000:0000:0000:0001'
            if row['src_addr']=='192.0.2.10': row['src_addr']=payload['address']
            else: row['dst_addr']=payload['address']
        result=await c.evidence('2001:db8::10',START,END)
        self.assertEqual(result['data']['address'],'2001:db8::10')
        self.assertEqual(result['data']['records'][0]['src_addr'],'2001:db8::10')
        self.assertEqual(result['data']['records'][1]['dst_addr'],'2001:db8::10')

    async def test_streaming_deadline_bounds_slow_trickle(self):
        class Trickle(httpx.AsyncByteStream):
            async def __aiter__(self):
                for chunk in (b'{',b'"site"',b':',b'"lab"',b'}'):
                    await asyncio.sleep(.015)
                    yield chunk
        c=self.client(handler=lambda r:httpx.Response(200,stream=Trickle(),
            headers={'content-type':'application/json'}))
        with patch.object(connector,'DEADLINE_SECONDS',.025):
            self.assertEqual((await c.summary())['error']['code'],'timeout')

    async def test_status_redirect_errors_do_not_reflect_secrets(self):
        for status,code in [(401,'unauthorized'),(403,'unauthorized'),(302,'unavailable'),(500,'unavailable')]:
            result=await self.client({'error':TOKEN},status,{'location':'https://other/'+TOKEN}).summary()
            self.assertEqual(result['error']['code'],code);self.assertNotIn(TOKEN,json.dumps(result))
            self.assertEqual(len(self.requests),1)

    async def test_malformed_oversized_and_encoded_responses(self):
        cases=[httpx.Response(200,content=b'{',headers={'content-type':'application/json'}),
               httpx.Response(200,json=summary(),headers={'content-type':'text/html'}),
               httpx.Response(200,json=summary(),headers={'content-length':str(connector.MAX_BYTES+1)}),
               httpx.Response(200,content=b'x'*(connector.MAX_BYTES+1),headers={'content-type':'application/json'}),
               httpx.Response(200,content=b'{"x":NaN}',headers={'content-type':'application/json'})]
        for response in cases:
            result=await self.client(handler=lambda r:response).summary()
            self.assertEqual(result['error']['code'],'compatibility')
        # Reject encoded payloads before decoding, including a potentially expanding body.
        response=httpx.Response(200,content=b'',headers={'content-encoding':'gzip','content-type':'application/json'})
        self.assertEqual((await self.client(handler=lambda r:response).summary())['error']['code'],'compatibility')

    async def test_absolute_deadline_and_network_error(self):
        async def slow(request):
            await asyncio.sleep(.1)
            return httpx.Response(200,json=summary())
        c=connector.ConvergenceClient(connector.Settings.from_env(ENV),httpx.MockTransport(slow))
        with patch.object(connector,'DEADLINE_SECONDS',.02):
            self.assertEqual((await c.summary())['error']['code'],'timeout')
        def fail(request): raise httpx.ConnectError(TOKEN,request=request)
        result=await self.client(handler=fail).summary()
        self.assertEqual(result['error']['code'],'unavailable');self.assertNotIn(TOKEN,json.dumps(result))


class StdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_exporter_protocol_names_and_numeric_identifiers(self):
        settings = connector.Settings.from_env(ENV)
        for protocol in ('UDP', 'TCP', 'ICMPv6', '47', 6):
            payload = evidence()
            payload['records'][0]['proto'] = protocol
            result = connector.validate_evidence(payload,settings,'192.0.2.10',START,END,None)
            self.assertTrue(result['records'])
        for protocol in ('<script>', 'x'*33, -1, 256, True):
            payload = evidence();payload['records'][0]['proto'] = protocol
            with self.assertRaises(connector.ReadError):
                connector.validate_evidence(payload,settings,'192.0.2.10',START,END,None)

    async def test_escaped_credential_echo_is_rejected(self):
        token = 'fixture"private\\key'
        settings = connector.Settings.from_env({**ENV, 'CONVERGENCE_API_TOKEN': token})
        for field in ('basis', 'limitations'):
            payload = summary()
            payload[field] = token if field == 'basis' else [token]
            client = connector.ConvergenceClient(settings, httpx.MockTransport(
                lambda request: httpx.Response(200, json=payload)))
            result = await client.summary()
            self.assertEqual(result['error']['code'], 'compatibility')
            self.assertNotIn(token, str(result))

    async def test_real_stdio_inventory_calls_disable_and_argument_scope(self):
        from fastmcp import Client
        requests=[]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed=urlsplit(self.path); args=parse_qs(parsed.query)
                requests.append((self.command,parsed.path,args))
                if self.headers.get('Authorization')!='Bearer '+TOKEN or args.get('site')!=['lab']:
                    self.send_response(403);self.end_headers();return
                payload=summary() if parsed.path=='/api/flows' else evidence()
                data=json.dumps(payload).encode()
                self.send_response(200);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
            def log_message(self,*args): pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        env={**ENV,'CONVERGENCE_API_URL':f'http://127.0.0.1:{server.server_port}',
             'CONVERGENCE_ALLOW_LOOPBACK_HTTP':'true','PYTHONDONTWRITEBYTECODE':'1'}
        def configuration(env):
            return {'mcpServers':{'convergence-read':{'command':sys.executable,
                'args':[str(ROOT/'mcp-servers/convergence-read-mcp/server.py')],'env':env}}}
        try:
            async with Client(configuration(env)) as mcp:
                tools=await mcp.list_tools()
                self.assertEqual({tool.name for tool in tools},{'convergence_flow_summary','convergence_flow_evidence'})
                self.assertTrue(all(tool.annotations.read_only_hint for tool in tools))
                result=await mcp.call_tool('convergence_flow_summary',{'range':'1h'})
                data=result.data
                self.assertTrue(data['ok']);self.assertEqual(data['data']['coverage']['mode'],'host')
                result=await mcp.call_tool('convergence_flow_evidence',{'address':'192.0.2.10','start':data['data']['start'],'end':data['data']['end']})
                self.assertEqual(len(result.data['data']['records']),2)
                before=len(requests)
                with self.assertRaises(Exception):
                    await mcp.call_tool('convergence_flow_summary',{'range':'1h','site':'other'})
                self.assertEqual(len(requests),before)
            async with Client(configuration({**env,'CONVERGENCE_ENABLED':'false'})) as mcp:
                result=await mcp.call_tool('convergence_flow_summary',{})
                self.assertEqual(result.data['error']['code'],'disabled')
                self.assertEqual(len(requests),before)
            self.assertEqual({x[1] for x in requests},{'/api/flows','/api/flows/records'})
            self.assertTrue(all(x[0]=='GET' for x in requests))
        finally:
            server.shutdown();server.server_close();worker.join(timeout=2)


if __name__=='__main__':
    unittest.main(verbosity=2)
