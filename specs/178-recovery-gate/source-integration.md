# R07 acceptance and source integration

The owner accepted the completed R07/Spec178 evidence and recovery targets on
2026-11-07 and requested commit, PR, merge, completed-branch deletion and return
to main. All31tasks are closed. This supersedes the source-integration hold only;
source1.18.6, extension1.6.1 and Mobile1.0.4+7 remain unchanged, and the roadmap
release/publication hold remains. Retained runtimes are not redeployed.

Feature branch: `178-recovery-gate`. Technical/documentation head: `78176432`.
Base and fetched origin/main: `6b986426bee772d7eb709db9fc2b0d7574d548bc`.
No upstream integration conflict exists at kickoff. Unrelated open PR332,
`177-defenseclaw-sidecar-identity`, stays separate. Private integration receipts
live under `~/.local/share/netclaw/roadmap-r07-20261107-integration/`.

See [completion summary](completion-summary.md), [verification](verification.md)
and [accepted objectives](recovery-objectives.md) for final behavior, evidence and
limits. The four implementation commits were compared with the integrated tree:
all43scopedfiles match. Native Mobile kernel differences are cosmetic-only, with
an exact-source final build. Source/client fixtures do not extend historical
cloud/provider/physical-device qualification.

## Validation

Prior qualified source: federation1,756passed/5existing skips, authority14passed,
actual pending-Border restart1passed, HUD529serial plus30focused, editor209passed
/3existing skips, Flutter518plus25focused, analyzer/builds passed. Source changes
for acceptance and next-stage discussion are documentation only. No native/provider
workload is replayed merely for source integration.

Clean tracked candidate `de89513d` passed166specs/4historical exceptions, FastMCP/task
adoption, all6registration reconciliation surfaces, catalog coverage and the
36-suite/33-CI contract list/matrix. The subsequent R08 discussion packet changes
maintainer documentation only. GitHub checks must pass on the final PR head before merge;
private receipts and the PR retain exact outcomes. Root's ignored installed
HumanRail pin failure remains separate from clean source verification.

## Runtime preservation and next step

R05November7 and R06November8 retirement remain authoritative. Source merging is
not a retention extension or evidence of future cleanup. R06 quiesce15:09:35Z,
cleanup15:14:35Z and fallback15:19:35Z; R05quiesce19:36:25Z and cleanup19:41:25Z.
Original BorderDecember1 remains. Keep the Mac awake/online for scheduled cleanup;
never replay spent claims or equate VM stop with disk/IP removal.

The owner requested evaluating R08 together after merge. See the
[R08 discussion packet](../../docs/roadmap/issue-310/R08-review.md). The existing brief
proposes three etcd voters, bounded control state, protected quorum transport and
new internal cluster links, distinct from eN2N. This is review/planning only.
Expected next free spec is179, subject to kickoff recheck; no R08 spec/branch,
new infrastructure, HA activation or publication is created by this integration.
