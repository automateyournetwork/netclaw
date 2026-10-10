# Feature Specification: Installer and first-use reliability

**Feature Branch**: `147-installer-followups`
**Created**: 2026-10-10
**Status**: Specified from user reports and current-main investigation; implementation pending
**Baseline**: `b4334bf255cd53aecd2e81f51abe63deea53f1df` (includes Nick's merged PR #287 and dotenv PR #288).

## Problem and evidence

Users report that an install can fail late, select incompatible dependencies, or finish with network tools unavailable. Two reports were supplied: a macOS/Homebrew/Hermes run selecting 108 components, and a Linux/OpenClaw/Ollama first-use report dated 2026-09-13. Their exact repository revisions are unknown. [Report triage](reports.md) distinguishes their observations from independently verified current behavior.

The priority is a usable, verifiable path from component selection to agent tool discovery. Existing host preflight, component isolation, configuration merging and preservation fixes remain the baseline.

## User Scenarios & Testing

### US1 — Select a supported host and runtime (P1)

An operator receives an actionable, aggregated preflight before installation or onboarding mutates state.

1. Unsupported Node versions are rejected for the selected OpenClaw target, including unsupported odd release lines and insufficient patch versions.
2. Existing Python 3.12 is preferred where appropriate; an explicit compatible interpreter remains respected. Interpreter support and individual package/architecture support are separate checks.
3. A selection requiring uv, uvx, Go/CGO, Docker or other declared tools reports those prerequisites together. An all-components selection on macOS identifies Linux-only components.
4. Package-manager instructions select compatible versions and resolve both installer and component interpreter paths after any approved repair.

### US2 — Install the runtime without ambiguous success (P1)

The OpenClaw install command follows the selected Node/npm release contract. Permission failures give a user-owned installation path; errors are not presumed to be privilege failures. Lifecycle scripts required by the target runtime run under a narrow, version-aware policy.

Acceptance covers npm before 11.16, npm 11.16+, npm 12+, permission errors, failed package installation, missing/broken runtime executable and runtime configuration preservation. No blanket approval of arbitrary dependency scripts or automatic model downloads.

### US3 — Discover the tools that were selected (P1)

For the reported twelve components, a successful supported install provides an explicit agent-access path with a launcher matching the installed environment. Native MCP registration is preferred; any intentional skill-mediated path is explicitly identified and verified.

1. Selecting pyATS, NetBox and CML produces usable bindings without copying the entire template over runtime configuration.
2. Each affected Python component uses its recorded interpreter even when a different Python appears first on the gateway PATH.
3. pyATS reuses the owned stdio-to-loopback-HTTP bridge. A standalone, public HTTP daemon is not required.
4. A canary with a known synthetic tool is discovered by the selected runtime, using explicit transport where required.
5. Reruns preserve persona files, credentials, custom registrations and unrelated settings. Native exposure retains existing write approvals and tool restrictions.

### US4 — Understand first-use readiness (P1)

The final result distinguishes installed artifacts, registration, protocol/tool discovery, provider readiness and actual endpoint verification.

1. Missing launchers, failed handshakes, empty/unexpected tool lists and a zero exit code with a failed structured probe cannot produce a tools-ready result.
2. Configured remote services whose credentials/connectivity were not checked are marked unverified.
3. Readiness is deterministic installer/runtime output, independent of the selected model's prose.
4. An optional operator-requested first-use canary verifies a harmless tool call and its provenance. A failed tool must yield an explicit unavailable result; fabricated network facts never count as acceptance evidence. No claim that prompts alone eliminate arbitrary model hallucinations.

### US5 — Use local or remote Ollama correctly (P2)

Readiness checks resolve the configured endpoint and exact model. A remote host does not require an Ollama executable on the NetClaw host. Report unreachable endpoints, missing models, incompatible API routing and unverified tool-call capability distinctly. No automatic pull, provider inference or live device operation is part of this specification's investigation.

## Functional requirements

- **FR-001**: Trace every report to its disposition and evidence; retain fixes already merged rather than reimplementing historical failures.
- **FR-002**: Share the Node compatibility rule between preflight and runtime installation. Validate the version range for the selected runtime target and document its source/date.
- **FR-003**: Make npm installation version-aware and offer a rootless path without silently changing a user's global npm policy.
- **FR-004**: Map all twelve reported components to an explicit access mode, executable/transport, credential requirements and verification method; a selected unsupported path must be reported.
- **FR-005**: Preserve per-component dependency isolation and recorded launcher bindings, including skill-based invocation. Do not purge or repurpose existing user-managed environments.
- **FR-006**: Check discovery through the selected runtime as well as direct MCP protocol tests; evaluate structured results and expected capabilities, not only exit codes.
- **FR-007**: Return failure for required install/registration/discovery failures; distinguish skipped, unverified and credential-dependent checks from success. Preserve per-run diagnostic logs without exposing secrets.
- **FR-008**: Resolve Ollama readiness from configured endpoint/model; distinguish local CLI integrations from a remote AI provider.
- **FR-009**: Preserve dotenv import, USER/persona/testbed files, custom launchers and existing approval controls. Native registration must not broaden write permissions.
- **FR-010**: Record supported platform/runtime versions and tests, plus explicit live/host boundaries. A release bump follows completed implementation, not this specification.

## Scope and boundaries

Reported components: `pyats netbox servicenow nvd-cve subnet-calc wikipedia markmap drawio-rfc packet-buddy nmap gtrace tts`; CML is the registered comparison case.

Nick's PR #287 is already merged: host/component preflight, Go prerequisites, Python bounds and Zabbix cwd repair are retained and regression-tested. Spec 133 and related changes already address REPO_ROOT coupling, shared installer dependency targets and native registration merging/binding. Dotenv preservation is spec 146.

The full log archive mentioned in the pasted conversation was not supplied. Six of the eight failed macOS components are not identified here. Exact original OpenClaw/npm versions and CML spawn diagnostics remain incomplete. No allegation of a general OpenClaw MCP defect is treated as proven.

## Success criteria

- Every report has a recorded current disposition; every remaining fix has a failing baseline reproduction and passing regression.
- All twelve reported access paths are accounted for; required selected paths cannot be silently omitted.
- Supported native stdio and explicit Streamable HTTP fixture discovery succeeds through the tested runtime; failed/empty discovery cannot look ready.
- macOS arm64 and Linux fixture coverage plus applicable real-host evidence are recorded honestly.
- Relevant installer/unit/declaration checks pass without weakening assertions or changing real operator credentials.
