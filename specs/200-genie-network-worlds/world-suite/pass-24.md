# Pass24 — world3: gate interactions on retained baseline

Assignment: SPEC200_WORLD_PASS=24, SPEC200_WORLD_NUMBER=3, source_refinement.
Spec Kit prerequisites pass; requirements15/15 and quality43/43. No optional Git
hooks. Reused current GAIT root/branch. Same sealed snapshot remains untouched.

Event, navigation/event checkpoints and keyboard movement now require active
status, an open media socket, a decoded frame and a successfully saved baseline.
The first baseline is single-flight across overlapping decodes. Pending/failed
baseline, recording/media failure, disconnect, stop and terminal state disable
interaction. Late decoded frames after end are discarded; late baseline completion
cannot reopen controls. Escape/key release, stop, evidence and local facts remain
independent. Completed buttons stay disabled across later frames/status refreshes.
No provider admission, reservation, receipt or settlement behavior changes.

Evidence: `.spec200-local/tests/world-pass-24/`.

- Red test reproduced pre-frame event/checkpoint enablement.
- Final isolated actual Chrome3/3, zero skips, including nine synthetic media
  scenarios: terminal/disconnect without frames, malformed JPEG, decoded-terminal,
  decoded-error/disconnect, failed baseline, pending baseline plus overlapping
  frame/terminal, and delayed decode after terminal. Tests assert movement gating,
  one baseline request, preserved stop/evidence access and completed controls.
- Recording fault/recovery/shutdown10/10 and source-review4/4 pass, zero skips.
- Initial validation assertion read WebSocket key delivery before keyup arrived;
  corrected to await the actual pair. Retained browser.log; no provider call.
- A later overlapping run failed before fixture playback: actual Chrome launch
  SIGABRT, dyld framework missing in a macOS code-sign clone. Cleanup was registered
  after launch, leaving the fixture manager open. Retained browser-verified.log
  and owned-process inventory; only its two test processes were terminated.
  Isolated rerun3/3 passes. Earlier pass22/23 playback timeouts remain unexplained;
  this distinct launch failure is not their diagnosis.
- Actual1280px screenshot reviewed: awaiting-media banner, disabled event and
  checkpoint buttons, enabled stop/evidence and separate facts remain legible.
  Synthetic fixtures/statuses only; zero Google calls and no generated-world review.
- git diff --check passes. Native GAIT start/final and gait_log plus hashes retained
  privately. Existing29-file source closure unchanged; old paid packets are stale.

Next concrete defect: browser.test.mjs registers teardown after chromium.launch;
launch failure leaks the already-created fixture manager and prevents test exit.
Register resource-safe teardown immediately after manager creation, then inject
launch failure to prove bounded cleanup without altering installed Chrome. This
is supported by this pass's retained actual failure. Separately, event checkpoint
still enables before an event receipt; evidence ordering remains an open review.

No checkbox closes:15/30. No live Google/member/T029 acceptance, provider/device
call, dotenv read, private export, authority/control/allowance/acceptance/PROGRESS
edit, owner runtime change, agents/loops, branch change, Git commit or publication.
Coordinator alone refreshes exact live packets; hosted worlds3–5 still require
actual1/2success. Preserve198at856bbc88and199AWS. No tickets/communications.
