# Spec162 planned operator walkthrough

This describes the intended implementation; the new commands/tools are not yet implemented.

1. Select NetConverter in a new isolated NetClaw setup. Choose hosted-readonly to inspect existing jobs, or local-terminal with an explicitly installed licensed Terminal, private workspace and installation-specific key. Review separate readiness results.
2. Ask the new `netconverter` skill to discover supported directions and prepare a local configuration for the selected operation. A local metadata-only proposal identifies source/hash/size, target, options and exact hosted destination.
3. Review that exact request through the native operator command. Approve only the reviewed digest. The agent invokes submit-approved using the opaque request ID; unknown outcomes reconcile rather than resubmit.
4. Review job evidence first. Download verified artifacts locally. Preserve NEEDS REVIEW, warnings, manual work and untested features.
5. Request an actual virtual-target rehearsal. Discover a compatible lab host, licensed image, architecture/capacity, isolated networks and authorized bootstrap. Create/boot run-owned resources and discover real management identity.
6. In the existing Terminal Intent Local/Lab flow, explicitly designate eligible SSH endpoints and select the candidate artifact. Complete real baseline/rollback preparation. Only the API's reviewed APPLY transition authorizes its exact candidate/tool/endpoints. Other configurations retain their normal approved change workflow.
7. Apply the candidate through the existing protected configuration route; verify commit/readback and run positive/negative behavior tests. Use a source twin when feasible. Include actual NAT observations when the migration contains NAT.
8. Add supported Batfish results and optional Jev review. Generate diagrams and a local evidence/change-package draft. Review failed/unexecuted tests and retained resources. Publishing a ticket or deploying to production remains a separate authorized action.

## Feasibility currently observed

The development Mac is ARM64. Its Docker client cannot reach the selected daemon socket, so image/capacity inventory is unavailable. The connected NetClaw read-only inventory request failed. No local Terminal executable/account was found by the bounded prerequisite checks. These observations do not establish that remote labs or an account are absent. Live qualification needs the selected host/image and enabled account; do not mark fixtures as live migration evidence.
