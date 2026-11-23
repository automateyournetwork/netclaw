# World-suite pass15 — world2 / bounded native CLI drain

Assignment: SPEC200_WORLD_PASS=15, SPEC200_WORLD_NUMBER=2; source_refinement.
Spec Kit prerequisites passed; checklists15/15requirements and43/43quality pass.
Current context/authority/control/handoff read; optional Git hooks skipped.

Reproduced the next handoff defect in an actual worker CLI subprocess: immediate
process.exit after local completion killed the pending create callback. The
synthetic transport trace contained create only; no late ID/connect/cancellation
was retained. Original failure is preserved in before.log.

worker.mjs now tracks original open and best-effort cleanup promises. The CLI
waits up to five seconds after local completion, records worker_shutdown_drain
(drained or deadline), then closes its ledger and exits. Late original IDs are
persisted and original transport receives one cancellation with no setup/media.
A pending create or cancellation cannot hold local shutdown indefinitely. Neither
drain outcome is a provider terminal receipt or settlement; full unknown exposure
and the permanent create claim remain held. No retry, reconnect or new operation.

Verification:100/100 affected supported-Node tests pass, zero failures/skips.
Suites:live,provider,core,campaign-budget,worker,recovery,manager. New test uses the
real worker CLI/OS process and a test-only import hook replacing the Google SDK;
fetch is forbidden, credentials and review artifacts independently synthetic.
Three scenarios: late create, late connect with permanently pending cancel, and
never-resolving create. They assert zero setup/media, one create and at most one
original connect/cancel, exact original-ID persistence when returned, unknown
state/full reservation after exit, drain outcome, bounded shutdown and no replay.
Private evidence: .spec200-local/tests/world-pass-15/before.log and tests.log.
No production injection switch or new runtime module; source closure remains
29 files. Changed bytes invalidate historical paid packets. git diff --check passes.

Next concrete defect: manager.close uses a6.5-second grace then SIGKILL. The
worker can spend5seconds awaiting a terminal receipt and another5seconds draining;
manager shutdown may therefore preempt the newly qualified drain. Qualify the
combined real manager/worker process path with synthetic delayed responses and a
bounded owned-child reap, preserving unknown/full exposure and lock/ledger order.
Actual service/input/text bounds and trusted original-ID terminal/billing
reconciliation remain open; typed artifact assertions alone do not prove them.

No Google world, frame, fantasy visual review, actual provider termination,
installed Risk member or human T029 acceptance. No checkbox closes;15/30 remains.
No provider/device/CML/SSH calls, owner dotenv read, private export, sealed bundle,
control/allowance/acceptance/PROGRESS or runtime edits, agents/loops, Git branch
changes/commits, publication or tickets. Preserve198at856bbc88and199AWS.
Daily memory, tasks/readiness/data-model and HANDOFF updated. Native GAIT reuses
current root/audit branch; final record and gait_log retained privately.
