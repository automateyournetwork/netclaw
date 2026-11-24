# Pass39 — world4 abrupt event-evidence process loss

Assignment: SPEC200_WORLD_PASS=39, SPEC200_WORLD_NUMBER=4; source_refinement.
Spec Kit prerequisites pass; requirements15/15 and quality43/43. Optional Git
hooks skipped. Existing native GAIT root/audit branch reused. Partial T020/T028;
no task checkbox closes and15/30 remains.

Added tests/genie-worlds/manager-crash.test.mjs, a test-only native process drill.
An isolated real manager and fixture worker save/fsync an event JPEG through the
actual checkpoint HTTP handler. Immediately before recordEventCheckpoint enters
its transaction, the harness suspends its worker and SIGKILLs its manager. The
parent kills the owned detached process group and observes worker/manager absence.
Reopen first refuses the stale manager lock. Only after checking the owned dead
PID does the harness remove its own fixture lock and reopen the same root.

Actual SDK2 stdio MCP evidence retains the original operation, sent event, nonempty
JPEG, unknown lifecycle, reserved usage, no terminal receipt and unconfirmed event
receipt. Repeating original start returns the same operation with zero workers;
a fresh operation receives409 active_or_unsettled. A second MCP evidence read is
identical: no event replay, fabricated receipt or acceptance. All evidence is
synthetic, fixture reservation is zero dollars, and Google calls are zero.

Private results: .spec200-local/tests/world-pass-39/.
- final-corrected.log:14/14 native crash/MCP and worker recovery tests, zero skips.
- manager-crash-evidence.json: retained original evidence and process/cleanup facts.
- crash.log: initial harness omitted required MCP projection_ref; corrected to
  create/bind an independently synthetic draft before initial start.
- final.log: second harness expected400 instead of the existing409 hold response;
  assertion corrected. Neither retained failure demonstrates a product defect.
- Native GAIT start/finish/log and result retained privately. git diff --check passes.

No runtime module or source-closure membership changed. Existing paid packets
remain stale. Sealed snapshot and private control were not mutated; control hash
matches its entry value. This unit does not repeat snapshot/style inspection or
browser visual qualification. It proves process loss with a deliberately suspended
then killed worker, not host power-loss durability, manager-only loss with a living
worker, actual Google behavior, or generated-world visual quality.

Next concrete unit: kill only the manager after this persistence boundary, allow
the original fixture worker to observe IPC/heartbeat loss, and verify its original
terminal/usage evidence survives same-root MCP recovery without replacement create.
Keep the no-terminal process-loss case distinct; never infer live provider success
from the fixture terminal. Own/clean up children and review only fixture stale locks.

No provider/device calls, dotenv reads, private export, control/allowance/acceptance/
PROGRESS changes, owner runtime changes, agents/loops, branches, Git commit or
publication. No installed Risk-member or human T029 acceptance.198at856bbc88 and
199AWS preserved. Hosted worlds3–5 remain coordinator-gated on actual success1/2.
