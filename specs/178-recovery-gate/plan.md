# Implementation Plan: R07 recovery gate

**Branch**: `178-recovery-gate` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

## Summary

Credit accepted R03–R06 recovery evidence, then close uncovered runtime/client
cases. Actual strict-TLS socket reproductions show post-await revocation races.
Client inspection shows stranded endpoint-bound references and non-durable HUD
approval send markers. Fix existing code; no new service, protocol or HA authority.

## Technical Context

**Language/Version**: Python3.12 federation; existing Node24.19/React18 HUD; TypeScript5.9 VS Code; Dart3.12.2/Flutter3.44.8 Mobile.
**Primary Dependencies**: Existing asyncio/SQLite, cryptography/pyOpenSSL, FastMCP/MCP, Express/React, VS Code APIs, Flutter secure storage/WebSocket.
**Storage**: Existing private identity/ledger/reference stores; additive bounded identifiers and monotone send markers; private evidence0700/0600.
**Testing**: pytest strict TLS/native MCP, Node/JSDOM/editor build, Flutter/analyzer, actual browser/isolated Code/native iOS simulator.
**Target Platform**: Mac clients/local federation; inherited Ubuntu GCP evidence explicitly tied to prior source/runtime.
**Project Type**: Existing distributed application recovery qualification.
**Performance Goals**: Measure detection and restore-to-recovery separately, then propose objectives for human agreement.
**Constraints**: Same pinned identity; no uncertain replay, automatic fallback, secret/cookie transfer, publication or retention extension.
**Scale/Scope**: Isolated single-region recovery, three clients, historical evidence credit; no new cloud resources by default.

## Constitution Check

Pre-research and post-design checks pass. I–III/VIII: read-only isolated work,
baseline/verify and exact applicable runtime review; no device configuration.
IV: active GAIT and additive evidence. V–VII: existing MCP/federation/guard.
IX/XIII: strict trust, authority checks and no secrets in references. X–XII:
separate client evidence and coherent declarations; capability counts unchanged.
XIV: no external communications. XV: preserve ordinary/protected compatibility.
XVI: complete SDD sequence. XVII: owner publication hold keeps technical evidence
local/in maintainer specs. No waiver or optional Ralph loop.

## Project Structure

- `mcp-servers/protocol-mcp/bgp/federation/`, `tests/n2n/`: runtime agent.
- `ui/netclaw-visual/`, `extensions/netclaw-vscode/`: surfaces agent.
- `mobile/netclaw-mobile/`: Mobile agent.
- `specs/178-recovery-gate/`, private evidence/resource integration: coordinator.

## Design and Phases

1. Freeze scope, evidence credit, retirement baseline and contracts. Three research
   agents work read-only in separate worktrees before the implementation checkpoint.
2. Runtime: retain failing real TLS races; recheck authority after awaited inbound
   handler/outbound call; persist removal before async channel close; enforce
   applicable certificate validity, bounded dial failure cause. Qualify same-ID
   async/protected duplicate/cancel and registry/restart behavior.
3. Surfaces: durable single-operation decision/revoke sent markers before I/O;
   no redirect; explicit same-installation endpoint update preserving profile ID
   and safely copied bounded references, never session cookies. Existing exact
   operation-ID recovery is reused; add nonce/parent recovery only as needed.
4. Mobile: explicit same trusted hostname/path/new WSS-port update verified by
   existing retained-key challenge and installation/principal identity. Preserve
   HTTPS origin/reference namespace. Reject late dial completion after stop.
5. Coordinator integrates commits and runs affected full suites; agents qualify
   actual isolated native clients. Serialize shared runtime/cloud mutations.
6. Export evidence, stop owned disposable processes/profiles, write scenario
   runbooks/timings, and seek final human timing/acceptance review before R08.

## Contracts and verification

Address is routing, not authority. Different verified hostname/key requires
separate trust/enrollment and is outside same-identity migration. Stale revision,
wrong identity, invalid certificate and redirects refuse without erasing old data.
Send markers only advance absent→sent, durably before I/O; GET/import cannot clear
uncertainty. Revocation linearizes at durable state change; recheck after await
before delivery/acceptance, but retain any earlier effects. Duplicate guarantees
apply to operation/task submission identities, not arbitrary repeated synchronous
read calls. Never replay a synchronous call whose result is unknown.

Evidence classes distinguish real local TLS/native client, controlled provider,
actual native guard/workload and inherited cloud evidence. Screenshots need
correlated original IDs, method/effect counts and authority hashes. If changed
code invalidates historical credit, requalify that path under concrete scope.
Focused regressions precede broad integrated checks; no repetitive test loop.

## Resources and preservation

Private root `~/.local/share/netclaw/roadmap-r07-20261106/`; three separate worktrees.
Fresh isolated local homes/processes are default. Inspect actual R05/R06 resources
and original retirement receipts before resource work. Preserve Nov7/Nov8 jobs
and original Border December1. No shared cloud mutation until a concrete baseline,
plan, rollback and applicable delegation exist. Private exports precede cleanup.
Source1.18.6/extension1.6.1/Mobile1.0.4+7 unchanged. No publication or R08 work.

## Complexity Tracking

No new framework, MCP server or authority protocol. Bounded client reference
preservation and explicit endpoint-port update are necessary to close proven gaps.
