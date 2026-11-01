# Changelog

NetClaw source releases use `1.x.y`. Feature specs increment the minor version and reset the patch; fixes, documentation and maintenance increment the patch. Every release records its numbered specs. Component and mobile distribution versions are independent.

## [1.18.0] - 2026-11-01

Spec [162-netconverterai](specs/162-netconverterai/spec.md): guarded NetConverter conversion, exact-file hosted approval, private pyATS candidate application, installer modes and a dedicated Risk member. Actual approved synthetic conversions, modeled Batfish checks, protected IOS-XE rehearsal and native Border/member discovery are recorded with their limits. Includes the minor fixes found during live qualification and preserves upstream Convergence and production-mode work through 1.17.1. See [release notes](docs/releases/1.18.0.md).

## [1.17.1] - 2026-11-01

Production-mode fixes found by live qualification (spec 167):

- Recognise DefenseClaw 1.x's OpenClaw plugin route (plugin enabled, allowed and loaded; proxy reachable) as model-guarded, alongside the `defenseclaw/<model>` provider route. Unknown provider domains stay blocked fail-closed by the proxy.
- Member homes carry only the DefenseClaw plugin entries and the Border's `security.mode`, so production members run guarded instead of refusing or bypassing the guard.
- Member list and health report `starts_on_route` for down on-demand members, so a Border routes to them instead of reporting them unavailable.
- `gateway_ws` resolves env SecretRef gateway tokens and refuses unsupported SecretRef sources instead of sending an object as the token.
- `defenseclaw-enable.sh`, `install.sh` and `netclaw-secure-start.sh` install a pinned, checksum-verified DefenseClaw release instead of piping unpinned installers; OpenShell is opt-in and must match a reviewed checksum. Docs cover non-interactive setup, provider registration and the DefenseClaw SecretRef gateway-token limitation.

Spec [167-production-mode-qualification](specs/167-production-mode-qualification/spec.md). See [release notes](docs/releases/1.17.1.md).

## [1.17.0] - 2026-10-31

- Cold-start on-demand iN2N members as confined system instances on OpenClaw 2026.10.9 and later: `in2n-services.py coldstart install` adds a hardened `netclaw-coldmember@.service` template and a polkit rule that lets only the installing operator start or stop only those instances, without sudo at run time. Posture and production cold-start use it when installed and authorized.

Spec [166-coldstart-system-members](specs/166-coldstart-system-members/spec.md). See [release notes](docs/releases/1.17.0.md).

## [1.16.0] - 2026-10-31

- Keep hardened iN2N members working on OpenClaw 2026.10.9 and later: always-on members can run as system units (`in2n-services.py generate|enable --system`, sudo -n only) with full confinement, and the Risk posture reports confinement unavailable instead of claiming a configuration that cannot run OpenClaw members.
- Add an opt-in `scripts/border-harden.py` that places an OpenClaw Border in the Docker sandbox and turns off Skill Workshop learning, dry-run by default.
- Hand Convergence observations from the HUD to the Border through Canvas with a bounded evidence envelope; add an optional `convergence` Risk member profile and stronger evidence guidance (capability search, latest-100 bound, record-only semantics, provenance).
- Name routable specialty capabilities when a Risk route has no capable member.

Specs [164-convergence-border](specs/164-convergence-border/spec.md) and [165-convergence-confinement](specs/165-convergence-confinement/spec.md). See [release notes](docs/releases/1.16.0.md).

## [1.15.0] - 2026-10-31

- Add an optional, disabled-by-default Convergence reader and HUD for retained flow summaries and same-window evidence.
- Include isolated Linux installation, viewer-scoped access, coverage labels and disposable demo/host integration checks.

Spec [162-convergence-read](specs/162-convergence-read/spec.md). See [release notes](docs/releases/1.15.0.md).

## [1.14.0] - 2026-10-30

