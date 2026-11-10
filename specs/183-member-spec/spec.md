# Spec 183: Provision an iN2N member from a member spec file

Created 2026-11-08; branch `183-member-spec`, stacked on `182-member-mcp-mappings`, on 1.19.1;
status: implementation and verification.

## Problem

A generic member's MCP servers come only from the hard-coded `MCP_SERVERS` table
(`scripts/in2n-profiles.py`), its skills from `PROFILE_MATCHERS` (or `scope custom a,b,c`), and it
gets no tool allowlist: every tool of every kept server. An operator who wants a narrowly scoped
member, for example a read-only investigator that may call only `pfsense-mcp__get_*`,
`pfsense-mcp__list_*` and `prometheus-mcp__*`, has to patch NetClaw. Convergence needs exactly
that for its alert investigator and must not put Convergence-specific code into NetClaw. A
declarative member spec is the generic fix.

## Requirements

- FR-001: A member spec is a versioned JSON object: `version` (1), `name`, `servers`, `tools`
  (required), `description`, `skills`, `model` (optional). `load_member_spec` validates it
  against the Border template's `mcp.servers` and reports every problem at once
  (`MemberSpecError`); an unknown top-level key is an error.
- FR-002: `name` is a safe local name (`[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`), not `convergence`,
  `custom` or `spec`. `servers` lists distinct servers present in the Border template; a server
  whose name OpenClaw would rewrite for tool names (not `[A-Za-z][A-Za-z0-9_-]{0,29}`) is
  refused, since no allowlist entry could name its tools.
- FR-003: `tools` is exactly `{"allow": [...]}`, non-empty. Each entry is an OpenClaw built-in
  tool id (`OPENCLAW_BUILTIN_TOOLS`, from OpenClaw 2026.10.9's core tool catalog) or
  `<server>__<tool>`, where `<server>` is a kept server (`servers` or `memory-mcp`) written
  literally and `<tool>` uses OpenClaw's tool-name characters plus `*`. Groups, `*`,
  `bundle-mcp`, aliases (`bash`), a pattern for a server not kept, and duplicates (OpenClaw
  matches case-insensitively) are errors.
- FR-004: `skills` lists distinct safe skill names. A skill not installed is a warning; the
  member's scope is what the existing `scope custom` path yields for the list (`scope()` gained
  an `installed` argument so validation and scope read the same listing).
- FR-005: `model` is `null` or an Anthropic model id, optionally `anthropic/<id>`; the generic
  member path registers only the Anthropic provider.
- FR-006: `in2n-member-home.py --spec PATH` provisions an OpenClaw member like a profile member,
  except: kept servers = `spec.servers` + `memory-mcp`; model = `--model`, else `spec.model`,
  else the default tier; the member home's top-level `tools` section is `spec_tool_policy(spec)`.
  `--member` defaults to `spec.name` and must equal it if given. Every spec-182 protection
  applies unchanged: the member env file check, the Border `.env` and home refusals, runtime path
  rewriting and record copying. An invalid spec writes nothing. Hermes is refused.
- FR-007: `spec_tool_policy` is `allow` = `tools.allow`, plus `read` when the spec lists skills
  (OpenClaw's prompt tells the agent to read a matching skill's SKILL.md), with
  `fs.workspaceOnly: true`, `elevated.enabled: false` and `toolSearch: false`, the native policy
  shape the Convergence member uses (`native_tool_policy`). It replaces the Border's top-level
  `tools`; OpenClaw applies global and agent policies in turn, so copied agent entries can only
  narrow it.
- FR-008: A spec member's env slice (`spec_env_slice_keys`) is every variable its kept servers
  reference as `${NAME}` or, for a component-launched server, its component's env keys (FR-012),
  with the spec-182 deny lists unchanged, plus `BASE_MEMBER_ENV_PREFIXES`; no profile prefixes.
