import copy
import uuid

import pytest

from bgp.federation import protected_contract as contract
from protected_support_171 import identity, approval


def ha_approval():
    border, member = identity('border'), identity('member')
    payload = approval(border, member)
    payload['cluster'] = {'cluster_id': str(uuid.uuid4()), 'generation': str(uuid.uuid4()),
        'manifest_revision': 1, 'issuer_node_id': str(uuid.uuid4()), 'authority_epoch': 9}
    payload['principal'] = {'issuer': 'open-lab', 'display_name': 'Unauthenticated lab operator',
        'roles': ['lab-operator'], 'subject': str(uuid.uuid5(uuid.UUID(payload['cluster']['cluster_id']),
                                                          'netclaw.open-lab.operator'))}
    payload['review_sha256'] = contract.sha256(contract.review_from_payload(payload))
    return border, member, payload


def test_explicit_v2_cluster_identity_and_domain_cannot_downgrade():
    border, _, payload = ha_approval()
    signed = contract.sign(contract.HA_APPROVAL, payload, border['key_pem'])
    assert contract.verify(signed, border['cert_pem'], contract.HA_APPROVAL) == payload
    with pytest.raises(contract.ProtectedError):
        contract.sign(contract.APPROVAL, payload, border['key_pem'])
    with pytest.raises(contract.ProtectedError):
        contract.verify(signed, border['cert_pem'], contract.APPROVAL)
    del payload['cluster']
    with pytest.raises(contract.ProtectedError):
        contract.sign(contract.HA_APPROVAL, payload, border['key_pem'])


@pytest.mark.parametrize('change', [
    lambda p: p['cluster'].update(authority_epoch=0),
    lambda p: p['cluster'].update(manifest_revision=True),
    lambda p: p['cluster'].update(generation='old'),
    lambda p: p['cluster'].update(issuer_node_id='border'),
    lambda p: p['principal'].update(subject=str(uuid.uuid4())),
    lambda p: p['cluster'].update(etcd_token='forbidden'),
])
def test_malformed_or_foreign_cluster_approval_refused(change):
    border, _, payload = ha_approval()
    change(payload)
    payload['review_sha256'] = contract.sha256(contract.review_from_payload(payload))
    with pytest.raises(contract.ProtectedError):
        contract.sign(contract.HA_APPROVAL, payload, border['key_pem'])
