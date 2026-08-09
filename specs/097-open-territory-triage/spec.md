# Feature Specification: Open-territory triage (R24)

**Feature Branch**: `097-open-territory-triage`
**Created**: 2026-08-05
**Status**: Draft
**Roadmap**: R24 — the last unstarted Tier A item, and the one that re-prioritises the others

## Overview

R24 lists 22 candidate integrations for which no mature MCP was found — "flag-planting opportunities
rather than gaps". It has never been assessed. Meanwhile **R1 shipped a multivendor CLI driver
reaching roughly 90 platform families**, which its own spec says covers MikroTik RouterOS, VyOS,
SONiC, Nokia SR Linux, Extreme, Huawei, Dell and Ubiquiti EdgeOS by name.

So the list is stale in an unknown way, and its first checklist item says so: *"After R1 lands,
re-test which platforms remain genuinely unreachable."*

**This feature produces a decision, not a server.** Its output is a disposition for every candidate
and, at most, one or two selected for their own future spec.

Left un-triaged, the list has a specific cost: it is 22 unassessed items that look like a backlog.
Anyone planning work has to re-derive the same conclusions, and the roadmap's own instruction —
*"record as DEFERRED with a reason so it isn't re-litigated"* — exists because that re-derivation
has a way of happening repeatedly.

## Clarifications

### Session 2026-08-05

- Q: For a candidate marked `SELECTED`, must the triage *demonstrate* verifiability or is a
  documented access check enough? → A: **Documented access check.** Record what access exists and
  what would verify it; do not stand the lab up. This is a triage — the selected candidate's own
  spec does the proving.
