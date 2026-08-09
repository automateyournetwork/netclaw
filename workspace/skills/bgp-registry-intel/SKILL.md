---
name: bgp-registry-intel
description: "BGP and registry intelligence — RPKI origin validation (is this announcement authorised?), RDAP registry ownership and abuse contacts, PeeringDB interconnection data, RIPEstat routing status and prefix visibility, RIPE Atlas anchors. Use when investigating an unfamiliar prefix or ASN, checking whether a BGP announcement is RPKI-valid, finding who owns address space or who to report abuse to, or determining what an AS announces and where it peers."
version: 1.0.0
license: Apache-2.0
tags: [bgp, rpki, rdap, whois, peeringdb, routing, registry, internet, security, external]
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["BGP_INTEL_MCP_CMD"] } } }
---

# BGP & Registry Intelligence

## MCP Server

- **Server**: `bgp-intel-mcp` (NetClaw-authored, spec 081 / roadmap R9)
- **Command**: `$BGP_INTEL_MCP_CMD`
- **Transport**: stdio
- **Credentials**: **none.** Every source is a public unauthenticated API
- **Mode**: read-only. There is no write path

## The one rule that matters most

> ### RPKI `not-found` is NOT `invalid`.

**Most of the internet has no ROA.** Unsigned address space is the overwhelmingly common case, not an
anomaly. If you report `not-found` as a hijack, a misconfiguration, or a security finding, you will
generate false incidents at scale and the operator will stop trusting you.

| State | Means | Actionable? |
|---|---|---|
| `valid` | A ROA authorises this origin AS | **No** — healthy |
| `invalid` + `reason: as` | A ROA covers this prefix; **a different AS** is authorised | **Yes** — possible hijack |
| `invalid` + `reason: length` | Correct AS, but the prefix is **more specific** than the ROA permits | **Yes** — usually a local misconfiguration, different fix |
| `not_found` | **No ROA exists.** RFC 6811 calls this NotFound | **No** — the normal case |

The two `invalid` reasons are different findings. `as` means someone else is announcing your space;
`length` usually means *you* announced a /24 under a /22 ROA. Never collapse them.

**`validation_unavailable` is not `not_found`.** If the validator is unreachable you get the former, and
the RPKI state is genuinely unknown. Do not infer "unsigned" from "could not ask", and do not fall back to
guessing from routing or registry data.

## Tools (10, all read-only)

| Tool | Answers |
|---|---|
| `rpki_validate` | Is this prefix legitimately announced by this AS? **Nothing else in NetClaw does this** |
| `registry_lookup` | Who is this IP/prefix/ASN allocated to? |
| `registry_abuse_contact` | Who do I report abuse to? |
| `routing_as_overview` | Who holds this ASN; is it announced at all? |
| `routing_announced_prefixes` | What does this AS announce, and how visible is it? |
| `peering_network` | Network type, traffic profile, peering policy |
| `peering_presence` | Which IXPs and facilities? |
| `atlas_anchors` | Atlas anchors in a country (stable measurement targets) |
| `atlas_probe_count` | Can this AS be measured from inside? |
| `resource_report` | Everything about a resource, one call, per-section sourcing |

## Three more "this is not what you think it is"

- **Registry data is allocation, not routing.** RDAP tells you who address space is *registered to*. It says
  nothing about who is *announcing* it. Use `routing_announced_prefixes` for that. Treating an RDAP holder
  as a routing fact is the same category error as treating FortiManager intent as device state.
- **PeeringDB is self-reported.** No record means nobody filled in the form — **not** that the network does
  not peer. Many networks peer extensively and publish nothing.
- **Visibility is RIPE's collectors, not the internet.** Low visibility has legitimate causes: scoped
  announcements, no-export, anycast, a recent change. The tool will never call it a leak, and neither should
  you without more evidence.

## Every response carries its source

```jsonc
{ "source": "rpki-validator.ripe.net", "retrieved_at": "...", "outcome": "ok",
  "cached": false, "cache_age_seconds": null, "data": {...}, "caveats": [...] }
```

`caveats` carries the statements above — read them, they are not decoration. `resource_report` gives each
section **its own** source; never attribute one section's data to another's origin.

Failures name the source that failed. **`source_unavailable` is never "no record found"** — a dead API and
an empty registry are different facts.

## Workflow: an unfamiliar prefix appears

1. `rpki_validate` with the prefix **and** the origin AS. Validation is always of the pair.
2. Read the state carefully against the table above. If `not_found`, **stop treating it as a problem.**
3. `registry_lookup` — who holds it, and who to contact.
4. `routing_announced_prefixes` on the origin AS — is this consistent with what it normally announces?
5. `peering_network` — is this a transit provider, content network, or enterprise? It changes what "normal"
   looks like.
6. Escalate only on `invalid`, and only after checking that the origin AS is what you think it is and the
   ROA is current. **This skill does not declare incidents** — that is your judgement.

## Workflow: who do I complain to?

1. `registry_abuse_contact` on the address.
2. If none is published, try the covering allocation with `registry_lookup`.
3. `peering_network` often has a technical contact when the registry does not.

## Boundaries — which tool owns what

| Question | Use |
|---|---|
| "Can the outside reach us? Measure from N countries" | **`globalping-external-checks`** (R8) — Globalping *measures*; this *looks up* |
| "Quick: who owns this traceroute hop, and where is it?" | **`gtrace-ip-enrichment`** — it owns ASN/geo/rDNS enrichment |
| "Is this software version vulnerable?" | `nvd-cve` / `cisco-psirt` — different plane entirely |
| "Is this *routing* legitimate?" | **this skill** |

Those first two are load-bearing, not politeness. `gtrace` already does quick ASN and geolocation lookups
and this skill deliberately does not duplicate them (Principle VII). For general Atlas/Globalping probe
availability by location, or to run any measurement, go to Globalping.

## Being a good citizen

RIPE NCC and PeeringDB are volunteer- and membership-funded. The server holds itself to **≤ 4 requests per
second per source, strictly serial** — even `resource_report` runs its sections one after another.

**Do not use these tools to enumerate, sweep, or bulk-harvest registry data.** Look things up in service of
a specific operational question. The rate limiter enforces politeness mechanically; the judgement about
*what to ask* is yours.

Repeated lookups come from a cache with per-source lifetimes — RPKI 5 minutes, registry 24 hours — and a
cached answer says so and reports its age. Pass `fresh=true` when a ROA was just published and you need to
see through the cache.

## Important rules

- **`not_found` is normal.** Say so when you report it.
- **Keep the two `invalid` reasons apart.** Different cause, different fix.
- **Never say hijack or attack.** Report state and evidence; escalation is the operator's.
- **Private and reserved addresses are refused locally**, before any request leaves — sending internal
  addressing to a public registry is a disclosure even if the lookup fails.
- **Single validator.** Results are never corroborated; they say so.
