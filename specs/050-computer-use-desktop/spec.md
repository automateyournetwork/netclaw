# Feature Specification: Computer Use — Full-Desktop Automation via OpenClaw's Native Skill

**Feature Branch**: `050-computer-use-desktop`
**Created**: 2026-07-08
**Status**: Draft
**Input**: User description: "Add OpenClaw's built-in "computer-use" skill to NetClaw as a full-desktop automation capability, building directly on the design established in spec 048 (chrome-devtools-mcp browser automation) but extending beyond the browser to the entire desktop. ... A new skill, or pair of skills, giving NetClaw a controlled way to drive the computer-use virtual desktop for tasks that have no browser or API path ... A watch experience analogous to spec 048's browser Watch Mode, using the skill's built-in VNC/noVNC access ... Add this to NetClaw's installer as a proper catalog entry and install function, following the modular installer pattern completed in spec 049 ... Full artifact coherence per the constitution's Principle XI checklist."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install Computer Use Through the Modular Installer (Priority: P1)

An operator selects "Computer Use" in NetClaw's installer (TUI, a profile, or an explicit component flag) the same way they'd select any other component, and ends up with a working, connectable virtual desktop — no manual follow-up steps beyond what the installer itself performs.

**Why this priority**: Nothing else in this feature is testable or demonstrable without a working virtual desktop first. This mirrors how spec 048's MCP registration had to exist before either of its skills could do anything.

**Independent Test**: Select the Computer Use component through the installer and confirm the virtual desktop environment (Xvfb + XFCE) and its VNC/noVNC viewing service come up successfully, with no errors and no credential prompt.

**Acceptance Scenarios**:

1. **Given** a fresh NetClaw install, **When** the operator selects Computer Use (individually or via a profile that includes it), **Then** the required system packages are installed and the virtual desktop environment starts successfully.
2. **Given** Computer Use is already installed, **When** the operator re-runs the installer with it still selected, **Then** the result is idempotent — no duplicate processes, no broken state.
3. **Given** the installation completes, **When** the operator checks status, **Then** NetClaw reports the virtual desktop and its viewing service are ready, with no credential ever requested.

---

### User Story 2 - Operate a Desktop-Only Tool With No Browser or API Path (Priority: P2)

Some legacy network/security tooling — an old Java-based NMS client, a vendor's Windows-only configuration utility, a terminal emulator with no scriptable interface — has no web GUI and no API at all. An operator asks NetClaw to read or confirm something in that application, and NetClaw drives the virtual desktop (opening the application, clicking, typing, reading the screen) to answer.

**Why this priority**: This is the feature's actual reason for existing — the desktop-automation analogue of spec 048's controller-GUI gap-fill, for the cases browser automation structurally cannot reach at all.

**Independent Test**: Ask NetClaw to open a desktop application already available in the virtual desktop and read back a specific piece of information visible in its UI, and confirm the answer is correct and no configuration change was made.

**Acceptance Scenarios**:

1. **Given** a desktop-only application with information an operator needs, **When** the operator asks NetClaw to retrieve it, **Then** NetClaw opens/navigates the application via mouse/keyboard/screenshot actions and returns the requested information.
2. **Given** a request that would require clicking something like "Apply," "Commit," or "Save" on a real configuration change, **When** NetClaw is asked to do so through this capability, **Then** it declines and states that the change must go through the appropriate API-based skill's gated workflow instead.
3. **Given** a legacy application that needs an interactive first-time setup (license acceptance, initial login) before it can be automated, **When** NetClaw encounters that state, **Then** it reports that manual setup is needed rather than guessing or fabricating a result.

---

### User Story 3 - Watch NetClaw Operate the Virtual Desktop Live (Priority: P3)

The same way an operator could watch the Chrome DevTools "Watch Mode" browser session live, an operator can open a live view of the virtual desktop (via VNC or a browser-based noVNC session) and watch — or take over — while NetClaw works, or while completing a task that genuinely needs a human (an interactive login, a one-time license dialog).

**Why this priority**: Directly valuable on its own, and it's how User Story 2's "needs manual setup" edge case actually gets resolved by a human, the same way spec 048's manual browser sign-in patterns did for authenticated sites.

**Independent Test**: Open a live viewer connection to the virtual desktop while NetClaw performs a task and confirm the operator can see the actions happen in real time, and can take control when needed.

**Acceptance Scenarios**:

1. **Given** NetClaw is performing a desktop-automation task, **When** an operator opens a live viewer connection, **Then** they see the virtual desktop's current state and NetClaw's subsequent actions in real time.
2. **Given** a task needs a human to complete a step interactively, **When** the operator is watching, **Then** they can take control of the virtual desktop directly and hand it back.
3. **Given** an operator wants to view the desktop from a machine other than the NetClaw host, **When** they do so, **Then** they must have explicitly established a secure path to it themselves (e.g., an SSH tunnel) — the viewing service is not reachable directly from the network by default.

---

### Edge Cases

