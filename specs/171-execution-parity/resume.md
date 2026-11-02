# R02–R05 active work — 2026-11-02

Owner scope: finish R02–R05 with a coordinator and three parallel agents, with at
most five optional implementation-loop passes total. Pass 1 is still active; the
Claude Code Ralph stop-hook plugin is not running. The release/version/public
rollout hold remains. Human roadmap gates and exact cloud-resource/spend reviews
remain. Conservatively use CAD100/month total including R01. No new cloud plan
is approved, and R03 is behind the human R02 evidence gate.

Branch `171-execution-parity`, baseline `5e50bbba`; source 1.18.3/extension 1.5.0
unchanged. Design gate passed. Backend, owner authority, protected HUD, guarded
OpenClaw/Hermes runtime and independent tests are integrated in stages. Current
progress: 24/36 tasks checked; real provider/device qualification is outstanding.
See verification.md, runtime-review.md, parity-matrix.md and contracts/.

Private work root: `~/.local/share/netclaw/roadmap-r02-r05-20261102/` (0700).
GAIT branch of the same name is active. Latest checkpoint receipt:
`gait-before-live.json`. Startup reads were completed; do not restart them.
Preserve existing R01 homes, cloud state, owner inventories and all prior evidence.

Actual fixture evidence: both native harnesses passed two model callbacks and
one MCP callback; strict TLS/iN2N transport passed ten checks, signed receipts
were independently verified, and lost-ACK/full restart retained one synthetic
effect. Chrome now passes sixteen checks including uncertain prepare-response
recovery. Official DefenseClaw runner/action/strict policy startup and stop pass;
actual SDK retry/drop/restart tests prove the new inner provider fence works
against local stubs. None of that is real provider/device acceptance.

CML is now reachable after the owner started it. Original R1/R2/SW1/SW2 are
booted. Exact-node authenticated console public key matches R1 SSH. Private
`live-qualification/pyats-config.json` and strict R1-only inventory are ready;
actual native load and SSH argv checks passed offline. Original inventories are
unchanged. Root commit `ef53e606` pins global known-host exclusion and exact native
Unicon class identity. Device credentials are copied from the original testbed,
never from the CML controller account. No R02 SSH authentication/show version yet.

Guard image/config/policy pins are in runtime-review.md. Existing authorized
Anthropic key is only in private `live-qualification/guard.env`; do not print it.
`member.env` has only the three device aliases and a separate guard-client token.
`guard-client.env` retains that token. Border and model never receive those keys.
Hermes qualifies the compatible HTTP guard adapter/MCP broker, not native hooks.

Current agent ownership:
- r02_protocol: fixes signed runtime/tool revision binding in protected_docker.py
  and a deterministic helper; exact local Docker socket/config and raw MCP
  arguments also being hardened. It owns this file; root has a pre-existing
  uncommitted per-operation guard launch patch it incorporated. Cherry-pick only
  its focused fix commit, not its local baseline snapshot.
- r02_runtime_design: UX integrated at `1453778b` atop `8e510a98`; final independent
  source/evidence review preparation is active. Tests/build/browser passed.
- r02_hud: guard and R1 identity/inventory work complete; reviewing private native
  qualification driver and preparing independent raw/parsed-result validation.

Private native driver `live-qualification/live.py` prepares fresh real enrolled
homes and uses worker.py `--executor native` (no fixture factory). It is NOT yet
started. Runtime-openclaw.json/runtime-hermes.json generation awaits the revision
helpers. It waits for browser-done.json, checks actual result and retained
provider/tool artifacts, then restarts/reconciles. Helpers launch-hud.py and
browser.mjs require an explicit current run path. Driver reads have deadlines.
Finish reviewing scoped cleanup and real refusal probes before launching.

Next: integrate revision fix; generate exact native configs; final independent
pre-live check; execute two actual delegated browser-approved reads (Hermes loses
ACK reply after durable member ACK); inspect raw/parsed output independently,
verify provider/tool counts and no-repeat recovery; full relevant regressions,
final matrix/security review, then present human R02 gate. Do not claim 100% or
start R03 until that evidence and gate are complete. No release or public docs.
