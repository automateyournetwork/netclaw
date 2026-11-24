# NetClaw in Azure

Run NetClaw **Borders** in Microsoft Azure, alone or as a three-region **HA group**, attach **Members** to them, and (with the
[multi-cloud mesh](NETCLAW-MULTICLOUD-MESH.md)) pair them with a GCP group. Azure is the second cloud after [NetClaw in GCP](NETCLAW-IN-GCP.md).

> ## !! NOT BEHIND ANY AUTHENTICATION !!
> A NetClaw deployment in Azure has NO sign-in, NO users and NO access control today.
> Anyone who can reach a Border endpoint URL can use it.
> Keep every URL and IP address private. Do not publish, paste or share them.
> Users, SSO and RBAC are a much later roadmap phase (R15-R17).
> Experiment freely (Azure, GCP, on-prem or a mix, HA Risk) with this limit in mind.

(The text above is `scripts/lib/azure_warning.txt`, shown identically by the installer step, this guide and the README.)

## How Azure differs from GCP

GCP has an interactive deployer (`scripts/netclaw-gcp.py`, installer TUI, VS Code command). **Azure is an operator path**: a
cost-capped set of scripts that builds the same sandboxed Border (OpenShell + DefenseClaw + guarded gateway + workspace + HUD)
that R09A proved on GCP. The installer offers a read-only Azure preflight and prints the exact commands; it never creates a
billable resource by itself. Every billable step needs your explicit go (`R10_GO=<phase>`).

| Phase | Shape | What it proves |
|---|---|---|
| `p2-single` | one Border (Canada Central) | a full Border: trusted HTTPS HUD, workspace, guarded gateway, OpenShell, DefenseClaw, a guard refusal, a real member call |
| `p3-ha` | three Borders (Canada Central, East US 2, Sweden Central), 3-voter TLS etcd over global VNet peering | the Spec 179/182 HA behavior on Azure: operations through every Border, leader loss, rejoin |
| `p4-mesh` | an Azure group and a GCP group together | the [multi-cloud mesh](NETCLAW-MULTICLOUD-MESH.md) (cross-group execution is a separate security-reviewed design) |

Live acceptance and final teardown/cost evidence are in [Spec198 closure](../specs/198-azure-multicloud-ha/closure-20261124.md). All six local/cross-group ingresses, the physical GCP member, actual successor, native clients and fail-closed guard passed; the recorded recovery limits remain explicit.

## Prerequisites

- An **Enabled** pay-as-you-go subscription: `az login`, then `az account show --query state` must print `Enabled`. A "Warned"
  subscription cannot create resources. Multi-factor sessions expire; re-run `az login` if a call returns `AADSTS50076`.
- `~/.openclaw/.env` holding `GODADDY_PAT` (DNS-01 certificates and A records), `NETBOX_URL` and `NETBOX_TOKEN` (the NetBox member);
  `ANTHROPIC_API_KEY` in the repo `.env` (a dedicated, spend-capped key). Names only: see `.env.example`. Never paste values into chat or argv.
- Your public address as a `/32` in `R10_SSH_ALLOW_CIDR` (it changes when you change networks; re-check before each run).
  An SSH key pair at `~/.ssh/id_ed25519` (override with `AZ_SSH_KEY`; the `.pub` must sit beside it).
- `lego` (ACME), Docker Desktop on the Mac that hosts members, and a Python 3.10+ venv with the image's pinned packages (`R10_PY`).
- A domain you control at GoDaddy. Each run uses fresh names `<code>-<id6>.<your domain>`.

## Regions, size and price

| Region | Code | Linux compute (USD/hour, validated) |
|---|---|---|
| Canada Central `canadacentral` | `nne1` | 0.1010 |
| East US 2 `eastus2` | `ew1` | 0.0908 |
| Sweden Central `swedencentral` | `ase1` | 0.0970 |

Image **Ubuntu 24.04 amd64** (`Canonical:ubuntu-24_04-lts:server:latest`), size **`Standard_D2as_v7`** (2 vCPU, 8 GiB), a 40 GiB
`StandardSSD_LRS` disk, a static Standard public IP. OpenShell requires Landlock (the bootstrap checks kernel ABI 8); Debian 12
is not suitable. West Europe is blocked for new customers and Southeast Asia may be restricted, so the code names map to
Canada Central, East US 2 and Sweden Central. **You must export the overrides** because the driver's built-in defaults differ:

```bash
export R10_AZ_REGION_EW1=eastus2 R10_AZ_REGION_ASE1=swedencentral
export R10_SIZE=Standard_D2as_v7          # the phase script defaults to a smaller size that does not run the full stack
export R10_RATE_USD_PER_H=0.15            # ledger rate per VM (compute plus disk/IP allowance)
```

Validation does not reserve capacity: re-run the preflight before every run.

## Cost control (hard rules)

- **$25** ceiling for the whole programme, **pause and ask at $15** (`labs/ha/r10_ledger.py`; the ceiling cannot be approved past).
  Historical reserves are retained; the final November24 run additionally held USD3.50 for provider/transfer/cleanup. Reserves are not measured billed spend and must never be reduced to bypass a gate.
- A subscription budget alert (`nc198-25usd`, 50 percent and 80 percent) must exist before the first billable phase. It warns; it
  does not stop spending. Creating or removing it needs an interactive `az login`.
- A launchd **watchdog** (`scripts/ha-r10-run-init.sh <run-id> <hours> <resource-group...>`) deletes the run's resource groups
  after the deadline. It runs on your Mac, so the Mac must be awake and online; it is not a provider spending cap.
