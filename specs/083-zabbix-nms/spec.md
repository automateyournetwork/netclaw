# Feature Specification: SNMP-poller NMS coverage (Zabbix)

**Feature Branch**: `083-zabbix-nms`
**Created**: 2026-08-03
**Status**: Draft
**Roadmap**: R11, Tier 2

## Overview

NetClaw covers Prometheus, Grafana, Datadog, Splunk, Auvik and ThousandEyes. It has **no SNMP-poller NMS at
all** — and Zabbix and LibreNMS are what a large share of enterprises actually run.

The consequence is sharper than a missing vendor. NetClaw **has no polled history anywhere.** It receives
syslog, SNMP traps and IPFIX — all of which are things that arrive when something happens. Nothing in the
platform answers:

- *Is this normal?*
- *What did this interface do overnight?*
- *How long has this been down?*
- *Was it like this last Tuesday?*

`SOUL.md` already names the gap out loud, in the Globalping section: *"use ThousandEyes when a baseline or
trend matters — Globalping holds no history."* That sentence is currently a dead end for anyone without a
ThousandEyes licence.

This feature adds the polled-history layer underneath everything else NetClaw already sees.

## The distinctions this feature exists to protect

Every feature since 078 has protected one distinction. This one has **three**, and the first two are
**silent-wrong-answer** failures — the API returns an empty list and a success status, and nothing anywhere
says a mistake was made. That is the most dangerous shape a defect can take, because the caller has no
signal at all that the answer is wrong.

### 1. An empty history result is not "nothing happened"

Zabbix's history retrieval takes a **value type**, and it **defaults to "numeric unsigned."** Interface
counters are frequently stored as float. Ask for the wrong type and Zabbix returns an **empty array, not an
error**.

So the naive implementation reports *"no data for this interface"* about a perfectly healthy, actively
forwarding link — and reports it with total confidence. Worse, "no data" reads like a finding: an engineer
sees it and starts investigating a polling failure that does not exist.

The item's real value type must be read from the item definition **before** history is requested, and value
types **cannot be mixed in one request**, so a query spanning items of different types must be split.

### 2. History exhausted is not "no data"

Zabbix keeps two things:

| | Holds | Typical retention |
|---|---|---|
| **History** | every raw polled value | ~14 days |
| **Trends** | hourly min / avg / max / count, numeric only | 365 days – 5 years |

Housekeeping deletes history past its window. **Any question older than that window returns nothing from
history** — and again, empty, not an error.

So *"what did this interface do last month?"* silently returns nothing, and NetClaw reports an absence that
is purely an artefact of where it looked. The retention windows are declared per item, so a correct
implementation **reads them and routes to trends automatically**. Zabbix's own graphs do exactly this.

A query spanning the boundary needs both sources, and the answer must say which parts came from raw values
and which from hourly aggregates — because "the peak was 400 Mbps" from raw data and from an hourly average
are different claims.

### 3. "The poller says unreachable" is not "the device is down"

An NMS reports what **one poller**, from **one vantage point**, at **one interval**, observed. That is
evidence, not a verdict. A device can be unreachable from the NMS and perfectly healthy from everywhere
else — a firewall rule, a management-VRF problem, or a dead SNMP daemon on an otherwise forwarding router.

This is the same discipline spec 079 applied to Globalping (*"no probes ≠ outage"*), and it matters more
here, because an NMS *feels* authoritative in a way a probe network does not.

## The tension, and how it was resolved

**Build-vs-adopt research is complete, and unusually it points at adopt** — unlike R1, R3 and R9, where
every candidate was inadequate. But the strongest candidate is in direct tension with the three distinctions
above, and that tension is the central decision here.

### The candidate landscape (measured, not read off READMEs)

| Server | Tools | Licence | Last commit | Note |
|---|---|---|---|---|
| `mpeirone/zabbix-mcp-server` | **3** (~823 tokens, **16% of ceiling**) | **GPL-3.0** | 2026-05-10 (~3 mo stale) | Read-only default true, plus an allow/deny gate |
| `initMAX/zabbix-mcp-server` | **237** | AGPL-3.0 | active | Supports subsetting. **`mcpservers.org` labels this "Official" — that label is wrong**; initMAX is a Zabbix Premium Partner, not Zabbix LLC |
| `mhajder/zabbix-mcp` | 53 | MIT | active | |
| 2 JavaScript servers | — | one has **no licence at all** | 2025 | stale / abandoned |

**There is no official Zabbix LLC MCP server.** Zabbix's own AI direction is WebMCP, a browser standard, not
a server that can be adopted.

