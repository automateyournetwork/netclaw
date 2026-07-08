# Feature Specification: Chrome DevTools Browser Automation & Inspection Skill

**Feature Branch**: `048-chrome-devtools-browser-inspection`
**Created**: 2026-07-07
**Status**: Draft
**Input**: User description: "chrome-devtools-mcp browser automation/inspection skill (MCP + CLI), controller-agnostic. NetClaw integrates the upstream ChromeDevTools/chrome-devtools-mcp community MCP server (registered like other community MCPs, e.g. devnet-content-search / gitlab-mcp pattern — skill docs and config only, no forked server code) plus a CLI wrapper skill, following the existing "stateless proxy to a community MCP" pattern used elsewhere in NetClaw. Primary use case: dogfooding NetClaw's own generated browser-based visualization outputs — open the HTML in a controlled Chrome instance, screenshot it, capture console messages, optionally run a Lighthouse audit. Secondary use cases: augmenting existing controller skills when a vendor REST API lacks a GUI-only report; discovering undocumented vendor APIs via network request inspection; general web-GUI automation for tools without an API integration. Authentication via a persistent Chrome `--userDataDir` profile the user manually signs into once per target site; NetClaw never stores or handles credentials."

## Clarifications

### Session 2026-07-07

- Q: Where/how does the one-time interactive sign-in happen, given the NetClaw host may not have a display attached? → A: Headless/headed mode is a user-configurable flag rather than fixed to one mode. Default is headless for automated/agent-driven invocations; a user can run headed directly (if the host has a display) or connect to the headless daemon's remote-debugging endpoint from their own machine's browser to complete an interactive sign-in (e.g., ACI APIC) once per site.
- Q: Should this skill restrict which URLs/domains it is allowed to navigate to? → A: No dedicated allowlist built into this skill — it is governed by NetClaw's existing general permission-prompt model and DefenseClaw tool-allow/tool-block controls, the same way every other MCP tool call is governed.
- Q: Should this skill record its own audit trail of navigations/actions? → A: No dedicated audit trail for this feature — rely entirely on DefenseClaw/GAIT's existing generic tool-call logging, the same as every other MCP tool in NetClaw.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verify a Generated Visualization Actually Renders (Priority: P1)

A user asks NetClaw to build a network topology visualization (e.g., via the three.js, canvas, drawio, UML, or markmap skills). Today, confirming the output actually rendered correctly — no blank canvas, no JavaScript errors, no broken layout — requires the user to manually open the generated file in a browser. With this feature, NetClaw opens the generated file itself in a controlled browser session immediately after creation, takes a screenshot, and checks for console errors, then reports back whether the visualization rendered cleanly or flags what went wrong.

**Why this priority**: This is the lowest-risk, highest-frequency use case — it requires no external credentials, no third-party site, and directly closes a QA gap that exists across several already-shipped NetClaw visualization skills. It is also the cleanest way to prove the new capability works before applying it to riskier, externally-authenticated scenarios.

**Independent Test**: Can be fully tested by generating any existing visualization output (e.g., a three.js topology HTML file), invoking this skill against that file, and confirming it returns a screenshot plus a pass/fail read on console errors — without touching any external site or credential.

**Acceptance Scenarios**:

1. **Given** a freshly generated visualization HTML file, **When** the user asks NetClaw to verify it, **Then** NetClaw opens the file in a browser session, returns a screenshot of the rendered page, and reports whether any JavaScript console errors occurred.
2. **Given** a visualization HTML file that fails to render (e.g., a broken script reference), **When** the user asks NetClaw to verify it, **Then** NetClaw's report clearly identifies the console error(s) rather than just returning a blank/inconclusive screenshot.
3. **Given** a rendered visualization, **When** the user additionally requests a performance/accessibility check, **Then** NetClaw runs an audit against the loaded page and returns a summary of the findings.

---

### User Story 2 - Fill a Gap in an Existing Controller Skill (Priority: P2)

A user is working with an existing API-driven controller skill (for example, a fabric health-score drilldown, an assurance timeline, or a policy-package wizard) and the vendor's REST API does not expose the specific report or setting they need — only the web dashboard shows it. The user asks NetClaw to retrieve that information from the controller's web UI instead.

**Why this priority**: This is the feature's core value proposition for network operations — it turns "the API can't do that" into "ask the dashboard directly" — but it depends on User Story 1's underlying browser session mechanics already working, and it introduces external, authenticated sites, so it carries more risk than Story 1.

**Independent Test**: Can be tested independently by picking one controller whose web UI the user has already manually signed into (in the persistent profile), asking NetClaw to navigate to a specific dashboard page, and confirming NetClaw returns the requested information (via screenshot, extracted text, or both) without ever being given a username or password.

**Acceptance Scenarios**:

