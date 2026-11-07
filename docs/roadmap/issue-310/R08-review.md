# R08 review after accepted R07

This is the owner's requested discussion packet, not a new numbered spec or
permission to implement/provision. R07/Spec178 is accepted31/31; R08 is next.
Expected next free spec is179, subject to checking main, open PRs and branches
again at kickoff. The [canonical R08 brief](briefs/R08-border-ha-authority.md)
remains the scope authority.

## What R08 adds

R06 connected independently administered organizations. R07 proved safe recovery
within the selected single-region system. R08 gives several Borders in **one
organization** a shared, single execution authority. If one fails or a partition
forms, a member must refuse stale authority even if the old Border is still
reachable. Losing quorum stops new protected execution. Reading retained status
must never become a way to approve or execute again.

This is a separate cluster relationship with its own enrollment and trust.
Existing iN2N member enrollment and eN2N bilateral exports do not confer a vote,
cluster membership or access to consensus storage. Three voters and three Borders
are distinct design choices, even if initially colocated in a qualification lab.

## Recommended scope for discussion

Keep the existing brief's three-voter etcd majority/CAS design, bounded control
state and member-enforced claims as the starting proposal. Review and pin the
actual etcd dependency at kickoff; the dated companion pin is not automatically
a current dependency/security clearance. Do not put chats, RAG, member secrets
or complete installation databases in consensus storage.

Use two explicit qualification gates:

1. **Fixture gate:** fresh isolated three-voter/control-plane setup; actual
   authenticated quorum transport plus controlled effects. Prove leader loss,
   minority/asymmetric/three-way partitions, stale leaders, no quorum, clock
   uncertainty, restart, retirement and fenced restore. Preserve unknown claims.
2. **Real-runtime gate:** bind the same fencing/admission chain to the actual
   supported NetClaw guarded runtime, native read-only MCP/tool, durable signed
   evidence and audit. Repeat the material fault cases; standalone Ollama or
   provider success plus fixture HA is insufficient. Verify actual HUD, VS Code
   and Mobile behavior for changed authority, pending approvals and results.

Begin locally with disposable owned resources and finite bounds. R09 remains the
three-region GCP deployment; R08 must not expand silently into it. A local lab is
not evidence of independent regional failure. Any cloud-based qualification needs
its own exact resource, spend, expiry and cleanup packet before activation.

## Decisions to make together

| Decision | Recommended starting point | What must be explicit |
|---|---|---|
| Quorum transport | Private/direct TCP, separate peer/client mTLS and scoped etcd RBAC | Reviewed caller/address allowlists and stable endpoints; members/external peers get no etcd credentials. The R08 brief marks this HUMAN. |
| Execution authority | One leased leader with member-enforced fresh one-use claims | Exact cluster generation, epoch/incarnation, approval digest, member and operation; no local force-leader escape |
| Restore/retirement | New fenced generation only after old authority/executors are demonstrably isolated | A changed UUID alone cannot neutralize a surviving old quorum; no stale database restore into live authority |
| Client identity | Stable cluster service identity plus separate node identity | Explicit trusted endpoint handling, authority/quorum status and stale-approval refusal; never infer trust from routing |
| First real workload | Small existing read-only native subnet workflow | Actual model/guard/MCP/effect path must carry the fencing claim; exact execution/provider bounds and runtime selection belong in the spec |
| Delivery boundary | Standalone behavior preserved; HA explicitly selected | No retained-pilot upgrade, public release or new user/SSO/RBAC scope by implication |

These are recommendations to review, not decisions already accepted by this
source-merge request. Full specify → clarify → plan → tasks → analyze precedes
implementation. Each client needs its own G12/G13 impact and actual evidence.

## Companion baseline inspected on 2026-11-07

The local Thermidor Spec005 evidence still says qualification is in progress;
its source and specification are uncommitted in that independent workspace.
It records actual etcd/mTLS/RBAC and network fault evidence, but HA model/guard/
confinement/effect providers are synthetic. Its standalone production broker
explicitly refuses HA execution until the complete enforcement chain qualifies.
No companion file or runtime was changed by this review.

Useful lessons to re-evaluate in NetClaw: bounded control-state/MVCC retention,
measured voter memory, lease renewal independent from dispatch, exact process
incarnation, conservative unknown-commit handling, endpoint selection latency,
and restored-state fencing. Do not copy its unfinished acceptance status or
Tailscale transport as NetClaw qualification. NetClaw keeps the selected direct
transport contract and produces its own fixture and real-runtime evidence.

## Clear-safe next session

After the R07 merge and cleanup are verified, use:

> Evaluate R08 / expected Spec179 using the saved R07 handoff. Review the authority,
> quorum transport and real-runtime qualification plan with me before starting.

The private handoff contains actual merge/check hashes and current retirement
receipts. R05 cleanup is scheduled November7 at19:36:25Z quiesce/19:41:25Z cleanup;
R06 November8 at15:09:35Z/15:14:35Z with15:19:35Z fallback. Existing original Border
December1 lifetime remains. Keep the Mac awake/online for scheduled cleanup;
these future outcomes must be checked, never assumed or replayed.
