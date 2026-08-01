# netclaw Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-07-31

## Active Technologies
- N/A (stateless server; subscription state held in-memory during runtime) (003-gnmi-mcp-server)
- Python 3.10+ + FastMCP (MCP framework), azure-mgmt-network, azure-mgmt-resource, azure-identity (DefaultAzureCredential), gait_mcp (audit logging) (004-azure-network-mcp)
- N/A (stateless; reads from Azure ARM APIs) (004-azure-network-mcp)
- JavaScript (ES2022) / HTML5 / CSS3 for Canvas components; SKILL.md for skill definition + OpenClaw Canvas/A2UI framework (rendering primitives), existing MCP servers (data sources) (005-canvas-a2ui-integration)
- N/A (stateless visualization — all data fetched on demand from MCP servers) (005-canvas-a2ui-integration)
- Python 3.10+ + FastMCP (mcp SDK), httpx (async HTTP client), python-dotenv (001-suzieq-mcp-server)
- N/A (stateless proxy to SuzieQ REST API) (001-suzieq-mcp-server)
- Python 3.10+ + anthropic (SDK with count_tokens), toon-format (TOON serialization), FastMCP (existing MCP framework) (006-token-optimization)
- N/A (in-memory session ledger; no persistent storage) (006-token-optimization)
- N/A (no server code — Jenkins plugin is Java-based and runs inside Jenkins). Skill documentation and configuration files only. + Jenkins 2.533+ with MCP Server plugin (v0.158+), MCP Java SDK 0.17.2 (007-jenkins-mcp-server)
- N/A (stateless — Jenkins maintains all job/build state) (007-jenkins-mcp-server)
- TypeScript/Node.js (community MCP server). No netclaw-authored server code — configuration and skill documentation only. + @zereight/mcp-gitlab (npm package), Node.js 18+ (008-gitlab-mcp-server)
- N/A (stateless proxy to GitLab REST API) (008-gitlab-mcp-server)
- Python 3.10+ (community MCP server). No netclaw-authored server code — configuration and skill documentation only. + mcp-atlassian (pip package), Python 3.10+ (009-atlassian-mcp-server)
- N/A (stateless proxy to Atlassian REST APIs) (009-atlassian-mcp-server)
- Python 3.10+ (consistent with existing NetClaw MCP servers) + FastMCP (MCP framework), asyncio (UDP receivers), pysnmp (SNMP trap decoding), python-syslog-rfc5424 (syslog parsing), xflow (IPFIX/NetFlow decoding) (010-telemetry-receivers)
- In-memory only (data lost on restart, acceptable for demo/testing scope) (010-telemetry-receivers)
- Markdown (documentation reorganization) + N/A (pure markdown files, OpenClaw read tool) (011-soul-optimization)
- Filesystem (`~/.openclaw/workspace/`) (011-soul-optimization)
- Python 3.10+ (consistent with existing NetClaw MCP servers) + FastMCP (MCP framework), httpx (async HTTP client), python-dotenv (environment variables) (012-gns3-mcp-server)
- N/A (stateless proxy to GNS3 REST API) (012-gns3-mcp-server)
- Python 3.10+ (community MCP server uses prisma_sase SDK) + prisma-sdwan-mcp (community), prisma_sase SDK (OAuth2 client) (013-prisma-sdwan-mcp-server)
- N/A (stateless proxy to Prisma SASE REST API) (013-prisma-sdwan-mcp-server)
- N/A (Remote MCP managed service) + Datadog MCP remote endpoint, DD_API_KEY, DD_APP_KEY (016-datadog-mcp-server)
- N/A (stateless proxy to Datadog APIs) (016-datadog-mcp-server)
- Python 3.10+ (consistent with NetClaw MCP servers) + blender-mcp (community, via uvx), Blender 3.0+ (user-installed) (024-blender-3d-viz)
- N/A (stateless - visualization is ephemeral in Blender) (024-blender-3d-viz)
- Python 3.10+ (community MCP server with Aruba CX REST API client) + aruba-cx-mcp-server (community), httpx or requests (REST client) (025-aruba-cx-mcp-server)
- N/A (stateless proxy to Aruba CX REST API) (025-aruba-cx-mcp-server)
- N/A (Remote MCP server - no code required) + N/A (Remote MCP managed service) (026-devnet-content-search-mcp)
- N/A (stateless - all data from remote API) (026-devnet-content-search-mcp)
- Python 3.10+ (MCP servers, policy scripts), Bash (installation) + NVIDIA OpenShell CLI (uv tool), Docker (container runtime), existing FastMCP servers (027-netshell-security)
- Local filesystem for policies and audit logs; no database (027-netshell-security)
- Bash (installation scripts), Python 3.10+ (DefenseClaw requires), Go 1.25+, Node.js 20+ + DefenseClaw (Cisco), Docker (container runtime) (027-netshell-security)
- SQLite (DefenseClaw audit logs), optional SIEM (Splunk HEC, OTLP) (027-netshell-security)
- Node.js 18+ (Check Point MCPs are NPM packages), Bash (install scripts) + @chkp/* NPM packages (15 total), npx (MCP execution) (031-checkpoint-mcp-integration)
- N/A (stateless proxy to Check Point APIs) (031-checkpoint-mcp-integration)
- Python 3.11+ + FastMCP, sqlite3 (stdlib), chromadb, sentence-transformers, torch (CPU) (033-memory-mcp)
- SQLite (facts, decisions, links) + ChromaDB (embedded sessions) in ~/.openclaw/memory/ (033-memory-mcp)
- Markdown (SOUL.md), Python 3.10+ (Memory MCP already implemented) + Memory MCP Server (Feature 033), GAIT, OpenClaw workspace (034-layered-memory-integration)
- SQLite (facts, decisions, links), ChromaDB (session embeddings), MEMORY.md (long-term) (034-layered-memory-integration)
- Markdown (documentation files) + N/A (pure documentation) (038-docs-hud-refresh)
- Python 3.10+ (consistent with NetClaw MCP servers) + FastMCP (MCP framework), tweepy 4.x (Twitter API v2 client), python-dotenv (039-twitter-x-integration)
- Memory MCP (tweet history for deduplication, 30-day retention) (039-twitter-x-integration)
- Python 3.10+ (consistent with existing NetClaw MCP servers) + FastMCP (MCP framework), tweepy 4.x (Twitter API v2 client), python-dotenv (040-twitter-mentions)
- Memory MCP (feature 033) for interaction history; in-memory tracking for processed mention IDs (040-twitter-mentions)
- Node.js 18+ (for @twilio-alpha/mcp), Python 3.10+ (for webhook server and skills) + @twilio-alpha/mcp (NPM), FastMCP (Python webhook), Twilio SDK, openai-whisper-api (existing skill for STT) (042-twilio-voice-mcp)
- Memory MCP (feature 033) for call logging and audit trail (042-twilio-voice-mcp)
- Python 3.10+ (webhook server, skills), Node.js 18+ (Twilio MCP) + FastMCP, Twilio SDK, @twilio-alpha/mcp, Anthropic SDK, httpx, existing MCP servers (pyATS, CML, GNS3, PagerDuty, RFC, Memory, Twitter) (043-full-voice-integration)
- Memory MCP (conversation context per caller ID), SQLite (call audit logs) (043-full-voice-integration)
- Python 3.10+ (skill logic), No custom MCP server code (uses built-in UE5 MCP) + httpx (HTTP client for MCP), Unreal Engine 5.8+ (user-installed with MCP plugin) (044-ue5-mcp-network-viz)
- N/A (stateless - visualization is ephemeral in UE5) (044-ue5-mcp-network-viz)
- Python 3.10+ (matches the existing `ue5-network-viz` skill and the rest of NetClaw) + httpx (existing UE5 MCP HTTP/JSON-RPC client, `ue5_mcp_client.py`), no new third-party packages required (045-ue5-digital-twin)
- N/A — all new state (sticky alert flags, live-mode status, session history buffer, manual zoom groupings) is in-memory for the lifetime of the running skill process; nothing persists across a NetClaw restart (045-ue5-digital-twin)
- Python 3.10+ (skill logic, consistent with the rest of NetClaw) + Three.js r147 pinned (`three@0.147.0` — last release with both classic UMD core and non-module OrbitControls/GLTFLoader addons) vendored as static JS, the newly vendored community `sketchfab-mcp-server` (Node.js, `mcp-servers/sketchfab-mcp-server/`, registered as `sketchfab-mcp` in `config/openclaw.json`) for real-stencil model search/download, and NetClaw's existing topology-source skills/MCP servers (CML lab tooling, `gns3-mcp-server`, `clab-mcp-server`, `eve-ng-mcp-server`, `nautobot-mcp-v2`, `netbox-mcp-server`, `infrahub-mcp`, `ipfabric` integration, `forward-mcp`) consumed as-is, not modified (046-threejs-network-viz)
- N/A for rendering itself; generated visualizations are written as timestamped, uniquely-named `.html` files to a persistent NetClaw workspace output directory (per Clarification session 2026-07-05) — never overwritten, never ephemeral (046-threejs-network-viz)
- Python 3.10+ (matches every other script in `scripts/`, e.g. `scan-all-mcp-source.py`, `register-all-mcps.py`) + None beyond the Python standard library (`os`, `json`, `re`) — no new third-party packages (047-docs-inventory-reconciliation)
- N/A (reads existing `workspace/skills/` directory tree and `config/openclaw.json`; writes no persistent state) (047-docs-inventory-reconciliation)
- Node.js 18+ (official `chrome-devtools-mcp` server — no NetClaw-authored server code); Bash (setup/enable script, consistent with `scripts/*-enable.sh` convention); Markdown (skill + MCP documentation) + `chrome-devtools-mcp` (npm package, official Chrome DevTools team release, MIT-style OSS), Node.js 18+, a locally installed Chrome/Chromium binary (stable channel by default) (048-chrome-devtools-browser-inspection)
- N/A for NetClaw itself (stateless proxy to a local browser process). A persistent Chrome profile directory on disk (`~/.openclaw/chrome-devtools/profile` by default, overridable via `CHROME_DEVTOOLS_PROFILE_DIR`) holds cookies/session state for manually authenticated sites — this is Chrome's own state, not a NetClaw-managed database. (048-chrome-devtools-browser-inspection)
- Bash (matches every existing NetClaw install/enable script and PR #96's own implementation), Python 3.10+ (for the coverage-check script, extending the existing `scripts/verify-inventory-counts.py` pattern) + None beyond what's already vendored — PR #96's own `scripts/lib/*.sh`, the repo's existing Python stdlib-only tooling convention (049-merge-modular-installer)
- N/A (installer logic + a plain-text component manifest at `~/.openclaw/netclaw-components.conf`, per PR #96's own design) (049-merge-modular-installer)
- Bash (install function, matching every existing `scripts/lib/install-steps.sh` entry), Markdown (skill documentation) + OpenClaw's ClawHub `computer-use` skill (consumed as-is, no fork); apt packages `xvfb`, `xfce4`, `xfce4-terminal`, `xdotool`, `scrot`, `imagemagick`, `dbus-x11`, `x11vnc`, `novnc`, `websockify` (all confirmed present in this host's apt repositories; `dbus-x11`, `imagemagick`, `scrot`, `xvfb` already installed) (050-computer-use-desktop)
- N/A — the virtual desktop's state is ephemeral (X11 session state), nothing NetClaw-managed persists across a restart (050-computer-use-desktop)
- Python 3.10+ (daemon federation layer + n2n-mcp, matching + Existing `bgp-daemon-v2.py` (listener, protocol (052-n2n-federation)
- SQLite at `~/.openclaw/n2n/federation.db` (consent records, grants, (052-n2n-federation)
- Python 3.10+ (daemon federation layer + n2n-mcp, matching + Existing `bgp-daemon-v2.py` + `bgp/federation/*` (053-n2n-ergonomics)
- Extend the existing SQLite at `~/.openclaw/n2n/federation.db` with (053-n2n-ergonomics)
- Python 3.10+ (daemon federation layer + `n2n-mcp`, matching 052/053), Node.js 18+/ES2022 (HUD), Bash (installer), no new languages + Existing `bgp-daemon-v2.py` + `bgp/federation/*` (manager, channel, service, inventory, authorization, invocation, chat, gateway, negotiate, tasks, audit), FastMCP (`n2n-mcp`), Python stdlib `json`/`sqlite3`/`asyncio`/`ssl`/`socket`; `cryptography` (already a repo dependency, spec 003) for self-signed key generation and pinned-key verification. No new third-party packages. (056-in2n-internal-federation)
- Extend the existing SQLite at `~/.openclaw/n2n/federation.db` with iN2N tables: `risk` (name/description/role/enabled-stacks), `member` (risk-local id, pinned key, transport binding, scope, health, state), `enrollment_token` (single-use). Reuse `delegated_task` for internal delegation; internal delegations are recorded in the existing `remote_invocation_record` audit table with a `channel_kind` discriminator. Pinned keys and the risk's own key stored under `~/.openclaw/n2n/keys/`. (056-in2n-internal-federation)
- Python 3.10+ (daemon + federation package + tooling), Bash (installer/service generator glue), Node.js 18+/ES2022 (HUD posture render only) + Existing `bgp-daemon-v2.py` + `bgp/federation/*` (service, risk, router, internal_channel, audit, gateway, manager, invocation, tasks); the installed `defenseclaw` CLI (`~/.local/bin/defenseclaw`, `docs/DEFENSECLAW.md`); the installed `openshell` CLI (`~/.local/bin/openshell`); `git` (GAIT trail); systemd `--user`. Python stdlib only (`asyncio`, `subprocess`, `sqlite3`, `json`, `pathlib`, `shutil`, `time`). No new third-party packages. (057-in2n-production-enforcement)
- Extend existing SQLite `~/.openclaw/n2n/federation.db` (member health fields, per-member service binding); new **GAIT git repo** at `~/.openclaw/n2n/gait/` (unbounded, FR-012a); systemd units under `~/.config/systemd/user/`; env under `~/.openclaw/mesh.systemd.env` + per-member env files (existing pattern). (057-in2n-production-enforcement)
- kramdown-rfc Markdown → RFCXML **v3** (via `kdrfc`); Markdown for supporting docs. No application code. + `kramdown-rfc` (Ruby gem, provides `kdrfc`), `idnits` (I-D nits checker), `xml2rfc` (invoked by `kdrfc`). Ground-truth source: the reference implementation `bgp/constants.py`, `channel.py`, `agent.py`, `internal_channel.py`, `negotiate.py`, `risk.py` (read-only; cited, not modified). Reference set: RFC 2119/8174/4271/8259 + JSON-RPC 2.0 (normative); RFC 7301/6455/7435/6335/8126, MCP, A2A, `draft-yan-a2a-device-agent-applicability` (informative). (059-ncfed-internet-draft)
- N/A — the deliverable is a document; no runtime state. (059-ncfed-internet-draft)
- Python 3.10+ (daemon + `bgp/federation/*`, matching 052/053/056/057); Node.js 18+/ES2022 (HUD render only); Bash (installer/patch) + Existing `bgp-daemon-v2.py` + `bgp/federation/*` (channel, internal_channel, risk, service, manager, audit, gateway, negotiate); `cryptography` (already a repo dependency — keys, CSRs, X.509 issuance/verification); **lego** (single-binary ACME client, vendored/downloaded at install, drives DNS-01 across 100+ providers); Python stdlib `ssl`/`asyncio`/`sqlite3`/`json`. No new Python packages. (060-claw-cert-security)
- Extend existing SQLite `~/.openclaw/n2n/federation.db` (peer trust columns, credential + rotation-event tables); key material under `~/.openclaw/n2n/keys/` (CA, host credential, ACME account) with `0600`/`0700` permissions (060-claw-cert-security)
- Python 3.10+ (server, matching repo MCP convention; memory-mcp packaging style with hatchling pyproject), Node.js 18+/ES2022 (HUD panel + Express endpoints), Bash (installer step) + `fastmcp`/`mcp`, `chromadb>=0.4`, `sentence-transformers>=2.2` (+ `torch` CPU), `rank_bm25`, `pymupdf` (PDF), `beautifulsoup4` + `httpx` (HTML/URL), `python-docx`, `openpyxl`, `python-pptx`, `vsdx` (modern office), LibreOffice headless (`soffice`, optional system package) for legacy DOC/XLS/PPT/VSD conversion (062-rag-mcp)
- `~/.openclaw/rag/` — ChromaDB (`chroma/`, dense vectors), SQLite (`rag.db`: document registry, retrieval log, telemetry, schema version), BM25 pickles (`bm25/<collection>.pkl`), retained originals (`sources/`), intake dir (`intake/`). Never touches `~/.openclaw/memory/` (FR-030) (062-rag-mcp)
- Python 3.10+ (daemon + `bgp/*`, `bgp/federation/*`); Bash (none new); Node/ES2022 (HUD posture render only) + existing `bgp-daemon-v2.py`, `bgp/agent.py`, `bgp/session.py`, `bgp/federation/{tls,service,manager,channel,inventory,posture}.py`; stdlib `ssl`/`asyncio`/`sqlite3`. **No new third-party packages.** (063-ncfed-wire-hardening)
- extend existing SQLite `~/.openclaw/n2n/federation.db` (reuse `federation_peer.endpoint_host/endpoint_port/endpoint_updated_at`); reuse keys under `~/.openclaw/n2n/keys/`. No new stores. (063-ncfed-wire-hardening)
- Python 3.10+ (daemon + `bgp/federation/*`, matching 052–063); Markdown (SOUL/skill docs + NCFED draft §11 for -01) + Existing only — `bgp/federation/inventory.py` (card), `router.py` (selection), `invocation.py`/`gateway.py` (retrieval turn), the feature-062 rag-mcp (`rag_list`, `rag_search`). No new third-party packages. (064-knowledge-capability-cards)
- Reuses `~/.openclaw/rag/rag.db` (documents registry, read-only for advertisement) and the issued capability card. Per-peer visibility reuses existing federation.db rows. No new store. (064-knowledge-capability-cards)
- Python 3.10+ (daemon + `bgp/federation/*`, matching 052–064) + Existing only — `bgp/federation/replication.py` (NEW: manifest/batch client+server logic, size-cap check, task worker), `tasks.py` (`TaskManager`/`delegated_task`, reused as-is for the async job), `authorization.py` (reused, new `target_type="knowledge_replica"` grant), `negotiate.py` (`TIER0_DENIED` gains `"knowledge/replicate"`), `channel.py` (existing `ch.call()` framing, already chunks messages >64 KB), `knowledge.py`/`inventory.py` (card gains `embedding_model`; `build_entries()` excludes `kind='replica'` rows), rag-mcp's `storage/chroma_store.py` (gains a paginated collection-export read and a rename-on-verify write path) and `storage/registry.py` (`documents.kind` gains `'replica'`; new nullable provenance columns). No new third-party packages. (065-chroma-vector-replication)
- Extends the existing rag-mcp `documents` table in `~/.openclaw/rag/rag.db` (feature 062) with a `'replica'` `kind` and new nullable columns (`source_peer_identity`, `source_collection_id`, `source_embedding_model`, `replicated_at`). Extends the existing Chroma store at `~/.openclaw/rag/chroma/` with one collection per replica, named from source peer + source `collection_id` (FR-016) — no new database, no new top-level store. (065-chroma-vector-replication)
- Python 3.10+ (daemon + `bgp/federation/*`, matching 052–065); Dart 3.x / Flutter 3.x (new mobile client, `mobile/netclaw-mobile/`) + Python: `websockets` (new, but already present transitively in this environment per Phase 0 research — declared explicitly in `protocol-mcp/requirements.txt`) for the Border-side WS listener; `qrcode` (new, pure-Python) for rendering the enrollment QR; existing `tls.py`/`FederationService.host_credential()` (060) reused as-is for the domain-verified SSL context; existing `manager.py`/`risk.py` enrollment-token and member-pinning code reused, extended with a `node_type` column. Dart: a WebSocket client package (`web_socket_channel` or equivalent), a QR-scanner package (`mobile_scanner` or equivalent), platform secure-storage packages (Keychain/Keystore-backed) for the enrollment key, and platform push packages (APNs/FCM) — exact package choices are an implementation detail of Phase 2 tasks, not fixed here. (066-netclaw-mobile-ncfed-edge)
- Extends the existing SQLite `~/.openclaw/n2n/federation.db` `member` table with a `node_type` column (`agent` default | `service` | `edge`); reuses its existing `pinned_key`/`key_fingerprint` columns for the edge node's TOFU-pinned key — no new table. On the phone: platform secure hardware (iOS Keychain/Secure Enclave, Android Keystore) holds the enrollment private key; app-local storage (not federation.db) holds the message feed and connection state. (066-netclaw-mobile-ncfed-edge)
- Python 3.10+ (daemon + `bgp/federation/*`, matching 052–067); Dart 3.x / Flutter 3.x (extends `mobile/netclaw-mobile/`) + Python: none new — reuses `push_to_edge()`, `resolve_approval()`, `RiskRouter`/`member.scope`, `TaskManager`. Dart: `local_auth` (biometric gating, US1), `camera` (photo/video capture, US2/US3) — exact audio-recording package (distinct from 067's speech-to-text, which discards audio after transcribing) is a Phase 2 task detail. (068-ncfed-mobile-biometrics-capture)
- No new tables — `member.scope` gains capture-capability entries (same column, same JSON shape 066/067 already write); `approval_request`'s existing `resolved_via` column gains a new value (`"biometric"`), no schema change. (068-ncfed-mobile-biometrics-capture)
- Python 3.10+ (daemon + `bgp/federation/*`, matching 052–066); Dart 3.x / Flutter 3.x (extends `mobile/netclaw-mobile/`, the same codebase 066 established) + Python: none new — reuses `gateway.run_agent_turn()`, `tasks.py`'s `TaskManager`, `edge.py`'s `EdgeChannel`/`EDGE_METHODS`, `invocation.py`'s `handle_task_status`/`result`/`cancel` exactly as-is. Dart: an on-device speech-to-text package for US4 (voice → text before sending, research D7) and (for US5) reuses `mobile_scanner` (already added in 066) for the QR half of the device deep link; the `netclaw://device/<id>` URI-scheme half needs a deep-link/app-links package (e.g. `app_links` or platform intent filters) — exact package choice is a Phase 2 task detail, not fixed here. (067-ncfed-mobile-command-channel)
- No Border-side schema change — `session_key=f"n2n-edge-{member_id}"` passed to `run_agent_turn` already gives each enrolled device its own agent session (research D6); the per-device conversation history itself (FR-007) is entirely on-device, a second JSON-Lines store mirroring 066's `MessageFeedStore` pattern (`ConversationStore`). (067-ncfed-mobile-command-channel)
- Swift 5.0 (existing `ios/Runner/*.swift`, `SWIFT_VERSION = 5.0` in + None new. Reuses what's already in `pubspec.yaml`: `local_auth ^3.0.2` (071-ios-mobile-port)
- N/A — Secure Enclave key storage is managed entirely by the Keychain/Secure Enclave (071-ios-mobile-port)
- Swift 5.0 (new watch app target + new `WatchRelayPlugin.swift` on the phone + `WatchConnectivity` (Apple system framework, phone + watch sides — no new (072-apple-watch-companion)
- N/A on the watch — it holds no persistent state of its own; every view (Approvals, (072-apple-watch-companion)
- JavaScript ES2022 (ESM), Node 22+ for tooling + three.js `^0.170.0` (existing), `OrbitControls`, (072-hud-2-org-chart)
- N/A — stateless client; all state from `/api/n2n` and `/api/graph` (072-hud-2-org-chart)
- Dart 3.x / Flutter 3.x (extends `mobile/netclaw-mobile/`, SDK constraint `^3.12.2` per pubspec.yaml); Swift 5.0 (extends the `WatchApp Watch App` target from spec 072); Python 3.10+ (the one Border-side addition, `authorization.py`/`service.py`, matching specs 052-072) + `flutter_local_notifications` (new — local notification posting, Darwin/Android notification actions, iOS badge control); existing `firebase_messaging`/`firebase_core` (unchanged, remote-push path stays out of scope per Assumptions); existing `app_links` (extended, not replaced, per research D4); watchOS `AVSpeechSynthesizer` (system framework, no new dependency, watch-side only) (073-push-notifications-sync)
- Extends the existing phone-local JSON-Lines `MessageFeedStore` and whole-file JSON `ConversationStore` (both under the app's documents directory) with new fields — no new store, no new database (073-push-notifications-sync)
- Python 3.10+ (all `scripts/*.py`), Bash (CI wiring, catalog is a Bash array) + None — Python standard library only, per the convention every existing (075-mcp-config-reconciliation)
- N/A — all state is existing repository files; this feature adds no datastore (075-mcp-config-reconciliation)
- Python — **interpreter choice is a live decision, not a default** (see R7). + `nornir` 3.5.0, `napalm` 5.2.0, `netmiko` (>=4,<5 per `nornir-netmiko`), (076-multivendor-cli-driver)
- No database. A generated inventory cache on disk (regenerable, credential-free); an (076-multivendor-cli-driver)
- on-disk cache, one JSON file per `(ostype, version)` under `~/.openclaw/cisco-psirt/`. No (078-cisco-psirt-vulnerability)

- Python 3.10+ + FastMCP (MCP framework), grpcio + grpcio-tools (gRPC transport), pygnmi (gNMI client library), protobuf, cryptography (TLS handling) (003-gnmi-mcp-server)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.10+: Follow standard conventions

## Recent Changes
- 078-cisco-psirt-vulnerability: Added on-disk cache, one JSON file per `(ostype, version)` under `~/.openclaw/cisco-psirt/`. No
- 076-multivendor-cli-driver: Added Python — **interpreter choice is a live decision, not a default** (see R7). + `nornir` 3.5.0, `napalm` 5.2.0, `netmiko` (>=4,<5 per `nornir-netmiko`),
- 075-mcp-config-reconciliation: Added Python 3.10+ (all `scripts/*.py`), Bash (CI wiring, catalog is a Bash array) + None — Python standard library only, per the convention every existing


<!-- MANUAL ADDITIONS START -->

## Adding an MCP Integration

**Follow [docs/ADDING-AN-MCP.md](docs/ADDING-AN-MCP.md)** for every new MCP server or integration,
then run `python3 scripts/reconcile-mcp.py` before pushing. CI runs the same command and fails the
merge on a non-zero exit.

Established by spec 075. It exists because three integrations once shipped hardcoded to a foreign
home directory and were broken for every installer, while nine documented capability counts drifted
unnoticed.

**Never read an exit code through a pipe** — `cmd | tail` reports `tail`'s status, not `cmd`'s. Use
`cmd >/dev/null 2>&1; echo $?`. That mistake misdiagnosed spec 075's central premise.

## DefenseClaw Security Layer

DefenseClaw from Cisco AI Defense is the recommended enterprise security layer for NetClaw. It provides comprehensive protection including OpenShell sandbox, component scanning, runtime guardrails, and SIEM integration.

### Quick Start

```bash
# During installation
./scripts/install.sh
# Answer "y" to "Enable DefenseClaw (recommended)?"

# Or enable later
./scripts/defenseclaw-enable.sh
```

### Key Features

- **Automatic OpenShell Sandbox** - Kernel-level isolation (Landlock, seccomp, network namespaces)
- **Component Scanning** - Skills, MCPs, and plugins scanned before execution
- **CodeGuard Analysis** - Detects credentials, eval, shell commands, SQL injection
- **Runtime Guardrails** - LLM prompt/completion inspection, tool call inspection
- **Audit Logging** - SQLite database with optional SIEM export (Splunk HEC, OTLP)

### Key Commands

```bash
defenseclaw --version              # Check installation
defenseclaw skill scan <name>      # Scan a skill
defenseclaw tool block <tool>      # Block a tool
defenseclaw tool allow <tool>      # Allow a tool
defenseclaw alerts                 # View security alerts
defenseclaw setup guardrail --mode action  # Enable blocking mode
```

### Configuration

Security mode is stored in `~/.openclaw/config/openclaw.json`:

```json
{
  "security": {
    "mode": "defenseclaw"  // or "hobby" for no security
  }
}
```

### Documentation

- **Full Guide**: [docs/DEFENSECLAW.md](docs/DEFENSECLAW.md)
- **Security Principles**: [docs/SOUL-DEFENSE.md](docs/SOUL-DEFENSE.md)
- **Upgrade Guide**: [docs/UPGRADE-TO-DEFENSECLAW.md](docs/UPGRADE-TO-DEFENSECLAW.md)

<!-- MANUAL ADDITIONS END -->
