"""Deployment of selected, separately owned files and component registrations."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import uuid

from setup_observation import git
from setup_plan import PlanValidator
from setup_schema import canonical, loads
from setup_state import Conflict, directory, guarded_read, guarded_write, revision


def helper(repository, name):
    spec = importlib.util.spec_from_file_location(name.replace('-','_'), Path(repository)/'scripts'/name)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class EffectAudit:
    def __init__(self, repository):
        self.repository = Path(repository)
        self.data = loads(guarded_read(self.repository/'config/components/effects.json'))
        self.components = {c['id']: c for c in self.data['components']}

    def verify(self):
        source = guarded_read(self.repository/'scripts/lib/install-steps.sh')
        if hashlib.sha256(source).hexdigest() != self.data['sourceSha256']:
            raise Conflict('component_effects_changed')
        for entry in self.components.values():
            match = re.search(r'^'+re.escape(entry['function'])+r'\(\) \{.*?^}', source.decode(), re.M|re.S)
            if not match or hashlib.sha256(match[0].encode()).hexdigest() != entry['sha256']:
                raise Conflict('component_effects_changed')


class Deployment:
    HOME_DIRECTORIES=('.setup/os-home','.setup/tmp','.setup/cache','.setup/data','.setup/state','workspace')
    def __init__(self, repository, claw, context):
        self.repository, self.claw, self.context = Path(repository), claw, context
        self.root = Path(claw['runtimeHome'])
        self.source = self.root/'.setup/source'
        self.validator = PlanValidator(repository)

    def artifact(self, path, data, kind='file', *, before=None):
        return {'owner': self.claw['id'], 'path': str(path), 'class': kind,
                'sha256': hashlib.sha256(data).hexdigest(), 'existedBefore': before is not None,
                'before': before, 'referencedBy': [self.claw['id']]}

    def write(self, effect, path, data, *, kind='file', expected=None):
        path = Path(path)
        if not path.is_relative_to(self.root):
            raise Conflict('write_outside_installation')
        artifact = self.artifact(path, data, kind, before=expected)
        prior=next((a for a in reversed(effect.get('artifacts',[])) if a['path']==str(path)),None)
        if prior and prior.get('owner')==self.claw['id'] and prior.get('class')==kind and prior.get('referencedBy')==[self.claw['id']] and prior.get('sha256')==artifact['sha256']:
            # A resumed deterministic file phase may encounter a write already
            # settled before the engine's final checkpoint. Only this effect's
            # exact journaled private bytes qualify; an identical unowned file
            # remains a conflict under the normal no-replace writer.
            try:current=hashlib.sha256(guarded_read(path,64*1024*1024,private=True)).hexdigest()
            except FileNotFoundError:current=None
            if current==artifact['sha256']:return prior
            if current!=prior.get('before'):raise Conflict('artifact_recovery_changed')
            expected=current
        # Do not journal a new ownership claim for a target already occupied
        # before this attempt. The atomic writer also rechecks for races.
        if revision(path)!=expected:raise Conflict('revision_conflict')
        self.context['artifactIntent'](effect['id'], [artifact])
        guarded_write(path, data, expected=expected)
        return artifact

    def home(self, effect):
        with directory(self.root, create=True, private=True):
            pass
        outputs=self.file_outputs('home')
        self.write(effect,*outputs[0][:2],kind=outputs[0][2])
        for relative in self.HOME_DIRECTORIES:
            with directory(self.root/relative, create=True, private=True):
                pass
        self.write(effect,*outputs[1][:2],kind=outputs[1][2])
        return {'state':'verified'}

    def copy_source(self, effect):
        """Copy reviewed, nonignored source; never borrow a mutable checkout."""
        outputs=self.source_outputs()
        prior={a['path']:a for a in effect.get('artifacts',[]) if a.get('class')=='source'}
        artifacts=[]
        for target,data,_ in outputs:
            artifact=self.artifact(target,data,'source');old=prior.get(str(target))
            if old is not None and old!=artifact:raise Conflict('source_recovery_changed')
            actual=revision(target)
            if actual is not None and (old is None or actual!=artifact['sha256']):raise Conflict('source_recovery_changed')
            if old is None:artifacts.append(artifact)
        if set(prior)-{str(target) for target,_,_ in outputs}:raise Conflict('source_recovery_changed')
        if artifacts:self.context['artifactIntent'](effect['id'],artifacts)
        for target,data,executable in outputs:
            try:current=guarded_read(target,64*1024*1024,private=True)
            except FileNotFoundError:current=None
            if current is None:guarded_write(target,data,expected=None)
            elif current!=data:raise Conflict('source_recovery_changed')
            if executable:
                with directory(target.parent) as parent:
                    fd=os.open(target.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=parent)
                    try:os.fchmod(fd,0o700);os.fsync(fd)
                    finally:os.close(fd)

    def observe_source_copy(self,effect):
        """Only a durable pre-dependency stage permits deterministic repair."""
        if effect.get('runtimeStage')!='source':return 'unknown'
        try:
            prior={a['path']:a for a in effect.get('artifacts',[]) if a.get('class')=='source'}
            expected=set()
            for target,data,_ in self.source_outputs():
                expected.add(str(target));artifact=self.artifact(target,data,'source');old=prior.get(str(target))
                if old is not None and old!=artifact:return 'conflict'
                actual=revision(target)
                if actual is not None and (old is None or actual!=artifact['sha256']):return 'conflict'
                if actual is not None:guarded_read(target,64*1024*1024,private=True)
            if set(prior)-expected:return 'conflict'
            if any(a.get('class')!='source' for a in effect.get('artifacts',[])):return 'conflict'
            return 'retry_owned'
        except (OSError,ValueError,Conflict):return 'conflict'

    def source_outputs(self):
        """Closed reviewed source set, before dependency acquisition begins."""
        names = sorted(set(git(self.repository,'ls-files','-z','--cached','--others','--exclude-standard').split(b'\0'))-{b''})
        pending = []
        for raw in names:
            relative = Path(raw.decode('utf-8','strict'))
            # The installed HUD imports these public snapshots at module load.
            # Keep them in the reviewed source set alongside the skill contract.
            runtime_documents = ('docs/DYNAMIC-TESTBEDS.md',
                                 'docs/reference/interfaces.json',
                                 'docs/reference/documents.json')
            if relative.parts[0] not in ('scripts','config','mcp-servers','workspace','ui','src','bin') and len(relative.parts) != 1 and relative.as_posix() not in ('tests/contract-suites.json', *runtime_documents) and not relative.as_posix().startswith('installer/native-comms/'):
                continue
            if any(p in ('.env','.git','node_modules','.venv','__pycache__') or p.startswith('.env.') for p in relative.parts):
                continue
            source, target = self.repository/relative, self.source/relative
            try:
                with directory(source.parent) as parent:
                    info = os.stat(source.name,dir_fd=parent,follow_symlinks=False)
                    if stat.S_ISLNK(info.st_mode):
                        # The repository's HUD fixture symlink is development
                        # data. Runtime acquisition never follows/copies aliases.
                        if relative.as_posix() == 'ui/netclaw-visual/public/fixtures':
                            continue
                        raise Conflict('source_link_refused')
                data = guarded_read(source,64*1024*1024)
            except FileNotFoundError:
                continue
            pending.append((target,data,info.st_mode&0o111))
        return pending

    def skills(self, effect):
        for target,data,kind in self.file_outputs('skills'):
            self.write(effect,target,data,kind=kind)
        return {'state':'verified'}

    def file_outputs(self,phase):
        """Expected bytes for the closed, deterministic file-only phases."""
        if phase=='inventory' and self.claw.get('testbed',{}).get('mode')=='dynamic':
            from pyats_testbeds import policy
            return [(self.root/'testbeds/policy.json',canonical({'schema':1,**policy(self.claw['testbed'])}),'inventory-policy')]
        if phase=='home':
            marker={'schema':1,'runId':self.context['runId'],'installationId':self.claw['id'],'planHash':self.context['planHash']}
            installation=str(uuid.uuid5(uuid.NAMESPACE_URL,'netclaw:'+self.context['runId']+':'+self.claw['id']))
            return [(self.root/'.netclaw-setup-owner.json',canonical(marker),'file'),
                    (self.root/'netclaw-hud/installation.json',canonical({'schemaVersion':1,'installationId':installation}),'file')]
        if phase=='identity':
            names={'soul':'SOUL.md','user':'USER.md','identity':'IDENTITY.md'};outputs=[];identity_files={}
            for item in self.context['plan']['identity']:
                if item['owner']!=self.claw['id']:continue
                data=guarded_read(item['path'],64*1024)
                if hashlib.sha256(data).hexdigest()!=item['sha256']:raise Conflict('input_changed')
                if item['kind'] not in names:raise Conflict('input_kind_invalid')
                name=names[item['kind']];outputs.append((Path(self.claw['workspace'])/name,data,'identity'))
                identity_files[name]=item['sha256']
            if self.claw['harness']=='hermes':outputs.append((self.root/'.setup/identity.json',canonical({'schema':1,'files':identity_files}),'identity'))
            return outputs
        if phase!='skills':raise Conflict('file_phase_unsupported')
        outputs=[];size=0
        base = self.root/'skills' if self.claw['harness']=='hermes' else Path(self.claw['workspace'])/'skills'
        for name in self.claw['capabilities']['skills']:
            descriptor = self.validator.skills[name]
            source = self.repository/'workspace/skills'/name
            # Schema/catalog already rejects path-bearing IDs. Every copied
            # resource gets a write-ahead hash, including scripts and assets.
            for file in sorted(source.rglob('*')):
                if file.is_symlink():
                    raise Conflict('skill_link_refused')
                if file.is_dir():
                    continue
                data = guarded_read(file,64*1024*1024)
                if file.name=='SKILL.md' and hashlib.sha256(data).hexdigest()!=descriptor['sha256']:
                    raise Conflict('skill_changed')
                size+=len(data)
                if size>64*1024*1024 or len(outputs)>=20000:raise Conflict('skill_output_limit')
                outputs.append((base/name/file.relative_to(source),data,'skill'))
        return outputs

    def observe_files(self,effect):
        """Prove the whole selected output set, or a bounded owned repair."""
        expected=self.file_outputs(effect['phase']);pending=False
        own={a['path']:a for a in effect.get('artifacts',[])}
        if set(own)-{str(path) for path,_,_ in expected}:return 'conflict'
        for path,data,kind in expected:
            digest=hashlib.sha256(data).hexdigest();prior=own.get(str(path))
            try:actual=hashlib.sha256(guarded_read(path,64*1024*1024,private=True)).hexdigest()
            except FileNotFoundError:actual=None
            if actual is None:
                if effect['state']=='verified' or (prior and prior.get('before') is not None):return 'conflict'
                pending=True;continue
            if not prior or prior.get('owner')!=self.claw['id'] or prior.get('class')!=kind or prior.get('referencedBy')!=[self.claw['id']] or prior.get('sha256')!=digest or actual!=digest:return 'conflict'
        if effect['phase']=='home':
            for relative in self.HOME_DIRECTORIES:
                try:
                    with directory(self.root/relative,private=True):pass
                except FileNotFoundError:pending=True
        if pending:return 'conflict' if effect['state']=='verified' else 'retry_owned'
        return 'completed'

    def reconcile_source(self,effect):
        """Record successful owned build revisions. An interrupted build stays unknown.

        Only previously copied source files are eligible. Dependencies and clone
        trees remain separately installed resources, never inferred cleanup targets.
        """
        latest={a['path']:a for e in self.context['journal']['effects'] for a in e.get('artifacts',[])}
        changes=[]
        for name,prior in latest.items():
            if not Path(name).is_relative_to(self.source):continue
            data=guarded_read(name,64*1024*1024,private=True)
            digest=hashlib.sha256(data).hexdigest()
            if digest!=prior['sha256']:
                changes.append(self.artifact(name,data,'built-source',before=prior['sha256']))
        if changes:self.context['artifactIntent'](effect['id'],changes)

    def inputs(self, effect):
        if effect['phase']=='identity':
            for target,data,kind in self.file_outputs('identity'):self.write(effect,target,data,kind=kind)
            return {'state':'verified'}
        if effect['phase']!='inventory':raise Conflict('input_phase_invalid')
        names={'testbed-yaml':'testbed.yaml','testbed-json':'testbed.json','testbed-csv':'testbed.csv'}
        selected=[i for i in self.context['plan'][effect['phase']] if i['owner']==self.claw['id']]
        from pyats_testbeds import policy
        testbed=policy(self.claw.get('testbed'))
        if testbed['mode']=='dynamic':
            if selected:raise Conflict('dynamic_static_input_conflict')
            for target,data,kind in self.file_outputs('inventory'):self.write(effect,target,data,kind=kind)
            return {'state':'verified'}
        if not selected and 'pyats' in self.claw['capabilities']['components']:
            # Static pyATS requires a testbed at startup. No selected inventory
            # means zero devices, never a source/neighbor testbed or guessed host.
            self.write(effect,Path(self.claw['workspace'])/'testbed.yaml',b'devices: {}\n',kind='inventory')
        for item in selected:
            data=guarded_read(item['path'],256*1024)
            if hashlib.sha256(data).hexdigest()!=item['sha256']:
                raise Conflict('input_changed')
            # Parsing/normalizing a testbed is a separate editor operation; this
            # copies the exact human-reviewed input, never a shared symlink.
            if item['kind'] not in names:
                raise Conflict('input_kind_invalid')
            self.write(effect,Path(self.claw['workspace'])/names[item['kind']],data,kind=effect['phase'])
            from setup_harness import Harness
            harness=Harness(self.repository,self.claw,self.context,self,
                tool_directories=self.context.get('toolDirectories',()))
            node=shutil.which('node',path=harness.environment()['PATH'])
            if not node:return {'state':'configuration_required'}
            result=harness.call(effect,[node,str(self.source/'scripts/setup-testbed.mjs'),
                str(Path(self.claw['workspace'])/names[item['kind']]),item['kind'].removeprefix('testbed-')],capture=True)
            if result['returncode']:return {'state':'failed'}
            target=Path(self.claw['workspace'])/'testbed.yaml'
            self.write(effect,target,result['stdout'],kind='inventory',
                expected=hashlib.sha256(data).hexdigest() if item['kind']=='testbed-yaml' else None)
        return {'state':'verified'}

    def registration(self, effect):
        from setup_generated import generated as generated_settings
        from setup_secrets import read_owned_environment,_dotenv
        env_path=self.root/'.env'
        latest={a['path']:a for e in self.context['journal']['effects'] for a in e.get('artifacts',[])}
        env_artifact=latest.get(str(env_path))
        if not env_artifact:raise Conflict('environment_ownership_missing')
        values=read_owned_environment(env_path,env_artifact['sha256'])
        python=guarded_read(self.root/'.setup/python312',8192,private=True).decode().strip()
        values.update(generated_settings(self.claw,self.validator,python))
        template=loads(guarded_read(self.repository/'config/openclaw.json',8*1024*1024))['mcpServers']
        installer=helper(self.repository,'install-mcp-config.py')
        requested=set(self.claw['capabilities']['components'])
        selected={e['component'] for e in self.context['journal']['effects']
                  if e['owner']==self.claw['id'] and e['phase']=='components' and e['state']=='verified'} & requested
        generated={}
        from setup_components import selected_servers,launcher_runtime,managed_comms_registration
        if 'twilio' in selected:
            from setup_secrets import child_environment
            import shutil
            node=shutil.which('node',path=child_environment(self.root,self.claw['harness'],
                tool_directories=self.context.get('toolDirectories',()))['PATH'])
            if not node:raise Conflict('comms_node_unavailable')
            pointer=self.root/'.setup/comms-node.json'
            self.write(effect,pointer,canonical({'command':node}),kind='runtime-record',
                expected=latest.get(str(pointer),{}).get('sha256'))
        for component in sorted(selected):
            for name in selected_servers(component,self.claw,self.validator.components[component]):
                if name not in template or name=='hermes-hud-mcp':
                    continue
                runtime=launcher_runtime(component,self,template[name],name)
                if runtime and not Path(runtime).is_relative_to(self.root):
                    raise Conflict('component_runtime_outside_home')
                entry=installer.bind_entry(template[name],self.source,runtime)
                if self.claw['harness']=='openclaw':
                    from setup_registration import native_environment
                    from mcp_environment import native_entry
                    entry=native_entry(name,entry,values,self.repository)
                    entry['env']=native_environment(name,entry.get('env',{}),values)
                entry.setdefault('env',{}).update({'NETCLAW_RUNTIME_ROOT':str(self.root/'python-runtimes'),
                    'NETCLAW_RUNTIME_ENV':str(self.root/'.env'),'NETCLAW_RUNTIME':self.claw['harness'],
                    'HOME':str(self.root/'.setup/os-home'),
                    'HERMES_HOME' if self.claw['harness']=='hermes' else 'OPENCLAW_STATE_DIR':str(self.root)})
                if self.claw['harness']=='hermes':
                    # The protected companion accepts exactly these two owned
                    # launcher references and inherits its selected runtime.
                    entry['env']={'NETCLAW_RUNTIME_ROOT':str(self.root/'python-runtimes'),
                                  'NETCLAW_RUNTIME_ENV':str(self.root/'.env')}
                entry=managed_comms_registration(self,name,python) or entry
                generated[name]=entry
        env_data=''.join(k+'='+_dotenv.quote(values[k])+'\n' for k in sorted(values)).encode()
        if hashlib.sha256(env_data).hexdigest()!=env_artifact['sha256']:
            self.write(effect,env_path,env_data,kind='credentials',expected=env_artifact['sha256'])
        values.clear()
        config=self.root/('config.yaml' if self.claw['harness']=='hermes' else 'openclaw.json')
        data=guarded_read(config,8*1024*1024);before=hashlib.sha256(data).hexdigest()
        # Engine-owned initial Hermes config uses JSON, a YAML subset. Native
        # YAML edits require reconciliation, rather than a lossy hand parser.
        current=loads(data,8*1024*1024)
        existing=current.get('mcp_servers',{}) if self.claw['harness']=='hermes' else current.get('mcp',{}).get('servers',{})
        prior_path=self.root/'netclaw-mcp-config.json'
        if str(prior_path) in latest and revision(prior_path)!=latest[str(prior_path)]['sha256']:
            raise Conflict('registration_changed')
        prior=loads(guarded_read(prior_path,8*1024*1024,private=True))['mcpServers'] if str(prior_path) in latest else {}
        merged=dict(existing)
        for name,entry in generated.items():
            if name in existing and existing[name] not in (entry,prior.get(name)):
                raise Conflict('registration_changed')
            merged[name]=entry
        for name,entry in prior.items():
            if name not in generated and merged.get(name)==entry:merged.pop(name)
        if self.claw['harness']=='hermes':current['mcp_servers']=merged
        else:current.setdefault('mcp',{})['servers']=merged
        self.write(effect,config,canonical(current)+b'\n',kind='configuration',expected=before)
        def expected(name):return latest.get(str(self.root/name),{}).get('sha256')
        self.write(effect,self.root/'netclaw-mcp-config.json',canonical({'mcpServers':generated})+b'\n',kind='registration',expected=expected('netclaw-mcp-config.json'))
        manifest='# NetClaw installed components — verified dependency adapters\n# Requested components and outcomes are in .setup/components.json.\n'+'\n'.join(c for c in self.claw['capabilities']['components'] if c in selected)+'\n'
        self.write(effect,self.root/'netclaw-components.conf',manifest.encode(),kind='manifest',expected=expected('netclaw-components.conf'))
        self.write(effect,self.root/'.setup/components.json',canonical({'schema':1,'requested':self.claw['capabilities']['components'],
            'installed':sorted(selected),'deferred':sorted(requested-selected)})+b'\n',kind='manifest',expected=expected('.setup/components.json'))
        return {'state':'verified' if requested==selected else 'configuration_required'}
