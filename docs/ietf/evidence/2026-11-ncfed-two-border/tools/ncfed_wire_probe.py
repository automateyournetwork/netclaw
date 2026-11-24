#!/usr/bin/env python3
"""Raw-wire NCFED probe for the two-Border evidence run (draft-capobianco-ncfed-00).

Adapted from scripts/ncfed-conformance-test.py and scripts/ncfed-consent-probe.py
(which hardcode 127.0.0.1 and one identity). Everything here is parameterised by
host, port and claimed identity. Needs Python 3.10+ and `cryptography` only for
the `hello` modes. It never prints nonces, private keys or full certificates:
fingerprints are truncated to 16 hex digits.

Subcommands
  discriminate HOST PORT          §4 first-octet / magic dispatch
  timeouts HOST PORT              §4 30 s first-octet and 10 s magic budgets
  handshake HOST PORT AS RID      §5/§6.1: reply bytes, TLS version, nonce length
      --hello none|keyless|forged|badsig
                                  §6.3/§6.4: send an n2n/hello after the nonce
      --tls12                     offer at most TLS 1.2 (downgrade check)
"""
import argparse
import hashlib
import json
import socket
import ssl
import struct
import sys
import time

MAGIC = b"NCFED"
TIMEOUT = 8.0


def out(label, ok, detail=""):
    print(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "check": label, "result": "PASS" if ok else "FAIL", "detail": detail}))
    return ok


def connect(host, port, timeout=TIMEOUT):
    s = socket.create_connection((host, port), timeout=timeout)
    s.settimeout(timeout)
    return s


def drain(s, limit=64, wait=TIMEOUT):
    """Read until EOF/timeout. Returns (bytes, how) where how is eof|reset|timeout."""
    s.settimeout(wait)
    data = b""
    try:
        while len(data) < limit:
            chunk = s.recv(limit - len(data))
            if not chunk:
                return data, "eof"
            data += chunk
        return data, "limit"
    except socket.timeout:
        return data, "timeout"
    except ConnectionResetError:
        return data, "reset"


def handshake_bytes(asn, rid):
    return MAGIC + struct.pack("!I", asn) + socket.inet_aton(rid)


def cmd_discriminate(a):
    ok = True
    for label, payload in (("0x00 first octet", b"\x00"),
                           ("direct TLS ClientHello record (0x16)", b"\x16\x03\x01\x00\x50\x01\x00\x00\x4c\x03\x03"),
                           ("'N' + unknown magic (NXXXX)", b"NXXXX"),
                           ("'N' + NCTUX (near-miss magic)", b"NCTUX")):
        s = connect(a.host, a.port)
        s.sendall(payload)
        data, how = drain(s)
        s.close()
        ok &= out(f"§4 {label} closed with zero bytes", data == b"" and how in ("eof", "reset"),
                  f"{len(data)} bytes, {how}")
    if a.no_bgp:
        return ok
    # 0xFF: hand to BGP with the octet replayed. A full 19-octet KEEPALIVE before
    # OPEN is an FSM error, so a BGP engine answers with a NOTIFICATION, which
    # itself starts with the 16 x 0xFF marker. That proves the octet was replayed
    # into a BGP parser rather than swallowed.
    s = connect(a.host, a.port)
    s.sendall(b"\xff" * 16 + struct.pack("!HB", 19, 4))
    data, how = drain(s)
    s.close()
    notif = len(data) >= 21 and data[:16] == b"\xff" * 16 and data[18] == 3
    ok &= out("§4 0xFF dispatched to BGP (marker replayed; KEEPALIVE-before-OPEN answered by BGP)",
              notif or (data == b"" and how == "timeout"),
              f"{len(data)} bytes, {how}" + (f", BGP NOTIFICATION code {data[19]}/{data[20]}" if notif else ""))
    return ok


def cmd_timeouts(a):
    ok = True
    s = connect(a.host, a.port, timeout=45)
    t0 = time.monotonic()
    data, how = drain(s, wait=45)
    dt = time.monotonic() - t0
    s.close()
    ok &= out("§4 silent connection closed after ~30 s first-octet budget",
              data == b"" and how in ("eof", "reset") and 25 <= dt <= 40, f"closed after {dt:.1f}s ({how})")
    s = connect(a.host, a.port, timeout=45)
    s.sendall(b"N")
    t0 = time.monotonic()
    data, how = drain(s, wait=45)
    dt = time.monotonic() - t0
    s.close()
    ok &= out("§4 'N' then silence closed after ~10 s magic budget",
              data == b"" and how in ("eof", "reset") and 7 <= dt <= 15, f"closed after {dt:.1f}s ({how})")
    return ok


def fp16(der_or_spki):
    return hashlib.sha256(der_or_spki).hexdigest()[:16]


def send_frame(tls, msg):
    payload = json.dumps(msg, separators=(",", ":")).encode()
    tls.sendall(struct.pack("!IB", len(payload), 0) + payload)


def read_frame(tls, wait=TIMEOUT):
    tls.settimeout(wait)
    buf = b""
    while len(buf) < 5:
        c = tls.recv(5 - len(buf))
        if not c:
            return None
        buf += c
    length, _flags = struct.unpack("!IB", buf)
    body = b""
    while len(body) < length:
        c = tls.recv(length - len(body))
        if not c:
            return None
        body += c
    return json.loads(body)


