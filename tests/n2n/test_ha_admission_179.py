import asyncio
import copy
import uuid

import pytest

from bgp.federation.ha.admission import MemberAdmission
from bgp.federation.ha.config import HAError, sign_manifest, verify_manifest
from bgp.federation.ha.signatures import sign
from bgp.federation import certs
from bgp.federation.protected_contract import key_id, sha256
from test_ha_contract_179 import manifest_fixture


def setup(tmp_path):
    value, root, root_key = manifest_fixture()
    node = value['nodes'][0]
    certificate, private_key = certs.create_self_signed(node['identity'])
    node.update(certificate=certificate, key_id=key_id(certificate))
    manifest = verify_manifest(sign_manifest(value, root_key), root, expected_key_id=key_id(root))
    member = {'installation_id': str(uuid.uuid4()), 'member_id': 'member-one',
              'key_id': 'a'*64, 'enrollment_generation': str(uuid.uuid4())}
    context = dict(operation_id=str(uuid.uuid4()), attempt_id=str(uuid.uuid4()), approval_digest='b'*64)
    clock = {'mono': 10., 'wall': 1000.}
    journal = MemberAdmission(tmp_path / 'private', manifest, member,
                              monotonic=lambda: clock['mono'], wall=lambda: clock['wall'])
    def response(request):
        claim = {'request': copy.deepcopy(request), 'member_sha256': sha256(member), 'state': 'committed',
                 'leader': {'node_id': node['node_id'], 'incarnation': str(uuid.uuid4()),
                            'generation': manifest.generation, 'election_nonce': 'd'*64}, 'epoch': 5}
        return sign('admission', {'claim': claim, 'commit_revision': 9}, private_key)
    return journal, manifest, member, context, clock, response


@pytest.mark.asyncio
async def test_consumption_durable_once_and_no_restart_replay(tmp_path):
    journal, manifest, member, context, clock, response = setup(tmp_path)
    effects = []
    async def send(request): return response(request)
    async def effect(): effects.append('model'); return 'result'
    assert await journal.run(context, 'model', 1, 'c'*64, send, effect) == 'result'
    with pytest.raises(HAError, match='admission_spent'):
        await journal.run(context, 'model', 1, 'c'*64, send, effect)
    restarted = MemberAdmission(tmp_path / 'private', manifest, member)
    with pytest.raises(HAError, match='admission_spent'):
        await restarted.run(context, 'model', 1, 'c'*64, send, effect)
    assert effects == ['model']


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['delay', 'wall_forward', 'wall_back', 'nonce', 'attempt', 'generation', 'issuer', 'lost_reply'])
async def test_bad_or_stale_admission_never_reaches_callback(tmp_path, fault):
    journal, manifest, member, context, clock, response = setup(tmp_path)
    effects = []
    async def send(request):
        if fault == 'delay': clock.update(mono=14., wall=1004.)
        if fault == 'wall_forward': clock['wall'] += 1.
        if fault == 'wall_back': clock['wall'] -= 1.
        if fault == 'lost_reply': raise ConnectionError('reply lost')
        request = copy.deepcopy(request)
        if fault == 'nonce': request['nonce'] = '0'*64
        if fault == 'attempt': request['attempt_id'] = str(uuid.uuid4())
        if fault == 'generation': request['generation'] = str(uuid.uuid4())
        result = response(request)
        if fault == 'issuer': result['key_id'] = 'f'*64
        return result
    async def effect(): effects.append('tool')
    with pytest.raises((HAError, ConnectionError)):
        await journal.run(context, 'tool', 1, 'c'*64, send, effect)
    assert effects == []
    with pytest.raises(HAError, match='admission_spent'):
        await journal.run(context, 'tool', 1, 'c'*64, send, effect)


@pytest.mark.asyncio
async def test_consumption_to_effect_pause_is_rechecked(tmp_path):
    journal, manifest, member, context, clock, response = setup(tmp_path)
    effects = []
    async def send(request): return response(request)
    async def effect(): effects.append('tool')
    original = journal.consume
    def paused(*args):
        original(*args)
        clock.update(mono=14., wall=1004.)
    journal.consume = paused
    with pytest.raises(HAError, match='admission_expired'):
        await journal.run(context, 'tool', 1, 'c'*64, send, effect)
    assert effects == []
