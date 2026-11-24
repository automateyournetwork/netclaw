# Pass10 — world1 explicit local campaign review

Bounded source unit: added full120s local review support as a prerequisite to
manager migration. Ledger.review records campaign-v1, the exact campaign session
policy hash and integer-microdollar allowance. New campaign admission rejects
historical20s/$15 reviews before reservation; ordinary admission cannot downgrade
a campaign review. Exact reservation/allowance mismatch or a missing reservation
result refuses the marker. A reservation already committed remains held. Original
IDs retain historical review/session bytes without reinterpretation. No new runtime
module; the29-file source closure remains complete and every old paid packet is
source-stale.

Verification:83/83 affected supported-Node tests, zero skipped, across campaign
budget, live review/source closure, provider, worker, core, manager and recovery.
New tests cover historical-review refusal with no reservation, downgrade refusal,
exact microdollars, invalid policy/amount/provider, mismatch with orphan hold and
null reservation refusal. Historical original-ID review bytes remain unchanged.
The initial run failed one synthetic worker fixture still using a historical
review; corrected to the explicit campaign contract, retaining the original log.
Checklists15/15 and43/43 pass; git diff --check passes. Private logs/hashes/native
GAIT: .spec200-local/tests/world-pass-10/. All evidence is source/synthetic.

Partial T013/T020 only; no checkbox closure, generated world, actual visual review,
installed member or human T029 acceptance. No provider/device calls, owner dotenv
reads, sealed snapshot/control/allowance/acceptance/PROGRESS edits, runtime changes,
agents, branches, git commits, publication or tickets.

The full manager migration was deliberately bounded to its local-review
prerequisite. NEXT: migrate live packet to explicit campaign policy/bound; manager
review must use that bound and CAMPAIGN_SESSION_POLICY. Freeze all four operator
authority/review pins at manager launch, selectively forward them to workers, and
call admitReviewedCampaign after awaited audit with fresh source/evidence checks.
Preserve historical original-ID recovery and reservation-before-marker/orphan
holds. Current manager still fails closed for Google sends. Then coordinator must
qualify actual service/input-text caps and trusted original-ID terminal/billing
reconciliation before preparing a new exact paid packet.
