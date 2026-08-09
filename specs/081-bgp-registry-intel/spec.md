# Feature Specification: BGP & Registry Intelligence (RPKI / RDAP / PeeringDB / RIPEstat)

**Feature Branch**: `081-bgp-registry-intel`
**Created**: 2026-08-03
**Status**: Draft
**Roadmap**: R9 — Tier 2, "the internet / external plane"

## Overview

Spec 079 (R8) gave NetClaw its first vantage point **outside** its own administrative domain: Globalping
measures *toward* a public target from ~4,800 probes. It answers "can anyone out there reach us?"

It cannot answer the questions that follow. When a prefix appears in a routing table, a firewall log, or a
traceroute hop, an operator needs to know: **who is this allocated to? is this announcement legitimate?
where does this network peer?** Those are registry and routing-database questions, and NetClaw has no way
to ask them.

This feature adds that. Five public, unauthenticated data sources — RPKI origin validation, RDAP registry
records, PeeringDB peering data, RIPEstat routing status, and RIPE Atlas probe inventory.

Together with R8 it completes the external plane: R8 **measures**, R9 **looks up**. Neither substitutes
for the other, and the skill must say so.

## The distinction this feature exists to protect

### RPKI `unknown` is not `invalid`

**Most of the internet has no ROA.** Unsigned address space is the overwhelmingly common case, not an
anomaly. An operator who is told that unsigned space is "invalid", "unverified in a bad way", or a security
finding will be handed false incidents at a scale that destroys trust in the tool within a day.

Measured live on 2026-08-03 against RIPEstat, and **the API does not use RFC 6811's vocabulary**:

| Query | RIPEstat `status` | RFC 6811 name | What it means | Actionable? |
|---|---|---|---|---|
| `AS13335` + `1.1.1.0/24` | `valid` | Valid | A ROA exists and authorises this origin | No — this is healthy |
| `AS13335` + `8.8.8.0/24` | **`invalid_asn`** | Invalid | A ROA exists for `AS15169`; this origin is not authorised | **Yes — possible hijack** |
| *(max-length violation)* | **`invalid_length`** | Invalid | A ROA exists; the prefix is more specific than `maxLength` | **Yes — usually a misconfiguration, different fix** |
| `AS3356` + `4.0.0.0/9` | **`unknown`** | **NotFound** | **No ROA exists at all** | **No — the common case** |

Three consequences the spec must carry:

1. **`unknown` MUST NOT be reported as a problem.** It is the default state of most address space.
2. **RIPEstat's names differ from the standard's.** `unknown` means RFC 6811 `NotFound`. Passing the API's
   raw string through without saying so invites a reader who knows RFC 6811 to conclude something is
   genuinely unknown or indeterminate, when in fact it is definitively unsigned.
3. **`invalid_asn` and `invalid_length` are different findings with different remediations.** RFC 6811
   collapses both to `Invalid`; the API is more granular, and flattening that away destroys the distinction
   between "someone else is announcing your space" and "you announced a /24 under a /22 ROA."

This is the same error class as spec 078's *"no advisories ≠ not vulnerable"*, spec 079's *"no probes found
≠ outage"*, and spec 080's *"no logs ≠ rule unused"*. Each shipped with the distinction named explicitly and
enforced structurally, and this feature does the same.

### Three further "this is not what you think it is" cases

- **Registry ownership is a claim, not routing truth.** RDAP says who a block is *allocated to*. It says
  nothing about who is *announcing* it. Presenting an RDAP holder as evidence about routing is the same
  category error as presenting FortiManager intent as device state (spec 080).
- **PeeringDB is self-reported.** Operators maintain their own records. A missing facility is not evidence
  the network is absent from it; it is evidence nobody updated the record.
- **RIPEstat visibility is RIPE's collectors' view, not global truth.** A prefix seen by few peers may be
  an intentionally scoped announcement, not a leak.

