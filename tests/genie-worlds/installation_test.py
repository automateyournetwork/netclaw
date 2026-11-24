"""Genie setup boundaries: selected homes, scoped member data and no paid activation."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts/lib'), str(ROOT/'tests')]
from setup_plan import PlanValidator
from setup_generated import generated
from setup_deploy import EffectAudit
from test_setup_plan import sample_plan


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/file)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class Installation(unittest.TestCase):
    def test_selected_home_bindings_and_risk_plan_have_no_google_credential(self):
        plan = sample_plan(); plan['shape'] = 'risk'; plan['verification']['risk'] = True
        border = plan['claws'][0]; border['role'] = 'border'
        border['capabilities'].update(components=['n2n','protocol'], skills=['n2n-federation'])
        member = copy.deepcopy(border)
        member.update(id='worlds', role='member', harnessChoice='inherit',
                      runtimeHome='/private/tmp/netclaw-fixture/worlds',
                      workspace='/private/tmp/netclaw-fixture/worlds/workspace')
        member['service']['name'] = 'netclaw-worlds'
        member['endpoints'] = {k:v+100 for k,v in member['endpoints'].items()}
        member['capabilities'].update(profile='genie-worlds', components=['n2n','genie-worlds'],
                                      skills=['netclaw-genie-worlds'])
        member['settings'] = {k:{**v,'owner':'worlds'} for k,v in member['settings'].items()}
        plan['claws'].append(member)
        validator = PlanValidator(ROOT)
        report = validator.inspect(plan)
        self.assertEqual(report['errors'], [])
        values = generated(member, validator, sys.executable)
        self.assertEqual(values['NETCLAW_GENIE_CONTROL_FILE'], member['runtimeHome']+'/genie-worlds/mcp-control.json')
        self.assertEqual(values['NETCLAW_GENIE_STATE_DIR'], member['runtimeHome']+'/genie-worlds')
        self.assertNotIn('GEMINI_API_KEY', values)
        self.assertNotIn('GOOGLE_API_KEY', values)

    def test_launcher_drops_provider_and_device_credentials(self):
        launcher = module('genie_install_launch', Path('scripts/component-launch.py'))
        with tempfile.TemporaryDirectory(dir=ROOT/'.spec200-local/tests') as tmp:
            home = Path(tmp); record = home/'python-runtimes/records'
            record.mkdir(parents=True); (record/'genie-worlds').write_text(sys.executable)
            env = {'PATH':os.environ['PATH'], 'OPENCLAW_STATE_DIR':str(home),
                   'NETCLAW_RUNTIME_ROOT':str(home/'python-runtimes'),
                   'NETCLAW_RUNTIME_ENV':str(home/'.env'),
                   'NETCLAW_GENIE_CONTROL_FILE':str(home/'genie-worlds/mcp-control.json'),
                   'GEMINI_API_KEY':'private-provider-canary', 'GOOGLE_API_KEY':'second-canary',
                   'PYATS_TESTBED_PATH':'private-device-canary', 'NETCLAW_GENIE_CAMPAIGN_AUTHORITY':'private-authority-canary'}
            args, scoped, cwd = launcher.resolve('genie-worlds', env=env)
            self.assertEqual(scoped['NETCLAW_GENIE_CONTROL_FILE'], env['NETCLAW_GENIE_CONTROL_FILE'])
            self.assertNotIn('canary', json.dumps(scoped))
            self.assertEqual(args[-1], str(ROOT/'mcp-servers/genie-worlds-mcp/server.py'))

    def test_member_spec_has_exact_controls_and_only_backend_binding(self):
        profiles = module('genie_install_profiles', Path('scripts/in2n-profiles.py'))
        spec = json.loads((ROOT/'specs/200-genie-network-worlds/contracts/genie-member.json').read_text())
        servers = json.loads((ROOT/'config/openclaw.json').read_text())['mcpServers']
        validated, warnings = profiles.load_member_spec(spec, servers)
        self.assertEqual(validated['name'], 'genie-worlds-member')
        keys = profiles.spec_env_slice_keys(spec,
            ['NETCLAW_GENIE_CONTROL_FILE','GEMINI_API_KEY','PYATS_TESTBED_PATH'], servers)
        self.assertEqual(keys, ['NETCLAW_GENIE_CONTROL_FILE'])
        policy = profiles.spec_tool_policy(spec)
        self.assertEqual({x for x in policy['allow'] if x.startswith('genie-worlds-mcp__')},
                         {'genie-worlds-mcp__genie_world_'+x for x in ('prepare','start','status','event','stop','evidence')})
        self.assertFalse(policy['elevated']['enabled'])
        self.assertTrue(policy['fs']['workspaceOnly'])

    def test_dependency_effects_remain_reviewable(self):
        EffectAudit(ROOT).verify()
        catalog = json.loads((ROOT/'config/components/catalog.json').read_text())
        c = next(x for x in catalog['components'] if x['id']=='genie-worlds')
        self.assertNotIn('service', c['installer']['effects'])
        self.assertFalse(any(x['classification']=='secret' for x in c['settings']))


if __name__ == '__main__': unittest.main()
