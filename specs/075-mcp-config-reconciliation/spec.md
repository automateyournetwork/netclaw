# Feature Specification: MCP Config Reconciliation

**Feature Branch**: `075-mcp-config-reconciliation`
**Created**: 2026-07-30
**Status**: Draft — clarifications resolved
**Roadmap item**: R0 in `docs/COVERAGE-ROADMAP.md` — blocks all remaining coverage items (R1–R24)
**Input**: User description: "MCP config reconciliation between the repo config, the live gateway config, and the vendored server directories. Roadmap item R0 from docs/COVERAGE-ROADMAP.md; blocks every other coverage item. Three measured inconsistencies: 20 vendored servers under mcp-servers/ have no config entry at all (including pyATS_MCP); 9 vendored servers have a config entry that bypasses the local copy via npx/uvx/remote; config/openclaw.json declares 89 entries while the live gateway config runs 7. Must resolve the authority model (is the repo config source-of-truth or a catalog), produce a drift check that fails loudly, apply an adopt-or-delete decision to each bypassed server, make cwd values portable, document one end-to-end add-an-MCP procedure the remaining roadmap items will follow, and give traceability from skill to config entry to running process. Foundation and config hygiene only; adds no new capability."

---

## The goal, as clarified

**All 89 registered integrations must be genuinely available to someone installing their own
NetClaw risk.** That is the success condition. The state of any particular developer's live gateway
is explicitly *not* in scope — see Resolved Clarification 1.

This reframes the feature away from "sync two config files" and toward **install correctness**: a
fresh installer on their own machine must be able to obtain every integration NetClaw claims to
ship.

---

## Correction to the originating premise

Investigation before writing this spec found the premise **partly wrong**. Recorded here because the
roadmap and the original framing both need amending.

**What was claimed:** 20 vendored servers are "silently unregistered."

**What is true:** most are *deliberately* unregistered and already documented.
`scripts/verify-inventory-counts.py` maintains an `EXTERNAL_INTEGRATIONS` list of 60 integrations
that intentionally have no `config/openclaw.json` entry because they are installed on demand via
pip/npm/Docker, are remote/OAuth, or are bundled into a skill's runtime. That list already names
pyATS, F5 BIG-IP, Catalyst Center, Cisco ACI, Cisco ISE, NetBox, ServiceNow, Packet Buddy,
Cisco SD-WAN, Wikipedia, Markmap, nmap, NVD CVE, Subnet Calculator, IPFIX/NetFlow, SNMP Trap
Receiver, Syslog Receiver and TTS. `pyATS_MCP` being absent from the config is by design.

### Four real defects found instead

**1. Two reconciliation scripts already exist, both report `FAIL` today — and nothing runs them.**

| Check | Reports | Exit code |
|---|---|---|
| `scripts/verify-inventory-counts.py` | `Documentation check: FAIL` — 9 wrong counts | `1` (correct) |
| `scripts/verify-catalog-coverage.py` | `Catalog coverage check: FAIL` — 19 uncovered servers | `1` (correct) |

> **Correction, 2026-07-30.** An earlier draft of this spec claimed both scripts exit `0` and called
> that the feature's central defect. That was a measurement error — the exit codes had been read
> through a `| tail` pipe, which reports the pipe's status rather than the script's. Both scripts
> correctly exit `1`.
>
> The enforcement gap is real but different: **no CI workflow or script invokes either check.**
> `.github/workflows/` contains only `skill-review.yml`, and a repository-wide search finds no
> invocation of either verifier outside prose. They fail correctly into a void because nobody calls
> them. The fix is therefore CI wiring plus a local entry point (FR-010, FR-011), not exit-code
> surgery.

