---
name: globalping-external-checks
description: "Measure a public endpoint from thousands of probes worldwide - ping, traceroute, DNS, MTR and HTTP from real vantage points on the internet. Use when asked whether the outside world can reach a service, to compare latency between regions, to check DNS propagation, or to answer 'is it us or the internet?'. Public targets only."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "env": ["GLOBALPING_TOKEN"] } } }
---

# Globalping External Checks

Every other device-facing tool NetClaw has looks at the network **from the inside**. This one looks at it
**from the outside** — ~4,800 probes across ~1,390 autonomous systems, measuring *toward* a public target.

It is the tool for "the router is fine, so why can't anyone reach us?"

## Read this first — three ways to get nothing back

These look similar and mean completely different things. Getting them confused is the single failure mode
this skill exists to prevent.

| Response | What it means | What to say |
|---|---|---|
| `no_probes_found` (422) | **The measurement never ran.** No probe matched the location filter. | "Nothing was tested — no probes matched that location. Retrying with a broader filter." |
| `finished`, **0 of N successful** | **The target did not answer.** Probes ran and got nothing. | "Unreachable from all N probes — this is a real finding." |
| Target refused before calling | **Out of scope.** Private/internal address. | "Globalping only measures public endpoints. Use pyATS/multivendor-cli instead." |

**`no_probes_found` is NOT an outage.** It arrives looking like a failure and tells you nothing whatsoever
about the target. Reporting it as unreachability escalates an incident that does not exist. When you see it,
say the measurement did not run, widen the location, and try again.

**0 of N successful IS a finding**, and a valuable one. The measurement succeeded; the answer is "nobody out
there could reach it." Report it as the answer, not as an error.

## Public targets only — refuse internal ones before calling out

**Check the target before every call.** Refuse locally, do not let Globalping refuse it for you:

| Refuse | Why |
|---|---|
| `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` | RFC1918 private |
| `127.0.0.0/8`, `localhost` | Loopback |
| `169.254.0.0/16`, `fe80::/10` | Link-local |
| `fc00::/7` | Private IPv6 |
| Any internal-only hostname | Not resolvable from the internet, and discloses naming |

Globalping rejects these server-side too — but by then the address or hostname **has already been sent to a
third party**. Refusing locally is a disclosure control, not a correctness one.

When refusing, **name the tool to use instead**:

> "10.0.0.1 is a private address — Globalping measures from the public internet and can't reach it. For
> internal reachability use pyATS (`run_show_command` with ping) or multivendor-cli; for a path from this
> host outward, use gtrace."

## Available Tools

Five measurement tools. All take `target`, `locations`, `limit` and `context`.

### 1. `ping` — reachability and latency

```bash
python3 $MCP_CALL globalping-mcp ping '{
  "target":"example.com", "locations":"world", "limit":10, "packets":3,
  "context":"Validating external reachability and latency distribution for a public service endpoint during operational troubleshooting."
}'
```

### 2. `traceroute` — the path from a probe toward the target

```bash
python3 $MCP_CALL globalping-mcp traceroute '{
  "target":"example.com", "locations":["Japan","Germany"], "limit":2,
  "context":"Identifying the network path and potential failure point toward a public endpoint from two distant regions."
}'
```

### 3. `dns` — resolution and propagation

```bash
python3 $MCP_CALL globalping-mcp dns '{
  "target":"example.com", "locations":"world", "limit":15, "queryType":"A",
  "context":"Verifying global DNS propagation consistency for a public domain record following a planned change."
}'
```

### 4. `mtr` — per-hop loss and latency together

```bash
python3 $MCP_CALL globalping-mcp mtr '{
  "target":"example.com", "locations":"Singapore", "limit":2,
  "context":"Correlating per-hop packet loss with latency toward a public endpoint to localise a degradation."
}'
```

### 5. `http` — application-layer reachability, status and timing

```bash
python3 $MCP_CALL globalping-mcp http '{
  "target":"example.com", "locations":"world", "limit":10, "method":"GET", "path":"/",
  "context":"Confirming HTTP availability and response timing for a public web endpoint across multiple global regions."
}'
```

### 6. `limits` — check the budget before a big investigation

```bash
python3 $MCP_CALL globalping-mcp limits '{
  "context":"Reviewing remaining measurement allowance before planning a broad multi-region reachability investigation."
}'
```

### 7. `locations` — are there probes where you want to measure from?

```bash
python3 $MCP_CALL globalping-mcp locations '{
  "context":"Checking probe availability in a target region before issuing a narrowly scoped measurement request."
}'
```

Call this **before** using a narrow filter. It is the difference between a wasted call and a real answer.

`getMeasurement` retrieves a prior result by id. `help`, `authStatus`, `compareLocations` and
`get_more_tools` are self-describing — use them if you want, they need no guidance here.

