import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/lib'))
from test_setup_plan import sample_plan


class HarnessTests(unittest.TestCase):
    def test_pyats_native_install_and_observation_share_dynamic_runtime_contract(self):
        from setup_deploy import helper
        from setup_state import guarded_write
        from unittest.mock import patch
        policy=helper(ROOT,'setup-pyats-runtime.py')
        self.deploy.home({'id':'home'})
        guarded_write(self.deploy.root/'.setup/python312',b'/fixture/owned-python\n')
        harness=self.Harness(ROOT,self.claw,self.context,self.deploy,execute=self.execute)
        with patch('setup_harness.shutil.which',side_effect=lambda name,**_:str(self.root/name)), patch.object(harness,'observe_pyats',return_value=True):
            self.assertTrue(harness.install_pyats({'id':'pyats'}))
        checkout=next(args for args,_ in self.calls if 'checkout' in args)
        self.assertEqual(checkout[-1],policy.REVISION)
        upstream=self.deploy.root/'pyats-venv/upstream';upstream.mkdir(parents=True)
        for name in ('pyats_mcp_server.py','pyats_tasks.py'):(upstream/name).write_text('# source\n')
        observed=[policy.REVISION]
        def execute(args,**kwargs):
            return {'returncode':0,'stdout':(observed[0]+'\n').encode() if 'rev-parse' in args else b''}
        harness=self.Harness(ROOT,self.claw,self.context,self.deploy,execute=execute)
        with patch('setup_harness.shutil.which',side_effect=lambda name,**_:str(self.root/name)):
            self.assertFalse(harness.observe_pyats({'id':'pyats'}))
            (upstream/'pyats_testbed_builder.py').write_text('# dynamic source\n')
            self.assertTrue(harness.observe_pyats({'id':'pyats'}))
            observed[0]='f11b02f06e0561392603cdd147d28f82373b5470'
            self.assertFalse(harness.observe_pyats({'id':'pyats'}))

    @unittest.skipUnless(os.environ.get('NETCLAW_SETUP_HERMES_PYTHON'),'opt-in isolated pinned Hermes interpreter')
    def test_actual_pinned_hermes_loader_validates_selected_config(self):
        import subprocess
        self.claw.update(harness='hermes',runtimeVersion='v0.21.6')
        self.deploy.home({'id':'home'})
        interpreter=os.environ['NETCLAW_SETUP_HERMES_PYTHON']
        def execute(args,**kwargs):
            # Only replace the fixture interpreter path. Execute the adapter's
            # actual validation with the real pinned Hermes dependencies.
            result=subprocess.run([interpreter,*args[1:]],cwd=kwargs['cwd'],env=kwargs['env'],
                                  capture_output=True,timeout=kwargs['timeout'])
            return {'returncode':result.returncode,'stdout':result.stdout}
        harness=self.Harness(ROOT,self.claw,self.context,self.deploy,execute=execute)
        self.assertEqual(harness.onboard({'id':'onboard'})['state'],'verified')

    def test_runtime_version_alone_never_proves_hud_dependencies(self):
        from setup_state import guarded_write
        from unittest.mock import patch
        self.deploy.home({'id':'home'})
        python=self.deploy.root/'.setup/python/bin/python'
        guarded_write(python,b'#!/bin/sh\nexit 0\n');python.chmod(0o700)
        guarded_write(self.deploy.root/'.setup/python312',str(python).encode())
        def execute(args,**kwargs):
            self.calls.append((args,kwargs))
            return {'returncode':0,'stdout':b'2026.7.1-2'}
        harness=self.Harness(ROOT,self.claw,self.context,self.deploy,execute=execute)
        self.assertFalse(harness.observe_runtime({'id':'runtime'}))
        with patch.object(harness,'observe_hud',return_value=True):self.assertTrue(harness.observe_runtime({'id':'runtime'}))
        python.unlink();python.symlink_to(sys.executable)
        with patch.object(harness,'observe_hud',return_value=True):self.assertFalse(harness.observe_runtime({'id':'runtime'}))

    def test_hud_observation_checks_locked_versions_transitive_tree_and_imports(self):
        import json
        from setup_state import guarded_write
        from unittest.mock import patch
        base=self.deploy.source/'ui/netclaw-visual'
        package={'dependencies':{'yaml':'^2.8.1','express':'^4.18.2'}}
        lock={'packages':{'':package,'node_modules/yaml':{'version':'2.8.1'},'node_modules/express':{'version':'4.18.2'}}}
        guarded_write(base/'package.json',json.dumps(package).encode())
        guarded_write(base/'package-lock.json',json.dumps(lock).encode())
        for name,version in (('yaml','2.8.1'),('express','4.18.2')):
            guarded_write(base/'node_modules'/name/'package.json',json.dumps({'version':version}).encode())
        failure=[None]
        def execute(args,**kwargs):
            self.calls.append((args,kwargs));return {'returncode':int(failure[0] is not None and failure[0] in args),'stdout':b''}
        harness=self.Harness(ROOT,self.claw,self.context,self.deploy,execute=execute)
        with patch('setup_harness.shutil.which',side_effect=lambda name,**_:str(self.root/name)):
            self.assertTrue(harness.observe_hud({'id':'runtime'}))
            for failure[0] in ('ls','--eval'):
                self.assertFalse(harness.observe_hud({'id':'runtime'}))
            failure[0]=None
            target=base/'node_modules/yaml/package.json';target.write_text('{"version":"1.0.0"}')
            self.calls.clear();self.assertFalse(harness.observe_hud({'id':'runtime'}));self.assertFalse(self.calls)
        self.assertTrue(all('install' not in args and 'ci' not in args and k.get('credentials') is None for args,k in self.calls))

    def test_incompatible_webex_is_refused_before_configuration_or_native_execution(self):
        from setup_plan import PlanValidator
        self.claw['channels']=[{'id':'webex','settingKeys':[]}]
        report=PlanValidator(ROOT).inspect(self.plan)
        self.assertFalse(report['applyReady'])
        self.assertIn('channel_plugin_api_incompatible',[e['code'] for e in report['errors']])
        harness=self.Harness(ROOT,self.claw,self.context,self.deploy,execute=self.execute)
        self.assertEqual(harness.onboard({'id':'onboard'}),{'state':'configuration_required'})
        self.assertFalse(self.calls)
        self.assertFalse((self.root/'claw/openclaw.json').exists())

    def setUp(self):
        from setup_deploy import Deployment
        from setup_harness import Harness
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.plan=sample_plan(str(self.root));self.claw=self.plan['claws'][0]
        self.context={'plan':self.plan,'runId':'run-test','planHash':'d'*64,'lockFds':(),
            'journal':{'effects':[]},'artifactIntent':lambda *args:None,'writerStarted':lambda *args:None}
        self.deploy=Deployment(ROOT,self.claw,self.context);self.Harness=Harness
        self.calls=[]

    def execute(self,args,**kwargs):
        self.calls.append((args,kwargs));return {'returncode':0,'stdout':b'guidance only'}

    def test_unknown_version_and_unsupported_api_fail_before_commands(self):
        from setup_schema import Invalid
        self.claw['runtimeVersion']='9999.1'
        with self.assertRaises(Invalid):self.Harness(ROOT,self.claw,self.context,self.deploy,execute=self.execute)
        self.assertFalse(self.calls)

    def test_hermes_writes_exact_selected_model_without_guidance_only_setup(self):
        from setup_state import guarded_read
        from setup_schema import loads
        self.claw.update(harness='hermes',runtimeVersion='v0.21.6')
        self.deploy.home({'id':'home'})
        harness=self.Harness(ROOT,self.claw,self.context,self.deploy,execute=self.execute)
        result=harness.onboard({'id':'onboard'})
        self.assertEqual(result['state'],'verified')
        config=loads(guarded_read(self.root/'claw/config.yaml'))
        self.assertEqual(config['model'],{'provider':'anthropic','default':'fixture-model','api_mode':'anthropic_messages'})
        self.assertFalse(any('setup' in args or '--non-interactive' in args for args,_ in self.calls))
        self.assertTrue(all(k['env']['HERMES_HOME']==str(self.root/'claw') for _,k in self.calls))

    def test_openclaw_reference_config_and_local_api_modes(self):
        harness=self.Harness(ROOT,self.claw,self.context,self.deploy,execute=self.execute)
        config=harness.base_config()
        self.assertEqual(config['models']['providers']['anthropic']['apiKey'],
                         {'source':'env','provider':'default','id':'ANTHROPIC_API_KEY'})
        self.claw['provider'].update(id='lm-studio',kind='local',apiMode='openai-responses',endpoint='http://127.0.0.1:1234/v1',credentialKeys=[])
        config=harness.base_config()
        self.assertEqual(config['models']['providers']['lmstudio']['api'],'openai-responses')
        self.assertNotIn('apiKey',config['models']['providers']['lmstudio'])

    def test_hermes_explicit_transport_and_custom_key_reference_survive_projection(self):
        sys.path.insert(0,str(ROOT/'mcp-servers/hermes-hud-mcp'))
        from model_config import protected_model
        from ledger import HudError
        self.claw.update(harness='hermes',runtimeVersion='v0.21.6')
        self.claw['provider'].update(id='custom',kind='cloud',apiMode='openai-responses',endpoint='https://example.invalid/v1',credentialKeys=['NETCLAW_MODEL_API_KEY'])
        harness=self.Harness(ROOT,self.claw,self.context,self.deploy,execute=self.execute)
        config=harness.base_config();projected=protected_model(config)
        self.assertEqual(projected['providers']['netclaw-selected']['api_mode'],'codex_responses')
        self.assertEqual(projected['providers']['netclaw-selected']['key_env'],'NETCLAW_MODEL_API_KEY')
        config['providers']['netclaw-selected']['key_cmd']='unsafe'
        with self.assertRaises(HudError):protected_model(config)
        self.claw['provider'].update(id='openai',credentialKeys=['OPENAI_API_KEY'],endpoint='')
        self.assertEqual(harness.base_config()['model']['provider'],'openai-api')

    def test_local_models_keep_harness_specific_endpoint_and_api_modes(self):
        from setup_plan import PlanValidator
        validator=PlanValidator(ROOT)
        for harness,version,provider,api,endpoint,expected in [
            ('openclaw','2026.7.1-2','ollama','ollama','http://127.0.0.1:11434','ollama'),
            ('hermes','v0.21.6','ollama','openai','http://127.0.0.1:11434/v1','chat_completions'),
            ('openclaw','2026.7.1-2','lm-studio','openai-responses','http://127.0.0.1:1234/v1','openai-responses'),
            ('hermes','v0.21.6','lm-studio','openai','http://127.0.0.1:1234/v1','chat_completions')]:
            with self.subTest(harness=harness,provider=provider):
                claw=copy.deepcopy(self.claw);claw.update(harness=harness,runtimeVersion=version,workspace=claw['runtimeHome'] if harness=='hermes' else claw['runtimeHome']+'/workspace')
                claw['provider'].update(id=provider,kind='local',model='fixture-local',apiMode=api,endpoint=endpoint,credentialKeys=[]);claw['settings']={}
                plan=copy.deepcopy(self.plan);plan['claws']=[claw]
                report=validator.inspect(plan);self.assertTrue(report['valid'],report)
                config=self.Harness(ROOT,claw,self.context,self.deploy,execute=self.execute).base_config()
                if harness=='openclaw':
                    actual=config['models']['providers'][{'lm-studio':'lmstudio'}.get(provider,provider)]
                    self.assertEqual(actual['api'],expected);self.assertEqual(actual['baseUrl'],endpoint)
                else:
                    self.assertEqual(config['model']['api_mode'],expected);self.assertEqual(config['model']['base_url'],endpoint)
                claw['provider']['endpoint']=endpoint.removesuffix('/v1') if endpoint.endswith('/v1') else endpoint+'/v1'
                self.assertFalse(validator.inspect(plan)['valid'])
        self.assertFalse(self.calls)


if __name__=='__main__':unittest.main()