### Why the elegant option was not an obvious yes

`mpeirone` collapses the entire Zabbix API into three tools: a generic passthrough, a documentation lookup,
and an object lister. It is a genuinely good design, it is the smallest manifest of any candidate NetClaw
has ever evaluated, and **it is essentially the design NetClaw would arrive at independently**.

But a generic passthrough means **the model composes the history request itself** — choosing the value type
and choosing between history and trends. That is precisely where both silent-wrong-answer failures live. A
passthrough **cannot structurally prevent them**; it can only document them and hope.

Specs 080, 081 and 082 all reached the same conclusion by different routes: a guarantee that lives in prose
is not a guarantee. Spec 082 made provenance impossible to omit by putting it at a chokepoint the caller
cannot route around. The same logic applies here — if the value-type lookup and the history/trends routing
are the caller's job, they will eventually be skipped, and the failure will be silent.

**Resolved in clarification: adopt as-is.** The traps are documented in the skill rather than enforced in
code, accepting that a caller who ignores the skill will get a wrong answer with nothing to stop it. What
this buys is the smallest surface NetClaw has ever added for a whole product category, and an upstream that
keeps maintaining it. What it costs is enforceability, and the cost is recorded rather than glossed —
see FR-033/FR-033a and the Clarifications section.

### The licence question is separate and also real

`mpeirone` is GPL-3.0. NetClaw ships Apache-2.0 and its other vendored servers are MIT/Apache.

This is **not** spec 082's situation. There, the upstream was "for demonstration and educational purposes
only" and simply could not be used. GPL-3.0 *is* open source, and invoking a separate program across a
subprocess/stdio boundary is not linkage. So the question is about **vendoring and redistribution posture**,
not permission — and it deserved a decision on its own terms rather than being folded into the technical
one.

**Resolved: vendor it, unmodified, with its own licence intact** (FR-034a). It stays a separately-licensed
third-party program invoked over stdio, never edited in place. Any change we need goes upstream — including
the launcher default-inversion bug this evaluation found (FR-034b).

## The infrastructure is real, and it is here today

Nothing in this feature is blocked on a VM, a trial or a licence — the situation that has R4 parked.

| | |
|---|---|
| **NMS** | Zabbix ships a first-party Docker compose (server + database + web UI), up in 1–3 minutes, ~2 GiB for a lab |
| **Host capacity** | 23 GiB RAM available, 700 GB free, Docker running |
| **Things to poll** | Three live FRR routers (`netclaw-core`, `netclaw-edge1`, `netclaw-edge2`) and a licensed FortiGate at 192.168.2.130 on FortiOS 7.6.7 |

**Every capability this feature claims can be exercised against a real NMS polling real devices.** There is
no reason for anything here to ship unverified — a stronger position than R3, where 12 of 21 tools still
await appliance access.

One consequence worth stating: **trend data takes real time to accumulate.** Trends are hourly, so a
meaningful trends verification needs the lab to have been polling for hours, not minutes. That is a
scheduling constraint on verification, not a design problem, but it must not be discovered late.

## Clarifications

### Session 2026-08-03

- Q: Adopt the 3-tool GPL-3.0 passthrough as-is, adopt it behind a thin NetClaw layer, or build a purpose-shaped server? → A: **Adopt `mpeirone/zabbix-mcp-server` as-is.** The two traps are documented in the skill rather than enforced in code. Smallest surface, upstream keeps maintaining it, and the manifest is ~16% of the ceiling.
- Q: Should any write path be exposed, even behind the two gates? → A: **No. R11 is strictly read-only.** Writes are deferred entirely.
- Q: Should the Zabbix lab be committed to the repository as a reproducible fixture? → A: **No.** Operator-local, documented in the quickstart only. The repo does not ship an NMS.
- Q: (raised during clarification) `mpeirone` has **no approval, change-record, or audit concept anywhere in its source** — verified by inspection, `grep -c` returns 0 across all six modules. Its only write control is a binary `READ_ONLY` flag plus regex allow/deny lists, and enabling writes unlocks *every* write method at once. Two gates cannot be inserted without a wrapper, which is the option that was declined. → A: **Confirmed read-only; the combination is resolved in favour of no writes.** Adopt-as-is and gated-writes were not simultaneously satisfiable.

### What these decisions cost, recorded plainly

**This is the first NetClaw integration where a core distinction is NOT structurally enforced.**

