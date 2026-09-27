# Continuation — HUD 127 and phase 4 upgrade utility

## Confirmed order and scope

User confirmed on 2026-09-27: phase 4 consisted of the README and a common utility that makes upgrading NetClaw to the latest build easy. The README is handled in 126 now. HUD 127 follows; the common upgrade utility remains planned work, with its own implementation spec/number to be assigned. No other phase 4 deliverable is currently identified.

## HUD 127 — function first

Preserve Adam Mason's reusable context/chat canvas and Border chat. Carry forward [Jev 125 HUD handoff](../125-jev-science-officer/hud-handoff.md): detailed Science Officer questions, typed answers, model/evidence age, spending and Border influence, with original/reconsideration comparison. Keep advisors separate from execution members and preserve authenticated session/task boundaries. Missing bindings show unavailable; do not infer them by timestamp. Start 127 by specifying the operator workflows and acceptance criteria before redesigning runtime code.

## Common upgrade utility — proposed implementation plan

Goal: one discoverable command that upgrades an existing NetClaw install to the latest supported build and reports what changed and whether it works.

1. Discover the actual checkout, runtime (OpenClaw/Hermes), selected components, platform (macOS/Linux/WSL), services, config/workspace/env and RISK membership. Show current and target revisions; stop on ambiguous ownership or conflicting local edits.
2. Preview updates and required migrations. Reuse the modular installer and existing migration/adoption helpers rather than cloning their logic. Preserve secrets, identity, certificates, enrollment, custom skills/persona, memory and operator configuration.
3. Create private backups and a resumable migration journal. Fetch a supported target revision, update selected components in their isolated environments, and apply only applicable migrations with conflict detection.
4. Restart only affected services, verify the gateway/MCP/HUD paths and existing member health, then report success or precise failures. Provide scoped recovery from the recorded baseline; never announce success merely because Git updated.
5. Document a single upgrade entry point in README, preview/recovery usage and host-specific limits. Exercise fresh/current/older installs, repeat runs, interrupted upgrades, dirty checkouts, custom paths, missing dependencies, offline failures and rollback conflicts with isolated fixtures; record actual host acceptance separately.

Existing building blocks include scripts/install.sh, scripts/lib/install-steps.sh, scripts/in2n-migrate.py, scripts/migrate-hud-access.py, scripts/migrate-pyats-http.py, scripts/jev-adopt.py and scripts/jev-border-adopt.py. Their exact contracts must be reviewed during the utility's specification. This is a plan, not a shipped command or an upgrade performed on this host.