- FR-009: `in2n-migrate.py --spec PATH` (repeatable) stages each spec member like a profile
  member (0600 `.env` slice, `run.sh`, runbook entries) and prints and writes the exact
  `in2n-member-home.py --spec PATH --member-env <staged .env>` command. `--specs-only` stages only
  spec members. A spec that fails validation, a duplicate spec name, or a name an offered profile
  member already uses stops migrate before anything is staged. The runbook registers a spec member
  as `profile: custom` with `specialty` = its scope.
- FR-010: `netclaw risk add spec PATH` validates the spec (`in2n-profiles.py spec`) against the
  selected Border template, then asks the daemon for a custom member whose specialty is the
  spec's scope, and prints the token and the staging command. An invalid spec never reaches the
  daemon. No daemon change.
- FR-011: `in2n-profiles.py spec PATH [--border-config X]` prints the validated spec, its kept
  servers and tool policy, warnings on stderr; exit 1 with the errors otherwise.

- FR-012 (review round 1): A server whose entry starts `scripts/component-launch.py <component>`
  reads settings from its env file that its entry never names as `${…}`. Its component's env keys
  (`component_env_keys`: `config/components/catalog.json` `components[].settings[].key`, plus
  `config/installer-access.json` `required_env`, `script_env`, `command_env`, the keys
  `component-launch.py` itself reads) join the slice, through `derived_ref_allowed`, so the
  ServiceNow and comms deny lists hold. This applies to profile members too (`_slice` is shared):
  spec 182's slices had the same gap, e.g. the pyats profile lacked the `NETCLAW_USERNAME`,
  `NETCLAW_PASSWORD` and `NETCLAW_ENABLE_PASSWORD` device logins and `NETCLAW_TESTBED_MODE`
  (`PYATS_` covers only `PYATS_*`), packet lacked `PCAP_UPLOAD_DIR`, netbox lacked
  `PYATS_TESTBED_PATH`.
- FR-013 (review round 1): A spec member loads only the spec's skills: `spec_skill_allowlist`
  sets `skills` = `spec.skills` on every agent entry of the member home (`agents.entries` or the
  legacy `agents.list`) and on `agents.defaults`; with no roster it creates
  `agents.entries.main`. An empty list is written as `skills: []`. OpenClaw's
  `resolveEffectiveAgentSkillFilter` takes an agent's own `skills` when present, else the
  defaults, so the member's agent (default, `main`, or `N2N_MEMBER_AGENT`) is covered.

## Review hardening contract (supersedes the earlier FR-002/006/007/013 details)

- All profile ids and reserved command names are refused regardless of offered profiles.
- Dangerous built-ins (`DANGEROUS_BUILTINS`: OpenClaw 2026.10.9's `group:runtime`,
  `group:automation`, `group:nodes`, `group:messaging`, the `group:fs` writers, the core tools
  its sandbox denies by default, and the session/agent/publishing tools) require explicit
  `--allow-dangerous-tools`. Every entry point accepts it (`in2n-profiles.py spec`,
  `in2n-migrate.py`, `in2n-member-home.py`, `netclaw risk add spec`); the printed staging and
  member-home commands carry it only for a spec that needs it. With it a warning is printed and
  the choice is recorded in the member home's private `netclaw-member-spec.json`. Without
  `--spec` the flag is a usage error.
- Border-only servers, including aliases launched through Border-only components,
  are refused. HUD-private/control component env derivation is excluded for all members.
- Spec members have an independent workspace containing regular-file copies of
  requested skills plus memory, GAIT and HumanRail escalation instructions. No Border
  files, symlinked skill content or extra skill directories are copied. Existing member
  workspaces are preserved and reprovisioning is refused. Profile behavior is unchanged.
- All agents and defaults receive the member workspace and skill list; inherited agent
  tools and agentDir are removed. Workshop autonomous mode is off.
