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
- Chrome DevTools MCP  → No credentials, no env vars at all (config is CLI flags only; auth is via manual browser sign-in)
- Token Optimization  → ANTHROPIC_API_KEY (reused), NETCLAW_TOKEN_PRICING_OVERRIDE (optional)
- GitLab MCP          → GITLAB_PERSONAL_ACCESS_TOKEN, GITLAB_API_URL (default: gitlab.com)
- Jenkins MCP         → JENKINS_URL, JENKINS_AUTH_BASE64 (remote HTTP, Basic Auth)
- Auvik              → AUVIK_USERNAME, AUVIK_API_KEY, AUVIK_BASE_URL (optional)
- HaloPSA / HaloITSM  → HALO_BASE_URL, HALO_CLIENT_ID, HALO_CLIENT_SECRET, HALO_TENANT, HALO_SCOPE (OAuth2 client-credentials)
- Claroty xDome MCP   → CLAROTY_API_URL (default: https://api.medigate.io), CLAROTY_API_TOKEN, CLAROTY_VERIFY_SSL, CLAROTY_TIMEOUT, CLAROTY_RATE_LIMIT_PER_MIN (default: 2000)
- Twitter MCP         → TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET, TWITTER_HEARTBEAT_ENABLED (default: false)
- Cisco PSIRT MCP     → CISCO_CLIENT_ID, CISCO_CLIENT_SECRET (OAuth2 client-credentials via id.cisco.com), CISCO_PSIRT_CACHE_DIR, CISCO_PSIRT_CACHE_TTL_S (default 21600)
- Globalping MCP      → GLOBALPING_TOKEN (bearer, remote endpoint mcp.globalping.dev; 401 without it)
```

## Detailed Per-Integration Notes

For **detailed infrastructure notes on specific MCP servers/skills** (GitLab, Chrome DevTools, Computer Use, Jenkins, Atlassian, Token Optimization, gNMI, Memory MCP, MemPalace, Twitter, UE5, Sketchfab, Claroty), read `TOOLS-REFERENCE.md`:
- Not auto-loaded — this file has a size budget, so the verbose per-integration reference material lives separately
- Load with: `read("~/.openclaw/workspace/TOOLS-REFERENCE.md")`
- Same pattern as `SOUL.md` deferring to `SOUL-SKILLS.md`/`SOUL-EXPERTISE.md` — read it when a task needs that level of detail, don't hold it in context otherwise

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

## RAG Knowledge Base MCP Server (NetClaw Native)

10 MCP tools for the offline, user-curated document knowledge base (separate from Memory — RAG holds what USERS upload, Memory holds NetClaw's own experience):
- `rag_ingest` — WHEN a document file on disk should be learned
- `rag_ingest_base64` — WHEN a Slack attachment should be learned (decode → ingest)
- `rag_ingest_url` — WHEN the user asks to ingest a web page (always preview crawl scope first)
- `rag_search` — WHEN a question concerns vendor procedures, customer standards, install steps, or ingested content (NEVER for live network state or past sessions)
- `rag_list` — WHEN the user asks what the knowledge base contains
- `rag_stats` — WHEN asked about corpus size/health or retrieval telemetry
- `rag_update_metadata` — WHEN a document's doc_type/title/version needs fixing
- `rag_delete` — WHEN the user asks to remove a document (confirm with the user first)
- `rag_reindex` — WHEN chunking/embedding config changed (confirm with the user first)
- `rag_snapshot` — ONLY when the user explicitly asks to store live output for later comparison (confirm scope; never automatic)
- Transport: stdio, Python 3.10+, fully offline (hybrid dense+BM25 retrieval, local reranker, cited results)
- Data: `~/.openclaw/rag/` (ChromaDB + SQLite + BM25 pickles + retained sources) — never touches `~/.openclaw/memory/`
- No credentials required

## N2N Federation MCP Server (NetClaw Native)

39 MCP tools proxying the local `bgp-daemon-v2` HTTP API for claw-to-claw federation over NCFED.

Observability / endpoint hygiene tool (feature 100 — see `specs/100-federation-log-observability/`):
- `n2n_forget_endpoint(peer, actor="operator")` — WHEN a peer's recorded dial endpoint is known-wrong (it moved, its tunnel rotated, or it will not return) and `n2n_health` shows repeated dial failures against it. A permanently-unreachable peer with a stale endpoint was the single largest source of federation log noise (23,366 lines in 7 days before this feature); clearing the endpoint stops it at the source. The peer stays federated and keeps trust material, chat setting and audit history — only the dial address is cleared, and it reconnects automatically the moment it re-registers by contacting this Border. A live channel is left running. Idempotent.
- Config (dead-peer log dampening, all optional): `N2N_RECONNECT_DAMPEN` (`0` = full bypass, restores per-attempt WARNING logging for diagnosis), `N2N_RECONNECT_DEAD_CEILING_S` (default `900`), `N2N_RECONNECT_DEAD_AFTER` (default `20`), `N2N_RECONNECT_ENDPOINT_STALE_S` (default `86400`), `N2N_RECONNECT_SUMMARY_INTERVAL_S` (default `300`), `N2N_RECONNECT_STABLE_AFTER_S` (default `120`)
- No new credentials.
 Replication-specific tools (feature 065, chroma-to-chroma vector replication — see `workspace/skills/n2n-federation/SKILL.md` for when/how to use them):
- `n2n_replicate` — WHEN the user wants a standing local copy of a consenting peer's RAG collection (not just a one-off answer — use `n2n_knowledge_query` for that). Returns a `task_id` immediately; does not block.
- `n2n_replicate_resync` — WHEN a previously replicated collection needs refreshing to match the source's current content (full replace, same async pattern)
- `n2n_replicate_delete` — WHEN the user wants a local replica removed entirely (distinct from revoking the grant, which only blocks *future* replication)
- Requires a `knowledge_replica` grant via `n2n_grant`, distinct from the `knowledge` (query-only) grant feature 064 uses
- Config: `N2N_REPLICATION_MAX_CHUNKS` (default `20000`) caps the size of a collection replication will transfer; `N2N_REPLICATION_BATCH_SIZE` (default `200`) sizes each page pulled from the source
- No new credentials — reuses existing NCFED peer identity/consent state

NetClaw Mobile edge-node tool (feature 066 — see `mobile/netclaw-mobile/README.md` and `specs/066-netclaw-mobile-ncfed-edge/`):
- `n2n_notify_phone(peer, content, kind="text")` — WHEN the operator or agent wants to explicitly push a message to an enrolled phone (`kind`: `text`/`voice`/`image`). Reachable identically from Slack, TUI, HUD, or agent reasoning. NEVER a blanket mirror — only content pushed through this tool ever reaches the phone. Falls back to a platform push notification automatically if the device is disconnected.
- Enrollment itself is operator-side, not an MCP tool: `netclaw risk token --edge [label]` renders a scannable QR (`scripts/netclaw`)
- Config: `N2N_EDGE_WS_PORT` (Border-only, the phone-facing WebSocket listener port); `FCM_SERVICE_ACCOUNT_JSON`/`APNS_KEY_PATH`/`APNS_KEY_ID`/`APNS_TEAM_ID`/`APNS_BUNDLE_ID`/`APNS_USE_SANDBOX` (optional — only needed for the disconnected-device push-notification fallback)
- No new credentials for the connected-phone path — reuses the same domain-verified/self-signed credential as eN2N/iN2N (feature 060)

NetClaw Mobile command channel (feature 067 — see `specs/067-ncfed-mobile-command-channel/`): **no new MCP tool**. A phone's typed/spoken/QR-triggered request reaches you as a real agent turn over the existing edge connection (`n2n/edge/ask`, wire-level only) — you answer it the same way you'd answer Slack/CLI, calling `n2n_route`/`n2n_delegate`/`n2n_invoke`/`n2n_chat` yourself if the question needs a member or a federated peer. Always state plainly whether you answered directly or are relaying a member's/peer's answer — the phone's conversation view has no other way to know. A phone request never carries elevated or reduced trust versus Slack/CLI/TUI.

NetClaw Mobile biometrics and capture (feature 068 — see `specs/068-ncfed-mobile-biometrics-capture/`): **no new MCP tool**, two slices:
- Biometric approval: your existing `notify_approval` hook (fired by the same tool/skill/delegation approval flow that already drives the CLI/HUD approval surface) now also pushes to every connected phone (`n2n/edge/message` with `content_type="approval"`, wire-level only); the phone's operator resolves it there with device biometrics before `resolve_approval` runs with `via="biometric"` — everything else about the approval (grant/deny semantics, audit trail) is unchanged.
- Capture: a phone can attach a photo/video/audio capture to its own `n2n/edge/ask` request (arrives to you as an ordinary multimodal ask). You can also request a capture FROM a phone via the existing `n2n_delegate`/capability-routing path — an edge node advertising `camera.capture`/`camera.record_video`/`audio.record` in its member scope is selected by the same `RiskRouter` matching used for any other member's capability; a capability the operator disabled in Settings is simply absent from that scope, never a special refusal case.

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

## Globalping External Checks (`globalping-mcp`, remote)

Outside-in measurement — the only vantage point NetClaw has **outside** its own administrative domain.
Official jsDelivr hosted MCP; no local server by design.

| Tool | Purpose |
|---|---|
| `ping` | Reachability and round-trip latency from chosen probes |
| `traceroute` | Path from a probe toward the target |
| `dns` | Resolution and propagation, per resolver |
| `mtr` | Per-hop loss and latency together |
| `http` | Application-layer reachability, status and timing |
| `limits` | Remaining budget and reset (free — costs nothing) |
| `locations` | Probe availability, before a narrow filter wastes units |

**Three ways to get nothing back, and they are not the same**: `no_probes_found` means **the measurement
never ran** (widen the filter — never report it as an outage); **0 of N successful** means the target
genuinely did not answer (a real finding); a private/internal target is **refused locally before any call**,
so internal addressing is never transmitted.

**Budget**: 500 probe-measurements/hour authenticated, 250/hour anonymous per IP, rolling. **Charged per
probe** — `limit: 20` spends 20 — so right-size `limit` rather than maximising it.

**Location syntax**: `+` is AND (`London+UK`, `Amazon+Germany`); an array for several places
(`["London","Frankfurt"]`); `world` for a global spread; `AS3320` for an ASN. A **comma inside one string
fails**, and **`AS13335` never returns probes** despite being the vendor's own schema example — Cloudflare
hosts none. Only ~1,390 of the internet's ASNs host a probe.

**Privacy note**: every tool requires a natural-language `context` field the vendor uses for intent
analytics. NetClaw sends a generic, task-shaped value with no customer name, internal hostname, ticket or
topology detail. `limits` output echoes a short token fragment — don't paste it into a public channel.

## Cisco PSIRT Advisories (`cisco-psirt-mcp`)

Answers whether a running Cisco version is affected by a published advisory. Read-only,
and it **never contacts a device** — versions come from `pyATS` or `multivendor-cli`.

| Tool | Purpose |
|---|---|
| `check_version` | Advisories for one `(ostype, version)` |
| `check_versions` | A fleet, de-duplicated by version first |
| `check_cve` | Cisco advisories covering a CVE id |
| `check_advisory` | One advisory by id |
| `list_recent` | Advisories by severity over a date range |
| `psirt_status` | Auth state, rate budget, cache stats, supported families |

**An empty result is not a clean bill of health.** `none_published` means Cisco published
nothing for that exact version; `normalisation_failed` and `api_error` mean the question
went unasked. Never report any of the three as "not vulnerable".

**Version format is per-family and the families contradict each other**: `iosxe` wants
`17.3.1` and rejects `17.3(1)`; `ios` wants `15.2(4)E` and rejects `15.2.4E`; `nxos` wants
`9.3(5)`; `asa`/`ftd`/`fmc` want dotted; `aci` wants the **switch image** version `15.2(3e)`,
not the APIC version. The server converts in whichever direction the family needs.

**Not available** (measured, not inferred): `iosxr` → 404, not an OSType on this API;
Bug/EoX/Case/Serial-to-Info → 403 under the API Console grant; CX Cloud → 504.

**Rate budget**: 5/sec and 30/min shared. Prefer `check_versions` over looping, and treat
`refresh: true` as an incident tool — it disables the 6-hour cache.

## Multivendor CLI Driver (`multivendor-cli-mcp`)

Reaches ~90 platform families no other NetClaw device server can — MikroTik, VyOS, SONiC,
Nokia SR Linux, Extreme, Huawei, Dell, Ubiquiti EdgeOS. Read-only by default.

| Tool | Purpose |
|---|---|
| `server_info` | Identity, read/write mode, modelled platforms |
| `check_command_policy` | Would this command pass? No device contacted |
| `list_devices` | Inventory with source attribution |
| `check_device_readiness` | Resolvable, authenticable, ours to act on? |
| `check_reachability` | Separates unreachable / auth_failed / platform_mismatch |
| `run_command` | Raw CLI, filtered server-side before connecting |
| `get_facts` | NAPALM normalized facts, one shape across vendors |
| `run_fleet` | Concurrent fan-out, per-device results |
| `apply_config` * | Gated write: routing → filter → CR → approval → baseline → verify → rollback |
| `check_change_request` * | ServiceNow CR authorisation lookup |

\* present only when `MULTIVENDOR_WRITE_ENABLED` is set.

**Routing**: Cisco → `pyATS`, Junos → `junos-mcp`, telemetry → `gnmi-mcp`. This server owns
everything else, plus cross-vendor normalized reads read-only. Writes are single-pathed per platform.

Dedicated virtualenv: `napalm`/`netmiko` resolve `cryptography` 49.x while the system carries 46.x,
which NCFED uses for X.509 issuance.

## Fortinet (`fortinet-mcp`, NetClaw-native)

**Spec 080 / roadmap R3.** Three planes, 21 tools, stdio, read-only by default.
Replaces an earlier `fortimanager-ops` skill that named `jmpijll/fortimanager-mcp` —
a server that was never vendored, registered, or installable.

| Plane | Appliance | Answers | Transport |
|---|---|---|---|
| `manager` | FortiManager | policy **intent** — ADOMs, packages, objects, revisions | JSON-RPC `/jsonrpc` |
| `device` | FortiGate | **observed state** — interfaces, routes, VPN, HA, VDOM | REST, bearer token |
| `analyzer` | FortiAnalyzer | **observed traffic** — logs, policy activity | JSON-RPC `/jsonrpc` |

FortiManager and FortiAnalyzer share one JSON-RPC client — same endpoint, same
envelope, different methods.

### Environment

`FORTINET_MCP_CMD` · `FORTIMANAGER_HOST` / `FORTIMANAGER_API_TOKEN` ·
`FORTIGATE_HOST` / `FORTIGATE_API_TOKEN` · `FORTIANALYZER_HOST` /
`FORTIANALYZER_API_TOKEN` · `FORTINET_VERIFY_SSL` (default `true`) ·
`FORTINET_ALLOW_WRITES` (default `false`)

Each plane is independently optional; an unconfigured plane is not consulted and
NetClaw says so rather than answering from another.

### Behaviour worth knowing

- Every response carries `plane` and `scope` **structurally** and is GAIT-audited —
  enforced at a chokepoint, so a new tool cannot omit either.
- **"No logs matched" is not "rule unused"** — returns `no_logs_in_window`, its own
  outcome.
- **VPN phase 1 and phase 2 are always separate fields.** Phase 1 up / phase 2 down
  is a specific fault, not "half up".
- `fgt_compare_with_manager` reports intent-vs-state divergence; `only_in_device`
  entries are candidate out-of-band changes.
- Writes need **two** gates: human approval **and** an approved ServiceNow CR.
  Neither substitutes for the other.

### Field notes (FortiOS 7.6.7, measured 2026-08-01)

- `monitor/system/interface` returns a **dict keyed by interface name**, not a list.
- An **unregistered** FortiGate returns 401 for every REST request regardless of
  token validity or trusthost. Check `License Status: Valid` before suspecting
  credentials.
- FortiOS **8.0.0 GA** has a web-GUI logout loop on the 1 vCPU trial profile
  (`VM resource exceeds license limit` → `httpsd` restart). SSH and REST unaffected;
  7.4/7.6 do not exhibit it.
- Evaluation licence caps: 1 vCPU, 2 GB RAM, 3 interfaces, 3 routes, 3 policies.

## BGP & Registry Intelligence (`bgp-intel-mcp`, NetClaw-native)

**Spec 081 / roadmap R9.** 10 tools, stdio, read-only, **no credentials**. The other half of the external
plane: R8's Globalping *measures* toward a target; this *looks up* ownership, routing legitimacy and peering.

| Source | Provides |
|---|---|
| `rpki-validator.ripe.net` | RPKI origin validation (primary — RFC 6811 vocabulary, returns VRPs) |
| `stat.ripe.net` | RPKI fallback, AS overview, announced prefixes, visibility |
| IANA bootstrap → RIR RDAP | Registry ownership, abuse contacts |
| `peeringdb.com` | IXPs, facilities, peering policy |
| `atlas.ripe.net` | Anchors, per-AS probe counts |

### The four RPKI states

| `state` | `reason` | Finding? | Meaning |
|---|---|---|---|
| `valid` | — | no | A ROA authorises this origin |
| `invalid` | `as` | **yes** | A ROA covers it; **a different AS** is authorised |
| `invalid` | `length` | **yes** | Correct AS; prefix more specific than `maxLength` |
| `not_found` | — | **no** | **No ROA exists.** The normal case for most of the internet |

`validation_unavailable` is a separate outcome — an unreachable validator is **not** `not_found`.

### Environment

`BGP_INTEL_MCP_CMD` · `BGP_INTEL_USER_AGENT` · `BGP_INTEL_MAX_RPS` (default 4) · `BGP_INTEL_AUDIT_LOG`

No API keys. Every source is public and unauthenticated.

### Behaviour worth knowing

- Every response carries `source` + `retrieved_at` and is GAIT-audited — enforced at a chokepoint.
- **`no_record` and `source_unavailable` are never conflated** — a dead API is not an empty registry.
- Registry data is **allocation, not routing**; PeeringDB is **self-reported**; visibility is **RIPE's
  collectors**, not global truth. Each is stated in the response `caveats`.
- **4 req/s per source, true sliding window, strictly serial.** Self-imposed — neither RIPEstat nor
  PeeringDB publishes rate-limit headers. Parallel fan-out prohibited, including inside `resource_report`.
- Private/reserved/bogon input is **refused locally with no outbound request** — a disclosure control.
- Manifest measured at **1,376 / 5,000 tokens**.

## Document Generation (`document-mcp`, NetClaw-native)

**Spec 082 / roadmap R18.** 6 tools, stdio, **no credentials**. Writes files; touches no device and no
ticket, so there is no approval gate here. This is the deliverable layer — every other NetClaw capability
produces findings, this turns a finding into something you can attach to a change record.

| Format | Tool | Built from |
|---|---|---|
| `.docx` | `docx_write` | Ordered blocks: heading, paragraph, figure, table, keyvalue, image, pagebreak |
| `.xlsx` | `xlsx_write` | Sheets of tagged rows, plus `failed_rows` for devices that could not be reached |
| `.pptx` | `pptx_write` | Slides: bullets, figure, image |
| `.pdf` | `pdf_inspect_form` / `pdf_fill_form` | An existing fillable form's **named** fields |
| — | `list_documents` | Finding something generated earlier |

### The one rule

**A document must never fabricate to fill a blank.** Tool output is ephemeral; a document is emailed, filed
and read months later by someone who was not there, and it carries the authority of its formatting. So every
value is one of three tagged shapes — `{"v":…, "src":…}`, `{"unavailable": reason}`, `{"failed": reason}` —
and a bare scalar or a value with no `src` is **refused**. There is no way to express "missing" as a blank.

### Environment

`DOCUMENT_MCP_CMD` · `DOCUMENT_OUTPUT_DIR` (default `workspace/output/document-mcp/`) ·
`DOCUMENT_MAX_ROWS` (50000) · `DOCUMENT_MAX_BLOCKS` (5000) · `DOCUMENT_MAX_SLIDES` (200) ·
`DOCUMENT_AUDIT_LOG`

No API keys. Nothing to rotate.

### Behaviour worth knowing

- **Provenance is visible, never hidden.** Source column per table row, per-figure parenthetical in prose, a
  visible source box on every slide, and a Sources section in every file. Word comments, document metadata
  and speaker notes are written *additively* but never count — they are collapsed by default, stripped on
  paste, and absent in print.
- **`python-docx` has no footnote API** (measured), so `.docx` attribution is inline. More visible than a
  footnote, not less.
- **openpyxl writes a leading `=` as a live formula.** Measured: `ws["A1"] = "=1+1"` produces
  `<c r="A1"><f>1+1</f>…`. Every string cell is forced to `inlineStr`, so a FortiGate interface description
  or a ServiceNow short-description cannot put executing content into an auditor's spreadsheet.
- **Admin and operational state must be separate columns.** A merged `status` column is refused — the
  distinction spec 080's completion established.
- **Failed devices are rows, not omissions.** A shorter spreadsheet reads as a smaller estate. The banner
  reports attempted / returned / failed.
- **Sources that disagree are both rendered** with their origins and a caveat. NetClaw does not pick a
  winner.
- **Office templates are refused, not ignored** — scratch-only, because a template's empty field is the
  strongest fabrication pressure in the feature. PDF forms are supported precisely because their fields are
  explicitly named and machine-readable.
- **A filled PDF carries no Sources section** — it is the customer's document. For that one format
  provenance lives in the response and the GAIT record. Stated rather than papered over.
- **Files are never overwritten.** `O_EXCL` create with a collision suffix, so a regenerated report cannot
  replace one already attached to a ticket. An unwritable output directory is a reported failure with no
  temp-directory fallback.
- **`ok` means complete.** Any gap forces `written_with_gaps`; a caller cannot report a gapped document as
  clean.
- Every call, **including refusals**, is GAIT-audited at the chokepoint.
- Manifest measured at **1,232 / 5,000 tokens**.

### Boundaries

`drawio-diagram` / `markmap-viz` / `uml-diagram` / `threejs-network-viz` produce **diagrams** — this
**embeds** them and never redraws. `rag-mcp` (feature 062) **reads** these formats for ingestion; this
**writes** them, sharing the same four libraries with identical bounds.
`servicenow-change-workflow` owns the CR lifecycle; this renders a document from one.
`slack-report-delivery` / `webex-report-delivery` **send** documents; this only writes them.

## Arista ANTA Validation (`anta-mcp`, NetClaw-authored over Apache-2.0 ANTA)

**Spec 098 / roadmap R25.** 4 tools, stdio, read-only, **own virtualenv**. Manifest measured
**1,272 / 5,000 tokens** for a **208-test** catalogue.

The assertion layer: every other source reads state, this one asserts on it.

| Tool | Purpose |
|---|---|
| `anta_list_tests(category, keyword)` | Search the 208-test catalogue — **contacts no device** |
| `anta_describe_test(test)` | One test's description and input schema — **contacts no device** |
| `anta_run_tests(host, tests\|category, inputs)` | Run tests against one EOS device |
| `anta_status()` | ANTA version, catalogue size, credential state |

### Five verdicts, never merged

`pass` / `fail` / **`not_applicable`** / `skipped` / `error`, counted separately.

**The reclassification that matters**: ANTA reports a test for an unconfigured feature as a
*failure*. Measured — `VerifyBGPPeerCount` on a device with no BGP returns
`"'show bgp summary vrf all' failed: BGP inactive"`. Counted naively that claims a BGP fault on a box
with no BGP. The server reclassifies to `not_applicable`, keeps the original message, and the rule is
deliberately narrow so a real failure is never hidden.

**No health percentage is emitted** — `passed/total` is meaningless with `not_applicable` and
`skipped` in the denominator. The helper raises rather than computing one.

### Its own venv, and not by preference

ANTA pulls **cryptography 50.0.0** while the system holds **46.0.5** with four unbounded dependents
(`Authlib`, `pygnmi`, `service-identity`, `sshsig`) including NetClaw's federation TLS stack. Measured
by dry-run *before* installing — spec 076's cryptography incident.

Credentials: `ANTA_USERNAME` / `ANTA_PASSWORD`, environment only. `ANTA_VERIFY_TLS` defaults to
`false` and is always disclosed in output as `tls_verified`.

## Elasticsearch Logs (`elasticsearch-mcp`, adopted third-party Apache-2.0)

**Spec 096 / roadmap R12.** 5 tools, stdio via Docker, read-only. **Manifest measured 1,094 / 5,000
tokens.** NetClaw installs no cluster — this queries one the operator already runs (8.x/9.x).

| Tool | Purpose |
|---|---|
| `list_indices(index_pattern)` | Indices, status, document counts |
| `get_mappings(index)` | Field names and types — read before composing a query |
| `search(index, query_body)` | Query DSL retrieval (and aggregations) |
| `esql(query)` | ES-QL — counting, grouping, ranking |
| `get_shards()` | Shard allocation and health |

### The counting rule

Elasticsearch caps `hits.total` at 10,000 and marks it `relation: "gte"`. **This server discards the
qualifier**, printing a bare `Total results: 10000` that is indistinguishable from an exact count.
Measured against 10,075 documents: unguarded `search` said **10000**; `esql` and
`search` + `track_total_hits: true` both said **10075**. The error is unbounded — a million-document
index still reports 10,000.

Count with `esql` or `track_total_hits`. An unguarded `search` retrieves example documents only.

### Adopted, deprecated upstream, digest-pinned

Elastic deprecated this server in favour of Agent Builder's MCP endpoint, which is **Enterprise-tier on
self-managed** — so the supported path is paywalled and this one is not. Apache-2.0 and already
published, so it cannot be withdrawn. The image is pinned by digest
(`sha256:d57ea11d…eb003`) so a security-only update cannot change answers underneath the operator.

`ES_URL` resolves **inside the container**: a cluster on the host is `http://host.docker.internal:9200`,
never `localhost`. Credentials: `ES_API_KEY` (scope it `read` + `view_index_metadata`) or
`ES_USERNAME`/`ES_PASSWORD`.

## Zabbix SNMP-Poller NMS (`zabbix-mcp`, vendored third-party GPL-3.0)

**Spec 083 / roadmap R11.** 3 tools, stdio, read-only. **Manifest measured 589 / 5,000 tokens** — the
smallest surface NetClaw has added for an entire product category.

This is the **polled-history layer**. Everything else NetClaw sees arrives when something happens — syslog,
traps, flows. This is the only source that can answer *what was it doing*, *is this normal*, *how long has
it been down*.

| Tool | Purpose |
|---|---|
| `zabbix_api(method, params)` | Generic JSON-RPC passthrough |
| `zabbix_api_docs(method)` | Upstream method documentation |
| `zabbix_api_list(object)` | Available methods for an object |

### Adopted, not built — and it runs in its own venv

`mpeirone/zabbix-mcp-server`, pinned `0722f48`, **unmodified**, GPL-3.0 retained verbatim. NetClaw invokes it
over stdio as a separate program; that is not linkage.

**It requires fastmcp 3.x while five NetClaw servers pin `<3`** (`netbox-mcp-server`,
`CiscoFMC-MCP-server-community`, `Wikipedia_MCP`, `rag-mcp`, `ISE_MCP`). It therefore runs from a dedicated
virtualenv — the same reason `multivendor-cli-mcp` has one. **Do not "simplify" that away.**

### Environment

`ZABBIX_MCP_CMD` · `ZABBIX_URL` · `ZABBIX_TOKEN` · `VERIFY_SSL` · `READ_ONLY` (forced true) ·
`ZABBIX_API_BLACKLIST`

### Two traps that return an empty array and a success status

Both measured against live Zabbix 7.0.29. Both silent — no error, no warning.

1. **`history.get` defaults its value type to unsigned (3), and 84 of 121 stock items are float (0).** Ask
   with the default and you get `[]`. Always call `item.get` first and pass the item's real `value_type`.
   Types **cannot be mixed** in one call — measured: 4 items, 2 returned each way, zero overlap.
2. **Raw history ages out into hourly trends.** A question older than the history window returns nothing
   from `history.get`. `item.get` reports per-item `history` and `trends`; read them and route.

**Retention can also be switched off**: `history=0` means raw values are never stored; `trends=0` means no
aggregates. Measured on a stock install: 10 items with `trends=0`, 5 with both zero. That is a
*configuration fact*, not an absence.

### Behaviour worth knowing

- **Read-only is FORCED by NetClaw, not inherited.** The upstream library defaults it safe
  (`utils.py:29` → True) but the shipped launcher inverts it (`start_server.py:139` → False). A
  destructive-method deny-list is configured as a second layer and **holds even with read-only disabled** —
  verified.
- Read/write classification upstream is a **method-name prefix heuristic** (`get`, `version`, `check`,
  `export`), not a curated list. That is why the deny-list exists.
- **The two traps are enforced by the SKILLS, not by code.** This is a generic passthrough with no
  chokepoint — the first NetClaw integration where a core distinction is guidance-level. Deliberate, and
  recorded.
- **No per-call GAIT audit.** The upstream has no audit concept and there is no platform-level MCP audit.
  Acceptable only because this is strictly read-only — there is no operation to record.
- Auth is API-token/bearer. The in-request credential property still works on 7.0 but is **removed in 7.2+**.

### Boundaries

`snmptrap-mcp` **receives** traps; this **polls** and keeps history. `ipfix-mcp` is flows, not counters.
`prometheus`/`grafana` are pull-based stores for infrastructure you instrumented; this is the NMS for gear
you did not. `auvik`/`thousandeyes`/`datadog` are SaaS with their own agents. `pyats`/`multivendor-cli`/
`fortinet` read **current** device state; this answers **what it was over time**, and can answer for a
device that is unreachable right now.

## Kubernetes read-only (`k8s-mcp`, vendored third-party Apache-2.0)

**Spec 084 / roadmap R14.** 7 tools, stdio, strictly read-only. **Manifest measured 1,643 / 5,000 tokens.**

`kubeshark` sees packets inside a cluster; this reads the objects — pods, services, ingresses,
EndpointSlices and **NetworkPolicies**.

| Tool | Purpose |
|---|---|
| `resources_list` / `resources_get` | Any `apiVersion`+`kind` — NetworkPolicy, Service, Ingress, EndpointSlice, CRDs |
| `pods_list` / `pods_list_in_namespace` / `pods_get` | Workload inventory |
| `namespaces_list` | Establish which namespaces exist — needed to tell "no such namespace" from "empty" |
| `events_list` | The why behind a pod status |

### Adopted: `containers/kubernetes-mcp-server` v0.0.66

**Apache-2.0** (identical to NetClaw's) and a **statically linked Go binary** — zero runtime deps, so it
cannot collide with the `fastmcp<3` pins. Pinned and verified against a recorded SHA-256; not committed.

**The DEFAULT config is 21 tools / 5,716 tokens and busts the ceiling.** Trimming to `core` + 6
`disabled_tools` is what makes adoption possible.

### The trap, reproduced

Given a credential without cluster-wide list permission the server **does not error** — it rewrites the
query to one namespace and returns it plainly:

```
raw kubectl  →  Forbidden: cannot list networkpolicies at the cluster scope
this server  →  success, 1 policy        ← the cluster had 2
```

`resources.go:34-38` narrows on denial and **discards the permission error**, so an API blip looks the same
as a 403. Mitigated by a **mandated cluster-wide-read ServiceAccount** (makes the branch unreachable —
verified) plus a **skill preflight** (`can-i` before trusting any empty result).

### Behaviour worth knowing

- **No NetworkPolicy means all traffic is permitted.** Kubernetes is default-allow, so "no policies" is a
  finding, not a neutral observation.
- **An empty list has six causes**: insufficient permission · no such namespace · empty namespace ·
  selector matched nothing · CRD not installed · cluster unreachable. A typo'd selector returns HTTP 200
  with zero rows, identical to a genuine non-match — so the selector must be shown.
- **Secrets denied at two layers** — server `denied_resources` *and* the ServiceAccount RBAC.
- **The kubeconfig must be explicit and token-only.** A kubeconfig carrying a client certificate silently
  ignores the token. Every candidate otherwise defaults to the ambient `current-context`, possibly
  production.
- **No per-call GAIT audit.** `--log-file` exists but at level 4 logs lifecycle only — no tool calls.
- **Reachable is not permitted.** `kubeshark` shows traffic that flowed; this shows what is declared.

### Boundaries

`kubeshark-traffic` = observed traffic · `prometheus`/`grafana` = metrics ·
`containerlab`/`gns3`/`cml` = building labs · this = the declared object model, read-only.


## Cisco Catalyst Center, read-only (`catc-mcp`)

**Spec 087.** 10 tools, stdio, strictly read-only. **Manifest measured 1,821 / 5,000 tokens** — with all
**514 read-only operations** reachable.

Cisco released an official Catalyst Center MCP server whose default bundle measures **515 tools / 64,420
tokens — 12.9x the ceiling**. NetClaw adopts its **catalogue** (Apache-2.0, `release/2.3.7.11`), not its
runtime, and fronts it with 8 grouped dispatchers plus `catc_find` and `catc_describe_operation`.

| Tool | Use |
|---|---|
| `catc_find` | **Start here** — search all 514 operations locally. Names are generated, not guessable |
| `catc_describe_operation` | Parameter schema on demand |
| `catc_devices` `catc_sites` `catc_wireless` `catc_health` `catc_compliance` `catc_software` `catc_events` `catc_other` | `(operation, params)` |

### Why the catalogue and not the runtime

Avoids three upstream properties at once: **`fastmcp>=2.0.0` unbounded** (resolves 3.x against five servers
pinning `<3` — the third occurrence of the spec-083 hazard), **HTTP transport on port 7001** (every other
NetClaw MCP is stdio), and **a container** needed only to isolate the first. Dependencies here are `mcp` and
`httpx`.

### Behaviour worth knowing

- **An empty inventory is not an empty network.** Zero devices is a statement about the controller. Every
  response is stamped at a chokepoint with **which appliance answered** and **when** — because the two
  DevNet sandboxes share credentials and `sandboxdnac2` has zero devices while authenticating perfectly.
- **Zero counts carry the same caveat as empty lists.** A bare `0` reads even more like data; found by live
  testing.
- **`unreachable`, `auth_failed` and `empty` are three different facts.** Keeping them apart required a real
  fix — `httpx.HTTPStatusError` subclasses `httpx.HTTPError`, so a 401 initially surfaced as `unreachable`.
- **Read-only by curation**: only GET operations are catalogued and the single upstream POST is excluded, so
  it cannot be dispatched. Upstream states it enforces no read-only access; curation plus account RBAC are
  the two controls.
- **"Catalyst Center says unreachable" is not "the device is down"** — one controller's last poll.
- Upstream is **version-coupled**: the branch name is the appliance version, and `main` contains no code.

### Boundaries

`pyats`/`multivendor-cli` read the device (and win on disagreement) · `netbox`/`nautobot` hold intent, this
reports discovery · `devnet-catalyst-search` reads docs, this queries an appliance.
