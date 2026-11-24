"""Actual stdio MCP, HTTP backend, SQLite and worker; deliberately no Google calls."""
import asyncio
from contextlib import AsyncExitStack
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from uuid import uuid4

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = Path(__file__).resolve().parents[2]
NODE = os.environ.get('NETCLAW_NODE', 'node')


def synthetic_snapshot(root):
    root.mkdir(mode=0o700)
    facts = dict(schema=1, classification='private', mode='frozen_historical_snapshot', snapshot_id='test-retained',
                 google_export_authorized=False, devices=[dict(id='TEST_ROUTER', role='router')],
                 physical_links=[], coverage_limits=['Unreachable at later collection; retained historical baseline.'],
                 verified_baseline_window={'start': '2026-01-01T00:00:00Z'}, enrichment_window=None)
    files = {'world-facts.json': facts, 'coverage.json': {'outcomes': {'unavailable': 1}}}
    manifest = {}
    for name, body in files.items():
        raw = json.dumps(body).encode(); (root/name).write_bytes(raw); (root/name).chmod(0o600)
        manifest[name] = hashlib.sha256(raw).hexdigest()
    raw = json.dumps(manifest).encode(); digest = hashlib.sha256(raw).hexdigest()
    (root/'SHA256SUMS.json').write_bytes(raw)
    (root/'SEAL.json').write_text(json.dumps(dict(snapshot_id='test-retained', manifest_sha256=digest)))
    for p in root.iterdir(): p.chmod(0o600)
    return digest


