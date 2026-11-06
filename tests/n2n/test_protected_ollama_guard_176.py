"""Keyless native DefenseClaw admission; no synthetic success claims for the binary."""
import hashlib
import sys
import pytest
import yaml
from protected_support_171 import file_module, SOURCE

sys.path.insert(0, str(SOURCE/'scripts/lib'))
from protected_provider import ProviderRefused
local = file_module('r05_guard_config', SOURCE/'scripts/lib/protected_ollama.py')
guard = file_module('r05_guard_runner', SOURCE/'scripts/protected-guard.py')


def configuration(home):
    llm = {'model':'ollama/qwen3:0.6b','forward_custom_headers':False}
    return {'config_version':9,'deployment_mode':'server','data_dir':str(home),'llm':llm.copy(),
        'gateway':{'api_bind':'127.0.0.1','api_port':18970},
        'guardrail':{'enabled':True,'mode':'action','scanner_mode':'local','connector':'openclaw',
            'host':'0.0.0.0','port':4000,'rule_pack':'strict','hook_fail_mode':'closed',
            'detection_strategy':'regex_only','allow_unknown_llm_domains':False,'allow_empty_providers':False,
            'model':llm['model'],'model_name':'qwen3:0.6b','llm':llm.copy(),
            'hilt':{'enabled':False},'judge':{'enabled':False}}}


def save(home, cfg):
    raw=yaml.safe_dump(cfg).encode();path=home/'config.yaml';path.write_bytes(raw);path.chmod(0o600)
    return hashlib.sha256(raw).hexdigest()


def test_native_route_has_no_hosted_key_or_dummy_sentinel(tmp_path):
    digest=save(tmp_path,configuration(tmp_path));assert local.verify_config(tmp_path,digest)==digest
    path=tmp_path/'guard.env';path.write_text('DEFENSECLAW_GATEWAY_TOKEN=fixture-private-guard-capability\n');path.chmod(0o600)
    secrets=guard.load_guard_env(tmp_path,local=True);env=guard.child_environment(tmp_path,secrets)
    assert not any('KEY' in key for key in env)
    assert set(secrets)=={'DEFENSECLAW_GATEWAY_TOKEN'}
    with pytest.raises(ProviderRefused):guard.load_guard_env(tmp_path)
    path.write_text(path.read_text()+'ANTHROPIC_API_KEY=fixture-not-real\n')
    with pytest.raises(ProviderRefused):guard.load_guard_env(tmp_path,local=True)


@pytest.mark.parametrize('mutate',[
    lambda c:c['llm'].update(api_key_env='DUMMY_KEY'),
    lambda c:c['llm'].update(base_url='http://127.0.0.1:11434'),
    lambda c:c['guardrail'].update(allow_private_upstreams=True),
    lambda c:c['guardrail'].update(mode='monitor'),
    lambda c:c['guardrail'].update(hook_fail_mode='open'),
    lambda c:c['guardrail'].update(detection_strategy_completion='llm'),
    lambda c:c['guardrail'].update(judge_sweep=True),
    lambda c:c['guardrail'].update(profiles={'anything':{}}),
    lambda c:c['guardrail']['judge'].update(enabled=True),
    lambda c:c['gateway'].update(api_bind='0.0.0.0'),
    lambda c:c.update(routing={'enabled':True}),
    lambda c:c.update(cisco_ai_defense={'enabled':True}),
])
def test_hash_pinning_does_not_admit_an_unsafe_reviewed_config(tmp_path,mutate):
    cfg=configuration(tmp_path);mutate(cfg)
    with pytest.raises(ProviderRefused):local.verify_config(tmp_path,save(tmp_path,cfg))


def test_yaml_duplicates_aliases_and_changed_pin_fail(tmp_path):
    digest=save(tmp_path,configuration(tmp_path));path=tmp_path/'config.yaml'
    with pytest.raises(ProviderRefused):local.verify_config(tmp_path,'0'*64)
    for addition in ('\nconfig_version: 9\n','\nx: &alias {y: true}\nz: *alias\n'):
        raw=yaml.safe_dump(configuration(tmp_path)).encode()+addition.encode();path.write_bytes(raw)
        with pytest.raises(ProviderRefused):local.verify_config(tmp_path,hashlib.sha256(raw).hexdigest())
