# Hermes HUD baseline observations

Inspected 2026-10-10 at repository baseline `a67aba7369e847ef50fea8542eed919552088d0c`. These are source observations, not results of a live Hermes connection test.

| Area | Observed behavior | Implication for the specification |
|---|---|---|
| Installer runtime selection | [common.sh](../../scripts/lib/common.sh) derives runtime home, configuration, workspace and skills from the selected runtime; Hermes has its own home and configuration. | The HUD should consume the operator's established runtime choice. |
| Installation and registration | [install-steps.sh](../../scripts/lib/install-steps.sh) includes Hermes install/setup and uses [openclaw-to-hermes-mcp.py](../../scripts/openclaw-to-hermes-mcp.py) for component registration. | Existing Hermes installation work must be preserved, not replaced by an OpenClaw requirement. |
| Main HUD configuration | [server.js](../../ui/netclaw-visual/server.js) defines OpenClaw home, environment and JSON configuration paths and uses those for settings and chat. | Changing the displayed runtime name alone cannot fix the connection. |
| Chat submission | `getGatewayConfig` and `/api/chat` in the HUD server read OpenClaw gateway settings and submit OpenClaw-specific agent/session information. | Acceptance must prove the request reaches the selected Hermes agent. No compatible Hermes endpoint is assumed. |
| Models and conversation settings | [chat-runtime.js](../../ui/netclaw-visual/src/hud-server/chat-runtime.js) launches the OpenClaw CLI for model discovery and session changes. | Model and effort controls need runtime-specific capability handling. |
| Conversation history | [chat-history.js](../../ui/netclaw-visual/src/hud-server/chat-history.js) uses OpenClaw session listing and history calls. The server also reads OpenClaw transcript directories. | History and session ownership are part of the integration gap. |
| Runtime settings and navigation | [runtime-settings.js](../../ui/netclaw-visual/src/hud-server/runtime-settings.js) interprets OpenClaw settings; [control-ui.js](../../ui/netclaw-visual/src/hud-server/control-ui.js) describes the OpenClaw native interface. | Hermes must have accurate settings and capability-aware navigation. |
| Logs and usage | [logs.js](../../ui/netclaw-visual/src/hud-server/logs.js), [chat-usage.js](../../ui/netclaw-visual/src/hud-server/chat-usage.js) and the HUD tokenomics route reference OpenClaw logs, CLI calls or transcripts. | A chat-only fix would leave misleading operational panels unless these dependencies are addressed. |
| Published support boundary | [README runtime guidance](../../README.md#agent-runtime--openclaw-or-hermes) describes Hermes installation support and identifies federation as OpenClaw-native. | HUD integration does not establish that all federation functionality is already portable. |

## Evidence limits and planning follow-up

- No live Hermes request, model/provider call, runtime installation, service restart or device configuration change was performed.
- The operator's specific failing deployment, runtime version and error output have not been supplied. Repository inspection nevertheless establishes multiple OpenClaw dependencies in the HUD path.
- Planning must verify the supported Hermes interaction surface, conversation ownership and persistence, tool execution, approval behavior, model controls and available telemetry against the exact target versions.
- Planning must also inventory runtime-dependent HUD and launch paths comprehensively. The table is an initial evidence map, not a claim that it enumerates every dependency.
- Verification must distinguish direct tool availability from discovery and invocation through the selected Hermes agent. Simulated tests and live evidence must be reported separately.
- The startup device-inventory attempt failed on an existing testbed validation error (`connections.defaults` contains unsupported `arguments`). No network state was inferred, and network access is not needed to draft this specification.
