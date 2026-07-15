# Implementation Plan: N2N Federation Ergonomics & Reliability

**Branch**: `053-n2n-ergonomics` | **Date**: 2026-07-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/053-n2n-ergonomics/spec.md`

## Summary

Harden the proven NCFED protocol (052) so federation self-heals and long tasks
complete reliably, without touching the frozen core. Six work areas, all
extending the existing `bgp/federation/` package and the `n2n-mcp` server:
async task delegation (submit/status/result/cancel with background workers),
channel health + auto-reconnect, endpoint auto-re-announce over the mesh
directory, capability/version negotiation in the `n2n/hello` handshake,
robustness hardening (consolidating the live 052 hot-patches with tests), and
operator health/ergonomics surfaces. No changes to NCFED framing, consent,
default-deny authorization, or the no-secrets guard.

## Technical Context

**Language/Version**: Python 3.10+ (daemon federation layer + n2n-mcp, matching
052), Node.js 18+/ES2022 (HUD server.js + Three.js), no new languages
**Primary Dependencies**: Existing `bgp-daemon-v2.py` + `bgp/federation/*`
(manager, channel, service, inventory, authorization, invocation, chat,
gateway, audit), FastMCP (n2n-mcp), httpx, Python stdlib `json`/`sqlite3`/
`asyncio` — no new third-party packages
**Storage**: Extend the existing SQLite at `~/.openclaw/n2n/federation.db` with
a `delegated_task` table (task state/progress/result survive restarts, FR-004);
per-peer channel-health and endpoint-freshness held in-memory in the service,
with endpoint persisted to `federation_peer.endpoint_host/port` (already exists)
**Testing**: pytest — unit tests for task lifecycle state machine, reconnect
backoff, endpoint-update handling, capability negotiation, and each robustness
fix (regression tests that fail pre-053, per FR/SC-008); extend the two-service
loopback harness from 052 for the integration paths
**Target Platform**: Linux/WSL2 hosts running the NetClaw mesh (unchanged)
**Project Type**: Extension of the existing multi-component repo (daemon +
`n2n-mcp` + HUD)
**Performance Goals**: async submit returns < ~3 s (SC-001); auto-reconnect
restores federation < 60 s after a peer restart (SC-002); endpoint re-announce
→ peer re-dial with zero manual steps (SC-003); a completed result is never lost
to a timeout mismatch (SC-005)
**Constraints**: No individual lifecycle call long enough for ngrok idle-reset
(FR-005 — keep all calls short, do the work in background workers); reconnect
uses bounded backoff, no tight loops (FR-008); endpoint updates trusted only
over the authenticated mesh session for an already-federated identity (FR-012);
frozen 052 core (FR-022)
**Scale/Scope**: Single-digit federated peers per claw; a handful of concurrent
delegated tasks per peer; the live 3-claw mesh (AS 65001/65007/65099) is the
soak testbed (SC-007)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Safety-First Operations | PASS | No new device write path; delegated tasks still run under the remote claw's own policies (unchanged from 052) |
| IV | Immutable Audit Trail | PASS | Task lifecycle events + reconnects + endpoint updates extend the existing dual-side audit (FR-015 052 carried this) |
| V | MCP-Native Integration | PASS | Operator surface stays the `n2n-mcp` FastMCP server; new task tools follow the same proxy pattern; NCFED remains peer transport, not tool integration |
| IX | Security by Default | PASS | Endpoint re-announce authenticated over the mesh session only (FR-012); no new inbound exposure; consent/default-deny frozen (FR-022) |
| X | Observability | PASS | Health/progress surfaced in HUD + status endpoint (US6) — directly advances this principle |
| XI | Full-Stack Artifact Coherence | PASS (planned) | Touches README, SKILL.md, `n2n-mcp` README, `.env.example` (new `N2N_*` tunables), HUD; no new catalog id (extends existing `n2n`); enumerated in tasks |
| XII | Documentation-as-Code | PASS (planned) | Contracts updated for the task lifecycle + negotiation; SKILL/README updated same PR |
| XIII | Credential Safety | PASS | No secrets added; no-secrets guard frozen |
| XIV | Human-in-the-Loop | PASS | Async delegation preserves the remote operator's approval gate (052); no autonomous cross-claw action added |
| XV | Backwards Compatibility | PASS | Pre-053 peers federate at 052 behavior via version negotiation graceful-degrade (FR-016); NCFED framing unchanged |
| XVI | Spec-Driven Development | PASS | This SDD flow |
| XVII | Milestone Blog | NOTED | Draft at implement completion |

**Initial gate: PASS** — no violations; Complexity Tracking not required. The
whole feature is deliberately additive over frozen 052 primitives.
**Post-design re-check: PASS** — design adds a task table + in-memory health/
negotiation state and reuses the existing channel, mesh directory, and audit;
no new ports, languages, or trust paths.

## Project Structure

### Documentation (this feature)

```text
specs/053-n2n-ergonomics/
├── spec.md
├── plan.md                       # this file
├── research.md                   # Phase 0 — 6 decisions
├── data-model.md                 # Phase 1 — DelegatedTask, ChannelHealth, CapabilityDescriptor
├── quickstart.md                 # Phase 1 — self-heal + async CML-clone walkthrough
├── contracts/
│   ├── n2n-task-lifecycle.md     # n2n/tasks submit|status|result|cancel (async)
│   ├── n2n-control-methods.md    # n2n/endpoint_update, n2n/hello capability descriptor
│   └── n2n-daemon-api-delta.md   # new /n2n/* HTTP routes (tasks, health)
└── tasks.md                      # Phase 2 (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
mcp-servers/protocol-mcp/bgp/federation/
├── channel.py        # + on_close hook → deregister from service; heartbeat-miss → close (US2)
├── service.py        # + reconnect supervisor loop, endpoint-update handler, capability
│                     #   descriptor in hello, task-manager wiring
├── invocation.py     # handle_task_submit → async (spawn worker, return task_id); tools/call unchanged
├── tasks.py          # NEW: DelegatedTask model, TaskManager (background workers, status/result/cancel,
│                     #   SQLite persistence + retention)
├── gateway.py        # + capability probe (which agent CLI flags exist), reply-shape adaptation (US4/US5)
├── manager.py        # + delegated_task table; endpoint update persistence
└── negotiate.py      # NEW: capability/version descriptor build + compare (US4)

mcp-servers/protocol-mcp/bgp/agent.py
                      # endpoint-change detection → trigger service.re_announce_endpoint() (US3)

mcp-servers/protocol-mcp/bgp-daemon-v2.py
                      # + /n2n/tasks/* routes, /n2n/health route; wire endpoint re-announce on ngrok change

mcp-servers/n2n-mcp/server.py
                      # + n2n_delegate (async submit), n2n_task_status, n2n_task_result, n2n_task_cancel,
                      #   n2n_health; n2n_connect/n2n_trust minimal flows (US6)

ui/netclaw-visual/
├── server.js         # + /api/n2n health/tasks aggregation
└── src/main.js       # claw node: channel state, last-seen, endpoint freshness, in-flight task progress

tests/n2n/
├── test_tasks.py             # lifecycle state machine, retention, cancel, survive-reconnect
├── test_reconnect.py         # dead-channel detect, backoff, auto re-federate
├── test_endpoint_reannounce.py
├── test_negotiate.py         # descriptor exchange + graceful degrade to 052
└── test_robustness.py        # timeout-outlast, trailing-log parse, segmented body, typed errors
```

**Structure Decision**: Pure extension of the 052 `bgp/federation/` package. Two
new modules (`tasks.py`, `negotiate.py`) keep the async-task and negotiation
concerns cohesive; everything else is additive edits to existing files. The
`n2n-mcp` operator surface and HUD extend their established proxy/polling
patterns. No restructuring.

## Complexity Tracking

No constitution violations — table not required.
