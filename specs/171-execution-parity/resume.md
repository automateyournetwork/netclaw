# R02–R05 active work — 2026-11-02

The owner authorized R02–R05 completion, a coordinator plus three parallel agents,
and optional implementation passes capped at five total. The roadmap release,
version and rollout hold persists. Human gates and exact cloud/spend review remain.
Use CAD100/month total GCP cost, including R01, conservatively. No new cloud plan
has been approved. R03 remains behind the human R02 evidence gate.

Branch/spec: 171-execution-parity; baseline 5e50bbba. Specify, clarify, plan, tasks
and independent analysis are complete. All six design findings were corrected
and independently rechecked PASS. Implementation is starting; no live R02
qualification yet. Source 1.18.3 and extension 1.5.0 remain unchanged.

Private work root: ~/.local/share/netclaw/roadmap-r02-r05-20261102/ (0700).
GAIT branch of the same name is active; start record 36645faf. Startup reads are
complete. Default pyATS/MemPalace were unavailable; do not infer device state.
Fresh private runtimes and prior spec162 inventory/credential evidence are
available, but current device reachability has not been established. Never print
credentials or modify the active R01 homes.

Contracts: execution.md and hud.md are authoritative. Backend owns Python
protocol/store/service/owner/GAIT and owner CLI. HUD owns Node/React. Coordinator
owns runtime/guard/facade/pyATS and qualification. Independent verifier owns new
test files/review. Separate worktrees prevent overlapping edits.

The installed Ralph plugin uses Claude Code stop hooks; no native Codex start
interface is exposed. Use explicitly counted implementation/test/review passes,
not fabricated hook records. Pass 1 starts now; maximum five across R02–R05.

Checkpoint progress: design3551cd6a, HUD cherry-pick1c11ac2d froma57db7be.
Root runtime implements isolated OpenClaw/Hermes, fixed relay, durable inference
limits and execute-once pyATS. Both actual harnesses passed synthetic2model/1tool
sequences; no real provider/device acceptance yet. Independent suite154passed
against sibling protocol and root runtime; verifier commit73a2335d ready.
Official guard startup/retry qualification is delegated to r02_hud in private
guard-qualification. Protocol agent preparing commit. Three worktrees under the
private root. Runtime profile requires sandbox_address_pool198.18.0.0/15 because
Docker default subnet pools are exhausted; no existing networks removed.
Hermes explicit scope addition is recorded in spec.md.
