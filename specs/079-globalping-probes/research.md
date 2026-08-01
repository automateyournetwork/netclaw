# Phase 0 Research: Globalping Global Probe Measurement

**Feature**: 079-globalping-probes | **Date**: 2026-07-31
**Purpose**: Settle the transport, the tool surface, the budget model and the location syntax before Phase 1.

Everything below was measured against the live endpoint with a real token. Nothing is inferred from
documentation — and in one case (R5) the vendor's own schema is wrong.

---

## R1 — Transport and authentication

```
POST https://mcp.globalping.dev/mcp
Accept: application/json, text/event-stream
Authorization: Bearer <GLOBALPING_TOKEN>
```

| Condition | Result |
|---|---|
| No token | **401** |
| Bearer token | **200**, `serverInfo: {name: "Globalping MCP", version: "1.0.2"}` |

Streamable HTTP with SSE responses; the session id arrives in the `Mcp-Session-Id` response header and must
be echoed on subsequent requests. Protocol version negotiated: `2025-06-18`.

**Decision**: register as a **remote MCP server**, no NetClaw-authored code. This is the established pattern
for Datadog and DevNet content search.

**Rationale**: the endpoint is official and maintained by jsDelivr. Vendoring a client would mean owning a
reimplementation of a server that already works, and would convert every upstream change into a NetClaw code
change. It also means terms changes are a registration edit, not a refactor.

**Alternative considered**: wrapping the underlying REST API (`https://api.globalping.io/v1/`) in a NetClaw
server. Rejected — it duplicates the official MCP for no gain, and the REST API is only useful here as a
cross-check (which is exactly how R4 and R5 below used it).

---

## R2 — The tool surface: 12 tools, 5 of which matter

| Tool | Args beyond `context` | Category |
|---|---|---|
| `ping` | target, locations, limit, packets | **measurement** |
| `traceroute` | target, locations, limit, protocol, port | **measurement** |
| `dns` | target, locations, limit, queryType, resolver, trace | **measurement** |
| `mtr` | target, locations, limit, protocol, port, packets | **measurement** |
| `http` | target, locations, limit, method, protocol, path, port, query | **measurement** |
| `limits` | — | meta, worth calling |
| `locations` | — | meta, worth calling |
| `compareLocations` | — | meta, self-describing |
| `help` | — | meta, self-describing |
| `authStatus` | — | meta, self-describing |
| `get_more_tools` | — | meta, self-describing |
| `getMeasurement` | id | retrieve a prior result |

**Decision**: document the five measurement tools plus `limits` and `locations`. The other four are
self-describing and need no NetClaw guidance — documenting them would add skill length without adding
capability.

**Note**: six of twelve tools take *only* `context`, so the advertised tool count overstates the capability
by more than half. Worth knowing when comparing this integration's "12 tools" against others'.

---

## R3 — The mandatory `context` analytics field

Every tool declares `context` as **required**, described as:

> "Explain why you are calling this tool and how it fits into the user's overall goal. This parameter is used
> for analytics and user intent tracking. YOU MUST provide 15-25 words (count carefully). NEVER use first
> person... NEVER include sensitive information such as credentials, passwords, or personal data."

**Measured: it is not enforced.** A `tools/call` with `context` omitted returned a normal successful
measurement.

**Decision**: always send a **generic, task-shaped** value — no customer name, internal hostname, ticket
reference, or topology detail. Do not exploit the non-enforcement.

**Rationale**: it is the documented contract, and depending on unenforced-required behaviour is fragile — the
server could begin enforcing it at any time and every call would break at once. But the non-enforcement is
recorded because it is the escape hatch if the field ever becomes a disclosure concern.

**Worth stating plainly to operators**: this field is natural-language operator intent leaving NetClaw's
boundary for a third party. Every other NetClaw integration sends only the data needed to perform the
operation. This one asks for a description of *why*. That is unusual enough to disclose rather than bury.

---

## R4 — Budget: 500 probe-measurements/hour, charged PER PROBE

| Condition | Limit | Window |
|---|---|---|
| Authenticated (token) | **500 measurements** | rolling 1 hour |
| Unauthenticated (per IP) | **250 measurements** | rolling 1 hour |

Confirmed against both the MCP `limits` tool and the REST endpoint `GET /v1/limits`, which agree exactly.

### A correction: cost is per probe, not per call

**An earlier version of this research concluded that one call costs one measurement regardless of probe
count. That was wrong**, and the error is recorded here rather than quietly overwritten because the wrong
conclusion had already propagated into the spec, the skill and the task list before a controlled test caught
it.

The mistake: 35 exploratory calls moved `remaining` from 500 to 465, and I read the matching arithmetic as
proof of per-call billing. It was a coincidence — most of those calls happened to use `limit: 1`.

Controlled measurement, one call at a time with `limits` read either side:

| `limit` | remaining before | after | **cost** |
|---|---|---|---|
| 1 | 439 | 438 | **1** |
| 5 | 438 | 433 | **5** |
| 20 | 459 | 439 | **20** |

**Cost equals the probe count.** A `limits` call itself costs nothing (433 → 433 across two consecutive
calls), so meta queries are free.

