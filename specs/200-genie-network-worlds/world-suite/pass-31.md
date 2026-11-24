# World-suite pass31 — world4: bounded baseline persistence

2026-11-23. Environment assignment pass31/world4; source_refinement.
One partial T018/T020/T028 unit; no checkbox closes,15/30 unchanged.

Automatic baseline capture previously awaited HTTP indefinitely. It now claims
the baseline before awaiting a three-second bounded request, displays Saving,
and retains Unconfirmed on error/response loss. Later media cannot replay the
claim. Failure uses the existing stop path, disables interaction and preserves
original-session evidence access. A late reply cannot convert an aborted save
into confirmed evidence. Decoded bitmaps close in finally, including save failure.
No new source module; existing29-file review membership unchanged. Viewer bytes
changed, so previously reviewed paid packets remain stale.

## Verification and visual review

- Spec Kit prerequisites pass; requirements15/15 and quality43/43. Optional Git
  hooks omitted. Existing native GAIT root/audit branch reused.
- Red actual Chrome reproduced the missing bounded outcome at4.5seconds:
  `.spec200-local/tests/world-pass-31/browser-red.log`.
- Initial green run exposed a new test-harness error: it attempted to parse the
  recorder's final WebM POST as JSON. Restricted JSON parsing to checkpoints;
  retained `browser-harness-failure.log`. No production binary handling changed.
- Final actual Chrome7/7, zero skips, including four new synthetic scenarios:
  hanging baseline, lost reply, Stop while pending and late success after timeout.
  Checks one baseline/one start, no key/event/capture replay, original-ID stop
  and readable original evidence. `browser-green.log` and `baseline-timeout.json`.
- Exact source closure/staleness checks5/5, zero skips: `source-review.log`.
  `git diff --check` passes; source/test hashes retained privately.
- Reviewed `baseline-unconfirmed.png`: explicit OFFLINE TRANSPORT FIXTURE /
  No Google generation label, retained frame, disabled interactions, readable
  ambiguity and accessible evidence. This is the existing synthetic transport
  JPEG, not a Google world or a new local scene substitute.
- The same screenshot exposes a separate existing defect: after an acknowledged
  terminal status, injected delayed active status overwrites the visible status
  with active/no receipt, although sticky terminal keeps Stop/interaction disabled.
  Preserve this finding for the next bounded unit; display consistency is not
  qualified by this pass.
- Native GAIT start/finish and full gait_log retained in the private pass folder.

No provider/device/CML/SSH/pyATS calls, dotenv reads, private projection export,
sealed/control/allowance/acceptance/PROGRESS changes, owner-runtime modification,
agents/loops, branch changes, Git commits or publication. Google generation,
camera/landmarks/navigation/event/drift, installed Risk member and human T029
remain unqualified.198at856bbc88 and199AWS preserved.

Next: reproduce and fix delayed status regressing terminal display while preserving
unknown versus confirmed-terminal receipts and original-session evidence. Secondary
recording.test.mjs cleanup-before-Chrome-launch gap remains; event JPEG/DB crash
gap remains unconfirmed. Hosted worlds3–5 still await coordinator-recorded1/2 success.
