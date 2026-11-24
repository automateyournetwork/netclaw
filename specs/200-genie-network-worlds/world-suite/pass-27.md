# Pass27 — world3 backend event checkpoint correlation

Implemented the concrete pass26 defect: direct authenticated event checkpoint
POST previously accepted a JPEG before any event. The red test retained HTTP200
versus expected400. Backend now re-reads state after body receipt, requires the
active original sent event and baseline, and accepts only a recent worker frame
observed after the original sent-status acknowledgement. Viewer submits its last
decoded sequence. A bounded256-frame window retains source-frame hash/time.

Synced immutable JPEG plus additive SQLite/audit receipt retain original operation,
event, send-marker time, acknowledgement-observation time, frame identity/hash,
capture hash/size/time and explicitly unassessed visibility. Evidence detects
missing/changed capture bytes; restart retrieves original receipt with zero new
workers. Neither an old historical capture nor a file-only partial write is
promoted to correlated. Source closure remains29files; manager/ledger/viewer bytes
changed, so old paid packets are stale.

Validation: requirements15/15 and quality43/43; Spec Kit prerequisites passed,
optional commit hooks omitted per owner. Supported Node, ignored private temp root.
Backend/core23/23; final focused backend1/1 after source-frame hash addition;
actual Chrome4/4; source-review5/5; zero skips. Tests cover premature event,
missing baseline, stale/invented sequence, immutable capture, retained receipt,
restart without creation and tampered JPEG. Actual browser playback retains the
correlated receipt; other synthetic browser scenarios preserve controls/media
ordering. Screenshot fixture-viewer.png inspected: clearly labeled offline
transport, no Google generation, terminal state, readable unassessed effect.
Private logs, JSON, screenshot, hashes and native GAIT are under
.spec200-local/tests/world-pass-27/; gait_log retained there.

Limits: backend sequence correlation does not authenticate recompressed JPEG
pixels or independently prove browser decoding. No Google visuals exist for
camera/landmarks/drift review. No task closes (15/30); no live/member/T029
acceptance. No provider/device calls, dotenv read, private export, authority or
PROGRESS changes, owner runtime modification, agents/loops or Git operations.
198at856bbc88and199AWS preserved.

Next concrete unit: prevent duplicate navigation/event checkpoint HTTP submissions
while persistence is delayed. Keep explicit unknown capture outcome after response
loss and never replay events or recreate a session to repair missing evidence.
Historical Chrome launch/playback failures remain unexplained.
