# Tasks: MCP Config Reconciliation

**Feature**: 075-mcp-config-reconciliation | **Date**: 2026-07-30
**Input**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/reconcile-cli.md](./contracts/reconcile-cli.md) · [quickstart.md](./quickstart.md)
**Tech**: Python 3.10+, standard library only. Bash for CI wiring and the test harness.

---

## Three findings that shape this task list

**1. Enforcement must come last.** Both verifiers report real failures today and both correctly exit
`1`. Wiring CI before the drift is fixed lands a red build on `main` that blocks every subsequent
commit. Story phases are therefore ordered **US1 → US4 → US3 → US2**, not by priority alone, even
though US1 and US2 are both P1. US2 (enforcement) is gated on all remediation being complete.

**2. CORRECTED — the exit codes were never broken.** An earlier version of these tasks claimed both
verifiers exit `0` and made "add non-zero exits" the core work. That was a measurement error: exit
codes had been read through a `| tail` pipe, which reports the pipe's status. Verified without a
pipe, both scripts exit `1` correctly (`verify-catalog-coverage.py:196,200`).

The real enforcement gap is that **nothing invokes them**. `.github/workflows/` holds only
`skill-review.yml`; a repository-wide search finds only prose references. So Stage 5 shrinks from
"add exit codes" to "add a regression test that the correct exit codes stay correct", and Stage 6's
CI wiring becomes the actual fix. `--warn-only` drops from compatibility requirement to optional
convenience, since the audit found no caller to protect.

**3. One deliberate contract supersede.** Spec 047's contract
(`specs/047-docs-inventory-reconciliation/contracts/verify-inventory-counts-cli.md`) says an
unlocatable claim is "an informational note, not a hard error, since prose phrasing can legitimately
change." FR-012 reverses this. That is intentional — silent check degradation is precisely how the 9
wrong counts survived — and must be recorded as an amendment, not left as a silent divergence.

---

## Phase 1: Setup

- [X] T001 Read all six overlapping scripts end to end before editing any of them: `scripts/verify-inventory-counts.py`, `scripts/verify-catalog-coverage.py`, `scripts/normalize-mcp-cwd.py`, `scripts/register-all-mcps.py`, `scripts/scan-all-mcp-source.py`, `scripts/openclaw-to-hermes-mcp.py`. Record in `specs/075-mcp-config-reconciliation/research.md` any behaviour that contradicts research R4's reuse decisions.
- [X] T002 Capture the pre-change baseline: run both verifiers, save full output to `specs/075-mcp-config-reconciliation/baseline-2026-07-30.txt`. This is the evidence that each later stage moved a specific `FAIL` to clean.
- [X] T003 [P] Create the test harness skeleton at `tests/reconcile/run-tests.sh` plus `tests/reconcile/fixtures/.gitkeep`. Harness copies real repository files into a temp directory, mutates one, asserts exit code and that the message names the offending item. Bash + Python stdlib only, no pytest.

---

## Phase 2: Foundational

**Blocking prerequisites. No user story work starts until these are done.**

