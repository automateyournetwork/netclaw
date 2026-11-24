# Pass35 — world4 repeated-arrow scroll suppression

Assignment: SPEC200_WORLD_PASS=35, SPEC200_WORLD_NUMBER=4; source_refinement.
One bounded keyboard regression/fix under T018/T028; no task checkbox closes,
15/30 remains. Spec Kit prerequisites passed; requirements15/15, quality43/43.
Optional Git hooks skipped. Current GAIT root/audit branch reused.

## Concrete evidence and change

Actual isolated Chrome reproduced the handoff defect: initial ArrowDown plus
8 native repeated keydowns moved scrollY from0 to320. Only the initial keydown
prevented its browser default; transport correctly sent one down/up pair.
The red assertion, native event witnesses, packets and screenshot are retained.

viewer.mjs now prevents default for every recognized movement keydown after
interaction eligibility, before duplicate/repeat filtering. It still sends just
one down/up pair. Native Tab focus navigation stays available. Existing physical
key identity, modifier-safe release, Escape, canvas/window blur and terminal
guards remain covered. No new runtime module; the existing29-file source closure
has changed viewer bytes, so earlier paid packets require fresh coordinator review.

## Verification

Private evidence: .spec200-local/tests/world-pass-35/.

- red/test.log and red/arrow-repeat.json: failing Chrome reproduction,8 repeats,
 1 prevented keydown,320-pixel scroll,2 key packets, zero provider calls.
- green/arrow-repeat.json: same8 repeats, all9 keydowns prevented,0-pixel scroll,
  exactly2 key packets. Regression also verifies unrelated Tab is not prevented.
- green/arrow-repeat.png: visually reviewed; explicit offline/no-Google banner,
  focused fixture canvas, separate fictional facts, visible stop/evidence controls,
  zero fixture cost and unknown usage. This is UI evidence, not Google imagery.
- Final suite results and native GAIT are retained beside these artifacts.

## Limits and next concrete unit

No Google generation/navigation/event/drift proof, real billing/termination,
private projection export or selected Risk/member acceptance is established.
No provider/device calls, dotenv reads, sealed/control/allowance/acceptance/PROGRESS
edits, owner runtime changes, agents/loops, branches, Git commits or publication.
Preserve198at856bbc88 and199AWS. No model supplies T029 acceptance.

Next pass36/world4: fix member-browser.test.mjs cleanup registration after
manager/browser/newPage acquisition. Reproduce launch/newPage failure without
provider/device calls, register cleanup before acquisition, and preserve the
snapshotRegistryPath option when using the shared fixture. Retain actual MCP
handoff verification; do not relabel it installed-member or live-world proof.
The event JPEG/DB crash gap remains unconfirmed and is not an established defect.

Final verification: actual Chrome9/9 and full live-packet/source-review suite44/44
passed, zero skips. The latter used synthetic credentials/transports only.
