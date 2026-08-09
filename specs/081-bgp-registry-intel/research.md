# Phase 0 Research — BGP & Registry Intelligence (spec 081 / roadmap R9)

**Date**: 2026-08-03 · **Branch**: `081-bgp-registry-intel`

Everything below was tested against live endpoints. Where something was **not** verified, it says so.

**Read R2 first** — it changes the primary data source the spec assumed, and improves the feature.

---

## R1 — Build, adopt, or wrap? → **Build**

### The candidate that matters: `duksh/peerglass`

A "deterministic MCP server for internet resource intelligence" whose stated scope overlaps R9 almost
exactly. Measured:

| Property | Value |
|---|---|
| Tools | **42**, across 9 "phases" |
| Language / licence | Python, `httpx`, FastAPI · MIT |
| Traction | **1 star**, 49 commits |
| Data sources | 5-RIR RDAP, Cloudflare VRP for RPKI, RIPEstat for BGP, PeeringDB, IANA bootstrap |
| Caching | **TTL 5 min – 24 h depending on tool** |
| Attribution | Results include the originating RIR/API |
| Writes | None — query-only |

### Why not adopt

1. **42 tools against a 5,000-token ceiling.** Even before measuring, a 42-tool manifest is the wrong
   order of magnitude for FR-027a. R9's whole surface should be ~10.
2. **Scope far beyond R9.** Its phases include DNS censorship detection, TLS/CT-log inspection, threat
   intel, **satellite tracking**, and "humanitarian/crisis" tooling. Adopting it means registering all of
   that, or suppressing most of it. Either way NetClaw inherits a charter it did not choose — and several
   of those areas belong to other roadmap items (R13 for NSM, R12 for logs).
3. **1 star, 49 commits.** Not a criticism of the author, but a real maintenance-risk input for something
   sitting on the routing-security path.
4. **RPKI source differs from ours.** It uses Cloudflare's VRP service; R2 below establishes a better
   source that reports RFC 6811 vocabulary natively.

### What adoption still gives us — and it is genuinely reassuring

`peerglass` arrived independently at **three of the design decisions this spec's clarification session
chose**: TTL caching in the 5-minute-to-24-hour band, per-result source attribution, and read-only
throughout. That is convergent evidence rather than borrowed design — two independent attempts at this
problem reaching the same conclusions is a signal the conclusions are right.

Also noted for reference: `simplebytes-com/rdap-mcp` (RDAP only) and a Go PeeringDB/IXP server. Both are
narrower than R9 and neither changes the decision.

**Decision: build** `mcp-servers/bgp-intel-mcp/`.
**Rejected**: adopt `peerglass` (manifest size, charter creep, single-star maintenance risk); wrap it
(inherits its 42-tool surface and its RPKI source choice).

---

## R2 — The RPKI source: switch from RIPEstat to `rpki-validator.ripe.net`

The spec was written assuming **RIPEstat** (`/data/rpki-validation/`), because that is what was verified
before drafting. A better endpoint exists and was verified during Phase 0.

### Side by side, both measured

| | RIPEstat `rpki-validation` | **`rpki-validator.ripe.net/api/v1/validity/`** |
|---|---|---|
| valid | `valid` | `valid` |
| wrong origin AS | `invalid_asn` | `invalid` + **`reason: "as"`** |
| max-length violation | `invalid_length` | `invalid` + `reason: "length"` |
| no ROA | **`unknown`** | **`not-found`** ← RFC 6811's own term |
| VRPs behind the verdict | not returned | **returned**: `matched`, `unmatched_as`, `unmatched_length` |
| Human-readable reason | no | **yes** — `"At least one VRP Covers the Route Prefix, but no VRP ASN matches the route origin ASN"` |

Live sample:

```json
{"validated_route": {"route": {"origin_asn": "AS13335", "prefix": "8.8.8.0/24"},
  "validity": {"state": "invalid", "reason": "as",
    "VRPs": {"matched": [], "unmatched_as": [ ... ]}}}}
```

**Three reasons this is the better primary source:**

1. **It speaks RFC 6811 natively.** `not-found`, not `unknown`. FR-004 exists purely because RIPEstat's
   vocabulary diverges from the standard; using this endpoint removes the translation risk at source rather
   than papering over it downstream.
2. **`state` and `reason` are separate fields.** RIPEstat fuses them into `invalid_asn` / `invalid_length`,
   forcing string parsing to recover a distinction FR-002 requires. Here it is structured.
3. **It returns the VRPs.** FR-005 requires the ROAs that drove the verdict be included so an operator can
   check the reasoning. RIPEstat does not provide them; this does.

