# R13 — AWS multi-region

- **Roadmap item:** 6 — AWS (multi)
- **Depends on:** R12
- **Gate:** human review before R14

## Specify input

Repeat R09 on AWS: three Borders in three AWS regions form a cluster with three
voters; every AWS-stage member attaches to all three; member-to-member refused;
region loss drills pass with no replay.

For this stage, include separate VS Code and Mobile impact decisions and
implementation/verification work under [G12/G13](../README.md#global-invariants-every-brief-inherits-these).
Record a reasoned no-change disposition for an unaffected client; affected
integration gaps remain part of this feature.

## Clarify: decisions (recommended default first)

1. Regions. [HUMAN]
2. Same decisions as R09, with measured AWS WAN timings.

## Acceptance evidence

All R09 acceptance rows, re-run on AWS, plus cost and teardown.

| Group | Evidence |
|---|---|
| VS Code integration | Explicit G12 impact/disposition and evidence: AWS regional Border selection and failover preserve connection and approval state |
| Mobile integration | Explicit G13 impact/disposition and evidence: Affected AWS regional failover/reconnection preserves enrollment, identity and results; reasoned no-impact outcome if unaffected |