## Clarifications

### Session 2026-08-03

- Q: Does US5 (RIPE Atlas inventory) survive, given it borders Globalping's existing `locations` capability? → A: **Kept, but narrowed** to what Globalping genuinely lacks — RIPE Atlas **anchors** (stable, well-known measurement targets) and **per-AS probe counts**. General probe-availability listing stays with Globalping; this feature MUST NOT reimplement it.
- Q: What request rate does NetClaw hold itself to against these free services? → A: **≤ 4 requests/second per source, and strictly serial (concurrency 1) per source.** No parallel fan-out across prefixes or ASNs — batch questions iterate. Chosen because it is testable, cannot be exceeded by a fan-out added later, and the latency cost is irrelevant for interactive lookups while the cost of being blocked is not.
- Q: Cache lifetime and location? → A: **Per-source TTLs, in memory only** — RPKI ~5 min, routing status ~15 min, RDAP and PeeringDB ~24 h. Nothing persists across a restart. Per-source because volatility differs by an order of magnitude (a ROA can appear in minutes; an allocation changes in months), and in-memory because the goal is not hammering a free service *within one investigation*, not mirroring a registry.
- Q: Does the spec-080 tool-manifest ceiling apply here? → A: **Yes — the same 5,000-token ceiling and the same build-failing test.** A repo-wide convention is worth more than a per-feature optimum: the check is copy-pasteable and a future maintainer inherits the guardrail without rediscovering why it exists. It will pass with large headroom, which is the point — a ceiling that never binds still prevents someone adding forty tools.
- Q: Single RPKI validator, or corroborate against two? → A: **Single source (RIPEstat), named on every result, with an explicit statement that the verdict is unconfirmed by a second validator.** Corroboration is deferred until a second validator is verified reachable — specifying a corroboration flow against an endpoint we have not confirmed would repeat the R3 mistake of assuming an API and discovering otherwise at implementation time.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Is this announcement legitimate? (Priority: P1)

An unfamiliar prefix appears — in a BGP table, a firewall log, a traceroute hop. The operator asks whether
the origin AS is authorised to announce it.

**Why this priority**: It is the question with real operational consequence, and the one most easily
answered wrongly. It is also where the `unknown`/`invalid` distinction lives, which is the reason this
feature is a spec rather than a wrapper.

**Independent Test**: query a known-good pair, a deliberately mismatched pair, and unsigned space; confirm
three distinct outcomes with three distinct explanations.

**Acceptance Scenarios**:

1. **Given** a prefix and origin AS with a matching ROA, **When** validation is requested, **Then** NetClaw
   reports **valid** and states that the announcement is RPKI-authorised.
2. **Given** a prefix whose ROA names a different AS, **When** validation is requested, **Then** NetClaw
   reports **invalid — wrong origin AS**, names the AS the ROA *does* authorise, and flags it as actionable.
3. **Given** a prefix more specific than its ROA's `maxLength`, **When** validation is requested, **Then**
   NetClaw reports **invalid — prefix too specific**, distinct from the wrong-AS case, and notes the
   remediation differs.
4. **Given** address space with no ROA, **When** validation is requested, **Then** NetClaw reports **no ROA
   exists (RFC 6811 NotFound)**, states explicitly that this is **normal and not a finding**, and MUST NOT
   describe it as invalid, suspicious, or unverified-in-a-bad-way.
5. **Given** any RPKI result, **When** it is reported, **Then** the ROA(s) that drove the decision are
   included, so the operator can see *why* rather than trusting a verdict.

---

### User Story 2 — Who is this allocated to, and how do I contact them? (Priority: P1)

An operator has an IP or ASN and needs the registry record: holder, allocation, abuse contact.

**Why this priority**: This is the single most frequent external lookup in incident response, and it is
currently done by shelling out to `whois` or a browser. It is also independently useful with nothing else
implemented.

