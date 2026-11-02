# R03 cloud review — prepared, not applied

2026-11-02. Maintainer-only unreleased qualification packet. R03 has no deployed
resources. The owner's hard CAD100 total monthly lab ceiling and exact delegation
remain execution gates; a budget alert is not a spending cap.

## Source and saved foundation plan

Cloud source is integrated in `cb0846f0` and `685032b9`. OpenTofu1.13.2 / Google8.9.0
format/schema checks pass. The focused cloud tests pass, as do actual Caddy2.11.7
adapt/validate, Ubuntu24.04 systemd255 unit validation and the local Caddy error-log
secret-marker probe. Integrated cloud/role tests:53 passed plus23 subtests.

Private packet:
`~/.local/share/netclaw/roadmap-r03-20261102/foundation-review-20261102T215532Z/foundation-packet.md`.
Saved `foundation.tfplan` SHA256:
`8373323e4f7406fdb94892c74f29ccbcf3710fcf2852c36a78cdcbde4867a3eb`.
The plan creates10 isolated resources, updates/deletes/replaces0, and uses a new
private state. Project `netclaw-506315`; Montréal zone
`northamerica-northeast1-a`; run `20261102-a91adf`.

The exact10 resources are a dedicated VPC, subnet, service account, empty operator
secret, secret-only accessor binding, one reserved IPv4, IAP ingress, private-egress
deny, default-egress deny and one Shielded e2-small VM with20GiB auto-delete disk.
Ubuntu24.04 AMD64 image is pinned to `ubuntu-2404-noble-amd64-v20261024`.
Only IAP-source TCP22 ingress is initially allowed; new Internet egress is denied.
No application, startup script, DNS record, token payload, model/tool/Docker,
project-wide role or existing-resource change is in this plan.

Fixed STOP is `2026-11-04T20:55:32Z`, initially47 hours after generation. A stale
plan must be regenerated and reviewed. This file supplies no apply delegation.

## Cost and activation gates

Authenticated account CAD prices put the47h new base at approximately CAD1.63
(48h:CAD1.67). Conservative744h R01 base including its unused IPv4 is CAD37.27;
continuous R01+R03 base is CAD63.04. These exclude traffic, tax, secret operations,
other services and provider charges. Current gross accrued billing is unavailable
through the connected read-only tools. Owner billing/currency/tax clarification is
pending. No source estimate establishes compliance with the hard total ceiling.

R01's existing public egress is not finitely bounded. R03 safeguards cannot cap
that existing exposure. Any R01 traffic bound or retirement requires its own
concrete reviewed delegation. R03 STOP leaves disk/IP costs: roughly CAD6.50 per
744h attached, or CAD12.77 with an unused retained IP. Reviewed teardown is required.

Before public activation, prove on the actual GCP kernel and selected network
manager the config-free closed boot baseline, mandatory manager dependency,
one-use output-byte quota, whole-interface rate limit, fixed expiry and spent
restart refusal. Local Linux tested real DROP/TBF installation and fail-closed
paths. Docker Desktop lacks NFT_QUOTA: actual quota enforcement remains unqualified,
and no weaker fallback is authorized. The allowance is at most10GiB and the rate
at most1Mbit/s. Reboot or guard reentry deliberately closes output including IAP;
export evidence before expiry/exhaustion. Reset is a new reviewed action.

A separately saved activation plan would add only public80/443, iN2N42102 from
reverified approved member /32 sources, and outboundTCP80/443. The exact runtime,
cloud-only numeric-version/SHA-pinned secret, first-create identity, source/venv/
asset closures, owner bootstrap and DNS/TLS packet must also be reviewed. Proposed
hostname `r03-gcp-montreal.lobsternet.automateyournetwork.com` is not live.

Actual four-device evidence, export and independent inspection precede a new exact
R03-only teardown plan. No teardown execution or billable residue is accepted by
this source review. R01 state remains unchanged at SHA256
`62364e466434974c6b4f55c395ef95a9376113aa9fcf4d44518511a160643fbf`.
