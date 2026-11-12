# NetClaw in GCP

Run NetClaw **Borders** and **Members** in Google Cloud, on-prem, or a mix, and build a highly available or distributed **Risk**.

> ## !! NOT BEHIND ANY AUTHENTICATION !!
> A NetClaw deployment in GCP has NO sign-in, NO users and NO access control today.
> Anyone who can reach a Border or Member endpoint URL can use it.
> Keep every URL and IP address private. Do not publish, paste or share them.
> Users, SSO and RBAC are a much later roadmap phase (R15-R17).
> Experiment freely (GCP, on-prem or a mix, HA Risk, distributed Risk) with this limit in mind.

(The text above is `scripts/lib/gcp_warning.txt`, shown identically by the installer, the VS Code command and the CLI.)

## What you can build

| Topology id | Shape | Typical use |
|---|---|---|
| `gcp-border` | One Border in GCP | Try a cloud Border; attach members later |
| `gcp-member` | One Member in GCP | Add a cloud capability to any Border |
| `gcp-border-onprem-members` | Border in GCP, on-prem Members | Cloud front door, devices stay on-prem (pyATS, CML) |
| `onprem-border-gcp-members` | Two Members in GCP for an on-prem Border | Cloud-hosted capability behind your own Border |
| `ha-risk` | Two Borders + etcd witness, one region | One execution authority with failover |
| `distributed-risk` | A Border in each of three regions | Region-loss tolerance; **needs published client builds for multi-region exposure (R09 gate)** |

A **Border** fronts a Risk and takes part in HA; each Border has its own identity (key, certificate, etcd membership), so deleting and recreating one creates a *new* identity. A **Member** provides capabilities and attaches to a Border.

## Prerequisites

- A GCP project you administer, with billing. NetClaw never creates projects or billing accounts.
- The `gcloud` CLI, logged in (`gcloud auth login`).
- Compute, IAM and IAP APIs enabled: `gcloud services enable compute.googleapis.com iam.googleapis.com iap.googleapis.com --project YOUR_PROJECT`
- macOS or WSL2 Ubuntu (native Windows is a read-only gate).

## Deploy (three equivalent paths)

All paths run the same tool, `scripts/netclaw-gcp.py`, so choices, warning and gates are identical.

1. **Installer TUI**: `./scripts/install.sh` and answer yes to *Deploy a NetClaw Border or Member to Google Cloud now?*
2. **VS Code**: open your NetClaw checkout, run **NetClaw: Deploy a Border or Member to GCP** from the Command Palette. It shows the warning, collects choices and opens a terminal with the plan.
3. **CLI / assistant / Claw Plan flow**:

```bash
python3 scripts/netclaw-gcp.py topologies
python3 scripts/netclaw-gcp.py plan --topology gcp-border --project YOUR_PROJECT \
  --region us-central1 --https-cidr YOUR.IP.ADDR/32          # asks you to type 'yes' to the warning
python3 scripts/netclaw-gcp.py apply --deployment ID --plan-sha256 HASH --confirm-cost
python3 scripts/netclaw-gcp.py bootstrap --deployment ID    # prepares the nodes over IAP SSH (Node, uv, checkout)
```

`plan` makes only read calls: it checks your login, project access and enabled APIs, then prints every resource, location, an **estimated** monthly and hourly cost, and a plan hash. `apply` refuses without that hash and `--confirm-cost`. A re-run converges instead of duplicating.

## What the plan creates (and why)

Per deployment (id `ID`, every name starts `nc-ID-`, label `netclaw-deployment=ID`): a custom VPC and subnet(s) with Private Google Access; a dedicated least-privilege service account (logging and monitoring write only, no keys); firewall rules (SSH only through IAP, HTTPS 443 only from **your** CIDR, iN2N 7444 public because it is mutual-TLS with pinned keys, cluster ports internal only; the public rules are logged); shielded VMs with OS Login; static IPs for Borders; for an HA witness, no external IP plus Cloud NAT. These come from the adopted items in the [R09B survey](../specs/192-gcp-completeness-survey/survey.md), which stays a reference.

A **budget alert is not created automatically**: set one in the console (Billing > Budgets).

## Attach on-prem Members

For mixed topologies, create the on-prem side with the Claw Plan Member flow ([Claw Plan](CLAW-PLAN.md), [federation guide](N2N-FEDERATION-GUIDE.md)) and enroll it to the GCP Border. Keep the Border URL private.

## Cost (estimates only)

Order-of-magnitude public list prices, not a billing quote; `plan` prints the figure for your exact choice.

| Topology | About, while running |
|---|---|
| `gcp-member` | ~$29/month |
| `gcp-border` | ~$56/month |
| `ha-risk` | ~$125/month (~$0.17/hour) |
| `distributed-risk` | ~$170/month |

Teardown stops all charges. Anything left running is billed.

## Teardown

```bash
python3 scripts/netclaw-gcp.py teardown --deployment ID                          # lists exactly what it would delete
python3 scripts/netclaw-gcp.py teardown --deployment ID --confirm-list-sha256 HASH
```

It deletes only resources carrying that deployment's prefix/label (never anything else in the project) and then verifies that none remain.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `no active gcloud login` | `gcloud auth login` |
| `service ... is not enabled` | run the `gcloud services enable` line it prints |
| `0.0.0.0/0 is refused` | pass your own CIDR to `--https-cidr`; there is no authentication |
| Apply stopped with `FAILED` | check quota/org policy for the region, then re-run `apply` (it converges) or `teardown` |
| Org policy forbids external IPs | use a project/folder that allows them for Borders, or an on-prem Border with GCP Members |

## Known limits (honest)

- No authentication, users, SSO or RBAC (R15-R17).
- `bootstrap` prepares each node (Node.js from a checksum-verified download, uv, a NetClaw checkout). Running `./scripts/install.sh` on the node is interactive (OpenClaw onboarding needs a TTY and your provider choices); `bootstrap` prints the exact `gcloud compute ssh -t` line. Enrolling the node into your Risk is the Claw Plan Member/Border flow. The HA sandboxing stack (OpenShell/DefenseClaw) validated in R09A is not installed by `bootstrap`.
- HA and distributed topologies provision the infrastructure and were validated at the coordination layer (a 3-voter etcd across both Borders and the NAT-only witness elected a leader, survived leader loss, refused writes without quorum and recovered). Starting the NetClaw Border HA authority on those nodes still uses the operator-run R09 tooling; the installer does not automate it yet.
- Load balancers, Cloud Armor and managed certificates were rejected or deferred by the survey.
- Cost figures are estimates.
- Distributed Risk exposure needs owner-approved published client builds.
