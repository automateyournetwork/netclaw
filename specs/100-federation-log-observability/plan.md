# Implementation Plan: Federation Inbound-Call Observability

**Branch**: `100-federation-log-observability` | **Date**: 2026-08-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/100-federation-log-observability/spec.md`

## Summary

Four confirmed log defects in the mesh daemon are fixed so that a real inbound federated call is distinguishable from routine noise. Three are noise-side (benign disconnects logged as ERROR with tracebacks; dead peers re-dialled every 60s forever at WARNING; a stdlib TLS warning on every channel close) and one is signal-side (refusals are severity-indistinguishable from successes, and log lines omit the request identifier that would join them to their audit row). A supported registry operation plus an MCP tool replaces the raw SQL write that resolving the live incident required.

**Approach**: all changes are surgical edits to existing choke points — `Auditor.record()` for inbound logging, the reconnect supervisor's health dict for dampening, a narrow pre-catch-all handler in the BGP agent for benign disconnects, one targeted stdlib log filter, and one new manager method plus daemon route and MCP tool. No new components, no new dependencies.

**Scope correction carried from research**: Phase 0 verified that inbound calls are *already* logged at info level with peer, target, decision, and outcome (research R2). User Story 1 shrank from "build inbound-call logging" to "enrich one existing line." FR-001/002/004/006 are regression guards, not new work.

## Technical Context

**Language/Version**: Python **3.14.4** (`/usr/bin/python3`) — the interpreter `netclaw-mesh.service` actually executes. **Not** the repo's `.venv/` (Python 3.13.0b1); see research R1.
**Primary Dependencies**: None new. Standard library only (`asyncio`, `logging`, `sqlite3`, `time`, `os`). Existing in-repo modules: `bgp/agent.py`, `bgp/federation/{service,manager,audit,invocation,posture}.py`, `mcp-servers/n2n-mcp/server.py`.
**Storage**: Existing SQLite at `~/.openclaw/n2n/federation.db`. **No schema change** — `federation_peer.endpoint_host/endpoint_port/endpoint_updated_at` already exist and are cleared, not added to. Dampening state is in-memory (`FederationService.health`), consistent with today.
**Testing**: `pytest` where unit-testable, invoked with `/usr/bin/python3` explicitly (research R1). Live verification against `netclaw-mesh.service` via `journalctl`, following the observe → baseline → apply → verify pattern (Constitution VIII).
**Target Platform**: Linux (WSL2), systemd `--user` service.
**Project Type**: Single project — daemon + MCP server inside an existing repo.
**Performance Goals**: No added latency on the inbound path. Dampening must *reduce* connect attempts against dead peers, never delay a healthy peer's reconnect (FR-012).
**Constraints**: No wire-protocol, trust-model, or audit-semantics change (FR-027, FR-029). Backwards compatible env vars (Constitution XV). Restarting the daemon drops live federation channels, so restart timing is operationally sensitive.
**Scale/Scope**: 7 peers currently in the registry (1 healthy, 1 severed, 5 endpoint-less). ~6 files touched.

## Constitution Check

*GATE: evaluated before Phase 0, re-evaluated after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| **IV. Immutable Audit Trail** | **PASS** | FR-027 forbids reducing audit content. Endpoint retirement is recorded via the existing `Auditor.record()` GAIT path with `event`/`actor` (research R7) — satisfying "no operation may execute silently." |
| **VIII. Verify After Every Change** | **PASS** | Live baseline already captured (dead-peer line counts, `federation.db` backed up before the earlier endpoint clear). Each change is verified against the journal after applying. |
| **X. Observability First-Class** | **PASS (with recorded deviation)** | This feature *is* observability work. The HUD clause applies to new integrations; none is added, and the HUD already renders peer posture. FR-014 preserves the health fields it reads. A HUD control was explicitly declined during clarification. See research R9. |
| **XI. Full-Stack Artifact Coherence** | **PASS (subset)** | Defect fix, not a new capability. Applicable subset: `.env.example` (new vars), `TOOLS.md` (new MCP tool), `README.md` (if counts stated), and `scripts/reconcile-mcp.py` must run clean. Catalog/install-steps/HUD/SOUL/SKILL not applicable — no new installable component or skill. Full table in research R9. |
| **XII. Documentation-as-Code** | **PASS** | Docs updated in this PR, not a follow-up. |
| **XIII. Credential Safety** | **PASS** | No credentials involved. New env vars documented in `.env.example` without values. FR-007 forbids logging secrets or payloads. |
| **XIV. Human-in-the-Loop (External)** | **PASS** | No external communication. The Principle XVII blog post is drafted and offered, never published unprompted. |
| **XV. Backwards Compatibility** | **PASS** | Existing `N2N_RECONNECT_*` vars keep working (FR-028). New vars default to preserving current behavior except where the spec mandates change. No MCP schema break — a tool is added, none altered. |
| **XVI. Spec-Driven Development** | **PASS** | specify → clarify → plan → tasks → analyze → implement. |
| **XVII. Milestone Documentation** | **DEFERRED to completion** | Draft offered after implementation; publication requires approval per XIV. |

**Principles I, II, III, V, VI, VII, IX**: not applicable — no device interaction, no configuration change to network devices, no new MCP server, no vendor logic, no new skill.

**Gate result: PASS.** No unjustified violations. One recorded deviation (Principle X HUD clause) with rationale.

## Project Structure

### Documentation (this feature)

```text
specs/100-federation-log-observability/
├── spec.md              # Feature specification (with corrected US1 premise)
├── plan.md              # This file
├── research.md          # Phase 0 — R1..R9, all verified against running system
├── data-model.md        # Phase 1 — state shapes, no DB schema change
├── quickstart.md        # Phase 1 — how to verify each fix live
├── contracts/
│   └── interfaces.md    # Phase 1 — env vars, MCP tool, log line formats
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
mcp-servers/protocol-mcp/
├── bgp/
│   ├── agent.py                     # US3: narrow benign-disconnect handler before
│   │                                #      the catch-all at :498; keep :307 warning
│   │                                #      convention for invalid-magic
│   ├── bgp-daemon-v2.py             # US4: HTTP route exposing forget-endpoint
│   └── federation/
│       ├── audit.py                 # US1: enrich the single info line at :78-80 —
│       │                            #      request_id in the message, denial severity
│       ├── service.py               # US2: dampening in the supervisor (:725-757),
│       │                            #      conditional health reset (:98-99),
│       │                            #      summarized failure logging (:711),
│       │                            #      new env vars (:83-85)
│       ├── manager.py               # US4: forget_peer_endpoint() alongside :289-317
│       ├── invocation.py            # US1: arrival event (FR-033) at handler entry
│       └── logfilter.py             # NEW — targeted stdlib asyncio filter (FR-030)
└── mcp-servers/n2n-mcp/server.py    # US4: forget-endpoint tool

