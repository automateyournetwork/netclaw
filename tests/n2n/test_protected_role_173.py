"""R04 member launch is explicit; legacy Border contracts remain unmodified."""
import json
from pathlib import Path
import sqlite3

import pytest
from test_protected_role_172 import selected, role, write


@pytest.fixture
def member(selected):
    file, cfg = selected; home = Path(cfg['home'])
    profile_path = home / 'netclaw-federation/protected-profile.json'
    old = json.loads(profile_path.read_text()); border = old['identity']
    binding = dict(installation_id=cfg['installation_id'], member_id='r03-fixture/netbox',
                   key_id=border['key_id'], enrollment_generation='enrolled-1')
    profile = dict(schemaVersion=1, role='member', identity=binding, border=border,
                   catalog={}, runtime={})
    cfg['profile_sha256'] = write(profile_path, profile)
    write(home / 'n2n/keys/protected/enrollment.json', binding)
    registry_path = Path(cfg['registry']); registry = json.loads(registry_path.read_text())
    entry = registry['entries'][0]
    for key in ('bind_host', 'bind_port', 'cert_file', 'key_file'): entry.pop(key)
    entry['direction'] = 'dial'; registry['entries'] = [entry]
    cfg['registry_sha256'] = write(registry_path, registry)
    capability = home / 'netclaw-federation/guard-capability'; write(capability, b'g' * 43 + b'\n')
    cfg.update(schemaVersion=2, role='member', control_only=False, origin=None, guard_token_file=str(capability))
    with sqlite3.connect(home / 'n2n/federation.db') as db:
        db.execute("UPDATE risk SET role='member',self_member_id=? WHERE id=1", (binding['member_id'],))
    write(file, cfg)
    return file, cfg, profile


def test_member_only_guard_capability_reaches_clean_environment(member, monkeypatch):
    file, cfg, profile = member
    monkeypatch.setenv('NETBOX_TOKEN', 'never-in-daemon')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'never-in-daemon')
    _, env = role.validate(file)
    assert env['NETCLAW_R04_GUARD_TOKEN'] == 'g' * 43
    assert env['N2N_MEMBER_ID'] == profile['identity']['member_id']
    assert env['N2N_ROLE'] == 'member'
    assert env['N2N_BORDER_REGISTRY_ID'] == 'in2n'
    assert 'NETBOX_TOKEN' not in env and 'ANTHROPIC_API_KEY' not in env


@pytest.mark.parametrize('field,value', [('control_only', True), ('origin', 'https://unexpected.test'),
    ('runtime_kind', 'hermes'), ('environment', {'NETBOX_TOKEN': 'secret'}), ('schemaVersion', 1)])
def test_member_role_cannot_expand_authority(member, field, value):
    file, cfg, _ = member; cfg[field] = value; write(file, cfg)
    with pytest.raises(ValueError): role.validate(file)


def test_foreign_enrollment_refused(member):
    file, cfg, profile = member
    write(Path(cfg['home']) / 'n2n/keys/protected/enrollment.json', dict(profile['identity'], enrollment_generation='foreign'))
    with pytest.raises(role.RoleRefused, match='enrollment_mismatch'): role.validate(file)


def test_guard_file_foreign_path_and_permissions_refuse(member):
    file, cfg, _ = member
    token = Path(cfg['guard_token_file']); token.chmod(0o644)
    with pytest.raises(role.RoleRefused, match='private_file'): role.validate(file)
    token.chmod(0o600); cfg['guard_token_file'] = str(token.parent / 'other'); write(file, cfg)
    with pytest.raises(role.RoleRefused, match='guard_path'): role.validate(file)


def test_member_dial_target_bound_to_border_identity(member):
    file, cfg, profile = member
    profile['border']['identity'] = 'foreign/border'
    cfg['profile_sha256'] = write(Path(cfg['home']) / 'netclaw-federation/protected-profile.json', profile); write(file, cfg)
    with pytest.raises(role.RoleRefused, match='border_identity'): role.validate(file)
