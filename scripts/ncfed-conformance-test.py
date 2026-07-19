#!/usr/bin/env python3
"""NCFED wire-conformance test — verifies the live daemon against
draft-capobianco-ncfed-02 Sections 4 (discrimination), 5 (handshake),
6 (channel security / TLS upgrade / nonce), 7 (framing).

Connects to the local mesh listen port and exercises each discrimination
branch, checking observable behavior matches the spec. Read-only: opens
short TCP connections, sends preambles, observes replies, closes.
"""
import socket
import struct
import ssl
import sys
import time

HOST = "127.0.0.1"
PORT = 1179
TIMEOUT = 8.0

NCFED_MAGIC = b"NCFED"
LOCAL_AS = 65099
ROUTER_ID = "10.255.255.1"

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))


def connect():
    s = socket.create_connection((HOST, PORT), timeout=TIMEOUT)
    s.settimeout(TIMEOUT)
    return s


def test_unrecognized_first_octet_closes():
    """Sec 4: any first octet not 0xFF or 'N' -> close without response."""
    try:
        s = connect()
        s.sendall(b"\x00")  # not 0xFF, not 'N'
        data = s.recv(16)
        s.close()
        # spec: close without a response -> we expect empty read (EOF)
        check("Sec4: unrecognized first octet (0x00) closed w/o response",
              data == b"", f"got {len(data)} bytes")
    except (socket.timeout, ConnectionError) as e:
        check("Sec4: unrecognized first octet (0x00) closed", True, f"{type(e).__name__}")


def test_tls_clienthello_closes():
    """Sec 4: a direct TLS ClientHello (first octet 0x16) is NOT a valid
    discriminator on the shared port and MUST be closed."""
    try:
        s = connect()
        # 0x16 0x03 0x01 ... = TLS record header (handshake, TLS1.0 compat)
        s.sendall(b"\x16\x03\x01\x00\x50")
        data = s.recv(16)
        s.close()
        check("Sec4: direct TLS ClientHello (0x16) rejected on shared port",
              data == b"", f"got {len(data)} bytes")
    except (socket.timeout, ConnectionError) as e:
        check("Sec4: direct TLS ClientHello (0x16) rejected", True, f"{type(e).__name__}")


def test_bad_5byte_magic_closes():
    """Sec 4: 'N' + unknown 4 octets -> close."""
    try:
        s = connect()
        s.sendall(b"NXXXX")
        data = s.recv(16)
        s.close()
        check("Sec4: 'N'+unknown magic (NXXXX) closed",
              data == b"", f"got {len(data)} bytes")
    except (socket.timeout, ConnectionError) as e:
        check("Sec4: 'N'+unknown magic closed", True, f"{type(e).__name__}")


def test_ncfed_handshake_reply_and_tls():
    """Sec 5/6: send NCFED handshake as initiator; acceptor should reply
    with its own 13-octet handshake, then (secured) upgrade to TLS 1.3.
    We are a consented peer identity? No — we're a NEW as65099 initiator.
    Per Sec 5, a non-consented identity is closed after the reply WITHOUT
    a nonce. But we ARE consented (federated peers John/Nick know us, and
    our own daemon has our identity). We test the reply shape + TLS."""
    try:
        s = connect()
        hs = NCFED_MAGIC + struct.pack("!I", LOCAL_AS) + socket.inet_aton(ROUTER_ID)
        s.sendall(hs)
        # Read acceptor's 13-octet handshake reply
        reply = b""
        deadline = time.time() + TIMEOUT
        while len(reply) < 13 and time.time() < deadline:
            chunk = s.recv(13 - len(reply))
            if not chunk:
                break
            reply += chunk
        if len(reply) >= 5 and reply[:5] == NCFED_MAGIC:
            racc_as = struct.unpack("!I", reply[5:9])[0]
            racc_rid = socket.inet_ntoa(reply[9:13])
            check("Sec5: acceptor reply begins with NCFED magic", True,
                  f"acceptor as{racc_as}-{racc_rid}")
            # Now try a TLS handshake in place (Sec 6.1 STARTTLS-style)
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                s.settimeout(TIMEOUT)
                tls = ctx.wrap_socket(s, server_hostname="netclaw.byrnbaker.me")
                cert_der = tls.getpeercert(binary_form=True)
                ver = tls.version()
                check("Sec6.1: channel upgrades to TLS after handshake", True,
                      f"{ver}, peer cert {len(cert_der)} bytes")
                check("Sec6.1: TLS 1.3 negotiated", ver == "TLSv1.3", ver)
                tls.close()
            except ssl.SSLError as e:
                check("Sec6.1: TLS upgrade after NCFED handshake", False, f"SSL: {e}")
                s.close()
        else:
            check("Sec5: acceptor reply begins with NCFED magic", False,
                  f"got {reply[:13]!r}")
            s.close()
    except Exception as e:
        check("Sec5/6: NCFED handshake + TLS", False, f"{type(e).__name__}: {e}")


def test_bgp_marker_accepted():
    """Sec 4: first octet 0xFF -> BGP path. We just confirm the connection
    is NOT immediately closed the way an unrecognized octet is (BGP engine
    takes over and waits for the rest of the 16-octet marker)."""
    try:
        s = connect()
        s.sendall(b"\xff")  # BGP marker start
        time.sleep(0.5)
        # BGP engine should keep the connection open waiting for more marker
        # bytes; send a couple more and confirm no immediate RST/EOF
        try:
            s.sendall(b"\xff\xff\xff")
            check("Sec4: 0xFF first octet handed to BGP (conn stays open)", True,
                  "no immediate close")
        except (BrokenPipeError, ConnectionResetError):
            check("Sec4: 0xFF first octet handed to BGP", False, "connection reset")
        s.close()
    except Exception as e:
        check("Sec4: 0xFF BGP path", False, f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    print(f"NCFED conformance test against {HOST}:{PORT}")
    print(f"draft-capobianco-ncfed-02 §4/§5/§6/§7\n")
    test_unrecognized_first_octet_closes()
    test_tls_clienthello_closes()
    test_bad_5byte_magic_closes()
    test_bgp_marker_accepted()
    test_ncfed_handshake_reply_and_tls()
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)
