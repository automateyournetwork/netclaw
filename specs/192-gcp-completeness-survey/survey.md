# R09B: GCP completeness survey

**Status**: Draft for owner review (gate before R10). Nothing here is built, billed or published.
**Inputs**: `docs/roadmap/issue-310/briefs/R09B-gcp-completeness-survey.md`; R09A evidence (`specs/185-openshell-defenseclaw-gcp/{verification,cost-model}.md`, `scripts/ha-r09a-deploy.sh`); R09 admission findings (`specs/182-multi-region-ha-borders/live-evidence.md`).
**Cost basis**: all figures are order-of-magnitude **estimates** from public list prices, not a catalog query. R09A's cost model queried the Billing Catalog API; repeat that for any adopted item before G1.

## What R09A actually deployed (the baseline being completed)

| Area | Today |
|---|---|
| Compute | 2 Borders `e2-standard-2` + 1 etcd witness `e2-small`, one region, own VPC, ~$0.20/h (~$147/mo if left up) |
| Ingress | Firewall `tcp:443,7444` from `0.0.0.0/0` to Borders (HUD and iN2N); cluster/etcd ports (`2379-2380,12379,7443`) VPC-internal only; SSH only via IAP range `35.235.240.0/20` |
| Identity | IAP TCP tunnelling for SSH; no dedicated service account, no OS Login configured in the deploy script |
| Secrets | Provider key injected at egress by OpenShell (placeholder in sandbox); GoDaddy token and other credentials handled out-of-band by the operator |
| Egress | Public IPs on every VM; egress allow-list enforced inside OpenShell policy only, nothing at VPC level |
| DNS/certs | GoDaddy A records plus lego DNS-01 |
| Images | Built on each VM; no registry |
| Ops | Manual `status`, evidence exported by hand; no alerting, no budget |
| Recovery | Manual rebuild (three full teardown/rebuilds proved it works) |

## Constraints from the HA findings that shape every decision

1. **Admission window is narrow.** The member model handoff accepts elapsed time in `[admission_ms-3000, admission_ms-250)`. Anything that adds variable latency or retries in the Border data path (an L7 proxy, a Cloud Armor inspection hop) can push operations outside it. R09A measured 17-19 ms per sandbox hop, which is fine; an extra proxy tier must be measured the same way before adoption.
2. **iN2N/NCFED uses pinned-key mutual TLS with ALPN** on 7444. Anything that terminates TLS in front of a Border breaks the pinned identity. Only L4 passthrough is compatible.
3. **Each Border is a distinct identity** (key, certificate, etcd membership). Automation that silently recreates a VM creates a new identity and a membership change, not a replacement.
4. **Follower-takeover timing during leader upgrade is undiagnosed** (epoch 15 to 17). Health-check-driven restarts could amplify it.
5. **R09 client gate**: multi-region exposure still needs owner-approved published client builds. Nothing in this survey changes that.

## Decisions

Legend: **Adopt** = scoped follow-on work; **Defer** = valid but not before Azure; **Reject** = does not fit this deployment.

