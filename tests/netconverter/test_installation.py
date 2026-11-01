"""Selected-installation settings and existing setup engine contracts."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/lib'));sys.path.insert(0,str(ROOT/'tests'))
from setup_generated import generated
from setup_plan import PlanValidator, contains_literal
from setup_deploy import EffectAudit
from test_setup_plan import sample_plan


def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


class InstallationTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.home=self.root/'selected';self.home.mkdir(mode=0o700)
        self.env=self.home/'.env';self.env.write_text('# preserve\nOTHER_KEY=private-canary\n');self.env.chmod(0o600)
        self.helper=module('nc_settings',Path('scripts/configure-netconverter.py'))

    def test_mode_change_preserves_credentials_and_other_installations(self):
        other=self.root/'other.env';other.write_text('untouched')
        self.helper.configure(self.env,self.home,'local-terminal','account',str(self.home/'files'),str(self.home/'terminal'),'synthetic-key')
        first=self.helper.dotenv.values(self.env.read_text());binding=first['NETCONVERTER_INSTALLATION_ID']
        self.helper.configure(self.env,self.home,'hosted-readonly','account')
        second=self.helper.dotenv.values(self.env.read_text())
        self.assertEqual(second['NETCONVERTER_API_KEY'],'synthetic-key')
        self.assertEqual(second['NETCONVERTER_INSTALLATION_ID'],binding)
        self.assertEqual(second['NETCONVERTER_WORKSPACE'],str(self.home/'files'))
        self.assertEqual(second['OTHER_KEY'],'private-canary');self.assertEqual(other.read_text(),'untouched')
        self.assertEqual(self.env.stat().st_mode & 0o777,0o600)

    def test_invalid_settings_and_noninteractive_prompt_do_not_write(self):
        original=self.env.read_bytes()
        for mode,workspace in [('arbitrary','/a'),('local-terminal','relative')]:
            with self.assertRaises(ValueError):self.helper.configure(self.env,self.home,mode,'account',workspace,'/terminal')
        with self.assertRaises(ValueError):self.helper.configure(self.env,self.home,'hosted-readonly','nck_live_mistaken-key')
        run=subprocess.run([sys.executable,str(ROOT/'scripts/configure-netconverter.py'),'--env',str(self.env),
                            '--home',str(self.home),'--interactive'],input='',text=True,capture_output=True)
        self.assertNotEqual(run.returncode,0);self.assertEqual(self.env.read_bytes(),original)

    def test_conditional_fields_and_generated_binding_are_per_claw(self):
        validator=PlanValidator(ROOT);plan=sample_plan(str(self.root))
        claw=plan['claws'][0];claw['capabilities'].update(components=['netconverter'],skills=['netconverter'])
        claw['settings'].update(NETCONVERTER_MODE={'kind':'value','value':'local-terminal'},
                               NETCONVERTER_ACCOUNT_REF={'kind':'value','value':'fixture account'},
                               NETCONVERTER_API_KEY={'kind':'secret','key':'NETCONVERTER_API_KEY','owner':claw['id'],'source':'later'})
        report=validator.inspect(plan)
        required={x['key'] for x in report['configurationRequired']}
        self.assertTrue({'NETCONVERTER_API_KEY','NETCONVERTER_WORKSPACE','NETCONVERTER_EXECUTABLE'}<=required)
        values=generated(claw,validator,sys.executable)
        self.assertEqual(values['NETCONVERTER_DATA_DIR'],claw['runtimeHome']+'/netconverter')
        self.assertEqual(values['NETCONVERTER_INSTALLATION_ID'],claw['id'])
        claw['settings']['NETCONVERTER_MODE']['value']='invalid'
        self.assertIn('invalid_netconverter_mode',{e['code'] for e in validator.inspect(plan)['errors']})

    def test_risk_netconverter_member_is_selectable_and_keeps_border_unprivileged(self):
        plan=sample_plan(str(self.root));plan['shape']='risk';plan['verification']['risk']=True
        border=plan['claws'][0];border['role']='border'
        border['capabilities'].update(components=['n2n','protocol'],skills=['n2n-federation'])
        member=copy.deepcopy(border)
        member.update(id='converter',role='member',harnessChoice='inherit',
                      runtimeHome=str(self.root/'converter'),workspace=str(self.root/'converter/workspace'))
        member['service']['name']='netclaw-converter'
        member['endpoints']={key:value+100 for key,value in member['endpoints'].items()}
        member['capabilities'].update(profile='netconverter',components=['n2n','netconverter'],skills=['netconverter'])
        member['settings']={key:{**value,'owner':member['id']} for key,value in member['settings'].items()}
        member['settings'].update(NETCONVERTER_MODE={'kind':'value','value':'hosted-readonly'},
            NETCONVERTER_ACCOUNT_REF={'kind':'value','value':'fixture member'},
            NETCONVERTER_API_KEY={'kind':'secret','key':'NETCONVERTER_API_KEY','owner':member['id'],'source':'prompt'})
        plan['claws'].append(member);validator=PlanValidator(ROOT)
        report=validator.inspect(plan)
        self.assertTrue(report['valid'],report['errors'])
        self.assertTrue(report['applyReady'],report['configurationRequired'])
        profile=validator.members['netconverter']
        self.assertEqual(profile['servers'],['netconverter-mcp'])
        self.assertEqual(profile['harnesses'],['openclaw'])
        self.assertFalse(any(key.startswith('NETCONVERTER_') for key in border['settings']))
        values=generated(member,validator,sys.executable)
        self.assertEqual(values['NETCONVERTER_DATA_DIR'],str(self.root/'converter/netconverter'))
        self.assertEqual(values['NETCONVERTER_INSTALLATION_ID'],'converter')
        border['capabilities']['components'].append('netconverter')
        self.assertIn('border_domain_capability',{e['code'] for e in validator.inspect(plan)['errors']})

    def test_literal_keys_and_generated_override_are_rejected(self):
        for key in ['nck_live_12345678','nck_test_12345678']:self.assertTrue(contains_literal({'note':key}))
        plan=sample_plan(str(self.root));claw=plan['claws'][0]
        claw['capabilities'].update(components=['netconverter'],skills=['netconverter'])
        claw['settings']['NETCONVERTER_DATA_DIR']={'kind':'value','value':'/another-installation'}
        self.assertIn('generated_setting_override',{e['code'] for e in PlanValidator(ROOT).inspect(plan)['errors']})

    def test_only_guard_registered_and_audited_dependency_install(self):
        registration=json.loads((ROOT/'config/openclaw.json').read_text())['mcpServers']
        matching={k:v for k,v in registration.items() if 'netconverter' in k}
        self.assertEqual(set(matching),{'netconverter-mcp'})
        self.assertEqual(matching['netconverter-mcp']['args'],['scripts/component-launch.py','netconverter'])
        EffectAudit(ROOT).verify()
        # Execute the real function with a controlled dependency boundary.
        marker=self.root/'calls'
        script='''source scripts/lib/install-steps.sh
log_step() { :; }; log_info() { :; }
netclaw_component_venv() { NETCLAW_COMPONENT_VENV="$1"; }
netclaw_pip_install() { printf '%s\\n' "$*" > "$FIXTURE_CALLS"; }
_set_env_default() { :; }
component_install_netconverter
'''
        result=subprocess.run(['bash','--noprofile','--norc','-c',script],cwd=ROOT,
            env={**os.environ,'NETCLAW_DIR':str(ROOT),'RUNTIME_HOME':str(self.home),'FIXTURE_CALLS':str(marker)},capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('config/python-components/netconverter.txt',marker.read_text())
        self.assertEqual(self.env.read_text(),'# preserve\nOTHER_KEY=private-canary\n')

    def test_installed_interpreter_passes_real_owned_dependency_observation(self):
        from setup_components import dependency_ready
        source=self.home/'.setup/source'
        for directory in ('scripts','config','mcp-servers/netconverter-mcp'):
            (source/directory).mkdir(parents=True,exist_ok=True)
        (source/'scripts/component-launch.py').write_text('# qualified launcher fixture\n')
        (source/'mcp-servers/netconverter-mcp/server.py').write_text('# source fixture\n')
        (source/'config/openclaw.json').write_bytes((ROOT/'config/openclaw.json').read_bytes())
        bootstrap=self.home/'owned-python';bootstrap.write_text('#!/bin/sh\nexit 0\n');bootstrap.chmod(0o700)
        runtimes=self.home/'python-runtimes';(runtimes/'records').mkdir(parents=True)
        # Preserve the real install function, runtime record and dependency
        # observer. Only the package download boundary is controlled.
        script='''source scripts/lib/install-steps.sh
log_step() { :; }; log_info() { :; }; _set_env_default() { :; }
netclaw_component_venv() { NETCLAW_COMPONENT_VENV="$1"; mkdir -p "$1/bin"; ln -s "$FIXTURE_PYTHON" "$1/bin/python"; }
netclaw_pip_install() { printf '%s\\n' "$NETCLAW_VENV/bin/python" > "$NETCLAW_RUNTIME_ROOT/records/netconverter"; chmod 600 "$NETCLAW_RUNTIME_ROOT/records/netconverter"; }
component_install_netconverter
'''
        env={**os.environ,'NETCLAW_DIR':str(source),'RUNTIME_HOME':str(self.home),
             'NETCLAW_RUNTIME_ROOT':str(runtimes),'FIXTURE_PYTHON':str(bootstrap)}
        result=subprocess.run(['bash','--noprofile','--norc','-c',script],cwd=ROOT,env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        deploy=SimpleNamespace(root=self.home,source=source,validator=PlanValidator(ROOT),claw={'harness':'openclaw'})
        harness=SimpleNamespace(environment=lambda:{'PATH':os.defpath})
        with patch('setup_components.helper',return_value=module('nc_binder',Path('scripts/install-mcp-config.py'))):
            self.assertTrue(dependency_ready('netconverter',deploy,harness))


if __name__=='__main__':unittest.main()
