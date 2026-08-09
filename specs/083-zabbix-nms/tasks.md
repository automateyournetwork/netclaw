# Tasks: SNMP-poller NMS coverage (Zabbix)

**Feature**: spec 083 / roadmap R11 · **Branch**: `083-zabbix-nms` · **Date**: 2026-08-03
**Input**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/mcp-tools.md](./contracts/mcp-tools.md)

**Tests are included and are not optional.** But note what is being tested here is unusual: this feature
adopts a third-party server unmodified, so **NetClaw authors no server code**. The guarantees live in the
skills. Tests therefore split in two:

- **Static** — does NetClaw force read-only? is the deny-list present? does the skill contain a *followable
  procedure* rather than a warning?
- **Live** — does an agent following that procedure get the right answer from a real NMS?

Asserting on skill text alone would prove nothing about the answer a user receives. That is the whole risk
of the adopt-as-is decision, and the test strategy has to face it.

**Total: 111 tasks** (15 added by `/speckit.analyze` remediation). MVP = Phase 1 + 2 + 3 (T001–T045, US1 — the metrics history skill).

---

## Phase 1: Setup — vendor and isolate (BLOCKING)

**Nothing else can start until the server runs from its own venv without disturbing the system interpreter.**

- [X] T001 Record the current resolution of `fastmcp` on the **system** interpreter and the five servers pinning `<3` (`netbox-mcp-server`, `CiscoFMC-MCP-server-community`, `Wikipedia_MCP`, `rag-mcp`, `ISE_MCP`) — this is the "before" measurement FR-037c compares against
- [X] T002 *(FR-030/FR-032 — adoption decision, tested before adopting in Phase 0 against live 7.0.29.)* Create `mcp-servers/zabbix-mcp/` and vendor `mpeirone/zabbix-mcp-server` at pinned revision **`0722f48`** into `mcp-servers/zabbix-mcp/vendor/zabbix-mcp-server/`, **unmodified** (FR-034a)
- [X] T003 Confirm the vendored tree is byte-identical to upstream at that revision, and that its `LICENSE` (GNU GPL v3) is present verbatim
- [X] T004 *(FR-031, FR-034a, SC-024a.)* Create `mcp-servers/zabbix-mcp/NOTICE.md` — third-party attribution, GPL-3.0, the pinned revision, upstream URL, and an explicit statement that **NetClaw does not modify it and any change goes upstream** (FR-034a)
- [X] T005 Add the `.gitignore` negation for `mcp-servers/zabbix-mcp/` following the existing `!mcp-servers/<name>/` pattern — without it the whole tree is invisible to git
- [X] T005a **Re-ignore the venv**: add `mcp-servers/zabbix-mcp/.venv/` after the negation. `.venv/` is globally ignored at line 14, but `!mcp-servers/zabbix-mcp/` re-includes *everything* beneath it — so without this line the entire virtualenv gets committed. `multivendor-cli-mcp` carries exactly this line (`.gitignore:71`) for exactly this reason
- [X] T005b Prove it: run `git status --porcelain` after the venv exists and confirm no `.venv` path appears, and `git check-ignore -v mcp-servers/zabbix-mcp/.venv/pyvenv.cfg` reports the re-ignore rule
- [X] T006 *(FR-035, FR-036, FR-037.)* Create `mcp-servers/zabbix-mcp/requirements.txt` describing what the dedicated venv installs, with a comment stating **why the venv exists**: fastmcp 3.x versus five servers pinning `<3` (FR-037a)
- [X] T007 [P] Create `tests/zabbix/` and `tests/zabbix/run-tests.sh` following `tests/bgp-intel/run-tests.sh` in structure

**Checkpoint**: vendored, licensed, git-visible.

---

## Phase 2: Foundational — the venv, read-only, and the deny-list (BLOCKING)

