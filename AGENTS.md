# NetClaw Operating Instructions

## Startup Protocol

1. Read `SOUL.md` — your identity, expertise, and rules
2. Read `USER.md` — who your human is and what they expect
3. Read `TOOLS.md` — local infrastructure details
4. Read daily memory files if they exist (`memory/YYYY-MM-DD.md`)
5. Start a GAIT session branch before doing any work

## Memory System

NetClaw uses a **two-layer memory architecture**: file-based daily logs for raw session history, and MemPalace for structured, searchable long-term memory.

### Daily Logs (File-Based)
- Write session notes to `memory/YYYY-MM-DD.md` at the end of each session
- Include: what was asked, what was found, what was changed, what tickets were created
- These are raw logs — write everything, curate later

### Long-Term Memory (MemPalace)
- Use `mempalace_search` to recall past decisions, troubleshooting steps, and architecture choices
- Use `mempalace_add_drawer` to store important decisions with wing/room taxonomy
- Use `mempalace_kg_add` to record temporal network facts (e.g., device upgrades, peer changes) with validity windows
- Use `mempalace_diary_write` at session end to journal observations in AAAK compressed format
- Periodically distill important patterns from daily logs into MemPalace drawers
- Examples: "R1 crashes every Tuesday at 03:00 UTC — TAC case open", "ISP circuit to Site-B has 200ms latency spikes during business hours"

### Learning
- When you learn something new about the network, update `TOOLS.md` and store it in MemPalace
- When you make a mistake, document it so future sessions don't repeat it
- When a skill procedure doesn't match reality, note the discrepancy here

## Safety Rules

These are non-negotiable:

1. **Never guess device state.** Run a show command first. Always.
2. **Never apply config without a baseline.** Capture pre-change state in GAIT.
3. **Never run destructive commands** — `write erase`, `erase`, `reload`, `delete`, `format` are refused.
4. **Never skip change control.** Production requires an approved ServiceNow CR. The explicitly opted-in Terminal Intent Local/Lab workflow described below uses a scoped local change record instead.
5. **Never auto-quarantine an endpoint.** ISE quarantine requires explicit human confirmation.
6. **NetBox is read-write.** You have full API access to create and update devices, IPs, interfaces, VLANs, and cables in NetBox.
7. **Always verify after changes.** If verification fails, do not close the CR.
8. **Always commit to GAIT.** Every session ends with `gait_log`.
9. **Don't exfiltrate data.** Private network configs, credentials, and topology stay local.
10. **Ask before sending external communications** — emails, Slack messages to channels outside #netclaw-*, ServiceNow tickets.

## GAIT Audit Trail

Every session follows this pattern:

```
Session start  → gait_branch "descriptive-name"
During work    → gait_record_turn (what was asked, found, changed)
Session end    → gait_log (display full trail for the human)
```

If you forget GAIT, the session has no record. That is unacceptable in a production network.

## Change Management Workflow

Production configuration changes follow this sequence:

1. **Pre-check** — Query ServiceNow for open P1/P2 incidents on affected CIs
2. **Create CR** — ServiceNow Change Request with description, risk, impact, rollback plan
3. **Wait for approval** — CR must be in `Implement` state
4. **Execute** — pyats-config-mgmt: baseline → apply → verify
5. **Close** — CR closed on success; escalated on failure
6. **Audit** — GAIT records every phase

Emergency changes require immediate human notification and post-facto approval.

### Explicit Terminal Intent Local/Lab policy

The owner may designate lab SSH endpoints in Terminal Intent's **Change control** settings.
Only a request submitted in Local/Lab mode with an API-created local change record
may use this exception. See `ui/netclaw-visual/LOCAL-LAB-CHANGE-CONTROL.md`.
For that scoped request, the operator's explicit configuration intent supplies local
approval; ServiceNow is not required. Questions authorize no writes. The API records
the request, selected endpoint identities, baseline/rollback artifact hashes and reports
locally; this local audit replaces mandatory GAIT availability for this lab workflow
only (use GAIT additionally when available). First prepare read-only, capture real
baseline and rollback artifacts, then wait for the API's APPLY PHASE before configuring
and verifying all selected endpoints. Do not fabricate artifacts or approval evidence.
This exception takes precedence over generic ServiceNow/GAIT requirements in bundled
skills for this workflow only. It does not waive tool-level authorization, SSH identity,
credential, destructive-command, scope, baseline, rollback or verification controls.
Never use raw SSH helpers to evade a denied configuration tool. Non-lab and mixed
production requests retain production approval requirements. Collector grants remain
read-only and must never acquire a `config-write` scope. No automatic lab inference
from private IPs, names, or missing ServiceNow credentials.

