# Spec199 Research — 2026-11-25

Two Spec Kit planning research agents inspected runtime reuse and AWS lifecycle docs read-only. Parent performed authenticated read-only checks; no cloud resource created.

## Actual account evidence
NetClaw login renewed; STS verified the intended assumed role/account privately. Ohio: zero instances, volumes, addresses and NAT gateways; one pre-existing default VPC/three subnets preserved. Standard On-Demand quota8vCPU. m7i.large/m6i.large/t3.large offered in all three Ohio zones,2vCPU/8GiB. Public Canonical Ubuntu24.04 AMI resolves to an available x86_64 image owned by099720109477, build20261120. Permission-only m7i.large launch dry-run returns DryRunOperation. None establishes capacity or runtime qualification.

Free Tier API returns FREE/ACTIVE, USD100 remaining, expiration2027-05-16. Gross reservations remain authoritative regardless of credits. Price List API on November25 returned Ohio Linux shared m7i.large USD0.1008/hour; disk/IPv4/transfer/model/safeguard costs still need exact packet pricing. Private raw receipts: `~/.local/share/netclaw/spec199-readiness-20261125/ohio/`.

Canada Central/Ireland/Singapore and diagnostic N.Virginia EC2 reads have explicit organization SCP denial p-mcrtphfx. DescribePolicy is denied. Ohio works; this is not a complete allowed-region list. Preserve requested regions count and obtain an organization-approved set before regional activation; no IAM bypass or alternate identity.

## Decisions

### D1 — Preserve current protected runtime
Decision: use r09_prepare one-voter mode, schema3 protected-role validation, r10_payload/node_run and fresh local member. Rationale: latest qualified full HUD/runtime and original-result contracts. Alternatives: old R03 GCP renderer is control-only/provider-specific; nine nodes first contradicts owner sequencing. One voter does not establish HA.

### D2 — Fresh AWS lifecycle and ownership
Decision: stdlib subprocess AWS CLI adapter, immutable account/region/run/stage/resource bindings and request digest/token. Reuse R10's audit/export patterns, not its Azure/GCP selectors/constants. Rationale: r10 ledger hard-clamps USD25 and cleanup/watchdog are provider-specific. Alternatives: blind template substitution and broad tag cleanup rejected.

### D3 — Conservative cost domains
Decision: USD100 AWS gross ceiling/pause80/reserve5; self-imposed USD10 all non-AWS ceiling under owner's small-spend direction. Reserve each full deadline plus uncertainty/cleanup; no credit subtraction or erased unknowns. Fixed-performance m7i.large is the initial candidate; T3 unlimited has additional CPU-credit exposure. Price every final packet before activation.

### D4 — Minimal network
Decision: new owned subnet/VPC/IGW, exact security rules, no NAT/LB/GPU. Inter-region private voter routing uses pairwise VPC peering only once regions qualify. Peering is non-transitive and inter-region SG rules use CIDRs/IPs. Host metadata uses required IMDSv2/hop1; containers do not need instance credentials. Rationale: preserve isolation without expensive managed transport. Alternatives: default-VPC changes, broad public voters and NAT/transit rejected.

### D5 — Idempotency and independent stop
Decision: persist create intent before send; bind ClientToken to region/AZ/subnet and digest. Unknown outcome is reconciled under original identity. DryRun only checks authorization. One-time exact-ID Scheduler stop is a proposed independent guard, subject to account validation; separate local/host guards remain. Scheduler trust SourceArn binds a schedule group. Stop preserves evidence but EBS costs remain open. Never rely solely on shutdown export, because shutdown scripts are not guaranteed.

### D6 — Member/Ollama reuse
Decision: r09_member immutable closure and lazy-import validation, short Unix-socket relay paths on Linux. Narrow Ollama owner_spec extension199, explicit post-export container/network/VM removal; existing stop preserves objects. No inherited Mac host alias, old owner_spec impersonation, hosted fallback or HA/Ollama acceptance requirement.

### D7 — Actual named acceptance
Decision: AWS9ingress/member cells; final27ingress/group cells including all physical AWS targets and fresh local Azure/GCP representative targets. PeerRegistry/merged peer configs already support multiple groups; new matrix keys must include receiving group/member. Generic remote success does not prove the other destination. Include actual successor, cold native recovery and stopped-guard failures last. Preserve manual recovery/artifact-reference limits.

### D8 — Clients and publication
Decision: actual HUD/Code proof; Mobile impact review and same existing device-key authority restrictions. No new mobile cross-cloud principal grant. No general cloud installer, public blog, version or client publication. Research/technical docs are maintainer evidence.