- The sandbox tool policy is retained with its tool list replaced by the exact member
  allowlist. Base grants are read for instructions and registered memory/GAIT server
  tools for those skills. HumanRail gets no implicit exec/external-dispatch grant;
  n2n-member-runtime/self-status/heartbeat/audit remain daemon capabilities.
- CLI staging instructions carry staging directory, Border endpoint and explicit hot
  selection; the empty selection keeps an on-demand custom member cold. The daemon's
  `<border-host:port>` placeholder (a risk with no recorded endpoint) is replaced by the
  loopback default `127.0.0.1:11790`, as `in2n-migrate.py` uses.
- Base floor: `memory`, `gait-session-tracking` and `humanrail-escalation` are the file-backed
  base skills (copied, allow-listed). `n2n-member-runtime`, `self-status`,
  `member_heartbeat` and `member_report_audit` are served by the member daemon (spec 174's
  `skill_report` excludes them), so they need no SKILL.md and no agent tool.

## Review round 2 contract

- A spec member's `openclaw.json` is built from `SPEC_MEMBER_TOP_KEYS` only (`mcp`, `channels`,
  `tools`, `skills`, `models`, `agents`, `memory`, `hooks`, `cron`, `plugins`), never copied
  from the Border: no `gateway` (the member runs `openclaw agent --local`), no `env`, `auth`,
  `secrets` or any other Border section; `hooks` and `cron` `{"enabled": false}`;
  `memory.search.enabled: false`; only the Anthropic provider with `apiKey:
  "${ANTHROPIC_API_KEY}"` (resolved from the member's `.env`; the spec slice carries
  `ANTHROPIC_API_KEY`); only the DefenseClaw guard plugin
  (`controls.defenseclaw_plugin_config`, as the Convergence member); `skills.entries` reduced
  to the `enabled` flag of the member's own skills; `agents.entries` = `main` only;
  `agents.defaults.sandbox` reduced to isolation settings (no binds, docker env, setupCommand,
  extraHosts, `dangerouslyAllow*`, ssh, browser or workspaceRoot), and a non-docker sandbox
  backend is refused.
- A spec member's `memory-mcp` uses `MEMORY_DATA_DIR=<home>/memory`; its `gait-mcp` runs with
  `cwd`, `HOME` and `GAIT_MCP_STICKY_FILE` under `<home>/gait` (the Border's `GAIT_VENV`
  executable is kept, made absolute). Both directories are created 0700. The spec slice never
  carries `MEMORY_DATA_DIR`, `GAIT_DIR`, `GAIT_ROOT` or `GAIT_MCP_STICKY_FILE`.
- Built-in tools: `SAFE_BUILTINS` = `read`, `session_status`; every other OpenClaw built-in
  (`DANGEROUS_BUILTINS = OPENCLAW_BUILTIN_TOOLS - SAFE_BUILTINS`) needs
  `--allow-dangerous-tools`.
- `copy_skill` opens each source file `O_NOFOLLOW` and copies it only when `fstat` shows a
  regular file with one link.

## Known behaviour (profile members; predates spec 183, not changed here)

A profile member's `openclaw.json` is still a deep copy of the Border's, minus comms channels
and plugins: it carries the Border's `gateway` (auth token/password), `hooks` (token,
mappings), `cron`, top-level `env.vars`, non-comms plugins and their config, every
`models.providers` entry (with literal keys), `memory.search` / `agents.defaults.memorySearch`
(remote apiKey, extraPaths) and `agents.defaults.sandbox` (docker binds), and its own Anthropic
key is written literally. Its plugin filter compares `plugins.load` paths with plugin ids, so
it removes no load path. Its `memory-mcp` keeps the Border template's `MEMORY_DATA_DIR` (the
Border's memory store) and its `gait-mcp` the Border's GAIT discovery. Follow-up: give profile
members the spec member's config builder (research.md, "Follow-up").

## Out of scope

Hermes members, providers other than Anthropic for generic members, a daemon-side spec store,
and skill filters for profile members.
