"""Actual JavaScript API signer + Python consumer; no network devices involved."""
import asyncio
import base64
import concurrent.futures
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/lib'))
from migration_artifacts import PrivateMigration, Refused
spec=importlib.util.spec_from_file_location('migration_managed',ROOT/'scripts/pyats-managed.py')
managed_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(managed_module)


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.vault=self.root/'changes'
        self.testbed=self.root/'tb.yaml';self.testbed.write_text('devices: synthetic\n')
        self.calls=[]
        async def configure(device_name,config_commands):
            self.calls.append((device_name,config_commands))
            return json.dumps({'status':'success','commands_applied':config_commands,'output':'RESULT_CANARY'})
        async def collect(device_name):
            return json.dumps({'status':'completed','output':'hostname SYNTHETIC_CONFIG_CANARY\n'})
        self.device=SimpleNamespace(os='iosxe',connections={'cli':{'protocol':'ssh','ip':'192.0.2.12','port':22}})
        self.server=SimpleNamespace(pyats_configure_device=configure,pyats_show_running_config=collect,
            TESTBED_PATH=str(self.testbed),_load_testbed=lambda:SimpleNamespace(devices={'target':self.device}),
            _get_testbed_connection_args=lambda device:{'init_config_commands':['hostname forbidden-before-baseline'],'ssh_options':'fixture-host-key-policy'},
            _dynamic_testbeds=SimpleNamespace(active_entry=lambda:None),_CONN_CACHE_TTL=0)
        self.managed=managed_module.ManagedTestbeds(self.server,{'NETCLAW_CHANGE_ROOT':str(self.vault)})
        self.current,_=self.managed.private_inventory()

    def issue(self,prepare=False,content='hostname SYNTHETIC_CANDIDATE_CANARY\n'):
        node=os.environ.get('NETCLAW_TEST_NODE') or shutil.which('node')
        args={'root':str(self.vault),'devices':self.current['devices'],'harness':self.current['harness'],
              'testbed':self.current['testbed'],'content':content,'prepareOnly':prepare}
        result=subprocess.run([node,str(ROOT/'tests/netconverter/issue-fixture.mjs')],input=json.dumps(args),text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def apply(self,f):
        return json.loads(asyncio.run(self.managed.call('pyats_configure_device',{'device_name':'target',
          'artifact_ref':f['candidate']['artifact_ref'],'grant_ref':f.get('grant','0'*32)})))

    def test_actual_api_issue_original_identity_private_result_and_replay(self):
        f=self.issue();result=self.apply(f)
        self.assertEqual(result['status'],'applied_unverified',result);self.assertEqual(len(self.calls),1)
        self.assertNotIn('CANARY',json.dumps(result));self.assertIn('CANARY',Path(result['evidence']['path']).read_text())
        self.assertEqual(self.apply(f)['status'],'error');self.assertEqual(len(self.calls),1)
        self.assertEqual(self.managed.private.read('attempts/'+f['grant']+'.json')['state'],'unknown')

    def test_prepare_does_not_issue_capability(self):
        f=self.issue(True);self.assertNotIn('applyGrants',f['change'])
        self.assertEqual(self.apply(f)['status'],'error');self.assertEqual(self.calls,[])

    def test_changed_candidate_or_baseline_or_closed_record(self):
        f=self.issue();p=self.vault/'candidates'/(f['candidate']['artifact_ref']+'.cfg');p.write_text('changed')
        self.assertIn('candidate_changed',self.apply(f)['code']);self.assertFalse(self.calls)

    def test_testbed_and_endpoint_changes_refused(self):
        f=self.issue();self.testbed.write_text('changed inventory')
        self.assertIn('context_changed',self.apply(f)['code']);self.assertFalse(self.calls)

    def test_wrong_harness_and_forged_signature(self):
        f=self.issue();store=PrivateMigration(self.vault)
        with self.assertRaises(Refused):store.claim(f['grant'],f['candidate']['artifact_ref'],self.current,self.current['devices'][0])
        p=self.vault/'grants'/(f['grant']+'.json');data=json.loads(p.read_text());data['signature']='0'*64;p.write_text(json.dumps(data))
        self.assertEqual(self.apply(f)['code'],'invalid_apply_signature');self.assertFalse(self.calls)

    def test_concurrent_claim_has_one_winner_and_restart_cannot_replay(self):
        f=self.issue()
        def run(_):
            try:return self.managed.private.claim(f['grant'],f['candidate']['artifact_ref'],self.current,self.current['devices'][0])
            except Refused:return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(run,range(8)))
        self.assertEqual(sum(r is not None for r in results),1)
        restarted=PrivateMigration(self.vault,self.current['harness'])
        with self.assertRaises(Refused):restarted.claim(f['grant'],f['candidate']['artifact_ref'],self.current,self.current['devices'][0])

    def test_original_denial_or_lost_response_never_uses_fallback(self):
        f=self.issue()
        async def denied(**kwargs):
            self.calls.append('original');return json.dumps({'status':'error','error':'DENIAL_CANARY'})
        self.managed.original['pyats_configure_device']=denied
        result=self.apply(f);self.assertEqual(result['status'],'unknown');self.assertNotIn('CANARY',json.dumps(result))
        self.assertEqual(self.calls,['original']);self.apply(f);self.assertEqual(self.calls,['original'])

    def test_collection_and_actual_prepare_baseline_without_model_content(self):
        f=self.issue(True)
        result=json.loads(asyncio.run(self.managed.call('pyats_show_running_config',{'device_name':'target','output_mode':'private','change_ref':f['change']['id']})))
        self.assertEqual(result['status'],'completed',result);self.assertNotIn('CANARY',json.dumps(result))
        self.assertIn('CANARY',Path(f['change']['devices'][0]['baselinePath']).read_text())
        self.assertFalse(Path(f['change']['devices'][0]['rollbackPath']).exists())

    def test_mixed_input_and_unqualified_route_refused(self):
        f=self.issue()
        result=json.loads(asyncio.run(self.managed.call('pyats_configure_device',{'device_name':'target','config_commands':'hostname other',
          'artifact_ref':f['candidate']['artifact_ref'],'grant_ref':f['grant']})))
        self.assertEqual(result['code'],'choose_inline_or_exact_artifact_input');self.assertFalse(self.calls)
        self.server._CONN_CACHE_TTL=60
        self.assertEqual(self.apply(f)['code'],'private_route_requires_uncached_connections')

    def test_junos_collection_is_fixed_private_read_in_original_identity(self):
        self.device.os='junos';commands=[]
        original=lambda name:'Cisco original collector'
        self.server._execute_get_running_config_str=original
        self.server._get_device=lambda name:SimpleNamespace(execute=lambda command:(commands.append(command) or 'set system host-name JUNOS_CANARY\n'))
        self.server._disconnect_device=lambda device:None
        async def collect(device_name):
            return json.dumps({'status':'completed','output':self.server._execute_get_running_config_str(device_name)})
        self.managed.original['pyats_show_running_config']=collect
        result=json.loads(asyncio.run(self.managed.call('pyats_show_running_config',{'device_name':'target','output_mode':'private'})))
        self.assertEqual(result['status'],'completed');self.assertNotIn('CANARY',json.dumps(result))
        self.assertEqual(commands,['show configuration | display set | no-more'])
        self.assertIs(self.server._execute_get_running_config_str,original)

    def test_closed_changed_policy_endpoint_and_baseline_bindings(self):
        for mutation in ('closed','policy','record_endpoint','baseline'):
            f=ApplyTests();f.setUp();self.addCleanup(f.doCleanups);issued=f.issue()
            record_file=f.vault/'records'/issued['change']['id']/'record.json'
            record=json.loads(record_file.read_text())
            if mutation=='closed':record['status']='completed';record_file.write_text(json.dumps(record))
            elif mutation=='record_endpoint':record['devices'][0]['host']='192.0.2.99';record_file.write_text(json.dumps(record))
            elif mutation=='baseline':Path(record['devices'][0]['baselinePath']).write_text('changed baseline')
            else:
                policy_file=f.vault/'policy.json';policy=json.loads(policy_file.read_text());policy['revision']='changed';policy_file.write_text(json.dumps(policy))
            self.assertEqual(f.apply(issued)['status'],'error',mutation);self.assertFalse(f.calls)

    def test_validly_signed_wrong_tool_task_or_expired_claim_is_refused(self):
        for field,value in (('tool','different_config_tool'),('task','0'*32),('expires',0)):
            f=ApplyTests();f.setUp();self.addCleanup(f.doCleanups);issued=f.issue()
            path=f.vault/'grants'/(issued['grant']+'.json');envelope=json.loads(path.read_text())
            claim=json.loads(base64.b64decode(envelope['payload']));claim[field]=value;raw=json.dumps(claim).encode()
            envelope={'payload':base64.b64encode(raw).decode(),'signature':hmac.new((f.vault/'api-signing.key').read_bytes(),raw,hashlib.sha256).hexdigest()}
            path.write_text(json.dumps(envelope))
            self.assertEqual(f.apply(issued)['status'],'error',field);self.assertFalse(f.calls)

    def test_result_storage_failure_after_write_is_unknown_not_unchanged(self):
        f=self.issue()
        with patch.object(self.managed.private,'publish',side_effect=Refused('synthetic_storage_failure')):result=self.apply(f)
        self.assertEqual(result['status'],'unknown');self.assertNotIn('activeUnchanged',result);self.assertEqual(len(self.calls),1)
        self.assertIn('uncertain_private_apply',self.apply(f)['code']);self.assertEqual(len(self.calls),1)

    def test_junos_separator_cannot_escape_set_only_route(self):
        self.device.os='junos';self.current,_=self.managed.private_inventory()
        f=self.issue(content='set system host-name demo; run request system halt\n')
        self.assertIn('without_command_separators',self.apply(f)['code']);self.assertFalse(self.calls)

    def test_private_read_disables_connect_time_writes_and_keeps_logs_private(self):
        original=self.server._get_testbed_connection_args;seen=[]
        async def collect(device_name):
            seen.append(self.server._get_testbed_connection_args(self.device))
            return json.dumps({'status':'completed','output':'hostname SYNTHETIC_CANARY\n'})
        self.managed.original['pyats_show_running_config']=collect
        result=json.loads(asyncio.run(self.managed.call('pyats_show_running_config',{'device_name':'target','output_mode':'private'})))
        self.assertEqual(result['status'],'completed');self.assertEqual(seen[0]['init_config_commands'],[])
        self.assertEqual(seen[0]['init_exec_commands'],[]);self.assertFalse(seen[0]['log_stdout'])
        self.assertEqual(seen[0]['ssh_options'],'fixture-host-key-policy')
        self.assertEqual(Path(seen[0]['logfile']).stat().st_mode&0o777,0o600)
        self.assertIs(self.server._get_testbed_connection_args,original)

    def test_cancellation_keeps_inventory_guard_until_original_operation_finishes(self):
        f=self.issue();original_load=self.server._load_testbed
        async def scenario():
            started=asyncio.Event();finish=asyncio.Event()
            async def original(**kwargs):
                self.calls.append('started');started.set();await finish.wait()
                self.assertIsNot(self.server._load_testbed,original_load)
                return json.dumps({'status':'success'})
            self.managed.original['pyats_configure_device']=original
            task=asyncio.create_task(self.managed.call('pyats_configure_device',{'device_name':'target',
                'artifact_ref':f['candidate']['artifact_ref'],'grant_ref':f['grant']}))
            await started.wait();task.cancel();await asyncio.sleep(0)
            self.assertFalse(task.done());self.assertTrue(self.managed.lock.locked())
            finish.set()
            with self.assertRaises(asyncio.CancelledError):await task
        asyncio.run(scenario())
        self.assertIs(self.server._load_testbed,original_load)
        self.assertTrue(self.managed.private_write_uncertain)
        self.assertIn('uncertain_private_apply',self.apply(f)['code']);self.assertEqual(self.calls,['started'])


if __name__=='__main__':unittest.main()
