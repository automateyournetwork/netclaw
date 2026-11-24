# Pass21 — world3: recover lost recording acknowledgement

Assignment: cinematic network city, source_refinement. Followed the pass20
lifecycle handoff; no generated Google captures exist for visual review.

Actual isolated Chrome reproduced a false incomplete recording: the manager
committed the final receipt, the injected transport lost its response, and the
viewer recorded an upload failure. The viewer now makes one bounded evidence GET
on the original operation. A matching acknowledged byte count recovers confirmation;
an unavailable read visibly reports final confirmation unavailable without marking
successful chunks failed. No upload, finalization or provider operation is retried.
Genuine recorder/upload failures remain durable and visible; shutdown bounds stay
unchanged. No new source module; existing29-file closure includes the changed viewer,
so every older paid packet is stale and must be reviewed again by the coordinator.

Tests:26/26 affected manager/actual-Chrome tests and44/44 source-binding/provider recovery tests pass,
zero skips. New scenarios lose the final response after server commit, also lose
the recovery read, and SIGKILL the owned isolated Chrome process before onstop.
Same-root manager restart returns the same operation with zero restarted workers.
Committed receipts retain matching media hash/size; browser death retains nonempty
media with no receipt and unconfirmed state. Single creation/finalization counts,
no external requests, no page errors and live_world_proven=false are asserted.
The death test closes the manager afterward; autonomous heartbeat-stop timing
following death is not separately qualified by this test.

Private evidence: .spec200-local/tests/world-pass-21/affected-tests.log,
source-binding-tests.log, receipt-recovery-*.json, reproduction.log,
reproduction-final-response-loss.json and native GAIT start/end/log. Original
failed assertion and false recording-failure receipt remain retained.

No task closes (15/30); T014/T025/T029 remain open. No live world, Google identity,
visual fidelity, installed Risk-member execution or human acceptance established.
No provider/device calls, dotenv reads, private projection export, sealed bundle/
control/allowance/acceptance/PROGRESS edits, owner-runtime changes, branches, agents,
loops, Git commits or publication.198at856bbc88 and199AWS preserved.

Next concrete defect: viewer Google-mode cost text still hardcodes US$2.02 estimate
and US$15 reservation. Bind displayed duration/cost/reservation to the actually
reviewed immutable session policy, distinguishing legacy fixture from120s campaign
and estimate from reservation; never infer paid authority from a UI label.