**Independent Test**: look up an IP and an ASN across at least two different RIRs and confirm holder and
abuse contact are returned with the responding registry named.

**Acceptance Scenarios**:

1. **Given** an IP address, **When** a registry lookup is requested, **Then** NetClaw returns the holder,
   allocation range, registry, and abuse contact where published.
2. **Given** an ASN, **When** a registry lookup is requested, **Then** NetClaw returns the holder and
   contacts.
3. **Given** any registry result, **When** it is reported, **Then NetClaw states that this is allocation
   data and not evidence about who is announcing the space** (see the distinction above).
4. **Given** a registry that refuses or fails, **When** the lookup runs, **Then** NetClaw names the registry
   that failed and reports the failure as a failure — never as "no record exists".

---

### User Story 3 — What does this AS announce, and how visible is it? (Priority: P2)

An operator wants an AS's announced prefixes and how widely each is seen.

**Independent Test**: query a large well-known AS and a small one; confirm prefix counts and per-prefix
visibility, with the collector basis stated.

**Acceptance Scenarios**:

1. **Given** an ASN, **When** routing status is requested, **Then** NetClaw returns announced prefixes and
   an AS overview (holder, allocation status).
2. **Given** a prefix with low visibility, **When** reported, **Then** NetClaw states this is **RIPE's
   collector view** and that low visibility has legitimate explanations — it MUST NOT be presented as a
   route leak or a fault.
3. **Given** an AS announcing nothing, **When** queried, **Then** NetClaw reports **no announcements
   observed**, distinct from "the AS does not exist" and from "the query failed".

---

### User Story 4 — Where does this network peer? (Priority: P2)

Interconnection questions: which IXPs and facilities does an AS use, what is its traffic profile, who is
the technical contact.

**Independent Test**: query an AS with rich PeeringDB records and one with none; confirm both are handled
without conflating "no record" with "does not peer".

**Acceptance Scenarios**:

1. **Given** an ASN, **When** peering data is requested, **Then** NetClaw returns the network record,
   IXP presence and facilities where published.
2. **Given** an AS with no PeeringDB record, **When** queried, **Then** NetClaw reports **no self-reported
   record**, and states explicitly that this is **not evidence the network does not peer**.

---

### User Story 5 — Atlas anchors and per-AS probe density (Priority: P3)

Read-only RIPE Atlas inventory, **narrowed to the two things Globalping does not provide**: **anchors** —
stable, well-known, always-on measurement targets useful as reference endpoints — and **per-AS probe
counts**, which tell an operator whether a given network is observable from inside at all.

**Why this priority**: Narrow but genuinely non-overlapping. General probe-availability listing belongs to
Globalping's `locations` and is explicitly **not** reimplemented here (Principle VII). Anchors are a
distinct concept Globalping has no equivalent of, and per-AS density answers "can anyone measure this
network from within it?" which registry data cannot.

**Independent Test**: list anchors for a country and probe counts for a named AS; confirm neither
duplicates Globalping's `locations` output, and that a request to *measure* is routed to R8.

**Acceptance Scenarios**:

1. **Given** a country, **When** anchors are requested, **Then** NetClaw returns Atlas anchors with status.
2. **Given** an ASN, **When** probe density is requested, **Then** NetClaw returns how many Atlas probes are
   present in that AS.
3. **Given** a request for general probe availability by location, **When** it reaches this feature, **Then**
   NetClaw routes it to Globalping's `locations` rather than answering from Atlas.
4. **Given** a request to *run* a measurement, **When** it reaches this feature, **Then** NetClaw routes it
   to Globalping (R8) and does not attempt it here.

---

### Edge Cases

- **A source is down or rate-limiting.** NetClaw names the source that failed and reports a failure.
  A dead API MUST NOT produce an empty-but-successful-looking answer.
