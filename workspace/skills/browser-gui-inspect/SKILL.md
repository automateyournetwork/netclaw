---
name: browser-gui-inspect
description: "Controller-agnostic browser automation and inspection — navigate, read, click, fill, and capture network traffic on any web GUI using a persistent, manually-authenticated Chrome profile. Use to (1) pull a GUI-only report a vendor's REST API doesn't expose, (2) discover the undocumented API behind a dashboard feature, (3) automate a one-off interaction with a web tool that has no NetClaw API integration, or (4) run any of the above in Watch Mode — a real, visible Chrome window an operator can watch work live. Never used to submit, apply, or commit a configuration change — that remains the job of the relevant API-based skill."
version: 1.0.0
license: Apache-2.0
tags: [browser-automation, sdn, controller-gui, api-discovery, chrome-devtools]
metadata:
  { "openclaw": { "requires": { "bins": ["node", "npx"], "env": [] } } }
---

# Browser GUI Inspect Skill

## Purpose

Many controllers and web-based tools NetClaw talks to via REST API also have GUI-only reports, dialogs, or visualizations the API doesn't expose — and some tools (classic SDN controller consoles, vendor support portals, SaaS admin consoles) have no NetClaw API integration at all. This skill is the controller-agnostic fallback: it drives a real, persistent, manually-authenticated Chrome session to read, search, confirm, and capture whatever an operator needs from a web GUI.

This skill deliberately contains **no per-vendor DOM/selector knowledge**. Every invocation is directed by the operator's own `target` URL and `intent` at request time — nothing about any specific controller's page layout is hardcoded here (Constitution VI — Multi-Vendor Neutrality). See `specs/048-chrome-devtools-browser-inspection/` for the full spec, research, and design behind this skill.

## Golden Rule — Read/Confirm/Search Only, Never a Config-Change Mechanism

**This skill's interactive tools (`click`, `fill`, `fill_form`, `drag`, `press_key`, `type_text`, `handle_dialog`, `upload_file`) are for reading, filtering, searching, and confirming state on a page — never for submitting, applying, or committing a configuration change to network infrastructure.** If a request would require clicking something like "Commit," "Apply," "Submit," "Deploy," or "Save" on a controller's configuration workflow, stop and tell the operator that this must go through the relevant API-based skill instead (e.g., the ACI, Panorama, or FortiManager skill), which implements the proper observe→baseline→modify→verify workflow and ServiceNow CR gating (Constitution I, II, III, VIII). Using this skill to bypass that workflow would create an unaudited, unverified side door around NetClaw's safety model — see `specs/048-chrome-devtools-browser-inspection/research.md` R8 for the full rationale.

## MCP Servers — Headless and Watch Mode

This skill uses tools provided by the **chrome-devtools-mcp** package (official Chrome DevTools team, `chrome-devtools-mcp` on npm), registered **twice**:

| Server | Mode | When to use |
|--------|------|-------------|
| `chrome-devtools-mcp` | `--headless=true` | Default — routine gap-fill, API discovery, general automation with no need for a human to watch |
| `chrome-devtools-mcp-visible` | `--headless=false` | **Watch Mode** — the operator explicitly wants to see it happen (e.g., "watch it...", "show me...", "let me see...") |

Both are the same package, spawned locally over stdio via `npx -y chrome-devtools-mcp@latest`. See `mcp-servers/chrome-devtools-mcp/README.md`. Every workflow below (gap-fill, API discovery, general automation) works identically against either server — pick the server based on whether the operator asked to watch, then use that server's tools for the whole request.

**Recognizing a Watch Mode request**: if the operator's phrasing signals they want to observe the browser (e.g., "watch", "show me", "let me see it", "I want to see this happen"), use `chrome-devtools-mcp-visible`'s tools for the entire request. Otherwise default to the headless `chrome-devtools-mcp` server. This is a per-request choice, not a global setting — the same skill, same workflows, just a different server backing the tool calls.

## Configuration

No environment variables — `chrome-devtools-mcp` takes all configuration as CLI flags, not env vars. NetClaw's registration pins `--headless=true` for automated use; everything else (including the persistent profile holding sign-in sessions) uses the tool's own default at `~/.cache/chrome-devtools-mcp/chrome-profile`.

No credential-bearing environment variable exists for this skill. NetClaw never requests, stores, or transmits credentials for any target site (FR-005) — see the Headless/Headed Mode & Sign-In section below.

---

## Workflow 1: Fill a Gap in an Existing Controller Skill (P2)

Use this when a controller's REST API doesn't expose a report, setting, or visualization the operator needs, but its web dashboard shows it.

