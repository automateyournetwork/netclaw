> Current R01 pilot: DNS/HTTPS, foundation/runtime activation and actual IP
> relocation/recovery are verified. The owner fully delegated these changes and
> requested the full open lab HUD, Anthropic Sonnet and a scoped on-prem subnet
> demonstration. Users/SSO/RBAC remain R15–R17. Use resume.md and verification.md
> for current receipts. Earlier preparation commands below are historical;
> never replay initial activation over the running pilot.

# R01 direct-cloud pilot — 2026-11-01

The owner explicitly approved native cloud connectivity, preserving optional ngrok
for home/NAT Borders. This supersedes the earlier ngrok-only pilot proposal. No
cloud resources or public endpoints have been changed. R02/R03 are not started.

| Role | Placement | Transport and scope |
|---|---|---|
| Fresh control-only Border | New GCP Montréal e2-small Ubuntu24.04 VM | Direct TCP iN2N42101 and NCFED42102; application TLS; no model/device credentials |
| Fresh member | Isolated private Mac home | Outbound iN2N; synthetic transport probes, no device/model calls |
| Fresh external Border | Separate private Mac home and trust/consent | Initiates eN2N using a distinct identity/CA; no internal-member access |

The Mac and GCP are separate networks. Distinct local trust/consent tests enforce
independent-organization policy, but this single-owner pilot is not second-human-
organization operational acceptance. Preserve that limit in the final evidence.

The cloud foundation uses a dedicated VPC/subnet, exact VM NIC10.168.0.2, a
reserved primary IP and a second reserved IP for the relocation test. Only the
reviewed client /32 can reach42101/42102. SSH is IAP-only. No ngrok, Cloud NAT,
load balancer, public BGP/admin/gateway/MCP/model/HUD ingress or static cloud key.
The VM's workload identity can read only its new pilot secret. Secret payloads
stay out of IaC/state; explicit provisioned material is reviewed separately.

[The IaC](pilot/gcp/main.tf) creates infrastructure with labels/descriptions and
expiry. The bootstrap installs Python prerequisites and a service user; **it does
not start a NetClaw listener**. The30-day expiry stops the VM; reserved IPs, disk
and secret storage can continue to incur charges until separately approved teardown.
The project budget alert is50 units of the actual billing currency, with50/90/100%
notifications to billing-role recipients. It is an alert, not a hard spending cap.
The owner's GCP credit remains an account identifier, not a spending allowance.

## Observed prerequisites

Read-only project discovery found ACTIVE status, billing enabled and zero VMs.
Montréal northamerica-northeast1 is UP; e2-small in zone-a has2sharedvCPU/2048MiB.
Observed regional quotas:200CPUs,24instances,8in-use addresses, all usage0.
Compute/IAP/SecretManager/BillingBudgets APIs were enabled. The existing default
network/subnet/four firewall rules remain unchanged and will not be reused.
Current billing currency is CAD. None of these observations reserves capacity or
proves write authorization.

Private discovery/pricing/plan receipts are under
`~/.local/share/netclaw/spec168-direct-cloud-pivot-20261101/`; earlier read-only
GCP receipts remain in `spec168-fresh-pilot-20261101/`.

## Historical ngrok account check

At19:04:54 UTC root `.env` `NGROK_API_KEY` returned HTTP200 for complete one-page
reservation/endpoint inventories: zero reserved TCP addresses and one existing
ephemeral endpoint, unchanged. The owner confirmed Free. Root `NGROK` is the
separate agent token; earlier use as an API key returned ERR_NGROK_206. The earlier
name scan missed exact `NGROK`; that was an inspection error, not absence.
Credential-list values were omitted, so token/key account alignment was not proven.

No secret was printed, passed in argv or sent to a runtime. Receipts remain private
under `spec168-ngrok-account-check-20261101/`. Paid TCP reservations are required
only for optional ngrok qualification; they do not block the direct-cloud pilot.

## Requested cloud HUD

The IAP operator view is live at the Mac tunnel end `http://127.0.0.1:13000/`,
with matching actual on-prem member evidence. The owner superseded IAP-only
viewing with an open cloud lab URL, no login. A separate projected read-only HUD
is built and browser-tested against the real cloud feed. See the
[exact public packet](public-hud-review.md); its prospective address is
`http://34.95.60.45/`, pending activation. The private operator APIs remain loopback.

## Remaining sequence

Foundation and runtime activation, actual enrollment/reconnect, refusal checks,
owned Border restarts and IAP browser acceptance are complete. After exact
public-packet delegation, apply the one firewall create/in-place IP update,
activate the frozen viewer, verify actual relocation/CAS/explicit recovery/key
continuity/zero tasks, and capture public browser evidence. Reconcile T028/T040/T038
and stop afterR01. Teardown and later briefs require their own review.
