# Coordinator visual observations

## After the pass02 synthetic screenshot

Reviewed .spec200-local/pass-02/local-world-1280.png. The local3D foundation
visibly preserves entity selection and has legible navigation controls. This is
an early technical view,not final visual-quality acceptance.

For a later T018refinement pass after collector/identity work:
- Give routers and switches recognizable,distinct network forms beyond simple
  blocks while preserving the exact graph. Improve depth/material/light and
  connection readability without adding decorative links or invented metrics.
- Use a compact human-readable selection summary (device/port,status,source/time,
  confidence,counter availability);keep raw JSON/hashes in expandable details.
- Retain the malicious-label fixture test,but capture showcase screenshots with
  a clean independent synthetic scene. Do not turn security-test payload text
  into the default demonstration artwork.
- Inspect the actual walkthrough close-up and overview,including labels near the
  camera and endpoints behind geometry. Keep full interface identity discoverable.
- Preserve explicit unavailable counters until the real normalization path exists.

Do not spend a paid generation or upload private screenshots for these local fixes.
Continue the dependency order;this review does not mark T018or visual acceptance done.

## Native collector source pointers reviewed during pass03

Installed selected-runtime upstream pyats_mcp_server.py has validate_show_command
(line427),run_show_command_async(line837),_get_device(line331) and
_execute_show_command(line514). The latter parses with implicit execution and
executes again on parse failure;_execute_show_raw is merely a wrapper around it,
NOT a capture-once primitive. Do not rely on its name. The public show tool also
uses asyncio.wait_for over a thread,so timeout alone does not establish termination.

scripts/lib/protected_pyats.py contains endpoint_identity,connection_policy,
validate_native_policy and execute_once. Its protected validate_arguments allows
ONLY show version. Preserve that existing restriction;do not widen or bypass a
protected tool grant. Its explicit connection/capture/offline-parse approach is a
reference for a separately qualified Spec200collector using the standard pyATS
read policy plus the frozen Spec200command allowlist. Native availability is not
proof of qualification. Verify exact emitted commands/SSH identity and parser
behavior before T016/T019closure. No actual new device command ran in this review.

## After pass07 independent screenshot review

Inspected actual synthetic local-network-1280.png and local-world-1280.png from
pass07. The shared inspector now explains endpoint identities, discovery certainty,
unknown current health, unresolved claims, failed read coverage and stale evidence;
raw proof details are appropriately expandable. This addresses the readable-summary
request above. Both graph and world remain clearly synthetic.

Remaining concrete visual defects for a later bounded refinement pass:
- The tall inspector stretches the scene panel into a large empty region below
  the canvas. Preserve the scene's natural height and use a readable independently
  scrollable evidence area or equivalent responsive layout; do not hide evidence.
- Router/switch shapes still read as generic blocks. Add recognizable distinct
  forms without implying extra physical ports or fabricated measurements.
- Verify routing/switch labels at the actual walkthrough close-up and narrow width,
  not just overview. Keep full endpoint identity accessible outside the canvas.

These are source/UI refinements only, not native facts or Google acceptance.
The currently shared owner URL remains a frozen pass02 synthetic preview until
explicitly refreshed; never describe it as current source or measured R1/R2/SW1/SW2.

## Owner preview refresh after pass08

The localhost58778 preview now serves a frozen pass08 source snapshot with the
existing independent synthetic four-device/three-link graph. Nine assets were
copied with matching before/after hashes; graph validation passed. Chrome verified
rendering, movement, key release and reset with zero external requests/page errors.
HTTP checks passed and refused environment/source/control routes. Evidence is in
.spec200-local/owner-preview/{snapshot-08,smoke-08.json,service.json}. The private
server owns no provider/device capability. Original pass02 assets are retained.
The first refresh guard rejected a relative process path before any mutation;
process cwd was then verified. A first smoke-script import path failed before
browser launch, was corrected, and the actual smoke check passed. This supersedes
the earlier note that the shared URL still serves pass02. No real topology shown.

## Verified lifecycle defect — prioritize T020 after pass09

Coordinator reproduced a worker lifecycle defect with an entirely synthetic
in-process provider. After one frame, key_down rejects while receive() blocks.
The worker records control_send_unknown, but unknown() sets finished=true, which
makes the periodic deadline return immediately. After1200ms with a1000ms deadline,
complete_calls=0,cancel_calls=0 and run_finished=false. The probe was manually
released locally so it left no process/session. No provider call occurred.

Reproducer:.spec200-local/ralph/coordinator-worker-loss-probe.mjs
Qualified result:coordinator-worker-loss-probe-qualified.json in that directory.
The initial fake ledger used the wrong transition argument signature, causing
its first two attempts to miss the failure; corrected before the qualified result.
Do not treat those invalid harness runs as successful fault verification.

Next bounded pass should implement meaningful recovery tests and correct this
T020 lifecycle gap before cosmetic refinement or any live trial. Keep durable
unknown/outstanding usage intact while separately bounding local transport/process
lifetime and attempting provider completion when possible. Do not infer remote
termination from local cancellation. Include stalled send/receiver, manager loss,
terminal arrival after unknown and missing terminal evidence. Inspect manager.close
which currently disconnects after6500ms but does not reap an indefinitely blocked
child. Existing worker/manager/provider/browser behavior must remain qualified.
No paid/live permission is supplied by this review.

