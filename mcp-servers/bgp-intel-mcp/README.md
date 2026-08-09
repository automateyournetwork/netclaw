# bgp-intel-mcp

BGP and registry intelligence from five public sources. NetClaw-authored — spec 081, roadmap **R9**.

The sequel to spec 079's Globalping: **R8 measures, R9 looks up.** Globalping answers "can anyone out there
reach us?"; this answers "who owns this, is the announcement legitimate, and where does this network peer?"

**Transport**: stdio · **Framework**: FastMCP · **Tools**: 10 · **Read-only** · **No credentials**

| Source | Provides | Cache TTL |
|---|---|---|
| `rpki-validator.ripe.net` | RPKI origin validation (primary) | 5 min |
| `stat.ripe.net` | RPKI fallback, AS overview, announced prefixes, visibility | 5 / 15 min |
| IANA bootstrap → RIR RDAP | Registry ownership, abuse contacts | 24 h |
| `peeringdb.com` | Interconnection: IXPs, facilities, policy | 24 h |
| `atlas.ripe.net` | Anchors, per-AS probe counts | 24 h |

## The distinction this server exists to protect

> **RPKI `not-found` is NOT `invalid`.**

Most of the internet has no ROA. Unsigned address space is the overwhelmingly common case, so reporting
`not-found` as a finding manufactures false incidents at scale and destroys trust in the tool.

| `state` | `reason` | `is_finding` | Meaning |
|---|---|---|---|
| `valid` | — | `false` | A ROA authorises this origin |
| `invalid` | `as` | **`true`** | A ROA covers this prefix; a **different AS** is authorised |
| `invalid` | `length` | **`true`** | Correct AS; prefix **more specific** than `maxLength` |
| `not_found` | — | `false` | **No ROA exists.** RFC 6811 `NotFound` |

All four states are **live-verified**, not read from documentation. Reproducible fixtures:

```
AS13335 + 1.1.1.0/24      -> valid
AS13335 + 8.8.8.0/24      -> invalid, reason=as      (ROA authorises AS15169)
AS15169 + 8.8.8.128/25    -> invalid, reason=length  (/25 under a maxLength-24 ROA)
AS3356  + 4.0.0.0/9       -> not_found
AS13335 + 2606:4700::/32  -> not_found               (IPv6 path)
```

`validation_unavailable` is a **separate outcome** from `not_found`. An unreachable validator does not mean
unsigned space, and the server will not infer state from routing or registry data (FR-007c).

### Spelling: three variants, all deliberate

| Where | Spelling |
|---|---|
| RFC 6811 and the validator's JSON | **`not-found`** (hyphen — wire format) |
| This codebase, enum members | **`not_found`** (underscore — a hyphen is not a valid identifier) |
| RIPEstat fallback only | `unknown` (a different vocabulary; mapped, never passed through) |

Normalising these would either produce invalid Python or silently break the wire mapping. A maintainer
tidying this "inconsistency" is a realistic hazard, hence this note.

## Why not RIPEstat as primary?

RIPEstat works and is the documented fallback, but `rpki-validator.ripe.net` is better on three measured
counts (research R2):

1. **RFC 6811 vocabulary natively** — `not-found`, not `unknown`
2. **`state` and `reason` are separate fields** — RIPEstat fuses them into `invalid_asn` / `invalid_length`
3. **It returns the VRPs** that drove the verdict, which FR-005 requires so an operator can check the
   reasoning rather than trust a label

## Not corroborated, and it says so

A second validator (`rpki-validator.ripe.net` vs RIPEstat) is reachable, but **both are RIPE NCC
Routinator** — same engine, same operator, same trust anchors. Comparing them would produce agreement that
means nothing, so `corroborated` is always `false` and every result states it.

Genuine corroboration needs a non-Routinator relying party — an `rpki-client`-based validator, or
Cloudflare's VRP dump evaluated locally. That is future work, not a claim made here.

## Response envelope

Every response passes through `envelope.emit()` — a **chokepoint, not a helper**, so a tool added later
cannot omit provenance or the audit record.

```jsonc
{ "source": "rpki-validator.ripe.net", "retrieved_at": "2026-08-03T12:04:11Z",
  "outcome": "ok", "cached": false, "cache_age_seconds": null,
  "query": {...}, "data": {...}, "caveats": [ "..." ] }
```

`caveats` is structured, not decoration: it carries the allocation-not-routing, self-reported and
collector-basis statements so they survive a model summarising the payload.

**Outcomes**: `ok` · `no_record` · `source_unavailable` · `source_refused` · `input_refused` ·
`rate_limited` · `validation_unavailable`

`no_record` and `source_unavailable` are never conflated — a dead API must not look like an empty registry.

