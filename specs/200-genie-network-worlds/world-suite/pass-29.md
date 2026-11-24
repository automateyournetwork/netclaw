# World-suite pass29 — world3 navigation checkpoint ordering

Assignment: SPEC200_WORLD_PASS=29; SPEC200_WORLD_NUMBER was unset. World3 follows
the ten-passes-per-world schedule and current handoff. Offline source refinement.
Spec Kit prerequisites passed; requirements15/15 and quality43/43. Optional Git
hooks skipped as instructed. Existing GAIT root/audit branch reused.

## Concrete change

Navigation checkpoint POST now rereads session state after receiving the body,
requires the original session active and its baseline present, and accepts only
a viewer-claimed sequence among the backend's last256 observed worker frames
newer than every frame received when baseline was saved. Missing, old, invented,
inactive and restarted-session submissions fail without a new capture. The
viewer submits its last decoded sequence. Captures remain immutable and do not
create event receipts or live acceptance. No new runtime module was added; the
existing29-file closure membership is unchanged, with changed manager/viewer bytes.
All prior paid packets remain stale and require coordinator review.

## Evidence

- Red direct HTTP test reproduced pre-baseline navigation acceptance (200 vs400).
- Backend/core24/24; active success, missing baseline/sequence, old/invented frame,
  immutable capture, inactive session and restart refusal covered.
- Actual Chrome5/5, zero skipped; existing navigation/event/recording/stop and
  pending/response-loss cases pass with the stricter backend.
- Reviewed private fixture-viewer.png: Navigation Saved / Event Saved, ended
  controls, readable separate facts and explicit no-Google fixture banner.
- Source-review5/5 pass; results retained alongside all logs and native GAIT under
  .spec200-local/tests/world-pass-29/.

## Limits and next defect

The frame reference is viewer-claimed; Canvas JPEG pixels are not authenticated
against the worker source image. This ordering gate does not prove10seconds of
navigation, camera motion, landmarks, recognizability or drift. Baseline barrier
is process-local and never reconstructed after restart. Navigation has no durable
correlation receipt; the artifact manifest alone proves only retained bytes.
No Google captures exist. No task closes;15/30 remains unchanged.

Next bounded unit: viewer navigation button currently enables on the initial
baseline before a subsequent frame is decoded. Add a baseline-acknowledgement
barrier (including in-flight decode) and visible waiting state before single-flight
navigation capture. Preserve no replay on uncertainty. Secondary existing gap:
recording.test.mjs cleanup must register before Chrome launch/launchServer.
Event JPEG/SQLite crash gap remains unconfirmed, with no repair in this pass.

No provider/CML/SSH/device calls, dotenv reads, private projection export, owner
runtime or sealed/control/allowance/acceptance/PROGRESS changes. No agents/loops,
branch changes, Git commits or publication.198at856bbc88 and199AWS preserved.
World3 hosted execution still waits on coordinator-recorded success of1/2.
No model supplies human T029 acceptance.
