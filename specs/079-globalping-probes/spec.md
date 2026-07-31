# Feature Specification: Globalping Global Probe Measurement

**Feature Branch**: `079-globalping-probes`
**Created**: 2026-07-31
**Status**: Draft
**Roadmap**: R8 — *"Highest value-per-effort item in the scan"*

## Overview

NetClaw can see the network from the inside. It cannot see itself from the outside.

Every device-facing integration NetClaw has — pyATS, the multivendor driver, gNMI, SuzieQ, Batfish —
answers questions from *within* the operator's administrative domain. When a user reports "the site is slow
from Singapore" or "our DNS change hasn't propagated", NetClaw currently has no way to check. It can prove
the router is healthy and still be unable to say whether anyone outside can reach it.

Globalping is a free public measurement network — ~4,800 probes across ~1,390 autonomous systems — exposed
as an official remote MCP server. It runs ping, traceroute, DNS, MTR and HTTP tests *from* those probes
*toward* a public target. Zero install, no vendored code, one bearer token.

This feature registers that server, wraps it in a skill, and — the part carrying the actual engineering
weight — teaches NetClaw to distinguish three different kinds of "nothing came back".

## The distinction this feature exists to protect

All measured live on 2026-07-31. These three outcomes look similar and mean completely different things:

| What happened | How it appears | What it means |
|---|---|---|
| No probe matched the location filter | HTTP 422 `no_probes_found` | **The measurement never ran.** Says nothing about the target. |
| Probes ran, target did not answer | `finished`, `0/N successful probes` | **The target is unreachable from there.** A real signal. |
| Target is private/internal | Refused before any probe | **Out of scope.** Globalping is outside-in only. |

Conflating the first with the second is the failure mode. `no_probes_found` from a too-narrow location
filter looks exactly like a total outage, and an agent that reports it as one will escalate an incident
that does not exist. This is the same class of error as spec 078's "no advisories ≠ not vulnerable", and it
gets the same treatment: separate, explicitly-named outcomes, and a skill that states the difference in
words.

## Clarifications

### Session 2026-07-31

- Q: Vendored server or remote registration? → A: Remote registration, no NetClaw-authored server code — the official endpoint is the supported path, matching the Datadog and DevNet content-search pattern.
- Q: What goes in the mandatory `context` analytics field? → A: A generic, task-shaped sentence containing no customer name, internal hostname, ticket ID, or topology detail (FR-012).
- Q: Should NetClaw pre-validate targets before calling out? → A: Yes — private/internal targets are refused locally in the skill, because sending an internal hostname to a third party is a disclosure even when the call then fails.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Is it us, or is it the internet? (Priority: P1)

An operator's users report a public service is unreachable. NetClaw's internal checks are all green.

**Why this priority**: It is the question NetClaw structurally cannot answer today, and the reason R8 was
rated highest value-per-effort. Everything else here is a variation on it.

**Independent test**: point it at a known-good public target and at an unresolvable one; the first returns
attributed per-probe latency, the second returns 0 successful probes as a *finding*.

**Acceptance Scenarios**

1. **Given** a public target, **When** the operator asks whether it is reachable from outside, **Then**
   NetClaw runs a measurement from geographically diverse probes and reports per-probe success/failure with
   latency.
2. **Given** probes that ran and got no answer, **When** results return `0/N successful`, **Then** NetClaw
   reports the target as unreachable from those locations — a positive finding, not an error.
3. **Given** a location filter matching no probe, **When** the API returns `no_probes_found`, **Then**
   NetClaw states that **the measurement did not run** and suggests a broader filter — and MUST NOT report
   it as an outage.
4. **Given** an internal target (`10.0.0.1`, `localhost`, an internal hostname), **When** an external check
   is requested, **Then** NetClaw refuses locally, explains that Globalping only measures public endpoints,
   and names the internal tool to use instead.

### User Story 2 — Geographic latency comparison (Priority: P2)

"Our European users say it's fast and our Asian users say it's slow." NetClaw measures from both.

**Independent test**: request two named regions and confirm both appear with locations attached.

**Acceptance Scenarios**

1. **Given** two or more regions, **When** asked to compare, **Then** NetClaw runs from probes in each and
   reports latency side by side with the probe location attributed to every figure.
2. **Given** a single-probe result, **When** NetClaw reports latency, **Then** it does not generalise one
   probe into a regional claim.

### User Story 3 — DNS propagation and resolver disagreement (Priority: P2)

After a DNS change, "has it propagated?" is a question about many resolvers, not one.

**Independent test**: query a record from multiple probes and confirm disagreement is reported as a split.

**Acceptance Scenarios**

1. **Given** a recently changed record, **When** asked whether it has propagated, **Then** NetClaw queries
   from multiple global probes and reports which return the old value and which the new.
