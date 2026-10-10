# Implementation Plan: NetClaw for Visual Studio Code

**Branch**: `150-vscode-extension` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)
**Status**: Design complete for review; implementation requires ratification. No runtime qualification is claimed.

## Summary

Manage existing standalone NetClaw and Risk installations from a desktop workspace extension. Required clients are macOS, Windows and Linux VS Code, including Remote SSH and mandatory WSL2. Required NetClaw host families are native Linux, WSL Linux and macOS. No backend installation/bootstrap/upgrade is performed by the extension.

The owner confirmed that VS Code Copilot, Claude Code and Codex may inspect, delegate natural-language work and propose managed changes. A separately scoped assistant MCP interface preserves this authority throughout downstream harness/tool calls; the private operator interface is not registered with assistants. Neither interface manufactures human approvals. Required WSL evidence includes a handoff to the owner's real Windows/WSL machine.

## Technical Context

**Language/Version**: Planned TypeScript 5.9.3/ES2022 extension; stable VS Code >=1.102.0; JavaScript ESM backend using existing NetClaw Node >=24.19 <25 or >=26.1; existing isolated Python 3.12 federation/MCP and Python 3.14 Hermes companion remain separate.
**Primary Dependencies**: Planned official MCP client/server 2.3.1, existing React 18.3.1 and HUD/Canvas/Three.js components; backend node:sqlite. VS Code MCP server-definition provider is stable by 1.101, MCP is generally available in 1.102. Build/test runner @vscode/test-electron3.1.0 requires Node>=22; build on Node24, separately from the editor host. Lock transitive dependencies during implementation.
**Storage**: Nonsecret host/profile-scoped editor storage, owner-private backend operation/ownership/grant ledger and artifacts, existing runtime histories/GAIT; secrets only in selected installation approved .env sources and existing SSH credential handling.
**Testing**: node:test contracts, packaged VSIX in real VS Code, existing HUD/Canvas/Python regression, real Windows+WSL2 and Remote SSH, real named-assistant MCP workflows, package/privacy inspection and Marketplace installation.
**Target Platform**: Desktop macOS/Windows/Linux with Remote SSH and WSL2; existing backend macOS/native Linux/WSL Linux. Browser, Codespaces, Dev Containers and native Windows NetClaw hosting are excluded.
**Project Type**: VS Code extension, operator-private MCP management backend, separately scoped assistant MCP surface, shared HUD/domain service adapters.
**Performance Goals**: Spec SC-001/004; bounded discovery, pagination and result sizes; durable admission before effects; no uncertain replay.
**Constraints**: Existing installations only, no generic shell/URL/path/MCP dispatch, no credentials in editor or tool output, no inference from a client name to its authority, no automated human approval.
**Scale/Scope**: Nine journeys; complete HUD domain coverage; Copilot/Claude Code/Codex; 100 members, 100 peers, 1,000 inventory rows.

## Constitution Check

Design gates, not implementation passes:

- I–IV/VIII: observation, real baselines, approved changes, append-only GAIT, verification/recovery and scoped Terminal Intent Local/Lab only.
- V–VII: official-SDK MCP interfaces and existing qualified domain tools. Presentation adapters do not create a second vendor execution path.
- IX/XIII: authenticate OS/SSH principal and backend grants, not client labels. Provider/integration credentials stay in .env. The new path must normalize legacy literal gateway/companion credentials through reviewed shared-launcher changes; copying them into another JSON/editor store is not acceptable.
- X–XII/XV: catalog/install-step/coverage/HUD/skill/SOUL/TOOLS/README/.env.example coherence, explicit private registration and preservation of existing clients. The extension does not install its backend component; owners obtain it through their ordinary NetClaw installation/update process.
- XIV/XVII: owner-selected publisher and explicit public-release authorization, blog draft for review, no automatic messages/tickets.
- XVI: all product clarifications are resolved; complete contracts and tasks, run read-only cross-artifact analysis, then obtain ratification before implementation. No implementation is authorized by this draft.

A separate executable or MCP tool inventory is not an OS security boundary against an unrestricted same-user terminal agent. Human approval must be independently validated by the backend/existing change-control system; stronger isolation needs qualified OS/account separation. Both hidden methods and direct calls must enforce permissions. External agents must not be given human approval or credential-management tools.

## Architecture decisions established by research

