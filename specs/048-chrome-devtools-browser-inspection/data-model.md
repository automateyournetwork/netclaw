# Data Model: Chrome DevTools Browser Automation & Inspection Skill

**Feature**: 048-chrome-devtools-browser-inspection
**Date**: 2026-07-07

None of these entities are persisted by NetClaw in a database — they are conceptual objects that exist for the lifetime of a tool invocation or a browser session, sourced from the upstream `chrome-devtools-mcp` server's own in-memory state and the on-disk Chrome profile it manages. This data model documents their shape for the purposes of skill design and contract definition, not schema implementation.

## Entities

### BrowserSession

A launched, controlled Chrome instance tied to a persistent (or, for `--isolated` runs, temporary) profile.

| Field | Type | Description |
|-------|------|-------------|
| mode | str | `"headless"` or `"headed"` (Clarification Q1 / FR-015) |
| profile_dir | str | Path to the on-disk Chrome profile in use (`CHROME_DEVTOOLS_PROFILE_DIR` or an `--isolated` temp path) |
| channel | str | Chrome channel: `stable` (default), `beta`, `dev`, or `canary` |
| attach_mode | str | `"launched"` (server started its own Chrome) or `"attached"` (connected to an already-running Chrome via `--browserUrl`/`--autoConnect`, per Research R3 Pattern B) |
| open_pages | list[TargetPage] | The page(s) currently open in this session |

**Lifecycle**: launched or attached → one or more pages navigated/inspected within it → closed (or left running for reuse by a subsequent invocation, per FR-010's "multiple checks in one session" requirement).

### PersistentProfile

The on-disk Chrome profile directory holding cookies/local storage/session state for previously, manually authenticated sites.

| Field | Type | Description |
|-------|------|-------------|
| path | str | Filesystem path (default `~/.openclaw/chrome-devtools/profile`) |
| authenticated_sites | list[str]? | Not tracked by NetClaw explicitly — this is implicit in Chrome's own cookie jar; recorded here only conceptually to describe the entity, not as a field NetClaw reads/writes directly |

**Validation rules**: NetClaw never inspects or extracts credential material from this path — it is treated as an opaque, Chrome-owned directory (FR-005). One profile may hold valid sessions for multiple sites at once and outlives any single `BrowserSession`.

### TargetPage

The local file or remote URL being loaded, inspected, or automated.

| Field | Type | Description |
|-------|------|-------------|
| source | str | Either a local file path (`file://...`, typically a NetClaw-generated visualization) or a remote URL |
| requires_auth | bool | Whether this page is expected to need a signed-in session in the persistent profile (always `false` for `browser-viz-verify` targets, situational for `browser-gui-inspect` targets) |
| load_state | str | `"loaded"`, `"timed_out"`, `"sign_in_required"`, or `"blocked"` (Edge Cases) |

### CapturedArtifact

A screenshot, console log excerpt, network request/response record, or audit report produced during a session.

| Field | Type | Description |
|-------|------|-------------|
| kind | str | `"screenshot"`, `"console_log"`, `"network_request"`, or `"audit_report"` |
| source_page | TargetPage | The page this artifact was captured from |
| content_ref | str | Where the artifact was written (a file path under the same convention as other NetClaw skill outputs) or inline content for small text artifacts (e.g., a single console message) |
| captured_at | str | ISO 8601 timestamp |

**Validation rules**: Per Edge Cases, an artifact containing sensitive data (a visible session token, a secret rendered in a dashboard) is written under the same access controls as other sensitive skill outputs — no separate, more permissive storage path.

## Relationships

```
BrowserSession --[has one]--> PersistentProfile
BrowserSession --[has many]--> TargetPage
TargetPage --[produces many]--> CapturedArtifact
```

## State Transitions

### TargetPage load_state

```
(navigation requested) → loaded
(navigation requested) → timed_out       (Edge Cases: bounded wait exceeded)
(navigation requested) → sign_in_required (Edge Cases: cached session expired/absent — FR-008)
(navigation requested) → blocked          (Edge Cases: target site detects/blocks automation)
```

### BrowserSession lifecycle

```
requested → launched|attached → (page(s) navigated, artifacts captured)* → closed
```
