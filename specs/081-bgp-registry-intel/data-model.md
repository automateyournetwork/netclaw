# Data Model — BGP & Registry Intelligence (spec 081)

**Phase 1** · 2026-08-03 · Stateless server. These are **response shapes and typed distinctions**, not
persisted records. Nothing is written to disk (FR-026a).

---

## 1. The provenance envelope — every response, no exceptions

Every response passes through `envelope.emit()`. There is no path to a client that bypasses it (FR-019/020).

```jsonc
{
  "source": "rpki-validator.ripe.net",   // REQUIRED — the specific service, never a category
  "retrieved_at": "2026-08-03T12:04:11Z",
  "outcome": "ok",
  "cached": false,                        // true + cache_age_seconds when served from cache (FR-026b)
  "cache_age_seconds": null,
  "query": { ... },                       // what was actually asked, echoed back
  "data": { ... },
  "caveats": []                           // the "this is not what you think" statements
}
```

**Validation rule (FR-019)**: a response whose `source` cannot be named MUST be an error, not an
unattributed answer. "The registry says" is not attributable; RIRs differ in freshness and completeness.

**Validation rule (FR-021)**: where a result merges data from more than one service, **each element carries
its own source**. One collective citation across a merged answer is not attribution.

`caveats` is a structured field, not decoration. It carries the statements FR-009, FR-013 and FR-016
require — self-reported, collector-based, allocation-not-routing — so they cannot be lost when a model
summarises the payload.

---

## 2. Outcomes — the typed distinctions

```
ok                        data returned
no_record                 the source answered; there is no record for this resource
source_unavailable        the source did not answer. NOT "no record"
source_refused            the source actively rejected us (e.g. ARIN's connection reset)
input_refused             private/reserved/bogon/malformed — refused locally, no request made
rate_limited              throttled; backed off rather than retried
validation_unavailable    RPKI-specific: the validator could not be reached
```

| Never collapse | Because |
|---|---|
| `no_record` vs `source_unavailable` | A dead API must never look like an empty registry (FR-011) |
| `no_record` vs `input_refused` | We refused, versus they had nothing |
| `validation_unavailable` vs RPKI `not_found` | **FR-007c.** An unreachable validator is not "unsigned" |

That last row is the feature's core distinction reappearing one level down, and the subtlest bug available
here.

---

## 3. RPKI validation — the flagship entity

### `RpkiValidation`

| Field | Notes |
|---|---|
| `prefix`, `origin_asn` | Validation is always of the **pair**, never a prefix alone |
| `state` | `valid` · `invalid` · `not_found` — RFC 6811 vocabulary. **See the spelling note below** |
| `reason` | `as` · `length` · `null`. Populated **only** when `state == invalid` |
| `description` | The validator's own human-readable sentence |
| `vrps_matched[]` | VRPs that matched — the evidence for `valid` |
| `vrps_unmatched_as[]` | Covering VRPs whose ASN differs — the evidence for `invalid`/`as` |
| `vrps_unmatched_length[]` | Covering VRPs whose maxLength is exceeded — evidence for `invalid`/`length` |
| `validator` | Named on every result (FR-007a) |
| `corroborated` | **Always `false`.** See below |
| `is_finding` | `true` only for `invalid`. See below |

### The four states, all live-verified (research R9)

| State | `reason` | Meaning | `is_finding` |
|---|---|---|---|
| `valid` | — | A ROA authorises this origin | `false` |
| `invalid` | `as` | A ROA covers this prefix; **a different AS** is authorised | **`true`** |
| `invalid` | `length` | A ROA covers this prefix; **it is more specific** than `maxLength` | **`true`** |
| `not_found` | — | **No ROA exists.** The common case | **`false`** |

**Rule (FR-003), the single most important in this model:** `not_found` MUST carry an explicit caveat that
this is normal for most address space and is **not** a finding. The words `invalid`, `suspicious` and
`unverified` MUST NOT appear in a `not_found` result.

**Rule (FR-002):** `reason` is a separate field precisely so `invalid/as` and `invalid/length` stay
distinguishable. RFC 6811 collapses both to "Invalid"; the validator is more granular, and flattening it
destroys the difference between *"someone else is announcing your space"* and *"you announced a /24 under a
/22 ROA."* Different severity, different remediation.

**Rule (FR-007a):** `corroborated` is a literal `false`, not omitted. Both reachable validators are RIPE NCC
Routinator — same engine, same operator (research R3) — so agreement between them would be theatre. The
field exists to make the absence of corroboration explicit rather than implied.

**Rule (FR-004):** the RIPEstat fallback returns `unknown` for what the standard calls `NotFound`, and fuses
`invalid_asn`/`invalid_length`. When the fallback is used, the mapping to this model MUST be applied and the
translation stated. Passing the raw string through is prohibited.

### Spelling: `not-found` on the wire, `not_found` in code — deliberately

Three spellings are in play and the difference is **intentional**, not drift:

| Where | Spelling | Why |
|---|---|---|
| RFC 6811, and the validator's JSON | **`not-found`** | The standard's term and the wire format |
| This model, enum members, Python identifiers | **`not_found`** | A hyphen is not valid in an identifier |
| RIPEstat fallback only | `unknown` | A different vocabulary entirely — mapped, never passed through |

