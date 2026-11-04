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
- Python 3.12 isolated protocol/n2n runtime; Python 3.10+ installer; existing Bash and HUD JavaScript. + Existing asyncio/federation stack; pyOpenSSL 26.4.0, cryptography 50.0.2, service-identity 26.1.0. Preserve separate certificate-helper environment. No new MCP server or web framework. (168-ngrok-transport-contract)
- Private installation-owned schema1/ngrok and schema2/direct-or-ngrok registries, atomic revision updates and explicit prior-revision recovery; owned daemon/ngrok process records. Direct GCP transport-only pilot and owner-selected open read-only lab HUD; users/SSO/RBAC remain R15–R17. No tokens in registry/bundles. (168-ngrok-transport-contract)
- Spec171 planned: isolated Python 3.12; existing Node 24.19/React 18 HUD, cryptography 50/P-256, SQLite, asyncio and MCP. (171-execution-parity)
- Spec171 planned: additive federation.db tables, private artifacts and owner authority, existing GAIT audit. (171-execution-parity)
- Python3.12 federation/native tools; Python3.10+ role/IaC helpers; existing JavaScript ESM/React18 and qualified Node24.19. + Existing strict TLS/federation, FastMCP/MCP, SQLite, Express/React/Vite build; OpenTofu1.13.2 Google8.9.0, Caddy2.11.7. No new MCP server or UI framework. (172-gcp-hybrid-border)
- Selected private homes/SQLite authority and ledger; one-device frozen profiles; external0700 private cloud state/evidence; bounded installation-scoped browser reference storage. (172-gcp-hybrid-border)
- Python3.12 federation/MCP; Python3.10+ host helpers; existing Node24.19/React18 HUD. + Existing FastMCP/MCP, requests, P256, SQLite, Docker, OpenClaw2026.7.1-2, strict iN2N, OpenTofu1.13.2/Google8.9.0, Caddy2.11.7. Existing NetBox/subnet MCPs; no new server/framework. (173-gcp-cloud-member)
- Private SQLite/GAIT and immutable profiles; external0700 state/evidence and0600 secrets; bounded browser identifiers only. (173-gcp-cloud-member)
- existing TypeScript5.9/Node24.19; Dart/Flutter current project toolchain; Python3.12 federation. + VS Code APIs, Node HTTPS, existing Flutter HTTP and secure storage, existing Express owner service. (174-cloud-client-integration)
- non-secret profile/reference state, native secure sessions, memory-only CSRF/tickets. (174-cloud-client-integration)

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

### Spec168/R01 closure (2026-11-01)

The owner fully delegated the isolated R01 cloud/DNS/HTTPS activation, relocation,
full open lab HUD and scoped Anthropic Sonnet demonstration. R01 is40/40 for that
amended scope; stop here. R02/R03, source commit/push/release, existing-runtime
upgrade and device operations are not authorized. Live lab URL and correlated
cloud-to-on-prem evidence: specs/168-ngrok-transport-contract/verification.md and
onprem-answer-evidence.md. Cloud Border and fresh Mac subnet member use
Sonnet4.6; the member is not the existing pyATS installation. Actual browser Chat,
RAG indexing/retrieval, cited Canvas handoff/answer, unchanged-key relocation,
DNS/trusted HTTPS and no-drift checks passed. Optional ngrok stays supported;
live ngrok and the explicitly untested platforms remain unqualified. The full
public lab exception does not implement users/SSO/RBAC (R15–R17). Private operator
access stays IAP; no raw admin/device-write API is published. Preserve the
authoritative private pilot.tfstate and active homes; never replay old activation
plans or initial secret payloads. VM stops December1; disk/IP costs remain until
separately reviewed teardown. GAIT and private receipts retain the full trail.

## Roadmap source integration and release hold — 2026-11-02

