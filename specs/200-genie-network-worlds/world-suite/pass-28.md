# Pass28 — World3: single-flight checkpoint capture

Assignment: SPEC200_WORLD_PASS=28, SPEC200_WORLD_NUMBER=3; source_refinement.
Followed current authority, handoff and Spec Kit implementation prerequisites;
requirements15/15 and quality43/43 remain passed. Optional Git hooks skipped.

## Concrete change

Navigation and event checkpoint actions claim their pending state synchronously,
before HTTP. Double clicks, direct handler calls and later media/status messages
cannot submit another image. Separate accessible capture text reports Saving,
Saved or Unconfirmed; it survives ordinary session status updates. Requests have
a three-second timeout. Failure/lost response leaves the capture locked and
points to original-session evidence; no capture/event replay or new session.
Stop stays independent while persistence is pending. A locally refused capture
cannot be marked saved. Baseline and recording-final protections remain intact.

## Evidence

- Red actual Chrome test reproduced the enabled pending navigation button.
- Final actual Chrome5/5, zero skips; new test covers ten synthetic cases:
  navigation/event × delayed save, HTTP500, response loss, timeout, stop-pending.
  Each asserts one POST, persistent lock, no event replay and no new session.
- Source closure/backend event correlation5/5, zero skips. No new live module;
  existing29-file closure membership unchanged. Viewer JS/HTML bytes changed;
  previous paid packets are stale and require coordinator review.
- Broader recording regression9/10: final_response_loss hit Chrome dyld missing
  framework during launch. Recording harness creates manager before registering
  cleanup; the failed launch left the test process alive after other cases.
  Terminated only this pass's owned test child (SIGTERM). Isolated failed case
  then passes1/1. Original failure retained; cause is not claimed fixed.
- Reviewed actual synthetic browser screenshot: uncertainty text readable,
  event capture locked, stop/evidence available, fixture identity explicit.
  No Google visual, camera, landmark, event visibility or drift evidence exists.
- git diff --check passes; private control and PROGRESS hashes unchanged.

Private results/screenshots/hashes/native GAIT and gait_log:
`.spec200-local/tests/world-pass-28/`. No test is relabeled real network or Google
proof. No checkbox closes;15/30 tasks. T029 requires the actual owner.

## Next concrete defect and limits

Backend navigation checkpoint POST still lacks event-equivalent active-session,
baseline and subsequent-frame checks. Add meaningful direct HTTP ordering tests
and enforce that boundary; navigation evidence still cannot prove deliberate
movement or fidelity. Separately migrate recording.test.mjs startup cleanup to
register before Chrome launchServer; pass25 fixed browser.test.mjs's helper only.
Do not run source-review tests that mutate served files alongside browser tests.

No provider/device/CML/SSH calls, dotenv reads, paid/private export, control/
allowance/acceptance/PROGRESS changes, owner runtime edits, agents/loops, branch
changes, Git commit or publication. Same sealed snapshot remains untouched.
Hosted worlds3–5 remain gated on coordinator-recorded world1/2 technical success.
198at856bbc88 and199AWS preserved.