**2. Nineteen registered servers fail the installer-coverage check.** Phase 0 research established
these are **declaration gaps in the checker, not installer gaps** — all 19 are installable today
(catalog ids `aap`, `aws`, `gcp`, `fmc`, `meraki`, `memory-mcp`, `te-community`, `te-official` all
exist, and catalog/install functions are a clean 1:1 at 88 each). The checker simply has no mapping
rule for them, and `memory-mcp` fails to a checker bug: its catalog id literally *is* `memory-mcp`,
but the `-mcp` suffix is stripped before comparison. The fix is 8 declarations, not 19 install
functions. Affected: `aap-ansible-mcp`, `aap-docs-mcp`, `aap-eda-mcp`, `aap-lint-mcp`, `aws-cloudtrail-mcp`,
`aws-cloudwatch-mcp`, `aws-cost-explorer-mcp`, `aws-diagram-mcp`, `aws-iam-mcp`, `aws-network-mcp`,
`cisco-fmc-mcp`, `gcp-compute-mcp`, `gcp-logging-mcp`, `gcp-monitoring-mcp`,
`gcp-resource-manager-mcp`, `memory-mcp`, `meraki-magic-mcp`, `thousandeyes-mcp`,
`thousandeyes-official-mcp`.

**3. Three registered servers are hardcoded to a foreign home directory** and therefore fail for
*every* installer — including on the machine this was measured on:

| Entry | Command | Args reference |
|---|---|---|
| `nautobot-mcp` | `/home/ubuntu/netclaw/.venv/bin/python3` | `/home/ubuntu/netclaw/mcp-servers/nautobot-mcp-v2/server.py` |
| `nautobot-golden-config-mcp` | `/home/ubuntu/netclaw/.venv/bin/python3` | `/home/ubuntu/netclaw/mcp-servers/nautobot-golden-config-mcp/server.py` |
| `nautobot-routing-mcp` | `/home/ubuntu/netclaw/.venv/bin/python3` | `/home/ubuntu/netclaw/mcp-servers/nautobot-routing-mcp/server.py` |

`/home/ubuntu` is not this machine's home directory, so all three Nautobot integrations are broken
on every install. Additionally `cml-mcp` declares `command: "/usr/bin/python3 -m cml_mcp"`, packing
arguments into the command string; whether that launches depends on whether the gateway splits it,
so it is flagged as suspect pending verification rather than asserted broken.

**4. Silent check degradation.** `verify-inventory-counts.py` emits two `could not locate` notes:
two README claims it used to check have drifted in phrasing, so it silently stopped checking them.
The checker quietly weakens as the documents it checks are edited.

Measured ground truth versus documented claims:

| Quantity | Actual | Claimed in docs |
|---|---|---|
| Skills | **199** | 198 (README ×2, SOUL ×1), 191 (README ×1, SOUL ×1) |
| MCP integrations | **149** (89 registered + 60 external) | 115 (README ×2, SOUL ×1), 113 (README ×1) |

**So this feature is not "register 20 forgotten servers."** It is: *make the existing reconciliation
machinery enforcing, fix the install-blocking defects it does not currently catch, and correct the
drift it is already reporting into the void.*

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A fresh install can actually obtain all 89 integrations (Priority: P1)

Someone installs their own NetClaw risk on their own machine. Every integration NetClaw claims to
ship is genuinely obtainable: it has installer coverage, and its registration contains no path that
only resolves on somebody else's computer.

**Why this priority**: This is the stated goal, and it is provably false today for three
integrations: the Nautobot trio is wired to `/home/ubuntu/netclaw/`, a path on nobody's machine. A
further 19 fail the coverage *check* but are in fact installable — the checker lacks mapping rules
(see `research.md` R1). So the user-facing breakage is 3 of 89, and the checker is misreporting 19.
Both need fixing; only the first is user-visible.

**Independent Test**: For every registered integration, confirm it maps to an installer component
and that its command, arguments and working directory contain no machine-specific absolute path.
Verified statically, with no running agent required.

**Acceptance Scenarios**:

1. **Given** the set of 89 registered integrations, **When** installability is checked, **Then**
   every one maps to an installer catalog component or is recorded as dropped with a reason.
2. **Given** a registration containing an absolute path outside the repository, **When** the check
   runs, **Then** it fails and names the entry and the offending path.
3. **Given** the three Nautobot entries, **When** the check runs after remediation, **Then** they
   resolve relative to the installing user's own repository rather than a fixed home directory.
4. **Given** a registration whose command packs arguments into one string, **When** the check runs,
   **Then** it is reported for verification rather than silently accepted.

---

### User Story 2 - Drift is caught automatically instead of reported into the void (Priority: P1)

A maintainer adds or changes an integration. Any inconsistency between the registration surfaces —
vendored directories, the repository config, the installer catalog, the documented counts — causes an
unmissable failure rather than a `FAIL` line printed above a success exit code.