- Add static/dynamic testbed choice and source selection to VS Code, new-plan terminal setup and `setup.sh`.
- Pin upstream pyATS MCP dynamic tooling and compose reviewed inventories through a managed build/validate/activate lifecycle.
- Add source contracts, examples and fixture coverage for 12 named platforms plus structured/REST exports; preserve static inventory and existing change controls.

Spec [160-dynamic-pyats-testbeds](specs/160-dynamic-pyats-testbeds/spec.md). See [release notes](docs/releases/1.14.0.md).

## [1.13.1] - 2026-10-29

Minor fixes, addressed oldest to newest:

- #262 / [Spec156](specs/156-openclaw-env-defaults/spec.md): resolve optional MCP defaults during installation for qualified native runtimes; preserve operator overrides and required inputs.
- #300 / [Spec157](specs/157-hermes-canvas-retry/spec.md): retain Canvas ancestor context across Hermes conversation-setup retries.
- #301 / [Spec158](specs/158-hermes-chat-recovery/spec.md): recover the original submitted question while preserving edited or cleared drafts and preventing duplicate transcript entries.
- #302 / [Spec159](specs/159-hermes-uncertain-capacity/spec.md): explicitly release a reviewed unknown admission reservation without erasing uncertainty or replaying work.

See [release notes](docs/releases/1.13.1.md) for upgrade guidance and verification limits.

## [1.13.0] - 2026-10-25

Spec [155-border-channel-setup](specs/155-border-channel-setup/spec.md). See [release notes](docs/releases/1.13.0.md).

## [1.12.0] - 2026-10-24

- Install separate Focused NetClaws and mixed OpenClaw/Hermes Risks from VS Code, CLI or assistant-guided plans, with exact native review and independent homes/credentials.
- Add a canonical setup catalog, durable pause/resume, verified connection handoff, private reports and ownership-safe cleanup.
- Include Windows/WSL return fixes and three additional actual Mac installer passes; retain explicit incomplete platform qualification.

Spec [153-ide-installer](specs/153-ide-installer/spec.md). See [release notes](docs/releases/1.12.0.md).

## [1.11.0] - 2026-10-16

- Add VS Code native workspace Markdown read/edit/upload without delete, verified owned-claw lifecycle and offline recovery, and Save & Restart.
- Preserve native OpenClaw workspace expansion and isolate systemd discovery from neighboring installations.
- Document exact Mac and WSL acceptance, source/helper upgrade requirements and unsupported symlink/live-lifecycle boundaries.

Spec [152-workspace-claw-controls](specs/152-workspace-claw-controls/spec.md). See [release notes](docs/releases/1.11.0.md).

## [1.10.0] - 2026-10-11

- Add an AYN-inspired VS Code workbench with responsive cards/forms, branded artwork, clearer connection setup and attributable3D BGP visualization.
- Add reviewed testbed YAML/JSON/CSV management and contextual per-MCP configuration/setup.
- Add DefenseClaw/OpenShell security rule, mode, status and log controls with explicit shared-scope and weakening reviews.
- Record local source acceptance and remaining vendor/platform limits. Packaging, deployment and release/Marketplace publication remain held.

Spec [151-extension-experience](specs/151-extension-experience/spec.md). See [release notes](docs/releases/1.10.0.md).

## [1.9.0] - 2026-10-11

- Prepare the unpublished NetClaw VS Code extension for existing installations, with integrated Chat, Canvas, Avatar, RAG, observation panels, reviewed controls and opt-in assistant access.
- Keep runtime execution, federation, authorization and audit in the existing NetClaw; no base runtime or installer changes.
- Record exact Mac and Windows/WSL evidence and retain the final RAG-delta WSL confirmation as outstanding. Marketplace and source-release publication remain on hold.

Spec [150-vscode-extension](specs/150-vscode-extension/spec.md). See [release notes](docs/releases/1.9.0.md).

## [1.8.0] - 2026-10-10

