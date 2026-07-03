---
name: intent-reconcile
description: "Reconcile live network devices to Nautobot intent, with a human approval gate over Discord. Triggered by a Nautobot webhook (device interface change) or by an approval/denial reply. Proposes the exact config diff, waits for `approve <id>`, then applies via the pyats-config-mgmt baseline→apply→verify→rollback workflow. SCOPE: device interface changes on switches only. Never touches firewalls."
version: 1.0.0
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"] } } }
---

# Intent Reconcile (Nautobot → device, human-approved)

Close the loop between Nautobot intent and live device config — **safely**.
A change in Nautobot proposes a device change; a human approves it in Discord;
only then is it applied, with automatic rollback on failure.

## SCOPE GUARD — read first, every time

You may reconcile **only**:

- **Device interface changes on switches** (create / update / delete).

You may **NOT**:

- Touch **firewalls** — ever. Not pfSense, not FMC, not any firewall role.
- Reconcile VLANs, routing, ACLs, or anything that is not an interface (VLAN
  create/update/delete is a *future* phase — decline it for now).
- Apply anything without a matching human `approve <id>`.

If a trigger falls outside this scope, STOP and post one line to the alerts
channel: "Out of scope for intent-reconcile: <what> — no action taken." Then end.

Confirm the target device's role is a switch (via `nautobot-sot`) before doing
anything else. If role is unknown or not a switch, treat as out of scope.

## Two ways this skill runs

1. **Propose** — a Nautobot webhook fired (the alert receiver hands you a
   "NAUTOBOT INTENT CHANGE" prompt). You compute and propose a change.
2. **Approve / Deny** — a human replies in Discord with `approve <id>` or
   `deny <id>`. You look up the stored change and apply or discard it.

## Pending-change store

Records live at `state/pending-changes/<id>.json` (relative to the workspace).
Each record:

```json
{
  "id": "CHG-a1b2c3",
  "created": "2026-07-03T12:00:00Z",
  "status": "pending",              // pending | approved | applied | failed | denied | expired
  "device": "core-sw1",
  "platform": "iosxe",
  "model": "interface",
  "event": "updated",
  "interface": "GigabitEthernet1/0/5",
  "diff": "description: '' -> 'uplink to R2'; mode: access -> trunk",
  "rendered_config": ["interface GigabitEthernet1/0/5", " description uplink to R2", " switchport mode trunk"],
  "nautobot_intent": { },
  "device_before": { }
}
```

Generate `id` as `CHG-` + 6 hex chars. Never reuse an id.

---

## Workflow A — Propose (from a Nautobot webhook)

### 1. Scope check
Confirm: model is `interface`, device role is a switch. Else → out-of-scope note, stop.

### 2. Read both sides — intent vs ACTUAL DEVICE (not the webhook snapshots)

The webhook's prechange/postchange payload is only a **trigger and context**. It
tells you *which* interface to look at — it is NOT the comparison. Do **not**
conclude "no-op" because prechange == postchange; a Nautobot edit to one field
(e.g. description) does not tell you whether the device matches intent on the
*other* fields. Always read the live device and compare full state.

- **Intent** (Nautobot): use `nautobot-sot` to read the interface's intended
  state — `enabled`, `description`, `mode`, `untagged_vlan`, `tagged_vlans`, `mtu`.
- **Reality** (device): use pyATS to read the live interface:
  `pyats_run_command(device="<name>", command="show running-config interface <if>")`
  and `pyats_run_command(device="<name>", command="show interfaces <if>")` (the
  latter shows the real admin/oper state: `administratively down` vs `up`).

### 3. Compute the diff + render config

Diff **Nautobot intent vs the live device** across every attribute below. Any
mismatch is drift, even if the webhook change was unrelated to it.