Normalising these to one spelling would either produce an invalid Python identifier or silently break the
wire mapping. A future maintainer tidying this "inconsistency" is a realistic hazard, which is why it is
written down rather than left to be inferred.

---

## 4. Registry records (RDAP)

### `RegistryRecord`

| Field | Notes |
|---|---|
| `resource` | The IP, prefix or ASN queried |
| `holder` | Registered organisation |
| `allocation_range` | The block the resource sits in |
| `registry` | **Which RIR answered** — required (FR-010) |
| `registry_selected_via` | `iana_bootstrap` · `rdap_org_fallback` — how we chose (research R4) |
| `abuse_contacts[]` | Email/phone where published |
| `events[]` | Registration/last-changed dates where published |

**Rule (FR-009):** every registry record carries the caveat that this is **allocation data, not evidence
about who is announcing the space.** Presenting an RDAP holder as a routing fact is the same category error
as presenting FortiManager intent as device state (spec 080).

**Rule (FR-011):** a registry that resets, times out or refuses yields `source_refused` /
`source_unavailable` **naming that registry** — never `no_record`. ARIN's connection reset from this host is
the live example, and it must not be hardcoded as "ARIN is broken" (research R4).

---

## 5. Routing status

### `AsOverview` · `AnnouncedPrefixes`

| Field | Notes |
|---|---|
| `asn`, `holder` | Allocation-level identity |
| `announced_prefixes[]` | Each with observed visibility |
| `visibility.peers_seeing` / `peers_total` | Raw counts, not a score |
| `collector_basis` | Required — whose collectors (FR-013) |
| `truncated`, `total_available` | Set when bounded; never silently cut |

**Rule (FR-013):** visibility is **RIPE's collector view, not global truth.** Low visibility has legitimate
explanations — deliberately scoped announcements, anycast, no-export. The words `leak` and `hijack` MUST NOT
be attached by the tool (SC-009).

**Rule (FR-014):** "no announcements observed" is distinct from "the AS does not exist" and from "the query
failed". Three different facts.

---

## 6. Peering data

### `PeeringRecord`

`asn` · `name` · `info_type` · `info_traffic` · `policy_general` · `ixps[]` · `facilities[]` · `contacts[]`

**Rule (FR-016):** PeeringDB is **self-reported**. An absent record is `no_record` with the caveat that this
is **not evidence the network does not peer** — it is evidence nobody updated the record. Absence of
evidence again.

---

## 7. Atlas inventory — deliberately narrow

### `AtlasAnchor` · `AsProbeCount`

`anchors[]` (id, fqdn, country, status) · `asn` + `probe_count` + `probes_connected`

**Rule (FR-017a):** general probe-availability-by-location is **not modelled here.** Globalping's
`locations` owns it; a request for it is routed there. This entity exists only for anchors and per-AS
density, the two things Globalping has no equivalent of (clarification Q1).

---

## 8. Request discipline

### `SourceBudget` (internal, one per source)

| Field | Value |
|---|---|
| `max_rps` | **4** |
| `max_concurrency` | **1** — strictly serial (FR-023a) |
| `user_agent` | Identifies NetClaw + a contact reference (FR-025) |

**Rule (FR-023b):** enforced at the request layer, so a tool added later inherits it without knowing it
exists. Not caller discipline.

### `CacheEntry` (in memory only)

| Source | TTL |
|---|---|
| RPKI validation | **5 min** — a ROA can appear or vanish in minutes; a stale `valid` is the most dangerous stale value here |
| Routing status / AS overview | 15 min |
| RDAP | 24 h |
| PeeringDB | 24 h |
| Atlas | 24 h |

**Rule (FR-026a):** in-memory, session-scoped. **No on-disk store.** Deliberately unlike spec 078, which
caches PSIRT data on disk because that data is large and genuinely slow-moving.

**Rule (FR-026b/c):** a cached response reports `cached: true` **and** `cache_age_seconds`, and a caller can
force a fresh lookup — for the case where a ROA was just published and the 5-minute TTL is the only thing
between the operator and the truth.

---

## 9. Input validation — refused before any request leaves

`validate.py` refuses, **locally, with no outbound request** (FR-028):

- RFC1918 · loopback · link-local · CGNAT (100.64/10) · multicast · reserved
- Documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24, 2001:db8::/32)
- IPv6 ULA (fc00::/7) · unspecified · unique-local
- Malformed: bad prefix length, non-numeric ASN, mixed address family, AS0

**Rule (FR-028):** this is a **disclosure control**, not a validation nicety. Sending an internal address to
a public registry is a disclosure even if the query then fails — the same reasoning spec 079 applied to
Globalping.

**Rule (FR-029):** IPv4 and IPv6 across every capability. Verified live for RPKI, RDAP and routing status
(research R10).

---

## 10. Audit records (GAIT) — FR-022, Principle IV

Emitted from the same chokepoint as provenance, so a new tool cannot skip it.

| Field | Notes |
|---|---|
| `ts`, `component`, `tool` | |
| `query` | The resource asked about |
| `source`, `outcome` | |
| `cached` | Whether a request actually left the machine |

Includes **refusals and failures**. There are no credentials in this feature, so unlike specs 078 and 080
there is no redaction concern — but the record still carries only the shape of the operation, not bulk
payload.
