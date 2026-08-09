# Quickstart — BGP & Registry Intelligence (spec 081 / R9)

> **There is nothing to obtain.** No lab, no licence, no trial, no API key, no account. Every source is a
> public unauthenticated API. This is the first roadmap item since R8 with no external dependency on the
> critical path — which is exactly why it was chosen while R4 waits on a vendor trial.

## Install

```bash
netclaw_pip_install -r mcp-servers/bgp-intel-mcp/requirements.txt
```

Two packages: `mcp>=1.2.0,<2` and `httpx>=0.27.0,<1`. The `mcp` upper bound is **load-bearing** — v2 exists
and removes `mcp.server.fastmcp`, which this server imports (spec 077).

## Configure

Nothing is required. All variables are optional tuning:

```bash
BGP_INTEL_USER_AGENT=          # override the contact string sent to public APIs
BGP_INTEL_MAX_RPS=             # default 4 — lower it, never raise it
BGP_INTEL_AUDIT_LOG=           # GAIT trail path; defaults under ~/.openclaw/gait/
```

**There are no credentials.** Nothing to leak, rotate or scope.

## Verify

```bash
./tests/bgp-intel/run-tests.sh                  # contract tests, no network
python3 tests/bgp-intel/test_manifest_size.py   # must be <= 5,000 tokens
python3 scripts/reconcile-mcp.py                # must exit 0
python3 scripts/trace-skill.py bgp-registry-intel
```

Live smoke tests — these hit real public APIs, so keep them few:

```bash
python3 $MCP_CALL "$BGP_INTEL_MCP_CMD" rpki_validate '{"prefix":"1.1.1.0/24","origin_asn":"AS13335"}'
python3 $MCP_CALL "$BGP_INTEL_MCP_CMD" registry_lookup '{"resource":"8.8.8.8"}'
python3 $MCP_CALL "$BGP_INTEL_MCP_CMD" routing_as_overview '{"asn":"AS15169"}'
```

Every response must carry `source` and `retrieved_at`. **A response missing either is a bug, not a quirk** —
that guarantee is the point of the feature.

## The four RPKI states, with real test fixtures

These are verified live (research R9) and make good regression cases:

| Query | Expected | Note |
|---|---|---|
| `AS13335` + `1.1.1.0/24` | `valid` | Healthy |
| `AS13335` + `8.8.8.0/24` | `invalid`, `reason: as` | ROA authorises AS15169 |
| `AS15169` + `8.8.8.128/25` | `invalid`, `reason: length` | Correct AS, but `/25` under a `maxLength 24` ROA |
| `AS3356` + `4.0.0.0/9` | `not_found` | **No ROA. The common case** |
| `AS13335` + `2606:4700::/32` | `not_found` | IPv6 path (FR-029) |

**The `not_found` case is the one to watch.** If its output ever contains the words *invalid*, *suspicious*
or *unverified*, the feature has broken its central promise. Most of the internet is unsigned; treating that
as a finding would manufacture false incidents at scale.

## Reading the results

**`not_found` means no ROA exists.** It is normal. It is not a hijack, not a misconfiguration, not a
security finding. Roughly speaking most address space is unsigned.

**`invalid` splits two ways, and the split matters:**
- `reason: as` → a ROA covers this prefix and authorises **a different AS**. Possible hijack. Actionable.
- `reason: length` → correct AS, but the prefix is **more specific** than the ROA permits. Usually your own
  misconfiguration, and a different fix.

**`validation_unavailable` is not `not_found`.** If the validator is unreachable you get the former, and
NetClaw will not guess from routing or registry data.

**Registry data is allocation, not routing.** RDAP tells you who a block is *allocated to*, never who is
*announcing* it. Use `routing_announced_prefixes` for the latter.

**PeeringDB is self-reported.** No record means nobody filled the form, not that the network does not peer.

**Visibility is RIPE's collectors.** Low visibility has legitimate causes — scoped announcements, anycast,
no-export. The tool will not call it a leak, and neither should you without more evidence.

## Which tool owns what

| Question | Use |
|---|---|
| "Is this announcement RPKI-authorised?" | `rpki_validate` — **nothing else in NetClaw does this** |
| "Who holds this block? Abuse contact?" | `registry_lookup` / `registry_abuse_contact` |
| "What does this AS announce?" | `routing_announced_prefixes` |
| "Where does this AS peer?" | `peering_network` / `peering_presence` |
| "Everything about this resource" | `resource_report` |
| **"Quick: who owns this traceroute hop, and where is it?"** | **`gtrace-ip-enrichment`** — not this |
| **"Can the outside reach us? Measure from N countries"** | **`globalping-external-checks`** (R8) — not this |

Those last two are load-bearing boundaries, not politeness. `gtrace` already does ASN/geo/rDNS enrichment
and this feature deliberately does not duplicate it (Principle VII). Globalping *measures*; this *looks up*.

## Being a good citizen

These are volunteer-funded services (RIPE NCC, PeeringDB). The server holds itself to **≤ 4 requests/second
per source, strictly serial** — no parallel fan-out, even for `resource_report`, which runs its four
sub-queries one after another.

That is deliberately slower than possible. Against free community infrastructure, being over-polite costs
latency nobody notices; being under-polite costs the integration for everyone.

Repeated lookups come from an in-memory cache with per-source TTLs — RPKI 5 minutes, RDAP 24 hours — and a
cached response says so and reports its age. Pass `fresh=true` when a ROA was just published.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `input_refused` on a private address | Working as designed — RFC1918/reserved input is never sent to a public registry | Use an internal tool; this feature is for public resources |
| `source_refused` naming ARIN | Measured: `rdap.arin.net` resets the connection from this host | Automatic fallback via IANA bootstrap / `rdap.org`. Retry from another path before concluding ARIN is broken |
| Everything is `not_found` | Probably correct — most space is unsigned | Confirm with a known-signed prefix like `1.1.1.0/24` + `AS13335` |
| `validation_unavailable` | Validator unreachable | Not a `not_found`. Check egress to `rpki-validator.ripe.net` |
| Results feel stale | Per-source TTL cache | Check `cached` / `cache_age_seconds`; pass `fresh=true` |
| `rate_limited` | Self-imposed 4/s ceiling reached | Expected under heavy batch use. It backs off; do not raise `BGP_INTEL_MAX_RPS` |
