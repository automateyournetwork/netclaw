"""Explicit no-auth lab attribution and historical authority preservation."""
import asyncio
import copy
import uuid
import pytest
from protected_support_171 import OperationPair, module
from test_protected_failure_recovery_174 import failed_pair


def select_lab(pair):
    pair.border.owner = module('protected_access').OpenLabAccess(pair.border.identity['installation_id'])
    pair.auth = {'access_mode': 'open-lab', 'installation_id': pair.border.identity['installation_id']}
    # No owner session, ticket, authority DB or cookie may be consulted.
    pair.owner.authorize = lambda *_: pytest.fail('owner authority must not be used')
    return pair.border.owner.principal


def test_lab_principal_is_stable_installation_scoped_and_exact():
    access = module('protected_access')
    identity = '00000000-0000-4000-8000-000000000174'
    principal = access.lab_principal(identity)
    assert principal == access.lab_principal(identity)
    assert principal['subject'] == str(uuid.uuid5(uuid.UUID(identity), 'netclaw.open-lab.operator'))
    assert principal['subject'] != access.lab_principal(str(uuid.uuid4()))['subject']
    with access.OpenLabAccess(identity).authorize({'access_mode': 'open-lab', 'installation_id': identity}) as result:
        assert result == principal
    for context in ({}, {'access_mode': 'open-lab'}, {'access_mode': 'open-lab', 'installation_id': str(uuid.uuid4())}, {'principal': principal}):
        with pytest.raises(module('protected_contract').ProtectedError):
            with access.OpenLabAccess(identity).authorize(context):
                pytest.fail('invalid context authorized')


