# Focused decisions

- Decision: explicit cloud-owner profiles. Source shows `HudClient.endpoint` rejects HTTPS before network; protected cloud exposes owner routes rather than local HUD session/management. Separate modes preserve existing local lifecycle binding. Rejected: widening the loopback parser globally.
- Decision: existing owner HTTPS protocol. Server already enforces exact installation, Origin, CSRF, one-use bootstrap and immutable operation decision. Rejected: general gateway/MCP exposure or weakening TLS.
- Decision: Mobile needs changes. Its edge WebSocket enrollment and legacy Ask/approval cannot use protected HTTP ingress; edge identity does not grant owner authority. Use separate native cloud workflow; retain legacy enrolled flows.
- Decision: secure storage for session, bounded non-secret references for recovery; never repeat ambiguous preparation/decision.
- Evidence status: these are inspected source findings, not live reproduction. Actual editor/native/cloud qualification is separately required. Device availability is a qualification dependency, not a reason to invent acceptance.
