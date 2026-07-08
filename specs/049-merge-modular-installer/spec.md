# Feature Specification: Merge Modular TUI Installer with Full Component-Coverage Parity

**Feature Branch**: `049-merge-modular-installer`
**Created**: 2026-07-08
**Status**: Draft
**Input**: User description: "Merge the community-contributed modular TUI installer (PR #96, branch feat/installer-tui-refactor, from fork calcuttin) into main, with full component-coverage parity, plus retrofit the chrome-devtools-mcp integration (spec 048) into the new architecture, plus amend the project constitution to reflect the new installer structure. PR #96 replaces the ~3,700-line monolithic scripts/install.sh (45 hardcoded, all-or-nothing steps) with a modular, selection-driven installer... GitHub reports the PR as CONFLICTING against main... the new catalog.sh is missing installer coverage for MCP servers/skills that exist on main today... A merge that silently drops installer support for any already-shipped, still-registered MCP server or skill is a regression, not just a conflict to paper over."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - No Regression: Every Installable Capability Survives the Merge (Priority: P1)

An operator installing NetClaw fresh, or re-running the installer on an existing install, must be able to install (or continue to have installed) every MCP server and skill that the project currently ships — regardless of whether that capability existed when the community contributor started their installer rewrite. Today, the contributed installer's component catalog was built against an older snapshot of the project and is missing entries for capabilities that have shipped since (confirmed gaps include GNS3, the standalone memory MCP, Ollama local LLM routing, the UDP telemetry receivers, DevNet content search, and everything from the three most recent feature branches). Merging as-is would silently make those capabilities uninstallable through the new installer.

**Why this priority**: This is the difference between "adopt a great contribution" and "ship a regression that quietly deletes existing functionality." It must be resolved before anything else in this effort has value — a great TUI that can't install everything the project already does is not yet mergeable.

**Independent Test**: Run an automated coverage check that compares the merged installer's component catalog against the live registered MCP servers and workspace skills; the check reports zero unexplained gaps.

**Acceptance Scenarios**:

1. **Given** the full list of MCP servers currently registered in NetClaw's reference configuration, **When** the coverage check runs against the merged installer's catalog, **Then** every one of those servers is represented by a catalog entry (either one-to-one, or as part of a deliberately documented group, such as the existing consolidation of the 15 Check Point servers into one entry).
2. **Given** the full list of skills in the workspace that require an installable setup step (a dependency to fetch, a credential prompt, an MCP registration), **When** the coverage check runs, **Then** every one of those skills is represented by a catalog entry and install function.
3. **Given** a host that was previously fully set up using the old monolithic installer, **When** an operator re-runs the merged installer, **Then** the components that host already has installed are recognized and preselected, not dropped or presented as if never installed.
4. **Given** the coverage check finds a capability intentionally excluded from the catalog (for example, a repo-maintenance script with nothing to "install"), **When** the check runs, **Then** it distinguishes that documented, intentional exclusion from a real gap, rather than reporting it as a failure forever.

---

### User Story 2 - Chrome DevTools Is a First-Class Component in the New Installer (Priority: P2)

The Chrome DevTools browser-automation capability (spec 048) — its two MCP registrations (headless and headed "Watch Mode") and its two skills — needs to be selectable the same way every other component is in the new installer: shown in the catalog, included in whichever profile(s) make sense, and installed via a proper install function, not left behind as an artifact of the old monolithic script the contributed installer deletes.

