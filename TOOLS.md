# TOOLS.md — Local Infrastructure Notes

Skills define *how* tools work. This file is for *your* specifics — the environment details that are unique to your deployment.

## Network Devices

Devices are defined in `testbed/testbed.yaml`. Update that file with your SSH-accessible Cisco devices.

```
### Example Device Map
- R1 → 10.1.1.1, Core Router, IOS-XE 17.9
- R2 → 10.1.1.2, Distribution Router, IOS-XE 17.9
- SW1 → 10.1.2.1, Access Switch, IOS-XE 17.9
- SW2 → 10.1.2.2, Access Switch, IOS-XE 17.9
```

## Platform Credentials

All credentials are in `~/.openclaw/.env`. Never put credentials in skill files or this document.

```
### Batfish Configuration Analysis (reference only — actual values in .env)
- Batfish Host        → BATFISH_HOST (default: localhost)
- Batfish Port        → BATFISH_PORT (default: 9997)
- Batfish Network     → BATFISH_NETWORK (default: netclaw)
- Docker Container    → batfish/batfish (ports 9997, 9996)

### Connection Details (reference only — actual values in .env)
- pyATS Testbed       → PYATS_TESTBED_PATH
- NetBox              → NETBOX_URL, NETBOX_TOKEN
- ServiceNow          → SERVICENOW_INSTANCE_URL, SERVICENOW_USERNAME, SERVICENOW_PASSWORD
- Cisco APIC          → APIC_URL, APIC_USERNAME, APIC_PASSWORD
- Cisco ISE           → ISE_BASE, ISE_USERNAME, ISE_PASSWORD
- NVD API             → NVD_API_KEY
- F5 BIG-IP           → F5_IP_ADDRESS, F5_AUTH_STRING
- Catalyst Center     → CCC_HOST, CCC_USER, CCC_PWD
- Microsoft Graph     → AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
- SuzieQ              → SUZIEQ_API_URL, SUZIEQ_API_KEY
- gNMI Telemetry      → GNMI_TARGETS (JSON), GNMI_TLS_CA_CERT, GNMI_TLS_CLIENT_CERT, GNMI_TLS_CLIENT_KEY
- Azure Network MCP   → AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_SUBSCRIPTION_ID
- Canvas/A2UI Viz     → No new credentials (uses existing MCP server connections)
- Token Optimization  → ANTHROPIC_API_KEY (reused), NETCLAW_TOKEN_PRICING_OVERRIDE (optional)
- GitLab MCP          → GITLAB_PERSONAL_ACCESS_TOKEN, GITLAB_API_URL (default: gitlab.com)
- Jenkins MCP         → JENKINS_URL, JENKINS_AUTH_BASE64 (remote HTTP, Basic Auth)
- Claroty xDome MCP   → CLAROTY_API_URL (default: https://api.medigate.io), CLAROTY_API_TOKEN, CLAROTY_VERIFY_SSL, CLAROTY_TIMEOUT, CLAROTY_RATE_LIMIT_PER_MIN (default: 2000)
- Twitter MCP         → TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET, TWITTER_HEARTBEAT_ENABLED (default: false)
```

## GitLab MCP Server

The GitLab MCP server (`@zereight/mcp-gitlab`) provides 98+ tools for GitLab operations via stdio transport:
- **Issues**: list_issues, get_issue, create_issue, update_issue, add_issue_comment, list_issue_comments
- **Merge Requests**: list_merge_requests, get_merge_request, create_merge_request, update_merge_request, merge_merge_request, add_merge_request_comment
- **Pipelines**: list_pipelines, get_pipeline, get_pipeline_jobs, get_pipeline_job_log, create_pipeline, retry_pipeline, cancel_pipeline
- **Repository**: list_repository_tree, get_file_content, list_commits, get_commit, compare_branches
- **Projects**: list_projects, get_project, search_projects
- **Labels**: list_labels, create_label, update_label, delete_label
- **Milestones**: list_milestones, create_milestone, update_milestone
- **Releases**: list_releases, get_release, create_release
- **Wiki**: list_wiki_pages, get_wiki_page, create_wiki_page, update_wiki_page, delete_wiki_page
- Supports gitlab.com and self-hosted instances via `GITLAB_API_URL`
- Read-only mode available via `GITLAB_READ_ONLY_MODE=true`

## Jenkins MCP Server

