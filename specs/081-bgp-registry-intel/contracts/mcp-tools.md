# Contract — `bgp-intel-mcp` tool surface

**Phase 1** · 2026-08-03 · Transport **stdio**, framework **FastMCP**, JSON-RPC lifecycle (Principle V).

**Budget**: the entire `tools/list` response MUST measure **≤ 5,000 tokens** (FR-027a) — the same ceiling
spec 080 set, carried as a repo-wide convention. This surface is ~10 tools and expected to pass with wide
headroom; the ceiling exists to stop a later expansion, not to constrain the initial build.

**Read-only.** No tool changes anything, anywhere. There is no write path and therefore no approval gate.

---

## Universal response envelope

Every tool returns the shape in [data-model.md §1](../data-model.md). Enforced by `envelope.emit()`, a
chokepoint rather than a convention.

```jsonc
{ "source": "...", "retrieved_at": "...", "outcome": "ok",
  "cached": false, "cache_age_seconds": null,
  "query": {...}, "data": {...}, "caveats": [] }
```

`caveats` is **structured, not prose decoration** — it carries the statements FR-009/013/016 require so they
survive a model summarising the payload.

---

## RPKI — 1 tool

### `rpki_validate(prefix, origin_asn, fresh=false)`

Origin validation for a prefix + origin-AS **pair**. FR-001–FR-007c.

Returns `state` ∈ `valid` · `invalid` · `not_found`, plus `reason` ∈ `as` · `length` · `null`, the VRPs that
drove the verdict, the validator's name, and `corroborated: false`.

**Contractual obligations — the core of this feature:**

| Obligation | Requirement |
|---|---|
| `not_found` carries a caveat that this is **normal and not a finding** | FR-003 |
| The words `invalid` / `suspicious` / `unverified` **never** appear in a `not_found` result | FR-003, SC-004 |
| `not_found` is reported using the **RFC 6811 term**, and if the RIPEstat fallback was used its `unknown` is translated with the translation stated | FR-004, SC-005 |
| `invalid/as` and `invalid/length` are **separately distinguishable** in output | FR-002, SC-003 |
| An `invalid` result names **what the ROA does authorise** (permitted ASN and maxLength) | FR-006 |
| The VRPs are included so the operator can check the reasoning, not trust a label | FR-005 |
| The validator is named and `corroborated` is literally `false` | FR-007a, SC-005a |
| The tool **never** says hijack, attack or incident | FR-007, SC-009 |
| Validator unreachable ⇒ `validation_unavailable`, **never** `not_found` | FR-007c, SC-005b |

`fresh=true` bypasses the 5-minute cache, for when a ROA was just published (FR-026c).

---

## Registry — 2 tools

### `registry_lookup(resource)`
IP, prefix or ASN → holder, allocation range, responsible registry, abuse contacts, events.

### `registry_abuse_contact(resource)`
Narrow convenience: just the abuse contacts. Exists because it is the single most common incident-response
question and folding it into the full record forces a caller to parse.

**Contractual obligations:**

| Obligation | Requirement |
|---|---|
| The **responding registry is named**, plus how it was selected (`iana_bootstrap` / `rdap_org_fallback`) | FR-010, SC-006 |
| Every record carries the caveat: **allocation data, not evidence about who is announcing** | FR-009 |
| A registry that resets/times out ⇒ `source_refused` / `source_unavailable` **naming it** — never `no_record` | FR-011, SC-007 |

---

## Routing — 2 tools

### `routing_as_overview(asn)`
Holder and allocation status for an ASN — distinct from what it announces.

### `routing_announced_prefixes(asn)`
Observed announcements with per-prefix visibility.

**Contractual obligations:**

| Obligation | Requirement |
|---|---|
| `collector_basis` present on every result; visibility is **RIPE's collectors, not global truth** | FR-013, SC-008 |
| The tool **never** attaches `leak` or `hijack` to a low-visibility prefix | FR-013, SC-009 |
| "No announcements observed" ≠ "AS does not exist" ≠ "query failed" | FR-014 |
| Large result sets are **bounded and say so** (`truncated`, `total_available`) — never silently cut | Edge Cases |

---

## Peering — 2 tools

### `peering_network(asn)`
PeeringDB network record: type, traffic profile, policy, contacts.

### `peering_presence(asn)`
IXPs and facilities.

**Contractual obligations:**

| Obligation | Requirement |
|---|---|
| Every result carries the caveat: **self-reported** | FR-016 |
| No record ⇒ `no_record` with the caveat that this is **not evidence the network does not peer** | FR-016, SC-010 |

---

## Atlas — 2 tools, deliberately narrow

### `atlas_anchors(country)`
Atlas anchors — stable, always-on measurement targets. Globalping has no equivalent.

### `atlas_probe_count(asn)`
How many Atlas probes sit inside a given AS — "can this network be measured from within?"

**Contractual obligations:**

| Obligation | Requirement |
|---|---|
| General probe-availability-by-location is **not implemented**; such a request is routed to Globalping's `locations` | FR-017a, SC-011 |
| A request to **run** a measurement is routed to Globalping (R8) | FR-018, SC-011 |

---

## Composite — 1 tool

### `resource_report(resource)`

The question an operator actually asks: *"what do I know about this prefix/ASN?"* Runs RPKI (if a prefix +
origin can be determined), registry, routing and peering, and returns one report.

**Contractual obligations:**

| Obligation | Requirement |
|---|---|
| **Per-element provenance** — each section carries its own `source`, never one collective citation | FR-021, SC-013 |
| Sub-queries run **serially**, respecting 4/s per source. No parallel fan-out | FR-023a, SC-016a |
| A failed section is reported as failed **within** the report; the report does not fail wholesale | FR-011 |
| Where sources disagree (RDAP holder vs PeeringDB name), the **disagreement is reported**, not resolved | Edge Cases |

This is the tool most at risk of quietly violating FR-023a, because "fetch four things" invites
`asyncio.gather`. It must not.

---

## Total surface: 10 tools

1 RPKI · 2 registry · 2 routing · 2 peering · 2 Atlas · 1 composite.

**A design target, not a measurement.** FR-027a/b require the real `tools/list` token count be measured and
enforced by a build-failing test once the surface exists.

---

## Error semantics

Every outcome in [data-model.md §2](../data-model.md) is reachable from this surface. Four obligations that
are easy to get wrong and are therefore contractual:

1. **`source_unavailable` names the source** and is never rendered as an empty result (FR-011).
2. **`input_refused` happens locally with no outbound request** — private, reserved and bogon input never
   reaches a public registry, because sending it is a disclosure even if the query fails (FR-028, SC-015).
3. **`rate_limited` produces backoff and a reported condition**, never a retry storm (FR-027, SC-018).
4. **`validation_unavailable` is distinguishable from RPKI `not_found`** in output (FR-007c, SC-005b) — the
   feature's core distinction, one level down, and the subtlest bug available here.
