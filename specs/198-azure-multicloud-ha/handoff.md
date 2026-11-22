# Spec198 / R10 handoff — 2026-11-14

**Owner requested STOP, teardown and this handoff. Do not create cloud resources
or continue implementation until the owner resumes.** Source is uncommitted on
`198-azure-multicloud-ha`; preserve the existing dirty tree. No push, merge,
release, version bump or client publication was performed or authorized here.

## Answer to the original blocker

**Azure VM creation works.** The subscription is Enabled and the Compute,
Network and Storage providers are registered. The original selection failed
because of SKU restrictions/zero family quota and a Microsoft West Europe
new-customer policy (`sys.blockwesteurope`), not a global VM-creation failure.

An actual Debian12 `Standard_D2als_v7` VM was created in Canada Central. It was
retired after the owner clarified the full OpenShell/DefenseClaw requirement:
Debian12's original kernel and Docker recipe were unsuitable.

The correct full-host candidate is **Ubuntu24.04 amd64, Standard_D2as_v7
(2 vCPU, 8 GiB), 40 GiB StandardSSD_LRS**. Actual ARM validation passed for:

| Region | Linux compute USD/hour | Successful validation correlation ID |
|---|---:|---|
| Canada Central (`canadacentral`) | 0.1010 | aefd73c9-7651-4bdb-9aae-2e2deefa5e59 |
| East US 2 (`eastus2`) | 0.0908 | 116453bb-e22b-45d0-8455-8d0d60001edf |
| Sweden Central (`swedencentral`) | 0.0970 | 49d0396f-5f13-4ae0-802a-ee8245999946 |

**Actual full-host VM creation also succeeded in Canada Central**
(`nc198-p2-full-nne1`). Bootstrap observed kernel `7.0.0-1017-azure`, Landlock
ABI8, installed Docker>=28 and pinned OpenShell0.1.7, passed its gateway/doctor
checks, and installed the container metadata block. The VM was then torn down
at the owner's request. Validation does not reserve future regional capacity;
recheck subscription quota, exact image/SKU and prices before a new run.

## Required delivery when resumed

1. One **full Azure Border**: trusted HTTPS HUD, running workspace and OpenClaw
   gateway, working VS Code, OpenShell and DefenseClaw, real successful calls,
   guard refusal/fail-closed evidence. Keep the on-prem subnet member scope.
2. Three such Azure Borders across the three usable regions, HA qualification,
   plus a cloud-hosted NetBox member using the real NetBox skill/MCP.
3. Three full GCP HA Borders, then federation with Azure: **six NCFED Borders**.
   Prove every ingress and actual bidirectional cross-cloud member operations,
   durable ACKs and correlated audit/recovery evidence.

The working interpretation is two three-Border quorum groups federated through
NCFED; a six-voter authority redesign was not authorized. Do not count VM
creation, posture, open ports or an ordinary peer handshake as full acceptance.

**None of the application/HA/cross-cloud acceptance above is complete.** No
Border runtime, workspace, gateway, sandbox image, enrolled member or model/tool
operation was activated on Azure. GCP was inspected only; no GCP resource was
created. No provider or NetBox credential was placed on either Azure VM.

## Source and technical findings

- `r10_preflight.py` now queries the real server-filtered Resource SKU API,
  includes restrictions, fails closed on missing regional/family quota, supports
  exact SKU selection and `az vm create --validate`, and retrieves retail prices.
  Defaults are the three usable regions and Ubuntu24.04/40GiB. The older
  `preflight-full-border.json` has an intermediate Sweden failure while retirement
  of the validation context group was in progress; `full-border-ubuntu-validation.json` is the
  subsequent all-three successful validation. Secret-presence reporting still
  reads only one env file and can falsely report Anthropic absent.
- Azure driver supports region overrides, restricted management/federation
  ingress, private VNet peering by resource ID, pinned SSH host keys, Ubuntu
  and configurable disk size. Logical codes `nne1/ew1/ase1` still carry old GCP
  region labels in clients: fix labels or add Azure codes before qualification.
- R10 ledger now reserves the reviewed duration, rejects invalid rates and
  duplicate open entries, and accounts for fixed reserves. It is not a provider
  spending cap and has no concurrent-writer lock. The phase scripts still need
  exact ownership/failure handling review before expansion.
