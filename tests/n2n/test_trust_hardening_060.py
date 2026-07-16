"""Trust-hardening tests for claw certification US5 (059 Security Considerations).

Covers FR-022 (per-source failed-auth rate limiting so an attacker cannot unpin a
legitimate member) and FR-023 (enrollment fingerprint surfaced for out-of-band
confirmation).
"""

import pytest

from bgp.federation.risk import RiskManager, STATE_QUARANTINED
from bgp.federation import certs


@pytest.fixture
def border(manager):
    rm = RiskManager(manager)
    rm.set_role("border", risk_name="johns-risk")
    return rm


def _enroll(rm, member_id="johns-risk/pyats"):
    raw = rm.issue_token(label="t")["token"]
    cert_pem, _ = certs.create_self_signed(member_id)
    res = rm.consume_token(raw, member_id, cert_pem,
                           scope=["self-status"], runtime_kind="process")
    return member_id, cert_pem, res


# ---- FR-022: quarantine-DoS resistance ------------------------------------

def test_foreign_source_failures_do_not_quarantine(border):
    member_id, _, _ = _enroll(border)
    # An attacker at a different source sprays failing auths well past threshold.
    for _ in range(50):
        triggered = border.record_auth_failure(
            member_id, source="203.0.113.9:44321",
            established_source="10.0.0.5:51000")
        assert triggered is False
    assert not border.is_quarantined(member_id)
    m = border.get_member(member_id)
    assert (m["auth_failures"] or 0) == 0  # member counter untouched


def test_genuine_member_origin_still_quarantines(border):
    member_id, _, _ = _enroll(border)
    # Failures from the member's OWN established origin still count (key gone bad).
    triggered = False
    for _ in range(border.quarantine_threshold):
        triggered = border.record_auth_failure(
            member_id, source="10.0.0.5:51000",
            established_source="10.0.0.5:51000")
    assert triggered is True
    assert border.is_quarantined(member_id)


def test_legacy_callers_without_source_unchanged(border):
    member_id, _, _ = _enroll(border)
    for _ in range(border.quarantine_threshold):
        border.record_auth_failure(member_id)  # old signature
    assert border.is_quarantined(member_id)


def test_source_rate_limit_budget(border):
    # Within budget returns True, then False once the bucket is exhausted.
    results = [border.note_source_failure("198.51.100.7:5000", limit=5)
               for _ in range(8)]
    assert results[:5] == [True] * 5
    assert results[5:] == [False] * 3


# ---- FR-023: enrollment fingerprint surfaced ------------------------------

def test_enrollment_surfaces_and_logs_fingerprint(border):
    member_id, cert_pem, res = _enroll(border)
    # The returned fingerprint equals the member cert's — the value both sides
    # confirm out of band; a mismatch would reveal an intercepted enrollment.
    assert res["enroll_fingerprint"] == certs.key_fingerprint(cert_pem)
    m = border.get_member(member_id)
    assert m["enroll_fingerprint_logged"] == 1
