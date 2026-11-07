import copy
import hashlib

import pytest

from bgp.federation import protected_contract as c
from bgp.federation.ha.config import HAError
from bgp.federation.ha.factory import load_configuration
from bgp.federation.protected_service import validate_profile


def profile(role='border'):
    binding = {'installation_id': 'installation', 'identity': 'risk/border', 'key_id': 'a'*64, 'authority_generation': 'generation'}
    value = {'schemaVersion': 2, 'role': role, 'identity': binding,
             'access': {'mode': 'open-lab'}, 'ha': {'config_file': '/private/cluster.json', 'config_sha256': 'b'*64}}
    return value


def test_explicit_profile_version_and_ha_reference_are_required():
    value = profile()
    assert validate_profile(value) == value
    for mutate in (lambda p: p.update(schemaVersion=1), lambda p: p.pop('ha'),
                   lambda p: p['ha'].update(password='secret'), lambda p: p['ha'].update(config_file='relative.json')):
        changed = copy.deepcopy(value); mutate(changed)
        with pytest.raises(c.ProtectedError): validate_profile(changed)


def test_private_config_hash_mismatch_fails_before_dependency_construction(tmp_path):
    path = tmp_path/'configuration.json'; path.write_bytes(b'{}'); path.chmod(0o600)
    with pytest.raises(HAError, match='ha_configuration_changed'):
        load_configuration({'config_file': str(path), 'config_sha256': '0'*64}, role='border')
