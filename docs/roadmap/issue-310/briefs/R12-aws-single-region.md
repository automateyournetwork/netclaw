# R12 — AWS single region

- **Roadmap item:** 6 — AWS, repeat the GCP sequence (single)
- **Depends on:** R09 (may run beside R10)
- **Gate:** human review before R13

## Specify input

Repeat the R03–R05 pattern on AWS using the provider-neutral role contract: an
AWS Border, an AWS NetBox member with a hosted model and an AWS Ollama member,
with the on-prem members attached. Same workloads, refusals and evidence.

## Clarify: decisions (recommended default first)

1. Region. [HUMAN]
2. Member identities: same rule as R10.
3. Admin path: SSM Session Manager.

## Plan notes (AWS deltas)

- IAM roles through instance profiles; Secrets Manager or SSM Parameter Store
  rendered into private `.env` at start.
- Security groups with no inbound rules for NetClaw services.
- IaC module under `labs/cloud/aws/` implementing the same role contract.

## Acceptance evidence

All R03, R04 and R05 acceptance rows, re-run on AWS, plus cost and teardown.
