# Pass33 — world4: recording harness resource ownership

Assignment: SPEC200_WORLD_PASS=33; SPEC200_WORLD_NUMBER was unset. The current
handoff and ten-passes-per-world control assign pass33 to world4, source_refinement.
Spec Kit prerequisites passed; requirements15/15 and quality43/43. Optional Git
hooks skipped; existing GAIT root and audit branch reused.

All three recording.test.mjs setup sites now use the existing test-only fixture.
It registers teardown before manager or browser acquisition, owns launchServer
before attempting connect, and preserves manager close/directory removal in
nested finally blocks even when browser/server close rejects. Original launch,
connect and page errors remain failures. No live source module or closure change.

Private evidence: `.spec200-local/tests/world-pass-33/`.

- Red: all three actual recording setup sites timed out after four seconds when
  pointed at a deliberately absent Chrome executable. Retained cleanup-red.log
  proves the leaked manager kept each child alive; no fixture session was started.
- Green:11/11 bounded independent Node probes, zero skips. Covers direct launch,
  newPage and close failures; server launch, connect, page and close failures;
  simultaneous connect/close failure; all three original recording setup sites.
  Each child exits with its expected failure, without timeout/signal, and removes
  its manager state. Acquired server close is explicitly witnessed.
- Actual Chrome recording10/10, zero skips: lost final/evidence replies, browser
  death,0/250/1250ms final-upload delays and constructor/recorder/upload/timeout
  faults. Shared direct-launch viewer smoke2/2, zero skips, covers fixture
  playback/controls/event/recording/stop and single-flight checkpoint ambiguity.
- Reviewed recording-failure-1280.png: explicit synthetic/no-Google banner,
  Recording incomplete, retained terminal receipt/reconciled usage, disabled
  session controls, accessible View evidence. No Google visuals are present.
- git diff --check passes. Hashes, result summary and native GAIT retained privately.

This qualifies immediate rejection cleanup, not permanently hung close promises,
Chrome's historical dyld cause or Google service behavior. No task checkbox closes;
15/30 remains. No camera/landmark/drift/fictional-event visual acceptance, member
installation or human T029 acceptance is supplied. No tickets or communications.

Next concrete interaction check: viewer maps keyboard events by case-sensitive
`event.key`. Pressing w, then Shift, then releasing W can miss the stored w key
and leave movement held until Escape/blur. Reproduce in actual Chrome with captured
synthetic control packets, repair down/up identity consistently, and retain focus/
Escape/repeat protections. This is source inspection, not yet observed behavior.
The separate member-browser harness still registers cleanup after launch; its
snapshotRegistryPath option needs preservation if later migrated to the helper.

No provider/device/CML/SSH calls, dotenv reads, sealed/control/allowance/acceptance/
PROGRESS changes, owner runtime changes, agents/loops, branch changes, Git commits
or publication. Coordinator owns fresh live packets; hosted worlds3–5 require
actual1/2success.198at856bbc88 and199AWS preserved.
