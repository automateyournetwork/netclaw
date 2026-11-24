# Tasks: R10 Azure Multi-Cloud

**Input**: `specs/198-azure-multicloud-ha/` (spec, plan, research, data-model, contracts, quickstart)
**Resumed by owner on 2026-11-24** from `ca64f507`. Current scope, evidence and the renewed USD15 pause are in `resume-20261124.md`. Historical stops below are superseded by this resume, not by checkbox counts. No new paid run has begun.

**Execution authorization before this pause**: See `activation-delegation.md`. Azure region substitutions and Azure phases are authorized; owner explicitly added the three-Border GCP mesh after Azure qualification. Retain USD15/USD25 gates and publication holds.

**Historical gates (superseded within the delegation above)**: tasks marked **[GO]** create billable resources and MUST NOT run until the owner says go for that phase. **[GCP-GO]** needs the separate GCP go. Never print secret values. Nothing is published or pushed without owner approval.

## Phase 1: Setup (free)

- [x] T001 Create `scripts/ha-cloud.sh` dispatcher (provider arg, verb routing, `--dry-run`, error on unknown provider) per `contracts/cloud-driver.md`
- [x] T002 [P] Extract existing gcloud behavior into `scripts/ha-cloud-gcp.sh` (project netclaw-506315, zone map, IAP ssh/scp, labels) with no behavior change
- [x] T003 [P] Add `r10-*` and `~/.local/share/netclaw/r10-*` ignore patterns and `.env.example` entries (AZURE_SUBSCRIPTION_ID, R10_SSH_ALLOW_CIDR, descriptions only, no values)

## Phase 2: Foundational (free, blocks all stories)

- [x] T004 Implement `labs/ha/r10_ledger.py` (ledger file 0600, add/stop entries, $15 pause and $25 hard refusal, `approve-over-pause`) per `data-model.md`
- [x] T005 [P] Unit tests `labs/ha/test_r10_ledger.py` covering pause, hard cap, approval, stopped-entry accounting
- [x] T006 Implement `scripts/ha-cloud-azure.sh` verbs `up/ssh/scp/ip/stop/start/down/list` (resource group per phase, tags `netclaw-spec=198 phase=<id>`, VNet+NSG+static IP+NIC+VM per region, Debian 12, SSH key only, SSH allowed from `R10_SSH_ALLOW_CIDR` only) with `--dry-run`
- [x] T007 [P] Dry-run test `labs/ha/test_r10_driver.py` asserting exact `az`/`gcloud` command lines per verb and that no command embeds a secret
- [x] T008 DECISION: R09 scripts left untouched (qualified); cloud-neutral copies `scripts/ha-r10-deploy-gen.sh`, `ha-r10-push.sh`, `ha-r10-place-provider-key.sh`, `ha-r10-remove-provider-key.sh` route through the driver; GCP driver parity proven by `labs/ha/test_r10_driver.py`

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
- [ ] T018 [GO] [US2] Enroll Mac subnet-calculator member (`r09_member.py` subnet flavor) and hosted NetBox member; run one operation each; capture workspace + audit evidence **[PARTIAL: hosted-Sonnet NetBox and Mac subnet execution have live ACK evidence. Prior members ran on the Mac; physical CLOUD placement of the NetBox member is still unproven. See resumed acceptance.]**
- [x] T019 [GO] [US2] Teardown p2-single (group delete, DNS records, key shredded), verify empty by tag; append EvidenceRecord with measured cost **[done: r10c torn down and verified empty (handoff.md end-of-session update)]**

## Phase 5: US3 3-region HA (P3)

**Independent test**: operation completes through each of 3 Borders; leader-loss outcome recorded.

- [x] T020 [US3] Parameterize region/zone/etcd peer mapping (canadacentral, eastus2, swedencentral; timing must be measured for the actual topology) in prepare/deploy scripts; dry-run only
- [x] T021 [GO] [US3] Phase p3-ha: `up` three Borders in parallel, DNS, certs, etcd bootstrap, units, HUD (same order as `ha-r09-deploy-gen.sh`) **[done in run r10d (and again r10e): three sandboxed Borders as one HA group]**
- [x] T022 [GO] [US3] Attach members; run real operations through each Border; run unknown-producing and degraded-quorum tests LAST **[done: operations through all three Azure Borders and all six Borders (r10e/r10f); degraded-quorum cases recorded last]**
- [x] T023 [GO] [US3] Leader-loss takeover test; record outcome and any limitation (known: degraded 2-of-3 far-region quorum cannot admit) **[done: Azure leader loss epoch 15 to 41 with a completed operation; GCP far-region refusal recorded as a limit]**
- [x] T024 [GO] [US3] Teardown p3-ha with verification; EvidenceRecord with cost; list any qualified-code changes for owner review **[done: r10d and r10e torn down and verified empty; qualified-code changes listed in handoff.md for owner review]**

## Phase 6: US4 GCP to Azure federation (P4) [GCP-GO]

**Independent test**: operation entered on one cloud completes through the other; both audits show it.

