# Research

Sources are the installed OpenClaw 2026.10.9 (`npm` global under nvm Node 24.22.1,
`.../lib/node_modules/openclaw/dist`) and this branch. File names in `dist/` carry build hashes;
the first 16 hex digits of each file's sha256 are given so the evidence can be matched.

## How OpenClaw names MCP tools

`dist/agent-bundle-mcp-names-CFVETBL6.mjs` (f5a5c361a4a32999), `buildSafeToolName`:
`${serverName}__${toolName}`, where `serverName` is `sanitizeServerName(raw)`: characters outside
`[A-Za-z0-9_-]` become `-`, a name not starting with a letter is prefixed `mcp-`, and it is cut to
30 characters (`TOOL_NAME_MAX_PREFIX`), with `-2`, `-3` suffixes on collisions. Total length is
capped at 64. `dist/agent-bundle-mcp-materialize-BZFLfYd6.mjs` logs a warning when a tool is
registered under a different name. So an allowlist entry for server `s` and tool `t` is `s__t`
only when `s` is already safe; a spec refuses servers whose names would be rewritten.

## How allowlists match

- `dist/tool-policy-shared-CNWjndK7.mjs` (ff73e84552ab1267), `normalizeToolPolicyName`:
  lowercase, then aliases `bash`→`exec`, `apply-patch`→`apply_patch`, `cron`→`automations`.
- `dist/glob-pattern-DuaaJ-nB.mjs` (0ca68c82264181da), `compileGlobPattern`: `*` alone is
  "all", an entry without `*` is exact, otherwise `*` becomes `.*` in an anchored regex. `*` is
  the only wildcard.
- `dist/tool-policy-pipeline-4Av_cTF8.mjs` (680a5ee13935a014), `buildDefaultToolPolicyPipelineSteps`
  and `applyToolPolicyPipeline`: the profile, provider profile, `tools.allow` (global),
  `tools.byProvider`, `agents.<id>.tools.allow`, group and sender policies filter the tool list
  one after another. Global and agent allowlists therefore intersect: an agent entry copied from
  the Border can narrow the member's policy, never widen it.
- `dist/agent-tools.policy-B-XJsXps.mjs`, `resolveEffectiveToolPolicy`: `globalPolicy` is
  `config.tools`; the agent policy comes from `agents.entries.<id>.tools` / `agents.list[i].tools`
  (or `agents.defaults.tools` without a roster).