**Decision**: `rpki-validator.ripe.net` is the primary RPKI source. RIPEstat remains a documented fallback,
and **FR-004's vocabulary translation still applies to it** — if the fallback is used, `unknown` must still
be reported as RFC 6811 `NotFound`.

---

## R3 — Is corroboration between two validators possible? → **No, and the clarified answer stands**

Clarification Q5 chose "single validator, named, explicitly uncorroborated," deferring corroboration until a
second validator was verified reachable. One now is. But it does **not** enable corroboration:

- **RIPEstat's RPKI validation is itself Routinator-backed** (per RIPE's own API documentation).
- **`rpki-validator.ripe.net` is Routinator**, operated by RIPE NCC.

Same engine, same operator, same trust anchors, same relying-party software. Comparing them would produce
agreement that means nothing — **corroboration theatre**, worse than none because it implies independence
that does not exist.

Also checked: `routinator.nlnetlabs.nl` → 400; `rpki.gin.ntt.net` → 404. Neither offers an open validity API.
Cloudflare's `rpki.cloudflare.com/api/v1/validity/...` → 404, as recorded in the spec; `peerglass` uses
Cloudflare's **VRP dump** instead, which is a different integration (fetch and evaluate locally) and a
materially larger piece of work.

**Decision**: single validator, per FR-007a. The clarified answer is unchanged, but the *reason* is now
stronger and evidence-based: not "we could not find a second one" but **"the available second one is not
independent."** Genuine corroboration would need a non-Routinator relying party — `rpki-client`-based, or
Cloudflare's VRP evaluated locally — and that is a future item, not a Phase 0 assumption.

---

## R4 — RDAP entry point

> **CORRECTED 2026-08-03 during implementation.** ARIN's RDAP was recorded below as
> refusing connections, based on a single `curl` observation. **That was wrong, or at least not
> durable.** Exercised through the implemented bootstrap path, `rdap.arin.net/registry/ip/8.8.8.8/32`
> returned **HTTP 200** with holder `GOGL`. The earlier reset was transient or specific to that
> request path — **not a property of ARIN**, and it must not be documented as one.
>
> The design is unchanged and was right for a better reason than the one it was chosen for: bootstrap
> resolution plus a fallback handles a *transient* per-registry failure exactly as well as a permanent
> one, and FR-011's "name the source that failed" is correct either way. Research open item 2 is now
> **closed** rather than carried into implementation.

| Endpoint | Result |
|---|---|
| `rdap.arin.net` direct | ⚠️ one observed connection reset; **later returned 200** — transient, see above |
| `rdap.org` bootstrap redirector | ✅ 200 (follows redirects to the responsible RIR) |
| `rdap.db.ripe.net` direct | ✅ 200 |
| IANA bootstrap (`data.iana.org/rdap/ipv4.json`) | ✅ 200 — authoritative RIR-to-range map |

**Decision**: resolve the responsible RIR from the **IANA bootstrap file**, then query that RIR directly,
falling back to `rdap.org` when the direct endpoint fails. This is the RFC 7484 mechanism and it means
FR-010's "name the responding registry" is satisfied by construction — we know which RIR we chose and why.

ARIN's reset is treated as a per-source failure (FR-011), not an absence of record. It may be host-specific
or transient; it MUST NOT be hardcoded as "ARIN is broken."

---

## R5 — Dependencies: two packages, matching specs 078 and 080

```
mcp>=1.2.0,<2
httpx>=0.27.0,<1
```

The `mcp` upper bound is **load-bearing**, and Phase 0 turned up fresh confirmation: the MCP Python SDK has
released **v2, a rework targeting the 2026-07-28 MCP specification**. `mcp` 2.x removes
`mcp.server.fastmcp`, which this server imports. An unbounded pin would resolve that major and die on
import for every new installer — exactly the failure spec 077 exists to prevent, now with a live v2 in the
wild rather than a hypothetical one.

No third-party RDAP/RPKI/BGP library. The payloads are plain JSON over HTTPS and the value here is in the
*semantics* — which state means what — not in transport. An SDK would add a pinning hazard and abstract the
one thing this feature must not abstract.

**No dedicated venv** (unlike spec 076): two pure-HTTP packages move nothing shared.

---

## R6 — Rate limits: undocumented, so self-imposed

Neither RIPEstat nor PeeringDB advertises `RateLimit`, `X-RateLimit` or `Retry-After` headers — measured on
live 200 responses. There is nothing to negotiate against at runtime.