- [x] T025 [US4] Write `specs/198-azure-multicloud-ha/contracts/cross-cloud-federation.md` (peer enrollment, pinned keys, which operation crosses, expected audit rows) reusing features 052-066/189/190 **[DONE as a design/source task: signed peer relay contract implemented and negative-tested; partial live evidence below. Human/live acceptance remains T027, not inferred here.]**
- [x] T026 [GCP-GO] [US4] Stand up three small GCP Borders in distinct regions (driver `gcp`, label spec 198), form their HA group, and connect it to the retained three-Border Azure HA group (six total) **[DONE: r10k/r10l had both groups, six functioning union catalogs and signed relays; successful execution acceptance remains T027.]**
- [ ] T027 (PARTIAL: union catalog + relay + one completed cross-cloud op live; Azure->GCP completed op and all-follower ingress not shown; see verification.md 2026-11-16) [GCP-GO] [US4] Federate the two HA groups; prove all six ingresses, GCP-to-Azure and Azure-to-GCP operations, capture both authority/audit trails and no-replay recovery evidence **[OPEN: GCP-to-Azure subnet success exists; Azure-to-GCP success and all-follower execution remain unproven. Latest stable-network r10k/r10l finding is authoritative.]**
- [ ] T028 [GCP-GO] [US4] Teardown both clouds, delete DNS records, verify empty on both; EvidenceRecord with cost **[PARTIAL: historical runs retired and fresh November24 inventory is empty; export and verified retirement of the resumed final run remain required.]**

## Phase 7: US5 Docs and release gate (P5, free)

- [x] T029 [P] [US5] Create `docs/NETCLAW-IN-AZURE.md` mirroring `docs/NETCLAW-IN-GCP.md` (preflight, budget guard, phases, teardown)
- [x] T030 [P] [US5] Add Azure sections/rows to `docs/COVERAGE-ROADMAP.md`, `docs/GETTING-STARTED-VSCODE.md`, `docs/CLAW-PLAN.md`, `docs/ASSISTANT-INSTALL.md`, `docs/N2N-RISK.md`, `docs/DEFENSECLAW.md` where GCP is listed
- [x] T031 [P] [US5] Update the spec 192/193 GCP completeness/setup surfaces with Azure counterparts (`specs/192-gcp-completeness-survey/survey.md`, `specs/193-gcp-docs-setup-refresh/verification.md` cross-links) **[done: Azure counterpart appended to specs/192 survey and cross-linked from specs/193 verification]**
- [x] T032 [US5] Update release-gate notes (`specs/179-border-ha-authority/*` references and this spec's verification.md): VS Code/mobile/HUD builds unpublished, owner approval required **[done: unchanged gate recorded in specs/179 acceptance.md and this spec verification.md; the unpublished local VS Code change is noted]**
- [x] T033 [US5] Update README.md and `.env.example`, run `python3 scripts/reconcile-mcp.py` (exit code not through a pipe) and doc inventory checks **[done: README Azure section, .env.example names, install.sh read-only Azure step, docs; reconcile-mcp and parity tests run, see verification.md]**

## Phase 8: Polish

- [ ] T034 (PARTIAL: November24 Azure Cost Management returns CAD6.8605695141; GCP actual costs, currency reconciliation and final-run costs remain open) Final spend reconciliation from the Azure billing view vs ledger; record in verification.md (SC-001)
- [x] T035 (drafted at specs/198-azure-multicloud-ha/wordpress-draft.md; NOT published, owner review only) Draft WordPress milestone post for owner review only (constitution XVII), never publish
- [ ] T036 (zero owned resources freshly confirmed 2026-11-24; repeat after resumed qualification; PR/merge authorized after actual acceptance and verified cleanup) Confirm GCP project and Azure subscription show zero spec-198 resources; open PR only on owner approval

## Resumed acceptance explicitly tracked (2026-11-24)

- [ ] T037 Diagnose r10k/r10l admission and validate the smallest repair in a fresh signed LIVE deployment. **[PARTIAL: source-matched nearest selection; controlled latency reproduction and126tests pass; fresh signed live GCP and Azure-to-GCP admission succeeded with durable ACK; full matrix and leader change remain pending.]**
- [ ] T038 Complete a GCP operation with durable ACK after stopping the observed GCP leader and confirming a different leader/increased epoch; retain original unknowns.
- [ ] T039 Prove actual HUD rendering and native VS Code discovery/review/approval/reconciliation, including a remote operation and GET-only recovery without repeated effects.
- [ ] T040 Obtain an actual stopped/unavailable-guard fail-closed witness; prior automatic sidecar restart made that test inconclusive.

## Dependencies

Phase 1 -> 2 -> US1 -> US2 -> US3 -> US4; US5 can start after Phase 2 for docs that do not need evidence, and finishes last. T012/T013 need an Enabled subscription. Parallel: T002/T003, T005/T007/T010, T029/T030/T031.

## Strategy

Free work first (T001-T011, T014-T016, T020, T025, T029-T031) can be completed now. MVP = US1 preflight. Each [GO] phase starts only on an owner go, ends with teardown and evidence before the next begins.
