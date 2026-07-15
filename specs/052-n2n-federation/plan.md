# Implementation Plan: NetClaw-to-NetClaw (N2N) Federation

**Branch**: `052-n2n-federation` | **Date**: 2026-07-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/052-n2n-federation/spec.md`

## Summary

Elevate the existing NetClaw Mesh (eBGP over ngrok, bgp-daemon-v2) from route
exchange to agent federation: consenting peers exchange capability inventories,
invoke allowlisted tools/skills on each other, and chat claw-to-claw — all
multiplexed on the existing mesh port via a third protocol-discrimination magic
(`NCFED`), carried as JSON-RPC 2.0 frames. Tool federation adopts MCP semantics
(`tools/list`/`tools/call` — a peer's grants surface locally as a standard MCP
server); chat and skill delegation adopt A2A-style task/streaming semantics
(inventory ≈ AgentCard, delegated skill ≈ task lifecycle, chat ≈ message/stream).
A new `n2n-mcp` server gives the local operator/agent control of federation;
the HUD federation view reads new daemon `/n2n/*` endpoints through server.js.

## Technical Context

**Language/Version**: Python 3.10+ (daemon federation layer + n2n-mcp, matching
protocol-mcp), Node.js 18+ / ES2022 (HUD server.js + Three.js frontend), Bash
(installer catalog entry)
**Primary Dependencies**: Existing `bgp-daemon-v2.py` (listener, protocol
discrimination, peer registry, HTTP API on 8179), FastMCP (n2n-mcp), httpx
(daemon↔gateway and MCP↔daemon calls), Python stdlib `json`/`sqlite3` — no new
third-party packages
**Storage**: SQLite at `~/.openclaw/n2n/federation.db` (consent records, grants,
budgets, audit index) — federation state must survive restarts (FR-028);
inventories cached as JSON per peer in `~/.openclaw/n2n/inventories/`
**Testing**: pytest — unit tests for framing/authorization/budget logic;
two-daemon loopback integration test (two bgp-daemon-v2 instances on localhost
ports, full consent → inventory → invoke → chat → kill-switch cycle)
**Target Platform**: Linux/WSL2 host running the NetClaw stack (same as mesh)
**Project Type**: Extension of existing multi-component repo (daemon + MCP server
+ HUD + installer artifacts)
**Performance Goals**: Capability query answered locally < 5 s (SC-002);
allowlisted invocation round-trip < 30 s (SC-005); chat first token < 15 s
(SC-007); kill switch effective < 10 s (SC-006); N2N I/O must never starve BGP
keepalives (SC-009 — zero session flaps over 24 h with federation active)
**Constraints**: No new listening ports (FR-010 — mux on the existing mesh
endpoint); default-deny authorization (FR-012); per-peer daily budgets enforced
by the executing side (FR-017); no credentials/secrets in any N2N payload
(FR-007); channel-anchored identity AS+router-id (FR-002/FR-003); pre-federation
peers unaffected (FR-027)
**Scale/Scope**: Single-digit federated peers per claw (demo mesh is 3 claws:
AS 65001/65007/65099); inventories up to ~200 skills + ~50 MCP servers
(~100–300 KB JSON) — chunked framing so keepalives interleave

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Safety-First Operations | PASS | N2N executes only allowlisted capabilities; remote side observes its own Safety rules; no device write path is introduced by N2N itself |
| II | Read-Before-Write | PASS | N2N adds no direct device writes; delegated skills inherit the remote claw's existing read-before-write behavior |
| III | ITSM-Gated Changes | PASS | Delegated executions run under the REMOTE claw's ServiceNow/lab-mode policy (FR-014) — a peer cannot bypass the executing side's CR gate |
| IV | Immutable Audit Trail | PASS | FR-015/FR-022 mandate dual-side audit; plan wires audit records into GAIT + the federation.db audit index |
| V | MCP-Native Integration | PASS | Operator control surface is a new FastMCP server (`n2n-mcp`); remote tool grants surface as MCP `tools/list`/`tools/call` semantics. The NCFED wire channel is peer transport (like BGP itself), not tool integration — same category as the existing mesh daemon |
| IX | Security by Default | PASS | Default-deny grants, budgets, kill switch, DefenseClaw inspection of inbound invocations (FR-014), least-privilege daemon API bound to 127.0.0.1 |
| X | Observability | PASS | New daemon `/n2n/*` status endpoints; HUD federation view (FR-023–026) |
| XI | Full-Stack Artifact Coherence | PASS (planned) | README, catalog.sh + install-steps.sh entry (`n2n`), verify-catalog-coverage, HUD, SOUL.md, `workspace/skills/n2n-federation/SKILL.md`, `.env.example`, TOOLS.md, `config/openclaw.json` registration — enumerated in tasks phase |
| XII | Documentation-as-Code | PASS (planned) | `mcp-servers/n2n-mcp/README.md`, SKILL.md, contracts/ in this spec |
| XIII | Credential Safety | PASS | FR-007 forbids secrets in inventories/payloads; config via `.env` (`N2N_*` vars) |
| XIV | Human-in-the-Loop | PASS | Mutual consent, approval prompts on existing channels (FR-013), operator-initiated only (out of scope: autonomous claw-to-claw) |
| XV | Backwards Compatibility | PASS | Third discrimination magic is additive; pre-federation peers see identical BGP behavior (FR-027); daemon HTTP API only gains routes |
| XVI | Spec-Driven Development | PASS | This SDD flow (spec 052 → clarify → plan) |
| XVII | Milestone Blog | NOTED | Draft WordPress post at implement completion |

**Initial gate: PASS** (no violations; Complexity Tracking not required).
**Post-design re-check (after Phase 1): PASS** — design introduces no new ports,
no new languages, no non-MCP tool integration, no credential movement.

## Project Structure

### Documentation (this feature)

```text
specs/052-n2n-federation/
├── spec.md              # Feature specification (clarified 2026-07-10)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── n2n-wire-protocol.md    # NCFED channel: framing + JSON-RPC methods
│   ├── n2n-mcp-tools.md        # Operator-facing MCP tool contract
│   └── n2n-daemon-api.md       # Daemon HTTP /n2n/* endpoints (MCP + HUD consumers)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
mcp-servers/protocol-mcp/
├── bgp-daemon-v2.py             # + FederationManager wiring, /n2n/* API routes
└── bgp/
    ├── agent.py                 # + NCFED branch in protocol discrimination
    ├── constants.py             # + NCFED_MAGIC, frame limits
    └── federation/              # NEW package
        ├── __init__.py
        ├── channel.py           # NCFED handshake, JSON-RPC 2.0 framing, mux I/O
        ├── manager.py           # consent state machine, peer registry, kill switch
        ├── inventory.py         # build local inventory (openclaw.json + workspace/skills), visibility filter
        ├── authorization.py     # grants, default-deny, approvals, budgets, rate limits
        ├── invocation.py        # inbound exec: MCP stdio tools/call (+ DefenseClaw pre-spawn inspection); gateway tasks for skills
        ├── chat.py              # chat sessions, streaming relay, transcripts
        └── audit.py             # dual-side audit records → federation.db + GAIT

mcp-servers/n2n-mcp/             # NEW operator-facing MCP server
├── server.py                    # FastMCP; proxies daemon /n2n/* (pattern from protocol-mcp fix d6e2cb2)
├── requirements.txt
└── README.md

ui/netclaw-visual/
├── server.js                    # + /api/n2n proxy (federation state, inventories, approvals)
└── src/                         # + expandable claw nodes, capability badges, chat panel

workspace/skills/n2n-federation/SKILL.md   # NEW skill documentation
scripts/lib/catalog.sh                     # + "n2n|…" component entry
scripts/lib/install-steps.sh               # + component_install_n2n()
config/openclaw.json                       # + n2n-mcp registration
.env.example                               # + N2N_* variables

tests/n2n/
├── test_framing.py              # NCFED frame encode/decode, chunking
├── test_authorization.py        # default-deny, grants, budgets, approval expiry
├── test_inventory.py            # visibility filtering, no-secrets invariant
└── test_two_daemon_loopback.py  # integration: consent→inventory→invoke→chat→kill
```

**Structure Decision**: Extend `protocol-mcp` (which owns the port-1179 listener
and discrimination — the channel cannot live anywhere else) with a new
`bgp/federation/` package; add a thin `n2n-mcp` FastMCP server as the operator
surface following the daemon-API-proxy pattern proven today in commit d6e2cb2;
HUD consumes the same daemon API through server.js like `/api/bgp` does.

## Complexity Tracking

No constitution violations — table not required.
