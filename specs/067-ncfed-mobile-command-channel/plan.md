# Implementation Plan: NCFED Mobile Command Channel

**Branch**: `067-ncfed-mobile-command-channel` | **Date**: 2026-07-22 | **Spec**: `specs/067-ncfed-mobile-command-channel/spec.md`
**Input**: Feature specification from `/specs/067-ncfed-mobile-command-channel/spec.md`

## Summary

Adds the phone-to-Border direction on top of feature 066's edge-node connection: an operator
asks the Border something from the phone and gets an answer, attributed to whoever actually
produced it (the Border itself, an in-risk member, or an external eN2N peer). The Border
bridges the phone's text into a real agent turn via the EXISTING `gateway.run_agent_turn()`
mechanism (already used by peer-to-peer chat, `chat.py`) — the agent's own existing tool-using
behavior (`n2n_route`/`n2n_delegate`/`n2n_invoke`) handles delegation and eN2N routing with no
new Border-side logic for those directions. The request is tracked via the EXISTING
`TaskManager` (feature 053) so it is cancellable and never silently hangs, exactly reusing
`n2n/tasks/status`/`result`/`cancel`. Voice input is transcribed on-device before sending — the
wire protocol never changes shape between typed and spoken requests.

## Technical Context

**Language/Version**: Python 3.10+ (daemon + `bgp/federation/*`, matching 052–066); Dart 3.x / Flutter 3.x (extends `mobile/netclaw-mobile/`, the same codebase 066 established)
**Primary Dependencies**: Python: none new — reuses `gateway.run_agent_turn()`, `tasks.py`'s `TaskManager`, `edge.py`'s `EdgeChannel`/`EDGE_METHODS`, `invocation.py`'s `handle_task_status`/`result`/`cancel` exactly as-is. Dart: an on-device speech-to-text package for US4 (voice → text before sending, research D7) and (for US5) reuses `mobile_scanner` (already added in 066) for the QR half of the device deep link; the `netclaw://device/<id>` URI-scheme half needs a deep-link/app-links package (e.g. `app_links` or platform intent filters) — exact package choice is a Phase 2 task detail, not fixed here.
**Storage**: No Border-side schema change — `session_key=f"n2n-edge-{member_id}"` passed to `run_agent_turn` already gives each enrolled device its own agent session (research D6); the per-device conversation history itself (FR-007) is entirely on-device, a second JSON-Lines store mirroring 066's `MessageFeedStore` pattern (`ConversationStore`).
**Testing**: `python3 -m pytest tests/n2n -q` (new: `tests/n2n/test_edge_ask.py`); `flutter analyze` + `flutter test` in `mobile/netclaw-mobile/`
**Target Platform**: Same as 066 — Android (buildable/testable in this environment once the
SDK is installed) and iOS (Xcode/macOS-only for build/run; no new native platform code needed
here beyond what 066 already added, since this spec introduces no new secure-hardware
key/biometric surface)
**Project Type**: Extends the existing single-project layout (066's mobile app + the existing
federation daemon) — no new top-level project
**Performance Goals**: Matches the existing agent-turn timeout budget (`run_agent_turn`'s
default 300s) — SC-005 requires no phone request be left pending beyond that same budget
**Constraints**: FR-002 (operator-extension trust, `untrusted=False`, research D2) must never
regress into treating the phone as a lower- or higher-trust peer than Slack/CLI/TUI; FR-009
(no auto-mirroring into other channels) must hold with zero new code path that could leak a
phone request into Slack/TUI/HUD
**Scale/Scope**: 5 user stories (2×P1, 3×P2); no new Border-side persistent schema; one new
wire method (`n2n/edge/ask` + `n2n/edge/ask_result`) plus reuse of three existing ones

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| IV. Immutable Audit Trail | Every phone-originated task is recorded via the existing `TaskManager`/`Auditor` exactly as member-delegated tasks already are — no new audit gap | PASS |
| V. MCP-Native Integration | No new MCP tool needed — the agent's existing `n2n_route`/`n2n_delegate`/`n2n_invoke`/`n2n_chat` tools already cover delegation/routing (research D3) | PASS |
| VI. Multi-Vendor/Agent Neutrality | Unaffected — this spec touches only the federation daemon + mobile client, not any vendor MCP | PASS |
| IX. Security by Default | FR-002's operator-extension model is `untrusted=False` (research D2), matching Slack/CLI/TUI's existing unchecked local trust — not a new default-allow surface, an explicit continuation of an existing one; eN2N crossing (US3) still goes through the unchanged per-peer grant/audit model (FR-004) | PASS |
| XI. Full-Stack Artifact Coherence | README/SOUL/TOOLS/SKILL.md/HUD updates planned in tasks.md's Polish phase, same as 066 | PASS (pending Polish tasks) |
| XIII. Credential Safety | No new credentials — reuses the existing NCFED edge connection/identity from 066 | PASS |
| XV. Backwards Compatibility | Purely additive: new wire methods, no change to any existing method's behavior or schema | PASS |
| XVI. Spec-Driven Development | This plan follows `/speckit.specify` → `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.implement` | PASS |

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/067-ncfed-mobile-command-channel/
├── plan.md              # This file
├── research.md          # Phase 0 output (D1-D8)
├── data-model.md        # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── edge-ask-command-channel.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
mcp-servers/protocol-mcp/bgp/federation/
├── edge.py                 # EDGE_METHODS gains n2n/edge/ask, n2n/edge/ask_result,
│                           #  n2n/tasks/status, n2n/tasks/result, n2n/tasks/cancel
├── service.py               # _edge_border_handlers gains n2n/edge/ask → _edge_on_ask
│                           #  (new), and REUSES self.invoker.handle_task_status/result/
│                           #  cancel under n2n/tasks/* — no new status/result/cancel code
├── chat.py                  # unchanged — read as the template for _edge_on_ask
├── gateway.py                # unchanged — run_agent_turn() called with untrusted=False
└── tasks.py                  # unchanged — TaskManager reused as-is

mobile/netclaw-mobile/lib/
├── ncfed/
│   ├── edge_ask_client.dart   # NEW: n2n/edge/ask + task status/result/cancel wire calls
│   ├── conversation_store.dart # NEW: per-device persisted chat history (mirrors 066's
│   │                           #  MessageFeedStore)
│   ├── device_deep_link.dart   # NEW: netclaw://device/<id> + QR → n2n/edge/ask shortcut
│   └── voice_transcription.dart # NEW: on-device speech-to-text before sending (US4)
└── screens/
    └── chat_screen.dart        # NEW: request/answer history, in-progress state, cancel
```

**Structure Decision**: Extends the existing `mobile/netclaw-mobile/` Flutter app (066) and the
existing federation daemon package (`bgp/federation/`) — no new top-level project. All new
Python logic lives in the same two files 066 already introduced/extended (`edge.py`,
`service.py`), reusing `chat.py`/`gateway.py`/`tasks.py`/`invocation.py` unchanged.