- Add selected-installation Hermes NCFED Border/member execution, protected operator delegation, contextual peer chat and bounded qualified subnet work.
- Carry additive harness metadata alongside capabilities without granting authority; preserve unknown values and existing enrollment/authorization.
- Persist admission/effect ownership, uncertain outcomes and cancellation state without automatic replay.
- Update Mobile to 1.0.3 (6): Summary Border type, durable request/reconnect recovery, voice-origin preservation, explicit media limits and Chat/Siri/Watch/Live Activity states. Signed build uploaded to App Store Connect; no public release.
- Preserve existing OpenClaw paths and document actual acceptance coverage and remaining platform qualification.

Spec [149-hermes-ncfed-federation](specs/149-hermes-ncfed-federation/spec.md). See [release notes](docs/releases/1.8.0.md).

## [1.7.0] - 2026-10-10

- Connect Hermes to shared HUD Chat, Canvas, local Avatar, owned history and runtime panels through a private MCP bridge and protected companion.
- Persist runtime selection and isolated installation state; qualify the real read-only subnet tool and skill with request-correlated evidence.
- Add durable admission, bounded recovery and cooperative stop without automatic replay; preserve populated homes and existing OpenClaw workflows.
- Explain runtime choices, upgrade steps and exact Mac/WSL qualification. Hermes n2n/iN2N federation follows in spec 149.

Spec [148-hermes-hud-integration](specs/148-hermes-hud-integration/spec.md). See [release notes](docs/releases/1.7.0.md).

## [1.6.2] - 2026-10-10

Spec [147-installer-followups](specs/147-installer-followups/spec.md). See [release notes](docs/releases/1.6.2.md).

## [1.6.1] - 2026-10-09

- Import filled checkout dotenv settings before runtime onboarding while preserving existing runtime credentials; add a previewable repair command.
- Stop installation when onboarding fails and honor the selected OpenClaw state/config paths.

Spec [146-dotenv-onboarding-preservation](specs/146-dotenv-onboarding-preservation/spec.md). See [release notes](docs/releases/1.6.1.md).

## [1.6.0] - 2026-10-09

- Add John/Lobster Avatar as a shared HUD Chat interface with authenticated local macOS speech and playback/camera controls.
- Repair OpenClaw model/history compatibility and preserve the selected CLI when pinning Node.
- Include an optional disabled experimental Tavus foundation; hosted acceptance and cloned voice remain deferred.

Spec [144-tavus-netclaw-pal](specs/144-tavus-netclaw-pal/spec.md). See [release notes](docs/releases/1.6.0.md).

## [1.5.0] - 2026-10-05

- Upgrade 35 owned FastMCP servers to FastMCP 4.0.11 / MCP SDK 2.3.0 with modern and legacy protocol support and explicit stateless HTTP for Dot and reviewed UML.
- Add reviewed external source migrations, isolated bounds, safe GAIT runtime promotion/restore, and framework regression coverage.
- Publish the migration inventory, test evidence and rollback guide; five external ports and licensed RADKit validation remain open.

- Add current MCP Tasks for 298 tools across 35 integrations, including the pinned persistent pyATS runtime and selective FastMCP Tasks adoption.

Coordinated specs [141](specs/141-fastmcp-stateless-upgrade/spec.md) and [142](specs/142-mcp-async-tasks/spec.md). See [release notes](docs/releases/1.5.0.md).

## [1.4.0] - 2026-10-01

- Add trusted-interface HUD access, configured-agent compatibility, model/effort controls, context/account quota indicators and runtime Settings.
- Preserve active chats and reopen previous browser-owned conversations with their original gateway context.

Coordinated specs 135–140; see the [release plan](specs/140-hud-chat-workflows/release-plan.md) and [release notes](docs/releases/1.4.0.md).

## [1.3.0] - 2026-10-01

- NetClaw can be connected to a ChatGPT Dot as an OAuth-protected MCP plugin (`netclaw-dot-mcp`): three read-only synthetic tools plus an asynchronous `netclaw_ask` / `netclaw_job_result` bridge to the local agent.
- Single-owner OAuth 2.1 (authorization code + PKCE, passphrase-gated approval), audit-first execution, nginx installer helper and operator guide; experimental and lab-data only.

