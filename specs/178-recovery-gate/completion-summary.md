# R07 completed: recover safely before adding HA

Spec178 closes the single-region recovery gate with31/31tasks, accepted by the
owner on2026-11-07. Border/member restart, explicit endpoint movement, revoked
authority, lost replies, duplicate requests and cancellation preserve the original
identity and execution record. Pending dispatched work interrupted by Border
process death becomes an unknown reconciliation item; recovery does not replay it.

The implementation checks authority across awaited work and response delivery,
persists revocation before closing channels, retains HUD/editor send markers,
and verifies endpoint changes before replacing client bindings. Mobile additionally
fences late reconnects and handles TLS failure without an unobserved readiness
error. Actual Chromium, Code1.109 and iOS simulator journeys preserve references;
client controlled workloads and earlier cloud evidence remain separately labeled.

Validation includes1,756federation passes/5existing skips,529HUD passes serial,
209editor passes/3existing skips,518Flutter passes, focused recovery regressions,
builds/analyzer and clean-source coherence. [Verification](verification.md)
retains exact counters, manifests, failures, platform limits and the initial
Code1.145 shared-storage mtime incident with unknown content impact.

The [runbook](runbook.md) covers every acceptance row. Accepted investigation
targets are120s failure visibility,180s automatic reattachment,30s explicit
recovery and130s cold history; these are not demonstrated worst-case SLAs.
All owned disposable services stopped and private evidence was exported.
R05/R06 schedules and the original Border lifetime remain unchanged.

Source integration does not redeploy retained runtimes or publish a release.
Next is a joint review of [R08 HA authority](../../docs/roadmap/issue-310/briefs/R08-border-ha-authority.md):
exactly one execution authority, member-enforced fencing and no protected work
without quorum. R08 implementation and resource creation are not started here.
