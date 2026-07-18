"""Certificate engine for NCFED/N2N channel security (feature 060).

Provides the X.509 primitives the claw-certification feature is built on:

  * key generation (ECDSA P-256, matching the existing self-signed identity in
    risk.py so pinned credentials stay wire-compatible)
  * self-signed host credentials (pinned trust model)
  * a risk-local certificate authority + CA-issued member/hub credentials
    (iN2N hub attestation, replacing risk.py's independent per-member certs)
  * SHA-256 fingerprints (over DER, hex — the value peers pin and heartbeats carry)
  * chain verification against a pinned anchor with an application-layer SAN check
  * the renew-at-2/3-lifetime threshold math

Design (specs/060 research R1/R5/R6):
  * No new third-party packages — uses the already-required `cryptography`.
  * Keys never touch the database; only public certs + fingerprints do. Private
    keys live under keys_dir() with 0600 perms, dirs 0700 (data-model.md §6).
  * Verification is deliberately app-layer for the pinned model (fingerprint
    equality) and chain-based for the CA model, matching how channel.py and
    internal_channel.py already split trust.
"""

from __future__ import annotations

import datetime
import hashlib
import ipaddress  # noqa: F401  (kept for parity with callers building IP SANs)
import os
from pathlib import Path
from typing import Optional, Tuple

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

_ONE_MINUTE = datetime.timedelta(minutes=1)
_UTC = datetime.timezone.utc


def _now_utc() -> datetime.datetime:
    return datetime.datetime.now(_UTC)


def _as_aware(dt: datetime.datetime) -> datetime.datetime:
    """Treat a naive datetime as UTC so callers can pass either kind."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=_UTC)


# ---- keys directory layout (data-model.md §6) ----------------------------

def keys_dir(base_dir: Optional[str] = None) -> Path:
    """Return ~/.openclaw/n2n/keys/ (override via base_dir for tests), creating
    the subdir layout with restrictive perms. Idempotent."""
    base = Path(base_dir or os.path.expanduser("~/.openclaw/n2n")) / "keys"
    base.mkdir(parents=True, exist_ok=True)
    _chmod(base, 0o700)
    for sub in ("host", "acme", "risk-ca", "members"):
        d = base / sub
        d.mkdir(exist_ok=True)
        _chmod(d, 0o700)
    return base


def _chmod(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass  # best-effort on filesystems without POSIX perms (e.g. some mounts)


def _write_secret(path: Path, data: str) -> None:
    path.write_text(data)
    _chmod(path, 0o600)


# ---- key + certificate primitives ----------------------------------------

def generate_keypair() -> ec.EllipticCurvePrivateKey:
    """ECDSA P-256 private key (matches risk.py's existing self-signed identity)."""
    return ec.generate_private_key(ec.SECP256R1())


def _key_pem(key: ec.EllipticCurvePrivateKey) -> str:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


def _cert_pem(cert: x509.Certificate) -> str:
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def _san(name: str) -> x509.SubjectAlternativeName:
    """DNS SAN for a claw domain; otherwise a URI SAN carrying the internal
    identity (member-id / risk name), which is not a hostname."""
    if "." in name and " " not in name and "/" not in name:
        return x509.SubjectAlternativeName([x509.DNSName(name)])
    return x509.SubjectAlternativeName([x509.UniformResourceIdentifier(f"ncfed:{name}")])


def create_self_signed(common_name: str, days: int = 3650) -> Tuple[str, str]:
    """Self-signed leaf for the pinned trust model. Returns (cert_pem, key_pem)."""
    key = generate_keypair()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = _now_utc()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _ONE_MINUTE)
        .not_valid_after(now + datetime.timedelta(days=days))
        .add_extension(_san(common_name), critical=False)
        .sign(key, hashes.SHA256())
    )
    return _cert_pem(cert), _key_pem(key)


def create_risk_ca(risk_name: str, days: int = 730) -> Tuple[str, str]:
    """Self-signed risk CA (FR-008). pathlen=0 — it signs leaf member/hub certs
    only, never sub-CAs. Returns (ca_cert_pem, ca_key_pem)."""
    key = generate_keypair()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"{risk_name} Risk CA")])
    now = _now_utc()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _ONE_MINUTE)
        .not_valid_after(now + datetime.timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_cert_sign=True, crl_sign=True,
                key_encipherment=False, content_commitment=False,
                data_encipherment=False, key_agreement=False,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        # SKI is required on CA certs by strict X.509 verification, which
        # Python 3.13+ enables by default (VERIFY_X509_STRICT) — without it,
        # peers on a modern stack refuse the chain outright.
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
                       critical=False)
        .sign(key, hashes.SHA256())
    )
    return _cert_pem(cert), _key_pem(key)


