# World-suite pass14 — world2 / late provider-open cleanup

Assignment: SPEC200_WORLD_PASS=14, SPEC200_WORLD_NUMBER=2; source_refinement.
Spec Kit prerequisites passed; checklists remain15/15requirements and43/43quality.
Current authority, context and handoff read; optional Git hooks skipped.

Concrete defect reproduced: delayed create completed after worker cleanup closed
SQLite, then adapter providerId/catch failed with database is not open. The exact
original response could not be recorded and late transport cancellation was lost.
Ledger now supports an in-flight reference held by the adapter through create and
connect, released in finally. Local close defers actual connection closure until
that reference releases. No reopen/new state root, retry or new provider ID.
Existing worker late-result cancellation runs without sending setup or reading
media. Cancellation return is not terminal or billing evidence.

Verification uses deferred synthetic create/connect promises and the actual worker
with its full five-second terminal wait. After worker completion and ledger close,
late responses persist the original provider ID; exactly one original create,
connect and cancellation occur, no setup/media receive, state remains unknown,
and full campaign exposure stays held. A permanently pending cancellation does
not block local completion. Late create/connect rejection preserves the original
error and releases the connection; tests assert the database really closes.
Evidence: .spec200-local/tests/world-pass-14/before.log (reproduced failure),
tests.log (98/98 interim), tests-final.log (99/99 final, zero failed/skipped).
Supported Node ran live/provider/core/campaign-budget/worker/recovery/manager
suites. git diff --check passed.
No new runtime module; reviewed closure remains29files. Source changes invalidate
old exact paid packets; coordinator alone prepares/reviews replacements.

Limits: in-process synthetic callback qualification, not actual process-death or
Google termination. CLI still calls process.exit after worker.run, so real delayed
callbacks may be killed before this lease can finish. Next bounded unit: qualify
and bound CLI shutdown/drain for pending original create/connect under injected
subprocess transport, preserving unknown on forced exit and avoiding setup/retry.
Then qualify service/input/text bounds and trusted terminal/billing reconciliation.
No Google frames or world2 fantasy visual review. No task checkbox closes;
15/30 remains, and no installed-member or human T029 acceptance is supplied.
No provider/device/CML/SSH calls, dotenv read, private export, control/allowance/
acceptance/PROGRESS/snapshot/runtime changes, agents, loops, branches, Git commits,
publication or tickets. Preserve198at856bbc88and199AWS.

Daily memory, task/readiness/data-model state and HANDOFF updated. Native GAIT
reuses current root/audit branch; final record and gait_log retained privately.
