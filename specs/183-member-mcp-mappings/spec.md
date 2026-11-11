# Spec 183: Members get the MCP servers their skills call

Created 2026-11-08; branch `183-member-mcp-mappings`, on 1.19.0; status: implementation and
verification. Found on an operator fork where pyATS, CML, Nautobot and GitHub members only worked
after their mappings were fixed by hand.

## Problem

`scripts/in2n-member-home.py` builds a member's OpenClaw config from the Border's and keeps only
the servers `MCP_SERVERS` (`scripts/in2n-profiles.py`) names for the member's profile, plus
`memory-mcp`. `MCP_SERVERS` was wrong for most profiles:

- Its comment called cml, pyats, catalyst-center, nso, netbox, nmap, gtrace, itential, aap and
  packet "skill-driven (no dedicated MCP server)". All of them have a registered server that
  their skills call, so those members had the skills and no tools.
- `"github": ["gitlab-mcp"]` gave the GitHub member GitLab's server.
- Twelve more profiles with registered, catalog-bound servers had no entry.
- A member's env slice came only from per-profile key prefixes, so a kept server reading a
  variable outside them started without it. The new mappings hit this (aap `EDA_*`/`REDHAT_*`,
  catalyst-center `CATALYST_CENTER_*`, terraform `TFC_*`, claroty/fortimanager `SERVICENOW_*`,
  viz's uml-mcp and aws-diagram-mcp), and existing mappings already had it (gnmi, gns3, sdwan
  `PAN_*`, splunk).
- Review round 1: `install-mcp-config.py` writes `NETCLAW_RUNTIME_ENV=<Border>/.env` and
  `NETCLAW_RUNTIME_ROOT` into every entry launched through `scripts/component-launch.py`, and
  `component-launch.py` loads every key of that file. `in2n-member-home.py` copied the entries
  unchanged, so a member keeping one of them (pyats, netbox, nvd, nmap, gtrace, packet's
  packet-buddy-mcp, viz's drawio and markmap, and subnet on the OpenClaw path before this spec)
  had a server that read the Border's whole `.env`, comms secrets included.

## Requirements

- FR-001: For every profile, `MCP_SERVERS` names the registered servers whose tools the profile's
  skills call, as bound in `config/components/catalog.json` and stated in the skills.
- FR-002: Every server `MCP_SERVERS` names is registered in `config/openclaw.json`, or is an
  operator-registered server with a named enable script (only `ipfabric-mcp`).
- FR-003: Where the evidence is unclear (asa, checkpoint, eve-ng), the mapping is unchanged and
  the reason is recorded in research.md and in the test's exception list.
- FR-004: The comment above `MCP_SERVERS` describes what the lists are and which profiles have
  no registered server.
- FR-005: A test fails when a profile's mapping drifts from the catalog's skill binding, outside
  the recorded exceptions.
- FR-006: A member home keeps exactly its mapped servers that the Border has, plus `memory-mcp`;
  the scoping is unchanged in behaviour and now a named function.
- FR-007: A member's env slice (`env_slice_keys`) holds, besides its `ENV_PREFIXES` and
  `BASE_MEMBER_ENV_PREFIXES` keys, every variable its kept servers reference as `${NAME}` (or
  `${NAME:-default}`) anywhere in their Border template entry: command, args, env, url, headers.
  `scripts/in2n-migrate.py` passes the Border template's `mcp.servers`, so a kept server
  starts with its credentials.
- FR-008: The Border-only rule holds. A server the member does not keep contributes nothing, so
  comms secrets and other integrations' credentials never reach a member through the slice
  unless one of its own kept servers references them by name, and shared credentials never do:
  derived names starting `SERVICENOW_`, `SLACK_`, `DISCORD_`, `WEBEX_`, `TWILIO_`, `TWITTER_`,
  `MSTEAMS_`, `TEAMS_` or `TELEGRAM_`, and every key `config/components/comms.json` lists, are
  never added (`DERIVED_DENY_PREFIXES`, `DERIVED_DENY_KEYS`). An operator grants one to a member
  through `ENV_PREFIXES`. claroty-mcp, fortinet-mcp and gnmi-mcp reference the shared
  ServiceNow account; without it their change gates refuse production writes (research.md), so
  leaving it out fails closed.
- FR-009: No kept server entry in a member home names the Border's runtime env file or runtime
  root. An entry that selects one (`NETCLAW_RUNTIME_ROOT`/`NETCLAW_RUNTIME_ENV`, or any
  `component-launch.py` entry) is rewritten to `<member home>/python-runtimes` and the member's
  own `.env` (`<member home>/.env`, or `--member-env`). The interpreter records those entries
  need are copied into the member's `python-runtimes/records` (opened `O_NOFOLLOW`, 0600; a
  symlinked target is refused; directory 0700). pyATS keeps the Border's `pyats-venv` executable,
  as gait keeps `GAIT_VENV`, taken from the entry's runtime root or else the Border config's
  directory. `in2n-migrate.py` writes no member server configs, only `.env` slices and launchers.