.env.example                         # Constitution XI/XIII: new N2N_RECONNECT_* vars
TOOLS.md                             # Constitution XI: new MCP tool
README.md                            # Constitution XII: tool counts if stated
```

**Structure Decision**: No new project or package. Every change lands in the existing `protocol-mcp` server that already owns the daemon, plus the already-registered `n2n-mcp` server. One new module (`logfilter.py`) isolates the stdlib filter so its narrowness is reviewable in one place rather than buried in daemon startup.

## Phase Sequencing and Risk

Ordered so the highest-noise, lowest-risk fixes land first and independently:

1. **US3 + FR-030 (benign disconnects, TLS warning)** — lowest risk, purely severity/classification, no behavioral change. Immediately makes the log readable for subsequent verification.
2. **US1 (enrich audit line)** — single choke point, additive.
3. **US2 (dampening)** — highest risk: touches dial scheduling. Must not delay a healthy peer (FR-012) and must not let flapping defeat dampening (FR-031). Requires the conditional-reset change that the current wholesale reset at `service.py:98-99` blocks.
4. **US4 (endpoint retirement)** — independent; touches manager, daemon route, MCP tool.

**Restart sensitivity**: the daemon must restart to load code changes, which drops live federation channels — including the channel to the peer currently being watched for an inbound call. Restart is therefore an explicit, confirmed step, not incidental.

**Primary implementation risk**: FR-010 (back long-dead peers off to 15 min) versus FR-012 (never penalize a transient blip). These pull in opposite directions and the classification rule between them is where an implementation will most likely go wrong. The spec resolves it with a two-signal test — consecutive failures **and** endpoint staleness — and FR-013 guarantees an endpoint change resets backoff immediately, which bounds the worst case for any peer that re-registers.

## Complexity Tracking

No constitutional violations requiring justification. One deviation recorded and rationalized in research R9 (Principle X HUD clause, not applicable — no new integration; HUD control explicitly declined in clarification).
