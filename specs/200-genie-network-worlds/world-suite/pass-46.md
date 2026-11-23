# Pass46 — world5: resilient VLAN parser boundaries

Bounded partial T018/T028 source refinement, 2026-11-23. Unsupported VLAN
containers and null/scalar/array records or port payloads now omit unsupported
cues instead of aborting all five styles. Supported sibling observations retain
their original source pointers, native-VLAN exclusions and bounded declarations.
Local facts, including unknown payloads and coverage limits, remain unchanged.
No new module/dependency; world-designs.mjs is already in the29-file reviewed
closure. Source-byte changes invalidate old paid packets.

Both new regressions failed before the fix. Full offline live-packet/source/
lifecycle suite44/44 passes, zero skips; SDK calls use synthetic transports and
no Google endpoint. This broader run includes native worker shutdown fixtures. Final design suite12/12 passes,
zero skips, including actual Chrome linked/unlinked local inspector. Its linked
synthetic fixture now includes a null port and still displays all five drafts;
zero sessions/external requests. Tests cover unsupported containers at each VLAN
layer, valid siblings, original pointers and unchanged facts. Browser evidence
is local-UI qualification only, not generated-pixel visual review.

Targeted trusted-manifest/world-facts digest checks pass; all five real drafts
retain two VLAN anchors and identical outbound hashes to pass45. Facts unchanged;
no repeated full-bundle qualification or sealed writes. Private results:
.spec200-local/tests/world-pass-46/{red.log,tests-browser.log,
source-review.log,source-review-corrected.log,real-vlan-check.json,
source-hashes.json,next-defect.json,gait-log.json}.

Retained procedure errors: first source-review command referenced a nonexistent
test filename (no tests ran); corrected to live.test.mjs. A manifest-schema
inspection mistakenly printed member filenames instead of counts. No file
contents, credentials, private addresses or full topology were printed; subsequent
private inspection emitted only counts/status/hashes. Avoid listing private keys
when a manifest is a path-to-digest map. No attempt to erase the original output.

Next reproduced synthetic defect: a null OSPF interface value throws TypeError
in confirmedProtocol and aborts all designs. Guard nested OSPF/BGP records while
preserving valid siblings and requiring actual established-state evidence. No
real-cohort failure inferred. Do not alter the sealed snapshot to create a test.

Requirements15/15 and quality43/43; no checkbox closure,15/30. Actual Google
streaming/private export/Risk-member acceptance remain open; hosted3–5 require
coordinator-recorded1/2 success. No provider/device/CML/SSH calls, dotenv reads,
private export, control/allowance/acceptance/PROGRESS edits, owner runtime changes,
agents/loops, branch/Git changes or publication. Reuse current native GAIT root
and audit branch; final log private.198at856bbc88 and199AWS preserved.
live_world_passed=false.
