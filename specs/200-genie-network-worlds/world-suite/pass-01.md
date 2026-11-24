# Pass01 — world1 durable campaign budget accounting

2026-11-23. Assignment: SPEC200_WORLD_PASS=01, SPEC200_WORLD_NUMBER=1.
One offline source unit for T013/T020; no checkbox closes. Requirements15/15
and quality43/43 passed; Spec Kit prerequisites identified the existing feature.
Optional git hooks skipped by owner instruction; branch and existing work retained.

Implemented `scripts/genie-worlds/campaign-budget.mjs`: private SQLite accounting,
120-second video bound plus explicit positive input/text allowance, integer USD
microdollars, aggregate settled + unresolved + proposed exposure, soft25/hard50,
original-ID idempotency/conflicts, durable unknown hold, immutable settlement
with terminal/billing references, and honest overrun retention. Missing authorities
fail closed; explicit bootstrap refuses reset. Canonical-root/campaign/policy
binding rejects copied databases and changed identities. No provider calls exist
in this component. Added it to the exact source-review closure (29 files).

Tests: six accounting tests, eight live/source-review tests and seven core tests:
**21/21 passed, zero skipped** on supported Node. Tests cover restart, separate
SQLite connections, changed world/ID, exact soft boundary and one-microdollar
overflow, invalid/fractional/unsafe amounts, missing terminal/billing evidence,
hard overrun, reset/copy refusal and changed accounting source invalidation.
Initial20/20 run also passed; one additional source-mutation test produced21/21.
All test billing/receipt references are synthetic; no real billing is asserted.

Private evidence: `.spec200-local/tests/world-pass-01/` contains test logs,
source/result hashes, native GAIT start/final and retained gait_log. Native GAIT
uses the existing root/audit branch, not a new branch. No private snapshot read
or reseal was needed for this accounting unit. Control/allowance/acceptance and
PROGRESS.md were not edited; no owner runtime, installation, device or cloud
operation, owner dotenv access, paid call, publication or source commit occurred.

Limits: this component is NOT connected to paid admission. Trusted bootstrap and
evidence hashes do not grant authority or prove a provider-enforced bound. The
coordinator/backend must pin one shared authority across session roots and account
aliases, validate referenced review/terminal/billing evidence and coordinate
reservation-before-send with the session ledger. Existing runtime20s/one-attempt
policy is deliberately unchanged. No full120s lifecycle, generated visual review,
actual member-in-Risk acceptance or T029 human acceptance is claimed.

Next defect: runtime admission still uses per-root US$15 single-attempt accounting,
so it cannot yet enforce the new campaign policy. Integrate the pinned authority,
fail closed on missing/stale budget binding and test crash/retry/cross-root cases;
then replace historical timing with deterministic full120s lifecycle tests.