- [X] T008 Add `component_install_zabbix()` to `scripts/lib/install-steps.sh` creating a **dedicated virtualenv** at `mcp-servers/zabbix-mcp/.venv`
- [X] T009 In T008, create the venv with `netclaw_venv_create` or `uv venv` — **never bare `python3 -m venv`**, which fails on this host because `ensurepip` is unavailable (FR-037b; spec 077 hazard #3, hit live in Phase 0)
- [X] T010 In T008, install the vendored package into that venv, never into the system interpreter. Export `ZABBIX_MCP_CMD_DETECTED` pointing at **the venv's interpreter**
- [X] T011 In T008, `log_warn` on failure and print the reason the venv exists, so a future maintainer does not "simplify" it away
- [X] T012 Register `zabbix-mcp` in `config/openclaw.json` with repo-relative paths pointing at **the venv interpreter**, `command`/`args` separate, `${VAR}` env passthrough only
- [X] T013 In the registration, set **`READ_ONLY=true` explicitly** — never rely on the upstream default. Measured: `utils.py:29` defaults True but `scripts/start_server.py:139` defaults **False** (FR-021a)
- [X] T014 In the registration, set a **destructive-method deny-list** via `ZABBIX_API_BLACKLIST` covering at minimum `.*\.delete`, `.*\.create`, `.*\.update`, `.*\.massdelete`, `.*\.massupdate`, `.*\.import`, `.*acknowledge` (FR-021b) — second layer, because one of the two upstream defaults is already wrong. `.*acknowledge` is already blocked by the read-only heuristic; it is listed deliberately so the deny-list stays correct if read-only is ever misconfigured
- [X] T015 Set `VERIFY_SSL=true` in the registration (FR-029)
- [X] T015a Configure **API-token (bearer) auth**, not username/password: `ZABBIX_TOKEN` from `.env`, never a literal. Measured on 7.0.29 the in-body property still works, but it is removed in 7.2+, so token is required for forward-compatibility (FR-026)
- [X] T015b Confirm no credential value appears in any response, log line or artifact — grep the live run output for the token (FR-028, SC-019)
- [X] T016 [P] Create `tests/zabbix/test_venv_isolation.py`: assert `mcp-servers/zabbix-mcp/.venv` exists and resolves fastmcp **3.x**, while the system interpreter still resolves **2.x** (FR-037c, SC-026)
- [X] T017 In `test_venv_isolation.py`: assert each of the five `<3`-pinned servers still has its constraint satisfied by the system interpreter after installation — compare against T001's recorded baseline
- [X] T018 In `test_venv_isolation.py`: assert the installer contains no bare `python3 -m venv` (SC-027)
- [X] T019 [P] Create `tests/zabbix/test_readonly_forced.py`: assert NetClaw's own registration sets `READ_ONLY=true` explicitly, and that the value is not left to the upstream default (SC-018a)
- [X] T020 In `test_readonly_forced.py`: assert the deny-list is configured and covers every destructive verb from T014 (SC-018b)
- [X] T021 In `test_readonly_forced.py`: prove the deny-list is **non-vacuous** by checking a known-destructive method name against the configured patterns and confirming it matches
- [X] T022 Wire T016 and T019 into `run-tests.sh`
- [X] T023 **Start the lab polling now** and leave it running — trends are hourly and Phase 7 needs real aggregates (research D8)
- [X] T023a **Verify what can actually be polled before relying on it.** FRR containers do not run `snmpd` by default and the FortiGate needs an SNMP community configured. Establish pollability *first*; if neither yields real interface counters, fall back to the Zabbix server's own host (which has 84 float items, confirmed in Phase 0) and **record in `VERIFICATION.md` that interface counters came from the NMS host rather than network gear**. Discovering this at verification time is how US1's live proof gets quietly downgraded
- [X] T024 Verify the server answers live Zabbix from the venv end to end: MCP handshake, `zabbix_api(host.get)` returns real hosts, `zabbix_api(host.delete)` is **refused with a message naming read-only** (FR-021, FR-024, SC-018)

**Checkpoint**: isolated, read-only, answering a real NMS. Lab accumulating history.

---

## Phase 3: User Story 1 — Interface metrics history (Priority: P1) 🎯 MVP

**Goal**: an engineer asks what an interface did over a window, and gets a true answer whether the window is
inside raw retention, beyond it, or spanning the boundary.

**This skill is the single most important artifact in the feature.** Both silent-wrong-answer traps live
here, and after the adopt-as-is decision it is the *only* thing standing between a user and a confidently
wrong "no data".

**Independent Test**: ask for three windows against a real polled float item and confirm each returns real
data with its source stated.

- [X] T025 [P] [US1] Create `workspace/skills/zabbix-metrics-history/SKILL.md` with frontmatter copied exactly from `workspace/skills/bgp-registry-intel/SKILL.md` (quoted single-line `description` ending in a "Use when …" clause, `version`, `license: Apache-2.0`, `tags`, `user-invocable: true`, inline-JSON `metadata.openclaw.requires`)
- [X] T026 [US1] *(FR-015 — this is the interface-utilization capability.)* Write the **value-type procedure** as numbered, followable steps: call `item.get` first, read `value_type`, pass it explicitly to `history.get`. State the measured fact that **the API defaults to 3 while 84 of 121 stock items are 0** (FR-001, FR-006a)
- [X] T027 [US1] Write the **type-splitting rule**: types cannot be mixed; a query across float and unsigned items must be split per type and merged. State the measured evidence — 4 items, 2 returned each way, overlap 0 (FR-002)
- [X] T028 [US1] Write the **retention router** as a decision procedure: read `history` and `trends` from `item.get`; window inside history → raw; beyond → trends; spanning → both (FR-003)
- [X] T029 [US1] Add the **three retention states** discovered in Phase 0: `history=0` (raw never stored), `trends=0` (no aggregates), both zero (nothing retained, trigger-only). Require these be reported as **configuration facts, not absences** (FR-006b)
- [X] T030 [US1] Require any aggregate-derived answer to say so, and to state that min/avg/max are **hourly rather than instantaneous** — a peak from an hourly average is a different claim (FR-004)
- [X] T031 [US1] Require a boundary-spanning answer to state which portion came from which source (FR-005)
- [X] T032 [US1] *(SC-005.)* Write the **five absences** as a lookup table the agent can apply: wrong-type, aged-out, retention-disabled, never-collected, genuinely-idle — each with how to tell and how to word it (FR-006)
- [X] T033 [US1] *(SC-014.)* Require every answer to carry source, the **window actually served** (which may differ from the one requested), and whether raw or aggregated (FR-011)
- [X] T034 [US1] *(SC-015.)* Require the NMS's own current time to be surfaced, so clock skew is diagnosable rather than baffling (FR-012)
- [X] T035 [US1] Require unambiguous timezones on all timestamps (FR-013)
- [X] T036 [US1] Require bounded results to state the bound and how to narrow (FR-014, SC-017)
- [X] T037 [US1] Refuse a future window or reversed start/end with the reason, rather than returning empty
- [X] T038 [US1] State that an item existing on multiple hosts with the same key must never be silently merged into one series
- [X] T039 [P] [US1] Create `tests/zabbix/test_skill_procedure.py`: assert the skill contains a **numbered procedure** mentioning `item.get` **before** `history.get`, not merely a warning that the trap exists (FR-006a)
- [X] T040 [US1] In `test_skill_procedure.py`: assert all five absence causes appear with distinct guidance, and that the three retention states are covered
- [X] T041 [P] [US1] Create `tests/zabbix/test_live_traps.py`: **against the live lab**, take a real float item with data and show the default value type returns 0 rows while the correct one returns data — the trap reproduced in NetClaw's own test suite (SC-002)
- [X] T042 [US1] In `test_live_traps.py`: mix float and unsigned items in one call and assert neither call returns all of them, proving splitting is mandatory (FR-002)
- [X] T043 [US1] In `test_live_traps.py`: assert an item with `history=0` or `trends=0` exists in the lab and is distinguishable from an item that simply has no data in the window (FR-006b, SC-028)
- [X] T043a [US1] In `test_live_traps.py`: prove the **three-way outcome distinction** against the lab — (a) valid token + healthy NMS + empty window → *empty*, (b) deliberately wrong token → *credential failure*, (c) NMS stopped → *unreachable*. All three must be distinguishable, and none may read as "no data" (FR-010, FR-027, SC-016)
- [X] T043b [US1] In `test_live_traps.py`: query a window **beyond raw retention** and assert the answer comes from hourly aggregates and says so (FR-004, SC-003). If the lab has not accumulated trends yet, **fail loudly rather than skipping silently** — a skipped test that looks green is how SC-003 slips
- [X] T043c [US1] In `test_live_traps.py`: query a window **spanning the retention boundary** and assert both sources are used and identified (FR-005, SC-004)
- [X] T043d [US1] In `test_live_traps.py`: assert every answer carries source, the window actually served, and the NMS's own current time (FR-011, FR-012, SC-014, SC-015); and that a bounded result states its bound (FR-014, SC-017)
- [X] T044 [US1] Wire `test_skill_procedure.py` and `test_live_traps.py` into `run-tests.sh`
- [X] T045 [US1] **End-to-end**: ask NetClaw for interface utilization on a real polled device across three windows and confirm the answers are correct and correctly attributed. Record for `VERIFICATION.md` (SC-001)

**Checkpoint**: US1 independently deliverable and live-verified.

---

## Phase 4: User Story 2 — Problem review (Priority: P1)

- [X] T046 [P] [US2] Create `workspace/skills/zabbix-problem-review/SKILL.md` with the standard frontmatter
- [X] T047 [US2] Document `problem.get` for **current** problems (dedicated table) versus `event.get` for history, and when each is right (FR-016, FR-017)
- [X] T048 [US2] Require severity, host, onset, duration and acknowledgement state on every problem (FR-016)
- [X] T049 [US2] Require **"no active problems"** to read as an explicit finding, textually distinct from "the NMS could not be reached" (FR-010, SC-007) — an unreachable monitoring system is the most misleading empty result in this feature
- [X] T050 [US2] Require acknowledgement to be reported as a **workflow fact**, never as evidence the condition cleared (FR-016, SC-008)
- [X] T051 [US2] Require severity and host/group filtering to happen before the answer, not by asking the reader to ignore rows (FR-020)
- [X] T052 [US2] Require resolved problems to carry both onset and resolution times (FR-017)
- [X] T053 [P] [US2] In `test_live_traps.py`: assert `problem.get` against the healthy lab returns an empty list **without error**, and that this is the "no problems" case not the "unreachable" case
- [X] T054 [US2] **Live**: raise a real problem in the lab (down an interface on an FRR router), confirm severity and onset, restore it, confirm resolution is retrievable. Record for `VERIFICATION.md` (SC-006)

---

## Phase 5: User Story 3 + 4 — Availability and inventory (Priority: P2 / P3)

- [X] T055 [P] [US3] Create `workspace/skills/zabbix-availability/SKILL.md` with the standard frontmatter
- [X] T056 [US3] Write **the wording rule** as the skill's headline: report *"the NMS could not reach it, as of <time>"* — **never** "the device is down". One poller, one vantage point, one interval (FR-007, SC-010)
- [X] T057 [US3] Require every availability answer to carry **when that state was last observed** (FR-008)
- [X] T058 [US3] Require transitions with times, so "down for 40 minutes" and "bounced nine times" are distinguishable (FR-018)
- [X] T059 [US3] Require **not monitored** to be a distinct answer from unreachable — the most common cause of surprise (FR-009, SC-011)
- [X] T060 [US4] In the same skill, cover inventory: hosts with groups, interfaces and monitoring state (FR-019)
- [X] T061 [US4] Require collected items to be listable **with units and retention**, so an engineer can see how far back a question can be answered *before* asking it (FR-019, SC-013)
- [X] T062 [US4] Require a **disabled** host to be shown as disabled, not omitted — a host nobody is watching is a finding, not an absence (SC-012)
- [X] T062a **All five boundaries in every skill** (FR-045, FR-046, FR-047, FR-048, FR-049): `prometheus`/`grafana` are pull-based stores for infrastructure you instrumented; `snmptrap-mcp` **receives** traps while this **polls**; `ipfix-mcp` is flows not counters; `auvik`/`thousandeyes`/`datadog` are SaaS with their own agents; `pyats`/`multivendor-cli`/`fortinet` read **current** state while this answers **what it was over time**
- [X] T062b In `test_skill_procedure.py`: assert all three skills name all five boundaries — Principle VII rests on these and nothing else checks them
- [X] T063 [US3] In `test_skill_procedure.py`: assert the availability skill never contains an unqualified "the device is down" phrasing and always attributes to the NMS
- [X] T064 [US3] **Live**: stop an FRR container, confirm a transition with a timestamp; restart it, confirm recovery. Record for `VERIFICATION.md` (SC-009)
- [X] T065 [US4] **Live**: list inventory and confirm it matches what the lab is configured to poll, including a deliberately disabled host shown as disabled (SC-012)

---

## Phase 6: Artifact coherence (Principle XI)

- [X] T066 *(FR-040.)* Add the `zabbix` entry to `scripts/lib/catalog.sh` under `Observability`, **and add it to `PROFILE_OBSERVABILITY`** — profile membership is the easy-to-miss artifact `docs/ADDING-AN-MCP.md` calls out
- [X] T067 Add **both** HUD entries to `ui/netclaw-visual/server.js`: the `INTEGRATION_CATALOG` node (id `zabbix`, category `Observability`, prefixes `['zabbix_']`, transport `stdio`, toolEstimate 3) **and** the `ENV_MAP` annotation with a `notes` string covering read-only, the venv, and the two traps. One entry is not enough
- [X] T068 Update `.env.example` with the box-header block: `ZABBIX_MCP_CMD`, `ZABBIX_URL`, `ZABBIX_TOKEN`, `READ_ONLY`, `VERIFY_SSL`, `ZABBIX_API_BLACKLIST` — names and defaults only, plus a comment that read-only is forced because the upstream launcher default is inverted
- [X] T069 Update `TOOLS.md` with `## Zabbix NMS (\`zabbix-mcp\`, vendored third-party, GPL-3.0)` following the bgp-intel block's shape, including the measured **589-token** manifest, the venv rationale, the two traps, the three retention states, and the five boundaries
- [X] T070 Create `mcp-servers/zabbix-mcp/README.md` — NetClaw-authored, beside the vendored tree: what is adopted, the pinned revision, the licence, why the venv exists, the two limitations (**guidance-not-structure, FR-033**; no per-call audit), the fact that **no write path exists and NMS configuration is unreachable** (FR-022, FR-025), and all five boundaries (FR-046, FR-047, FR-048)
- [X] T071 Update `SOUL.md`: add a `### SNMP-Poller NMS (3)` capability section describing the polled-history capability, the three distinctions, and — plainly — that the guarantees are guidance-level here (FR-033a, SC-023)
- [X] T072 In `SOUL.md`, fix the Globalping line that currently says *"use ThousandEyes when a baseline or trend matters"* — Zabbix is now a credential-free self-hosted answer to that, and leaving the old sentence sends readers to a licence they may not have
- [X] T073 Update both `SOUL.md` count sites and all four `README.md` count sites to **156 MCP integrations / 212 skills** (155+1, 209+3) — confirm against `verify-inventory-counts.py`'s computed truth rather than arithmetic
- [X] T074 Add the `README.md` MCP table row and the skill rows for the three new skills
- [X] T075 Update `docs/COVERAGE-ROADMAP.md`: mark R11 with its spec link and status, and **correct the Netdata claim** — MCP is built into the **free open-source agent** (v2.6.0+, `:19999/mcp`), not only the paid Cloud tier, which makes Netdata a separate near-zero-effort item rather than part of R11
- [X] T076 In `docs/COVERAGE-ROADMAP.md`, record that **LibreNMS's only MCP server is 111 tools** and **Observium's is abandoned and bypasses the API for direct DB + RRD access** — so the next reader does not re-research them
- [X] T077 Verify the vendored directory has a recorded state for `verify-catalog-coverage.py`

---

## Phase 7: Honest verification

- [X] T078 [P] *(FR-044.)* Create `tests/zabbix/test_manifest_size.py`: measure the manifest via a real MCP handshake and assert **≤ 5,000 tokens**; record the figure (SC-021, SC-030)
- [X] T079 In `test_manifest_size.py`: assert exactly **3** tools are exposed, so an upstream bump that explodes the surface is caught
- [X] T080 Wire `test_manifest_size.py` into `run-tests.sh`
- [X] T081 Run `bash tests/zabbix/run-tests.sh` and confirm all suites pass
- [X] T082 Run `python3 scripts/reconcile-mcp.py; echo $?` and confirm **exit 0** across all four surfaces — read the exit code directly, never through a pipe (FR-042)
- [X] T083 Run `python3 scripts/verify-inventory-counts.py; echo $?` and confirm exit 0 with updated counts (FR-043, SC-022)
- [X] T084 Run `python3 scripts/trace-skill.py` for each of the three new skills and confirm all resolve
- [X] T085 *(FR-035, FR-036, FR-039.)* Run `python3 scripts/check-dependency-pins.py; echo $?` and confirm exit 0 — the venv must not introduce a new unbounded submodule-imported pin into the scanned surface
- [X] T086 **Re-verify the five `<3`-pinned servers still work** after installation, not just that their pins are unchanged — import-level check (FR-037c)
- [X] T087 Create `specs/083-zabbix-nms/VERIFICATION.md` with a per-capability table distinguishing **exercised against the live NMS** from **executed without error** (FR-050, SC-025)
- [X] T088 In `VERIFICATION.md`, state the **exact NMS version tested** (7.0.29) and note that the in-body auth property still works there while being removed in 7.2+ (SC-029)
- [X] T089 In `VERIFICATION.md`, record the **trend verification honestly**: if the lab has not accumulated hourly aggregates by verification time, mark trend-based answers **unverified** rather than claiming them (FR-051)
- [X] T090 In `VERIFICATION.md`, record the two **corrections to earlier claims** — the candidate uses `zabbix_utils` not `pyzabbix`, and in-body auth survives on 7.0 — with the note that both came from research repeated without verification
- [X] T091 In `VERIFICATION.md`, state prominently that **this is the first NetClaw integration whose core distinctions are enforced by guidance rather than structure**, and why that trade was accepted (FR-033, FR-033a, SC-024b). Also record that the two-gate machinery is deliberately **not built** because there are no writes, and that any future write requires a NetClaw-owned layer (FR-022, FR-023)
- [X] T092 In `VERIFICATION.md`, state the **no-per-call-GAIT** limitation and its rationale (FR-038, FR-038b, FR-038c, SC-020)
- [X] T092a In `VERIFICATION.md`, record the **iN2N decision** (FR-041) explicitly — whether a member gets this and why. A conditional requirement resolved silently reads as an omitted one
- [X] T092b In `mcp-servers/zabbix-mcp/README.md`, record the **build-vs-adopt decision with the measured candidate table** — 3 / 53 / 111 / 237 tools, their licences, and that `mcpservers.org` labels initMAX "Official" when it is not (FR-030, FR-031, FR-034, SC-024). It belongs in a shipped artifact, not only in `specs/`
- [X] T092c In `VERIFICATION.md`, state anything not exercised as **unverified or cut** (FR-052)
- [X] T093 Report the two upstream defects: the **inverted `READ_ONLY` launcher default** and the invalid **`fastmcp>=v3.2.0`** specifier. Record the issue links (FR-034b, SC-024c)
- [X] T094 Confirm the vendored tree is unmodified and its `LICENSE` intact at commit time (SC-024a)
- [X] T095 Secret-scan the diff; confirm no token, password or host leaked into any artifact (FR-028, SC-019)
- [X] T096 Record the GAIT session log for this feature (FR-038a)

---

## Dependencies

```
Phase 1 (vendor + isolate)
   └─▶ Phase 2 (venv, read-only, deny-list)  ── BLOCKING ──┐
                                                           ├─▶ Phase 3 (US1 metrics, P1) 🎯 MVP
                                                           ├─▶ Phase 4 (US2 problems, P1)
                                                           └─▶ Phase 5 (US3+US4, P2/P3)
                                                                        │
                                                             Phase 6 (artifacts)
                                                                        │
                                                             Phase 7 (verification)
```

**T023 (start the lab polling) must happen in Phase 2**, not Phase 7. Trends are hourly; if the lab starts
accumulating only at verification time, trend-based answers cannot be verified and FR-051 forces marking
them unverified. This is the one scheduling constraint that cannot be fixed late.

**Story independence**: US1, US2 and US3/US4 each depend only on Phase 2.

## Parallel execution

**Phase 2** — T016 and T019 are different new test files, both `[P]`. T008–T015 all edit installer or config
and must serialise.

**Across stories** — the three skills are three separate files:
```
T025 zabbix-metrics-history   (US1) ┐
T046 zabbix-problem-review    (US2) ├── all [P]
T055 zabbix-availability      (US3) ┘
```
Their live-test additions share `test_live_traps.py` and must serialise.

## Independent test criteria

| Story | Independently testable by |
|---|---|
| **US1** (P1) | Three windows against a real polled float item — inside retention, beyond it, spanning. Correct data, source stated, no false "no data" |
| **US2** (P1) | Raise a real problem in the lab; correct severity and onset; resolution retrievable; empty ≠ unreachable |
| **US3** (P2) | Stop an FRR container; transition with timestamp; wording never says "the device is down" |
| **US4** (P3) | Inventory matches what the lab polls, disabled host shown as disabled |

## Implementation strategy

**MVP** = Phases 1–3 (T001–T045). That is the polled-history capability with both traps addressed, which is
the reason R11 exists.

**Then** Phase 4 (the most frequent daily use), Phase 5, then 6 and 7.

**The rule that governs Phase 7**: because the guarantees are guidance-level, a passing static test proves
only that the skill *says* the right thing. Every claim in `VERIFICATION.md` must say whether it was
**exercised against the live NMS** or merely **executed without error** — and the trend row must say
*unverified* if the hours have not elapsed.
