# Verification Report — SNMP-poller NMS coverage (spec 083 / R11)

**Date**: 2026-08-03 · **FR-050, FR-051, FR-052, SC-025**

**NMS tested: Zabbix 7.0.29** (PostgreSQL, official images), stood up for this feature and polling for
~1.5 hours at verification time.

FR-052 requires anything not exercised to be recorded as unverified rather than claimed. Two things below
are, and one of them is a claim my own test was weaker than.

## Two things that make this feature different from 078–082

**1. The core distinctions are enforced by SKILL, not by structure.**

Specs 080, 081 and 082 each moved their guarantee to a chokepoint the caller could not route around. This
one cannot: adopting a generic passthrough unmodified means there is **no NetClaw code in the call path**.
`zabbix-metrics-history`'s procedure is the only thing preventing two silent-wrong-answer failures. An agent
that ignores it will produce a confidently wrong answer and nothing will stop it.

That was a deliberate clarification decision — smallest surface, upstream maintenance — and it is recorded
here, in the skill, in the server README and in `TOOLS.md` rather than assumed away. **The corresponding
"lesson carried forward" in the requirements checklist is left deliberately unticked**, because ticking it
would hide the departure.

**2. No per-call GAIT audit.**

The upstream has no audit concept (`grep -c` → 0 across all six modules) and there is no platform-level MCP
audit — `~/.openclaw/gait/` holds two files, both NetClaw-authored servers. This integration inherits the
posture of every externally-sourced NetClaw integration.

Acceptable **only because it is strictly read-only**: Principle IV bites on actions and configuration
changes, and this performs neither. FR-038c requires that any future write path arrive with per-call audit
*and* both gates, so this cannot quietly become a gap.

## Per-capability status

| Capability | Exercised against live NMS | Notes |
|---|---|---|
| Trap 1 — wrong value type returns empty, no error | ✅ **reproduced** | `zabbix[wcache,values,float]`: correct type → data; API default (3) → **0 rows, no error** |
| Trap 1 scale | ✅ **measured** | **84 of 121** items are float. The default is wrong for the majority |
| Trap 2 — types cannot be mixed | ✅ **reproduced** | 4 items, 2 returned each way, **overlap 0**, union 4 |
| Retention states | ✅ **measured** | Three configurations present: `31d/365d` (106), `31d/0` (10), `0/0` (5) |
| Never-collected ≠ no-data | ✅ | 57 monitored items have never returned a value — distinguishable via `lastclock` |
| Three-way outcome distinction | ✅ **all three** | empty window → success+`[]`; bad token → auth error; dead endpoint → transport failure |
| `problem.get` | ✅ live | 1 active problem in the lab; empty is a success, not an error |
| `trend.get` returns hourly aggregates | ✅ **but thin** | Real rows with `value_min/avg/max/num`. **Only one hourly bucket** (19:00Z) — see below |
| Read-only refusal | ✅ live | `host.delete` refused with `READ_ONLY=true` |
| Deny-list holds with read-only OFF | ✅ live | `READ_ONLY=false host.delete` → *"Blacklist pattern `.*\.delete$` matched"*; `host.get` still allowed |
| Venv isolation | ✅ measured | venv fastmcp **3.4.5**, system **2.14.7**, five `<3` pins still satisfied |
| Manifest ≤ 5,000 tokens | ✅ **589** | Via real MCP handshake; 3-tool surface asserted stable |
| Token/bearer auth | ✅ live | Real `token.create` + `token.generate`, end to end |

**132 assertions across 5 suites, exit 0.**

## Unverified, stated plainly

| Item | Why | What would close it |
|---|---|---|
| **SC-003 — routing an aged-out window to trends** | The lab's raw history retention is **31 days** and it is ~1.5 hours old. **Nothing has aged out**, so the aged-out→trends *routing* was never exercised. What *is* verified is that `trend.get` returns real hourly aggregates. **My own live test asserted the weaker claim** ("hourly trend data is retrievable") and passed — the stronger SC-003 remains unverified, and the test is weaker than the criterion it is filed under | A lab running longer than the history retention, or an item with a deliberately short `history` |
| **SC-004 — a window spanning the retention boundary** | Same cause: no boundary exists yet | Same |
| **Interface counters from network gear** | FRR containers ship **no `snmpd`**, and the FortiGate's SNMP community was not configured. All metric verification used the **Zabbix server's own host** (121 items, 84 float) — real polled data from a real NMS, but **not from network equipment** | `snmpd` in the FRR images, or an SNMP community on the FortiGate |
| **Zabbix 7.2+** | Tested on **7.0.29 LTS** only | A 7.2/7.4 lab |
| **US2 problem lifecycle end-to-end** | A problem exists in the lab and is readable, but a deliberate raise-then-resolve cycle on network gear was not run (same `snmpd` gap) | Pollable gear |

