# Verification: R10 Azure (spec 198)

Honest record. A phase is only "passed" when a live entry below says so.

## 2026-11-14 free work (no cloud resources created)

- Driver: `scripts/ha-cloud.sh` + `ha-cloud-{azure,gcp}.sh`; verbs up/ssh/scp/get/ip/peer/stop/start/down/list, all with `--dry-run`.
- Ledger: `labs/ha/r10_ledger.py` ($15 pause, $25 ceiling that approval cannot lift).
- Preflight: `labs/ha/r10_preflight.py` (read-only, secrets as booleans only).
- Phase runner: `scripts/ha-r10-phase.sh` refuses `up` without `R10_GO=<phase>` (exit 4).
- Tests: `python3 labs/ha/test_r10_ledger.py`, `test_r10_preflight.py`, `test_r10_driver.py`: all pass (16 tests).
- Finding: R09 etcd peers use private addresses routed by GCP's global VPC; Azure needs global VNet peering, added to `phase up` for multi-node phases (research R4 updated).
- Finding: `~/.openclaw/.env` currently has no `ANTHROPIC_API_KEY` (preflight reports presence only); the key must be supplied via an env file at the key-placement step.
- Not done / not proven: no live Azure resource exists; subscription state was `Warned` at last check and the CLI session was cleared (owner must `az login`).
- No qualified code was modified; R09 scripts are untouched.

## 2026-11-14 live read-only and free steps (still no billable resource)

