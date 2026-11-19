# Spec 198: percepxion-oob skill refresh and source-of-truth console paths

Created 2026-11-19; branch `198-percepxion-oob-skill-refresh`, on 1.24.0. Follow-up to
[spec 104](../104-percepxion-oob-integration/spec.md) by the same contributor.

## Problem

- `workspace/skills/percepxion-oob/SKILL.md` is 1,122 lines, the largest skill in the repository
  (the next is 623). The asynchronous-job rule appears six times and the console-server versus
  managed-device distinction four times; most of the length is per-call JSON the tool schemas
  already carry. An agent loads all of it to answer a one-line inventory question.
- Several tool parameters in it are wrong against the server NetClaw installs:
  `request_device_syslog_upload` takes `device_ids` (a list), `query_device_access_log` has no
  `query` parameter, and `search_job_groups` takes `search_string`. `update_device_config` and
  `clone_device_config` start jobs but aren't listed as asynchronous.
- It names two skills that don't exist (`netbox-source-of-truth`, `itential-orchestration`).
- It carries dated product status, version history and endpoint provenance that age badly in a
  shared repository. TOOLS.md repeats the provenance and says 37 Percepxion tools; the server has 38.
- It has no path from NetBox or Nautobot. Lantronix now publishes a NetBox plugin
  (`netbox-lantronix`) and a Nautobot SSoT app (`nautobot-app-ssot-lantronix`) that keep console
  servers, port labels and console cables current from Percepxion and ship a console coverage gate,
  and `lantronix.oob` 1.4.0 adds a gate role and an Event-Driven Ansible source. NetClaw already has
  `netbox-mcp` and `nautobot-mcp`, which can read the cabling and run the Nautobot gate job.

## Requirements

- FR-001: `SKILL.md` keeps the routing knowledge an agent needs on every call (the two device
  identities, which server answers what, the rules) and moves setup and step-by-step detail into
  `references/` files it links to. Target: under 250 lines.
- FR-002: Every tool name and parameter in the skill and its references matches percepxion-mcp-server
  and slc-mcp-server at the revisions NetClaw installs (`config/fastmcp-external-patches.json`).
- FR-003: Rules are stated once, with the reason, and without dated product status or version
  history. Change-safety comes first: the preflight (W2) is the lead workflow.
- FR-004: W9 finds a managed device's console path from NetBox (`dcim.consoleport` connected
  endpoints) or Nautobot (GraphQL, the SSoT app's custom fields), confirms it in Percepxion, and
  reports a disagreement to `netbox-reconcile` instead of returning the path. Read-only.
- FR-005: W10 runs the console coverage gate: the Nautobot job through `nautobot-mcp`, and for NetBox
  the `lantronix.oob` role or the operator. It lists the gate's reasons and fixes.
- FR-006: Only publicly available software is referenced: the two MCP servers, the NetBox plugin and
  Nautobot app (PyPI and GitHub), `lantronix.oob` (Automation Hub and GitHub release tags), and the
  community device-type library.
- FR-007: Related-skill references resolve to skills that exist.
- FR-008: Documentation surfaces agree: the Percepxion tool count is 38 in README, TOOLS.md, the
  component catalog and the installer message; TOOLS.md drops endpoint provenance and version history;
  the catalog's skill digest and description are regenerated.

## Out of scope

Moving the reviewed revisions of the two Lantronix servers forward (newer releases add HTTP
transports and credential providers but no tools); installer, HUD or `.env.example` changes; any
change to `netbox-mcp`, `nautobot-mcp` or other skills.
