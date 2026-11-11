# Implementation Plan: Federated Peer Limit Semantics (max-prefix-style)

**Branch**: `189-peer-limit-semantics` | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)
**Input**: GitHub issue #343

## Summary

Make the existing per-peer rate / daily budget limits normative and add a max-prefix-style exceed policy. The existing chokepoints are reused: `Authorizer.authorize()` (decision), `Authorizer.admit()/reserve_request()/debit()` (debit), `ChatService.handle_chat_message` (chat). A new `limits` layer inside `authorization.py` resolves a per-peer effective policy (persisted override, else env default), applies the exceed action (`refuse` default, `warn`, `teardown`), emits warning and limit events through the existing `Auditor`, applies an optional global cap, and persists a hold-down. `FederationService` wires a teardown hook (closes the channel via the same path as `sever_local` but WITHOUT revoking consent) and checks hold-down on inbound channel accept. No wire changes: -32004/-32005/-32007 are reused. Draft text and docs are updated in place.

## Technical Context

**Language/Version**: Python 3.10+ source (tests run on 3.12 venv)
**Primary Dependencies**: stdlib only (sqlite3, time, os, asyncio); existing FederationManager/Auditor/FederationService
**Storage**: existing `~/.openclaw/n2n/federation.db`; new additive tables (see data-model.md); `CREATE TABLE IF NOT EXISTS`, idempotent
**Testing**: pytest (`tests/n2n/`), new `tests/n2n/test_peer_limits_189.py`; full `tests/n2n` regression run
**Target Platform**: Border/daemon on Linux/macOS
**Project Type**: protocol library inside protocol-mcp
**Performance Goals**: limit check adds O(1) SQLite reads per admitted request; no measurable change to defaults
**Constraints**: default behavior byte-identical when no config; no new wire fields/codes; Decision/grant API shape unchanged (FR-015)
**Scale/Scope**: tens of peers

## Constitution Check

- IV Immutable Audit Trail: every limit event goes through `Auditor.record` (SQLite + GAIT). PASS.
- IX Security by Default: default stays refuse; teardown/hold-down persisted so restart cannot bypass. PASS.
- X Observability: status API + HUD peer record fields. PASS.
- XI Full-Stack Artifact Coherence: draft source, docs, HUD status fields, tests, spec all updated; rendered draft files cannot be regenerated locally (kdrfc/xml2rfc absent) and this is recorded, not hidden. PASS with documented gap.
- XV Backwards Compatibility: defaults unchanged; additive schema. PASS.
- XVI Spec-Driven: this flow. PASS.
- Not applicable: ITSM/Read-before-write (no device changes), MCP-native (no new MCP server; operator surface is manager/authz API + daemon status).

Re-check after design: no violations.

## Project Structure

```text
specs/189-peer-limit-semantics/  spec.md plan.md research.md data-model.md quickstart.md contracts/ tasks.md verification.md
mcp-servers/protocol-mcp/bgp/federation/
  authorization.py   # policy resolution, exceed actions, warning latch, global cap, hold-down, reset, status
  manager.py         # SCHEMA_189 tables
  invocation.py      # no-op except teardown scheduling via decision.teardown (small)
  chat.py            # route chat through authz.admit_chat()
  service.py         # wire teardown hook, hold-down check on accept/register
bgp-daemon-v2.py     # peer status includes limits block (HUD)
tests/n2n/test_peer_limits_189.py
docs/ietf/draft-capobianco-ncfed-00.md  # edited in place
docs/ (operator doc)  # docs/N2N-PEER-LIMITS.md
```

## Complexity Tracking

None.