**Input**:
- `target` (required) — the vendor dashboard/GUI page URL
- `intent` (required) — plain-language description of what to read or extract (e.g., "get the bridge domain list from this ACI tenant page")
- `actions` (optional) — a sequence of navigate/click/fill/read steps if multi-step interaction is needed
- `capture` (optional, default `["screenshot", "console"]`) — artifact kinds to capture

### Step 1: Navigate using the persistent profile

```
Tool: navigate_page
Args: { "url": <target> }
```

### Step 2: Detect a sign-in wall before proceeding

Read the page (via `take_snapshot` or `take_screenshot`) and check whether it looks like a login/SSO page rather than the expected dashboard content. If so, **stop** and return:

```
status: "sign_in_required"
```

Do not proceed to interact with a login form, and do not return an empty or fabricated result — report this distinctly so the operator knows a manual sign-in (see below) is needed, per FR-008.

### Step 3: Perform the requested read/confirm/search actions

Using `click`, `fill`, `hover`, `press_key`, etc. as needed to reach the information described in `intent` — e.g., selecting a tenant, expanding a section, applying a filter. Reiterate: these actions are for navigating *to* the information, never for submitting a change.

### Step 4: Capture the requested artifacts

- `take_screenshot` for a visual capture
- `take_snapshot` or targeted reading of page text/structure for the extracted value
- `list_console_messages` if `"console"` is requested

### Step 5: Return the result

```
{
  "result": "<the extracted value(s)/text answering intent>",
  "artifacts": { "screenshot_path": "...", "console_log": [...] },
  "status": "ok" | "sign_in_required" | "blocked" | "timed_out"
}
```

### Worked Example: ACI APIC Bridge Domains

> "Pull the bridge domain list from the ACI tenant page in APIC — the API doesn't expose it the way I need."

1. `navigate_page` to the tenant's Bridge Domains page in APIC.
2. Confirm the session is authenticated (not a login page) — if not, return `sign_in_required`.
3. Read the bridge domain table via `take_snapshot` (accessibility-tree text read is more reliable than parsing a screenshot).
4. Return the bridge domain names/subnets found, plus a screenshot for visual confirmation.

---

## Workflow 2: Discover an Undocumented Vendor API (P3)

Use this when building a new API-based skill for a controller whose public API documentation is incomplete — load the dashboard feature in question and observe what network calls it actually makes.

**Input**:
- `target` (required) — the dashboard page to load
- `intent` (required) — the action to trigger (e.g., "click Refresh on the client list filtered by SSID")
- `capture: ["network_requests"]` (required for this workflow)

### Step 1: Navigate and authenticate

Same as Workflow 1, Steps 1-2 — navigate to `target`, confirm the session isn't sign-in-walled.

### Step 2: Trigger the action under investigation

Perform the click/fill/navigation described in `intent` that causes the dashboard to make the network call(s) of interest.

### Step 3: Enumerate observed network activity

```
Tool: list_network_requests
```

This returns every request (method, URL, status) made since the page loaded — including calls the dashboard makes that aren't part of any published API documentation.

### Step 4: Retrieve full detail on a specific request

```
Tool: get_network_request
Args: { "requestId": <id from the list above> }
```

Returns the full method, URL, status, and request/response body for that call — everything needed to replicate it in a future API-based skill.

### Step 5: Summarize the finding

Report the discovered endpoint (method + URL pattern), the request payload shape, and the response shape, so a contributor can go implement it as a proper API-based skill rather than continuing to rely on GUI automation for that use case going forward.

### Worked Example: Meraki Dashboard Client List

> "Load the Meraki dashboard's client list page and tell me what API calls it makes when I filter by SSID."

1. `navigate_page` to the network's Clients page in the Meraki dashboard.
2. Apply the SSID filter (a `click`/`fill` interaction — reading/filtering, not a config change).
3. `list_network_requests` to see what the filter action triggered.
4. `get_network_request` on the relevant XHR/fetch call to get its exact URL, query parameters, and response shape.
5. Report back the endpoint found, so it can inform a future Meraki API-based skill enhancement.

---

## Workflow 3: General-Purpose Web GUI Automation (P4)

Use this as the broadest fallback: an ad hoc navigate/read/interact request against a browser-based tool with no existing NetClaw integration — a classic SDN controller GUI (e.g., OpenDaylight or ONOS), a vendor support/TAC portal, or a SaaS admin console with incomplete API coverage.

**Input**:
- `target` (required) — the page to load
- `intent` (required) — free-form description of what to read or do; no page-structure assumptions are made ahead of time

### Approach