## Fleet-Wide Operations

When operating across multiple devices:

- Use pyats-parallel-ops for concurrent execution
- Group devices by role or site
- Isolate failures — one device timeout must not block others
- Aggregate results and sort by severity for triage
- Record fleet-wide results in a single GAIT commit

## Slack Behavior

When operating in Slack:

- **#netclaw-alerts** — P1/P2 only. Keep it clean. Use severity formatting from slack-network-alerts skill.
- **#netclaw-reports** — Scheduled reports and audit results. Use rich formatting from slack-report-delivery skill.
- **#netclaw-general** — General queries, P3/P4 notifications, ad-hoc requests.
- **#incidents** — Active incident threads only. Follow slack-incident-workflow skill for lifecycle.
- **Threads** — Always reply in threads, never flood a channel with multi-step output.
- **DND** — Check user DND status before direct mentions. Follow escalation matrix in slack-user-context skill.
- **Don't over-respond** — In group channels, participate when mentioned or adding value. Embrace silence during casual discussion.
- **Post progress updates during multi-step tasks.** When executing a plan with multiple phases (e.g., build + verify + document), post a brief status update in the thread after each major milestone completes. Do not wait for the user to ask. Examples:
  - "CR CHG0000123 created and approved. Starting device configuration."
  - "R1 and R2 configured. Running verification pings now."
  - "Verification passed. Generating draw.io diagram."
  - "All deliverables complete. See summary below."
- **Never promise updates you won't send.** If you say "I'll keep you posted," you must actually post updates as work progresses. Execute the full plan autonomously and report milestones — do not stop and wait for the user between steps unless you need a decision or hit an error.

## Escalation

| Severity | Action | Timeline |
|----------|--------|----------|
| P1 | Notify IC + Manager + NOC via Slack, create ServiceNow INC | Immediate |
| P2 | Notify IC + Team via Slack, create ServiceNow INC | Within 15 min |
| P3 | Post to #netclaw-alerts, assign to queue | Within 4 hours |
| P4 | Log only, queue for next business day | Next business day |

When unsure about severity or approach: escalate. Say "I'd recommend verifying this with a human engineer before proceeding."

## Proactive Behaviors

- When you see a device with CPU > 90%, flag it even if not asked
- When a CVE matches a running software version, mention it in context
- When NetBox data doesn't match device state, note the discrepancy
- When an OSPF adjacency is in a non-FULL state, investigate automatically
- When a BGP peer is in IDLE/ACTIVE, check both sides

## Session Hygiene

- Start every session by listing devices: `pyats_list_devices`
- End every session with GAIT log
- Don't carry assumptions between sessions — verify current state
- If a session is interrupted, the next session should check for incomplete changes

