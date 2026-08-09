# Verification Report — Catalyst Center official MCP, curated (spec 087)

**Date**: 2026-08-04 · **FR-038, FR-039, FR-040, SC-021**

**Verified against two live appliances**: `sandboxdnac.cisco.com` (4 devices, 25 sites) and
`sandboxdnac2.cisco.com` (0 devices, 1 site) — both real Catalyst Center instances sharing credentials.

## The design changed during the feature, and the spec records the old one

The spec was written around **curating to ~15 tools** via `CATALYST_CENTER_BUNDLED_TOOLS_DIR`. The operator
then asked for *"all the tools if possible or grouped as much as possible"*, which is achievable and better:

| Approach | Tools | Manifest | Coverage |
|---|---|---|---|
| Upstream default | 515 | **64,420 tokens** | all — 12.9× over ceiling |
| Spec's original curation | ~15 | ~4,200 | **~3% of the API** |
| **Delivered: 8 dispatchers + find + describe** | **10** | **1,821** | **all 514 read-only** |

FR-001–FR-006 as written describe the curation mechanism. **What shipped is the dispatcher design**, which
satisfies their intent (stay under the ceiling, read-only only, deliberate surface) by a different mechanism.
Recorded here rather than retro-fitted into the spec, so the change is visible.

`CATALYST_CENTER_BUNDLED_TOOLS_DIR` is consequently **unused** — we do not restrict upstream's bundle, we
front it.

## And "adopt" came to mean the catalogue, not the runtime

A second in-flight decision: NetClaw uses Cisco's **generated tool definitions** with its own client, rather
than running their server. That avoids three upstream properties at once — unbounded `fastmcp>=2.0.0`
(resolving 3.x against five servers pinning `<3`), HTTP-on-7001 transport, and the container needed only to
isolate the first. Dependencies are `mcp` and `httpx`.

## Per-capability status

| Capability | Exercised live | Evidence |
|---|---|---|
| **Empty vs populated appliance** | ✅ **both** | Same call, same credentials: `outcome=ok data=4` vs `outcome=empty` + caveat |
| Appliance identity on every response | ✅ | asserted; the two answers name different hosts |
| `observed_at` on every response | ✅ | asserted present |
| Discovery before dispatch | ✅ | `catc_find` returns real operations; states it does not contact the appliance |
| Dispatch returns real data | ✅ | `api_getSites` → 25 sites |
| Schema on demand | ✅ | `catc_describe_operation` returns uri + method + params |
| Unreachable ≠ empty | ✅ | dead endpoint → `unreachable`, message says "NOT AN EMPTY RESULT" |
| Bad credentials ≠ empty ≠ unreachable | ✅ | → `auth_failed`, "state is UNKNOWN, not empty" |
| Unknown operation refused helpfully | ✅ | refusal names `catc_find` |
| 514 read-only ops, 0 non-GET | ✅ | asserted; the single POST excluded |
| Manifest ≤ 5,000 | ✅ | **1,821**, measured by real handshake |
| 10-tool surface pinned | ✅ | exact name set asserted |

**43 assertions across 2 suites, exit 0.** No regression in the k8s, document, zabbix, bgp-intel, fortinet or
reconcile suites.

## Two defects the tests found in my own code

**1. A zero count was not treated as an absence.** `getDeviceConfigCount` returned a bare `0` on the empty
appliance and `4` on the populated one — and the empty-list branch never fired, so the `0` shipped with no
caveat. A scalar zero reads *more* like data than an empty list does. Fixed; both now yield
`outcome=empty` with an explicit caveat.

**2. Bad credentials were reported as `unreachable`.** `httpx.HTTPStatusError` subclasses `httpx.HTTPError`,
so a 401 on the token endpoint was caught by the transport handler — **collapsing "credentials rejected"
into "could not be reached"**. That is precisely the conflation this feature exists to prevent, in my own
code. Fixed with a distinct `AuthRejected` exception.

Both were caught by the live suite, not by review. Neither would have been caught by the static tests.

## Corrections to earlier claims in this feature

| Claim | Reality |
|---|---|
| "513 GET, 2 mutating (`getApplicationPolicy` POST, `complianceRemediation` DELETE)" | **514 GET, 1 POST.** My first pass string-matched `"DELETE"` anywhere in the JSON and hit it inside a parameter description. Reading `additionalMetadata.method` gives the truth: the only non-GET is `api_complianceRemediation` (POST) |
| "Use `sandboxdnac2.cisco.com`" (operator-supplied) | **`sandboxdnac2` is empty** — 0 devices. `sandboxdnac` (no `2`) has 4 devices and 25 sites on the same credentials |

The second is now load-bearing rather than trivia: `sandboxdnac2` is retained as the **empty-appliance test
case** (FR-039), because it is a free, real instance of the trap this feature protects against.

## Retired

`catalyst-center-mcp` — 7 tools, `fastmcp>=0.1.0` **unbounded** (resolves 3.x), **0 files tracked in git**,
and **absent from `config/openclaw.json`** entirely. Its catalog entry is replaced and its orphaned
`component_install_catalyst_center()` removed, since with no catalog id it could never be dispatched.

`devnet-catalyst-search` is untouched — it searches documentation, a different question.

## Unverified, stated plainly

| Item | Why | What would close it |
|---|---|---|
| **US3 health/compliance content** | The sandbox is shared and returns thin assurance data. The dispatchers reach those operations and `catc_find` lists them, but no health answer was inspected for correctness | An appliance with real assurance history |
| **US2 site hierarchy relationships** | 25 sites retrieved, but parent/child structure was not asserted | An assertion over `siteHierarchy` |
| **The 403/`forbidden` path** | Both sandbox accounts return 403 on writes, not on reads, so the "your other answers may be scoped" caveat is **coded but never triggered** | An RBAC-scoped read-only account |
| **Appliance versions other than 2.3.7.11** | The catalogue is version-coupled and only one release branch exists upstream | A second Catalyst Center version |
| **The 500 operations outside the tested handful** | 514 are *reachable and dispatchable* (asserted: every one has uri + method). Roughly six were actually called | Sustained real use |

That last row is the honest shape of this feature: **reachability is proven for all 514, correctness is
proven for a handful.** Saying otherwise would overstate it.

## Audit

No per-call GAIT record — the inherited posture of every externally-sourced integration, acceptable only
because this is strictly read-only. Unlike specs 083 and 084 the facade *is* NetClaw code, so adding audit
later is a small change rather than a wrapper.

## Checks

| Check | Result |
|---|---|
| `bash tests/catc/run-tests.sh` (with both appliances) | ✅ **43 assertions, exit 0** |
| `reconcile-mcp.py` | ✅ exit 0, all four surfaces |
| `verify-inventory-counts.py` | ✅ **216 skills / 158 integrations** |
| `trace-skill.py catalyst-center-readonly` | ✅ |
| Regression (6 other suites) | ✅ all exit 0 |
| No credential in any committed file | ✅ scanned |
