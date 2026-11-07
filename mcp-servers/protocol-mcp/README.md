# protocol-mcp — eN2N Federation Protocol Server

MCP server implementing the NCFED (NetClaw Federation) protocol for
inter-claw communication over the eN2N mesh.

Core modules:
- `bgp-daemon-v2.py` — main HTTP control plane + eN2N listener
- `bgp/federation/` — channel management, TLS (060), endpoint persistence (063)
- `server.py` — MCP tool surface (`n2n_health`, `n2n_status`, `n2n_connect`, etc.)

Maintainer R08/Spec179 source adds the private `bgp/federation/ha/` authority and
execution adapters. Signed manifests bind cluster generation, node keys and
endpoints; etcd holds the single execution authority and shared decisions.
Members use three strict iN2N attachments and fresh model/native handoff admission.
This adds no MCP server, public admin API or advertised installer option. A durable
HA marker forbids standalone fallback. The private operator CLI is
`scripts/ha-cluster.py`; source rehearsal and evidence are in `labs/ha/` and
`specs/179-border-ha-authority/`. Fixture, REAL and native client qualification
are separate gates; R09 region-loss qualification and roadmap release remain held.

---

## Agent Turn Dispatch: WS RPC, not CLI-per-turn (Feature 116)

> **READ THIS before changing `gateway.py::run_agent_turn()`'s default dispatch path.**

`run_agent_turn()` (the sole function every channel — chat, Slack-via-OpenClaw, the phone's "Ask
NetClaw", eN2N peer skill delegation — funnels through to get an agent to actually answer) dispatches
via a **persistent WebSocket JSON-RPC connection** to the local OpenClaw gateway
(`bgp/federation/gateway_ws.py`), not a per-turn `openclaw agent --json` CLI subprocess.

**Do not revert this to a CLI subprocess.** It used to be one, and every single turn — regardless of
channel or answer length — paid a fixed ~27 second cost before any real work started, because the
CLI's own gateway-dispatch code (`openclaw`'s bundled `agent-via-gateway-*.js`) unconditionally sets
`cleanupBundleMcpOnRunEnd: true`, which tears down the gateway's session-scoped MCP tool runtime
cache after every turn. OpenClaw's own internal `sessions_send` tool proves the cache is meant to be
reused across turns sharing a session key — it calls the identical gateway `agent` RPC method the
same way and simply omits that flag. `gateway_ws.py`'s `GatewayWsClient` does the same: one
persistent connection per Border process, no forced teardown, so a session's second and later turns
are ~6x faster than its first (measured live: cold ~35s, warm ~6s).

The embedded (`local=True`) dispatch path — used by iN2N members running their own model/provider
in-process (feature 056) — is unchanged and still shells out to the CLI; it never goes through a
gateway at all, so this fix doesn't apply to it.

Full root-cause analysis, live measurements, and the wire protocol this client implements:
`specs/116-border-turn-latency/research.md` and `specs/116-border-turn-latency/contracts/`.

---

## Cloudflare Tunnel Transport (Feature 108)

> **READ THIS BEFORE writing a `cloudflared` config for eN2N traffic.**

### Fixed Architectural Decision: TCP / Private-Network Mode ONLY

| Aspect | Decision |
|--------|----------|
| **Required mode** | TCP / private-network (opaque byte relay) |
| **Forbidden mode** | HTTP(S) ingress — **NEVER** for eN2N traffic |
| **Configurability** | None. This is a fixed decision (FR-009), not operator-selectable. |

### Why — Confidentiality Rationale

The eN2N listener speaks **NCFED**, a custom framed protocol (`NCFED_MAGIC`
handshake → TLS upgrade → JSON-RPC 2.0 frames). It is not HTTP.

If `cloudflared` were configured in HTTP(S) ingress mode:

1. Cloudflare's edge would terminate TLS on behalf of the origin.
2. NCFED payload would transit Cloudflare infrastructure **in plaintext**
   (or re-encrypted under Cloudflare's own keys, not the peers' keys).
3. This is a **confidentiality regression** — the whole point of spec 060's
   in-protocol TLS is that only the two authenticated peers can decrypt
   the channel. Delegating decryption to an intermediary defeats that.

In TCP / private-network mode:

- `cloudflared` relays **opaque bytes** end-to-end.
- Cloudflare's infrastructure never observes decrypted NCFED payload.
- Spec 060's peer-to-peer TLS remains the **sole layer** that can decrypt.
- Consistent with spec 063 R2's principle: *"encrypt in-protocol, don't rely
  on an incidental transport"* — applied here to the transport choice itself.

### Correct `config.yml` Ingress (Example)

```yaml
# /etc/cloudflared/config.yml (or ~/.cloudflared/config.yml)
tunnel: <TUNNEL-UUID>
credentials-file: /path/to/credentials.json

ingress:
  # eN2N federation listener — TCP mode, opaque relay
  - hostname: netclaw-en2n.example.com
    service: tcp://127.0.0.1:7179    # local eN2N listener port
  # Catch-all (required by cloudflared)
  - service: http_status:404
```

**Key points:**
- The `service:` value is `tcp://...` — this tells `cloudflared` to relay raw
  TCP, not interpret it as HTTP.
- The hostname resolves via Cloudflare DNS (CNAME to the tunnel), giving the
  stable address that eliminates ngrok-style address rot (spec 108, US1).
- The local port (`7179` above) must match the eN2N listener's bind port in
  `bgp-daemon-v2.py`.

### What NOT to Do

```yaml
# ❌ WRONG — HTTP(S) ingress. Cloudflare terminates TLS at the edge.
ingress:
  - hostname: netclaw-en2n.example.com
    service: https://127.0.0.1:7179   # BREAKS CONFIDENTIALITY
```

```yaml
# ❌ WRONG — HTTP mode. NCFED is not HTTP; this will fail AND leak.
ingress:
  - hostname: netclaw-en2n.example.com
    service: http://127.0.0.1:7179    # PROTOCOL MISMATCH + LEAK
```

### Deployment

For the full deployment procedure (tunnel creation, DNS binding, systemd unit,
smoke tests), see:

- **Quickstart**: `specs/108-cloudflare-tunnel-transport/quickstart.md`
- **Durable service pattern**: `scripts/cloudflared-transport.sh` (mirrors
  spec 057's `in2n-services.py` systemd-unit generation)

### Related Specs

| Spec | Relevance |
|------|-----------|
| 060 | In-protocol TLS — the peer-to-peer encryption that this decision protects |
| 063 | Endpoint persistence — the mechanism that stores the stable tunnel address |
| 057 | Durable service pattern — `cloudflared` runs as a systemd unit, not ad-hoc |
| 108 | This feature — Cloudflare Tunnel as a hardened transport |