- **ARIN's RDAP refuses us.** Measured: `Recv failure: Connection reset by peer` from
  `rdap.arin.net` on this host. Bootstrap redirection and RIPE's RDAP both return 200. A single
  registry being unreachable MUST NOT fail the whole lookup silently.
- **Sources disagree.** RDAP holder and PeeringDB name differ, or RIPEstat shows an announcement the
  registry does not explain. NetClaw reports the disagreement rather than choosing a winner.
- **Private, reserved, or bogon input** — RFC1918, loopback, documentation ranges, unallocated space.
  These have no meaningful registry or RPKI answer and MUST be refused locally with an explanation, not
  sent to a public API.
- **An AS or prefix that does not exist.** Distinct from "exists but unsigned" and from "query failed".
- **Very large result sets** — an AS announcing thousands of prefixes. Bounded and stated, never silently
  truncated.
- **IPv6 throughout.** Every capability MUST accept IPv6 prefixes and addresses, not just IPv4.

## Requirements *(mandatory)*

### Functional Requirements

#### RPKI origin validation — the core

- **FR-001**: NetClaw MUST report RPKI origin validation state for a prefix + origin-AS pair.
- **FR-002**: The four observed states MUST be reported distinctly: **valid**, **invalid (wrong origin
  AS)**, **invalid (prefix too specific / maxLength)**, and **no ROA exists**. Collapsing any two is
  prohibited.
- **FR-003**: "No ROA exists" MUST be accompanied by an explicit statement that **this is the normal state
  for most address space and is not a finding**. It MUST NOT be described as invalid, suspicious,
  unverified, or a security concern.
- **FR-004**: NetClaw MUST translate the source's vocabulary to the standard's and say it is doing so:
  RIPEstat's `unknown` is RFC 6811 **NotFound**. Passing the raw string through unexplained is prohibited.
- **FR-005**: The ROA(s) that determined the verdict MUST be included in the result, so the operator can
  verify the reasoning rather than trusting a label.
- **FR-006**: An `invalid` result MUST name what the ROA *does* authorise (the permitted origin AS and
  `maxLength`), because that is what makes it actionable.
- **FR-007**: NetClaw MUST NOT declare a hijack, an incident, or an attack. It reports RPKI state; incident
  declaration is an operator judgement (see Out of Scope).
- **FR-007a**: Validation comes from a **single validator**, and the result MUST name it. NetClaw MUST NOT
  present an RPKI verdict as independently confirmed, corroborated, or cross-checked, because it is none of
  those things.
- **FR-007b**: The asymmetry MUST be reflected in how results are framed. A wrong `valid` tells an operator
  an announcement is authorised when it may not be; a wrong `invalid` sends them chasing a hijack that is
  not happening. Both are worse than an honest "this is one validator's view."
- **FR-007c**: If the validator is unreachable, NetClaw MUST report **validation unavailable** — naming the
  validator — and MUST NOT fall back to inferring state from routing data, registry data, or the absence of
  a ROA. An unavailable validator is not a `not-found`.

#### Registry records (RDAP)

- **FR-008**: NetClaw MUST return registry records for an IP address or ASN: holder, allocation range,
  responsible registry, and abuse contact where published.
- **FR-009**: Every registry result MUST state that it is **allocation data, not evidence about who is
  announcing the space**.
- **FR-010**: The **responding registry MUST be named** on every result. "The registry says" is not
  attributable; RIRs differ in completeness and freshness.
- **FR-011**: A registry that refuses, times out, or resets MUST be reported as a **source failure naming
  that registry** — never as an absence of record. ARIN's reset (Edge Cases) is the live example.

#### Routing status

- **FR-012**: NetClaw MUST return an AS overview and its observed announced prefixes.
- **FR-013**: Visibility figures MUST state the **collector basis** and MUST NOT be presented as global
  ground truth or as evidence of a leak.
- **FR-014**: "No announcements observed" MUST be distinct from "AS does not exist" and from "query
  failed".

#### Peering data

