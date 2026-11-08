# Tasks: Multi-Region HA Borders (R09)

**Input**: `specs/182-multi-region-ha-borders/` (spec, plan, research, data-model, contracts, quickstart, cost-model)
**Branch**: `182-multi-region-ha-borders`
**Tests**: included where the spec demands evidence (FR-010..FR-014, FR-027). Use `python3.10` for pytest.

**Owner deliverables (definition of done for this effort)**
1. Three Border-served HUD links with the HUD updates (built from this branch; NOT a published release).
2. Three DNS-named Border URLs that paste into VS Code.
3. A live test with the local pyATS and CML, both up and reachable from the owner's machine, attached outbound, plus the cloud NetBox member (`demo.netbox.dev`).

**Hard rules for every task**: nothing billed before gate G1; nothing published/pushed live/announced (VS Code, Mobile, HUD) without a recorded owner approval; never reset an `unknown` budget slot; never read exit codes through pipes (`cmd >/dev/null 2>&1; echo $?`); remove only resources labelled `netclaw-spec=182` (Docker: `netclaw.spec=182`); never touch equinix-*, pyats-mcp, gateway5, drawio-mcp or the old VM/IPs/rules; secrets only in `~/.openclaw/.env`, never in the repo; Linux CI differs from macOS.

Format: `- [ ] T### [P?] [US?] description with file path`. `[P]` = parallelizable. **(OWNER)** = needs the owner.

---

## Phase 1: Setup (offline, no cloud)

- [ ] T001 Commit specs/182-multi-region-ha-borders and `.specify/feature.json` on branch `182-multi-region-ha-borders` (after owner OK to commit; no push)
- [ ] T002 [P] Create `tests/n2n/test_ha_multiregion_182.py` skeleton and confirm it runs under `python3.10 -m pytest`
- [ ] T003 [P] Create `scripts/ha-rtt-estimate.py` printing the estimated RTT table (research D2) and the admission budget `N x RTT`, marked `source=estimate`
- [ ] T004 [P] Inventory read-only the current GCP state to `specs/182-multi-region-ha-borders/inventory-before.md` (old VM, 2 IPs, firewall rules, quotas for e2-medium in the 3 regions) using `gcloud ... list/describe` only
- [ ] T005 [P] Check local prerequisites and record in `specs/182-multi-region-ha-borders/inventory-before.md`: gcloud auth, docker, node, python3.10, flutter, `lego` presence (install `lego` locally only if the owner agrees)

## Phase 2: Foundational (blocks all stories)

### 2a. Cost, ownership and cloud script (no billing until G1)

- [ ] T006 Write `scripts/ha-gcp-multiregion.py` with `plan` (read-only describe, prints creates), `apply` (idempotent describe-before-create, refuses without `--confirm-cost` and an `owner_confirmed_at` record), `status` and `teardown --list` (label `netclaw-spec=182`; deletion needs a second explicit flag). All resources named `nc182-*` with label `netclaw-spec=182`
- [ ] T007 [P] Write `scripts/ha-cost-estimate.py` reading the plan from T006, printing line items and failing (exit 1) above $300 (tests in `tests/n2n/test_ha_multiregion_182.py`)
- [ ] T008 [P] Add a billing budget alert (50/80/100% of $300) step to `scripts/ha-gcp-multiregion.py` (`gcloud billing budgets`), plan-only until G1
- [ ] T009 Define the network plan in `scripts/ha-gcp-multiregion.py`: VPC `nc182-r09`, 3 regional subnets plus one NetBox/member subnet if needed, static IPv4 per Border, firewall: Border-to-Border cluster/etcd/NCFED only between the 3 /32s, public 443 and the iN2N port, IAP ssh only, no 0.0.0.0/0 ssh/rdp (FR-022)
- [ ] T010 [P] Test: plan output has exactly 3 Borders in the 3 regions, every resource labelled, no world-open ssh/rdp, estimate <= $300 (`tests/n2n/test_ha_multiregion_182.py`)

### 2b. DNS and certificates (GoDaddy, automateyournetwork.com)