- FR-011: Fail closed on the member's env file. `in2n-member-home.py` refuses, naming the servers,
  the missing path and `--member-env`, and writes nothing, when a kept server would load an env
  file that does not exist or is not a regular file (a symlink or directory is refused), or is
  the Border's own `.env` (the selected runtime's env file or the Border config directory's
  `.env`, compared with `os.path.samefile`, so a hard link or a `..` path is caught too). It also
  refuses a member home that is the Border's home (the selected runtime home or the Border config's
  directory). `--member-env` and `--home` are written as absolute paths with `..` collapsed and
  symlinks not followed. `in2n-migrate.py`
  prints, and writes into the runbook (step 2b), the exact `in2n-member-home.py ... --member-env
  <staging>/members/<member>/.env` command for each staged member.
- FR-010: `in2n-migrate.py` warns, naming the config path and the offered members' mapped
  servers, when the Border config is missing, unreadable, invalid JSON or has no `mcp.servers`;
  the slices then use prefixes only. It creates each staged member `.env` with mode 0600 from
  the start.

## Known behaviour

- A mapped server the Border has not registered is skipped, as before. Mapping a server does not
  install it.
- Members staged before this change keep their old `.env`; re-running `in2n-migrate.py`
  regenerates it.
- A component-launched server in a member reads the file its `NETCLAW_RUNTIME_ENV` names, the
  member's own, plus the environment its runtime passes it, never the Border's `.env`. For it to
  find its settings (for example `PYATS_TESTBED_PATH`, `NETBOX_TOKEN`), the member's slice must
  be at `<member home>/.env`, or the member home is provisioned with `--member-env` pointing at
  the staged `members/<name>/.env`.
- Every component-launched server of a member (`component-launch.py` loads every key of
  `NETCLAW_RUNTIME_ENV`) receives the member's whole `.env`: its integration keys and its own
  `N2N_*` settings, including the enrollment token while it is set, and its provider key. The
  file is the member's least-privilege slice, never the Border's, so these servers see no more
  than the member process itself.
- A pyATS member's change root (`NETCLAW_CHANGE_ROOT`, set by `component-launch.py` from the
  runtime root) is `<member home>/netclaw-changes`, the member's own. The HUD's change workflow
  issues apply grants only into the Border's vault and binds them to that vault's path, so a
  pyATS member cannot apply a HUD-approved private migration: the claim is refused (no grant,
  policy or signing key in its vault). HUD private-migration change flows are Border-only and
  unsupported on members; research.md has the evidence.
- Every member keeps `memory-mcp`, whose `MEMORY_DATA_DIR` defaults to the Border's
  `~/.openclaw/memory` (`config/mcp-env-defaults.json`), so members share the Border's memory
  store. This predates spec 183 and is out of scope here.
- Existing member homes are not rewritten: `in2n-member-home.py` refuses to overwrite a
  provisioned `openclaw.json`. An operator re-provisions a member to pick up the new servers.

## Out of scope

Skill documentation that names tools or servers differently from the registered server, adding
profiles, and Hermes members (only `subnet` is qualified there); see research.md. The Convergence
member's `.env` is written by `provision_convergence`, not by the slice, and its registration is
built there with the member's own runtime paths (unchanged).
