# Phase 0 Research: N2N Federation

**Feature**: 052-n2n-federation | **Date**: 2026-07-10

All spec-level unknowns were resolved in the 2026-07-10 clarification session
(identity, budgets, transport, approvals, skill semantics). This phase resolves
the plan-level unknowns: wire protocol, channel mechanics, execution paths,
persistence, and HUD integration.

## R1. Wire protocol: A2A vs MCP vs bespoke JSON-RPC 2.0

**Decision**: JSON-RPC 2.0 frames on the NCFED channel, with a hybrid semantic
split:

- **Tool federation = MCP semantics.** A peer's granted tools are exposed with
  `tools/list` / `tools/call` shapes. Locally, `n2n-mcp` re-exposes each
  federated peer's grants as namespaced tools (`n2n_invoke` with
  `peer` + `tool` args in v1; a v2 option is dynamic per-peer MCP mounts).
  Rationale: NetClaw is MCP-native (Constitution V); the gateway, HUD, and 51
  existing servers already speak these shapes; zero new invocation semantics for
  the requesting agent.
- **Chat + delegated skills = A2A-style semantics.** Capability inventory maps
  to A2A's AgentCard concept; a delegated skill run maps to the A2A task
  lifecycle (`submitted → working → completed/failed` with status updates); chat
  maps to `message/stream` with incremental chunks. Rationale: these are
  agent-level, long-running, streaming interactions that MCP's request/response
  tool shape models poorly; A2A's lifecycle is purpose-built for them.
- **Not full A2A compliance.** A2A assumes HTTPS + SSE + well-known URL
  discovery; N2N runs over the muxed TCP channel with discovery via the mesh.
  We vendor the semantics (method names, task states, AgentCard-like inventory
  document), not the HTTP transport binding. Documented as "A2A-inspired" to
  avoid false interop claims.

**Alternatives considered**:
- *Pure A2A over HTTPS*: requires a new exposed HTTP endpoint per claw —
  violates FR-010 (no new inbound exposure) and doubles ngrok endpoint churn.
- *Pure MCP for everything*: chat and skill delegation would need long-poll
  hacks inside `tools/call`; no streaming, no task lifecycle; rejected.
- *Bespoke protocol*: both candidates are already JSON-RPC 2.0; inventing a
  third vocabulary adds cost with no benefit; rejected.

## R2. Channel: multiplexing on the mesh port

**Decision**: Add a third protocol-discrimination branch in
`agent._handle_incoming_connection` (bgp/agent.py:271). Current logic peeks the
first byte: `\xff` → BGP, `N` + `CTUN` → tunnel. Change: after reading `N`,
read 4 more bytes; `CTUN` → existing tunnel path, `CFED` → new federation
channel (`NCFED` magic + 4-byte AS + 4-byte router-id, mirroring the NCTUN
handshake in tunnel.py:145). Lower-AS side initiates the channel (same
collision-avoidance rule as NCTUN, tunnel.py:83). Framing: 4-byte big-endian
length prefix + UTF-8 JSON-RPC 2.0 message; max frame 64 KB with continuation
flag so large inventories chunk and BGP keepalives are never starved (FR-011 —
the channel is a separate TCP connection from the BGP session, so starvation
risk is host-level, mitigated by chunking + flow control, not framing on the
same socket).

**Rationale**: Reuses the proven discrimination mechanism and the existing
public endpoint; works wherever BGP works (clarification Q3); pre-federation
peers never send `NCFED` and see zero behavior change (FR-027).

**Alternatives considered**:
- *Ride the NCTUN overlay tunnel*: observed failing 3/3 attempts between live
  peers today (AS 65001 → 65007) and couples federation to TUN-device/root
  requirements; rejected per clarification Q3.
- *Second ngrok endpoint*: new exposure, endpoint churn; rejected (FR-010).
- *In-band BGP capability/community encoding*: BGP messages are the wrong place
  for multi-hundred-KB payloads and request/response semantics; rejected.

## R3. Remote execution paths on the executing side

**Decision**: Two paths, both implemented in `federation/invocation.py`:

- **Tools (deterministic)**: the daemon spawns the target MCP server via stdio
  and performs `initialize` → `tools/call` directly (JSON-RPC over stdio, ~30
  lines with subprocess + stdlib json). No LLM involved; result returned
  verbatim. Server command/args come from `config/openclaw.json` exactly as the
  gateway launches them. **DefenseClaw compliance (FR-014)**: because this path
  bypasses the gateway where runtime guardrails hook, the daemon MUST perform
  its own inspection step before spawn when `security.mode == "defenseclaw"` in
  `~/.openclaw/config/openclaw.json`: invoke DefenseClaw's tool-inspection
  interface (`defenseclaw` CLI check on the tool name + serialized arguments)
  and refuse with error code `-32008 guardrail_blocked` on rejection; when
  security mode is `hobby`, the step is skipped. This keeps deterministic tools
  out of the LLM path while preserving "same inspection as any local tool call."