def cmd_handshake(a):
    s = connect(a.host, a.port)
    s.sendall(handshake_bytes(a.asn, a.rid))
    reply, how = b"", "limit"
    s.settimeout(TIMEOUT)
    try:
        while len(reply) < 13:
            c = s.recv(13 - len(reply))
            if not c:
                how = "eof"
                break
            reply += c
    except socket.timeout:
        how = "timeout"
    except ConnectionResetError:
        how = "reset"
    claimed = f"as{a.asn}-{a.rid}"
    if len(reply) < 13:
        out(f"§5 handshake as {claimed}: acceptor reply", False,
            f"{len(reply)} reply bytes then {how} (no handshake reply, no nonce)")
        s.close()
        return False
    if reply[:5] != MAGIC:
        out(f"§5 handshake as {claimed}: reply magic", False, repr(reply[:5]))
        return False
    racc = f"as{struct.unpack('!I', reply[5:9])[0]}-{socket.inet_ntoa(reply[9:13])}"
    out(f"§5 handshake as {claimed}: 13-octet NCFED reply", True, f"acceptor {racc}")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE   # we record the leaf; trust is the daemon's job
    if a.tls12:
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    try:
        tls = ctx.wrap_socket(s, server_hostname=a.sni or None)
    except (ssl.SSLError, OSError) as e:
        out("§6.1 in-place TLS upgrade", False if not a.tls12 else True, f"{type(e).__name__}: {str(e)[:120]}")
        return bool(a.tls12)
    der = tls.getpeercert(binary_form=True)
    san = "?"
    try:
        from cryptography import x509
        cert = x509.load_der_x509_certificate(der)
        try:
            san = ",".join(cert.extensions.get_extension_for_class(
                x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)) or "-"
        except x509.ExtensionNotFound:
            san = "-"
        from cryptography.hazmat.primitives import serialization
        spki = cert.public_key().public_bytes(serialization.Encoding.DER,
                                              serialization.PublicFormat.SubjectPublicKeyInfo)
        cn = cert.subject.rfc4514_string()
        detail_cert = f"subject {cn}, SAN [{san}], SPKI sha256 {fp16(spki)}…"
    except Exception:
        detail_cert = f"leaf sha256 {fp16(der)}…"
    out("§6.1 in-place TLS upgrade after handshake", not a.tls12,
        f"{tls.version()} {tls.cipher()[0]}; {detail_cert}")
    nonce = b""
    try:
        tls.settimeout(TIMEOUT)
        while len(nonce) < 32:
            c = tls.recv(32 - len(nonce))
            if not c:
                break
            nonce += c
    except socket.timeout:
        pass
    out("§5/§6.3 32-octet nonce received inside TLS", len(nonce) == 32, f"{len(nonce)} octets (value not logged)")
    if a.hello == "none" or len(nonce) != 32:
        tls.close()
        return len(nonce) == 32
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    import datetime
    binding = hashlib.sha256(der).digest()
    params = {"identity": claimed, "display_name": "ncfed-wire-probe", "versions": ["1.0"]}
    if a.hello in ("forged", "badsig"):
        key = ec.generate_private_key(ec.SECP256R1())
        now = datetime.datetime.now(datetime.timezone.utc)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, claimed)])
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now - datetime.timedelta(minutes=5))
                .not_valid_after(now + datetime.timedelta(days=1)).sign(key, hashes.SHA256()))
        signer = key if a.hello == "forged" else ec.generate_private_key(ec.SECP256R1())
        params["cert_pem"] = cert.public_bytes(serialization.Encoding.PEM).decode()
        params["signature"] = signer.sign(nonce + binding, ec.ECDSA(hashes.SHA256())).hex()
        spki = key.public_key().public_bytes(serialization.Encoding.DER,
                                            serialization.PublicFormat.SubjectPublicKeyInfo)
        print(json.dumps({"note": f"probe presented a fresh self-signed key, SPKI sha256 {fp16(spki)}…, "
                                  f"signature {'valid' if a.hello == 'forged' else 'made with a different key'}"}))
    send_frame(tls, {"jsonrpc": "2.0", "id": 1, "method": "n2n/hello", "params": params})
    resp = read_frame(tls)
    err = (resp or {}).get("error")
    after, how = drain(tls, wait=3)
    out(f"§6.3/§6.4 n2n/hello ({a.hello}) refused", bool(err),
        (f"error {err.get('code')} '{err.get('message')}'" if err else f"response {str(resp)[:160]}")
        + f"; then {how}")
    tls.close()
    return bool(err)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("discriminate", "timeouts"):
        q = sub.add_parser(name)
        q.add_argument("host")
        q.add_argument("port", type=int)
        q.add_argument("--no-bgp", action="store_true", help="skip the 0xFF/BGP check")
    q = sub.add_parser("handshake")
    q.add_argument("host")
    q.add_argument("port", type=int)
    q.add_argument("asn", type=int)
    q.add_argument("rid")
    q.add_argument("--hello", choices=("none", "keyless", "forged", "badsig"), default="none")
    q.add_argument("--tls12", action="store_true")
    q.add_argument("--sni", default="")
    a = p.parse_args()
    ok = {"discriminate": cmd_discriminate, "timeouts": cmd_timeouts, "handshake": cmd_handshake}[a.cmd](a)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
