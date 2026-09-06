# Spec 120 — Topolograph BGP Topology MCP Onboarding

**Status**: draft
**Roadmap**: external integration (remote HTTP MCP), follow-on to spec 119
**Date**: 2026-09-02

## Problem

Spec 119 onboarded `topolograph-mcp` for IGP (OSPF/IS-IS) link-state
analysis only — deliberately out of scope for BGP (see spec 119 research
R4/scope). Upstream `topolograph-mcp-server` has since added 14 read-only
BGP tools (PR #1, branch `claude/flask-visual-topolograph-onboarding-0lz6rb`,
not yet merged) fronting Topolograph's BMP-fed BGP topology: speakers,
sessions, route search, VRF/VPN inventory, and BGP-to-IGP graph binding.
NetClaw has no source for "what does the BGP control plane believe" the way
`topolograph-igp-analysis` answers that question for IGP.

## Goal

Extend the existing `topolograph-mcp` remote registration (same server, same
`config/openclaw.json` entry, same `TOPOLOGRAPH_API_TOKEN`) with the new
tool surface, and add a second, narrowly-scoped skill —
`topolograph-bgp-analysis` — that owns BGP topology reasoning. No new MCP
server, no new credential, no new catalog id.

## Scope

In:
- Documentation surfaces for the 14 new tools: README MCP Servers row +
  counts, SOUL.md capability section + counts, `TOOLS.md` detail section,
  new `workspace/skills/topolograph-bgp-analysis/SKILL.md`.
- `catalog.sh` / `install-steps.sh` description strings updated to mention
  BGP (same component id `topolograph`, no new entry).

Out:
- Merging upstream PR #1 — tracked separately, this spec documents against
  the reviewed tool surface regardless of merge state (mirrors how spec 119
  landed docs referencing `TOPOLOGRAPH_MCP_READ_ONLY` before every consumer
  had upgraded).
- Any change to `config/openclaw.json`, `EXTERNAL_INTEGRATIONS`, or the
  credential shape — unchanged from spec 119.
- Write tools — the upstream server is still `TOPOLOGRAPH_MCP_READ_ONLY=true`
  by default; none of the 14 new tools mutate.
- Functional acceptance testing against a live Topolograph + BMP watcher
  stack — deferred, see `research.md` (same constraint as spec 119 R4).

## Acceptance

- `python3 scripts/reconcile-mcp.py` exits 0.
- `python3 scripts/verify-spec-artifacts.py` passes for this spec dir.
- `python3 scripts/verify-inventory-counts.py` PASS with skill count
  incremented by exactly 1 (new skill dir), MCP integration count unchanged
  (no new server).
- README/SOUL/TOOLS tool-count prose for `topolograph-mcp` reads 27 (13 IGP
  + 14 BGP), computed by hand against the upstream tool list, not guessed.
