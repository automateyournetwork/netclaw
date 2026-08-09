# Phase 0 Research — SNMP-poller NMS coverage (spec 083 / roadmap R11)

**Date**: 2026-08-03 · **Branch**: `083-zabbix-nms`

Everything below was **measured against a live Zabbix 7.0.29** stood up for this purpose and polling real
data, and against the adoption candidate actually installed and run. Where a measurement contradicts the
spec or the prior research, the contradiction is stated rather than smoothed over — and **three do**.

---

## D1 — The lab, stood up and used

```
zabbix/zabbix-server-pgsql:alpine-7.0-latest + postgres:16-alpine + zabbix-web-nginx-pgsql
→ apiinfo.version: 7.0.29 · web on :8888 · healthy in ~40s
```

Port 8080 was already allocated on this host, so the lab uses **8888**. Worth recording: the quickstart must
not assume 8080 is free.

Auth: a real API token created via `token.create` + `token.generate`, verified end to end.

---

## D2 — BLOCKING: the candidate requires `fastmcp` 3.x, and five servers pin `<3`

**Measured.** `mpeirone/zabbix-mcp-server` declares:

```toml
dependencies = ["fastmcp>=v3.2.0", "zabbix_utils>=2.0.4", "python-dotenv>=1.2.2",
                "bs4>=0.0.2", "requests>=2.33.1"]
```

Installed in an isolated venv it resolves **fastmcp 3.4.5** and **mcp 1.29.0**. The system interpreter has
**fastmcp 2.14.7**.

**Five servers in this repo pin `fastmcp<3`:**

```
netbox-mcp-server · CiscoFMC-MCP-server-community · Wikipedia_MCP · rag-mcp · ISE_MCP
```

`rag-mcp`'s bound was added *by the previous feature* (spec 082). Installing this candidate into the shared
interpreter would force 2.14.7 → 3.4.5 and break all five declared constraints. **That is FR-037 and spec
076's `cryptography` incident, exactly.**

**Decision: a dedicated virtualenv**, following the precedent this repo already set —
`multivendor-cli-mcp` (spec 076) runs from its own venv because napalm/netmiko resolve cryptography 49.x
while NCFED's X.509 stack needs 46.x. Same shape, same fix.

**Verified working**: installed into a venv, the server starts, completes an MCP handshake, and answers
against live Zabbix. Zero conflicts with the system interpreter.

Note the upstream specifier `fastmcp>=v3.2.0` carries a stray `v` and is not valid PEP 440. `uv` tolerates
it; stricter resolvers may not. Recorded as an upstream defect (see D12).

---

## D3 — CORRECTION: it does **not** use `pyzabbix`

The spec's FR-032 says the candidate *"delegates authentication to a library with a known bug against
exactly the version this targets (pyzabbix#226)."*

**That is wrong, and it came from prior research I repeated without verifying.** Measured:

```
src/zabbix_mcp_server/client.py:6 →  from zabbix_utils import ZabbixAPI
```

It uses **`zabbix_utils` 2.0.4 — Zabbix LLC's own official Python library**, not the third-party `pyzabbix`.
`pyzabbix` is not installed and is not a dependency.

**Consequence**: the staleness risk is materially lower than the spec claims. FR-032's *requirement* (test
before adopting) stands and has been satisfied; its stated *rationale* must be corrected.

---

## D4 — CORRECTION: in-body `auth` still works on 7.0

The spec says the in-request credential property was *"deprecated in 6.4 and removed in 7.2"*, and treats
this as a reason Bearer auth is mandatory. Measured on **7.0.29**:

| Auth style | Result |
|---|---|
| In-body `"auth": <session>` | **WORKS** |
| `Authorization: Bearer <token>` | **WORKS** |

Removal lands in **7.2+**; 7.0 is LTS and still accepts both. So Bearer is required for
**forward-compatibility**, not because 7.0 rejects the alternative. The requirement is unchanged; the
justification needs precision, and the verification report must state **which version was tested**.

---

## D5 — Trap 1 confirmed, on real data

The flagship claim, measured against a real float item that genuinely has values:

```
item: zabbix[wcache,values,float]   value_type=0 (float)   history=31d trends=365d

  history.get with value_type=0  (correct)  →  1 point,  value 0.6826832627489122
  history.get with value_type=3  (default)  →  0 points, NO ERROR
```

**Value-type distribution on a stock install: 84 of 121 items are float (value_type=0).** The API default is
`3`. So the naive call is wrong for the **majority** of items, and it fails silently.

This is the single most important finding in this research, and it is not theoretical.

---

## D6 — Trap 2 confirmed: types cannot be mixed

Four items — two float, two unsigned — **all verified to have data first**, then queried together:

```
one call, history=0  →   4 rows from 2 of 4 items
one call, history=3  →   6 rows from 2 of 4 items
union 4 of 4 · overlap 0
```

No single call returns all four, and **each half silently omits the other's items with no error**. A
mixed-type query must be split per type and the results merged.

*Method note*: the first attempt at this test picked items with no recent data and returned 0/0 — which
would have "confirmed" the trap for entirely the wrong reason. It was rerun against items proven to have
values. An inconclusive test that happens to agree with the hypothesis is worse than no test.

---

## D7 — NEW: a third retention case the spec missed

The spec models retention as "history window vs trends window". Measured, a stock install has **three**
configurations:

