# Tasks: Globalping Global Probe Measurement

**Feature**: 079-globalping-probes | **Date**: 2026-07-31 | **Roadmap**: R8
**Input**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [contracts/mcp-tools.md](./contracts/mcp-tools.md) · [quickstart.md](./quickstart.md)

> **Read research R4, R5 and R6 first.** R4 inverts the previous spec's budget strategy, R5 shows the
> vendor's own documented example is broken, and R6 is the safety semantic the whole feature exists for.

## Three things that shape this list

**1. There is no server to write.** The deliverable is a registration plus a skill. That makes the *skill*
the engineering artifact, not documentation of one — every safety property in this feature lives in prose,
because prose is the only mechanism a remote MCP gives us.

**2. `no_probes_found` must never read as an outage.** A location filter narrower than probe coverage returns
a failure-shaped response that says nothing about the target. An agent that reports it as unreachability
escalates an incident that does not exist. Same class as spec 078's "empty ≠ safe".

**3. Budget is charged PER PROBE, so `limit` is the thing being spent.** `limit: 20` costs 20 of 500;
`limits` calls cost nothing. Research R4 first concluded per-call billing and was **wrong** — a controlled
test corrected it, and the correction is recorded in R4 rather than overwritten. Practical effect: the same
economy instinct spec 078 needed applies here; the two differ only in what a unit buys (078 per distinct
query, this per probe).

---

## Phase 1: Registration

**Blocking — nothing is testable until the endpoint answers through NetClaw.**

- [x] T001 Read `specs/079-globalping-probes/research.md` in full. Four of the spec's starting assumptions were wrong; R4 and R5 are the ones that change behaviour.
- [x] T002 Register the remote endpoint `https://mcp.globalping.dev/mcp` in `config/openclaw.json` following the existing remote-MCP pattern (Datadog, DevNet content search). **No `mcp-servers/` directory** — the absence is the design decision from R1, not an omission (FR-001).
- [x] T003 Wire `GLOBALPING_TOKEN` as the bearer credential. The endpoint returns **401** without it (FR-002). A missing token MUST be reported **by variable name, never by value** (FR-003, SC-009).
- [x] T004 Verify the registration end to end: `initialize` → `tools/list` returns **12 tools**, and a `ping` returns attributed per-probe results.

---

## Phase 2: The skill's safety semantics (P1 — the substance)

**Goal**: NetClaw can tell the three "nothing came back" states apart and never conflates them.

**Independent test**: request `AS13335` and an unresolvable target; the first must be reported as *not run*,
the second as *unreachable*.

- [x] T005 [US1] Create `workspace/skills/globalping-external-checks/SKILL.md` with the five measurement tools — `ping`, `traceroute`, `dns`, `mtr`, `http` — as the documented capability (FR-004).
- [x] T006 [US1] **Document `no_probes_found` as "the measurement did not run"**, with a broader-filter suggestion, and an explicit instruction never to report it as an outage, unreachability, or a syntax error (FR-006, FR-006a). This is the highest-value sentence in the feature.
- [x] T007 [US1] Document **0-of-N successful probes** as a *positive finding* — the target is unreachable from those locations — distinct from T006 (FR-007).
- [x] T008 [US1] Require every latency/loss/resolver figure to carry its probe location, and forbid generalising one probe into a regional claim (FR-008, FR-008a).
- [x] T009 [US1] Document the budget model: 500/hour authenticated, 250/hour unauthenticated, and **cost equals probe count** (`limit: 5` spends 5; `limits` spends 0). Instruct NetClaw to choose the smallest `limit` that answers the question — 3-5 spot check, 10-20 for geographic spread, above 20 a conscious decision. Do **not** present breadth as free (FR-013, FR-013a).
- [x] T010 [US1] Document the location syntax as measured: `+` is AND, arrays express multiple locations, `world` works, ASN form works, **a comma inside one string fails** (FR-011).
- [x] T011 [US1] **Warn that `AS13335` — the vendor's own schema example — never returns probes**, and that an ASN failure usually means "no probes there" rather than "wrong syntax". Point at `locations` to check first (FR-011a).
- [x] T011b [US4] Document calling `limits` to report remaining budget and reset time **before** a large investigation, so an operator sees the allowance rather than discovering it mid-sweep (FR-014, SC-007).
- [x] T011a [US1] Document `limits` and `locations` as the two meta tools worth calling. Deliberately do **not** document `help`, `authStatus`, `compareLocations` or `get_more_tools` — self-describing, and guidance would add length without capability (FR-005).

---

## Phase 3: Scope boundary — outside-in only (P1)

- [x] T012 [US1] Refuse private/internal targets **locally, before any outbound call**: RFC1918, loopback, link-local, private IPv6, `localhost`. Globalping refuses them too, but by then an internal address has already reached a third party — the local refusal is a **disclosure control**, not a correctness one (FR-009).
- [x] T012a [US1] Every refusal MUST name the internal tool to use instead — pyATS, multivendor-cli, or gtrace — rather than only saying no (FR-009a).
- [x] T013 [US1] State that Globalping measures **from the internet toward a public target**, complementary to and never a substitute for NetClaw's inside-out tooling (FR-010).
- [x] T013a [US1] State that this is measurement of infrastructure the operator runs, **not scanning**: the skill MUST NOT direct NetClaw to sweep, enumerate or probe third-party infrastructure (FR-018).
- [x] T014 Document the `context` analytics field: send a **generic, task-shaped** 15-25 word value with no customer name, internal hostname, ticket reference or topology detail; state plainly that it **reaches a third party**; record that omission is accepted but not to be relied on (FR-012, FR-012a, FR-012b).
- [x] T014a Note that `limits` output echoes an 8-character token fragment, so tool output should not be pasted verbatim into a public place (Principle XIII).
- [x] T015 [US3] Document the composition boundaries: **ThousandEyes** for baselines and trends, **gtrace** for from-this-host paths, **Globalping** for "from out there, right now" (FR-015, FR-016, SC-010).
- [x] T015a Document DNS propagation and resolver disagreement as a **split**, never an average (US3, SC-005).