- **FR-015**: NetClaw MUST return an AS's PeeringDB network record, IXP presence and facilities where
  published.
- **FR-016**: Every peering result MUST state that PeeringDB is **self-reported**, and an absent record
  MUST be reported as "no self-reported record", explicitly **not** as evidence the network does not peer.

#### Measurement inventory

- **FR-017**: NetClaw MUST be able to report, read-only, RIPE Atlas **anchors** by country and **probe
  counts by AS** — and nothing broader.
- **FR-017a**: General probe-availability-by-location MUST NOT be implemented here. Globalping's
  `locations` already owns it (Principle VII); a request for it MUST be routed there.
- **FR-018**: This feature MUST NOT run measurements. A request to measure MUST be routed to Globalping
  (spec 079).

#### Source attribution and provenance — structural

- **FR-019**: Every response MUST carry, as **structured fields rather than prose**: the **source** that
  produced it, the **time** it was retrieved, and its **outcome**. A result whose source cannot be named
  MUST be an error rather than an unattributed answer.
- **FR-020**: Attribution and audit MUST be enforced at a **single chokepoint** through which every
  response passes, so a tool added later cannot omit them. Spec 080 proved this works and spec 080's
  `/speckit.analyze` pass proved the alternative fails: an audit requirement with a verification task and
  no implementing task passes review by accident.
- **FR-021**: Where a question is answered from more than one source, **each element MUST carry its own
  source**. A merged answer with one collective citation is not attributable.
- **FR-022**: Every operation MUST produce a GAIT record by construction (Principle IV), including
  refusals and failures.

#### Being a good citizen of free services

- **FR-023**: These are volunteer-funded community services (RIPE NCC, PeeringDB). NetClaw MUST hold itself
  to **≤ 4 requests per second per source** and **strict serialisation (concurrency 1) per source**.
- **FR-023a**: **Parallel fan-out is prohibited.** A question spanning many prefixes or ASNs MUST iterate
  serially, not dispatch concurrently. This is the rule most likely to be broken by a later "make it
  faster" change, so it is a requirement rather than guidance.
- **FR-023b**: The limit MUST be enforced in code at the request layer, not left to caller discipline —
  a tool added later must inherit it without having to know it exists.
- **FR-024**: Actual rate limits MUST be **measured and documented**, not assumed. Measured 2026-08-03:
  **neither RIPEstat nor PeeringDB advertises rate-limit headers**, so there is nothing to negotiate
  against at runtime. FR-023's ceiling is therefore a deliberately conservative self-imposed figure rather
  than a service-declared one, and the documentation MUST say so — a later maintainer who finds a published
  limit should not mistake this number for that.
- **FR-025**: NetClaw MUST identify itself in requests (a `User-Agent` naming NetClaw and a contact
  reference), which is the courtesy these services ask of automated consumers.
- **FR-026**: Repeated identical lookups MUST be served from an **in-memory cache with per-source TTLs**,
  because the sources differ in volatility by an order of magnitude:

  | Source | TTL | Why |
  |---|---|---|
  | RPKI validation | **5 minutes** | A ROA can be published or withdrawn within minutes; a stale `valid` is the most dangerous stale value here |
  | Routing status / AS overview | **15 minutes** | Announcements change on minutes-to-hours |
  | RDAP registry records | **24 hours** | Allocations change on months |
  | PeeringDB records | **24 hours** | Self-reported, updated rarely |
  | Atlas anchors / probe counts | **24 hours** | Infrastructure inventory, slow-moving |

- **FR-026a**: The cache MUST be **in-memory and session-scoped**. Nothing persists across a restart, and
  this feature MUST NOT create an on-disk store. It is a courtesy buffer for one investigation, not a
  registry mirror — unlike spec 078, which legitimately caches PSIRT data on disk because that data is
  large and genuinely slow-moving.
