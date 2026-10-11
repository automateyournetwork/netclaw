# Spec150 implementation readiness after the WSL baseline

**Current status, 2026-10-10:** the owner subsequently authorized all five execution
steps. Implementation is now underway in the separate
`150-vscode-extension-implementation` worktree. WSL qualification requires an
owner-machine handoff; local authentication was selected for publishing. The
review below is retained as the historical planning baseline, not a current
implementation prohibition. See [Mac development evidence](evidence/mac-development.md).

Review date: 2026-10-10. Source: fetched commit `aa2795313b487e00ccbe85d53f6a78db07b10a94` on `origin/150-vscode-extension`, reviewed in a separate detached Mac worktree. The original Mac checkout was preserved; no merge, push, implementation, installation, restart, credential/configuration change, provider request or publication was performed.

The owner authorizes **review and planning only**. All 79 tasks, including T075, remain unchecked. This document refines the execution order and prerequisites in [plan.md](plan.md) and [tasks.md](tasks.md); it does not ratify them or record any new runtime acceptance.

## Evidence reviewed and its limits

The actual [WSL baseline](evidence/wsl-baseline.md) is now available, rather than only its summary. The commit adds that report plus explanatory task/handoff notes; it changes no implementation. WSL observations below are attributed to that committed report, not repeated from this Mac.

| Finding | Meaning for implementation and acceptance |
|---|---|
| Windows build 26300.9550, WSL 3.0.1.0, Ubuntu 26.04 x86_64, actual Linux VS Code 1.140.0 extension host | A real WSL target and editor context exist. This is not a Spec150 extension pass; minimum-editor, second-distro and other platform rows remain open. |
| Owner source files at 1.8.0, but live HUD/daemon return older shapes | The running backend's loaded source version is unverified. Identify service executable, process start time, working directory, selected configuration and restart provenance before planning a cutover. Do not infer a running upgrade from Git/VERSION. |
| Owner shell and live gateway/HUD use Node 25.1.0 | Rejected by [backend policy](../../config/installer-runtime.json): `>=24.19.0 <25` or `>=26.1.0`. Editor-bundled Node 24.21.0 does not fix service Node. A private Spec148 Node 24.19.0 was observed, but its use for a new isolated development target needs explicit selection and dependency validation. |
| Stable owner installation ID is unavailable; strict federation status refuses foreign/legacy identity | Correct fail-closed behavior. Connecting the extension must not create a UUID, overwrite ownership or bless a legacy daemon. Initialization/migration belongs to a separately authorized owner backend preparation. |
| Owner mesh uses system Python 3.14.4; required isolated federation Python 3.12 record not found in standard records | Resolve exact interpreter/dependency ownership. This is not proof that no 3.12 interpreter exists anywhere; alternate private layouts were not exhaustively searched. Preserve federation/bridge Python 3.12 versus Hermes companion Python 3.14 isolation. |
| Secondary Hermes is a separate Spec148 instance at source 1.6.2 | Useful evidence of existing prerequisites, not a replacement for the owner's Risk or a Spec149/150 federation pass. Preserve it while building a separate candidate fixture. |
| Four submitted entries in a bounded 50-item recent-task list | Complete active/unresolved-work inventory is still needed before disruption. Do not cancel/replay these entries or infer that they are the only active jobs. |
| Copilot, Claude Code and Codex packages/commands exist | Real MCP consent, account/policy availability, grants and NL execution remain untested. Absence of sampled policy keys is not permission. |
| One owner WSL distro plus stopped container infrastructure | E8 requires a separately designated second NetClaw test distribution/installation. Do not start or repurpose container infrastructure as that target. |

Source inspection on Mac confirms that `resolveRuntime()` defaults to read-only and can return a null ID; `initialize:true` writes installation identity, and `selectRuntime()` also writes selection/initializes identity. These behaviors in [runtime-selection.mjs](../../scripts/runtime-selection.mjs) must remain distinct in the new connection adapter. No resolver or live service was invoked to initialize anything during this review.

## Concrete execution sequence

