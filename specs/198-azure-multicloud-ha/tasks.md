# Tasks: R10 Azure Multi-Cloud

**Input**: `specs/198-azure-multicloud-ha/` (spec, plan, research, data-model, contracts, quickstart)
**Current evidence**: [closure-20261124.md](closure-20261124.md). Actual live receipts determine completion. The owner authorized bounded qualification, all-cloud teardown, commit/push and merge after verified acceptance. The approved USD23.0075943167 envelope crosses the USD15 pause once; USD25 remains hard. Client publication is held. Historical phase-go markers document original sequencing.

## Phase 1: Setup (free)

- [x] T001 Create `scripts/ha-cloud.sh` dispatcher (provider arg, verb routing, `--dry-run`, error on unknown provider) per `contracts/cloud-driver.md`
- [x] T002 [P] Extract existing gcloud behavior into `scripts/ha-cloud-gcp.sh` (project netclaw-506315, zone map, IAP ssh/scp, labels) with no behavior change
- [x] T003 [P] Add `r10-*` and `~/.local/share/netclaw/r10-*` ignore patterns and `.env.example` entries (AZURE_SUBSCRIPTION_ID, R10_SSH_ALLOW_CIDR, descriptions only, no values)

## Phase 2: Foundational (free, blocks all stories)

- [x] T004 Implement `labs/ha/r10_ledger.py` (ledger file 0600, add/stop entries, $15 pause and $25 hard refusal, `approve-over-pause`) per `data-model.md`
- [x] T005 [P] Unit tests `labs/ha/test_r10_ledger.py` covering pause, hard cap, approval, stopped-entry accounting
- [x] T006 Implement Azure cloud-driver verbs, exact phase resource groups/tags, SSH key/CIDR controls and dry-run. Actual qualified image is Ubuntu24.04 amd64, D2as_v7, 8GiB/40GiB; the original Debian12 candidate was rejected.
- [x] T007 [P] Dry-run test `labs/ha/test_r10_driver.py` asserting exact `az`/`gcloud` command lines per verb and that no command embeds a secret
- [x] T008 R10 cloud-neutral deployment copies preserve the R09 deployment scripts. The shared member builder was changed for the fresh Linux MCP closure finding; the exact change and live proof are listed in closure.

## Phase 3: US1 Preflight and budget guard (P1) MVP, free

**Independent test**: preflight prints go/no-go for 3 regions and creates nothing.

- [x] T009 [US1] Implement `labs/ha/r10_preflight.py` (az account state, `az vm list-skus` size availability + restrictions, `az vm list-usage` quota, budget presence, secrets presence booleans, retail price lookup) per `contracts/preflight-report.md`
- [x] T010 [P] [US1] Unit tests `labs/ha/test_r10_preflight.py` using fixture `az` JSON (warned state, restricted size, low quota, all-go)
- [x] T011 [US1] Add `scripts/ha-r10-preflight.sh` wrapper and `scripts/ha-r10-phase.sh` (`up|status|down`, ledger-gated, tag-verified teardown)
- [x] T012 [US1] Run preflight against the real subscription (read-only); record result in `verification.md`. Blocked until `az account show` state is Enabled
- [x] T012b [US1] Add a `--probe` to `labs/ha/r10_preflight.py` that runs `az vm create --validate` per region/size (creates nothing) so SKU/region blocks surface in preflight; list-sizes is not sufficient
- [x] T013 [GO] [US1] Create the $25 budget alert (50% and 80%) on the subscription (free); record in verification.md

## Phase 4: US2 Azure Border + on-prem and cloud members (P2)

**Independent test**: one Azure Border live over trusted TLS; Mac subnet member and hosted NetBox member each complete a real operation.

- [x] T014 [US2] Superseded: full OpenShell/DefenseClaw requires Ubuntu24.04 amd64, Docker>=28 and Landlock ABI>=3. Adapt/verify the R09A full stack; Debian12 bootstrap is diagnostic only. **[satisfied: the full OpenShell/DefenseClaw stack on Ubuntu 24.04 ran live (verification.md 2026-11-15)]**
- [x] T015 [US2] `r09_prepare.py` already takes `--node code=internal,public` (cloud-neutral); deploy side covered by the `ha-r10-*` copies. Live preparation/deployment proven by the six-Border runs; fresh preparation required for changed source. NOTE: `ha-r09-vm-net-etcd.sh` public-IP alias/DNAT shim applies on Azure too (public IP is not on the NIC)
- [x] T016 [US2] Store the owner's current NetBox token in `~/.openclaw/.env` via `scripts/write-env.py` (stdin only, never echoed); verify against demo.netbox.dev
- [x] T017 [GO] [US2] Phase p2-single: `up` one Border (canadacentral), DNS A record, lego cert, deploy, place provider key (port `ha-r09-place-provider-key.sh` to driver), start Border + HUD **[done in run r10c: one full Azure Border; see verification.md]**
- [x] T018 [US2] Actual Mac subnet and physical GCP NetBox member operations completed from Azure ingress with signed results and durable ACKs. Physical witness: `32083482-191e-4c49-ad05-b7398d7389a4`.
- [x] T019 [GO] [US2] Teardown p2-single (group delete, DNS records, key shredded), verify empty by tag; append EvidenceRecord with measured cost **[done: r10c torn down and verified empty (handoff.md end-of-session update)]**

## Phase 5: US3 3-region HA (P3)

**Independent test**: operation completes through each of 3 Borders; leader-loss outcome recorded.