Specs 080, 081 and 082 each concluded that a guarantee living in prose is not a guarantee, and each moved
its guarantee to a chokepoint the caller could not route around. A generic passthrough has no such
chokepoint: the model composes the history request itself, choosing the value type and choosing between raw
history and hourly trends.

So FR-001 through FR-006 below are stated as **skill obligations**, not implementation guarantees, and the
feature is honest about the difference. That is a deliberate trade — bought smallest-surface and upstream
maintenance, paid for in enforceability — and it MUST be visible in the spec, the skill, and the
verification report rather than quietly assumed away.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — What did this interface actually do? (Priority: P1)

An engineer is investigating a complaint about slowness last night. They need the utilization history for a
specific interface over a specific window — which may be within the raw-history window, beyond it, or
spanning the boundary.

**Why this priority**: It is the flagship capability, the reason the roadmap lists R11 at all, and the place
where **both** silent-wrong-answer failures live. Nothing else in this feature is worth shipping if this one
lies.

**Independent Test**: request utilization for a real interface on a real polled device across three windows
— inside the history window, entirely beyond it, and spanning the boundary — and confirm each returns real
data with its source stated.

**Acceptance Scenarios**:

1. **Given** an interface polled for hours, **When** utilization is requested for the last hour, **Then**
   real values are returned with their timestamps and units.
2. **Given** an interface whose counter is stored as a float, **When** utilization is requested, **Then**
   real values are returned. It MUST NOT report "no data" because it guessed the wrong value type.
3. **Given** a window older than the raw-history retention, **When** utilization is requested, **Then** the
   answer comes from hourly aggregates and **says so**, including that min/avg/max are hourly rather than
   instantaneous.
4. **Given** a window spanning the retention boundary, **Then** both sources are used and the response
   states which part came from which.
5. **Given** an interface that genuinely has never been polled, **Then** the response says *no such data has
   been collected* — and this is **distinguishable** from a retention or type miss.
6. **Given** an item that is not numeric, **When** utilization is requested, **Then** the response explains
   that aggregates do not exist for non-numeric items rather than returning empty.

---

### User Story 2 — What is wrong right now, and what has been wrong? (Priority: P1)

An engineer wants the current problem list, with severity, duration, and whether anyone has acknowledged it.

**Why this priority**: The most frequent daily use of an NMS, and independently valuable with nothing else
built. It is also where "how long has this been going on?" — the question NetClaw currently cannot answer at
all — gets answered.

**Independent Test**: trigger a real problem in the lab (down an interface on an FRR router), confirm it
appears with correct severity and start time, restore it, and confirm the resolution is visible.

**Acceptance Scenarios**:

1. **Given** active problems, **When** the problem list is requested, **Then** each carries severity, the
   host, when it started, how long it has been active, and its acknowledgement state.
2. **Given** no active problems, **Then** the response says *no active problems* — explicitly distinct from
   *the NMS could not be reached*.
3. **Given** a problem that has been resolved, **When** history is requested, **Then** both onset and
   resolution are visible with their times.
4. **Given** a severity filter, **Then** filtering happens before the response is returned, not by asking
   the reader to ignore rows.
5. **Given** an acknowledged problem, **Then** the acknowledgement is shown as a fact about the workflow —
   never as evidence the underlying condition has cleared.

---

### User Story 3 — Is this device reachable, and since when? (Priority: P2)

An engineer wants availability for a device or group: reachable now, and the recent pattern of transitions.

**Why this priority**: Real and frequently asked, and it is where distinction 3 lives. Slightly lower than
US1/US2 because "is it up right now" is partly answerable today by other NetClaw skills — what is missing is
*since when*, and *how often*.

**Independent Test**: stop one FRR container, confirm the transition appears with a timestamp, restart it,
confirm recovery appears — and confirm the wording never claims more than one poller can know.

**Acceptance Scenarios**:

1. **Given** a polled device, **Then** availability is reported with **when that state was last observed**,
   not as a timeless fact.
2. **Given** a device the NMS reports unreachable, **Then** the response says the **NMS cannot reach it** and
   names the vantage point. It MUST NOT state the device is down.
3. **Given** a device that has flapped, **Then** the transitions are visible with times, so "it has been
   down for 40 minutes" and "it has bounced nine times" are distinguishable.
4. **Given** a device not monitored by the NMS at all, **Then** the response says it is **not monitored** —
   which is not the same as unreachable, and is a much more common cause of surprise.

---

### User Story 4 — What does the NMS know about? (Priority: P3)

An engineer wants the monitored inventory: hosts, groups, interfaces, and what is actually being collected
for each.

