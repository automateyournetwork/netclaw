# Verification Report — Fortinet Coverage (spec 080 / R3)

**Date**: 2026-08-01 · **FR-035 / FR-036 / SC-016**

FR-036 requires that anything not exercised is recorded as **unverified** rather
than claimed. This is spec 078's precedent, where four of five Cisco API families
were dropped after returning 403 rather than shipped as coverage that had never
run.

## The lab

| | |
|---|---|
| Device | FortiGate-VM64-HV, Hyper-V, `192.168.2.130` |
| Serial | `FGVMEVS9GWUAOMBD` |
| Firmware | **FortiOS 7.6.7** build 3704 (GA.M) |
| Licence | **Valid**, evaluation — 1 vCPU / 2048 MB / 3 interfaces / 3 routes / 3 policies |
| Auth | Read-only `api-user` (`netclawapi`), profile `netclaw_ro`, trusthost `/32` |
| FortiManager | ❌ not deployed |
| FortiAnalyzer | ❌ not deployed |

## Per-capability status

### Device plane — LIVE-VERIFIED

| Capability | Status | Evidence |
|---|---|---|
| `fgt_system_status` | ✅ live | 200; hostname/serial/version returned |
| `fgt_list_interfaces` | ✅ live | 200; 2 interfaces. **Extended 2026-08-03** to report `admin_status` (config) separately from `link` (carrier) — the conflation NetClaw reported itself |
| `fgt_get_routes` | ✅ live | 200; 2 routes (static default + connected) |
| `fgt_get_policies` | ✅ live | 200; `empty_result` on an empty ruleset |
| `fgt_vpn_tunnels` | ⚠️ **partial** | Endpoint verified 200; **no tunnel configured**, so only the empty path ran |
| `fgt_compare_with_manager` | ❌ **unverified** | Needs FortiManager |
| Plane/scope on every response | ✅ live | Asserted across all 5 live calls |
| GAIT audit emission | ✅ live | 5 records written during the live run |
| Empty ≠ error | ✅ live | `empty_result` distinguished from `plane_unreachable` |

**FR-016 caveat, and an attempt that failed instructively (2026-08-03):** phase 1 /
phase 2 separation is **implemented and unit-tested, but cannot be exercised on an
evaluation-licensed FortiGate.**

Defining a phase1-interface with an unreachable peer — intended to produce a real
populated tunnel structure with phase 1 down — **wedged the REST API**. `httpsd`
stopped answering (HTTP 000) while SSH, ping and `get system status` all stayed
healthy, so the damage was invisible from the CLI. The eval licence caps the unit at
3 interfaces and an IPsec tunnel creates a virtual one; the API did not recover
until the phase1 was deleted, at which point it returned 200 immediately.

**Conclusion: this is not verifiable on the eval tier**, and the attempt is
recorded so nobody repeats it. Coverage is instead provided by
`tests/fortinet/test_device_plane.py`, which proves phase-1-up/phase-2-down is
representable, that per-selector detail survives, and that no collapsed `status`
field exists. The populated *field mapping* remains coded from the FortiOS layout
rather than observed — genuinely unverified, and stated as such.

### Manager plane — NOT VERIFIED

All 8 tools implemented against the documented FortiManager JSON-RPC surface.
**No FortiManager was deployed**, so none has been exercised.

`fmg_list_adoms` · `fmg_list_devices` · `fmg_list_policy_packages` ·
`fmg_get_policy_package` · `fmg_search_rules` · `fmg_resolve_object` ·
`fmg_get_revisions` · `fmg_preview_install` — **all unverified.**

### Analyzer plane — NOT VERIFIED

All 4 tools implemented. **No FortiAnalyzer was deployed.**

`faz_query_logs` · `faz_fetch_more` · `faz_policy_activity` · `faz_list_devices` —
**all unverified.**

### Write path — LOGIC VERIFIED, EXECUTION NOT

| Capability | Status |
|---|---|
| Read-only default refuses writes | ✅ unit-tested |
| Three distinct refusal outcomes | ✅ unit-tested |
| Approval and CR are independent | ✅ unit-tested |
| `is_lab` waives CR only, never approval | ✅ unit-tested |
| Real ServiceNow CR lookup | ❌ unverified — no ServiceNow configured |
| An actual package install | ❌ **never executed** |

