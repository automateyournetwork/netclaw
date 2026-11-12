# Feature Specification: Skill Load and Prompt Limits

**Feature Branch**: `188-skill-load-limits`
**Created**: 2026-11-11
**Status**: Draft
**Input**: GitHub issue #326 "Workspace ships 239 skills; OpenClaw loads 200 per source by default" (related: #325 / spec 174, which reports members' unloadable skills but does not change the limit).

## Clarifications

### Session 2026-11-11

No human was available; each question was resolved with the recommended default.

- Q: Should the installer ever lower an operator's value? → A: No. Raise-only; higher operator values are kept.
- Q: How are prompt limits sized? → A: Count limit at least the load limit; character budget at least the measured need (sum over shipped skills of name + description + fixed per-entry overhead of 120 chars) times 1.25 headroom, rounded up to a multiple of 1000. The check recomputes the measurement, so the policy file cannot silently go stale.
- Q: Which source do members use for limits? → A: The repository policy only (not the Border's live config), so members stay deterministic; operator-raised member values are preserved by raise-only when an existing member config is regenerated and merged.
- Q: Headroom for load/candidate limits? → A: Load limit 400 and candidate limit 400 (about 1.6x the 240 shipped); a warning, not a failure, when the count passes 80% of a limit; failure when it exceeds a limit.
- Q: Where does the check live? → A: A new checker script invoked by `scripts/reconcile-mcp.py` (so CI runs it), with unit tests; it also validates the committed policy file schema.
- Q: Scope of the skill count? → A: Directories under `workspace/skills/` containing a `SKILL.md`; other sources are out of scope.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every shipped skill is loaded on a Border (Priority: P1)

An operator installs or upgrades NetClaw. The runtime's skill loader has a built-in ceiling of 200 skills per source, but the workspace ships 240. Today the skills after roughly the 200th (alphabetically: subnet-calculator, suzieq-*, threejs-network-viz, ue5-network-viz, uml-diagram, vault-*, webex-*, twilio-*, wifi-diagnosis and others) are never loaded and fail silently ("not found"). After this feature, the configuration NetClaw writes for the Border carries load limits above the shipped skill count, so all shipped skills load.

**Why this priority**: Skills that silently do not exist are the core defect; every install is affected.

**Independent Test**: Run the installer's configuration step against an empty and an existing runtime config; the resulting config declares load limits at or above the shipped skill count plus headroom.

**Acceptance Scenarios**:

1. **Given** a fresh OpenClaw runtime config, **When** the installer writes NetClaw configuration, **Then** the skills load limits cover every shipped skill with headroom.
2. **Given** an operator config where a limit is already higher than NetClaw's value, **When** the installer runs, **Then** the operator's higher value is kept.
3. **Given** an operator config where a limit is lower than NetClaw's value, **When** the installer runs, **Then** it is raised, and unrelated keys (including other `skills` keys such as per-skill entries) are untouched.
4. **Given** the Hermes runtime, **When** the installer runs, **Then** no skill limits are written.

---

### User Story 2 - Loaded skills are not silently hidden from the model (Priority: P1)

Raising the load limit alone would shift the problem: the runtime also caps how many skills (150) and how many characters (18,000) of skill descriptions go into the model prompt. An operator Border already had 152 eligible skills. After this feature the prompt limits NetClaw configures are sized to cover every shipped skill, so which skills the model sees never depends on an unnoticed cap. Raising the prompt limits increases prompt size on every turn; that cost is recorded and the values are tunable in one place.

**Why this priority**: Without it, loading all skills would hide some at random from the model, a silent failure of a different kind.

**Independent Test**: The automated check computes the shipped skill count and the characters their descriptions need, and passes only if the configured prompt limits cover both.

**Acceptance Scenarios**:

1. **Given** the shipped limits, **When** the check runs, **Then** configured prompt count and character limits cover all shipped skills.
2. **Given** a maintainer adds skills beyond the configured headroom, **When** the check runs, **Then** it fails and names which limit is exceeded and by how much.

---

### User Story 3 - Members get the same guarantees (Priority: P2)

Member homes are generated fresh with a workspace linked to the Border's and a per-member skill allowlist; their config has no limits, so they hit the runtime defaults too. After this feature, member configs carry the same load limits (and prompt limits), so a member's allowlisted skills load regardless of alphabetical position. Members that only enable their scoped skills stay well under the limits.

**Why this priority**: Members report scoped skills as `not_loaded` (spec 174) when past the ceiling.

**Independent Test**: Generate a member config for a spec member and for a profile member; both contain the limits.

**Acceptance Scenarios**:

1. **Given** any generated member config, **When** inspected, **Then** it carries the load and prompt limits from the single source of truth.
2. **Given** a Border config that has operator-raised limits, **When** a member is generated, **Then** the member uses at least the repository values and is not given more than needed from unrelated Border keys.

---

### User Story 4 - Drift is caught automatically (Priority: P2)

A maintainer adds skills. A check, run by the existing reconcile tooling and in CI, fails whenever the shipped skill count exceeds the configured limits (load, candidate, prompt count, prompt characters), so the problem cannot silently return.

**Why this priority**: The count has already grown by one between the issue's filing (239) and now (240).

**Independent Test**: Run the check against the repo (passes) and against a synthetic workspace exceeding the limits (fails, naming the limit).

**Acceptance Scenarios**:

1. **Given** the repository as shipped, **When** `scripts/reconcile-mcp.py` runs, **Then** the new check passes.
2. **Given** a workspace with more skills than the load limit, **When** the check runs, **Then** it exits non-zero with an actionable message.

### Edge Cases

- Operator config has no `skills` section, has `skills` without `limits`, or has non-numeric/invalid limit values: the installer replaces invalid values with NetClaw's and preserves everything else.
- Operator deliberately set a lower limit: it is raised (NetClaw requires all shipped skills to load); documented.
- Operator set a higher limit: preserved, never lowered.
- Skills with missing/empty descriptions: the character estimate uses a safe default per skill.
- Skills in other sources (user-level directories) have their own per-source count; only the workspace source is checked.
- Existing installs upgrading: the next installer run applies the limits idempotently (second run changes nothing).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST hold a single source of truth for the skill limits NetClaw configures (per-source load, per-root candidates, prompt skill count, prompt character budget).
- **FR-002**: Load and candidate limits MUST exceed the shipped skill count with documented headroom.
- **FR-003**: Prompt limits MUST be sized so that every shipped skill can be presented to the model; the trade-off in prompt size MUST be documented.
- **FR-004**: The installer MUST apply the limits to the OpenClaw Border config, raise-only: an existing higher value is preserved, a lower or invalid value is raised, and no other key is modified.
- **FR-005**: Applying the limits MUST be idempotent and MUST NOT write limits for the Hermes runtime.
- **FR-006**: Generated member configs MUST carry the same limits.
- **FR-007**: An automated check MUST fail when the shipped workspace skill count exceeds the configured load, candidate or prompt-count limits, or when estimated description size exceeds the prompt character budget, and MUST report the exceeded limit and the amount.
- **FR-008**: The check MUST run as part of the existing reconcile command that CI already runs, and have automated tests.
- **FR-009**: Documentation MUST explain the limits, where they are set, how to change them and the `not_loaded` relationship to spec 174.
- **FR-010**: The feature MUST NOT hide, rename, remove or disable any skill.

### Key Entities

- **Skill limits policy**: the four configured numbers plus headroom rules; one file in the repo.
- **Shipped skill set**: workspace skill directories containing a skill definition.
- **Runtime config**: the Border's or member's OpenClaw configuration whose `skills.limits` is raised.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of shipped skills (240 today) are within the configured load limits on a fresh install, versus 200 today.
- **SC-002**: 0 shipped skills are excluded from the model prompt by a count or character cap in the configured limits.
- **SC-003**: Adding enough skills to exceed any limit makes the reconcile check fail in 100% of cases, with the limit named.
- **SC-004**: Re-running the installer on an already configured runtime produces zero changes; an operator's higher value survives 100% of runs.
- **SC-005**: Members' generated configs contain the limits in 100% of generated profiles.

## Assumptions

- The OpenClaw option names are `skills.limits.maxSkillsLoadedPerSource`, `maxCandidatesPerRoot`, `maxSkillsInPrompt`, `maxSkillsPromptChars`, as documented in the issue; they cannot be verified against a live OpenClaw on this host beyond what the issue states.
- Headroom default: roughly 1.5x the shipped count, so routine additions do not trip the check.
- Option 1 plus option 3 of the issue are chosen; option 2 (members get only scoped skills) already exists via the per-agent allowlist and is left as is, with the limits added because the symlinked workspace is still scanned.
- Larger prompt budgets cost more tokens per turn; this is accepted over silently hiding skills, and operators may tune values (raise-only means lowering requires editing the repository source).
- Hermes is unaffected.
