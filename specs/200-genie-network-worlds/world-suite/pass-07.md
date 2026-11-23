# Pass07 — world1 campaign session accounting

Implemented one offline unit from pass06: new campaign session markers retain an
explicit `campaign-v1` accounting version and `CAMPAIGN_SESSION_POLICY`, with a
120s target, 130s deadline from send (10s initial-frame window plus target), and
existing 5s terminal wait. This is a local lifecycle policy, never proof of a
provider-enforced billing cap or 120s of delivered media.

`reserved_microusd` is authoritative integer accounting copied from the reviewed
campaign reservation. `reserved_usd` and conservative `estimated_usd` reflect its
complete video-plus-input/text bound; `estimated_video_usd` separately shows12.096.
Invalid reservation bounds fail before the local send marker. No schema rewrite
or implicit migration: original-ID retrieval returns historical session fields
unchanged, including earlier campaign seam records with20s-era estimates.

Verification:58/58 tests, zero skipped, using supported Node across campaign
budget, core ledger, live source/review seams, manager and worker. Five new tests
cover full-duration records, original-record recovery after reopen, unchanged
ordinary admission, exact non-round input/text bounds and malformed reservations.
The initial new policy assertion failed before implementation as expected; its
log is retained. `git diff --check` passes. Private logs, hashes and native GAIT:
`.spec200-local/tests/world-pass-07/`.

No runtime module was added;29-file live closure remains. Changed source hashes
invalidate old packets. Live manager/worker still use legacy defaults and are NOT
wired to campaign admission. Their policy choice must next come from a validated
campaign record; do not silently reinterpret historical records as120s sessions.
No generated visual evidence was produced or reviewed; no checkbox/live/member/
human acceptance closes. Checklists remain15/15 requirements and43/43 quality.
No provider/device call, dotenv read, snapshot/control/allowance/acceptance/
PROGRESS edit, runtime change, agent/loop, git branch change or source commit.
