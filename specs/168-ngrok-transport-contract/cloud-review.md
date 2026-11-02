> Current outcome: the exact foundation and budget-only recovery were delegated
> and applied. All11 resources verify without drift. Runtime activation was then
> delegated and completed; Mac→GCP iN2N/NCFED and IAP browser evidence now exist.
> The historical IAP-only viewer choice is superseded by the owner's open lab URL.
> See [public-hud-review.md](public-hud-review.md) for the separate final packet.
> The original saved plans below are historical and must not be replayed.

# R01 cloud foundation review — partial apply, budget recovery prepared

## Current execution status

The owner explicitly delegated the original saved plan and selected IAP HUD
access. Apply ran2026-11-01T19:41:07Z–19:42:07Z: **10 resources created**; only
`google_billing_budget.pilot` failed. No NetClaw listener or HUD was activated.
The Budget API required an explicit quota project for user OAuth credentials.
Provider configuration now sets `billing_project` to the same selected project
and `user_project_override=true`, as required by the
[provider documentation](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/billing_budget.html).

A refreshed saved plan contains **one addition, zero changes/deletions**: the
same CAD50 budget, with parameters byte-for-byte equal in the JSON plans to the
original approved budget. It is prepared, not applied:

- Private plan: `~/.local/share/netclaw/spec168-direct-cloud-pivot-20261101/budget-recovery.tfplan`
- SHA256: `05d6b8572c486d78ed8f2a17255c1bebf8046ae5669ac19965936468791bf13e`

The original approval was for an exact saved plan, so this refreshed plan is
presented for delegation before execution. Do not rerun the original stale plan.
After review, use the same private/module variables defined below:

```sh
GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)" \
  "$R01_PRIVATE/tools/tofu" -chdir="$R01_MODULE" apply \
  "$R01_PRIVATE/budget-recovery.tfplan"
```

The first apply also revealed that plan-time `-state` did not persist the apply
backend path. The0600 ignored source-directory state was preserved and moved to
private `pilot.tfstate`; the local backend is now explicitly initialized with
`-backend-config=path=.../pilot.tfstate`. This changed no cloud resource. Future
plans use that authoritative backend; never initialize a second empty state.
The failed original receipt and refreshed plan are retained. The budget alert is
not active until recovery succeeds; the created resources already incur usage.

## Original approved packet (historical; original plan is now stale)

The source pivot is approved. The roadmap driver separately reserves cloud
mutation/spend commands: “Never do any of the following yourself; prepare the
exact commands and ask me.” This packet makes the **foundation creation** concrete.
It does not claim a deployed Border, working HUD or live iN2N result.

## Frozen scope

- Project `netclaw-506315`; Montréal `northamerica-northeast1-a`.
- OpenTofu1.13.2; signed Google provider8.9.0; pinned observed Ubuntu24.04 image.
- **11 additions, 0 changes, 0 destructions** in the saved read-only plan.
  Dedicated VPC/subnet, e2-small VM/20GiB disk, primary/relocation static IPv4,
  service account, empty secret/scoped reader grant, two firewall rules, budget.
- Application ingress42101/42102 restricted to the observed owner client `/32`,
  recorded in the private tfvars/plan. Re-observe it before apply; a changed client
  address requires a new reviewed plan, not a wider firewall.
- SSH22 only from IAP35.235.240.0/20. OS Login enabled; no static cloud key or
  public HUD, BGP, gateway, MCP or model port. No ngrok resource or agent.
- Bootstrap installs Python prerequisites and an unprivileged service account.
  **It does not install/start NetClaw, upload secrets or enable inference.**
- VM stops2026-12-01T00:00:00Z. Reserved IP/disk/secret costs continue until
  separately reviewed teardown. Labels/descriptions identify R01 and expiry.
- CAD50 monthly project budget alerts at50/90/100%, excluding credits, to existing
  billing-role recipients. This is not a spending cap; credits are not presumed.

Private plan:
`~/.local/share/netclaw/spec168-direct-cloud-pivot-20261101/foundation.tfplan`

SHA256: `0b02e08b315d66751ee1318cda55035f1513223166e7e9882bff83e86b4efe78`

