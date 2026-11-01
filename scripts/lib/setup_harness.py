"""Pinned native runtime acquisition and non-secret configuration adapters."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

from setup_schema import Invalid, canonical, loads
from setup_state import Conflict, guarded_read
from setup_secrets import child_environment, read_owned_environment
from setup_process import run, WriterUncertain
from setup_deploy import helper
from convergence_member_policy import native_tool_policy


class Harness:
    def __init__(self, repository, claw, context, deploy, *, execute=run, tool_directories=()):
        self.repository,self.claw,self.context,self.deploy=Path(repository),claw,context,deploy
        self.home=Path(claw['runtimeHome']);self.execute=execute
        self.tool_directories=tuple(tool_directories)
        policy=loads(guarded_read(self.repository/'config/components/harness-adapters.json'))
        self.policy=policy[claw['harness']]
        if claw['runtimeVersion'] not in self.policy['versions']:
            raise Invalid('harness_version_unqualified')
        if claw['provider']['apiMode'] not in self.policy['apiModes']:
            raise Invalid('harness_api_mode_unsupported')

    def environment(self, credentials=None):
        return child_environment(self.home,self.claw['harness'],credentials,tool_directories=self.tool_directories)

    def command(self):
        if self.claw['harness']=='openclaw':
            return [str(self.home/'.setup/prefix/bin/openclaw')]
        base=self.home/'python-runtimes/hermes-hud-agent'
        return [str(base/'venv/bin/python'),'-m','hermes_cli.main']

    def call(self,effect,args,*,credentials=None,timeout=60,capture=False,cwd=None):
        return self.execute(args,cwd=cwd or self.home,env=self.environment(credentials),timeout=timeout,
            capture=capture,lock_fds=self.context['lockFds'],
            started=lambda identity:self.context['writerStarted'](effect['id'],identity))

    def install(self,effect):
        env=self.environment();uv=shutil.which('uv',path=env['PATH'])
        if not uv:return {'state':'configuration_required'}
        installed=self.call(effect,[uv,'python','install','3.12'],timeout=600)
        if installed['returncode']:return {'state':'failed'}
        found=self.call(effect,[uv,'python','find','--managed-python','3.12'],capture=True)
        python=found['stdout'].decode('utf-8','strict').strip()
        if found['returncode'] or not Path(python).is_absolute() or not Path(python).is_relative_to(self.home/'.setup/python') or not os.access(python,os.X_OK):
            return {'state':'failed'}
        self.deploy.write(effect,self.home/'.setup/python312',python.encode()+b'\n',kind='runtime-record')
        if self.claw['harness']=='openclaw':
            env=self.environment();npm=shutil.which('npm',path=env['PATH'])
            if not npm:return {'state':'configuration_required'}
            node=shutil.which('node',path=env['PATH'])
            if not node:return {'state':'configuration_required'}
            probe=self.call(effect,[node,'--version'],capture=True)
            policy=self.call(effect,[sys.executable,str(self.repository/'scripts/runtime-policy.py'),
                '--runtime','openclaw','--node',probe['stdout'].decode().strip()])
            if policy['returncode']:return {'state':'configuration_required'}
            result=self.call(effect,[npm,'install','--global','--prefix',str(self.home/'.setup/prefix'),
                '--no-audit','--no-fund','openclaw@'+self.claw['runtimeVersion']],timeout=1200)
            if result['returncode']:return {'state':'failed'}
            version=self.call(effect,self.command()+['--version'],capture=True)
            if version['returncode'] or self.claw['runtimeVersion'] not in version['stdout'].decode('utf-8','replace').split():
                return {'state':'failed'}
        else:
            result=self.call(effect,[sys.executable,str(self.repository/'scripts/install-hermes-hud-agent.py'),
                                     '--home',str(self.home)],timeout=1800)
            if result['returncode']:return {'state':'failed'}
            base=self.home/'python-runtimes/hermes-hud-agent'
            manifest=json.loads(guarded_read(self.repository/'config/hermes-hud-compatibility.json'))
            for relative,expected in manifest['files'].items():
                if hashlib.sha256(guarded_read(base/'source'/relative,8*1024*1024)).hexdigest()!=expected:
                    return {'state':'failed'}
            if not self.install_python_component(effect,'hermes-hud'):return {'state':'failed'}
        return {'state':'verified' if self.install_hud(effect) else 'failed'}

    def install_hud(self,effect):
        env=self.environment();node=shutil.which('node',path=env['PATH']);npm=shutil.which('npm',path=env['PATH'])
        if not node or not npm:return False
        if self.call(effect,[node,str(self.deploy.source/'scripts/hud-node-version.mjs')])['returncode']:return False
        if self.call(effect,[npm,'ci','--no-audit','--no-fund'],cwd=self.deploy.source/'ui/netclaw-visual',timeout=1200)['returncode']:return False
        return self.observe_hud(effect)

    def observe_hud(self,effect):
        """Recheck the installed dependency tree without install/lifecycle hooks."""
        env=self.environment();node=shutil.which('node',path=env['PATH']);npm=shutil.which('npm',path=env['PATH'])
        if not node or not npm:return False
        base=self.deploy.source/'ui/netclaw-visual'
        package=loads(guarded_read(base/'package.json'))
        lock=loads(guarded_read(base/'package-lock.json',8*1024*1024))
        # Require every direct runtime dependency at the exact locked version.
        # The private reader rejects symlinked package/ancestor directories.
        dependencies=package.get('dependencies',{})
        if not dependencies or lock.get('packages',{}).get('',{}).get('dependencies')!=dependencies:return False
        for name in dependencies:
            relative='node_modules/'+name
            installed=loads(guarded_read(base/relative/'package.json'))
            if installed.get('version')!=lock['packages'].get(relative,{}).get('version') or not installed.get('version'):return False
        if self.call(effect,[node,str(self.deploy.source/'scripts/hud-node-version.mjs')])['returncode']:return False
        # npm's offline read-only tree check also catches missing/invalid
        # transitive dependencies. Raw package paths/diagnostics are discarded.
        if self.call(effect,[npm,'ls','--omit=dev','--all','--offline'],cwd=base,timeout=45)['returncode']:return False
        check='await Promise.all(["express","yaml","js-yaml","ws","ssh2","dotenv"].map(name=>import(name)));'
        return self.call(effect,[node,'--input-type=module','--eval',check],cwd=base,timeout=20)['returncode']==0

    def install_pyats(self,effect):
        policy=helper(self.repository,'setup-pyats-runtime.py')
        env=self.environment();uv=shutil.which('uv',path=env['PATH']);git=shutil.which('git',path=env['PATH'])
        if not uv or not git:return False
        base=self.home/'pyats-venv';source=base/'upstream'
        # Empty, separately owned home only. No legacy migration, promotion
        # symlink, inherited testbed or sibling environment is involved.
        if base.exists():return self.observe_pyats(effect)
        python=guarded_read(self.home/'.setup/python312',8192).decode().strip()
        commands=[[uv,'venv',str(base),'--python',python],
            [git,'clone','--no-checkout',policy.REPOSITORY,str(source)],
            [git,'-C',str(source),'checkout','--detach',policy.REVISION],
            [uv,'pip','install','--python',str(base/'bin/python'),'-r',str(source/'requirements.txt'),'mcp==2.3.0']]
        for args in commands:
            if self.call(effect,args,timeout=1200)['returncode']:return False
        if not self.observe_pyats(effect):return False
        self.deploy.write(effect,self.home/'python-runtimes/records/pyats',(str(base/'bin/python')+'\n').encode(),kind='runtime-record')
        return True

    def observe_pyats(self,effect):
        policy=helper(self.repository,'setup-pyats-runtime.py')
        base=self.home/'pyats-venv'
        if any(not (base/'upstream'/name).is_file() for name in policy.SOURCE_FILES):return False
        git=shutil.which('git',path=self.environment()['PATH'])
        if not git:return False
        revision=self.call(effect,[git,'-C',str(base/'upstream'),'rev-parse','HEAD'],capture=True,timeout=15)
        if revision['returncode'] or revision['stdout'].decode().strip()!=policy.REVISION:return False
        changed=self.call(effect,[git,'-C',str(base/'upstream'),'status','--porcelain','--untracked-files=no'],capture=True,timeout=15)
        if changed['returncode'] or changed['stdout'].strip():return False
        result=self.call(effect,[str(base/'bin/python'),'-c','import pyats,genie,unicon; from mcp.client.client import Client'],timeout=20)
        return result['returncode']==0

    def install_python_component(self,effect,component):
        if component not in ('n2n','hermes-hud','claw-certs'):raise Invalid('component_adapter_invalid')
        env=self.environment();python=guarded_read(self.home/'.setup/python312',8192).decode().strip()
        if not Path(python).is_relative_to(self.home):raise Invalid('component_runtime_outside_home')
        env['NETCLAW_PY']=python
        result=self.execute(['/bin/bash',str(self.deploy.source/'scripts/lib/plan-python.sh'),component,str(self.deploy.source),str(self.home)],
            cwd=self.home,env=env,timeout=1200,lock_fds=self.context['lockFds'],
            started=lambda identity:self.context['writerStarted'](effect['id'],identity))
        if result['returncode']:return False
        record=self.home/'python-runtimes/records'/component
        try:
            executable=guarded_read(record,8192).decode().strip()
            if not Path(executable).is_relative_to(self.home) or not os.access(executable,os.X_OK):return False
            self.context['artifactIntent'](effect['id'],[self.deploy.artifact(record,guarded_read(record),'runtime-record')])
            return self.observe_python_component(effect,component)
        except OSError:return False

    def observe_python_component(self,effect,component):
        if component not in ('n2n','hermes-hud','claw-certs','gait'):raise Invalid('component_adapter_invalid')
        record=self.home/'python-runtimes/records'/component
        executable=Path(guarded_read(record,8192,private=True).decode().strip())
        if not executable.is_absolute() or not executable.is_relative_to(self.home) or not executable.resolve().is_relative_to(self.home) or not os.access(executable,os.X_OK):return False
        check='import sys,importlib.metadata as m; assert sys.version_info[:2]==(3,12); '
        if component!='claw-certs':check+='import mcp,fastmcp; assert m.version("mcp")=="2.3.0" and m.version("fastmcp")=="4.0.11"; '
        if component in ('n2n','hermes-hud'):check+='import httpx; '
        if component in ('n2n','claw-certs'):check+='from cryptography import x509; assert m.version("cryptography")=="46.0.5"; '
        if component=='gait':
            from setup_components import gait_runtime
            if executable!=gait_runtime(self.home):return False
            check+='import gait; '
        return self.call(effect,[str(executable),'-c',check],timeout=20)['returncode']==0

    def observe_runtime(self,effect):
        try:
            python=guarded_read(self.home/'.setup/python312',8192).decode().strip()
            if not Path(python).is_relative_to(self.home) or not Path(python).resolve().is_relative_to(self.home) or not os.access(python,os.X_OK):return False
            if self.call(effect,[python,'-c','import sys; assert sys.version_info[:2]==(3,12)'],timeout=15)['returncode']:return False
            if self.claw['harness']=='openclaw':
                result=self.call(effect,self.command()+['--version'],capture=True,timeout=15)
                if result['returncode'] or self.claw['runtimeVersion'] not in result['stdout'].decode('utf-8','strict').split():return False
            else:
                base=self.home/'python-runtimes/hermes-hud-agent'
                manifest=loads(guarded_read(self.repository/'config/hermes-hud-compatibility.json'))
                executable=base/'venv/bin/python'
                if not executable.resolve().is_relative_to(self.home) or not os.access(executable,os.X_OK) or not all(
                    hashlib.sha256(guarded_read(base/'source'/name,8*1024*1024)).hexdigest()==digest for name,digest in manifest['files'].items()):return False
                if not self.observe_python_component(effect,'hermes-hud'):return False
                check='import sys,hermes_yaml; assert sys.version_info[:2]==(3,14); import hermes_cli.main'
                if self.call(effect,[str(executable),'-c',check],timeout=30)['returncode']:return False
            return self.observe_hud(effect)
        except WriterUncertain:raise
        except Exception:return False

    def base_config(self):
        claw=self.claw;provider=claw['provider'];mode=provider['apiMode'];model=provider['model']
        if claw['harness']=='hermes':
            provider_id={'lm-studio':'lmstudio','openai':'openai-api','ollama':'custom:netclaw-selected','custom':'custom:netclaw-selected'}.get(provider['id'],provider['id'])
            transport={'openai':'chat_completions','openai-responses':'codex_responses','anthropic':'anthropic_messages'}[mode]
            config={'model':{'provider':provider_id,'default':model,'api_mode':transport},'mcp_servers':{},
                    'gateway':{'multiplex_profiles':False}}
            if provider['endpoint']:config['model']['base_url']=provider['endpoint']
            if provider_id=='custom:netclaw-selected':
                entry={'base_url':provider['endpoint'],'api_mode':transport,'default_model':model}
                if provider['credentialKeys']:entry['key_env']=provider['credentialKeys'][0]
                config['providers']={'netclaw-selected':entry}
            return config
        native_provider={'lm-studio':'lmstudio'}.get(provider['id'],provider['id'])
        primary=native_provider+'/'+model
        config={'gateway':{'mode':'local','bind':'loopback','port':claw['endpoints']['gatewayPort'],
            'http':{'endpoints':{'chatCompletions':{'enabled':True}}},
            'auth':{'mode':'token','token':{'source':'env','provider':'default','id':'OPENCLAW_GATEWAY_TOKEN'}}},
            'agents':{'defaults':{'workspace':claw['workspace'],'model':{'primary':primary},'models':{primary:{}}}},
            'models':{'providers':{}},'mcp':{'servers':{}},'channels':{}}
        if claw.get('role') == 'member' and claw.get('capabilities', {}).get('profile') == 'convergence':
            config['tools'] = native_tool_policy()
        config['models']['providers'][native_provider]={'api':self.policy['apiModes'][mode]}
        # Comms effects configure channels after provider/MCP registration.
        if provider['endpoint']:
            config['models']['providers'][native_provider].update(baseUrl=provider['endpoint'],models=[{'id':model,'name':model}])
        if provider['credentialKeys']:
            config['models']['providers'].setdefault(native_provider,{})['apiKey']={
                'source':'env','provider':'default','id':provider['credentialKeys'][0]}
        return config

    def onboard(self,effect):
        if any(c['id'] in self.policy.get('unavailableChannels',{}) for c in self.claw['channels']):
            return {'state':'configuration_required'}
        target=self.home/('config.yaml' if self.claw['harness']=='hermes' else 'openclaw.json')
        config=self.base_config()
        self.deploy.write(effect,target,canonical(config)+b'\n',kind='configuration')
        # Re-read fields; an exit-0 guidance message cannot satisfy onboarding.
        if loads(guarded_read(target))!=config:return {'state':'failed'}
        if self.claw['harness']=='openclaw':
            env_effect=next((e for e in self.context['journal']['effects'] if e['owner']==self.claw['id'] and e['phase']=='credentials'),None)
            artifact=next((a for a in (env_effect or {}).get('artifacts',[]) if a['path']==str(self.home/'.env')),None)
            if not artifact:return {'state':'configuration_required'}
            values=read_owned_environment(self.home/'.env',artifact['sha256'])
            checked=self.call(effect,self.command()+['config','validate'],credentials=values,timeout=30)
            if checked['returncode']:return {'state':'failed'}
        else:
            # Hermes config is validated with its installed safe YAML loader,
            # never by calling its guidance-only noninteractive setup command.
            base=self.home/'python-runtimes/hermes-hud-agent'
            check='import os,pathlib,hermes_yaml; p=pathlib.Path(os.environ["HERMES_HOME"])/"config.yaml"; c=hermes_yaml.safe_load(p.read_text()); assert isinstance(c.get("model"),dict) and c["model"].get("provider") and c["model"].get("default")'
            result=self.call(effect,[str(base/'venv/bin/python'),'-c',check],timeout=30)
            if result['returncode']:return {'state':'failed'}
        # Configuration/authentication/transport evidence belongs to each
        # selected Comms effect; a configured-platform list is not a connection.
        return {'state':'verified'}