The owner authorized committing, pushing and merging the completed R01 source into
main, with a short maintainer summary. This supersedes R01's earlier source-merge
hold only. The issue310 roadmap work remains unreleased until the entire roadmap
is complete, including user identities, SSO and RBAC (R15–R17) and closure (R20).
Do not bump a version, create a release/tag, publish a package/Marketplace build,
publish a blog/changelog/announcement, or promote general cloud deployment for
this work. R01 transport proof is not authorization to deploy a cloud Border
without user controls. Keep technical specs/evidence for maintainers; rollout
copy is deferred under specs/168-ngrok-transport-contract/deferred-docs/ and absent
from the public README, setup wizard and general installation guides. Existing
owner pilot authorization is a bounded exception, not a user deployment recipe.
R01 integrated on upstream 1.18.1 without a version increment. Subsequent upstream
fixes #317/spec169 and #318/spec170 advance source to 1.18.3; extension 1.5.0 is
unchanged. These maintenance fixes do not release or qualify the cloud roadmap.
Next roadmap brief is R02 execution parity, expected next available spec 171
(recheck at kickoff; 169 and 170 are occupied by those upstream fixes);
it is not started by this integration request. No R02 cloud/device operation is
authorized here. Keep the original R01 directory name despite the parallel
upstream168-openclaw-2026-10-compat feature; cite R01/full path to distinguish them.

## R02–R05 work authorization — 2026-11-02

The owner subsequently authorized driving R02–R05 to completion with a
coordinator and three parallel agents, using separate worktrees. This supersedes
the earlier R01-only stop and R02 source-work hold. Human roadmap acceptance
gates and exact cloud-resource/spend reviews remain. Total GCP lab spend must
not exceed $100/month; use CAD100 conservatively, including R01, pending any
owner correction. Budget alerts are not hard spending caps. Optional bounded
implementation/test/review passes are capped at five total across R02–R05.
The entire-roadmap release, version and public rollout hold remains in force.
Spec171 implements R02; R03 cannot begin before its human evidence gate.

### R02/Spec171 technical acceptance — 2026-11-02

Source8c178ff8 passed both actual protected OpenClaw/Hermes Sonnet reads through
fresh Mac/Docker members: one R1show-version, zero setup commands, signed results,
durable ACK, attributable GAIT and no-repeat restart recovery. Independent review
passes. All36 tasks are complete; the owner accepted T036 on 2026-11-02 and
authorized R03 planning. Exact cloud-resource/spend review and later human gates
remain. See specs/171-execution-parity/verification.md, parity-matrix.md and resume.md.
Two of the five bounded implementation passes were used. The earlier unknown SSH
operation and authentic reads with an implicit Unicon setup probe remain retained
with their limitations, never replayed. The corrected native policy is narrowly
pinned to IOS-XE/IOL and the qualified Mac dependencies. No arbitrary provider,
cloud, other-plugin, write or multi-user qualification is implied. Source1.18.3
and extension1.5.0 unchanged; entire-roadmap release hold remains. No R03 resource
or existing R01 runtime was changed.

### R03/Spec172 source checkpoint — 2026-11-02

The owner requested driving R03 to100%. Source is integrated on
`172-gcp-hybrid-border`: immutable four-device selection, production owner HUD,
strict control-only Border role/posture, one-use protected enrollment and isolated
GCP IaC/host controls. Combined protected/posture464 tests and fullHUD453 tests
pass; actual LinuxAMD64 dependency extraction is verified offline. Four lab
endpoint/host-key diagnostic proofs are private, with explicit console versus
historical SSH-pin provenance. No actual R03 cloud apply/activation/provider read,
DNS change or R01 runtime change has occurred. R03 is not100% or human accepted.
Current billing/total CAD100 gate, exact cloud/runtime delegation, actual GCP
controls/HTTPS/four protected reads/recovery and reviewed teardown remain open.
The optional exact R01 stop in Spec172 cost-bound-review.md is awaiting owner
choice; do not execute it without delegation. Source1.18.3/extension1.5.0 and
roadmap release hold remain unchanged. Pass3 source/offline preparation is complete;
actual execution remains gated. No automatic Ralph hook. Exact foundation apply
delegation was requested and is pending; no elapsed time supplies approval.
See Spec172 verification.md/resume.md and private roadmap-r03-20261102 evidence.

### R03 activation delegation — 2026-11-03