The source is [pilot/gcp/main.tf](pilot/gcp/main.tf); exact billing identity,
client address and image URL stay in private `pilot.tfvars.json`. Do not publish
the raw plan/state. Regeneration changes the hash and requires review again.

## Cost estimate

Conservative public list-price estimate for720hours:

| Item | USD estimate |
|---|---:|
| Montréal e2-small (0.5effective vCPU +2GiB) | 13.28 |
| 20GiB standard persistent disk | 0.88 |
| One attached external IPv4, ignoring any free entitlement | 3.60 |
| One reserved unused relocation IPv4 | 7.20 |
| Base total | **24.96** |

Traffic, Secret Manager usage, taxes and USD→CAD conversion are additional.
No load balancer or Cloud NAT is proposed. The cost estimate is not an account
quote. The authenticated billing-account API reports CAD; the Cloud Billing SKU
catalog was read in USD (33,567SKUs/7pages, private `pilot-prices-usd.json`).
[Google VPC pricing](https://cloud.google.com/vpc/pricing) gives attached and
unused IPv4 rates; [VM pricing](https://cloud.google.com/compute/vm-instance-pricing)
and the catalog identify regional compute rates. Recheck before a delayed apply.

## Operator commands

These commands are prepared for the owner. None has been run by the agent.
Use the private evidence directory and inspect both the hash and resource diff:

```sh
R01_PRIVATE="$HOME/.local/share/netclaw/spec168-direct-cloud-pivot-20261101"
R01_MODULE="/Users/john.capobianco/netclaw/specs/168-ngrok-transport-contract/pilot/gcp"
shasum -a 256 "$R01_PRIVATE/foundation.tfplan"
"$R01_PRIVATE/tools/tofu" -chdir="$R01_MODULE" show -no-color \
  "$R01_PRIVATE/foundation.tfplan"
```

The exact creation command, **only after the owner's review**, is:

```sh
GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)" \
  "$R01_PRIVATE/tools/tofu" -chdir="$R01_MODULE" apply \
  "$R01_PRIVATE/foundation.tfplan"
```

This applies only the saved plan; no auto-approve or fresh implicit plan. The
OAuth token stays in the child environment. State is bound by the saved plan to
the private `pilot.tfstate` path. Retain the apply output privately, then run
read-only inventory and compare actual state before any runtime activation.

If the owner wants the coding agent to execute a reserved command, that requires
an explicit delegation overriding the driver's “never … yourself” boundary for
this exact plan. Architecture approval and an available credential are insufficient.

## Next reviewed stage and HUD evidence

Once the foundation supplies actual IPs, freeze fresh cloud/local identities,
TLS/application trust, source archive and service/configuration hashes. Prepare
the exact IAP transfer, secret-version upload, service-start and member-enrollment
commands for review. Keep local member keys on premises. No existing runtime is
adopted. Registry routing addresses come from the observed deployment; identities
and TLS names do not come from the provider IP.

The default HUD access contract is [IAP/SSH](pilot/gcp/README.md), with prospective
browser address `http://127.0.0.1:13000/` after provisioning/tunnel verification.
**Historical prospective address:** IAP now verifies at that local tunnel end.
The owner subsequently chose an open lab status viewer without login; its exact
public-ingress packet is linked above.
R01 must deliver the verified cloud HUD view plus actual on-prem iN2N
enrollment/reconnect evidence, not just a screenshot of synthetic members.

Address relocation receives its own saved plan against actual state. Do not
change `use_relocation_address` and apply implicitly. Teardown preparation:

```sh
bash "$R01_MODULE/teardown-plan.sh" "$R01_PRIVATE/tools/tofu" \
  "$R01_PRIVATE/pilot.tfstate" "$R01_PRIVATE/pilot.tfvars.json" \
  "$R01_PRIVATE/teardown.tfplan"
```

This writes a destroy **plan only**. Export approved evidence, verify that the
plan contains only this pilot's resources, then ask for separate destruction
review. A VM stop is not teardown. All11 foundation resources exist; no resource has been destroyed.
