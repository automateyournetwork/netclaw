# Implementation Plan: NCFED Mobile Biometrics and Capture

**Branch**: `068-ncfed-mobile-biometrics-capture` | **Date**: 2026-07-23 | **Spec**: `specs/068-ncfed-mobile-biometrics-capture/spec.md`
**Input**: Feature specification from `/specs/068-ncfed-mobile-biometrics-capture/spec.md`

## Summary

Adds two capabilities sharing the same device machinery (camera/mic/biometric) on top of 066's
connection and 067's command channel: (A) biometric-gated approval resolution — the first real
delivery mechanism behind the never-wired `notify_approval` hook, reusing 066's push channel and
the existing `resolve_approval(..., via=...)`'s already-generic resolution-method field; (B)
bidirectional capture — phone-initiated captures ride 067's `n2n/edge/ask` as an optional
attachment (no new wire method), and Border-requested captures reuse `n2n_delegate` unchanged,
with capture capabilities advertised via the existing `member.scope` mechanism `RiskRouter`
already reads. No new MCP tool for either capability.

## Technical Context

**Language/Version**: Python 3.10+ (daemon + `bgp/federation/*`, matching 052–067); Dart 3.x / Flutter 3.x (extends `mobile/netclaw-mobile/`)
**Primary Dependencies**: Python: none new — reuses `push_to_edge()`, `resolve_approval()`, `RiskRouter`/`member.scope`, `TaskManager`. Dart: `local_auth` (biometric gating, US1), `camera` (photo/video capture, US2/US3) — exact audio-recording package (distinct from 067's speech-to-text, which discards audio after transcribing) is a Phase 2 task detail.
**Storage**: No new tables — `member.scope` gains capture-capability entries (same column, same JSON shape 066/067 already write); `approval_request`'s existing `resolved_via` column gains a new value (`"biometric"`), no schema change.
**Testing**: `python3 -m pytest tests/n2n -q` (new: `tests/n2n/test_edge_approval.py`,
`tests/n2n/test_edge_capture.py`); `flutter analyze` + `flutter test`
**Target Platform**: Same Android(buildable/testable here)/iOS(Xcode-only) split as 066/067
**Project Type**: Extends the existing single-project layout — no new top-level project
**Performance Goals**: Capture round-trip bounded by the same `TaskManager`/agent-turn timeout
budget already governing delegation (067)
**Constraints**: FR-003/D7 — biometric auth MUST NEVER touch or expose the 066 enrollment key;
`local_auth` runs fully independent of `EdgeIdentity`'s Keystore/Secure-Enclave code paths, no
shared state, no new method on `EdgeIdentity` at all
**Scale/Scope**: 3 user stories (all P1); 3 new wire methods
(`n2n/edge/register_capabilities`, `n2n/edge/capture`, `n2n/edge/approval_resolve`); one
extended existing method (`n2n/edge/ask` gains an optional `attachment` field); one extended
existing content_type (`n2n/edge/message` gains `content_type="approval"`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| IV. Immutable Audit Trail | Biometric approval resolution flows through the EXISTING `resolve_approval`/audit path unchanged (research D6); capture delegation is audited exactly as any other `delegate_to_member`-family call already is | PASS |
| V. MCP-Native Integration | Zero new MCP tools — `n2n_delegate` reused unchanged for capture requests (research D2); approval resolution has no agent-facing tool at all (it's a phone-only action) | PASS |
| VI. Multi-Vendor/Agent Neutrality | Unaffected | PASS |
| IX. Security by Default | FR-003/D7: biometric gating is strictly additive to the decision layer, verified to never touch the 066 enrollment key's Keystore/Secure-Enclave code path (no shared class, no new EdgeIdentity method) | PASS |
| XI. Full-Stack Artifact Coherence | README/SOUL/TOOLS/SKILL.md/HUD updates planned in tasks.md's Polish phase | PASS (pending) |
| XIII. Credential Safety | No new credentials | PASS |
| XV. Backwards Compatibility | Purely additive; `n2n_approve`/`n2n_deny`/CLI approval path explicitly required unchanged (FR-004) | PASS |
| XVI. Spec-Driven Development | Follows the standard `/speckit.*` pipeline | PASS |

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/068-ncfed-mobile-biometrics-capture/
├── plan.md / research.md / data-model.md / quickstart.md
├── contracts/
│   └── edge-biometrics-and-capture.md
└── tasks.md
```

### Source Code (repository root)

```text
mcp-servers/protocol-mcp/bgp/federation/
├── edge.py            # EDGE_METHODS gains register_capabilities, capture, approval_resolve
├── service.py          # _edge_on_register_capabilities, _edge_on_approval_resolve (new);
│                       #  _edge_on_ask gains attachment handling; notify_approval gains
│                       #  edge-push fan-out; delegate_to_member gains a node_type='edge' branch
│                       #  calling a new delegate_to_edge() helper (n2n/edge/capture)

mobile/netclaw-mobile/lib/
├── ncfed/
│   ├── approval_client.dart      # NEW: receives pushed approvals, resolves via biometric
│   ├── capture_client.dart        # NEW: n2n/edge/capture handler (Border-requested) +
│   │                               #  attachment helper for n2n/edge/ask (phone-initiated)
│   └── capability_registration.dart # NEW: n2n/edge/register_capabilities + Settings toggles
└── screens/
    ├── approvals_screen.dart      # NEW: pending approvals, biometric approve/deny (US1)
    └── capture_screen.dart        # NEW: camera/video/voice capture UI (US2/US3)
```

**Structure Decision**: Extends the existing `mobile/netclaw-mobile/` app and federation daemon
package — no new top-level project. All new Python logic lives in the same two files 066/067
already extended (`edge.py`, `service.py`).
