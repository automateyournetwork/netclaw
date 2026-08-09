# Phase 1 Data Model — Arista ANTA validation (R25)

**Date**: 2026-08-05 | **Plan**: [plan.md](plan.md)

Nothing is persisted. These entities exist only within a call, and are modelled because the
distinctions between them are the feature.

---

## Entity: Verdict

The load-bearing entity. ANTA's own enum has five values; NetClaw maps them to **five reported
outcomes**, splitting one of ANTA's.

| NetClaw outcome | From ANTA | Means | Must never be counted as |
|---|---|---|---|
| `pass` | `success` | tested, and the expectation held | — |
| `fail` | `failure` | tested, and the expectation did not hold | — |
| **`not_applicable`** | **`failure`** *(reclassified)* | the feature is not configured or the command is unsupported — **nothing was tested** | `fail` |
| `skipped` | `skipped` | ANTA declined to run it | `pass` |
| `error` | `error` | the device could not be reached or the run broke | `fail` |

### The reclassification is the point

Measured on the lab device: `VerifyBGPPeerCount` returns **`failure`** with the message
*"'show bgp summary vrf all' failed on veos1: BGP inactive"*. BGP is not configured. The honest
answer is *not applicable*, not *failing*.

Counting that as a failure reports a BGP problem on a device with **no BGP at all** — an absence
rendered as a finding, the same class as R13's inert Suricata and R12's capped count.

**Detection**: an ANTA `failure` whose message indicates an inactive feature or an unsupported
command (e.g. *"failed on … : … inactive"*, *"Invalid input"*, *"not supported"*) is reclassified to
`not_applicable`. Uncertain cases stay `fail` — **the reclassification must never hide a real
failure**, so the rule is deliberately narrow and the original message is always preserved.

---

## Entity: Test result

One test against one device.

| Field | Notes |
|---|---|
| `test` | catalogue name, e.g. `VerifyEOSVersion` |
| `category` | e.g. `routing.bgp` |
| `device` | which device answered (FR-012) |
| `verdict` | one of the five above |
| `observed` / `expected` | populated on `fail` — ANTA supplies both natively |
| `messages` | ANTA's own text, **never discarded**, including for reclassified results |

---

## Entity: Run summary

| Field | Rule |
|---|---|
| `passed`, `failed`, `not_applicable`, `skipped`, `errored` | **five separate counts** — no merging (FR-004) |
| `total` | sum of all five |
| `device` | who answered |
| `observed_at` | when (FR-012) |
| `tls_verified` | whether certificate verification was on — disclosed always, never silent (spec 094 discipline) |

**Forbidden**: a single "health percentage". `passed / total` is meaningless when `not_applicable`
and `skipped` are in the denominator — 40 tests of which 30 are not applicable is not "25% healthy".
`summary.emit()` raises if asked to produce one.

---

## Entity: Catalogue entry

Discovery data, available **without contacting a device** (FR-008).

| Field | Notes |
|---|---|
| `name`, `category`, `description` | from the test class |
| `inputs` | the input schema, so an operator can see what a test requires before running it (FR-007) |

208 entries across 33 modules — enumerated at import, never exposed as individual tools.

---

## Validation rules

1. No summary merges the five outcomes (FR-004).
2. An unreachable device yields `error` for that device and no test failures (FR-005).
3. An empty selection reports "no tests selected", never an all-pass run (FR-006).
4. A test missing required inputs reports what is required (FR-007).
5. No credential appears in any field (FR-009).
6. Every result carries device and timestamp (FR-012).
