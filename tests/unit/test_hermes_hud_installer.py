"""Populated-home preservation and recursive-registration rejection (no providers)."""
import json
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]

def test_select_and_repeat_preserves_populated_owner_files(tmp_path):
    home=tmp_path/'Hermes Home';home.mkdir(mode=0o700)
    original={'config.yaml':b'model: owner-model\ncustom: keep\n','.env':b'API_KEY=fixture-private\n','MEMORY.md':b'private memory','skills/local/SKILL.md':b'# Owner skill'}
    for name,body in original.items():
        file=home/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(body)
    env={k:v for k,v in os.environ.items() if k in ('PATH','LANG')};env['HOME']=str(tmp_path)
    command=['node',str(ROOT/'scripts/hud-launch.mjs')]
    ids=[]
    for _ in range(2):
        subprocess.run(command+['select','hermes',str(home)],env=env,cwd='/tmp',check=True,capture_output=True)
        status=subprocess.run(command+['status'],env=env,cwd='/tmp',check=True,capture_output=True,text=True)
        ids.append(json.loads(status.stdout)['installationId'])
    assert ids[0]==ids[1]
    assert all((home/name).read_bytes()==body for name,body in original.items())
    assert not (tmp_path/'.openclaw').exists()
    assert not (home/'state.db').exists()

def test_private_bridge_never_becomes_an_agent_registration(tmp_path):
    source=tmp_path/'source.json';source.write_text(json.dumps({'mcpServers':{'hermes-hud-mcp':{'command':'python3','args':['private-conversation.py']}}}))
    config=tmp_path/'config.yaml';config.write_text('model: owner-model\ncustom: keep\n')
    result=subprocess.run(['python3',str(ROOT/'scripts/openclaw-to-hermes-mcp.py'),'--source',str(source),'--repo',str(ROOT),'--config',str(config)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert 'hermes-hud' not in config.read_text()
    assert 'owner-model' in config.read_text() and 'custom: keep' in config.read_text()
    generated=tmp_path/'selected.json'
    result=subprocess.run(['python3',str(ROOT/'scripts/install-mcp-config.py'),'--repo',str(ROOT),'--runtime-root',str(tmp_path/'runtimes'),'--components','hermes-hud','--output',str(generated)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert 'hermes-hud' not in generated.read_text()
