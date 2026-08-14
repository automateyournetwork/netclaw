# Spec 104, Lantronix Percepxion OOB integration

**Status**: implemented
**Branch**: `104-percepxion-oob-integration`
**Date**: 2026-08-13
**Roadmap**: new coverage area, out-of-band (OOB) console-server management

## Summary

Adds a `percepxion-oob` skill covering out-of-band (OOB) console-server management via two
external, actively-maintained Lantronix MCP servers:

- **`percepxion-mcp-server`** (37 tools), fleet-wide operations through the Percepxion SaaS
  platform: device inventory, firmware compliance and rollout, config management, Smart Groups,
  security audit, and asynchronous CLI command dispatch with output retrieval.
- **`slc-mcp-server`** (37 tools), direct, synchronous device-level operations against
  individual SLC9000/SLC8000 console servers: port status, session management, synchronous CLI
  output, cellular status, and the Percepxion client lifecycle running on the device itself.

OOB is a real coverage gap NetClaw had no answer for: **the primary network path is exactly what
console-server access exists to work around.** When a device is unreachable in-band, an OOB path
through its serial console (often over an independent cellular WAN) is the only way to diagnose
or recover it without a truck roll. None of NetClaw's 163 existing MCP integrations reach a
device's console port; this closes that gap.

## Why two servers, one skill

Percepxion and slc-mcp-server are not redundant, they answer different questions and the
distinction is the skill's spine, the same way spec 094's BMC-vs-host distinction is the spine of
`redfish-mcp`:

| Question | Answer via | Why not the other |
|---|---|---|
| Fleet-wide firmware compliance, bulk config push, security audit across many devices | Percepxion | slc-mcp-server has no fleet concept, it talks to one device at a time |
| Synchronous CLI output from one device, right now, no polling | slc-mcp-server (`apply_config_commands`) | Percepxion's `send_direct_cli_command` is async, job group create, then a separate `get_cli_command_output` fetch once status reaches `"Completed"` |
| A device reachable only through Percepxion's cloud path (no direct network route) | Percepxion | slc-mcp-server needs a direct IP/jump-host path to the device |

The skill's own "Key Terms" and "CLI Command Routing" sections (ported from an existing internal
draft, see Verification) encode this distinction as tool-routing rules, not prose the caller has
to infer.

## External, not vendored, and why

Both servers are Lantronix's own actively co-developed repositories
([`percepxion-mcp-server`](https://github.com/Lantronix/percepxion-mcp-server),
[`slc-mcp-server`](https://github.com/Lantronix/slc-mcp-server)), not a frozen third-party target
to adopt and pin. Both shipped real fixes in the week this spec was written, a permission-model
bug, a new CLI-output-retrieval capability, a dependency refresh. Vendoring a frozen copy under
`mcp-servers/` (spec 083's Zabbix pattern) would go stale on the first upstream release and
require a manual re-sync on every Lantronix change; that maintenance shape fits an adopted
third-party tool, not two repos under active co-development by the same author submitting this
integration.

Classified per `docs/ADDING-AN-MCP.md`'s table as **installed on demand (pip/git)**, the same
shape as `pyats` and `aap-automation`: `git clone` + `pip install -e .` into
`$NETCLAW_DIR/mcp-servers/`, recorded in `EXTERNAL_INTEGRATIONS`, no `config/openclaw.json`
entry (the installed path is user-specific, not a fixed repo-relative path).

## Requirements

- **FR-001** The skill MUST disambiguate "OOB device" (the Lantronix console server) from
  "managed device" (the router/switch/firewall cabled to its serial port) before routing any
  tool call, the two device-identity spaces are not interchangeable and confusing them sends a
  command to the wrong hardware.
- **FR-002** CLI output retrieval MUST be documented as the two-call pattern it actually is:
  poll `get_job_group`/`search_job_groups` for status, then `get_cli_command_output` for text.
  `get_job_group` alone never returns command output, documenting it as sufficient produces an
  agent that reports empty output as "the command produced nothing."
- **FR-003** Destructive and write operations (`send_direct_cli_command` in write mode,
  `update_firmware_by_smart_group`, `reboot_device`, `remove_device_from_platform`) MUST require
  explicit operator confirmation before invocation, consistent with Constitution Principle III.
- **FR-004** The skill MUST document that Percepxion enforces its own server-side CLI policy
  (read-only default, deny-list, `PERCEPXION_CLI_WRITE_ENABLED`) which the calling agent cannot
  override at runtime, this is server configuration, not a tool parameter.
- **FR-005** The skill MUST document Percepxion's role-based `organization_id` requirement:
  required for Project Admin sessions on job/telemetry/content/Smart-Group/audit calls, optional
  (auto-scoped) for Tenant Admin/Tenant User. Omitting this context produces confusing
  `ACCESS_DENIED` failures with no indication of the actual cause.
- **FR-006** Both servers MUST be installed into a dedicated virtualenv, never the installer's
  shared interpreter. Both pin `fastmcp>=3.1.0,<4.0`; spec 076's cryptography incident and the
  Zabbix install function's fastmcp-3-vs-five-servers-pinning-fastmcp<3 conflict are the same
  failure shape this sidesteps.
- **FR-007** Neither server's `requirements.txt`/`pyproject.toml` may carry an unbounded pin on a
  package whose submodule is imported (spec 077). Verified directly against both repos' current
  `pyproject.toml`, see Verification.

## Verification

- Both servers' `pyproject.toml` dependency pins checked directly: `fastmcp>=3.1.0,<4.0`,
  `requests>=2.32.0,<3.0`, `python-dotenv>=1.2.0,<2.0` (`percepxion-mcp-server`); the same three
  plus `hvac`, `boto3`, `pyotp`, all upper-bounded (`slc-mcp-server`). No unbounded pin on any
  package with an imported submodule.
- `scripts/reconcile-mcp.py` run against this branch (see plan.md Phase 4 for the exact command
  and result).
- `python3 scripts/verify-inventory-counts.py` confirms the count delta: 221 → 222 skills,
  163 → 165 MCP integrations (60 → 62 external, 103 config-registered unchanged, since neither
  server gets a `config/openclaw.json` entry).
- The skill body (workflows, tool routing, CLI output correction) was drafted and iterated
  against both servers' actual source over several sessions of hands-on use, including a live
  root-cause finding that `get_job_group` never returns CLI output text (only
  `get_cli_command_output`, added upstream in `percepxion-mcp-server` v1.1.0, does), rather than
  written from the servers' documentation alone.

## Out of scope

- **Vendoring either server.** See "External, not vendored, and why" above.
- **A NetClaw-side CLI policy layer.** Both servers already enforce their own (Percepxion
  server-side env vars; slc-mcp-server's `cli_policy.py`). Duplicating it in the skill would be
  two sources of truth for the same rule.
- **iN2N federation artifacts.** No request to expose this to a federated member as of this
  spec; the five-artifact federation checklist in `docs/ADDING-AN-MCP.md` is not executed here.
- **A dedicated `mcp-servers/<name>/README.md`.** That artifact is for vendored copies; an
  external/on-demand integration's install and tool documentation lives in the skill itself and
  in each upstream repo's own README, consistent with `aap-automation`'s precedent.