The owner explicitly said to do what is needed, push forward using the stated
GCP credit, stop treating money as the blocker, and clean up owned resources so
charges do not continue. This supersedes the Nov2 billing/approval holds for the
reviewed isolated R03 foundation/runtime/DNS/four-read/verification/cleanup scope.
Do not repeat those permission requests. Preserve exact plans, bounded safeguards,
unknown outcomes and audit evidence; the credit is not a spend target. Cleanup
follows evidence export and includes billable residues. R01/R02 work and unrelated
runtimes stay preserved. Release/version/public rollout holds and R04 human gate
remain. See specs/172-gcp-hybrid-border/activation-delegation.md.


### R03 technical qualification and retirement — 2026-11-03

R03 implementation, actual GCP/on-prem qualification and reviewed cleanup are
complete;35/36 tasks closed. T036 memory/GAIT is recorded but human acceptance
remains pending before R04. Four browser-approved R1/R2/SW1/SW2 `show version`
reads returned IOS17.18.2 with one command/two OpenClaw-Sonnet provider calls each,
signed results, durable ACKs and unchanged effects after loss/restart recovery.
62 browser/auth checks and actual cloud confinement/IAM/network checks passed.
See Spec172 verification.md for narrow platform/provider scope and retained failures.
All13 R03 cloud resources, owned DNS and temporary OS Login key are removed;
actual inventories found zero owned billable residues. Local workers and owned
containers/networks are retired; private homes/current-state archive remain.
R01 state/DNS and running pilot are unchanged, with existing costs retained.
Never replay spent R03 plans, enrollment or first-create state; use the private
current-state preservation record only as evidence, not an activation payload.
Source1.18.3/extension1.5.0 and the entire-roadmap release hold remain unchanged.


### R02/R03 source integration and R03 acceptance — 2026-11-03

After receiving the completed R03 technical/cleanup handoff, the owner requested
commit, PR, quiet merge and return to main, plus a small maintainer blurb. This
accepts the completed R03 scope and closes T036 (36/36); no new R04/cloud/device
work is implied. Commit/push/PR/merge of completed R02/R03 source is authorized.
Reconcile upstream #321 failure reporting and retain its source1.18.4 version;
extension1.5.0 remains unchanged, with no additional roadmap bump or publication.
The complete-roadmap release hold through R20 is still in force. Keep historical
`171-execution-parity` (R02) and upstream `171-skill-failure-reporting` distinct by
full path; never rename historical specs to hide the collision. R03 live evidence
remains tied to its frozen tested source, not a claim that merged source was redeployed.
See specs/172-gcp-hybrid-border/source-integration.md for verification and PR outcome.

### R04 autonomous execution — 2026-11-03

Owner requested R04 to100%, supplied the existing public NetBox demo source and
private credential, required actual NetClaw member/NetBox skills/MCP, then delegated
autonomous completion. Use fresh isolated cloud Border/member and separate subnet,
read-only device/prefix/subnet workloads, finite bounds, real evidence and full
owned cleanup. Existing source guard pins select Sonnet4.6 instead of historical
Haiku default. Do not repeat delegated permissions. Preserve R01, retired R03
archives and source1.18.4/extension1.5.0; no release/public rollout or R05.
Pass4 is R04; see specs/173-gcp-cloud-member/activation-delegation.md.

### R04a and continuing client integration — 2026-11-03

The owner inserted R04a between accepted R04 and R05 to catch up VS Code cloud
Border connectivity and affected Mobile flows. See
docs/roadmap/issue-310/briefs/R04a-cloud-border-client-integration.md.
Every subsequent stage must separately assess, implement where affected and
verify VS Code and Mobile integration under roadmap G12/G13; record evidence for
no-impact decisions instead of silently deferring client work to R20. R04a is
planned, not started by this documentation amendment. Preserve current R04
qualification/cleanup, human gates, existing milestone IDs and release holds.


### R04 technical qualification and retirement — 2026-11-03

R04/Spec173 implementation, actual cloud-member qualification and owned cleanup
are complete. The existing NetClaw NetBox skill/MCP read the observed demo device
and prefix; the existing subnet tool calculated192.0.2.0/26. Three separate
browser approvals produced three native MCP calls, six guarded Sonnet4.6 provider
calls, signed results and durable ACKs. Actual member loss/restart preserved the
same authorities/results/effect counts without replay. Two earlier attempts remain
unknown with zero provider/MCP calls and their original witnesses. Driver and
archive failures and all narrow qualification limits remain in verification.md.

