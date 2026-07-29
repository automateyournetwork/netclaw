# Phase 0 Research: NCFED Mobile Command Channel

No `NEEDS CLARIFICATION` markers remain in the spec (resolved in the prior `/speckit.clarify`
session). This document records the implementation-approach decisions needed to turn the
clarified spec into a design.

## D1: How does a Slack/CLI-originated message actually get answered today?

- **Decision**: There is no in-repo "message router." OpenClaw's own runtime (a separate
  installed system, not source in this repo) receives Slack/TUI messages and runs its own
  agent loop directly — this repo only supplies MCP tools/skills the agent calls. The daemon
  (`bgp-daemon-v2.py`) is a SEPARATE process from that agent and has zero LLM-calling code of
  its own; when it needs to hand text to the agent and get a reply back (peer chat, delegated
  skill execution), it shells out to the `openclaw agent` CLI via `gateway.run_agent_turn()`
  (`gateway.py:187-286`).
- **Rationale for 067**: the phone's request arrives at the DAEMON (over the edge WS channel),
  not at OpenClaw's own channel-listening loop — so the daemon must bridge it into the agent
  exactly the way `chat.py`'s `_ask_gateway` already does for peer-to-peer chat
  (`chat.py:80-87`), not invent new agent-invocation plumbing.
- **Correction to an implicit assumption in the spec's Dependencies section**: feature
  043 (Twilio voice)'s `webhook_server.py` looks like a template for "external channel → agent
  → response" but its primary path POSTs to a `/v1/chat/completions` REST route OpenClaw's
  gateway (2026.6+) no longer exposes (`gateway.py:1-11` states this explicitly) — it silently
  falls through to a degraded direct-Anthropic-API fallback with only 7 hardcoded tools. **Do
  not use 043 as the template.** `chat.py`'s `_ask_gateway`/`run_agent_turn` pattern is the
  current, correct one (post-dates 043's REST assumption).

## D2: Trust flag for the agent turn — `untrusted=True` or `False`?

- **Decision**: `untrusted=False` (the default) — `run_agent_turn`'s `untrusted` flag exists
  specifically to mark EXTERNAL (eN2N) peer input (`gateway.py:202-207`); a phone request is
  the OPERATOR'S OWN device (FR-002's operator-extension model — the same unchecked local
  access Slack/CLI/TUI already have). `chat.py`'s peer-chat path passes `untrusted=True`
  because that path is genuinely external; this one must not copy that unconditionally.

## D3: Delegation (US2) and eN2N routing (US3) need NO new code

- **Decision**: `n2n_route`/`n2n_delegate`/`n2n_invoke`/`n2n_chat` are `@mcp.tool()` functions
  the AGENT calls itself, as part of its own reasoning, when it decides an incoming request
  needs cross-claw routing (`server.py:298,324,443,670` — confirmed by reading each; none is
  triggered by an automated process). Once the phone's text reaches the agent via D1/D2's
  bridge, the agent's EXISTING tool-using behavior handles delegation/eN2N-routing and
  produces an attributed reply exactly as it already does for a Slack-originated "recreate my
  lab" or "ask Byrn's claw" request (`workspace/skills/n2n-federation/SKILL.md`'s existing
  workflow docs). US1/US2/US3 are the SAME mechanism (one agent turn); they differ only in
  what the agent's own reasoning decides to do, not in any Border-side code path.

## D4: Async task tracking, not a blocking RPC call

- **Decision**: A single `run_agent_turn` call can take up to its timeout (default 300s) —
  too long to hold open a synchronous RPC response, and FR-012 (cancellable) has no target
  without a task_id. Reuse the EXISTING `TaskManager` (feature 053, `tasks.py`) exactly as
  `_in2n_member_submit` (`service.py:1451-1490`) already does for member-delegated skill
  execution: `tasks.create(...)` returns a `task_id` immediately; `tasks.run(task_id, worker)`
  spawns the agent turn in the background; the phone can then poll `n2n/tasks/status`/`result`
  or (better, since the WS connection is already persistent) the Border proactively pushes the
  result via `ch.notify("n2n/edge/ask_result", ...)` once done.
- **Reuse, don't reinvent**: `Invoker.handle_task_status`/`handle_task_result`/
  `handle_task_cancel` (`invocation.py:224-235`) are ALREADY fully generic — they take
  `(channel, params)` and use `channel.peer_identity`, which `EdgeChannel` already has
  post-auth. Register the SAME three handler functions under the SAME method names
  (`n2n/tasks/status`, `n2n/tasks/result`, `n2n/tasks/cancel`) in `_edge_border_handlers`
  rather than writing new ones — this is the "existing task-cancellation mechanism as-is"
  FR-012 asks for, literally.

## D5: New wire method — `n2n/edge/ask`

- **Decision**: One new Border-side inbound method, `n2n/edge/ask` (phone → Border), added to
  `EDGE_METHODS` and `_edge_border_handlers` alongside `n2n/tasks/status`/`result`/`cancel`.
  Deliberately NOT `n2n/edge/message` — that method is documented as Border-initiated-push-only
  (`service.py:144-147`, feature 066 FR-008/FR-009's explicit-push boundary); reusing it
  bidirectionally would blur a line 066 drew on purpose. The Border's async result is pushed
  back via a distinct `n2n/edge/ask_result` notification (Border → phone), matching D4.

## D6: Per-device independent conversation history (FR-007) lives entirely on the phone

- **Decision**: The Border does not need a new persistent "conversation" table — `session_key`
  passed to `run_agent_turn` (`f"n2n-edge-{member_id}"`) already gives each enrolled device
  its own agent session, matching `chat.py`'s `f"n2n-chat-{peer}"` pattern. The actual
  chat-history UI/persistence (surviving app restart/reboot, SC-004) is a Dart-side concern —
  the same `path_provider` + JSON-Lines pattern `MessageFeedStore` (066) already established,
  just a second store (`ConversationStore`) keyed by nothing extra since it's already
  per-installation (one device = one store).

## D7: Voice requests (US4) — where does transcription happen?

- **Decision**: On-device transcription before sending, using a Dart speech-to-text package
  (the spec's own Assumptions section states this is an implementation choice, not a
  behavioral requirement — "not observable to the operator as a behavioral difference"). This
  keeps the wire protocol identical to a typed request (`n2n/edge/ask` with `{text}}` — no
  separate voice wire method, no server-side transcription code, and no new NCFED payload size
  concern (068's capture size cap doesn't apply here — a voice REQUEST is transcribed to text
  before it's ever sent, unlike 068's voice/image ATTACHMENTS which do travel as media).
- **Alternative considered**: server-side transcription (Whisper, matching the existing
  `openai-whisper-api` skill referenced in 042/043's voice work) — rejected for this spec
  because it would require a new binary wire payload type and a new Border-side dependency for
  a P2 story that has an equally-valid, simpler on-device option; 068 already owns
  audio-capture/attachment wire semantics if a future spec wants server-side transcription for
  a genuine audio attachment.

## D8: Device deep link (US5) resolves via existing source-of-truth integrations

- **Decision**: `netclaw://device/<id>` (or its QR-code form) is a pure client-side shortcut —
  the Dart app parses the identifier and submits a normal `n2n/edge/ask` request with a fixed
  prompt template (`f"What is the current status of device {id}?"`). No new Border-side
  method, no new device registry (per the spec's own Assumptions section) — resolution against
  NetBox/inventory/etc. happens exactly as it already does when the same question is typed.
  An unrecognized identifier surfaces as whatever "unknown device" response the agent's
  existing inventory-lookup tools already produce for a typed equivalent — not a new error
  code invented here.
