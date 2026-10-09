# Spec 146: Preserve filled dotenv settings during onboarding

Status: implemented and locally verified; awaiting review/publication. Scope authorized by the owner's request to investigate and fix initialization ignoring a filled `.env`. Date: 2026-10-09.

## User scenarios and acceptance

P1: An operator follows `.env.example`, fills the checkout's `.env`, and runs the installer. Supported, nonempty settings reach the selected runtime's durable environment before its onboarding wizard or daemon starts. Running from another directory does not lose them.

P1: An existing operator reruns installation or imports settings separately. Existing runtime assignments (including deliberately empty ones), unrelated settings, comments and runtime configuration are preserved. Conflicts are reported by variable name only. Repeating the import is idempotent.

P1: Dotenv is treated as data. Shell substitutions are never executed; values are never logged or placed in command arguments. Writes are atomic and private. Invalid input or an unsafe destination fails before any write or wizard launch.

P2: A user can preview and apply the same import without reinstalling components. Setup uses the same import. Documentation explains that provider credentials do not replace provider/model/gateway configuration; initialization can legitimately still be required.

## Requirements

- FR-001: Import from the checkout's `.env`, resolved independently of the caller's working directory, before onboarding and platform setup. A missing source is a successful no-op.
- FR-002: Import only declared `.env.example` variables. Report unknown names, blank values and obvious template placeholders without promoting arbitrary host controls into the runtime. Preserve literal single-line dotenv syntax; reject malformed/multiline records with a line number and no value.
- FR-003: Runtime assignments take precedence over checkout assignments. Process environment precedence remains the runtime's responsibility. Never overwrite runtime configuration or credentials during import.
- FR-004: Use the selected runtime environment; honor `OPENCLAW_STATE_DIR` and `HERMES_HOME`, retaining the installer's historical `OPENCLAW_HOME` fallback. The installer and its OpenClaw onboarding subprocess must agree on the state directory.
- FR-005: Standalone import defaults to preview and requires `--apply` to write. Reuse the existing private atomic writer; refuse symlinks/nonregular files. Invalid input cannot partially import.
- FR-006: Failed or unavailable onboarding must fail the installer instead of printing completion. Existing config skips the wizard using the selected runtime config path; a skipped wizard still imports missing environment settings.

## Assumptions and boundaries

The user's exact init command, runtime version and dotenv location are unknown (owner replied "no idea"). Reproduction establishes a repository defect, not a diagnosis of that specific host. File name is `.env` (lowercase on case-sensitive systems). Existing config presence remains the installer's established wizard-skip criterion; validating the complete upstream config schema is outside this patch.

No provider calls, real onboarding, daemon changes, credential inspection, device changes, external messages, PR publication or merge are part of local verification. Hermes import and orchestration can be tested with stubs; live Hermes credential loading is not claimed. This fixes installation, not every standalone wrapper's path handling.

## Success criteria

Dummy provider and network keys are available from an unrelated working directory after import; conflict values and all original runtime bytes remain intact; no dummy secrets appear in diagnostics; shell payloads do not execute; failed imports/wizards exit nonzero. Existing affected installer tests and repository declaration checks pass.
