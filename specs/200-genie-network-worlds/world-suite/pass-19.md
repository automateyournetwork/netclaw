# Pass19 — World2: actual browser final recording flush

One offline T020/T010 verification and repair unit. SPEC200_WORLD_PASS=19 and
SPEC200_WORLD_NUMBER=2; source_refinement authority, existing200branch. Spec Kit
prerequisites pass, requirements15/15 and quality43/43; optional Git hooks skipped.

Actual headless Chrome exposed a final-chunk loss: immediate flush passed, but a
250ms delay before the final recording fetch failed because server.close() had
already refused new connections. Real MediaRecorder/canvas capture was used over
the declared synthetic transport fixture; the test delayed fetch, not encoding.
Initial evidence: .spec200-local/tests/world-pass-19/before.log and
before-shutdown-recording-250.json.

Manager now keeps its listener open for the full one-second grace after worker
drain/stream closure. Admission remains blocked; existing stop/evidence handlers
retain ledger ownership. At expiry the listener closes and all owned sockets are
destroyed, then handlers/audits settle before ledger close/unlock. No added module,
new session, provider call or extended hosted deadline. Source closure remains29
files; changed manager bytes invalidate any previous paid packet.

Validation:21/21 manager/actual-Chrome tests plus5/5 source-binding checks pass,
zero skips. Immediate and250ms final uploads preserve every actual emitted byte.
A1250ms late upload fails visibly as Recording incomplete, preserves earlier
successful bytes and cannot extend the bounded transport shutdown. Existing
stalled bodies, partial headers, unacknowledged upgrade, audit ownership and
admission tests pass. Private logs: affected.log and source-closure.log; final
capture/status records: shutdown-recording-{0,250,1250}.json. Browser requests
remain loopback-only, no page errors. Inspected recording-failure-1280.png:
fixture banner, incomplete-recording status and disabled controls are readable.
This is failure-UI/transport review, not generated-world visual assessment.

Limit: late upload/failure-report delivery after listener shutdown cannot update
that manager. The private browser witness retains the failure here; a durable
recording-completion acknowledgement/missing-final marker needs separate design
and regression evidence. A fixture terminal receipt is not media completeness.
No Google captures were supplied, so fantasy camera/landmark/event fidelity remains
unassessed. No live world, Risk member, task checkbox or humanT029 acceptance.
15/30 tasks unchanged. No provider/device calls, .env read, private projection
export, sealed bundle/control/allowance/acceptance/PROGRESS/runtime change,
agents/loops, branch change, Git commit/publication or ticket.198at856bbc88 and
199AWS preserved. Native GAIT and final gait_log retained in the private pass root.
