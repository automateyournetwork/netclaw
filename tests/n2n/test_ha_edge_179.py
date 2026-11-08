"""Shared device identity never adopts a node-local or serialized principal."""
from types import SimpleNamespace
import asyncio
import hashlib
import uuid

import pytest

from bgp.federation.certs import create_self_signed
from bgp.federation.ha.config import HAError
from bgp.federation.ha.edge import ClusterEdgeRegistry, proof_bytes, REQUEST_PREFIX
from bgp.federation.protected_contract import encode
from bgp.federation.protected_device import ClusterDeviceAuthority
from bgp.federation.risk import RiskManager
from test_ha_authority_179 import cluster


def enrolled():
    store, nodes = cluster()
    nodes[0].campaign()
    clock = [1000]
    regs = [ClusterEdgeRegistry(n, clock_ms=lambda: clock[0]) for n in nodes]
    offer = regs[0].issue(nodes[0].node_id, str(uuid.uuid4()))
    cert, key = create_self_signed('mobile-device')
    ch = regs[0].challenge(nodes[0].node_id)
    params = dict(client_nonce=offer['client_nonce'], token=offer['enrollment_token'],
                  member_id='mobile-one', certificate=cert, challenge=ch,
                  signature=RiskManager.sign_challenge(key, proof_bytes(ch, 'mobile-one', 'enroll', offer['enrollment_token'])).hex())
    binding = regs[0].enroll(**params)
    return store, nodes, regs, clock, binding, key, params


def test_retained_key_fails_over_same_subject_and_proof_is_consumed():
    store, nodes, regs, _, binding, key, original = enrolled()
    store.revoke_lease('123')
    nodes[1].campaign()
    ch = regs[1].challenge(nodes[1].node_id)
    params = dict(member_id=binding['member_id'], key_fingerprint=binding['key_fingerprint'], challenge=ch,
                  signature=RiskManager.sign_challenge(key, proof_bytes(ch, binding['member_id'], 'hello')).hex())
    assert regs[1].hello(**params) == binding
    assert regs[2].binding(binding['member_id']) == binding
    with pytest.raises(HAError, match='device_challenge_spent'):
        regs[1].hello(**params)
    with pytest.raises(HAError):
        regs[1].enroll(**original)


def test_revocation_invalidates_other_node_channel_without_local_member_row():
    store, nodes, regs, _, binding, _, _ = enrolled()
    channel = SimpleNamespace(trusted=True, _closed=False, member_id=binding['member_id'], ha_binding=binding)
    operations = object()
    service = SimpleNamespace(protected_enabled=True, protected_operations=operations, ha_edge=regs[2],
                              edge_channels={binding['member_id']: channel})
    capability = ClusterDeviceAuthority(service, channel)
    assert capability.principal() == binding['principal']
    regs[0].revoke(binding['member_id'])
    with pytest.raises(HAError, match='device_authority_changed'):
        asyncio.run(capability.refresh())


def test_quorum_loss_and_foreign_proofs_fail_closed_without_mutation():
    store, nodes, regs, _, binding, key, _ = enrolled()
    ch = regs[0].challenge(nodes[2].node_id)
    args = dict(member_id=binding['member_id'], key_fingerprint=binding['key_fingerprint'], challenge=ch,
                signature=RiskManager.sign_challenge(key, proof_bytes(ch, binding['member_id'], 'hello')).hex())
    before = store.mutations
    forged = dict(ch, node_id=nodes[1].node_id)
    with pytest.raises(HAError, match='device_proof_invalid'):
        regs[0].hello(**dict(args, challenge=forged))
    assert store.mutations == before
    store.available = False
    with pytest.raises(HAError, match='no_quorum'):
        regs[2].binding(binding['member_id'])
    with pytest.raises(HAError, match='no_quorum'):
        regs[0].hello(**args)
    assert store.mutations == before


def test_expired_challenge_never_admits_and_offer_has_no_persisted_token():
    store, nodes, regs, clock, binding, key, _ = enrolled()
    ch = regs[0].challenge(nodes[1].node_id)
    clock[0] = ch['expires_at_ms']
    with pytest.raises(HAError, match='device_challenge_expired'):
        regs[0].hello(member_id=binding['member_id'], key_fingerprint=binding['key_fingerprint'], challenge=ch,
                      signature=RiskManager.sign_challenge(key, proof_bytes(ch, binding['member_id'], 'hello')).hex())
    assert 'in2n_' not in str(store.rows)


def test_lost_reply_cannot_create_a_second_enrollment_identity():
    store, nodes, regs, _, binding, key, _ = enrolled()
    ch = regs[0].challenge(nodes[1].node_id)
    before = store.mutations
    store.lose_reply = True
    result = regs[0].hello(member_id=binding['member_id'], key_fingerprint=binding['key_fingerprint'], challenge=ch,
                          signature=RiskManager.sign_challenge(key, proof_bytes(ch, binding['member_id'], 'hello')).hex())
    assert result == binding and store.mutations == before + 1


def test_signed_operation_proof_binds_exact_parameters_and_revocation_index():
    _, nodes, regs, _, binding, key, _ = enrolled()
    method = 'n2n/edge/operations/status'
    params = {'installation_id': nodes[1].manifest.node(nodes[1].node_id)['installation_id'],
              'operation_id': 'original-operation'}
    proof = {'schema_version': 1, 'cluster_id': binding['cluster_id'], 'generation': binding['generation'],
             'member_id': binding['member_id'], 'enrollment_generation': binding['enrollment_generation'],
             'request_id': str(uuid.uuid4()), 'method': method,
             'params_sha256': hashlib.sha256(encode(params)).hexdigest()}
    proof['signature'] = RiskManager.sign_challenge(key, REQUEST_PREFIX + encode(proof)).hex()
    verified = regs[2].verify_request(proof, method, params)
    assert verified.principal() == binding['principal']
    assert verified.key == 'edge-principals/' + binding['principal']['subject']
    with pytest.raises(HAError, match='device_proof_invalid'):
        regs[2].verify_request(proof, method, dict(params, operation_id='another'))
    regs[0].revoke(binding['member_id'])
    with pytest.raises(HAError, match='device_authority_changed'):
        regs[2].verify_request(proof, method, params)


def test_non_p256_possession_is_not_cluster_device_authority():
    import datetime
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    key = ec.generate_private_key(ec.SECP384R1())
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, 'wrong-curve')])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(1).not_valid_before(now - datetime.timedelta(minutes=1))
            .not_valid_after(now + datetime.timedelta(hours=1)).sign(key, hashes.SHA256())
            .public_bytes(serialization.Encoding.PEM).decode())
    challenge = {'nonce': 'a' * 64}
    signature = key.sign(proof_bytes(challenge, 'device', 'hello'), ec.ECDSA(hashes.SHA256())).hex()
    with pytest.raises(HAError, match='device_certificate_invalid'):
        ClusterEdgeRegistry._proof(cert, challenge, 'device', 'hello', signature)
