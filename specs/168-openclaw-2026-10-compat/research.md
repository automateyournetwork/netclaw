# Research

- OpenClaw 2026.10.6 and 2026.10.9 `openclaw agent --help` both list `--agent <id>`
  ("Agent id (overrides routing bindings)"); 2026.7.1 also has it, so passing it does not
  narrow CLI support.
- The refusal is `cli_error` JSON on stdout, exit 1. Member homes built by
  `in2n-member-home.py` (OpenClaw builder) copy `agents.entries` from the Border; the
  observed Risk's Border has `main` and `alert`, so every member had both.
- `_apply_production_controls` finds `--model` by name, not by position, so adding
  `--agent` before `--model` does not change production wrapping.
- `negotiate.local_descriptor()` already probes the session flag (`--session-id` vs
  `--session-key`); no probe is needed for `--agent` given the support above.
- On 2026.10.9 `--agent main` fails ("Unknown agent id \"main\"") in a home whose only
  agent is `ops`, while the unnamed command works there, so `main` cannot be forced.
  A home with no entries accepts `--agent main` and the unnamed command alike.
- The CLI prints `{"ok": false, "error": {"type", "message"}}` for refused commands.
  Stderr can echo configuration, so only that structured message is surfaced.
- OpenClaw 2026.10.6 and 2026.10.9 log `[workspace] bootstrap file is unreadable:
  file=<workspace>/AGENTS.md reason=symlink path component not allowed` and continue.
  `core_deploy` has copied these files since the persona-preservation change but keeps
  any existing entry (`-e || -L`), so links from older installs persist.