- `r10_prepare.py` selects etcd12379 with `--sandbox`, otherwise2379, and defaults
  admission to3000ms. Measure actual cross-region admission timing; do not assume
  the old4500ms or the new3000ms is qualified for all topologies.
- `r10_node_run.py` is **new, unfinished and untested**. It attempts a frozen,
  explicit full-stack runner without R09A's uploaded `CTL/run-script` hook. It
  was never built into an image or deployed. Finish and test before use.
- `r09a_policy.py` has a **qualified-code change needing review**: exact R10
  Azure private-DNS names and a single-node `host.openshell.internal:12379`
  loopback exception. Existing R09A regression tests pass, but the new paths
  have no dedicated tests or live proof. Preserve confinement and test both
  refused and allowed cases before deployment. No Azure private DNS zone exists.
- A single-node member is currently refused by `scripts/lib/protected_role.py`
  (`ha_outbound_topology_required` requires2..3 nodes); the manifest schema
  accepts1..3. Resolve and test this deliberately for the one-Border phase.
- R09A had sandboxed Borders/guarded embedded-agent calls, but its long-running
  workspace/gateway was explicitly not run. R09 had the workspace outside the
  sandbox. Combining those capabilities requires new real qualification.
- **Cross-HA execution is an implementation gap:** protected mode in federation
  `service.py` refuses legacy eN2N execution routes. `ha/border.py` scopes owner
  authorization to the current cluster/generation. Design protected federation
  preserving peer grants, owner consent, authority, admission and no-replay;
  never bypass those checks or just enable legacy execution.
- Existing R10 deploy/push scripts are initial unsandboxed three-node copies;
  they are not ready for this full single-node/R09A deployment. Review mutation
  retries and error propagation. GCP driver still needs fresh owned VPC/prefix,
  IAM/SSH controls, full-host sizes and exact cleanup instead of default-network
  assumptions. No new six-Border capability is implied by these scripts.

Validation:24 R10 preflight/ledger/driver tests passed;107 existing R09A sandbox,
bind and negative tests passed after the policy edit. HUD rebuilt successfully
under the isolated Node24 runtime. These are source checks, not live acceptance.

## Budget, evidence and cleanup

Owner cap: **USD25 total**, pause atUSD15. The reviewed full-host envelope used
USD0.15/hour per Azure VM, a six-hour window and a USD5 reserve for transfer,
model calls and cleanup. It was a short validation budget, not continuous hosting.
The ledger's USD5 fixed entry is a reserve, **not actual incurred spend**. Azure
billing reconciliation is still pending; don't report the reserve as a bill.

Private evidence root (0700/0600, never publish secrets):
`~/.local/share/netclaw/r10-execution-20261114/`.
Important files: `full-border-ubuntu-validation.json`, `preflight-full-border.json`,
`p2-full-vm.json`, `p2-full-bootstrap.log`, both baseline inventories, SSH control
proofs, cleanup receipts, `dns-cleanup.json`, and final cleanup inventory.
Private ledger: `~/.local/share/netclaw/r10-ledger.json`.
The old private `p2-generation` is spent diagnostic material, **not a deployable
resume point**. Generate new identities/state and re-review a fresh plan.

Cleanup completion and final estimated usage are appended below after verification.
The run's launchd cleanup watchdog must be unloaded only after zero owned cloud
resources are observed. Do not reactivate its old deadline/manifest.

Credentials remain in existing private owner env files. Do not echo them or place
them in argv. Repo `.env` holds Anthropic; `~/.openclaw/.env` holds GoDaddy PAT and
NetBox credentials. NetBox device27 read and DNS account access were verified.
GAIT branch: `diagnose-azure-vm-spec198-20261114`; stop/cleanup is recorded there.


## Final cleanup — verified 2026-11-14T16:58:59.463922+00:00

- Both resource groups `rg-nc198-p2-single` and `rg-nc198-p2-full` are absent.
- Azure resource/group inventories show **zero Spec198 resources**, including
  VM disks, static public IPs, NICs, NSGs and VNets. The owned `nc198-25usd`
  subscription budget alert was also removed; recreate it before a resumed run.
- GCP inventories show zero owned instances, disks, addresses, networks, subnets
  or firewalls. No GCP creation occurred in this session.
