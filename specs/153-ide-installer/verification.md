# Spec153 verification — Mac installer complete; publication authorized; WSL return partial

2026-10-24 Mac return: **3/3 additional installer scenarios passed** against `575bb084a8ca54c629b8f39434539cbd10597065`: fresh OpenClaw, fresh Hermes with native cancellation and checkpoint resume, and a fresh four-claw mixed Risk. All six installations passed required Tiers 1–3; all four Risk installations also passed installer Risk readiness. Actual VS Code connection handoff reported ready for each scenario. No operational capability qualification was repeated. [Acceptance record](mac-return-installer-acceptance.md) and [sanitized evidence](evidence/mac-return-three-pass.json) contain the scope, unsuccessful fixture attempt, regression results and verified cleanup. This completes the requested additional Mac installer test scope; it does not change the platform results below. The owner subsequently authorized merge and publication; see [release verification](release-verification.md).

2026-10-18: **8/8 frozen Mac groups passed**. [MAC-COMPLETION.md](MAC-COMPLETION.md) defines exactly what this means and records decisions. Original task count remains **81/84 checked**; T081's Windows/WSL portion, T082 and final cross-platform T084 remain. The October 24 Windows/WSL return is partial, with real-host results and explicit blockers in [SUMMARY.md](../../spec153-wsl-return/SUMMARY.md) and [matrix.json](../../spec153-wsl-return/matrix.json). Packaging, the final recording and owner walkthrough follow readiness reconciliation and affected Mac regression.

## Follow-up: Tier 3 HUD probe timeout (T085) — 2026-11-25

A fresh WSL2 Ubuntu 24.04 install of v1.18.6 (focused OpenClaw claw) passed Tiers 1 and 2 but reported Tier 3 `unverified` / `probe_failed`, which blocked **Save verified connection**. The services were running and the HUD answered with the right identity. `GET /api/hud/management` runs `openclaw agents list --json` and took 10–13 s on that host; the probe gave every request 5 s, and the timeout was reported as `probe_failed`.

