# World-suite pass32 — world4: preserve ended-session status

2026-11-23. Environment assignment pass32/world4; source_refinement.
One partial T018/T020/T028 unit; no task closes,15/30 unchanged.

The actual Chrome regression reproduced a delayed active status replacing an
unknown display while terminal control guards remained set. The viewer now retains
ended lifecycle fields independently from arriving session metadata. Unknown can
advance to terminal, and terminal usage can advance to reconciled; subsequent
stale active/unknown statuses cannot discard the receipt or settled usage.
Failed-pre-send remains ended. The original operation and evidence access persist;
this display state never creates a provider receipt or changes backend authority.
No new runtime module: existing29-file closure membership is unchanged. Viewer
bytes changed, invalidating all earlier exact paid source packets.

## Verification and visual review

- Spec Kit prerequisites pass; requirements15/15 and quality43/43; optional Git
  hooks omitted. Current native GAIT root and audit branch reused.
- Red actual Chrome assertion reproduced unknown-to-active regression:
  `.spec200-local/tests/world-pass-32/browser-red.log`.
- Final actual Chrome8/8, zero skipped: `browser-green.log`. New synthetic
  unknown/terminal/failed-pre-send cases cover delayed active statuses, later
  terminal receipt, later reconciled usage, stale unknown and stale terminal
  snapshots, disabled controls, one start, zero stop replays and original-ID
  evidence. Existing baseline timeout, media, event, navigation and capture
  regressions also pass. `status-order.json` retains the new case results.
- Exact source-closure/staleness checks5/5, zero skipped: `source-review.log`.
  Source/test hashes and diff whitespace check retained privately.
- Reviewed `status-reconciled.png`: explicit OFFLINE TRANSPORT FIXTURE / No Google
  generation, VIEWING ENDED / No frame decoded, terminal receipt and reconciled
  usage labels, disabled Stop/actions, readable original-ID evidence. These are
  synthetic transport statuses, not provider termination or generated-world proof.
- Native GAIT start/finish and full gait_log retained in the private pass folder.

No provider/device/CML/SSH/pyATS calls, dotenv reads, projection export, sealed
bundle/control/allowance/acceptance/PROGRESS changes, owner-runtime modification,
agents/loops, branch changes, Git commits or publication. Actual Google visual
navigation/event/drift, installed Risk member and human T029 remain unqualified.
198at856bbc88 and199AWS preserved. Hosted worlds3–5 still require coordinator
recorded actual success of1/2; all five source styles may continue refinement.

Next concrete unit: fix recording.test.mjs cleanup registration before Chrome
launch/launchServer. All three sites register t.after only after launch; failed
launch can leak the already-created manager/root (previous pass28 observed this).
Use an injected rejected launcher and bounded process teardown evidence; preserve
recording tests and failures. Event JPEG/DB crash gap remains unconfirmed.
