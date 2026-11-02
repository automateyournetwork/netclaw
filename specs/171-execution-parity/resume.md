# R02–R05 checkpoint — R02 human gate ready

2026-11-02. Technical R02 acceptance is complete: T001–T035 pass; T036 is pending
human review of parity-matrix.md and verification.md. The R02 roadmap brief and
FR016 explicitly gate R03 on that review. Do not infer acceptance from silence.

Owner scope remains R02–R05 with coordinator plus three parallel agents, separate
worktrees and at most five optional implementation passes total. Two passes were
used; no Claude Code Ralph stop-hook ran. Preserve the full-roadmap release,
version and public-rollout hold. Total GCP lab ceiling is conservatively CAD100
per month including R01, with exact resource/spend review. R03–R05 have not started;
no new cloud resource or existing R01 runtime change occurred.

Branch `171-execution-parity`, qualified runtime source `8c178ff8`; source1.18.3
and extension1.5.0 unchanged. Final native run under private root
`~/.local/share/netclaw/roadmap-r02-r05-20261102/`:
`live-qualification/run-20261102T155125-625aeb/`.

- OpenClaw operation `ff22d921-951b-4024-8eaa-b5547417c980`.
- Hermes operation `dc674dfe-5af0-46ce-a5dc-9091fb0bd0d1`.
- Each: two guarded Sonnet4.6 provider calls, one R1 `show version`, zero setup
  commands, parsed IOS-XE17.18.2, verified signatures/ACK and correlated GAIT.
- Native driver7 groups, Chrome15, HTTP26 and wire12 checks pass. Actual submit
  reply loss, result-ACK reply loss and full restart preserve original identities
  and provider/inference/tool evidence. All owned services/containers stopped.
- Independent report `independent-native-receipts-20261102T155405.json` passes
  strict signature/authority/transcript/provider/tool/GAIT/recovery checks.
- Credential scan86 files has no matches; original inventories unchanged.

Tests: protected311 (two existing utcnow warnings), relevant legacy/installer219,
HUD436 serialized (initial parallel run had two fixed-delay flakes, isolated
files23 passes), Node boundary8 and HUD build. Actual same-image network probes
and actual production ASGI/MCP negative fixtures passed; their external synthetic
seams and platform limits are explicit. Do not rerun successful real operations
or broaden tests without a new reason.

## Important retained history

Pass1 produced authentic guarded signed reads in run152632-4e16f6, but independent
full transcripts found an extra Unicon `show version | include operating mode`
connection probe. Empty init lists and MIT alone do not suppress this. That
run's aggregate report failed on tuple serialization; clearly labelled salvage
and independent20-check read-only restart evidence remain. It does not establish
exact-command acceptance. The final pass2 run above has original complete reports
and sole-command acceptance; no old approval was replayed.

Pass2 pins pyATS/Genie/Unicon25.2 and all580 Unicon .py/.so files for this Mac
IOS-XE/IOL profile. Internal operating_mode=True is the vendor skip-discovery
marker, not a device-mode assertion. Fixed MIT/no-learning/no-reconnect settings,
actual setting checks and an already-enable state prevent unreviewed setup/state
transitions. Tool/source revisions bind this policy; other profiles refuse.
Native source manifest e53e542cee1b5b531ffeb9042e43685eaad3cf1fc36a4f0c46fe23a949f3f7b7.
Current tool revision6ed490f59921afee69780ba5e90a9d3a0ae95baa32cb7952ca6ce70293b01f68.
Exact image/runtime pins remain in runtime-review.md; guard image5aec2081….

Earlier failed bootstrap/guard/token runs and the SSH timeout run151005-bf2245
remain preserved. Operation1a7a0400-d272-4d68-80ff-cb1d6efaa205 is still unknown/
spent: one provider call, claimed tool, no captured result. Independent14-check
reconciliation-only restart caused no new effects. Never replay that operation.

CML restored twice by owner; saved addresses controller192.168.2.125, R1.201,
R2.202, SW1.211, SW2.212. Only R1 qualified in R02. Exact-node interface/public-key
verification and latest endpoint key check matched the original pin. Native
credentials are separate from controller credentials; no trust relaxation.

## Resume action

Present/resolve the concrete T036 human evidence gate. After acceptance, record
it and begin the R03 Spec Kit cycle, rechecking the next available spec number.
R03 is an authenticated control-only GCP Border plus outbound on-prem members
reading four CML devices; it does not inherit R01's open-lab exception. Later
R04 is a cloud NetBox/subnet member, R05 cloud/local Ollama, each with its own
human gate. Prepare exact reviewable resource/cost plans before cloud changes;
no budget alert is a hard spending cap. The $100 total ceiling remains binding.

Preserve all private successful/failed homes, receipts, stopped containers,
source manifests, original testbeds and authoritative R01 tfstate. No new real
operation is needed to close R02. Startup reads and GAIT session already exist.
GAIT branch `roadmap-r02-r05-20261102`; retain final gate/log receipts and daily
memory. MemPalace tools were unavailable. No external messages/tickets were sent.