Spec [134-netclaw-dot](specs/134-netclaw-dot/spec.md). See [release notes](docs/releases/1.3.0.md).

## [1.2.1] - 2026-10-01

- Isolate legacy installer Python dependencies and bind MCP launchers to their runtimes.
- Report dependency failures accurately; fix independent component paths, Nautobot source selection and gNMI startup.

Spec [133-installer-python-isolation](specs/133-installer-python-isolation/spec.md). See [release notes](docs/releases/1.2.1.md).

## [1.2.0] - 2026-09-29

- Equinix Fabric and Network Edge MCP integration with two skills, OAuth, scoped Risk membership, installer/setup and HUD entries.
- Documented Fabric create/update/actions gated by observed baselines, exact-operation ServiceNow approval and GAIT; delete is not exposed upstream.

Spec [132-equinix-fabric-mcp](specs/132-equinix-fabric-mcp/spec.md). See [release notes](docs/releases/1.2.0.md).

## [1.1.0] - 2026-09-28

- Standard Chat is now the default HUD view, alongside preserved Canvas and native OpenClaw in a separate tab.
- Isolated conversations, draft/error recovery, safe native UI navigation and corrected empty gateway reply classification.

Spec [130-chat-interface-switch](specs/130-chat-interface-switch/spec.md). See [release notes](docs/releases/1.1.0.md).

## [1.0.0] - 2026-09-28

First official versioned source release, including the function-first HUD (spec127), optional Jev Science Officer (spec125), README refresh (spec126), and contribution/release foundation (spec129), on top of the existing network engineering platform.

- 233 skills and 173 MCP integrations, with selective installation.
- Operations panels, preserved Canvas, specialist federation, cited document retrieval, mobile and Zoom integration surfaces.
- Numbered Spec Kit contribution workflow, PR template and repeatable versioned releases.
- Restored the protected HUD inventory statement required by documentation reconciliation.

See [full release notes and validation boundaries](docs/releases/1.0.0.md).

## NetConverter unpublished development history

These branch-local milestones predate reconciliation with upstream 1.17.1; they are not additional published releases. Their final source release is 1.18.0.

## [NetConverter pre-release 1.15.5] - 2026-11-01 (source milestone; unpublished)

Minor fix from Spec162's real Risk qualification: bind each Border/member MCP to
its reviewed local federation API before native registration freezes environment
aliases. Previously the installer could verify tool discovery while the tools
still addressed default port 8179. A regression reproduces the stale endpoint and
checks both native and companion registrations against each selected port.
Focused-claw endpoint settings retain their existing behavior.

The first Risk install completed, but its actual delegation trial failed and the
agent attempted an unrequested configuration repair. That attempt is retained as
failed evidence. A fresh clean run then passed all 26 effects, required verification,
rendered HUD and real native Border/member authenticated discovery. All 44 scoped
Spec162 tasks and three additional live loops are complete, with simulated review
inputs explicitly distinguished from human approval.
See [Spec162 verification](specs/162-netconverterai/verification.md).

## [NetConverter pre-release 1.15.4] - 2026-11-01 (source milestone; unpublished)

Minor fix for Spec162 Risk composition: add the missing dedicated OpenClaw
NetConverter member profile to the shared VS Code/terminal setup catalog. The
Border remains a router with no NetConverter component or account credential;
the member owns its guarded MCP, skill and private integration state. A regression
reproduced the previously rejected member plan and verifies Border isolation.

The owner requested an automated disposable Border-plus-one-member installation
test with simulated review input. Actual runtime/federation/guard evidence is
tracked separately from human native review. See [verification](specs/162-netconverterai/verification.md).
Extension code remains 1.5.0; profiles are read from the selected source catalog.

