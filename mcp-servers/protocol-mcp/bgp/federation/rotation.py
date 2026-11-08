"""Certificate renewal with preserved pinned identity.

Routine host certificate renewal retains its existing private key, so peer SPKI
pins remain valid. ACME renewal is delegated to lego. Unchanged CA/hub output is
reported as a failure, never a successful rotation. Deliberate key replacement
requires operator re-verification; automatic successor-key overlap is not provided.
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
        """Renew a certificate; preserve routine pinned identity and report failures.

        A new certificate with the same key updates its active registry row. A
        different key fingerprint retires the predecessor only after registration.
        """
        kind = cred["kind"]
        subject = cred["subject_identity"]
        try:
            if kind == "acme":
                from . import acme
                new_cert = await acme.renew(subject, self.manager.base_dir)
                if not new_cert:
                    raise RuntimeError("acme renew produced no certificate")
                self._validate_successor(cred, new_cert)
                self.register("acme", subject, new_cert, issuer="ACME")
            elif kind == "risk-ca":
                new_cert, _ = self.risk.ensure_risk_ca()  # idempotent; explicit rekey elsewhere
                self._validate_successor(cred, new_cert)
                self.register("risk-ca", subject, new_cert, issuer="self")
            elif kind == "hub":
                new_cert, _ = self.risk.hub_credential(renew=True)
                self._validate_successor(cred, new_cert)
                self.register("hub", subject, new_cert, issuer="risk-ca")
            elif kind == "host-pinned":
                installed, key_pem = self.svc.host_credential()
                if certs.key_fingerprint(installed) != cred["fingerprint"]:
                    raise RuntimeError("Installed host identity differs from renewal registry")
                cert_pem, _ = certs.create_self_signed(subject, key_pem=key_pem)
                if certs.key_fingerprint(cert_pem) != cred["fingerprint"]:
                    raise RuntimeError("Installed private key does not match host certificate")
                new_cert = cert_pem
                self._validate_successor(cred, new_cert)
                kd = certs.keys_dir(str(self.manager.base_dir)) / "host"
                certs._write_secret(kd / "host.crt", cert_pem)
                self.svc._host_cred = (cert_pem, key_pem)
                self.register("host-pinned", subject, cert_pem, issuer="self")
            else:
                logger.info("rotation: no renewer for kind %s (%s)", kind, subject)
                return False
            if certs.key_fingerprint(new_cert) != cred["fingerprint"]:
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

    @staticmethod
    def _validate_successor(cred, certificate):
        previous = cred.get("cert_pem")
        if previous and certs.fingerprint(previous) == certs.fingerprint(certificate):
            raise RuntimeError("Renewal returned the unchanged certificate; operator renewal is required")
        now = datetime.datetime.now(_UTC)
        parsed = certs.x509.load_pem_x509_certificate(certificate.encode())
        if not (parsed.not_valid_before_utc <= now < parsed.not_valid_after_utc):
            raise RuntimeError("Renewal returned a certificate that is not currently valid")

    async def run_once(self, now: Optional[datetime.datetime] = None) -> int:
        """Renew everything currently due. Returns the count renewed."""
        n = 0
        for cred in self.due(now):
            if await self.renew_one(cred):
                n += 1
        return n
