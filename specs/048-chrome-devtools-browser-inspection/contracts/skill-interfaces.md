# Skill Interface Contracts

**Feature**: 048-chrome-devtools-browser-inspection
**Date**: 2026-07-07

These are the operator/agent-facing contracts for the two skills this feature adds. Both are thin orchestration layers over `chrome-devtools-mcp` tool calls (see `mcp-tools.md`) — neither implements browser automation itself.

## `browser-viz-verify`

**Maps to**: User Story 1 (P1)

**Input**:
- `file_path` (required) — absolute path to a NetClaw-generated visualization HTML file
- `run_audit` (optional, default `false`) — whether to also run a Lighthouse audit

**Behavior**:
1. Verify `file_path` exists; if not, return a file-not-found error (Edge Cases).
2. Open the file in a browser session (headless by default — no external site is ever involved, so headed mode is never required for this skill).
3. Wait for the page to settle (bounded timeout).
4. Capture a screenshot.
5. Read console messages; classify as clean or errored.
6. If `run_audit` is true, run `lighthouse_audit` and summarize findings.
7. Close the page.

**Output**:
- `verdict`: `"rendered_clean"` | `"rendered_with_errors"` | `"timed_out"` | `"file_not_found"`
- `screenshot_path`: path to the captured screenshot artifact
- `console_errors`: list of console error/warning messages (empty if clean)
- `audit_summary`: present only if `run_audit` was true

**Never**: requests or touches the persistent authenticated profile; never navigates to a remote URL.

---

## `browser-gui-inspect`

**Maps to**: User Stories 2-4 (P2-P4)

**Input**:
- `target` (required) — a URL (the vendor dashboard / GUI page in question)
- `intent` (required) — a natural-language description of what to read, extract, or interact with (e.g., "get the bridge domain list from this ACI tenant page", "list the network requests this page makes when I click Refresh")
- `actions` (optional) — a sequence of navigate/click/fill/read steps if the intent requires multi-step interaction
- `capture` (optional, default `["screenshot", "console"]`) — which artifact kinds to capture; may include `"network_requests"` for API-discovery use (US3)
- `mode` (optional, default from `CHROME_DEVTOOLS_HEADLESS`) — override headless/headed for this invocation

**Behavior**:
1. Navigate to `target` using the persistent profile.
2. If the page indicates a sign-in wall (Edge Cases: `sign_in_required`), stop and report that distinctly (FR-008) rather than proceeding.
3. Perform any requested `actions`, restricted to read/confirm/search interactions (Research R8) — never used to submit/apply/commit a configuration change.
4. Capture the requested artifact kinds.
5. Return the extracted information/artifacts to satisfy `intent`.

**Output**:
- `result`: the extracted value(s)/text answering `intent`
- `artifacts`: paths/content for each captured kind (screenshot, console log, network request list/detail)
- `status`: `"ok"` | `"sign_in_required"` | `"blocked"` | `"timed_out"` | `"conflict"` (concurrent profile use, FR-014)

**Never**: stores, requests, or transmits credentials (FR-005); applies a domain allowlist of its own (Clarification Q2 — governed by DefenseClaw instead); writes a dedicated audit record beyond what DefenseClaw already captures generically (Clarification Q3).
