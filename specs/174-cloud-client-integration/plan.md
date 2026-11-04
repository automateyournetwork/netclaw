# Implementation Plan: R04a cloud Border clients

**Branch**: `174-cloud-client-integration` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

## Summary

Add explicit cloud-owner clients to the existing VS Code extension and Flutter app, using the existing protected HTTPS routes. Preserve local and edge authority. No new server surface or framework.

## Technical Context

**Language/Version**: existing TypeScript5.9/Node24.19; Dart/Flutter current project toolchain; Python3.12 federation.
**Primary Dependencies**: VS Code APIs, Node HTTPS, existing Flutter HTTP and secure storage, existing Express owner service.
**Storage**: non-secret profile/reference state, native secure sessions, memory-only CSRF/tickets.
**Testing**: Node/extension host, Flutter unit/widget/native, existing Python/HUD suites and finite live cloud qualification.
**Target Platform**: actual Mac VS Code; selected available native Mobile target, with physical versus simulator scope explicit.
**Project Type**: existing clients and narrow server compatibility correction.
**Performance Goals**: bounded response sizes/timeouts; no polling that repeats effects.
**Constraints**: verified TLS, no redirect, immutable exact review, unknown outcome pause, no new provider/member secrets on clients.
**Scale/Scope**: one owner, two client integrations, existing R04 read catalog.

## Constitution Check

Pre/post design PASS: observation precedes changes; actual effects require exact review; GAIT/private receipts retained. Existing MCP execution reused. Existing capabilities extended, no new integration/server/catalog/install component. README/public rollout and WordPress publication deferred under explicit roadmap hold; maintainer specs supply documentation. Spec→plan→tasks→implementation ordering retained. Native/platform evidence never inferred from mocks. No required product clarification.

## Project Structure

- `extensions/netclaw-vscode/src/` and `test/`: explicit remote profile, owner client, native protected workflow and local guard tests.
- `mobile/netclaw-mobile/lib/` and `test/`: separate cloud owner connection, native review/results/recovery and compatibility tests.
- `mcp-servers/protocol-mcp/bgp/federation/service.py`: truthful protected edge capabilities only.
- `ui/netclaw-visual/src/hud-server/`: existing owner API and confinement regressions.
- `specs/174-cloud-client-integration/`: contracts, task/evidence/maintainer handoff.

Root owns common contracts and cloud/native evidence; isolated VS Code and Mobile worktrees own their respective clients. No concurrent edits to the same paths. Remaining optional pass5 covers this implementation; no automatic extra loop.

## Complexity Tracking

No new architectural exception. Fresh finite cloud deployment uses new identity/state and exact resource review; spent R04 artifacts are evidence only. R05 remains behind human acceptance.