class MCPIntegration(unittest.TestCase):
    def run_scenario(self, name):
        async def run():
            await self.asyncSetUp()
            try: await getattr(self, 'scenario_'+name)()
            finally: await self.asyncTearDown()
        asyncio.run(run())

    def test_discovery(self): self.run_scenario('discovery_closed_schemas_and_no_approval_tool')
    def test_private_boundary(self): self.run_scenario('private_prepare_replay_conflict_and_export_block')
    def test_lifecycle(self): self.run_scenario('real_mcp_lifecycle_same_id_event_readiness_and_evidence')

    async def asyncSetUp(self):
        base = Path(os.environ.get('NETCLAW_TEST_TMP', REPO/'.spec200-local/tests'))
        base.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root = Path(tempfile.mkdtemp(prefix='mcp-', dir=base))
        self.root.chmod(0o700)
        snapshot = self.root/'snapshot'; digest = synthetic_snapshot(snapshot)
        registry = self.root/'bindings.json'
        registry.write_text(json.dumps(dict(schema=1, snapshots=[dict(ref='test-retained', path=str(snapshot), manifest_sha256=digest)])))
        registry.chmod(0o600)
        self.log = (self.root/'process.log').open('w')
        self.manager = subprocess.Popen([NODE, str(REPO/'scripts/genie-worlds/cli.mjs'), 'serve'], cwd=REPO,
            env={'PATH': os.environ['PATH'], 'NETCLAW_GENIE_STATE_DIR': str(self.root/'state'), 'NETCLAW_GENIE_SNAPSHOT_REGISTRY': str(registry)}, stdout=self.log, stderr=self.log)
        for _ in range(100):
            if (self.root/'state/mcp-control.json').exists(): break
            if self.manager.poll() is not None: self.fail('manager exited; inspect private process log')
            await asyncio.sleep(.03)
        self.service = json.loads((self.root/'state/service.json').read_text())
        self.control = json.loads((self.root/'state/mcp-control.json').read_text())
        self.stack = AsyncExitStack(); await self.stack.__aenter__()
        read, write = await self.stack.enter_async_context(stdio_client(StdioServerParameters(
            command=sys.executable, args=[str(REPO/'mcp-servers/genie-worlds-mcp/server.py')],
            env={'PATH': os.environ['PATH'], 'PYTHONDONTWRITEBYTECODE': '1', 'NETCLAW_GENIE_CONTROL_FILE': str(self.root/'state/mcp-control.json')}), errlog=self.log))
        self.session = await self.stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

    async def asyncTearDown(self):
        await self.stack.aclose()
        self.manager.terminate()
        await asyncio.to_thread(self.manager.wait, 10)
        self.log.close()
        shutil.rmtree(self.root)

    def http(self, path, data=None, owner=False):
        token = self.service['owner'] if owner else self.control['token']
        req = Request(self.service['origin']+path, data=None if data is None else json.dumps(data).encode(),
                      headers={'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'})
        try:
            with urlopen(req, timeout=5) as r: return r.status, json.load(r)
        except HTTPError as e: return e.code, json.load(e)

    async def call(self, tool, **args):
        r = await self.session.call_tool(tool, args)
        self.assertFalse(r.is_error, tool)
        if r.structured_content is not None: return r.structured_content
        return json.loads(next(x.text for x in r.content if x.type == 'text'))

    async def scenario_discovery_closed_schemas_and_no_approval_tool(self):
        result = await self.session.list_tools()
        self.assertEqual({t.name for t in result.tools}, {'genie_world_'+x for x in ('prepare','start','status','event','stop','evidence')})
        for t in result.tools:
            self.assertFalse(t.input_schema['additionalProperties'])
            self.assertEqual(t.annotations.read_only_hint, t.name.endswith(('_status','_evidence')))
        r = await self.session.call_tool('genie_world_prepare', dict(request_id=str(uuid4()), synthetic_fixture_id='synthetic-museum-v1', approved=True))
        self.assertTrue(r.is_error)
        for path, data in [('/v1/reviews', {}), ('/v1/snapshots', None), ('/v1/draft', None)]:
            self.assertEqual(self.http(path, data)[0], 403)

    async def scenario_private_prepare_replay_conflict_and_export_block(self):
        request_id = str(uuid4())
        d = await self.call('genie_world_prepare', request_id=request_id, private_snapshot_ref='test-retained')
        self.assertFalse(d['hosted_eligible']); self.assertTrue(d['historical'])
        self.assertNotIn('TEST_ROUTER', json.dumps(d))
        self.assertEqual(d, await self.call('genie_world_prepare', request_id=request_id, private_snapshot_ref='test-retained'))
        conflict = await self.call('genie_world_prepare', request_id=request_id, synthetic_fixture_id='synthetic-museum-v1')
        self.assertEqual(conflict['error']['code'], 'request_conflict')
        blocked = await self.call('genie_world_start', request_id=str(uuid4()), projection_ref=d['projection_ref'], review_ref=str(uuid4()))
        self.assertEqual(blocked['error']['code'], 'private_projection')
        route = '/v1/drafts/'+d['projection_ref']+'/facts'
        self.assertEqual(self.http(route)[0], 403)
        code, facts = self.http(route, owner=True)
        self.assertEqual(code, 200); self.assertEqual(facts['facts']['devices'][0]['id'], 'TEST_ROUTER')

    async def scenario_real_mcp_lifecycle_same_id_event_readiness_and_evidence(self):
        d = await self.call('genie_world_prepare', request_id=str(uuid4()), synthetic_fixture_id='synthetic-museum-v1')
        no_review = await self.call('genie_world_start', request_id=str(uuid4()), projection_ref=d['projection_ref'], review_ref=str(uuid4()))
        self.assertEqual(no_review['error']['code'], 'review_required')
        code, review = self.http('/v1/reviews', dict(projection_sha256=d['projection_sha256'], provider='fixture'), owner=True)
        self.assertEqual(code, 200)
        oid = str(uuid4()); start = dict(request_id=oid, projection_ref=d['projection_ref'], review_ref=review['id'])
        a = await self.call('genie_world_start', **start)
        b = await self.call('genie_world_start', **start)
        self.assertEqual(a['operation_id'], oid); self.assertEqual(b['operation_id'], oid)
        other = await self.call('genie_world_prepare', request_id=str(uuid4()), synthetic_fixture_id='synthetic-museum-v1')
        conflicting = await self.call('genie_world_start', **{**start, 'projection_ref': other['projection_ref']})
        self.assertEqual(conflicting['error']['code'], 'request_conflict')
        for _ in range(50):
            s = await self.call('genie_world_status', operation_id=oid)
            if s['state'] == 'active': break
            await asyncio.sleep(.02)
        self.assertEqual(s['state'], 'active')
        eid = str(uuid4())
        event = dict(request_id=eid, operation_id=oid, event_id=d['event_id'])
        await self.call('genie_world_event', **event)
        for _ in range(50):
            s = await self.call('genie_world_status', operation_id=oid)
            if s['control_requests'] and s['control_requests'][0]['status'] != 'pending': break
            await asyncio.sleep(.02)
        self.assertEqual(s['event_state'], 'planned')
        self.assertEqual(s['control_requests'][0]['code'], 'event_target_not_ready')
        await self.call('genie_world_event', **event)
        stop = dict(request_id=str(uuid4()), operation_id=oid)
        await self.call('genie_world_stop', **stop)
        await self.call('genie_world_stop', **stop)
        for _ in range(100):
            s = await self.call('genie_world_status', operation_id=oid)
            if s['state'] == 'terminal': break
            await asyncio.sleep(.02)
        self.assertEqual(s['state'], 'terminal'); self.assertEqual(s['usage_state'], 'reconciled')
        e = await self.call('genie_world_evidence', operation_id=oid)
        self.assertFalse(e['live_world_proven']); self.assertIsNone(e['acceptance'])
        self.assertNotIn('provider_id', e['session'])
        self.assertEqual(len(e['session']['control_requests']), 2)


if __name__ == '__main__': unittest.main(verbosity=2)