- **FR-026b**: A response served from cache MUST say so **and report the age of the cached value**, so an
  operator chasing a fast-moving RPKI change can tell whether they are looking at a fresh answer.
- **FR-026c**: A caller MUST be able to force a fresh lookup, bypassing the cache, for the case where a ROA
  was just published and the 5-minute TTL is the thing standing between the operator and the truth.
- **FR-027**: On rate-limit or throttle response, NetClaw MUST back off and report the condition rather
  than retrying blindly.

#### Tool-manifest budget

- **FR-027a**: The registered tool manifest MUST NOT exceed **5,000 tokens**, measured as the token count of
  the serialised `tools/list` response. This is the same ceiling and the same measurement method spec 080
  established, carried deliberately as a repo-wide convention rather than re-derived per feature.
- **FR-027b**: The measurement MUST be enforced by a **build-failing test**, not a manual check. A ceiling
  nobody verifies is a comment.
- **FR-027c**: The measured figure MUST be recorded in the server documentation. This surface is expected to
  pass with wide headroom; the ceiling exists to stop a later expansion, not to constrain the initial build.

#### Input validation

- **FR-028**: Private, reserved, loopback, link-local, documentation and unallocated ranges MUST be
  **refused locally before any outbound request**, with an explanation of why they have no registry answer.
- **FR-029**: Both IPv4 and IPv6 MUST be supported across every capability.
- **FR-030**: Malformed input (bad prefix length, non-numeric AS, mixed family) MUST be rejected with a
  message naming the problem, not passed through to a remote API.

#### Composition boundaries (Principle VII)

- **FR-031**: The boundary against **Globalping (spec 079)** MUST be stated in both directions: Globalping
  *measures from* probes toward a target; this feature *looks up* registry and routing state. Neither
  substitutes for the other.
- **FR-032**: The boundary against the existing **`gtrace-ip-enrichment`** skill MUST be stated and
  respected. `gtrace` already provides `asn_lookup` (ASN, organisation, network range, registry) and
  `geo_lookup` for quick hop enrichment. This feature MUST NOT duplicate quick ASN/geo enrichment; it owns
  **authoritative registry records, RPKI validation, routing status and peering data**. Where they overlap,
  the skill MUST name which tool to use for which question.
- **FR-033**: The boundary against **`nvd-cve`/`cisco-psirt`** MUST be stated: those answer "is this
  software vulnerable"; this answers "is this routing legitimate". Unrelated planes.

#### Read-only

- **FR-034**: Every capability is read-only. This feature MUST introduce no write path, no device access,
  and therefore no approval or change-record gate.
- **FR-035**: NetClaw MUST NOT be directed to enumerate, sweep or bulk-harvest registry data. Lookups are
  in service of a specific operational question.

#### Honest verification reporting

- **FR-036**: On completion, the feature MUST state **per capability** what was exercised against a live
  API and what was only checked statically.
- **FR-037**: Because every source here is publicly reachable with no credentials, **near-total live
  verification is the expectation** — not the aspiration. Spec 080 shipped 13 of 21 tools unexercised
  because appliances were unavailable; that excuse does not exist here, and any unexercised capability
  MUST be justified explicitly or cut.

#### Artifact coherence (Principle XI)

- **FR-038**: All of the following MUST be updated, none assumed: registration in `config/openclaw.json`
  with **repo-relative paths** (or an `EXTERNAL_INTEGRATIONS` entry with a stated reason);
  `scripts/lib/catalog.sh` entry **and curated profile membership**; `scripts/lib/install-steps.sh` install
  function; **both** HUD entries in `ui/netclaw-visual/server.js` (node list *and* annotation map);
  `README.md` and `SOUL.md` including counts **and** a SOUL capability section; `SKILL.md`;
  `.env.example`; `TOOLS.md`; a server `README.md`.
- **FR-039**: `python3 scripts/reconcile-mcp.py` MUST exit 0 across all four surfaces.
- **FR-040**: `python3 scripts/verify-inventory-counts.py` MUST exit 0 with counts updated from the current
  206 skills / 153 integrations.