- [X] T004 Audit every caller of both verifiers and record the result in `specs/075-mcp-config-reconciliation/research.md` as R10. Initial audit found only prose references (`README.md`, `CLAUDE.md`, `docs/COVERAGE-ROADMAP.md`, `mcp-servers/README.md`, and prior spec directories) and **no** invoking script or workflow — confirm this, since it determines whether `--warn-only` is insurance or a hard requirement.
- [X] T005 Record the deliberate supersede of spec 047's exit-code contract in `specs/047-docs-inventory-reconciliation/contracts/verify-inventory-counts-cli.md`: unlocatable claims become failures per FR-012, with a pointer to spec 075 and the rationale. Also note the exit-`2` semantic widening (bad arguments, per contracts/reconcile-cli.md) so the two contracts do not diverge on a second axis unremarked. Do not silently diverge from a ratified contract.
- [ ] T006 [P] Add a `dropped` integration record store — a plain data file plus loader, sited alongside `EXTERNAL_INTEGRATIONS` in `scripts/verify-inventory-counts.py` so the three states live in one place. Each record carries name and reason, per data-model.md Entity: Integration (FR-016).
- [X] T006a **[moved from Phase 9 per analyze finding I1]** Rewrite the R0 body of `docs/COVERAGE-ROADMAP.md` (lines ~139–250), which still carries the superseded Bucket A/B/C framing and instructs work the ratified spec contradicts — "Fix Bucket A (20 unregistered)" (they are deliberate externals) and "Fix Bucket C (82 undeployed)" (live config is explicitly OUT OF SCOPE per Resolved Clarification 1). Must land early: R1–R24 will read this document during this feature's implementation.
- [X] T006b **[moved from Phase 9 per analyze finding I2]** Correct `docs/COVERAGE-ROADMAP.md` line ~400 in the **R7** section, which states "see R0 Bucket A — `ACI_MCP` is vendored but unregistered, so R0 may partially resolve this." ACI is a deliberate `EXTERNAL_INTEGRATIONS` entry and R0 will not register it.

---

## Phase 3: User Story 1 — A fresh install can obtain all 89 integrations (P1)

**Goal**: Every registered integration is genuinely obtainable by a new user — installer coverage
resolves, and no registration carries a machine-specific path.

**Independent test**: `scripts/verify-catalog-coverage.py` reports zero uncovered servers, and the
new portability check reports zero machine-specific paths. Both verifiable with no agent installed.

### Stage 1 — the 8 mapping declarations (research R1)

- [X] T007 [US1] Add three prefix-group rules to `GROUPED_CONFIG_PREFIXES` in `scripts/verify-catalog-coverage.py`: `aap-` → `aap`, `aws-` → `aws`, `gcp-` → `gcp`. Covers 14 of the 19 failures.
- [X] T008 [US1] Add five explicit aliases to the explicit map in `scripts/verify-catalog-coverage.py`: `cisco-fmc-mcp` → `fmc`, `meraki-magic-mcp` → `meraki`, `thousandeyes-mcp` → `te-community`, `thousandeyes-official-mcp` → `te-official`, `memory-mcp` → `memory-mcp`. Comment the `memory-mcp` entry explaining it works around suffix-stripping when the catalog id itself ends in `-mcp`, matching the existing `rag-mcp` precedent.
- [X] T009 [US1] Verify: run `scripts/verify-catalog-coverage.py` and confirm `Catalog coverage check` reports zero uncovered registered servers, down from 19. Confirm no catalog entry or install function was added — FR-002 forbids creating coverage that already exists.
- [X] T010 [US1] Confirm the grouping semantics still hold (FR-019): Check Point's 15 `chkp-*` servers and both `chrome-devtools` variants remain covered by one catalog id each and are not reported as gaps.

### Stage 2 — repair the malformed registrations

- [X] T011 [US1] Determine whether the three Nautobot servers require the virtualenv interpreter specifically, by checking their imports against system Python availability: `mcp-servers/nautobot-mcp-v2/server.py`, `mcp-servers/nautobot-golden-config-mcp/server.py`, `mcp-servers/nautobot-routing-mcp/server.py`. The answer decides whether T012 can use bare `python3`.
- [X] T012 [US1] Rewrite the three entries in `config/openclaw.json` — `nautobot-mcp`, `nautobot-golden-config-mcp`, `nautobot-routing-mcp` — as repo-relative invocations (`command: "python3"`, `args: ["-u", "mcp-servers/<dir>/server.py"]`), removing every `/home/ubuntu/netclaw/` path. Let `normalize-mcp-cwd.py` supply `cwd` at install time (FR-003).
- [X] T013 [US1] Verify `scripts/normalize-mcp-cwd.py --dry-run` now recognises all three repaired entries as repo-relative and would inject a correct `cwd`.
- [X] T014 [US1] Verify the `cml-mcp` embedded-args command actually launches (`command: "/usr/bin/python3 -m cml_mcp"`). If the gateway does not split the string, correct it to `command: "python3"`, `args: ["-m", "cml_mcp"]`. If it does launch, record that in research.md rather than changing it (FR-005, research R3).

