# Pass26 — world3: event capture ordering

Assignment: SPEC200_WORLD_PASS=26, SPEC200_WORLD_NUMBER=3, source_refinement.
Spec Kit prerequisites and checklists pass (requirements15/15, quality43/43).
Optional Git hooks skipped; current native GAIT root/audit branch reused.

The viewer no longer enables event capture from a baseline alone. It waits for
`event_state: sent` from the original session, then a frame received and decoded
after that acknowledgement. A frame already decoding at receipt time does not
qualify. This is local ordering, not proof of provider generation timing or a
visible effect. A persistent readable status keeps visibility unassessed.

The backend already validates the single fixed event identity across viewer/MCP.
Its sent status now disables the viewer event button even when a member sent it.
Delayed, refused and unknown attempts do not enable capture or replay the event.
The checkpoint handler also checks readiness; an ignored call cannot falsely mark
capture complete. Existing baseline/media/focus/stop guards remain in force.

Evidence: `.spec200-local/tests/world-pass-26/`.

- Actual Chrome red regression reproduced the premature button from baseline.
- Final browser4/4, zero skips: existing playback, budget and media-readiness
  scenarios plus five new event cases (delayed, refused, unknown, member-sent,
  in-flight decode). Tests retain original fixed event ID, zero/one send, exact
  checkpoint order and zero real provider calls. Synthetic status/media injection
  is labeled; it is not actual member or Google execution.
- Source-review4/4 confirms existing29-file closure covers changed viewer assets
  and rejects stale bytes. No new live module. Old paid packets remain stale.
- Actual screenshot `event-delayed.png` reviewed: separate send/frame/visibility
  text, readable controls and explicit offline-fixture banner. Generated city,
  camera, landmarks, recognizability and visible event remain unreviewed.
- Recording regression10/10 passes, zero skips; final native GAIT receipts/log
  and evidence hashes retained privately. git diff --check passes.

Next concrete defect: authenticated checkpoint POST currently accepts an event
JPEG before a sent event and records no original-event/frame correlation. Viewer
ordering does not enforce backend evidence integrity. Add backend refusal and
explicit retained capture metadata with synthetic tests; do not infer visible
success or replay events to repair missing evidence. Single-flight checkpoint
submission during a delayed HTTP response is also not yet qualified.

No task closes (15/30). No provider/device calls, dotenv read, sealed snapshot or
control/allowance/acceptance/PROGRESS edits, private export, owner runtime changes,
agents/loops, branches, Git commits or publication. Coordinator owns live packets;
hosted worlds3–5 require actual1/2success. T029 remains human-only. No tickets or
external communications. Preserve198at856bbc88and199AWS.
