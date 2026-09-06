# Spec 119 — Topolograph IGP Topology MCP Onboarding

**Status**: draft
**Roadmap**: external integration (remote HTTP MCP)
**Date**: 2026-08-27

## Problem

NetClaw can read device state, flow, and telemetry, but has no source for
**IGP link-state topology analysis** — OSPFv2/OSPFv3/IS-IS shortest-path and
backup-path computation, per-area LSDB inspection, edge/node failure
simulation, MPLS-TE/CSPF feasibility, and an event timeline of topology
churn. Topolograph exposes exactly this over an HTTP API, and there is an
existing MCP wrapper (`topolograph-mcp-server`) that fronts it.

## Goal

Register the Topolograph MCP server as a **remote HTTP integration** — the
same shape as `globalping-mcp` (spec 079): a `config/openclaw.json` entry
with a `url`, no vendored server, a bearer token from the operator's own
Topolograph instance. Add one skill, `topolograph-igp-analysis`, that owns
the "what does the IGP think the topology is / would be" question.

## Scope

In:
- `config/openclaw.json` `topolograph-mcp` entry (`url` + bearer header).
- Installer coverage: `catalog.sh` id `topolograph`,
  `component_install_topolograph()` (registration + credential check only).
- `PROFILE_MULTIVENDOR` membership. **Not** `PROFILE_RECOMMENDED` — IGP
  link-state analysis is a multivendor-network concern, not a baseline one.
- Documentation surfaces: README MCP Servers table + counts, SOUL.md
  capability section + counts, `.env.example`, `TOOLS.md`, HUD node +
  annotation, `workspace/skills/topolograph-igp-analysis/SKILL.md`.
- Client-side tool allowlist via `defenseclaw tool allow` (documented in the
  skill, not enforced in repo config).

Out:
- Vendoring the server. It fronts an operator-run API and is actively
  developed upstream; a frozen copy would go stale.
- Write tools. The upstream server defaults to `TOPOLOGRAPH_MCP_READ_ONLY=true`
  and hides all mutation tools from `tools/list`; NetClaw consumes the
  read-only surface only.
- Manifest token-count measurement and functional acceptance testing against
  a live Topolograph + MongoDB stack — deferred, see `research.md`.

## Acceptance

- `python3 scripts/reconcile-mcp.py` exits 0.
- `python3 scripts/verify-spec-artifacts.py` passes for this spec dir.
- README/SOUL headline counts computed, not hand-counted, and consistent.
- `$MCP_CALL topolograph-mcp get_all_graphs '{...}'` resolves the endpoint
  from `config/openclaw.json` once `TOPOLOGRAPH_API_TOKEN` is set.
