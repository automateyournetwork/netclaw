"""Domain-separated HA proofs. Callers validate exact typed payloads separately."""
import base64
import hashlib
import re

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from ..protected_contract import encode, exact, key_id
from .config import HAError, check

KINDS = {'hello', 'admission', 'member-result', 'forward', 'attachment-border', 'attachment-member', 'dispatch'}
MAX_PROOF = 65536


def message(kind, payload):
    check(kind in KINDS, 'invalid_proof_kind')
    raw = encode(payload)
    check(len(raw) <= MAX_PROOF, 'proof_capacity')
    return b'netclaw.ncfed.ha/' + kind.encode() + b'/v1\0' + raw


def sign(kind, payload, private_key):
    key = serialization.load_pem_private_key(private_key.encode(), password=None)
    check(isinstance(key, ec.EllipticCurvePrivateKey) and isinstance(key.curve, ec.SECP256R1))
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    raw = key.sign(message(kind, payload), ec.ECDSA(hashes.SHA256()))
    return {'kind': kind, 'payload': payload, 'key_id': hashlib.sha256(public).hexdigest(),
            'signature': base64.urlsafe_b64encode(raw).rstrip(b'=').decode()}


def verify(proof, certificate, kind):
    try:
        exact(proof, 'kind payload key_id signature')
        check(proof['kind'] == kind and proof['key_id'] == key_id(certificate), 'proof_key_mismatch', 403)
        check(isinstance(proof['signature'], str) and re.fullmatch('[A-Za-z0-9_-]{8,200}', proof['signature']))
        raw = base64.urlsafe_b64decode(proof['signature'] + '=' * (-len(proof['signature']) % 4))
        check(base64.urlsafe_b64encode(raw).rstrip(b'=').decode() == proof['signature'])
        public = x509.load_pem_x509_certificate(certificate.encode()).public_key()
        check(isinstance(public, ec.EllipticCurvePublicKey) and isinstance(public.curve, ec.SECP256R1))
        public.verify(raw, message(kind, proof['payload']), ec.ECDSA(hashes.SHA256()))
        return proof['payload']
    except Exception:
        raise HAError('invalid_ha_proof', 403) from None
