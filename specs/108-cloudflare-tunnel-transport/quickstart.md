# Quickstart: Verify Cloudflare Tunnel Transport (108)

Reference deployment: this claw is `as65099-10.255.255.1`, domain `byrnbaker.me` (Cloudflare-managed DNS), the same host referenced throughout specs 057/060/063. Peers `as65001-4.4.4.4` (John) and `as65007-7.7.7.7` (Nick) are the two live peers whose ngrok-address rot motivated this feature — full end-to-end validation against them requires *they* also adopt Cloudflare Tunnel (this feature never requires that; see Assumptions in spec.md), but US1's core claim (this claw's own endpoint survives restarts) is fully verifiable unilaterally.

## US1 — Endpoint never goes stale (the confirmed bug this feature fixes)

```bash
# 1. One-time: create the tunnel and bind a stable hostname (ops layer, see contracts/interfaces.md)
cloudflared tunnel create netclaw-byrnbaker
cloudflared tunnel route dns netclaw-byrnbaker netclaw-en2n.byrnbaker.me
# config.yml ingress: TCP/private-network mode targeting the local eN2N listener port — NOT http/https ingress.

# 2. Install as a durable service (mirrors spec 057's mesh-daemon pattern)
systemctl --user enable --now cloudflared-netclaw-byrnbaker.service

# 3. Tell the daemon this is now the advertised transport for outbound dials
curl -s -X POST http://127.0.0.1:8179/n2n/connect -H 'Content-Type: application/json' \
  -d '{"peer":"as65007-7.7.7.7","host":"netclaw-en2n.byrnbaker.me","port":<TUNNEL_PORT>,"transport":"cloudflare_tunnel"}'

# 4. Confirm it persisted, including the new transport field:
python3 - <<'PY'
import sqlite3; c=sqlite3.connect("/home/USER/.openclaw/n2n/federation.db")
print(c.execute("SELECT endpoint_host,endpoint_port,transport,endpoint_updated_at FROM federation_peer WHERE peer_as=65007").fetchone())
PY

# 5. Restart BOTH the tunnel and the mesh daemon, do NOT re-dial or reconfigure anything:
systemctl --user restart cloudflared-netclaw-byrnbaker.service
systemctl --user restart netclaw-mesh.service

# 6. PASS: the hostname is unchanged (it's a fixed DNS name, not a rotated ngrok URL) —
#    the reconnect supervisor targets the SAME netclaw-en2n.byrnbaker.me:<TUNNEL_PORT>
#    with zero manual action, zero n2n_forget_endpoint call needed.
#    Contrast with the pre-108 failure: an ngrok restart would have produced a NEW
#    host:port with no live channel left to announce it (research.md R0).

# 7. Also restart the whole host — PASS: hostname survives (it's DNS, not process state).
```

## US2 — Unauthenticated probes never reach the NCFED listener (Access edge-gate, opt-in)

```bash
# 1. In the Cloudflare dashboard (or API), attach an Access policy requiring
#    mTLS client cert (or a service token) to the tunnel's hostname.

# 2. Enable it for ONE peer only (per-peer opt-in, default off — Clarifications):
curl -s -X POST http://127.0.0.1:8179/n2n/peer/edge_gate -H 'Content-Type: application/json' \
  -d '{"peer":"as65007-7.7.7.7","edge_gate":"cloudflare_access"}'

# 3. Attempt a connection with NO client credential (simulating a random prober):
#    PASS: connection refused at Cloudflare's edge. Confirm zero NCFED bytes reached
#    the listener — no discrimination-preamble log line, no audit row, nothing:
journalctl --user -u netclaw-mesh.service --since "1 min ago" | grep -i "netclaw-en2n" || echo "PASS: no listener-side trace of the rejected attempt"

# 4. Attempt a connection WITH the correct client credential:
#    PASS: reaches the listener, proceeds to normal spec-060 TLS + peer-identity
#    negotiation exactly as an Access-free connection would (FR-004 — Access never
#    replaces or weakens 060's identity check, by construction, not by extra code).

# 5. Confirm a SECOND peer with edge_gate still "none" is completely unaffected:
curl -s http://127.0.0.1:8179/n2n/health | python3 -m json.tool | grep -A3 '"as65001-4.4.4.4"'
# PASS: edge_gate: "none", behaves exactly as before this feature — Access is never
# silently implied by adopting cloudflare_tunnel transport alone.
```

## US3 — Transport and edge-gate status are visible in existing posture view

```bash
curl -s http://127.0.0.1:8179/n2n/posture | python3 -m json.tool | grep -E 'transport|edge_gate|local_transport_healthy'
# PASS: every peer row shows transport (ngrok|cloudflare_tunnel|other) and edge_gate
# (none|cloudflare_access) alongside the existing 060 trust-model/credential fields —
# no second tool, no second view.

curl -s http://127.0.0.1:8179/n2n/health | python3 -m json.tool | grep local_transport_healthy
# PASS: reflects this claw's OWN tunnel health, independent of any specific peer.
```

## Fault classification — transport outage vs. peer-down (extends spec 057)

```bash
# Simulate a local tunnel outage (stop cloudflared without touching any peer):
systemctl --user stop cloudflared-netclaw-byrnbaker.service

curl -s http://127.0.0.1:8179/n2n/faults | python3 -m json.tool
# PASS: fault_class names the transport-layer condition explicitly (e.g. "transport"),
# distinct from "member" — the operator is told "your own tunnel is down," not
# "peer X is flapping." Restart the service and confirm fault_class returns to "none"
# once the tunnel and any dependent channels recover:
systemctl --user start cloudflared-netclaw-byrnbaker.service
```

## Degradation check — an operator who never adopts this feature sees zero change

```bash
# On a peer still configured with transport unset/default:
curl -s http://127.0.0.1:8179/n2n/health | python3 -m json.tool | grep -B2 -A2 '"transport": "ngrok"'
# PASS: identical behavior to pre-108 — this field simply documents what was already true.
```