## Pass10 follow-up review

Pass10 fixed the prioritized blocked-receiver defect. Original coordinator
failure JSON remains unchanged in .spec200-local/ralph/; the copied reproducer
and successful result are under .spec200-local/pass-10/. The latter records one
completion request and run_finished=true with an actual synthetic terminal event.
Full42-test Node/browser suite and final8 recovery tests passed. Source inspection
confirms unknown/cleanup separation, bounded receive/open/send grace, stop bypass
and manager reaping. Do not keep reprioritizing the now-fixed original defect.

For the remaining T020 fault pass, include rejection of a normal focus-loss
release (not only release during stop): the enqueue catch currently emits a control
error, whereas stop's release catch marks uncertainty. Verify the intended immediate
stop/unknown behavior and retained key/outcome evidence before qualifying this case.
This is a source-review test gap, not a claim of another reproduced live failure.
Recording/upload faults and host/network loss also remain in T020's stated scope.

## Pass11 resolves the focus-loss review item

The focus-loss release gap above is now reproduced, fixed and qualified by pass11.
Full48 source/browser tests and12 recovery tests passed, with originals retained.
Do not repeat either the original blocked-receiver defect or this release defect
as new work. Consult pass11 and its handoff for the final behavior and limits.

Next preferred bounded unit is the still-open T018 visual refinement: recognizable
router/switch forms and actual near-camera/visit labels at1280/820, preserving
all identities/ports/edges and evidence. Recording/upload faults remain a separate
future T020 unit. Native collection remains a real gate, not simulated success.

## Pass12 independent visual review and owner preview

Inspected overview1280, router visit1280 and switch visit820 synthetic screenshots.
Routing drums/arrows and lower switch chassis now visibly distinguish roles;
selected shapes and labels remain framed on actual visits. The scene panel no
longer stretches with the evidence inspector. Earlier generic-block/visit-framing
review items are addressed for this four-device fixture, not human acceptance.

The shared localhost58778 preview is now frozen pass12, including its independent
synthetic browser fixture (four devices,eight interfaces,three links,one counter).
Asset mtimes precede the completed pass12 handoff; before/after hashes matched.
Graph validation passed. A separate actual Chrome smoke verified navigation,
key release,reset and the synthetic counter inspector with zero external requests
or page errors. Evidence:.spec200-local/owner-preview/snapshot-12 and smoke-12.json.
Earlier snapshots remain retained. The preview is synthetic, not R1/R2/SW1/SW2
measurements or Google generation. No provider/device capability is exposed.

## Counter integration review for the upcoming native graph bridge

The current selection inspector shows derived rate/delta/utilization and sample
times, but not the individual observed counter values. When binding the installed
parser's interface samples into the graph, preserve readable raw counter values
and units with each sample's provenance even if timing/incarnation/continuity
makes a rate unknown. The owner's request includes actual counters, not only
rates. Keep observed sample values distinct from derived values; retain exact
large integer strings and explicit missing data. Do not manufacture continuity
just to make the inspector nonempty. This is an upcoming integration requirement,
not a claim that the current fixture proves real counter qualification.

## Pass17/18 counter sample visibility resolution

The raw-counter visibility review item is implemented: pass17 preserves and shows
observed counts independently of rates; pass18 connects normalized interface
counter observations through exact evidence-backed aliases into the graph and
shared inspector. Final pass18 verification reports69 Python tests,12 Node tests
and installed-parser-to-inspector synthetic qualification with zero device calls.
Do not repeat this visibility fix as new work. CDP/LLDP binding and the selected
native capture path still need integration/qualification; no actual lab read or
full task acceptance is implied. The owner preview remains the frozen pass12
synthetic snapshot, not automatically updated with every later source pass.

## Owner preview refresh after pass21

The shared localhost58778 URLs now serve frozen pass21 assets and the independent
synthetic browser fixture, including exact observed samples beside derived rates.
Before/after hashes and completed-checkpoint mtimes matched. Graph validation and
actual Chrome movement/key-release/reset/counter-sample inspector checks passed,
with zero external requests or page errors. Evidence is under ignored
.spec200-local/owner-preview/{snapshot-21,smoke-21.json,service.json}.
The preview's explicit asset allowlist excludes automation scripts,private service
metadata,environment and control routes; all four refusal checks returned404.
Older snapshots remain retained. This is synthetic, not native or Google acceptance.

## Completion-report precision after pass21

Pass21's structured tasks_completed field described two partial units instead of
existing Txxx IDs. The controller independently compared tasks.md and correctly
retained14/30; no checkbox was changed or acceptance inferred. Preserve that
historical result. Future output schema now limits completed entries to the30
actual task IDs and explicitly excludes partial units. This affects subsequent
fresh passes; no running controller logic,authorization or task inventory changed.

## Remaining-pass focus after detailed graph assembly

