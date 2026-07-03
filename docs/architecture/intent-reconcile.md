# Intent Reconcile — Nautobot → Device, With a Human Gate

## TL;DR

When you change a device interface in Nautobot, a webhook tells NetClaw. NetClaw
computes the exact config diff, posts a **proposal** to Discord, and waits. Only
after you reply `approve <id>` does it push the change — through a
baseline → apply → verify → rollback workflow. A separate daily job reports
drift between Nautobot intent and live switches (read-only).

**Scope (today): device interface changes on switches only. Firewalls never.
VLAN create/update/delete is a planned next phase.**

> **Setting it up?** See the step-by-step runbook (config, webhook creation, SSH,
> testing, troubleshooting): `docs/runbooks/intent-reconcile-webhook-setup.md`.

- Receiver endpoint: `scripts/alert-receiver/server.py` → `/nautobot-webhook`
- Skill: `workspace/skills/intent-reconcile/SKILL.md`
- Gateway hook mapping: `reconcile` (in `openclaw.json`)
- Daily job: `daily-switch-reconcile` (OpenClaw cron, disabled by default)

## Why a human gate

This is the highest-blast-radius automation in NetClaw. A bad edit in Nautobot
could otherwise reconfigure a live switch with no human in the loop. So the
webhook only ever **proposes**; nothing touches a device without an explicit
Discord approval, and every apply is reversible (auto-rollback on failed verify).
Firewalls are excluded entirely — the lockout risk isn't worth it.

## The flow

```
Nautobot (edit an interface)
   │  Webhook — HMAC-SHA512 signed (X-Hook-Signature), fires for ALL interface changes
   ▼
Receiver /nautobot-webhook   (192.168.3.252:8099)
   │  1. verify signature
   │  2. gate: model == interface  AND  device role == switch
   │  3. build a reconcile proposal prompt
   │  POST /hooks/reconcile
   ▼
Gateway hook "reconcile"  →  wakes the agent (fresh session)
   ▼
intent-reconcile skill — Workflow A (propose):
   read intent (nautobot-sot) + live state (pyATS) → diff → render config →
   dry-run → store state/pending-changes/<id>.json → post proposal to Discord
   … waits …
You reply "approve CHG-1234" in Discord
   ▼
intent-reconcile skill — Workflow B (apply):
   look up the change → pyats-config-mgmt: baseline → apply → verify → rollback
   → post the result to Discord
```

The webhook can fire for *every* interface change in Nautobot — that's fine. The
**receiver and the skill are the gate**: the receiver drops anything that isn't
an interface change on a switch, and the skill re-checks scope before doing
anything.

## Why the pending-change store exists

Your `approve <id>` reply arrives as a *fresh* inbound Discord message, in a
different session from the one that made the proposal. So the proposal is
persisted to `state/pending-changes/<id>.json` (device, rendered config, diff,
intent, baseline). The skill handles both halves — "propose and store" on the
webhook, "look up and apply" on the approval — and that file is what bridges the
two sessions.

## Security

- **HMAC-SHA512 signature.** Nautobot signs the raw body with a shared secret and
  sends `X-Hook-Signature`. The receiver recomputes it with a timing-safe
  compare and rejects anything unsigned or mismatched. No secret configured →
  reject (fail closed).
- **Scope gating in two places.** The receiver gates on model + device role; the
  skill re-checks (switch + interface) before any read or write.
- **No blind apply.** Nothing is applied without a matching, current
  `approve <id>`. Deletes and trunk/mode changes are flagged as higher risk in
  the proposal.
- **Reversible.** Every apply captures a baseline and auto-rolls-back on failed
  verification. Every step is recorded in GAIT.

## Daily switch reconciliation

`daily-switch-reconcile` (OpenClaw cron, created **disabled**) runs Workflow C:
enumerate switch-role devices, compare intended vs live interface state, and post
a concise **drift report** to Discord. It is read-only — it never auto-applies.
For each drift item it may open a proposal so the fix flows through the same
`approve <id>` gate.

Enable when ready: `openclaw cron enable daily-switch-reconcile`.

## Configuration

`scripts/alert-receiver/.env` (all off by default):

```dotenv
RECONCILE_ENABLED=false
NAUTOBOT_WEBHOOK_SECRET=            # must match the Nautobot webhook "Secret"
RECONCILE_ALLOWED_MODELS=interface
RECONCILE_ALLOWED_ROLES=switch
RECONCILE_CHANNEL_ID=1426234100339048701
```

### Nautobot webhook to create

- Content type: `dcim | interface`
- Events: Created, Updated, Deleted
- URL: `http://192.168.3.252:8099/nautobot-webhook`
- HTTP method: POST
- Secret: (a strong secret; set the same value in `NAUTOBOT_WEBHOOK_SECRET`)

Then set `RECONCILE_ENABLED=true` and restart the receiver.

## Verified vs not

- **Verified:** HMAC accept/reject, empty-signature reject, model gating,
  device-role gating (switch allowed, firewall blocked), proposal-prompt scope
  guard, endpoint returns `disabled` until enabled, hook mapping + skill present.
- **Not yet exercised live** (needs a real switch + enabling): the full
  `approve → apply → verify` cycle against a device, and the Discord-reply →
  agent matching. The plumbing is proven; the device write path runs only when
  you enable it and a real change flows through. Test on one non-production
  interface first.

## Files

| Path | Role |
|------|------|
| `scripts/alert-receiver/server.py` | `/nautobot-webhook` endpoint, signature + gating |
| `workspace/skills/intent-reconcile/SKILL.md` | propose / approve / apply / daily drift |
| `openclaw.json` → `hooks.mappings[reconcile]` | wakes the agent (runtime config) |
| OpenClaw cron `daily-switch-reconcile` | daily drift report (runtime, disabled) |
| `state/pending-changes/<id>.json` | pending-change records (runtime) |