**Why this priority**: Genuinely useful — including for reconciling the NMS against the source of truth —
but it is the enabling capability behind the other three rather than the reason to build them.

**Independent Test**: list the monitored inventory and confirm it matches what the lab NMS is actually
configured to poll.

**Acceptance Scenarios**:

1. **Given** monitored hosts, **Then** each is listed with its groups, interfaces and monitoring state.
2. **Given** a host, **Then** the collected items are listable, with their units and retention windows — so
   an engineer can see *before asking* how far back a question can be answered.
3. **Given** a host that exists but is disabled, **Then** it is shown as **disabled**, not omitted. A host
   nobody is watching is a finding, not an absence.

---

### Edge Cases

- **The NMS is unreachable.** Reported as *the NMS is unreachable* — never as "no problems" or "no data".
  An unreachable monitoring system is the single most misleading empty result in this feature.
- **Credentials are missing or expired.** Reported distinctly from unreachable, and from empty.
- **A very large result** — thousands of history points or hundreds of hosts. Bounded, with the bound stated
  in the response, and the caller told how to narrow.
- **A device is monitored but its items have never collected a value** (template attached, polling failing).
  Distinct from both "no such host" and "no data in this window", and a real finding.
- **Clock skew** between the NMS and the caller makes a "last 5 minutes" query return nothing. The response
  must expose the NMS's own notion of time so this is diagnosable rather than baffling.
- **A window in the future**, or reversed start/end. Refused with the reason, not silently returning empty.
- **An item exists on multiple hosts with the same key.** The response must never merge them into one series
  without saying so.

## Requirements *(mandatory)*

### Functional Requirements

#### The three distinctions — enforced by SKILL, not by code

> **Read this before implementing.** Adoption-as-is was chosen in clarification, so there is no NetClaw
> chokepoint between the model and the API. FR-001 through FR-006 are therefore **obligations the skill
> places on the agent**, verified by live behaviour, not invariants the server can enforce. Unlike specs
> 080/081/082, a caller that ignores the skill will produce a wrong answer and nothing will stop it.
> This limitation is required to be stated in the skill and the verification report (FR-033a).

- **FR-001**: The skill MUST require the item's real value type to be read from its definition **before**
  history is requested, and MUST state that the API's default silently returns empty for a mismatched type.
- **FR-002**: The skill MUST require a history request spanning items of differing value types to be split
  per type, and MUST state that types cannot be mixed in one request.
- **FR-003**: The skill MUST require per-item history and trend retention to be read, and the request routed
  to raw history, hourly trends, or both, according to the requested window. The routing rule MUST be stated
  concretely enough to follow without consulting vendor documentation.
- **FR-004**: An answer drawn from hourly aggregates MUST say so, and MUST state that min/avg/max are hourly
  rather than instantaneous. A peak from an hourly average is a different claim from a peak from raw values,
  and the reader must be able to tell.
- **FR-005**: An answer spanning both sources MUST state which portion came from which.
- **FR-006**: **Never collected**, **aged out of retention**, **wrong-type miss**, **genuinely idle** and
  **retention disabled** MUST be five outcomes the agent distinguishes and reports differently. Collapsing
  any of them into a bare "no data" is prohibited, and the skill MUST give the agent a way to tell them
  apart.
- **FR-006b**: *(Added from Phase 0, D7.)* **Retention can be disabled per item**, and a stock install ships
  items in that state: `history=0` means raw values are **never stored**; `trends=0` means there are **no
  aggregates at all**; both zero means the item is collected only to fire triggers and nothing is kept. The
  skill MUST require these to be read from the item definition and reported as a **configuration fact**,
  never as an absence of data. The spec originally modelled only two retention windows; there are three
  states per window.
- **FR-006a**: The skill MUST be written so that following it produces the correct answer **without the
  agent needing to already know** the two traps. Guidance that merely mentions the hazards without giving a
  procedure is not sufficient — it is the only enforcement mechanism this feature has.
- **FR-007**: Availability MUST be reported as **what the NMS observed, from its vantage point, at its
  polling interval** — never as an unqualified statement that a device is up or down.
- **FR-008**: Every availability answer MUST carry **when that state was last observed**.
- **FR-009**: A device **not monitored** by the NMS MUST be reported as not monitored, distinct from
  unreachable.
- **FR-010**: An **unreachable NMS** MUST be a distinct outcome from an empty result. It MUST NOT be
  reported as "no problems" or "no data".

#### Provenance and time

- **FR-011**: Every response MUST carry its source, the time window actually queried (which may differ from
  the one requested), and whether raw or aggregated data was used.
