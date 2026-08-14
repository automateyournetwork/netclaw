# Contract: Operator & Wire Interface Deltas (108)

Deltas only — everything else is unchanged from 057/060/063.

## Daemon HTTP (localhost:8179)

| Route | Change |
|---|---|
| `POST /n2n/connect` | Gains an optional `transport` field (`ngrok`\|`cloudflare_tunnel`\|`other`, default `ngrok` when omitted — existing callers/scripts unaffected). On a **successful, authenticated** channel (same precondition 063 already established for endpoint persistence), persist `transport` to the peer record alongside the existing `endpoint_host`/`endpoint_port` write. No new field is required to specify Access — that's edge-side config, not a per-connect argument. |
| `POST /n2n/peer/edge_gate` (new, small) | Operator-facing toggle: `{"peer": "as65007-7.7.7.7", "edge_gate": "cloudflare_access"\|"none"}`. Sets `federation_peer.edge_gate` directly (US2) — independent of, and does not require, changing `transport`. Defaults every peer to `none`; this route is the only way to change it (never implied by adopting `cloudflare_tunnel` transport — Clarifications). |
| `GET /n2n/health` (existing `n2n_health` backing route) | Each peer entry gains `transport` and `edge_gate` (US3). The overall response gains `local_transport_healthy` (`true`\|`false`\|`"n/a"`) describing *this claw's own* advertised endpoint, not any specific peer (data-model.md §2). |
| `GET /n2n/faults` (existing `n2n_faults` backing route) | `fault_class` gains a new distinguishable value/cause: when a peer channel is down **and** `local_transport_healthy=false`, the fault is attributed to this claw's own transport layer, named explicitly (e.g. `fault_class: "transport"`, distinct from `daemon`/`member`/`backend`/`none`) — never folded into a generic member-down report, matching spec 057's stated fault-isolation principle. When `local_transport_healthy` is `true` or `n/a`, classification is byte-for-byte unchanged from today. |
| `GET /n2n/posture` | Per-peer entries in the existing trust-model/credential view gain `transport` and `edge_gate` (US3, same fields as `/n2n/health`, same source row — one write, two read surfaces, consistent with how 060/063 already expose the same underlying facts from both `/n2n/certs`-style and `/n2n/posture`-style endpoints). |

## MCP tool surface (`n2n-mcp`)

No new tool names required for US1 or US3 — `n2n_health`, `n2n_status`, `n2n_faults` response shapes simply carry the new fields above, since they proxy the daemon HTTP routes directly (per the `n2n-federation` skill's existing tool-to-route mapping).

US2 gains one new tool, mirroring the existing small-surface pattern (`n2n_forget_endpoint` from spec 100 is the closest precedent — a single-purpose, explicitly-named operator action):

| Tool | Signature | Behavior |
|---|---|---|
| `n2n_set_edge_gate` | `(peer: str, edge_gate: "cloudflare_access"\|"none")` | Proxies `POST /n2n/peer/edge_gate`. Explicitly per-peer, explicitly opt-in each way — no bulk/"enable for all peers" variant, so an operator must deliberately choose each peer, matching the Clarifications resolution that default-on-for-all-peers would force uncoordinated re-credentialing. |

## Ops layer (not wire, not MCP) — `cloudflared` deployment

Not a code contract, but a repeatable deployment contract analogous to spec 057's `in2n-services.py generate`/`enable`/`status` pattern:

```
cloudflared tunnel create <claw-name>              # one-time: creates tunnel + credentials file
cloudflared tunnel route dns <claw-name> <hostname> # binds the stable DNS hostname
# config.yml: ingress rule maps the hostname to the LOCAL eN2N listener port,
#   in TCP/private-network mode (R1) — never http/https ingress type.
systemctl --user enable --now cloudflared-<claw-name>.service   # durable, mirrors netclaw-mesh.service
```

The federation daemon's `asyncio.start_server`/`asyncio.open_connection` calls (`bgp-daemon-v2.py`, `bgp/federation/service.py`) are **unchanged** — `cloudflared` makes the configured `host:port` resolve and route correctly from the outside; the Python code has no awareness of which transport delivered a given TCP connection, exactly as it has no awareness today of whether ngrok or a direct route delivered it.

## Wire — NCFED channel

**Unchanged.** No discrimination-preamble, handshake, or TLS-upgrade wire-format change (FR-008). This is the entire point of choosing TCP/private-network tunnel mode (R1) — `cloudflared` relays opaque bytes; the NCFED protocol running inside is byte-for-byte identical to a direct or ngrok-carried connection.

## Degradation contract (honesty, mirrors 063's own degradation contract)

- An operator who never configures `cloudflared` sees `transport: "ngrok"` (or whatever they already had) on every peer, `local_transport_healthy: "n/a"`, and zero behavior change — this feature must never make a claw that hasn't adopted it behave differently.
- An operator who adopts `cloudflare_tunnel` transport but never enables Access sees `edge_gate: "none"` on every peer and functions exactly as if they were still on ngrok, just with a stable address — Access is never silently implied.
- A local tunnel/DNS health-probe failure MUST be visible (`local_transport_healthy: false`) and MUST drive `fault_class` toward the new transport-specific value rather than silently degrading to a misleading `member`/`backend` classification.