**Decision**: choose `limit` deliberately — it is the thing being spent. Use the smallest probe count that
answers the question: 3-5 for a spot check, 10-20 when geographic spread is the point, and treat anything
above 20 as a decision worth making consciously. A single 100-probe `world` test costs a fifth of the hourly
allowance.

**Consequence for the skill**: economy matters here just as it does for spec 078's PSIRT budget. The two
specs need the *same* instinct, not opposite ones — which is what the earlier wrong conclusion had asserted.
The genuine difference is only in what a unit buys: PSIRT charges per distinct query (so de-duplicate),
Globalping charges per probe (so right-size `limit`).

---

## R5 — Location syntax, and the vendor's own broken example

| Filter | Result |
|---|---|
| `London+UK` | **200** — `+` is AND |
| `Amazon+Germany` | **200** — cloud provider + country |
| `US` | **200** |
| `world` | **200** — diverse global set |
| `AS3320`, `AS16509`, `AS174` | **200** — ASN form works |
| `["London","Frankfurt"]` (array) | **200** — array expresses multiple locations |
| `London,UK` (comma in one string) | **422 `no_probes_found`** |
| `AS13335` | **422 `no_probes_found`** |
| `AS15169` | **422 `no_probes_found`** |

**`AS13335` appears as an example in the vendor's own tool schema description, and it never works.**

Cross-checked against ground truth via `GET https://api.globalping.io/v1/probes`: **4,833 probes across
1,390 distinct ASNs**. AS13335 (Cloudflare) and AS15169 (Google) host **no probes**; AS3320, AS16509 and
AS174 do.

**Decision**: ASN syntax is correct and supported. `AS13335` fails for lack of probes, not for syntax. The
skill must say so explicitly, and must not repeat the vendor's example.

**Why this matters more than a documentation nit**: an earlier NetClaw scan recorded this as an unresolved
"location syntax bug". It was two separate things conflated — a real syntax issue (`London,UK`) and a
probe-availability fact (`AS13335`). Anyone learning the syntax from the vendor's schema will try
`AS13335` first, get `no_probes_found`, and conclude the ASN form is broken. That wrong lesson then makes
every future ASN-scoped measurement look impossible.

---

## R6 — The three-way distinction, measured

This is the feature's core, so each state was produced deliberately:

| Input | Response | Correct interpretation |
|---|---|---|
| `AS13335` | 422 `no_probes_found` | **The measurement never ran.** No information about the target. |
| `this-does-not-exist-netclaw-test.invalid` | `finished`, **0/1 successful** | **The target did not answer.** A real finding, returned as success. |
| `192.168.1.1` | Refused: "private IPv4 address (RFC1918)" | **Out of scope.** |
| `10.0.0.1` | Refused: "private IPv4 address (RFC1918)" | Out of scope. |
| `localhost` | Refused: "is a localhost domain" | Out of scope. |
| `172.16.5.5` | Refused: "private IPv4 address (RFC1918)" | Out of scope. |
| `fe80::1` | Refused: "private IPv6 address" | Out of scope. |

Two things follow.

**First**: an unresolvable target is *not* an error. It returns a completed measurement with zero successful
probes — which is the correct design, because "nobody could reach it" is exactly the answer being sought.
But it means "0 successful" and "no probes found" arrive as different shapes and must be read differently.
An agent that treats both as "empty result" will report a location-filter mistake as a global outage.

**Second**: Globalping validates private targets itself, with good error text. NetClaw should *still* refuse
them locally (FR-009), because by the time the server rejects it, an internal hostname or address has already
been transmitted to a third party. The refusal is about disclosure, not about correctness.

---

## R7 — Composition with what NetClaw already has

**Decision**: position by direction of measurement, not by feature list.

- **Globalping** — from the internet, toward a public target. Free, ad-hoc, ~4,800 vantage points.
- **`gtrace`** — from *this host*, outward. One vantage point: NetClaw's own.
- **ThousandEyes** — enterprise agents, continuous, with historical baselines. Paid.
- **pyATS / multivendor-cli / SuzieQ** — inside the administrative domain, device-facing.

**Rationale**: "which tool for external checks" is ambiguous between Globalping, gtrace and ThousandEyes, and
the honest discriminator is not capability but *where the measurement originates* and *whether a baseline is
needed*. Globalping answers "can the outside world reach this, right now, from many places". It cannot answer
"is this worse than last week" — that needs ThousandEyes.

---

## Summary of what changed versus the spec's assumptions

| Assumption going in | Finding |
|---|---|
| "12 tools" is the capability | **5 measurement tools**; 6 of 12 take only `context` |
| Location syntax has an unresolved bug | Two conflated issues: comma-in-string genuinely fails; `AS13335` is correct syntax with **no probes** — and it is the vendor's own example |
| Rate limits work like spec 078's | **Charged per probe, not per call** — `limit: 20` costs 20 of 500. An earlier draft of this research concluded per-call billing and was wrong; a controlled test corrected it. Economy matters, same as 078 |
| Auth is token or OAuth | Token confirmed working; OAuth not needed |
| — (unanticipated) | A **mandatory natural-language analytics field** ships operator intent to a third party, and is **not actually enforced** |