- [ ] T011 Write `scripts/ha-dns-godaddy.py` with `plan` (GET only; verifies the zone, lists existing records, computes `<code>-<id6>.automateyournetwork.com` names) and `apply --apply` (A records, TTL 600, refuses existing names with another target or non-matching patterns; never prints the token) per `contracts/dns-naming.md`
- [ ] T012 [P] Test the name generator and refusal rules offline with a stub HTTP server (`tests/n2n/test_ha_multiregion_182.py`)
- [ ] T013 (OWNER) Provide the GoDaddy Personal Access Token in `~/.openclaw/.env` as `GODADDY_PAT` plus `N2N_ACME_DNS_PROVIDER` and `N2N_CLAW_DOMAIN` (not pasted into chat); then run `scripts/ha-dns-godaddy.py plan` and record the result
- [ ] T014 [P] Document the certificate path (lego DNS-01 via `scripts/lib/godaddy-acme-hook.sh`, spec 060 quickstart B.1) for each Border in `specs/182-multi-region-ha-borders/quickstart.md`

### 2c. Hosted foundation-model transport (no Ollama on Borders)

- [ ] T015 Write a design note `specs/182-multi-region-ha-borders/model-transport.md`: how a Sonnet 5.5 (`claude-sonnet-5-5`) transport preserves DefenseClaw guard inspection, admission freshness, the independent model-request counter and `no result fabricated on uncertainty`, replacing `docker-exec://` and `127.0.0.1:11434` assumptions in `mcp-servers/protocol-mcp/bgp/federation/ha/model_transport.py`
- [ ] T016 Read `mcp-servers/protocol-mcp/bgp/federation/ha/{model_transport,config,factory,effect}.py` and `tests/n2n/test_ha_model_transport_179.py` and record the exact coupling points (Ollama executor fields) in `model-transport.md`
- [ ] T017 [P] Add failing tests for the hosted transport (guard in path, API key never logged or stored in the manifest, request counted independently, timeout leaves the operation `unknown` not retried) in `tests/n2n/test_ha_model_transport_182.py`
- [ ] T018 Implement the hosted-model transport as a new module `mcp-servers/protocol-mcp/bgp/federation/ha/hosted_model_transport.py`, selected by config, leaving the Ollama path unchanged (Constitution XV)
- [ ] T019 Wire the transport into `mcp-servers/protocol-mcp/bgp/federation/ha/factory.py` behind an explicit setting; add egress-to-API requirement and the key variable name to `.env.example`
- [ ] T020 [P] Run the HA contract and transport suites on python3.10 and the Linux contract env (`tests/n2n/test_ha_contract_179.py`, `tests/n2n/test_ha_model_transport_179.py`, new 182 tests) and record results in `specs/182-multi-region-ha-borders/verification.md`
- [ ] T021 (OWNER) Provide the Anthropic API key location (`~/.openclaw/.env` as `ANTHROPIC_API_KEY`) and confirm whether API spend has its own monthly cap (Q-model-budget)

### 2d. Client and HUD region display (offline)

- [ ] T022 [P] Implement the region-label parser per `contracts/region-display.md` in `ui/netclaw-visual/src/shared/cluster-binding.js` (display only; no trust change) with a unit test beside the existing HUD tests
- [ ] T023 [P] Implement the same parser in `extensions/netclaw-vscode/src/client/cluster.ts` with a unit test
- [ ] T024 [P] Implement the same parser in `mobile/netclaw-mobile/lib/ncfed/endpoint_recovery.dart` with a Dart test
- [ ] T025 Verify no signed-manifest validator changed (diff `config.py`, `cluster-binding.js`, `cluster_trust.dart`, extension validator) and record in `verification.md`

**Checkpoint**: source, scripts and tests ready; nothing billed.

---

## Phase 3: User Story 5 - Cost-bounded, owned, reversible environment (P1)

**Goal**: estimate under $300 confirmed, resources labelled, reversible.
**Independent test**: review the estimate and plan without any billed resource; later check labels.