def test_lab_review_approval_result_ack_and_recovery_do_not_use_owner_sessions(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        principal = select_lab(pair)
        prepared = await pair.prepare()
        assert prepared['review']['principal'] == principal
        await pair.decide(prepared)
        await pair.drain()
        first = await pair.reconcile(prepared['operation_id'])
        assert first['state'] == 'completed' and first['result']['durable_ack']
        assert first['result']['evidence']['principal'] == principal
        for _ in range(3):
            assert (await pair.reconcile(prepared['operation_id']))['result'] == first['result']
        assert pair.executor_calls == len(pair.effects) == 1
        assert [m for m, _ in pair.transport_calls].count('execution/submit') == 1
        for _, record in pair.audit_events:
            assert record['principal'] == principal
    asyncio.run(run())


def test_historical_failed_read_reconciles_original_principal_and_ack_without_new_effect(tmp_path, monkeypatch):
    async def run():
        pair = await failed_pair(tmp_path, monkeypatch)
        old = copy.deepcopy(pair.original)
        principal = select_lab(pair)
        status = await pair.border.status({'auth_context': pair.auth, 'client_nonce': 'fixture-request'})
        assert status['review']['principal'] == old['review']['principal'] != principal
        assert status['allowed_actions'] == ['reconcile']
        with pytest.raises(module('protected_contract').ProtectedError, match='operation_not_found'):
            await pair.decide(status)
        with pytest.raises(module('protected_contract').ProtectedError, match='operation_not_found'):
            await pair.border.revoke({'auth_context': pair.auth, 'operation_id': pair.operation})
        # Reusing a retained pre-cutover nonce recovers; it cannot issue a new review.
        assert (await pair.prepare())['operation_id'] == pair.operation
        result = await pair.reconcile(pair.operation)
        assert result['state'] == 'failed' and result['result']['durable_ack']
        assert result['result']['evidence']['principal'] == old['review']['principal']
        row = pair.member.store.get('member', pair.operation)
        for key in ('review', 'approval', 'approval_digest', 'attempt_id', 'effect_authorization', 'trust_snapshot'):
            assert row[key] == old[key]
        assert row['receipt']['payload']['error_code'] == 'native_netbox_http_403'
        assert pair.executor_calls == len(pair.effects) == 1
        assert (await pair.reconcile(pair.operation))['result'] == result['result']
        assert pair.executor_calls == len(pair.effects) == 1
    asyncio.run(run())


def test_historical_pending_review_cannot_be_reapproved_or_reattributed(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        old = await pair.prepare()
        select_lab(pair)
        recovered = await pair.prepare()
        assert recovered['operation_id'] == old['operation_id']
        assert recovered['review'] == old['review']
        assert recovered['allowed_actions'] == ['reconcile']
        for decision in ('approve', 'deny'):
            with pytest.raises(module('protected_contract').ProtectedError):
                await pair.decide(old, decision)
        assert pair.executor_calls == 0
        new = await pair.prepare(nonce='new-explicit-lab-review')
        assert new['review']['principal'] == pair.border.owner.principal
    asyncio.run(run())


def test_wrong_installation_history_and_ambiguous_nonce_are_refused(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        old = await pair.prepare()
        select_lab(pair)
        pair.border.identity = dict(pair.border.identity, installation_id=str(uuid.uuid4()))
        with pytest.raises(module('protected_contract').ProtectedError):
            await pair.border.status({'auth_context': pair.auth, 'operation_id': old['operation_id']})
        pair.border.identity = pair.template['border']
        row = pair.border.store.get('border', old['operation_id'])
        pair.border.store.create('border', str(uuid.uuid4()), owner_subject=str(uuid.uuid4()),
            review=row['review'], review_digest=row['review_digest'], trust_snapshot=row['trust_snapshot'],
            client_nonce=row['client_nonce'], candidate_digest=row['candidate_digest'])
        with pytest.raises(module('protected_contract').ProtectedError, match='client_nonce_conflict'):
            await pair.prepare()
        assert pair.executor_calls == 0
    asyncio.run(run())


def test_private_profile_opt_in_and_lab_binding_validation(tmp_path):
    pair = OperationPair(tmp_path)
    service, contract = module('protected_service'), module('protected_contract')
    profile = {'schemaVersion': 1, 'role': 'border', 'identity': pair.template['border']}
    assert service.validate_profile(profile) == profile
    assert service.validate_profile(dict(profile, access={'mode': 'open-lab'}))['access']['mode'] == 'open-lab'
    for access in (None, {}, {'mode': 'owner'}, {'mode': 'open-lab', 'principal': {}}, {'mode': True}):
        with pytest.raises(contract.ProtectedError):
            service.validate_profile(dict(profile, access=access))
    review = {k: copy.deepcopy(v) for k, v in pair.template.items() if k in 'principal border member model_profile tool_call limits change_request_ref'.split()}
    review['principal'] = module('protected_access').lab_principal(profile['identity']['installation_id'])
    contract.validate_review(review)
    review['principal']['subject'] = str(uuid.uuid4())
    with pytest.raises(contract.ProtectedError, match='lab_principal_mismatch'):
        contract.validate_review(review)


def test_factory_uses_no_owner_database_for_explicit_lab(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    pair = OperationPair(tmp_path)
    svc = module('protected_service')
    state = tmp_path / 'fresh-lab-state'; state.mkdir(mode=0o700)
    identity = pair.template['border']
    cfg = {'schemaVersion': 1, 'role': 'border', 'identity': identity, 'access': {'mode': 'open-lab'}}
    svc.write_private(state / 'protected-profile.json', json.dumps(cfg).encode())
    svc.write_private(state / 'protected-operator.env', ('NETCLAW_PROTECTED_OPERATOR_TOKEN=' + 'x' * 43).encode())
    monkeypatch.setattr(svc, 'OwnerAuthority', lambda *_: pytest.fail('owner DB was initialized'))
    risk = SimpleNamespace(is_border=lambda: True,
        hub_credential=lambda: (pair.border_signer['cert_pem'], pair.border_signer['key_pem']),
        get_risk=lambda: {'risk_name': identity['identity'].removesuffix('/border')}, list_members=lambda: [])
    service = SimpleNamespace(runtime=SimpleNamespace(installation=identity['installation_id'], state=state),
        risk=risk, manager=pair.managers['border'], audit=SimpleNamespace(protected=lambda *a, **kw: 'fixture'),
        member_channels={}, border_channel=None)
    op = svc.from_service(service)
    assert op.open_lab and op.owner.principal == module('protected_access').lab_principal(identity['installation_id'])
    assert sorted(p.name for p in state.iterdir()) == ['protected-operator.env', 'protected-profile.json']
    assert asyncio.run(op.catalog({'auth_context': {'access_mode': 'open-lab', 'installation_id': identity['installation_id']}}))['members'] == []
    asyncio.run(op.close())


from test_protected_border_172 import control_only

def test_lab_posture_is_truthful_and_never_probes_owner_database(control_only):
    import json
    service, sandbox, guard = control_only
    op = service.protected_operations
    op.config['access'] = {'mode': 'open-lab'}
    module('protected_owner').write_private(service.runtime.state / 'protected-profile.json', json.dumps(op.config).encode())
    op.owner = module('protected_access').OpenLabAccess(op.identity['installation_id'])
    result = asyncio.run(module('posture').compute_posture(service))
    assert result['state'] == 'enforced' and result['missing'] == []
    controls = {row['name']: row for row in result['controls']}
    assert 'owner-authority' not in controls
    assert controls['lab-attribution']['available']
    assert 'unauthenticated' in controls['lab-attribution']['detail']
    op.bridge.server = None
    assert asyncio.run(module('posture').compute_posture(service))['state'] == 'degraded'
    sandbox.assert_not_called(); guard.assert_not_called()


def test_colliding_legacy_subject_is_still_historical_not_a_lab_approval(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        lab = module('protected_access').lab_principal(pair.border.identity['installation_id'])
        pair.owner = module('protected_owner').OwnerAuthority(tmp_path / 'collision-owner', pair.border.identity['installation_id'], clock_ms=lambda: pair.now)
        pair.owner.init('Legacy owner with explicit UUID', subject=lab['subject'])
        pair.border.owner = pair.owner
        pair.auth = pair.login()
        old = await pair.prepare()
        assert old['review']['principal']['subject'] == lab['subject']
        select_lab(pair)
        status = await pair.border.status({'auth_context': pair.auth, 'operation_id': old['operation_id']})
        assert status['allowed_actions'] == ['reconcile']
        assert status['review']['principal']['issuer'] == 'local'
        for decision in ('approve', 'deny'):
            with pytest.raises(module('protected_contract').ProtectedError):
                await pair.decide(status, decision)
        with pytest.raises(module('protected_contract').ProtectedError):
            await pair.border.revoke({'auth_context': pair.auth, 'operation_id': old['operation_id']})
        assert pair.executor_calls == 0
    asyncio.run(run())


from test_protected_role_172 import selected, role, write

@pytest.mark.parametrize('access,valid', [({'mode': 'open-lab'}, True), ({'mode': 'owner'}, False), ({'mode': 'open-lab', 'principal': {}}, False)])
def test_role_profile_pin_binds_explicit_access_without_credentials(selected, access, valid):
    import json
    from pathlib import Path
    file, cfg = selected
    profile = Path(cfg['home']) / 'netclaw-federation/protected-profile.json'
    data = json.loads(profile.read_bytes()); data['access'] = access
    cfg['profile_sha256'] = write(profile, data); write(file, cfg)
    if valid:
        result, env = role.validate(file)
        assert result == cfg and not any('AUTH' in key or 'COOKIE' in key for key in env)
    else:
        with pytest.raises(role.RoleRefused): role.validate(file)