The Jenkins MCP server (official Jenkins plugin) provides 16 tools via Streamable HTTP transport:
- **Job Management**: getJob, getJobs, triggerBuild, getQueueItem
- **Build Operations**: getBuild, updateBuild, getBuildLog, searchBuildLog
- **SCM Integration**: getJobScm, getBuildScm, getBuildChangeSets, findJobsWithScmUrl
- **System**: whoAmI, getStatus
- **Pipeline**: getPipelineRuns, getPipelineRunLog
- Remote HTTP server running inside Jenkins (Streamable HTTP at `/mcp-server/mcp`)
- Auth: HTTP Basic with Jenkins API token (Base64-encoded username:token)
- Requires Jenkins 2.533+ with MCP Server plugin v0.158+

## Atlassian MCP Server

The Atlassian MCP server (community mcp-atlassian by sooperset) provides 72 tools via stdio transport:
- **Jira Issues**: jira_search, jira_get_issue, jira_create_issue, jira_update_issue, jira_delete_issue, jira_add_comment, jira_batch_create_issues
- **Jira Transitions**: jira_get_transitions, jira_transition_issue
- **Jira Projects/Fields**: jira_get_projects, jira_get_project, jira_get_fields, jira_get_issue_types
- **Jira Links**: jira_link_issues, jira_get_issue_links, jira_get_link_types
- **Confluence Pages**: confluence_search, confluence_get_page, confluence_create_page, confluence_update_page, confluence_delete_page
- **Confluence Comments**: confluence_get_page_comments, confluence_add_comment
- **Confluence Spaces**: confluence_get_spaces, confluence_get_space
- Supports Atlassian Cloud and Server/Data Center deployments
- Auth: API token (Cloud) or Personal Access Token (Server/DC)
- Runs via `uvx mcp-atlassian`

## Token Optimization Infrastructure

The `netclaw_tokens` shared library (`src/netclaw_tokens/`) provides token counting, TOON serialization, and cost tracking:
- **counter.py** — Token counting via Anthropic `count_tokens()` API with `len/4` fallback
- **toon_serializer.py** — TOON format serialization for MCP responses (40-60% savings on tabular data)
- **cost_calculator.py** — Model-aware pricing: Opus ($5/$25), Sonnet ($3/$15), Haiku ($1/$5) per 1M tokens
- **session_ledger.py** — Thread-safe cumulative session tracking with per-tool breakdown
- **footer.py** — Mandatory token/cost footer formatter for every interaction
- **toon_wrapper.py** — TOON conversion wrapper for community/remote MCP servers
- Pricing override via `NETCLAW_TOKEN_PRICING_OVERRIDE` env var (JSON format)
- Prompt caching discount: 90% off cached input tokens

## gNMI Infrastructure

The gNMI MCP server provides 10 tools for streaming telemetry and model-driven configuration:
- **gnmi_get** / **gnmi_set** / **gnmi_subscribe** / **gnmi_unsubscribe** / **gnmi_get_subscriptions** / **gnmi_get_subscription_updates** / **gnmi_capabilities** / **gnmi_browse_yang_paths** / **gnmi_compare_with_cli** / **gnmi_list_targets**
- Supported vendors: Cisco IOS-XR (port 57400), Juniper (32767), Arista (6030), Nokia SR OS (57400)
- YANG models: OpenConfig and vendor-native
- TLS mandatory, mTLS supported, max 50 concurrent subscriptions

## Slack Integration

```
### Channels
- #netclaw-alerts     → P1/P2 critical alerts
- #netclaw-reports    → Scheduled health reports, audit results
- #netclaw-general    → General queries, P3/P4 notifications
- #incidents          → Active incident threads
```

## Microsoft Teams Integration

```
### Teams Channels (if using Microsoft Graph for Teams delivery)
- #netclaw-alerts     → P1/P2 critical alerts, CVE exposure
- #netclaw-reports    → Health reports, audit results, reconciliation
- #netclaw-changes    → Change request updates, completion notices
- #network-general    → P3/P4 notifications, topology updates

### SharePoint Sites
- Network Engineering → Topology diagrams, audit reports, config backups
```

## SSH Access

```
### Jump Hosts / Bastion
- (your bastion host, if applicable)

### Console Servers
- (your console server, if applicable)
```

## Site Information

```
### Sites
- Site-A → Primary data center
- Site-B → DR site
- Lab    → Non-production test environment (relaxed change control)
```

## Memory MCP Server (NetClaw Native)