- [ ] T026 [US5] Run `scripts/ha-gcp-multiregion.py plan` and `scripts/ha-cost-estimate.py`; write the line-item table with the billing-catalog prices (replace estimates) to `specs/182-multi-region-ha-borders/cost-model.md`
- [ ] T027 [US5] (OWNER) **Gate G1**: owner confirms the line-item estimate, the GoDaddy token (T013), the API key (T021) and quota readiness; record `owner_confirmed_at` in `specs/182-multi-region-ha-borders/g1-approval.md`
- [ ] T028 [US5] After G1: `scripts/ha-gcp-multiregion.py apply` creates network, firewall, static IPs, 3 Border VMs (e2-medium) and the budget alert; verify every resource carries `netclaw-spec=182` and save `status` output to `specs/182-multi-region-ha-borders/inventory-after.md`
- [ ] T029 [US5] Verify no 0.0.0.0/0 ssh/rdp rule exists in the new VPC and that the old VM/IPs/rules are byte-for-byte unchanged versus `inventory-before.md` (FR-023)

## Phase 4: User Story 1 - Three Borders by DNS name, VS Code + HUD links (P1) MVP

**Goal**: three live URLs, three HUD links, VS Code screenshot.
**Independent test**: add all three names in VS Code and see three connected Borders with distinct regions.

- [ ] T030 [US1] `scripts/ha-dns-godaddy.py apply --apply`: create the three A records pointing at the Border static IPs; verify with `dig` (no pipe-read exit codes)
- [ ] T031 [US1] Issue a lego DNS-01 certificate per Border name (GoDaddy hook); verify chain and expiry; store private keys `0600` on each VM only
- [ ] T032 [US1] Package the branch source as a tarball and copy to each VM via IAP `gcloud compute scp` (no git push needed); install Docker/Node/Python deps per Border
- [ ] T033 [US1] Measure real inter-region RTT between all Border pairs (p50/p95 over 5 min) with a read-only probe; write `specs/182-multi-region-ha-borders/measurements.md` (`source=measured`); update `scripts/ha-rtt-estimate.py` output
- [ ] T034 [US1] Decide leader placement and `admission_ms` from T033 (NA or EU leader; manifest bound 100-10000), record the justification; if measurements do not fit even at 10000 ms, STOP and bring the owner options (FR-010)
- [ ] T035 [US1] Generate the cluster identity and signed manifest for generation 1 with the three DNS names (offline anchor), per `docs`/`scripts/ha-cluster.py --help`; keep the anchor off the VMs
- [ ] T036 [US1] Bootstrap the 3-voter etcd across regions and start each Border with its identity, key, TLS and hosted-model transport; verify `scripts/ha-cluster.py status` from each Border shows one authority and quorum
- [ ] T037 [US1] Move the etcd leader to the chosen region (`etcdctl move-leader`) and confirm stability for 10 minutes
- [ ] T038 [P] [US1] HUD update: show per-Border region label, role (leader/follower/no_quorum) and failover notice in `ui/netclaw-visual/src` using T022's parser; `npm test` and `vite build` for the branch
- [ ] T039 [US1] Deploy the built HUD to each Border (HUD served by the Border over its DNS name; extend ingress lifetime with `NETCLAW_INGRESS_LIFETIME_S` for the demo) and confirm all three HUD URLs load over verified TLS
- [ ] T040 [P] [US1] VS Code: show region, role, and failover state for added Borders in `extensions/netclaw-vscode/src` (using T023); `npm test`, typecheck and build a local `.vsix` (NOT published)
- [ ] T041 [US1] Install the local `.vsix` in the owner's VS Code (owner OK) and verify add-by-DNS for all three names; refuse test: add a name not in the signed manifest and confirm refusal with the reason
- [ ] T042 [US1] **Deliverable A+B**: report to the owner the 3 HUD links and the 3 VS Code-pasteable URLs (`https://<code>-<id6>.automateyournetwork.com`) with the cluster identity fingerprint to compare
- [ ] T043 [US1] (OWNER) **Gate G2**: owner adds the three Borders in VS Code and captures the screenshot; record in `specs/182-multi-region-ha-borders/g2-screenshot.md`. The old environment stays untouched

## Phase 5: User Story 3 - Members: NetBox cloud, local pyATS and CML (P2)