- **FR-012**: Every response MUST expose the NMS's own notion of current time, so clock skew is diagnosable.
- **FR-013**: Timestamps MUST be unambiguous as to timezone.
- **FR-014**: Where a bound was applied, the response MUST state the bound and how to narrow the query.

#### Capabilities

- **FR-015**: Interface utilization history over an arbitrary window MUST be retrievable.
- **FR-016**: The current problem list MUST be retrievable with severity, host, onset, duration and
  acknowledgement state.
- **FR-017**: Problem history — including resolution times — MUST be retrievable.
- **FR-018**: Device and group availability, with recent transitions, MUST be retrievable.
- **FR-019**: Monitored inventory — hosts, groups, interfaces, collected items with units and retention —
  MUST be retrievable.
- **FR-020**: Severity and host/group filtering MUST happen before the response is returned.

#### Read-only posture — no write path at all

- **FR-021**: The integration MUST be **strictly read-only**. **No write path is exposed in this feature.**
- **FR-021a**: Read-only mode MUST be **forced explicitly in NetClaw's own configuration and installer**,
  never left to the upstream default. Measured 2026-08-03: the library defaults it to safe
  (`utils.py:29` → `True`) but **the shipped launcher inverts that** (`scripts/start_server.py:139` →
  `False`). Running it the documented upstream way enables writes.
- **FR-021b**: A **deny-list of destructive methods** MUST additionally be configured as defence in depth,
  so a misconfigured read-only flag is not the only thing standing between an agent and `host.delete`.
  Belt and braces, because the upstream default is known to be wrong in one of two places.
- **FR-022**: Because writes are absent, the two-gate machinery (approval + approved change record) is **not
  built in this feature**. This is recorded as a scope decision, not an omission: adopting a passthrough
  as-is leaves nowhere to insert gates, and a gate an agent can decline to invoke is not a gate.
- **FR-023**: If a write path is ever added, it MUST arrive with both gates, which necessarily means a
  NetClaw-owned layer between the agent and the API. That requirement MUST be recorded so a future change
  cannot enable writes by flipping a flag.
- **FR-024**: An attempted write MUST be refused with a message stating that this integration is read-only
  by design and naming what would be required to change that.
- **FR-025**: Configuration of the NMS itself — creating or modifying hosts, templates, triggers, items —
  is **out of scope** and MUST NOT be reachable, including via the generic passthrough.

#### Auth and transport

- **FR-026**: Authentication MUST use the **API-token / bearer** mechanism. *(Measured on 7.0.29: the older
  in-request credential property still works there — removal lands in 7.2+. So bearer is required for
  **forward-compatibility**, not because the tested version rejects the alternative. The verification report
  MUST state which version was tested.)*
- **FR-027**: A missing, invalid or expired credential MUST be a distinct outcome from an unreachable NMS
  and from an empty result.
- **FR-028**: No credential value may appear in any response, log, or audit record.
- **FR-029**: TLS verification MUST default to on, with any override explicit and documented.

#### Adoption, licence, and provenance of code

- **FR-030**: The build-vs-adopt decision MUST be recorded with its reasoning, including the **measured**
  tool counts and licences of every candidate evaluated.
- **FR-031**: The licence of any adopted code MUST be recorded explicitly, along with why it is acceptable
  for NetClaw to ship or invoke it.
- **FR-032**: Any adopted server MUST be **tested against a live NMS before adoption**, not after, and the
  tested version MUST be recorded. *(Correction from Phase 0: an earlier draft justified this by claiming the
  candidate delegates auth to `pyzabbix`, which has a known bug against this version. Measured — it uses
  `zabbix_utils`, Zabbix LLC's own library. The requirement stands; the stated reason was wrong and has been
  removed rather than left to mislead.)*
- **FR-033**: The adopted component **cannot** structurally enforce FR-001 through FR-006. This MUST be
  stated as a known limitation in the skill, the server README, `TOOLS.md` and the verification report —
  in each case as a limitation, not as a footnote.
- **FR-033a**: The verification report MUST state plainly that **this is the first NetClaw integration whose
  core distinctions are enforced by guidance rather than by structure**, and why that trade was accepted.
  A future maintainer must be able to see the decision, not infer it.
- **FR-034**: The incorrect "Official Zabbix MCP Server" label carried by a third-party directory MUST be
  recorded so nobody adopts on the strength of it.