def issue_cert(ca_cert_pem: str, ca_key_pem: str, subject_cn: str,
               san: Optional[str] = None, days: int = 90,
               server: bool = True, client: bool = True) -> Tuple[str, str]:
    """Issue a leaf (member or hub) signed by the risk CA (FR-009/010).
    Returns (cert_pem, key_pem). SAN defaults to subject_cn."""
    ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())
    ca_key = serialization.load_pem_private_key(ca_key_pem.encode(), password=None)
    leaf_key = generate_keypair()
    now = _now_utc()
    ekus = []
    if server:
        ekus.append(ExtendedKeyUsageOID.SERVER_AUTH)
    if client:
        ekus.append(ExtendedKeyUsageOID.CLIENT_AUTH)
    builder = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject_cn)]))
        .issuer_name(ca_cert.subject)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _ONE_MINUTE)
        .not_valid_after(now + datetime.timedelta(days=days))
        .add_extension(_san(san or subject_cn), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        # AKI (+SKI) are required on CA-issued leaves by strict X.509
        # verification, on by default since Python 3.13 — a leaf without AKI
        # fails with "Missing Authority Key Identifier" on a modern peer.
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()),
                       critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False)
    )
    if ekus:
        builder = builder.add_extension(x509.ExtendedKeyUsage(ekus), critical=False)
    cert = builder.sign(ca_key, hashes.SHA256())
    return _cert_pem(cert), _key_pem(leaf_key)


# ---- fingerprints + verification ------------------------------------------

def fingerprint(cert_pem: str) -> str:
    """SHA-256 over the certificate DER, lowercase hex. This identifies a
    SPECIFIC certificate (it changes on every re-issue) and is what the RFC 5929
    tls-server-end-point channel binding uses. For the value peers PIN, use
    key_fingerprint() instead — it survives rotation."""
    cert = x509.load_pem_x509_certificate(cert_pem.encode())
    return cert.fingerprint(hashes.SHA256()).hex()


def key_fingerprint(cert_pem: str) -> str:
    """SHA-256 over the SubjectPublicKeyInfo (public key) DER — the stable PIN
    value used across eN2N and iN2N. Identical to risk.py's fingerprint_of(), and
    unchanged when a certificate is renewed with the same key, so a pinned peer
    stays pinned through rotation. This is what peers pin and heartbeats carry."""
    cert = x509.load_pem_x509_certificate(cert_pem.encode())
    pub_der = cert.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo)
    return hashlib.sha256(pub_der).hexdigest()


def san_names(cert_pem: str) -> list:
    """All SAN values (DNS + our ncfed: URIs) of the leaf, for identity checks."""
    cert = x509.load_pem_x509_certificate(cert_pem.encode())
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
    except x509.ExtensionNotFound:
        return []
    out = list(ext.value.get_values_for_type(x509.DNSName))
    out += [u[len("ncfed:"):] if u.startswith("ncfed:") else u
            for u in ext.value.get_values_for_type(x509.UniformResourceIdentifier)]
    return out


def cert_not_after(cert_pem: str) -> datetime.datetime:
    cert = x509.load_pem_x509_certificate(cert_pem.encode())
    return cert.not_valid_after_utc


def verify_chain(leaf_pem: str, anchor_pem: str, expected_san: Optional[str] = None,
                 at: Optional[datetime.datetime] = None) -> Tuple[bool, str]:
    """Verify a leaf is signed by `anchor` (the risk CA), is time-valid, and —
    when expected_san is given — carries it (FR-010 hub attestation; the member
    checks the hub's cert chains to its enrolled anchor and names the risk).

    App-layer verification (not a full path builder): the risk PKI is a single
    CA signing leaves directly (pathlen=0), so signature + validity + SAN is the
    complete check. Returns (ok, reason)."""
    now = _as_aware(at) if at else _now_utc()
    try:
        leaf = x509.load_pem_x509_certificate(leaf_pem.encode())
        anchor = x509.load_pem_x509_certificate(anchor_pem.encode())
    except ValueError as e:
        return False, f"malformed certificate: {e}"

    if not (leaf.not_valid_before_utc - _ONE_MINUTE <= now <= leaf.not_valid_after_utc):
        return False, (f"leaf not time-valid (now={now.isoformat()}Z, "
                       f"notAfter={leaf.not_valid_after_utc.isoformat()}) — check host clock")
    if not (anchor.not_valid_before_utc - _ONE_MINUTE <= now <= anchor.not_valid_after_utc):
        return False, "risk CA anchor not time-valid"

    try:
        anchor.public_key().verify(
            leaf.signature, leaf.tbs_certificate_bytes,
            ec.ECDSA(leaf.signature_hash_algorithm),
        )
    except Exception:
        return False, "leaf is not signed by the pinned risk CA"

    if expected_san is not None and expected_san not in san_names(leaf_pem):
        return False, f"leaf SAN does not include expected identity {expected_san!r}"
    return True, ""


# ---- rotation threshold (FR-012) ------------------------------------------

def renew_after(not_before: datetime.datetime, not_after: datetime.datetime,
                fraction: float = 0.667) -> datetime.datetime:
    """The instant a credential becomes eligible for renewal: `fraction` of its
    lifetime elapsed (default two-thirds → ~30 days left on a 90-day cert)."""
    lifetime = not_after - not_before
    return not_before + datetime.timedelta(seconds=lifetime.total_seconds() * fraction)


def days_remaining(not_after: datetime.datetime,
                   at: Optional[datetime.datetime] = None) -> int:
    """Whole days until expiry (negative if already expired) — HUD aging input."""
    now = _as_aware(at) if at else _now_utc()
    return (not_after - now).days