### Stage 4a — the portability check

- [X] T015 [P] [US1] Create `scripts/check-mcp-portability.py` implementing the `PathClassification` model from data-model.md. Classify every `command`, every `args` element, and `cwd` as `repo_relative`, `system_absolute`, `machine_specific`, `package_spec`, or `embedded_args`. Fail only on `machine_specific`; warn on `embedded_args`. Stdlib only; resolves paths from its own location.
- [X] T016 [US1] Ensure the check does not flag legitimate system paths (FR-004): `/usr/bin/python3` and any `/usr/`, `/bin/`, `/sbin/`, `/opt/`, `/etc/` prefix must pass. Only `/home/` and `/Users/` prefixes fail.
- [X] T017 [P] [US1] Add fixture tests in `tests/reconcile/` asserting the portability check fails on a `/home/ubuntu/...` command and passes on `/usr/bin/python3`, per contracts/reconcile-cli.md.
- [X] T018 [US1] Verify `scripts/check-mcp-portability.py` reports zero machine-specific paths against the repaired `config/openclaw.json`, satisfying SC-001's "down from 3".

**Checkpoint US1**: all 89 registered integrations map to a catalog component and carry no
machine-specific path. This is the feature's headline outcome.

---

## Phase 4: User Story 4 — Documented counts match reality (P2)

**Sequenced before US2** because US2's enforcement will fail on these if they remain wrong.

**Goal**: `README.md` and `SOUL.md` state the true counts — 199 skills, 149 integrations.

**Independent test**: `scripts/verify-inventory-counts.py` reports zero disagreements and zero
`could not locate` notes.

- [X] T019 [US4] Re-derive the counts immediately before editing, since skills may have changed: run `scripts/verify-inventory-counts.py` and use its computed values rather than the 199/149 recorded on 2026-07-30.
- [X] T020 [US4] Correct four claims in `README.md`: line 7 top prose (skills and MCP), line 242 Visual HUD prose (MCP and skills), line 521 `## MCP Servers (N)` heading, line 661 `## Skills (N)` heading.
- [X] T021 [P] [US4] Correct two claims in `SOUL.md`: line 15 identity line (skills and MCP), line 398 SOUL-SKILLS cross-reference.
- [X] T022 [US4] Resolve the two unlocatable claims — README installer prose for skills and for MCP. Either restore phrasing the existing patterns match, or update the patterns to match current prose. Do not delete the claims to silence the check.
- [X] T023 [US4] Verify `scripts/verify-inventory-counts.py` reports `Documentation check: PASS` with zero notes (SC-005, SC-006).

**Checkpoint US4**: documented counts are true and every expected claim is locatable.

---

## Phase 5: User Story 3 — Every integration has one explained state (P1)

**Goal**: Every vendored directory resolves to exactly one of registered, external, or dropped —
and an unexplained directory fails loudly instead of undercounting silently.

**Independent test**: add a throwaway `mcp-servers/zz-test-mcp/` directory and confirm the check
fails naming it; remove it and confirm the check passes.

