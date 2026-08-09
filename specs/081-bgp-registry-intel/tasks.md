# Tasks: BGP & Registry Intelligence (RPKI / RDAP / PeeringDB / RIPEstat)

**Input**: Design documents from `/specs/081-bgp-registry-intel/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.md, quickstart.md
**Roadmap**: R9 — Tier 2, "the internet / external plane"

**Tests**: Included, and mandatory. SC-012 requires provenance be asserted *mechanically across all tools,
not spot-checked*; SC-016a requires the rate limit be proven from an observed request timeline. Neither is
demonstrable by inspection. Spec 080 also shipped a null-fields bug past 24 passing tests, so this task list
separates **structural** tests (no network) from **live** tests (real APIs) and requires both.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 RPKI · US2 registry · US3 routing · US4 peering · US5 Atlas

## Path Conventions

New vendored server at `mcp-servers/bgp-intel-mcp/`, one skill at
`workspace/skills/bgp-registry-intel/`, tests at `tests/bgp-intel/`. Per plan.md "Source Code".

---

## ⚠️ No external blockers — and that raises the bar

Unlike spec 080 (three appliances, a licence saga, 13 of 21 tools unexercised) and R4 (waiting on a
human-reviewed vendor trial), **every source here is public and reachable today**. Verified before the spec
was written and again in Phase 0.

FR-037 therefore sets a harder standard: **near-total live verification is the expectation, not the
aspiration.** Any capability that ships unexercised must be justified explicitly or cut.

---

## Phase 1: Setup

- [ ] T001 Create `mcp-servers/bgp-intel-mcp/` with a `sources/` subpackage and `__init__.py` files per plan.md
- [ ] T002 Add `.gitignore` negation for `mcp-servers/bgp-intel-mcp/` — the repo ignores `mcp-servers/*` broadly and a new server dir is otherwise silently untracked (docs/ADDING-AN-MCP.md step 1)
- [ ] T003 Write `requirements.txt` with `mcp>=1.2.0,<2` and `httpx>=0.27.0,<1`, including the comment that the upper bound is load-bearing — **mcp v2 now exists** and removes `mcp.server.fastmcp` (spec 077, research R5)
- [ ] T004 Create `server.py` FastMCP skeleton, stdio transport, JSON-RPC lifecycle (Principle V), no tools yet
- [ ] T005 [P] Create `tests/bgp-intel/run-tests.sh` following `tests/reconcile/run-tests.sh` — bash + stdlib, no new framework

---

## Phase 2: The distinctions and provenance (BLOCKS EVERYTHING)

**This phase is the feature.** The four RPKI states are why this is a spec and not a wrapper.

- [ ] T006 Implement `outcomes.py` with the RPKI state model: `state` ∈ `valid`/`invalid`/`not_found` and `reason` ∈ `as`/`length`/`None`, as **separate fields** (FR-002, data-model §3)
- [ ] T007 Implement the `Outcome` enum in `outcomes.py` with all seven values from data-model §2, keeping `no_record`, `source_unavailable` and `input_refused` distinct (FR-011)
- [ ] T008 Add `validation_unavailable` as its own outcome, **distinct from `not_found`** — an unreachable validator is not unsigned space (FR-007c). This is the subtlest bug available in this feature
- [ ] T009 Implement `is_finding` in `outcomes.py`: `true` **only** for `invalid`. `not_found` and `valid` are both non-findings (FR-003)
- [ ] T010 Implement the RIPEstat vocabulary mapping in `outcomes.py`: `unknown`→`not_found`, `invalid_asn`→(`invalid`,`as`), `invalid_length`→(`invalid`,`length`), for the fallback path only (FR-004)
- [ ] T011 Implement `envelope.py` `emit()` stamping `source`, `retrieved_at`, `outcome`, `cached`, `cache_age_seconds`, `query`, `data`, `caveats` (FR-019, data-model §1)
- [ ] T012 Make `envelope.py` a **chokepoint** — a wrapper every tool response must pass through, so provenance cannot be omitted by a tool added later (FR-020)
- [ ] T013 Enforce in `envelope.py` that a response with no nameable `source` is an **error**, not an unattributed answer (FR-019)
- [ ] T014 Implement `caveats` as a **structured field** carrying the FR-009/013/016 statements, so they survive a model summarising the payload
- [ ] T015 [P] Contract test `tests/bgp-intel/test_outcomes.py`: all four RPKI states distinct; `not_found` has `is_finding=False`; `validation_unavailable` ≠ `not_found` — **no network** (SC-004, SC-005b)
- [ ] T016 [P] Contract test `tests/bgp-intel/test_envelope.py`: every envelope carries source + retrieved_at; a source-less response errors — **no network** (SC-012)
- [ ] T017 [P] Contract test asserting the strings `invalid`, `suspicious` and `unverified` **never appear** in a rendered `not_found` result (SC-004) — the feature's central promise, tested as text
- [ ] T017a [P] Contract test asserting the strings `confirmed`, `verified` and `cross-checked` **never appear** in **any** RPKI result, and that `corroborated` is literally `false` (SC-005a, FR-007a). Both reachable validators are RIPE NCC Routinator, so implying corroboration would be false — this is tested as text because it is a claim about wording, not structure
- [ ] T017b [P] Contract test asserting a `not_found` result and a `validation_unavailable` result are **distinguishable in rendered output**, not merely different enum values (SC-005b, FR-007c)

---

## Phase 3: Audit (same chokepoint — Principle IV)

> Placed here, not at the end, because `/speckit.analyze` caught spec 080 with an audit **verification**
> task and no **implementation** task. Verifying an unimplemented guarantee passes by accident.

- [ ] T018 Implement GAIT emission **inside** `envelope.emit()` so every operation is audited by construction (FR-022, Principle IV)
- [ ] T019 Ensure the audit record carries tool, query, source, outcome, `cached`, and timestamp — the shape of the operation, not bulk payload (data-model §10)
- [ ] T020 Ensure refusals and failures are audited too, not only successes — a refused private-address lookup is an operation that happened
- [ ] T021 Surface a GAIT write failure rather than swallowing it: an unaudited operation violates Principle IV whether the tool call worked or not
- [ ] T022 [P] Contract test `tests/bgp-intel/test_audit.py`: every invocation including refusals emits exactly one record — **no network** (FR-022)

---

## Phase 4: Request discipline (BLOCKS all source work)

- [ ] T023 Implement `http_client.py` with a per-source rate limiter: **≤ 4 req/s and concurrency 1** (FR-023)
- [ ] T024 Enforce the limit **at the request layer**, not by caller discipline, so a tool added later inherits it without knowing it exists (FR-023b)
- [ ] T025 Implement the per-source TTL cache in memory: RPKI 5 min, routing 15 min, RDAP/PeeringDB/Atlas 24 h (FR-026, data-model §8)
- [ ] T026 Ensure the cache is **in-memory and session-scoped** — no on-disk store, deliberately unlike spec 078 (FR-026a)
- [ ] T027 Report `cached` **and** `cache_age_seconds` on cached responses (FR-026b)
- [ ] T028 Implement `fresh=true` cache bypass, for when a ROA was just published and the 5-min TTL is the only thing hiding the truth (FR-026c)
- [ ] T029 Set a `User-Agent` identifying NetClaw plus a contact reference (FR-025, SC-017)
- [ ] T030 Implement backoff on throttle → `rate_limited` outcome, never a retry storm (FR-027, SC-018)
- [ ] T031 [P] Contract test `tests/bgp-intel/test_rate_limit.py`: a multi-target batch never exceeds 4/s and never issues concurrent requests to one source, asserted from an **observed request timeline** against a local stub — **no external network** (SC-016a)
- [ ] T032 [P] Contract test `tests/bgp-intel/test_cache.py`: RPKI entries expire at 5 min while RDAP survives, proving TTLs are genuinely per-source; `fresh=true` bypasses (SC-017a, SC-017b)

---

## Phase 5: Input refusal (BLOCKS all source work)

> Before Phase 6 because FR-028 is a **disclosure control**, not a validation nicety. Sending an internal
> address to a public registry is a disclosure even if the query then fails — spec 079's reasoning.

- [ ] T033 Implement `validate.py` refusing RFC1918, loopback, link-local, CGNAT 100.64/10, multicast, reserved (FR-028)
- [ ] T034 Refuse documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24, 2001:db8::/32) and IPv6 ULA fc00::/7 (FR-028)
- [ ] T035 Refuse malformed input: bad prefix length, non-numeric ASN, mixed address family, AS0 (FR-030)
- [ ] T036 Ensure refusal happens **before any outbound request** and yields `input_refused` with an explanation (FR-028)
- [ ] T037 Support IPv4 **and** IPv6 across all validation paths (FR-029)
- [ ] T038 [P] Contract test `tests/bgp-intel/test_validate.py`: each refused class is refused with **no request issued**, verified by a stub that records calls — **no network** (SC-015)
- [ ] T038a [P] Contract test asserting the server exposes **no tool that mutates anything** — every registered tool is a read (FR-034). Structurally true today because no write code exists; the test keeps it true when someone later adds a tool

---

## Phase 6: US1 — RPKI origin validation (P1) 🎯 MVP

**Goal**: answer "is this announcement legitimate?" — the capability nothing else in NetClaw has.

**Independent test**: query the four fixture pairs from quickstart.md and confirm four distinct outcomes.

- [ ] T039 [US1] Implement `sources/rpki.py` against **`rpki-validator.ripe.net/api/v1/validity/`** as primary — RFC 6811 vocabulary natively, `state`/`reason` separate, VRPs included (FR-001, research R2)
- [ ] T040 [US1] Parse and return `vrps_matched`, `vrps_unmatched_as`, `vrps_unmatched_length` so the operator can check the reasoning rather than trust a label (FR-005)
- [ ] T041 [US1] Include the validator's own `description` sentence, and name the validator on every result with `corroborated: false` (FR-007a)
- [ ] T042 [US1] Implement the RIPEstat fallback path, applying the T010 vocabulary mapping and **stating that a translation occurred** (FR-004)
- [ ] T043 [US1] On `invalid`, name **what the ROA does authorise** — permitted ASN and maxLength — because that is what makes it actionable (FR-006)
- [ ] T044 [US1] Attach the `not_found` caveat: normal for most address space, **not a finding** (FR-003)
- [ ] T044a [US1] Frame results to reflect the **error asymmetry** (FR-007b): a `valid` result states it reflects one validator's current view and is not a guarantee of legitimacy; an `invalid` result states what would need checking before treating it as an incident. A wrong `valid` says an announcement is authorised when it is not; a wrong `invalid` sends someone chasing a hijack that is not happening. Both are worse than an honest single-validator view
- [ ] T045 [US1] Ensure the tool never emits the words hijack, attack or incident (FR-007, SC-009)
- [ ] T046 [US1] Map validator-unreachable to `validation_unavailable`, and **never** infer state from routing, registry, or absence of a ROA (FR-007c)
- [ ] T047 [US1] Register `rpki_validate(prefix, origin_asn, fresh)` in `server.py` per contracts
- [ ] T048 [US1] **Live-verify all four states** against the fixtures: `AS13335`+`1.1.1.0/24`→valid; `AS13335`+`8.8.8.0/24`→invalid/as; `AS15169`+`8.8.8.128/25`→invalid/length; `AS3356`+`4.0.0.0/9`→not_found (SC-001, SC-002, SC-003, SC-004, SC-005)
- [ ] T049 [US1] **Live-verify IPv6**: `AS13335`+`2606:4700::/32` returns a verdict (SC-016, FR-029)

**Checkpoint**: US1 alone is a shippable MVP.

---

## Phase 7: US2 — Registry records (P1)

- [ ] T050 [US2] Implement `sources/rdap.py` resolving the responsible RIR from the **IANA bootstrap file** (RFC 7484), then querying that RIR directly (research R4)
- [ ] T051 [US2] Implement the `rdap.org` fallback for when a direct RIR endpoint fails
- [ ] T052 [US2] Return holder, allocation range, registry, abuse contacts, events; **name the responding registry and how it was selected** (FR-008, FR-010)
- [ ] T053 [US2] Attach the caveat: **allocation data, not evidence about who is announcing** (FR-009)
- [ ] T054 [US2] Map a registry reset/timeout/refusal to `source_refused`/`source_unavailable` **naming that registry** — never `no_record` (FR-011)
- [ ] T055 [US2] Register `registry_lookup` and `registry_abuse_contact` per contracts
- [ ] T056 [US2] **Live-verify across at least two different RIRs**, with the registry named on each (SC-006)
- [ ] T057 [US2] **Live-verify the ARIN failure path** yields a named source failure, not "no record" (SC-007)
- [ ] T058 [US2] Retry ARIN from a different network path to establish whether the reset is host-specific — **do not document it as a property of ARIN until confirmed** (research open item 2)

---

## Phase 8: US3 — Routing status (P2) · US4 — Peering (P2)

- [ ] T059 [P] [US3] Implement `sources/routing.py` for RIPEstat `as-overview` and `routing-status` (FR-012)
- [ ] T060 [US3] Return per-prefix visibility with **`collector_basis`** on every result (FR-013)
- [ ] T061 [US3] Ensure the tool never attaches `leak` or `hijack` to a low-visibility prefix (FR-013, SC-009)
- [ ] T062 [US3] Distinguish "no announcements observed" from "AS does not exist" from "query failed" (FR-014)
- [ ] T063 [US3] Bound large result sets with `truncated` and `total_available` — never silently cut
- [ ] T064 [P] [US4] Implement `sources/peeringdb.py` for the network record, IXPs and facilities (FR-015)
- [ ] T065 [US4] Attach the **self-reported** caveat to every result; absent record ⇒ `no_record` with "not evidence the network does not peer" (FR-016)
- [ ] T066 [US3][US4] Register `routing_as_overview`, `routing_announced_prefixes`, `peering_network`, `peering_presence`
- [ ] T067 [US3] **Live-verify** an AS overview and announced prefixes with collector basis stated (SC-008)
- [ ] T068 [US4] **Live-verify** a rich PeeringDB record, and find an ASN **genuinely absent** from PeeringDB to verify the no-record path rather than assuming one exists (SC-010, research open item 3)

---

## Phase 9: US5 — Atlas, narrowed (P3)

- [ ] T069 [US5] Implement `sources/atlas.py` for **anchors by country** and **probe count by AS** — and nothing broader (FR-017)
- [ ] T070 [US5] Ensure general probe-availability-by-location is **not implemented**; such a request is routed to Globalping's `locations` (FR-017a)
- [ ] T071 [US5] Route any request to *run* a measurement to Globalping (R8), never attempt it here (FR-018)
- [ ] T072 [US5] Register `atlas_anchors` and `atlas_probe_count`
- [ ] T073 [US5] **Live-verify** anchors for a country and probe count for an AS (SC-011)

---

## Phase 10: Composite report and manifest budget

- [ ] T074 Implement `resource_report(resource)` running RPKI, registry, routing and peering into one report
- [ ] T075 Ensure **per-element provenance** — each section carries its own source, never one collective citation (FR-021, SC-013)
- [ ] T076 Run sub-queries **serially**. This is the tool most likely to attract an `asyncio.gather`; FR-023a prohibits it
- [ ] T077 Report a failed section **within** the report; the report does not fail wholesale (FR-011)
- [ ] T078 Report source **disagreement** (RDAP holder vs PeeringDB name) rather than resolving it silently
- [ ] T079 Measure the serialised `tools/list` token count with `count_tokens` and **record the number** (FR-025 measurement, FR-027a)
- [ ] T080 Assert the manifest is **≤ 5,000 tokens**; merge tools or fold parameters if exceeded (FR-027a)
- [ ] T081 [P] Contract test `tests/bgp-intel/test_manifest_size.py` failing the build if the ceiling is breached — **no network** (FR-027b, SC-020a)
- [ ] T082 [P] Document the measured figure in the server README (FR-027c)
- [ ] T083 **Live-verify** `resource_report` returns per-element provenance and runs serially (SC-013, SC-016a)

---

## Phase 11: Artifact coherence (Principle XI — NON-NEGOTIABLE)

- [ ] T084 Register `bgp-intel-mcp` in `config/openclaw.json` with **repo-relative** paths, `command` + `args` separate — never an absolute path under `/home/` (docs/ADDING-AN-MCP.md step 2)
- [ ] T085 Add a catalog entry to `scripts/lib/catalog.sh` under an appropriate category
- [ ] T086 Add the component to **curated profiles** — `PROFILE_SECURITY` and `PROFILE_RECOMMENDED`. A component in no profile appears only in the fine-tune checklist, the gap that caught spec 076
- [ ] T087 Add `component_install_bgp_intel()` to `scripts/lib/install-steps.sh` using `netclaw_pip_install`, **never** bare `pip`/`pip3` (spec 077, FR-042)
- [ ] T088 Add the HUD **node list** entry in `ui/netclaw-visual/server.js` — `{ id, name, prefixes }`
- [ ] T089 Add the HUD **annotation map** entry in `ui/netclaw-visual/server.js`. **Both are required**; the annotation alone renders no node
- [ ] T090 [P] Update `README.md` — description, architecture, **and the counts** (206→207 skills, 153→154 integrations)
- [ ] T091 Update `SOUL.md` counts **and** add a capability section describing the external plane and its routing boundaries — a bumped count does not tell the agent what it can do (FR-038, SC-022)
- [ ] T092 [P] Update `.env.example` with the three optional tuning variables, **names and descriptions only**. Note explicitly that this integration needs **no credentials**
- [ ] T093 [P] Update `TOOLS.md` with the BGP/registry reference including the four-state table
- [ ] T094 [P] Write `mcp-servers/bgp-intel-mcp/README.md` — tools, sources, the four states, rate-limit posture, measured manifest count
- [ ] T094a Record in the README that **neither RIPEstat nor PeeringDB advertises rate-limit headers** and that the 4 req/s figure is therefore **NetClaw's own conservative choice, not a service-declared limit** (FR-024). A later maintainer who finds a published limit must not mistake this number for it
- [ ] T094b Record in the README the deliberate **`not-found` (wire) vs `not_found` (code)** distinction: the validator returns the hyphenated RFC 6811 spelling, the internal model uses the underscored identifier. They are intentionally different and "fixing" either to match the other would break the mapping
- [ ] T095 Run `python3 scripts/reconcile-mcp.py`; must exit 0 across all four surfaces (FR-039, SC-021). Check the exit code **directly** — never through a pipe, which reports the pipe's status
- [ ] T096 Run `python3 scripts/verify-inventory-counts.py`; must exit 0 with updated counts (FR-040)

---

## Phase 12: Skill and honest reporting

- [ ] T097 Create `workspace/skills/bgp-registry-intel/SKILL.md` — **one skill**, because these four sources answer facets of one operator question (plan.md Structure Decision)
- [ ] T098 State the four RPKI states in the skill, with **`not_found` explicitly marked normal and not a finding** (FR-003)
- [ ] T099 State the boundary against **Globalping (R8)**: Globalping measures, this looks up (FR-031)
- [ ] T100 State the boundary against **`gtrace-ip-enrichment`**: `gtrace` owns quick ASN/geo/rDNS hop enrichment, this owns authoritative registry, RPKI, routing and peering (FR-032, SC-019)
- [ ] T101 State the boundary against `nvd-cve`/`cisco-psirt`: software vulnerability vs routing legitimacy (FR-033)
- [ ] T102 State the three "not what you think" caveats in the skill: registry ≠ routing, PeeringDB self-reported, visibility is collector-based
- [ ] T102a State in the skill that these lookups serve a **specific operational question** and MUST NOT be used to enumerate, sweep or bulk-harvest registry data (FR-035). These are volunteer-funded services; the rate limiter enforces politeness mechanically, but the skill must not *direct* NetClaw toward harvesting in the first place
- [ ] T102b State in the skill the **error asymmetry** from T044a, so an operator reading an `invalid` knows what to check before escalating (FR-007b)
- [ ] T103 Run `python3 scripts/trace-skill.py bgp-registry-intel`; must resolve (FR-041)
- [ ] T104 Build the per-capability verification table distinguishing **live-exercised** from **static-only** (FR-036, SC-020)
- [ ] T105 **Justify or cut** any capability not live-exercised. Every source is public, so FR-037 gives no excuse — this is a harder bar than spec 080 met
- [ ] T106 Confirm every operation during verification produced a GAIT record (FR-022, SC-014)
- [ ] T107 Update `docs/COVERAGE-ROADMAP.md` R9 status to `DONE` with the outcome, following the R1/R2/R3/R8 format
- [~] T108 ~~Draft the milestone blog post~~ — **SKIPPED by operator decision** (Principle XVII). R3's post was also written but never published; a backlog of unpublished drafts is worse than none. Revisit as a batched write-up across R3/R9 if wanted.

---

## Dependencies

```
Phase 1 (Setup)
   └─> Phase 2 (outcomes + envelope)        ← BLOCKS EVERYTHING. The distinctions ARE the feature
          └─> Phase 3 (GAIT in the chokepoint)
                 ├─> Phase 4 (rate limit + cache) ─┐
                 └─> Phase 5 (input refusal) ──────┤
                                                   ├─> Phase 6  (US1 RPKI)  🎯 MVP
                                                   ├─> Phase 7  (US2 registry)
                                                   ├─> Phase 8  (US3 routing, US4 peering)
                                                   └─> Phase 9  (US5 Atlas)
                                                          └─> Phase 10 (composite + manifest)
                                                                 └─> Phase 11 (artifacts)
                                                                        └─> Phase 12 (skill + reporting)
```

**Story independence**: US1–US5 are each independently deliverable once Phases 4 and 5 land. Only Phase 10's
`resource_report` depends on more than one story.

**Phases 4 and 5 both gate all source work** — the rate limiter so no source can bypass it, input refusal so
nothing can call out with a private address.

## Parallel opportunities

- **Phase 2**: T015, T016, T017 parallel with each other
- **Phase 3**: T022 parallel with Phase 4 start
- **Phase 4/5**: T031, T032, T038 parallel
- **Phase 8**: T059 and T064 parallel (different files)
- **Phase 11**: T090, T092, T093, T094 parallel

**Note**: parallel *task execution* is fine. Parallel *HTTP requests to one source* is prohibited (FR-023a).

## Implementation strategy

**MVP = Phases 1 → 2 → 3 → 4 → 5 → 6.** That delivers RPKI origin validation with all four states, full
provenance and audit — the capability nothing else in NetClaw has. Phases 7–9 are additive; Phase 10's
composite needs at least two sources.

**Phase 2 is not optional scaffolding — it is the deliverable.** Writing a source first and adding the
distinction afterwards produces exactly the code that collapses `not_found` into `invalid`, because
collapsing is the path of least resistance once you already hold a string from an API.

**Total: 116 tasks** — 108 from the initial pass plus nine added by `/speckit.analyze` remediation:

| Added | Closes |
|---|---|
| T017a, T017b | **SC-005a** forbidden-words test, and rendered-output distinguishability of `not_found` vs `validation_unavailable` |
| T038a | **FR-034** read-only assertion — keeps it true when a tool is added later |
| T044a, T102b | **FR-007b** the valid/invalid error asymmetry, in output framing and in the skill |
| T094a | **FR-024** documenting that 4 req/s is self-imposed, not service-declared |
| T094b | The deliberate `not-found` (wire) vs `not_found` (code) spelling, so nobody "fixes" it into a bug |
| T102a | **FR-035** no enumeration, sweeping or bulk-harvesting of registry data |

**Every task can be completed today.** Nothing waits on a licence, trial, appliance or vendor — which is why
FR-037's near-total live verification is an expectation here rather than an aspiration.
