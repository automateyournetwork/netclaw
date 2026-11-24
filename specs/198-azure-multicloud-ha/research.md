# Research: R10 Azure

> Current resumption: [resume-20261124.md](resume-20261124.md). The owner resumed
> bounded work on November24. Its scope, budget gate and measured latency finding
> supersede the historical status, topology and sequencing below. No new live
> acceptance is implied. The binding peer contract uses ONE group per member.

## R1 VM size
**Decision**: Standard_B2s (2 vCPU, 4 GiB) by default; preflight falls back to B2ls_v2/B2als_v2 if B2s is unavailable or quota-blocked per region.
**Rationale**: R09 ran Borders on e2-medium (1 vCPU shared, 4 GiB); B2s is the nearest Azure equivalent at roughly $0.04-0.05/h. The full workspace in R09 (OpenClaw + HUD) fit 4 GiB.
**Alternatives**: B1s/B1ms (1-2 GiB) too small for the workspace; D-series costs 2-4x with no benefit.

## R2 Cost model (estimate, verify against live price API in preflight)
3 VMs x ~$0.05/h + 3 Standard static IPs x ~$0.005/h + 3 x 30 GiB Standard SSD (~$0.002/h each) + egress (cents) ≈ **$0.18-0.25/h** for the HA phase, matching R09's $0.17/h on GCP. A 12 h session including the single-Border phase is ~$3. GCP mesh phase (2 small VMs) ~$0.10/h. **Expected total under $10; ceiling $25.** VMs are deallocated (compute billing stops) whenever work pauses; disks and IPs keep billing cents until deletion.

## R3 Management access
**Decision**: public IP with an NSG that allows SSH (22) only from the operator's current public IP; 443 and federation ports as R09 requires; no Azure Bastion.
**Rationale**: Bastion costs ~$0.19/h per VNet, which is more than the whole HA stack. GCP used IAP; Azure has no free equivalent. SSH key auth only, password auth off.
**Alternatives**: Bastion Developer SKU (free tier exists but limited regions/no scp); serial console (no file transfer).

## R4 Networking
One resource group per phase containing a VNet per region (three regions cannot share a VNet), NSG, public IP, NIC, VM, disk.
**Revised after reading the R09 scripts:** etcd voters peer over *private* addresses (`r09_prepare.py` builds peers from each node's
internal IP), which GCP's global VPC routed. Azure VNets are regional, so the three VNets get distinct address spaces
(10.198.1/2/3.0/24) and **global VNet peering** (full mesh, `ha-cloud.sh azure peer`). Peering is free to create and bills only a
small per-GB transfer charge; etcd traffic is tiny. Federation (iN2N 7444, cluster 7443) stays on public IPs with pinned-key mutual
TLS exactly as in R09. The public-IP alias/DNAT shim (`ha-r09-vm-net-etcd.sh`) is still needed on Azure because the public IP is not on the NIC.

## R5 Teardown and verification
`az group delete --yes --no-wait` per phase, then poll `az group exists` and list resources by tag `netclaw-spec=198` across the subscription; also delete the GoDaddy A records for the run and verify the key file is gone. A subscription-level budget alert ($25, 50%/80%) is created once in preflight go (it is free).

## R6 Open-lab workspace exposure
R09 had an unauthenticated workspace on the internet that could spend the Anthropic key; the owner accepted it. For R10 the NSG restricts 443 to the owner's IP plus the other Borders' IPs while the key is placed, and the key must be a dedicated, spend-capped key. Federation port stays open to peer Borders only. Restating this as a default is safer than copying the R09 acceptance.

## R7 Subscription state
`az` reports the subscription "Warned" until the upgrade completes. Preflight stops on any state other than Enabled. Region restrictions on new subscriptions are common (southeastasia in particular); a blocked region is reported with a proposed substitute that needs owner approval.

## R8 Certificates and DNS
Reuse lego DNS-01 with the GoDaddy token exactly as R09; names `<code>-<id6>.automateyournetwork.com` with fresh ids per run; A records deleted at teardown. Let's Encrypt rate limits (50 certs/week per domain) are far above 3-6 certs/run.

## R9 Cross-cloud mesh
Use the existing peer federation trust (pinned keys + domain-verified TLS, features 052-066/189/190). GCP side is a single small Border (e2-medium) federating to one Azure Border, not a second 3-region group. Proof: an operation entered at the GCP Border completes on an Azure-side member (and the reverse), audited on both. GCP stood up only on explicit go.

## R10 Members
On-prem = Mac subnet-calculator member (existing `r09_member.py` subnet flavor). Cloud-hosted = hosted subnet member plus hosted NetBox member against demo.netbox.dev using the token in `~/.openclaw/.env`. No CML.