- **FR-034a**: The adopted code is **GPL-3.0** while NetClaw is Apache-2.0. The vendored copy MUST retain
  its own `LICENSE` verbatim, MUST be clearly marked as third-party and separately licensed, and MUST NOT
  be modified in place — a local fork would create a maintenance burden and a licence-obligation question
  that adopting-as-is exists to avoid. If upstream must be changed, the change goes upstream.
- **FR-034b**: The upstream launcher's inverted read-only default (FR-021a) MUST be reported upstream as a
  bug. Recording a hazard we benefit from without telling the maintainer is not a good-citizen posture, and
  spec 081 established that being a good citizen of free infrastructure is part of how NetClaw behaves.

#### Dependencies

- **FR-035**: Installation MUST use the repository's pip helper, never a bare `pip`/`pip3` (spec 077).
- **FR-036**: Any pin on a package whose submodule is imported MUST be upper-bounded (spec 077).
- **FR-037**: No shared dependency version may be moved for another feature's benefit (spec 076's lesson).
- **FR-037a**: *(Added from Phase 0, D2 — blocking.)* The adopted server requires **fastmcp 3.x**, while
  **five servers in this repository pin `fastmcp<3`** (`netbox-mcp-server`, `CiscoFMC-MCP-server-community`,
  `Wikipedia_MCP`, `rag-mcp`, `ISE_MCP`). Installing it into the shared interpreter would break all five.
  It MUST therefore run from a **dedicated virtualenv**, following the precedent `multivendor-cli-mcp`
  (spec 076) set for exactly this class of conflict.
