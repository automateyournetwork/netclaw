---
name: browser-viz-verify
description: "Verifies that a NetClaw-generated visualization HTML file (three.js, canvas, drawio, UML, markmap) actually renders correctly — screenshot, console-error check, and an optional Lighthouse audit. Use immediately after generating any browser-based visualization output, to close the QA gap that otherwise requires a human to manually open the file. Never touches an external site or the authenticated browser profile."
version: 1.0.0
license: Apache-2.0
tags: [browser-automation, qa, visualization, chrome-devtools]
metadata:
  { "openclaw": { "requires": { "bins": ["node", "npx"], "env": [] } } }
---

# Browser Visualization Verify Skill

## Purpose

NetClaw ships several skills that generate browser-based visualization outputs — `threejs-network-viz`, `canvas-network-viz`, `drawio-diagram`, `uml-diagram`, `markmap-viz`. Until now, confirming that a generated file actually rendered correctly (no blank canvas, no JavaScript errors, no broken layout) required a human to manually open it in a browser. This skill closes that gap: it opens the file itself in a controlled, headless Chrome session, takes a screenshot, reads the console for errors, and optionally runs a Lighthouse audit — then reports a clear verdict.

This skill **never** navigates to a remote URL and **never** touches the persistent authenticated browser profile used by `browser-gui-inspect`. It only ever opens local `file://` paths. See `specs/048-chrome-devtools-browser-inspection/` for the full spec, research, and design behind this skill.

## MCP Server

This skill uses tools provided by the **chrome-devtools-mcp** server (official Chrome DevTools team package, `chrome-devtools-mcp` on npm), spawned locally via `npx -y chrome-devtools-mcp@latest` over stdio transport. See `mcp-servers/chrome-devtools-mcp/README.md`.

## Environment Variables

None. `chrome-devtools-mcp` takes all configuration as CLI flags, not env vars. This skill always runs headless against a local file — it never needs `--headless=false` or the persistent profile's authenticated sessions.

---

## Workflow: Verify a Generated Visualization (P1 — MVP)

**Input**:
- `file_path` (required) — absolute path to the generated visualization HTML file
- `run_audit` (optional, default `false`) — whether to also run a Lighthouse audit

### Step 1: Confirm the file exists

Before opening a browser session, verify `file_path` exists on disk. If it does not, stop and return:

```
verdict: "file_not_found"
```

Do not attempt to open a browser session for a path that doesn't exist.

### Step 2: Open the file in a headless session

```
Tool: new_page
Args: { "url": "file://<file_path>" }
```

### Step 3: Wait for the page to settle

Async-rendered visualizations (three.js scenes, canvas drawings) may take a moment to finish drawing. Use a bounded wait rather than capturing immediately:

```
Tool: wait_for
Args: { "text": <a string known to appear once rendering completes, e.g. a legend label>, "timeoutMs": 15000 }
```

If the wait times out, stop and return:

```
verdict: "timed_out"
```

### Step 4: Capture a screenshot

```
Tool: take_screenshot
```

Save the result as the `screenshot_path` artifact, following the same output-directory convention as other NetClaw skill artifacts.

### Step 5: Read the console

```
Tool: list_console_messages
```

Classify the result:
- No errors/warnings present → `verdict: "rendered_clean"`
- One or more error/warning messages present → `verdict: "rendered_with_errors"`, and include the message text in `console_errors` — don't just report a blank/inconclusive screenshot when the console explains exactly what broke.

### Step 6: Optional Lighthouse audit

If `run_audit` is `true`:

```
Tool: lighthouse_audit
```

Summarize the findings (performance, accessibility) into `audit_summary`. Skip this step entirely when `run_audit` is `false` — it adds meaningful runtime and isn't needed for a quick render check.

### Step 7: Close the session

```
Tool: close_page
```

### Output

```
{
  "verdict": "rendered_clean" | "rendered_with_errors" | "timed_out" | "file_not_found",
  "screenshot_path": "<path to captured screenshot>",
  "console_errors": ["<message>", ...],
  "audit_summary": { ... }   // present only if run_audit was true
}
```

---

## Invoking from Other Skills

`threejs-network-viz`, `canvas-network-viz`, `drawio-diagram`, `uml-diagram`, and `markmap-viz` should each call `browser-viz-verify` automatically immediately after writing their generated HTML file, passing the freshly written file's path. This turns "did it render?" from a question the operator has to answer manually into a QA step NetClaw answers itself, within the ~30-second budget described in the spec's success criteria (SC-001). If `browser-viz-verify` returns `rendered_with_errors` or `timed_out`, surface that to the operator alongside the generated file rather than silently reporting success.

## Error Handling

| Verdict | Meaning | What to tell the operator |
|---------|---------|----------------------------|
| `rendered_clean` | Screenshot captured, no console errors | Visualization is good to share/open |
| `rendered_with_errors` | Screenshot captured, but console shows JS errors/warnings | Show the exact console message(s) — don't just say "something went wrong" |
| `timed_out` | Page never reached the expected rendered state within the bounded wait | The generated file may be malformed, or reference a resource that failed to load |
| `file_not_found` | `file_path` doesn't exist | Confirm the visualization skill actually wrote the file before calling this skill |

## Constitution Notes

This skill is purely observational (Constitution I) — it never performs a write against any system, requires no ITSM gating (III), and needs no bespoke audit trail beyond DefenseClaw's generic tool-call logging (IV) since it is read-only and touches no external or authenticated system.