## [NetConverter pre-release 1.15.3] - 2026-11-01 (source milestone; unpublished)

Minor fixes discovered during real Spec162 native runtime and appliance qualification:

- Include the two public reference snapshots imported by the installed HUD, fixing its first-load module failure.
- Resolve the native gateway's environment SecretRef for authenticated HUD and Terminal Intent requests; unresolved explicit references fail closed.
- Add an explicitly started, authenticated, installation-bound foreground pyATS session for clients that close STDIO between turns. Keep the original tool identities, live inventory binding, private task store and one-use apply controls. Process exit requires fresh composition and review.
- Bind migration baseline receipts to the real captured private artifact and reject reference-note substitution before API APPLY and again in the configuration consumer. The live agent exposed this gap; the original baseline remained retained.
- Record actual CML capacity juggling, IOS-XE target/peer boot and private baseline collection, including retained failed bootstrap/legacy SSH attempts and independently verified target host-key rotation.

Spec [162-netconverterai](specs/162-netconverterai/spec.md). See [milestone notes](docs/releases/1.15.3.md) and current [qualification evidence](specs/162-netconverterai/verification.md). Extension source remains **1.5.0**; no extension code changed in this patch.

## [NetConverter pre-release 1.15.2] - 2026-10-31 (source milestone; unpublished)

Minor fixes discovered in the owner-approved real Spec162 rehearsal installation:

- Install the NetConverter guard's Python environment under the selected runtime root so native dependency observation accepts it without weakening source ownership or symlink checks.
- Make the native pyATS installer and observer use the same qualified revision and required source files as the staged runtime installer. This removes a stale pin that installed a server without dynamic-testbed support.
- Verify an actual OpenClaw/Claude turn, agent-driven NetConverter authentication/capability discovery, native MCP discovery and the repaired dynamic pyATS runtime. Keep the original partial installation report and separate maintenance evidence.
- Record remaining CML connectivity, image, protected application and live behavior gaps; no 100% acceptance or deployment claim.

Spec [162-netconverterai](specs/162-netconverterai/spec.md), including a correction to the Spec160 native installation path. See [milestone notes](docs/releases/1.15.2.md). Extension source remains **1.5.0**; no extension code changed in this patch.

## [NetConverter pre-release 1.15.1] - 2026-10-31 (source milestone; unpublished)

Minor fixes discovered using the real Spec162 account:

- Recognize successful hosted account envelopes and reject explicit failed envelopes.
- Preserve nested review verdicts, manual-work counts, partial/truncated evidence and absent reports without exposing private prose.
- Correct text/XML capability guidance and record two separately approved real synthetic routing conversions, including verified downloads and unresolved review items.
- Restore isolated Batfish startup compatibility for its pinned pybatfish client with `setuptools<81`.
- Add three live qualification loops; retain the native UI and actual appliance/application/forwarding gates. Source checks do not establish 100% live acceptance.

Spec [162-netconverterai](specs/162-netconverterai/spec.md). See [milestone notes](docs/releases/1.15.1.md). Extension source remains **1.5.0**; no extension code changed in this patch.

## [NetConverter pre-release 1.15.0] - 2026-10-30 (source milestone; unpublished)

- Add optional NetConverter hosted-readonly/local-Terminal setup, account-bound discovery and native exact-file submission approval.
- Keep source, conversion reports and candidate application private; extend the existing Local/Lab API and pyATS identities with one-use artifact binding and unknown-outcome recovery.
- Add a migration skill, virtual-target rehearsal procedure, evidence templates and staged community article; correct Batfish partial-parse/query-failure interpretation.
- Record five review/fix/test iterations. Live NetConverter account/client discovery, vendor-target acceptance and native UI/platform qualifications remain open; controlled tests do not complete those gates.

Spec [162-netconverterai](specs/162-netconverterai/spec.md). See [milestone notes](specs/162-netconverterai/source-milestone-1.15.0.md). Coordinated extension source: **1.5.0**, unpublished.