- **FR-037b**: The virtualenv MUST be created with the repository's helper or `uv`, **never bare
  `python3 -m venv`** — measured on this host, that fails outright because `ensurepip` is unavailable
  (spec 077 hazard #3, encountered live).
- **FR-037c**: The dedicated venv MUST be proven not to perturb the system interpreter: the five `<3`-pinned
  servers MUST still resolve their own fastmcp after installation.

#### Audit — inherited posture, recorded as a limitation

> Measured 2026-08-03: only NetClaw-**authored** servers write GAIT, each implementing it itself
> (`~/.openclaw/gait/` contains exactly two files). There is **no platform-level MCP call audit**. An as-is
> adoption therefore produces no per-call audit trail, and the upstream has no audit concept to enable.

- **FR-038**: Per-call GAIT records are **NOT** produced by this integration. It inherits the standard
  posture of every externally-sourced NetClaw integration. This MUST be recorded as a known limitation in
  the skill, the server README, `TOOLS.md` and the verification report — alongside the enforcement
  limitation (FR-033a), not buried separately.
- **FR-038a**: The developer session MUST be GAIT-logged as normal, per the `docs/ADDING-AN-MCP.md`
  checklist. That obligation is unaffected.
- **FR-038b**: The rationale MUST be recorded: Principle IV's requirement that *"no operation may execute
  silently"* bites on actions and configuration changes, and **this integration performs neither** — it is
  strictly read-only (FR-021). A read-only integration with no write path has no operation to audit.
- **FR-038c**: If a write path is ever added, the NetClaw-owned layer required by FR-023 MUST carry
  **per-call GAIT audit as well as the two gates**. Writes without audit are not acceptable at any point,
  and recording this here is what prevents a future change from adding one without the other.
- **FR-039**: Wherever this feature does produce records of its own — installer output, error paths, the
  verification report — credentials MUST be redacted.

#### Artifact coherence (Principle XI)

- **FR-040**: All of the following MUST be updated: registration or an `EXTERNAL_INTEGRATIONS` entry with a
  reason; `scripts/lib/catalog.sh` entry **and curated profile membership**; `scripts/lib/install-steps.sh`
  install function; **both** HUD entries in `ui/netclaw-visual/server.js`; `README.md` and `SOUL.md`
  including counts **and** a SOUL capability section; skill documentation; `.env.example`; `TOOLS.md`; a
  server `README.md`.
- **FR-041**: If an iN2N member should use it, the **five member artifacts plus a mesh restart** from
  `docs/ADDING-AN-MCP.md` MUST be completed.
- **FR-042**: `python3 scripts/reconcile-mcp.py` MUST exit 0 across all four surfaces.
- **FR-043**: `python3 scripts/verify-inventory-counts.py` MUST exit 0 with updated counts.
- **FR-044**: The tool manifest MUST measure **≤ 5,000 tokens**, with the figure recorded.

#### Boundaries

- **FR-045**: The boundary against `prometheus`/`grafana` MUST be stated: those are pull-based stores for
  infrastructure you instrumented; this is the SNMP-polled NMS for network gear you did not.
- **FR-046**: The boundary against `snmptrap-mcp` (feature 010) MUST be stated: that **receives** unsolicited
  traps; this **polls** on an interval and keeps history. Trap versus poll.
- **FR-047**: The boundary against `ipfix-mcp` MUST be stated: flow records, not counters.
- **FR-048**: The boundary against `auvik`/`thousandeyes`/`datadog` MUST be stated: SaaS monitoring with
  their own agents; this is the self-hosted NMS an enterprise already runs.
- **FR-049**: The boundary against `pyats`/`multivendor-cli`/`fortinet` MUST be stated: those read
  **current** state from the device itself; this answers **what it was over time**, from a poller, and can
  answer for a device that is unreachable right now.

#### Honest verification

- **FR-050**: On completion, the feature MUST state per capability what was **actually exercised against the
  live NMS polling real devices**, versus what merely ran without error.
- **FR-051**: Trend-based answers MUST be verified against **genuinely accumulated** hourly data, not
  synthesised. If the lab has not polled long enough at verification time, that MUST be recorded as
  unverified rather than claimed.
- **FR-052**: Anything not exercised MUST be marked unverified or cut.

### Key Entities

- **Monitored host** — a device the NMS polls, with groups, interfaces, monitoring state, and whether it has
  ever returned data.
- **Collected item** — one metric on one host, with its value type, units, and **its own** history and trend
  retention windows.
- **Data window** — a requested time range, the range actually served, and which source served each part.
- **Data absence** — a first-class outcome with four distinguishable causes: never collected, aged out,
  type mismatch, genuinely idle.
- **Problem** — an active or resolved condition with severity, host, onset, duration, resolution and
  acknowledgement state.
- **Availability observation** — what one poller saw, from one vantage point, at one interval, at a stated
  time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Utilization history for a real interface on a real polled device is retrieved and the values
  match what the NMS's own UI shows for the same window.
- **SC-002**: An interface whose counter is stored as a float returns real data — verified against an item
  that would return empty under the API's default type.
- **SC-003**: A window beyond raw retention returns aggregated data and the response states that the values
  are hourly.
- **SC-004**: A window spanning the retention boundary returns both, and the response identifies which part
  came from which.
- **SC-005**: Never-collected, aged-out, type-mismatch and genuinely-idle produce four distinguishable
  answers, verified by wording against the live NMS. Because enforcement is by guidance, this MUST be tested
  **end to end through the agent following the skill** — asserting on the skill's text alone would prove
  nothing about the answer a user receives.
- **SC-006**: A real problem raised in the lab appears with correct severity and onset; after resolution,
  both onset and resolution are retrievable.
- **SC-007**: With no active problems, the response says so — and is textually distinct from the response
  when the NMS is unreachable.
- **SC-008**: An acknowledged problem is shown as acknowledged, and the wording never implies the condition
  has cleared.
- **SC-009**: Stopping a real device produces an availability transition with a timestamp; restarting it
  produces a recovery.
- **SC-010**: No availability response asserts that a device is down. Every one attributes the observation
  to the NMS and states when it was observed.
- **SC-011**: A device not monitored is reported as not monitored, distinct from unreachable.
- **SC-012**: Monitored inventory matches what the lab NMS is configured to poll, including a disabled host
  shown as disabled rather than omitted.
- **SC-013**: Collected items are listable with units and retention, so an engineer can see how far back a
  question can be answered before asking it.
- **SC-014**: Every response carries its source, the window actually queried, and whether raw or aggregated
  data was used.
- **SC-015**: Every response exposes the NMS's own current time.
- **SC-016**: An unreachable NMS, a missing credential and an empty result are three distinguishable
  outcomes.
- **SC-017**: A bounded result states its bound and how to narrow the query.
- **SC-018**: An attempted write is refused, and the refusal states that this integration is read-only by
  design. Verified against the live NMS with a real write method.
- **SC-018a**: Read-only is forced in NetClaw's own configuration and installer, not inherited from the
  upstream default — proven by showing NetClaw's setting overrides the launcher's `False`.
- **SC-018b**: A destructive method is refused by the deny-list **even with read-only deliberately
  disabled**, proving the second layer is real and not decorative.
- **SC-019**: No credential value appears in any response, log or audit record.
- **SC-020**: The absence of per-call GAIT is stated as a known limitation in all four required places, and
  the developer session GAIT log exists. No document claims an audit trail this integration does not have.
- **SC-021**: The manifest measures ≤ 5,000 tokens, with the figure recorded.
- **SC-022**: `reconcile-mcp.py` exits 0 across all four surfaces; `verify-inventory-counts.py` exits 0 with
  updated counts; `trace-skill.py` resolves for every skill added.
- **SC-023**: `SOUL.md` gains a capability section describing the polled-history capability and the three
  distinctions — not merely an incremented count.
- **SC-024**: The build-vs-adopt decision, every candidate's measured tool count and licence, and the
  incorrect "Official" label are all recorded.
- **SC-024a**: The vendored copy retains its own GPL-3.0 `LICENSE` verbatim, is marked as third-party and
  separately licensed, and is byte-identical to upstream at the pinned revision.
- **SC-024b**: The skill, the server README, `TOOLS.md` and the verification report each state that the
  three distinctions are enforced by guidance rather than structure, and that this is a first for NetClaw.
- **SC-024c**: Both upstream defects — the inverted read-only default and the invalid `fastmcp>=v3.2.0`
  specifier — are reported upstream, with links recorded.
- **SC-026**: The server runs from a dedicated virtualenv, and after installation the five servers pinning
  `fastmcp<3` still resolve their own version — proven by measurement, not assumed.
- **SC-027**: The virtualenv is created without bare `python3 -m venv`, which fails on this host.
- **SC-028**: A five-way absence is demonstrated: never-collected, aged-out, wrong-type, genuinely-idle and
  **retention-disabled** each produce a different answer against the live NMS.
- **SC-029**: The verification report states the exact NMS version tested, and notes that the in-body auth
  property still works there while being removed in 7.2+.
- **SC-030**: The measured manifest token count is recorded.
- **SC-025**: A per-capability verification table exists distinguishing **exercised against the live NMS**
  from **executed without error**, with anything uninspected marked unverified or cut.

## Assumptions

- **Zabbix is the only target.** LibreNMS's only MCP server exposes 111 tools and busts the manifest
  ceiling; Observium's sole server is abandoned and bypasses the API entirely for direct database and
  filesystem access. Both are out of scope here.
- **Netdata is not in this category and belongs elsewhere.** It is agent/push-based, not SNMP-polling. Worth
  recording separately: MCP is built into the **free open-source agent**, not only the paid cloud tier — the
  roadmap's "official Cloud MCP" description is inaccurate and should be corrected. That makes Netdata a
  near-zero-effort *separate* item, not part of this one.
- **Current-generation Zabbix is the target.** Authentication uses API tokens; the older in-request
  credential property has been removed, so compatibility with pre-token versions is not pursued.
- **The lab is the verification environment**, and it polls real devices — three FRR routers and a licensed
  FortiGate. No capability needs to ship unverified.
- **The lab is operator-local and NOT committed.** Decided in clarification: the quickstart documents how to
  stand it up; the repository ships no compose file and no NMS. Consequence to accept honestly — the
  verification is reproducible only by someone who rebuilds the lab from the quickstart.
- **Trend verification needs elapsed time.** Trends are hourly, so verifying them requires the lab to have
  been polling for hours. This is a scheduling constraint on verification and must be planned for, not
  discovered.
- **No new persistent state.** The NMS holds the history; this feature stores nothing of its own.

## Out of Scope

- **Every write, without exception** — acknowledging problems, enabling or disabling hosts, maintenance
  windows. Decided in clarification (FR-021/022). Adding any of them later requires a NetClaw-owned layer
  carrying both gates, not a configuration flag.
- **Configuring the NMS** — creating or modifying hosts, templates, triggers, items, actions or media types.
  This reads an NMS someone else runs (FR-025).
- **A committed lab** — no compose file, no NMS shipped in the repository (clarification Q3).
- **LibreNMS, Observium and Netdata** — see Assumptions. Netdata is a credible separate item.
- **Replacing `prometheus`, `grafana`, `datadog`, `auvik` or `thousandeyes`** — different data, different
  collection model, all already covered.
- **Receiving traps or flows** — `snmptrap-mcp` and `ipfix-mcp` own those. Trap and flow are not poll.
- **Reading current device state** — `pyats`, `multivendor-cli` and `fortinet` own that. This answers what
  state *was*, over time.
- **Graph or dashboard rendering.** This returns data; the existing visualization skills render it.
- **Alerting or notification delivery.** Reading the problem list is in scope; sending anything anywhere is
  Principle XIV territory and belongs to the delivery skills.
- **Capacity forecasting or anomaly detection.** Returning history is in scope; drawing conclusions from it
  is a separate feature with its own honesty requirements.
