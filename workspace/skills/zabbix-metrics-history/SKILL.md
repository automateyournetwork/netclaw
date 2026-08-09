---
name: zabbix-metrics-history
description: "Retrieve polled metric history from Zabbix — interface utilization, counters and any collected item — over any time window, correctly routed between raw history and hourly trends. Use when someone asks what something WAS doing over time: is this normal, what did this interface do overnight, was it like this last Tuesday. This is the only NetClaw skill that can answer a question about the past from a poller."
version: 1.0.0
license: Apache-2.0
tags: [zabbix, nms, snmp, monitoring, history, trends, utilization, baseline, observability]
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["ZABBIX_URL", "ZABBIX_TOKEN"] } } }
---

# Zabbix Metrics History

## Server

`zabbix-mcp` — **vendored third-party** (`mpeirone/zabbix-mcp-server`, GPL-3.0, pinned `0722f48`), running
from its own virtualenv. Three tools: `zabbix_api(method, params)`, `zabbix_api_docs(method)`,
`zabbix_api_list(object)`. **Read-only, enforced two ways** (forced flag + destructive-method deny-list).

## ⚠ Read this before you report "no data"

**This server is a generic passthrough. It will not stop you getting a wrong answer.**

Unlike most NetClaw integrations, there is no code between you and the API enforcing correctness. Zabbix has
two traps that return **an empty array and a success status** — no error, no warning. If you skip the
procedure below you will confidently tell an engineer an interface was idle when it was carrying traffic.

Follow the procedure. It is the only safeguard that exists.

---

## The procedure — always, in this order

### Step 1 — `item.get` FIRST. Never call `history.get` without it.

```jsonc
zabbix_api("item.get", {
  "hostids": ["<hostid>"],
  "search": {"key_": "net.if.in"},          // or whatever you're after
  "output": ["itemid","name","key_","value_type","units","history","trends"]
})
```

You need four fields off every item:

| Field | Why |
|---|---|
| `value_type` | **Step 2 depends on it.** Getting it wrong returns empty, silently |
| `history` | how far back raw values exist — or `0`, meaning never stored |
| `trends` | how far back hourly aggregates exist — or `0`, meaning none |
| `units` | so your answer has units |

### Step 2 — pass the item's real `value_type`. Do not accept the default.

**`history.get` defaults `history` to `3` (numeric unsigned). Measured on a stock Zabbix 7.0: 84 of 121
items are `0` (float).** So the default is wrong for most items, and wrong silently.

| `value_type` | Meaning |
|---|---|
| **0** | float ← **most interface counters and rates** |
| 1 | character |
| 2 | log |
| **3** | unsigned ← **the API default** |
| 4 | text |
| 5 | binary |

```jsonc
zabbix_api("history.get", {
  "itemids": ["<itemid>"],
  "history": 0,                    // ← the item's OWN value_type, not the default
  "time_from": <epoch>, "time_till": <epoch>,
  "output": "extend", "sortfield": "clock", "sortorder": "DESC", "limit": 500
})
```

### Step 3 — never mix value types in one call.

A single `history.get` serves **one** value type. Query four items of mixed types and you get back only the
matching ones — **the rest vanish with no error**. Measured: 2 of 4 returned each way, zero overlap.

**Group your items by `value_type`, make one call per group, merge the results.**

### Step 4 — route between history and trends by the window.

Raw history is short-lived; hourly aggregates last far longer. `item.get` told you both in Step 1.

| Requested window | Use | Say in your answer |
|---|---|---|
| entirely within `history` | `history.get` | raw polled values |
| entirely beyond `history`, `trends` > 0 | `trend.get` | **hourly min/avg/max, not instantaneous** |
| spans the boundary | **both**, merged | which part came from which |
| beyond both | neither exists | *not retained* — see below |

`trend.get` returns `value_min` / `value_avg` / `value_max` / `num` per hour, and is **numeric only**.

**Say when you used trends.** "The peak was 400 Mbps" from raw values and from an hourly average are
different claims, and an engineer sizing a link needs to know which they have.

---

## The five reasons you get nothing back

They are indistinguishable over the wire — all five are an empty array. Tell them apart, and word them
differently.

| Cause | How to tell | How to say it |
|---|---|---|
| **Wrong value type** | you didn't do Step 1/2 | **Never report this.** Re-query correctly |
| **Aged out** | window predates `history`, `trends` > 0 | *"beyond raw retention — here is the hourly data"* |
| **Retention disabled** | `history=0` and/or `trends=0` on the item | *"this item does not retain that"* — a **configuration fact**, not an absence |
| **Never collected** | item exists, no values ever, empty `lastclock` | *"monitored but has never returned a value"* — **a real finding**, usually a broken poll |
| **Genuinely idle** | data exists and the values are zero | *"zero throughput"* — the only one that means nothing happened |

**Retention can be switched off per item.** Measured on a stock install: 10 items had `trends=0`, and 5 had
both `history=0` and `trends=0` — collected purely to fire triggers, never stored. Read the item; do not
guess.

---

## Every answer must carry

- **The source** — Zabbix, and which host/item.
- **The window actually served**, which may differ from the one requested (say so if it does).
- **Whether the values are raw or hourly aggregates.**
- **The item's units.**
- **Zabbix's own clock** where relevant — if a "last 5 minutes" query looks empty, clock skew between you
  and the NMS is a likely cause, and surfacing the NMS time makes that diagnosable instead of baffling.
- **Unambiguous timezones.**
- **The bound**, if you limited the result, plus how to narrow the query.

Refuse a future window or a reversed start/end with the reason — do not return empty.

If the same item key exists on multiple hosts, **never merge them into one series** without saying so.

---

## Boundaries — which skill owns what

| Want to… | Use |
|---|---|
| Receive unsolicited traps | `snmptrap-mcp` — that is **push**; this **polls** on an interval and keeps history |
| Flow records | `ipfix-mcp` — flows, not counters |
| Metrics from infrastructure you instrumented | `prometheus`, `grafana` — pull-based stores; this is the NMS for gear you did not instrument |
| SaaS monitoring with its own agents | `auvik`, `thousandeyes`, `datadog` — this is the self-hosted NMS an enterprise already runs |
| **Current** device state | `pyats`, `multivendor-cli`, `fortinet` — they read the device now; **this answers what it was over time**, and can answer for a device that is unreachable right now |
| Problems and alerts | `zabbix-problem-review` |
| Availability and inventory | `zabbix-availability` |

## Rules

1. **`item.get` before `history.get`. Always.** There is no shortcut and nothing will catch you.
2. **Never report "no data" without identifying which of the five causes it is.**
3. **Say when an answer came from hourly aggregates.**
4. **This integration is read-only.** There is no write path; do not attempt one.
5. **No per-call audit trail exists** for this integration. Say so if someone needs an auditable record.