- `dist/tool-policy-BrMCyUgN.mjs`, `analyzeAllowlistByToolType`: entries that match no core,
  plugin or declared MCP prefix (`<safe server>__`) only produce a warning ("allowlist contains
  unknown entries"); nothing is stripped. `bundle-mcp` as an entry allows every MCP tool, which
  is why the spec refuses it.

## Built-in tool ids

`dist/tool-catalog-DfaCehx8.mjs` (c822c8d06f35f4ba): `CORE_TOOL_DEFINITIONS` and
`CORE_TOOL_GROUPS` give 66 ids (`read`, `write`, `edit`, `exec`, `session_status`, …); every id
in `OPENCLAW_BUILTIN_TOOLS` passes the module's `isKnownCoreToolId`. Groups (`group:fs`, …) are
refused because they expand to several tools.

## How the operator's existing members express it

- The Convergence member: `scripts/lib/convergence_member_policy.py` `native_tool_policy()` is
  written as the member home's top-level `tools` by `provision_convergence`
  (`scripts/in2n-member-home.py`) and by `scripts/lib/setup_harness.py`:
  `allow: ['read', 'convergence-read-mcp__convergence_flow_summary', …]`, `deny`, `fs.workspaceOnly`,
  `elevated.enabled: false`, `toolSearch: false`. Spec 164's verification records the member
  running live under that policy, and the Border's `border-fed` agent denying both Convergence
  tools through the same matcher.
- Spec 177 validated per-agent policies (`agents` entries with their own `tools`) against the
  installed schema and native policy functions.
- A member's turn runs agent `main` (`N2N_MEMBER_AGENT`, docs/N2N-RISK.md), so the top-level
  `tools` section, which applies to every agent, is the right place. A spec member uses it.

## Skills and the `read` addition

`dist/system-prompt-CIvDrwqR.mjs`, `buildSkillsSection`: with listed skills the prompt says
"Scan <available_skills> for a matching workflow" and, unless the `skills_read` path is active,
"Clear match: read exact <location>", that is, the agent reads the skill's SKILL.md with `read`.
A member whose allowlist lacks `read` cannot follow its skills, so `spec_tool_policy` adds `read`
when the spec lists skills, and only then. Heartbeat and audit (`member_heartbeat`,
`member_report_audit`) are daemon protocol methods handled by `scripts/in2n-member.py`, not agent
tools, so the member runtime needs no other tool.

`deny` is not copied from the Convergence policy: it would override an operator's explicit
`exec` or `write`, and the allowlist already excludes everything else.

## Adding a member today

`netclaw risk add <profile|custom> <name> [skills]` (`scripts/netclaw` `risk_add`) posts to the
daemon's `/n2n/members/add` (`bgp-daemon-v2.py`), which resolves a profile's skills through
`in2n-profiles.py` or takes `specialty` for `custom`, then `RiskManager.add_member` stores the
scope and issues a single-use token. `in2n-migrate.py` stages `.env` slices and `run.sh`, and its
runbook posts the same endpoint. A spec member uses `profile: custom` with `specialty` = the
spec's scope, so no daemon change is needed.

## The slice and component-launched servers (review round 1)

Installed component-launched entries (`scripts/component-launch.py <component>`) carry no
`${…}` for the settings the component reads from `NETCLAW_RUNTIME_ENV`; `component-launch.py`
`environment()` loads every key of that file. The installer knows a component's keys from two
places: `config/components/catalog.json` `components[].settings` (what setup collects or
generates; for pyats `PYATS_TESTBED_PATH`, `PYATS_MCP_SCRIPT`, `PYATS_VENV`, the
`NETCLAW_USERNAME`/`NETCLAW_PASSWORD`/`NETCLAW_ENABLE_PASSWORD` device logins its testbeds
reference with `%ENV{}`, and the testbed mode settings) and `config/installer-access.json`
(`required_env`, `script_env`, `command_env`, read by `component-launch.py` `resolve`). Every
installer-access component is a catalog component. `component_env_keys` takes the union.

Spec 183's profile slices had the same gap wherever a component setting matches no profile
prefix: pyats (device logins, `NETCLAW_TESTBED_MODE`/`NETCLAW_TESTBED_SOURCES`), packet
(`PCAP_UPLOAD_DIR`), netbox (`PYATS_TESTBED_PATH`). The fix is in the shared `_slice`. The
servicenow component's settings are all `SERVICENOW_*` and stay denied.

## Skills (review round 1)

- `dist/agent-filter-Cde7DN_E.mjs` (e070f70c200f579e), `resolveEffectiveAgentSkillFilter(cfg,
  agentId)`: an agent entry with its own `skills` key wins, else `agents.defaults.skills`, else
  no filter. `isSessionSkillEnabled` admits a skill when the filter is unset or includes it, so
  `[]` admits none.
- `dist/workspace-skill-loader-B2ho4lmV.mjs` `filterSkillEntries` applies it through
  `isSkillEntrySelected` (`config-*.mjs`), which matches `entry.skill.name` (the SKILL.md
  `name`) and always admits Workshop-sourced skills. Every repository skill's frontmatter
  `name` equals its directory name.
- `agent-scope-config` `resolveAgentEntry` reads keyed `agents.entries` or the legacy
  `agents.list`. OpenClaw 2026.10.9's validator rejects `agents.list` ("moved to keyed
  agents.entries") and legacy `default: true` markers in entries; `openclaw doctor --fix`
  rewrites them to `agents.entries` plus `agents.ownership: "explicit"` and
  `defaults.systemAgent`/`heartbeat`. A member home keeps whatever roster the Border has and
  adds `skills` to each entry; `pal-prepare-agent.py` already writes a per-agent `skills: []`.
- `gateway.py` `_member_agent_args`: the member's turn runs the default agent, `main` when the
  home has several agents, or `N2N_MEMBER_AGENT`. Setting every entry and the defaults covers
  each case.

## Review round 2: what a member runtime needs from its config

- `gateway.py` runs a member turn as `openclaw agent --local [--agent main] [--model M]
  --session-id ... --json` (`_member_agent_args`, line ~447): an embedded turn, no gateway
  process, so no `gateway` section (auth token/password, bind, remote) is needed; without
  `gateway.mode` OpenClaw does not start a gateway from the member home. `_member_agent_args`
  reads only `agents.entries`/`agents.list` ids: with `main` alone it passes no `--agent`.
- `in2n-member.py` clears its environment and loads only `N2N_MEMBER_ENV_FILE`; `_agent_env`
  passes that environment to `openclaw`, so `${ANTHROPIC_API_KEY}` in `models.providers`
  resolves from the member's own `.env`. The Convergence member (`provision_convergence`, spec
  165/167) is the qualified precedent: `mcp`, `channels: {}`, `tools`, one provider with
  `${VAR}` references, `agents.defaults` (workspace, model), and only the DefenseClaw plugin
  (`controls.defenseclaw_plugin_config`); no gateway, hooks, cron or env.