## Tools (10)

**RPKI** · `rpki_validate`
**Registry** · `registry_lookup` `registry_abuse_contact`
**Routing** · `routing_as_overview` `routing_announced_prefixes`
**Peering** · `peering_network` `peering_presence`
**Atlas** · `atlas_anchors` `atlas_probe_count`
**Composite** · `resource_report`

## Manifest budget

**Measured 1,376 tokens against a hard 5,000 ceiling** (FR-027a) — 3,624 headroom. Re-measure with
`python3 tests/bgp-intel/test_manifest_size.py`, which fails the build if exceeded.

For scale, `duksh/peerglass` covers similar ground with **42 tools across 9 phases** including DNS
censorship detection, TLS/CT-log inspection and satellite tracking. That charter is far beyond R9 and the
manifest is the wrong order of magnitude, which is why this was built rather than adopted (research R1).

## Rate limiting — self-imposed, not service-declared

**Neither RIPEstat nor PeeringDB advertises rate-limit headers.** Measured on live 200 responses: there is
nothing to negotiate against at runtime.

So **4 requests/second per source is NetClaw's own conservative choice, not a published limit.** A
maintainer who later finds an official figure should not mistake this number for it.

Enforced as a **true sliding window**: no one-second window contains more than four requests to a source.
An earlier implementation enforced only a minimum 250 ms *gap*, which bounds the rate asymptotically but
lets five requests land inside one second — a contract test caught it, and the window replaced it.

Requests to one source are **strictly serial**; different sources proceed independently. Parallel fan-out is
prohibited (FR-023a), including inside `resource_report`, which runs its sections one after another.
`peerglass` parallelises for latency; this deliberately does not. Against volunteer-funded infrastructure,
being over-polite costs latency nobody notices and being under-polite costs the integration.

`BGP_INTEL_MAX_RPS` may **lower** the ceiling. Values above 4 are clamped.

## Environment

| Variable | Purpose |
|---|---|
| `BGP_INTEL_USER_AGENT` | Contact string sent to public APIs. Defaults to a NetClaw string with the project URL |
| `BGP_INTEL_MAX_RPS` | Default 4. Lowering is honoured; raising is clamped |
| `BGP_INTEL_AUDIT_LOG` | GAIT trail path; defaults under `~/.openclaw/gait/` |

**No credentials.** This is the first NetClaw integration with nothing to leak, rotate or scope.

## Install

```bash
netclaw_pip_install -r mcp-servers/bgp-intel-mcp/requirements.txt
```

`mcp>=1.2.0,<2` and `httpx>=0.27.0,<1`. The `mcp` upper bound is **load-bearing and no longer
hypothetical**: the MCP Python SDK has shipped **v2** targeting the 2026-07-28 specification, and v2 removes
`mcp.server.fastmcp`, which this server imports (spec 077).

No RDAP/RPKI/BGP library. The payloads are plain JSON and the value here is in the **semantics** — which
state means what — not the transport. An SDK would add a pinning hazard while abstracting the one thing this
feature must not abstract.

## Tests

```bash
./tests/bgp-intel/run-tests.sh
```

Five suites, **none of which touches a public API**. The rate-limit suite stubs the transport so it can
assert on the request timeline the limiter produces; the rest are pure functions. That matters twice: these
are volunteer-funded services that CI should not hit, and the guarantees are structural so they are provable
without the network.

Two suites assert on **rendered text** rather than structure, because the requirement is about wording:
the strings `invalid`, `suspicious` and `unverified` must never appear in a `not_found` result, and
`confirmed` / `cross-checked` must never appear in any RPKI result. Spec 080 shipped a null-fields bug past
24 passing tests that asserted only on envelope shape; these do not repeat that.

## Field notes

- **ARIN's RDAP is fine.** An early observation recorded a connection reset from `rdap.arin.net`; exercised
  through the bootstrap path it returned 200 with holder `GOGL`. The reset was **transient, not a property
  of ARIN**, and is deliberately not hardcoded as such.
- **RIPEstat's `unknown` is RFC 6811's `NotFound`.** A reader who knows the standard would otherwise
  conclude the state was indeterminate when it is definitively unsigned.
- **RIPEstat's RPKI validation is Routinator-backed**, which is why it cannot corroborate the primary.
- **`routinator.nlnetlabs.nl` → 400, `rpki.gin.ntt.net` → 404, `rpki.cloudflare.com/api/v1/validity` →
  404.** No open third-party validity API was found.

## Related

`workspace/skills/bgp-registry-intel` · `globalping-external-checks` (R8 — measures, does not look up) ·
`gtrace-ip-enrichment` (owns quick ASN/geo/rDNS hop enrichment — not duplicated here, Principle VII)
