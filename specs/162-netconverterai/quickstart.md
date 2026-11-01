# Spec162 operator walkthrough

These source tools and controlled workflows are implemented. Actual licensed Terminal 0.6.0 discovery and two approved synthetic routing conversions completed on 2026-10-31. Vendor-target application/forwarding and native desktop acceptance remain open; see [verification](verification.md).

1. Select NetConverter in a new isolated NetClaw setup. Choose hosted-readonly to inspect existing jobs, or local-terminal with an explicitly installed licensed Terminal, private workspace and installation-specific key. Review separate readiness results.
2. Ask the new `netconverter` skill to discover supported directions and prepare a local configuration for the selected operation. A local metadata-only proposal identifies source/hash/size, target, options and exact hosted destination.
3. Review that exact request through the native operator command. Approve only the reviewed digest. The agent invokes submit-approved using the opaque request ID; unknown outcomes reconcile rather than resubmit.
4. Review job evidence first. Download verified artifacts locally. Preserve NEEDS REVIEW, warnings, manual work and untested features.
5. Request an actual virtual-target rehearsal. Discover a compatible lab host, licensed image, architecture/capacity, isolated networks and authorized bootstrap. Create/boot run-owned resources and discover real management identity.
6. In the existing Terminal Intent Local/Lab flow, explicitly designate eligible SSH endpoints and select the candidate artifact. Complete real baseline/rollback preparation. Only the API's reviewed APPLY transition authorizes its exact candidate/tool/endpoints. Other configurations retain their normal approved change workflow.
7. Apply the candidate through the existing protected configuration route; verify commit/readback and run positive/negative behavior tests. Use a source twin when feasible. Include actual NAT observations when the migration contains NAT.
8. Add supported Batfish results and optional Jev review. Generate diagrams and a local evidence/change-package draft. Review failed/unexecuted tests and retained resources. Publishing a ticket or deploying to production remains a separate authorized action.

## Feasibility currently observed

The development Mac is ARM64. After the owner started Docker, the Linux ARM64 daemon reported 14 CPUs and approximately 8.3 GB memory. Its existing pyATS MCP successfully listed four devices and completed four live `show version` checks through the existing local SSH relays. All four hostnames matched their inventory names and reported 17.18.2. No device configuration was changed. The separate connected NetClaw agent still returned an internal error; direct local MCP supplied the read-only evidence.

The preferred reference is IOS-XE→JunOS OSPF. The real account converted IOS-XE → Junos SET and the returned Junos → IOS-XE, both needs review. Authenticated local CML 2.10 discovery found IOS-XE 17.18.2 images but no Junos image. Scoped trust of the observed self-signed certificate enabled read-only API discovery; this is not independent certificate authentication or a global trust change. These are distinct qualification gaps; live source observations do not establish target boot, hosted conversion or migration acceptance.
