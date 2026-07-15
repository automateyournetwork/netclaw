"""iN2N offboarding + auto-quarantine (feature 056, US5).

Covers FR-013c/d and SC-010.
"""

import pytest

from bgp.federation.risk import (
    RiskManager, STATE_REMOVED, STATE_QUARANTINED, STATE_ENROLLED,
)


@pytest.fixture
def border(manager):
    rm = RiskManager(manager, quarantine_threshold=3)
    rm.set_role("border", risk_name="risk", enabled_stacks="in2n",
                border_endpoint="10.0.0.1:1179")
    return rm


def _enroll(border, name="risk/cml"):
    tok = border.issue_token()["token"]
    cert, _ = RiskManager._generate_self_signed(name)
    border.consume_token(tok, name, cert)
    return cert, RiskManager.fingerprint_of(cert)


def test_remove_unpins_and_refuses_reconnect(border):
    _cert, fp = _enroll(border)
    assert border.verify_member("risk/cml", fp) is True
    assert border.remove_member("risk/cml") is True
    mem = border.get_member("risk/cml")
    assert mem["state"] == STATE_REMOVED and mem["pinned_key"] is None
    # reconnect on the old key is refused (SC-010)
    assert border.verify_member("risk/cml", fp) is False
    # removed member is not listed
    assert all(m["member_id"] != "risk/cml" for m in border.list_members())


def test_reenroll_after_removal(border):
    _cert, _fp = _enroll(border)
    border.remove_member("risk/cml")
    # a NEW token + key re-enrolls the same member_id
    tok = border.issue_token()["token"]
    cert2, fp2 = RiskManager._generate_self_signed("risk/cml"), None
    cert2_pem = cert2[0]
    res = border.consume_token(tok, "risk/cml", cert2_pem)
    assert res["state"] == STATE_ENROLLED
    assert border.verify_member("risk/cml", RiskManager.fingerprint_of(cert2_pem)) is True


def test_auto_quarantine_at_threshold(border):
    _cert, fp = _enroll(border)
    # threshold is 3
    assert border.record_auth_failure("risk/cml") is False   # 1
    assert border.record_auth_failure("risk/cml") is False   # 2
    assert border.record_auth_failure("risk/cml") is True    # 3 → quarantine
    mem = border.get_member("risk/cml")
    assert mem["state"] == STATE_QUARANTINED and mem["pinned_key"] is None
    assert border.is_quarantined("risk/cml")
    # a quarantined member cannot reconnect on its old key
    assert border.verify_member("risk/cml", fp) is False
