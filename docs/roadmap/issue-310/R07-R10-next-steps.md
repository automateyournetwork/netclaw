# Next steps after accepted R06: R07–R10

R06/Spec177 is accepted35/35. Its three independent organizations prove external
eN2N federation; they are not a single HA cluster. The following stages remain
sequential, with a new numbered Spec Kit cycle and an evidence gate per stage.
This is a maintainer planning brief, not authorization to provision or execute.
Expected next free spec is178; recheck main, open PRs and remote branches at
kickoff. R06 and the separate open DefenseClaw fix both use177 with distinct paths.

| Stage | Work | Exit evidence and decisions |
|---|---|---|
| [R07 — recovery gate](briefs/R07-recovery-gate.md) | Drill single-region Border/member restarts, endpoint replacement, network/provider loss, live-channel revocation, lost replies, duplicates and cancellation. Publish an operator runbook for each scenario. | Same enrolled identity after recovery; immediate revocation; no weaker fallback or uncertain replay; one effect or none. Measure recovery times and agree targets. Qualify optional ngrok cases only if selected. Pass before HA/multi-region. |
| [R08 — HA authority](briefs/R08-border-ha-authority.md) | Establish one execution authority, member-enforced fencing, protected quorum transport and a separate internal cluster relationship. Proposed design: three etcd voters and bounded control state. | Review mTLS/RBAC/private transport and authority design. Prove leader loss, minority/asymmetric partitions, quorum loss, clock uncertainty, full restart and stale/retired-node return. Label fixture and real guarded-runtime evidence separately; both must pass. |
| [R09 — three-region GCP](briefs/R09-gcp-multi-region.md) | Deploy one organization across Americas, Europe and Asia-Pacific, with three meshed Borders and four members attached to each. | Select regions and review exact resource/cost/expiry plans. Prove12authenticated member attachments,3cluster links, member-to-member refusal, prior read-only workloads through each Border and loss of each region without replay. Human review before Azure. |
| [R10 — Azure single region](briefs/R10-azure-single-region.md) | Repeat the protected Border, hosted-model NetBox and Ollama member workloads on Azure, with separate on-prem enrolled instances for that environment. | Select region, identity arrangement and admin path; implement managed identity/Key Vault and provider-specific IaC. Re-run R03/R04/R04a/R05 acceptance, recovery, cost and teardown. Human review before R11. |

Every stage separately assesses and verifies actual VS Code and Mobile behavior
under [G12/G13](README.md#global-invariants-every-brief-inherits-these): connection
and identity, pending approvals/results, failure and reconnect as affected. A
reasoned no-impact finding needs inspected-contract evidence. Simulator results
do not qualify physical hardware. Read-only workload and release holds continue.

Before R07 activation, inspect the original R05/R06 retirement receipts and
actual current resources. R05 cleanup is scheduled November7; R06 quiesces
November8 at15:09:35Z, cleans up at15:14:35Z and has independent STOP at15:19:35Z.
The Mac must remain awake/online for its cleanup jobs. Preserve the original
Border's December1 lifetime. Never replay spent activation or cleanup claims,
extend expired deployments implicitly, or infer disk/IP removal from VM STOP.
Fresh resources require a concrete bounded plan.

At R10 planning, reconcile the Azure brief's older “no inbound NetClaw services”
wording with the roadmap's primary direct-TCP transport. Use reviewed, narrowly
scoped ingress for the selected direct path, or explicitly select and qualify
the optional tunnel path; the brief does not waive the global transport contract.
