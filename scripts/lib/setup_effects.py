"""Fixed adapters for the engine. No plan-supplied executable or shell input."""
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import sys

from setup_deploy import Deployment, EffectAudit
from setup_harness import Harness
from setup_plan import PlanValidator
from setup_process import run
from mcp_environment import load_mcp_template
from setup_schema import canonical, loads
from setup_secrets import child_environment, write_environment, read_owned_environment
from setup_state import Conflict, directory, guarded_read, revision, artifact_revision


class EffectRunner:
    def __init__(self, repository, *, secret_input=None, native_step=None, tool_directories=(),session=None):
        self.repository=Path(repository)
        self.validator=PlanValidator(repository)
        self.audit=EffectAudit(repository);self.audit.verify()
        self.secret_input=secret_input
        self.native_step=native_step
        self.session=session
        # Chosen by the trusted host preflight, never the plan or MCP caller.
        self.tool_directories=tuple(tool_directories)

    def __call__(self,effect,context):
        context['toolDirectories']=self.tool_directories
        claw=next(c for c in context['plan']['claws'] if c['id']==effect['owner'])
        deploy=Deployment(self.repository,claw,context)
        harness=Harness(self.repository,claw,context,deploy,tool_directories=self.tool_directories)
        phase=effect['phase']
        if phase=='home':return deploy.home(effect)
        if phase=='runtime':
            effect['runtimeStage']='source';context['save']()
            deploy.copy_source(effect)
            from setup_observation import source_identity
            actual=source_identity(self.repository)
            if any(actual[key]!=context['plan']['source'][key] for key in actual):
                raise Conflict('source_changed_during_copy')
            # A crash after this checkpoint may have started package managers;
            # matching source files alone can never authorize replaying them.
            effect['runtimeStage']='dependencies';context['save']()
            return harness.install(effect)
        if phase=='credentials':return self.credentials(effect,context,deploy)
        if phase=='onboard':return harness.onboard(effect)
        if phase=='components':return self.component(effect,context,deploy,harness)
        if phase=='skills':return deploy.skills(effect)
        if phase=='registration':return deploy.registration(effect)
        if phase in ('inventory','identity'):return deploy.inputs(effect)
        if phase=='comms':
            from setup_comms import configure_channel
            return configure_channel(effect,context,deploy,harness,session=self.session)
        if phase=='comms-binding':
            from setup_comms import configure_zoom_binding
            return configure_zoom_binding(effect,context,deploy)
        if phase=='risk':
            from setup_risk import configure_risk
            return configure_risk(effect,context,deploy,harness)
        if phase=='services':
            from setup_risk import install_services
            return install_services(effect,context,deploy,harness)
        if phase=='verification':
            from setup_verify import verify_installation,Probes
            from setup_live import LiveVerification
            probes=Probes(effect,context,deploy,harness)
            return verify_installation(effect,context,deploy,harness,probes=probes,live=LiveVerification(self.session,probes,context))
        raise Conflict('unknown_effect')

    def credentials(self,effect,context,deploy):
        claw=deploy.claw;home=deploy.root;values={};deferred=False;before=None
        owned=[a for e in context['journal']['effects'] for a in e.get('artifacts',[]) if a['path']==str(home/'.env')]
        if owned:
            before=owned[-1]['sha256'];values=read_owned_environment(home/'.env',before)
        for key,setting in claw['settings'].items():
            if setting['kind']=='value':
                value=setting['value'];values[key]=str(value).lower() if isinstance(value,bool) else str(value)
            elif setting['source']=='later':deferred=True
            elif setting['source']=='existing':
                # Initial installs cannot adopt secrets from an unowned home.
                artifacts=[a for e in context['journal']['effects'] for a in e.get('artifacts',[]) if a['path']==str(home/'.env')]
                if not artifacts:raise Conflict('existing_secret_not_owned')
                value=read_owned_environment(home/'.env',artifacts[-1]['sha256']).get(key)
                if value is None:deferred=True
                else:values[key]=value
            else:
                value=values.get(key) or (self.secret_input(claw['id'],key,context['runId']) if self.secret_input else None)
                if value is None:deferred=True
                else:values[key]=value
        values.update(NETCLAW_RUNTIME=claw['harness'],NETCLAW_RUNTIME_ROOT=str(home/'python-runtimes'),
            NETCLAW_RUNTIME_ENV=str(home/'.env'),NETCLAW_DIR=str(deploy.source),
            HUD_API_KEY=values.get('HUD_API_KEY') or secrets.token_hex(32),HUD_HOST='127.0.0.1',HUD_PORT=str(claw['endpoints']['hudPort']),
            HUD_UI_PORT=str(claw['endpoints']['hudUiPort']),N2N_PORT=str(claw['endpoints']['federationPort']),
            MCP_CALL=str(deploy.source/'scripts/mcp-call.py'))
        installation=loads(guarded_read(home/'netclaw-hud/installation.json'))['installationId']
        values.update(NETCLAW_INSTALLATION_ID=installation,NETCLAW_HUD_INSTALLATION_ID=installation)
        if 'twilio' in claw['capabilities']['components']:
            values['NETCLAW_COMMS_MANAGED']='1'
            if claw['harness']=='openclaw':values['OPENCLAW_GATEWAY_URL']='http://127.0.0.1:'+str(claw['endpoints']['gatewayPort'])
        values.update(HF_HOME=str(home/'.setup/cache/huggingface'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        from setup_generated import generated
        python=guarded_read(home/'.setup/python312',8192).decode().strip()
        if not Path(python).is_relative_to(home):raise Conflict('component_runtime_outside_home')
        values.update(generated(claw,self.validator,python))
        if claw['harness']=='hermes':
            values.update(HERMES_HOME=str(home),NETCLAW_HERMES_HUD_PORT=str(claw['endpoints']['companionPort']),
                NETCLAW_HERMES_HUD_API_KEY=values.get('NETCLAW_HERMES_HUD_API_KEY') or secrets.token_hex(32))
        else:
            values.update(OPENCLAW_STATE_DIR=str(home),OPENCLAW_CONFIG_PATH=str(home/'openclaw.json'),
                          OPENCLAW_GATEWAY_TOKEN=values.get('OPENCLAW_GATEWAY_TOKEN') or secrets.token_hex(32))
        if 'pyats' in claw['capabilities']['components']:
            values.update(PYATS_VENV=str(home/'pyats-venv'),PYATS_MCP_SCRIPT=str(deploy.source/'scripts/pyats-stdio.py'),
                PYATS_UPSTREAM_SCRIPT=str(home/'pyats-venv/upstream/pyats_mcp_server.py'))
        # No source/neighbor env reads. Serialized values go directly to the
        # guarded writer, while the journal gets only a private content hash.
        from setup_secrets import _dotenv
        data=''.join(k+'='+_dotenv.quote(values[k])+'\n' for k in sorted(values)).encode()
        deploy.write(effect,home/'.env',data,kind='credentials',expected=before)
        values.clear()
        required=self.validator.inspect(context['plan'])['configurationRequired']
        return {'state':'configuration_required' if deferred or any(v['owner']==claw['id'] for v in required) else 'verified'}

    def component(self,effect,context,deploy,harness):
        self.audit.verify()
        item=self.audit.components[effect['component']]
        if effect['component'] in ('twilio','zoom-rtms'):
            from setup_comms_tools import install
            return install(effect['component'],effect,context,deploy,harness)
        if effect['component']=='pyats':
            return {'state':'verified' if harness.install_pyats(effect) else 'failed'}
        if effect['component'] in ('n2n','hermes-hud'):
            return {'state':'verified' if harness.install_python_component(effect,effect['component']) else 'failed'}
        if effect['component']=='claw-certs':
            from setup_certificates import install
            return install(effect,context,deploy,harness)
        if item['adapter']=='scoped-special':
            from setup_special import install_special
            return install_special(effect,context,deploy,harness)
        if item['adapter']=='native':
            if self.native_step:
                self.native_step(effect,context,item)
            # A native terminal closing is not proof. Its dedicated observe
            # adapter must establish the postcondition before advancing.
            return {'state':'configuration_required'}
        env=harness.environment()
        python=guarded_read(deploy.root/'.setup/python312',8192).decode().strip()
        if not Path(python).is_relative_to(deploy.root):raise Conflict('component_runtime_outside_home')
        env.update(NETCLAW_PY=python,NETCLAW_RUNTIME_ROOT=str(deploy.root/'python-runtimes'),
                   NETCLAW_INSTALL_COMPONENT=effect['component'],GAIT_VENV=str(deploy.root/'gait-venv'))
        result=run(['/bin/bash',str(deploy.source/'scripts/lib/plan-steps.sh'),effect['component'],
                    str(deploy.source),str(deploy.root)],cwd=deploy.source,env=env,timeout=1200,
                   lock_fds=context['lockFds'],started=lambda identity:context['writerStarted'](effect['id'],identity))
        deploy.reconcile_source(effect)
        if result['returncode']:return {'state':'failed'}
        if effect['component']=='gait':
            from setup_components import gait_runtime
            record=deploy.root/'python-runtimes/records/gait'
            deploy.write(effect,record,str(gait_runtime(deploy.root)).encode()+b'\n',kind='runtime-record')
            if not harness.observe_python_component(effect,'gait'):return {'state':'unverified'}
        descriptor=self.validator.components[effect['component']]
        template=load_mcp_template(guarded_read(self.repository/'config/openclaw.json',8*1024*1024))
        record=deploy.root/'python-runtimes/records'/effect['component']
        if record.exists():
            executable=guarded_read(record,8192).decode().strip()
            if not Path(executable).is_relative_to(deploy.root) or not os.access(executable,os.X_OK):
                return {'state':'failed'}
            if effect['component']!='gait':
                context['artifactIntent'](effect['id'],[deploy.artifact(record,guarded_read(record),'runtime-record')])
        from setup_components import dependency_ready
        return {'state':'verified' if dependency_ready(effect['component'],deploy,harness,effect=effect) else 'unverified'}

    def observe(self,effect,context):
        if effect['state']=='pending':return 'not_applied'
        claw=next(c for c in context['plan']['claws'] if c['id']==effect['owner'])
        deploy=Deployment(self.repository,claw,context)
        if effect['phase'] in ('home','skills','identity'):
            return deploy.observe_files(effect)
        if effect['phase']=='inventory' and claw.get('testbed',{}).get('mode')=='dynamic':
            return deploy.observe_files(effect)
        if effect['phase']=='runtime' and effect.get('runtimeStage')=='source' and effect['state']!='verified':
            return deploy.observe_source_copy(effect)
        if effect['phase']=='components' and effect['component']=='claw-certs':
            from setup_certificates import observe
            return observe(effect,context,deploy,Harness(self.repository,claw,context,deploy,tool_directories=self.tool_directories))
        # Later owned revisions supersede earlier versions of a file within the
        # same run. Operator edits never inherit this ownership.
        latest={a['path']:a for e in context['journal']['effects'] for a in e.get('artifacts',[])}
        if effect['phase']=='comms-binding':
            from setup_comms import observe_zoom_binding
            return observe_zoom_binding(effect,context,deploy)
        if effect['phase']=='comms':
            from setup_comms_services import observe_channel_effect
            return observe_channel_effect(effect,context,deploy,Harness(self.repository,claw,context,deploy,tool_directories=self.tool_directories))
        artifacts=effect.get('artifacts',[])
        for artifact in artifacts:
            expected=latest[artifact['path']]['sha256']
            if artifact_revision(artifact)!=expected:return 'conflict'
        harness=Harness(self.repository,claw,context,deploy,tool_directories=self.tool_directories)
        if effect['phase']=='runtime':
            return 'completed' if harness.observe_runtime(effect) else 'unknown'
        if effect['phase']=='services':
            from setup_risk import observe_services
            return 'completed' if observe_services(effect,context,deploy,harness) else 'unknown'
        if effect['phase']=='risk':
            from setup_risk import observe_risk
            return 'completed' if observe_risk(effect,context,deploy,harness) else 'unknown'
        if effect['phase']=='credentials':
            artifact=latest.get(str(deploy.root/'.env'))
            if not artifact:return 'unknown'
            values=read_owned_environment(deploy.root/'.env',artifact['sha256'])
            if any(s['kind']=='secret' and s['source']=='prompt' and not values.get(k) for k,s in claw['settings'].items()):
                return 'retry_owned'
            return 'completed' if effect['state']=='verified' else 'configuration_required'
        if effect['phase']=='components' and effect['state']=='verified':
            from setup_components import dependency_ready
            component=effect['component']
            if component=='pyats' and not harness.observe_pyats(effect):return 'conflict'
            if component in ('n2n','hermes-hud','gait') and not harness.observe_python_component(effect,component):return 'conflict'
            return 'completed' if dependency_ready(component,deploy,harness,effect=effect) else 'conflict'
        if effect['phase']=='components' and effect['state']=='failed':
            # A settled nonzero dependency process in the audited owned build
            # area is retryable after exact artifact and writer rechecks. An
            # interrupted/unknown process never receives this permission.
            return 'retry_owned' if self.audit.components[effect['component']]['adapter'] in ('isolated-shell','isolated-python') else 'configuration_required'
        if effect['state']=='configuration_required':return 'configuration_required'
        if effect['state']=='verified':
            return 'completed'
        # Inventory conversion and registration span several outputs. A prefix
        # of matching artifacts does not prove that the entire phase finished.
        return 'unknown'
