# Spec 163: Fresh Linux Convergence qualification

Created 2026-10-31; branch `163-convergence-linux-qualification`.
User authorized a dedicated fresh Ubuntu VM and resumption of the next milestone.
Follow the checked-in Spec Kit artifact order manually; this is a bounded follow-up
to spec 162 / PR311, not an expansion of its read-only tool contract.

## User scenarios and acceptance

1. P1: A new Linux user can install an isolated synthetic Convergence service and
optional NetClaw reader using published commands, without existing runtime state,
network equipment or device credentials. Document actual prerequisites and versions.
2. P1: A real OpenClaw gateway/model turn invokes both native MCP tools, preserving
site, exporter and the exact summary window. Its answer identifies synthetic scope,
record limits and uncertainty. Native inventory alone is not model execution proof.
3. P2: Restart preserves retained evidence and registration; disabling the reader
removes access without destroying external data. Unauthorized and unavailable cases
remain explicit, not fabricated zero traffic.

## Requirements and success criteria

Use a private site-scoped viewer token, loopback-only trial endpoints and minimal
provider authentication. Never copy production device credentials or runtime state.
Record baseline, commands, versions, outcomes and gaps without secrets. Fix discovered
onboarding defects with proportional regression checks. Independent review and
applicable repository gates precede completed qualification claims.

Only Ubuntu 24.04 amd64, synthetic demo, OpenClaw and the chosen provider are in scope.
Mac/Windows, Hermes, physical capture, production migration and K3s qualification
remain separate. A missing provider credential is blocked coverage, not a pass.