- What happens when the virtual desktop environment fails to start (missing dependency, a resource conflict)? NetClaw MUST report this distinctly from a generic failure, with enough detail to diagnose it.
- What happens when two requests try to use the virtual desktop at the same time? Only one virtual display exists — NetClaw MUST serialize access or clearly report a conflict, not silently interleave actions from two unrelated tasks into one desktop session.
- What happens when a desktop action would require submitting a real configuration change (see User Story 2, Scenario 2)? NetClaw MUST decline and redirect to the appropriate API-based, safety-gated skill.
- What happens when the live-viewing service is asked to be reachable from outside the NetClaw host? It MUST require an explicit, operator-established secure path (e.g., an SSH tunnel) rather than exposing an open, unauthenticated port to the network by default.
- What happens when a target desktop application needs interactive setup NetClaw cannot complete on its own? NetClaw MUST report that manual setup (via the live viewer, User Story 3) is needed, rather than guessing or fabricating a result.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a skill capable of driving the virtual desktop (mouse movement/clicks/drags, keyboard input, scrolling, screenshots) to read, confirm, or search state in a desktop application that has no browser or API path.
- **FR-002**: The skill MUST NOT use desktop actions to submit, apply, or commit a configuration change on managed network/security infrastructure — any such change belongs to the relevant API-based skill's baseline→apply→verify and ITSM-gated workflow, never to this capability.
- **FR-003**: System MUST allow an operator to view the virtual desktop live while NetClaw is operating it, and to take manual control when a task genuinely requires human interaction.
- **FR-004**: The live-viewing service MUST NOT be reachable from a non-loopback network interface by default — remote viewing requires an explicit, operator-initiated secure path (e.g., an SSH tunnel), not an open port.
- **FR-005**: System MUST add this capability as a selectable component in NetClaw's modular installer (a catalog entry with a working install function), installable via a profile or explicit selection like every other component.
- **FR-006**: The install function MUST install the required system packages and then install the computer-use skill itself through OpenClaw's own skill-marketplace mechanism, rather than cloning or vendoring a copy of the skill's code.
- **FR-007**: System MUST require no NetClaw-managed credentials or secrets for this capability. If a specific legacy application being automated needs its own login, that login happens manually via the live viewer (User Story 3), never through NetClaw storing or entering credentials.
- **FR-008**: System MUST prevent two concurrent tasks from silently corrupting or cross-contaminating the single shared virtual desktop — access MUST be serialized, or a conflict MUST be clearly reported.
- **FR-009**: The project's catalog-coverage verification tooling MUST recognize this new catalog entry so the zero-unexplained-gap guarantee already established for the installer is not regressed by this feature.
- **FR-010**: Full artifact coherence (documentation, infrastructure reference, HUD, coverage-check recognition) MUST be completed for this capability before it is considered done, per the project's existing artifact-coherence requirements.
- **FR-011**: A separate, macOS-specific, Codex-mode-only computer-use integration path (evaluated during research) MUST NOT be implemented as part of this feature — it is documented as a considered, explicitly out-of-scope alternative for this deployment.

### Key Entities

- **Virtual Desktop Session**: The running virtual display environment, one per NetClaw host at a time (a single shared display), holding whatever application windows are currently open within it.
- **Live Viewer Connection**: An operator's real-time view into the Virtual Desktop Session, either read-only (watching) or interactive (taking control), reachable locally by default and remotely only via an operator-established secure path.
- **Desktop Action**: A single mouse, keyboard, scroll, or screenshot operation performed against the Virtual Desktop Session.
- **Legacy Target Application**: The desktop-only application being read from or interacted with, which has no browser or API path of its own.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can retrieve a specific piece of information from a desktop-only application with no API/browser path, entirely through this capability, without any real configuration change being made in the process.
- **SC-002**: An operator can watch a NetClaw-initiated desktop-automation task live, from start to finish, the same way they could watch a Chrome DevTools Watch Mode browser session.
- **SC-003**: This capability is installable through NetClaw's modular installer in a single selection, with zero additional manual setup steps beyond what the installer itself performs.
- **SC-004**: The live-viewing service is never reachable from outside the NetClaw host by default — verified by review, not just documentation.
- **SC-005**: The installer's catalog-coverage check continues to report zero unexplained gaps after this capability ships.

## Assumptions

- The integration target is OpenClaw's ClawHub-hosted "computer-use" skill (Linux headless-server virtual desktop, verified available on this deployment's host via a live catalog search) — not the separate "codex-computer-use" plugin, which is Codex-mode-specific and macOS-only and does not apply to this Claude-based, Linux-hosted deployment.
- A single shared virtual desktop is sufficient for v1, the same assumption spec 048 made for its single shared browser profile — concurrent use is handled by detection and conflict-reporting, not by provisioning multiple parallel virtual desktops.
- No NetClaw-authored fork of the computer-use skill itself is created; it is consumed as-is via ClawHub, consistent with the "no forked server code" pattern already used for the Chrome DevTools integration and other community-sourced capabilities.
- The live-viewing service defaults to loopback-only access; an operator who wants to view it from a different machine is expected to establish their own secure path (e.g., SSH port forwarding), mirroring the remote-debugging-over-SSH-tunnel pattern already documented for headless hosts in spec 048.
