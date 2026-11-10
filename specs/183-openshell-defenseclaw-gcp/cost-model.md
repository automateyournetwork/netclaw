# Cost model: R09A validation topology (ESTIMATE; confirm before G1)

**Topology**: 2 Border VMs + 1 etcd witness VM, one region (`northamerica-northeast1`, Montreal), own VPC `nc183-r09a`, Ubuntu 24.04 LTS amd64, labels `netclaw-spec=183`, prefix `nc183-`.
**Pricing source**: Google Cloud Billing Catalog API (`cloudbilling.googleapis.com/v1/services/<id>/skus`, currency USD, on-demand), queried 2026-11-10 for services *Compute Engine* (`6F81-5844-456A`) and *Networking* (`E505-1604-58F8`). Rows marked **UNCONFIRMED** were not found in the catalog for Montreal and are carried from the R09 estimate or an analogous region. No committed-use or sustained-use discounts assumed. Prices drift: re-check immediately before G1.

## Confirmed unit prices (Montreal, catalog 2026-11-10)

| Item | Unit price |
|---|---|
| E2 Instance Core | $0.024013 / vCPU-hour |
| E2 Instance RAM | $0.003218 / GiB-hour |
| Balanced PD capacity | $0.11 / GiB-month |
| Static IP charge | $0.011 / hour (catalog row; in-use external IPv4 may be lower, so this is an upper bound) |
| Internet egress from Americas (rows for Zurich/Finland to Americas shown as analog; Americas-origin rows go to $0.12-$0.19 per GiB by destination) | ~$0.12 / GiB, **UNCONFIRMED for this origin** |
| Inter-zone egress inside the region | ~$0.01 / GiB, **UNCONFIRMED** (no Montreal SKU matched) |

Derived: **e2-standard-2** (2 vCPU, 8 GiB) = 2 x 0.024013 + 8 x 0.003218 = **$0.07377 / hour** (~$53.85 / 730 h).
**e2-medium** and **e2-small** are shared-core: the catalog returned no Montreal SKU for them (only a Micro row, $0.0084/h), so they are **UNCONFIRMED**: carried at ~$0.034/h (e2-medium, from the R09 estimate of ~$25/mo) and ~$0.017/h (e2-small, assumed half).

## Line items

| Item | Qty | Unit | Hourly |
|---|---|---|---|
| Border VM e2-standard-2 (selected: verified 8 GB, OpenShell gateway ~137 MB + supervisor ~49 MB + sandbox) | 2 | $0.07377/h | $0.14754 |
| etcd witness VM e2-small (etcd only; UNCONFIRMED price) | 1 | ~$0.017/h | $0.017 |
| Boot disk pd-balanced 40 GB (Borders) | 2 | $0.11 x 40 / 730 = $0.00603/h | $0.01206 |
| Boot disk pd-balanced 20 GB (witness) | 1 | $0.11 x 20 / 730 = $0.00301/h | $0.00301 |
| Static external IPv4 (Borders; witness uses an ephemeral address) | 2 | $0.011/h (upper bound) | $0.022 |
| Egress (HUD/chat/WAN tests; est. 5 GB total) | - | ~$0.12/GiB (UNCONFIRMED) | ~$0.60 one-time |
| **Total, e2-standard-2 Borders** | | | **~$0.20 / hour** |

| Window | e2-standard-2 Borders | e2-medium Borders (alt.) |
|---|---|---|
| Per hour | ~$0.20 | ~$0.12 |
| 6-hour validation window | ~$1.2 + ~$0.6 egress = **~$1.8** | ~$0.7 + ~$0.6 = ~$1.3 |
| If left running a month by mistake | ~$147 | ~$89 |

e2-medium (4 GB) is the cheaper alternative, but the R09 e2-medium Borders ran at ~1.5 GB used before OpenShell, Docker 28+ and the sandbox image; headroom is thin. e2-standard-2 is the verified shape (8 GB) and the recommendation.

## Not included
Anthropic API usage (separate); the Docker image registry (none; images are built on the VMs); DNS (GoDaddy, existing zone); the optional Cloud NAT/load-balancer items (R09B). Cost is not capped by the owner for validation; the control is **teardown right after validation**.

## Teardown list pattern (exact, owner-confirmed before deletion)
Everything created by this stage carries label `netclaw-spec=183` or name prefix `nc183-`:
- instances `nc183-border-a`, `nc183-border-b`, `nc183-witness` (and their boot disks via `--delete-disks=all`)
- addresses `nc183-ip-a`, `nc183-ip-b`
- firewall rules `nc183-*`
- subnet `nc183-sub` and network `nc183-r09a`
- GoDaddy A records `<code>-<id6>` created for this stage (list from the deploy plan)
`scripts/ha-r09a-deploy.sh teardown --confirm` lists these first and refuses anything not matching the label or prefix. The default network, `default-*` firewall rules and any resource without the label/prefix are never touched.