1. **Given** a controller web UI the user has previously signed into in the shared browser profile, **When** the user asks NetClaw to retrieve a GUI-only report from that controller, **Then** NetClaw navigates to the relevant page and returns the requested information without requesting or receiving any credentials.
2. **Given** a controller web UI whose cached session has expired, **When** the user asks NetClaw to retrieve information from it, **Then** NetClaw reports that a sign-in is required rather than returning an empty or misleading result.

---

### User Story 3 - Discover an Undocumented Vendor API (Priority: P3)

A NetClaw contributor wants to build a new API-based skill for a controller whose public API documentation is incomplete. They ask NetClaw to load a specific dashboard page in the controller's web UI and report which network requests the page makes, so they can identify the underlying (often undocumented) API endpoint and payload shape before writing the new skill.

**Why this priority**: High value for NetClaw's own development velocity, but it is a developer-facing workflow rather than an end-user operational one, and it depends on the same session/navigation mechanics as Stories 1 and 2.

**Independent Test**: Can be tested independently by loading any web dashboard in the persistent profile, triggering an action on that page, and confirming NetClaw can list the network requests that action produced along with each request's method, URL, and response.

**Acceptance Scenarios**:

1. **Given** a loaded dashboard page in an authenticated session, **When** the user asks NetClaw to list the network activity for that page, **Then** NetClaw returns the observed requests (method, URL, status) since the page was loaded.
2. **Given** a specific request identified in that list, **When** the user asks for its full detail, **Then** NetClaw returns that request's and its response's content.

---

### User Story 4 - General-Purpose Web GUI Automation (Priority: P4)

A user needs NetClaw to interact with some other browser-based tool that has no NetClaw API integration at all — a classic SDN controller GUI (e.g., an OpenDaylight or ONOS console), a vendor support/TAC portal, or a SaaS admin console with incomplete API coverage — to read a value, submit a form, or capture the current state of a page.

**Why this priority**: Broadest but most open-ended use case; valuable as a fallback for one-off needs, but lowest priority since it's the least predictable to support well and has no single acceptance scenario tied to an existing NetClaw skill.

**Independent Test**: Can be tested independently by pointing NetClaw at a web page unrelated to any existing NetClaw skill (in the authenticated profile if needed) and asking it to perform a basic navigate/click/read interaction and confirming the requested outcome.

**Acceptance Scenarios**:

1. **Given** a browser-based tool with no existing NetClaw integration, **When** the user describes what they want read or done on a given page, **Then** NetClaw performs the requested navigation/interaction and reports the resulting page state or extracted value.

---

### Edge Cases