| Nautobot field | Device config / check | Drift example |
|----------------|-----------------------|---------------|
| `enabled: false` | interface is `shutdown` (admin down) | **Nautobot disabled but port is UP → propose `shutdown`** |
| `enabled: true` | interface is `no shutdown` (admin up) | Nautobot enabled but port shut → propose `no shutdown` |
| `mode: access` | `switchport mode access` | mode differs |
| `untagged_vlan` | `switchport access vlan <vid>` | access VLAN differs |
| `mode: tagged/trunk` | `switchport mode trunk` + allowed VLANs | trunk/allowed differ |
| `mtu` | `mtu <n>` | MTU differs |
| `description` | `description <text>` | text differs (low risk) |

**Admin state is a first-class check.** Explicitly compare `enabled` against the
device's admin state every time. A port that is administratively up while
Nautobot says `enabled: false` (or vice-versa) is drift and MUST be surfaced —
propose the `shutdown` / `no shutdown` to match intent.

A genuine no-op is only valid when **the live device already matches Nautobot
intent on all fields above**. State what you compared (intent vs actual values)
when you report a no-op — do not claim no-op from the webhook snapshots alone.

Render the **exact** platform config you would push (IOS-XE example):

```
interface GigabitEthernet1/0/5
 description uplink to R2
 switchport mode trunk
```

For a **deleted** interface in Nautobot, propose `default interface <if>` /
`no interface <if>` as appropriate — but flag deletes as higher risk.

### 4. Dry-run / validate
Validate syntax without applying (e.g. render + parse, or the device MCP's
dry-run/preview if available). Do NOT apply.

### 5. Store + propose
- Write `state/pending-changes/<id>.json` with status `pending`.
- Post to the Discord alerts channel via the native bridge:

```bash
openclaw message send --channel discord --target <RECONCILE_CHANNEL_ID> --message "$(cat <<'MSG'
🔧 Proposed change CHG-a1b2c3 — core-sw1 / GigabitEthernet1/0/5
Diff: mode access → trunk; description → "uplink to R2"
Config to apply:
  interface GigabitEthernet1/0/5
   description uplink to R2
   switchport mode trunk
Reply `approve CHG-a1b2c3` to apply, or `deny CHG-a1b2c3` to discard.
MSG
)"
```

- Record the proposal in GAIT (`gait-session-tracking`). Then STOP — do not apply.

---

## Workflow B — Approve / Deny (from a Discord reply)

When a message like `approve CHG-a1b2c3` or `deny CHG-a1b2c3` arrives:

### 1. Look up the change
Read `state/pending-changes/<id>.json`. If missing or not `pending`, reply that
the change id is unknown or already actioned, and stop.

### 2. On `deny`
Set status `denied`, post "❌ CHG-... denied — no change made.", record in GAIT, stop.

### 3. On `approve` — apply via pyats-config-mgmt (5-phase)
Re-confirm scope (switch + interface). Then:
1. **Baseline** — capture the current running-config of the interface.
2. **Apply** — push `rendered_config` via pyATS.
3. **Verify** — re-read the interface; confirm it matches intent.
4. **Rollback** — if verification fails, restore the baseline and mark `failed`.
5. Update the record (`applied` or `failed`), record all phases in GAIT.

### 4. Report
Post the outcome to Discord:

```
✅ CHG-a1b2c3 applied to core-sw1 GigabitEthernet1/0/5 — verified.
```
or
```
⚠️ CHG-a1b2c3 FAILED verification on core-sw1 — rolled back to baseline.
```

---

## Workflow C — Daily switch reconciliation (scheduled)

Runs from an OpenClaw cron job (read-only sweep, switches only):

1. Enumerate switch devices from Nautobot (`nautobot-sot`).
2. For each, compare intended interface state vs live (pyATS).
3. Compile a **drift report** — do NOT auto-apply. Post a summary to Discord.
4. For each drift item, you MAY open a proposal (Workflow A) so it flows through
   the same `approve <id>` gate. Never apply drift fixes automatically.

Keep the report concise: device, interface, intent vs actual, one line each.

---

## Non-negotiables

- Firewalls: never.
- No apply without a matching, current `approve <id>`.
- Every apply goes through baseline → verify → rollback.
- Every proposal, approval, apply, and rollback is recorded in GAIT.
- Deletes and trunk/mode changes are higher risk — state that in the proposal.