**Why this priority**: Equal to US1. US1 is a one-time cleanup; this is what keeps it true. Two
checks already detect real problems and already fail correctly — but **nothing invokes them**, so
their findings reach nobody. Without wiring, each of the 22 remaining roadmap items adds fresh drift.

**Independent Test**: Deliberately introduce a mismatch per surface and confirm a non-zero exit
naming the surface and item. Revert and confirm it passes.

**Acceptance Scenarios**:

1. **Given** a clean, reconciled repository, **When** the check runs, **Then** it reports success and
   exits zero.
2. **Given** a server registered with no installer catalog coverage, **When** the check runs,
   **Then** it fails with a non-zero exit and names that server.
3. **Given** a documented count that disagrees with the computed count, **When** the check runs,
   **Then** it fails with a non-zero exit and names the file, line, and both numbers.
4. **Given** a documented claim whose phrasing has drifted so it cannot be located, **When** the
   check runs, **Then** it fails rather than emitting an advisory note and passing.
5. **Given** a vendored directory neither registered nor recorded as intentionally external,
   **When** the check runs, **Then** it fails and names that directory.

---

### User Story 3 - Every integration has one explained state (Priority: P1)

A maintainer can ask "what is the state of integration X?" and get one unambiguous answer:
registered, intentionally external, or explicitly dropped with a reason. Nothing sits in an
undocumented in-between state.

**Why this priority**: P1 because US2's check is only meaningful if the categories it checks against
are trustworthy. The current external list is hand-maintained and carries its own staleness warning
("Verified … as of 2026-07-07") — the single point where the scheme degrades.

**Independent Test**: Enumerate states for every vendored directory and registered entry; confirm a
newly added directory with no recorded state is rejected by the US2 check.

**Acceptance Scenarios**:

1. **Given** the vendored directories, **When** states are enumerated, **Then** each is exactly one
   of registered, intentionally external, or dropped-with-reason.
2. **Given** an intentionally-external record, **When** inspected, **Then** it states why — on-demand
   install, remote/OAuth, or skill-bundled.
3. **Given** a dropped record, **When** inspected, **Then** it states the reason, so it is not
   re-litigated by a future roadmap item.
4. **Given** a new vendored directory with no recorded state, **When** the check runs, **Then** it
   fails rather than silently undercounting.

---

### User Story 4 - The documented counts match reality (Priority: P2)

Anyone reading `README.md` or `SOUL.md` sees the true number of skills and integrations, and the
agent's own self-description is accurate.

**Why this priority**: P2 — a consequence of US2/US3 rather than a precondition, but user-visible and
currently wrong in nine places across two files. The agent's identity document misstating its own
capability count is a correctness problem, not cosmetics.

**Independent Test**: Run the count verification; confirm zero disagreements and zero
`could not locate` notes.

**Acceptance Scenarios**:

1. **Given** the reconciled repository, **When** counts are verified, **Then** every claim in
   `README.md` and `SOUL.md` matches the computed totals.
2. **Given** the count check runs, **When** it completes, **Then** it reports no unlocatable claims.

---

### User Story 5 - Adding an integration has one procedure (Priority: P2)

A maintainer implementing any of roadmap items R1–R24 follows one documented procedure, ending in a
check that proves the integration is installable by a fresh user rather than merely present in a
file.

**Why this priority**: P2 because it is documentation rather than enforcement, but 22 subsequent
roadmap items each depend on it. Getting it wrong once costs 22 times.

**Independent Test**: Follow the procedure end to end for one integration; confirm the final step
demonstrates installability.

**Acceptance Scenarios**:

1. **Given** the documented procedure, **When** followed for a new integration, **Then** every
   artifact required by Constitution Principle XI is addressed.
2. **Given** the procedure has been followed, **When** the verification step runs, **Then** it
   confirms the integration is installable and portable, not merely registered.
3. **Given** an integration registered without installer coverage, **When** verification runs,
   **Then** it reports the failure and which artifact is missing.

---

### User Story 6 - A skill can be traced to what backs it (Priority: P3)

Given a skill name, a maintainer can follow the chain from skill, to the integration it depends on,
to that integration's recorded state and installer component — and see clearly where the chain
breaks.

