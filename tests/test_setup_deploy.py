import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/lib'))
from test_setup_plan import sample_plan


class DeployTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.plan=sample_plan(str(self.root))
        self.claw=self.plan['claws'][0];self.intents=[]
        self.context={'runId':'run-fixture','planHash':'a'*64,'plan':self.plan,
                      'artifactIntent':lambda _,items:self.intents.extend(items)}

    def test_home_and_only_selected_skill_are_private_and_not_shared(self):
        from setup_deploy import Deployment
        deploy=Deployment(ROOT,self.claw,self.context)
        deploy.home({'id':'home','artifacts':[]})
        deploy.skills({'id':'skills','artifacts':[]})
        skills=Path(self.claw['workspace'])/'skills'
        self.assertEqual([p.name for p in skills.iterdir()],['subnet-calculator'])
        self.assertFalse(skills.is_symlink())
        self.assertEqual((skills/'subnet-calculator/SKILL.md').stat().st_mode&0o077,0)
        self.assertTrue(self.intents)

    def test_identity_file_changed_since_review_is_refused(self):
        from setup_deploy import Deployment
        from setup_state import Conflict
        file=self.root/'identity.md';file.write_text('changed')
        self.plan['identity']=[{'owner':self.claw['id'],'kind':'identity','path':str(file),'sha256':'b'*64}]
        deploy=Deployment(ROOT,self.claw,self.context);deploy.home({'id':'home','artifacts':[]})
        with self.assertRaises(Conflict):deploy.inputs({'id':'identity','phase':'identity','artifacts':[]})

    def test_no_inventory_creates_private_empty_testbed_only_for_selected_pyats(self):
        from setup_deploy import Deployment
        from setup_state import Conflict
        deploy=Deployment(ROOT,self.claw,self.context);deploy.home({'id':'home','artifacts':[]})
        effect={'id':'inventory','phase':'inventory','artifacts':[]}
        target=Path(self.claw['workspace'])/'testbed.yaml'
        deploy.inputs(effect);self.assertFalse(target.exists())
        self.claw['capabilities']['components'].append('pyats')
        self.assertEqual(deploy.inputs(effect),{'state':'verified'})
        self.assertEqual(target.read_text(),'devices: {}\n')
        self.assertEqual(target.stat().st_mode&0o077,0)
        target.write_text('devices: {owned: {}}\n')
        with self.assertRaises(Conflict):deploy.inputs(effect)
        self.assertEqual(target.read_text(),'devices: {owned: {}}\n')

    def test_dynamic_policy_has_private_recoverable_output_and_preserves_static_file(self):
        from setup_deploy import Deployment
        from setup_generated import generated
        from setup_plan import PlanValidator
        self.claw['capabilities']['components'].append('pyats')
        self.claw['testbed']={'mode':'dynamic','sources':['netbox','cml']}
        deploy=Deployment(ROOT,self.claw,self.context);deploy.home({'id':'home','artifacts':[]})
        static=Path(self.claw['workspace'])/'testbed.yaml'
        effect={'id':'inventory','phase':'inventory','state':'applying','artifacts':[]}
        self.assertEqual(deploy.observe_files(effect),'retry_owned')
        deploy.inputs(effect);self.assertFalse(static.exists())
        path=Path(self.claw['runtimeHome'])/'testbeds/policy.json'
        self.assertEqual(json.loads(path.read_text())['sources'],['cml','netbox'])
        self.assertEqual(path.stat().st_mode&0o077,0)
        effect['artifacts']=[a for a in self.intents if a['path']==str(path)]
        self.assertEqual(deploy.observe_files(effect),'completed')
        static.write_text('operator-owned')
        deploy.inputs(effect);self.assertEqual(static.read_text(),'operator-owned')
        env=generated(self.claw,PlanValidator(ROOT),'/fixture/python')
        self.assertEqual(env['PYATS_TESTBED_PATH'],'')
        self.assertEqual(env['NETCLAW_TESTBED_SOURCES'],'cml,netbox')
        path.write_text('{}')
        self.assertEqual(deploy.observe_files(effect),'conflict')

    def test_shell_audit_covers_every_component_and_rejects_drift(self):
        from setup_deploy import EffectAudit
        audit=EffectAudit(ROOT)
        catalog=json.loads((ROOT/'config/components/catalog.json').read_text())
        self.assertEqual(set(audit.components),{c['id'] for c in catalog['components']})
        self.assertEqual(audit.components['computer-use']['adapter'],'native')
        self.assertEqual(audit.components['subnet-calc']['adapter'],'isolated-shell')
        audit.verify()

    def test_installed_dashboard_has_its_imported_reference_snapshots(self):
        import re
        from setup_deploy import Deployment
        deploy=Deployment(ROOT,self.claw,self.context)
        outputs={target:data for target,data,_ in deploy.source_outputs()}
        view=deploy.source/'ui/netclaw-visual/src/dashboard/ReferenceViews.jsx'
        imports=re.findall(r"from\s+['\"]([^'\"]+\.json)['\"]",outputs[view].decode())
        self.assertTrue(imports, 'Exercise the actual dashboard data imports')
        for relative in imports:
            target=(view.parent/relative).resolve()
            self.assertTrue(target in outputs, f'Missing installed HUD import: {relative}')
            self.assertTrue(isinstance(json.loads(outputs[target]),(dict,list)))

    def test_only_successful_components_registered_and_built_source_revision_owned(self):
        from setup_deploy import Deployment
        from setup_schema import canonical,loads
        from setup_state import guarded_read
        from setup_harness import Harness
        self.claw['capabilities']['components']=['subnet-calc','netbox']
        effects=[];self.context['journal']={'effects':effects}
        def effect(name,**kwargs):
            value={'id':name,'owner':self.claw['id'],'phase':name,'component':'','artifacts':[],**kwargs};effects.append(value);return value
        self.context['artifactIntent']=lambda key,items:next(e for e in effects if e['id']==key)['artifacts'].extend(items)
        deploy=Deployment(ROOT,self.claw,self.context)
        deploy.home(effect('home'))
        runtime=effect('runtime')
        # This test only serializes registrations; its executable is an owned
        # fixture file, never a borrowed engine/global Python interpreter.
        fixture_python=deploy.root/'python/bin/python'
        deploy.write(runtime,fixture_python,b'#!/bin/sh\nexit 0\n');fixture_python.chmod(0o700)
        deploy.write(runtime,deploy.root/'.setup/python312',(str(deploy.root/'python/bin/python')+'\n').encode())
        copied=deploy.source/'mcp-servers/local/server.py';deploy.write(runtime,copied,b'original',kind='source')
        credentials=effect('credentials');deploy.write(credentials,deploy.root/'.env',b'FIXTURE=local\n',kind='credentials')
        onboard=effect('onboard');deploy.write(onboard,deploy.root/'openclaw.json',canonical(Harness(ROOT,self.claw,self.context,deploy).base_config()))
        success=effect('component-good',phase='components',component='subnet-calc',state='verified')
        effect('component-failed',phase='components',component='netbox',state='failed')
        copied.write_bytes(b'built');deploy.reconcile_source(success)
        self.assertEqual(success['artifacts'][0]['before'],next(a['sha256'] for a in runtime['artifacts'] if a['path']==str(copied)))
        registration=effect('registration');result=deploy.registration(registration)
        self.assertEqual(result['state'],'configuration_required')
        manifest=guarded_read(deploy.root/'netclaw-components.conf').decode().splitlines()
        self.assertIn('subnet-calc',manifest);self.assertNotIn('netbox',manifest)
        registered=loads(guarded_read(deploy.root/'netclaw-mcp-config.json'))['mcpServers']
        self.assertEqual(set(registered),{'subnet-calc-mcp'})
        self.assertEqual(loads(guarded_read(deploy.root/'.setup/components.json'))['deferred'],['netbox'])

    def test_generated_references_are_scoped_and_never_copy_sibling_paths(self):
        from setup_generated import generated,SCRIPTS,COMMANDS
        from setup_plan import PlanValidator
        from setup_secrets import child_environment
        self.claw['capabilities']['components']=['subnet-calc','pyats','gait','document','fortinet']
        result=generated(self.claw,PlanValidator(ROOT),str(self.root/'claw/python/bin/python'))
        self.assertTrue(all(str(self.root/'claw') in v for k,v in result.items() if k not in ('NETCLAW_TESTBED_MODE','NETCLAW_TESTBED_SOURCES','PYATS_MCP_DYNAMIC_ONLY')))
        self.assertEqual(result['PYATS_TESTBED_PATH'],str(Path(self.claw['workspace'])/'testbed.yaml'))
        self.assertEqual(result['GAIT_VENV'],str(self.root/'claw/gait-venv'))
        self.assertIn('component-launch.py',result['FORTINET_MCP_CMD'])
        self.assertEqual(child_environment(self.root/'claw','openclaw',result)['GAIT_VENV'],result['GAIT_VENV'])


if __name__=='__main__':unittest.main()
