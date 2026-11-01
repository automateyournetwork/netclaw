# Research

Baseline: branch from 164-convergence-border at 2d930087 plus uncommitted spec164
ledger. npm on 2026-10-31: newest stable openclaw 2026.10.9 (2026-10-29); newest
beta 2026.10.10-beta.5 changelog has no namespace-identity change.
Source `dist/gateway-state-owner-*.mjs` (2026.10.9): readGatewayLockProcessNamespace
stats /proc/self/ns/pid; on failure identity is null and a fresh holder classifies
"unknown" -> GatewayLockNamespaceError. VM probe (systemd 255): user unit + PrivateTmp,
ProtectSystem=strict or ProtectHome -> EACCES (PrivateUsers=no does not help;
self/identity unsupported); NoNewPrivileges/RestrictSUIDSGID/LockPersonality -> ok;
system unit User=ubuntu + PrivateTmp + ProtectSystem=strict + InaccessiblePaths -> ok.
OpenClaw docs: sandbox mode/workspaceAccess/network, tools.sandbox.tools.alsoAllow
bundle-mcp, tools.elevated.enabled, skills.workshop.autonomous.mode off|auto.
