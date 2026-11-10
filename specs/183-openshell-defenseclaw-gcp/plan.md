# Implementation Plan: GCP Borders and HA Mesh inside OpenShell and DefenseClaw (R09A)

**Branch**: `183-openshell-defenseclaw-gcp` (stacked on `182-multi-region-ha-borders`, PR #340) | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)
**Input**: spec.md; [research.md](research.md) (decisions D1-D9 and live experiment results E1/E2/E5/E8).

## Summary

Run each GCP Border node's NetClaw processes inside one OpenShell sandbox with a generated, versioned policy, guarded by a node-local DefenseClaw sidecar in blocking mode, and prove the R09 HA behavior still holds. Experiments showed the transport objections are retired: TLS 1.3 exporter binding survives OpenShell's forward (inbound) and `tls: skip` egress (outbound), the added latency is ~5 ms per hop, Ubuntu 24.04 (kernel 7.0, Landlock ABI 8) satisfies the Landlock hard requirement, and DefenseClaw 1.0.4 installs on amd64.

Target design (per node): one sandbox `netclaw-node` holding the Border role, the public HUD ingress, the workspace backend, the OpenClaw chat gateway and the DefenseClaw sidecar, sharing one loopback. Host-side, outside the sandbox by documented disposition: the etcd voter container (host network), the OpenShell gateway, the host port forwards, the metadata-server block, and (not deployed on GCP in this stage) member executors that need the Docker socket. The Anthropic key is never inside the sandbox: OpenShell's provider mechanism injects it at the egress proxy for `api.anthropic.com`.

Guaranteed floor if the deeper placement fails an experiment gate (E3/E4 below): the hybrid of research D2 option 3 (OpenShell for workspace backend and gateway only, DefenseClaw on every model path, hardened systemd/Docker for the HA core), stated plainly in the disposition table.

## Technical Context

**Language/Version**: Python 3.10+ (Border source, role launcher, tooling; contract env 3.12 inside the image), Node 24 (HUD ingress, workspace backend), Bash, YAML policies, Dockerfile.
**Primary Dependencies**: NVIDIA OpenShell 0.1.7 (Debian package, Docker compute driver), Docker >= 28, Cisco DefenseClaw 1.0.4 (pinned, checksum-verified), OpenClaw 2026.7.1-2 (qualified), etcd 3.6.x, existing R09 tooling (`labs/ha/r09_*.py`, `scripts/ha-r09-*.sh`), qualified R04A Anthropic guard configuration.
**Storage**: per-node persistent disk; sandbox state volume for the Border home; DefenseClaw audit SQLite on the node, exported on demand.
**Testing**: pytest (python3.10 venv), node tests for ingress, the R09 live matrix, a negative isolation suite (`labs/ha/r09a_negative.py`).
**Target Platform**: GCE Ubuntu 24.04 LTS amd64 (e2-standard-2, 8 GB), project `netclaw-506315`, region `northamerica-northeast1` for the validation topology.
**Project Type**: infrastructure + security hardening of an existing multi-client system.
**Performance Goals**: operations still complete inside the signed `admission_ms` (4500 in R09); overhead measured per hop and end to end.
**Constraints**: no HA/identity/admission guarantee weakened (FR-005); no billed resource before the owner confirms the estimate; nothing published or pushed live without approval; qualified-code changes listed for owner review (FR-024).
**Scale/Scope**: two Borders in one region plus one etcd witness (validation topology); three-region mesh not re-proven.

## Constitution Check

| Gate | Status | Note |
|---|---|---|
| I Safety-First / VIII Verify | PASS | Experiments before design; post-deploy verification and negative suite are tasks. |
| IV Immutable audit | PASS | DefenseClaw audit retained per node and exported before teardown. |
| IX Security by default | PASS | Default-deny sandbox policy, metadata block, no key in the agent sandbox, no world-open SSH. |
| XI Artifact coherence | ACTION | Docs/README/roadmap touchpoints in tasks (T0xx); no new MCP server is added. |
| XIII Credential safety | PASS | Provider key only in OpenShell's provider store/host root file, never in repo or sandbox. |
| XIV Human-in-the-loop | PASS | Owner approves cost estimate, deploy, qualified-code changes and teardown. |
| XV Backwards compatibility | PASS | Bind separation is optional and default-off; signed manifest and existing configs unchanged. |
| XVI Spec-driven | PASS | This spec/plan/tasks. |

Post-design re-check: PASS. The only new risk is D9a (qualified HA code); it is optional, default-off and tested, and listed for owner review.

## Phases

0. **Research and experiments** (done): [research.md](research.md); E1, E2a/b, E5 and E8-partial retired on one throwaway VM (torn down).
1. **Source work, offline**: (a) bind/advertise separation in `ha/config.py`, `ha/factory.py`, `ha/node.py` and the `scripts/lib/protected_role.py` validator, default-off, with tests; (b) policy generator, node image builder, VM bootstrap, deploy driver; (c) DefenseClaw node sidecar tooling from the qualified R04A configuration; (d) posture reporting and the negative isolation suite; (e) VS Code posture command (G12) and a G13 disposition note.
2. **Owner gate G1 (cost)**: owner confirms a line-item estimate for the validation topology.
3. **Deploy** (billed): two Border VMs + one etcd witness VM in one region, OpenShell + DefenseClaw per node; first-boot experiments E3 (Border role inside the sandbox) and E4 (member/ingress listeners via forwards) decide deeper placement vs the floor.
4. **Validate**: acceptance rows, R09 failure matrix, overhead, DefenseClaw block/fail-closed tests, negative suite.
5. **Document and release gate**: evidence, dispositions, owner-review list; PR; nothing published without approval.
6. **Teardown** (only on the owner's request, exact resource list).

## Project Structure

```text
specs/183-openshell-defenseclaw-gcp/
├── plan.md  research.md  data-model.md  quickstart.md  tasks.md
├── contracts/ sandbox-policy.md  node-posture.md  disposition-table.md
└── checklists/requirements.md

labs/ha/r09a_policy.py         # NEW: sandbox policy generator + validator (default-deny, tls: skip peers, provider injection)
labs/ha/r09a_image.py          # NEW: node image build context (frozen source, python 3.12 env, node, openclaw, defenseclaw)
labs/ha/r09a_negative.py       # NEW: negative isolation suite driver
scripts/ha-r09a-vm-bootstrap.sh  scripts/ha-r09a-deploy.sh   # NEW: Ubuntu 24.04, Docker, OpenShell, DefenseClaw, forwards
mcp-servers/protocol-mcp/bgp/federation/ha/{config,factory,node}.py   # CHANGED (D9a, default-off)
scripts/lib/protected_role.py  # CHANGED (accept optional listen block in ha-config)
extensions/netclaw-vscode/src/...   # CHANGED: show node posture (G12)
tests/n2n/test_ha_sandbox_183.py  tests/n2n/test_ha_bind_183.py
```

**Structure Decision**: tooling beside the R09 tooling; HA code changed minimally and default-off; clients extended read-only.

## Qualified-code changes (owner review, FR-024)

a. D9a: optional `listen` block (private ha-config, not signed) separating bind address from the advertised manifest address; default-off.
b. `protected_role.py`: accept that optional block in the exact-field check.
c. Posture aggregator wording: per-component reporting; never "enforced" for components outside OpenShell.
d. Carry-overs from R09 still pending review (PR #340).

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
|---|---|---|
| D9a bind separation | Border must listen on a sandbox loopback address while peers dial the signed address | Binding the signed public address is impossible inside a sandbox netns |
| One sandbox per node (not per component) | Components share a loopback (ingress to operator API, backend upstream) | Per-component sandboxes would need cross-sandbox loopback bridges and changes to the HUD config validation |
| etcd + witness outside OpenShell | Needs host networking and TLS peer ports | Documented disposition (FR-019); confined by container policy |
