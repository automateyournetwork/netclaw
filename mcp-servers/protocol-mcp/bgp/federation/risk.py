"""iN2N risk state: roles, member registry, enrollment tokens, key pinning.

The RiskManager owns this claw's iN2N state on top of the shared
FederationManager SQLite connection (feature 056). It is transport-agnostic —
the internal_channel/service layers call into it for enrollment and auth
decisions, and the daemon HTTP API calls into it for operator actions.

Distinguishing iN2N from eN2N is the TRUST DOMAIN, not location: a "risk" is
one owner's group of claws, coordinated by a single Border. Members may be
co-located or distributed across clouds/datacenters; they dial the Border
outbound and are authenticated by a pinned, self-signed key (trust-on-first-use)
bootstrapped by a single-use enrollment token. No CA. The frozen eN2N core
(consent/default-deny/framing) is untouched.
"""

import datetime
import hashlib
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Optional

from ..constants import (
    N2N_ROLE_STANDALONE, N2N_ROLE_BORDER, N2N_ROLE_MEMBER, N2N_ROLES,
    N2N_QUARANTINE_THRESHOLD_DEFAULT,
)

logger = logging.getLogger("n2n.risk")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ── mandatory base floor (FR-021a) — every member gets these, non-removable,
# regardless of profile; tagged tier=base so they are EXCLUDED from the routing
# specificity tie-break (FR-021b).
BASE_FLOOR = [
    {"name": "n2n-member-runtime", "type": "skill", "tier": "base"},
    {"name": "self-status",        "type": "skill", "tier": "base"},
    {"name": "member_heartbeat",   "type": "tool",  "tier": "base"},
    {"name": "member_report_audit","type": "tool",  "tier": "base"},
]

