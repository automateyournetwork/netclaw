#!/usr/bin/env python3
"""Probe the consent-gated handshake distinction (draft Sec 5 vs implementation).

Connects claiming a CONSENTED peer identity (John, as65001-4.4.4.4) and a
NON-CONSENTED identity, comparing whether the acceptor sends its 13-octet
handshake reply before closing. This isolates the spec discrepancy:

  draft Sec 5:  acceptor closes AFTER its handshake reply (no nonce) when
                the claimed identity is not consented.
  observed:     acceptor closes WITHOUT any reply for a non-consented (or
                self) identity — it never reveals its own AS/router-id.
"""
import socket, struct, time

HOST, PORT, TIMEOUT = "127.0.0.1", 1179, 6.0
NCFED_MAGIC = b"NCFED"

def probe(as_num, router_id, label):
    try:
        s = socket.create_connection((HOST, PORT), timeout=TIMEOUT)
        s.settimeout(TIMEOUT)
        s.sendall(NCFED_MAGIC + struct.pack("!I", as_num) + socket.inet_aton(router_id))
        reply = b""
        deadline = time.time() + 3
        while len(reply) < 13 and time.time() < deadline:
            try:
                chunk = s.recv(13 - len(reply))
            except socket.timeout:
                break
            if not chunk:
                break
            reply += chunk
        s.close()
        got_reply = len(reply) >= 5 and reply[:5] == NCFED_MAGIC
        print(f"  {label} (as{as_num}-{router_id}): "
              f"{'GOT 13-octet reply' if got_reply else f'closed, {len(reply)} bytes'}")
        return got_reply
    except Exception as e:
        print(f"  {label}: {type(e).__name__}: {e}")
        return None

if __name__ == "__main__":
    print("Consent-gated handshake probe (draft Sec 5)\n")
    print("Consented peer (John):")
    john = probe(65001, "4.4.4.4", "consented")
    print("\nNon-consented stranger:")
    stranger = probe(65123, "203.0.113.99", "stranger")
    print("\nSelf identity (no peer consent record):")
    myself = probe(65099, "10.255.255.1", "self")
    print("\n--- Finding ---")
    if john and not stranger:
        print("  Consented peer gets the handshake reply; stranger is closed silently.")
        print("  Implementation closes a NON-consented peer WITHOUT a handshake reply,")
        print("  which is STRICTER than draft Sec 5 ('close after its handshake reply').")
        print("  Recommend draft Sec 5 wording: acceptor MAY close without any reply")
        print("  to avoid revealing its AS/router-id to an unconsented peer.")
    elif john is False:
        print("  Even consented John got no reply — consent record may be missing;")
        print("  check /n2n/health for as65001-4.4.4.4 consent state.")
