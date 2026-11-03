# R12 — AWS single region

- **Roadmap item:** 6 — AWS, repeat the GCP sequence (single)
- **Depends on:** R09 (may run beside R10)
- **Gate:** human review before R13

## Specify input

Repeat the R03–R05 pattern on AWS using the provider-neutral role contract: an
AWS Border, an AWS NetBox member with a hosted model and an AWS Ollama member,
with the on-prem members attached. Same workloads, refusals and evidence.

For this stage, include separate VS Code and Mobile impact decisions and
implementation/verification work under [G12/G13](../README.md#global-invariants-every-brief-inherits-these).
Record a reasoned no-change disposition for an unaffected client; affected
integration gaps remain part of this feature.

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

All R03, R04, R04a and R05 acceptance rows, re-run on AWS, plus cost and teardown.

| Group | Evidence |
|---|---|
| VS Code integration | Explicit G12 impact/disposition and evidence: AWS Border connection, verified identity/authentication and supported workflows |
| Mobile integration | Explicit G13 impact/disposition and evidence: Affected AWS endpoint/enrollment/Ask Border paths use the supported verified transport; reasoned no-impact outcome if unaffected |
