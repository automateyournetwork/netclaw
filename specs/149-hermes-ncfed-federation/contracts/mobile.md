# NetClaw Mobile / Hermes Border contract

Existing enrollment and NCFED method names remain unchanged. A verified active enrolled edge device is an operator extension; backend ingress alone mints `origin=operator`, `profile=operator`. Scope requester includes the device identity and conversation ownership is installation+device+pinned-key generation+client conversation. Never infer this trust from a harness card, prompt or user-provided origin. `origin:voice` is interaction metadata only.

Ask accepts existing text/attachment/origin fields plus optional stable request/conversation IDs and `task_outcomes_v1` capability. New client persists its request reference before dispatch. An ambiguous receipt is uncertain; query the existing status/result method with the owned request reference and the current authenticated enrollment generation to discover the original task. Duplicate owner/request/body maps to one task; different body refuses. Legacy peers need not implement this extension and must never be blindly resent.

Task canonical states include outcome_unknown and interrupted. Cancellation carries requested and confirmed facts separately. New clients show explicit labels/messages, retain recoverable owned handles and never auto-resubmit. Legacy clients receive an existing terminal fallback with explanatory error/outcome_state when they cannot render new terminal states; no uncertainty is mislabeled successful or confirmed cancelled. Reconnection reconciles owned tasks, not native run/session IDs.

The protected mobile operator profile can use the same named, bounded n2n MCP subset as HUD. Per-effect checks read the active admission and current enrolled device state. Channel replacement during reconnect preserves device ownership; removed/quarantined devices cannot execute new effects or retrieve another owner's work. Returned task/chat handles belong to the device conversation.

Voice composition reuses the existing gateway voice instruction before scoped body hashing. Text transcription is ordinary text; Siri origin voice changes response composition only.

Hermes photo/video support is initially unavailable. Advertise attachments:false; reject any media submission before inference with a capability_unsupported explanation. Updated mobile gates capture submission appropriately; legacy media requests receive explicit refusal. OpenClaw media behavior remains independently covered.

Safe Border harness metadata is additive beside model/capabilities. Missing/invalid means unknown. Complete new-state UI targets mobile1.0.3+5; baseline1.0.2+4 remains wire-compatible for supported text with documented legacy projections. Build/evidence must state actual SDK, artifact type/signing and protocol/simulator/physical-device coverage. No store publishing.
