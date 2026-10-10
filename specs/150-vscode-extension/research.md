# Spec150 technical research

2026-10-10. Source/documentation evidence only. Two planning research agents examined host placement and management interfaces without changing source or runtime state. The owner resolved all three scope decisions, including inspection, delegation and managed-change proposals for external assistants.

## R1 — Workspace extension and mandatory WSL

**Decision**: one desktop workspace extension. Local stdio on macOS/Linux and within Remote SSH/WSL; explicit existing SSH-alias profiles for other supported hosts. Local Windows users managing WSL reopen the chosen distribution. Never guess Windows/Linux path mappings.

**Rationale**: processes, files and credentials then belong to the execution host. WSL server startup does not normally run shell initialization; use a verified absolute launcher and explicit environment. Remote-context type is not a unique authenticated host identity. [Extension host](https://code.visualstudio.com/api/advanced-topics/extension-host), [WSL guidance](https://code.visualstudio.com/docs/remote/wsl), [remote extensions](https://code.visualstudio.com/api/advanced-topics/remote-extensions).

**Alternatives**: a UI-only extension needs remote process/path plumbing; two packages add coordination; browser/container scope was not selected. Real Windows/WSL2 acceptance is mandatory and cannot be simulated by setting a platform string on native Linux.

## R2 — Private MCP and fixed actions

**Decision**: official MCP Node client/server 2.3.1, operator-private stdio and typed domain services. Preserve the HUD's trusted-local boundary. Authentication comes from actual OS/SSH principal and backend grants, not Origin headers or client-supplied names.

**Rationale**: [local access](../../ui/netclaw-visual/src/security/local-access.js) explicitly is not user authentication. Existing [private Hermes MCP](../../mcp-servers/hermes-hud-mcp/server.py) demonstrates separation from agent tool registration. Node can reuse ESM services; Python federation remains isolated.

**Alternatives**: exposing HUD HTTP or relaxing CORS bypasses the boundary; loopback MCP plus tunnel adds token/listener management. No generic shell, endpoint, file-path or MCP-name dispatcher is provided. Stdio stdout must contain protocol messages only. [MCP transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).

## R3 — Durable work independent of editor lifetime

**Decision**: shared backend SQLite admission, operation nonce/body digest, ownership, configuration revisions and locks; existing runtimes own long-running work; reconcile uncertain outcomes without replay.

**Evidence**: installed MCP client2.3.1's stdio close terminates its subprocess after bounded waits. [HUD launcher](../../scripts/hud-launch.mjs) also owns its process groups. Neither may own independent backend-service lifetime. [Federation control](../../scripts/federation-control.py) provides installation/PID/start-time checks; [Hermes ledger](../../mcp-servers/hermes-hud-mcp/ledger.py) supplies durable-admission precedent. Current OpenClaw/Terminal Intent paths need additional persistent ownership and recovery.

**Alternatives**: browser-cookie JSON plus in-memory busy flags do not serialize multiple processes. SSH disconnection is not proof of cancellation. WSL shutdown may interrupt real work and must preserve that uncertainty.

## R4 — Existing-installation management is narrower than existing scripts

**Decision**: reuse reviewed domain methods and implement narrow ownership-checked lifecycle adapters.

**Evidence**: [n2n MCP](../../mcp-servers/n2n-mcp/server.py) supplies federation methods, while [operator policy](../../mcp-servers/protocol-mcp/bgp/federation/operator_policy.py) has limited qualified execution, not broad administration grants. [DefenseClaw enable](../../scripts/defenseclaw-enable.sh) installs software; [secure start](../../scripts/netclaw-secure-start.sh) builds/migrates and contains destructive cleanup; [disable](../../scripts/defenseclaw-disable.sh) kills by process name. These cannot implement the accepted management-only lifecycle scope.

**Alternatives**: a wrapper around those scripts would silently bootstrap or affect unrelated processes. Persisted role, daemon role, restart and verification need one bounded transaction rather than independent UI toggles.

## R5 — Credential source and settings revisions

**Decision**: provider/integration keys remain in the selected `.env`; OpenSSH retains SSH credentials. Editor profiles and journals contain nonsecret references only. Managed fields use typed schemas, optimistic revisions, redacted preview, locked atomic writes and real verification.

**Evidence**: [environment helper](../../ui/netclaw-visual/src/security/private-files.js) preserves unrelated content but needs conflict/transaction controls. [Hermes adapter](../../ui/netclaw-visual/src/hud-server/runtime/hermes.js) accepts an environment override and has a legacy JSON bearer-key fallback. [Gateway adapter](../../ui/netclaw-visual/src/hud-server/chat-runtime.js) accepts environment references and legacy literal config keys. The new path needs reviewed env-reference normalization/shared launcher compatibility rather than duplicating those literals into new storage. Secret replacement input may exist transiently during authenticated transport, never in proposal records or logs.

**Alternatives**: editor SecretStorage is available but does not justify copying backend keys contrary to the repository credential policy. Raw environment editors must not enable executable/path injection through fields such as NODE_OPTIONS/PYTHONPATH.

## R6 — Native navigation and rich views

**Decision**: native explorer/commands/status/output plus bundled Chat/Canvas/Avatar/topology views with typed messages and restrictive CSP. Reuse existing component/data shapes through adapters.

**Evidence**: [Canvas](../../ui/netclaw-visual/src/canvas-chat/App.jsx) persists investigations in browser-specific stores. Use explicit versioned import/export and an extension persistence adapter; never steal browser cookies or assume histories are already shared. [Webviews](https://code.visualstudio.com/api/extension-guides/webview), [Workspace Trust](https://code.visualstudio.com/api/extension-guides/workspace-trust).

**Alternatives**: embedding the entire remote HUD creates framing/authentication/state problems; direct webview requests cannot bypass the current origin guard. Rewriting Canvas risks losing saved work.

## R7 — Named assistant clients and editor floor

**Decision**: use stable VS Code MCP server-definition registration for opt-in Copilot integration and standard stdio configuration for Claude Code/Codex. Adopt planned editor floor `^1.102.0`: MCP provider API became stable in1.101; MCP reached general availability in1.102. Do not rely on the contribution `when` property introduced later; gate discovery/resolution and handlers in code. [VS Code1.101](https://code.visualstudio.com/updates/v1_101), [VS Code1.102](https://code.visualstudio.com/updates/v1_102), [MCP developer guide](https://code.visualstudio.com/api/extension-guides/ai/mcp).

**Evidence**: official Claude Code documentation supports stdio server registration. Codex documentation supports CLI/IDE MCP configuration and stdio command/args; local `codex mcp --help` confirmed external-server management commands. No client registration was changed. [Claude Code MCP](https://code.claude.com/docs/en/mcp), [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

**Rationale**: other assistants can invoke NetClaw tools while retaining their own models; a delegated NetClaw turn still runs on the selected NetClaw harness/provider. These are distinct inference and billing scopes. Core extension use must not require Copilot.

**Alternatives**: the initially researched1.100 editor floor works for the generic MCP SDK but lacks the now-required stable provider integration, so it is superseded. A custom chat participant may be added later but is not required for MCP access from Copilot.

## R8 — Agent-facing authority is a separate contract

**Decision**: external assistants can inspect, delegate and propose managed changes under existing NetClaw authorization and approval rules. No external assistant may receive human approval/credential-management tools or grant itself authority through prompts, origins, labels or method selection. A reduced server-enforced interface, scoped grants, revocation and direct-call denial are required.

**Alternatives**: read-only questions were offered but the owner selected the broader mediated workflow. Registering the human operator interface or allowing a delegated unrestricted conversation would exceed that choice.

**Rationale**: Copilot/Claude/Codex may share an OS UID with the operator. Distinct executable names, tool inventories and client configuration are not hard isolation from unrestricted same-user shell access. Retain independently verified backend/human approvals; qualify real OS/account separation if stronger confinement is claimed. Client-native tool confirmation never stands in for a production CR or NetClaw local-change record.

**Privacy**: explain that tool results can enter the external client's own model provider; use explicit minimal disclosure scope and redaction, never provider credentials or automatic workspace ingestion. Client policy denial is surfaced, not bypassed. Actual named-client tests are required; generic MCP fixtures are insufficient. [VS Code MCP configuration](https://code.visualstudio.com/docs/agent-customization/mcp-servers).

## R9 — Toolchain and publication

**Decision**: TypeScript5.9.3, exact official MCP client/server2.3.1, backend's existing Node policy. Registry reads verified server2.3.1 requires Node>=20 and test-electron3.1.0 requires Node>=22; build/test orchestration uses Node24 independently of editor host. Lock and validate transitive versions during implementation. [Extension testing](https://code.visualstudio.com/api/working-with-extensions/testing-extension).

Marketplace plus matching VSIX remains mandatory, using the mobile PNG. Publisher identity is an owner-supplied release prerequisite; none is assumed registered or available. Record exact client/editor/backend versions and actual public package installation. [Publishing](https://code.visualstudio.com/api/working-with-extensions/publishing-extension), [manifest](https://code.visualstudio.com/api/references/extension-manifest).

No new runtime qualification, publisher access, client account entitlement or live extension operation is established by this research. Existing spec149 Linux/WSL gaps remain release dependencies.