| # | Candidate | Problem it solves here | Est. cost | HA / admission interaction | Decision |
|---|---|---|---|---|---|
| 1 | Pooled load balancer, one hostname | Single entry name for clients | $18+/mo per forwarding rule plus data | Hides which Border is reached, but each Border has its own pinned identity and clients already fail over from the manifest endpoints. L7 types terminate TLS and break pinned mTLS. A passthrough Network LB would be compatible but adds a hop inside the admission window and a health signal that cannot tell leader from follower. | **Reject** pooled hostname for iN2N. Keep per-Border DNS names. |
| 1b | Health-checked endpoints per Border | Know when a Border is unreachable | Free (health checks) to a few $/mo | None if used for monitoring only | **Adopt as monitoring** via uptime checks (item 9), not as traffic steering. |
| 2 | Cloud Armor / edge rate limiting | Abuse of public 443/7444 | Enterprise tier ~$200/mo plus rules; needs an LB in path | Requires an LB, which item 1 rejects. 7444 is already mTLS-authenticated and 443 is the real exposure. | **Defer.** Instead: restrict the HUD source ranges now (item 6) and revisit when the HUD has sign-in. |
| 3a | OS Login | Per-person SSH identity and audit instead of project keys | Free | None | **Adopt.** |
| 3b | Dedicated least-privilege service account, no long-lived keys | VMs currently use the default compute identity | Free | None | **Adopt.** Scopes limited to logging, monitoring, Secret Manager read, Artifact Registry read. |
| 3c | IAP for the HUD (HTTPS) | Sign-in before HUD | Needs an HTTPS LB (see item 1) | Same objection as item 1 | **Defer** with item 2. |
| 4a | Secret Manager | Provider key, DNS credential and per-node secrets are placed by hand | ~$0.06/secret-version/mo plus access ops, under $2/mo | Fetch at start through the service account; OpenShell still injects at egress, so the sandbox never sees the value. | **Adopt.** Audit-log secret access. |
| 4b | Cloud KMS / CMEK | Customer-managed disk and secret keys | ~$1/key/mo plus ops | None | **Defer.** Google-managed keys are adequate for the validation and early production stages. |
| 5a | Cloud NAT and no external IP on the witness | Witness needs egress only (packages, images), not inbound | ~$1-2/mo plus ~$0.045/GiB; removes a public IPv4 | Witness is VPC-internal for etcd; unaffected | **Adopt** for the witness. |
| 5b | Cloud NAT for Borders | Borders need static public IPs for inbound anyway | n/a | Static inbound IPs are required by DNS | **Reject**; keep static IPs. |
| 5c | VPC egress allow-list (FQDN firewall policy) | Defence in depth under OpenShell | Firewall Standard tier fees | OpenShell already enforces the allow-list and is the audited control | **Defer.** Enable Private Google Access (free) alongside item 5a. |
| 6 | Firewall policy structure | Public rule is wide; no logging | Free (logging adds small log volume) | None | **Adopt**: keep 7444 public (peers are anywhere, protected by mTLS); restrict 443 to owner-approved ranges; use a network firewall policy rather than loose rules; log the public rule. Keep the `nc*-` ownership prefix for teardown. |
| 7a | Managed instance group autohealing | Automatic VM replacement | VM cost only | Replacement creates a new identity and etcd membership; health-triggered restarts could worsen the open takeover-timing issue | **Reject** for Borders and witness. |
| 7b | VM restart/maintenance policy and disk snapshots | Survive host events; recover Border state | Snapshots ~$0.05/GiB-mo, a few $/mo | Restart keeps identity. Snapshot is state backup, restore is an owner decision | **Adopt** (automatic restart, live migrate, daily snapshot schedule). |
| 8a | Budgets and alerts | Left-running mistake (~$147/mo) | Free | None | **Adopt** (budget alert at low thresholds; the owner has said teardown, not a cap, is the control). |
| 8b | Ops Agent (logs, metrics) and alert policies | Today failures are found by hand | Free tier covers expected volume | Alert on leader absent, `no_quorum`, certificate expiry, disk, process down. Alerts only, no remediation. | **Adopt.** |
| 8c | Uptime checks on `/api/hud/posture` | External view of each Border | Free tier | Read-only GET | **Adopt.** |
| 8d | DefenseClaw audit export to Cloud Logging | Durable, searchable audit; today exports are manual | Log ingestion beyond free tier | R09A showed zero secret hits in OCSF exports | **Adopt**; retention-lock **defer**. |
| 9 | Cloud DNS delegated sub-zone + lego `gcloud` DNS-01 | Removes the long-lived GoDaddy token from the deployment; same pattern exists as Azure DNS and Route 53 | ~$0.20/zone/mo plus queries | Names change (new sub-zone), so peers re-pin names. Plan once, before more peers exist. | **Adopt**, with the parent-zone NS delegation as a one-time owner action at the registrar. |
| 10 | Google-managed certificates | Cert lifecycle | Free but LB-only | Needs an LB; Borders need certificates they control inside the sandbox | **Reject.** Keep lego. |
| 11a | Artifact Registry with images built once and pulled by digest | Images currently built on every VM; stale-artifact hazard seen in R09A rebuild | ~$0.10/GiB-mo, about $1/mo | Pins OpenShell 0.1.7, DefenseClaw 1.0.4 (checksum), image digest per node | **Adopt.** |
| 11b | Shielded VM (secure boot, vTPM, integrity monitoring) | Boot integrity | Free | OpenShell/Docker compatibility must be verified once | **Adopt**, verify first. |
| 11c | Org Policy constraints (no SA key creation, require OS Login, shielded VM) | Make items 3 and 11b non-optional | Free | None | **Adopt** if the project sits in an organization. |
| 11d | OS Config patch management | Unattended OS updates | Free tier | Patch reboots interact with quorum | **Defer.** Patch by rebuild or manually staggered. |
| 12 | Confidential VM, VPC Service Controls | Not requested, no data-exfiltration boundary need identified | Premium | None | **Reject.** |

