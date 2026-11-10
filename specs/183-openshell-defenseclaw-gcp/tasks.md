# Tasks: GCP Borders and HA Mesh inside OpenShell and DefenseClaw (R09A)

**Input**: `specs/183-openshell-defenseclaw-gcp/` (spec, plan, research, contracts). Tests are included because the spec demands adversarial and HA evidence.
**Gates**: G1 = owner confirms the line-item cost estimate before any billed resource (T020). Nothing is published or pushed live without owner approval. Teardown only on the owner's request.
**Format**: `- [ ] T### [P?] [US?] description with path` (P = parallel; US = user story from spec.md).

## Phase 1: Setup and research (done where checked)

- [x] T001 Research OpenShell/DefenseClaw hosting and record decisions in `specs/183-openshell-defenseclaw-gcp/research.md`
- [x] T002 Run experiments E1 (kernel/Landlock), E2a/E2b (TLS exporter in/out of a sandbox), E5 (DefenseClaw amd64), E8-partial on one throwaway VM and tear it down; append results to `research.md`
- [x] T003 Write `plan.md`, `data-model.md`, `contracts/*`, `quickstart.md`
- [ ] T004 [P] Write `specs/183-openshell-defenseclaw-gcp/cost-model.md`: line items for 2 Border VMs + 1 witness (Ubuntu 24.04 e2-standard-2 vs e2-medium), disks, static IPs, egress; confirm prices with `gcloud` pricing data, not memory

## Phase 2: Foundational code (blocks all stories)

- [ ] T005 Add the optional, default-off `listen` block (bind address/port separate from the signed advertised endpoint) to the private HA config: `mcp-servers/protocol-mcp/bgp/federation/ha/config.py`, `ha/factory.py` (iN2N attach listener), `ha/node.py` (cluster listener)
- [ ] T006 Accept the optional `listen` block in the role launcher's exact-field check: `scripts/lib/protected_role.py`
- [ ] T007 [P] Tests for T005/T006 (default-off identical behavior; listener binds the override; peers still dial the manifest address; malformed block refused): `tests/n2n/test_ha_bind_183.py`
- [ ] T008 [P] Policy generator and validator enforcing `contracts/sandbox-policy.md` (default deny, tcp peers with `tls: skip` and no L7 fields, Anthropic via provider injection, no metadata server, hard_requirement Landlock): `labs/ha/r09a_policy.py`
- [ ] T009 [P] Tests for the generator and its refusals: `tests/n2n/test_ha_sandbox_183.py`
- [ ] T010 [P] Node image build context generator (root-owned frozen source and Python 3.12 env, Node 24, pinned OpenClaw 2026.7.1-2, DefenseClaw 1.0.4 checksum-verified, `sandbox` user, private state dir owned by it): `labs/ha/r09a_image.py`
- [ ] T011 [P] DefenseClaw node sidecar tooling: config derived byte-for-byte from the qualified R04A Anthropic file, `mode: action`, `hook_fail_mode: closed`, audit path and export: `labs/ha/r09a_defenseclaw.py`
- [ ] T012 [P] VM bootstrap for Ubuntu 24.04 (Docker >= 28, OpenShell 0.1.7, DefenseClaw 1.0.4, `docker` group, linger, `OPENSHELL_COMPUTE_DRIVER=docker`, metadata-server iptables rule, etcd container): `scripts/ha-r09a-vm-bootstrap.sh`
- [ ] T013 Node deploy driver: build image, create `netclaw-node` sandbox with generated policy and provider, start host forwards (7443, 7444, 8443 with host 443 redirect), start sidecar; idempotent; label-owned: `scripts/ha-r09a-deploy.sh`
- [ ] T014 Posture endpoint `GET /api/hud/posture` in the R09 ingress (read-only, no secrets, components outside the sandbox listed with disposition): `labs/ha/hud_ingress_r09.mjs` and test `labs/ha/hud_ingress_r09.test.mjs`
- [ ] T015 [P] Negative isolation suite driver implementing the cases of FR-013 with expected refusal and record: `labs/ha/r09a_negative.py`

## Phase 3: User Story 1 - Components run inside OpenShell (P1)

**Test**: two Borders in one region sandboxed; posture shows each component; a real operation completes through each Border.