10 MCP tools for hybrid persistent memory combining structured storage, semantic search, and entity graphs:
- **Facts**: `memory_record_fact`, `memory_get_facts`, `memory_invalidate`, `memory_timeline` — temporal key-value storage with automatic supersession
- **Semantic Search**: `memory_store_session`, `memory_recall` — ChromaDB + sentence-transformers for fuzzy session recall
- **Decisions**: `memory_record_decision`, `memory_get_decisions` — audit trail with context, rationale, and CR references
- **Graph Links**: `memory_link_entities`, `memory_query_graph` — entity relationships (peers_with, depends_on, connects_to)
- Transport: stdio, Python 3.11+, uvx package, fully offline
- Data: `~/.openclaw/memory/` (SQLite + ChromaDB)
- No credentials required

## MemPalace AI Memory

19 MCP tools for persistent, structured, local-only AI memory across sessions ([source](https://github.com/milla-jovovich/mempalace)):
- **Palace**: status, wings, rooms, taxonomy, search, duplicates, AAAK spec, add/delete drawers
- **Knowledge Graph**: entity query, add/invalidate temporal triples, timeline, stats
- **Navigation**: room traversal, cross-wing tunnels, graph stats
- **Agent Diary**: write/read specialist agent journals (AAAK-compressed)
- Transport: stdio, Python 3.9+, no credentials, fully offline
- `MEMPALACE_MCP_SCRIPT` → cloned repo `mcp_server.py`

## Twitter MCP Server (NetClaw Native)

16 MCP tools for Twitter/X integration — bidirectional (pay-as-you-go tier) via stdio transport:

**Posting Tools (9):**
- **Posting**: `twitter_post_tweet`, `twitter_post_thread`, `twitter_post_tweet_with_media`, `twitter_delete_tweet`
- **Rate Limits**: `twitter_get_rate_limits` — quota monitoring
- **Heartbeat**: `twitter_generate_heartbeat_content`, `twitter_post_heartbeat` — autonomous CCIE-persona tweets (opt-in)
- **Deduplication**: `twitter_check_duplicate`, `twitter_get_history` — 30-day memory-backed history

**Bidirectional Tools (7):**
- **Mentions**: `twitter_get_mentions` — fetch @mentions, `twitter_classify_mention` — categorize intent
- **Conversation**: `twitter_get_conversation` — thread context for context-aware replies
- **Reply**: `twitter_generate_reply` — CCIE-level draft, `twitter_reply_to_tweet` — post with human approval
- **Tracking**: `twitter_mark_processed` — prevent duplicate handling, `twitter_get_user_history` — interaction memory

- Content guardrails: IPv4/IPv6 sanitization (RFC 5737/3849), MAC/credential/hostname blocking
- Human approval required for all replies (Constitution Principle XIV)
- Spam detection: account age, follower ratio, username patterns, content patterns
- `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`
- `TWITTER_MENTION_POLL_INTERVAL` — polling frequency (default 300s)

## Unreal Engine 5.8 MCP Server

The Unreal Engine 5.8 MCP server is built into UE5.8+ and provides enterprise-grade 3D network topology visualization via HTTP transport. Tool names below are confirmed against a real running UE5 8.0 MCP server (not the originally-assumed names) — see `workspace/skills/ue5-network-viz/SKILL.md` for the full incident history behind these:

- **Tool Search Mode**: `list_toolsets`, `describe_toolset`, `call_tool` — meta-tools for discovering and executing UE5 tools. `call_tool` takes `toolset_name` (full path, e.g. `editor_toolset.toolsets.scene.SceneTools`) and `tool_name` as the **short** method name only (e.g. `add_to_scene_from_class`) — passing the fully-qualified `toolset.method` string as `tool_name` silently returns "Unknown tool" on some builds.
- **`editor_toolset.toolsets.scene.SceneTools`**: `add_to_scene_from_class`, `add_to_scene_from_asset`, `remove_from_scene`, `find_actors`, `load_level`, `get_current_level` — spawn/find/remove device and link actors
- **`editor_toolset.toolsets.actor.ActorTools`**: `set_actor_transform`, `set_label`, `add_tag`, `get_components` — position, label, and tag actors. `set_actor_transform` has been observed to reset omitted fields (e.g. location, when only scale is set) to `(0,0,0)` on some builds despite its own docs claiming otherwise — always pass location + rotation + scale together.
- **`editor_toolset.toolsets.object.ObjectTools`**: `set_properties`, `get_property` — set mesh/material properties on a spawned actor
- **`editor_toolset.toolsets.asset.AssetTools`**: `load_asset`, `find_assets`, `save_assets`, `create_folder` — load basic-shape meshes, manage `/Game/` folders
- **`editor_toolset.toolsets.programmatic.ProgrammaticToolset`**: `execute_tool_script` (`{"script": "<python>"}`) — run a script inside UE5's embedded Python in one MCP round trip instead of one call per actor. **Not universally available**: some UE5 8.0 builds' script sandbox forbids `import unreal` (only stdlib modules allowed), making this batch path unusable — the skill falls back to per-actor calls automatically when this happens. Still used for config/metrics panels and hierarchical zoom (045-ue5-digital-twin); everything else that used to depend on this (interface actors, labels, the legend, status/traffic/trap/incident/ping coloring, camera control) has since moved to the confirmed-real toolsets below, which are plain MCP calls unaffected by the script sandbox.
- **`editor_toolset.toolsets.material_instance.MaterialInstanceTools`**: `create(folder_path, asset_name, parent)`, `set_vector_parameter(instance, name, value)`, `set_scalar_parameter`, `list_parameters`, `set_parent`, `clear_parameters` — create/modify `MaterialInstanceConstant` assets. Confirmed live 2026-07-03: `/Engine/BasicShapes/BasicShapeMaterial` (the material this skill's own primitive meshes already use) exposes a `Color` vector parameter and a `Roughness` scalar — the confirmed-working, non-scripted way to recolor a spawned actor (`actors.apply_color_to_actor_ref()`).
- **`EditorToolset.EditorAppToolset`**: `SetCameraTransform`/`GetCameraTransform`, `FocusOnActors`, `CaptureViewport` (returns a base64 PNG directly), `GetVisibleActors`, `SelectActors`, `WorldPosToScreenCoords` — real, non-scripted viewport/camera control and screenshot capture. `CaptureViewport`'s `annotations` overlay config has the same "marked optional but actually required" schema quirk as elsewhere in this list — pass `captureTransform` and every `annotations` sub-field explicitly (`gridSpacing`/`gridExtent`/`gridHeight`/`maxLabelDistance`/`maxLabels` all `0`, plus a valid `classFilter`) to suppress the grid/label overlay.
- **`ObjectTools.set_properties`/`get_properties` on mesh/material properties (`staticMesh`, `overrideMaterials`) must target the actor's StaticMeshComponent, not the actor itself.** Confirmed live 2026-07-03: setting `staticMesh` on the actor reference silently no-ops (`get_properties` afterward still shows `"None"`); resolving the component first via `ActorTools.get_components` and targeting that works. This had been silently breaking mesh assignment since 044 shipped.
- **The base primitive meshes (`/Engine/BasicShapes/Cube.Cube`, `Sphere.Sphere`, `Cylinder.Cylinder`) are already 100cm (1m) per side/diameter at `scale=1.0`.** This codebase assumed 1cm and used `scale=100` for "1 meter" devices, actually producing 100-meter devices (confirmed via `ActorTools.get_actor_bounds`) — the root cause of most rendering-looks-wrong reports throughout 044/045. Any new mesh-scale constant should be verified against `get_actor_bounds()` on a live build before trusting a comment's stated intent.
- URL: `http://127.0.0.1:8000/mcp` (local-only, loopback). Endpoint only accepts POST — a bare `curl` GET correctly returns HTTP 405, that's the server confirming it's up.
- **045-ue5-digital-twin** extends the base topology renderer into an interactive digital twin: interface-level actors, live traffic/health/SNMP-trap-driven color state, ping/traceroute animation, on-demand config/metrics panels, PagerDuty incident correlation, historical playback, and NetBox/Infrahub-sourced hierarchical zoom — all orchestrated by `workspace/skills/ue5-network-viz/` reusing `snmptrap-mcp`, `gnmi-mcp`, PagerDuty, NetBox, and Infrahub's existing MCP integrations rather than adding new ones. See `workspace/skills/ue5-network-viz/SKILL.md`'s "Digital Twin Capabilities (045)" section for the full command reference.
- Requires: UE5.8+ with MCP plugin enabled (Edit > Plugins > "Unreal MCP")
- Auto-start or manually: `ModelContextProtocol.StartServer` in UE5 console
- `UE5_MCP_URL` → server endpoint (default: `http://127.0.0.1:8000/mcp`)
- Client note: some builds respond over a keep-alive `text/event-stream` even after the real answer has been sent — a client that waits for the full response body to complete (rather than reading the SSE stream line-by-line and stopping at the first complete JSON-RPC object) can hang for the full timeout on an answer that already arrived.

## Sketchfab MCP Server

The Sketchfab MCP server ([gregkop/sketchfab-mcp-server](https://github.com/gregkop/sketchfab-mcp-server), vendored at `mcp-servers/sketchfab-mcp-server/`) provides 3D model search/download for `workspace/skills/threejs-network-viz/`'s optional real-stencil mode (046-threejs-network-viz, User Story 5) — it is not used by any other skill.

- **Tools (3)**: `sketchfab-search` (query/tags/categories/downloadable/limit), `sketchfab-model-details` (full model metadata including license, given a model ID), `sketchfab-download` (format gltf/glb/usdz/source, given a model ID)
- Transport: stdio (Node.js), registered as `sketchfab-mcp` in `config/openclaw.json`
- Requires: `SKETCHFAB_API_KEY` (get one at https://sketchfab.com/settings/password → API Tokens); `SKETCHFAB_USERNAME` is reference/attribution only, not required by the API
- Install: `cd mcp-servers/sketchfab-mcp-server && npm install && npm run build` (produces `build/index.js`, the file `config/openclaw.json` points at)
- **Patched during 046's implementation**: the upstream server's `sketchfab-model-details` tool silently dropped the `license` field from its formatted text output, even though the real Sketchfab API returns it — confirmed live against `https://api.sketchfab.com/v3/models/{uid}`. Without it, `threejs-network-viz/assets.py` has no way to verify a candidate model is actually CC0-licensed before using it. Fixed in `mcp-servers/sketchfab-mcp-server/index.ts`'s `formatModelForDisplay()` (see the "NetClaw patch" comments) and rebuilt. **If this vendored server is ever re-cloned fresh from upstream, this patch must be reapplied and rebuilt before real-stencil mode's license verification will work.**
- Sketchfab's catalog is mixed-license — the `sketchfab-search` tool has no license filter parameter, so every candidate must be individually verified via `sketchfab-model-details` before download (never trust `downloadable: true` alone as a license signal). The real Sketchfab API's CC0 license record has `slug: "cc0"`, `uid: "7c23a1ba438d4306920229c12afcb5f9"` — confirmed live against `GET /v3/licenses`.
- Not every downloadable model has a ready-made glTF/GLB export — `sketchfab-download` silently substitutes a different format (source/gltf/usdz) when the requested `glb` isn't available for that specific model; callers must check the tool's response text for the exact "in glb format." success phrasing rather than assuming success means the requested format was honored.
- In practice, CC0-licensed models specific to network equipment are essentially nonexistent on Sketchfab — confirmed via live searches during development ("router", "server rack", "electronic box" all returned zero or irrelevant CC0 results). Procedural-shape fallback in `threejs-network-viz` is the expected common case, not a rare edge case.

## Claroty xDome MCP Server

The Claroty xDome MCP server provides 21 tools (15 read-only + 6 ITSM-gated writes) for OT / IoT / IoMT visibility via stdio transport:

- **Assets**: `list_devices`, `get_device_details`, `get_device_communication_map`
- **Alerts**: `list_alerts`, `get_alert_with_devices`
- **Vulnerabilities**: `list_vulnerabilities`, `get_vulnerable_devices`
- **Sites & sensors**: `list_sites`, `get_site`, `list_edge_locations`
- **Servers & OT activity**: `list_servers`, `get_server_interfaces`, `list_ot_activity_events`
- **Governance**: `get_audit_log`, `list_organization_zones`
- **Writes (ITSM-gated, CHG\d+ CR required)**: `acknowledge_alert`, `set_vulnerability_relevance`, `set_device_purdue_level`, `set_device_custom_attribute`, `label_alerts`, `assign_alerts`
- Default base URL `https://api.medigate.io`; Bearer token auth; sliding-window rate gate at 2000 req/min matches the xDome upstream cap; lab-mode bypass via `NETCLAW_LAB_MODE=true` (shared with gnmi-mcp).
- Edge sensor lifecycle, site CRUD, and organisation policy CRUD are deferred to a future spec — see `specs/035-claroty-mcp/research.md`.

## Notes

- Add whatever helps NetClaw do its job — device nicknames, maintenance windows, ISP circuit IDs, TAC case numbers, anything environment-specific.
- This file is yours. Skills are shared. Keeping them apart means you can update skills without losing your notes.
