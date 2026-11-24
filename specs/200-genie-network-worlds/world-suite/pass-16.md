# World-suite pass16 — world2 / composed manager shutdown

Assignment: SPEC200_WORLD_PASS=16, SPEC200_WORLD_NUMBER=2; source_refinement.
Spec Kit prerequisites and checklists pass:15/15requirements,43/43quality.
Current authority/context/control/handoff read; optional Git hooks skipped.

Reproduced manager.close killing the actual worker process at6.5s before a late
original create response. before.log retains the failed assertion: SIGKILL instead
of normal exit. A test-only SDK import hook prevents provider calls; all review,
credential, authority and transport fixtures are independently synthetic.

Shared constants in model.mjs now compose the worker's5s terminal wait and5s drain
with a1.5s scheduling margin. manager.close waits at most11.5s for owned workers
using a monotonic clock, then retains unknown and performs the existing owned-child
SIGKILL/reap before ledger close and lock removal. worker.mjs uses the same drain
constant. No runtime module added; reviewed source closure stays29files. Existing
paid packets are stale after these source changes.

New actual manager/worker process test covers late create, late connect with
permanently stuck cancellation, and a SIGSTOP-frozen create. It checks normal late
response exit versus forced frozen-child reap, original-ID persistence, zero
setup/media, one create/connect/cancel where applicable, unchanged12,500,000
synthetic microdollar exposure, unknown/no terminal receipt and denied replay.
Reopening a manager after close verifies released lock/ledger ownership; OS PID
checks verify the child was reaped. Existing frozen fixture test uses the revised
finite grace bound. These are local synthetic process results, never Google
termination, network-partition, host-death or generated-world acceptance.

Evidence: .spec200-local/tests/world-pass-16/before.log, tests.log, hashes.json
and native GAIT records/log. Final affected-suite result is recorded below.

Next defect: close does not gate new session admission or admissions awaiting
native audit; qualify those races and shared repeated-close completion. Actual
service/input/text caps and trusted terminal/billing reconciliation remain open.
No visual capture exists for this pass; fantasy camera/landmark review awaits
actual coordinator-owned provider evidence. No checkbox closes;15/30 unchanged.

No provider/device/CML/SSH calls, owner dotenv read, private export, sealed bundle,
control/allowance/acceptance/PROGRESS or owner runtime changes, agents/loops, Git
branch changes/commits, publication or tickets. Preserve198at856bbc88and199AWS.
HANDOFF/tasks/readiness/data-model/daily memory updated. Native GAIT reuses the
current root/audit branch and retains gait_log privately.

Final verification:101/101 affected supported-Node tests pass, zero failures or
skips (live,provider,core,campaign-budget,worker,recovery,manager). The combined
manager shutdown test covers all three native process scenarios. git diff --check
passes. No live_world_passed or human acceptance claim.