---

## Phase 4: Tests

- [x] T016 [P] Create `tests/globalping/run-tests.sh` — offline only, **spends no measurements**. Assert: registration present and portable; token referenced by name not value; skill documents all five measurement tools; skill contains the `no_probes_found` distinction, the `AS13335` warning, the local-refusal rule, and the budget model. **Capture exit codes without a pipe.**
- [x] T017 [P] Create `tests/globalping/live-api.sh` — **opt-in only**, ~15 probe-measurements. Verify SC-002 (`AS13335` → not-run), SC-003 (unresolvable → 0-of-N), SC-007 (`limits` figures match), SC-008 (**per-probe accounting**: `limit: 1` costs 1, `limit: 5` costs 5, `limits` costs 0).

---

## Phase 5: Integration — installer, identity, dashboard (Principle XI)

> **Every artifact explicit, because PR #204 found three missing after R1 and `reconcile-mcp.py` catches
> none of them.**

- [x] T018 Add a catalog entry to `scripts/lib/catalog.sh`: `"globalping|Observability|Globalping|..."`.
- [x] T019 **Add `globalping` to the curated profiles it belongs in** — `PROFILE_OBSERVABILITY` at minimum, and consider `PROFILE_RECOMMENDED` since it needs no install and closes a structural gap.
- [x] T020 Add `component_install_globalping()` to `scripts/lib/install-steps.sh`. Registration-only — nothing is downloaded or compiled, so the function verifies the token is set and explains where to get one.
- [x] T021 Add **both** HUD entries to `ui/netclaw-visual/server.js`: the **node list** entry *and* the **annotation map** entry. Adding only one leaves the dashboard incomplete — the R1 mistake.
- [x] T022 Update `SOUL.md` with a section describing **the capability**: that NetClaw can now see the network from outside, and that "no probes matched" is not "the service is down".
- [x] T023 [P] Update `README.md` (MCP Servers table + counts, Skills table), `TOOLS.md` (per-integration notes + connection details), and `.env.example` (`GLOBALPING_TOKEN`, name only).
- [x] T024 Verify `python3 scripts/reconcile-mcp.py` exits **0** across all four surfaces, and that every artifact FR-019 enumerates is actually updated — the gate checks four of the eight, so the other four are eyes-on (FR-019, FR-020, SC-011).
- [x] T024a Confirm read-only: no device access, no writes anywhere (FR-017), by inspecting the tool surface.

---

## Phase 6: Close-out

- [x] T025 Verify SC-004 end to end: `10.0.0.1`, `localhost` and an internal hostname each refused **locally**, with no outbound call made.
- [x] T026 Verify SC-001, SC-005 and SC-006 against live probes: attributed multi-probe latency, a DNS split, and a two-region comparison.
- [x] T027 Verify SC-012: skill and integration counts remain correct after the addition.
- [x] T028 Update `docs/COVERAGE-ROADMAP.md`: mark R8 `DONE` with an outcome section recording the inverted budget model, the vendor's broken `AS13335` example, and the three-way distinction.
- [x] T029 Record the GAIT session summary (Principle IV). Blog post drafted for review per Principle XVII.

---

## Dependencies

```
Phase 1 Registration (T001-T004)
      ↓
Phase 2 Skill safety semantics (T005-T011a)   ★ the substance
      ↓
Phase 3 Scope boundary + composition (T012-T015a)
      ↓
   ┌──┴──────────────┐
   ↓                 ↓
Phase 4 Tests    Phase 5 Integration (T018-T024a)
(T016-T017)          ↓
   └────────┬────────┘
            ↓
   Phase 6 Close-out (T025-T029)
```

**Hard constraints**

- Phase 1 blocks everything — no registration, nothing to call.
- Phase 2 before Phase 3: the outcome semantics must exist before the boundary rules that reference them.
- Phases 4 and 5 are independent of each other.

## Parallel opportunities

| Batch | Tasks |
|---|---|
| Tests | T016, T017 together |
| Integration | T023 alongside T018-T022 |

## Implementation strategy

**MVP = Phases 1-3** (T001-T015a). Delivers the whole point: NetClaw can answer "can the outside world reach
this" and cannot be tricked into reporting a location-filter mistake as an outage.

Then **Phase 4** for regression cover, **Phase 5** to make it installable and known to the agent, **Phase 6**
to close out.

## Summary

| Phase | Story | Tasks | Count |
|---|---|---|---|
| 1 Registration | — | T001-T004 | 4 |
| 2 Skill safety semantics | US1/US4 (P1) | T005-T011a | 9 |
| 3 Boundary + composition | US1/US3 (P1) | T012-T015a | 8 ★ MVP |
| 4 Tests | — | T016-T017 | 2 |
| 5 Integration (XI) | — | T018-T024a | 8 |
| 6 Close-out | — | T025-T029 | 5 |
| **Total** | | | **36** |