## Cost of the adopted set (estimate)

Baseline ~$147/mo continuous (e2-standard-2 x2 + witness, static IPs). Adopted additions are roughly **$6-12/mo**: Cloud NAT ~$2, snapshots ~$3-5, Secret Manager ~$1, Artifact Registry ~$1, Cloud DNS ~$0.5, logging above free tier a few dollars. The validation pattern is unchanged: build, validate, tear down; a 6-hour window stays near $2.

## Recommended GCP reference deployment (what R10 and R12 mirror)

1. Per-Border static IP and DNS name; no pooled hostname. L4/L7 balancers are not in the Border path.
2. Dedicated service account per role, OS Login on, IAP TCP for admin, Secret Manager for secrets, Org Policy where available.
3. Network firewall policy: public 7444, restricted 443, VPC-internal cluster plane, logging on the public rule.
4. Witness with no external IP behind NAT and Private Google Access.
5. Images built once, stored in a registry, pulled by digest; shielded VMs.
6. Delegated cloud-native DNS sub-zone with lego DNS-01; no long-lived registrar credential.
7. Ops Agent, uptime checks on the posture endpoint, alerting (no auto-remediation), DefenseClaw audit export, budget alerts, snapshots.
8. Recovery is rebuild-and-rejoin by procedure, not autohealing.

**Cross-cloud mapping**: service account to Azure managed identity / AWS IAM role; Secret Manager to Key Vault / Secrets Manager; Cloud NAT to NAT Gateway; Cloud DNS to Azure DNS / Route 53; Artifact Registry to ACR / ECR; Ops Agent and uptime checks to Azure Monitor / CloudWatch; firewall policy to NSG / security groups. Items 1 and 7a are rejected on HA-identity grounds that are cloud-independent.

## Open questions for the owner

1. Is the project inside a Google organization (affects Org Policy and some IAP options)?
2. Approve moving to a delegated Cloud DNS sub-zone now (renames the Borders) or keep GoDaddy until after R12?
3. Which source ranges may reach the HUD on 443 until it has sign-in?
4. Should HUD sign-in plus IAP/Cloud Armor become its own follow-on spec, since it depends on the LB question?

## Follow-on scoping (nothing started)

Suggested specs after approval: (a) identity, secrets and firewall hardening (items 3, 4a, 6, 11b, 11c); (b) observability and budgets (8); (c) registry-based images and snapshots (7b, 11a); (d) DNS sub-zone migration (9); (e) witness NAT (5a). Each needs a catalog-priced estimate and owner approval before any billed resource.
