import json
import pytest
from bgp.federation.runtime import selected, project_harness, read_private


def test_descriptor_identity_shared_with_hud_and_federation_is_separate(tmp_path):
    config = tmp_path/'config/netclaw'
    config.mkdir(parents=True)
    home = tmp_path/'Hermes Home'
    home.mkdir()
    descriptor = config/'runtime.json'
    descriptor.write_text(json.dumps({'schemaVersion':1,'kind':'hermes','home':str(home)}))
    descriptor.chmod(0o600)
    env = {'HOME':str(tmp_path), 'XDG_CONFIG_HOME':str(tmp_path/'config')}
    assert selected(env).installation is None
    runtime = selected(env, initialize=True).fence(initialize=True)
    assert runtime.installation == read_private(home/'netclaw-hud/installation.json')['installationId']
    assert selected(env).installation == runtime.installation
    assert runtime.state != home/'netclaw-hud'
    assert 'OPENCLAW_HOME' not in runtime.environment({'OPENCLAW_HOME':'/wrong'})
    assert runtime.skills == home/'skills'


def test_identity_and_symlinks_fail_closed(tmp_path):
    home = tmp_path/'hermes'
    home.mkdir()
    env = {'HOME':str(tmp_path), 'NETCLAW_RUNTIME':'hermes','HERMES_HOME':str(home)}
    runtime = selected(env,initialize=True).fence(initialize=True)
    (runtime.state/'owner.json').write_text('{}')
    with pytest.raises(ValueError,match='owner_invalid'):runtime.fence()
    link = tmp_path/'link'
    link.symlink_to(home)
    with pytest.raises(ValueError):selected({**env,'HERMES_HOME':str(link)})


@pytest.mark.parametrize('card',[None,{},'hermes',{'type':'<script>'},{'type':'x'*65}])
def test_legacy_and_hostile_harness_are_unknown(card):
    assert project_harness(card)['type'] == 'unknown'


def test_unknown_harness_is_display_only_and_provenance_not_trusted():
    result = project_harness({'type':'future-agent','version':'1.2','source':'verified','installationId':'private'})
    assert result['status'] == 'unrecognized'
    assert result['source'] == 'peer-advertised'
    assert 'installationId' not in result
    assert project_harness({'type':'hermes','version':'bad\nversion'})['version'] is None
