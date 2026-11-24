# Pass44 — world5: evidence-backed protocol ribbons

Bounded partial T018/T028 source refinement on2026-11-23. The local design
builder previously selected OSPF/iBGP ribbons from record kind alone. It now
requires a source digest and a confirmed parsed relationship. Explicit negative
record/source outcomes override retained parsed data. OSPF requires FULL in the
interface-neighbor table; iBGP requires an established state or numeric received
prefix count (including zero) and matching valid local/remote ASNs in the
neighbor address family. Empty, missing-source, failed, raw-only, unavailable,
non-established and external-BGP records cannot supply those cues.

Each qualifying relation adds a local provenance anchor to its logical_relations
record and source. Peer addresses/ASNs stay outside outbound text. Unknown data
and coverage remain available in the unchanged fact inspector. This supports the
sealed parser shapes; unsupported alternate shapes remain without ribbon cues.
No new module or dependency; existing29-file source review covers changed
world-designs.mjs bytes. Old paid packets remain stale; no packet was prepared.

Validation: both new regression tests failed before the fix. Final design suite
8/8 (including actual Chrome linked/unlinked synthetic inspector) and affected
source-review5/5 pass, zero failures/skips. New fixtures test six negative outcome
classes, empty/source failures, INIT/Active, zero-prefix established BGP and
external/missing/invalid ASNs across all five styles. Chrome covers existing local
inspection, not generated protocol pixels or real snapshot registry integration.

A targeted private read verified the pinned manifest and world-facts member hash;
all five real drafts retain OSPF/iBGP wording and four sourced logical claims,
without mutating facts. This was not a repeated full1,011-file qualification.
Only counts/status/hashes were emitted. Private evidence:
.spec200-local/tests/world-pass-44/{red.log,tests.log,source-review.log,
real-protocol-check.json,source-hashes.json,next-defect.json,gait-log.json}.

Next concrete defect: an independently synthetic unavailable trunk_membership
record with plausible VLAN data still produces VLAN10/20 guidance in5/5 styles.
The VLAN projection also checks kind/data without evidence outcome eligibility.
Inspect the real trunk source semantics before changing it; preserve observed
membership, native-VLAN exclusions, bounded ranges and uncertainty. No real-cohort
failure is inferred from this synthetic probe.

Requirements15/15 and quality43/43 passed; optional Git hooks skipped. No checkbox
closure:15/30 tasks; T029 remains human-only. No Google/provider/device/CML/SSH
calls, dotenv reads, private export, owner runtime changes, authority/control/
allowance/acceptance/PROGRESS changes, agents/loops, branch changes, Git commits
or publication. Native GAIT reused the current root/branch, with final log private.
Worlds3–5 hosted execution remains gated on actual1/2 success.198at856bbc88 and
199AWS preserved. live_world_passed=false.
