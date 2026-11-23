# World-suite pass17 — world2 / admission during shutdown

Assignment: SPEC200_WORLD_PASS=17, SPEC200_WORLD_NUMBER=2; source_refinement.
Spec Kit prerequisites and checklists pass: 15/15 requirements, 43/43 quality.
Current authority, control, handoff and context read; optional Git hooks skipped.

Three synthetic HTTP/process regressions failed before the change: repeated close
returned early, a disconnected admission released the ledger/lock before its audit
finished, and new admission continued into validation/audit during worker drain.
The before.log preserves these failures. No provider transport was used.

manager.mjs now refuses new session admission with HTTP503 manager_closing before
native admission audit/reservation and rechecks immediately after audit resolves.
Pending admission audits join the existing pending-audit set, so a disconnected
request cannot release ledger ownership prematurely. All close callers receive
the same shutdown promise. Original-ID retrieval stays observational during the
worker drain; already admitted workers retain the composed11.5s cleanup grace.
No new runtime module; source review closure remains29 files. Changed source bytes
invalidate earlier paid packets; only the coordinator prepares replacements.

New tests cover connected/disconnected deferred audit, lock retention until audit
settlement, zero sessions/workers after refused admission, HTTP503 and original-ID
retrieval while an actual SIGSTOP/SIGCONT fixture worker drains. The focused result
is3/3 passing. This qualifies local synthetic behavior, not Google termination,
actual campaign charges, generated visuals or installed Risk-member acceptance.

Evidence: .spec200-local/tests/world-pass-17/{before,focused,tests}.log,
hashes.json and native GAIT records/log. Final affected-suite result follows below.
No task checkbox closes;15/30 unchanged. T020/T030 remain partial.

Next concrete source concern: manager awaits server.close without an HTTP body
drain deadline. A client paused inside body(req) can keep shutdown waiting beyond
the worker grace; qualify a partial-body connection and bound owned HTTP cleanup
without releasing ledger/audit ownership early. This is a source inspection
finding, not an observed infinite hang. Avoid unrelated lifecycle expansion.
Camera/landmark/event refinement still needs actual coordinator-supplied Google
captures; none was available for this pass.

No provider/device/CML/SSH calls, owner dotenv reads, private export, sealed bundle,
control/allowance/acceptance/PROGRESS or owner runtime edits, agents/loops, branch
changes, Git commits, publication or tickets. Preserve198at856bbc88and199AWS.
Native GAIT reuses the existing root/audit branch and retains gait_log privately.

Final verification:104/104 affected supported-Node tests pass, zero failures or skips (live,provider,core,campaign-budget,worker,recovery,manager). git diff --check passes. No live-world or human acceptance claim.
