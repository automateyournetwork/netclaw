"""Scoped native service definitions and independent Risk materialization."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import pwd
import re
import shutil
import sys

from setup_schema import canonical, loads
from setup_state import Conflict, directory, guarded_read, guarded_write, revision, artifact_revision
from setup_secrets import read_owned_environment, _dotenv
from ha_setup_guard import require_standalone_home

ROLES=('gateway','hud','federation')


def latest_environment(context,home,*,effect=None):
    artifacts=[a for e in context['journal']['effects'] for a in e.get('artifacts',[]) if a['path']==str(home/'.env')]
    if not artifacts:raise Conflict('environment_ownership_missing')
    expected=artifacts[-1]['sha256']
    if effect is not None:
        from setup_comms_services import observed_owned_revision
        expected=observed_owned_revision(context,home/'.env',effect=effect)
    return read_owned_environment(home/'.env',expected),expected


def configure_risk(effect,context,deploy,harness):
    claw=deploy.claw;border=next(c for c in context['plan']['claws'] if c['role']=='border')
    require_standalone_home(deploy.root)
    require_standalone_home(border['runtimeHome'])
    values,before=latest_environment(context,deploy.root)
    values.update(N2N_ENABLED='true',N2N_ROLE=claw['role'],N2N_RISK_NAME=border['id'],
        N2N_RISK_DESCRIPTION=border['displayName'],N2N_RISK_MODE=context['plan']['posture']['mode'],
        N2N_ENABLED_STACKS='in2n',N2N_BASE_DIR=str(deploy.root/'n2n'),N2N_DISPLAY_NAME=claw['displayName'],
        N2N_IN2N_BIND='127.0.0.1',N2N_IN2N_PORT=str(claw['endpoints']['federationPort']),
        NETCLAW_MESH_OPEN='false',BGP_LISTEN_HOST='127.0.0.1',
        BGP_API_PORT=str(claw['endpoints']['bgpApiPort']),BGP_LISTEN_PORT=str(claw['endpoints']['bgpPort']),
        BGP_DAEMON_API='http://127.0.0.1:'+str(claw['endpoints']['bgpApiPort']),
        NETCLAW_BGP_API='http://127.0.0.1:'+str(claw['endpoints']['bgpApiPort']))
    if claw['role']=='member':
        values.update(N2N_MEMBER_ID=border['id']+'/'+claw['id'],N2N_MEMBER_BASE=str(deploy.root/'n2n'),
            N2N_MEMBER_ENV_FILE=str(deploy.root/'.env'),N2N_BORDER_ENDPOINT='127.0.0.1:'+str(border['endpoints']['federationPort']))
        values.update(N2N_MEMBER_SCOPE=json.dumps(claw['capabilities']['skills']),N2N_IDLE_EXIT_S='120' if claw['service']['mode']=='on-demand' else '0',
            N2N_MEMBER_MODEL=({'lm-studio':'lmstudio'}.get(claw['provider']['id'],claw['provider']['id'])+'/'+claw['provider']['model']) if claw['harness']=='openclaw' else claw['provider']['model'])
    data=''.join(k+'='+_dotenv.quote(values[k])+'\n' for k in sorted(values)).encode()
    deploy.write(effect,deploy.root/'.env',data,kind='credentials',expected=before)
    # Membership/pinning is a separate observed transaction. No Border secrets
    # or token are copied into a member's environment or persisted plan.
    if harness is None:return {'state':'configuration_required'}
    record={'schema':1,'runId':context['runId'],'planHash':context['planHash'],'border':border,'claw':claw,'python':sys.executable}
    file=deploy.root/'.setup/risk-input.json'
    deploy.write(effect,file,canonical(record),kind='risk-input')
    python=guarded_read(deploy.root/'python-runtimes/records/n2n',8192).decode().strip()
    if not Path(python).is_relative_to(deploy.root):raise Conflict('runtime_outside_home')
    result=harness.call(effect,[python,str(deploy.source/'scripts/setup-federation.py'),'materialize','--record',str(file)],timeout=30,capture=True)
    return {'state':'verified' if result['returncode']==0 and loads(result['stdout']).get('enrolled') is True else 'unknown'}


def observe_risk(effect,context,deploy,harness):
    python=guarded_read(deploy.root/'python-runtimes/records/n2n',8192).decode().strip()
    if not Path(python).is_relative_to(deploy.root):return False
    result=harness.call(effect,[python,str(deploy.source/'scripts/setup-federation.py'),'observe','--record',str(deploy.root/'.setup/risk-input.json')],capture=True,timeout=20)
    return result['returncode']==0 and loads(result['stdout']).get('enrolled') is True


def service_root(platform, user_home):
    return Path(user_home)/('Library/LaunchAgents' if platform=='macos' else '.config/systemd/user')


def roles(claw,shape):
    result=['hud']
    if claw['harness']=='openclaw' or claw.get('channels'):result.insert(0,'gateway')
    if shape=='risk':result.append('federation')
    return result


def gateway_command(home,harness):
    """Foreground commands only; the owned native manager handles restarts."""
    home=Path(home)
    if harness=='openclaw':return [str(home/'.setup/prefix/bin/openclaw'),'gateway','run']
    if harness=='hermes':return [str(home/'python-runtimes/hermes-hud-agent/venv/bin/python'),
        '-m','hermes_cli.main','gateway','run','--external-supervisor']
    raise Conflict('service_role_unsupported')


def service_hot(claw,role):
    # On-demand applies to the routed member worker. Its local management
    # plane stays available for identity-bound verification and editor controls.
    return role!='federation' or claw['role']!='member' or claw['service']['mode']=='hot'


def descriptor(platform,name,role,home,source,python,user_home,*,hot=True):
    if role not in ROLES or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}',name):raise Conflict('service_identity_invalid')
    label=name+'-'+role
    # Management binds the actual executable, not a mutable python3 alias.
    # In particular pyenv and Homebrew expose symlinked entrypoints on macOS.
    arguments=[str(Path(python).resolve()),str(source/'scripts/setup-service.py'),'--home',str(home),'--role',role]
    root=service_root(platform,user_home)
    if platform=='macos':
        file=root/(label+'.plist')
        data=plistlib.dumps({'Label':label,'ProgramArguments':arguments,'WorkingDirectory':str(home),
            'RunAtLoad':hot,'KeepAlive':hot,'ThrottleInterval':10,'Umask':0o077,
            'StandardOutPath':'/dev/null','StandardErrorPath':'/dev/null'},sort_keys=True)
    elif platform=='wsl2':
        # systemd has its own specifier/argument escaping, not shell quoting.
        def quote(value):return json.dumps(str(value).replace('%','%%'),ensure_ascii=False)
        file=root/(label+'.service')
        # WorkingDirectory is a literal path, unlike ExecStart's quoted argv.
        # Quoting it makes systemd see a non-absolute path. Start in the owned
        # .setup directory so systemd 255 cannot strip a home's trailing space.
        # setup-service.py validates ownership, then chdirs to the exact home.
        working_directory=str(home/'.setup').replace('%','%%')
        text='[Unit]\nDescription=Owned NetClaw '+role+'\n[Service]\nType=simple\nUMask=0077\nWorkingDirectory='+working_directory+'\nExecStart=:'+ ' '.join(quote(a) for a in arguments)+'\nRestart='+('on-failure' if hot else 'no')+'\nRestartSec=10\nStandardOutput=null\nStandardError=null\n[Install]\nWantedBy=default.target\n'
        data=text.encode()
    else:raise Conflict('service_platform_unsupported')
    item={'role':role,'label':label,'file':str(file),'arguments':arguments,'sha256':hashlib.sha256(data).hexdigest(),'hot':hot}
    if platform=='wsl2':item['execFlags']=['no-env-expand']
    return item,data


def native_call(harness,effect,arguments,*,capture=True):
    env={'PATH':os.defpath,'HOME':pwd.getpwuid(os.getuid()).pw_dir,'LANG':'C',
         'XDG_RUNTIME_DIR':'/run/user/'+str(os.getuid()),'DBUS_SESSION_BUS_ADDRESS':'unix:path=/run/user/'+str(os.getuid())+'/bus'}
    return harness.execute(arguments,cwd=harness.home,env=env,capture=capture,timeout=20,
        lock_fds=harness.context['lockFds'],started=lambda identity:harness.context['writerStarted'](effect['id'],identity))


def native_service_pid(harness,effect,platform,item):
    if revision(item['file'])!=item['sha256']:raise Conflict('service_definition_changed')
    if platform=='macos':
        result=native_call(harness,effect,['/bin/launchctl','print','gui/'+str(os.getuid())+'/'+item['label']])
        if result['returncode']:return None
        value=result['stdout'].decode('utf-8','strict')
        args=re.search(r'\n\s*arguments = \{\n([\s\S]*?)\n\s*\}',value)
        pid=re.search(r'\n\s*pid = ([1-9][0-9]*)\b',value)
        valid=bool('path = '+item['file'] in value and args and
            [a.strip() for a in args[1].splitlines() if a.strip()]==item['arguments'] and
            pid and int(pid[1])>1)
        return int(pid[1]) if valid else None
    result=native_call(harness,effect,['/usr/bin/systemctl','--user','show',Path(item['file']).name,'--no-pager',
        '--property=ActiveState,MainPID,FragmentPath,NeedDaemonReload,DropInPaths'])
    if result['returncode']:return None
    fields=dict(line.split('=',1) for line in result['stdout'].decode().splitlines() if '=' in line)
    from setup_systemd import observe_argv
    valid=(fields.get('ActiveState')=='active' and fields.get('MainPID','0').isdigit() and int(fields['MainPID'])>1 and
        fields.get('FragmentPath')==item['file'] and fields.get('NeedDaemonReload')=='no' and not fields.get('DropInPaths') and
        observe_argv(lambda args:native_call(harness,effect,args),item))
    return int(fields['MainPID']) if valid else None


def native_observe(harness,effect,platform,item):
    return native_service_pid(harness,effect,platform,item) is not None


def install_services(effect,context,deploy,harness,*,user_home=None):
    platform=context['plan']['host']['platform'];claw=deploy.claw
    from setup_comms_services import activation_gate,verify_activation_binding
    try:comms_binding=activation_gate(effect,context,deploy,harness)
    except Conflict as error:
        # This known pre-activation prerequisite runs before any manager or
        # service write. It is incomplete configuration, not an uncertain start.
        if str(error)=='comms_access_scope_required':return {'state':'configuration_required'}
        raise
    account=Path(user_home) if user_home is not None else Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
    env=harness.environment();node=shutil.which('node',path=env['PATH']);npm=shutil.which('npm',path=env['PATH'])
    if not node or not npm:return {'state':'configuration_required'}
    policy=harness.call(effect,[node,str(deploy.source/'scripts/hud-node-version.mjs')])
    if policy['returncode']:return {'state':'configuration_required'}
    manager=['/bin/launchctl','print','gui/'+str(os.getuid())] if platform=='macos' else ['/usr/bin/systemctl','--user','show-environment']
    if native_call(harness,effect,manager)['returncode']:return {'state':'configuration_required'}
    if not (deploy.source/'ui/netclaw-visual/node_modules/vite/bin/vite.js').is_file():return {'state':'failed'}
    values,env_hash=latest_environment(context,deploy.root)
    data={'schema':1,'owner':claw['id'],'runId':context['runId'],'harness':claw['harness'],'home':str(deploy.root),
        'source':str(deploy.source),'node':node,'toolDirectories':list(harness.tool_directories),'envHash':env_hash,
        'platform':platform,'userHome':str(account),'role':claw['role'],'services':[]}
    data['installationId']=loads(guarded_read(deploy.root/'netclaw-hud/installation.json'))['installationId']
    data['endpoints']=dict(claw['endpoints'])
    if comms_binding is not None:data['commsBinding']=comms_binding
    from setup_service_binding import capture
    source_index=capture(deploy.source,claw['id'],context['journal'])
    index=deploy.write(effect,deploy.root/'.setup/service-source.json',canonical(source_index),kind='service-source')
    data['sourceIndex']={'sha256':index['sha256'],'count':len(source_index['files'])}
    definitions=[]
    for role in roles(claw,context['plan']['shape']):
        item,content=descriptor(platform,claw['service']['name'],role,deploy.root,deploy.source,sys.executable,account,
                                hot=service_hot(claw,role))
        # An existing label/file belongs to somebody until proved otherwise.
        if revision(item['file']) is not None:raise Conflict('service_already_exists')
        query=['/bin/launchctl','print','gui/'+str(os.getuid())+'/'+item['label']] if platform=='macos' else ['/usr/bin/systemctl','--user','cat',Path(item['file']).name]
        if native_call(harness,effect,query)['returncode']==0:raise Conflict('service_label_occupied')
        data['services'].append(item);definitions.append((item,content))
        if platform=='wsl2' and item['hot']:
            link=service_root(platform,account)/'default.target.wants'/Path(item['file']).name
            if os.path.lexists(link):raise Conflict('service_enable_link_occupied')
            item['enableLink']={'path':str(link),'sha256':hashlib.sha256(item['file'].encode()).hexdigest()}
    deploy.write(effect,deploy.root/'.setup/services.json',canonical(data),kind='service-manifest')
    for item,content in definitions:
        context['artifactIntent'](effect['id'],[deploy.artifact(Path(item['file']),content,'service')])
        guarded_write(item['file'],content,expected=None)
        if item.get('enableLink'):
            link=Path(item['enableLink']['path'])
            context['artifactIntent'](effect['id'],[deploy.artifact(link,item['file'].encode(),'service-link')])
            with directory(link.parent,create=True) as parent:
                os.symlink(item['file'],link.name,dir_fd=parent);os.fsync(parent)
    if platform=='wsl2' and native_call(harness,effect,['/usr/bin/systemctl','--user','daemon-reload'])['returncode']:return {'state':'unknown'}
    verified=True
    verify_activation_binding(deploy.root,claw['harness'],comms_binding)
    for item,_ in definitions:
        if not item['hot']:continue
        command=['/bin/launchctl','bootstrap','gui/'+str(os.getuid()),item['file']] if platform=='macos' else ['/usr/bin/systemctl','--user','start',Path(item['file']).name]
        if native_call(harness,effect,command)['returncode']:return {'state':'unknown'}
        verified=native_observe(harness,effect,platform,item) and verified
    return {'state':'verified' if verified else 'unverified'}


def observe_services(effect,context,deploy,harness):
    from setup_process import WriterUncertain
    try:
        manifest=next((a for e in reversed(context['journal']['effects']) for a in reversed(e.get('artifacts',[])) if a['path']==str(deploy.root/'.setup/services.json')),None)
        if not manifest or revision(manifest['path'])!=manifest['sha256']:return False
        data=loads(guarded_read(deploy.root/'.setup/services.json',65536,private=True))
        if data['runId']!=context['runId'] or data['owner']!=deploy.claw['id'] or data['home']!=str(deploy.root):return False
        from setup_service_binding import verify
        verify(deploy.root,deploy.source,data.get('sourceIndex'))
        for item in data['services']:
            link=item.get('enableLink')
            if link and artifact_revision({'path':link['path'],'class':'service-link'})!=link['sha256']:return False
        return bool(data['services']) and all(native_observe(harness,effect,data['platform'],item) for item in data['services'] if item['hot'])
    except WriterUncertain:raise
    except Exception:return False
