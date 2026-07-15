# N2N — Peering NetClaws

**NetClaw-to-NetClaw (N2N) Federation** turns a set of independently-operated
NetClaw instances into a federated mesh of AI network engineers that can
discover, use, and converse with one another — safely, and only between
operators who both opt in. This document covers **eN2N** (external federation
between different operators). For **iN2N** — one operator's own group of focused
claws behind a Border Claw ("a risk of NetClaws") — see
[docs/N2N-RISK.md](docs/N2N-RISK.md) and the [eN2N vs iN2N](#en2n-vs-in2n--external-federation-vs-a-risk-of-netclaws) summary below.

> **Is N2N a new protocol?** Yes. **NCFED** is a new application-layer protocol
> introduced by NetClaw. It is *not* BGP and not a reuse of an existing wire
> format — it is a purpose-built federation protocol that rides the NetClaw
> mesh transport. It speaks **JSON-RPC 2.0** and borrows semantics from two
> open agent standards: **MCP** (Model Context Protocol) for tool invocation
> and **A2A** (Agent2Agent) for capability discovery, task delegation, and
> streaming chat. See [Is N2N a new protocol?](#is-n2n-a-new-protocol) below.

---

## What you can do once two NetClaws are federated

- **Discover capabilities** — ask your own claw "does Nicholas's claw have CML?"
  or "what skills does Byrn have that I don't?" and get an answer from a signed
  capability inventory the peer advertised.
- **Invoke remote tools/skills** — "list the labs on Nicholas's CML server"
  runs on *his* claw with *his* credentials, and only the result comes back.
  Every call is default-deny, allowlisted per peer, optionally human-approved,
  budgeted, and audited on both sides.
- **Chat claw-to-claw** — "ask Byrn's claw why its OSPF area 0 is flapping"
  relays to Byrn's agent, which answers under his policies; the reply streams
  back attributed to Byrn's claw.
- **See it in the HUD** — each remote claw node expands to show its skills,
  MCP tools, capability badges (CML, pyATS, Meraki…), inventory freshness, and
  a chat box.

Everything is governed by **mutual consent per peer**, a **kill switch** that
severs federation without dropping BGP, and the ironclad rule that **no
credentials, `.env` values, device addresses, or testbed secrets ever leave a
claw** — only capability names and descriptions.

---

## The stack, in one picture

```
   Operator (Slack / Webex / CLI / HUD)
        │  asks "does Nicholas have CML?" / "run his cml list" / "ask Byrn about OSPF"
        ▼
   n2n-mcp  (FastMCP, stdio)  ──HTTP──►  bgp-daemon-v2  /n2n/* API (127.0.0.1:8179)
                                              │
                                              │  FederationService
                                              ▼
   ┌──────────────────────── NCFED channel ────────────────────────┐
   │  JSON-RPC 2.0 over the existing mesh port (ngrok TCP)          │
   │  discriminated alongside BGP (0xFF) and NCTUN tunnels          │
   │  MCP-shaped tools/call · A2A-shaped tasks + chat streaming     │
   └────────────────────────────────────────────────────────────────┘
                                              ▲
                                              │  same channel, other operator's daemon
                                     Peer NetClaw (Nicholas / Byrn)
```

The BGP mesh (identity routes, who-is-peered) is the **control plane**. N2N is
the **application layer** on top of it.

---

## Is N2N a new protocol?

**Yes — NCFED is a new protocol, layered on the existing mesh transport.**

| Layer | What it is | New? |
|-------|-----------|------|
| Mesh transport | TCP to a peer's public endpoint (e.g. ngrok), shared with BGP | Existing |
| Protocol discrimination | First bytes select BGP (`0xFF`), tunnel (`NCTUN`), or **federation (`NCFED`)** | **NCFED branch is new** |
| **NCFED channel** | **Framed JSON-RPC 2.0 with a handshake, heartbeats, and chunking** | **New** |
| Semantics | MCP `tools/list`/`tools/call` for tools; A2A AgentCard/task/stream for discovery, skill delegation, and chat | Borrowed from open standards |

Why not just use A2A or MCP directly?

- **MCP** is request/response tool invocation — perfect for "run this tool,"
  wrong for long-running delegated tasks and streaming chat.
- **A2A** is purpose-built for agent-to-agent tasks and streaming, but assumes
  HTTPS + a new well-known endpoint per agent — which would violate N2N's
  "no new inbound exposure" rule and double ngrok endpoint churn.

So NCFED takes the **semantics** of both (they are both JSON-RPC 2.0) and binds
them to the **transport we already have** — the authenticated mesh channel — so
federation works *everywhere BGP already works*, with no new open ports.

### NCFED wire format (summary)

```
Discrimination:  'N' + "CFED" + <4-byte AS> + <4-byte router-id>   (lower-AS initiates)
Framing:         [4-byte length][1-byte flags][UTF-8 JSON-RPC 2.0]  (flags bit0 = chunk)
Heartbeat:       empty frame every 30s; 3 misses = channel down
Identity:        BGP identity  as<AS>-<router-id>  (survives endpoint changes)
```

Methods: `n2n/hello`, `n2n/consent_state`, `n2n/sever`, `n2n/inventory`,
`n2n/inventory_get`, `n2n/tools/call`, `n2n/tasks/submit`, `n2n/chat/open`,
`n2n/chat/message`. Full contract in
[`specs/052-n2n-federation/contracts/n2n-wire-protocol.md`](specs/052-n2n-federation/contracts/n2n-wire-protocol.md).

---

## Peering two NetClaws — the flow

Prerequisite: both claws are already mesh-peered (BGP Established), and both set
`N2N_ENABLED=true` and restarted the mesh daemon.

1. **Confirm identities out-of-band.** Exchange AS + router-id (e.g. in Slack):
   "I'm AS 65001 / 4.4.4.4."
2. **Both operators consent** (mutual — nothing flows until both do):
   - John: *"Federate with Nicholas, AS 65007, router-id 7.7.7.7"*
   - Nicholas: *"Federate with John, AS 65001, router-id 4.4.4.4"*
3. The lower-AS side opens the NCFED channel; inventories exchange automatically.
   HUD claw nodes flip to **federated**.
4. **Browse:** *"What can Nicholas's claw do?"*
5. **Grant + invoke:** Nicholas *"let John run my cml list_labs"*; John *"list
   the labs on Nicholas's CML."*
6. **Chat:** enable per-peer, then *"ask Byrn's claw why OSPF area 0 is flapping."*
7. **Sever anytime:** *"kill federation with Nicholas"* — N2N stops instantly,
   BGP keeps running.

Step-by-step with exact tool calls:
[`specs/052-n2n-federation/quickstart.md`](specs/052-n2n-federation/quickstart.md).

---

## How other operators join your mesh with this capability

A peer running an older NetClaw stays on the mesh unaffected (they simply show
as *not federated*). To gain N2N they:

1. `git pull` NetClaw (or apply the N2N patch) to get the `bgp/federation/`
   package, `n2n-mcp`, and the daemon changes.
2. Set `N2N_ENABLED=true` (and optional `N2N_*` tuning) in `~/.openclaw/.env`.
3. Install `n2n-mcp` deps and reload MCP servers:
   `pip install -r mcp-servers/n2n-mcp/requirements.txt` then
   `openclaw mcp reload` (or restart the gateway).
4. Restart the mesh daemon so the NCFED discrimination branch is live.
5. Complete mutual consent with each peer (step 2 above).

---

## Safety model

- **Mutual consent per peer** before any capability data is exchanged.
- **Default-deny** remote invocation; explicit per-peer allowlists; optional
  human approval; per-peer daily budgets + rate limits.
- **No secrets ever leave** — inventories carry names/descriptions only, and a
  build-time guard aborts advertisement if any `.env` value appears.
- **Remote results are untrusted input** — displayed and reasoned over, never
  auto-executed.
- **Kill switch** severs N2N in <10s without touching the BGP session.
- **Dual-side audit** of every invocation and chat; DefenseClaw guardrail
  inspection of inbound tool calls when enabled.

---

## Reliability & ergonomics (feature 053)

The protocol self-heals so you don't babysit it across restarts:

- **Async task delegation** — long remote operations (e.g. recreating a 10-node
  CML lab) run as background tasks: `n2n_delegate` returns a `task_id`
  instantly, you poll `n2n_task_status` / fetch `n2n_task_result`. No single
  call is long enough for ngrok to reset — the fix for "Connection lost"
  mid-build. Use delegation, not chat, for multi-minute work.
- **Channel auto-reconnect** — a peer restart no longer wedges federation; the
  dead channel is detected and re-established automatically from persisted
  consent (bounded backoff, `peer unreachable` surfaced after repeated failures).
- **Endpoint auto-re-announce** — when your ngrok endpoint changes on restart,
  your claw announces it to federated peers over the live session and they
  re-dial automatically. No more manual host:port swapping.
- **Capability/version negotiation** — peers on different OpenClaw builds
  interoperate (agent-flag and reply-shape differences are negotiated); a
  pre-053 peer degrades gracefully to 052 behavior.
- **Health & one-step setup** — `n2n_health` (and the HUD claw node) show
  channel state, last-seen, endpoint freshness, and in-flight tasks;
  `n2n_connect` and `n2n_trust` collapse the multi-step setup into one call each.

Full spec: [`specs/053-n2n-ergonomics/`](specs/053-n2n-ergonomics/).

---

## eN2N vs iN2N — external federation vs "a risk of NetClaws"

Everything above is **eN2N**: federation between **different operators'** claws
over the NCFED mesh, gated by mutual consent. Feature 056 adds **iN2N**, the
*internal* counterpart: **one operator** running a group of focused claws — a
**risk** — coordinated by a single **Border Claw**.

| | eN2N (this document) | iN2N ([docs/N2N-RISK.md](docs/N2N-RISK.md)) |
|---|---|---|
| Between | different operators | one operator's own claws |
| Trust | mutual consent per peer | pinned key + single-use token (one owner) |
| Transport | NCFED over the BGP mesh (ngrok) | members dial the Border outbound (loopback/VPN) |
| Topology | peer-to-peer between Borders | hub-and-spoke (Border ↔ members) — no mesh |
| Identity | each claw's BGP identity | one identity per risk (the Border) |

**How they compose:** a *risk* federates externally through its **Border only** —
Border-to-Border. To a peer, a risk is one identity; member claws and internal
topology are never exposed. The Border advertises the **aggregate** of its
members' capabilities under the risk identity, so a peer can still ask "does that
risk have CML?" and the Border routes it internally. The eN2N wire format,
consent, and safety model in this document are **unchanged** by iN2N.

Already federated with a peer who is adopting the risk model? See
[docs/N2N-RISK-MIGRATION-FOR-PEERS.md](docs/N2N-RISK-MIGRATION-FOR-PEERS.md).

## Reference

- **A risk of NetClaws (iN2N):** [`docs/N2N-RISK.md`](docs/N2N-RISK.md)
- **For federated peers (migration readout):** [`docs/N2N-RISK-MIGRATION-FOR-PEERS.md`](docs/N2N-RISK-MIGRATION-FOR-PEERS.md)
- Skill: [`workspace/skills/n2n-federation/SKILL.md`](workspace/skills/n2n-federation/SKILL.md)
- MCP server: [`mcp-servers/n2n-mcp/README.md`](mcp-servers/n2n-mcp/README.md)
- Spec / plan / contracts: [`specs/052-n2n-federation/`](specs/052-n2n-federation/) (eN2N) · [`specs/056-in2n-internal-federation/`](specs/056-in2n-internal-federation/) (iN2N) · [`specs/057-in2n-production-enforcement/`](specs/057-in2n-production-enforcement/) (iN2N production enforcement + durable runtime)
- Mesh bring-up (BGP layer): [`PEERINGEXAMPLE.md`](PEERINGEXAMPLE.md)