### Appliance-free guarantees — VERIFIED

| Capability | Status |
|---|---|
| Envelope contract suite | ✅ pass |
| GAIT audit suite (incl. refusals) | ✅ pass |
| Credential suite (no value in any output) | ✅ pass |
| Manifest ≤ 5,000 tokens | ✅ **2,486** measured |
| `reconcile-mcp.py` all four surfaces | ✅ exit 0 |

## Summary

| Plane | Implemented | Live-verified |
|---|---|---|
| Device | 6 tools | **5 fully, 1 partial, 1 needs manager** |
| Manager | 8 tools | 0 |
| Analyzer | 4 tools | 0 |
| Write/posture | 3 tools | logic only |

**8 of 21 tools have touched a real appliance.** The rest are implemented, typed,
and structurally guaranteed by the envelope, but unexercised — and this document
exists so nobody mistakes the second group for the first.

## What would close the gaps

1. **FortiManager-VM** (15-day trial, separate entitlement) → 8 manager tools plus
   `fgt_compare_with_manager`, the P1 story.
2. **FortiAnalyzer-VM** (15-day trial, 6 GB/day) → 4 analyzer tools.
3. ~~One IPsec tunnel on the FortiGate~~ — **not possible on the eval tier.** Attempted 2026-08-03 and it
   wedged the REST API (see the FR-016 note above). Needs a licensed unit with headroom above the
   3-interface cap, or a second FortiGate to peer with.
4. **A ServiceNow instance** → the real CR lookup in gate 2.

## The bug the tests could not have caught

**Every contract test passed while `fgt_system_status` returned `null` for serial, version and build.**

FortiOS splits its response across two levels:

```jsonc
{ "results": { "hostname": "...", "model_name": "..." },   // <- what get() returns
  "serial": "...", "version": "v7.6.7", "build": 3704 }     // <- TOP LEVEL
```

The client returned only `results`, so three of the most useful fields read as absent. The tests could
not see it: they assert on the **envelope** — that `plane` and `scope` are present and correct — not on
whether `data` is populated. The envelope was flawless. The payload was half empty.

It surfaced only when a real agent ran the tool end to end from Slack and reported the nulls. Worse, the
member then *inferred* eval licensing from circumstantial evidence (2 interfaces, 2 routes, 0 policies
against eval caps of 3). That inference happened to be right, which is the dangerous kind of wrong.

Fixed by adding `get_envelope()` alongside `get()`, and — because the same investigation showed licence
status and uptime are genuinely CLI-only — `fgt_system_status` now states plainly that neither is
available over REST rather than omitting them and inviting inference. The live session count, CPU and
memory were added at the same time from `monitor/system/resource/usage`, which a test run had reported as
needing raw CLI. It did not.

**The lesson, recorded because it generalises:** structural guarantees are testable without an appliance
and were worth building that way. *Field population is not.* An end-to-end run against a real device
remains irreplaceable, and this feature had 24 passing appliance-free tests while shipping a tool that
returned three nulls.

## Findings worth keeping

- **An unregistered FortiGate blocks the entire management plane.** Every REST
  request returns 401 regardless of token validity, admin profile, or trusthost —
  proven by widening the trusthost to `0.0.0.0/0` and by packet-capturing the source
  address. The GUI login-loops for the same reason. The *only* variable that changed
  behaviour was `License Status: Invalid → Valid`.
- **`monitor/system/interface` returns a dict keyed by interface name**, not a list.
  Most third-party examples have this wrong.
- **FortiOS 8.0.0 GA has a web-GUI logout loop** on the 1 vCPU trial profile
  (`VM resource exceeds license limit` → `httpsd` restarts). SSH and REST unaffected.
  7.4/7.6 do not exhibit it. This cost most of a day before it was identified.
- **A FortiGate VM licence is bound to a serial and the unit adopts it on apply.**
  Applying a licence issued for a different serial does not fail cleanly — it sets
  the unit to `FGVM00UNLICENSED` and destroys the working evaluation licence. Three
  VMs were lost to this before it was understood.
