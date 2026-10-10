"""Runtime discovery is evidence, not an exit code or a directory check."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('readiness', ROOT/'scripts/installer-readiness.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize('data,valid', [
    ({'servers':{'s':{'tools':1}}, 'tools':['mcp_s_expected']}, True),
    ({'servers':{'s':{'tools':0}}, 'tools':[]},False),
    ({'servers':{'other':{'tools':1}}, 'tools':['mcp_s_expected']},False),
    ({'servers':{'s':{'tools':1}}, 'tools':['mcp_s_wrong']},False),
    ({'servers':{'s':{'tools':1}}, 'tools':['expected'],'diagnostics':[{'message':'failed'}]},False),
    ({'error':'failed'},False),
])
def test_native_probe_requires_expected_discovery(data,valid):
    assert module.native_result(data,'s',['expected']) is valid


@pytest.mark.parametrize('mode,reason', [('ok',None),('empty','expected_tools_missing'),
    ('init-error','protocol_error'),('partial','timeout'),('closed','server_closed')])
def test_real_stdio_lifecycle_and_negative_cases(tmp_path,mode,reason):
    script=tmp_path/'fixture.py'
    script.write_text('''import json,sys,time
mode=sys.argv[1]
for line in sys.stdin:
 m=json.loads(line)
 if mode=='closed': sys.exit(0)
 if mode=='partial': sys.stdout.write('{');sys.stdout.flush();time.sleep(10)
 if 'id' not in m: continue
 if mode=='init-error': result={'error':{'code':-32603,'message':'fixture secret must not be emitted'}}
 elif m['method']=='initialize': result={'result':{'protocolVersion':'2025-06-18','capabilities':{'tools':{}},'serverInfo':{'name':'fixture','version':'1'}}}
 else: result={'result':{'tools':[] if mode=='empty' else [{'name':'expected','inputSchema':{'type':'object'}}]}}
 print(json.dumps({'jsonrpc':'2.0','id':m['id'],**result}),flush=True)
''')
    started=time.monotonic()
    result=module.probe.discover([sys.executable,str(script),mode],{},str(tmp_path),timeout=.8,expected=['expected'])
    assert time.monotonic()-started<4
    assert result['status']==('failed' if reason else 'verified')
    if reason: assert result['reason']==reason
    assert 'secret' not in json.dumps(result)


def ollama_config():
    return {'agents':{'defaults':{'model':{'primary':'ollama/network-model:latest'}}},
            'models':{'providers':{'ollama':{'baseUrl':'http://fixture.invalid:11434/v1','apiKey':'${OLLAMA_API_KEY}'}}}}


def test_remote_ollama_uses_configured_endpoint_without_cli():
    calls=[]
    def request(url,headers,body=None):
        calls.append((url,headers,body))
        return {'models':[{'name':'network-model:latest'}]} if url.endswith('/tags') else {'capabilities':['tools','completion']}
    result=module.ollama_readiness(ollama_config(),{'OLLAMA_API_KEY':'fixture-private'},True,request)
    assert result=={'status':'verified','reason':'ollama_model_available','tool_calling':'advertised_not_exercised'}
    assert calls[0][0]=='http://fixture.invalid:11434/api/tags'
    assert calls[1][2]=={'model':'network-model:latest'}
    assert 'fixture-private' not in json.dumps(result)


@pytest.mark.parametrize('outcome,reason',[('missing','ollama_model_missing'),('no-tools','ollama_model_has_no_tool_capability'),
                                         ('offline','ollama_endpoint_or_api_unavailable')])
def test_provider_errors_are_not_ready(outcome,reason):
    def request(url,*_):
        if outcome=='offline': raise OSError('secret URL/password in upstream exception')
        if url.endswith('/tags'): return {'models':[] if outcome=='missing' else [{'name':'network-model:latest'}]}
        return {'capabilities':['completion']}
    result=module.ollama_readiness(ollama_config(),{'OLLAMA_API_KEY':'fixture'},True,request)
    assert result['status']=='failed'
    assert result['reason']==reason
    assert 'secret' not in json.dumps(result)


def test_provider_check_is_opt_in_and_does_not_download():
    result=module.ollama_readiness(ollama_config(),{},False,lambda *_:pytest.fail('unexpected request'))
    assert result['status']=='unverified'


def test_failed_install_and_missing_registration_cannot_be_success(tmp_path):
    result=module.report(['netbox','pyats'],{'netbox'},{},{},{'NETCLAW_RUNTIME_ROOT':str(tmp_path)},tmp_path/'cfg','openclaw')
    assert not result['ok']
    assert [r['status'] for r in result['components']]==['failed','failed']


def test_artifacts_do_not_claim_discovery_or_endpoint_readiness(tmp_path):
    result=module.check_server('fixture',{'command':sys.executable,'args':[], 'cwd':str(tmp_path)},
        'fixture',{}, {},tmp_path/'cfg','openclaw',False,1)
    assert result['artifacts']=='verified'
    assert result['discovery']['status']=='unverified'
    assert result['endpoint']=='unverified'


def test_missing_credentials_are_configuration_required_without_launch(tmp_path,monkeypatch):
    monkeypatch.setattr(module.launcher,'resolve',lambda *a,**k: ([],{},str(tmp_path)))
    monkeypatch.setattr(module,'native_probe',lambda *a,**k: pytest.fail('must not launch'))
    result=module.check_server('netbox-mcp',{'command':sys.executable},'netbox',module.launcher.CONTRACT['netbox'],
        {},tmp_path/'cfg','openclaw',True,1)
    assert result['discovery']['status']=='configuration_required'
    assert result['discovery']['variables']==['NETBOX_URL','NETBOX_TOKEN']


def test_zero_exit_probe_with_empty_catalog_fails_cli(tmp_path):
    bin_dir=tmp_path/'bin';bin_dir.mkdir()
    cli=bin_dir/'openclaw'
    cli.write_text('#!/bin/sh\nprintf \'%s\\n\' \'{"servers":{"bgp-intel-mcp":{"tools":0}},"tools":[]}\'\n')
    cli.chmod(0o700)
    config=tmp_path/'config.json'
    config.write_text(json.dumps({'mcp':{'servers':{'bgp-intel-mcp':{'command':sys.executable}}}}))
    out=tmp_path/'readiness.json'
    env={'PATH':str(bin_dir)+os.pathsep+os.defpath,'HOME':str(tmp_path)}
    result=subprocess.run([sys.executable,str(ROOT/'scripts/installer-readiness.py'), '--runtime-root',str(tmp_path/'runtimes'),
        '--config',str(config),'--components','bgp-intel','--output',str(out),'--probe'],env=env,capture_output=True,text=True)
    assert result.returncode==1,result.stdout+result.stderr
    report=json.loads(out.read_text())
    assert report['components'][0]['status']=='failed'
    assert out.stat().st_mode & 0o777 == 0o600
