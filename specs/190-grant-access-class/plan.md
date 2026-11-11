# Implementation Plan: Read/Write Access Class on Per-Peer Grants

**Branch**: `190-grant-access-class` (stacked on `189-peer-limit-semantics`, PR #350) | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)
**Input**: GitHub issue #344

## Summary

Add a first-class access class to `invocation_grant` (`read` | `read_write`, stored default `read_write`) and a target classification registry (`tool_classification`: operator override and imported MCP annotation). `Authorizer.authorize()` gets one new check between "grant found" and the rate check: under a `read` grant the target must be classified read, else `Decision(False, "not_allowlisted", ...)` with a generic reason and an `access_class_denied` audit row. `admit()` re-runs `authorize()` so revalidation is covered for free. Wire: no new error code or method; the card gains optional advisory hints. Operator surface: `n2n_grant` gains `access_class`; new classification routes and n2n-mcp tools. Draft and docs updated.

## Technical Context

**Language/Version**: Python 3.10+ (tests on 3.12 venv)
**Primary Dependencies**: stdlib only (sqlite3, json); existing FederationManager, Authorizer, Auditor, InventoryBuilder
**Storage**: existing `federation.db`; additive: `ALTER TABLE invocation_grant ADD COLUMN access_class TEXT NOT NULL DEFAULT 'read_write'` through the existing try/except ALTER list, and `CREATE TABLE IF NOT EXISTS tool_classification` (SCHEMA_190)
**Testing**: pytest `tests/n2n/test_grant_access_class_190.py`; full `tests/n2n` regression
**Project Type**: protocol library inside protocol-mcp + n2n-mcp operator tools
**Performance Goals**: one extra indexed SQLite read per authorize for `read` grants only; `read_write` grants skip it
**Constraints**: existing tests unmodified and passing; no new wire fields except optional card hints; no new wire error code; `_find_grant` signature unchanged
**Scale/Scope**: tens of peers, hundreds of tools

## Constitution Check

- IV Immutable Audit Trail: class refusals, grant class, classification changes via `Auditor.record`. PASS.
- IX Security by Default: default-deny unchanged; unclassified is never read; peer-supplied claims never authorize. PASS.
- XI Full-Stack Artifact Coherence: draft source, operator doc, skill doc, MCP tool docs, hash pin, tests, spec. Rendered draft cannot be regenerated (kdrfc/xml2rfc absent) and is recorded as a gap. PASS with documented gap.
- XV Backwards Compatibility: additive schema, stored default preserves behavior. PASS.
- XVI Spec-Driven: this flow. PASS.
- N/A: Read-before-write (no device change), new MCP server.

Re-check after design: no violations.

## Project Structure

```text
specs/190-grant-access-class/  spec.md plan.md research.md data-model.md quickstart.md contracts/ tasks.md verification.md
mcp-servers/protocol-mcp/bgp/federation/
  manager.py         # ALTER invocation_grant.access_class; SCHEMA_190 tool_classification
  authorization.py   # grant(access_class), classify/clear/import, effective class, check in authorize()
  inventory.py       # advisory tool_access / access hints in card
  invocation.py      # audit decision access_class_denied
mcp-servers/protocol-mcp/bgp-daemon-v2.py   # grants + classification routes, one-step trust
mcp-servers/n2n-mcp/server.py               # n2n_grant(access_class), n2n_classify, n2n_list_classifications
config/hermes-hud-tool-policy.json          # re-pin n2n-mcp/server.py hash
docs/ietf/draft-capobianco-ncfed-00.md      # normative section + cross refs + change history
docs/N2N-GRANT-ACCESS-CLASS.md, docs/N2N-PEER-LIMITS.md, workspace/skills/n2n-federation/SKILL.md
tests/n2n/test_grant_access_class_190.py
```

## Design decisions (answers to the issue)

1. First-class field: yes, `access_class` on the grant.
2. Expression: a ceiling on the grant plus a callee-side classification of each target; card carries advisory hints only.
3. Default: `read_write` for legacy rows and omitted values (node default overridable with `N2N_GRANT_DEFAULT_ACCESS=read`, stored explicitly per new grant).
4. Inventory pull stays on visibility; knowledge query/replication are intrinsically read, still separate grants.
5. Skill delegation: write unless the operator classified the skill read; request text never inspected.

See research.md for alternatives and the normative decision table.
