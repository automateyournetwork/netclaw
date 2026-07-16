"""US6 T026: the patch upgrade preserves all federation state and is idempotent.

Simulates the patch installer's core: seed a pre-060 federation.db with peers,
members, consent, and grants; re-open the manager (which runs the additive v3
migration in place, exactly as the patch does); assert every row is preserved and
that re-running converges (idempotent)."""

from bgp.federation.manager import FederationManager
from bgp.federation.risk import RiskManager
from bgp.federation import certs


def _counts(m):
    c = m._conn
    return {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("federation_peer", "consent_record", "invocation_grant", "member")}


def test_patch_preserves_state_and_is_idempotent(tmp_path):
    base = str(tmp_path / "n2n")
    # Seed as a "pre-060" claw: peers + consent + grant + an enrolled member.
    m = FederationManager(base_dir=base)
    m.upsert_peer(65007, "7.7.7.7", display_name="Nicholas")
    m.local_consent(65007, "7.7.7.7"); m.remote_consent(65007, "7.7.7.7")
    m.upsert_peer(65099, "10.255.255.1", display_name="Byrn")
    from bgp.federation.authorization import Authorizer
    Authorizer(m).grant("as65007-7.7.7.7", "skill", "pyats-health-check")
    rm = RiskManager(m); rm.set_role("border", risk_name="johns-risk", enabled_stacks="in2n")
    tok = rm.issue_token(label="pyats")["token"]
    cert_pem, _ = certs.create_self_signed("johns-risk/pyats")
    rm.consume_token(tok, "johns-risk/pyats", cert_pem, scope=["self-status"])
    before = _counts(m)
    m.close()

    # Patch: re-open (runs migration v3) + generate credentials, as the installer does.
    m2 = FederationManager(base_dir=base)
    rm2 = RiskManager(m2); rm2.ensure_risk_ca(); rm2.hub_credential()
    after = _counts(m2)
    assert after == before, f"state changed: {before} -> {after}"
    # Existing peers/members backfilled to legacy trust, nothing dropped.
    assert m2.get_peer("as65007-7.7.7.7")["trust_model"] == "legacy"
    assert rm2.get_member("johns-risk/pyats")["credential_state"] == "legacy"
    m2.close()

    # Idempotent: a third open changes nothing.
    m3 = FederationManager(base_dir=base)
    assert _counts(m3) == before
    m3.close()