All24 owned R04 cloud resources, DNS and temporary OS Login access are removed.
Actual12-category inventory found zero owned residues; R01's checked resources,
state, DNS, HTTPS and shared budgets remain preserved, with R01 costs retained.
Private current-state archives and the1423-file frozen export are local under
~/.local/share/netclaw/roadmap-r04-20261103/. They contain private authority and
are evidence-only, never activation payloads. Do not replay spent R04 plans,
enrollment or attempts, or reconnect to its retired hostname/IPs.

Human acceptance remains required before R04a, then R05. Pass4 of five bounded
R02–R05 implementation passes is complete; no automatic loop. Source1.18.4 and
extension1.5.0 are unchanged, with the entire-roadmap release/public rollout hold
through R20 intact. No R04a, later roadmap, existing-runtime upgrade, release or
external announcement was performed. See specs/173-gcp-cloud-member/verification.md
and resume.md. This does not self-record the owner's acceptance.


### R04 acceptance and source integration — 2026-11-03

After the completed R04 qualification/retirement handoff, the owner explicitly
requested full commit, PR, merge, completed-branch deletion, return to main and a
short R04/R04a/R05 writeup. This accepts the completed R04 scope (33/33) and
supersedes its pending acceptance/source-integration gate. Preserve all frozen
live evidence and original qualification limits; merged source is not a claim
of redeployment. Include the owner's R04a and continuing VS Code/Mobile roadmap
amendment in this integration. R04a is next, then R05; neither starts here.
Source1.18.4/extension1.5.0 remain unchanged. No version, release, Marketplace,
blog or public rollout authorization; the entire-roadmap hold through R20 remains.
See specs/173-gcp-cloud-member/source-integration.md.

### R04a client integration authorization — 2026-11-03

The owner subsequently instructed driving R04a efficiently to completion. This
starts Spec174 on `174-cloud-client-integration`; R04 is already accepted and
merged. The coordinator and separate VS Code/Mobile lanes implement explicit
cloud-owner clients using the existing protected HTTPS authority, exact review
and no-repeat recovery. Fresh finite qualification and owned cleanup remain
scoped to the R04a client evidence; never replay retired R04 state, identities,
enrollment or workloads. Preserve R01 and existing owner clients/runtimes.
Four optional roadmap passes were used; this is pass5 with no automatic extra
improvement loop. Required verification/fixes are part of this pass. Actual
editor/native Mobile evidence and human review precede R05; inventory, source
tests and simulator execution cannot imply physical-device qualification.
Source1.18.4/extension1.5.0/Mobile1.0.3+6 and the R20 publication hold remain.

### R04a technical qualification and retirement — 2026-11-03

Spec174 technical work is complete:16/17 tasks, with human evidence acceptance
still required before R05. Actual Mac VS Code1.109.0 and native iOS26.5 simulator
cloud-owner reads each produced one NetBox MCP call, two guarded Sonnet4.6 calls,
a signed result and durable ACK. Actual process restarts recovered the same
references/results with GETs only and no repeated effects. Three unapproved
original reviews remain owner-denied with no execution. Physical iPhone remains
unqualified because installation was refused while locked. The final narrow Mobile
definite-unsubmitted recovery fix has20 focused tests and independent review;
successful live evidence retains its earlier source binding.

All24 fresh R04a cloud resources, owned DNS and temporary OS Login key are removed;
12 actual residue categories found none. R01's checked resources/state/DNS/HTTPS
and shared budgets remain preserved, with its existing costs retained. The315-file
private frozen export is evidence only, excludes private identity keys and selected
integration credentials, and must never be replayed as activation state. Never
reconnect to retired R04a addresses or replay its plans/enrollment/approvals.
See specs/174-cloud-client-integration/verification.md and resume.md for exact
platform/source, preservation and failure limits. Pass5 is complete, with no extra
optional loop. No R05, version change, release, public rollout or existing-runtime
upgrade was performed. This does not record the owner's acceptance.

### R04a owner-delivery correction — 2026-11-04

