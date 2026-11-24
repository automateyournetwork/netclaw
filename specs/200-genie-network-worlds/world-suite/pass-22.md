# Pass22 — world3: reviewed session duration and cost

Assignment: cinematic network city, source_refinement. Used the current handoff
and Spec Kit implementation workflow; requirements15/15 and quality43/43 pass.
No generated Google world is available for world/camera/landmark review.

Replaced hard-coded20s/30s bounds and US$2.02/US$15 copy with authenticated
backend session_bounds. Draft values require the current validated packet;
status values preserve the original session policy/estimate/reservation even
when current authority is unavailable. Campaign120s/130s, legacy20s/30s and
free fixture mode are distinct. Display retains six-decimal USD precision,
video versus total estimate, reservation, and separate US$25soft/US$50hard
campaign limits. None is described as billed usage or a local provider cap.
Admission/settlement/persisted session records are unchanged.

Verification retained under `.spec200-local/tests/world-pass-22/`:

- Initial browser/manager/source-binding/provider recovery run:60passes and
  one30s fixture-browser timeout; zero skips. No cause established for timeout.
- Isolated browser rerun:2/2 pass (including the timed-out fixture), with actual
  Chrome screenshots/JSON. Campaign/legacy display tests use immutable synthetic
  response packets against a fixture-only manager; zero admission/provider calls.
- Targeted final backend campaign and historical original-ID checks:2/2 pass.
- Recording fault rerun:10/10 pass, zero skips. Initial recording run failed nine
  evidence writes because this pass omitted creating its output directory; the
  original errors remain in recording.log. Corrected test setup only.
- Existing29-file runtime source review covers all three changed runtime files;
  old packets are stale. No module/dependency added. git diff --check passes.

Viewed campaign and legacy screenshots: bounds and amounts wrap legibly without
clipping at1280px; legacy has no campaign limits. Empty Canvas and intercepted
Google-mode banner are synthetic UI evidence, never Google-generated pixels.
The visual review found the next concrete defect: the mode banner already says
GOOGLE GENERATED ILLUSTRATION before any provider frame has arrived. Qualify
awaiting-media, decoded-media and failed/no-frame labels in the next pass.

No checkbox/live/member/T029 acceptance, provider/device calls, dotenv reads,
private export, sealed/control/allowance/acceptance/PROGRESS changes, owner runtime
modification, agents/loops, Git branch/commit/publication or tickets. Source
refinement remains allowed for world3; hosted3–5 await coordinator-recorded live
success of1/2. Exact packets and authorization remain coordinator-owned.
Native GAIT start/end/log retained privately, using the existing root/branch.
Preserve198at856bbc88 and199AWS.15/30 feature tasks remain complete.
