# R15 — Multi-user foundation

- **Roadmap item:** 8 — multi-user
- **Depends on:** R14 (and R02's principal model)
- **Gate:** human review; feature flag stays off in releases until R17

## Specify input

Many engineers use one NetClaw service through any Border, each with a
server-side identity. Each user has private, persistent conversations (several at
once) that resume across browsers and devices. The service and agent
configuration are shared; each user's runtime state is isolated: agent sessions,
working files, uploads, Canvas network terminals, and background tasks. OpenClaw
states that shared-agent session ownership is not a security boundary, so NetClaw
enforces isolation itself. Every HTTP, WebSocket and streaming endpoint
authorizes on the server-side principal; nothing relies on browser storage or a
client-supplied session ID for isolation.

Authorization and audit start here, not later. Until R17, only the owner or an
administrator can approve protected execution; other users can chat and read.
Access to a Border never implies administrator rights. Every action is attributed
to its principal in GAIT. Authentication goes through a pluggable authenticator
interface; this feature ships the existing owner binding and a test-only provider,
and R16 adds real identity providers.

User stories:
- P1: Engineer A investigates an ISE issue while Engineer B investigates an ASA
  issue on the same agent, concurrently, with no interference.
- P1: A user resumes yesterday's conversation from another device and another
  Border.
- P1: One user cannot read, attach to or influence another user's conversations,
  terminals, files or background results by any path.
- P2: Existing single-user installs upgrade with the owner's history intact.

## Clarify: decisions (recommended default first)

1. Isolation under OpenClaw: per-user agent session namespace, per-user workspace
   directory and per-user sandbox for exec and terminals; shared configuration is
   read-only. Research OpenClaw's current session and trust model first. [research]
2. Hermes runtime: single-user only; multi-user recorded as unqualified. [HUMAN]
3. User data placement across nine Borders: a user data store (not etcd) with a
   home region per user; any Border serves the user from it; data residency is a
   setting. [HUMAN]
4. Bootstrap authentication before R16: the owned-HUD binding becomes the owner
   principal; additional users only through a test OIDC provider in development.
   No local passwords as a product feature.
5. Per-principal budgets and concurrency limits.
6. Migration: the owner's existing history becomes the owner principal's history.

## Plan notes

- The HUD's owned-session cookie lives in `ui/netclaw-visual/src/hud-server/bindings.js`;
  the gateway uses one bearer token for `/v1`. That shared token must never become
  the user isolation key.
- Related specs: 130 (chat interface), 131 (Canvas network terminals), 139 (chat
  history picker), 140 (HUD chat workflows); `bgp/federation/gateway_ws.py`.
- Isolation tests belong in CI from this feature onward.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Concurrency | ISE/ASA scenario run concurrently with correct, separate results |
| Direct access | Guessed or swapped conversation, terminal, file and task IDs refused |
| Transport | WebSocket and streaming connections without a valid session refused |
| Leakage | Canary secret planted in A's conversation cannot be elicited by B through prompts, tools or memory |
| Background | Task results route only to the initiating principal |
| Authority | Non-owner principals cannot approve protected execution |
| Audit | GAIT shows the principal on every action |
| Mesh | Same user, same history through Borders in different providers |
| Compatibility | Single-user mode unchanged with the flag off |
