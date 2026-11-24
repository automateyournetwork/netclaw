# Pass34 — world4 keyboard identity across modifiers

Assignment: SPEC200_WORLD_PASS=34, SPEC200_WORLD_NUMBER=4; source_refinement.
One bounded T018/T020/T028 source unit; no checkbox closes (15/30).
Spec Kit prerequisites passed; requirements15/15 and quality43/43. Optional
Git hooks skipped as instructed. Existing GAIT root and audit branch reused.

## Concrete defect and repair

Actual isolated Chrome reproduced w-down, Shift-down, repeated W-down and W-up:
the browser emitted KeyW throughout but the viewer sent only movement-down.
Case-sensitive keyup lookup lost the release. The regression retains native key
witnesses and synthetic WebSocket controls; it makes no provider request.

The viewer now stores the original command under event.code and retrieves it
on keyup. Letter matching accepts uppercase WASD; a normalized fallback covers
missing code. Repeat suppression, Escape, canvas/window blur and terminal release
remain intact. No new runtime module or source-closure member is added. Existing
29-file source closure has changed viewer bytes; previous paid packets are stale.
Coordinator must review a fresh exact packet before any future admission.

## Evidence

Private: .spec200-local/tests/world-pass-34/.

- keyboard-red.log: actual Chrome failure, movement-down without movement-up.
- keyboard-green.log: retained first repair run; a test assertion raced the
  asynchronous down packet. Replaced timing assumptions with observed ordered
  WebSocket messages; no production rule was relaxed.
- browser-final.log:9/9 actual Chrome tests, zero skips. New regression covers
  changed-case releases in both directions, repeat suppression, arrow release,
  Escape, canvas/window blur, terminal controls and zero event sends.
- source-review.log:5/5 source closure/mutation/manifest checks, zero skips.
- keyboard-reproduction.json and keyboard-guards.json: final synthetic key/control
  packets, zero provider calls. Red console assertion remains separately retained.
- keyboard-released.png: visually reviewed; explicit offline/no-Google banner,
  retained fixture frame, ended session, disabled controls, usable evidence and
  unknown usage. This is transport/UI evidence, not generated-world fidelity.
- source-hashes.json, result.json and native GAIT start/finish/full log retained.

## Limits and next unit

Google generation, visual navigation/event/drift, provider termination/billing,
private projection export and selected Risk/member acceptance remain open.
No provider/device calls, dotenv reads, sealed bundle/control/allowance/acceptance/
PROGRESS changes, runtime changes, agents, loops, branch changes, Git commits,
publication or external tickets.198at856bbc88 and199AWS preserved. No T029 verdict.

Next pass35/world4: reproduce held ArrowDown repetition in Chrome. preventDefault
is still inside the first-keydown-only branch; repeated arrows may scroll the
page while steering. Capture native defaultPrevented/scroll position and packets
before fixing. This is a source-inspected risk, not yet observed live behavior.
Member-browser harness cleanup-before-launch remains a separate known test gap;
preserve snapshotRegistryPath if migrating it. Event JPEG/DB crash gap remains
unconfirmed. Never use a paid session to reproduce these offline issues.
