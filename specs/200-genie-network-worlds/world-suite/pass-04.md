# World-suite pass04 — world1

Status: source progress; Google generated-world acceptance remains false.

## Concrete work

Partial T013 evidence handling in `scripts/genie-worlds/live-packet.mjs`:
private packet, authority and credential reads now use a bounded file descriptor,
O_NOFOLLOW/O_NONBLOCK, private ownership/mode and single-link checks. Before/after
file metadata and final path identity are checked; reads allocate at most1MiB+1.
`readReviewedArtifact` accepts a closed reference containing absolute path,
SHA256, device/inode and exact byte length. It returns only locally verified bytes
and rejects byte-identical inode replacement as well as content changes.
No module was added to the29-file live source closure; changed bytes invalidate
older source reviews. No real credential was read or live packet prepared.

## Evidence

Spec Kit prerequisites pass; requirements15/15 and quality43/43 remain complete.
Supported Node affected tests:40/40, zero failed/skipped, covering live packet,
campaign budget, core ledger and manager. Five new tests cover exact content,
byte-identical replacement, hardlink/symlink/permission rejection, malformed and
oversized/empty references, and actual loader rejection of hardlinked inputs.
`git diff --check` passed. Full test log, source hashes and native GAIT records
are retained under `.spec200-local/tests/world-pass-04/`.

## Limits and next defect

Artifact bytes/identity do not establish a provider-enforced duration, input/text
price bound, terminal outcome or billed charge. The new reviewed-artifact reader
is an available source seam, not yet called by campaign admission. Add typed
review/service/input-text schemas and cross-binding to exact source, projection,
trusted campaign and numeric budget, then wire manager admission to CampaignAdmission.
Keep conservative unknown reservations and original-ID recovery. Historical live
runtime remains20s/US$15/one attempt until120s lifecycle integration is qualified.
No task checkbox closes; no generated visual review or installed Risk-member
acceptance exists. No provider/device calls, sealed snapshot/control/allowance/
acceptance/PROGRESS edits, owner runtime changes, agents, branches or commits.