# Member states beyond the enrolled→active lifecycle:
#   provisioned → enrolled → active ↔ unreachable ; quarantined ; removed
STATE_PROVISIONED = "provisioned"   # add_member ran; token issued; no key yet
STATE_ENROLLED = "enrolled"         # key pinned (TOFU); awaiting/idle channel
STATE_ACTIVE = "active"             # authenticated, live channel
STATE_UNREACHABLE = "unreachable"   # was active, channel dropped
STATE_QUARANTINED = "quarantined"   # auto-unpinned after repeated failures
STATE_REMOVED = "removed"           # operator removed; unpinned
_TRUSTED_STATES = (STATE_ENROLLED, STATE_ACTIVE, STATE_UNREACHABLE)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RiskManager:
    """iN2N role + member + enrollment state, on the shared FederationManager DB."""

    def __init__(self, manager, quarantine_threshold: Optional[int] = None):
        self.m = manager
        self._conn = manager._conn
        self.base_dir = Path(manager.base_dir)
        self.keys_dir = self.base_dir / "keys"
        self.pinned_dir = self.keys_dir / "pinned"
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self.pinned_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_threshold = int(
            quarantine_threshold
            if quarantine_threshold is not None
            else os.environ.get("N2N_QUARANTINE_THRESHOLD", N2N_QUARANTINE_THRESHOLD_DEFAULT))

    # ---- keys (self-signed, no CA — R3/FR-013a) -----------------------

    def ensure_self_identity(self, common_name: str = "netclaw-claw"):
        """Generate (once) this claw's self-signed keypair+cert under keys/.
        Returns (cert_pem_str, fingerprint_hex). Used for the internal channel
        and as the identity a peer/Border pins."""
        key_path = self.keys_dir / "self.key"
        crt_path = self.keys_dir / "self.crt"
        if key_path.exists() and crt_path.exists():
            cert_pem = crt_path.read_text()
            return cert_pem, self.fingerprint_of(cert_pem)
        cert_pem, key_pem = self._generate_self_signed(common_name)
        key_path.write_text(key_pem)
        os.chmod(key_path, 0o600)
        crt_path.write_text(cert_pem)
        return cert_pem, self.fingerprint_of(cert_pem)

    @staticmethod
    def _generate_self_signed(common_name: str):
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
        now = datetime.datetime.utcnow()
        cert = (
            x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=1))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .sign(key, hashes.SHA256())
        )
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        key_pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()).decode()
        return cert_pem, key_pem

    def self_cert_pem(self) -> str:
        cert_pem, _ = self.ensure_self_identity(self.self_member_id() or self.role())
        return cert_pem

    def self_sign(self, nonce: bytes, binding: bytes = b"") -> bytes:
        """Sign a peer/Border-issued nonce with this claw's own private key —
        proves possession of the self-signed key whose cert was pinned. `binding`
        is the optional tls-server-end-point channel binding (feature 060): when
        the channel is TLS, the caller passes the SHA-256 of the peer's server
        certificate so the proof is bound to this session (RFC 5929). Empty on a
        cleartext channel (and for iN2N, which is unchanged)."""
        self.ensure_self_identity(self.self_member_id() or self.role())
        key_pem = (self.keys_dir / "self.key").read_text()
        return self.sign_challenge(key_pem, nonce + binding)

    @staticmethod
    def sign_challenge(key_pem: str, nonce: bytes) -> bytes:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        key = serialization.load_pem_private_key(key_pem.encode(), password=None)
        return key.sign(nonce, ec.ECDSA(hashes.SHA256()))

    # ── feature 060: risk certificate authority + hub attestation (US2) ──
    # The Border is its risk's CA. It presents a CA-signed hub credential to
    # members so they can verify (at dial time) that the hub they reached is the
    # legitimate one — closing the 059 "does not authenticate the Border to the
    # member" gap. The CA anchor is delivered to a member at enrollment.
    def ensure_risk_ca(self):
        """Create (once) this risk's CA under keys/risk-ca/. Returns (ca_cert_pem,
        ca_key_pem). Only meaningful on a Border."""
        from . import certs
        cad = self.keys_dir / "risk-ca"
        cad.mkdir(exist_ok=True)
        crt, key = cad / "ca.crt", cad / "ca.key"
        if crt.exists() and key.exists():
            return crt.read_text(), key.read_text()
        risk_name = (self.get_risk() or {}).get("risk_name") or "risk"
        ca_cert, ca_key = certs.create_risk_ca(risk_name)
        crt.write_text(ca_cert)
        certs._write_secret(key, ca_key)
        logger.info("Created risk CA for %s (fingerprint %s)", risk_name,
                    certs.fingerprint(ca_cert)[:16])
        return ca_cert, ca_key

    def risk_ca_pem(self) -> Optional[str]:
        crt = self.keys_dir / "risk-ca" / "ca.crt"
        return crt.read_text() if crt.exists() else None

    def store_risk_anchor(self, anchor_pem: str):
        """Member side: persist the risk CA anchor received at enrollment so the
        member can verify the hub on every future dial (FR-010)."""
        (self.keys_dir / "risk-ca-anchor.pem").write_text(anchor_pem)

    def risk_anchor(self) -> Optional[str]:
        p = self.keys_dir / "risk-ca-anchor.pem"
        return p.read_text() if p.exists() else None

    def hub_credential(self):
        """The Border's CA-signed hub credential (cert + key), created once.
        Returns (hub_cert_pem, hub_key_pem)."""
        from . import certs
        cad = self.keys_dir / "risk-ca"
        hcrt, hkey = cad / "hub.crt", cad / "hub.key"
        if hcrt.exists() and hkey.exists():
            return hcrt.read_text(), hkey.read_text()
        ca_cert, ca_key = self.ensure_risk_ca()
        risk_name = (self.get_risk() or {}).get("risk_name") or "risk"
        hub_cert, hub_key = certs.issue_cert(ca_cert, ca_key, f"{risk_name}/border",
                                             san=f"{risk_name}/border")
        hcrt.write_text(hub_cert)
        certs._write_secret(hkey, hub_key)
        return hub_cert, hub_key

    def attest_hub(self, member_nonce: bytes) -> Optional[dict]:
        """Produce hub attestation for a member's challenge: the CA-signed hub
        cert + a signature over the member's nonce. Member verifies chain-to-anchor
        + signature. Returns None if this claw has no CA (not a Border)."""
        if not self.is_border():
            return None
        hub_cert, hub_key = self.hub_credential()
        sig = self.sign_challenge(hub_key, member_nonce)
        return {"hub_cert": hub_cert, "hub_sig": sig.hex(),
                "risk_ca": self.risk_ca_pem()}

    @staticmethod
    def verify_hub_attestation(attest: dict, anchor_pem: str,
                               member_nonce: bytes, risk_name: str) -> bool:
        """Member side: verify the hub cert chains to the enrolled risk CA, names
        the risk's border, and signed our nonce (proof the hub holds the key)."""
        from . import certs
        hub_cert = attest.get("hub_cert")
        sig = bytes.fromhex(attest.get("hub_sig", "") or "")
        if not hub_cert or not sig:
            return False
        ok, _ = certs.verify_chain(hub_cert, anchor_pem,
                                   expected_san=f"{risk_name}/border")
        if not ok:
            return False
        return RiskManager.verify_possession(hub_cert, member_nonce, sig)

    @staticmethod
    def verify_possession(cert_pem: str, nonce: bytes, signature: bytes,
                          binding: bytes = b"") -> bool:
        """Verify a signature over `nonce || binding` was made by the private key
        matching `cert_pem` — impersonation resistance. `binding` is the optional
        tls-server-end-point channel binding (feature 060); it MUST match the
        value the signer used, so a proof made for one TLS session cannot be
        relayed to another. Empty for cleartext / iN2N (unchanged)."""
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.exceptions import InvalidSignature
        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode())
            cert.public_key().verify(signature, nonce + binding, ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False

    @staticmethod
    def fingerprint_of(cert_pem: str) -> str:
        """Stable sha256 fingerprint of a PEM cert's public key (DER)."""
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        pub_der = cert.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo)
        return _sha256_hex(pub_der)

    def _pin_key_file(self, member_id: str, cert_pem: str):
        safe = member_id.replace("/", "__")
        (self.pinned_dir / f"{safe}.crt").write_text(cert_pem)

    def _unpin_key_file(self, member_id: str):
        safe = member_id.replace("/", "__")
        (self.pinned_dir / f"{safe}.crt").unlink(missing_ok=True)

    # ---- eN2N peer pinning (TOFU) — reconciled from Josh/TunnelMind ----
    # External claws are NOT risk members (no enrollment token, no scope), so they
    # pin to a cert file under pinned/ keyed by eN2N identity — reusing the same
    # store + fingerprint primitive, namespaced ("en2n__") so an external peer can
    # never overwrite an internal member's pin.
    def _peer_pin_path(self, ident: str):
        return self.pinned_dir / f"en2n__{ident.replace('/', '__')}.crt"

    def check_peer_pin(self, ident: str, cert_pem: str) -> str:
        """Trust-on-first-use for a federated peer's self-signed cert.
          'new'      first contact — cert is now pinned to this identity.
          'match'    presented cert matches the pinned key.
          'mismatch' key changed for a known identity — caller MUST reject and
                     alert the operator; this NEVER silently re-pins.
        Uses the SPKI (key) fingerprint so a peer survives cert rotation with the
        same key (consistent with certs.key_fingerprint / feature 060)."""
        path = self._peer_pin_path(ident)
        if not path.exists():
            path.write_text(cert_pem)
            return "new"
        if self.fingerprint_of(path.read_text()) == self.fingerprint_of(cert_pem):
            return "match"
        return "mismatch"

    def repin_peer(self, ident: str, cert_pem: str):
        """Deliberate operator re-pin after a verified key rotation (never automatic)."""
        self._peer_pin_path(ident).write_text(cert_pem)

    # ---- role model (FR-002/003/004/015) ------------------------------

    def get_risk(self) -> dict:
        row = self._conn.execute("SELECT * FROM risk WHERE id=1").fetchone()
        if row:
            return dict(row)
        # Default: standalone (a risk of one) — behaves as pre-056 NetClaw.
        return {"id": 1, "risk_name": None, "description": None,
                "role": N2N_ROLE_STANDALONE, "enabled_stacks": None,
                "border_endpoint": None, "self_member_id": None}

    def is_standalone(self) -> bool:
        return self.get_risk()["role"] == N2N_ROLE_STANDALONE

    def is_border(self) -> bool:
        return self.get_risk()["role"] == N2N_ROLE_BORDER

    def role(self) -> str:
        return self.get_risk()["role"]

    def self_member_id(self) -> Optional[str]:
        return self.get_risk().get("self_member_id")

    def set_role(self, role: str, risk_name: Optional[str] = None,
                 description: Optional[str] = None, enabled_stacks: Optional[str] = None,
                 border_endpoint: Optional[str] = None, self_member_id: Optional[str] = None):
        """Configure this claw's role (installer / reconfig). Enforces the
        single-Border invariant (FR-003): a claw cannot be Border of two
        different risks."""
        if role not in N2N_ROLES:
            raise ValueError(f"invalid role: {role!r} (expected one of {N2N_ROLES})")
        cur = self.get_risk()
        if (role == N2N_ROLE_BORDER and cur["role"] == N2N_ROLE_BORDER
                and cur["risk_name"] and risk_name and cur["risk_name"] != risk_name):
            raise ValueError(
                f"this claw is already the Border of risk '{cur['risk_name']}'; "
                f"a claw cannot be Border of a second risk '{risk_name}' (FR-003)")
        if role == N2N_ROLE_MEMBER and risk_name and self_member_id is None:
            self_member_id = self_member_id  # provided by caller when known
        now = _now()
        exists = self._conn.execute("SELECT 1 FROM risk WHERE id=1").fetchone()
        if exists:
            self._conn.execute(
                "UPDATE risk SET risk_name=?, description=?, role=?, enabled_stacks=?, "
                "border_endpoint=?, self_member_id=?, updated_at=? WHERE id=1",
                (risk_name, description, role, enabled_stacks, border_endpoint,
                 self_member_id, now))
        else:
            self._conn.execute(
                "INSERT INTO risk (id, risk_name, description, role, enabled_stacks, "
                "border_endpoint, self_member_id, created_at, updated_at) "
                "VALUES (1,?,?,?,?,?,?,?,?)",
                (risk_name, description, role, enabled_stacks, border_endpoint,
                 self_member_id, now, now))
        self._conn.commit()
        return self.get_risk()

    def stack_enabled(self, stack: str) -> bool:
        """Is 'en2n' or 'in2n' enabled? Only a Border runs either (FR-014/015)."""
        r = self.get_risk()
        if r["role"] != N2N_ROLE_BORDER:
            # A member never runs eN2N; standalone is eN2N-capable as before.
            return stack == "en2n" and r["role"] == N2N_ROLE_STANDALONE
        es = (r["enabled_stacks"] or "").lower()
        return es == "both" or es == stack

    # ---- enrollment tokens (single-use — FR-013a/b) -------------------

    def issue_token(self, label: Optional[str] = None, ttl_seconds: Optional[int] = None) -> dict:
        """Issue a single-use enrollment token. The raw token is returned once;
        only its hash is stored."""
        if not self.is_border():
            raise ValueError("only a Border can issue enrollment tokens")
        raw = "in2n_" + secrets.token_urlsafe(24)
        token_hash = _sha256_hex(raw.encode())
        expires_at = None
        if ttl_seconds:
            expires_at = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + ttl_seconds))
        self._conn.execute(
            "INSERT INTO enrollment_token (token_hash, label, issued_at, expires_at) "
            "VALUES (?,?,?,?)", (token_hash, label, _now(), expires_at))
        self._conn.commit()
        return {"token": raw, "token_hash": token_hash, "expires_at": expires_at}

    def _token_row(self, raw: str):
        return self._conn.execute(
            "SELECT * FROM enrollment_token WHERE token_hash=?",
            (_sha256_hex(raw.encode()),)).fetchone()

    def consume_token(self, raw_token: str, member_id: str, cert_pem: str,
                      scope: Optional[list] = None, runtime_kind: str = "process",
                      display_name: Optional[str] = None,
                      transport_binding: str = "loopback") -> dict:
        """Validate a single-use token + pin the member's self-signed key (TOFU).
        Raises ValueError(code) on invalid/spent/expired token or id/key clash."""
        if not self.is_border():
            raise ValueError("IN2N_ERR_NOT_A_BORDER")
        row = self._token_row(raw_token)
        if not row or row["spent_at"]:
            raise ValueError("IN2N_ERR_ENROLL_TOKEN_INVALID")
        if row["expires_at"] and _now() > row["expires_at"]:
            raise ValueError("IN2N_ERR_ENROLL_TOKEN_INVALID")
        fp = self.fingerprint_of(cert_pem)
        existing = self.get_member(member_id)
        if (existing and existing["state"] not in (STATE_REMOVED, STATE_QUARANTINED,
                                                    STATE_PROVISIONED)
                and existing["key_fingerprint"] and existing["key_fingerprint"] != fp):
            raise ValueError("IN2N_ERR_MEMBER_ID_TAKEN")
        now = _now()
        self._pin_key_file(member_id, cert_pem)
        scope_json = json.dumps(scope) if scope is not None else (
            existing["scope"] if existing else json.dumps(BASE_FLOOR))
        if existing:
            # Keep the Border-provisioned scope (structured {name,tier} from
            # add_member) — do NOT overwrite it with the member's advertised scope,
            # which may be a flat name list. The Border defines scope at
            # provisioning; the member's advertised list is informational.
            self._conn.execute(
                "UPDATE member SET pinned_key=?, key_fingerprint=?, runtime_kind=?, "
                "transport_binding=?, display_name=COALESCE(?, display_name), "
                "state=?, auth_failures=0, updated_at=? WHERE member_id=?",
                (cert_pem, fp, runtime_kind, transport_binding, display_name,
                 STATE_ENROLLED, now, member_id))
        else:
            self._conn.execute(
                "INSERT INTO member (member_id, display_name, pinned_key, key_fingerprint, "
                "profile, scope, runtime_kind, transport_binding, state, auth_failures, "
                "enrolled_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,0,?,?)",
                (member_id, display_name, cert_pem, fp, None, scope_json, runtime_kind,
                 transport_binding, STATE_ENROLLED, now, now))
        # Spend the token atomically.
        self._conn.execute(
            "UPDATE enrollment_token SET spent_at=?, spent_by_member_id=? WHERE token_hash=?",
            (now, member_id, row["token_hash"]))
        # FR-023: record that the credential fingerprint was surfaced at
        # enrollment so an intercepted enrollment is detectable — the member
        # recomputes this over the cert it holds and compares (a mismatch, i.e.
        # the Border pinned a different key than the member generated, means an
        # active attacker sat in the middle). Advisory (logged both sides), not a
        # blocking prompt — scripted/bulk provisioning keeps working.
        self._conn.execute(
            "UPDATE member SET enroll_fingerprint_logged=1 WHERE member_id=?",
            (member_id,))
        self._conn.commit()
        logger.info("Enrolled member %s — confirm fingerprint out of band: %s", member_id, fp)
        return {"member_id": member_id, "pinned": True, "state": STATE_ENROLLED,
                "enroll_fingerprint": fp}

    # ---- member registry (FR-008/029) ---------------------------------

    def get_member(self, member_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM member WHERE member_id=?", (member_id,)).fetchone()
        return dict(row) if row else None

    def list_members(self) -> list:
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM member WHERE state != ? ORDER BY member_id", (STATE_REMOVED,))]

    def verify_member(self, member_id: str, key_fingerprint: str) -> bool:
        """Authenticate a reconnecting member against its pinned key (FR-013a).
        On success marks it active; on failure the caller should record it."""
        mem = self.get_member(member_id)
        if not mem or mem["state"] not in _TRUSTED_STATES:
            return False
        if not mem["key_fingerprint"] or mem["key_fingerprint"] != key_fingerprint:
            return False
        self._set_state(member_id, STATE_ACTIVE, reset_failures=True)
        return True

    def _set_state(self, member_id: str, state: str, reset_failures: bool = False):
        if reset_failures:
            self._conn.execute(
                "UPDATE member SET state=?, auth_failures=0, updated_at=? WHERE member_id=?",
                (state, _now(), member_id))
        else:
            self._conn.execute(
                "UPDATE member SET state=?, updated_at=? WHERE member_id=?",
                (state, _now(), member_id))
        self._conn.commit()

    def mark_unreachable(self, member_id: str):
        mem = self.get_member(member_id)
        if mem and mem["state"] == STATE_ACTIVE:
            self._set_state(member_id, STATE_UNREACHABLE)

    def update_health(self, member_id: str, **fields):
        mem = self.get_member(member_id)
        if not mem:
            return
        health = {}
        if mem["health"]:
            try:
                health = json.loads(mem["health"])
            except (ValueError, TypeError):
                health = {}
        health.update(fields)
        self._conn.execute("UPDATE member SET health=?, updated_at=? WHERE member_id=?",
                           (json.dumps(health), _now(), member_id))
        self._conn.commit()

    # ---- provisioning (FR-019/020/021/022) ----------------------------

    def add_member(self, name: str, profile: Optional[str] = None,
                   specialty: Optional[list] = None,
                   ttl_seconds: Optional[int] = None,
                   launch_cmd: Optional[str] = None, on_demand: bool = False) -> dict:
        """Provision a member: compute scope (base floor + specialty), create a
        provisioned row, and issue a single-use enrollment token. Does NOT spawn
        the member runtime — that is a separate NetClaw install (FR-028)."""
        if not self.is_border():
            raise ValueError("only a Border can add members")
        risk = self.get_risk()
        member_id = f"{risk['risk_name']}/{name}"
        scope = list(BASE_FLOOR) + self._specialty_scope(profile, specialty)
        now = _now()
        existing = self.get_member(member_id)
        if existing and existing["state"] not in (STATE_REMOVED, STATE_QUARANTINED):
            raise ValueError(f"member '{member_id}' already exists")
        if existing:
            self._conn.execute(
                "UPDATE member SET profile=?, scope=?, state=?, pinned_key=NULL, "
                "key_fingerprint=NULL, auth_failures=0, updated_at=? WHERE member_id=?",
                (profile or "custom", json.dumps(scope), STATE_PROVISIONED, now, member_id))
        else:
            self._conn.execute(
                "INSERT INTO member (member_id, display_name, profile, scope, state, "
                "auth_failures, enrolled_at, updated_at) VALUES (?,?,?,?,?,0,?,?)",
                (member_id, name, profile or "custom", json.dumps(scope),
                 STATE_PROVISIONED, now, now))
        self._conn.commit()
        if launch_cmd:
            self.set_launch(member_id, launch_cmd, on_demand=on_demand)
        tok = self.issue_token(label=member_id, ttl_seconds=ttl_seconds)
        return {
            "member_id": member_id,
            "profile": profile or "custom",
            "scope": scope,
            "enrollment_token": tok["token"],
            "join": {
                "N2N_ROLE": N2N_ROLE_MEMBER,
                "N2N_RISK_NAME": risk["risk_name"],
                "N2N_BORDER_ENDPOINT": risk.get("border_endpoint") or "<border-host:port>",
                "token": tok["token"],
                "note": "Install NetClaw with these env vars + token; the member "
                        "dials the Border outbound and enrolls (FR-028).",
            },
        }

    @staticmethod
    def _specialty_scope(profile: Optional[str], specialty: Optional[list]) -> list:
        """Specialty capabilities tagged tier=specialty. If the caller passes an
        explicit specialty list use it; otherwise defer to scripts/in2n-profiles
        (the daemon injects the resolved list) — here we accept what's given."""
        out = []
        for item in (specialty or []):
            if isinstance(item, dict):
                e = dict(item)
                e.setdefault("type", "skill")
                e["tier"] = "specialty"
                out.append(e)
            else:  # bare name string
                out.append({"name": str(item), "type": "skill", "tier": "specialty"})
        return out

    # Names that are always base floor (excluded from specialty specificity),
    # covering both the technical floor and the interview-expanded floor.
    _BASE_NAMES = {e["name"] for e in BASE_FLOOR} | {
        "memory", "gait-session-tracking", "humanrail-escalation"}

    @staticmethod
    def _scope_list(scope):
        """Normalize a scope column (JSON) to a list; tolerates both the
        structured [{name,tier}] form and a flat [name,...] form."""
        if isinstance(scope, str):
            try:
                scope = json.loads(scope)
            except (ValueError, TypeError):
                return []
        return scope or []

    @classmethod
    def specialty_count(cls, scope) -> int:
        """Count only specialty entries — base floor excluded (FR-021b).
        Tolerant: dict entries use tier; bare-string entries count as specialty
        unless they are known base-floor names."""
        n = 0
        for e in cls._scope_list(scope):
            if isinstance(e, str):
                if e not in cls._BASE_NAMES:
                    n += 1
            elif isinstance(e, dict) and e.get("tier") == "specialty":
                n += 1
        return n

    def covers(self, member: dict, capability: str) -> bool:
        """Does a member's scope (base or specialty) include the capability?
        Tolerant of both structured and flat-string scope shapes."""
        for e in self._scope_list(member.get("scope")):
            if (e == capability) or (isinstance(e, dict) and e.get("name") == capability):
                return True
        return False

    def in_scope(self, member_id: str, capability: str) -> bool:
        mem = self.get_member(member_id)
        return bool(mem and self.covers(mem, capability))

    # ---- offboarding + quarantine (FR-013c/d) -------------------------

    def remove_member(self, member_id: str) -> bool:
        """Operator removal: unpin, drop from routing, refuse reconnect (FR-013c)."""
        mem = self.get_member(member_id)
        if not mem:
            return False
        self._conn.execute(
            "UPDATE member SET state=?, pinned_key=NULL, key_fingerprint=NULL, updated_at=? "
            "WHERE member_id=?", (STATE_REMOVED, _now(), member_id))
        self._conn.commit()
        self._unpin_key_file(member_id)
        logger.info("Removed member %s (unpinned; must re-enroll to return)", member_id)
        return True

    # ── feature 060 (FR-022): per-source failed-auth rate limiting so an
    # attacker who can reach the listener cannot unpin a legitimate member by
    # spraying failing authentications. The token bucket lives in the
    # auth_failure_bucket table; only failures whose source matches the member's
    # own established origin are allowed to count toward quarantine.
    def note_source_failure(self, source: str, limit: int = 5,
                            window_s: int = 60) -> bool:
        """Record an unauthenticated failure from `source`; return True while the
        source is within its rate budget, False once it should be dropped+audited."""
        now = time.time()
        row = self._conn.execute(
            "SELECT count, window_start FROM auth_failure_bucket WHERE source=?",
            (source,)).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO auth_failure_bucket (source, count, window_start) VALUES (?,1,?)",
                (source, str(now)))
            self._conn.commit()
            return True
        start = float(row["window_start"] or now)
        if now - start > window_s:
            count = 1
            start = now
        else:
            count = (row["count"] or 0) + 1
        self._conn.execute(
            "UPDATE auth_failure_bucket SET count=?, window_start=? WHERE source=?",
            (count, str(start), source))
        self._conn.commit()
        return count <= limit

    def record_auth_failure(self, member_id: str, source: Optional[str] = None,
                            established_source: Optional[str] = None) -> bool:
        """Increment failure count; auto-quarantine at threshold (FR-013d).
        Returns True if this failure triggered quarantine.

        FR-022: when `source` is given and does NOT match the member's
        established origin, the failure is rate-limited per source and MUST NOT
        count toward quarantine — otherwise any host reaching the listener could
        unpin a healthy member. Callers with no source (loopback/tests) keep the
        original behavior."""
        if source is not None and established_source is not None and source != established_source:
            allowed = self.note_source_failure(source)
            logger.info("iN2N auth failure for %s from foreign source %s — "
                        "rate-limited, not counted toward quarantine%s",
                        member_id, source, "" if allowed else " (over budget, dropped)")
            return False
        mem = self.get_member(member_id)
        if not mem or mem["state"] in (STATE_REMOVED, STATE_QUARANTINED):
            return False
        failures = (mem["auth_failures"] or 0) + 1
        if failures >= self.quarantine_threshold:
            self._conn.execute(
                "UPDATE member SET state=?, pinned_key=NULL, key_fingerprint=NULL, "
                "auth_failures=?, updated_at=? WHERE member_id=?",
                (STATE_QUARANTINED, failures, _now(), member_id))
            self._conn.commit()
            self._unpin_key_file(member_id)
            logger.warning("Auto-quarantined member %s after %d failures — operator alert",
                           member_id, failures)
            return True
        self._conn.execute(
            "UPDATE member SET auth_failures=?, updated_at=? WHERE member_id=?",
            (failures, _now(), member_id))
        self._conn.commit()
        return False

    def is_quarantined(self, member_id: str) -> bool:
        mem = self.get_member(member_id)
        return bool(mem and mem["state"] == STATE_QUARANTINED)

    # ---- cold / on-demand spawn spec (FR — hybrid runtime) ------------

    def set_launch(self, member_id: str, launch_cmd: str, on_demand: bool = True):
        """Register how the Border cold-starts this member (a local, spawnable
        member). Remote members leave launch_cmd NULL — the Border can't spawn
        them; they are brought up by their own host and just dial in."""
        self._conn.execute(
            "UPDATE member SET launch_cmd=?, on_demand=?, updated_at=? WHERE member_id=?",
            (launch_cmd, 1 if on_demand else 0, _now(), member_id))
        self._conn.commit()

    def launch_spec(self, member_id: str):
        """Return (launch_cmd, on_demand) for a member, or (None, False)."""
        mem = self.get_member(member_id)
        if not mem:
            return None, False
        return mem.get("launch_cmd"), bool(mem.get("on_demand"))

    # ---- durable-runtime binding (feature 057, US5/FR-014) ------------

    def managed_by(self, member_id: str) -> str:
        """'service' (own durable systemd unit) | 'cold' (spawn on route).
        Defaults to 'cold' for pre-057 rows."""
        mem = self.get_member(member_id)
        return (mem.get("managed_by") if mem else None) or "cold"

    def set_managed_by(self, member_id: str, kind: str,
                       service_unit: Optional[str] = None):
        """Bind a member to durable-service management (always-on) or cold-start.
        kind ∈ {'service','cold'}; service_unit is the systemd unit name when
        kind='service' (single-owner: the cold-start path skips a service member)."""
        if kind not in ("service", "cold"):
            raise ValueError(f"invalid managed_by: {kind!r}")
        self._conn.execute(
            "UPDATE member SET managed_by=?, service_unit=?, updated_at=? WHERE member_id=?",
            (kind, service_unit if kind == "service" else None, _now(), member_id))
        self._conn.commit()

    def service_unit(self, member_id: str) -> Optional[str]:
        mem = self.get_member(member_id)
        return mem.get("service_unit") if mem else None

    def set_component_scan(self, member_id: str, verdict: Optional[str]):
        """Cache the DefenseClaw component-scan verdict for a member (feature 057,
        FR-008): 'pass' | 'flagged:<what>' | None (re-scan next start)."""
        self._conn.execute(
            "UPDATE member SET component_scan=?, updated_at=? WHERE member_id=?",
            (verdict, _now(), member_id))
        self._conn.commit()

    def component_scan(self, member_id: str) -> Optional[str]:
        mem = self.get_member(member_id)
        return mem.get("component_scan") if mem else None
