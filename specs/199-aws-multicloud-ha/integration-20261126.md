# Spec199 source integration — 2026-11-26

The owner accepted the completed qualification and explicitly requested source reconciliation, commit/push/merge into main, completed-branch retirement and a separate NET CLAW MULTI CLOUD writeup. This supersedes the earlier Spec199 source-integration hold. The existing roadmap version, package and client publication hold remains in effect.

The live campaign is closed at 39/39 for the approved Ohio three-AZ scope. [Acceptance, cleanup, costs and limitations](closure-20261126.md) remain authoritative. No cloud resource or operation is reactivated for source integration.

Upstream main includes PR #372 (slow HUD discovery probe timeout) and PR #373 (native agent discovery cache), through `6892e6bb`. Both were reconciled without conflicts. There were no other open PRs at kickoff. The detached Spec200 checkout remains at `97fc1f1a` and existing services/private evidence are preserved.

The 107 offline AWS lifecycle tests are added to the existing `n2n` contract-suite paths so CI exercises them with the qualified federation dependencies. This is test registration only; cloud credentials and live activation are not used by these fixtures.

Integration validation and the merge receipt will be recorded here before closeout. The separate writeup is a private document, not a website deployment, package release or announcement.

Reconciliation also found the existing tracked `tests/azure` family missing from the suite manifest. It is now registered as an offline Azure documentation/installer parity suite. The installed, untracked HumanRail clone has an unbounded `mcp>=1.0.0` declaration and fails the local dependency scan; its runtime is not changed or qualified by this integration. Source-only reconciliation is verified independently from a clean tracked snapshot, without waiving a declaration gate.
