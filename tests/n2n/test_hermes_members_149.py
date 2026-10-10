import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest
from bgp.federation.runtime import ROOT,selected


def script(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/name)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_hermes_member_provisioning_is_scoped_private_and_preserving(tmp_path,monkeypatch):
    home=tmp_path/'Border Home';home.mkdir(mode=0o700)
    monkeypatch.setenv('NETCLAW_RUNTIME','hermes');monkeypatch.setenv('HERMES_HOME',str(home));monkeypatch.setenv('XDG_CONFIG_HOME',str(tmp_path/'xdg'))
    config={'model':{'default':'fixture','provider':'custom'},'mcp_servers':{'subnet-calc-mcp':{'command':'python3','args':['subnet']},'n2n-mcp':{'command':'danger'},'pyats-mcp':{'command':'admin'}},'slack':{'token':'must-not-copy'}}
    (home/'config.yaml').write_text(json.dumps(config));(home/'.env').write_text('OPENAI_API_KEY=provider-fixture\nSLACK_BOT_TOKEN=private-border\nNETBOX_TOKEN=private-border\n')
    records=home/'python-runtimes/records';records.mkdir(parents=True)
    for name in ('hermes-hud','subnet-calc','n2n'):(records/name).write_text(sys.executable+'\n')
    runtime=selected(initialize=True);module=script('in2n-member-home.py')
    before=(home/'config.yaml').read_bytes()
    member=module.provision_hermes(runtime,'risk','subnet')
    scoped=json.loads((member/'config.yaml').read_text())
    assert set(scoped['mcp_servers'])=={'subnet-calc-mcp'} and 'slack' not in scoped
    assert not (member/'skills').is_symlink()
    assert [p.name for p in (member/'skills').iterdir()]==['subnet-calculator']
    assert 'private-border' not in (member/'.env').read_text()
    assert 'provider-fixture' in (member/'.env').read_text()
    assert (member/'.env').stat().st_mode&0o777==0o600
    with pytest.raises(ValueError,match='preserved'):module.provision_hermes(runtime,'risk','subnet')
    assert (home/'config.yaml').read_bytes()==before
    with pytest.raises(ValueError):module.provision_hermes(runtime,'risk','../escape')
    with pytest.raises(ValueError,match='only the subnet'):module.provision_hermes(runtime,'risk','pyats')


def test_member_launch_scrubs_border_environment_and_uses_literal_selected_values(tmp_path,monkeypatch):
    file=tmp_path/'.env';file.write_text('NETCLAW_RUNTIME=hermes\nHERMES_HOME="'+str(tmp_path)+'"\nOPENAI_API_KEY=member-key\nN2N_MEMBER_SCOPE=["subnet-calculator"]\n');file.chmod(0o600)
    monkeypatch.setenv('N2N_MEMBER_ENV_FILE',str(file));monkeypatch.setenv('OPENAI_API_KEY','border-key');monkeypatch.setenv('SLACK_BOT_TOKEN','border-secret');monkeypatch.setenv('NETCLAW_HERMES_FEDERATION_API_KEY','border-private')
    previous=dict(os.environ)
    try:
        script('in2n-member.py')._load_env_file()
        assert os.environ['OPENAI_API_KEY']=='member-key'
        assert os.environ['HERMES_HOME']==str(tmp_path)
        assert 'SLACK_BOT_TOKEN' not in os.environ and 'NETCLAW_HERMES_FEDERATION_API_KEY' not in os.environ
        assert json.loads(os.environ['N2N_MEMBER_SCOPE'])==['subnet-calculator']
    finally:os.environ.clear();os.environ.update(previous)


def test_custom_hermes_service_binds_selected_home_and_interpreter(tmp_path,monkeypatch):
    home=tmp_path/'Hermes custom';home.mkdir()
    monkeypatch.setenv('NETCLAW_RUNTIME','hermes');monkeypatch.setenv('HERMES_HOME',str(home));monkeypatch.setenv('XDG_CONFIG_HOME',str(tmp_path/'config'))
    records=home/'python-runtimes/records';records.mkdir(parents=True);(records/'n2n').write_text('/fixture/python312\n')
    module=script('in2n-services.py');module._full_sandbox_cache=False
    text=module._mesh_unit_text()
    assert '/fixture/python312' in text and str(home) in text and 'federation-control.py' in text
    assert '@' not in text
    assert module._mesh_name()!='netclaw-mesh.service'
    confinement=module._hardening_block(True)
    assert str(home/'.env') in confinement and str(home/'config.yaml') in confinement
    assert 'InaccessiblePaths=-%h/.openclaw/.env' not in confinement
