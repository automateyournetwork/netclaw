# Pass38 — world4 event receipt transaction failure

Assignment: SPEC200_WORLD_PASS=38, SPEC200_WORLD_NUMBER=4; source_refinement.
Bounded partial T020/T028 verification. Spec Kit prerequisites and checklists
pass (requirements15/15, quality43/43); optional Git hooks skipped. Existing
native GAIT root/audit branch reused. No task checkbox closes;15/30 remains.

## Concrete work and evidence

Extended the actual Chrome/SDK2 stdio MCP test with a TEMP SQLite trigger that
aborts the event receipt INSERT after the real manager writes/fsyncs its JPEG.
The failed transaction leaves a nonempty event artifact but no receipt. The
browser reports unconfirmed; one event and one attempt per checkpoint remain.
After normal fixture stop/final flush, close and reopen the same manager root,
then inspect through actual MCP: the unchanged four-artifact manifest and original
session survive; event evidence stays unconfirmed with receipt=null. Repeating
the original reviewed start lookup returns the original operation and spawns no
worker. Acceptance remains null and live_world_proven=false.

Each scenario inspects the sealed real snapshot and packet-scale draft locally;
provider media is independently synthetic. No private projection export occurs.
Private evidence: .spec200-local/tests/world-pass-38/.

- member.log:4/4 actual Chrome/stdio MCP scenarios pass, zero skips.
- browser/member-mcp-event-receipt-restarted.json retains original-ID recovery,
  real SQLite failure, unchanged artifact evidence and zero replacement workers.
- cleanup.log: initial11/13; adding a fourth scenario exceeded the cleanup
  harness's fixed four-second child deadline because it selected the whole suite.
  Cleanup now explicitly selects one setup scenario, preserving the same timeout
  and original failure assertions rather than accumulating shutdown grace periods.
- cleanup-final.log:13/13 pass, zero skips; child fault logs retained privately.
- Native screenshots/JSON and GAIT start/finish/log retained privately. These are
  fixture/interface evidence, never a Google world visual-quality review.

Test-only changes; no runtime module or live source closure change. Existing paid
packets remain stale. This verifies a transaction abort and orderly manager reopen,
not SIGKILL/power-loss durability or a provider crash. No production defect found.

## Limits and next unit

Next bounded source unit: isolated manager-process death exactly after event JPEG
persistence and before its receipt transaction, with owned-worker cleanup and
same-root MCP evidence recovery. Preserve unknown lifecycle/usage if no terminal
receipt arrives; prove no replacement create or event replay. This remains an
unqualified abrupt-process-loss boundary, not a claimed defect.

Actual Google navigation/event/drift/terminal/billing and installed Risk-member
acceptance remain open. No provider/device calls, dotenv reads, authority/control/
allowance/acceptance/PROGRESS changes, owner-runtime modifications, agents/loops,
branches/Git commits or publication. No T029 verdict.198at856bbc88 and199AWS
preserved. Source work does not qualify a generated world.