| Step | Work and task mapping | Exit evidence / required authority |
|---|---|---|
| 0 — Preserve and pin | Retain the immutable WSL baseline and exact source reference; record publisher `NetClaw` as reported by the owner. Recheck freshness when implementation starts. | Baseline commit verified locally; original Mac and WSL runtime observations kept separate. This review is authorized now. |
| 1 — Isolated development setup | After design ratification, T001–T004: pinned extension/MCP packages, declared supported Node, separate dependency environments and synthetic homes. Reuse an already installed qualified interpreter only through explicit paths; do not change owner PATH, service units or shared environments. | A documented build/test runtime and fixtures incapable of selecting owner homes by default. Needs implementation plus bounded dependency/test-process authorization; not supplied by this review. |
| 2 — Authority and durability | T005–T014: strict schemas, verified identity, scoped grants at every delegation hop, actual approval checks, durable nonce/ownership journal, independent workers, proposal/recovery, GAIT isolation and private façade. | Negative tests for spoofing, missing identity, denial, CR withdrawal, lab scope, audit loss, uncertain dispatch and secret disclosure. No unrestricted assistant bridge while these controls are incomplete. |
| 3 — Connection milestone | T015–T021: native extension/profile/SSH/WSL connection and explicit compatibility failures. Add the owner-baseline conditions to existing US1/foundation test cases without adding new unchecked task IDs. | Candidate reports unsupported backend Node, legacy/missing identity and absent management contract accurately. An online legacy HUD cannot pass as a contract-1 connection; no auto-upgrade or silent runtime selection. |
| 4 — Working product | T022–T047: Chat/Canvas/Avatar, estate/federation, settings/lifecycle and Operations/GAIT/security; T048–T055 then add the scoped Copilot/Claude/Codex surface. T056–T070 finish remaining HUD domains and distribution preparation. | Each story's independent behavior passes on isolated qualified targets. Proposals use human review and existing approvals; source changes alone are not live acceptance. |
| 5 — Backend preparation for real WSL | Plan an owner-managed update or an explicitly designated parallel test installation. Establish supported Node, isolated Python records, pinned runtime source, stable installation identity and installed management contract major 1. Verify actual executing binaries/identity after the approved deployment. | Separate exact target, backup/recovery, unresolved-work disposition, service/unit list and authorized maintenance window. The extension itself never performs backend bootstrap/upgrade. No maintenance command is selected until target/process provenance is known. |
| 6 — Spec149 dependency | Complete Spec149 T040's applicable real Linux/WSL runtime matrix, selected service lifecycle/ownership, populated rollback and independently observed confinement/model-guard evidence. Use [the existing handoff](../149-hermes-ncfed-federation/validation-handoff.md) and [fixture guidance](../../tests/n2n/README.md). | Initially use isolated homes and controlled loopback providers. Real systemd/confinement tests require designated disposable units/accounts/resources. Production Hermes remains denied unless its separate guard/confinement implementation is actually qualified; installing a newer Node is not that qualification. |
| 7 — Real editor/client acceptance | T073–T076: all domain/accessibility/performance/regression rows, then actual WSL E3/E8, both harnesses, all named clients, minimum/current VS Code and remaining Mac/Linux/Remote SSH matrix. | Exact VSIX/backend/client/OS versions and real results. Explicit grants/disclosure/account availability; separate authorization for any hosted-provider request, client-registration change or disruptive fault. WSL shutdown/restart is confined to the designated test target. |
| 8 — Release | T077–T079: reconcile every gate, prepare concrete VSIX/listing/download, verify publisher access, then publish only when the owner authorizes that release. | Public version and clean Marketplace installation observed. Publisher creation, baseline collection and local package generation do not close delivery. |

Steps 1–4 can proceed on isolated qualified development targets without upgrading the owner's running Risk. Step 5 is required before that Risk can serve as a supported acceptance target. Step 6 can use separate disposable fixtures once explicitly authorized; it need not wait for every editor view, but its relevant results must precede production-support claims and release. All 79 existing task obligations remain intact.

## Exact future authorization and test inputs

This is a description of what later execution needs, not a request to perform it now.

| Scope | Concrete authorization / information needed |
|---|---|
| Source implementation | Ratify the reviewed Spec150 design and authorize T001–T014 first in a named isolated checkout, including pinned development dependencies and synthetic local test processes. Existing owner runtime/configuration remains outside that scope. |
| Owner backend preparation | Name the installation/distro and selected runtime; identify actual executable/service-unit ownership and all active/unresolved work; approve the exact runtime/dependency/identity update with baseline, recovery and applicable change control. |
| Linux/WSL system tests | Designate disposable installation homes, ports, service units/accounts and test data. Authorize only those process/service faults and configuration effects, retaining exact production/Local-Lab boundaries. |
| Second-distro test | Name an existing suitable second distro or separately authorize its provisioning. No creation/start/stop of a distro is included in this review or in the extension's product scope. |
| Named assistant acceptance | Supply enabled client/account contexts and approve the exact NetClaw grant, registration change and disclosure scope. Authorize any hosted-provider smoke test and its input/budget separately; fixture-provider tests are labeled accordingly. |
| Publication | Confirm authenticated access to publisher `NetClaw`, choose the extension name/version and publishing-authentication path, then authorize publication of the reviewed exact package after qualification. Nothing should publish automatically from a spec/source push. |

The owner's current message explicitly excludes implementation, installation/upgrades, restarts, credential/configuration changes, provider requests, pushing, merging and publication. Those exclusions supersede earlier permission to push the initial spec. No additional permission is needed to complete this local document review.

## Publisher automation

The owner reports the portal now displays `NetClaw(NetClaw)` with no extensions. Preserve the exact reported publisher ID `NetClaw`; do not silently replace it with the earlier lowercase suggestion. Publisher creation is reported by the human; this review did not authenticate to its management API. Planned manifest identity is `publisher: "NetClaw"`; the extension name/version remain release inputs and are not reserved by this report.

Microsoft's official [`@vscode/vsce`](https://github.com/microsoft/vscode-vsce) provides a CLI and a small [Node API](https://github.com/microsoft/vscode-vsce/blob/main/src/api.ts), including `listFiles`, `createVSIX` and `publishVSIX`. Use that supported packaging/publishing path for the proposed release automation. Do not substitute Azure DevOps organization-extension installation APIs for VS Code Marketplace publication.

When authorized, pin a released vsce version, validate package contents, build the VSIX, record its digest, publish that exact package and read back its public version/install result. Authentication must have access to this publisher; the browser sign-in does not supply a CLI credential. Microsoft documents Entra-based publishing, and the current upstream vsce README also documents GitHub Actions trusted OIDC publishing; verify support in the pinned released version and publisher policy before choosing the pipeline. No package, credential, trust policy or workflow was installed/configured during this review. See [publishing documentation](https://code.visualstudio.com/api/working-with-extensions/publishing-extension).

## Review result

The baseline supports proceeding to a separately authorized isolated implementation, not connecting or publishing a nonexistent candidate. The first product milestone remains foundations plus a truthful, authenticated US1 connection. Owner-runtime migration and Spec149 qualification are separate prerequisites for real WSL acceptance. No task is completed or scope waived by this review.
