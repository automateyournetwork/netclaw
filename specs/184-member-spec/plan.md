# Plan

- Read the installed OpenClaw for MCP tool naming, allowlist matching, policy layering, the core
  tool ids and how skills are loaded; read how the Convergence member and spec 177 express tool
  policy (research.md).
- `scripts/in2n-profiles.py`: `load_member_spec` (strict validation, every error at once,
  `MemberSpecError`), `OPENCLAW_BUILTIN_TOOLS`, `spec_member_servers`, `spec_env_slice_keys`,
  `spec_tool_policy`, `border_template_servers`, and a `spec` subcommand. `member_servers` and
  `env_slice_keys` share `_kept` and `_slice` with the spec functions (no copy of the deny
  logic). `scope()` takes an optional `installed` list.
- `scripts/in2n-member-home.py`: `--spec`; `--member` optional (defaults to and must equal the
  spec name). The generic OpenClaw body moves into `_provision_openclaw(args, runtime, name,
  spec=None)`, used by both paths, so the spec-183 protections run unchanged.
  `scoped_mcp_servers(..., spec=)` and `member_home_command(..., spec=)`.
- `scripts/in2n-migrate.py`: `--spec` (repeatable) and `--specs-only`; `_load_specs` validates
  before anything is staged; the generic staging body becomes `_stage_member`, used by profile and
  spec members; runbook add bodies via `_add_body` (spec: `custom` + scope).
- `scripts/netclaw`: `risk add spec <file>` (`risk_add_spec`).
- Docs: docs/N2N-RISK.md "Member spec" section and table row; `n2n-federation` skill pointer.
- Tests: `tests/n2n/test_member_spec_184.py`, using spec 183's installed-config fixture Borders.
- Review round 1: `in2n-profiles.py` gains `launched_component`, `COMPONENT_ENV_KEYS` (catalog
  settings + installer-access contract) and `component_env_keys`, used by the shared `_slice`, so
  profile and spec slices both carry a component-launched server's settings; `in2n-member-home.py`
  delegates `_launched_component` to it and gains `spec_skill_allowlist`, applied with the tool
  policy.

## Review round 1 (second commit set)

- `in2n-profiles.py`: `DANGEROUS_TOOL_GROUPS`/`DANGEROUS_BUILTINS` and the `allow_dangerous`
  argument of `load_member_spec`; `BORDER_ONLY_COMPONENTS`/`BORDER_ONLY_SERVERS` derived from
  `config/installer-access.json` (`access: hud-private`), `config/components/comms.json` and the
  federation/control set, used by spec validation, `COMPONENT_ENV_KEYS` and the shared `_slice`;
  `reserved_member_names()` (every profile id); `SPEC_BASE_SKILLS` and `spec_skills`.
- `in2n-member-home.py`: `spec_tools_section` (narrowed sandbox), `spec_skills_section`
  (Workshop off, no extra dirs), `spec_skill_allowlist(..., workspace=)` (strips agent `tools`
  and `agentDir`), `skill_sources`/`copy_skill` (own workspace, regular files only), the
  `netclaw-member-spec.json` record, `--allow-dangerous-tools` (spec only),
  `member_home_command(..., allow_dangerous=)`.
- `in2n-migrate.py`: `--allow-dangerous-tools` into `_load_specs` and the printed command.
- `scripts/netclaw`: `risk add spec <file> [--allow-dangerous-tools]`; printed staging command
  with `--staging`, a real `--border-endpoint` and `--hot ""`.
- Review round 2: `spec_member_config` (`SPEC_MEMBER_TOP_KEYS`), `spec_sandbox`,
  `spec_store_overrides`, a built `spec_skills_section`, `copy_skill` with `O_NOFOLLOW` + `fstat`
  in `in2n-member-home.py`; `SAFE_BUILTINS`, `SPEC_MEMBER_STORE_KEYS` and
  `SPEC_MEMBER_PROVIDER_KEYS` in `in2n-profiles.py`. Profile members unchanged, documented.
- Tests against the installed OpenClaw where it decides: its tool groups and sandbox default deny
  (dangerous set), `resolveSandboxToolPolicyForAgent`/`isToolAllowed` (hardened member),
  `openclaw config validate` (member home, and a negative control).