| `history` | `trends` | Items | Meaning |
|---|---|---|---|
| `31d` | `365d` | 106 | the normal case the spec describes |
| `31d` | **`0`** | 10 | **no aggregates at all** — the history window is the only answerable range |
| **`0`** | **`0`** | 5 | **nothing is retained** — the item is collected purely to fire triggers |

So `history=0` means raw values are **never stored**, and `trends=0` means there is **no long-term data**.
A router that reads "no data for 40 days ago" must be able to distinguish *aged out* from *never retained*,
and the second is a configuration fact, not an absence.

**This adds a fifth cause of absence** to FR-006's four, and the skill must cover it.

---

## D8 — Trends need elapsed time, confirmed

```
trend.get on a <1h-old install → 0 rows, no error
```

Trends are written hourly. The scheduling constraint the spec anticipated is real: **verifying trend-based
answers requires the lab to have been polling for hours.** Planning must sequence this, and if the window
has not elapsed at verification time, FR-051 requires recording it as unverified rather than claiming it.

---

## D9 — Manifest measured: 589 tokens

Via a real MCP handshake against the running server:

```
TOOLS (3): zabbix_api, zabbix_api_docs, zabbix_api_list
MANIFEST: 2,234 chars ≈ 589 tokens  →  11.8% of the 5,000 ceiling
```

Better than the ~823 the prior research estimated. This is the smallest surface NetClaw has added for an
entire product category.

---

## D10 — Read-only works; the launcher default is inverted

Against live Zabbix with `READ_ONLY=true`:

```
zabbix_api(host.get)     →  [{"hostid":"10084","host":"Zabbix server"}]
zabbix_api(host.delete)  →  REFUSED: "Server is in read-only mode ..."
```

The refusal works. But the default does not:

```
src/zabbix_mcp_server/utils.py:29        READ_ONLY default True
scripts/start_server.py:139              READ_ONLY default False   ← the shipped launcher
```

**Running it the documented upstream way enables writes.** NetClaw must set the flag itself (FR-021a) and
add a destructive-method deny-list as a second layer (FR-021b), because one of the two upstream defaults is
already wrong and we should not depend on which one wins.

Read/write classification is a **method-name prefix heuristic** (`get`, `version`, `check`, `export`), not a
curated list — worth knowing, because a future Zabbix read method that does not match those prefixes would
be refused, and a write method that does would not be.

---

## D11 — `python3 -m venv` fails on this host

```
python3 -m venv zvenv  →  "Failing command: .../zvenv/bin/python3"  (no ensurepip)
uv venv zvenv          →  works
```

This is **hazard #3 from spec 077's own docstring**, encountered live. The installer must use
`netclaw_venv_create` / `uv venv`, never bare `python3 -m venv` — and `check-dependency-pins.py` already
scans for exactly this.

---

## D12 — Upstream defects found, to be reported

Two, both worth sending upstream rather than silently working around (FR-034b):

1. **The launcher inverts the safe `READ_ONLY` default** (D10) — a security-relevant discrepancy between
   the library and the shipped entrypoint.
2. **`fastmcp>=v3.2.0` is not a valid PEP 440 specifier** (D2) — the `v` prefix will break stricter
   resolvers.

Spec 081 established that being a good citizen of free infrastructure is part of how NetClaw behaves.
Benefiting from a hazard while not telling the maintainer is not that.

---

## D13 — Licence and vendoring

GPL-3.0, confirmed (`LICENSE` = GNU GPL v3). Vendored **unmodified**, licence retained verbatim, marked as
third-party and separately licensed, invoked over stdio as a separate program (FR-034a). Never edited in
place — any change goes upstream.

Pinned revision: **`0722f48`, 2026-05-10, "Feature/v2"**.

---

## D14 — No audit, as expected

```
grep -c "approval|change_record|servicenow|gait|audit"  →  0  across all six modules
~/.openclaw/gait/  →  2 files, both NetClaw-authored servers
```

No per-call GAIT, and no platform-level MCP audit to fall back on. Resolved in clarification: recorded as an
inherited limitation (FR-038), acceptable because the integration is strictly read-only and therefore
performs no operation to audit (FR-038b). FR-038c blocks a future write path from arriving without audit.

---

## Summary of measured findings that change the spec

| # | Finding | Action |
|---|---|---|
| **D2** | Candidate needs fastmcp 3.x; **five servers pin `<3`** | **Dedicated venv**, per spec 076's precedent. Blocking otherwise |
| **D3** | Uses `zabbix_utils` (Zabbix LLC), **not `pyzabbix`** | Correct FR-032's rationale; staleness risk is lower than stated |
| **D4** | In-body `auth` still works on 7.0; removal is 7.2+ | Correct the justification; state the tested version |
| **D5** | 84/121 items are float; the default returns **0 points, no error** | Confirms trap 1 with real data |
| **D6** | Mixed types: 2-of-4 each way, overlap 0 | Confirms trap 2; splitting is mandatory |
| **D7** | **`history=0` and `trends=0` are real configurations** | **Fifth cause of absence** — extend FR-006 and the skill |
| **D8** | Trends empty on a fresh install | Sequence verification; record unverified if the window has not elapsed |
| **D9** | Manifest **589 tokens** (11.8%) | Record; ceiling is comfortable |
| **D10** | Refusal works; **launcher default inverted** | Force the flag; add a deny-list; report upstream |
| **D11** | `python3 -m venv` fails here (no ensurepip) | Use the repo helper — spec 077 hazard #3, live |
| **D12** | Two upstream defects | Report them (FR-034b) |
