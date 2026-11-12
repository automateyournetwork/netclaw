# R09C — GCP setup, installer and documentation refresh

- **Roadmap item:** 4 (closes GCP before Azure)
- **Depends on:** R09B (complete; [survey](../../../../specs/192-gcp-completeness-survey/survey.md) kept as a reference)
- **Spec:** [193-gcp-docs-setup-refresh](../../../../specs/193-gcp-docs-setup-refresh/spec.md)
- **Gate:** owner review before R10

Make deploying Borders and Members in GCP possible from the real install paths (`scripts/install.sh` TUI, the VS Code setup wizard, the Claw Plan / assistant flow) using the user's own project and regions, in GCP-only, mixed on-prem/GCP, HA Risk and distributed Risk topologies, with teardown. Publish a separate [NetClaw in GCP](../../../NETCLAW-IN-GCP.md) guide and refresh the README, getting-started, assistant-install and Claw Plan docs.

**Every entry point states that the deployment is NOT behind any authentication; keep URLs private.** Users, SSO and RBAC are a much later phase (R15-R17).

## Acceptance evidence
Spec 193 `verification.md`: stub-tested provisioner, parity tests across frontends, documented review of all updated docs, and a recorded real-GCP run (or an honest statement that it was not run).