## Corrections to earlier claims in this feature

Both came from research I repeated without verifying, and both are corrected in the spec with the
correction visible rather than silently overwritten.

| Claim | Reality |
|---|---|
| *"The candidate delegates auth to `pyzabbix`, which has a known bug"* | **Wrong.** It uses **`zabbix_utils` 2.0.4** — Zabbix LLC's own library (`client.py:6`). `pyzabbix` is not a dependency. The staleness risk is materially lower than the spec originally claimed |
| *"The in-request auth property was removed in 7.2, so bearer is mandatory"* | **Imprecise.** On **7.0.29 both still work**. Removal lands in 7.2+. Bearer is required for **forward-compatibility**, not because the tested version rejects the alternative |

## Blocking finding caught before it broke anything

The candidate requires **fastmcp 3.x**. **Five NetClaw servers pin `fastmcp<3`** — `netbox-mcp-server`,
`CiscoFMC-MCP-server-community`, `Wikipedia_MCP`, `rag-mcp`, `ISE_MCP`. Installing into the shared
interpreter would have broken all five: spec 076's `cryptography` incident, verbatim.

Found by FR-032's *test before adopting*, which is exactly what that requirement exists for. Resolved with a
**dedicated virtualenv**, the precedent `multivendor-cli-mcp` already set. Isolation is asserted in
`test_venv_isolation.py`, not assumed.

Two related environment notes:

- **`python3 -m venv` fails on this host** — no `ensurepip`. Spec 077's hazard #3, encountered live. The
  installer uses `netclaw_venv_create`/`uv`, and a test asserts no executable line calls bare venv.
- **`netclaw_pip_install` is deliberately NOT used here.** It targets the *system* interpreter — the exact
  thing the venv protects. `reconcile-mcp.py` flagged this correctly; the fix was to name the target
  interpreter explicitly (`uv pip install --python .../.venv/bin/python`), which satisfies the rule's actual
  intent — *packages land in the interpreter the server runs under* — rather than adding an exception.

## Upstream defects found, being reported (FR-034b)

1. **The shipped launcher inverts the safe read-only default.**
   `src/zabbix_mcp_server/utils.py:29` → `True`; `scripts/start_server.py:139` → **`False`**. Running it the
   documented way enables writes. NetClaw forces the flag and adds a deny-list.
2. **`fastmcp>=v3.2.0` is not a valid PEP 440 specifier** — stray `v`. `uv` tolerates it; stricter
   resolvers may not.

Neither is patched locally: the vendored tree is unmodified (SC-024a) and fixes go upstream.

## iN2N (FR-041)

**Not triggered — a decision, not an omission.** This is a read-only observability integration with a single
credential; there is no member specialisation to justify the five member artifacts plus a mesh restart. If a
member is ever given it, `docs/ADDING-AN-MCP.md`'s section applies in full.

## Environment note

The Zabbix lab runs under Docker Desktop's engine, which the default `docker` context on this host does not
list — `docker ps` shows a different daemon's containers while the service answers normally on `:8888`.
Recorded so a future reader does not conclude the lab was fabricated when `docker ps` comes back empty.

## Checks

| Check | Result |
|---|---|
| `bash tests/zabbix/run-tests.sh` (with lab) | ✅ **132 assertions, 5 suites, exit 0** |
| `python3 scripts/reconcile-mcp.py` | ✅ exit 0 — all four surfaces |
| `python3 scripts/verify-inventory-counts.py` | ✅ **212 skills / 156 integrations** |
| `python3 scripts/check-dependency-pins.py` | ✅ exit 0 |
| `trace-skill.py` × 3 | ✅ all resolve |
| `node --check ui/netclaw-visual/server.js` | ✅ |
| `bash -n scripts/lib/{catalog,install-steps}.sh` | ✅ |
| Vendored tree unmodified, `LICENSE` intact | ✅ |