- [x] T020 [US3] Parameterize region/zone/etcd peer mapping (canadacentral, eastus2, swedencentral; timing must be measured for the actual topology) in prepare/deploy scripts; dry-run only
- [x] T021 [GO] [US3] Phase p3-ha: `up` three Borders in parallel, DNS, certs, etcd bootstrap, units, HUD (same order as `ha-r09-deploy-gen.sh`) **[done in run r10d (and again r10e): three sandboxed Borders as one HA group]**
- [x] T022 [US3] Actual local/cross-group operations completed through every Azure and GCP ingress: twelve baseline cells. Fault/unknown-producing guard tests ran last; no replay manufactured evidence.
- [x] T023 [US3] Historical Azure takeover plus actual November24 GCP Montreal→Belgium leader change and completed epoch70 operation. Explicit member-process restart and full-artifact availability limits are recorded in closure.
- [x] T024 [GO] [US3] Teardown p3-ha with verification; EvidenceRecord with cost; list any qualified-code changes for owner review **[done: r10d and r10e torn down and verified empty; qualified-code changes listed in handoff.md for owner review]**

## Phase 6: US4 GCP to Azure federation (P4) [GCP-GO]

**Independent test**: operation entered on one cloud completes through the other; both audits show it.

- [x] T025 [US4] Signed peer contract implemented, negative-tested and live-qualified; receiving authority and each member's single-group binding remain intact.
- [x] T026 [US4] Three distinct regions per cloud, six protected Borders and two separate three-voter HA groups were deployed and live-qualified.
- [x] T027 [US4] Both cross-group directions through every leader/follower completed; fourteen original result/ACK pairs independently verified. Twelve cells re-observed GET-only after takeover with unchanged counters.
- [x] T028 [US4] All seven final-run VMs, bound boot disks, IPs and exact firewalls removed; both clouds verified empty of qualification assets; four generations of A/ACME TXT DNS absent. Complete state exported first. See closure and private cleanup receipts.

## Phase 7: US5 Docs and release gate (P5, free)

- [x] T029 [P] [US5] Create `docs/NETCLAW-IN-AZURE.md` mirroring `docs/NETCLAW-IN-GCP.md` (preflight, budget guard, phases, teardown)
- [x] T030 [P] [US5] Add Azure sections/rows to `docs/COVERAGE-ROADMAP.md`, `docs/GETTING-STARTED-VSCODE.md`, `docs/CLAW-PLAN.md`, `docs/ASSISTANT-INSTALL.md`, `docs/N2N-RISK.md`, `docs/DEFENSECLAW.md` where GCP is listed
- [x] T031 [P] [US5] Update the spec 192/193 GCP completeness/setup surfaces with Azure counterparts (`specs/192-gcp-completeness-survey/survey.md`, `specs/193-gcp-docs-setup-refresh/verification.md` cross-links) **[done: Azure counterpart appended to specs/192 survey and cross-linked from specs/193 verification]**
- [x] T032 [US5] Update release-gate notes (`specs/179-border-ha-authority/*` references and this spec's verification.md): VS Code/mobile/HUD builds unpublished, owner approval required **[done: unchanged gate recorded in specs/179 acceptance.md and this spec verification.md; the unpublished local VS Code change is noted]**
- [x] T033 [US5] README/env/docs updated; required reconciliation command executed. Global optional installed MCP dependency/startup checks FAIL on unchanged baseline issues; catalog/docs/package/portability checks pass. Qualified isolated runtime and live proof pass. See closure for precise limits.

## Phase 8: Polish

- [x] T034 Posted Azure CAD6.8605695141 and GCP CAD3.06 gross/CAD0 net reconciled with indicative FX and delayed billing. Final conservative held ledger USD19.589, zero open entries/burn; all historical and new reserves retained below USD25. Final invoice posting remains explicitly pending.
- [x] T035 (drafted at specs/198-azure-multicloud-ha/wordpress-draft.md; NOT published, owner review only) Draft WordPress milestone post for owner review only (constitution XVII), never publish
- [x] T036 Both cloud inventories verify zero Spec198 resources; export hashes verified and finite watchdogs unloaded. Owner explicitly authorized PR/merge after actual acceptance and cleanup; integration receipt follows in closure.

## Resumed acceptance explicitly tracked (2026-11-24)

- [x] T037 Measured stable-network admission/quorum latency and nearest-Border behavior; smallest justified signed-window/RPC-wait repair passed controlled tests and a fresh signed live deployment. No region or guarantee removed.
- [x] T038 Actual different GCP leader at epoch70 while original leader paused; new operation `e155c521-0efc-4e42-99c3-579d3ee64451` completed with durable ACK; unknowns retained.
- [x] T039 All six actual HUDs rendered; real HUD and native VS Code remote review/approval/reconciliation and cold GET-only recovery passed with no repeated effects.
- [x] T040 Actual guard worker/supervisor absent, both ports connection-refused; request failed closed HTTP408 in0.307s with no fallback. Earlier suspended-guard unknown remains reserved.

## Dependencies

Phase 1 -> 2 -> US1 -> US2 -> US3 -> US4; US5 can start after Phase 2 for docs that do not need evidence, and finishes last. T012/T013 need an Enabled subscription. Parallel: T002/T003, T005/T007/T010, T029/T030/T031.

## Strategy

Implemented in bounded phases under the recorded owner delegation; final acceptance uses actual receipts and verified cleanup, not checklist totals.