- One resource group per phase, tagged `netclaw-spec=198` and `run-id`, so teardown is a group delete plus a tag-based check.
- Order of magnitude: three D2as_v7 VMs run about USD 0.45 per hour. Check `python3 labs/ha/r10_ledger.py status` any time.

## Run it

```bash
bash scripts/ha-r10-preflight.sh --regions canadacentral,eastus2,swedencentral --size Standard_D2as_v7 --disk-gb 40
export R10_RUN_ID=r10x-YYYYMMDD R10_GO=p3-ha
bash scripts/ha-r10-run-init.sh $R10_RUN_ID 8 rg-nc198-p3-ha                  # watchdog first
bash scripts/ha-r10-phase.sh up p3-ha nne1 ew1 ase1                           # ledger-gated VMs + VNet peering
PROVIDER=azure GROUP=az bash scripts/ha-r10-build-group.sh plan               # the ordered steps
```

`scripts/ha-r10-build-group.sh` builds one three-Border group in re-runnable steps (`--dry-run` prints every command and changes
nothing): `nodes`, `zone` (Azure private DNS names the sandbox policy accepts), `bootstrap`, `prepare` (identities, manifest, etcd
PKI; November24 qualification explicitly used `R10_ADMISSION_MS=9000`), `dns` and `cert` (need `R10_GO_DNS=1` and `R10_ACME_EMAIL`; they change public DNS), `policy-payload`
(needs `R10_GUARD_DIR`), `image`, `provider` (hosted Sonnet via the guard; the key is read at run time, stdin only), `etcd`,
`sandbox`, `authority`, `enroll-members`, `start`, `status`. Read the exact plan before running. Never replay a spent preparation, rematerialize a used identity or restart an expired watchdog. A source change requires a fresh signed preparation.

A single Border (`p2-single`) is the same flow with one node. The HUD of each Border is `https://<code>-<id6>.<your domain>`;
add it in VS Code with **NetClaw: Add Connection → Cloud Border** (see [VS Code guide](GETTING-STARTED-VSCODE.md)).

## Members (hosted Sonnet only, Ollama not required)

Members run on your Mac (Docker Desktop must be running) and **dial the Borders outbound** on 7444. Build them with
`labs/ha/r09_member.py` (`identity`, `freeze`, `python-env`, flavor env, `artifacts`, `materialize`, `validate`):

| Flavor | What it does | Needs |
|---|---|---|
| `netbox` | one reviewed `netbox_get_object_by_id` read through the hosted Sonnet guard | NetBox URL and token (demo.netbox.dev works) |
| `subnet` | the qualified native subnet summary calculator on hosted Sonnet | nothing external (stdlib, no network) |
| `pyats` | one reviewed `show version` on one IOS-XE IOL device | a reachable device and its testbed |

Enrollment is a one-shot written into the cluster ledger and needs **every Border of the group stopped** (leases expired).
`enroll-members` does this in one outage window. A **failed member result keeps a member-wide fence** (`resource_recovery_required`);
there is no automatic release and no reconciliation path yet, so enroll several spare members and a fresh identity replaces a fenced one.

## Teardown and verification

```bash
bash scripts/ha-r10-phase.sh down p3-ha nne1 ew1 ase1          # group delete, ledger stop, tag listing
bash scripts/ha-r10-run-fini.sh $R10_RUN_ID                     # unload the watchdog (only after zero resources are observed)
az group list --query "[?starts_with(name,'rg-nc198')].name" -o tsv      # expect nothing
az resource list --tag netclaw-spec=198 --query "length(@)" -o tsv        # expect 0
```

Also delete the run's GoDaddy A records (there is no delete mode in `ha-dns-godaddy.py`; use the API with your token, never printing it)
and confirm no `_acme-challenge` TXT record remains. Emergency: `az group delete -n rg-nc198-<phase> --yes`. Azure billing data can
lag by a day; reconcile the final spend against the Azure cost view, not only the ledger.

## Known limits (honest)

- No authentication, users, SSO or RBAC (R15-R17). NSGs restrict SSH and HTTPS to your address; federation ports use pinned-key mutual TLS.
- **Admission window.** The older4500ms window and fixed five-second wait failed on a stable network. November24 used a freshly signed9000ms window (`R10_ADMISSION_MS`) and manifest-derived RPC wait, with measured quorum proposal latency and all three regions retained. Slower/degraded topologies can still refuse safely; do not solve that by removing authority checks.
- **Member fence.** A failed or refused result fences its member; recover by enrolling a fresh member identity.
- **First NetBox request.** demo.netbox.dev can stall on the first request after idle; warm it before each operation. A cold Docker Desktop
  network can also fail the hosted call.
- **Operator host.** The Mac that runs the members must stay awake, plugged in and on a stable (ideally wired) network for the whole run: sleep kills the member processes and unstable Wi-Fi makes hosted-model calls fail. Keep the member count small (memory pressure) and restart Docker Desktop if a container cannot reach api.anthropic.com.
- Restarting a stopped Border needs its sandbox recreated and about three minutes before HTTPS posture is 200.
- Cross-group execution between an Azure group and a GCP group is a separate security-reviewed design; see the
  [multi-cloud mesh](NETCLAW-MULTICLOUD-MESH.md) for its status.
- The VS Code extension, mobile app and HUD builds are unpublished; publishing needs your explicit approval (release gate).
- Cost figures are estimates.
