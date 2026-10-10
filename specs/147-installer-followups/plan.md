# Implementation Plan: Installer and first-use reliability

**Branch**: `147-installer-followups` | **Updated**: 2026-10-10 | **Spec**: [spec.md](spec.md)
**Status**: Concrete scope defined; production implementation pending.

## Technical context

Bash 3.2-compatible orchestration, standard-library Python helpers and the existing contract-test runner. Start from Nick's preflight and Zabbix fixes on main `b4334bf`. Keep the installer's runtime-specific OpenClaw/Hermes paths and managed component environment records.

## Delivery order

### Phase A — Runtime compatibility and bootstrap (US1–US2)

- Add one declared/versioned OpenClaw Node rule consumed by preflight and core installation. Reject unsupported major/minor/patch combinations before mutation; keep Hermes-specific requirements separate where applicable.
- Keep Python/component rules from PR #287. Explain uv as an actual selected-component prerequisite; any future interactive repair must choose compatible packages and refresh both installer and component interpreters.
- Construct the npm command from detected npm capabilities/version and the selected OpenClaw target. Narrow allow-scripts to reviewed first-party needs; prefer a user-owned prefix or existing version manager when the global prefix is not writable. Preserve existing npm settings.
- Propagate installation and executable verification failures without suggesting privilege escalation for unrelated errors.

### Phase B — Component access and launcher coverage (US3)

- Inventory the twelve reported components in one explicit access-path contract: component id, server/skill names, mode, executable, transport, expected tools, required configuration and verification.
- Add supported native registrations or an explicit supported skill path; bind Python/console launchers to successful runtime records. Resolve external checkout entry points against actual packaged code rather than guessing paths.
- Reuse pyATS's owned stdio bridge and its managed runtime; do not introduce a mandatory persistent/public HTTP service.
- Preserve custom entries, managed ownership state, credentials and persona/testbed files. Retain write approval/filter semantics when making tools natively visible.
- Update catalog/inventory/doc counts coherently when an external integration moves into native registration.

### Phase C — Readiness and first-use evidence (US4–US5)

- Produce structured per-component stages: artifacts, access path/registration, discovery, endpoint verification. Render that evidence directly; do not have the model infer readiness.
- Use bounded native-runtime discovery plus direct protocol diagnostics. Check structured errors and expected tool presence even when the probe exits 0. Separate empty legitimate servers from missing required tools.
- Keep credential-dependent or unrequested endpoint operations unverified. Validate local/remote Ollama against its configured endpoint/model without requiring a local binary for remote use.
- Add an explicit synthetic tool canary with provenance and negative cases. Live CML/pyATS canaries require configured, authorized read-only targets and remain separately recorded.
- Reproduce any remaining CML stdio failure with exact runtime/server versions and sanitized command/env/cwd differences; escalate upstream only with a minimal reproducer.

## Validation strategy

Use temporary HOME/state/config paths and fake endpoints for install orchestration. Matrix includes macOS arm64/Linux, Node support boundaries, npm pre-11.16/11.16+/12+, compatible/incompatible/explicit Python, isolated package targets, altered PATH, repeat installs, config preservation, failed/empty discovery, explicit HTTP transport and remote Ollama without local CLI.

Run affected unit tests and the installer suite, then declaration/reconciliation checks. Real-host evidence supplements fixtures; no full live catalog or arbitrary model reliability claim follows from a passing offline suite.

## Constitution and scope

Existing device/write approvals, credentials and operator files must survive. No global environment purge, blanket script-policy bypass or speculative dependency upgrade. Installer/registration/skills/docs/tests change as needed; no unrelated HUD redesign is proposed. No additional release bump for research; prepare one patch release when agreed implementation and checks are complete.
