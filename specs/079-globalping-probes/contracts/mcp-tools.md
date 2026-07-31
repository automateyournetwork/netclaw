# Contract: Globalping Remote MCP Tool Surface

**Feature**: 079 | **Transport**: remote streamable HTTP + SSE | **Server id**: `globalping`
**Endpoint**: `https://mcp.globalping.dev/mcp` | **Server version observed**: `1.0.2`

This is a **consumed** contract, not one NetClaw defines. Everything here was read off the live endpoint on
2026-07-31. NetClaw's obligations are in the right-hand column of each table.

## Rules binding every call

1. **Bearer token required** — `Authorization: Bearer $GLOBALPING_TOKEN`. Absent → **401**.
2. **Session id must be echoed** — `Mcp-Session-Id` from the initialize response, on every later request.
3. **Public targets only** — private/internal targets are refused, and NetClaw refuses them *locally first*.
4. **`context` on every call** — sanitised, generic, 15-25 words (see below).
5. **Cost equals probe count** against the 500/hour budget — `limit: 20` spends 20 units. Meta calls are free.

---

## The five measurement tools

All share `target`, `locations`, `limit`, `context`.

| Tool | Additional args | Use for |
|---|---|---|
| `ping` | `packets` | Reachability and round-trip latency |
| `traceroute` | `protocol`, `port` | Path from a probe toward the target |
| `dns` | `queryType`, `resolver`, `trace` | Resolution and propagation |
| `mtr` | `protocol`, `port`, `packets` | Per-hop loss and latency combined |
| `http` | `method`, `protocol`, `path`, `port`, `query` | Application-layer reachability, status, timing |

`limit` is the probe count: **1-100, default 3**.

---

## The three response shapes that must never be conflated

This is the contract's most important section and the reason the feature exists.

### 1. `no_probes_found` — the measurement never ran

```
isError: true
"Globalping API error (422): {"error":{"type":"no_probes_found",
                              "message":"No matching IPv4 probes available."}}"
```

**Means**: no probe matched the location filter. **Carries no information about the target whatsoever.**

**NetClaw MUST**: say the measurement did not run, and suggest a broader filter.
**NetClaw MUST NOT**: report an outage, report unreachability, or call it a syntax error.

Reproduce with `locations: "AS13335"` — correct syntax, zero probes.

### 2. `finished` with 0 of N successful — the target did not answer

```
isError: false
Status: finished
Probes: 1
- Successful Probes: 0/1
```

**Means**: probes ran and got nothing back. **This is a real finding** and the answer the operator wanted.

**NetClaw MUST**: report it as unreachable from those probe locations, naming them.

Reproduce with any unresolvable target.

### 3. Locally refused — out of scope

Globalping rejects these itself with good error text:

| Target | Server message |
|---|---|
| `192.168.1.1`, `10.0.0.1`, `172.16.5.5` | "is a private IPv4 address (RFC1918)" |
| `localhost` | "is a localhost domain" |
| `fe80::1` | "is a private IPv6 address" |

**NetClaw MUST refuse these before calling out** (FR-009). Not for correctness — the server would reject
them anyway — but because by the time the server answers, an internal address or hostname has already
been sent to a third party. The refusal is a disclosure control.

**NetClaw MUST** name the internal tool to use instead: pyATS, multivendor-cli, or gtrace.

---

## Location filter syntax, as measured

| Form | Example | Result |
|---|---|---|
| Single term | `US`, `London`, `Greece` | works |
| AND with `+` | `London+UK`, `Amazon+Germany` | works |
| Array of terms | `["London","Frankfurt"]` | works |
| Global spread | `world` | works |
| ASN | `AS3320`, `AS16509`, `AS174` | works |
| **Comma in one string** | `London,UK` | **fails** — `+` is the AND separator |
| **ASN with no probes** | `AS13335`, `AS15169` | **fails** — correct syntax, no probes exist |

**`AS13335` is used as an example in the vendor's own tool schema and never works.** Cloudflare hosts no
probes. Ground truth from `GET https://api.globalping.io/v1/probes`: 4,833 probes across 1,390 ASNs;
AS13335 and AS15169 are not among them.

NetClaw's skill must not repeat the vendor's example, and must explain that an ASN failure usually means
"no probes there" rather than "wrong syntax".

---

## The `context` parameter

Declared **required** on every tool:

> "Explain why you are calling this tool and how it fits into the user's overall goal. This parameter is used
> for analytics and user intent tracking. YOU MUST provide 15-25 words... NEVER include sensitive
> information such as credentials, passwords, or personal data."

**Measured: not enforced.** A call with `context` omitted succeeds normally.

**NetClaw's contract with itself**:
- Always send a value (it is the documented contract; unenforced-required behaviour is fragile).
- Make it **generic and task-shaped**. No customer name, internal hostname, ticket reference, or topology.
- Disclose in the skill that it reaches a third party.

Acceptable: *"Validating external reachability and latency distribution for a public service endpoint during
operational troubleshooting across multiple regions."*

Not acceptable: anything naming a customer, an internal host, a ticket, or the topology.

---

## Meta tools

| Tool | NetClaw guidance |
|---|---|
| `limits` | **Document.** Budget and reset before a large investigation. Note: echoes an 8-char token fragment. |
| `locations` | **Document.** Probe availability — answers "are there probes there?" before a narrow filter wastes a call. |
| `getMeasurement` | Document briefly — retrieve a prior result by id. |
| `compareLocations`, `help`, `authStatus`, `get_more_tools` | **Do not document.** Self-describing; guidance would add length without capability. |

Six of the twelve advertised tools take only `context`, so "12 tools" overstates the capability by more than
half. Worth remembering when comparing integration sizes.

---

## Budget

| Condition | Limit | Window |
|---|---|---|
| Authenticated | **500 probe-measurements** | rolling 1 hour |
| Unauthenticated (per IP) | **250 probe-measurements** | rolling 1 hour |

Verified via both the `limits` tool and `GET /v1/limits`, which agree.

**Cost equals the probe count**, confirmed by controlled test (one call at a time, `limits` read either
side):

| `limit` | cost |
|---|---|
| 1 | **1** |
| 5 | **5** |
| 20 | **20** |
| a `limits` call | **0** |

**Strategy**: `limit` is the thing being spent, so choose it deliberately — 3-5 for a spot check, 10-20 when
geographic spread is the point, above 20 as a conscious decision. A single 100-probe `world` test costs a
fifth of the hourly allowance.

> **Correction on record**: an earlier pass concluded one call costs one unit regardless of probe count,
> inferred from 35 exploratory calls moving `remaining` 500 → 465. That match was a coincidence — most of
> those calls used `limit: 1`. Guidance built on "breadth is free" was wrong and has been corrected
> throughout. The same economy instinct spec 078 required applies here; the two differ only in what a unit
> buys.

## Environment contract

| Variable | Purpose | Required |
|---|---|---|
| `GLOBALPING_TOKEN` | Bearer token; raises the hourly allowance from 250 to 500 | recommended |

Without it the endpoint returns 401 through the MCP. (The underlying REST API allows anonymous use at
250/hour per IP, but the MCP endpoint itself requires auth.)