2. **Given** resolvers that disagree, **When** results differ, **Then** NetClaw reports the split rather
   than averaging or picking one.

### User Story 4 — Stay inside the measurement budget (Priority: P2)

**Independent test**: confirm budget accounting is per probe — `limit: 5` decrements by 5, and a `limits` call by 0.

**Acceptance Scenarios**

1. **Given** a budget of 500 probe-measurements/hour, **When** NetClaw plans a test, **Then** it chooses
   `limit` deliberately, because **the cost of a call equals its probe count** — a 100-probe test spends a
   fifth of the hourly allowance.
2. **Given** a large investigation about to start, **When** the operator asks, **Then** NetClaw reports
   remaining budget and reset time first.

### Edge Cases

- Correct syntax, no probes (`AS13335` — Cloudflare has none) → `no_probes_found`, reported as "no probes
  there", never as a syntax error and never as an outage.
- Comma-separated locations in a single string (`"London,UK"`) → fails. `+` is the AND separator.
- A target that does not resolve → measurement completes with 0 successful probes. A real result.
- Token absent → 401. NetClaw reports the missing variable by name.
- Budget exhausted → report remaining/reset rather than retrying blindly.

## Requirements *(mandatory)*

### Functional Requirements

#### Registration and transport

- **FR-001**: The official remote endpoint `https://mcp.globalping.dev/mcp` MUST be registered as a remote
  MCP server. NetClaw MUST NOT author or vendor a server for this — the official endpoint is the supported
  path, matching the existing remote-MCP pattern (Datadog, DevNet content search).
- **FR-002**: Authentication MUST use a bearer token from `GLOBALPING_TOKEN`. The endpoint returns **401**
  without one.
- **FR-003**: A missing token MUST be reported by variable name, never by value (Principle XIII).

#### Capability surface

- **FR-004**: The skill MUST document the five measurement tools — `ping`, `traceroute`, `dns`, `mtr`,
  `http` — as the feature's actual capability.
- **FR-005**: The skill MUST document `limits` (budget) and `locations` (probe availability) as the two meta
  tools worth calling deliberately. The remaining four (`help`, `authStatus`, `compareLocations`,
  `get_more_tools`) are self-describing and need no NetClaw guidance.

#### The three-way distinction — the core of this feature

- **FR-006**: `no_probes_found` MUST be reported as **the measurement not having run**. NetClaw MUST NOT
  present it as an outage, as unreachability, or as a syntax error.
- **FR-006a**: On `no_probes_found`, NetClaw MUST suggest a broader location filter, because the usual cause
  is a filter narrower than probe coverage.
- **FR-007**: A completed measurement with **0 of N successful probes** MUST be reported as the target being
  unreachable from those probes — a positive finding, distinct from FR-006.
- **FR-008**: Every reported latency, loss or resolver figure MUST carry the probe location that produced it.
  An unattributed aggregate hides the geographic variance that is the entire reason to use this.
- **FR-008a**: NetClaw MUST NOT generalise a single probe's result into a regional or global claim.

#### Scope boundary — outside-in only

- **FR-009**: NetClaw MUST refuse private and internal targets **locally, before calling out**: RFC1918
  IPv4, loopback, link-local, private IPv6, and `localhost`. Globalping rejects these server-side too, but a
  local refusal prevents sending an internal address to a third party at all.
- **FR-009a**: A refusal MUST name the internal tool to use instead (pyATS, multivendor-cli, gtrace), rather
  than only saying no.
- **FR-010**: The skill MUST state that Globalping measures **from the internet toward a public target**, and
  is therefore complementary to — never a substitute for — NetClaw's inside-out tooling.

#### Location syntax

- **FR-011**: The skill MUST document the syntax as measured: `+` is AND (`London+UK`, `Amazon+Germany`); an
  **array** expresses multiple distinct locations (`["London","Frankfurt"]`); `world` selects a diverse
  global set; ASN form (`AS3320`) works. A **comma inside a single string fails**.
- **FR-011a**: The skill MUST warn that `AS13335`, used as an example **in the vendor's own tool schema**,
  never returns probes. Correct syntax with no probes is indistinguishable from bad syntax unless the reader
  has been told, and a wrong lesson learned from the vendor's own example is worse than no example.

#### The mandatory analytics field

- **FR-012**: Every measurement tool declares a required `context` parameter — a 15-25 word third-person
  explanation of *why* the call is being made, which the vendor states is used for "analytics and user intent
  tracking". NetClaw MUST supply a **generic, task-shaped** value containing no customer name, internal
  hostname, ticket reference, or topology detail.
- **FR-012a**: The skill MUST state plainly that this field leaves NetClaw's boundary and reaches a third
  party, so an operator can make an informed choice about using the integration at all.