- [X] T024 [US3] Implement vendored-state completeness in `scripts/verify-catalog-coverage.py` (or a helper it imports): enumerate `mcp-servers/*` directories, resolve each to registered (via a config entry or mapping rule), external (via `EXTERNAL_INTEGRATIONS`), or dropped (via T006's store). Reuse `register-all-mcps.py`'s discovery logic per research R4.
- [X] T025 [US3] Fail with a message naming any directory in no state (FR-017), and any resolving to more than one (FR-014). This is research R8's inversion — the change that stops the hand-maintained list rotting silently.
- [X] T026 [US3] Resolve every currently-unexplained vendored directory by assigning it a state. Expect most to already be covered by `EXTERNAL_INTEGRATIONS`; assign `dropped` with a reason only where genuinely warranted.
- [X] T027 [P] [US3] Require a non-empty reason on every external and dropped record (FR-015, FR-016); fail if one is missing.
- [X] T028 [P] [US3] Add fixture tests in `tests/reconcile/` for an unexplained directory (must fail, naming it) and a reasonless dropped record (must fail).

### Stage 4b — the nine bypassed vendored directories

- [~] T029 **DEFERRED** [US3] Assess each of the nine individually for staleness and divergence from upstream — `CiscoFMC-MCP-server-community`, `atlassian-mcp`, `chrome-devtools-mcp`, `fwrule-mcp`, `gait_mcp`, `gitlab-mcp`, `infrahub-mcp`, `jenkins-mcp`, `mcp-nautobot`. Record findings per directory in `specs/075-mcp-config-reconciliation/research.md` as R11.
- [~] T030 **DEFERRED** [US3] Apply the decision per directory. **Retain the vendored copy whenever evidence is inconclusive** (FR-022, maintainer's explicit instruction). Treat `gait_mcp` with particular care — it backs the audit trail Constitution Principle IV makes non-negotiable.
- [~] T031 **DEFERRED** [US3] Record each of the nine decisions and its reason so a later roadmap item does not re-litigate them (FR-021).

> **T029–T031 DEFERRED 2026-07-30, with reason (FR-016 requires the reason to persist).**
> A triage pass showed the assessment is not necessary. Of the nine: four are **empty stubs**
> (`atlassian-mcp`, `chrome-devtools-mcp`, `gitlab-mcp`, `jenkins-mcp` — 1 file each) whose
> registrations correctly resolve via `uvx`/`npx`, so there is no dead weight to evaluate. Four hold
> real code for legitimate reasons: `fwrule-mcp` (149 files) is the source behind the `fwrule-mcp`
> package spec, `mcp-nautobot` (61) is the *intentional* community alternative already recorded in
> `EXTERNAL_INTEGRATIONS`, and `infrahub-mcp` (107) plus `CiscoFMC-MCP-server-community` (59) are
> pinned upstream sources. `gait_mcp` (37) backs `scripts/gait-stdio.py`, which is wired and working
> — the GAIT repo exists at `~/.openclaw/n2n/gait`, so Principle IV is intact.
>
> Nothing is broken, nothing is user-facing, and every one of the nine already resolves to a recorded
> state, so the reconciliation gate is green without this work. The only available outcome was
> reclaiming disk space, which does not justify blocking R1 — and deleting vendored code is exactly
> the irreversible action the maintainer's keep-on-tie ruling was guarding against.
>
> **Revisit if**: a vendored copy is found to be both stale and actually in use, or disk pressure
> makes the ~380 files worth reclaiming.

**Checkpoint US3**: every vendored directory has exactly one explained state; forgetting now fails loudly.

---

## Phase 6: User Story 2 — Drift is caught automatically (P1)

> **GATE: do not start until US1, US4 and US3 are all complete and both verifiers report clean.**
> Enabling enforcement earlier lands a red build on `main`.

**Goal**: Any inconsistency fails with a non-zero exit, in CI and locally, from one entry point.

**Independent test**: introduce one defect per surface; confirm non-zero exit each time and that the
message names the surface and item. Revert; confirm exit 0.

### Stage 5 — protect the exit-code behaviour (revised: it already works)

- [X] T032 [US2] Confirm both verifiers report clean before proceeding. If either still reports `FAIL`, stop — a prior phase is incomplete. **Read exit codes without a pipe** (`cmd >/dev/null 2>&1; echo $?`); `cmd | tail` reports the pipe's status and caused the original misdiagnosis.
- [X] T033 [US2] Add a regression test asserting `scripts/verify-inventory-counts.py` exits `1` on a count disagreement and `2` when counts cannot be computed. Do **not** modify its exit logic — verified correct. Preserves the contract spec 047 ratified (FR-008).
- [X] T034 [US2] Promote unlocatable claims from advisory note to failure in `scripts/verify-inventory-counts.py` (FR-012), consistent with the T005 contract amendment. This is the one genuine behaviour change to either verifier.
- [X] T035 [P] [US2] Add a regression test asserting `scripts/verify-catalog-coverage.py` exits `1` on a coverage or state failure and `2` on unreadable input. Do **not** modify its exit logic — verified correct at line 196/200.
- [X] T036 [P] [US2] Optionally add `--warn-only` to both verifiers for local convenience. No longer a compatibility requirement — T004's audit found no caller to protect. Skip if it adds complexity without a consumer.
- [X] T037 [US2] Ensure every failure message names surface, item, observed and expected, per the format in contracts/reconcile-cli.md (FR-013).

### Stage 6 — orchestrator and CI

- [X] T038 [US2] Create `scripts/reconcile-mcp.py` per contracts/reconcile-cli.md: invoke each surface check, aggregate findings, print the summary block, exit non-zero if any surface fails. Support `--warn-only`, `--surface` (repeatable), `--json`, `--quiet`. Compose via `importlib` as `verify-catalog-coverage.py` already does (research R4). Read-only — never writes repository files.
- [X] T039 [US2] Enforce the exit contract: `0` all-pass or flagged-only, `1` any failure, `2` cannot-run. Exit `2` must be distinguishable so CI can tell an inconsistent repository from a broken check.
- [X] T040 [US2] Guarantee no agent, network, or credentials are required (FR-029, SC-013). Never read `~/.openclaw/openclaw.json`. Report env var names only, never values (Principle XIII).
- [X] T041 [US2] Add the CI job invoking `scripts/reconcile-mcp.py` with no arguments and failing on non-zero, in `.github/workflows/`. No existing workflow runs these checks, so this is new wiring. `--warn-only` MUST NOT appear in CI.
- [X] T042 [P] [US2] Complete the fixture harness in `tests/reconcile/run-tests.sh`: one case per surface asserting non-zero exit and that the message names the item, plus a clean-tree case asserting exit 0 (SC-002, SC-010).
- [X] T043 [US2] Verify determinism (FR-011): the same repository state yields identical output and exit code locally and in CI, so the two cannot disagree.

**Checkpoint US2**: drift now fails the build. This is the change that keeps every earlier fix true.

---

## Phase 7: User Story 5 — One documented add-an-integration procedure (P2)

- [X] T044 [P] [US5] Publish `docs/ADDING-AN-MCP.md` from `specs/075-mcp-config-reconciliation/quickstart.md`, covering integration-kind selection, registration, state recording, installer coverage, documentation surfaces, and verification (FR-023).
- [X] T045 [US5] Enumerate every Constitution Principle XI artifact in the procedure (FR-024), and state plainly that the counts are the step most often forgotten — they were wrong in 9 places.
- [ ] T046 [US5] Validate the procedure end to end against one integration, confirming the final step demonstrates installability rather than mere presence in a file (SC-010).
- [X] T047 [P] [US5] Link `docs/ADDING-AN-MCP.md` from `README.md`, `CLAUDE.md` and `docs/COVERAGE-ROADMAP.md` so R1–R24 find it without being told.

---

## Phase 8: User Story 6 — Skill traceability (P3)

- [X] T048 [P] [US6] Create `scripts/trace-skill.py` reporting the chain from skill name to backing integration to recorded state and catalog component (FR-025). Exit `0` chain resolved, `1` chain broken, `2` no such skill.
- [X] T049 [US6] Report "intentionally external and not installed" as an expected state, not a fault (FR-026). Getting this wrong would make 60 of 149 integrations look broken.
- [X] T050 [US6] Derive each skill's backing integration from `workspace/skills/*/SKILL.md`, and report skills with no discoverable backing integration rather than failing (SC-011).
- [X] T051 [US6] Keep `trace-skill.py` out of the CI gate — it is diagnostic, and skills legitimately reference integrations a given install has not enabled.

---

## Phase 9: Polish & Cross-Cutting

- [X] T052 Verify no regression (FR-028, SC-012): all 149 integrations and 199 skills available before remain available after. Compare against T002's baseline.
- [X] T053 [P] Record the host/sandbox `cwd` conflict as a documented limitation with its consequence, per FR-007's escape clause and research R7. State explicitly that it does not affect a fresh install, only sandbox migration of an installed config.
- [X] T054 [P] Update `docs/COVERAGE-ROADMAP.md`: mark R0 `DONE`, correct the R0 premise note to reflect that the 19 were checker declaration gaps rather than installer gaps, and record the 3 Nautobot entries as the real user-facing defect found.
- [X] T055 [P] Correct the roadmap's R0 body text, which still describes Buckets A/B/C from the original mistaken framing.
- [X] T056 Confirm FR-027 held: no new integration capability was added. `git diff --stat` must show no new `mcp-servers/` server, no new catalog entry, and no new install function.
- [ ] T057 Run the Constitution Principle XI Artifact Coherence Checklist and record the result, noting which items are N/A because no capability was added.
- [ ] T058 [P] Draft the WordPress milestone post per Principle XVII: R0 complete, what reconciliation found, and the two premise corrections. Present to John before publishing.
- [ ] T059 Record the GAIT session summary commit (Principle IV).

---

## Dependencies

```
Phase 1 Setup (T001–T003)
      ↓
Phase 2 Foundational (T004–T006)          ← blocks all stories
      ↓
   ┌──────────────┬──────────────┬──────────────┐
   ↓              ↓              ↓              ↓
US1 (T007–T018)  US4 (T019–T023)  US5 (T044–T047)  US6 (T048–T051)
   ↓              ↓                  (independent)   (independent)
US3 (T024–T031)  ─┘
   ↓
   └──────────────┴─→ GATE: all remediation clean
                            ↓
                      US2 (T032–T043)   ← enforcement, MUST be last
                            ↓
                      Phase 9 Polish (T052–T059)
```

**The one hard ordering constraint**: US2 depends on US1, US3 and US4 all being complete. Everything
else is flexible.

**US5 and US6 are fully independent** of the remediation and enforcement work and can proceed in
parallel with any phase after Foundational.

## Parallel opportunities

| Batch | Tasks | Note |
|---|---|---|
| Setup | T003 alongside T001–T002 | Harness skeleton is independent |
| Foundational | T006 alongside T004–T005 | Different files |
| US1 Stage 1 | T007, T008 | Same file, so sequential in practice; T015, T017 are genuinely parallel |
| US4 | T020, T021 | Different files (README vs SOUL) |
| US3 | T027, T028 | Independent of T024–T026 |
| US2 Stage 5 | T035, T036 | Separate from T033–T034 |
| Cross-story | All of US5 and US6 | Independent of everything after Foundational |
| Polish | T053, T054, T055, T058 | Different files |

## Implementation strategy

**MVP = Phase 1 + Phase 2 + US1.** That alone delivers the stated goal: all 89 integrations
obtainable by a fresh installer, with the 3 genuinely broken registrations repaired. Shippable on its
own.

**Then US4 + US3** to reach a clean tree on every surface.

**Then US2** to make it stay clean. Deferring US2 leaves the feature's durable value unrealised —
without enforcement, the next 22 roadmap items re-introduce drift — but it is correctly last, because
enforcement on a dirty tree blocks all work.

**US5 and US6 any time** after Foundational.

## Task summary

| Phase | Story | Tasks | Count |
|---|---|---|---|
| 1 Setup | — | T001–T003 | 3 |
| 2 Foundational | — | T004–T006 | 3 |
| 3 | US1 (P1) | T007–T018 | 12 |
| 4 | US4 (P2) | T019–T023 | 5 |
| 5 | US3 (P1) | T024–T031 | 8 |
| 6 | US2 (P1) | T032–T043 | 12 |
| 7 | US5 (P2) | T044–T047 | 4 |
| 8 | US6 (P3) | T048–T051 | 4 |
| 9 Polish | — | T052–T059 | 8 |
| **Total** | | | **59** |