1. `navigate_page` to `target`.
2. Use `take_snapshot` (accessibility-tree text read) as the primary way to understand an unfamiliar page's structure and content — it's more reliable for arbitrary, unknown layouts than trying to guess CSS selectors.
3. Use `take_screenshot` when a visual answer is what's actually being asked for (e.g., "what does the topology view look like").
4. Use `evaluate_script` only to read a value the DOM/accessibility tree doesn't otherwise expose (e.g., a value held in a JS variable) — never to submit a change (Golden Rule above still applies here).
5. Report the resulting page state or extracted value back to the operator in plain language.

### Worked Examples

> "Open the ONOS GUI topology view and tell me how many devices it shows."

Navigate to the ONOS GUI topology page, read the device count via `take_snapshot` or a screenshot, report the number back.

> "Check the status of my open case on the vendor support portal."

Navigate to the portal's case list (using the already-authenticated persistent profile), read the case status, report it back.

---

## Workflow 4: Watch Mode — Run Any Workflow With a Visible Browser (FR-015)

Headless vs. headed is a genuine per-request choice, not a fixed setting — NetClaw has **two live registrations** of the same server (see MCP Servers above): `chrome-devtools-mcp` (headless, default) and `chrome-devtools-mcp-visible` (headed). When the operator asks to watch, use `chrome-devtools-mcp-visible`'s tools for Workflow 1, 2, or 3 above exactly as written — nothing about the workflow steps changes, only which server backs the tool calls. A real Chrome window opens wherever NetClaw's host process runs: on a Mac or Linux desktop it's simply on that screen, on WSL2 with WSLg it renders as a native Windows window, and on a genuinely display-less host it will fail to launch (use the sign-in-only Pattern B below in that case, which doesn't require Watch Mode).

**Worked Example: Watch NetClaw Log Into NetBox and Create a Site**

> Slack: "Watch it log into the NetBox demo at https://demo.netbox.dev/ and create a new site."

1. Recognize "watch" → use `chrome-devtools-mcp-visible`.
2. `navigate_page` to `https://demo.netbox.dev/login/`.
3. If a session already exists in the shared profile, skip to step 5; otherwise this is exactly the kind of GUI login a human should complete live in the visible window (NetBox's public demo uses shared read/write demo credentials published on its own login page — reading and entering credentials that are publicly published by the target site for anonymous demo use is not the same as NetClaw handling a real operator's private credentials, but this skill still doesn't type them in blindly: ask the operator to confirm the demo login flow, or complete it in the visible window yourself since you can see it).
4. Navigate to the Sites section, click "Add," fill the new site's name/slug/status fields per the operator's request, and submit.
5. Take a screenshot of the created site's detail page and report success back in Slack.

This is the one documented case where filling and submitting a form is expected (Golden Rule caveat): it's a public demo sandbox with no real network impact, explicitly requested and watched live by the operator — not an unattended, unaudited configuration change against production infrastructure.

**One-time sign-in for sites that need real credentials** (separate from Watch Mode — this is about establishing a session, not watching one): still needed for real production dashboards. Two patterns, both documented in full in `specs/048-chrome-devtools-browser-inspection/quickstart.md` and `mcp-servers/chrome-devtools-mcp/README.md`:

- **Pattern A — host has a display**: launch `chrome-devtools-mcp-visible` (or run `npx chrome-devtools-mcp@latest --headless=false` directly) and sign in once — the shared default profile (`~/.cache/chrome-devtools-mcp/chrome-profile`) carries the session forward to the headless registration too.
- **Pattern B — host has no display at all**: sign in on your own workstation's Chrome with `--remote-debugging-port=9222`, tunnel that port over SSH, and attach via `--browserUrl` (or `--autoConnect` on Chrome 144+) for that session.

## Access Control & Audit

No bespoke domain allowlist or audit trail is built into this skill. Access scoping relies on NetClaw's general permission-prompt model and DefenseClaw's `tool block` / `tool allow` controls; auditing relies on DefenseClaw's existing "Tool Call Inspection... on all tool executions." See `specs/048-chrome-devtools-browser-inspection/research.md` R4/R5 for the rationale — this skill's tool calls are not special-cased or exempt from either mechanism.

## Error Handling

| Status | Meaning | What to tell the operator |
|--------|---------|----------------------------|
| `ok` | Requested information/interaction succeeded | Return the result and artifacts |
| `sign_in_required` | The target site's cached session has expired or was never established | Ask the operator to complete Pattern A or B above for that site, then retry |
| `blocked` | The target site detected and blocked automated access | Report the block plainly — do not retry silently or attempt to disguise the automation |
| `timed_out` | The page never finished loading within the bounded wait | The site may be slow/unreachable, or the page may require a different starting URL |
| `conflict` | A concurrent session is already using the persistent profile | Retry once the other session completes |