Once pass23's inspector integration is verified, prioritize the remaining selected-
runtime capture adapter/read-policy source gap and T020's outstanding host/network/
account recovery cases over further cosmetic refinement. The combined graph and
recognizable views already have substantial synthetic evidence. Prepare the fresh
NetClaw installation review where it can be done without crossing T014's direct-
world gate. Do not weaken native/human/live exit criteria to change the task count.

The coordinator's TCP-only check at20:53Z still finds no route to the controller
or any selected endpoint. Device operations remain coordinator-only; do not try
actual SSH collection inside a pass. Source/offline adapter work is independent,
and must preserve the existing protected show-version-only grant rather than
widening it. Native source pointers above remain relevant. The32-pass cap remains.

## Final bounded-pass readiness focus

After the native collector composition, use the remaining passes for concrete
outstanding recovery/inspection gaps and final artifact coherence, not cosmetic
repetition. Pass32 should leave a complete, honest readiness handoff and perform
appropriate changed-component/native-offline regression checks. The32-pass cap
must not reset or extend automatically. Incomplete live/native/human tasks stay open.

Quickstart still starts with "planned, not implemented" and suggests generating
tasks despite the existing30-task implementation. Reconcile that text with the
actual available source commands, synthetic preview and qualification limits;
do not imply a supported native deployment or an installed MCP wrapper. A fresh
NetClaw native-review artifact is still absent and T024 remains gated/preparatory.
Record the exact next implementation unit and current blockers, preserving failures.
The paid packet remains unauthorized and source-stale; only the coordinator may
refresh its source binding after final verification, never silently authorize it.

## Verified live source-binding gap — next priority after pass29

The coordinator's read-only closure check found LIVE_SOURCE_FILES still contains
15files and omits eight served viewer assets:network-graph.mjs,network.css,
network.html,network.mjs,selection.mjs,world-geometry.mjs,world.html,world.mjs.
manager.mjs statically imports network-graph.mjs, so the omission includes executed
backend code, not just decorative assets. Changed omitted files currently cannot
invalidate an exact source review. Evidence:.spec200-local/ralph/coordinator-source-closure.json;
zero provider requests. The private packet remains unauthorized/source-stale.

The next bounded pass after29 should fix the application's source closure in
live-packet.mjs and add meaningful checks that new local imports/served assets
cannot silently fall outside the reviewed manifest and that changed dependencies
invalidate admission. Preserve existing authorization/projection/policy/one-attempt
rules; do not edit/authorize the private trial packet or start any provider. The
coordinator will refresh that concrete packet only after final source verification.
This takes priority over optional presentation polish or native installation.

## Final browser regression command

Inspection of pass30's actual commands confirms its broad Chrome run used default
Node file concurrency, while the isolated playback case passed. Earlier Mac
qualification already found concurrent Chrome startup unreliable. For pass32's
final browser-enabled suite, use the supported Node with --test-concurrency=1,
NETCLAW_BROWSER_EXECUTABLE and the owned NETCLAW_TEST_TMP path. Retain the59/1
parallel run and isolated success; do not claim concurrency caused the timeout
without further evidence. No need to repeat the concurrent run or hide its limit.
The final source closure has26 files, including three synthetic fixture images;
pass30's tests cover omission/change/refusal with no paid packet modification.


## Coordinator final closure of the 32-pass batch

All 32 passes finished; the runner exited with no child. Tasks remain 14/30,
with all 16 open exits in readiness.md. Final recorded checks: 60/60 serial
Node/actual Chrome, 139/139 Python and 4/4 installed-native synthetic collector
scenarios. This does not qualify actual SSH, a Google-generated world, installed
MCP/skill, fresh NetClaw or human acceptance.

The coordinator refreshed the unauthorized trial packet to the final 26-file
closure at 21:48:55Z. Scene and policy hashes are unchanged, allowance remains
pending, and expiry is 2026-11-22T22:48:55.696Z. No provider request was made by
this refresh. live-review.md, readiness.md, resume.md and HANDOFF.md reflect it.
The final TCP check at 21:49:42Z returned No route to host for CML and all four
devices. No configuration or successful recollection occurred. Restore routing,
obtain fresh baselines and exact management identities, then use the supported
change-control path, exclude management ports before global enablement, verify
and recollect. Do not infer authentication failure or device power state.

The local synthetic preview on port 58778 returned HTTP 200 for all three pages
and remains running for the owner. It is frozen at pass21 and contains no real
R1/R2/SW1/SW2 measurements or Google output. Source HEAD remains ba2b86b7;
local and remote-tracking Spec198 refs remain 856bbc88; Spec199 is untouched.
No source commit, push, merge, release, extra pass or spending was authorized.

Final GAIT receipt: 5f693665. Full 82-entry trail is private at
.spec200-local/ralph/coordinator-gait-final.json. Reused the actual existing audit
branch spec200-implementation-20261122, consistent with prior coordinator receipts.
An initial guard expected a different branch from a handoff summary and stopped
before recording; no branch was created or changed. Future sessions should verify
the existing audit root/branch instead of trusting the incorrect summary name.
Next independent source unit is T020 host/network/account-alias recovery coverage;
this batch handoff does not close T030 or authorize an automatic pass33.
