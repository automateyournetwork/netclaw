"""TLS + channel-bound authentication for secured NCFED channels (feature 060).

This module is the keystone of claw certification: it builds the SSL contexts for
the two eN2N trust models and implements the dialer's proof-of-possession, bound
to the specific TLS session so an on-path attacker cannot relay it (research R1).

Why a signed nonce and not TLS client certificates:
  Let's Encrypt is removing the clientAuth EKU, so mutual TLS with public certs on
  both ends is not durable. Instead the LISTENER presents a TLS server credential
  (domain-verified WebPKI chain, or pinned self-signed) and the DIALER proves key
  possession at the application layer by signing (nonce || tls_exporter) with the
  private key behind the certificate it presents. The exporter value binds the
  signature to this TLS session (RFC 9266 pattern), closing the "no channel
  binding" gap the NCFED draft (059) flags.

Verification split (mirrors how channel.py / internal_channel.py already work):
  * domain-verified — the TLS stack verifies the WebPKI chain + hostname (SNI =
    claw domain); we then check the SAN equals the peer's recorded claw domain.
  * pinned — TLS runs with verification disabled and we compare the peer leaf's
    SHA-256 fingerprint to the pinned value at the application layer (TOFU on
    first contact). Encrypted either way.

Channel binding uses tls-server-end-point (RFC 5929): the SHA-256 of the
listener's certificate. Both ends know it on every Python/TLS version (the RFC
5705 tls-exporter is still not exposed by Python's ssl module as of 3.14), and it
defeats relay: a MITM presenting its own cert to the dialer produces a different
binding than the real listener expects, so the dialer's signature won't verify.
"""

from __future__ import annotations

import asyncio
import hashlib
import ssl
from typing import Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography import x509

from ..constants import NCFED_ALPN


# ---- SSL context builders -------------------------------------------------

def server_context(cert_chain_pem: str, key_pem: str) -> ssl.SSLContext:
    """Listener-side context presenting this claw's credential. Verification of
    the *dialer* happens at the app layer (signed nonce), so no client-cert
    requirement here — this is what lets Let's Encrypt (server-auth-only) certs
    work for the listener."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # NCFED -00 §6.1 mandates TLS 1.3; refuse any downgrade to 1.2 or below.
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    _load_chain(ctx, cert_chain_pem, key_pem)
    _maybe_apply_pq(ctx)  # 063 P4: accept the PQ hybrid where the stack supports it
    try:
        ctx.set_alpn_protocols([NCFED_ALPN])
    except NotImplementedError:  # pragma: no cover - old openssl
        pass
    return ctx


def client_context(trust_model: str, *, claw_domain: Optional[str] = None,
                   cafile: Optional[str] = None,
                   ech_config: Optional[bytes] = None) -> Tuple[ssl.SSLContext, Optional[str]]:
    """Dialer-side context. Returns (ctx, server_hostname):

    * domain-verified → default WebPKI trust with hostname checking; the caller
      dials the tunnel host but sets server_hostname to the claw domain (SNI +
      cert name check) so identity binds to the domain, not the endpoint (FR-003).
    * pinned → verification disabled at the TLS layer; the caller compares the
      peer leaf fingerprint to the pin after handshake (app-layer, FR-002/006)."""
    if trust_model == "domain-verified":
        ctx = ssl.create_default_context(cafile=cafile)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        _maybe_apply_pq(ctx)             # 063 P4: offer the PQ hybrid opportunistically
        _maybe_apply_ech(ctx, ech_config)  # 063 P3: conceal SNI on an ECH-capable stack
        _set_alpn(ctx)
        return ctx, claw_domain
    # pinned (and legacy-upgrade): encrypt, verify by fingerprint at app layer
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    _maybe_apply_pq(ctx)
    _set_alpn(ctx)
    return ctx, None


def _load_chain(ctx: ssl.SSLContext, cert_chain_pem: str, key_pem: str) -> None:
    import tempfile, os
    # SSLContext.load_cert_chain needs files; write to a private temp, then unlink.
    cf = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False)
    kf = tempfile.NamedTemporaryFile("w", suffix=".key", delete=False)
    try:
        cf.write(cert_chain_pem); cf.flush(); cf.close()
        kf.write(key_pem); kf.flush(); kf.close()
        os.chmod(kf.name, 0o600)
        ctx.load_cert_chain(certfile=cf.name, keyfile=kf.name)
    finally:
        for f in (cf.name, kf.name):
            try:
                os.unlink(f)
            except OSError:
                pass


def _set_alpn(ctx: ssl.SSLContext) -> None:
    try:
        ctx.set_alpn_protocols([NCFED_ALPN])
    except NotImplementedError:  # pragma: no cover
        pass


# ---- Feature 063 (P4/P3): PQ + KEX visibility, ECH seam -------------------
#
# The original 063 reference host was Python 3.10 / OpenSSL 3.0.2, which could
# not offer the X25519MLKEM768 hybrid, control TLS groups, read the negotiated
# group, or do ECH. These helpers degrade honestly there and activate the real
# behaviour automatically once the ssl module exposes group control/readout
# (`SSLContext.set_groups` + `SSLObject.group`, Python >= 3.15 — verified absent
# on 3.14) on OpenSSL >= 3.5 (research R0/R4).
#
# Verified 2026-07-17 on Ubuntu 26.04 (Python 3.14.4 / OpenSSL 3.5.5): OpenSSL
# 3.5 includes X25519MLKEM768 in its DEFAULT group list, so channels between two
# OpenSSL>=3.5 hosts negotiate the PQ hybrid on the wire even though Python 3.14
# can neither request nor observe it. pq_available() therefore means "can offer
# AND verify", never "the wire is classical".

# The hybrid PQ group name, offered ahead of classical curves where supported.
_PQ_GROUPS = "X25519MLKEM768:x25519:secp256r1:x448:secp521r1:secp384r1"


def _openssl_at_least(major: int, minor: int) -> bool:
    try:
        v = ssl.OPENSSL_VERSION_INFO  # (major, minor, patch, ...)
        return (v[0], v[1]) >= (major, minor)
    except Exception:  # pragma: no cover
        return False


def pq_available() -> bool:
    """True only if this stack can BOTH offer the X25519MLKEM768 hybrid AND report
    the negotiated group — i.e. `SSLContext.set_groups` (Python 3.15+), readable
    `SSLObject.group` (3.15+), and OpenSSL >= 3.5 (MLKEM). False on Python <= 3.14
    even over OpenSSL 3.5 (which may still negotiate the hybrid by default), so
    P4 degrades honestly and never labels an unverifiable channel as PQ."""
    return (hasattr(ssl.SSLContext, "set_groups")
            and hasattr(ssl.SSLObject, "group")
            and _openssl_at_least(3, 5))


def ech_available() -> bool:
    """True only if `ssl` exposes an ECH config API (absent through at least
    Python 3.12 / OpenSSL 3.0.2). Gates the P3 SNI-concealment seam."""
    return hasattr(ssl.SSLContext, "set_ech_config") or hasattr(ssl, "ECHConfig")


def _maybe_apply_pq(ctx: ssl.SSLContext) -> None:
    """Opportunistically offer the PQ hybrid group ahead of classical curves. A
    documented no-op on a stack without `set_groups` — connectivity is never
    affected, PQ simply isn't offered (FR-010)."""
    if hasattr(ctx, "set_groups"):
        try:
            ctx.set_groups(_PQ_GROUPS)
        except (ssl.SSLError, ValueError):  # pragma: no cover - stack rejects the group
            pass


