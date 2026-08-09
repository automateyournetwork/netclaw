# Verification Report — BGP & Registry Intelligence (spec 081 / R9)

**Date**: 2026-08-03 · **FR-036 / FR-037 / SC-020**

FR-037 set a harder bar than spec 080 met: every source here is public and unauthenticated, so
**near-total live verification was the expectation, not the aspiration.** Spec 080's excuse — appliances
unavailable — does not exist.

## Result: 10 of 10 tools live-verified

| Tool | Status | Source that answered |
|---|---|---|
| `rpki_validate` | ✅ live | `rpki-validator.ripe.net` |
| `registry_lookup` | ✅ live | `rdap.db.ripe.net`, `rdap.arin.net` |
| `registry_abuse_contact` | ✅ live | `rdap.db.ripe.net` |
| `routing_as_overview` | ✅ live | `stat.ripe.net` |
| `routing_announced_prefixes` | ✅ live | `stat.ripe.net` |
| `peering_network` | ✅ live | `peeringdb.com` |
| `peering_presence` | ✅ live | `peeringdb.com` |
| `atlas_anchors` | ✅ live | `atlas.ripe.net` |
| `atlas_probe_count` | ✅ live | `atlas.ripe.net` |
| `resource_report` | ✅ live | composite — **5 sections, 4 distinct sources** |

**Nothing shipped unexercised.** Compare spec 080, which shipped 13 of 21 tools untouched because no
FortiManager or FortiAnalyzer was deployed.

## The four RPKI states — all observed, none inferred

| Query | `state` | `reason` | RFC 6811 | `is_finding` |
|---|---|---|---|---|
| `AS13335` + `1.1.1.0/24` | `valid` | — | Valid | `false` |
| `AS13335` + `8.8.8.0/24` | `invalid` | **`as`** | Invalid | **`true`** |
| `AS15169` + `8.8.8.128/25` | `invalid` | **`length`** | Invalid | **`true`** |
| `AS3356` + `4.0.0.0/9` | `not_found` | — | **NotFound** | `false` |
| `AS13335` + `2606:4700::/32` | `not_found` | — | NotFound | `false` |

The `length` case was **constructed deliberately**: `8.8.8.0/24` carries a ROA with `maxLength 24`, so
announcing `8.8.8.128/25` with the *correct* origin AS is invalid on length alone. That is the distinction
FR-002 forbids collapsing, and it is now demonstrable rather than asserted.

## The central promise, asserted as text

| Assertion | Result |
|---|---|
| `not_found` output contains "invalid" | ❌ absent |
| `not_found` output contains "suspicious" | ❌ absent |
| `not_found` output contains "unverified" | ❌ absent |
| `not_found` output says "normal" and "not a finding" | ✅ present |
| Any RPKI output contains "confirmed" / "cross-checked" | ❌ absent |
| Every RPKI output says "not corroborated" and names its validator | ✅ present |

These are **text** assertions on purpose. Spec 080 shipped `fgt_system_status` returning three `null`
fields past 24 passing tests, because those tests asserted on envelope *shape* and never on content. A
requirement about wording needs a test about wording.

## Structural guarantees — verified without the network

| Guarantee | Status |
|---|---|
| Every response names its source; a source-less response errors | ✅ |
| Merged answers carry **per-element** provenance (SC-013) | ✅ 4 distinct sources in one report |
| Every operation GAIT-audited, **including refusals and failures** | ✅ 30 records in the live run |
| `no_record` ≠ `source_unavailable` | ✅ |
| `validation_unavailable` ≠ `not_found` | ✅ |
| Private/reserved/bogon refused **with no outbound request** | ✅ 16 classes, v4 and v6 |
| No 1-second window exceeds 4 requests per source | ✅ observed from a request timeline |
| Requests to one source never concurrent | ✅ zero overlapping intervals |
| Different sources not serialised against each other | ✅ |
| Per-source TTLs (RPKI 5 min ≠ RDAP 24 h) | ✅ |
| `fresh=true` bypasses cache | ✅ |
| `BGP_INTEL_MAX_RPS` cannot be raised above 4 | ✅ clamped |
| Manifest ≤ 5,000 tokens | ✅ **1,376** |

## Two things found during implementation that changed the work

### The rate limiter was genuinely too weak

The first implementation enforced a **minimum 250 ms gap** between requests. A contract test measuring the
observed timeline failed at **4.53 requests/second**, and the cause was a fencepost: N requests spaced
250 ms apart span (N−1)×0.25 s, so **five** fit inside one second against a ceiling of four.

That is a real violation of FR-023's literal reading, against volunteer-funded infrastructure. Replaced
with a **true sliding window**: no one-second window may contain more than four requests.

A second round then failed at 4.89/s — and that time **the test was wrong, not the code**.
`total_requests / total_elapsed` is not "requests in any window"; with a correct sliding window, requests
1–4 fire immediately and the 5th waits for the 1st to age out, giving a misleading burst average while
every actual window holds exactly four. The assertion was rewritten to check the invariant directly.

Worth recording because the sequence matters: the test caught a real bug, then the fixed code caught a bad
test.

### ARIN is not broken

Phase 0 recorded `rdap.arin.net` refusing connections (`Recv failure: Connection reset by peer`) from a
single `curl`. Exercised through the implemented IANA-bootstrap path it returned **HTTP 200** with holder
`GOGL`.

**The reset was transient, not a property of ARIN.** The spec and research have been corrected. The design
is unchanged and was right for a better reason than it was chosen for: bootstrap resolution plus a fallback
handles a transient per-registry failure exactly as well as a permanent one, and FR-011's "name the source
that failed" is correct either way.

## What was not verified, and why

| Not exercised | Why | Justified? |
|---|---|---|
| `rate_limited` outcome against a real throttle | No source throttled us at 4 req/s — the ceiling is conservative enough that provoking it would mean deliberately abusing a free service | **Yes.** Verified against a stub instead |
| `source_refused` against a live refusal | ARIN's reset was not reproducible (see above) | **Yes.** Verified against a stub; the transient case is the honest finding |
| PeeringDB `no_record` against a genuinely absent ASN | Research open item 3 — not closed. Logic is unit-tested, but no real ASN absent from PeeringDB was located | **Partially.** The path is tested, not live-observed |
| RIPEstat RPKI **fallback** path | The primary validator never failed during verification | **Yes.** Translation logic is unit-tested including `unknown`→`not_found` and `invalid_asn`→(`invalid`,`as`) |

Four items, each a case that requires the *unhappy* path of a healthy public service. Each is unit-tested
and each is named here rather than glossed. That is the whole point of this document.

## Gates

| Check | Result |
|---|---|
| `reconcile-mcp.py` (4 surfaces) | ✅ exit 0 |
| `verify-inventory-counts.py` | ✅ exit 0 — 207 skills, 154 integrations |
| `trace-skill.py bgp-registry-intel` | ✅ exit 0 |
| `tests/bgp-intel/run-tests.sh` (5 suites) | ✅ exit 0 |
| `test_manifest_size.py` | ✅ 1,376 / 5,000 |
| Bash / Node / JSON / Python syntax | ✅ all valid |