- OpenClaw 2026.10.9 schema (`schema-CMLO0qbi.mjs`): `hooks.enabled` ("Keep disabled unless you
  are actively routing external events"), `cron.enabled` ("disable ... to pause all automation
  execution"); memory search is top-level `memory.search` (`enabled`, `extraPaths`,
  `remote.apiKey`, ...). `agents.defaults.memorySearch` is rejected by `openclaw config
  validate` ("agents.defaults: Unrecognized key: memorySearch"), so the member sets
  `memory.search.enabled: false`.
- Sandbox (`zod-schema.agent-runtime-B8-yzGte.mjs`, `AgentSandboxSchema`): mode, backend,
  workspaceAccess, sessionToolsVisibility, scope, workspaceRoot, docker, ssh, browser, prune;
  `SandboxDockerSchema` has `binds`, `env`, `setupCommand`, `extraHosts` and three
  `dangerouslyAllow*` switches besides resource/isolation settings; `SandboxSshSchema` holds
  identity/certificate/known-hosts data; `SandboxBrowserSchema` has its own `binds`.
- Stores. `memory_mcp_server.py`: `DATA_DIR = MEMORY_DATA_DIR or ~/.openclaw/memory`; the
  installed entry sets `MEMORY_DATA_DIR: ~/.openclaw/memory`, which a member running as the same
  user resolves to the Border's store. GAIT (`gait_mcp.py` `_try_repo`): explicit path, else the
  sticky root (`GAIT_MCP_STICKY_FILE`, default `~/.gait_mcp_root`), else cwd (the installed entry
  sets the repository root), else `HOME`. A spec member's `gait-mcp` gets all three under
  `<home>/gait`. Residual: a GAIT tool call naming an explicit `path` still reaches it (GAIT's
  own argument; `tools.fs.workspaceOnly` does not cover MCP tools).
- Safe built-ins. `tools.fs.workspaceOnly` is documented for read/write/edit/apply_patch, not
  `ls`; `session_status` is "Show session status/model/usage". Everything else reaches the
  network (`web_*`, `x_search`), paid APIs (media generators, `tts`), OpenClaw's memory files and
  `memory.search.extraPaths` (`memory_get`, `memory_search`, `personal_instructions`), or other
  sessions, processes, files or devices.

## Follow-up (not in spec 184)

