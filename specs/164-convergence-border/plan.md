# Plan

1. Implement an allowlisted bounded evidence builder and selected-address Investigate
control using existing Dashboard/Canvas context. Cover scope changes, failed refresh,
empty/maximal records, large/untrusted strings and timestamp fidelity.
2. Add the OpenClaw profile and narrow provisioning/environment paths with readiness
validation and isolation regressions. Retain Hermes restrictions and existing profiles.
Extract the existing connector Settings validation into a stdlib-only module to reuse
it from profiles without importing HTTP dependencies; preserve public imports and
request/response behavior. Convergence-specific member setup must isolate skills as
well as credentials because generic OpenClaw provisioning shares the Border workspace.
Exercise the actual existing OpenClaw receiver path and test completed dispatch.
OpenClaw uses native member configuration; the protected execution profile applies
to Hermes. Keep dispatcher behavior unchanged. Restrict the Convergence member's
native tools and workspace reads without restricting the Border's other capabilities.
Share the native member tool policy between the scoped legacy provisioner and the
separate-claw setup builder for role=member/profile=convergence. Selecting that profile
through another setup surface must not omit its restrictions. Existing platform gates
remain authoritative; this adds no Mac/WSL or Linux IDE qualification.
3. Clarify source-specific retrieval limits versus Border investigation ownership in
skill and user docs; regenerate the existing catalog if skill hashes change. No new
component/server/tool/env variable is introduced, so installer entry/count changes
are not applicable; verify existing catalog coverage and reconciliation.
4. Run affected contract suites, HUD unit/build and fixture browser interaction;
independently review final integrated diff. Preserve outstanding real-model acceptance.
If fixed-delay HUD fixture waits fail under parallel load, replace only those waits
with bounded readiness conditions while retaining all behavioral assertions. This
test-harness correction is required for the default suite; production Pal code is
outside scope.

Coordinator owns spec/docs/skill/generated catalog and integration. HUD worker owns
Convergence UI, handoff helper and HUD tests. Member worker owns in2n profile/provisioning
scripts and associated tests. No worker commits, publishes, deploys or calls providers.
