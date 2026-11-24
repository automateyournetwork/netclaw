# Pass37 — world4 composed member evidence

Assignment: SPEC200_WORLD_PASS=37, SPEC200_WORLD_NUMBER=4; source_refinement.
One bounded partial T028 verification unit. Spec Kit prerequisites pass;
requirements15/15 and quality43/43. Optional Git hooks skipped. Existing native
GAIT root/audit branch reused. No task checkbox closes;15/30 remains.

## Concrete work

Expanded actual Chrome/stdio MCP original-ID handoff into three scenarios:
complete evidence, synthetic event-checkpoint persistence refusal, and synthetic
final-flush refusal. Each inspects the same sealed local snapshot and packet-scale
world draft without exporting it; session media remains independently synthetic.

The composed MCP evidence must retain the original reviewed operation, one event
send, one attempt per checkpoint and one finalization. Successful event receipts
match the sent event ID, operation, worker frame hash, artifact hash and size;
visible effect stays unassessed. Successful recording receipts match nonempty
WebM hash and size. Event refusal yields no event receipt/artifact; finalization
refusal preserves nonempty media but no final receipt and explicit unconfirmed
state. Terminal confirmation cannot substitute for either receipt. All cases
retain acceptance=null and live_world_proven=false.

## Evidence and retained mistakes

Private evidence: .spec200-local/tests/world-pass-37/.
Initial member.log used the GAIT interpreter for the MCP test and failed because
that environment lacks mcp.server.mcpserver. It is suitable for GAIT, not this
SDK2 integration. Switched to the already-qualified installed MCP interpreter;
no installation change. member-qualified.log passed2/3, then cancelled the final
case: its wait for transient terminal UI text raced the final-confirmation warning.
Removed that assumption, kept terminal validation in returned MCP evidence and
bounded browser waits to5seconds. These were harness mistakes, not product defects.

member-final.log:3/3 pass, zero skips, using actual Chrome and SDK2 stdio MCP.
cleanup.log:13/13 pass, zero skips, including launch/newPage failure cleanup. Native scenario JSON/screenshots remain
private and are never Google visual-quality evidence. No runtime source or new
module changed; live source review closure unchanged. Existing paid packets still
require fresh coordinator review.

## Limits and next unit

No Google call, device query, dotenv read, private export, owner-runtime change,
control/allowance/acceptance/PROGRESS change, agents/loops, branch/Git mutation,
publication or external ticket. Preserve198at856bbc88 and199AWS. No T029 verdict.
Actual Google navigation/event/drift, terminal/billing and installed Risk-member
acceptance remain open.

Next bounded unit: inject failure between event JPEG persistence and the receipt
SQLite commit, then restart the same manager and read evidence through MCP.
Verify file-only capture remains unconfirmed with no fabricated receipt or replay.
This existing crash-window coverage gap is not yet a demonstrated product defect.
