# Qualification and release contract

These are future acceptance gates, not passes. Store sanitized results under `specs/150-vscode-extension/evidence/` and summarize in a future `verification.md`. Each result identifies source/VSIX digest, OS/build/architecture, editor/client version, extension-host context, actual installation/harness version, provider mode, action and observed outcome. Keep raw private evidence local; Git stores sanitized summaries/digests only. Unrun, blocked, failed and passed are distinct.

## Required environment matrix

Initial qualification fixtures are Windows 11 with WSL2 (record exact Windows/WSL builds), Ubuntu 24.04 LTS and Ubuntu 26.04, and macOS 26.5.2 or the owner's later recorded supported version. Do not infer support for all versions in an OS family. Record actual versions before running; a changed fixture must be documented and still satisfy every required family. Test minimum VS Code 1.102.0 and release-current stable; freeze exact current version at qualification.

| ID | Desktop / context | Managed host | Mandatory evidence |
|---|---|---|---|
| E1 | macOS / local workspace | Same Mac | Real installed VSIX, connect, settings/read-only work, saved-state preservation. |
| E2 | Ubuntu 24.04 and 26.04 / local | Same native Linux | Both distro fixtures, existing install discovery and management/denial. |
| E3 | Windows 11 / WSL extension host | Owner's actual WSL2 Linux NetClaw | Real Windows desktop + WSL, path/principal/distro identity, no Windows fallback; primary handoff gate. |
| E4 | Windows/macOS/Linux / Remote SSH | Native Linux | All three desktop clients; verified host identity and owned job reconnect. |
| E5 | Windows / Remote SSH | macOS | Cross-OS paths/authentication, no assumption remote localhost is local. |
| E6 | macOS or Linux / Remote SSH | WSL Linux with existing reachable SSH setup | WSL target identity and disconnect/reconnect. Extension does not install/configure SSH. |
| E7 | Local Windows workspace with configured SSH profile | Native Linux or macOS | Fixed-launcher path, safe quoting, explicit target and credentials. |
| E8 | Two WSL distributions / two installations | Distinct WSL identities | Same-label/profile confusion denial; only an isolated test target may be restarted for the fault test. |

WSL shutdown/restart is a disruptive acceptance action, never part of read-only handoff discovery. The owner must designate the test distribution and authorize the interruption after active jobs and rollback/recovery are reviewed. Preserve unknown work and prove zero replay after restart. Native Linux fixture tests or WSL environment variables do not satisfy E3/E8.

## Runtime and client matrix

- Standalone OpenClaw and Hermes; iN2N Border/member O/O, O/H, H/O, H/H; eN2N H↔H and H↔O in both directions plus O↔O regression. Record actual qualification per action and platform. Begin with existing qualified read-only subnet tools and contextual chat; do not claim every registered tool works.
- Real OpenClaw and Hermes connections on E1, E2 and E3 are required. Run the full mixed/all-Hermes federation matrix on native Linux and WSL as well as retained Mac reference coverage. Resolve spec149 T040 Linux/WSL host-control gaps before claiming affected production control works. Missing qualification remains a release blocker for required supported workflows, not a green “unavailable” replacement.
- Actual Copilot, Claude Code and Codex each run discovery, NL inventory, permitted delegation, proposal, owned status, denied direct/private method, self-approval rejection, grant expiry/revocation and lost-response recovery. Each client must run in real WSL and Remote SSH contexts with OpenClaw/Hermes targets. Record exact client versions/account prerequisites and client policy failures; fixture-only passes do not count.
- Core Chat/Canvas must pass with Copilot unavailable. Configured backend credentials are reused; no provider key copied to editor/client config. Hosted-provider smoke evidence is separate from deterministic-provider tool/runtime evidence; disclose which was run and obtain authorization for any new external data boundary.

## Required behavioral gates

| Gate | Required scenarios / evidence | Criteria |
|---|---|---|
| Q1 Connection/isolation | Same display labels, multiple windows, no-folder/multi-root, changed SSH key, wrong UUID/distro, revoked grant, incompatible contract, stopped prerequisites | FR-004–008/035, SC-001/005; first read-only workflow within five minutes on each supported row. |
| Q2 Domain coverage | Every row of editor domain table has positive supported workflow plus truthful denied/unavailable/empty/stale states | SC-002; screenshots alone do not prove handlers. |
| Q3 Durable work | Lost receipt before/after dispatch, bridge exit, editor reload, backend crash, WSL restart, cancel races, expired nonce, target switch | SC-007/011; no uncertain replay, actual owned recovery and unknown outcomes. |
| Q4 Approval/policy | Unapproved/withdrawn CR, no real baseline, missing audit, invalid lab scope/APPLY phase, read-only collector, forbidden operation, injected peer instructions, nested delegation escape | SC-006/013; refuse before dispatch, bounded rollback and visible failure. |
| Q5 Settings/secrets | Keep/replace/clear, synthetic masks/blank/multiline, unrelated entries/comments, external edit, file/symlink ownership, legacy credential migration, restart/rollback failure | SC-008/011; no secret marker in views/logs/exports/package; real revision conflicts. |
| Q6 Usage/provenance | Exact known tokens/cost fixtures, missing Hermes aggregate, source gaps, stale topology, simulation, memory validity, distinct external-client billing | SC-009 and FR-027–032/044. |
| Q7 UI performance/accessibility | 100 members, 100 peers, 1,000 integration/tool rows; keyboard workflows, all themes, hostile/oversize webview content | SC-004/010; measure p95 navigation <1s and post-refresh rendering <2s, excluding reported backend latency. |
| Q8 Regression/coherence | Existing HUD/Canvas/mobile/CLI/runtime/federation paths, catalog coverage, env docs, isolated dependencies and private registration | FR-039–040; current applicable suites run in their declared isolated environments. |
| Q9 Package/release | Clean profile VSIX, candidate upgrade/disable/uninstall, package allowlist, no private artifacts, Marketplace exact version install | SC-012; actual public URL + matching downloadable VSIX + observed clean connection. |

## Release order

1. Confirm owner-selected authorized publisher and extension ID; validate availability before producing distributable candidates. Select semantic extension/backend versions under existing release policy, pin dependencies and license/SBOM sources, and update support matrix.
2. Package only extension build/resources/docs/license using an explicit allowlist. Copy mobile `icon.png`; derive Activity Bar mark. Keep `.env`, journal/GAIT databases, private snapshots, test fixtures with sensitive content, and NetClaw runtime trees out of the VSIX.
3. Complete Q1–Q8 and every required environment/client row. Review blockers and evidence, walkthrough, screenshots, privacy, README/changelog and support links. Test update from previous candidate and documented rollback without erasing backend state.
4. Prepare release artifacts and local milestone blog draft for owner review. Ask for public publication authorization when the concrete release is ready unless already explicitly authorized for that release. Pushing this spec branch is not Marketplace authorization.
5. Publish through the authorized publisher, retrieve public listing/version, install that exact version from Marketplace in a clean profile, connect to a reference installation and compare the release VSIX digest. Only then close release delivery. No fabricated public URL, account entitlement or successful install.