- **Skills + chat (agentic)**: the daemon POSTs to the local OpenClaw gateway's
  OpenAI-compatible API (the same `http://127.0.0.1:<gw.port>/v1/...` surface
  ui/netclaw-visual/server.js already proxies for HUD chat). A delegated skill
  run is a chat completion whose system context names the skill to execute;
  responses stream back as A2A-style task/status frames. Runs under the remote
  gateway's own model, policies, DefenseClaw guardrails, and the peer's budget.

**Rationale**: Deterministic tools must not burn LLM budget or add
nondeterminism; agentic work must go through the gateway so every existing
policy layer (DefenseClaw, lab mode, GAIT) applies unchanged (FR-014).

**Alternatives considered**:
- *Everything through the gateway*: burns tokens for deterministic calls and
  makes tool results nondeterministic; rejected.
- *Daemon imports MCP servers in-process*: dependency hell across 51 servers;
  rejected.

## R4. Persistence

**Decision**: SQLite (stdlib `sqlite3`) at `~/.openclaw/n2n/federation.db` for
consent records, grants, budget counters, and the audit index; per-peer
inventory JSON cached at `~/.openclaw/n2n/inventories/as<AS>-<router-id>.json`
with received-at metadata. Audit records additionally emit to GAIT per
Constitution IV.

**Rationale**: FR-028 requires surviving restarts; SQLite matches the
memory-mcp precedent (feature 033) and needs no new dependency; budgets need
atomic counters which flat JSON handles poorly.

**Alternatives considered**: flat JSON state file (no atomic counters, corruption
risk on crash — the operator crashed twice today); Memory MCP as the store
(wrong ownership — federation state belongs to the daemon, and Memory MCP is an
agent-facing tool, not a daemon library); rejected.

## R5. Operator surface (n2n-mcp) and HUD integration

**Decision**: `n2n-mcp` is a thin FastMCP server proxying new daemon HTTP routes
(`/n2n/status`, `/n2n/peers`, `/n2n/consent`, `/n2n/grants`, `/n2n/invoke`,
`/n2n/chat`, `/n2n/approvals`, `/n2n/kill`), exactly the daemon-API-proxy
pattern applied to protocol-mcp today (commit d6e2cb2) — the daemon is the
single source of truth, and the MCP server works from any gateway session.
HUD: server.js gains `/api/n2n` (aggregating daemon `/n2n/*` like `/api/bgp`
does for BGP state), and the Three.js scene extends claw nodes with federation
state, expandable inventory panels, capability badges, pending-approval list,
and a chat panel that drives `/n2n/chat`.

**Rationale**: One source of truth avoids the exact stale-view bug fixed this
morning (Slack agent blind to mesh peers); HUD and agent read identical state.

## R6. Approval delivery on existing channels

**Decision**: The daemon exposes pending approvals at `/n2n/approvals`;
approval prompts are delivered by the gateway agent via the existing
`humanrail-escalation` skill pattern (Slack/Webex/CLI), and `n2n-mcp` provides
`n2n_approve` / `n2n_deny` tools so the operator can respond from any connected
channel. The HUD lists pending approvals from the same endpoint. Expiry is
enforced daemon-side (FR-013) regardless of delivery channel.

## R7. Capability badges

**Decision**: Badge derivation is a static mapping from installed/advertised
MCP server ids to badge labels (e.g. `cml-*` → CML, `pyats`/testbed presence →
pyATS, `meraki-*` → Meraki), computed in `federation/inventory.py` at
advertisement build time from `config/openclaw.json` — never by probing devices
(spec assumption). The mapping table lives beside the catalog so new servers
get badges in the same PR that adds them (Constitution XI).

## R8. Defaults deferred from clarification

**Decision** (operator-overridable via `.env` `N2N_*` vars):
- Inventory refresh: on local capability change + every 6 h; stale threshold 2×
  refresh interval.
- Rate limits: 10 requests/min per peer (invocations + chat combined).
- Daily budget: 200 requests and 500 K tokens per peer per day.
- Approval window: 15 minutes, then expire-deny.
- Invocation timeout: 120 s tools; 600 s delegated skills; chat idle timeout 300 s.
- Kill switch: drops the NCFED channel, marks peer severed, purges cached
  inventory both directions; BGP untouched (FR-004, SC-006).
