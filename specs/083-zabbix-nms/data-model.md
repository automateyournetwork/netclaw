# Data Model — SNMP-poller NMS coverage (spec 083 / R11)

**Date**: 2026-08-03 · Derived from spec.md Key Entities + research.md D5/D6/D7

No database, no NetClaw-authored types. The NMS holds everything. What follows is the model **the skills
must reason with** — and getting it wrong is exactly how the two silent-wrong-answer traps happen.

---

## 1. Collected item — the type that decides everything

| Field | Values | Why it matters |
|---|---|---|
| `value_type` | 0 float · 1 char · 2 log · **3 unsigned** · 4 text · 5 binary | **The API defaults to 3.** Measured: 84 of 121 stock items are 0. Query with the wrong one and you get an empty array and no error |
| `history` | e.g. `31d`, or **`0`** | `0` = raw values are **never stored** |
| `trends` | e.g. `365d`, or **`0`** | `0` = **no hourly aggregates at all** |
| `units`, `key_`, `itemid`, `hostid` | | |

**Three retention states, measured on a stock install (D7):**

| `history` | `trends` | Count | What is answerable |
|---|---|---|---|
| `31d` | `365d` | 106 | recent → raw; older → hourly |
| `31d` | `0` | 10 | **only the last 31d.** Older is *not retained*, not *absent* |
| `0` | `0` | 5 | **nothing.** Collected purely to fire triggers |

The spec originally modelled two windows. There are **three states per window**, and the difference between
"aged out" and "never retained" is a configuration fact the reader needs.

---

## 2. Data absence — five causes, five different answers

This is the model FR-006/FR-006b exist to protect. All five look identical over the wire: an empty array.

| Cause | How to tell | How it must read |
|---|---|---|
| **Wrong value type** | the item's `value_type` ≠ the one queried | never reaches the user — split and re-query |
| **Aged out** | window predates `history`, and `trends` > 0 | *"beyond raw retention; here is the hourly data"* |
| **Retention disabled** | `history=0` and/or `trends=0` | *"this item does not retain that"* — a config fact |
| **Never collected** | item exists, no values ever, `lastclock` empty | *"monitored but has never returned a value"* — a real finding |
| **Genuinely idle** | data exists, values are zero | *"zero throughput"* — the only one that means nothing happened |

---

## 3. Data window

Requested range, **range actually served**, and which source served each part. A query spanning the
retention boundary is served by both and must say so — a peak from raw values and a peak from an hourly
average are different claims.

---

## 4. Problem

`severity` · `host` · `onset` · `duration` · `acknowledged` · `resolved_at`.

`problem.get` returns **current** problems from a dedicated table; `event.get` is the historical, heavier
path. An empty problem list is a legitimate answer and must never read like an unreachable NMS.
Acknowledgement is a workflow fact, never evidence the condition cleared.

---

## 5. Availability observation

`state` · **`observed_at`** · `vantage_point` · `interval`.

Never rendered as "the device is up/down". Always "the NMS could/could not reach it, as of <time>".
A device the NMS does not monitor is a **fourth** state, distinct from unreachable — and the most common
cause of surprise.