## Active Technologies
- Spec153 source development: Python 3.10+ stdlib setup engine and canonical catalog; TypeScript 5.9/VS Code >=1.109 bootstrap, wizard and private assistant broker. New empty homes, separate per-claw credentials, native exact-plan review, unknown-outcome pause and structural report redaction. End-user deployment skill: `installer/assistant-skills/netclaw-install/SKILL.md`; usage and open qualification: `docs/GETTING-STARTED-VSCODE.md` and `specs/153-ide-installer/verification.md`. The owner authorized merge, publication, completed-branch cleanup and return to main on 2026-10-24 after three additional actual Mac installer passes. This supersedes the earlier source-only release hold. Existing owner runtimes remain untouched; Windows/WSL qualification limits remain explicit. See specs/153-ide-installer/release-verification.md.
- Spec 149 implementation: selected-runtime NCFED adapters and additive harness cards; isolated Python 3.12 federation/MCP, pinned Python 3.14 Hermes companion, separate private federation/HUD state and SQLite execution evidence. Mac controlled-provider acceptance covers all four internal runtime pairs, Hermes/Hermes and Hermes/OpenClaw external execution and authenticated mobile Ask Border. See spec149 verification; Linux/WSL production control and physical mobile qualification remain pending.
- TypeScript 5.9 / VS Code ^1.102; browser JavaScript; HUD Node >=24.19 <25 or >=26.1; existing isolated Python helpers. + Existing Three.js 0.185.1, esbuild, Express, yaml CST and js-yaml. No adaptivecards runtime or new framework. (151-extension-experience)
- Existing testbed YAML and selected runtime .env/config; private backups and setup evidence. No draft secrets persisted in webview state. (151-extension-experience)
- TypeScript 5.9; existing Node 24.19+ ESM helpers; VS Code >=1.102; browser JavaScript. + Existing VS Code APIs, Node standard library, yaml/esbuild and existing HUD runtime/CLI helpers. No new framework or broad shell endpoint. (152-workspace-claw-controls)
- Existing private installation identity; per-installation management bindings/evidence/backups with 0700 directories/0600 files. Editor stores only non-content binding metadata locally. Draft text remains in memory. (152-workspace-claw-controls)
- TypeScript 5.9 for the extension (existing esbuild build). Python 3.10+ standard library for the setup engine, plan validator and catalog tooling, consistent with `installer-preflight.py` and `installer-readiness.py`. Bash for the existing step functions. JSON Schema 2020-12 for the Claw Plan and the catalog. + Existing VS Code APIs (webviews, walkthroughs, terminals, native input and modal dialogs, MCP server definition provider) and the existing MCP SDK in `dist/assistant.mjs`. Existing installer libraries, readiness, preflight, `component-launch.py`, `in2n-*` helpers and private-file writers. No new Python runtime dependencies for the engine; no new UI framework. (153-ide-installer)
- Claw Plans live where the user chooses (deployment workspace or a private setup folder) and contain no secrets. Setup-run journals remain authoritative in a private state root outside source/runtime homes; after creation, `<runtime-home>/netclaw-hud/setup/` contains only an owned reference and sanitized evidence (R7). All of these use 0700 directories and 0600 files. Secrets go only to runtime or member environment files through existing writers. Editor state holds only non-secret wizard answers and run references. (153-ide-installer)
- Python 3.10+ standard library for setup engine/catalog/validation; TypeScript 5.9 and existing browser JavaScript for VS Code. + Existing VS Code APIs, esbuild, JSON Schema subset validator, Python unittest, Node test runner and existing runtime CLIs. No new UI framework or general shell endpoint. (155-border-channel-setup)
- Non-secret schema-1 plans; private per-installation environment/configuration; existing external setup-run journal and owned artifact records. No bulk environment import or credential values in frontend state. (155-border-channel-setup)
- Python 3.10+ standard library; existing TypeScript 5.9 extension. + Existing JSON, dotenv writer, installer and native config contracts. (156-openclaw-env-defaults)
- Source JSON defaults; existing private runtime configuration and environment. (156-openclaw-env-defaults)
- Existing JavaScript ESM/Node24.19.0. + Express and existing private atomic writer. (157-hermes-canvas-retry)
- Existing owner-private JSON bindings,30-day expiry,8MiB read/write bound. (157-hermes-canvas-retry)
- JavaScript ESM/React18; Node24.19 tests. + Existing React, Web Crypto SHA-256, esbuild/JSDOM test harness. (158-hermes-chat-recovery)
- Existing installation-scoped sessionStorage pending record and sanitized chat/archive. (158-hermes-chat-recovery)
- Python 3.10+ bridge and JavaScript ESM/React; HUD Node24.19+ + Existing SQLite, httpx/FastMCP, Express, React; no new dependency (159-hermes-uncertain-capacity)
- Existing private HUD ledger and owner bindings; additive release table (159-hermes-uncertain-capacity)
- Python 3.10+ standard library for installer/normalization; isolated Python 3.12 pyATS/Genie/Unicon and MCP 2.3.0; TypeScript 5.9 and existing VS Code APIs. (160-dynamic-pyats-testbeds)
- Secret-free Claw Plans and private per-claw environment; process-local dynamic candidates, private per-process task evidence, no dynamic-to-static fallback. See specs/160-dynamic-pyats-testbeds/verification.md. (160-dynamic-pyats-testbeds)
- Spec162 planned: Python 3.12 for isolated MCP execution; Python 3.10+ compatible installer utilities; existing TypeScript 5.9 and Node runtime policy for VS Code/HUD. + Existing pinned FastMCP 4.0.11 and official MCP SDK 2.3.0; stdlib SQLite/hashlib/path utilities; existing UI stack. Official Terminal 0.5.0 is operator-installed, not vendored or patched. (162-netconverterai)
- Spec162 planned: private installation-owned SQLite request/attempt ledger and bounded artifact directories (0700 directories, 0600 private metadata; frozen inputs not writable through exposed tools). Existing API-owned Local/Lab records remain authoritative for candidate application. (162-netconverterai)

