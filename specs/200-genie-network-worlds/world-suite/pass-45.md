# Pass45 — world5: evidence-backed VLAN membership

Bounded partial T018/T028 source refinement, 2026-11-23. The design builder now
shares sourced-observation eligibility between VLAN and protocol cues. A valid
source SHA256 is required. Any explicit outcome/status other than observed on
either record or source suppresses the cue, including null. Historical sealed
records without those fields remain eligible with their source and supported
parsed membership. Native-VLAN exclusions, bounded enumerations, local provenance
anchors and coverage are preserved. Unsupported records remain in local facts.
No new module/dependency; existing29-file source closure covers the changed
world-designs.mjs bytes. Old paid packets remain stale even though real outbound
hashes are unchanged.

Validation: new rejection regression failed before the fix. Final designs suite
10/10 including actual Chrome local linked/unlinked inspector; source-review5/5,
zero failures/skips. Fixtures cover missing/invalid hashes, six negative outcomes
plus null at both record/source outcome/status fields, legacy/explicit observed
success, native-only/invalid/range/over-bound declarations and retained anchors
across all five styles. Synthetic fixtures are never relabeled real.
Initial non-browser run9/9 with one skipped browser test is retained separately;
final browser-enabled run closes that test gap. An initial inspection used the
wrong manifest filename and failed read-only; corrected to SHA256SUMS.json.

Targeted pinned-manifest/world-facts member hashes pass; all five real drafts
retain two VLAN anchors each and identical outbound hashes to pass44. Facts are
unchanged. This is not repeated full1,011-file qualification. Only counts/status/
hashes were emitted. Private evidence in .spec200-local/tests/world-pass-45/:
red.log, tests.log, tests-browser.log, source-review.log, real-vlan-check.json,
source-hashes.json, next-defect.json and native GAIT records/final gait-log.json.

Next reproduced defect: a synthetic trunk interface mapped to null throws
TypeError and aborts all designs. Guard unsupported parser containers/port entries
and preserve supported siblings and unknown local facts. Do not infer a failure
in the real cohort or modify the sealed snapshot.

Requirements15/15 and quality43/43 pass. No checkbox closure;15/30. No generated
world or generated-pixel visual review exists; Chrome checks local UI only.
Google/private-export/Risk-member acceptance stays open; hosted worlds3–5 await
actual1/2 success. T029 is human-only. No provider/device/CML/SSH calls, dotenv
reads, private export, authority/control/allowance/acceptance/PROGRESS edits,
owner runtime/branch/Git changes, agents/loops or publication. Current native
GAIT root/branch reused; final log private.198at856bbc88 and199AWS preserved.
live_world_passed=false.
