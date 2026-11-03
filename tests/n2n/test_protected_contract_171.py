"""Independent wire attacks for T010/T015; all keys and data are synthetic."""

import copy
import hashlib

import pytest

from protected_support_171 import APPROVAL, ACK, RESULT, approval, canonical, identity, module, sha, wire_sign


@pytest.fixture
def contract():
    return module("protected_contract")


@pytest.fixture
def signed_input():
    border, member = identity("border"), identity("member")
    payload = approval(border, member)
    return border, member, payload


def test_canonical_bytes_match_independent_utf8_reference(contract, signed_input):
    _, _, payload = signed_input
    actual = contract.canonical_bytes(APPROVAL, payload)
    expected = canonical({"schema": APPROVAL, "payload": payload})
    assert actual == expected
    assert "Montréal".encode() in actual
    assert b"\\u00e9" not in actual
    assert not actual.endswith(b"\n")
    assert contract.digest(APPROVAL, payload) == hashlib.sha256(expected).hexdigest()


def test_valid_independently_signed_approval_is_accepted(contract, signed_input):
    border, _, payload = signed_input
    assert contract.verify(wire_sign(APPROVAL, payload, border), border["cert_pem"]) == payload


def test_signatures_are_verifiable_without_production_signer(contract, signed_input):
    border, _, payload = signed_input
    envelope = contract.sign(APPROVAL, payload, border["key_pem"])
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    import base64
    signature = envelope["signature"]["value"]
    raw = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
    body = b"netclaw.r02/" + APPROVAL.encode() + b"\0" + canonical({"schema": APPROVAL, "payload": payload})
    border["key"].public_key().verify(raw, body, ec.ECDSA(hashes.SHA256()))
    assert envelope["signature"]["key_id"] == border["key_id"]
    assert "=" not in signature


@pytest.mark.parametrize("field", ["principal", "member", "model_profile", "tool_call", "limits"])
def test_change_to_any_authority_object_breaks_existing_signature(contract, signed_input, field):
    border, _, payload = signed_input
    envelope = wire_sign(APPROVAL, payload, border)
    key = next(iter(envelope["payload"][field]))
    envelope["payload"][field][key] = "attacker-substitution"
    with pytest.raises(contract.ProtectedError):
        contract.verify(envelope, border["cert_pem"])


def test_embedded_certificate_does_not_replace_pinned_signer(contract, signed_input):
    border, _, payload = signed_input
    attacker = identity("foreign-border")
    envelope = wire_sign(APPROVAL, payload, attacker)
    with pytest.raises(contract.ProtectedError):
        contract.verify(envelope, border["cert_pem"])
    envelope["certificate"] = attacker["cert_pem"]
    with pytest.raises(contract.ProtectedError):
        contract.verify(envelope, border["cert_pem"])


@pytest.mark.parametrize("schema", [RESULT, ACK, "netclaw.execution.approval.v2", "approval"])
def test_approval_signature_cannot_be_transplanted_to_other_domains(contract, signed_input, schema):
    border, _, payload = signed_input
    envelope = wire_sign(APPROVAL, payload, border)
    envelope["schema"] = schema
    with pytest.raises(contract.ProtectedError):
        contract.verify(envelope, border["cert_pem"])


@pytest.mark.parametrize("mutation", [
    lambda e: e.update(extra=True),
    lambda e: e["signature"].update(extra=True),
    lambda e: e["signature"].update(algorithm="none"),
    lambda e: e["signature"].update(key_id="f" * 64),
    lambda e: e["signature"].update(value=""),
    lambda e: e["signature"].update(value=e["signature"]["value"] + "="),
    lambda e: e["signature"].update(value="%%%"),
])
def test_envelope_and_signature_are_strict(contract, signed_input, mutation):
    border, _, payload = signed_input
    envelope = wire_sign(APPROVAL, payload, border)
    mutation(envelope)
    with pytest.raises(contract.ProtectedError):
        contract.verify(envelope, border["cert_pem"])


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(unrecognized=True),
    lambda p: p.update(issued_at_ms=True),
    lambda p: p.update(issued_at_ms=1.5),
    lambda p: p.update(issued_at_ms=-1),
    lambda p: p.update(change_request_ref="CHG-write-not-authorized"),
    lambda p: p["principal"].update(roles=["owner", "admin"]),
    lambda p: p["limits"].update(max_tool_calls=2),
    lambda p: p["limits"].update(max_inference_calls=3),
    lambda p: p["limits"].update(max_output_bytes=512 * 1024 + 1),
    lambda p: p["tool_call"].update(arguments_sha256="0" * 64),
    lambda p: p.update(review_sha256="0" * 64),
])
def test_correct_signature_does_not_authorize_invalid_schema(contract, signed_input, mutation):
    border, _, original = signed_input
    payload = copy.deepcopy(original)
    mutation(payload)
    if payload["review_sha256"] == original["review_sha256"]:
        payload["review_sha256"] = sha({key: payload[key] for key in (
            "principal", "border", "member", "model_profile", "tool_call", "limits", "change_request_ref")})
    with pytest.raises(contract.ProtectedError):
        contract.verify(wire_sign(APPROVAL, payload, border), border["cert_pem"])


def test_logical_hash_does_not_depend_on_ecdsa_signature_bytes(contract, signed_input):
    border, _, payload = signed_input
    one, two = wire_sign(APPROVAL, payload, border), wire_sign(APPROVAL, payload, border)
    assert contract.verify(one, border["cert_pem"]) == contract.verify(two, border["cert_pem"])
    assert contract.digest(one["schema"], one["payload"]) == contract.digest(two["schema"], two["payload"])


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
                                  b'{"x":-Infinity}', b'{"x":1.5}', b'{"x":"\\ud800"}'])
def test_wire_json_rejects_ambiguous_or_noncanonical_types(contract, raw):
    with pytest.raises(contract.ProtectedError):
        contract.decode(raw)