## Primary sources
- [EC2 idempotency](https://docs.aws.amazon.com/ec2/latest/devguide/ec2-api-idempotency.html): regional/zonal token semantics; request changes are not a retry strategy.
- [RunInstances](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_RunInstances.html): DryRun permission meaning and launch parameters.
- [IMDS options](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html): explicit token/hop settings.
- [Canonical AMI parameters](https://documentation.ubuntu.com/aws/aws-how-to/instances/build-cloudformation-templates/): public Ubuntu release/architecture paths.
- [EC2 quotas](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-resource-limits.html): regional account limits.
- [Free Tier account state](https://docs.aws.amazon.com/cli/latest/reference/freetier/get-account-plan-state.html): plan status, credit and expiry fields.
- [VPC pricing](https://aws.amazon.com/vpc/pricing/), [EBS pricing](https://aws.amazon.com/ebs/pricing/), [EC2 pricing](https://aws.amazon.com/ec2/pricing/on-demand/): public IPv4 currentlyUSD0.005/address-hour, storage persists after stop; do not treat compute rate as total cost.
- [VPC peering](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html), [peering SG rules](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-security-groups.html).
- [Scheduler universal targets](https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-targets-universal.html), [timing](https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html), [trust scope](https://docs.aws.amazon.com/scheduler/latest/UserGuide/cross-service-confused-deputy-prevention.html):60second precision; proposed safeguard is not a guaranteed monetary cap.
- [EC2 termination](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/how-ec2-instance-termination-works.html), [eventual consistency](https://docs.aws.amazon.com/ec2/latest/devguide/eventual-consistency.html): export beforehand and recheck owning services.
- [SCP explicit denies](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic_policy-eval-denyallow.html): role name/full-access label does not override an organization deny.

## Unqualified environment gates
US1–US3 subsequently completed their bounded actual execution and owned retirement; see verification.md. Regional access, full regional custody/cleanup, a fresh complete price packet and actual three-voter runtime evidence remain open. These are explicit execution predicates, not unanswered product choices.

## Live Free-plan correction
The first actualRunInstances failed before resource creation:InvalidParameterCombination,m7i.large not eligible forFreeTier. GetAccountPlanState credits and DryRunOperation had not established product eligibility. DescribeInstanceTypes filteredfree-tier-eligible=true returnedm7i-flex.large with2vCPU/8GiBx86_64. Preflight now checksFreeTierEligible forFREEaccounts. The original request/token stays consumed and its explicit rejection/absence evidence is preserved; replacement needs a fresh priced packet and carried ledger. [AWS’s M7i/Flex table](https://aws.amazon.com/ec2/instance-types/m7i/) specifies40%baseline/vCPU for m7i-flex.large with burst capability, so this is not a continuous-full-CPU promise. Actual confinement/runtime/model proof remains required.

The [AWS CLI reference](https://docs.aws.amazon.com/cli/latest/reference/ec2/run-instances.html) documents output-skeleton input validation without sending a request. Installed2.35.24 passes16of17plannedrequest skeletons;CreateRole fails on its own generateddummyoutputRoleId/Arn/MaxSessionDuration, while the actualCreateRole request succeeded. Record the tool limitation rather than weakening input checks or confusing fixture output with cloud evidence.


## Three-region offline continuation — 2026-11-25
The regional draft uses three distinct non-overlapping10.199/16 subnets, fixed private host addresses, three pairwise peering connections and six host-specific/32 routes. A central transit assumption is invalid because [VPC peering is non-transitive](https://docs.aws.amazon.com/vpc/latest/peering/peering-configurations-full-access.html). Acceptance requests target the [accepter VPC’s region](https://docs.aws.amazon.com/cli/latest/reference/ec2/accept-vpc-peering-connection.html). Tags are [account/region local](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html), so the draft separately tags each accepter-side connection. Route checks require the original peering ID/endpoints, actual active status and matching account/run/region/table/destination; an active route cannot be inferred from a create response. [AWS documents blackhole routes before active peering](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-routing.html).

Exact run-owned aliases nc199-<12hex>-<code>.aws.internal are supported by the existing policy generator with private/32 resolution. This preserves end-to-end TLS and the resolved Python3.12 binary. Each host has a distinct IAM stop-role name because IAM names are account-global. Every draft remains activation_ready=false; it is not a frozen/reserved execution packet. Future once-only journal/custody/cleanup wiring must retain these exact regional bindings.

Measured timing checks require all six directed admission round trips bound to the already verified frozen manifest. They do not infer admission from ping/RTT or widen signed limits. Transport wait matches existing internal.py:max(5seconds,admission_ms/1000). Actual measurement, TLS and successor evidence remain uncollected.

### Final mesh lifecycle review — 2026-11-26

Read-only review found and corrected missing handling for timeout-created VMs,
attached boot-disk custody before cascading deletion, Google canonical resource
origins, Azure parent/child identity, complete prerequisite/manifest/network
binding, source/price/readiness pins and asynchronous stop completion. Explicit
owned NetworkWatchers avoid untracked automatic watcher resources. No final
cloud resource was created during this review.

The actual fresh candidate regions are Azure Canada Central, East US2 and Sweden
Central, each offering Standard_D2as_v7 with ten free vCPUs; and GCP Montreal,
Belgium and Singapore, each with sufficient e2-standard-2/IP/disk quota. Current
pinned images are Azure24.04.202611170 and GCP Ubuntu2404v20261125. Private current
retail/SKU receipts supply compute, disk/mount/transaction and IPv4 rates. The
external reservation remainsUSD4.50, combined across six VMs, storage/cleanup
hold, IPs, transfer, bounded provider calls and miscellaneous I/O; the protected
USD1reserve remains outside it. AWS reservation isUSD5 without credit deductions.

Primary references: [GCP fixed runtime limits](https://docs.cloud.google.com/compute/docs/instances/limit-vm-runtime),
[Google network/IP pricing](https://cloud.google.com/vpc/network-pricing),
[Azure VM create and conditional request semantics](https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/create-or-update?view=rest-compute-2025-04-01),
[Azure deallocation API](https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/deallocate?view=rest-compute-2025-04-01),
[Azure states and billing](https://learn.microsoft.com/en-us/azure/virtual-machines/states-billing),
[Azure resource-group API history](https://learn.microsoft.com/en-us/azure/templates/microsoft.resources/change-log/resourcegroups).
