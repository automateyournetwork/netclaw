"""iN2N enrollment: single-use token + self-signed key pinned TOFU (feature 056).

Covers FR-013a/b and SC-010. See contracts/in2n-enrollment.md.
"""

import time

import pytest

from bgp.federation.risk import RiskManager, STATE_ENROLLED, STATE_ACTIVE


@pytest.fixture
def border(manager):
    rm = RiskManager(manager, quarantine_threshold=5)
    rm.set_role("border", risk_name="johns-risk", enabled_stacks="in2n",
                border_endpoint="10.0.0.1:1179")
    return rm


def _member_cert():
    """A fresh member self-signed cert (as a member would generate at runtime)."""
    cert_pem, _key_pem = RiskManager._generate_self_signed("johns-risk/cml")
    return cert_pem


def test_token_single_use_and_pin(border):
    tok = border.issue_token(label="cml")["token"]
    cert = _member_cert()
    res = border.consume_token(tok, "johns-risk/cml", cert,
                               scope=[{"name": "cml-lab-lifecycle", "tier": "specialty"}])
    assert res["pinned"] and res["state"] == STATE_ENROLLED
    mem = border.get_member("johns-risk/cml")
    assert mem["key_fingerprint"] == RiskManager.fingerprint_of(cert)
    # Re-presenting the SAME token is rejected (single-use, SC-010).
    with pytest.raises(ValueError, match="TOKEN_INVALID"):
        border.consume_token(tok, "johns-risk/cml", cert)


def test_unknown_token_rejected(border):
    with pytest.raises(ValueError, match="TOKEN_INVALID"):
        border.consume_token("in2n_bogus", "johns-risk/x", _member_cert())


def test_expired_token_rejected(border):
    tok = border.issue_token(label="cml", ttl_seconds=-1)["token"]  # already expired
    with pytest.raises(ValueError, match="TOKEN_INVALID"):
        border.consume_token(tok, "johns-risk/cml", _member_cert())


def test_reconnect_pinned_vs_nonpinned_key(border):
    tok = border.issue_token()["token"]
    cert = _member_cert()
    border.consume_token(tok, "johns-risk/cml", cert)
    fp = RiskManager.fingerprint_of(cert)
    # correct pinned key → authenticated, marked active
    assert border.verify_member("johns-risk/cml", fp) is True
    assert border.get_member("johns-risk/cml")["state"] == STATE_ACTIVE
    # a different (non-pinned) key → refused
    other_fp = RiskManager.fingerprint_of(_member_cert())
    assert border.verify_member("johns-risk/cml", other_fp) is False


def test_member_id_taken_by_different_key(border):
    t1 = border.issue_token()["token"]
    t2 = border.issue_token()["token"]
    border.consume_token(t1, "johns-risk/cml", _member_cert())
    with pytest.raises(ValueError, match="MEMBER_ID_TAKEN"):
        border.consume_token(t2, "johns-risk/cml", _member_cert())  # different cert


def test_enroll_requires_border(manager):
    rm = RiskManager(manager)
    rm.set_role("member", risk_name="r", border_endpoint="127.0.0.1:9")
    with pytest.raises(ValueError, match="NOT_A_BORDER"):
        rm.consume_token("in2n_x", "r/cml", _member_cert())
