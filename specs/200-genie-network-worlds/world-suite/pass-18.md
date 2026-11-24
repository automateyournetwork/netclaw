# World-suite pass18 — world2 / bounded HTTP shutdown

Assignment: SPEC200_WORLD_PASS=18, SPEC200_WORLD_NUMBER=2; source_refinement.
Spec Kit prerequisites and checklists pass:15/15 requirements,43/43 quality.
Current authority/control/context read; optional Git hooks skipped.

Reproduced unfinished POST bodies holding manager.close beyond1.8s with no
workers: both new-session and recording endpoints failed the regression before
the fix. Tests explicitly destroyed their own clients afterward; no infinite-hang
claim. The first harness run omitted the required policy argument to Ledger.review;
that harness error is preserved separately and is not a product finding.

manager.mjs now grants HTTP peers one second after the existing11.5s maximum
worker drain, then destroys only owned sockets. It tracks sockets including
partial headers and WebSocket upgrades, and awaits request-handler completion
before closing SQLite/unlocking. Aborted recordings persist their failure before
ledger closure; completed uploads survive. Pending native audits still retain
ledger/lock ownership even after socket destruction. This is a transport cleanup
bound, not a total shutdown deadline for an external audit that never resolves.
Original-ID observation/stop/evidence remain available during worker drain.
No provider termination, usage reconciliation or held-budget release is inferred.

Five new synthetic local HTTP/socket cases cover unfinished session/recording
bodies, an upload completing during shutdown, incomplete headers and a WebSocket
peer that never acknowledges close. The focused suite, including the two existing
deferred-audit tests, passes7/7. All fixtures remain synthetic; no live visuals.
Private evidence: .spec200-local/tests/world-pass-18/{harness-error,before,focused,
focused-final,tests}.log, hashes.json and native GAIT records/log.

No task checkbox closes;15/30 unchanged. T020/T030 remain partial. The source
closure stays29 files; changed manager bytes invalidate prior paid packets.
Only coordinator prepares/reviews replacements. No Google captures were supplied;
fantasy recognizability/camera/landmark/event review remains unperformed.

Next: qualify browser final recording upload against the new one-second HTTP
grace during manager stop; current proof is Node HTTP only, not MediaRecorder
flush timing. Preserve any late-upload loss as evidence failure. Avoid unrelated
lifecycle expansion; coordinator still owns live packet and Google visual proof.

No provider/device/CML/SSH calls, dotenv reads, private export, sealed bundle,
control/allowance/acceptance/PROGRESS or owner runtime edits, agents/loops, branch
changes, Git commits, publication or tickets. Preserve198at856bbc88and199AWS.
Native GAIT reuses the existing root/audit branch and retains gait_log privately.

Final verification:107/107 affected supported-Node tests pass, zero failures/skips. Final focused7/7 also passes, including the two additional header/upgrade cases added after the broad run (109 distinct tests total). git diff --check passes. No live-world or human acceptance claim.
