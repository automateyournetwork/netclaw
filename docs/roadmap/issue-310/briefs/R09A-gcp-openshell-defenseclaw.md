# R09A — GCP Borders and HA mesh inside OpenShell and DefenseClaw

- **Roadmap item:** 4 (substep 1 of 2 before Azure)
- **Depends on:** R09 (spec 182, PR #340)
- **Gate:** human review before R09B
- **Spec:** `specs/183-openshell-defenseclaw-gcp/`

## Specify input

Run the GCP HA Borders and the HA mesh (public HUD ingress, workspace backend and chat gateway, model guard, and the GCP-hosted members) inside NVIDIA OpenShell sandboxes with Cisco DefenseClaw guardrails, without weakening any Spec 179/182 identity, authority or admission guarantee. Two Borders in one region are an acceptable validation topology.

R09 left these gaps: no sandbox on any Border or member host; an unguarded Border chat path holding the provider credential; no egress filter or spend meter on the hosted guard; an open-lab HUD. The repository also documents systemd confinement (not OpenShell) as the production sandbox control for iN2N Risks, so this stage must decide, with evidence, what OpenShell can and cannot host.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Sandboxing | Every in-scope process shows its sandbox, policy version/hash and health; documented disposition for any exclusion |
| Mesh | Cluster forms, leader elected, real operations complete through each Border while sandboxed |
| Guardrails | Violating prompt and tool call blocked and audited; guard stopped means no provider call |
| Isolation | Negative suite: out-of-policy file access, frozen-source change, metadata server, unapproved egress, credential read, member-to-member |
| HA | R09 failure matrix re-run; admission overhead measured against the signed window |
| Operability | Per-node sandbox/guard status in HUD and VS Code; audit export; clean teardown |
| Clients | Explicit G12/G13 disposition |
