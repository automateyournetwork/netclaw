# Implementation Plan: Cloudflare Tunnel as a Hardened eN2N Transport

**Branch**: `108-cloudflare-tunnel-transport` | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/108-cloudflare-tunnel-transport/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add Cloudflare Tunnel as an **additional, operator-opt-in** eN2N transport alongside the existing raw-TCP/ngrok path, run in **TCP/private-network (opaque-relay) mode** so it requires zero NCFED wire-format changes. This directly closes the confirmed live gap between spec 063's endpoint-persistence fix (which only helps a channel that is *still alive* to receive an announced address) and reality (a channel dead long enough has no live session left to announce over, and a rotating ngrok address can't be guessed back) — by removing the underlying cause: a Cloudflare-Tunnel-bound hostname doesn't change on restart, so there is nothing to re-announce. Layered on top, an optional (default-off, per-peer opt-in) Cloudflare Access policy rejects unauthenticated connection attempts at Cloudflare's edge, strictly before any bytes reach the claw's `asyncio.start_server` listener or spec 060's TLS/peer-identity negotiation — a defense-in-depth addition, not a replacement for 060's identity checks. Transport type and edge-gate status are surfaced in the existing 060/063 posture view (no new UI surface), and a local tunnel/DNS health probe extends spec 057's fault-class model so a transport-layer outage is never misattributed as "peer down."

## Technical Context

