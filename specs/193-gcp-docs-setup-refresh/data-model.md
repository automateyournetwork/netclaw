# Data Model: Spec 193

- **Deployment** `{id, project, topology, prefix, label, regions[], createdAt, planSha256, state: planned|applied|partial|torn-down}` stored 0600 in `~/.openclaw/gcp/<id>.json`.
- **PlannedResource** `{kind: network|subnet|address|firewall|serviceaccount|instance|budget, name, region/zone, detail, estMonthlyUsd}`; names always start with the Deployment prefix.
- **Node** `{role: border|member|witness, name, region, zone, machineType, externalIp?}`; Border and Member map to the existing Spec153 roles.
- **Acknowledgement** `{warningSha256, acknowledgedAt}` required before a plan is produced; recorded in state.
- State transitions: planned -> applied -> torn-down; apply interruption -> partial (re-run converges; teardown always allowed).