- GoDaddy `nne1-689f25.automateyournetwork.com` A record and its ACME TXT are absent.
- `com.netclaw.r10-20261114-cleanup` was unloaded and confirmed absent from
  launchd; its plist is archived as `cleanup.plist.disabled` in private evidence.
- Both ledger VM entries are closed. Conservative VM/disk/IP rate accounting
  totals **USD0.0593**, excluding the USD5 unspent reserve. This is an estimate,
  not a reconciled Azure invoice; usage/billing data may arrive later. No hosted
  model calls were made. Unrelated owner resources and private credentials remain.
- Private diagnostic artifacts are retained locally for audit, with no running
  deployment or automation. Do not replay their identities, old plans or deadline.

Final receipts: `cleanup-inventory.json`, `cleanup-summary.json`, `dns-cleanup.json`.
Owner stop is fulfilled. Spec198 application/HA/mesh work remains paused/incomplete.


## Update 2026-11-15 (run r10c): phase 1 PROVEN, HA next

One full Azure Border + hosted-model NetBox member proven (see verification.md 2026-11-15 sections). Owner-GUI items outstanding: VS Code owner-client journey (formal harness `labs/ha/client_qualification.mjs`, needs Code 1.109 + built extension, no publish) and a Mac subnet member (needs the confined local model stack). Source fixes this session: `r10_node_run.py` (maxTokens, guard token env), `r09_vm_enroll.py` (NC_STATE), `ha-r10-openshell-provider.sh` (PTYPE). Provider profile must carry `auth_style: header`, `header_name: x-api-key`. Operational notes: failed member results keep a member-wide fence (re-enroll a fresh identity); Docker Desktop must be running for the Mac member; ACME needs an exec wrapper and `--dns.propagation-wait`.


## Update 2026-11-15 (end of session): HA built and proven in part, then torn down

**Proven**: one full Azure Border + NetBox member (r10c); three sandboxed Azure Borders as one HA group with operations completing through nne1 and ew1 (r10d). **Unproven**: ase1 ingress completion, completed operation after leader loss, Mac subnet member, VS Code owner-client journey, GCP, six-Border mesh, cross-HA execution (needs a security-reviewed design).

**HA build recipe (all manual so far; worth scripting before the next run)**: preflight and budget alert; run-init watchdog; `R10_AZ_REGION_EW1=eastus2 R10_AZ_REGION_ASE1=swedencentral ha-r10-phase.sh up p3-ha nne1 ew1 ase1` (peering is automatic); create a private DNS zone `r10-<YYYYMMDD>.azure.internal` with A records azca/azus/azse linked to the three VNets; host bootstrap on each VM (`ha-r09a-vm-bootstrap.sh all`, parallel); `R10_ADMISSION_MS=4500 r10_prepare.py prepare --node nne1=int,pub,azca.<zone> ... --state-dir /sandbox/nc182 --sandbox`; DNS A records (`ha-dns-godaddy.py`), lego DNS-01 per node with an executable EXEC_PATH wrapper and `--dns.propagation-wait 90s`; per node `r09a_policy` (spec: two remote voters as etcd and peers, resolve map to private IPs), `r09_workspace render/pack`, `r09_hud_pack`, `r10_payload`; image build on each VM (context from `r09a_image.py context`); provider profile with `auth_style: header` and `header_name: x-api-key` then `PTYPE=nc183-anthropic ha-r10-openshell-provider.sh`; etcd stage on each host, all three together; sandbox created without START (`ha-r10-node-recreate.sh` minus the START line); authority bootstrap once from nne1 with `NC_ETCD_HOST=azus.<zone>`; enroll members in one outage window (sandbox without START, upload `r09_vm_enroll.py` + member.json + etcd-owned.json, run with `NC_STATE=/sandbox/nc182`, 25 s between enrollments, then START nne1 first); run members on the Mac with Docker Desktop up and warm NetBox before each operation. Each failed operation fences its member, so enroll several spares.

**Release gate unchanged**: nothing published or pushed; source is uncommitted on `198-azure-multicloud-ha`.


## Update 2026-11-15 (build script): the HA group recipe is now scripted (dry-run verified only)