**Goal**: all members attached outbound; live test.
**Independent test**: each member enrolled and visible through all three Borders; drop a Border and work still reaches the member.

- [ ] T044 [US3] Read-only discovery of the owner's local pyATS and CML (are they up, reachable from this Mac, versions, endpoints), recorded in `specs/182-multi-region-ha-borders/members.md`; do not touch `pyats-mcp` or other listed containers
- [ ] T045 [US3] (OWNER) Provide CML URL/credentials and pyATS testbed access location in `~/.openclaw/.env` if not already present; confirm both are up and reachable
- [ ] T046 [US3] Configure the NetBox cloud member against `https://demo.netbox.dev` using `NETBOX_URL`/`NETBOX_TOKEN` from `~/.openclaw/.env`; read-only status call first, then enroll as an outbound iN2N member to all three Borders
- [ ] T047 [US3] Enroll the local CML member outbound to all three Borders (no inbound port opened on this Mac or the network); verify no listening role and no consensus credentials on the member (FR-008)
- [ ] T048 [US3] Enroll the local pyATS member outbound the same way; same verification
- [ ] T049 [US3] Live test 1: from each Border HUD/agent run a read-only action on each member (NetBox site list, CML lab list, pyATS `show version` on a lab device) and record the GAIT references
- [ ] T050 [US3] Live test 2 (cross-system): a read-only workflow that reads NetBox, checks CML, and runs a pyATS observation, completed through a non-leader Border (forwarded over NCFED)
- [ ] T051 [US3] Live test 3: stop one Border (owned process only); repeat T049 through a survivor and confirm the members stay attached to the other two; restart the Border and confirm it rejoins without replaying earlier work
- [ ] T052 [US3] **Deliverable C**: report the live test transcript summary and evidence paths to the owner

## Phase 6: User Story 2 - Authority survives loss of a region (P1)

**Goal**: real WAN faults prove refusal and continuity.
**Independent test**: isolate one region at the network level; majority continues, isolated Border refuses, no double effect.

