"""Actual pinned MCP/pyATS acceptance. Opt in with PYATS_TEST_RUNTIME/UPSTREAM.

Synthetic RFC5737/RFC3849 inventory only. Never probes, logs in or runs commands.
"""
import asyncio
from datetime import datetime, timezone
import importlib.util
import functools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=os.environ.get('PYATS_TEST_RUNTIME')
UPSTREAM=os.environ.get('PYATS_TEST_UPSTREAM')


def fixture(kind='structured',name=None):
    value=json.loads((ROOT/f'tests/fixtures/pyats-testbeds/{kind}.json').read_text())
    stamp=datetime.now(timezone.utc).isoformat()
    for source in value['sources']:
        source['capturedAt']=stamp
        if 'snapshotCapturedAt' in source:source['snapshotCapturedAt']=stamp
        for endpoint in source.get('endpoints',{}).values():endpoint['observedAt']=stamp
    if name:value['name']=name
    return value


def native_case(fn):
    @functools.wraps(fn)
    async def wrapped(self):
        async with self.client:
            return await fn(self)
    return wrapped


@unittest.skipUnless(RUNTIME and UPSTREAM,'Set isolated PYATS_TEST_RUNTIME and PYATS_TEST_UPSTREAM for actual MCP acceptance')
class NativeDynamicTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from mcp.client.client import Client
        from mcp.client.stdio import StdioServerParameters,stdio_client
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.private=Path(self.temp.name).resolve();self.errors=tempfile.TemporaryFile(mode='w+');self.addCleanup(self.errors.close)
        ids=[p.stem for p in (ROOT/'tests/fixtures/pyats-testbeds').glob('*.json')]
        static=self.private/'operator.yaml';static.write_text('devices: {}\n')
        self.env={'PATH':os.environ['PATH'],'PYATS_VENV':RUNTIME,'PYATS_UPSTREAM_SCRIPT':UPSTREAM,
            'NETCLAW_TESTBED_MODE':'dynamic','NETCLAW_TESTBED_SOURCES':','.join(ids),
            'PYATS_TESTBED_PATH':str(static),'PYATS_MCP_ARTIFACTS_DIR':str(self.private/'artifacts'),
            'NETCLAW_USERNAME':'synthetic-user','NETCLAW_PASSWORD':'SYNTHETIC-NOT-A-REAL-PASSWORD',
            'NETCLAW_ENABLE_PASSWORD':'SYNTHETIC-NOT-A-REAL-ENABLE','PYTHON_DOTENV_DISABLED':'1',
            'NETCLAW_RUNTIME_ENV':str(self.private/'selected.env'),'NETCLAW_RUNTIME_ROOT':str(self.private/'python-runtimes')}
        self.env['NETCLAW_CHANGE_ROOT']=str(self.private/'netclaw-changes')
        self.params=StdioServerParameters(command=sys.executable,args=[str(ROOT/'scripts/pyats-stdio.py')],env=self.env,cwd=self.private)
        self.client=Client(stdio_client(self.params,errlog=self.errors),read_timeout_seconds=60)


    async def call(self,name,args=None,client=None):
        response=await (client or self.client).call_tool(name,args or {})
        self.assertFalse(response.is_error)
        return json.loads(''.join(b.text for b in response.content if b.type=='text'))

    @native_case
    async def test_all_sources_actual_builder_schema_activation_and_guards(self):
        tools=(await self.client.list_tools()).tools
        self.assertEqual(len(tools),35)
        config=next(t for t in tools if t.name=='pyats_configure_device')
        self.assertIn('artifact_ref',config.input_schema['properties'])
        self.assertIn('grant_ref',config.input_schema['properties'])
        self.assertNotIn('config_commands',config.input_schema.get('required',[]))
        self.assertFalse(any('approve' in t.name or 'grant' in t.name for t in tools))
        self.assertEqual(len([t for t in tools if t.name.startswith('pyats_testbed_')]),8)
        self.assertEqual((await self.call('pyats_testbed_list'))['active'],'none')
        for path in sorted((ROOT/'tests/fixtures/pyats-testbeds').glob('*.json')):
            candidate=fixture(path.stem);name=candidate['name']
            result=await self.call('netclaw_testbed_compose',{'envelope':candidate})
            self.assertEqual(result['status'],'completed',result)
            self.assertEqual((await self.call('pyats_testbed_activate',{'name':name}))['code'],'candidate_requires_successful_schema_and_credential_validation')
            validation=await self.call('pyats_testbed_validate',{'name':name,'check_reachability':False})
            self.assertEqual(validation['status'],'completed',validation)
            self.assertEqual(validation['reachability'],'not_checked')
            self.assertEqual((await self.call('pyats_testbed_activate',{'name':name}))['active'],name)
            devices=await self.call('pyats_list_devices')
            self.assertEqual(len(devices['devices']),1)
            self.assertIn('privateMigration',devices)
            self.assertEqual((await self.call('netclaw_testbed_compose',{'envelope':candidate}))['code'],'candidate_name_already_used')
            self.assertEqual((await self.call('pyats_testbed_delete',{'name':name}))['code'],'active_candidate_cannot_be_deleted')
            self.assertEqual((await self.call('pyats_testbed_list'))['active'],name)
            detail=await self.call('pyats_testbed_get',{'name':name,'as_yaml':True})
            self.assertNotIn(self.env['NETCLAW_PASSWORD'],json.dumps(detail))
        self.assertEqual((await self.call('pyats_testbed_activate',{'name':'static'}))['code'],'no_static_fallback_in_dynamic_mode')
        combined=fixture('cml','combined-cml-netbox');combined['sources']+=fixture('netbox')['sources']
        self.assertEqual((await self.call('netclaw_testbed_compose',{'envelope':combined}))['preview']['devices'],2)
        self.assertEqual((await self.call('pyats_testbed_validate',{'name':combined['name']}))['status'],'completed')
        self.assertEqual((await self.call('pyats_testbed_activate',{'name':combined['name']}))['active'],combined['name'])
        self.assertEqual(len((await self.call('pyats_list_devices'))['devices']),2)
        failed=fixture('netbox','partial-after-active');failed['sources'][0]['complete']=False
        self.assertEqual((await self.call('netclaw_testbed_compose',{'envelope':failed}))['status'],'error')
        self.assertEqual((await self.call('pyats_testbed_list'))['active'],combined['name'])

    @native_case
    async def test_raw_fetch_and_credential_bypass_refused_and_dryrun_not_stored(self):
        for source in ('rest','file','netbox','itential_inventory'):
            value=await self.call('pyats_testbed_build',{'name':'unsafe','source':source})
            self.assertEqual(value['status'],'error')
        e=fixture(name='dryrun')
        result=await self.call('pyats_testbed_build',{'name':e['name'],'source':'inline','data':e,'dry_run':True})
        self.assertEqual(result['status'],'completed',result);self.assertFalse(result['stored'])
        self.assertEqual((await self.call('pyats_testbed_list'))['dynamic'],[])
        result=await self.call('pyats_testbed_build',{'name':e['name'],'source':'inline','data':e,'activate':True})
        self.assertEqual(result['status'],'error')

    @native_case
    async def test_missing_credentials_cannot_activate(self):
        e=fixture(name='missing-credentials');e['credentials']={'username_env':'PYATS_DEVICE_MISSING_USERNAME','password_env':'PYATS_DEVICE_MISSING_PASSWORD','enable_env':'PYATS_DEVICE_MISSING_ENABLE_PASSWORD'}
        self.assertEqual((await self.call('netclaw_testbed_compose',{'envelope':e}))['status'],'completed')
        self.assertEqual((await self.call('pyats_testbed_validate',{'name':e['name']}))['status'],'invalid')
        self.assertEqual((await self.call('pyats_testbed_activate',{'name':e['name']}))['status'],'error')
        self.assertEqual((await self.call('pyats_testbed_list'))['active'],'none')

    async def test_static_default_keeps_operator_inventory_and_refuses_dynamic_composition(self):
        from mcp.client.client import Client
        from mcp.client.stdio import stdio_client
        static=Path(self.env['PYATS_TESTBED_PATH'])
        static.write_text('devices:\n  static-router:\n    os: iosxe\n    type: router\n    connections:\n      cli:\n        protocol: ssh\n        ip: 192.0.2.254\n        port: 22\n')
        before=static.read_bytes()
        self.params.env.pop('NETCLAW_TESTBED_MODE');self.params.env.pop('NETCLAW_TESTBED_SOURCES')
        async with Client(stdio_client(self.params,errlog=self.errors),read_timeout_seconds=60) as client:
            self.assertEqual((await self.call('pyats_testbed_list',client=client))['active'],'static')
            self.assertEqual(len((await self.call('pyats_list_devices',client=client))['devices']),1)
            self.assertEqual((await self.call('pyats_testbed_activate',{'name':'static'},client=client))['status'],'completed')
            self.assertEqual((await self.call('netclaw_testbed_compose',{'envelope':fixture()},client=client))['code'],
                'select_dynamic_mode_and_sources_before_composition')
        self.assertEqual(static.read_bytes(),before)

    @native_case
    async def test_restart_is_empty_and_one_process_cli_works(self):
        from mcp.client.client import Client
        from mcp.client.stdio import stdio_client
        e=fixture(name='cli-fixture')
        await self.call('netclaw_testbed_compose',{'envelope':e})
        async with Client(stdio_client(self.params,errlog=self.errors),read_timeout_seconds=60) as other:
            listing=await self.call('pyats_testbed_list',client=other)
            self.assertEqual(listing['active'],'none');self.assertEqual(listing['dynamic'],[])
        file=self.private/'candidate.json';file.write_text(json.dumps(e));file.chmod(0o600)
        # Explicit empty selected environment prevents owner/source env import.
        envfile=Path(self.env['NETCLAW_RUNTIME_ENV']);envfile.write_text('');envfile.chmod(0o600)
        for activate in (False,True):
            command=[sys.executable,str(ROOT/'scripts/pyats-testbed-session.py'),'--input',str(file)]
            if activate:command.append('--activate')
            process=await asyncio.to_thread(subprocess.run,command,env=self.env,capture_output=True,text=True,timeout=60)
            self.assertEqual(process.returncode,0,process.stdout+process.stderr[-500:])
            value=json.loads(process.stdout);self.assertEqual(value['deviceIO'],'none')
            self.assertNotIn(self.env['NETCLAW_PASSWORD'],process.stdout)
            if activate:self.assertEqual(value['activation']['active'],e['name'])
            else:self.assertEqual(value['activation'],'not_requested')


class ConcurrencyGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_activation_does_not_race_inflight_operation(self):
        from types import SimpleNamespace
        spec=importlib.util.spec_from_file_location('managed_testbed',ROOT/'scripts/pyats-managed.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        server=SimpleNamespace(task_runtime=SimpleNamespace(jobs={}))
        guard=module.ManagedTestbeds(server,{'NETCLAW_TESTBED_MODE':'dynamic','NETCLAW_TESTBED_SOURCES':'structured'})
        async with guard.lock:
            value=json.loads(await guard.call('pyats_testbed_activate',{'name':'candidate'}))
        self.assertEqual(value['code'],'inventory_busy_retry_after_operations_complete')


if __name__=='__main__':unittest.main()
