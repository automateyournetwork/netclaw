#!/usr/bin/env python3
"""Source-only member readiness/provisioning fixtures; no gateway or provider calls."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'mcp-servers/protocol-mcp'))
from bgp.federation.runtime import Runtime


def script(name):
    spec = importlib.util.spec_from_file_location('fixture_'+name.replace('-', '_'), ROOT/'scripts'/name)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


ENV = {'CONVERGENCE_ENABLED':'true', 'CONVERGENCE_API_URL':'https://convergence.example',
       'CONVERGENCE_API_TOKEN':'fixture-viewer', 'CONVERGENCE_SITE':'lab',
       'CONVERGENCE_EXPORTERS':'192.0.2.1', 'OLLAMA_API_KEY':'fixture-provider',
       'AWS_SECRET_ACCESS_KEY':'must-not-copy', 'SLACK_BOT_TOKEN':'must-not-copy'}


class MemberTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.border = self.root/'Border'; self.border.mkdir(mode=0o700)
        self.runtime = Runtime('openclaw', self.border, self.border/'openclaw.json', None)
        self.member = self.root/'Member'
        self.values = dict(ENV)
        self.config = {'mcp': {'servers': {'convergence-read-mcp': {'command':'danger',
            'env': {'NETCLAW_RUNTIME_ENV': str(self.border/'.env'), 'SLACK_BOT_TOKEN':'must-not-copy'}},
            'other-mcp': {'command':'danger'}}},
            'agents': {'defaults': {'workspace': str(self.border/'workspace'), 'model': {'primary':'ollama/fixture-model'}}},
            'models': {'providers': {'ollama': {'api':'openai-completions', 'baseUrl':'https://ollama.example/v1',
                'apiKey':'${OLLAMA_API_KEY}', 'models':[{'id':'fixture-model','name':'Fixture','contextWindow':8192}]},
                'other': {'apiKey':'must-not-copy'}}}, 'channels': {'slack': {'token':'must-not-copy'}}}
        self.write_border()
        records = self.border/'python-runtimes/records'; records.mkdir(parents=True)
        for component in ('convergence-read','n2n'):(records/component).write_text(sys.executable+'\n')
        self.home = script('in2n-member-home.py')
        self.profiles = script('in2n-profiles.py')
        self.profiles.ENV_FILE = str(self.border/'.env')

    def write_border(self):
        self.runtime.config.write_text(json.dumps(self.config)); self.runtime.config.chmod(0o600)
        (self.border/'.env').write_text(''.join(k+'='+json.dumps(v)+'\n' for k,v in self.values.items()))
        (self.border/'.env').chmod(0o600)

    def test_ready_only_with_valid_complete_enabled_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIn('convergence', self.profiles.profiles())
            for key in ('CONVERGENCE_ENABLED','CONVERGENCE_API_URL','CONVERGENCE_API_TOKEN','CONVERGENCE_SITE','CONVERGENCE_EXPORTERS'):
                saved = self.values.pop(key); self.write_border()
                self.assertNotIn('convergence', self.profiles.profiles(), key)
                self.values[key] = saved
            for key, value in [('CONVERGENCE_ENABLED','false'),('CONVERGENCE_API_URL','http://192.0.2.1'),
                               ('CONVERGENCE_SITE','../escape'),('CONVERGENCE_EXPORTERS','not-an-ip'),
                               ('CONVERGENCE_API_TOKEN','bad token')]:
                saved = self.values[key]; self.values[key] = value; self.write_border()
                self.assertFalse(self.profiles.profiles(include_unconfigured=True)['convergence']['configured'])
                self.values[key] = saved
            self.write_border()
            with patch.dict(os.environ, {'CONVERGENCE_ENABLED':'false'}):
                self.assertNotIn('convergence', self.profiles.profiles())

    def test_hermes_does_not_advertise_or_provision_convergence(self):
        with patch.object(self.profiles, '_RUNTIME', Runtime('hermes', self.border, self.runtime.config, None)):
            self.assertNotIn('convergence', self.profiles.profiles(include_unconfigured=True))
        with self.assertRaisesRegex(ValueError, 'Hermes'):
            self.home.provision_convergence(Runtime('hermes', self.border, self.runtime.config, None), 'lab', self.member)
        with self.assertRaisesRegex(ValueError, 'only the subnet'):
            self.home.provision_hermes(self.runtime, 'lab', 'convergence', self.member)
        self.assertFalse(self.member.exists())

    def test_profile_scope_and_environment_slice(self):
        scope = self.profiles.scope('convergence')
        self.assertEqual([x['name'] for x in scope if x['tier']=='specialty'], ['convergence-observations'])
        self.assertEqual(self.profiles.MCP_SERVERS['convergence'], ['convergence-read-mcp'])
        keys = self.profiles.env_slice_keys('convergence', [*ENV, 'GAIT_MCP_SCRIPT'])
        self.assertNotIn('AWS_SECRET_ACCESS_KEY', keys); self.assertNotIn('OLLAMA_API_KEY', keys)
        self.assertIn('CONVERGENCE_API_TOKEN', keys)

    def test_provisioned_home_uses_member_credentials_and_scoped_workspace(self):
        before = self.runtime.config.read_bytes()
        home = self.home.provision_convergence(self.runtime, 'lab', self.member)
        config = json.loads((home/'openclaw.json').read_text())
        self.assertEqual(set(config['mcp']['servers']), {'convergence-read-mcp'})
        self.assertEqual(set(config['models']['providers']), {'ollama'})
        self.assertEqual(config['tools']['allow'], ['read', 'convergence-read-mcp__convergence_flow_summary', 'convergence-read-mcp__convergence_flow_evidence'])
        self.assertTrue(config['tools']['fs']['workspaceOnly'])
        self.assertFalse(config['tools']['elevated']['enabled'])
        self.assertEqual(config['agents']['defaults']['model']['primary'], 'ollama/fixture-model')
        self.assertNotIn('must-not-copy', json.dumps(config)+(home/'.env').read_text())
        self.assertNotIn('fixture-provider', json.dumps(config))
        self.assertNotIn('fixture-viewer', json.dumps(config))
        self.assertFalse((home/'workspace').is_symlink())
        self.assertEqual([p.name for p in (home/'workspace/skills').iterdir()], ['convergence-observations'])
        entry = config['mcp']['servers']['convergence-read-mcp']
        self.assertEqual(entry['env']['NETCLAW_RUNTIME_ENV'], str(home/'.env'))
        self.assertEqual(entry['env']['NETCLAW_RUNTIME_ROOT'], str(home/'python-runtimes'))
        with patch.dict(os.environ, {'HOME':str(self.root), 'PATH':os.defpath,
            'N2N_MEMBER_ENV_FILE':str(home/'.env'), 'CONVERGENCE_API_TOKEN':'border-wrong',
            'SLACK_BOT_TOKEN':'must-not-copy'}, clear=True):
            script('in2n-member.py')._load_env_file()
            self.assertNotIn('SLACK_BOT_TOKEN', os.environ)
            command, env, _ = script('component-launch.py').resolve('convergence-read', env={**os.environ, **entry['env']})
            self.assertEqual(env['CONVERGENCE_API_TOKEN'], 'fixture-viewer')
            self.assertEqual(env['OLLAMA_API_KEY'], 'fixture-provider')
            self.assertEqual(command[0], sys.executable)
        self.assertEqual((home/'.env').stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.runtime.config.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'preserved'):
            self.home.provision_convergence(self.runtime, 'lab', self.member)

    def test_setup_member_policy_is_shared_and_does_not_restrict_border(self):
        sys.path.insert(0, str(ROOT/'scripts/lib'))
        from setup_harness import Harness
        from convergence_member_policy import native_tool_policy
        policy = json.loads((ROOT/'config/components/harness-adapters.json').read_text())['openclaw']
        base = {'harness':'openclaw', 'runtimeHome':str(self.border), 'runtimeVersion':policy['versions'][0],
                'workspace':str(self.border/'workspace'), 'endpoints':{'gatewayPort':18789},
                'provider':{'id':'ollama', 'endpoint':'http://127.0.0.1:11434/v1', 'apiMode':'openai',
                            'model':'fixture-model', 'credentialKeys':[]}}
        for role, profile in (('member', 'convergence'), ('border', None), ('focused', None), ('member', 'subnet')):
            claw = {**base, 'role':role, 'capabilities':{'profile':profile}}
            config = Harness(ROOT, claw, {}, None).base_config()
            if role == 'member' and profile == 'convergence':
                self.assertEqual(config['tools'], native_tool_policy())
            else:
                self.assertNotIn('tools', config)

    def test_actual_setup_generated_provider_secret_refs_and_builtin_models(self):
        # Use the installer builder, not a hand-written approximation of its shape.
        sys.path.insert(0, str(ROOT/'scripts/lib'))
        from setup_harness import Harness
        policy = json.loads((ROOT/'config/components/harness-adapters.json').read_text())['openclaw']
        for provider, endpoint, api_mode, key in (
            ('ollama', 'https://ollama.example/v1', 'openai', 'OLLAMA_API_KEY'),
            ('anthropic', '', 'anthropic', 'ANTHROPIC_API_KEY'),
        ):
            claw = {'harness':'openclaw', 'runtimeHome':str(self.border), 'runtimeVersion':policy['versions'][0],
                    'workspace':str(self.border/'workspace'), 'endpoints':{'gatewayPort':18789},
                    'provider':{'id':provider, 'endpoint':endpoint, 'apiMode':api_mode,
                                'model':'fixture-model', 'credentialKeys':[key]}}
            self.config = Harness(ROOT, claw, {}, None).base_config()
            self.config['mcp']['servers']['convergence-read-mcp'] = {'command':'fixture'}
            self.values[key] = 'fixture-provider'; self.write_border()
            home = self.home.provision_convergence(self.runtime, 'lab', self.root/('native-'+provider))
            copied = json.loads((home/'openclaw.json').read_text())['models']['providers'][provider]
            self.assertEqual(copied['apiKey'], {'source':'env', 'provider':'default', 'id':key})
            self.assertEqual('models' in copied, bool(endpoint))
            self.assertNotIn('fixture-provider', (home/'openclaw.json').read_text())
            self.assertEqual(script('write-env.py').values((home/'.env').read_text())[key], 'fixture-provider')

    def test_actual_setup_local_provider_needs_no_cloud_credential(self):
        sys.path.insert(0, str(ROOT/'scripts/lib'))
        from setup_harness import Harness
        policy = json.loads((ROOT/'config/components/harness-adapters.json').read_text())['openclaw']
        claw = {'harness':'openclaw', 'runtimeHome':str(self.border), 'runtimeVersion':policy['versions'][0],
                'workspace':str(self.border/'workspace'), 'endpoints':{'gatewayPort':18789},
                'provider':{'id':'ollama', 'endpoint':'http://127.0.0.1:11434/v1', 'apiMode':'openai',
                            'model':'fixture-model', 'credentialKeys':[]}}
        self.config = Harness(ROOT, claw, {}, None).base_config()
        self.config['mcp']['servers']['convergence-read-mcp'] = {'command':'fixture'}
        self.values.pop('OLLAMA_API_KEY'); self.write_border()
        home = self.home.provision_convergence(self.runtime, 'lab', self.root/'local-member')
        copied = json.loads((home/'openclaw.json').read_text())['models']['providers']['ollama']
        self.assertNotIn('apiKey', copied)
        self.assertNotIn('OLLAMA_API_KEY', script('write-env.py').values((home/'.env').read_text()))
        for endpoint in ('https://ollama.example/v1', 'http://192.0.2.1/v1', 'http://user@127.0.0.1/v1'):
            self.config['models']['providers']['ollama']['baseUrl'] = endpoint; self.write_border()
            with self.assertRaisesRegex(ValueError, 'API-key'):
                self.home.provision_convergence(self.runtime, 'lab', self.member)
        self.config['models']['providers']['ollama'].update(baseUrl='http://127.0.0.1:11434/v1', authHeader=True)
        self.write_border()
        with self.assertRaisesRegex(ValueError, 'API-key'):
            self.home.provision_convergence(self.runtime, 'lab', self.member)

    def test_provider_secret_refs_reject_other_sources_and_missing_values(self):
        good = {'source':'env', 'provider':'default', 'id':'OLLAMA_API_KEY'}
        for bad in ({**good, 'source':'file'}, {**good, 'source':'exec'}, {**good, 'provider':'vault'},
                    {**good, 'extra':'unexpected'}, {**good, 'id':'MISSING_API_KEY'}, {**good, 'id':'../env'}):
            self.config['models']['providers']['ollama']['apiKey'] = bad; self.write_border()
            with self.assertRaises(ValueError):self.home.provision_convergence(self.runtime, 'lab', self.member)
            self.assertFalse(self.member.exists())

    def test_posture_is_explicit_and_defaults_fail_closed(self):
        writer = script('write-env.py')
        for index, mode in enumerate((None, 'production', 'testing')):
            if mode is not None:self.values['N2N_RISK_MODE'] = mode
            self.write_border()
            home = self.home.provision_convergence(self.runtime, 'lab', self.root/('mode-'+str(index)))
            self.assertEqual(writer.values((home/'.env').read_text())['N2N_RISK_MODE'], mode or 'production')
        self.values['N2N_RISK_MODE'] = 'unknown'; self.write_border()
        with self.assertRaisesRegex(ValueError, 'risk mode'):
            self.home.provision_convergence(self.runtime, 'lab', self.member)
        self.assertFalse(self.member.exists())

    def test_missing_selected_model_never_invents_a_member_model(self):
        self.config['agents']['defaults'].pop('model'); self.write_border()
        with self.assertRaisesRegex(ValueError, 'explicit provider/model'):
            self.home.provision_convergence(self.runtime, 'lab', self.member)
        self.assertFalse(self.member.exists())

    def test_literal_provider_key_is_moved_to_member_env(self):
        self.config['models']['providers']['ollama']['apiKey'] = 'fixture-literal-provider'
        self.write_border()
        self.home.provision_convergence(self.runtime, 'lab', self.member)
        self.assertNotIn('fixture-literal-provider', (self.member/'openclaw.json').read_text())
        self.assertIn('fixture-literal-provider', (self.member/'.env').read_text())

    def test_missing_provider_reference_and_connector_records_fail_before_writes(self):
        self.values.pop('OLLAMA_API_KEY'); self.write_border()
        with self.assertRaisesRegex(ValueError, 'credential'):
            self.home.provision_convergence(self.runtime, 'lab', self.member)
        self.assertFalse(self.member.exists())
        self.values['OLLAMA_API_KEY']='fixture-provider'; self.write_border()
        (self.border/'python-runtimes/records/convergence-read').unlink()
        with self.assertRaisesRegex(ValueError, 'install convergence-read'):
            self.home.provision_convergence(self.runtime, 'lab', self.member)
        self.assertFalse(self.member.exists())

    def test_migration_scaffold_launches_scoped_home_without_enrollment(self):
        staging = self.root/'staging'
        env = {'HOME':str(self.root), 'PATH':os.environ['PATH'], 'NETCLAW_RUNTIME':'openclaw',
               'OPENCLAW_STATE_DIR':str(self.border), 'OPENCLAW_CONFIG_PATH':str(self.runtime.config),
               'XDG_CONFIG_HOME':str(self.root/'xdg')}
        result = subprocess.run([sys.executable, str(ROOT/'scripts/in2n-migrate.py'), '--risk','lab',
            '--staging',str(staging), '--border-endpoint','127.0.0.1:11790'], env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        home = staging/'members/convergence/home'
        self.assertTrue((home/'openclaw.json').is_file())
        self.assertIn(str(home/'.env'), (staging/'members/convergence/run.sh').read_text())
        self.assertIn(str(home/'.env'), (staging/'RUNBOOK.md').read_text())
        self.assertNotIn('fixture-viewer', result.stdout+result.stderr)
        self.assertNotIn('fixture-provider', result.stdout+result.stderr)
        self.assertNotIn('N2N_ENROLLMENT_TOKEN=', (home/'.env').read_text())


if __name__ == '__main__': unittest.main()
