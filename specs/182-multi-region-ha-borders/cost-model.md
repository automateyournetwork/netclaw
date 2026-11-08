# Cost model (ESTIMATE, +/-15%; verify against the Cloud Billing catalog before G1)

Monthly, 730 h, on-demand, no committed-use discounts. Prices are approximate list prices and differ slightly by region.

## Alternative shape (not needed now): Borders e2-standard-2. Only if a local model were added.

| Item | Qty | Unit (USD/mo) | Total |
|---|---|---|---|
| Border VM e2-standard-2 (NA-NE1, EW1, ASE1) | 3 | ~49-55 | ~156 |
| Border boot/data disk pd-balanced 40 GB | 3 | ~4.0-4.8 | ~13 |
| Static external IPv4 (in use) | 3 | 3.65 | ~11 |
| NetBox VM e2-medium + pd-balanced 30 GB | 1 | ~28 | ~28 |
| NetBox static IPv4 | 1 | 3.65 | ~4 |
| Cross-region/continent egress (est. 40 GB/Border/mo) | 3 | ~4-8 | ~18 |
| Disk snapshots (weekly, 40 GB x 4, retained 4) | 4 | ~1.5 | ~6 |
| Logging/monitoring (free tier) | - | 0 | 0 |
| **Total new environment** | | | **~236** |
| Old environment while it remains (e2-small, 20 GB pd-standard, 2 IPs) | | | ~25 |
| **Total during overlap** | | | **~261** |

Headroom to $300: ~64 during overlap, ~64 after teardown plus teardown savings.

## SELECTED shape: Borders e2-medium (owner: foundation model via API, no Ollama on Borders)
Border VM ~25 each (75), disks 13, IPs 11, NetBox 32, egress 18, snapshots 6 = **~155**; ~180 with the old VM.

## Notes
- IPv4 external addresses are billed (in use and reserved). The old reserved-unused IP `34.47.13.89` costs about $7/mo reserved and is a teardown candidate (owner decision).
- Egress is the least certain line: etcd and NCFED traffic is small, but model/HUD traffic and WAN tests can raise it. A billing budget alert at 50/80/100% of $300 is part of the deploy task.
- Anthropic API usage is separate from this GCP estimate.
- Nothing is created until the owner confirms this table (FR-021).
