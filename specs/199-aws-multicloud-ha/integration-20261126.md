# Spec199 source integration — 2026-11-26

The owner accepted the completed qualification and explicitly requested source reconciliation, commit/push/merge into main, completed-branch retirement and a separate NET CLAW MULTI CLOUD writeup. This supersedes the earlier Spec199 source-integration hold. The existing roadmap version, package and client publication hold remains in effect.

The live campaign is closed at 39/39 for the approved Ohio three-AZ scope. [Acceptance, cleanup, costs and limitations](closure-20261126.md) remain authoritative. No cloud resource or operation is reactivated for source integration.

Upstream main includes PR #372 (slow HUD discovery probe timeout) and PR #373 (native agent discovery cache), through `6892e6bb`. Both were reconciled without conflicts. There were no other open PRs at kickoff. The detached Spec200 checkout remains at `97fc1f1a` and existing services/private evidence are preserved.

The 107 offline AWS lifecycle tests are added to the existing `n2n` contract-suite paths so CI exercises them with the qualified federation dependencies. This is test registration only; cloud credentials and live activation are not used by these fixtures.

Integration validation is recorded below. [PR #375](https://github.com/automateyournetwork/netclaw/pull/375) supplies the authoritative final merge status and commit receipt. The separate writeup is a private document, not a website deployment, package release or announcement.

Reconciliation also found the existing tracked `tests/azure` family missing from the suite manifest. It is now registered as an offline Azure documentation/installer parity suite. The installed, untracked HumanRail clone has an unbounded `mcp>=1.0.0` declaration and fails the local dependency scan; its runtime is not changed or qualified by this integration. Source-only reconciliation is verified independently from a clean tracked snapshot, without waiving a declaration gate.

## Validation of reconciled source

- Full federation plus AWS collection: `python -m pytest -q tests/n2n labs/cloud/aws/spec199` — 2,960 passed, 14 skipped, 55 subtests passed. This includes the 107 AWS lifecycle tests. Existing dependency/deprecation warnings remain; skipped cases are not promoted to coverage.
- Azure documentation/installer parity: eight passed. Client-evidence contracts: ten passed. Reconciled upstream HUD management tests: five passed. Installer verification: nine passed.
- Extension TypeScript check, numbered-spec artifacts, catalog generation/metadata/coverage and the contract-suite matrix pass. The matrix now includes the previously omitted Azure suite and runs the AWS fixtures within n2n.
- A clean tracked source snapshot passed all six declaration reconciliation surfaces: catalog, dependencies, docs, Meraki IDs, package references and portability. The installed untracked HumanRail limitation above remains separate.
- Changed-file secret-shape review found only an existing, explicitly fake provider key fixture; no added credentials. Whitespace validation passed.

The cloud acceptance is retained from the closed campaign and was not rerun. No new package dependency, MCP integration, installer behavior, client release or Mobile behavior is introduced by the CI registration fixes. Source version remains 1.26.0 under the coordinated roadmap release hold recorded in AGENTS.md.

The accepted source is tracked in [PR #375](https://github.com/automateyournetwork/netclaw/pull/375). After its final-head checks pass, merge it, synchronize main and retire only `199-aws-multicloud-ha`. Keep the detached Spec200 checkout and unrelated historical worktrees. The final GitHub merge receipt and local cleanup verification are retained privately under `~/.local/share/netclaw/spec199-main-integration-20261126/`; do not reactivate the closed campaign.
