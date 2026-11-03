#!/usr/bin/env python3
"""Run one official DefenseClaw process behind a durable operation provider fence.

The runner loads guard.env and passes a non-secret upstream sentinel to the
official child. The provider key is absent from the child environment; these
trusted guard processes share a UID and the private filesystem. The unauthenticated
loopback proxy requires the dedicated guard-container network namespace.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent/'lib'))
from protected_provider import (MODEL,ProviderFence,ProviderProxy,ProviderRefused,
    canonical,private_directory,private_read,private_write,require)


def load_guard_env(home):
    raw=private_read(home/'guard.env',16384)
    try:lines=raw.decode('utf-8','strict').splitlines()
    except UnicodeError:raise ProviderRefused('guard_env_invalid',503) from None
    values={}
    for line in lines:
        line=line.strip()
        if not line or line.startswith('#'):continue
        require('=' in line,'guard_env_invalid',503)
        key,value=line.split('=',1)
        require(key in ('ANTHROPIC_API_KEY','DEFENSECLAW_GATEWAY_TOKEN') and key not in values,'guard_env_invalid',503)
        if value.startswith(('"',"'")):
            require(len(value)>=2 and value[-1]==value[0],'guard_env_invalid',503);value=value[1:-1]
        require(value and value.isascii() and '\n' not in value and '\r' not in value and len(value)<=4096,'guard_env_invalid',503)
        values[key]=value
    require(set(values)=={'ANTHROPIC_API_KEY','DEFENSECLAW_GATEWAY_TOKEN'},'guard_credentials_missing',503)
    require(values['ANTHROPIC_API_KEY']!=values['DEFENSECLAW_GATEWAY_TOKEN'],'distinct_guard_credentials_required',503)
    return values


def verify_config(home,expected,key):
    require(isinstance(expected,str) and re.fullmatch('[0-9a-f]{64}',expected),'guard_config_pin_required',503)
    raw=private_read(home/'config.yaml',1024*1024)
    require(hashlib.sha256(raw).hexdigest()==expected,'guard_config_changed',503)
    require(key.encode() not in raw,'provider_key_in_guard_config',503)
    try:text=raw.decode('utf-8','strict')
    except UnicodeError:raise ProviderRefused('guard_config_invalid',503) from None
    # Hash pin binds the whole reviewed official config. These checks additionally
    # prevent accidental direct-provider/credential routing during construction.
    base_urls=re.findall(r'^\s*base_url:\s*(\S+)\s*$',text,re.M)
    keys=re.findall(r'^\s*api_key_env:\s*(\S+)\s*$',text,re.M)
    models=re.findall(r'^\s*model:\s*(\S+)\s*$',text,re.M)
    require(base_urls and all(value=='http://127.0.0.1:18888' for value in base_urls),'guard_must_use_provider_fence',503)
    require(keys and set(keys)=={'DEFENSECLAW_LLM_KEY'},'guard_credential_route_refused',503)
    require(models and set(models)=={'anthropic/'+MODEL},'guard_model_mismatch',503)
    require(re.search(r'^data_dir:\s*'+re.escape(str(home))+r'\s*$',text,re.M),'guard_data_directory_mismatch',503)
    require(not re.search(r'^\s*(api_key|forward_custom_headers):\s*(?!false\s*$)\S+',text,re.M),'guard_inline_or_forwarded_credential_refused',503)
    return hashlib.sha256(raw).hexdigest()


def verify_policies(home,expected):
    require(isinstance(expected,str) and re.fullmatch('[0-9a-f]{64}',expected),'guard_policy_pin_required',503)
    raw=private_read(home/'official-policy-manifest.json',1024*1024)
    require(hashlib.sha256(raw).hexdigest()==expected,'guard_policy_manifest_changed',503)
    try:manifest=json.loads(raw)
    except ValueError:raise ProviderRefused('guard_policy_manifest_invalid',503) from None
    require(isinstance(manifest,list) and 0<len(manifest)<=512,'guard_policy_manifest_invalid',503)
    expected_paths=set()
    for item in manifest:
        require(isinstance(item,dict) and set(item)=={'path','sha256'},'guard_policy_manifest_invalid',503)
        name=item['path'];digest=item['sha256']
        require(isinstance(name,str) and name.startswith('policies/') and '\\' not in name and '..' not in Path(name).parts and not Path(name).is_absolute() and name not in expected_paths,'guard_policy_path_invalid',503)
        require(isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest),'guard_policy_manifest_invalid',503)
        path=home/name;info=path.lstat()
        require(path.absolute()==path.resolve() and stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and not info.st_mode&0o022 and info.st_size<=5*1024*1024,'unsafe_guard_policy',503)
        require(hashlib.sha256(path.read_bytes()).hexdigest()==digest,'guard_policy_changed',503)
        expected_paths.add(name)
    actual={str(path.relative_to(home)) for path in (home/'policies').rglob('*') if path.is_file() or path.is_symlink()}
    require(actual==expected_paths,'guard_policy_closure_changed',503)
    return expected


def bootstrap_policies(home,expected,source):
    """Copy a pinned immutable image policy pack only into an absent owned pack."""
    target=home/'policies'
    if target.exists() or target.is_symlink():return verify_policies(home,expected)
    source=Path(source).absolute()
    require(source==source.resolve(),'unsafe_image_policy_source',503)
    def image_read(path,maximum):
        info=path.lstat()
        require(path.absolute()==path.resolve() and stat.S_ISREG(info.st_mode) and info.st_uid in (0,os.getuid()) and not info.st_mode&0o022 and info.st_size<=maximum,'unsafe_image_policy_source',503)
        return path.read_bytes()
    raw=image_read(source/'official-policy-manifest.json',1024*1024)
    require(hashlib.sha256(raw).hexdigest()==expected,'guard_policy_manifest_changed',503)
    try:manifest=json.loads(raw)
    except ValueError:raise ProviderRefused('guard_policy_manifest_invalid',503) from None
    require(isinstance(manifest,list) and 0<len(manifest)<=512,'guard_policy_manifest_invalid',503)
    # Read and verify all image-owned bytes before creating any runtime policy.
    files={}
    for item in manifest:
        require(isinstance(item,dict) and set(item)=={'path','sha256'},'guard_policy_manifest_invalid',503)
        name=item['path'];digest=item['sha256']
        require(isinstance(name,str) and name.startswith('policies/') and '..' not in Path(name).parts and '\\' not in name and name not in files,'guard_policy_path_invalid',503)
        require(isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest),'guard_policy_manifest_invalid',503)
        content=image_read(source/name,5*1024*1024)
        require(hashlib.sha256(content).hexdigest()==digest,'guard_policy_changed',503)
        files[name]=content
    actual={str(path.relative_to(source)) for path in (source/'policies').rglob('*') if path.is_file() or path.is_symlink()}
    require(set(files)==actual,'guard_policy_closure_changed',503)
    if (home/'official-policy-manifest.json').exists():
        require(private_read(home/'official-policy-manifest.json')==raw,'guard_policy_manifest_changed',503)
    stage=private_directory(home/('.policies-'+str(__import__('uuid').uuid4())))
    for name,content in files.items():private_write(stage/Path(name).relative_to('policies'),content)
    os.rename(stage,target)
    private_write(home/'official-policy-manifest.json',raw)
    return verify_policies(home,expected)


def child_environment(home,secrets):
    user=private_directory(home/'official-user')
    return {'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':str(user),'DEFENSECLAW_HOME':str(home),
            'DEFENSECLAW_LLM_KEY':'netclaw-operation-proxy',
            'DEFENSECLAW_GATEWAY_TOKEN':secrets['DEFENSECLAW_GATEWAY_TOKEN']}


async def drain_guard_log(reader,stream,secret_values,maximum=4*1024*1024):
    """Bound diagnostics and redact credential matches across arbitrary pipe chunks."""
    tokens=sorted({value.encode() for value in secret_values.values()},key=len,reverse=True)
    keep=max(map(len,tokens),default=1)-1
    pending=b'';written=0
    def output(data):
        nonlocal written
        if written<maximum:
            data=data[:maximum-written];stream.write(data);written+=len(data)
    while chunk:=await reader.read(65536):
        pending+=chunk;limit=max(0,len(pending)-keep);position=0
        while position<limit:
            matches=[(pending.find(token,position),token) for token in tokens]
            matches=[(index,token) for index,token in matches if position<=index<limit]
            if not matches:
                output(pending[position:limit]);position=limit
            else:
                index,token=min(matches,key=lambda match:(match[0],-len(match[1])))
                output(pending[position:index]+b'[redacted]');position=index+len(token)
        pending=pending[position:]
    for token in tokens:pending=pending.replace(token,b'[redacted]')
    output(pending)
    stream.flush();os.fsync(stream.fileno())


async def run(args):
    os.umask(0o077)
    # The fixed HTTPS transport ignores proxy environment; also remove custom CA
    # and routing variables before constructing its TLS context.
    for key in list(os.environ):
        if key.lower() in ('http_proxy','https_proxy','all_proxy','no_proxy') or key in ('SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE','CURL_CA_BUNDLE','ANTHROPIC_BASE_URL','OPENAI_BASE_URL'):
            os.environ.pop(key,None)
    home=private_directory(args.home)
    secret_values=load_guard_env(home)
    config_pin=verify_config(home,args.config_sha256,secret_values['ANTHROPIC_API_KEY'])
    policy_pin=bootstrap_policies(home,args.policy_manifest_sha256,args.policy_source)
    require(args.model==MODEL and args.maximum_calls==2,'unqualified_provider_profile',503)
    require(args.expires_at_ms>int(time.time()*1000),'operation_expired',403)
    binary=Path(args.binary).absolute();info=binary.lstat()
    require(binary==binary.resolve() and stat.S_ISREG(info.st_mode) and not info.st_mode&0o022 and os.access(binary,os.X_OK),'unsafe_guard_binary',503)
    # Guard image/binary provenance is frozen by the coordinator's image pin.
    binary_pin=hashlib.sha256(binary.read_bytes()).hexdigest()
    fence=ProviderFence(home/'provider.sqlite',operation_id=args.operation_id,expires_at_ms=args.expires_at_ms,model=args.model,maximum_calls=args.maximum_calls)
    proxy=ProviderProxy(fence,secret_values['ANTHROPIC_API_KEY'])
    await proxy.start('127.0.0.1',18888)
    stop=asyncio.Event();loop=asyncio.get_running_loop()
    for sig in (signal.SIGTERM,signal.SIGINT):loop.add_signal_handler(sig,stop.set)
    process=None;returncode=1;waiters=[];log_task=None
    fd=os.open(home/'guard.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
    log=os.fdopen(fd,'ab',buffering=0)
    try:
        info=os.fstat(log.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and not info.st_mode&0o077,'unsafe_guard_log',503)
        process=await asyncio.create_subprocess_exec(str(binary),env=child_environment(home,secret_values),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
        log_task=asyncio.create_task(drain_guard_log(process.stdout,log,secret_values))
        private_write(home/'provider-runner.json',{'schemaVersion':1,'operation_id':args.operation_id,'proxy_host':'127.0.0.1','proxy_port':18888,
            'runner_pid':os.getpid(),'guard_pid':process.pid,'config_sha256':config_pin,'policy_manifest_sha256':policy_pin,
            'binary_sha256':binary_pin,'model':MODEL,'maximum_provider_calls':2,'expires_at_ms':args.expires_at_ms})
        process_wait=asyncio.create_task(process.wait());stop_wait=asyncio.create_task(stop.wait())
        expiry_wait=asyncio.create_task(asyncio.sleep(max(0,(args.expires_at_ms-int(time.time()*1000))/1000)))
        waiters=[process_wait,stop_wait,expiry_wait]
        await asyncio.wait(waiters,return_when=asyncio.FIRST_COMPLETED)
        returncode=process.returncode if process.returncode is not None else 0
    finally:
        if proxy.server:proxy.server.close();await proxy.server.wait_closed()
        if process and process.returncode is None:
            process.terminate()
            try:await asyncio.wait_for(process.wait(),5)
            except asyncio.TimeoutError:process.kill();await process.wait()
        await proxy.close()
        if log_task:
            try:await asyncio.wait_for(log_task,5)
            except asyncio.TimeoutError:log_task.cancel();await asyncio.gather(log_task,return_exceptions=True)
        for waiter in waiters:waiter.cancel()
        if waiters:await asyncio.gather(*waiters,return_exceptions=True)
        private_write(home/'provider-receipt.json',fence.snapshot())
        log.close()
    return returncode


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',required=True)
    parser.add_argument('--binary',default='/usr/local/bin/defenseclaw')
    parser.add_argument('--policy-source',default='/opt/defenseclaw')
    parser.add_argument('--config-sha256',required=True)
    parser.add_argument('--policy-manifest-sha256',required=True)
    parser.add_argument('--operation-id',default=os.environ.get('NETCLAW_OPERATION_ID'))
    parser.add_argument('--expires-at-ms',type=int,default=os.environ.get('NETCLAW_OPERATION_EXPIRES_MS'))
    parser.add_argument('--model',default=os.environ.get('NETCLAW_OPERATION_MODEL',MODEL))
    parser.add_argument('--maximum-calls',type=int,default=os.environ.get('NETCLAW_OPERATION_MAX_PROVIDER_CALLS','2'))
    args=parser.parse_args()
    try:
        require(args.operation_id is not None and type(args.expires_at_ms) is int,'operation_binding_required',503)
        return asyncio.run(run(args))
    except ProviderRefused as exc:
        print('protected_guard: '+exc.code,file=sys.stderr);return 1
    except Exception:
        print('protected_guard: guard_unavailable',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