- Q: Where should the 22 dispositions live? → A: **A separate triage document**
  (`specs/097-open-territory-triage/TRIAGE.md`), with the roadmap's R24 section carrying a summary
  and linking out. Same shape spec 093 used with `FINDINGS.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Deciding what to build next (Priority: P1)

A maintainer finishing a roadmap item opens the roadmap to pick the next one. R24 presents 22
candidates with no indication of which are already reachable, which are blocked on access they do
not have, and which are worth real effort.

**Why this priority**: This is the whole feature. Every other outcome follows from a maintainer
being able to read a disposition instead of re-running an investigation.

**Independent test**: Deliver only this and the roadmap is usable for planning — a maintainer can
choose the next item without opening a terminal.

**Acceptance scenarios**:

1. **Given** the triaged roadmap, **when** a maintainer looks at any of the 22 candidates, **then**
   they find one of exactly four dispositions — `COVERED`, `SELECTED`, `DEFERRED`, `DROPPED` — each
   with a reason stated in one or two sentences.
2. **Given** a candidate marked `COVERED`, **when** the maintainer asks what covers it, **then** the
   entry names the specific server or spec that does.
3. **Given** a candidate marked `DEFERRED`, **when** the maintainer considers re-opening it,
   **then** the entry states the condition that would change the answer.

### User Story 2 — Not re-litigating a settled question (Priority: P2)

Someone proposes building one of the deferred candidates. The roadmap should answer without a new
investigation.

**Independent test**: Pick any deferred candidate, propose it, and check whether the recorded reason
settles the question on its own.

**Acceptance scenarios**:

1. **Given** a `DEFERRED` entry, **when** someone proposes it, **then** the recorded reason is
   specific enough to accept or rebut without re-measuring — naming the blocker, not a sentiment.
2. **Given** a `DROPPED` entry, **when** someone proposes it, **then** the entry explains what would
   have to become true, or states plainly that nothing would.

### User Story 3 — Knowing that "covered" is true, not assumed (Priority: P2)

R1's spec *claims* coverage of eight named platforms. A claim is not a verification, and this
project has been bitten by exactly that gap before — spec 088's seven dead registered servers, spec
093's 14 invented tool names.

**Independent test**: Take every `COVERED` disposition and check whether its evidence is a
measurement or a claim, and whether the entry says which.

**Acceptance scenarios**:

1. **Given** a candidate marked `COVERED` **by R1**, **when** the disposition is challenged, **then**
   the evidence cited is either a live verification or an explicit statement that coverage is
   claimed-but-unverified.
2. **Given** a platform R1 claims but cannot demonstrate, **when** it is triaged, **then** it is not
   marked `COVERED` on the strength of the claim alone.

### Edge Cases

- **A candidate is partially covered.** Some capability is reachable and some is not (a device CLI is
  reachable but its controller API is not). The disposition must state which half, and the uncovered
  half must get its own disposition rather than being averaged away.
- **A candidate is reachable but not usefully.** R1 can open a session to a platform without a skill
  making that platform's data meaningful. Reachability is not the same as coverage, and the two must
  not be conflated.
- **A candidate cannot be verified with available access.** By the roadmap's own verifiability rule
  this is `DEFERRED` with the missing access named — never `SELECTED` on the strength of its value.
- **A candidate turns out to have acquired a mature MCP** since the list was written. That changes it
  from build-candidate to adopt-candidate, and the manifest ceiling then decides.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** Every one of the 22 candidates MUST receive exactly one disposition: `COVERED`,
  `SELECTED`, `DEFERRED`, or `DROPPED`. No candidate may be left unassessed.
- **FR-002** Every disposition MUST carry a reason. A reason MUST name a specific blocker, covering
  server, or measurement — not a judgement such as "low value".
- **FR-003** A `COVERED` disposition MUST name what covers it, and MUST distinguish **verified**
  coverage from **claimed** coverage.
- **FR-004** A `DEFERRED` disposition MUST state the condition that would change the answer.
- **FR-005** **At most two** candidates may be `SELECTED`. The roadmap's instruction is "at most one
  or two"; selecting more would recreate the unassessed backlog this feature exists to remove.
- **FR-006** A `SELECTED` candidate MUST be verifiable with access already available, per the
  roadmap's verifiability-first rule. If it cannot be verified today it is `DEFERRED`, however
  valuable. Verifiability is established by a **documented access check** — naming the access that
  exists and what would exercise it — **not** by standing the environment up. Demonstration belongs
  to the selected candidate's own spec.
- **FR-006a** Because no environment is stood up, **no candidate's disposition may rest on an
  untested assumption presented as fact.** Where coverage or verifiability is asserted rather than
  observed, the entry MUST say so (see FR-003 and FR-010).
- **FR-007** Each `SELECTED` candidate MUST be recorded with enough detail to start its spec without
  repeating this assessment: what it does that nothing else does, what would verify it, and what the
  manifest-cost risk is.
- **FR-008** Candidates whose capability is already reachable MUST be `COVERED` or `DROPPED`, not
  `DEFERRED` — deferral implies a future, and there is none for redundant work.
- **FR-009** The full dispositions MUST live in `specs/097-open-territory-triage/TRIAGE.md`. The
  roadmap's R24 section MUST be rewritten to carry a **summary** — counts by disposition, the
  `SELECTED` candidates, and a link to the triage document — replacing the untriaged candidate list.
  The full table MUST NOT be duplicated into the roadmap: two copies drift the first time either is
  edited, and the roadmap is already ~1,200 lines.
- **FR-010** The triage MUST record which candidates were assessed **by measurement** and which by
  desk research, so a reader can weigh them differently.

### Key Entities

- **Candidate** — a named integration target from R24's list. Attributes: name, category,
  disposition, reason, evidence type (measured / desk research), and for `DEFERRED`, the unblocking
  condition.
- **Disposition** — one of four states. `COVERED` (the capability is already reachable), `SELECTED`
  (worth its own spec, and verifiable now), `DEFERRED` (worth doing, blocked on a named condition),
  `DROPPED` (assessed and rejected; will not be revisited).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** All 22 candidates carry a disposition and a reason. Count of unassessed candidates: **0**.
- **SC-002** At most 2 candidates are `SELECTED`.
- **SC-003** Every `COVERED` entry names its covering server or spec, and states whether that
  coverage is verified or claimed.
- **SC-004** Every `DEFERRED` entry names the condition that would unblock it.
- **SC-005** A maintainer can decide whether to build any candidate by reading its entry alone,
  without re-running an investigation.
- **SC-006** Each `SELECTED` candidate has enough recorded detail that its spec can begin without
  repeating this assessment.
- **SC-007** No candidate is `SELECTED` that cannot be verified with currently available access,
  where "can be verified" is established by a documented access check naming the access and what
  would exercise it.
- **SC-008** The dispositions exist in exactly **one** place — `TRIAGE.md` — with the roadmap
  carrying a summary and a link, and no duplicated table.

## Assumptions

- **R1's platform claims are the starting point, not the conclusion.** Its spec names eight platforms
  it reaches; only Nokia SR Linux and FRR were verified live. The rest are claimed. Where a
  candidate's disposition rests on R1 coverage, that distinction is recorded rather than smoothed
  over.
- **Available access** means what this environment demonstrably has: containerlab with an Arista vEOS
  image and Nokia SR Linux, GNS3/EVE-NG, CML, a FortiGate, Docker, and **no vendor cloud tenants**.
  The R5 and R12 experiences establish that assuming access is how a spec stalls.
- **Desk research eliminates; a documented access check selects.** Marking something `DEFERRED`
  because a tenant is required needs no lab. Marking something `SELECTED` requires naming the access
  that exists and what would exercise it — an inventory check against this environment, not a
  literature review, and not a lab build (per the 2026-08-05 clarification). The distinction that
  matters is between *checking what we have* and *assuming what we have*; it was the second that
  stalled R5.
- **This feature adds no MCP server, no skill and no registration**, so `docs/ADDING-AN-MCP.md` does
  not apply to it — only to whatever a `SELECTED` candidate later becomes.

## Out of Scope

- **Building any selected candidate.** Selection produces a roadmap item, not an implementation.
- **Re-assessing items already dispositioned elsewhere** — R10 (deferred), R22 (closed) and R5
  (blocked) keep their existing states.
- **Expanding the candidate list.** New territory found during triage is recorded as a note, not
  silently added and assessed.
