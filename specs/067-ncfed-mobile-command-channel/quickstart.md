# Quickstart: NCFED Mobile Command Channel

Prove the phone-to-Border ask flow end-to-end, then the automated checks.

## Manual walkthrough

1. **Confirm 066 is live**: an enrolled, connected edge node (per spec 066's own quickstart)
   exists and its heartbeat is healthy.
2. **Ask a direct question**: from the phone's Chat screen, type a question the Border can
   answer without delegation. Confirm a task_id returns immediately and the answer arrives via
   `n2n/edge/ask_result` shortly after, attributed to the Border itself.
3. **Ask a question requiring a member**: type a question only an enrolled iN2N member can
   answer. Confirm the answer arrives attributed to that specific member, not the Border.
4. **Ask a question requiring an eN2N peer** (if federated peers exist): confirm the answer is
   attributed to the external peer, or refused/audited identically to a non-mobile eN2N request
   if no grant exists.
5. **Cancel an in-progress request**: submit something slow enough to catch mid-flight, cancel
   from the phone, confirm the conversation shows "cancelled" — never "failed" and never both
   cancelled and completed for the same request.
6. **Restart the app**: confirm prior requests/answers are still in the conversation history.
7. **Voice**: record and send a voice message equivalent to step 2's question; confirm the
   same answer behavior.
8. **Device deep link**: scan/open a `netclaw://device/<id>` link; confirm a device-status
   request submits with no typing, and an unrecognized id fails explicitly.

## Automated checks

```bash
cd ~/netclaw
python3 -m pytest tests/n2n/test_edge_ask.py -q

cd mobile/netclaw-mobile
flutter test
```

## Success signals (from spec)

- SC-001: correct attribution regardless of who actually answered, 100% in testing.
- SC-002: unauthorized requests refused/audited identically to non-mobile ones.
- SC-003: voice and text requests produce equivalent answers.
- SC-004: conversation history survives app restart/reboot, 0% loss.
- SC-005: no request left indefinitely pending — same timeout budget as non-mobile.
- SC-006: device deep link/QR produces an answered or explicitly-failed request, zero typing.

## T027: automated coverage as of implementation — mapped to SC-001…SC-006

`python3 -m pytest tests/n2n -q` → 255 passed, 0 regressions (was 249 before this feature).
`flutter test` (mobile/netclaw-mobile) → 32 passed, 0 regressions (was 20 before this feature).

| SC | Covered by | Notes |
|----|------------|-------|
| SC-001 | `test_edge_ask.py::test_edge_ask_creates_task_and_returns_immediately`, `::test_edge_ask_result_pushed_to_connected_phone`, `::test_edge_ask_task_owner_bound_to_submitting_device` | Attribution itself is agent-composed text (research D3) — not independently automatable; the owner-binding test proves no edge-specific code path exists to misattribute across devices. |
| SC-002 | `test_edge_ask.py::test_edge_ask_task_owner_bound_to_submitting_device` (structural: no special-casing exists), `chat_screen_test.dart` | A live eN2N-grant-refusal scenario (T017) needs a real federated peer — manual-only, see below. |
| SC-003 | `voice_transcription_test.dart` (all 3 cases) | Proves voice produces the *identical* `n2n/edge/ask` request shape a typed message would — the strongest automatable proxy for "equivalent answers" without a live agent. |
| SC-004 | `conversation_store_test.dart::appended turns persist across a simulated app restart` | Direct coverage. |
| SC-005 | `test_edge_ask.py::test_edge_ask_failure_surfaces_not_hangs`, `::test_edge_ask_task_cancellable_via_existing_mechanism`, `::test_edge_ask_cancel_after_completion_is_a_noop` | Direct coverage, including the completion/cancel race edge case. |
| SC-006 | `device_deep_link_test.dart` (all cases) | The "unrecognized identifier fails explicitly" half is proven structurally (T023: no separate client-side unknown-device path exists — it's the same agent-turn failure SC-005 already covers), not by simulating an actual unknown-device agent reply. |

### T017 (US3, manual-only) and T029 (full walkthrough) — real-daemon verification performed

Ran against a throwaway (non-production) Border daemon — isolated `HOME`, isolated SQLite DB,
distinct ports (`BGP_API_PORT=28179`, `BGP_LISTEN_PORT=21179`, `N2N_EDGE_WS_PORT=28443`) — never
touching the real production daemon's state:

1. Issued a real edge enrollment QR via `netclaw risk token --edge`.
2. A Python WS client (mirroring the Dart wire protocol exactly) completed the full `wss://`
   enrollment handshake against the real daemon subprocess — `member` row created for real,
   `node_type='edge'`, GAIT-audited (`n2n.audit: AUDIT[in2n] inbound ... enroll ... success`).
3. Sent `n2n/edge/ask` against the real daemon — got a `task_id` back immediately (non-blocking,
   confirming SC-001/SC-005's "never hangs" holds against a genuinely separate process, not just
   the in-test-process pytest harness).
4. The task correctly failed cleanly (`state: 'failed'`, `[Errno 2] No such file or directory:
   'openclaw'`) because this throwaway sandbox has no `openclaw` CLI installed — this is EXPECTED
   and is itself a real confirmation of FR-010 (surfaces failure, never hangs) against a live
   process.
5. Disconnecting the WS client correctly flipped the member's `state` to `unreachable`.

**Not performed** (needs the operator's Mac and/or a real device): an actual `openclaw agent`
call succeeding end-to-end (needs a real OpenClaw install + credentials in the test sandbox);
US3's live eN2N-peer attribution (needs a real second federated Border); the actual Android
build was verified separately (see `mobile/netclaw-mobile/README.md`'s platform notes) but not
re-run in the exact same session as this throwaway-daemon check due to an environment restart
mid-session — both were independently confirmed working, just not simultaneously.
