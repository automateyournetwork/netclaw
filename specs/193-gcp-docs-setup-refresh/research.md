# Research: Spec 193

## D1. Provision outside the Spec153 effect engine
**Decision**: standalone provisioner invoked by every frontend; Claw Plan only records the chosen topology id.
**Rationale**: the engine's effects are owned by a claw id and pinned by hash (`effects.json`); adding a cloud phase means a new schema block, dispatcher branches in apply/observe, cleanup artifacts and extension client changes, with high regression risk to a qualified engine. The provisioner already needs its own list-hash and cost gates.
**Alternatives**: new `cloud` effect phase (cleanest review binding, much larger blast radius; recorded as a follow-up); OpenTofu (new dependency, rejected in R09).

## D2. No default project
**Decision**: project must be supplied or taken from `gcloud config` and shown for confirmation; never a baked-in value.
**Rationale**: spec FR-006/SC-008; the lab scripts default to a previous operator's project.

## D3. Reuse R09 pattern
**Decision**: plan/apply/status/teardown, pure plan builder, injected runner, label+prefix ownership, IAP SSH retry.
**Rationale**: proven in three live rebuilds; testable with a fake runner.

## D4. Ownership marker
**Decision**: per-deployment id (6 hex) -> prefix `nc-<id>-`, label `netclaw-deployment=<id>`; state file records exact names.
**Rationale**: SC-003; two users in one project must not collide; addresses cannot be labeled, so names carry the prefix.

## D5. Warning single source
**Decision**: `scripts/lib/gcp_warning.txt` read by TUI, CLI, extension and docs generator/check.
**Rationale**: FR-015 requires identical text; a test asserts docs embed it verbatim.

## D6. Software bootstrap scope
**Decision**: single Border/Member bootstrap via the standard installer; HA/distributed via generalized R09 scripts. Limits documented.
**Rationale**: honesty over breadth; OpenShell/DefenseClaw sandboxing (R09A) is offered only if the generalization is verified live.