**Why this priority**: P3 — diagnostic convenience rather than a correctness gate, and US1–US3
remove most situations that make it necessary. Still valuable: with 199 skills, "why did this skill
fail" is a frequent question.

**Independent Test**: Pick a skill whose backing integration is intentionally external and confirm
the trace reports that state accurately rather than as a fault.

**Acceptance Scenarios**:

1. **Given** a skill name, **When** its chain is traced, **Then** the backing integration and its
   recorded state are reported.
2. **Given** a skill whose backing integration is intentionally external, **When** traced, **Then**
   this is reported as an expected state, not an error.
3. **Given** a skill with no discoverable backing integration, **When** traced, **Then** it is
   reported so the gap can be assessed.

---

### Edge Cases

- **The check runs where no agent is installed.** This is now the *primary* case, not an exception:
  all requirements here are statically verifiable from the repository, so the check works in CI and
  on a contributor's laptop.
- **A vendored directory exists but the registration resolves elsewhere** — an on-demand package or
  remote endpoint. Nine such cases exist. The vendored copy is either the intended implementation or
  dead weight; the state record must say which, and the check must not treat divergence as
  automatically wrong.
- **An integration is bundled under one selectable installer component.** Check Point registers 15
  separate `chkp-*` servers and Chrome DevTools two variants, both intentionally covered by one
  catalog id. Grouping rules must survive reconciliation rather than being flattened into spurious
  gaps.
- **A documented claim's phrasing changes.** Today this silently disables that claim's check.
- **An integration is deliberately removed.** Its dropped state and reason must persist, so a later
  roadmap item does not re-add it by assuming absence means oversight.
- **Reconciliation runs mid-edit,** with a directory added but documentation not yet updated. The
  failure must name what is missing specifically enough to fix without re-deriving the analysis.
- **A path is absolute but legitimately so** — a system interpreter such as `/usr/bin/python3` is
  fine, whereas `/home/ubuntu/netclaw/.venv/bin/python3` is not. The check must distinguish these
  rather than banning all absolute paths.
- **The host and the sandbox need different working directories.** One static value cannot satisfy
  both; the check must not certify a configuration as portable when it is not.

## Requirements *(mandatory)*

### Functional Requirements

**Installability — the primary goal**

- **FR-001**: Every registered integration MUST map to an installer catalog component, or be
  recorded as dropped with a reason.
- **FR-002**: All 19 registered servers currently failing the installer-coverage check MUST pass it.
  Per research R1 this is achieved by declaring the missing mapping rules for catalog components that
  already exist; new catalog entries or install functions MUST NOT be created for coverage that is
  already present.
- **FR-003**: No registration MUST contain a filesystem path that resolves only on a specific
  machine. The three Nautobot entries hardcoded to `/home/ubuntu/netclaw/` MUST be remediated.