**Why this priority**: Directly follows from User Story 1 (it's one of the confirmed coverage gaps) but is called out on its own because it has specific behavior — provisioning a browser binary without elevated privileges, and pinning an explicit binary path rather than relying on a default lookup — that must be preserved exactly, not just "have some install function that sort of works."

**Independent Test**: Select the Chrome DevTools component (individually or via a profile that includes it) through the new installer and confirm both MCP registrations end up configured with a working, explicit browser binary reference, with no elevated-privilege step required and no credential ever requested.

**Acceptance Scenarios**:

1. **Given** an operator selects the Chrome DevTools component through the new installer (TUI or scripted flag), **When** installation runs, **Then** a usable Chrome/Chromium binary is located or provisioned without requiring sudo, and both the headless and Watch Mode registrations are configured with an explicit reference to that binary.
2. **Given** the component is already installed and the operator re-runs the installer, **When** they leave the component selected, **Then** re-installation is idempotent (no duplicate registrations, no broken state).
3. **Given** a maintainer wants to know whether the previously-standalone browser-provisioning helper still exists as its own script or was absorbed into the installer, **When** they read the relevant project documentation, **Then** the answer is stated explicitly, and it matches the pattern used by comparable existing components (so a future contributor doesn't have to guess which style to follow).

---

### User Story 3 - The Constitution Reflects How Installer Support Is Actually Added Now (Priority: P3)

A future contributor adding a new MCP server or skill needs to know, from the project's own governing document, that "update the installer" now means adding a catalog entry and an install function in two specific files — not adding a numbered step to a single large script that no longer exists in that form.

**Why this priority**: Lower urgency than the first two (the merge can technically happen without this), but leaving the constitution describing a script structure that no longer exists would make every future feature's artifact-coherence checklist wrong on day one after this merge.

**Independent Test**: Read the constitution's artifact-coherence requirements after this change and confirm they describe the current, real installer structure — a person unfamiliar with the installer's history can follow them correctly on the first try.

**Acceptance Scenarios**:

1. **Given** the constitution's artifact-coherence checklist, **When** it is read after this change, **Then** it names the catalog and install-function files (not a single monolithic install script) as the required touchpoint for new capabilities.
2. **Given** the constitution defines its own amendment process (documented rationale, impact review, version bump), **When** this change is made, **Then** that process is followed and recorded the same way prior amendments were.

---

### Edge Cases

- What happens when an old install step doesn't map cleanly to one new catalog entry (e.g., it installed two related things at once)? The coverage check and catalog MUST account for legitimate one-to-many or many-to-one groupings, not force an artificial one-to-one mapping.
- What happens when a component's install behavior depends on something the new installer's own safety rules restrict (for example, refusing to run under sudo) — does that ever conflict with a component's own no-sudo design? These MUST be complementary, not contradictory (a component that already avoids sudo should not be blocked by a general anti-sudo safeguard).
- What happens if the coverage check itself becomes stale the same way the original catalog did? It MUST be a repeatable, re-runnable check (not a one-time manual pass) so this specific failure mode cannot recur silently.
- What happens to a host's existing component manifest (the record of what's installed) if it references something that no longer exists in the merged catalog under the same name? The re-run experience MUST surface this clearly rather than silently dropping or silently mismapping it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a repeatable way to verify that every MCP server currently registered in NetClaw's reference configuration has a corresponding entry in the merged installer's component catalog.
- **FR-002**: System MUST provide a repeatable way to verify that every skill in the workspace that requires an installable setup step has a corresponding catalog entry and install function, or is explicitly documented as intentionally excluded (with a stated reason).
- **FR-003**: The merged installer MUST NOT remove the ability to install any MCP server or skill that was installable through the pre-merge installer.
- **FR-004**: The merged installer MUST include the Chrome DevTools integration — both MCP registrations and both associated skills — as catalog entries with working install functions.
- **FR-005**: The Chrome DevTools install function(s) MUST preserve existing behavior: locate or provision a Chrome/Chromium binary without requiring elevated privileges, and register both MCP servers with an explicit binary-path reference rather than relying on a default channel-based lookup.
- **FR-006**: Project documentation MUST state explicitly whether the standalone Chrome DevTools browser-provisioning helper remains an independently invokable script or is absorbed into the installer's own component logic, and that choice MUST be consistent with how comparable existing components handle non-trivial setup logic in the new architecture.
- **FR-007**: The project constitution MUST be amended, following its own documented amendment process, so its artifact-coherence requirements describe the current catalog-and-install-function pattern rather than a single monolithic install script.
- **FR-008**: The coverage-verification method (FR-001, FR-002) MUST be runnable repeatedly as part of normal development, not only as a one-time manual audit performed for this merge.
- **FR-009**: Re-running the merged installer on a host previously set up with the old monolithic installer MUST recognize and preselect components that host already has, rather than presenting a blank or incorrect starting state.
- **FR-010**: A component MAY be represented in the catalog as a deliberate group (matching existing precedent, such as the consolidation of the Check Point server suite into a single entry) rather than strictly one-to-one with every underlying MCP server, provided the coverage check accounts for that grouping explicitly.
- **FR-011**: The resulting change MUST be mergeable into the current state of the main branch with no unresolved conflicts, while preserving the original contributor's authorship on their work.

### Key Entities

- **Catalog Entry**: An installable unit an operator can select — an identifier, category, display name, and description — mapped to exactly one install function.
- **Install Profile**: A named, curated set of catalog entry identifiers representing a common use case (e.g., a Cisco-focused install, a security-focused install).
- **Install Function**: The executable logic that installs and configures one catalog entry, including any prerequisite resolution specific to that component.
- **Coverage Report**: The computed comparison between what is actually registered/present today (live configuration and workspace skills) and what the catalog covers, distinguishing real gaps from documented, intentional exclusions.
- **Component Manifest**: The per-host record of which catalog entries have already been installed, used to preselect on a re-run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The coverage-verification check reports zero unexplained gaps between what's live/registered today and what the merged installer's catalog covers.
- **SC-002**: An operator who previously installed every component available under the old installer sees 100% of those components represented and preselected when they re-run the new installer.
- **SC-003**: An operator can install the Chrome DevTools capability through the new installer (via profile or explicit selection) and end up with the same working, no-sudo, explicit-binary-path behavior previously validated for that capability.
- **SC-004**: The resulting pull request is reported as cleanly mergeable against main, with zero manual conflict markers remaining.
- **SC-005**: A contributor unfamiliar with the installer's history can read the constitution and correctly identify which files to update to add installer support for a new capability, without reading install script history first.

## Assumptions

- The contributed installer's overall design — the TUI, the profile system, the catalog file format — is accepted as the target architecture for this project going forward; this effort extends its coverage and resolves its conflict with main, and does not redesign those decisions.
- "Installable setup steps" excludes skills that are pure documentation/workflow skills requiring no dependency fetch, credential, or MCP registration of their own (they call existing, already-installed MCP servers) — these do not need a catalog entry.
- The project's existing inventory-verification tooling (built for a prior documentation-reconciliation effort) is a reasonable starting point to extend for the new catalog-coverage check, since it already knows how to enumerate the live configuration and workspace skills.
- The constitution amendment described here is a clarifying/extending change to existing principle text (not a redefinition or removal of a principle), consistent with a minor version bump under the constitution's own semantic-versioning rule.
- The external contributor is not expected to make further changes themselves; this effort completes the coverage-parity and retrofit work directly on top of their contributed branch, preserving their authorship, before merging.