T085 gives the management route 20 s (above the HUD server's 15 s CLI limit), keeps 5 s for the other routes, reports timeouts as `probe_timeout` and retries `probe_timeout` while waiting for readiness.

| Check | Before | After |
| --- | --- | --- |
| Fake HUD, management route answers after 6 s | `probe_failed` | `identity_verified` |
| Full `setup-engine.py verify` of the same run on the same claw (v1.18.6 with and without the change) | Tier 3 `probe_failed`, exit 8 | Tier 3 `identity_verified`, exit 0 |
| `tests/test_setup_verification.py` | new tests fail | all pass |

Three tests were added: a slow management route within its limit verifies; a route past its limit reports `probe_timeout` while a refused connection still reports `probe_failed`; and the verifier's management timeout stays above the limit read from `management.js`. Caching the agent catalog in the HUD would make the route itself fast, but that is a separate change and not part of T085.

## Windows/WSL return — 2026-10-24

Exact Mac baseline `89627477fb470cd7c293e33e192c5983819d45d4`; fresh ext4 qualification branch `153-ide-installer-wsl-qualification`. Original dirty checkout, owner claws and credentials preserved. New source/host-bound plans and native reviews were used throughout. No archive overlay or Spec Kit regeneration.

| Exercise | Observed result |
| --- | --- |
| Ubuntu 26.04 focused wizard | Actual Windows VS Code / Linux remote extension host: OpenClaw and fresh managed-Python Hermes passed required Tiers 1–3. |
| Ubuntu 24.04 focused wizard | OpenClaw passed required tiers. Hermes installed but lost its engine during verification; unknown, not passed. Both new runs subsequently received verified reviewed cleanup. |
| Mixed Risk and management | Ubuntu 26.04 three-claw Risk passed installation and authenticated hot-member status. Actual focused OpenClaw/Hermes stop/start/restart reruns preserved neighbor hashes/PIDs. Full Risk cold-wake rerun remains blocked after volatile fixture loss. |
| Installed clients / Spec Kit | Ubuntu 26.04 Codex/Claude/VS Code MCP discovery passed in isolated profiles, with no hosted chat turn. Actual pinned Specify checks passed on both releases. Ubuntu 24.04 installed-client discovery and actual legacy CLI installs remain unrun. |
| Native systemd / regressions | Final source `cf97be1c286442660c355d50cf0788199a24c2a1`: **140 setup tests passed, zero skips on each release**, including native special paths and cold wake. Extension: 136 passed, three explicit skips on each release; check/build passed. Installer: 216 passed plus 16 subtests. Catalog checks passed. Exact versions, source bindings, log hashes and unsuccessful attempts are in the return evidence. |
| Native Windows gate | Missing/disabled WSL extension, supported/cancel, UTF-16, reviewed private handoff/restore/replay exercised. Other actual OS variants, expiry and wrong-host cases remain blocked/unrun. Source-development restoration does not qualify packaged VSIX activation. |

[Findings](wsl-findings.md) retain every observed failure and fix. The owner requested remote delivery and a Mac handoff, then cautioned against destabilizing the shared host. Further disposable installations and deliberate restart exercises were stopped; this does not change the acceptance scope. Cleanup retains uncertain/changed artifacts and private journals rather than forcing removal. See [cleanup evidence](../../spec153-wsl-return/evidence/cleanup.json).

The separately requested [60-second synthetic draft tour](../../spec153-wsl-return/demo/netclaw-setup-60s.mp4) was completed October 18. It configures two MCP selections and a mixed Risk draft in the actual UI, then cancels native Apply; it is not deployment acceptance or the final release recording. No publication or merge occurred in this WSL stage. Mac regressions and unresolved platform gates must be reconciled before final closure/integration.

All operator inputs below are synthetic unless stated otherwise. No provider turn, real channel message or device connection occurred. Existing owner credentials and claws were excluded. Passing supported installer scenarios does not qualify every one of the 110 catalog components against live infrastructure.

## Actual Mac acceptance

| Exercise | Result and evidence |
| --- | --- |
| Fresh macOS prerequisite/bootstrap and blank Minimal wizard | macOS 26.6.2 / 25G83 arm64 VM, 4 vCPU, 8GiB, 80GiB virtual disk. Native package actions installed prerequisites; supplied public checkout, no owner files. OpenClaw 2026.7.1-2; pyATS, GAIT, subnet and drawio/RFC all discovered; required Tiers 1–3 verified. [Report and timing](evidence/clean-mac-minimal.json), [report screenshot](evidence/clean-mac-result.jpg). |
| Both harness wizard journeys | Actual isolated VS Code 1.109 saved-plan review/Apply/report: OpenClaw 48.943s, Hermes 169.442s. Required tiers verified. These are separate fresh homes on the existing Mac, not additional clean OS tests. [Composed evidence](evidence/mac-composed-acceptance.json). |
| Mixed Risk, both Border harnesses | Each actual Border has three members, both member harnesses, inheritance/override, Ollama/LM Studio configurations, hot and on-demand modes. All four pairings, enrollment, identity-bound local self-status and Tiers 1–3 pass. On-demand wake and idempotence pass. Provider configurations are not model execution. [Evidence](evidence/mac-composed-acceptance.json). |
| Multiclaw management | Actual native connection/save/bind, reviewed USER.md edits, stop/start/restart on OpenClaw Border/OpenClaw member/Hermes member. Existing-NetClaw disclosure visible. Neighbor config/identity/service hashes and PIDs unchanged. Config-budget forms have fixture coverage; no native Hermes budget API support is invented. [Evidence](evidence/mac-composed-acceptance.json). |
| Legacy CLI | Actual `--plan` through controlling PTY; exact-hash synthetic review, 49.58s, required tiers verified. [Evidence](evidence/cli-native.json). |
| Installed assistants | Codex 0.163.0 registration and native app-server discovery of eight tools; Claude Code 2.1.286 registration/connected handshake with tools capability (CLI does not expose the full list); actual VS Code MCP client used by Copilot discovers eight tools. No signed-in hosted chat turn. Same seven intent cases across three client formats remain contract fixtures. [Evidence](evidence/assistant-clients.json). |
| Deployment Spec Kit | Actual pinned Specify 0.7.1 renders Codex, Claude, Copilot and combined integrations; effective templates/commands verified; overriding a required template is refused. Included in setup regression. |
| Earlier native focused/preservation acceptance | Three fresh-home engine installations (59.136s, 67.962s, 52.500s), first-claw file/PID preservation and five reviewed cleanups. [Evidence](evidence/mac-native-local.json). |

## Synthetic usability and performance

The owner replaced recruited participants with synthetic engineering and a final owner walkthrough. [UI evidence](evidence/ui-workflows.json) covers nine light/dark/high-contrast × 360/700/1200px combinations; six native keyboard dialog/cancel paths per combination; keyboard search/Tab; 200% zoom; numeric Shape Advisor; both-direction shape override; actual report inspection. Cached search/render took **2.3–2.8ms**. Earlier visual preview screenshots remain in [editor-preview](evidence/editor-preview/report.json).

For the clean VM's unmodified Minimal profile, three blank native wizard journeys measured **8.289s, 7.556s and 7.519s**; median **7.556s**. These are automated choice/input timings, not human comprehension measurements. One journey installed; two stopped after validation. **Apply to verified Tier 3: 110.755s**. Package acquisition phases totaled **55.918s**, including resolver, transfer, unpack/build/install; wire-only transfer cannot be isolated by the adapters. OS/Homebrew prerequisite bootstrap occurred before this benchmark and is excluded. No model download occurred. Full phase samples are in [clean-mac-minimal.json](evidence/clean-mac-minimal.json).

Twenty-nine actual engine stdout frames reached the webview's next animation frame in **0–14ms**. The native plan review now restores visible progress before execution advances. Validation messages survive unchanged snapshots and invalidate when the draft changes. This measurement covers observed engine-output delivery and rendering, not user reaction time.

## Regression and analysis

| Check | Result |
| --- | --- |
| Setup Python | **136 passed, zero skips**, 20.703s, with actual pinned Specify, Hermes, certificate and MCP interpreters supplied. Final GAIT record ownership tightening also passed all six deployment and four component tests. |
| Extension | **134 passed, two skips**, 25.351s; TypeScript and build passed. Skips require an installed-native workspace fixture and cached RAG embedding model. Actual disposable setup/management is separately covered; RAG retrieval is outside this fixed installer gate. |
| Installer selection | **216 passed plus 16 subtests**, 31.33s. Retained relevant legacy regression, unchanged by final setup-only fixes. |
| Catalog/schema | 110 components, 237 skills, 124 registered MCP servers and 52 external integrations; metadata/generation/coverage checks pass, zero unexplained joins. Plan schemas identical. |
| Traceability | All 84 unique tasks mapped; 56 FR and 14 SC covered, no unmapped tasks. Scope remained fixed. |
| Links | 126 syntactically valid links; 124 checked successfully and two retained auth/transport dispositions. No unexplained dead link. See catalog-links.json; not a claim of universal unauthenticated access. |
| Privacy | Default report structural redaction, secret/native-channel tests and final seeded artifact scan pass. Scan scope and limits in [privacy-audit.json](evidence/privacy-audit.json). |

[Test hashes](evidence/test-results.json) identify retained Mac logs. [Analysis](analysis.md) records original design remediation and subsequent runtime findings. No unresolved implementation finding remained in the frozen Mac scope. Later Windows findings and open cross-platform closure are recorded separately above; the WSL fixes still require affected Mac regression.

Actual isolated supplements: [ANTA catalog canary](evidence/anta-canary.json), [certificate helper](evidence/certificate-helper.json), [gtrace build](evidence/gtrace-build.json), and [HUD dependency remove/restore observation](evidence/hud-dependencies.json). None sends network configuration or claims general integration qualification.

## Recovery, ownership and cleanup

The engine retains writer locks, journals effects before writes, and pauses after native input cancellation/editor loss. Real child-process tests exercise surviving writers and disconnect. Owned partial home/skill/identity/source files may repair only against exact journal evidence and fresh review. Source recovery stops at the dependency boundary. Runtime and native services require their own observed postconditions; uncertain components/registration/inventory remain unknown instead of being replayed. Apply/Resume never advances beyond unsettled onboarding.

Source indexes bind service launch and management to the selected copied source. Canonical interpreter paths agree across setup and management. Native Hermes MCP discovery verifies a live owned registry for servers outside the protected companion allowlist; the allowlist is not widened. Reports distinguish artifact, native discovery, local canary and authenticated HUD readiness from optional live tiers.

[Actual cleanup](evidence/mac-cleanup.json) stopped and removed all five final host test installations' native controllers, including both four-claw Risks. The OpenClaw-Border Risk returned `configuration_required` because cleanup correctly retained the Hermes identity manifest changed by the management test. Audit ownership records and dependency directories remain private. No changed/shared file was forced away. Earlier diagnostic and clean-VM runs also used reviewed cleanup; the final Minimal cleanup verified, and the VM is stopped with its disk retained for reproduction.

Cleanup's closed-connection port probe tolerates TCP TIME_WAIT while still refusing an active listener. A launchd list/print disappearance race now requires a second successful parsed listing to establish absence; manager failures remain unknown.

## Supported limits and remaining stages

- Optional provider/channel/device tiers were unselected. They require designated resources and separate native consent. No existing credentials were borrowed and no live-host export was received.
- Production requests refuse when mandatory installation-bound controls are unverified; no silent downgrade. Hermes model guard remains unsupported.
- Webex 0.1.3 is incompatible with the pinned OpenClaw API and refuses before effects. The legacy shared-host `in2n-production` component is unavailable in this independent-home installer. `computer-use` remains WSL-only/native. These are explicit tested dispositions, not unfinished Mac success claims.
- Keychain popups in ephemeral editors were cancelled; test editors use `--use-mock-keychain`. No reset or owner keychain change.
- Windows/WSL now performs only the bounded smoke/platform-difference matrix in [WSL-HANDOFF.md](WSL-HANDOFF.md). The old archive is obsolete. New source plans/reviews must bind to the Windows/WSL host.
- Return fixes and sanitized evidence to this Mac for regression and T084 closure, then owner walkthrough/recording and separately authorized package/publication. Nothing has been published or packaged as a release.