- **FR-041**: `python3 scripts/trace-skill.py <skill>` MUST resolve for every skill added.
- **FR-042**: Any dependency pin on a package whose submodule is imported MUST be upper-bounded, and
  installation MUST use `netclaw_pip_install`, never a bare `pip`/`pip3` (spec 077).

### Key Entities

- **Prefix** — an IPv4 or IPv6 network. The unit of RPKI validation and routing observation.
- **Origin AS** — the autonomous system announcing a prefix. Validation is always of the *pair*.
- **ROA** — a Route Origin Authorisation: which AS may announce which prefix, up to a `maxLength`. The
  evidence behind every RPKI verdict.
- **Validation state** — one of: valid · invalid (wrong AS) · invalid (too specific) · no ROA. Four values,
  never fewer.
- **Registry record** — allocation data for a resource: holder, range, registry, abuse contact. A claim of
  allocation, not of routing.
- **AS overview** — holder and allocation status for an ASN, distinct from what it announces.
- **Peering record** — an AS's self-reported interconnection: IXPs, facilities, traffic profile.
- **Source** — the specific service that produced a datum. Carried on every response; never implied.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A ROA-matching prefix/AS pair is reported **valid** with the authorising ROA included.
- **SC-002**: A prefix whose ROA names a different AS is reported **invalid — wrong origin AS**, naming the
  AS the ROA authorises. Verified live against a deliberately mismatched pair.
- **SC-003**: A maxLength violation is reported **invalid — too specific**, and is distinguishable in the
  output from SC-002.
- **SC-004**: Unsigned space is reported as **no ROA exists**, with an explicit statement that this is
  normal and not a finding — and the words "invalid", "suspicious" and "unverified" do not appear in that
  result.
- **SC-005**: The response for unsigned space names the RFC 6811 term **NotFound** alongside the source's
  own `unknown`, so the vocabulary mismatch cannot mislead.
- **SC-005a**: Every RPKI result names its validator and states that the verdict is **not corroborated by a
  second validator**; the words "confirmed", "verified" and "cross-checked" do not appear.
- **SC-005b**: With the validator unreachable, the result is **validation unavailable** naming the
  validator — and is distinguishable in the output from "no ROA exists".
- **SC-006**: An IP and an ASN are each resolved to holder and abuse contact, across **at least two
  different RIRs**, with the responding registry named on each.