FR-023's **≤ 4 req/s per source, strictly serial** is therefore a deliberately conservative self-imposed
figure, and the documentation must say so (FR-024) rather than let a later maintainer mistake it for a
service-declared limit.

`peerglass` uses "async parallel queries" to minimise latency. This spec deliberately does the opposite
(FR-023a): against volunteer-funded infrastructure, being over-polite costs latency nobody notices, and
being under-polite costs the integration.

---

## R7 — The `gtrace` boundary is real and narrow

`gtrace-ip-enrichment` already ships `asn_lookup` — returning ASN, organisation, network range **and
registry** — plus `geo_lookup`. That genuinely overlaps RDAP.

| Question | Owner |
|---|---|
| "Quick: who owns this traceroute hop, and where is it?" | **`gtrace`** — enrichment, geo, rDNS |
| "Authoritatively: what is the registry record, abuse contact, allocation?" | **this feature** |
| "Is this announcement RPKI-authorised?" | **this feature** — gtrace has no RPKI |
| "What does this AS announce? Where does it peer?" | **this feature** |

**Decision**: no ASN-enrichment or geolocation tool here. FR-032 draws the line and the skill must name
`gtrace` for hop enrichment. Principle VII.

---

## R8 — Atlas: what the narrowed US5 actually needs

Clarification Q1 narrowed US5 to **anchors** and **per-AS probe counts**. Verified: `atlas.ripe.net/api/v2/`
serves `anchors/` and `probes/` read-only, unauthenticated, with filters including `asn` and `country`.
Measurement *creation* needs a key and credits — out of scope, routed to R8 (FR-018).

---

## Summary of decisions

| # | Decision | Drives |
|---|---|---|
| R1 | Build `bgp-intel-mcp`; `peerglass` rejected but validates three design choices | FR-027a |
| R2 | **`rpki-validator.ripe.net` primary** — RFC 6811 native, returns VRPs, `reason` separate | FR-002, FR-004, FR-005 |
| R3 | Single validator confirmed correct — the second one is not independent | FR-007a |
| R4 | IANA bootstrap → direct RIR → `rdap.org` fallback | FR-010, FR-011 |
| R5 | `mcp>=1.2.0,<2` + `httpx>=0.27.0,<1`; no venv; **mcp 2.0 is real** | FR-042 |
| R6 | 4 req/s serial, self-imposed and documented as such | FR-023, FR-024 |
| R7 | No ASN/geo enrichment here — `gtrace` owns it | FR-032 |
| R8 | Atlas anchors + per-AS probe counts only | FR-017, FR-017a |

## R9 — All four RPKI states verified against the primary source

Closed during Phase 0. Every state FR-002 requires is now **observed**, not inferred from documentation:

| Query | `state` | `reason` | Description (verbatim) |
|---|---|---|---|
| `AS13335` + `1.1.1.0/24` | `valid` | — | "At least one VRP Matches the Route Prefix" |
| `AS13335` + `8.8.8.0/24` | `invalid` | **`as`** | "…no VRP ASN matches the route origin ASN" |
| `AS15169` + `8.8.8.128/25` | `invalid` | **`length`** | "…the Route Prefix length is greater" |
| `AS3356` + `4.0.0.0/9` | **`not-found`** | — | no covering VRP |

The `length` case was constructed deliberately: `8.8.8.0/24` has a ROA with `maxLength 24`, so announcing
`8.8.8.128/25` with the *correct* origin AS is invalid on length alone. That is the distinction FR-002
forbids collapsing, and it is now demonstrable rather than asserted.

## R10 — IPv6 verified across every source

| Source | IPv6 query | Result |
|---|---|---|
| RPKI validator | `AS13335` + `2606:4700::/32` | ✅ verdict returned (`not-found`) |
| RDAP (RIPE) | `2001:67c:2e8::` | ✅ 200 |
| RIPEstat routing-status | `2606:4700::/32` | ✅ 200 |

FR-029 is satisfiable. Note the RPKI result is `not-found` for that pair, which is a useful test fixture in
its own right — an IPv6 prefix that returns the *common* state rather than the exceptional one.

## Still open — carried as tasks, not assumptions

1. **Measure the manifest** once the surface exists (FR-027a/b). Cannot be done before the tools exist.
2. ~~Confirm ARIN's reset is not host-specific~~ — **CLOSED during implementation.** ARIN returned 200
   through the bootstrap path. The reset was transient; the correction is recorded in R4.
3. **Confirm PeeringDB behaviour for an AS with no record** — needed for SC-010, and requires finding an ASN
   that is genuinely absent from PeeringDB rather than assuming one.
