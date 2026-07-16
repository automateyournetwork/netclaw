"""Foundational unit tests for claw certification (feature 060).

Covers the certs.py X.509 engine and the schema-migration v3 additive changes.
Uses the shared conftest path setup (mcp-servers/protocol-mcp on sys.path).
"""

import datetime

import pytest

from bgp.federation import certs
from bgp import constants


# ---- certs.py primitives (T008) -------------------------------------------

def test_self_signed_roundtrip_and_fingerprint_stable():
    cert_pem, key_pem = certs.create_self_signed("netclaw-claw")
    assert "BEGIN CERTIFICATE" in cert_pem
    assert "BEGIN PRIVATE KEY" in key_pem
    fp1 = certs.fingerprint(cert_pem)
    fp2 = certs.fingerprint(cert_pem)
    assert fp1 == fp2 and len(fp1) == 64  # SHA-256 hex


def test_domain_cert_carries_dns_san():
    cert_pem, _ = certs.create_self_signed("netclaw.automateyournetwork.ca")
    assert "netclaw.automateyournetwork.ca" in certs.san_names(cert_pem)


def test_internal_identity_uses_uri_san_not_dns():
    # a member id is not a hostname — it must not become a DNS SAN
    cert_pem, _ = certs.create_self_signed("johns-risk/pyats")
    assert "johns-risk/pyats" in certs.san_names(cert_pem)


def test_ca_issues_leaf_that_chains_and_verifies():
    ca_cert, ca_key = certs.create_risk_ca("johns-risk")
    leaf_cert, _ = certs.issue_cert(ca_cert, ca_key, "johns-risk/pyats",
                                    san="johns-risk/pyats")
    ok, reason = certs.verify_chain(leaf_cert, ca_cert, expected_san="johns-risk/pyats")
    assert ok, reason


def test_verify_rejects_wrong_ca():
    ca_cert, ca_key = certs.create_risk_ca("johns-risk")
    other_ca, _ = certs.create_risk_ca("someone-elses-risk")
    leaf_cert, _ = certs.issue_cert(ca_cert, ca_key, "johns-risk/pyats")
    ok, reason = certs.verify_chain(leaf_cert, other_ca)
    assert not ok and "not signed" in reason


def test_verify_rejects_san_mismatch():
    ca_cert, ca_key = certs.create_risk_ca("johns-risk")
    leaf_cert, _ = certs.issue_cert(ca_cert, ca_key, "johns-risk/pyats")
    ok, reason = certs.verify_chain(leaf_cert, ca_cert, expected_san="johns-risk/imposter")
    assert not ok and "SAN" in reason


def test_verify_rejects_expired_leaf_with_clock_hint():
    ca_cert, ca_key = certs.create_risk_ca("johns-risk")
    leaf_cert, _ = certs.issue_cert(ca_cert, ca_key, "johns-risk/pyats", days=1)
    future = datetime.datetime.utcnow() + datetime.timedelta(days=3)
    ok, reason = certs.verify_chain(leaf_cert, ca_cert, at=future)
    assert not ok and "clock" in reason.lower()


def test_renew_after_is_two_thirds_of_lifetime():
    nb = datetime.datetime(2026, 1, 1)
    na = nb + datetime.timedelta(days=90)
    ra = certs.renew_after(nb, na, fraction=constants.CERT_RENEW_FRACTION_DEFAULT)
    # ~60 days in (two-thirds of 90) → ~30 remaining
    assert 59 <= (ra - nb).days <= 61
    assert 29 <= (na - ra).days <= 31


def test_keys_dir_layout_and_perms(tmp_path):
    import os
    base = str(tmp_path / "n2n")
    kd = certs.keys_dir(base)
    for sub in ("host", "acme", "risk-ca", "members"):
        assert (kd / sub).is_dir()
    mode = os.stat(kd).st_mode & 0o777
    assert mode == 0o700


# ---- schema migration v3 (T006) -------------------------------------------

def test_migration_adds_060_columns_and_tables(manager):
    conn = manager._conn
    peer_cols = {r[1] for r in conn.execute("PRAGMA table_info(federation_peer)")}
    assert {"trust_model", "claw_domain", "pinned_fp", "pinned_fp_next",
            "peer_cred_fp", "verify_state"} <= peer_cols
    member_cols = {r[1] for r in conn.execute("PRAGMA table_info(member)")}
    assert {"credential_state", "cred_fp", "enroll_fingerprint_logged"} <= member_cols
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"credential", "rotation_event", "auth_failure_bucket"} <= tables


def test_existing_peers_backfill_to_legacy(manager):
    manager.upsert_peer(65007, "7.7.7.7", display_name="Nicholas")
    row = manager._conn.execute(
        "SELECT trust_model FROM federation_peer WHERE peer_as=65007").fetchone()
    assert row["trust_model"] == "legacy"


def test_migration_is_idempotent(fed_base):
    from bgp.federation.manager import FederationManager
    m1 = FederationManager(base_dir=fed_base)
    m1.upsert_peer(65099, "10.255.255.1")
    m1.close()
    # second open re-runs migration against the now-migrated DB
    m2 = FederationManager(base_dir=fed_base)
    cnt = m2._conn.execute("SELECT COUNT(*) FROM federation_peer").fetchone()[0]
    assert cnt == 1
    m2.close()


# ---- audit event kinds (T007) ---------------------------------------------

def test_cert_event_recorded_and_rejects_unknown_kind(manager):
    from bgp.federation.audit import Auditor
    a = Auditor(manager)
    rid = a.record_cert_event(kind="renewed",
                              subject_identity="netclaw.automateyournetwork.ca",
                              detail="lego renew ok")
    assert rid > 0
    assert a.recent_cert_events(10)[0]["kind"] == "renewed"
    with pytest.raises(ValueError):
        a.record_cert_event(kind="nonsense", subject_identity="x")
