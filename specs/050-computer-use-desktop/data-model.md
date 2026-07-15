# Data Model: Computer Use — Full-Desktop Automation via OpenClaw's Native Skill

**Feature**: 050-computer-use-desktop
**Date**: 2026-07-08

None of these are persisted by NetClaw — they are conceptual entities describing the ephemeral state of the upstream `computer-use` skill's own virtual desktop session, documented here for skill design and contract clarity, not schema implementation.

## Entities

### VirtualDesktopSession

The running Xvfb + XFCE environment.

| Field | Type | Description |
|-------|------|-------------|
| display | str | The virtual X display identifier (e.g. `:99`, per the upstream skill's own default) |
| resolution | str | Virtual screen resolution (e.g. `1024x768`, per upstream default) |
| open_windows | list[str]? | Conceptual — whatever application windows are currently open; not tracked by NetClaw directly, only observable via screenshot/state actions |

**Lifecycle**: started by the skill on first use (or at install time, depending on upstream behavior — confirmed during implementation) → remains running across multiple `desktop-gui-inspect` invocations → one shared session per host at a time (spec Assumptions).

### LiveViewerConnection

An operator's real-time view into the `VirtualDesktopSession`.

| Field | Type | Description |
|-------|------|-------------|
| mode | str | `"watch"` (read-only) or `"control"` (operator has taken over input) |
| transport | str | `"vnc"` (native client) or `"novnc"` (browser-based, via websockify) |
| reachable_from | str | `"loopback"` by default (FR-004); `"remote-via-tunnel"` only if the operator has explicitly established one |

**Validation rules**: `reachable_from` MUST be `"loopback"` unless an operator-established secure path exists — this is verified post-install (research.md R5), not assumed.

### DesktopAction

A single action performed against the `VirtualDesktopSession` (one of the upstream skill's 17: click variants, type, key combination, scroll, drag, screenshot, zoom, wait).

| Field | Type | Description |
|-------|------|-------------|
| kind | str | e.g. `"click"`, `"type"`, `"screenshot"`, `"scroll"`, `"drag"` |
| target_description | str? | Operator-supplied description of what's being acted on (no pre-programmed per-application knowledge, per Constitution VI) |
| is_state_changing | bool | Conceptual flag used by `desktop-gui-inspect`'s own Golden Rule reasoning — read/navigate actions (click to open a menu, type into a search box) vs. actions that would submit a real change (click "Apply"). This distinction is enforced by the skill's documented judgment, not a technical guardrail the upstream tool itself understands. |

### LegacyTargetApplication

The desktop-only application being read from or interacted with.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Operator-supplied, at request time |
| requires_manual_setup | bool | Whether first-time interactive setup (license dialog, initial login) is needed before automation can proceed (Edge Cases) |

## Relationships

```
VirtualDesktopSession --[viewed/controlled by 0..1 active]--> LiveViewerConnection
VirtualDesktopSession --[hosts]--> LegacyTargetApplication (0 or more open at once)
DesktopAction --[performed against]--> VirtualDesktopSession
DesktopAction --[targets]--> LegacyTargetApplication
```

## State Transitions

### LegacyTargetApplication readiness

```
(first encountered) → requires_manual_setup=true → (operator completes setup via LiveViewerConnection) → requires_manual_setup=false → automatable
```

### LiveViewerConnection mode

```
(operator opens viewer) → watch → (operator takes input) → control → (operator releases) → watch
```