The owner rejected the disposable-only completion as failing the actual objective:
his installed VS Code must connect to a persistent usable GCP Border. He explicitly
authorized rebuilding the GCP NetClaw Border image if necessary and designated this
as non-live development/build-time infrastructure. Reopen R04a. This supersedes
the earlier no-existing-runtime-upgrade restriction for the scoped GCP pilot and
necessary private local client installation; it does not authorize public release,
Marketplace publication, unrelated runtimes, device writes or R05. Retain concrete
baseline/rollback, review exact resource changes and preserve the existing trial
expiry/spend bounds. Leave the intended owner deployment and client profile usable;
retire only disposable test resources. Prior isolated evidence remains historical,
not owner-delivery acceptance. No new optional improvement loop is started: this
is required correction of the unfinished R04a objective.


### R04a connection-flow and authentication correction — 2026-11-04

The owner explicitly rejected the premature authentication requirement: no login,
one-use tickets, owner sessions or another auth scheme in this current development
pilot. Authentication belongs to the later roadmap steps and will use a different
design. The exact requested VS Code flow is **Add Connection → Local / Cloud →
Cloud → Name → URL → Connected**. Do not ask for installation ID or an access-mode
choice; discover and pin installation identity over verified HTTPS. Selecting the
cloud profile must open a useful view directly and must not flicker/reconnect an
already-selected profile. This supersedes earlier R04a owner-sign-in assumptions
and requirements for this pilot. No hidden auto-login/ticket mechanism may be
substituted. Preserve exact read scope/review, no-repeat recovery, private member
credentials, TLS/endpoint identity and truthful unauthenticated lab attribution.
Existing approval/history must not be relabeled or silently cleared. Keep later
identity/SSO/RBAC and public rollout deferred; no general deployment/release is
authorized. Owner supplied a replacement NetBox key privately; use it instead of
the temporary demo credential created during diagnosis, and never put it in source
or output.


### R04a retained runtime checkpoint — 2026-11-04

The explicit no-user-auth Border/member migrations and corrected private extension
installation are complete. Same Montréal URL/VM, December1stop, original identities
and failed403 authority are preserved. Cloud public readiness0e1ef7c3 and member
verification7e24664d pass. Owner replacement key is installed only on the member;
source1.18.4/extension1.5.0/Mobile1.0.3+6 unchanged, no public release.

Actual native completion is blocked by the Mac lock screen. The owner has been
asked to unlock normally; never request a password or send blind UI input. After
unlock, use only extension-host restart (preserve CodePID924/window/terminal), exact
Name+URL connection and stable profile selection, then same original5004 recovery
under GAITb21011f2. New distinctprefix1 approval requires full root review; signed
success/ACK plus GET-only restart/effect comparison remain required before100%.
Original apply and completion claims are spent; never rerun them or restore oldDB.
See specs/174-cloud-client-integration/resume.md for exact remaining sequence.
Existing Mobile QR needs proposedR04b HUD/WSS/protectedoperations; preserve scanner
and devicekeys, no replacement manualwizard or userauth. Human acceptance/R05 and
roadmap release holds remain. This checkpoint is not a completion or acceptance claim.


### R04a actual operating-interface correction — November 4

The owner explicitly rejected the JSON-only connection landing and narrow
read-operation client: make the normal NetClaw VS Code interface work against
the cloud Border after Name + URL, with no user authentication. This supersedes
R04a's earlier operations-only UI acceptance assumptions. Do not count a connected
badge, diagnostic document, menu presence or isolated read as completion, and do
not build another operations-only substitute. Stop redundant verification of that
rejected target. Reuse normal Overview/Chat/Canvas/RAG/estate/integration views and
the existing full HUD/runtime handlers through verified HTTPS remote capabilities.
Local extension-host filesystem/install/lifecycle actions remain local. Preserve
current b164 installation, protected authority and failed403 history while composing
any separate conversation/runtime services; do not silently restore old f03c authority
or legacy device execution. Needed owner-pilot development runtime updates remain
delegated; no additional user sign-in, release/version/public rollout or R05.
Native Name+URL/no-login/stableclick checks passed before this correction; initial
extension activation passed with CodePID924 preserved. Original5004 reconciliation
was NOT submitted. Actual full operating-interface qualification remains open.