- **FR-012b**: Measured: the server **accepts calls with `context` omitted** despite declaring it required.
  NetClaw MUST still send a sanitised value rather than exploiting that, because it is the documented
  contract and relying on unenforced-required behaviour is fragile — but the skill MUST record that omission
  works, since it is the fallback if the field ever becomes a disclosure concern.

#### Budget

- **FR-013**: Measured: **500 measurements/hour** authenticated, **250/hour per IP** unauthenticated, rolling
  1-hour reset. The skill MUST document both.
- **FR-013a**: Measured by controlled test: **cost equals the probe count.** `limit: 1` costs 1, `limit: 5`
  costs 5, `limit: 20` costs 20. Meta calls (`limits`) cost nothing. The skill MUST therefore direct NetClaw
  to choose the smallest `limit` that answers the question — 3-5 for a spot check, 10-20 when geographic
  spread is the point — and MUST NOT present breadth as free.
- **FR-014**: NetClaw MUST be able to report remaining budget and reset time via `limits` before a large
  investigation.

#### Composition

- **FR-015**: The skill MUST state the boundary against ThousandEyes: Globalping is free, global and ad-hoc;
  ThousandEyes is paid, enterprise, and continuously monitored with historical baselines. Use Globalping for
  "check it now from out there", ThousandEyes when a baseline or trend matters.
- **FR-016**: The skill MUST state the boundary against `gtrace`: gtrace traces from *this* host outward;
  Globalping traces from *elsewhere* inward.

#### Read-only

- **FR-017**: Every tool is read-only. This feature MUST introduce no device access and no writes.
- **FR-018**: The integration MUST be used as **measurement of infrastructure the operator runs**, not as
  scanning. The skill MUST NOT direct NetClaw to sweep, enumerate or probe third-party infrastructure.

#### Artifact coherence (Principle XI)

- **FR-019**: All of the following MUST be updated, none assumed: catalog entry, curated profile membership,
  install/enable path, registration in `config/openclaw.json`, **both** HUD entries (node list *and*
  annotation map), `SOUL.md` capability text, `README.md`/`TOOLS.md`, `.env.example`.
- **FR-020**: `python3 scripts/reconcile-mcp.py` MUST exit 0 across all four surfaces.

### Key Entities

- **Measurement** — one call: a type (ping/traceroute/dns/mtr/http), a public target, a location filter, a
  probe count. Costs exactly one unit of budget.
- **Probe** — a measurement source, attributed by city, country, ASN and network. ~4,800 exist across ~1,390
  ASNs.
- **Outcome** — one of: `completed` (probes ran, results attributed), `no_probes_found` (never ran),
  `target_refused` (private/internal, refused locally), `budget_exhausted`, `auth_error`.

## Success Criteria *(mandatory)*

- **SC-001**: A public target is measured from geographically diverse probes, with per-probe latency and loss
  attributed to a named location.
- **SC-002**: `no_probes_found` is reported as "the measurement did not run", with a broader filter
  suggested — verified by requesting `AS13335`.
- **SC-003**: An unresolvable target returns a completed measurement with 0 successful probes, reported as
  unreachability rather than an error — verified live.
- **SC-004**: `10.0.0.1`, `localhost` and an internal hostname are each refused **locally**, naming an
  internal tool instead, with no outbound call made.
- **SC-005**: A DNS query from multiple probes reports resolver disagreement as a split, not an average.
- **SC-006**: Latency from two regions is reported side by side with locations attached.
- **SC-007**: `limits` reports remaining budget and reset time; the documented figures (500/hour
  authenticated, 250/hour unauthenticated) match.
- **SC-008**: Budget accounting is confirmed to be **per probe**: `limit: 1` costs 1 and `limit: 5` costs 5, while a `limits` call costs 0.
- **SC-009**: No token value appears in any NetClaw output or log.
- **SC-010**: The skill states the ThousandEyes and gtrace boundaries, and that Globalping is outside-in.
- **SC-011**: `reconcile-mcp.py` exits 0 across all four surfaces.
- **SC-012**: Skill and integration counts remain correct after the addition.

## Assumptions

- The remote endpoint remains available and free at current terms. If jsDelivr changes them, this becomes a
  registration change rather than a code change — much of the argument for not vendoring a server.
- `GLOBALPING_TOKEN` is account-scoped; the 500/hour budget is shared by everything using that token.
- The vendor's `context` analytics field is taken at face value as analytics. NetClaw's obligation is to send
  nothing sensitive through it, not to audit what the vendor does with it.

## Out of Scope

- **Continuous or scheduled external monitoring.** This is ad-hoc measurement; baselines and trends are
  ThousandEyes' job (FR-015).
- **Probe hosting.** Running a Globalping probe is an infrastructure decision, not an integration.
- **Credits.** The account has 0 credits; only the free hourly allowance is in scope.
- **Scanning or enumeration of third-party infrastructure** (FR-018).