`scripts/ha-r10-build-group.sh` codifies the r10d recipe for ONE three-Border group, Azure or GCP: `PROVIDER=azure|gcp GROUP=az|gc R10_RUN_ID=<id>-YYYYMMDD bash scripts/ha-r10-build-group.sh [--dry-run] <step>`, steps `nodes zone bootstrap prepare dns cert policy-payload image provider etcd sandbox authority enroll-members start status` (`plan` prints the list). Naming/spec logic lives in `labs/ha/r10_group.py` (tested, and cross-checked against `r09a_policy.build_policy`): Azure uses the private-zone names `az{ca,us,se}.r10-<date>.azure.internal`; GCP uses GCE zonal internal names `<vm>.<zone>.c.<project>.internal` (already accepted by `GCE_INTERNAL`, no zone to create) with the exact private-IP `resolve` map. Admission defaults to `R10_ADMISSION_MS=4500`. `dns` and `cert` refuse without `R10_GO_DNS=1` (public DNS). Secrets are read at run time (GoDaddy token via `write-env.py --get`, Anthropic key over stdin in `ha-r10-openshell-provider.sh`), never printed.
GCP path changes: `ha-cloud-gcp.sh` now defaults to Ubuntu 24.04 (the bootstrap's Landlock gate rejects Debian 12), a 40 GB disk, `run-id` label (from `R10_RUN_ID`) and network tag `nc198-<phase>`, plus `cloud_firewall` (`nc198-<phase>-owner` from `R10_SSH_ALLOW_CIDR`, `nc198-<phase>-mesh` for etcd/peer traffic) that `ha-r10-phase.sh up --provider gcp` runs first and `down` removes. Use `GCP_VM_PREFIX=nc198-<phase>` (the build script enforces the `nc198-` prefix) and `R10_SIZE=e2-standard-2` (the new GCP default; e2-medium is too small).
Watchdog: `ha-r10-run-init.sh <run> <hours> [rg-nc198-...] [--gcp-project P [--gcp-firewall nc198-...]]` writes a manifest with an optional `gcp` scope; `labs/ha/r10_watchdog.py` deletes only instances/addresses labelled `netclaw-spec=198` + `run-id=<run>` whose names start with `nc198-`, and exactly the listed `nc198-` firewall rules (firewall rules cannot carry labels). `ha-r10-run-fini.sh` also checks GCP when `R10_GCP_PROJECT` is set.
NOT live-verified: nothing here ran against a cloud. The provider step's order (`profile import` of the header-auth profile, then `provider create --type nc183-anthropic`) differs from the hand run (create, then export and `profile update` with `resource_version`); the GCP firewall/Ubuntu/IAP path, `step_nodes` private-IP lookups, and the per-step parallel `ssh`/`scp` quoting on GCP are untested; GCP VMs get ephemeral public IPs (DNS A records go stale after a stop); the member files for `enroll-members` and the guard directory are inputs the script does not create; the first live run will need fixes. Tests: `labs/ha/test_r10_group.py`, `test_r10_build_group.py` (dry-run of all steps on both providers, no-secret and no-write checks, watchdog ownership), plus existing driver/ledger/preflight tests (40 pass).

## Update 2026-11-16: mesh built twice, federation fixed, torn down
`scripts/ha-r10-mesh-up.sh` builds both three-Border groups in parallel (Azure `az`, GCP `gc`, run ids `AZ_RUN`/`GC_RUN`, `R10_HOURS` caps the reserved window so the ledger projection stays under the USD 15 pause), `ha-r10-members.sh` builds/starts members, `labs/ha/r10_ops.py` drives operations (`catalog`, `op`, `sweep`, `matrix`), and `ha-r10-teardown-all.sh` deletes everything and prints the verification block. The build script has `kill-node`, `start-node`, `rotate`, `peer-fw` steps. Proven: follower-ingress federation catalog, relay with re-authorization, takeover (epoch 33 -> 85), certificate rotation, one completed cross-cloud subnet operation. Not proven: completed Azure->GCP operation and all-follower cross-group operations with durable ACKs (member-side admission refusals on an unstable operator link; see verification.md). Before any new run: use a stable network (wired or good Wi-Fi), keep the Mac awake (the member processes die on sleep), restart Docker Desktop if container egress to api.anthropic.com times out, start fewer members, and consider the nearest-Border admission change. A durable venv for the tooling is `~/.local/share/netclaw/r10-venv` (py3.10).