- [ ] T016 [US1] Deployment topology script for two Border VMs + one etcd witness in one region (own VPC, IAP-only SSH, label `netclaw-spec=183`, prefix `nc183-`): `scripts/ha-r09a-deploy.sh` (infra part)
- [ ] T017 [US1] Generate identities/manifest for two nodes with the R09 preparer (2 nodes, `admission_ms` 3000-4500 as measured), DNS names under `automateyournetwork.com`, lego certificates: reuse `labs/ha/r09_prepare.py`, `scripts/ha-dns-godaddy.py`
- [ ] T018 [US1] Experiment E3: start the Border role inside the sandbox with the bind override and forwards; record pass/fail in `contracts/disposition-table.md`
- [ ] T019 [US1] Experiment E4: HUD ingress and workspace backend inside the sandbox; public HTTPS via host redirect; record disposition
- [ ] T020 [US1] **G1**: present the line-item estimate (T004) and obtain owner confirmation before creating any billed resource
- [ ] T021 [US1] Deploy, bring up the two-Border cluster, verify leader election and a real operation through each Border (reuse `scripts/ha-r09-*.sh` verification drivers)
- [ ] T022 [US1] Fill the disposition table with evidence; for any component outside, record the reason (FR-019)

## Phase 4: User Story 2 - DefenseClaw guardrails (P1)

**Test**: violating prompt/tool call blocked and audited; guard stopped means no provider call; scanning refuses a bad component.

- [ ] T023 [US2] Provider credential via OpenShell provider mechanism for `api.anthropic.com` (no key inside the sandbox); verify the agent cannot read it
- [ ] T024 [US2] Route all chat/model traffic through the DefenseClaw guardrail proxy; verify one real chat turn end to end
- [ ] T025 [US2] In-band block tests with the guard capability token: policy-violating prompt and tool call refused with a reason and an audit record
- [ ] T026 [US2] Fail-closed test: stop the sidecar mid-turn; assert zero provider calls (independent counter from the guard/provider fence)
- [ ] T027 [US2] Component scanning flow: add a skill/MCP, assert scan-before-enable and refusal of a failing component

## Phase 5: User Story 3 - Isolation under attack (P1)

- [ ] T028 [US3] Run `labs/ha/r09a_negative.py` on a deployed node: out-of-policy file read/write, frozen-source modification, metadata-server access, unapproved egress, provider-credential read, member-to-member connection
- [ ] T029 [US3] Record each result with its audit/OCSF evidence reference in `specs/183-openshell-defenseclaw-gcp/verification.md`; any success fails the release (SC-003)

## Phase 6: User Story 4 - HA behavior survives confinement (P2)

- [ ] T030 [US4] Stopped-Border / leader-change test inside sandboxes; compare with R09 timings
- [ ] T031 [US4] Cut between the two Borders (7443) and healing; isolated Border reports `no_quorum`; compare with R09
- [ ] T032 [US4] Measure per-hop and end-to-end overhead against the signed window; record the setting that restores the window if exceeded
- [ ] T033 [US4] Restart a node and verify it rejoins with its original identity without reclaiming lost authority (FR-018)
- [ ] T034 [US4] Record the two-Border loss-of-majority limit and the witness voter role (FR-020)

## Phase 7: User Story 5 - Operability (P2)

- [ ] T035 [US5] VS Code command "NetClaw: Show Node Posture" reading `/api/hud/posture`, plus the G12 disposition and how a guard-blocked request is presented: `extensions/netclaw-vscode/src/...`, `extensions/netclaw-vscode/test/`
- [ ] T036 [US5] G13 disposition for Mobile (reasoned no-change or required change) in `verification.md`
- [ ] T037 [US5] Audit export per node (DefenseClaw SQLite + OCSF) and retention check
- [ ] T038 [US5] Start/stop/upgrade of one node without breaking identity or authority

## Phase 8: Polish and release gate

- [ ] T039 [P] Update `docs/DEFENSECLAW.md` and `docs/N2N-RISK.md` for the layered result and the per-component disposition (XI/XII)
- [ ] T040 [P] Update the roadmap brief `docs/roadmap/issue-310/briefs/R09A-gcp-openshell-defenseclaw.md` with the outcome
- [ ] T041 List every qualified-code change for owner review in the PR (FR-024); keep R09 carry-overs listed
- [ ] T042 Cost recorded against the estimate in `cost-model.md`
- [ ] T043 Evidence summary `specs/183-openshell-defenseclaw-gcp/verification.md`; memory and GAIT
- [ ] T044 Open the PR (stacked on #340 or retargeted after #340 merges); no publish/push-live without approval
- [ ] T045 Teardown only on the owner's request: exact resource list (label `netclaw-spec=183`, prefix `nc183-`), separate confirmation

## Dependencies and order

T005-T006 before T007; T008 before T009 and T013; T010-T012 before T013; T013-T015 before Phase 3 live steps; T018-T019 decide deeper placement vs the floor before T021; T020 (G1) before any billed resource; Phases 4-6 need T021; T029 and T043 gate release.

**Parallel**: T004, T007-T012, T015 can proceed together (different files). **MVP**: Phase 1-3 plus T023-T025 (sandboxed cluster + guarded chat) proves the core; Phases 5-7 complete the spec.