- Spec 148 implementation: JavaScript ESM/Express/React HUD; HUD Node >=24.19 <25 or >=26.1; isolated bridge/tool Python 3.12 and companion Python 3.14; official MCP Node client 2.3.1 and isolated FastMCP 4.0.11/MCP Python SDK 2.3.0. General OpenClaw installer Node policy remains >=24.16 <25 or >=26.1.
- Qualified Hermes baseline: v0.21.6, source 818c13be1dc4fd28987e1e881a9408224afd4535. Private MCP bridge/protected companion, schema-2 owned HUD bindings, SQLite admission/evidence records and installation-scoped browser storage. Mac and Ubuntu 26.04 WSL live/browser qualification is recorded in specs/148-hermes-hud-integration/closure.md; broader tool and platform qualification is not implied.

## Recent Changes

- 148-hermes-hud-integration: all 58 tasks complete for the owner-approved Mac/WSL scope; source version 1.7.0. Live Hermes/provider, browser, process-fault, preservation and existing OpenClaw evidence is in specs/148-hermes-hud-integration/closure.md. Ubuntu 24.04 and native Windows OpenClaw remain explicitly unverified. Hermes n2n/iN2N federation is separate spec 149.

### Spec151 implementation notes

The extension now has local source-development cards/forms, testbed YAML/JSON/CSV management, scoped MCP configuration/setup and native-bound security controls. See specs/151-extension-experience/verification.md for actual evidence and platform limits. Distribution remains held by the owner. DefenseClaw's current connector-scoped rules and revision-aware config writer differ from historical `workspace/skills/defenseclaw-ops/SKILL.md` source-scoping examples: capability-probe the installed CLI; do not infer an MCP-only policy scope from `--source`. OpenShell lacks an atomic revision precondition; coordinate external writers and never claim universal blocking from one removed allow rule.

Spec151 repository merge was explicitly authorized on2026-10-11 after local completion. Commit/push/PR/merge may proceed; packaging, deployment and release/Marketplace publication remain held.

Spec152 production release was explicitly authorized on 2026-10-16 after the WSL inspection. Fetch/commit/PR/merge, completed-branch cleanup and production publication may proceed with verification. Historical release holds for Spec152 are superseded.

Spec155 production publication was explicitly authorized on 2026-10-25 after Mac reconciliation. Commit/PR/merge, versioned source and Marketplace publication, completed-branch cleanup and return to main may proceed. This supersedes earlier Spec155 source-only holds. The release retains T048 and overall 49/50 qualification; six WSL service-manager failures, genuine remote-editor acceptance and documented fixture limits remain visible. Existing installations and provider/model/device operations remain outside release scope. See specs/155-border-channel-setup/release-verification.md.

Spec160 release authorization (2026-10-30): the owner requested versioned source and touched-extension publication, README/community notes, commit/push/PR/merge, completed-branch cleanup and return to main. Earlier Spec160 source-only publication holds are superseded. The two-part modern_website writeup remains staged as drafts; no website deployment or existing-runtime upgrade is requested. Preserve all recorded qualification limits.

Spec162 NetConverter release was explicitly authorized on 2026-11-01: reconcile upstream, publish the versioned source and touched extension, PR/merge and return to main. Source 1.18.0 combines this feature with upstream 1.17.1; extension is 1.5.0. This supersedes the earlier unpublished source milestone hold. The website article remains a staged draft, and the leadership/community messages remain unsent. Existing running lab/Risk installations are not upgraded. See specs/162-netconverterai/release-verification.md for exact scope and qualification limits.