### R04a live workspace checkpoint — November4, final recovery

The normal cloud workspace is now deployed and active in the owner's original
VS Code window. Private VSIX3fa30a37 (clientcebf8109/root7856e856) preserves profiles,
settings and other extensions. Actual normal Overview, Chat, RAG retrieval/context
review and cited Canvas passed; the sole342-byte upload used production HudClient
after native file-picker automation failed before submission. Five public docs and
gateway logs were repaired; all advertised read panels and real Sonnet usage passed.
No user authentication was introduced. Current cloud gateway56278/HUD56057/edge55882
and protected federation51900/Caddy50879 remain running; sourcee68+7856delta, same
b164 identity, authority and December1stop. No new cloud resources or publication.

Original5004 is signedFAILED/native_netbox_http_403 with durableACK and unchanged
1provider/1MCP/1GET403. Authoritative settlement is17:36:49UTC, initiating caller
unestablished; earlier summaries of an unresolved operation were stale. Current
native Recover GET repeated no action. Fresh prefix9c380fdc was approved once and
succeeded with2guardedprovider/inference calls,1nativeNetBoxMCP/1HTTP200GET, signed
resultbae4366c and durableACK; both member and Border pre-recovery collectors pass.

Final correctly targeted extension-host restart39253/39255→57203/57208 and existing
profile reconnect succeeded; mainCode924, both references and completed Chat/Canvas
files are unchanged. macOS locked before final operation selection. The owner has
been asked to unlock normally and leave the original netclaw window visible. After
unlock finish ONLY same-prefix GET recovery and normal Overview, then run the
existing recovered-phase collectors. No more restart, preparation, approval,
reconciliation, upload, search or provider prompt is needed. Do not claim the final
native lookup passed until it does. See specs/174-cloud-client-integration/resume.md.
Human acceptance beforeR05, proposed Mobile QR R04b and R20 release holds remain.

### R04a final owner verification — November4

The owner authorized the last check after unlocking. Actual native post-restart
status at20:03:24UTC displayed the same prefix9c380fdc completed, signed result
verified and delivery acknowledged; normal connected GCP Overview is left visible
(20:04:31UTC). MainCode924/hosts57203/57208 remain unchanged; all five persisted
NetClaw files, both references/decision markers and completed Chat/Canvas match
their pre-restart hashes. Native final receipt1e9c306c retains the exact-click
attribution limit: the picker was selected between snapshots; the source path is
GET but no raw HTTP trace is claimed. No extra lookup was forced.

Root's member recovered-phase collector verified identical approval/result/ACK,
unchanged original403 evidence and new-prefix2provider/2inference/1MCP/1HTTP200GET.
Border comparisonf52c7fc8 verifies every retained field unchanged except observation
timestamp, including both authorities/results/ACKs, GAIT, counters and source pins.
All21 technical R04a tasks are complete; T017 remains the separate human acceptance
gate beforeR05. Do not resume old pending-lookup instructions or run another
workload/restart to improve evidence. Keep the intended pilot/member running within
its December1scope. Mobile QR is proposedR04b; no R05, version bump, publication or
general rollout occurred. Final handoff is specs/174-cloud-client-integration/resume.md.

### R04a acceptance and production extension update — November4

After the completed native verification handoff, the owner requested commit, PR,
quiet merge, return to main and production VS Code packaging/publication. This
accepts R04a (22/22 including T017) and supersedes the earlier extension version
and Marketplace hold for this scoped update. Preserve upstream source1.18.5 from
PR325 and both distinct Spec174 directories. Extension1.6.0 targets the verified
Marketplace1.5.0 baseline; publish only the checked archive with recorded source
and digest. Verify PR checks, merge and public artifact availability.

The broader source release/tag, blog, external announcement and general cloud
deployment holds throughR20 remain. Do not redeploy the retained pilot or restart
the owner's editor, repeat provider/device operations, or start R04b/R05 during
this integration/publication task. R04b cloud HUD Mobile QR enrollment is the
recommended next scoped feature, followed by R05. No new user-authentication scheme
belongs in either client correction; users/SSO/RBAC stay R15–R17. See
specs/174-cloud-client-integration/release-verification.md for actual release evidence.