def _maybe_apply_ech(ctx: ssl.SSLContext, ech_config: Optional[bytes]) -> None:
    """P3 SNI-concealment seam. A single guarded point that would install an ECH
    config on an ECH-capable stack; a documented no-op on the current stack, so
    the claw-domain SNI remains an accepted, reported residual (FR-007)."""
    if ech_config and hasattr(ctx, "set_ech_config"):
        try:
            ctx.set_ech_config(ech_config)  # pragma: no cover - no ECH on this stack
        except Exception:  # pragma: no cover
            pass


def channel_kex(sslobj) -> dict:
    """Per-channel key-exchange facts for the operator posture view (FR-012).
    On the reference stack `kex_group` is None (not readable) while `tls_version`
    and `cipher` populate — honest, never faked."""
    out = {"tls_version": None, "cipher": None, "kex_group": None}
    try:
        out["tls_version"] = sslobj.version()
    except Exception:
        pass
    try:
        c = sslobj.cipher()
        if c:
            out["cipher"] = c[0]
    except Exception:
        pass
    try:
        g = getattr(sslobj, "group", None)  # SSLObject.group is 3.15+
        if g:
            out["kex_group"] = g
    except Exception:
        pass
    return out


def is_pq_group(kex_group: Optional[str]) -> bool:
    """Whether a negotiated group name denotes a PQ/hybrid KEM. None (unreadable)
    is NOT treated as PQ — honesty over optimism."""
    return bool(kex_group) and ("mlkem" in kex_group.lower() or "kyber" in kex_group.lower())


# ---- peer credential inspection -------------------------------------------

def peer_leaf_pem(sslobj) -> Optional[str]:
    """PEM of the peer's leaf certificate from a completed handshake, or None.
    Works whether or not the TLS layer verified it (needed for pinned mode where
    verify_mode is CERT_NONE — use getpeercert(binary_form=True) which does not
    require verification)."""
    try:
        der = sslobj.getpeercert(binary_form=True)
    except Exception:
        return None
    if not der:
        return None
    cert = x509.load_der_x509_certificate(der)
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def leaf_key_fingerprint(sslobj) -> Optional[str]:
    """SPKI (public-key) SHA-256 of the peer leaf — the value we pin/compare.
    Keyed on the public key, not the cert, so a pinned peer survives certificate
    rotation with the same key (matches certs.key_fingerprint / risk.fingerprint_of)."""
    try:
        der = sslobj.getpeercert(binary_form=True)
    except Exception:
        return None
    if not der:
        return None
    pub_der = x509.load_der_x509_certificate(der).public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo)
    return hashlib.sha256(pub_der).hexdigest()


