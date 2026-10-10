#!/usr/bin/env python3
"""Selected-installation daemon control; never kills another installation by name."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shlex
import signal
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'mcp-servers/protocol-mcp'))
from bgp.federation.runtime import selected,read_private,write_private


def environment(runtime):
    spec=importlib.util.spec_from_file_location('literal_env',ROOT/'scripts/write-env.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    env=dict(os.environ)
    for file in (runtime.env_file,runtime.home/'mesh.systemd.env'):
        if file.exists():
            env.update({k:v for k,v in module.values(file.read_text()).items() if k.startswith(('NETCLAW_','N2N_','BGP_'))})
    return runtime.environment(env)


def api_url(runtime):
    env=environment(runtime)
    url=env.get('NETCLAW_BGP_API') or f"http://127.0.0.1:{int(env.get('BGP_API_PORT','8179'))}"
    from urllib.parse import urlsplit
    p=urlsplit(url)
    if p.scheme!='http' or p.hostname not in ('127.0.0.1','localhost') or p.username or p.password or p.query or p.fragment or p.path not in ('','/'):
        raise ValueError('local selected federation API required')
    return url.rstrip('/')


def status(runtime):
    with urllib.request.urlopen(api_url(runtime)+'/status',timeout=2) as response:
        result=json.loads(response.read(65536))
    if not runtime.installation or result.get('installation_id')!=runtime.installation or result.get('harness_type')!=runtime.kind:
        raise ValueError('foreign or legacy daemon: selected installation identity does not match')
    return result


def stamp(pid):
    return subprocess.run(['ps','-p',str(pid),'-o','lstart='],capture_output=True,text=True).stdout.strip()


def claim(runtime):
    runtime.fence(initialize=True)
    fd=os.open(runtime.state/'daemon.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:os.close(fd);raise RuntimeError('selected daemon already owned by a running process')
    os.set_inheritable(fd,True)
    nonce=secrets.token_hex(24)
    write_private(runtime.state/'daemon.json',{'installationId':runtime.installation,'pid':os.getpid(),'started':stamp(os.getpid()),'nonce':nonce})
    os.environ.update(NETCLAW_DAEMON_NONCE=nonce,NETCLAW_DAEMON_LOCK_FD=str(fd))
    return fd


def stop(runtime):
    try:record=read_private(runtime.state/'daemon.json')
    except FileNotFoundError:return
    if record.get('installationId')!=runtime.installation:raise ValueError('foreign daemon ownership')
    pid=record['pid']
    if not isinstance(pid,int) or pid<=1:raise ValueError('invalid owned PID')
    if not stamp(pid):return
    command=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True).strip()
    if stamp(pid)!=record['started'] or str(ROOT/'mcp-servers/protocol-mcp/bgp-daemon-v2.py') not in command:
        raise ValueError('PID ownership no longer matches; refusing to signal')
    os.kill(pid,signal.SIGTERM)
    for _ in range(100):
        if not stamp(pid):return
        time.sleep(.1)
    raise RuntimeError('owned daemon did not stop within 10s; no unrelated process was signalled')


def main():
    action=sys.argv[1] if len(sys.argv)>1 else 'status'
    runtime=selected(initialize=action in ('start','run'))
    if action=='env':
        env=environment(runtime)
        fields={'NETCLAW_RUNTIME':runtime.kind,'RUNTIME_HOME':str(runtime.home),'BGP_API':api_url(runtime)}
        fields.update({k:env[k] for k in ('HERMES_HOME','OPENCLAW_HOME','OPENCLAW_STATE_DIR','OPENCLAW_CONFIG_PATH','N2N_BASE_DIR') if k in env})
        for key,value in fields.items():print('export '+key+'='+shlex.quote(value))
        return
    if action=='status':print(json.dumps(status(runtime)));return
    if action=='stop':stop(runtime);return
    if action=='start':
        runtime.fence(initialize=True)
        try:
            status(runtime)
            stop(runtime)
        except (OSError,ValueError):
            # A foreign listener is not a service to replace. The new daemon's
            # bind fails visibly; it never signals the unrelated process.
            pass
        env=environment(runtime)
        record=runtime.home/'python-runtimes/records/n2n'
        interpreter=record.read_text().strip() if record.exists() else sys.executable
        if runtime.kind=='hermes' and not record.exists():raise RuntimeError('install the n2n component into this Hermes home before starting federation')
        output=runtime.state/'daemon.log'
        fd=os.open(output,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'a') as log:
            process=subprocess.Popen([interpreter,str(Path(__file__).resolve()),'run'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        for _ in range(150):
            if process.poll() is not None:raise RuntimeError('selected daemon failed; inspect '+str(output))
            try:
                result=status(runtime)
                if result.get('pid')==process.pid and (result.get('federation_ready') or result.get('n2n_enabled') is False):
                    print(json.dumps(result));return
            except (OSError,ValueError):pass
            time.sleep(.2)
        raise RuntimeError('selected daemon not ready; inspect '+str(output))
    if action=='run':
        env=environment(runtime)
        os.environ.update(env)
        claim(runtime)
        os.execve(sys.executable,[sys.executable,str(ROOT/'mcp-servers/protocol-mcp/bgp-daemon-v2.py')],dict(os.environ))
    raise ValueError('expected env, start, stop, status or run')

if __name__=='__main__':
    try:main()
    except Exception as error:sys.exit(str(error))
