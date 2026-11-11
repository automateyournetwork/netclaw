# Verification

No credentials are recorded here.

## Tests

- `tests/n2n/test_member_spec_184.py`: 138 tests, all passing on 2026-11-10 on top of upstream
  e21d867c (spec 182 HA merged), with the installed OpenClaw 2026.10.9 found through `npm root -g`
  or `NETCLAW_TEST_OPENCLAW_DIST`; the OpenClaw-backed tests skip when it is absent.
  Fixture Borders are built with spec 183's `install_config` (every catalog
  component through `scripts/install-mcp-config.py`), plus an operator-registered `pfsense-mcp`.
  - Format: the example spec validates; each error is raised with its message (non-object,
    unknown keys, each missing required key, version 2/"1"/true, unsafe/empty/long/non-string and
    reserved names, non-string description, servers not a list, empty or duplicate server, server
    missing from the template, skills not a list, unsafe or duplicate skill, `tools` shape, empty
    or non-list allow, unknown built-in, `*`, `group:fs`, `bundle-mcp`, alias `bash`, upper-case
    `READ`, blank/padded/non-string entries, globbed server part, illegal tool characters, empty
    tool part, case-insensitive duplicates, non-Anthropic/empty/non-string model); every problem in
    one spec is reported at once; unreadable and invalid JSON files; servers OpenClaw would rename
    (dotted, over 30 characters) are refused.
  - Allowlist: patterns for `gitlab-mcp`, `netbox-mcp` and `slack-mcp` (not kept) are errors
    naming the server; `memory-mcp__*` is accepted while the Border has `memory-mcp` and refused
    when it does not. `spec_tool_policy` adds `read` only when skills are listed.
  - Skills: not installed → warning; scope follows `scope custom` (installed subset, or all when
    none is installed); no skills → empty scope.
  - OpenClaw cross-check (installed 2026.10.9): every `OPENCLAW_BUILTIN_TOOLS` id passes its
    `isKnownCoreToolId`; its `buildSafeToolName` names `pfsense-mcp`'s `get_rules`
    `pfsense-mcp__get_rules`; its glob matcher over the example allowlist allows `get_rules`,
    `list_aliases`, `prometheus-mcp__query`, `pyats_list_devices` and `read`, and refuses
    `pfsense-mcp__set_rule`, `grafana-mcp__search`, `pyats_configure_device` and `exec`.
  - Env slice (round 1): on the installed Border, `spec_env_slice_keys` equals the kept servers'
    allowed references and component env keys plus base-prefix keys; a pyats spec member's slice
    holds `PYATS_TESTBED_PATH`, `PYATS_MCP_SCRIPT`, `NETCLAW_USERNAME`/`PASSWORD`/
    `ENABLE_PASSWORD` and `NETCLAW_TESTBED_MODE`; `PYATS_UNREFERENCED`, `NETBOX_TOKEN`,
    `PCAP_UPLOAD_DIR` (packet-buddy, not kept), `SLACK_*` and `SERVICENOW_*` are absent.
    `component_env_keys` combines catalog settings and installer-access `required_env` (every
    contract component is a catalog component); a server not component-launched and an unknown
    component contribute nothing. Denied keys never appear: a spec keeping `servicenow-mcp` gets
    none of its `SERVICENOW_*` settings, and a catalog patched to declare `SLACK_BOT_TOKEN`,
    `EMAIL_PASSWORD` and `TWILIO_AUTH_TOKEN` as pyats settings still yields only
    `NETCLAW_PASSWORD`. Profile members (spec 183 gap): pyats now gets the device logins and
    `NETCLAW_TESTBED_MODE`, packet `PCAP_UPLOAD_DIR`, netbox `PYATS_TESTBED_PATH`.
  - Skills (round 1): `spec_skill_allowlist` creates `agents.entries.main` without a roster, sets
    `skills` on every keyed entry (keeping `ownership`) and every legacy `list` entry, and on
    `agents.defaults`; `[]` for none. The member home from the example writes
    `entries.main.skills = ['pyats-health-check']`; a Border with `main` and `ops` entries and a
    spec with no skills gives both `skills: []`. OpenClaw cross-check: its
    `resolveEffectiveAgentSkillFilter` + `isSessionSkillEnabled` over the generated configs
    (no roster; keyed roster whose `ops` and defaults had `memory`) admit exactly the spec's skills
    for agents `main` and `ops`, and none for `[]`.
  - Member home: `--spec` writes exactly the spec's servers plus `memory-mcp`, the tool policy
    (replacing the Border's `tools: {profile: full, allow: ['*']}`), no channels, the spec model
    registered and allow-listed, no Border `.env` or runtime root; `--member` must equal the spec
    name; default home `~/.openclaw-lab-<name>`; an invalid spec writes nothing; neither `--member`
    nor `--spec` is a usage error; Hermes is refused.
  - Spec 183 protections for a spec member keeping `pyats-mcp`: no `<home>/.env` refused naming
    `pyats-mcp` and `--member-env`; the Border's `.env` directly, through `..` and through a hard
    link refused; a symlinked env file refused; `--home` at the Border's home (direct and `..`)
    refused; the Border's `openclaw.json` unchanged. With `--member-env`, netbox and pyats entries
    point at the staged file and `<member>/python-runtimes`, pyats keeps the Border's `pyats-venv`,
    the netbox record is copied 0600.
  - Migrate: `--spec --specs-only` (staging `stage` and `st age$x`, spec path with a space) stages
    only the spec member, `.env` 0600 with `PFSENSE_*`, `MEMORY_DATA_DIR`, `GAIT_DIR`, not
    `PYATS_TESTBED_PATH` (unreferenced, see spec.md), Slack, ServiceNow or NetBox; the spec model;
    scope ending in the spec skill; the printed command names `--spec <path>` and ends
    `--member-env <staged>`, is in the runbook, and provisions the home when run; the runbook's add
    body is `custom` with the scope. Invalid, duplicate and profile-colliding specs and
    `--specs-only` alone are refused before staging; Hermes is refused.
  - `in2n-profiles.py spec` prints kept servers and the policy, exits 1 naming the bad server.
    `netclaw risk add spec` (functions extracted from `scripts/netclaw`, `api_post` stubbed)
    posts `{"name", "profile": "custom", "specialty"}`, prints the token and the migrate command,
    and never calls the daemon for an invalid spec.
- With `tests/n2n/test_member_mcp_mappings_183.py` (50, unchanged): 133 passed with OpenClaw set;
  131 passed and 2 skipped without.
- Full `tests/n2n`: 7 failed, 1595 passed, 7 skipped, 158 collection errors. An export of commit
  c00a62ca (before spec 184) run the same way: 7 failed, 1514 passed, 5 skipped, 158 errors; the
  failing and erroring test ids are identical (MCP SDK runtime tests and a `lib` import
  collision).

## Review round 1 (second commit set, final)

- `tests/n2n/test_member_spec_184.py`: 116 tests; 111 passed and 5 skipped without OpenClaw on
  `npm root -g`; 116 passed with `NETCLAW_TEST_OPENCLAW_DIST` (and nvm Node 24 on `PATH`) set to
  the installed OpenClaw 2026.10.9. With the 182 file: 166 passed with OpenClaw set; 161 passed,
  5 skipped without.
  - Dangerous built-ins: each of write, exec, edit, apply_patch, process, gateway, secrets,
    openclaw, plugins, code_execution, terminal, computer, sessions_spawn, subagents,
    skill_workshop, message, conversations_send is refused without `--allow-dangerous-tools` and
    accepted, with a warning, with it. Installed-OpenClaw check: `group:runtime`,
    `group:automation`, `group:nodes`, `group:messaging`, the fs writers and the core ids of the
    sandbox `DEFAULT_TOOL_DENY` are all in `DANGEROUS_BUILTINS`, which holds only core tool ids.
    Migrate refuses a dangerous spec without the flag; with it the printed member-home command
    carries `--allow-dangerous-tools`, runs, and records `dangerous_tools_allowed: ["exec"]`; a
    safe spec's command never carries it. `--allow-dangerous-tools` without `--spec` is a usage
    error. `netclaw risk add spec` refuses before the daemon without the flag, carries it with it,
    and rejects any other extra argument.
  - Border-only: n2n-mcp, protocol-mcp, hermes-hud-mcp, netconverter-mcp, convergence-read-mcp
    refused in a spec; no Border-only component in `COMPONENT_ENV_KEYS`; a component-launched
    alias of `protocol` contributes nothing; every profile (Convergence excepted, its own path)
    keeping every Border-only server with `${BGP_DAEMON_API}`, `${NETCLAW_BGP_PEERS}`,
    `${N2N_REGISTRY_TOKEN}`, `${NETCLAW_HERMES_HUD_API_KEY}`, `${NETCONVERTER_API_KEY}` gets only
    the base `GAIT_DIR`.
  - Own workspace: a Border with a private file, a skill containing a symlink to it, agent
    `agentDir` and `tools {alsoAllow: [exec], profile: full, allow: [*]}`, `extraDirs` and Workshop
    `auto`: the member workspace is a directory holding only `skills/` with the spec skill and the
    three base skills, the symlink is not copied, every agent points at it, agent `tools` and
    `agentDir` are gone, `extraDirs` dropped, Workshop `off`. A profile member's workspace is still
    the Border symlink with no spec record.
  - Hardened Border (`tools.sandbox.tools.alsoAllow: [bundle-mcp]`, `agents.defaults.sandbox.mode:
    all`, agent sandbox allow `*`): OpenClaw's `resolveSandboxToolPolicyForAgent` +
    `isToolAllowed` on the member config admit `pfsense-mcp__get_rules`, `prometheus-mcp__query`,
    `memory-mcp__memory_recall`, `gait-mcp__gait_log`, `read` and refuse `pfsense-mcp__set_rule`,
    `exec`, `write`, `sessions_spawn`.
  - `openclaw config validate` on that member home: exit 0 ("Config valid"); the same home with
    Workshop mode `bogus`: exit 1.
  - Names: every `reserved_member_names()` entry (all profile ids and convergence/custom/spec) is
    refused; migrate refuses a spec named `pyats`.
  - `netclaw risk add spec`: printed staging command has `--staging <root>/migration-staging/<risk>`,
    the join endpoint, or `127.0.0.1:11790` for the daemon's `<border-host:port>` placeholder, and
    `--hot ""`.
- Full `tests/n2n` (fastmcp4 runtime, `--continue-on-collection-errors`): this branch 8 failed,
  1624 passed, 10 skipped, 158 errors; an export of `origin/main` (2b2f8e2b) run the same way:
  8 failed, 1463 passed, 5 skipped, 158 errors. The failing and erroring test ids are identical:
  the 8 failures are `test_mobile_enrollment_175.py` (`qrcode` not installed in this runtime); the
  errors are collection errors of 9 modules (missing `service_identity`/`qrcode`) and setup errors
  of the protected-runtime tests (`test_protected_selection_172`, `_revision_bindings`,
  `_ollama_selection_176`, `_orchestration_171`: `RuntimeRefused: unsafe_pinned_source` on this
  host's checkout).

## Review round 3 (rebased onto upstream e21d867c, 2026-11-10)

Reviewer: Grok (read-only), after the Claude agents reached their usage limit; fixes by the
coordinator. Round-2 items 1-4 confirmed fixed; `require_standalone_home` (upstream HA) runs
before every member-home write. Round-3 fixes and tests:
- literal secrets in kept server entries or the guard plugin are refused, naming server and key
  only (`test_literal_secrets_finds_paths_never_values`,
  `test_spec_member_refuses_a_literal_secret_in_a_kept_server`);
- `copy_skill` does not enter a symlinked skill or subdirectory
  (`test_copy_skill_does_not_enter_a_symlinked_skill_or_subdirectory`);
- a second read-only Grok pass confirmed the fixes and listed residual shapes; defaults with
  literals, more secret names, URL passwords and `_FILE`/`_TTL`-style names are now handled
  (`test_literal_secrets_round3_residuals`), the shipped template stays clean
  (`test_literal_secrets_flags_nothing_in_the_shipped_template`);
- docs now state that kept servers keep their own data stores (allowlist-limited) and that
  `GAIT_VENV`/`GAIT_MCP_SCRIPT` come from the Border.

## Integration finding (Convergence investigator)

Validating Convergence's investigator spec against a real Border showed `alert-triage`, which
Convergence installs into the Border's workspace, reported as not installed and left out of the
routing scope: `_installed_skills()` returns the first skills directory that exists (the
repository's), while in2n-member-home.py copies from the Border's workspace too. A member spec's
installed set is now the union of the repository's and the selected runtime's skills
(`_all_installed_skills`; `test_skills_installed_only_on_the_border_count_as_installed`).

A spec with `model: null` staged `N2N_MEMBER_MODEL=anthropic/claude-sonnet-5` (the profile
placeholder) while in2n-member-home.py configured and allowed only the member tier, so the
member's `--model` override would be rejected. in2n-migrate.py now stages the model the member
home configures (`test_null_model_stages_the_model_the_member_home_configures`).

Results on top of e21d867c: `test_member_spec_184.py` 146 passed, `test_member_mcp_mappings_183.py`
50 passed (installed OpenClaw 2026.10.9). Full `tests/n2n` (fastmcp4 runtime): main 32 failed,
1975 passed, 16 skipped, 179 errors; this branch the identical failing/erroring ids and 2163+
passed. The failures and errors come from modules not installed on this host (for example
`service_identity`, `qrcode`) and protected-runtime setup refusals, the same on main.

## Checks

- `python3 scripts/verify-spec-artifacts.py`: exit 0.
- `git diff --check`: clean.
- `scripts/check-catalog-metadata.py`: PASS after refreshing the `n2n-federation` skill hash in
  `config/components/catalog.json`. `scripts/build-catalog.py` cannot run on this host
  (`setup_state.Conflict: unsafe_parent`, group-writable checkout, as spec 183 recorded), so
  `scripts/lib/catalog.sh` was regenerated with its `render()`: `render()` of the HEAD catalog
  reproduces the committed file byte for byte, and the new file differs only in the
  `# Catalog SHA-256` line (as commit 1f9d5bcc did).
- `python3 scripts/reconcile-mcp.py`: catalog, dependencies, docs, meraki-ids, packages and
  portability pass; startup fails for missing host Python modules, as on spec 183. No server is
  registered by this change.
- `openclaw config validate` (2026.10.9, scratch `HOME`/`OPENCLAW_STATE_DIR`) on a spec member home:
  "Config valid", warnings only for unset fixture variables. Round 1, with the skill allowlist,
  on homes from a Border without a roster and from a Border with keyed `main`/`ops` entries
  (shape from `openclaw doctor --fix`), each with one skill and with none: all four "Config
  valid". `openclaw skills list --agent main --json` on a Border workspace holding
  `pyats-health-check`, `memory` and `subnet-calculator`: with `["pyats-health-check"]`,
  `memory` and `subnet-calculator` are `blockedByAgentFilter` and `pyats-health-check` is not;
  with `[]`, all three are. A legacy `agents.list` roster fails 2026.10.9 validation on the
  Border itself ("moved to keyed agents.entries"), independent of this change.

## Attempts (bounded loop, budget 10)

1. Implementation and tests: 64 passed, 4 failed. A list source crashed `Path()` (loader now treats
   any non-path as data); the duplicate test used `READ`, which is not a built-in (tests now cover
   both); the migrate test expected `PYATS_TESTBED_PATH` in a spec slice, which the specified slice
   does not derive (recorded as known behaviour, test asserts absence).
2. 70 passed, 1 skipped (OpenClaw not on `npm root -g`); added `NETCLAW_TEST_OPENCLAW_DIST`; the
   cross-check passed against the installed copy. Catalog skill hash refreshed.
3. Review: migrate ignored `--spec` on a Hermes runtime; now refused, with a test.
4. Coordinator review round 1: component env keys in every slice (spec 183 profile gap fixed) and
   the per-agent skill allowlist. First run: 2 failures, the migrate test still asserting the old
   absence of `PYATS_TESTBED_PATH`; updated. A first `openclaw config validate` attempt used a
   legacy `agents.list` fixture, which 2026.10.9 rejects on the Border too; the fixture now uses the
   doctor-repaired keyed shape. Final runs above.
5. Review round 1, second set (WIP 5e079ff7, stopped at a usage limit): dangerous built-ins,
   Border-only servers, own workspace, narrowed sandbox, base skills, stripped agent policies,
   reserved names, staging command. Kept as committed; 156 passed, 2 skipped on resume.
6. Completion: the opt-in reaches staging (`in2n-migrate.py`, `risk add spec`), the endpoint
   placeholder, and installed-OpenClaw tests. Two new tests first failed on fixtures (no member
   `.env` for component-launched servers, as the 182 protection requires); fixed in the tests.
   Final runs above.

## Not verified

A live member provisioned from a spec, enrolled and routed to; that OpenClaw's runtime refuses a
non-allowed MCP tool call (only the installed matcher and schema were exercised); macOS.