## Location syntax

| To express | Write | |
|---|---|---|
| A city within a country | `London+UK` | `+` means AND |
| Several distinct places | `["London","Frankfurt"]` | an **array** |
| A cloud provider in a region | `Amazon+Germany` | |
| Diverse global spread | `world` | |
| An autonomous system | `AS3320` | |
| A country or region | `US`, `Europe`, `Greece` | |

**`"London,UK"` does not work.** A comma inside a single string fails. Use `+` for AND, or an array for
several locations.

**`AS13335` never returns probes** — even though it appears as an example in Globalping's own tool
documentation. Cloudflare hosts no probes. AS15169 (Google) hosts none either. AS3320, AS16509 and AS174 do.

So when an ASN filter returns `no_probes_found`, the overwhelmingly likely cause is **that ASN has no
probes**, not that the syntax is wrong. Check `locations` rather than rewriting the filter. Only ~1,390 of
the internet's autonomous systems host a probe.

## Budget: `limit` is what you spend

**500 probe-measurements/hour** with a token (250/hour unauthenticated, per IP). Rolling one-hour window,
shared across everything using the token.

**The cost of a call equals its probe count.** `limit: 1` spends 1, `limit: 5` spends 5, `limit: 20` spends
20. Calling `limits` to check the budget is free.

So `limit` is the dial that spends the allowance — choose it for the question being asked:

| Question | Suggested `limit` | Cost |
|---|---|---|
| "Is it up?" — quick spot check | 3-5 | 3-5 |
| "Is it slow from certain regions?" — geographic spread | 10-20 | 10-20 |
| "Has DNS propagated globally?" — wide sample genuinely needed | 20-30 | 20-30 |
| Anything above 30 | make it a conscious decision | 30+ |

Five 100-probe `world` tests exhaust the hour. Don't reach for `limit: 100` because it is available.

Equally, **don't loop** where one call would do: ten separate 3-probe pings cost the same 30 units as one
30-probe ping, but give you ten small unattributed samples instead of one broad comparable set. Prefer one
right-sized call.

Call `limits` first before a big investigation — it costs nothing and tells you what you have.

## Always attribute results to a location

Every latency, loss and resolver figure must be reported **with the probe location that produced it**.
Geographic variance is the entire reason to use this tool; an unattributed average destroys the signal.

**Never generalise one probe into a regional claim.** One probe in Frankfurt is one probe in Frankfurt, not
"Europe".

Good: *"Reachable from 9 of 10 probes. 12ms from Frankfurt, 18ms from London, 210ms from São Paulo, timeout
from Sydney."*

Bad: *"Average latency 68ms."* — hides that one region is broken.

## DNS: report disagreement as a split

Resolvers disagreeing **is** the answer during a propagation check. Report the split, never an average or a
single winner.

Good: *"11 of 15 probes return the new address (203.0.113.10); 4 still return the old one (198.51.100.5) —
Singapore, Mumbai, Sydney, Tokyo. Propagation is incomplete in APAC."*

## When to use something else

| Question | Tool |
|---|---|
| "Can the outside world reach this, right now, from many places?" | **this skill** |
| "Is this worse than last week? What's the trend?" | **ThousandEyes** — continuous, baselined, paid |
| "What path does traffic take from *this host* outward?" | **gtrace** — one vantage point, ours |
| "Is the device/interface/protocol itself healthy?" | **pyATS**, **multivendor-cli**, **SuzieQ** |

Globalping is ad-hoc and free with ~4,800 vantage points. It cannot tell you whether today is worse than
last Tuesday — it holds no history. If the question involves a baseline, it is a ThousandEyes question.

## Measurement, not scanning

Use this to measure **infrastructure the operator runs**. Do not sweep, enumerate, or probe third-party
infrastructure, and do not use it to survey hosts the operator has no responsibility for. If a request looks
like reconnaissance of somebody else's estate rather than validation of the operator's own service, say so
and stop.

## About the `context` field

Every tool requires a `context` argument: a 15-25 word, third-person description of *why* the call is being
made. Globalping states it is used for "analytics and user intent tracking".

**This text leaves NetClaw and reaches a third party.** Keep it generic and task-shaped:

- **Never include**: customer or company names, internal hostnames, IP addressing, ticket or change numbers,
  topology detail, or anything about the operator's business.
- **Do include**: the shape of the task only — "validating external reachability", "verifying DNS
  propagation", "comparing regional latency".

The examples in this skill are all safe to reuse verbatim.

(For reference: the server currently accepts calls with `context` omitted despite marking it required. Send it
anyway — it is the documented contract, and relying on unenforced behaviour would break every call at once if
that changed.)

## One more credential note

`limits` output includes a short fragment of the token (first 8 characters after a prefix). Don't paste raw
`limits` output into a ticket, chat channel, or anywhere public.
