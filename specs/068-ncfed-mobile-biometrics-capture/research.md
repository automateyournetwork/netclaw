# Phase 0 Research: NCFED Mobile Biometrics and Capture

## D1: Capture capabilities are advertised via the EXISTING `member.scope` column

- **Decision**: A capture capability (`camera.capture`, `camera.record_video`, `audio.record`)
  is just another entry in the edge member's `scope` column — the exact same mechanism
  `RiskRouter.candidates()`/`covers()` already use to find which AGENT member can handle a
  named capability (`router.py:34-39`). No new inventory/advertisement mechanism.
- **Rationale for FR-007a (per-type opt-out, toggle-by-omission)**: since `covers()` is a
  simple scope-membership check, a disabled type is just absent from `scope` — the Border has
  no way to even see it, exactly as required ("not requested and refused, but never offered").
- **New wire method**: `n2n/edge/register_capabilities` (phone → Border) — the app calls it at
  connect time and whenever the operator changes a capture toggle in Settings, with the
  currently-enabled capability names; the Border writes them into `member.scope` (replacing
  prior capture entries, leaving `enrollment`-time base scope `[]` semantics from 066
  otherwise undisturbed). Mirrors `n2n/edge/register_push`'s existing shape exactly
  (service.py `_edge_on_register_push`).

## D2: Border-initiated capture reuses `n2n_delegate` — zero new MCP tools

- **Decision**: The agent requests a capture from the phone exactly the way it already
  delegates any named capability to a member: `n2n_delegate(target_name="camera.capture",
  input_text="")`. `route_and_delegate()` (`service.py:1268-1276`) already resolves
  `target_name` to a member via `RiskRouter.select_member()` — this works unchanged for an
  edge node once D1's scope entries exist. What's NEW is a branch in delegation: today
  `delegate_to_member()` unconditionally calls `n2n/tasks/submit` over `self.member_channels`
  (`service.py:1406-1414`); a target whose `node_type == 'edge'` must instead call a new
  `n2n/edge/capture` method over `self.edge_channels`, since a capture is "activate camera/mic
  and return a media result," not "run this skill against this text input."
- **Async tracking reused from 067**: mirrors `_edge_on_ask`'s exact pattern (research 067-D4)
  — the Border creates a `self.tasks` entry and runs a background worker that calls
  `ch.call("n2n/edge/capture", {...})` and awaits the result; `n2n_task_status`/
  `n2n_task_result`/`n2n_task_cancel` (already reachable from any source, unchanged) work
  transparently regardless of whether the target was an agent member or an edge node.
- **Rationale**: a capture may wait on the operator physically taking a photo — an unbounded
  real-world delay, same reasoning that makes agent-member delegation async in the first place.

## D3: Phone-initiated capture (US2) needs NO new wire method

- **Decision**: A phone-initiated capture (photo/video/voice, with or without accompanying
  text) is sent as an OPTIONAL `attachment` field on the EXISTING `n2n/edge/ask`
  (`{"text": "...", "attachment": {"content_type": "image", "content": "<base64>"}}`) — FR-006
  explicitly requires "no parallel attachment path," and `n2n/edge/ask`'s existing handler
  (`_edge_on_ask`, service.py) already just forwards `text` into `gateway.run_agent_turn()`;
  it needs only to fold a present attachment into the prompt (e.g. as an image block) before
  that call, not a new dispatch path.

## D4: Capture size caps are enforced entirely client-side, at capture time

- **Decision**: `NCFED_MAX_MESSAGE` (16 MiB, `bgp/constants.py`, unchanged) is the ceiling; the
  Dart capture UI enforces a duration/resolution/bitrate budget that keeps every capture
  comfortably under it (FR-005a) — refusing/truncating at capture time, never discovering the
  overage at send time. No Border-side size-check code is added; the existing channel framing
  (already chunks/rejects oversized messages, feature 052/063) is the backstop, unchanged.

## D5: Biometric-gated approval push reuses `push_to_edge()`/`n2n/edge/message` with a new `content_type`

- **Decision**: `notify_approval()` (`service.py:163-169`) currently only calls the never-wired
  `self.approval_notifier` hook. This spec is the FIRST real delivery mechanism behind it
  (per the spec's own Overview) — extend `notify_approval` to ALSO push to every connected edge
  channel via the EXISTING `push_to_edge()` (066/US2), with a new `content_type="approval"`
  carrying the structured fields (`approval_id`, `device`, `change`, `reason`,
  `requesting_agent`, `risk_name`). Backgrounded delivery is free: `push_to_edge`'s existing
  disconnected-fallback to FCM/APNs (066/US3) already covers FR-001's "push notification if
  backgrounded" clause with no new code.
- **Rationale**: satisfies FR-001 literally ("using spec 066's existing push delivery
  mechanism") and keeps `n2n/edge/message` as the SINGLE Border-to-phone content-delivery
  method rather than adding a second one for a different content shape.

## D6: Biometric resolve is one new wire method calling the EXISTING `resolve_approval()` unchanged

- **Decision**: `Authorizer.resolve_approval(approval_id, action, via="cli")`
  (`authorization.py:149-157`) already takes an arbitrary `via` string — the exact "resolution
  method" field FR-004 needs. Zero changes to that function or the CLI/HTTP path
  (`bgp-daemon-v2.py:342-344`, unchanged — confirms FR-004's "existing CLI/HTTP approval path
  MUST continue to work unchanged"). One new inbound edge method,
  `n2n/edge/approval_resolve` (phone → Border), whose handler calls
  `self.authz.resolve_approval(approval_id, action, via="biometric")` directly.

## D7: Biometric authentication is 100% on-device; the Border never sees or verifies it

- **Decision**: `local_auth` (Flutter's standard biometric package, wrapping iOS
  LocalAuthentication / Android BiometricPrompt) runs entirely on the phone. The Border trusts
  the phone's report the same way it already trusts any other edge-node-originated action
  (066/067's operator-extension model) — there is no biometric proof/token sent over the wire,
  by design (FR-003: biometrics gate the local decision, never the cryptographic identity
  066 established). This means `n2n/edge/approval_resolve`'s Border-side handler does no
  biometric-specific verification at all — the `via="biometric"` tag is honest bookkeeping, not
  a security boundary the Border enforces.

## D8: Capture UI packages

- **Decision**: `camera` (photo + video capture) and reuse `record` or extend the existing
  voice-recording path from 067's `speech_to_text`-adjacent audio pipeline for voice notes —
  exact package for audio-only recording (distinct from speech-to-text, which discards the
  audio after transcribing) is a Phase 2 task detail. `local_auth` for biometric gating
  (US1). No new camera/mic PLATFORM PERMISSION plumbing beyond what 066/067 already added
  (`NSCameraUsageDescription`/`NSMicrophoneUsageDescription` in Info.plist; Android permissions
  auto-merge from each plugin's own manifest, confirmed working pattern from 066/067).
