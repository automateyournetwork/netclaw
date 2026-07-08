# MCP Tool Reference: chrome-devtools-mcp

**Feature**: 048-chrome-devtools-browser-inspection
**Date**: 2026-07-07
**Transport**: stdio (local process via `npx chrome-devtools-mcp@latest`)
**Auth**: None required by the server itself — target-site authentication is handled entirely via the operator's manual sign-in into the persistent Chrome profile (`CHROME_DEVTOOLS_PROFILE_DIR`)
**Source**: Official Chrome DevTools team package (`chrome-devtools-mcp` on npm, `github.com/ChromeDevTools/chrome-devtools-mcp`)

> These tools are provided by the upstream `chrome-devtools-mcp` package. NetClaw registers and spawns it — it does not implement the tools. The full tool set includes ~50+ tools (navigation, input, network, performance, debugging/emulation, memory/heap-snapshot, extensions, third-party/WebMCP); only the subset relevant to this feature's four user stories is documented below. Memory/heap-snapshot and extension-management tools are out of scope for this feature.

## Tools Used by `browser-viz-verify` (US1)

| Tool | Description | Used For |
|------|-------------|----------|
| new_page / navigate_page | Open the generated visualization file (`file://...`) | Loading the target HTML |
| wait_for | Wait for a specific text/element to appear before capturing | Letting async-rendered visualizations (three.js, canvas) finish drawing |
| take_screenshot | Capture the rendered page | Visual confirmation (FR-001) |
| list_console_messages / get_console_message | Retrieve JS console output | Detecting render errors (FR-002) |
| lighthouse_audit | Run a performance/accessibility audit | Optional deeper check (FR-003) |
| close_page | Close the tab when done | Session cleanup |

## Tools Used by `browser-gui-inspect` (US2-US4)

### Navigation & Session

| Tool | Description | Write? |
|------|-------------|--------|
| navigate_page | Go to a URL, back/forward, or reload | No |
| new_page / list_pages / select_page / close_page | Tab management | No |
| wait_for | Wait for text/element before proceeding | No |

### Reading & Interacting

| Tool | Description | Write?* |
|------|-------------|--------|
| take_snapshot | Accessibility-tree text representation of the page (structured reading) | No |
| take_screenshot | Visual capture | No |
| click / hover | Activate or move over an element | Situational |
| fill / fill_form | Enter text / populate form fields | Situational |
| drag / press_key / type_text | Additional input actions | Situational |
| handle_dialog | Respond to a browser-native dialog | Situational |
| upload_file | Submit a file through an upload control | Situational |

*"Situational" — per Research R8, these tools MUST be used only for reading, filtering, searching, or confirming state (e.g., typing into a search box, expanding an accordion, dismissing a cookie banner) — never for submitting/applying/committing a configuration change on network infrastructure. `browser-gui-inspect`'s `SKILL.md` states this explicitly.

### Network Inspection (US3 — API discovery)

| Tool | Description | Write? |
|------|-------------|--------|
| list_network_requests | All network activity observed since the page loaded | No |
| get_network_request | Full detail (method, URL, status, request/response body) of one request | No |

### Debugging & Emulation

| Tool | Description | Write? |
|------|-------------|--------|
| list_console_messages / get_console_message | Console output | No |
| evaluate_script | Run JS in the page context to extract a value the DOM doesn't otherwise expose | No (read-only use only — see Research R8 scoping) |
| resize_page / emulate | Viewport/device emulation | No |
| performance_start_trace / performance_stop_trace / performance_analyze_insight | Performance tracing | No |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| CHROME_DEVTOOLS_PROFILE_DIR | No | `~/.openclaw/chrome-devtools/profile` | Persistent Chrome profile directory (`--userDataDir`) |
| CHROME_DEVTOOLS_HEADLESS | No | `true` | `true` for headless, `false` for headed (FR-015 / Clarification Q1) |
| CHROME_DEVTOOLS_CHANNEL | No | `stable` | Chrome channel: `stable`, `beta`, `dev`, `canary` |

None of these are secrets — no credential-bearing environment variable exists for this integration (FR-005).

## Error Responses

Tools in this integration surface (via the skill layer, per spec Edge Cases):

- **Browser runtime unavailable**: Node.js or a Chrome/Chromium binary is missing on the host (FR-013)
- **Sign-in required**: the target page's cached session has expired or was never established (FR-008)
- **Profile conflict**: a concurrent session attempted to use the same persistent profile (FR-014)
- **Navigation timeout**: the page did not finish loading within the bounded wait
- **Blocked**: the target site detected and blocked automated access
- **File not found**: a local file target does not exist at the given path
