"""Owned lifecycle boundaries; no Docker daemon/model/network qualification."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import pytest
from protected_support_171 import file_module,SOURCE

q=file_module('r05_model_qualification',SOURCE/'labs/ollama/qualify.py')


def arguments(tmp_path,family=4):
    return SimpleNamespace(family=family,image='sha256:'+'a'*64,name='netclaw-r05-fixture',
        model_store=str(tmp_path/'models'),state_dir=str(tmp_path/'new-state'),
        guard_uid=os.getuid(),model_uid=21006,docker='/fixture/docker',docker_host='unix:///fixture/docker.sock')


@pytest.mark.parametrize('family',[4,6])
def test_create_plan_has_exact_resources_no_model_port_and_no_credentials(tmp_path,family):
    profile=q.selected_profile(arguments(tmp_path,family));q.model.validate_profile(profile)
    args=q.create_model_args(profile,'netclaw-r05-owned-net')
    assert args[args.index('--memory')+1]==args[args.index('--memory-swap')+1]=='2048m'
    assert args[args.index('--cpus')+1]==('2' if family==4 else '1')
    assert '--publish' not in args and '--publish-all' not in args
    assert args[args.index('--entrypoint')+1]=='/usr/local/bin/ollama' and args[-1]=='serve'
    env=[args[index+1] for index,value in enumerate(args) if value=='--env']
    assert set(env)=={key+'='+value for key,value in q.model.model_environment(profile).items()}
    assert not any('API_KEY' in item or 'Tailscale' in item or 'thermidor' in item for item in args)
    assert 'type=bind,src='+profile['model_store']+',dst=/models,readonly' in args


def test_nft_plan_has_no_broad_model_loopback_or_external_allow():
    rules=q.nft_rules(501,21006)
    assert rules.count('policy drop;')==2
    assert 'meta skuid 501 tcp dport { 4000, 4001, 11434, 18970 } accept' in rules
    assert 'meta skuid 21006 tcp dport 32768-65535 tcp dport != { 4000, 4001, 11434, 18970, 49171 } accept' in rules
    assert 'meta skuid 21006 accept' not in rules
    assert 'flush ruleset' not in rules and 'table inet netclaw_r05' in rules


@pytest.mark.parametrize('guard,model',[(0,1),(1,0),(1,1),(True,2),('1',2),(-1,2),(1,2**31)])
def test_invalid_uid_cannot_generate_policy(guard,model):
    with pytest.raises(q.QualificationRefused):q.nft_rules(guard,model)


def inspection():
    return {'Id':'b'*64,'Image':'sha256:'+'a'*64,'Name':'/netclaw-r05-fixture',
        'Config':{'Labels':{'netclaw.spec':'176'}},'State':{'Running':True}}


@pytest.mark.parametrize('change',[lambda c:c.update(Id='c'*64),lambda c:c.update(Image='sha256:'+'d'*64),
    lambda c:c.update(Name='/existing-owner-runtime'),lambda c:c['Config']['Labels'].update({'netclaw.spec':'173'})])
def test_stop_never_adopts_other_objects(change):
    data=inspection();change(data)
    with pytest.raises(q.QualificationRefused):q.owned_container(data,'sha256:'+'a'*64,'netclaw-r05-fixture','b'*64)


def test_prepare_verifies_public_model_bytes_before_creating_state_or_docker(tmp_path,monkeypatch):
    args=arguments(tmp_path);calls=[]
    def bad_store(profile):calls.append('verify');raise q.QualificationRefused('fixture_wrong_bytes')
    monkeypatch.setattr(q.model,'verify_store',bad_store)
    monkeypatch.setattr(q,'Docker',lambda *_args,**_kwargs:calls.append('docker'))
    with pytest.raises(q.QualificationRefused):q.prepare(args)
    assert calls==['verify'] and not Path(args.state_dir).exists()


def test_lost_container_reply_keeps_named_unknown_receipt_and_never_probes(tmp_path,monkeypatch):
    args=arguments(tmp_path);calls=[]
    monkeypatch.setattr(q.model,'verify_store',lambda _:None)
    class Docker:
        def __init__(self,*_,**__):pass
        def call(self,*argv,**kwargs):
            calls.append(argv)
            if argv[:2]==('network','create'):return ('c'*64+'\n').encode()
            raise q.QualificationRefused('docker_outcome_unknown')
    monkeypatch.setattr(q,'Docker',Docker)
    with pytest.raises(q.QualificationRefused):q.prepare(args)
    receipt=json.loads((Path(args.state_dir)/'owned.json').read_bytes())
    assert receipt['state']=='failed_or_unknown' and receipt['network_id']=='c'*64 and receipt['model_id'] is None
    assert len(calls)==2 and calls[1][0]=='create' and not (Path(args.state_dir)/'confinement.json').exists()


def test_stop_requires_actual_stopped_state_preserves_unknown(tmp_path,monkeypatch):
    args=arguments(tmp_path);state=Path(args.state_dir);state.mkdir(mode=0o700)
    q.write(state/'owned.json',{'schema_version':1,'image':'sha256:'+'a'*64,'model_name':'netclaw-r05-fixture',
        'model_id':'b'*64,'network_id':'c'*64,'probe_name':'netclaw-r05-fixture-peer','probe_id':None})
    calls=[]
    class Docker:
        def __init__(self,*_,**__):pass
        def inspect(self,_):return inspection()
        def call(self,*argv,**kwargs):calls.append(argv);return b''
    monkeypatch.setattr(q,'Docker',Docker)
    with pytest.raises(q.QualificationRefused,match='stop_unknown'):q.stop(args)
    assert calls==[('stop','--time','8','b'*64)] and not (state/'stop-receipt.json').exists()


def test_qualification_cli_is_stdlib_and_does_not_start_at_help():
    result=subprocess.run([sys.executable,'-S',str(SOURCE/'labs/ollama/qualify.py'),'--help'],capture_output=True,check=False)
    assert result.returncode==0 and b'prepare' in result.stdout and b'no public deployment' not in result.stderr
