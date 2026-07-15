# Contract: `desktop-gui-inspect` Skill Interface

**Feature**: 050-computer-use-desktop
**Date**: 2026-07-08

This is the operator/agent-facing contract for the one new skill this feature adds. It is a thin orchestration layer over the upstream `computer-use` skill's 17 actions — it does not implement desktop automation itself.

## `desktop-gui-inspect`

**Maps to**: User Stories 2 and 3 (P2, P3)

**Input**:
- `intent` (required) — a natural-language description of what to read, confirm, or do in the target desktop application (e.g., "open the legacy NMS client and tell me the current alarm count")
- `target_application` (optional) — the application name/identifier if already known; otherwise the skill locates it on the virtual desktop
- `watch` (optional, default `false`) — if true, the skill's response includes the live-viewer connection details so the operator can follow along (or was asked to open one before starting)

**Behavior**:
1. Confirm the virtual desktop session is available (report distinctly if the `computer-use` component isn't installed/running — see Error Handling).
2. If `target_application` needs to be opened and it appears to require first-time interactive setup, stop and report that (Edge Cases) rather than guessing.
3. Perform the sequence of desktop actions (click/type/scroll/screenshot, etc.) needed to satisfy `intent` — restricted to read/navigate/confirm actions (Golden Rule, research.md R4) — never a submit/apply/commit action.
4. Capture a screenshot as supporting evidence alongside the answer.
5. Return the result.

**Output**:
```
{
  "result": "<the extracted value/text/confirmation answering intent>",
  "screenshot_path": "<path to the captured screenshot>",
  "status": "ok" | "manual_setup_required" | "virtual_desktop_unavailable" | "conflict"
}
```

**Never**: uses a desktop action to submit, apply, or commit a real configuration change (Golden Rule); stores or requests credentials for any target application (FR-007); assumes the live-viewing service is safe to expose beyond loopback without verification (FR-004).

## Error Handling

| Status | Meaning | What to tell the operator |
|--------|---------|----------------------------|
| `ok` | Requested information/interaction succeeded | Return the result and the screenshot |
| `manual_setup_required` | The target application needs interactive first-time setup | Ask the operator to complete it via the live viewer (Workflow 2), then retry |
| `virtual_desktop_unavailable` | The `computer-use` component isn't installed, or its session failed to start | Point at `./scripts/install.sh --components computer-use` (or the equivalent at implementation time) |
| `conflict` | Another task is already using the single shared virtual desktop | Retry once the other task completes |
