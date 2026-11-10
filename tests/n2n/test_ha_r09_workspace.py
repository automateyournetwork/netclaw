"""R09 workspace tooling: schema parity with the product remote-hud.js, private files, no secrets, pack contents."""
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from labs.ha import r09_workspace as ws  # noqa: E402

INSTALLATION = '11111111-2222-4333-8444-555555555555'
NODE = shutil.which('node')


def base(tmp_path, **over):
    args = dict(installation_id=INSTALLATION, conversation_home=str(tmp_path / 'ws'), upstream_port=3001,
                border_home=str(tmp_path / 'border'), ingress_port=443)
    args.update(over)
    return args


def test_features_mirror_the_product_list():
    source = (REPO / 'ui/netclaw-visual/src/hud-server/remote-hud.js').read_text()
    listed = re.search(r"REMOTE_HUD_FEATURES = Object\.freeze\(\[(.*?)\]\)", source, re.S).group(1)
    assert [x.strip().strip("'") for x in listed.split(',')] == list(ws.FEATURES)
    assert set(ws.DEFAULT_FEATURES) <= set(ws.FEATURES)
    assert 'rag' not in ws.DEFAULT_FEATURES  # needs rag-mcp (torch/chroma); not installed on e2-medium Borders


@pytest.mark.parametrize('features', [[], ['chat', 'chat'], ['unknown'], ['canvas'], ['canvas', 'overview']])
def test_feature_validation_matches_remote_hud(tmp_path, features):
    with pytest.raises(ws.WorkspaceRefused, match='invalid_workspace_features'):
        ws.workspace_config(**base(tmp_path, features=features))