- What happens when the browser runtime required to launch a session is not installed on the NetClaw host? NetClaw MUST report this distinctly from a generic failure, with guidance to install the missing dependency.
- What happens when the target site's cached session (in the persistent profile) has expired or was never established? NetClaw MUST report that a manual sign-in is needed rather than returning an empty, stale, or misleading result.
- What happens when two requests try to use the persistent browser profile at the same time? NetClaw MUST serialize access or clearly report a conflict rather than corrupting profile state or producing cross-talk between sessions.
- What happens when the target page never finishes loading (e.g., a hung request, an infinite animation, or a very large WebGL scene)? NetClaw MUST apply a bounded wait and report a timeout rather than hanging indefinitely.
- What happens when a target site actively detects and blocks automated browser access? NetClaw MUST report that the interaction was blocked/failed rather than silently returning partial or fabricated results.
- What happens when a captured screenshot, console log, or network response contains sensitive data (e.g., a session token visible in a page, or a secret rendered in a dashboard)? NetClaw MUST handle and store captured artifacts under the same access controls as other sensitive skill outputs, not expose them more broadly by default.
- What happens when the requested local file (e.g., a generated visualization) does not exist at the given path? NetClaw MUST report a clear file-not-found error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a way to open a specified local file or remote URL in a controlled browser session and capture a screenshot of the rendered result.
- **FR-002**: System MUST capture browser console output (including JavaScript errors and warnings) produced while a page is loaded, and make it available to the requester.
- **FR-003**: System MUST support an optional performance/accessibility audit of a loaded page and return a summary of the findings.
- **FR-004**: System MUST reuse a persistent, user-designated browser profile across invocations, so that an authenticated session established by a prior manual sign-in remains usable for subsequent automated interactions with that same site.
- **FR-005**: System MUST NOT require, request, store, or transmit login credentials for any target site; all authentication happens exclusively via the user's manual sign-in within the persistent browser profile.
- **FR-006**: System MUST allow navigating, clicking, filling forms, and reading text/structure on a loaded page to extract a specific value or confirm a specific state, without requiring the skill itself to contain pre-programmed knowledge of any specific site's page layout.
- **FR-007**: System MUST allow listing the network requests made by a loaded page and retrieving the full detail (method, URL, status, request/response content) of an individual request.
- **FR-008**: System MUST distinguish "target site requires sign-in" failures from other errors, so the user knows a manual re-login in the persistent profile is needed.
- **FR-009**: System MUST expose this capability through both an MCP interface (for skill/agent-driven invocation) and a standalone CLI (for direct manual use), matching the pattern used by NetClaw's other dual MCP+CLI capabilities.
- **FR-010**: System MUST support running multiple checks (e.g., screenshot, console read, audit, network inspection) against a single loaded page within one session, without requiring a new browser launch per check.
- **FR-011**: System MUST document how to apply this capability to each of the four supported usage patterns (visualization verification, controller-skill augmentation, API discovery, general GUI automation) without embedding per-vendor page-structure logic into the skill itself.
- **FR-012**: System MUST write captured artifacts (screenshots, console logs, network request records, audit reports) to a location consistent with where NetClaw's other skills persist generated outputs, so they can be reviewed after the session ends.
- **FR-013**: System MUST report a clear, distinct error when the browser runtime required to launch a session is unavailable on the NetClaw host.
- **FR-014**: System MUST prevent concurrent sessions from silently corrupting or cross-contaminating the shared persistent browser profile.
- **FR-015**: System MUST allow the requester to select headless or headed browser mode via an explicit flag/option, defaulting to headless for automated/agent-driven invocations, so the interactive one-time sign-in can be completed in whichever mode fits the host environment (headed directly, or headless with the user connecting to the session's remote-debugging endpoint from their own machine).

### Key Entities

- **Browser Session**: A launched, controlled browser instance tied to a persistent profile; holds the open page(s) and their state for the duration of a task, and is the unit against which navigation, capture, and inspection actions are performed.
- **Persistent Profile**: The on-disk browser profile directory holding cookies/session state for previously, manually authenticated sites. One profile can hold valid sessions for multiple sites at once and outlives any single session.
- **Target Page**: The local file or remote URL being loaded, inspected, or automated — either a NetClaw-generated visualization output or an external controller/vendor web page.
- **Captured Artifact**: A screenshot, console log excerpt, network request/response record, or audit report produced during a session and returned to the requester (human or another NetClaw skill).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a visualization is generated, a user can get a rendered-correctly / rendered-with-errors verdict (screenshot + console check) without manually opening the file, in under 30 seconds.
- **SC-002**: For a controller dashboard the user has previously signed into, NetClaw can retrieve a requested GUI-only report or value within a single request, with zero instances of NetClaw asking for or storing that controller's credentials.
- **SC-003**: A one-time manual sign-in to a given site remains sufficient for repeat use until that site's own session naturally expires — the user is not asked to re-authenticate through NetClaw itself between invocations.
- **SC-004**: A NetClaw contributor can identify the specific API request(s) backing a vendor dashboard feature in a single session, without manually opening browser developer tools themselves.
- **SC-005**: Zero target-site credentials ever appear in NetClaw's stored configuration, logs, or captured artifacts — verifiable by review.
- **SC-006**: When a target site's cached session has expired, 100% of affected requests come back with a distinct "sign-in required" result rather than an ambiguous failure or empty success.

## Assumptions

- The browser runtime and any supporting runtime (e.g., Node.js) needed to run the upstream community `chrome-devtools-mcp` server can be installed on the NetClaw host as a prerequisite, the same way other community MCP integrations (e.g., GitLab, Atlassian) declare their own runtime dependency.
- A single shared persistent browser profile is sufficient for v1. Supporting multiple isolated profiles (e.g., per persona, per environment) is out of scope for v1 and can be revisited later.
- v1 targets a single NetClaw host used by one operator at a time; it reduces (via FR-014) but does not fully solve multi-operator concurrent access to the same persistent profile.
- This feature integrates the upstream `chrome-devtools-mcp` server as-is (skill documentation and configuration only), consistent with NetClaw's existing pattern for community MCP servers — no NetClaw-authored fork of the browser automation server itself.
- Vendor sites that actively detect and block headless/automated browser access are not guaranteed to work in v1; such cases surface as a reported failure (see Edge Cases), not a silent bypass.
- Users are responsible for ensuring their own use of this capability against any given third-party site complies with that site's terms of service.
- No per-vendor DOM/selector knowledge, automated credential injection, or unattended/headless CI-style authentication is in scope for v1.
- This skill introduces no bespoke domain/URL allowlist of its own; access control for which sites it may reach relies on NetClaw's existing permission-prompt model and DefenseClaw's tool-allow/tool-block controls, consistent with how every other MCP tool in NetClaw is governed.
- This feature does not add its own structured audit trail; it relies on DefenseClaw/GAIT's existing generic tool-call logging to capture what this skill did, consistent with every other MCP tool in NetClaw.