1. One workspace extension (`extensionKind: ["workspace"]`). In WSL/Remote SSH it runs beside the selected installation. Local Windows users reopen the intended WSL distribution or use an existing SSH alias; no guessed path translation.
2. Native explorer, commands, status/output and bundled rich views. Webviews use typed messages to the extension host, not direct calls through loosened HUD CORS/authentication.
3. Private operator MCP over stdio, or fixed safely quoted launcher over authenticated OpenSSH. No new public HUD listener, agent forwarding, automatic host-key acceptance or workspace-controlled command text.
4. Durable backend admission, nonce/body-digest matching, configuration revisions and process-safe locks. Existing runtimes own asynchronous work. Closing an MCP/SSH bridge must not terminate independently owned services; lost outcomes remain unknown until authoritative reconciliation.
5. Installation-owned service identity includes PID/start time/executable/manifest. Never wrap broad DefenseClaw enable/disable or secure-start scripts that install software, migrate data or kill by name.
6. Shared backend services extract useful HUD logic without importing its listening server. Add owned durable OpenClaw/Terminal Intent request handling; preserve Hermes ledger/qualification. Profile selection does not change global runtime selection.
7. Agent-facing MCP is a distinct permission surface with explicit client setup, grant/disclosure scope, revocation and named-client tests. Copilot uses the stable MCP server-definition provider after user opt-in. Terminal agents use documented reviewed configuration independent of the VS Code process. No client choice supplies NetClaw approval.
8. Dedicated NetClaw chat remains independent of Copilot. External-assistant inference and delegated NetClaw inference may use different providers and incur separate usage; no invented combined cost.

## Project Structure

Planned paths; not implemented:

```text
extensions/netclaw-vscode/
  src/connection/  src/state/  src/views/  src/commands/  src/webview/  src/clients/
  webview/  resources/  test/  package.json
mcp-servers/netclaw-operator-mcp/
  server.mjs  schemas.mjs  README.md
mcp-servers/netclaw-assistant-mcp/
  server.mjs  schemas.mjs  README.md
ui/netclaw-visual/src/management/
  identity.js  policy.js  journal.js  proposals.js  worker.js
  configuration.js  lifecycle.js  runtime.js  federation.js  security.js
  conversations.js  intent.js  evidence.js  workspace.js  clients.js
scripts/netclaw-operator.mjs
scripts/netclaw-assistant.mjs
tests/operator/  tests/vscode/  tests/assistant-clients/
docs/VSCODE.md  docs/VSCODE-COMPATIBILITY.md
workspace/skills/netclaw-operator/SKILL.md
```

## Design artifacts and delivery sequence

- [Research](research.md), [data model](data-model.md), [operator MCP](contracts/operator-mcp.md), [assistant MCP](contracts/assistant-mcp.md), [editor and domain coverage](contracts/editor.md), [qualification and release](contracts/qualification.md).
- [Quickstart](quickstart.md) defines the intended product workflow and acceptance sequence. [Windows/WSL handoff](windows-wsl-handoff.md) separates the owner's real-host baseline now from later extension qualification, with exact prompts and evidence requirements.
- [Tasks](tasks.md) deliver setup and authorization/durability foundations, US1–5, US9, then US6–8, coherence and full-platform acceptance, followed by authorized Marketplace publication. P1 milestones are development checkpoints; all domains are required for the full release.

No new credentials, client registrations, installation migrations, services, external communications or Marketplace publication are performed by this planning session. The owner separately authorized committing and pushing these SDD artifacts to continue from Windows/WSL.

### Authority propagation

Each assistant call resolves a server-issued grant from its authenticated credential, never a caller-selected role. Grant, installation, expiry, allowed target/action classes and disclosure limits follow every delegated turn and downstream MCP call. Intersection with the existing runtime/federation policy is mandatory. A runtime adapter without an enforceable grant boundary cannot offer assistant delegation until that adapter is implemented and qualified. Model instructions or a reduced tool list alone are insufficient. Proposal execution is initiated by the human management workflow after independent approval verification, and the originating assistant can only observe its permitted outcome.

### Compatibility and packaging

Management contract major 1 is required; older backends return upgrade guidance and remain untouched. The backend source release must contain this feature's management components, regardless of source version numbering. Handshake checks explicit protocol/capabilities, not only semver. Pin exact supported backend, OS, editor, client and harness versions in release evidence; proposed test fixtures are listed in the qualification contract. A publisher identifier is acquired during release preparation before the first distributable candidate; no placeholder publisher reaches publication.

### Post-design constitution check

No waiver is requested. Contracts require immutable audit, bounded tool methods, inherited denial, real baseline/rollback, independent approval, credential redaction and qualified enforcement. Tasks cover official SDKs, private component catalog/installer documentation, HUD visibility, skill and identity docs, environment examples, regression, a local blog draft and explicitly authorized release. Existing configuration with literal legacy credentials has a reviewed backward-compatible normalization path before the new management path uses it. OS-level confinement against unrestricted same-user shell access is not claimed.

Release remains blocked until the real Windows/WSL gate, Linux/macOS gates, named-client tests and actual Marketplace installation pass. Source149's unfinished Linux/WSL control qualification must be completed on the applicable deployed baseline; it is not inherited from Mac results.

## Complexity Tracking

No constitutional waiver is proposed. Distinct human/assistant surfaces and a durable backend journal are justified by authority and uncertain-outcome requirements. They cannot be replaced with arbitrary terminal execution, agent-readable approval tokens or a full-HUD iframe.
