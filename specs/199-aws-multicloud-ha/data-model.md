# Spec199 Data Model

All authoritative objects are private owner-scoped files outside source; no secrets in example source. Values are validated before writes, with0600 files/0700directories and atomic replace under an exclusive lock.

| Entity | Fields and constraints | Transitions |
|---|---|---|
| Campaign | schema1, campaign_uuid, expected_account, source_sha, aws_ceiling100, aws_pause80, aws_reserve5, external_ceiling10, accepted_stage0..5, created_at | created→active→quiescing→exported→closed; blocked is observable without erasing state |
| StagePacket | campaign, stage1..5, revision/hash, predecessor receipt hashes, source/profile/AMI digests, qualification_scope, exact region/AZ name/AZ ID/subnet/resources, original token, deadline, per-domain reservation | draft→frozen→reserved→sent→observed; unknown never returns to draft |
| Resource | account, region, type, immutable ID, run/stage tags, request digest, related volume/ENI IDs, prior baseline, actual observed state | planned→sent→unknown/created→running→stopped→exported→removed→absence_verified |
| Reservation | unique id, packet hash, AWS/external amounts, usage amounts, uncertainty amounts, cleanup floor, deadline | held→partially spent→settled; no release without explicit verified disposition |
| Witness | stage, ingress, destination_group, target_member, original operation, member placement, result/ACK digests, counters and evidence class | prepared→approved→sent→completed/refused/unknown; never reset/replay |
| CleanupReceipt | immutable export manifest/hash, exact resource IDs, repeated owning-service absence observations, DNS/guard/IAM dispositions, remaining billable residue | pending→verified; unexported/unknown/residue prevents closure |

Invariants: packet/source change requires fresh unspent identity; client token fixed across original-region/AZ reconciliation; no blanket account-wide deletion; tags must agree with recorded IDs/account/region; accepted_stage advances only one step with verified receipt and required previous cleanup; final mesh cannot activate before stage4. Gross cost is spent plus all held obligations, independent of credit. Unknowns/retained EBS remain held. A failed export can stop compute but cannot authorize destruction. Billing settlement and resource closure are distinct facts.

Scope is `three-region` (original strict behavior) or `ohio-three-az` (owner amendment); the latter cannot be silently inferred from duplicate regions. Physical observations bind zone IDs and instance IDs. Matrix groups carry region and zone provenance; AWS multi-AZ claims never spread to Azure/GCP region validation.