- **SC-007**: A registry failure (ARIN's connection reset is the live case) is reported as a **named source
  failure**, and does not present as "no record found".
- **SC-008**: An AS's announced prefixes and overview are retrieved, with the collector basis stated.
- **SC-009**: A low-visibility prefix is reported without the words "leak" or "hijack" attached by the tool.
- **SC-010**: An AS with no PeeringDB record is reported as "no self-reported record", explicitly not as
  "does not peer".
- **SC-011**: Atlas **anchors** are listed for a country and **probe counts** returned for a named AS;
  a request for general probe availability by location is routed to Globalping's `locations`, and a request
  to *run* a measurement is routed to Globalping.
- **SC-012**: **Every** response carries a structured source and retrieval time — asserted mechanically
  across all tools, not spot-checked.
- **SC-013**: A multi-source answer carries per-element attribution, not one collective citation.
- **SC-014**: Every operation, including refusals and failures, produces a GAIT record.
- **SC-015**: RFC1918, loopback, documentation and unallocated inputs are each **refused locally with no
  outbound request made**, and the refusal explains why.
- **SC-016**: IPv6 works across every capability, verified with at least one real IPv6 prefix.
- **SC-016a**: Request rate against any single source never exceeds **4/second**, and requests to one
  source are never concurrent — asserted by a test that issues a multi-target batch and observes the
  request timeline, not by inspection.
- **SC-017**: Requests identify NetClaw via `User-Agent`; a repeated identical lookup within a session is
  served from cache, says so, and **reports the cached value's age**.
- **SC-017a**: A forced-fresh lookup bypasses the cache and issues a real request, verified by observing
  that the request occurred.
- **SC-017b**: RPKI results expire from cache in 5 minutes while RDAP results survive, confirming TTLs are
  genuinely per-source rather than one global value.
- **SC-018**: A throttle response produces backoff and a reported condition, not a retry storm.
- **SC-019**: The skill states the Globalping boundary, and states which of `gtrace`'s existing
  `asn_lookup`/`geo_lookup` questions belong to `gtrace` rather than here.
- **SC-020**: A per-capability verification table exists distinguishing live-exercised from static-only,
  with **every** capability live-exercised or its absence explicitly justified.
- **SC-020a**: The registered tool manifest measures **≤ 5,000 tokens**, with the figure recorded and the
  check enforced by a test that fails the build if exceeded.
- **SC-021**: `reconcile-mcp.py` exits 0 across all four surfaces; `verify-inventory-counts.py` exits 0
  with updated counts; `trace-skill.py` resolves for every new skill.
- **SC-022**: `SOUL.md` gains a capability section describing the external plane and its routing
  boundaries — not merely an incremented count.

## Assumptions

- **All five sources are public and unauthenticated for the capabilities in scope.** Verified reachable
  2026-08-03: RDAP (via bootstrap and RIPE), PeeringDB, RIPEstat (`as-overview`, `routing-status`,
  `rpki-validation`), RIPE Atlas read-only — all HTTP 200 with no credentials.
- **ARIN's RDAP is unreachable from this host** (connection reset). The bootstrap redirector and RIPE's
  RDAP both work, so registry lookups remain viable; this is a source-selection consequence, not a blocker.
- **RIPEstat is the sole RPKI validation source**, and the feature is explicit about that rather than
  implying corroboration (FR-007a). Cloudflare's `rpki.cloudflare.com/api/v1/validity/...` 404s as measured;
  whether that is a moved path or a withdrawn endpoint is a **Phase 0 research question**. If a second
  validator is found reliably reachable, adding corroboration is a clean follow-on — the source-attribution
  machinery (FR-019/FR-021) already supports per-element provenance, so agreement/disagreement reporting
  would slot in without redesign.
- **Rate limits are undocumented in responses.** Neither RIPEstat nor PeeringDB advertises rate-limit
  headers, so courtesy behaviour must be derived from published policy rather than negotiated at runtime.
- **RIPE Atlas *measurement* execution requires credentials and credits; read-only inventory does not.**
  Only the read-only half is in scope, which is also why FR-018 routes measurement to R8.
- **`gtrace`'s existing enrichment stays as it is.** This feature does not modify it; FR-032 draws the
  boundary rather than absorbing it.
- **No credentials, therefore no secret handling beyond the usual.** There is no API key to leak, which
  removes a whole class of risk present in specs 078 and 080.

## Out of Scope

- **Hijack detection or alerting.** This feature reports RPKI state and routing observations. Declaring an
  incident, correlating events over time, or paging someone is an operator judgement and a different
  product (FR-007).
- **Continuous BGP monitoring or historical analysis.** These are point-in-time lookups. Trend and
  time-series work belongs to a monitoring platform, not here.
- **Running RIPE Atlas measurements** — credentials, credits, and R8 already owns outside-in measurement
  (FR-018).
- **Operating an RPKI validator.** NetClaw consumes published validation; running Routinator or similar is
  an infrastructure decision, not an integration.
- **Quick per-hop ASN/geo enrichment** — already delivered by `gtrace-ip-enrichment` (FR-032).
- **IRR / RPSL objects (`route:`, `as-set`) and BGP communities.** Adjacent and genuinely useful, but a
  distinct data model and a separate body of work; deliberately deferred rather than half-done.
