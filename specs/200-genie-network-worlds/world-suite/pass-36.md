# Pass36 — world4 member-browser setup cleanup

Assignment: SPEC200_WORLD_PASS=36, SPEC200_WORLD_NUMBER=4; source_refinement.
One bounded partial T028 unit. Spec Kit prerequisites pass; requirements15/15
and quality43/43. Optional Git hooks skipped; existing GAIT root/branch reused.
No checkbox closes;15/30. This is offline test reliability, not world acceptance.

## Concrete repair

The actual member-browser test registered teardown only after manager creation,
Chrome launch and newPage. Two isolated synthetic fault children running that
actual test reproduced4s timeouts on launch and newPage failure. No Chrome or
provider was launched by those faults; the real local manager kept the child alive.

Migrated the test to createBrowserFixture, which registers teardown before resource
acquisition and preserves manager/root cleanup even if browser.close rejects.
The shared fixture now accepts explicit snapshotRegistryPath (default null), so
real frozen local inspection is preserved. No generic manager options, new runtime
module, production behavior, source-review membership or paid authority changed.

## Evidence

Private results: .spec200-local/tests/world-pass-36/.

- red.log and red/member-cleanup-{launch,page}.log retain both expected timeout
  reproductions and original injected errors.
- cleanup-green.log:13/13 pass, zero skips; launch/page faults now exit normally
  with failing status1, original errors, empty owned state and browser-close witness.
  Existing browser/server/connect/close and recording setup fault checks pass.
- native.log:9/10 actual Chrome tests passed, including actual stdio MCP and sealed
  snapshot inspection. The keyboard check failed with ENOENT because this pass
  had not created its requested evidence directory before the run. This is a
  retained test-invocation mistake, not a viewer defect. Created the private
  directory; keyboard-rerun.log:1/1 pass. All10 distinct native cases passed across
  these runs, zero skips; do not describe the initial suite as10/10 green.
- native/member-mcp-evidence.json: actual_mcp=true, actual_browser=true,
  actual_agent=false, google_calls=0, external_browser_requests=0; four artifacts,
  event checkpoint correlated, recording final_flush_acknowledged. Reviewed start
  request ID equals operation ID, five local designs and original snapshot
  inspection assertions remain intact. Real data stays local.
- native/fixture-viewer.png visually inspected: explicit offline/no-Google banner,
  separate fictional facts, ended lifecycle, saved captures and accessible evidence.
  This is synthetic transport media, not Google visual-quality evidence. Private
  member snapshot screenshot retained without printing network facts.
- source-hashes.json, result.json and native GAIT start/finish/full log retained.
  git diff --check passes. Test-only changes do not refresh stale paid packets.

## Limits and next unit

Google generation/navigation/event/drift, actual provider terminal/billing,
reviewed private export and installed Risk-member acceptance remain open. No
provider/device calls, dotenv reads, sealed bundle/control/allowance/acceptance/
PROGRESS edits, runtime changes, agents/loops, branches, commits or publication.
No external tickets.198at856bbc88 and199AWS preserved; no model T029 verdict.

Next pass37/world4: member-browser currently checks terminal/event-sent but does
not assert its retained event checkpoint correlation or final recording receipt.
Strengthen that composed MCP evidence boundary with a bounded checkpoint/final-
flush failure case, proving incomplete evidence cannot silently pass the member
handoff. Preserve original IDs, local snapshot registration and no replay. This
is a concrete coverage gap; no production evidence-loss defect is established.
Event JPEG/DB crash gap remains unconfirmed. Precreate private evidence output
directories before browser runs to avoid repeating this pass's invocation mistake.