def test_config_shape_is_exact_and_canonical(tmp_path):
    config = ws.workspace_config(**base(tmp_path))
    assert set(config) == {'schemaVersion', 'installationId', 'upstream', 'conversationHome', 'conversationConfig', 'features'}
    assert config['upstream'] == 'http://127.0.0.1:3001'
    assert config['conversationConfig'] == config['conversationHome'] + '/openclaw.json'
    raw = ws.canonical(config)
    assert raw == json.dumps(config, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


@pytest.mark.parametrize('over,code', [
    ({'installation_id': 'nope'}, 'invalid_installation_id'),
    ({'conversation_home': 'relative'}, 'invalid_conversation_home'),
    ({'conversation_home': '/a/../b'}, 'invalid_conversation_home'),
    ({'upstream_port': 443}, 'workspace_loop'),
    ({'upstream_port': 80}, 'workspace_loop'),
])
def test_refusals(tmp_path, over, code):
    with pytest.raises(ws.WorkspaceRefused, match=code):
        ws.workspace_config(**base(tmp_path, **over))


def test_conversation_home_must_be_separate_from_the_border_home(tmp_path):
    same = str(tmp_path / 'border')
    for home in (same, same + '/ws', str(tmp_path)):
        with pytest.raises(ws.WorkspaceRefused, match='invalid_conversation_root'):
            ws.workspace_config(**base(tmp_path, conversation_home=home))


def render_to(tmp_path, **extra):
    out = tmp_path / 'out'
    argv = ['render', '--installation-id', INSTALLATION, '--border-home', str(tmp_path / 'border'),
            '--conversation-home', str(tmp_path / 'ws'), '--out-dir', str(out), *extra]
    assert ws.main(argv) == 0
    return out


def test_render_writes_identical_private_copies_and_no_secrets(tmp_path):
    out = render_to(tmp_path)
    edge, backend = (out / 'workspace.edge.json').read_bytes(), (out / 'workspace.backend.json').read_bytes()
    assert edge == backend
    for path in [out / 'workspace.edge.json', out / 'workspace.backend.json', out / 'conversation-home/openclaw.json',
                 out / 'summary.json']:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    text = '\n'.join(p.read_text() for p in out.rglob('*') if p.is_file())
    assert 'sk-ant' not in text and 'ANTHROPIC_API_KEY=' not in text
    oc = json.loads((out / 'conversation-home/openclaw.json').read_text())
    assert oc['gateway']['auth']['token'] == '${OPENCLAW_GATEWAY_TOKEN}'
    assert oc['gateway']['bind'] == 'loopback'
    assert oc['agents']['defaults']['workspace'] == str(tmp_path / 'ws') + '/workspace'
    summary = json.loads((out / 'summary.json').read_text())
    assert summary['workspace_sha256'] == ws.sha256(edge)
    assert ws.main(['render', '--installation-id', INSTALLATION, '--border-home', str(tmp_path / 'border'),
                    '--conversation-home', str(tmp_path / 'ws'), '--out-dir', str(out)]) == 1  # fresh directory only


@pytest.mark.skipif(NODE is None, reason='node required')
def test_product_edge_and_backend_readers_accept_the_rendered_config(tmp_path):
    border = tmp_path / 'border'
    (border / 'netclaw-federation').mkdir(parents=True, mode=0o700)
    (tmp_path / 'ws').mkdir(mode=0o700)
    profile = border / 'netclaw-federation/protected-profile.json'
    profile.write_text(json.dumps({'schemaVersion': 2, 'role': 'border', 'identity': {'installation_id': INSTALLATION},
                                   'access': {'mode': 'open-lab'}}))
    os.chmod(profile, 0o600)
    out = render_to(tmp_path)
    shutil.copy(out / 'conversation-home/openclaw.json', tmp_path / 'ws/openclaw.json')
    os.chmod(tmp_path / 'ws/openclaw.json', 0o600)
    sha = ws.sha256((out / 'workspace.edge.json').read_bytes())
    script = r'''
import {readRemoteHudConfig,resolveRemoteHudBackend} from %r;
const [edge,backend,border,sha]=process.argv.slice(1);
const installation=Object.freeze({home:border,kind:'openclaw',installationId:%r});
const e=readRemoteHudConfig(edge,installation,sha);
const b=resolveRemoteHudBackend(backend);
console.log(JSON.stringify({edge:e.features,backend:b.workspace.features,home:b.installation.home}));
''' % ((REPO / 'ui/netclaw-visual/src/hud-server/remote-hud.js').as_uri(), INSTALLATION)
    result = subprocess.run([NODE, '--input-type=module', '-e', script, str(out / 'workspace.edge.json'),
                             str(out / 'workspace.backend.json'), str(border), sha], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    seen = json.loads(result.stdout)
    assert seen['edge'] == seen['backend'] == list(ws.DEFAULT_FEATURES)
    assert seen['home'] == str(tmp_path / 'ws')
    # a tampered edge copy fails the product's pin
    tampered = out / 'workspace.edge.json'
    os.chmod(tampered, 0o600)
    tampered.write_bytes(tampered.read_bytes().replace(b'3001', b'3002'))
    bad = subprocess.run([NODE, '--input-type=module', '-e', script, str(tampered), str(out / 'workspace.backend.json'),
                          str(border), sha], capture_output=True, text=True)
    assert bad.returncode != 0 and 'workspace_config_changed' in bad.stderr


def test_pack_contains_backend_source_and_excludes_tests(tmp_path):
    dist = REPO / 'ui/netclaw-visual/dist/index.html'
    if not dist.exists():
        pytest.skip('built dist required')
    target = tmp_path / 'backend.tar'
    assert ws.main(['pack', '--out', str(target)]) == 0
    with tarfile.open(target) as archive:
        names = set(archive.getnames())
        owners = {(m.uid, m.gid, m.uname) for m in archive.getmembers()}
    assert 'ui/netclaw-visual/server.js' in names and 'SOUL.md' in names and 'IDENTITY.md' in names
    assert 'ui/netclaw-visual/dist/index.html' in names and 'scripts/mcp-call.py' in names
    assert not any(n.startswith(('ui/netclaw-visual/test/', 'ui/netclaw-visual/node_modules/')) for n in names)
    assert owners == {(0, 0, 'root')}
    assert ws.main(['pack', '--out', str(target)]) == 1  # an existing output is never overwritten
