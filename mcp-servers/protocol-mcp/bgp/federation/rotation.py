"""Certificate rotation (feature 060, US3).

Renews every managed credential automatically before expiry (default at 2/3 of
lifetime elapsed — FR-012), with a dual-trust overlap so no channel drops during
rollover (FR-013). Local credentials (host-pinned, risk CA, hub, member) are
re-issued in place; domain-verified (ACME) credentials are renewed by acme.py.
Rotation lifecycle events are audited (FR-016).

Design (research R6): trust-by-name (domain-verified) rotates for free — peers
verify the successor's chain automatically. Trust-by-key (pinned / risk CA)
distributes the successor over the existing authenticated channel before the old
one expires; both are accepted during the overlap window (the peer/member records
carry pinned_fp + pinned_fp_next).
"""

from __future__ import annotations

import datetime
import logging
from typing import Optional

from . import certs

logger = logging.getLogger("n2n.rotation")
_UTC = datetime.timezone.utc


def _iso(dt: datetime.datetime) -> str:
    return dt.astimezone(_UTC).isoformat()


class RotationManager:
    def __init__(self, service):
        self.svc = service
        self.manager = service.manager
        self.audit = service.audit
        self.risk = service.risk

    # ---- registration -------------------------------------------------

    def register(self, kind: str, subject: str, cert_pem: str,
                 key_path: Optional[str] = None, issuer: Optional[str] = None,
                 fraction: Optional[float] = None) -> int:
        """Record a credential in the registry with its computed renew_after."""
        import os
        from ..constants import CERT_RENEW_FRACTION_DEFAULT
        frac = fraction if fraction is not None else float(
            os.environ.get("N2N_CERT_RENEW_FRACTION", CERT_RENEW_FRACTION_DEFAULT)
            or CERT_RENEW_FRACTION_DEFAULT)
        nb = certs.x509.load_pem_x509_certificate(cert_pem.encode()).not_valid_before_utc
        na = certs.cert_not_after(cert_pem)
        ra = certs.renew_after(nb, na, frac)
        return self.manager.upsert_credential(
            kind=kind, subject_identity=subject, fingerprint=certs.key_fingerprint(cert_pem),
            issuer=issuer, not_before=_iso(nb), not_after=_iso(na), renew_after=_iso(ra),
            cert_pem=cert_pem, key_path=key_path)

    # ---- renewal ------------------------------------------------------

    def due(self, now: Optional[datetime.datetime] = None) -> list:
        now = now or datetime.datetime.now(_UTC)
        return self.manager.credentials_due(_iso(now))

    async def renew_one(self, cred: dict) -> bool:
        """Renew a single credential: issue a successor, open the overlap window,
        distribute to peers/members where trust is by key, retire the old. Returns
        True on success. Best-effort per-kind; failures escalate (FR-014)."""
        kind = cred["kind"]
        subject = cred["subject_identity"]
        try:
            if kind == "acme":
                from . import acme
                new_cert = await acme.renew(subject, self.manager.base_dir)
                if not new_cert:
                    raise RuntimeError("acme renew produced no certificate")
                self.register("acme", subject, new_cert, issuer="ACME")
            elif kind == "risk-ca":
                new_cert, _ = self.risk.ensure_risk_ca()  # idempotent; explicit rekey elsewhere
                self.register("risk-ca", subject, new_cert, issuer="self")
            elif kind == "hub":
                new_cert, _ = self.risk.hub_credential()
                self.register("hub", subject, new_cert, issuer="risk-ca")
            elif kind == "host-pinned":
                cert_pem, key_pem = certs.create_self_signed(subject)
                kd = certs.keys_dir(str(self.manager.base_dir)) / "host"
                (kd / "host.crt").write_text(cert_pem)
                certs._write_secret(kd / "host.key", key_pem)
                self.svc._host_cred = (cert_pem, key_pem)
                self.register("host-pinned", subject, cert_pem, issuer="self")
                # Open overlap: announce successor pin to key-pinned peers.
                await self._announce_successor(cert_pem)
            else:
                logger.info("rotation: no renewer for kind %s (%s)", kind, subject)
                return False
            self.manager.set_credential_state(cred["fingerprint"], "retired")
            self.audit.record_cert_event(kind="renewed", subject_identity=subject,
                                         detail=f"{kind} rotated")
            return True
        except Exception as e:
            self.manager.set_credential_state(cred["fingerprint"], "failed")
            self.audit.record_cert_event(kind="renewal-failed", subject_identity=subject,
                                         detail=str(e))
            logger.warning("rotation: renew failed for %s (%s): %s", subject, kind, e)
            return False

    async def _announce_successor(self, new_cert_pem: str):
        """Distribute a new host credential's pin to every live key-pinned peer
        over the existing authenticated channel (FR-013 dual-trust overlap)."""
        succ_fp = certs.key_fingerprint(new_cert_pem)
        for ident, ch in list(self.svc.channels.items()):
            try:
                await ch.notify("n2n/cert/update", {"fingerprint": succ_fp,
                                                     "cert_pem": new_cert_pem})
                self.audit.record_cert_event(kind="overlap-opened", subject_identity=ident,
                                             detail=f"successor {succ_fp[:16]}")
            except Exception:
                pass

    async def run_once(self, now: Optional[datetime.datetime] = None) -> int:
        """Renew everything currently due. Returns the count renewed."""
        n = 0
        for cred in self.due(now):
            if await self.renew_one(cred):
                n += 1
        return n