**Language/Version**: Python 3.14 (matches the reference host per spec 063 R0-addendum; `asyncio`-based daemon)
**Primary Dependencies**: Existing `bgp/federation/{service,channel,tls,manager}.py` (unchanged); external `cloudflared` binary/service (ops-level, not a Python dependency) for the tunnel; Cloudflare Access (edge-hosted policy engine, no local library) for the optional US2 gate
**Storage**: Existing SQLite-backed `federation_peer` table (via `FederationManager`) — extended with two new display columns (`transport`, `edge_gate`), no new store
**Testing**: Existing repo test pattern (pytest under `tests/n2n/`), consistent with 052/053/056/057's test layout
**Target Platform**: Linux server (systemd-managed durable services, per spec 057's `in2n-services.py` pattern) — this claw's reference host (`as65099-10.255.255.1`, domain `byrnbaker.me`, Cloudflare-managed DNS)
**Project Type**: Single project (existing `mcp-servers/protocol-mcp` daemon + `n2n-mcp` tool surface) — no new project/service boundary
**Performance Goals**: N/A — this is a transport/ops substitution; no new hot path in the federation code (`open_channel`/`asyncio.start_server` are unchanged; `cloudflared` sits underneath at the OS/network layer exactly where ngrok does today)
**Constraints**: Zero NCFED wire-format changes (FR-008); zero forced peer migration (FR-001, FR-008); TCP/private-network mode only, never HTTP(S) ingress (FR-009); Access default-off (FR-005)
**Scale/Scope**: Two known live peers to validate against once they independently adopt this (John/as65001, Nick/as65007) plus this claw's own advertised endpoint; scope is this claw's transport configuration and the small posture/fault-reporting extensions, not a peer-side mandate

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reviewed against `.specify/memory/constitution.md` and the precedent set by specs 057/060/063 (the most directly analogous prior features — all touch the same federation trust/transport surface):

- **No wire-protocol change**: PASS. FR-008 explicitly forbids it; R1's TCP/private-network mode decision is chosen specifically to keep this true. Consistent with 063's own constraint (FR-013: "MUST NOT weaken... existing... guarantees").
- **No parallel state/surfaces**: PASS. R4 extends the existing 060/063 posture record and R3 extends the existing 057 `n2n_faults` model rather than introducing new stores or views — matches the explicit cross-cutting requirement both 060 (FR cross-cutting) and 063 (FR-014) impose on themselves.
- **Additive, non-breaking to existing peers**: PASS. FR-001/FR-008/SC-005 require zero regression for peers who stay on ngrok or any other transport; mirrors 060's own patched-vs-unpatched-peer philosophy (peers upgrade independently).
- **Honest posture, never a false claim**: PASS by design — FR-004 makes Access's non-interference with 060's identity checks true *by construction* (R2: Access sits strictly earlier in the connection lifecycle, invisible to the federation code), not by an enforcement flag that could be wrong. This follows spec 057's "never claim a control is active when it isn't" principle.
- **Immutable audit trail (GAIT) for security-relevant events**: applicable if/when Access enable/disable or tunnel-transport-adopted events are treated as security-relevant per spec 057 US4's GAIT event list — flagged in Complexity Tracking below as a scope question for `/speckit.tasks`, not a blocker to planning.

No violations requiring justification at this stage. Re-check after Phase 1 (data-model/contracts) below.

**Post-Phase-1 re-check**: The two new peer-record display fields (`transport`, `edge_gate` — see data-model.md) and the local tunnel-health probe (no new store, computed on read) do not introduce any new trust boundary, wire format, or bypass of existing 060 TLS/identity checks. Constitution Check remains PASS.

## Project Structure

### Documentation (this feature)

```text
specs/108-cloudflare-tunnel-transport/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md         # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
mcp-servers/protocol-mcp/
├── bgp/
│   └── federation/
│       ├── manager.py        # FederationManager — extend upsert_peer/get_peer/list_peers
│       │                     #   with transport/edge_gate display fields (US3)
│       ├── posture.py        # Existing 060 posture surface — add transport/edge_gate
│       │                     #   fields to the per-peer posture record (US3, R4)
│       ├── service.py        # UNCHANGED — open_channel/on_conn already work against
│       │                     #   whatever host:port resolves; cloudflared is transparent
│       ├── channel.py        # UNCHANGED — no wire-format touch (FR-008)
│       └── tls.py            # UNCHANGED — 060's TLS layer is untouched (FR-004, R2)
├── bgp-daemon-v2.py           # Add a local tunnel/DNS health probe surfaced via the
│                               #   existing /n2n/faults-equivalent status endpoint (US2/US3, R3)
└── (ops, not Python) cloudflared systemd unit + config — new durable service,
    generated the same way spec 057's in2n-services.py generates the mesh
    daemon/member units (US1)

n2n-mcp/                       # MCP tool surface — n2n_health/n2n_faults/n2n_status
                                #   response shapes gain transport/edge_gate fields;
                                #   no new tool names required for US1/US3.
                                #   US2 (Access) is pure Cloudflare-side + cloudflared
                                #   config — no new MCP tool is required to "enable" it
                                #   from this claw's side (operator-managed at the
                                #   Cloudflare dashboard/API), but n2n_health SHOULD
                                #   reflect its configured state if detectable.

tests/n2n/
├── test_endpoint_stability.py     # NEW — US1: simulate cloudflared/host restart,
│                                   #   assert stored endpoint host:port unchanged
├── test_transport_posture.py      # NEW — US3: assert transport/edge_gate fields
│                                   #   appear in posture output for mixed-transport peers
└── test_fault_classification.py   # NEW — US2/US3 support: assert local tunnel-health
                                    #   failure is classified distinctly from peer-down
```

**Structure Decision**: Single project, extending the existing `mcp-servers/protocol-mcp` federation daemon in place — the same structure specs 057/060/063 already used for this exact subsystem. No new service boundary or repository is introduced; `cloudflared` is an external, ops-managed process (a durable systemd service, mirroring spec 057's pattern for the mesh daemon itself), not a new in-repo component.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none — no gate violations)* | — | — |

**Open scope question for `/speckit.tasks`** (not a constitution violation, but flagged for task-breakdown time): should enabling/disabling the Cloudflare Access edge-gate for a peer be logged to the GAIT immutable trail per spec 057 US4's existing event list (delegation, enrollment, member removal, quarantine)? It is a security-posture-relevant change to a peer's channel, which suggests yes, but it is not explicitly named in 057's list and this spec does not mandate it (FR-005/FR-006 only require it be *visible* in posture, not that its toggle be GAIT-audited). Recommend deciding this explicitly in `/speckit.tasks` rather than defaulting silently either way.
