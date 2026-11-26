# Spec199 Lifecycle Contract

Private maintainer CLI; no MCP or general assistant cloud-write endpoint.

## Read-only preflight
`python3 labs/cloud/aws/spec199/preflight.py --profile NetClaw --region us-east-2 --out PRIVATE_DIR`

Explicit profile/region; capture identity, instance/disk/address baseline, VPC/subnet inventory, StandardvCPU quota, candidate type/offerings, Canonical Ubuntu image, gross rates and credit observations. Save raw receipts privately, emit sanitized summary with observed_at, available/denied/unknown states. Do not print credentials/account identifiers by default. Zero rows only when the API succeeded. A later-stage regional denial cannot make single-region source work unavailable. No AWS write API is reachable from this command. Permission dry-run is a separate explicit action, not a false capacity proof.

## Campaign and lifecycle commands
`campaign.py init|validate|reserve|status` operates only on private validated packets/ledger; stage acceptance is an explicit library operation after evidence review. A reservation needs predecessor proof, finite deadline, exact cost components and remaining domain budgets; no broad approved boolean. `run.py plan|apply-one|observe|retire-one|status` handles stages1–3. `regional_run.py plan|apply-one|observe|verify-routes|retire-one|confirm-absence` handles stage4, including explicit three-region or owner-approved Ohio-three-AZ scope and39expected custody objects. Each apply persists a sent marker before one request; ambiguous outcomes halt new creates. Reconciliation uses original IDs/tokens; no new token or region/AZ migration. `lifecycle.py verify-export|verify-absence` checks the corresponding artifacts. Quiescent exports and stage acceptance remain explicit evidence operations, not fictional CLI verbs. Never use read-only preflight credentials as evidence of production authorization.

Regional creation descriptors freeze action, response path, region and journal namespace. Global IAM names are unique per host. Peering tags are recorded in both endpoint regions. Unknown launches preserve all network/stop guards; a VPC cannot retire with unknown/unrecorded/live peerings. Route cleanup refuses foreign routes/associations. Peering absence requires successful reads in both owning regions, repeated at least two seconds apart. Cleanup stays available after expiry/source changes; it never authorizes new creates or resets unknown operations.

## Ownership and cleanup
Deletion requires same observed account/region, recorded immutable ID and matching run/stage tags plus verified export references. Baseline/default/foreign objects are denied even when names match. Root volume deletion flags/ENIs/addresses are enumerated, not inferred from instance termination. Remove dependents only after verified safe ordering. Direct inventory is repeated under bounded waits; failed/ambiguous observations keep ledger/guards open. No account-wide scan selector can become a deletion list without ownership checks.

## Deadline safeguards
Before paid execution, validate independent exact-instance cloud stop plus host/local quiescence. Scheduler group/role resources are campaign-owned, scoped to exact instance IDs; trust SourceArn names the group, with source account. Bound retries/event age; completed schedule auto-delete does not prove target success. Export checkpointing occurs during execution, not only in shutdown. At expiry stop new work, preserve uncertain provider state, stop compute if export fails, hold EBS costs and continue bounded cleanup. No guard claims a hard monetary cap; full reservations remain authoritative.

## Spend and scope
USD100AWS gross; pause80/reserve5; USD10 external total. Six-hour early stage, one-hour Ollama, two-hour mesh maxima. No unpriced NAT/GPU/LB/reserved-capacity purchases. No dynamic secret upload or role policy expansion without the frozen stage design. Region-policy denial is never repaired by bypassing it.

Ohio mode freezes one region, three unique zone names/IDs, three distinct instances and account-bound scope/upgrade evidence. Per-host costs are summed for three hosts and shared quota is checked against six vCPUs. Peer orientation binds source/requester node identity even when both regions are Ohio. The mode is never an automatic fallback after denial.
