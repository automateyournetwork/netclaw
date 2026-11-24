# Pass25 — world3: browser launch failure cleanup

Assignment: SPEC200_WORLD_PASS=25, SPEC200_WORLD_NUMBER=3, source_refinement.
Spec Kit prerequisites and checklists pass (requirements15/15, quality43/43).
Optional Git hooks skipped; existing GAIT root/audit branch reused.

All three browser.test.mjs scenarios now share a test-only fixture helper that
registers teardown immediately after creating the private temporary directory,
before manager creation or Chrome launch. Nested finally blocks close the manager
and remove its owned state even when browser.close rejects. Launch/newPage errors
remain failures. No installed Chrome repair, viewer/runtime change or new module
in the live29-file source closure.

Evidence: `.spec200-local/tests/world-pass-25/`.

- Corrected red subprocess test reproduces the leaked manager/process timeout.
  Initial invocation inherited NODE_TEST_CONTEXT and skipped its child tests;
  that failed harness result is retained separately. Final probes remove that
  variable and disable child runner isolation, keeping timeout ownership in one
  process. No remaining owned probe process was found after the red run.
- Cleanup regression3/3: injected launch, page creation and browser.close failure.
  Each independent supported-Node process exits with its original failure within
  four seconds, without timeout/signal, and leaves no manager state directory.
  Each child error log is retained; this is synthetic fault injection.
- Actual isolated Chrome3/3, zero skips: fixture playback/recording/event/stop,
  budget display and nine media-readiness scenarios. Actual screenshot reviewed:
  awaiting-media banner, disabled event/checkpoints and enabled stop/evidence are
  legible. All media/status packets are synthetic; Google calls remain zero.
- git diff --check passes. Private hashes and native GAIT start/final/log retained.

This repairs test resource ownership on rejection, not Chrome's historical dyld
launch failure or the unexplained pass22/23 playback timeouts. A permanently hung
browser.close is not qualified by these immediate rejection cases. No generated
city/camera/landmark/event review or provider/member/human acceptance is claimed.

Next concrete defect: eventshot shares the generic canInteract predicate and can
capture an event checkpoint before an event is sent/acknowledged. Qualify ordering
against original event state with synthetic delayed/refused/unknown outcomes;
preserve the distinction between send acknowledgement and visible effect.

No checkbox closes:15/30. No provider/device calls, dotenv read, private export,
authority/control/allowance/acceptance/PROGRESS edits, owner runtime changes,
agents/loops, branch changes, Git commits or publication. Coordinator owns live
packets; hosted worlds3–5 require actual1/2success. T029 remains human-only.
Preserve198at856bbc88and199AWS. No tickets or external communications.
