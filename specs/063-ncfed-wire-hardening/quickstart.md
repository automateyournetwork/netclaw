# Quickstart: Verify NCFED Wire Hardening (063)

Verifies each story, including honest stack-gated behavior. Originally written for Python 3.10 / OpenSSL 3.0.2; the host is now Python 3.14 / OpenSSL 3.5 (research R0-addendum), where OpenSSL negotiates X25519MLKEM768 by default but the Python group APIs (`set_groups`/`SSLObject.group`) remain absent until Python 3.15 — so `pq_available` is still honestly `false` here.

## P1 — Endpoint persistence (the confirmed bug)

```bash
# 1. Dial a peer at a fresh address
curl -s -X POST http://127.0.0.1:8179/n2n/connect -H 'Content-Type: application/json' \
  -d '{"peer":"as65007-7.7.7.7","host":"NEW.tcp.ngrok.io","port":NNNNN}'
# 2. Confirm it PERSISTED (only after the channel came up):
python3 - <<'PY'
import sqlite3; c=sqlite3.connect("/home/USER/.openclaw/n2n/federation.db")
print(c.execute("SELECT endpoint_host,endpoint_port,endpoint_updated_at FROM federation_peer WHERE peer_as=65007").fetchone())
PY
# 3. Restart the mesh daemon, do NOT re-dial:
systemctl --user restart netclaw-mesh.service
# 4. PASS: supervisor reconnects to NEW.tcp.ngrok.io:NNNNN with zero manual action.
#    Negative: a dial to a bad port must NOT overwrite the good stored address.
```

## P2 — Mesh-layer TLS (gated by enforcement flag)

```bash
# With mesh-TLS enforced on both ends, capture the mesh session:
sudo tcpdump -i any -s0 -U -w /tmp/mesh.pcap 'tcp port <mesh-port>'
# PASS: after the BGP OPEN, traffic is TLS (type-23 records); KEEPALIVEs are no longer
# readable 19-byte 0xff-marker BGP messages on an untrusted leg.
# A non-upgraded mesh peer is refused with an actionable reason (enforce mode).
```

## P3 — Metadata (stack-gated: document on this host)

```bash
# On THIS stack (Python <= 3.14: no ssl ECH API even on OpenSSL 3.5): the claw-domain SNI is still visible — expected + documented.
tshark -r capture.pcap -Y "tls.handshake.type==1" -T fields -e tls.handshake.extensions_server_name
# PASS-here: SNI present AND the daemon/docs report it as an accepted residual (no ECH on this stack).
# PASS-on-ECH-stack: SNI concealed once the ECH seam activates (OpenSSL/Python that support ECH).
```

## P4 — PQ posture + visibility

```bash
# See the posture + what each channel negotiated:
curl -s http://127.0.0.1:8179/n2n/certs   | python3 -m json.tool | grep -E 'pq|kex|cipher|tls_version'
curl -s http://127.0.0.1:8179/n2n/posture | python3 -m json.tool | grep -E 'pq_mode|pq_available'
# On THIS stack: pq_available=false, kex_group="unknown", cipher/tls_version populated — honest.
# require mode on a non-PQ stack must FAIL FAST at startup:
N2N_PQ_MODE=require systemctl --user restart netclaw-mesh.service
journalctl --user -u netclaw-mesh.service -n5   # expect: clear "PQ not available on this crypto stack" error
# On an OpenSSL>=3.5 / Python>=3.15 stack: a PQ-capable peer shows kex_group=X25519MLKEM768, pq=available.
# NOTE (R0-addendum): on OpenSSL>=3.5 with Python<=3.14 the wire may already be
# X25519MLKEM768 (OpenSSL default groups) — verify with tcpdump/tshark, not posture;
# posture honestly reports unavailable because Python cannot read the group until 3.15.
```

## Regression

```bash
python3 -m pytest tests/n2n/ -q     # full federation suite stays green
# Existing peers keep federating with no re-consent/re-pin (P1/P3/P4 are back-compatible;
# only P2 mesh-TLS is a coordinated flag-day, gated behind the enforcement flag).
```