- [ ] T053 [US2] Write `labs/ha/real_wan_faults.py` with `cut`/`heal` using GCP firewall deny rules between exact Border /32s per port class (etcd, cluster/NCFED, public), every rule labelled `netclaw-spec=182` and always removed on heal/exit
- [ ] T054 [P] [US2] Add chrony fault helpers (`makestep` forward/backward offset, NTP off skew, SIGSTOP/SIGCONT suspend of owned process groups) in `labs/ha/real_wan_faults.py`
- [ ] T055 [P] [US2] Tests with a dry-run backend for the fault driver (rule generation, heal-always, label enforcement) in `tests/n2n/test_ha_multiregion_182.py`
- [ ] T056 [US2] Positive baseline first: a protected NetBox-effect operation through the authority with an independent effect count in the NetBox change log (no negatives before positives; unknown-producing rows last)
- [ ] T057 [US2] One-region loss (etcd-path and NCFED cut of the authority's region): majority elects, work resumes within `admission_ms`; approval through the isolated Border refused; NetBox change log shows exactly-once effects
- [ ] T058 [US2] Asymmetric partition (both directed cuts): majority side performs distinct work exactly once
- [ ] T059 [US2] Border-to-Border NCFED channel cut with etcd path intact (closes R08 limit 1b): observe refusal/forwarding behaviour and record
- [ ] T060 [US2] Clock rows: forward step, backward step and suspend; record refusal codes and recovery
- [ ] T061 [US2] Rejoin after heal: no replay of earlier work (FR-006)
- [ ] T062 [US2] Three-way partition last among positives: all Borders refuse; zero added tool calls and zero added model requests
- [ ] T063 [US2] Unknown-producing scenarios, each in its own fresh run and last: reply drop after commit; lost result/ACK; stale leader. Never reset an `unknown` slot; export evidence before any cleanup

## Phase 7: User Story 6 - Honest evidence against R08 limits (P3)

- [ ] T064 [US6] Run fenced restore Phase 2 on a new generation (additional labelled VM in an existing region, new DNS name) per `labs/ha/real_restore.py` / `REAL-FENCED-RESTORE.md`, or record "not claimed" with the reason in `specs/182-multi-region-ha-borders/evidence-matrix.md`
- [ ] T065 [US6] Build `specs/182-multi-region-ha-borders/evidence-matrix.md`: for each of the 13 R08 limits, new evidence or an explicit "still not claimed"
- [ ] T066 [US6] Record hosted-model evidence separately (independent request counter vs guard ingress log) since R08 Ollama evidence does not transfer

## Phase 8: User Story 4 - Client builds and the release gate (P2)

**Goal**: multi-region-ready clients, built and held for approval.
**Independent test**: builds exist; no outward action without a recorded approval.

- [ ] T067 [P] [US4] VS Code: multi-endpoint failover UX (move among signed endpoints, show failover; stale review stays stale, no auto-renew/resend) with tests in `extensions/netclaw-vscode`; bump `package.json` version (owner decides number); build `.vsix` only
- [ ] T068 [P] [US4] Mobile: enrollment against a 3-endpoint descriptor, `select-node` across regions, cold/background recovery with WAN-tuned timeouts in `mobile/netclaw-mobile/lib/ncfed`; Flutter tests; bump version; build only (no TestFlight)
- [ ] T069 [P] [US4] HUD/Border: confirm every Border serves the fixed mobile enrollment route (`/api/hud/mobile/enrollment`) and bump the source version (owner decides; main is 1.20.0)
- [ ] T070 [US4] Re-run the HUD, VS Code and iOS journeys of `specs/179-border-ha-authority/evidence-matrix.md` against the local multi-region topology using the new builds and record results
- [ ] T071 [US4] (OWNER) **Release gate**: per client, owner approves or declines publish/push live/announce; record each in `specs/182-multi-region-ha-borders/release-approvals.md`. Do not publish without a record
- [ ] T072 [US4] After approved publication: re-run the three journeys against the PUBLISHED builds on the multi-region topology and record the installed version against source (FR-020)

## Phase 9: Polish and closure

- [ ] T073 [P] Docs: multi-region deployment and operator runbook under `docs/` (do NOT describe multi-region HA as available to end users before T072; FR-029); update `README.md` counts only if an integration was added (`python3 scripts/reconcile-mcp.py`)
- [ ] T074 [P] Draft the maintainer note (not sent): spec-number collision with `specs/179-convergence-setup` and un-bumped versions (main 1.20.0) in `specs/182-multi-region-ha-borders/maintainer-note.md`
- [ ] T075 Write `specs/182-multi-region-ha-borders/verification.md` (suite results on macOS and Linux, python3.10) and `acceptance.md` with limits
- [ ] T076 GAIT session summary commit and memory update (spec 182 status, decisions, open gates)
- [ ] T077 (OWNER) Teardown only when asked: `scripts/ha-gcp-multiregion.py teardown --list` shows the exact resources; owner confirms separately; old VM/IPs/rules handled only on the owner's explicit list; export evidence first

---

## Dependencies and order

- Phase 1 -> Phase 2 (2a-2d parallel except T018->T019, T015/T016->T017->T018) -> **G1 (T027)** -> T028-T029.
- US1 (Phase 4) needs T028, T013, T018/T019, T022-T024. T033/T034 precede T035/T036.
- US3 (Phase 5) needs US1 Borders running. US2 (Phase 6) needs US1 and at least NetBox from US3 (T046) for the independent effect count.
- US6 (Phase 7) follows US2. US4 build tasks (T067-T069) can run in parallel from Phase 2 onward; T070 needs US1; T071/T072 need owner approval and are last.
- Gates: G1 (T027) before any billed resource; G2 (T043) before any teardown request; release gate (T071) before any publish.

## Parallel examples

- T002/T003/T004/T005 together; T007/T008/T010/T012 together; T022/T023/T024 together; T038 and T040 together; T067/T068/T069 together.

## Strategy

MVP = Phases 1-2, G1, then US5 and US1 to deliver the three HUD links and three VS Code URLs. Then US3 (live pyATS/CML/NetBox test), US2 and US6 for evidence, US4 for the release gate. Stop at every OWNER task.