Profile members still deep-copy the Border's config (see spec.md "Known behaviour"): gateway
auth, hooks token, cron, env.vars, every provider key, memory search remote key and extra
paths, sandbox binds, non-comms plugins, and the Border's memory/GAIT stores. Their plugin
filter (`_provision_openclaw` step 2) compares `plugins.load` entries (paths) with plugin ids
and removes nothing from `load.paths`. Moving profile members onto `spec_member_config`
(servers from `MCP_SERVERS`, no tool allowlist change) and `spec_store_overrides` would close
this; it changes the provisioned shape of every existing profile member, so it is its own spec.

## Validation of the result

`openclaw config validate` (2026.10.9, `HOME` and `OPENCLAW_STATE_DIR` in a scratch directory)
on a spec member home built by `in2n-member-home.py --spec`: "Config valid", with only
missing-env-var warnings for the fixture servers.

## Review round 1 (second commit set)

All from the installed OpenClaw 2026.10.9 (`~/.nvm/versions/node/v24.22.1/lib/node_modules/openclaw`).

- Dangerous built-ins. `tool-catalog-DfaCehx8.mjs` `CORE_TOOL_GROUPS`: `group:runtime` = exec,
  process, code_execution, secrets; `group:automation` = heartbeat_respond, automations, gateway,
  plugins, openclaw; `group:nodes` = nodes, computer, mobile_ui; `group:messaging` = message;
  `group:fs` = ls, read, write, edit, apply_patch; `group:sessions` includes sessions_spawn,
  sessions_send, conversations_send/turn, subagents, github_publish; `group:agents` includes
  skill_workshop. `constants-B3lt5mRy.mjs` `DEFAULT_TOOL_DENY` (sandbox) = browser, canvas,
  computer, mobile_ui, nodes, automations, gateway, then channel ids (not core tools).
  `DANGEROUS_BUILTINS` is the union of the first four groups, the fs writers, the core ids of the
  default deny, and the session/agent/publishing tools plus terminal, screen and portal. A test
  re-derives the required subset from the installed catalog.
- Sandbox layer. `tool-policy-BQO0kfjo.mjs` `resolveSandboxToolPolicyForAgent`: the agent's
  `tools.sandbox.tools` else the global one; `allow` (when set) merged with `alsoAllow`, else the
  default allow (exec, process, read, write, ..., no MCP tool); `deny` when set, else
  `DEFAULT_TOOL_DENY` minus explicitly allowed names. Patterns are globs
  (`compileGlobPatterns`), so `prometheus-mcp__*` matches. A hardened Border's
  `alsoAllow: ["bundle-mcp"]` would be lost by replacing `tools` wholesale (the default allow then
  has no MCP tool); setting `tools.sandbox.tools = {"allow": <member allowlist>}` admits exactly
  the allowlist. Agent entries' `tools.sandbox` is removed with their `tools`.
- Workshop. `schema-CMLO0qbi.mjs`: `skills.workshop.autonomous.mode` — "auto" lets agents save
  and update Workshop skills, "off" disables background learning; default "auto". The Workshop
  source also bypasses the per-agent skill filter (`isSkillEntrySelected`), so it is forced off.
- Base floor. `bgp/federation/risk.py` `BASE_FLOOR` = n2n-member-runtime, self-status (skills),
  member_heartbeat, member_report_audit (tools); `_BASE_NAMES` adds memory,
  gait-session-tracking, humanrail-escalation. Only the last three exist as
  `workspace/skills/*/SKILL.md`; spec 174's `skill_report` excludes the first two ("served by the
  member daemon, not OpenClaw", `tests/n2n/test_member_skill_status_174.py`). Their tools: the
  `memory` skill calls `memory_*` (memory-mcp), `gait-session-tracking` calls `gait_*` (gait-mcp),
  `humanrail-escalation` calls a HumanRail MCP server through `exec`/mcp-call, which is not added.
- Validation. `openclaw config validate` on a spec member home from a hardened Border with
  Workshop `auto`: "Config valid" (missing fixture env warnings only); the same home with
  `autonomous.mode: "bogus"` exits 1. Kept as a test.