- **FR-004**: The check MUST distinguish a legitimate system-wide absolute path (such as a system
  interpreter) from a machine-specific one (such as a path inside another user's home directory),
  and MUST fail only on the latter.
- **FR-005**: Registrations that pack arguments into the command string MUST be identified and
  verified to launch, or corrected. `cml-mcp` is the known instance.
- **FR-006**: Reconciliation MUST NOT certify a configuration as portable when it contains
  machine-specific paths.
- **FR-007**: The conflict between the host requiring one absolute working directory and the sandbox
  requiring another MUST be reconciled with the mechanism documented, or recorded as a known
  limitation with its consequence stated.

**Enforcement**

- **FR-008**: The reconciliation check MUST exit non-zero whenever it reports any failure. Both
  existing checks already satisfy this and MUST continue to; any new check MUST match. This is a
  property to preserve and test, not a defect to fix.
- **FR-009**: The reconciliation check MUST be runnable as a single entry point covering all
  registration surfaces, so a maintainer need not know which of several scripts to run.
- **FR-010**: The check MUST hard-fail in continuous integration so inconsistent state cannot be
  merged, satisfying Constitution Principle XI's "MUST NOT be merged".
- **FR-011**: The same check MUST be runnable locally as a single command before pushing, using the
  same logic as the CI invocation so results cannot diverge.
- **FR-012**: The check MUST treat an expected documentation claim that cannot be located as a
  failure, not an advisory note.
- **FR-013**: Every failure message MUST identify the surface, the specific item, and the observed
  versus expected state, sufficient to act on without re-deriving the analysis.

**State completeness**

- **FR-014**: Every vendored server directory MUST resolve to exactly one recorded state:
  registered, intentionally external, or dropped.
- **FR-015**: Each intentionally-external record MUST carry its reason — on-demand install,
  remote/OAuth, or skill-bundled.
- **FR-016**: Each dropped record MUST carry its reason and MUST persist, so absence is never
  mistaken for oversight by a later roadmap item.
- **FR-017**: A vendored directory with no recorded state MUST cause failure rather than being
  silently omitted from counts.
- **FR-018**: The set of intentionally-external integrations MUST be verifiable against the
  repository rather than trusted as a hand-maintained list, or MUST fail when it goes stale.
- **FR-019**: Existing intentional grouping of several registered servers under one installer
  component MUST be preserved and MUST NOT be reported as missing coverage.

**Documented counts**

- **FR-020**: All documented skill and MCP counts in `README.md` and `SOUL.md` MUST be corrected to
  the computed values — 199 skills and 149 integrations as of 2026-07-30.

**Bypassed vendored directories**

- **FR-021**: Each of the nine vendored directories whose registration bypasses the local copy MUST
  be assessed individually for staleness and divergence from its upstream, and receive a recorded,
  applied adopt-or-delete decision.
- **FR-022**: Where the evidence for a given directory is inconclusive, the vendored copy MUST be
  retained rather than deleted.

**Procedure and traceability**

- **FR-023**: A single end-to-end procedure for adding an integration MUST be documented, covering
  registration through verification of installability.
- **FR-024**: The procedure MUST enumerate every artifact required by Constitution Principle XI.
- **FR-025**: Given a skill name, the chain from skill to backing integration to recorded state and
  installer component MUST be reportable, including where the chain breaks.
- **FR-026**: Tracing MUST distinguish "backing integration is intentionally external" from
  "backing integration is broken."

**Scope discipline**

- **FR-027**: This feature MUST NOT add any new integration capability. Registering a
  previously-unregistered vendored server is in scope; adding a new server is not.
- **FR-028**: Existing behaviour MUST NOT regress: the 149 integrations and 199 skills available
  before MUST remain available after.
- **FR-029**: Synchronising or modifying any developer's live gateway configuration is OUT OF SCOPE.
  The check MUST NOT require a running agent and MUST NOT fail because a live config differs from
  the repository's.

### Key Entities

- **Integration**: A capability NetClaw can use. Has a name, a state (registered, intentionally
  external, dropped), a reason when not registered, and optionally a vendored implementation
  directory and an installer catalog component.
- **Registration surface**: One of the places an integration's existence is asserted — vendored
  directory, repository config, installer catalog, documented counts. Reconciliation makes them agree.
- **Installability**: Whether a fresh user on their own machine can obtain the integration —
  requires installer coverage plus the absence of machine-specific paths. The primary property.
- **Reconciliation result**: Per-surface pass/fail plus specific discrepancies, and one overall
  outcome determining exit status.
- **Add-an-integration procedure**: The ordered steps and required artifacts for introducing an
  integration, ending in an installability check. Consumed by roadmap items R1–R24.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 89 registered integrations are installable by a fresh user — zero failing the
  installer-coverage check (down from 19) and zero carrying machine-specific paths (down from 3), or
  each exception recorded with a reason.
- **SC-002**: The reconciliation check exits non-zero for every condition it reports as a failure,
  verified by introducing at least one inconsistency per surface and observing a non-zero exit each
  time.
- **SC-003**: The check hard-fails in continuous integration on inconsistent state, confirmed by
  test.
- **SC-004**: The same check is runnable locally as one command and produces the same result as CI
  for the same repository state.
- **SC-005**: Zero documented count claims disagree with computed totals, down from 9.
- **SC-006**: Zero expected documentation claims are unlocatable, down from 2.
- **SC-007**: Every vendored server directory resolves to exactly one recorded state, with zero
  unaccounted directories.
- **SC-008**: Each of the nine bypassed vendored directories has a recorded, applied decision.
- **SC-009**: A maintainer can determine any integration's state in a single command, without
  reading source.
- **SC-010**: Adding an integration by following the documented procedure ends in a step that
  demonstrates installability, validated at least once end to end.
- **SC-011**: Given any of the 199 skill names, the chain to its backing integration and that
  integration's state is reportable.
- **SC-012**: All 149 integrations and 199 skills available before remain available after.
- **SC-013**: The check completes successfully on a machine with no NetClaw agent installed.

## Resolved Clarifications

Three scope questions were put to the maintainer on 2026-07-30 and resolved as follows.

### 1. Authority model — live config is out of scope

**Decision**: *"Let's not worry about the live config as long as all 89 are available for people
when they install their own risk."*

**Consequence**: This is the largest simplification in the spec. The repository config is the source
of truth for **availability**, and the property that matters is that a fresh installer can obtain
all 89. No live-config synchronisation, no live-parity check, and no requirement for a running agent
(FR-029, SC-013). It also redirected the feature's centre of gravity to install correctness, which
is what surfaced the three `/home/ubuntu` entries — a defect the original "sync two files" framing
would have missed entirely.

### 2. Bypassed vendored directories — per-directory, keep on a tie

**Decision**: Assess each of the nine individually; when evidence is inconclusive, retain the
vendored copy.

**Consequence**: FR-021 and FR-022. Keeping code is reversible and deleting it is not, and `gait_mcp`
in particular backs the audit trail Constitution Principle IV makes non-negotiable.

### 3. Enforcement — CI hard-fail plus a local command

**Decision**: Hard-fail in CI, plus a local command maintainers can run before pushing.

**Consequence**: FR-010 and FR-011, with FR-011 requiring both paths to share one implementation so
they cannot diverge.

## Assumptions

- **Both existing checks are the foundation, not competitors.** `verify-inventory-counts.py` and
  `verify-catalog-coverage.py` already encode hard-won domain knowledge, including grouping rules
  and the external-integration rationale. This feature makes them enforcing; it does not replace
  them. Four further scripts overlap the same surface — `register-all-mcps.py`,
  `normalize-mcp-cwd.py`, `scan-all-mcp-source.py`, `openclaw-to-hermes-mcp.py` — and MUST be read
  before any new tooling is written.
- **Fixing the drift these checks already report is in scope.** The 19 catalog gaps and 9 wrong
  counts are on the surface this feature governs; enforcing a check while leaving its known failures
  outstanding would mean shipping a check that fails on day one.
- **Computed values are ground truth for counts** — 199 skills and 149 integrations as measured on
  2026-07-30. Documentation is corrected to match, never the reverse.
- **"Registered" and "available" are different things,** and both are legitimate. An integration
  installed on demand is not broken. This is why the external list exists and why it is kept.
- **No new capability is added,** per FR-027. Any temptation to fix a gap by adding an integration
  belongs to a later roadmap item.
- **Constitution Principle XI is the artifact checklist,** and this feature is partly the mechanism
  enforcing it. Principle XI's own reference to `verify-catalog-coverage.py` is the existing hook.
- **The three Nautobot entries are remediable within this feature.** They are misconfigurations, not
  missing capability — the vendored directories they point at exist in the repository.
- **`cml-mcp`'s embedded-argument command may be working.** It is flagged for verification rather
  than presumed broken, since whether it launches depends on gateway argument handling that has not
  been tested here.
- **The host/sandbox working-directory conflict may not be fully solvable here.** Ring-1 cutover has
  four known blockers, of which this is one; FR-007 permits recording it as a documented limitation
  rather than requiring the cutover be solved by this feature.

## Dependencies

- `scripts/verify-inventory-counts.py`, `scripts/verify-catalog-coverage.py` — extended, not
  replaced.
- `scripts/lib/catalog.sh`, `scripts/lib/install-steps.sh` — the installer catalog surface
  (spec 049), where the 19 missing components land.
- `config/openclaw.json` — the repository registration surface and source of truth for availability.
- `README.md`, `SOUL.md` — the documented-count surface.
- `mcp-servers/` — the vendored implementation surface.
- Constitution Principle XI — the artifact coherence requirement being enforced.
- `docs/COVERAGE-ROADMAP.md` — this is R0; its status board is updated on completion.
- **Explicitly not a dependency**: `~/.openclaw/openclaw.json`. Out of scope per Resolved
  Clarification 1.