# ---- channel binding + proof-of-possession --------------------------------

def _der_sha256(der: bytes) -> bytes:
    return hashlib.sha256(der).digest()


def binding_from_peer(sslobj) -> Optional[bytes]:
    """tls-server-end-point binding as the DIALER computes it: SHA-256 of the
    listener's certificate observed on this TLS channel (RFC 5929)."""
    try:
        der = sslobj.getpeercert(binary_form=True)
    except Exception:
        return None
    return _der_sha256(der) if der else None


def binding_from_own_cert(cert_pem: str) -> bytes:
    """The same binding as the LISTENER computes it: SHA-256 of its own leaf.
    Equals binding_from_peer() on the dialer for the same session."""
    leaf = x509.load_pem_x509_certificate(cert_pem.encode())
    return _der_sha256(leaf.public_bytes(serialization.Encoding.DER))


async def upgrade_to_tls(reader, writer, ctx: ssl.SSLContext, *, server_side: bool,
                         server_hostname: Optional[str] = None):
    """STARTTLS-style upgrade of an existing NCFED stream to TLS in place.

    Secured NCFED keeps the cleartext 'N'+magic+handshake discrimination (so the
    existing shared-port peek is untouched — research R4 revised), then upgrades
    the SAME connection to TLS before any sensitive payload. This sidesteps the
    asyncio peek-vs-start_tls conflict: nothing after the handshake has been read,
    so start_tls sees a clean TLS ClientHello.

    Returns the SAME (reader, writer) with their transport swapped to the TLS
    transport. Raises ssl.SSLError / OSError on handshake failure."""
    loop = asyncio.get_event_loop()
    transport = writer.transport
    protocol = transport.get_protocol()
    new_tr = await loop.start_tls(
        transport, protocol, ctx,
        server_side=server_side, server_hostname=server_hostname)
    # Redirect the stream objects at the new TLS transport. The StreamReader keeps
    # being fed by the same protocol (now decrypted data); the writer must send
    # through the TLS transport.
    reader._transport = new_tr
    writer._transport = new_tr
    if getattr(protocol, "_stream_writer", None) is not None:
        protocol._stream_writer._transport = new_tr
    return reader, writer


def sign_auth(key_pem: str, nonce: bytes, exporter: bytes) -> bytes:
    """Dialer signs (nonce || exporter) with its private key — proves possession
    of the key behind the certificate it presented, bound to this TLS session."""
    key = serialization.load_pem_private_key(key_pem.encode(), password=None)
    return key.sign(nonce + exporter, ec.ECDSA(hashes.SHA256()))


# ---- framed exchange used for the post-upgrade auth handshake -------------

import os as _os  # noqa: E402


def _frame(data: bytes) -> bytes:
    return len(data).to_bytes(4, "big") + data


async def _read_frame(reader, timeout: float = 10.0) -> bytes:
    n = int.from_bytes(await asyncio.wait_for(reader.readexactly(4), timeout), "big")
    if n > 1 << 20:  # 1 MB guard — auth frames are tiny
        raise ValueError("oversized auth frame")
    return await asyncio.wait_for(reader.readexactly(n), timeout)


async def listener_authenticate(reader, writer, *, host_cert_pem: str):
    """Listener side of the post-TLS auth: issue a nonce, receive the dialer's
    certificate + signature, verify the signature is bound to THIS session (our
    cert's end-point binding). Returns (dialer_cert_pem, ok: bool)."""
    nonce = _os.urandom(32)
    writer.write(_frame(nonce))
    await writer.drain()
    dialer_cert = (await _read_frame(reader)).decode()
    sig = await _read_frame(reader)
    ok = verify_auth(dialer_cert, sig, nonce, binding_from_own_cert(host_cert_pem))
    writer.write(_frame(b"ok" if ok else b"no"))
    await writer.drain()
    return dialer_cert, ok


async def dialer_authenticate(reader, writer, sslobj, *, host_cert_pem: str,
                              host_key_pem: str) -> bool:
    """Dialer side: read the listener's nonce, sign (nonce || server-end-point
    binding) with our key, send our cert + signature, await the verdict."""
    nonce = await _read_frame(reader)
    binding = binding_from_peer(sslobj)
    if binding is None:
        return False
    sig = sign_auth(host_key_pem, nonce, binding)
    writer.write(_frame(host_cert_pem.encode()))
    writer.write(_frame(sig))
    await writer.drain()
    return (await _read_frame(reader)) == b"ok"


def verify_auth(cert_pem: str, sig: bytes, nonce: bytes, exporter: bytes) -> bool:
    """Listener verifies the dialer's signature against the public key in the
    certificate the dialer presented on the TLS channel."""
    try:
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        cert.public_key().verify(sig, nonce + exporter, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False
