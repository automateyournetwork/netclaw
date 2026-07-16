"""US3 rotation: credentials past their renew_after are renewed automatically,
old ones retired, successors announced — no channel drop required. Uses the
credential registry + RotationManager directly (no 30-day waits)."""

import asyncio
import datetime

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager
from bgp.federation.rotation import RotationManager
from bgp.federation import certs

_UTC = datetime.timezone.utc


def _svc(base):
    return FederationService(local_as=65001, router_id="4.4.4.4", display_name="John",
                             manager=FederationManager(base_dir=str(base)))


def test_due_detection_and_renew(tmp_path):
    svc = _svc(tmp_path)
    rot = RotationManager(svc)
    # Register a host credential whose renew_after is already in the past.
    cert_pem, key_pem = certs.create_self_signed("as65001-4.4.4.4")
    cid = rot.register("host-pinned", "as65001-4.4.4.4", cert_pem, issuer="self")
    assert cid > 0
    # Force renew_after into the past so it's due now.
    svc.manager._conn.execute(
        "UPDATE credential SET renew_after=? WHERE credential_id=?",
        ("2000-01-01T00:00:00+00:00", cid))
    svc.manager._conn.commit()

    due = rot.due()
    assert any(c["subject_identity"] == "as65001-4.4.4.4" for c in due)

    renewed = asyncio.run(rot.run_once())
    assert renewed == 1
    # A fresh active credential exists and the old fingerprint is retired.
    active = [c for c in svc.manager.list_credentials() if c["kind"] == "host-pinned"]
    assert active and active[0]["state"] == "active"
    assert active[0]["fingerprint"] != certs.key_fingerprint(cert_pem)
    # Rotation was audited.
    kinds = [e["kind"] for e in svc.audit.recent_cert_events(10)]
    assert "renewed" in kinds
    svc.manager.close()


def test_renew_after_is_two_thirds(tmp_path):
    svc = _svc(tmp_path)
    rot = RotationManager(svc)
    cert_pem, _ = certs.create_self_signed("x", )  # 10y default → far future
    cid = rot.register("host-pinned", "x", cert_pem)
    row = [c for c in svc.manager.list_credentials() if c["credential_id"] == cid][0]
    nb = datetime.datetime.fromisoformat(row["not_before"])
    na = datetime.datetime.fromisoformat(row["not_after"])
    ra = datetime.datetime.fromisoformat(row["renew_after"])
    frac = (ra - nb) / (na - nb)
    assert 0.66 <= frac <= 0.67
    svc.manager.close()