- Subscription "Azure subscription 1" is **Enabled** (after the owner's `az login`).
- Finding: a new subscription has Compute/Network/Storage **NotRegistered**; all queries returned empty until registered. Registered the three providers (free, no resources).
- Finding: `az vm list-skus` takes ~100 s per call and returned empty on the fresh subscription; preflight now uses `az vm list-sizes` (instant) + `az vm list-usage`. Restriction detail is therefore not checked; real capacity is confirmed at `up`.
- Preflight (T012): **GO** in canadacentral, westeurope, southeastasia; Standard_B2s; 10 regional vCPUs and 10 B-family vCPUs free each (5 VMs per region); 24 s run.
- Budget alert (T013): `nc198-25usd`, $25 monthly, email at 50% and 80% of actual spend. Warns only; the ledger is the enforcement.
- NetBox token (T016): current token stored in `~/.openclaw/.env` (0600) and verified against demo.netbox.dev (HTTP 200).
- Owner SSH key for the lab: `~/.ssh/nc198_azure` (ed25519, no passphrase, local only) via `AZ_SSH_KEY`.

## 2026-11-14 p2-single attempt: BLOCKED at VM creation (torn down, est. cost $0.004)

- `ha-r10-phase.sh up p2-single nne1` created the resource group, VNet, NSG and static IP, then `az vm create` failed (the CLI crashed while printing the error; real cause found with `--validate`).
- `az vm create --validate` (creates nothing) across 18 regions and 10 sizes: `Standard_B2s`, `A2_v2`, `F2s_v2`, `D2as_v4`, `D2s_v3`, `D2als_v6` all **SkuNotAvailable (capacity restrictions)**; `B2ls_v2`/`D2ls_v5` **QuotaExceeded** (no quota in those families); **westeurope: "not accepting new customers"** (RequestDisallowedByAzure, aka.ms/locationineligible).
- Conclusion: this brand-new subscription cannot create any VM yet. `az vm list-sizes`/`list-usage` look healthy and mislead; only `--validate` shows the truth. Preflight must include a validate probe (task T012b).
- Teardown done: group deleted, tagged-resource list empty, ledger burn $0.
- Needs owner action: an Azure support request (free) for SKU/region access, or waiting for the new subscription to be released.

## Pending live phases

| Phase | Status |
|-------|--------|
| T012 preflight on real subscription | passed (GO, 3 regions) |
| p2-single | blocked: Azure refuses VM creation on this subscription (see above) |
| p3-ha | not started (needs owner go) |
| p4-mesh (GCP) | not started (needs separate owner go) |

## 2026-11-14 independent VM-blocker diagnosis: alternate size validates

This supersedes the earlier conclusion that the subscription cannot create any VM.
It also supersedes T012's apparent availability GO; catalog presence and quota were
insufficient checks. No deployment or live phase was performed in this investigation.

- Live ARM subscription state: Enabled, PayAsYouGo_2014-09-01, spendingLimit Off.
  Microsoft.Compute, Microsoft.Network and Microsoft.Storage are Registered.
- The actual failed deployment/validation events confirm three distinct blockers:
  selected older sizes return SkuNotAvailable/capacity restrictions; newer Bsv2,
  Basv2 and selected Dv5 families have zero quota; West Europe has Microsoft's
  `sys.blockwesteurope` deny assignment and RequestDisallowedByAzure (new-customer
  region restriction). More regional vCPU quota does not remove SKU restrictions.
- The Canada Central Resource SKUs API explicitly marks Standard_B2s,
  Standard_B2ls_v2 and Standard_B2als_v2 NotAvailableForSubscription. The first
  has 10 unused family vCPUs; the two v2 families have zero. The subscription's
  total regional vCPU quota is 10, with zero usage.
- A complete Canada Central SKU response (1,339 records, no next page), joined to
  live quota, identifies newer x64 D/F/E v7 candidates with no location restrictions
  and 10 unused family vCPUs. ARM-only options were not substituted for R10's x64 image.
- **Standard_D2als_v7 (2 vCPUs, 4 GiB, x64) passed `az vm create --validate`**
  with Debian:debian-12:12-gen2:latest, SSH authentication, 30 GiB StandardSSD_LRS.
  Exit 0, provisioningState Succeeded, 2026-11-14T16:28:08.512139Z, correlation
  `8cb458dc-ee68-4ad5-ba9d-25e502712005`. NetworkWatcherRG was only the existing
  validation context; the diagnostic template used no NSG ingress rule and created
  no resources. This validates a fresh VM/network template, not the full phase's
  resource group, policy/security layout or actual allocation.
- Azure Retail Prices API returns Linux on-demand compute **USD0.0896/hour** for
  this size in Canada Central (Windows and Spot rows excluded). Disk, public IP,
  transfer and taxes are additional. The current phase runner's USD0.07/hour default
  is below compute alone and must be revised before a run. `R10_SIZE` and
  `R10_RATE_USD_PER_H` already support overrides; no source change is needed to
  select the size. An actual run remains under its phase approval and USD25 ceiling.
- Additional preflight defects reproduced without cloud writes: B2ls_v2 is mapped
  to nonexistent `standardBlsv2Family` instead of actual `standardBsv2Family`;
  `quota_free` accepts the regional total when the family row is missing. A fixture
  containing regional 10/free and actual Bsv2 0/free therefore incorrectly returns
  GO/10. T012b must also restore subscription-aware SKU restrictions, fix the family
  mapping, fail closed on missing quota rows, and evaluate the selected size.
- First-phase recommendation: use the validated Canada Central D2als_v7 candidate
  with a recalculated ledger rate and retained phase approval. Actual allocation
  is still unproven; support is not established as necessary for this candidate.
  West Europe remains a separate region-access issue for the later HA phase.
- Private filtered evidence: `~/.local/share/netclaw/r10-diagnosis-20261114/`
  (`activity-errors.json`, `sku-canadacentral.json`, `small-skus-canadacentral.json`,
  `validate-d2als-v7.json`, `candidate-retail-price.json`). No support request,
  quota change, provider registration or cloud creation was submitted.

Microsoft references: [SKU restrictions](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/error-sku-not-available),
[family quotas](https://learn.microsoft.com/en-us/azure/quotas/per-vm-quota-requests),
[region access](https://learn.microsoft.com/en-us/troubleshoot/azure/general/region-access-request-process).


## Authorized execution, full-host correction and owner stop — 2026-11-14

This supersedes the diagnostic-only state above. Actual D2als_v7/Debian12 VM
creation succeeded in Canada Central, with DNS and trusted ACME certificate.
The owner's full OpenShell/DefenseClaw/HUD/VSCode requirement required correcting
that initial host selection: it was retired without any Border activation.
D2as_v7/Ubuntu24.04/40GiB validation passed in Canada Central, EastUS2 and Sweden
Central; the actual Canada Central 8GiB VM was created and host bootstrap passed
(kernel7.0.0-1017-azure, Landlock ABI8, Docker>=28, pinned OpenShell0.1.7 gateway).
No Azure Border services, sandbox image, workspace/gateway, member or model/tool
call was activated. No GCP resource was created. Thus this proves Azure VM/host
feasibility, not application, HA or six-Border mesh acceptance.

The owner then requested stop, complete owned teardown and an agent handoff.
See [handoff.md](handoff.md) for regional price/validation receipts, source changes,
open technical gaps, budget distinction and final cleanup. Source checks:24 R10
unit tests and107 existing R09A sandbox/bind/negative regressions passed; HUD built
with Node24. New R10 runner and newly broadened policy paths remain unqualified.

Official requirements: [OpenShell support matrix](https://docs.nvidia.com/openshell/latest/reference/support-matrix),
[Azure Dasv7 sizes](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/dasv7-series).

Final cleanup verified 2026-11-14T16:58:59.463922+00:00: both owned Azure groups absent; zero owned cloud resources on Azure/GCP, DNS and ACME challenge absent, owned budget alert removed, watchdog unloaded, ledger closed. Estimated infrastructure allowance USD0.0593, excluding the unspent USD5 reserve; actual billing reconciliation remains pending. Private cleanup receipts and full handoff are retained.


## 2026-11-14 (resumed from handoff): ONE FULL AZURE BORDER LIVE, member and VS Code not yet done

Run `r10b-20261114`, group `rg-nc198-p2-full`, Canada Central, Ubuntu 24.04, `Standard_D2as_v7` (2 vCPU, 8 GiB), 40 GiB.
Evidence: `~/.local/share/netclaw/r10-run-r10b-20261114/` (private). Cleanup watchdog loaded (6 h), ledger reserve 6 h at $0.13/h.

Observed (not assumed):
- Preflight real validation GO in canadacentral/eastus2/swedencentral for the exact SKU (`--probe`).
- Bootstrap on Azure Ubuntu: kernel 7.0.0-1017-azure, Landlock ABI 8, Docker 29.9.3, OpenShell 0.1.7, DefenseClaw 1.0.4, OpenClaw 2026.7.1-2.
- One-node identity generated with `--sandbox`; DNS A record + Let's Encrypt cert via DNS-01 for `nne1-bcc342.automateyournetwork.com`; trusted TLS (curl verify=0, HTTP 200).
- Node image built on the VM (exit 0); OpenShell provider `nc183-anthropic` created from a custom endpointless profile (`openshell provider profile import`), key streamed over ssh stdin, never in argv/files.
- etcd RBAC enabled and authority bootstrapped; Border running inside the sandbox; `GET /api/hud/posture` shows border-role, hud-ingress, workspace-backend, chat-gateway and defenseclaw-sidecar running, guard `action`/fail_closed, Landlock hard_requirement, policy sha 1e4b1ecf...; authority epoch 3 in cluster mode; operations catalog reachable with the cluster pin headers (members: none yet).

Findings and fixes (all in source, tested where noted):
1. `protected_role.py` refused a one-Border member topology; now 1..3 allowed (tests: `tests/n2n/test_ha_single_node_198.py`, 7 cases).
2. `r09a_policy.py` loopback exception was not confined: a spec listing `host.openshell.internal:12379` next to a remote voter was accepted. Fixed (`single_host_etcd_must_stand_alone`); tests `tests/n2n/test_ha_policy_198.py` (12 cases). 94 R09A/R10 policy and bind tests pass.
3. The sandbox policy's python entry must be the RESOLVED interpreter `/usr/local/bin/python3.12`, not `/opt/nc182/venv/bin/python3.12` (OpenShell denied `transparent_tcp_policy_denied`); render with `"binaries":{"python":"/usr/local/bin/python3.12"}`.
4. `r10_node_run.py` called a guard script path that is not in the image and never copied the guard config; fixed (script and config now come from the payload; `labs/ha/r10_payload.py`).
5. Posture still reports `region: northamerica-northeast1` (old GCP label for logical code nne1): cosmetic, to fix before qualification.
6. The cloud IP allow-list must track the operator's address (it changed during the session): the NSG source is the current /32.

NOT done yet (do not count as passed): on-prem subnet member enrolment and a member-run operation with durable ACK; cloud-hosted NetBox member; VS Code owner-client discovery/review/approval/reconciliation; a real guarded chat turn through the HUD; guard refusal and fail-closed evidence on Azure; the three-Border HA, GCP and cross-cloud phases.


## 2026-11-15 (new run r10c-20261115): one full Azure Border, guarded turn and isolation PROVEN

Run `r10c-20261115`, group `rg-nc198-p2-full`, Canada Central, Ubuntu 24.04, `Standard_D2as_v7`; DNS `nne1-97af1e.automateyournetwork.com`.
Observed: trusted HTTPS `GET /api/hud/posture` HTTP 200 with border-role, hud-ingress, workspace-backend, chat-gateway, defenseclaw-sidecar running inside the OpenShell sandbox (Landlock hard requirement, guard action/fail_closed, policy sha 1e4b1ecf...).
- Real guarded chat turn: `openclaw agent` through the in-sandbox gateway and the DefenseClaw guard to the hosted Sonnet returned `pong`.
- Guard refusal: a prompt-extraction + fake private-key prompt was blocked (matched TRUST-PROMPT-EXTRACT, action=block); guard log redacted the match.
- Bypass refused: a direct embedded (`--local`) call that skips the guard got 401 (the policy only lets `defenseclaw-gateway` reach the provider); `labs/ha/r09a_negative.py`: 9 of 9 cases refused, 0 unexpected success.
- Guard kill test inconclusive: the sidecar was restarted automatically within seconds, so a stopped-guard fail-closed proof was NOT obtained.
Findings fixed in source: (1) single-node sandbox identity needs `--node code=int,pub,host.openshell.internal` so the etcd server cert carries that SAN; (2) OpenShell provider profile needs `auth_style: header` + `header_name: x-api-key` and an endpointless profile (`PTYPE=nc183-anthropic ha-r10-openshell-provider.sh`); (3) `r10_node_run.py` must add `maxTokens/contextWindow` to the OpenClaw model entry and pass `DEFENSECLAW_GATEWAY_TOKEN`/`DEFENSECLAW_LLM_KEY` to the gateway (the plugin authenticates to the guard with X-DC-Auth); (4) lego needs an executable EXEC_PATH wrapper and `--dns.propagation-wait`.
Still not done: Mac subnet member + durable ACK, NetBox member, VS Code owner client, HA, GCP, mesh.

### 2026-11-15: NetBox member operation through the Azure Border PROVEN (durable ACK)

NetBox-flavor member (hosted Sonnet via DefenseClaw guard, exact reviewed `netbox_get_object_by_id` read of demo.netbox.dev device 27) enrolled into the sandboxed Azure Border and attached outbound over 7444. Prepare, approve, dispatch, member admission, result: state `completed`, outcome `succeeded`, effect `finished`, `durable_ack: true` (`op-netbox-5.json`, private evidence).
Finding (security design working as intended): a first attempt that ran while Docker was stopped on the member host returned `refused/docker_operation_failed` and the Border retained the member-wide resource fence (`resource_recovery_required` 409 on every later operation). There is no automatic release; recovery was enrolling a fresh member identity (`netbox-fc96f6`). A proven reconciliation path for a failed-and-fenced member remains a design item. The enrollment ran as a one-shot inside the sandbox before START (`r09_vm_enroll.py` now honours `NC_STATE`).
Still not done: Mac subnet member, VS Code owner-client journey, HA, GCP, mesh.

### 2026-11-15: THREE sandboxed Azure Borders live as one HA group (run r10d-20261115)

Canada Central, East US 2, Sweden Central (`Standard_D2as_v7` each), group `rg-nc198-p3-ha`, global VNet peering plus a private DNS zone `r10-20261115.azure.internal` (azca/azus/azse) linked to the three VNets (names match `AZURE_INTERNAL` in `r09a_policy.py`). Three-voter etcd formed across the regions (health commit 100-210 ms); etcd RBAC + authority bootstrapped through the sandbox policy path to a remote voter; each Border runs inside its own OpenShell sandbox with the guarded gateway, workspace backend, HUD ingress and DefenseClaw sidecar. All three answer `GET /api/hud/posture` HTTP 200 over trusted TLS (guard action, Landlock, sandbox Ready) and report authority epoch 3, mode cluster.
Not yet: member enrollment into this group, operations through each Border, leader-loss test, then GCP and the six-Border mesh.

### 2026-11-15: three-Border HA — operations, takeover, limits (run r10d-20261115)

Facts (observed): with `admission_ms=4500` (R10_ADMISSION_MS) the three-region group completed a NetBox member operation entered through **nne1** (state `completed`, outcome `succeeded`, `durable_ack: true`, epoch 31) and another entered through **ew1** (completed, durable ACK, epoch 78). Takeover: stopping the nne1 Border advanced the authority epoch (78 to 113, later 163 to 165) and the surviving Borders kept serving catalog reads. A completed operation entered through **ase1**, and a completed operation after leader loss, were NOT obtained: the far-region entries (ase1, ew1 during degraded quorum) answered slowly (46 s catalog, 15 s posture) and my polling client timed out; this matches the known R09 limit that a degraded two-of-three far-region quorum cannot admit reliably. Treat HA ingress through ase1 and post-takeover execution as UNPROVEN.
Findings: (1) `admission_ms=3000` (default of `r10_prepare`) is too tight for three regions; hosted-model execution then fails (`agent_produced_no_tool_evidence`) and fences the member; use 4500 and re-measure. (2) A failed or refused member result keeps a member-wide fence with no automatic release (`resource_recovery_required`); recovery used here was enrolling fresh member identities, ahead of any designed reconciliation path. (3) The public `demo.netbox.dev` stalls on the first request after idle (30 s) and the member's single 20 s read then fails; warm it before an operation. (4) About half of hosted-model attempts failed on cold container networking (Docker Desktop) in the provider relay; retry needs a fresh member. (5) Private DNS names `azca/azus/azse.r10-20261115.azure.internal` satisfy the sandbox policy's cluster-host rule; etcd 3-voter health commit 24-210 ms across regions.
Not started: GCP Borders, six-Border federation, cross-HA execution design (protected mode still refuses legacy eN2N execution).

### 2026-11-15 (run r10e Azure + r10f GCP): SIX sandboxed Borders live; real operations through ALL SIX

Two three-voter groups built with `scripts/ha-r10-build-group.sh` (azure: Canada Central/East US 2/Sweden Central; gcp: northamerica-northeast1/europe-west1/asia-southeast1, Ubuntu 24.04 e2-standard-2, Landlock ABI 8). Each Border runs in its own OpenShell sandbox with guarded gateway, workspace, HUD ingress and DefenseClaw (guard action mode); posture HTTP 200 over trusted TLS on all six. Hosted Sonnet only (no Ollama). Eight NetBox members (4 per group) on the Mac, attached outbound; every Border's catalog lists its group's four members.
One real NetBox read (device 27, hosted Sonnet via guard) per Border, entered through that Border's HUD API: all six `completed`, `succeeded`, `durable_ack: true`, authority epoch 15 in both groups. This includes the ase1 ingress that was unproven in r10d.
Script defects found and fixed live: Azure host-key pin file was assembled after the first SSH (now appended per node); `image` step pre-created the context dir the builder refuses to overwrite; the phase script defaults to a B2s size (set `R10_SIZE`).
Still to prove: takeover/rotation per group, cross-group (delegated) execution, Mac subnet member.

#### Takeover and rejoin (r10e Azure, r10f GCP), same session
- Stopped the nne1 Border in both groups (runner killed in sandbox). Survivors kept serving posture. Azure: operation entered through ew1 under the 2-of-3 quorum **completed**, durable ACK, authority epoch 15 -> 41. GCP: the same operation was **refused** (`agent_produced_no_tool_evidence`) four times with four different members: the new leader was ase1 (Singapore) and the entry was ew1 (Belgium), consistent with the known far-region admission limit at `admission_ms=4500`. Each refusal fenced its member (4 GCP members spent).
- Enrolled four fresh members per group in one outage window, restarted all three Borders per group (nne1 rejoined): operations completed through nne1 and ase1 (Azure, epoch 63) and ase1, nne1, ew1 (GCP, epoch 79), all `durable_ack: true`.
- Not yet shown: GCP completed operation under degraded quorum.
- GCP, second degraded attempt: with the ase1 Border stopped (surviving pair nne1 + ew1), an operation entered through nne1 **completed** with a durable ACK (epoch unchanged at 79: the stopped node was not the leader, so this shows a surviving 2-of-3 quorum, not a leader change). Azure covers the actual leader change (epoch 15 -> 41, operation completed).

### 2026-11-15 TEARDOWN of the six-Border run (r10e Azure, r10f GCP), owner request (bad Wi-Fi)
Azure group `rg-nc198-p3-ha-az` deleted (0 groups, 0 tagged resources); GCP: 0 instances, disks, addresses and firewall rules matching nc198/nc182; six GoDaddy A records and their ACME TXT records absent; both launchd watchdogs unloaded; ledger `open_entries: 0` (est. total USD 8.85 including the USD 5 reserve, i.e. about USD 3.85 estimated real spend); Mac member processes stopped. Interrupted by the operator's network loss: GCP enrollment of two subnet + two NetBox spares and the Azure subnet/NetBox spare operations did not run, so the Mac subnet member, rotation, and cross-group federation remain unproven. Build script defects fixed live are listed above. Nothing committed or pushed.

### Release-gate note (T032)
Unchanged. The VS Code extension carries an **unpublished** local change (connection Rename/Remove row menus and a removal confirmation; `package.json` version
not bumped, no VSIX packaged or published); the Mobile app and the HUD/Border source were not published. Publishing any client build that exposes
multi-region or multi-cloud Borders needs the owner's explicit approval (spec 179 R09 gate, `../179-border-ha-authority/acceptance.md`).

### Offline docs and installer work (T029-T033), run without any cloud call
- Azure guide `docs/NETCLAW-IN-AZURE.md` rewritten to the proven recipe (Ubuntu 24.04, Standard_D2as_v7, canadacentral/eastus2/swedencentral, ledger, watchdog, build-group steps, hosted-Sonnet members, teardown, limits); new `docs/NETCLAW-MULTICLOUD-MESH.md` (mesh status: cross-group execution still pending live proof); README Azure section; `.env.example` Azure names (no values); read-only Azure step in `scripts/install.sh` via `scripts/lib/azure-menu.sh` (runs only the preflight, prints the commands, creates nothing).
- VS Code (unpublished, no version bump): connection rows get inline and context Rename/Remove with a removal confirmation. `tsc --noEmit` clean, build OK, `test/connection-menu.test.mjs` 3/3; full extension suite 222 pass, 2 fail (the managed HUD launcher tests require Node 24.19+, this machine runs Node 25.3), same two failures before the change.
- `tests/azure/test_docs_parity.py` 8/8 and `tests/gcp` parity 8/8 and `test_netclaw_gcp.py` 14/14; `scripts/verify-inventory-counts.py` PASS. `python3 scripts/reconcile-mcp.py` exits 1 both with and without these changes: its failures are registered servers that cannot start in this environment (missing Python modules) and a humanrail dependency pin, not caused by spec 198; its documented-counts check passes.

### 2026-11-16 (runs r10g Azure + r10h GCP): six Borders rebuilt with cross-group federation, first live federation results
Built with `scripts/ha-r10-mesh-up.sh` (both groups in parallel, peer config + tcp/7445 only from the other cloud's three /32s, sandbox egress via `federation_peers`). Hosted Sonnet only; 10 members per group queued, 6 per group enrolled in this pass (4 netbox + 2 subnet).
- **Union catalog works**: Azure nne1 lists its 6 members plus the 6 GCP members tagged `remote: gcp`; GCP nne1 lists Azure's tagged `azure` (12 each, signed peer catalogs, `federation.peers[].status = ok`).
- **Cross-cloud operation completed**: entered on the GCP nne1 HUD, executed by the Azure `hsubnet` member (hosted Sonnet via the guard + the calculator tool): `completed`, `succeeded`, `durable_ack: true` (this is also the first live subnet-flavor member operation). The receiving group authorized it in its own ledger.
- **Azure-ingress -> GCP-member** attempts ended `refused` (`agent_produced_no_tool_evidence`) on four GCP members, and a LOCAL GCP operation through a fresh GCP netbox member refused the same way, i.e. not a federation failure: the operator's Wi-Fi was dropping (heartbeat losses at 11:30:45, ping jitter 5-433 ms); each refusal fences its member.
- **Defect found live (offline tests missed it)**: `ha/federation.py` read `authority.epoch`, which is only set on the lease-holding node, so a FOLLOWER ingress (ew1/ase1) signed a null epoch and every peer call from it failed with `peer_error` while the leader ingress (nne1) worked. TCP/TLS 7445 reachability to all three peer nodes was verified from inside the sandboxes, isolating it to the application layer. Fixed to use the quorum epoch (`authority.current()`), sender refuses a non-integer epoch, regression test added (29 tests pass). The signed source manifest means a code change requires a full re-prepare, so both groups are being rebuilt to verify follower ingress.

### 2026-11-16 (runs r10i Azure + r10j GCP): six-Border mesh WITH the follower-epoch fix; final live results and teardown
Built by `scripts/ha-r10-mesh-up.sh` (both groups, hosted Sonnet, 10 members per group). Window reserved at 5 h after the ledger gate (projected USD 15.68) paused the 8 h plan; watchdogs matched.
**Proven live**
- Follower-ingress fix verified: ALL six Borders (leaders and followers) list 20 members (10 tagged `remote`) with `federation.peers[].status = ok`; before the fix only nne1 did. TLS/7445 reachability was independently verified from inside the sandboxes.
- Union catalog and relay: an Azure-ingress operation toward a GCP member was relayed, authorized by the GCP group in its OWN ledger (own operation id, GCP epoch 33, `origin` recorded: cluster, node, epoch, principal subject, relay digest) and the signed response returned (`remote.served_by` = the GCP Border). In the earlier build (r10h) a GCP-ingress operation on an Azure `hsubnet` member completed `succeeded`, `durable_ack: true` (also the first live subnet-flavor member operation).
- Local operation on Azure nne1 completed with a durable ACK (epoch 33).
- Azure leader loss: nne1 killed, authority epoch 33 -> 85, followers kept serving; the federation survived (Azure followers and all three GCP Borders still showed 20 members, peers ok). nne1 restarted through the certificate rotation.
- Certificate rotation: `ha-r10-build-group.sh rotate nne1` renewed the ACME certificate, rebuilt the node payload, restarted the Border; the TLS serial changed and posture returned to 200.
**Not proven / honest limits**
- After the first hour, member-executed operations were refused (`agent_produced_no_tool_evidence`; member-side `inference_refused` before any model forward) for Azure and GCP members alike, including after restarting Docker Desktop (container egress to api.anthropic.com had timed out and recovered) and with only six members running. The operator's Wi-Fi was unstable throughout (dropouts, ping jitter 5-433 ms, laptop sleep killing the member processes) and the Mac was under memory pressure. Cause not isolated. Hypothesis supported by the code and node ordering: a member sends admissions through the lowest-sorted Border id (`ha/internal.py send_admission`, 5 s timeout); in the GCP group that is ew1 (Belgium), far from the Mac, while Azure's is nne1 (Canada).
- Not shown: completed Azure->GCP, and cross-group operations through every follower ingress, with durable ACKs; GCP leader change with a completed operation; Mac subnet member beyond the one subnet operation above.
- Open product item: member admission should pick the nearest authenticated Border (latency-aware), not the lowest id. That is a security-relevant change to qualified code and was NOT made.
**Spend and teardown**: ledger est. USD 13.06 including the USD 5 reserve (about USD 8 estimated real); Azure group deleted (0 groups, 0 tagged resources), GCP 0 instances/disks/addresses/firewall rules, 6 A and TXT records removed, watchdogs unloaded, member processes stopped; `scripts/ha-r10-teardown-all.sh` printed the verification block. Nothing committed or pushed.

### 2026-11-16 closing record (offline)
- **T034 billing reconciliation: PENDING.** `az consumption usage list` returned the run's VM usage records with null cost (Azure billing lags by about a day). Reconcile against the Azure cost view for `rg-nc198-*` resource groups (Cost Management, filter tag `netclaw-spec=198`) and compare with the ledger (est. USD 13.06 including the USD 5 reserve, about USD 8 estimated real) before closing SC-001.
- **Offline change added, not live-verified:** nearest-Border member admission (`ha/internal.py`, `ha/member.py`; see the contract's qualified-code table). 3 new tests; HA/protected suites 1481 passed.
- **Owner decisions (2026-11-16):** all cloud assets torn down at the owner's direction; the three open live gaps (Azure-entered operation completing on a GCP member, cross-group operations through every follower Border, a completed GCP operation after a leader change) will be closed in a later session on a stable network.

## 2026-11-16 run r10k (Azure) + r10l (GCP): GCP admission timeout finding, torn down at owner request

Mesh built end to end by `ha-r10-mesh-up.sh` (all steps ok, six Borders, 12-member union catalog visible from every Border). Network stable (0% loss, 6 ms to 8.8.8.8), Mac awake, Docker egress to api.anthropic.com 64 ms.

Results (evidence `~/.local/share/netclaw/r10-matrix-1/`):
- Azure-local operations through nne1 and ew1: COMPLETED, durable ACK (`1a5914`, `9f1d8e`).
- Azure-entered cross-group operations on five GCP members: REFUSED `agent_produced_no_tool_evidence` (durable ACK, member fenced each time).
- GCP-local operation via GCP nne1 on `d32e29`: REFUSED the same way. So the fault is the GCP group, not the cross-group relay.
- Matrix stopped early to avoid fencing spares; it did not complete. Gaps 1, 2 and 3 remain OPEN.

Root cause (measured, not yet fixed): the member's agent container saw `502` after 5021 ms on its first model call, then `403 inference_refused`. `ha/internal.py:229` gives `execution/admission` a 5 s timeout. GCP Borders were in northamerica-northeast1, europe-west1, asia-southeast1 (RTT 107 ms and 238 ms measured from nne1). Each etcd txn on the GCP Border took about 320 ms (3 txns/s from `border-role.log`), so admission exceeds 5 s. Azure Borders are far closer together, so Azure admission fits. Mac-to-Border latency (60-230 ms) was similar in both groups and is not the cause. No GCP network denials, provider profile correct (`auth_style: header`).

Options not taken (owner chose to stop): rebuild the GCP group in tighter regions (no qualified-code change), or raise the admission timeout (qualified code, needs owner review and a fresh signed prepare). The earlier r10i/r10j GCP success predates this finding and should be re-read with it in mind.


## November24 resumed investigation (no new paid run)

See [resume-20261124.md](resume-20261124.md) for current authentication, inventory,
ledger, billing and the concrete proposed USD23.0076 cumulative reservation.
Azure validation passed for the exact full-host selection in all three regions;
GCP quotas are available in all three unchanged regions. Zero owned cloud
resources and zero old R10 watchdogs were observed.

The r10l frozen source ALREADY includes nearest-Border selection (exact hash match
to the resumed checkout), while its signed admission window is4500ms. A controlled
real-TLS/fixture-quorum reproduction measured15quorum calls for follower admission:
4.88s at320ms/call,6.08s at400ms/call. The former fails the original freshness
limit; the latter also exceeds the old5s RPC wait. A9s signed window plus a
manifest-derived wait passes both; a700ms/call case times out at9s with zero
fixture effects.126targeted tests passed. These are controlled tests, not live
Azure/GCP/provider acceptance. All three actual live gaps remain open.

Azure ActualCost now reports CAD6.8605695141. GCP actual billing remains unavailable
through the current API/export/browser surfaces. The full historical USD13.9276
hold remains; no reserve was reduced and no Genie allowance was transferred.
Checked tasks carrying stale PARTIAL/OPEN notes were reconciled; cloud NetBox
placement, native HUD/VS Code and fail-closed guard proof remain explicit tasks.

## November24 fresh live r10m/r10n — intermediate evidence

The owner renewed completion/merge authorization subject to actual acceptance and
USD25 cumulative. The reviewed six-hour reservation is USD23.0075943167 including
all historical reserves, seven hosts and a fresh USD3.50 provider/transfer/cleanup
reserve. Watchdogs were armed once; their deadlines have not been extended.
Private evidence: `~/.local/share/netclaw/r10-live-20261124/`.

All six Borders started over trusted HTTPS with three distinct regions per cloud.
Both fresh manifests explicitly sign9000ms admission. GCP etcd health measured
104–373ms. All six union catalogs expose the five enrolled members. Azure HUD
rendering was observed in actual Chromium. These are intermediate checks, not
completion of the matrix.

GCP-native operation `ceb65c4d-1626-4ea7-b38c-6eb2738632cf` completed on the Mac
subnet member with a verified receipt and delivered durable ACK at epoch12:
two hosted Sonnet calls, one subnet effect. Its three admission challenges
(model1/tool1/model2) are finished. The operation took109.481s including collection
of the original result; the first reconcile had returned before the result was
ready. A later confirmed reconcile collected that same receipt without execution.

Azure-to-physical-GCP operation `83b1d9bc-9dd3-4029-86e3-f8569f0510c6` did NOT
complete. The physical member retained `outcome_unknown/effect_outcome_unknown`,
zero claimed/finished native effects and no executor result. Its freshly built
Linux environment lacked MCP: the executor's lazy import failed before creating
its operation runtime directory. The old builder requirements omitted MCP,
FastMCP, Uvicorn and Starlette while the reused qualified Mac environment already
contained them. The original unknown identity and fence remain untouched. No
replacement approval is authorized by a checkbox or by the absence of a result.

The builder now pins the qualified versions (MCP2.3.0/FastMCP4.0.11/
Uvicorn0.54.0/Starlette1.10.0), probes the executor's lazy imports and returns a
nonzero validation status on failure.21 existing member-builder tests pass.
The old actual Linux closure now fails that validation with `No module named mcp`;
a separate fresh immutable environment passes the lazy-import probe. Any further
member execution requires fresh identity/source/runtime preparation, with the
original failure retained and never replayed.

An actual Azure HUD cross-member prepare (no approval) exposed another acceptance
gap: the remote receiving-cluster review is rejected as “another cluster, issuer
or operator.” The API relay alone does not qualify HUD or VS Code. Client trust
must bind the peer review to the trusted ingress and original operator; removing
cluster/principal checks is not an acceptable repair. The current DTO also
returns the original client nonce only for prepare, so status recovery needs
consistent nonce provenance. Both gaps remain open pending a verified repair and
fresh signed deployment.

Client repair source validation:74Python federation/manifest/authority/admission
checks pass under the qualified Python3.12 environment;549HUD tests pass; native
TypeScript checking/build pass. The extension suite initially found one stale
region-label expectation from the earlier observed-region display change; it was
corrected to assert the actual region and reject a false Belgium label for Azure.
40targeted editor tests and the added native peer-verification test pass. The
public cross-language fixture contains controlled signatures, no private keys and
no provider/native-effect evidence. This is source validation only; fresh live
native acceptance and the matrix remain required.


## Fresh generation2 activation and first repaired cross-cloud proof — 2026-11-24

Source0b9d0d11 was freshly signed into gen-az2/gen-gc2 on the same seven run-owned
VMs and original six-hour watchdogs. No VM reservation or deadline was reduced or
extended. Before replacement, all six old Border states and all six stopped etcd
stores were exported and hash-verified. Old etcd state remains archived on each
host; the failed physical member and all four old Mac member roots also have
private exports and SQLite integrity checks. The original unknown operation is
retained and fenced, with its operation-budget claim/reservation unchanged.

The operator cleanup helper initially missed members because protected-role had
exec'd bgp-daemon-v2.py. da4d61eb adds exact private-source-path matching for that
owned daemon, immediate command rechecks and verified process exit; existing
owner/spec200 roots cannot match. Two ownership tests pass and all four old
qualification member processes were stopped and exported.

GCP fresh quorum health writes measured127.943142/270.495039/393.934520ms across
Montreal/Belgium/Singapore; Azure24.409284/45.044293/125.291863ms. These are quorum
proposal timings, not pure network RTT. All six fresh HTTPS postures and five-member
union catalogs returned200 before effects. Azure Canada leader epoch9 entered
operation228a28a8-af9d-41f0-b8a7-e7a8befc6944, which completed on GCP-enrolled
Mac subnet memberhsubnet-a7d3f2 with verified receipt and delivered durable ACK
at GCP epoch12. Its three model/tool admissions finished. Origin nonce and the
live signed peer-client endorsement passed the shared client verifier. This is
real Azure-to-GCP authority execution; physical cloud NetBox execution remains a
separate required witness.

The demo NetBox token had expired: both Mac and cloud returned403/Invalid v2 token
before any new NetBox provider execution. The owner supplied a replacement; it
was written through the private atomic environment writer without echoing it.
Only the three unspent generation2 qualification member credential files were
refreshed; the old fenced identity was preserved. Read-only device27 preflights
then returned200 on Mac and GCP (cloud0.3355s). Source, identities, selected endpoint
and signed profiles were unchanged; secrets are not embedded in source manifests.

GCP signed-in Billing Reports now isolates project322389837669/netclaw-spec=198:
CAD3.06 posted gross, CAD-3.06 credits, CAD0 net for November1–24. Actual CSV and
accessibility evidence are exported privately. Project networking CAD1.90 is
unattributed and remains conservatively covered by the historical reserve. Azure
posted CAD6.8605695141 and the
[Bank of Canada November24 rate](https://www.bankofcanada.ca/rates/exchange/daily-exchange-rates/)
(1USD=1.4296CAD) give indicative USD4.79894 Azure and USD2.14046 GCP gross; these
are not card settlement rates. Billing lag is not zero current-run cost. Historical
USD13.9275943167 held and the full USD23.0075943167 envelope remain unchanged.
Private root: `~/.local/share/netclaw/r10-live-20261124/`.

Native qualification helpers now validate receiving-cluster endorsement/review
and ACK keys while retaining original local principal/nonce binding. Ten helper
checks pass; this remains distinct from actual browser/Code acceptance. The
real full-HUD navigation includes a numeric prefix on Approved operations; the
driver uses its observed accessible name rather than an exact unprefixed label.
Earlier read-only screenshot attempts timed out on continuous polling/networkidle
and that label; they performed no approval and remain retained as diagnostics.

Additional current checks: actual Chromium rendered the full HUD on all six
fresh URLs with no page-script errors in the diagnostic page. Native extension
suite225passed/3explicitly skipped/0failed (228total). `reconcile-mcp.py` was run
as required: catalog, docs, package, portability, Meraki IDs and skill limits pass;
its global dependency/startup checks fail for an existing unbounded HumanRail MCP
pin and numerous optional MCP environments absent from this checkout. These are
not silently reported as passing and no unrelated owner installation was changed.
The isolated signed qualification runtime closure checks and actual operations
remain the evidence for the deployed stack.

### November24 native review and physical Linux relay findings

The actual HUD operation21d4e8ab-60b8-486a-a9f3-a9102760d1d9 completed Azure Sweden→GCP member with verified result/durable ACK. Same-tab cold recovery sent GETs only (incidental chat-usage POST was blocked); actual member effect/inference counters were unchanged. The first navigation probe sent no preparation; its evidence remains. Eleven of twelve baseline ingress/direction cells now have actual ACK evidence.

Actual Code1.109.0 prepared62438fb1-b26d-4075-88ce-5d224dd7a41c but the view incorrectly compared the receiving cloud principal directly with the ingress principal. No approval was sent. The view now uses the existing cryptographically verified operation-principal binding; a native-dialog regression proves the signed remote review reaches decision review and an unverified clone does not. TypeScript/build and36 relevant tests pass. Fresh native approval remains required.

Physical NetBox member905712 returned signed refusal/ACK for b298ec49-a7d9-4a68-b5ab-3fa9911f2e85 (`agent_produced_no_tool_evidence`, zero tool claims, zero provider forwards). Its identity remains fenced. The inherited Mac TCP relay uses Docker Desktop's host loopback name, absent on this Linux Docker host. The same immutable Linux relay image passed a real Unix-socket HTTP preflight with no provider/device access. A fresh identity/preparation with Unix relay and bounded short private socket path is being validated; the failed operation is not replayed and its reservation is retained.
