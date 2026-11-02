"""Protected Border posture and role checks do not invent local guard evidence."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import asyncio
import copy
import json

import pytest

from bgp.federation import posture, controls, gait
from bgp.federation.protected_owner import OwnerAuthority, write_private
from bgp.federation.protected_service import validate_profile
from bgp.federation.protected_contract import ProtectedError
import uuid

def border_identity():
    return {"installation_id": str(uuid.uuid4()), "identity": "r03-fixture/border",
            "key_id": "a" * 64, "authority_generation": "generation-1"}


def test_border_profile_cannot_ignore_executor_or_credentials():
    identity = border_identity()
    base = {'schemaVersion': 1, 'role': 'border', 'identity': identity}
    assert validate_profile(base) == base
    for key in ('runtime', 'catalog', 'border', 'provider_key'):
        with pytest.raises(ProtectedError): validate_profile(dict(base, **{key: {}}))
    with pytest.raises(ProtectedError): validate_profile(dict(base, schemaVersion=True))


@pytest.fixture
def control_only(tmp_path, monkeypatch):
    identity = border_identity()
    state = tmp_path / 'state'; state.mkdir(mode=0o700)
    cfg = {'schemaVersion': 1, 'role': 'border', 'identity': identity}
    write_private(state / 'protected-profile.json', json.dumps(cfg).encode())
    owner = OwnerAuthority(state, identity['installation_id']); owner.init('Test owner')
    server = SimpleNamespace(is_serving=lambda: True)
    entries = [{'service': 'in2n', 'direction': 'listen', 'bind_host': '10.172.0.2'},
               {'service': 'en2n', 'direction': 'listen', 'bind_host': '127.0.0.1'}]
    service = SimpleNamespace(protected_enabled=True, risk=SimpleNamespace(is_border=lambda: True, list_members=lambda: []),
        runtime=SimpleNamespace(state=state), execution_broker=None, hermes_runtime=None,
        protected_operations=SimpleNamespace(role='border', executor=None, identity=identity, config=cfg,
            owner=owner, bridge=SimpleNamespace(server=server)), cert_enforce=True,
        manager=SimpleNamespace(base_dir=tmp_path), transport_registry=lambda: SimpleNamespace(load=lambda: {'entries': entries}),
        endpoint_status=lambda: {'services': [{'listener_ready': True}, {'listener_ready': True}]})
    monkeypatch.setattr(controls, 'is_production', lambda: True)
    monkeypatch.setattr(controls, 'strict_all', lambda: True)
    monkeypatch.setattr(gait, 'ensure_repo', lambda directory: (True, 'fixture'))
    # These probes would contact local guard/sandbox services; protected control-
    # only posture must not run them or claim their enforcement.
    sandbox = AsyncMock(side_effect=AssertionError('must not probe sandbox'))
    guard = AsyncMock(side_effect=AssertionError('must not probe model guard'))
    monkeypatch.setattr(controls, 'sandbox_available', sandbox)
    monkeypatch.setattr(controls, 'defenseclaw_available', guard)
    return service, sandbox, guard


def test_control_only_explicit_not_applicable_and_owner_transport_required(control_only):
    service, sandbox, guard = control_only
    result = asyncio.run(posture.compute_posture(service))
    assert result['state'] == 'enforced' and result['missing'] == []
    assert result['model'] == {'primary': None, 'guarded': False, 'execution': 'control-only'}
    rows = {r['name']: r for r in result['controls']}
    assert rows['model-guard']['applicability'] == 'not-applicable'
    assert rows['sandbox']['applicability'] == 'not-applicable'
    assert rows['owner-authority']['available'] and rows['strict-transport']['available']
    sandbox.assert_not_called(); guard.assert_not_called()


@pytest.mark.parametrize('change', ['executor', 'profile', 'owner', 'transport', 'local-member'])
def test_control_only_missing_boundaries_are_degraded(control_only, change):
    service, _, _ = control_only
    if change == 'executor': service.protected_operations.executor = object()
    if change == 'profile':
        config = copy.deepcopy(service.protected_operations.config); config['runtime'] = {}
        write_private(service.runtime.state / 'protected-profile.json', json.dumps(config).encode())
    if change == 'owner': service.protected_operations.bridge.server = None
    if change == 'transport': service.cert_enforce = False
    if change == 'local-member': service.risk.list_members = lambda: [{'launch_cmd': 'never'}]
    result = asyncio.run(posture.compute_posture(service))
    assert result['state'] == 'degraded' and result['missing']
    assert not posture.posture_ok_for_delegation(result)['allow']


def test_audit_failure_stays_visible_and_strict(control_only, monkeypatch):
    service, _, _ = control_only
    monkeypatch.setattr(gait, 'ensure_repo', lambda directory: (False, 'unavailable'))
    result = asyncio.run(posture.compute_posture(service))
    assert result['missing'] == ['audit'] and not posture.posture_ok_for_delegation(result)['allow']


def test_missing_opt_in_never_reopens_legacy_runtime(tmp_path, manager, monkeypatch):
    from bgp.federation import runtime
    from bgp.federation.service import FederationService
    state = tmp_path / 'selected-state'; state.mkdir(mode=0o700)
    write_private(state / 'protected-profile.json', b'{}')
    monkeypatch.delenv('N2N_PROTECTED_OPERATIONS', raising=False)
    monkeypatch.setattr(runtime, 'selected', lambda **kw: SimpleNamespace(state=state))
    with pytest.raises(ValueError, match='protected profile requires'):
        FederationService(local_as=65003, router_id='10.172.0.2', manager=manager)


@pytest.mark.parametrize("drift", ["unparseable", "runtime", "border"])
def test_member_factory_validates_startup_and_latches_unparseable_reread(tmp_path, manager, monkeypatch, drift):
    from bgp.federation import protected_runtime
    from bgp.federation.protected_service import from_service
    from bgp.federation.protected_contract import key_id
    from protected_support_171 import identity as signer, approval
    border, member = signer('border'), signer('member')
    payload = approval(border, member)
    binding = payload['member']
    state = tmp_path / 'member-state'; state.mkdir(mode=0o700)
    keys = tmp_path / 'keys'; keys.mkdir(mode=0o700)
    write_private(keys / 'self.key', member['key_pem'].encode())
    catalog = {'member': binding, 'model_profiles': [payload['model_profile']],
               'tools': [dict(payload['tool_call'], limits={k: v for k, v in payload['limits'].items() if k != 'expires_at_ms'})]}
    config = {'schemaVersion': 1, 'role': 'member', 'identity': binding, 'catalog': catalog,
              'runtime': {'fixture': True}, 'border': payload['border']}
    file = state / 'protected-profile.json'; write_private(file, json.dumps(config).encode())
    class Probe:
        def __init__(self): self.calls = []; self.invalid = False
        def validate_catalog(self, value, *, runtime_config):
            if runtime_config != config['runtime'] or value != catalog: self.invalid = True
            if self.invalid: raise ProtectedError('runtime_configuration_changed')
            self.calls.append((copy.deepcopy(value), copy.deepcopy(runtime_config)))
        def invalidate(self): self.invalid = True
        def close(self): pass
    executor = Probe()
    monkeypatch.setattr(protected_runtime, 'build_executor', lambda *a, **kw: executor)
    risk = SimpleNamespace(is_border=lambda: False, self_cert_pem=lambda: member['cert_pem'], keys_dir=keys,
                           protected_enrollment=lambda: binding)
    service = SimpleNamespace(runtime=SimpleNamespace(installation=binding['installation_id'], state=state),
        risk=risk, manager=manager, audit=SimpleNamespace(protected=lambda *a, **kw: 'fixture'), member_channels={}, border_channel=None)
    op = from_service(service)
    assert len(executor.calls) == 1
    assert asyncio.run(op.catalog_provider()) == catalog and len(executor.calls) == 2
    if drift == 'unparseable':
        write_private(file, b'{')
        with pytest.raises(Exception): asyncio.run(op.catalog_provider())
    else:
        changed = copy.deepcopy(config)
        if drift == 'runtime': changed['runtime']['fixture'] = False
        else: changed['border']['authority_generation'] = 'unexpected-generation'
        write_private(file, json.dumps(changed).encode())
        # This is the final trust reread used after remote effect authorization.
        with pytest.raises(ProtectedError): op.trust_resolver(binding)
    assert executor.invalid
    write_private(file, json.dumps(config).encode())
    with pytest.raises(ProtectedError, match='runtime_configuration_changed'): asyncio.run(op.catalog_provider())
    asyncio.run(op.close())
