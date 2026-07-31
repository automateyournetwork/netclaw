# Quickstart: Globalping External Checks

**Feature**: 079 | **Roadmap**: R8

## Setup

1. Get a token at [globalping.io](https://www.globalping.io) (free; raises the hourly allowance from 250 to
   500 measurements).
2. Add it to your gitignored `.env`:

   ```bash
   GLOBALPING_TOKEN=your_token_here
   ```

3. Install the component:

   ```bash
   ./scripts/install.sh        # select "globalping", or the observability profile
   ```

   Nothing is downloaded or compiled — this is a remote endpoint, so "install" is registration only.

## First check

Ask NetClaw:

> "Can the outside world reach example.com right now?"

NetClaw runs a ping from geographically diverse probes and reports per-probe latency with each probe's
location attached.

## The three answers you need to tell apart

This is the whole reason the skill exists.

| NetClaw says | It means | What to do |
|---|---|---|
| "5 of 5 probes reached it, 12-180ms depending on region" | Reachable, with real geographic variance | Nothing |
| "0 of 5 probes reached it" | **Genuinely unreachable from outside** | Investigate — this is a finding |
| "The measurement did not run — no probes matched that location" | **Nothing was tested** | Broaden the location and ask again |

The third one is the trap. It arrives looking like a failure and says nothing at all about your service.

## Useful questions

```
"Compare latency to our site from Europe and Asia."
"Has the DNS change for example.com propagated globally?"
"Traceroute to example.com from Japan — where does it break?"
"What's my remaining Globalping budget?"
"Are there any probes in AS3320?"
```

## What it will refuse, and why

```
"Ping 10.0.0.1 from Globalping"
→ Refused. Globalping measures public endpoints only. Use pyATS or
  multivendor-cli for internal addresses.
```

NetClaw refuses this **before** calling out, so your internal addressing is never transmitted. RFC1918,
`localhost`, link-local and private IPv6 are all refused locally.

## Location syntax

| To express | Write | Note |
|---|---|---|
| A city in a country | `London+UK` | `+` is AND |
| Several distinct places | `["London","Frankfurt"]` | an array, not a comma-string |
| A cloud provider in a region | `Amazon+Germany` | |
| Diverse global spread | `world` | |
| An autonomous system | `AS3320` | |

**`London,UK` does not work** — a comma inside one string fails. Use `+` or an array.

**`AS13335` never works** even though the vendor's own documentation uses it as an example: Cloudflare hosts
no probes. If an ASN filter returns "no probes found", the usual cause is that the ASN has no probes, not
that your syntax is wrong. Ask NetClaw to check `locations` first.

## Budget

**500 probe-measurements per hour** with a token, rolling. **The cost of a test is its probe count** — a
50-probe global test spends 50 units, a 3-probe check spends 3. Asking for the budget (`limits`) is free.

Practical consequence: **`limit` is the dial that spends money.** Use 3-5 for a spot check, 10-20 when
geographic spread is the actual question, and treat anything above 20 as a deliberate choice. Five 100-probe
`world` tests exhaust the hour.

## When to use something else

| Question | Tool |
|---|---|
| "Can the outside world reach this, right now, from many places?" | **Globalping** |
| "Is this worse than last week?" | ThousandEyes (baselines, continuous) |
| "What path does traffic take from *this host*?" | `gtrace` |
| "Is the device itself healthy?" | pyATS / multivendor-cli / SuzieQ |

## One privacy note

Every Globalping tool requires a `context` field — a short natural-language explanation of *why* the call is
being made, which the vendor uses for analytics. NetClaw sends a generic, task-shaped sentence with no
customer name, internal hostname or ticket reference in it. If sending any intent description to a third
party is unacceptable in your environment, do not enable this integration.

## Verify

```bash
./tests/globalping/run-tests.sh    # offline, spends no measurements
./tests/globalping/live-api.sh     # opt-in, spends ~10 measurements
```
