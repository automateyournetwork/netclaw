# netclaw Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-07-08

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
- 050-computer-use-desktop: Added Bash (install function, matching every existing `scripts/lib/install-steps.sh` entry), Markdown (skill documentation) + OpenClaw's ClawHub `computer-use` skill (consumed as-is, no fork); apt packages `xvfb`, `xfce4`, `xfce4-terminal`, `xdotool`, `scrot`, `imagemagick`, `dbus-x11`, `x11vnc`, `novnc`, `websockify` (all confirmed present in this host's apt repositories; `dbus-x11`, `imagemagick`, `scrot`, `xvfb` already installed)
- 049-merge-modular-installer: Added Bash (matches every existing NetClaw install/enable script and PR #96's own implementation), Python 3.10+ (for the coverage-check script, extending the existing `scripts/verify-inventory-counts.py` pattern) + None beyond what's already vendored — PR #96's own `scripts/lib/*.sh`, the repo's existing Python stdlib-only tooling convention
- 048-chrome-devtools-browser-inspection: Added Node.js 18+ (official `chrome-devtools-mcp` server — no NetClaw-authored server code); Bash (setup/enable script, consistent with `scripts/*-enable.sh` convention); Markdown (skill + MCP documentation) + `chrome-devtools-mcp` (npm package, official Chrome DevTools team release, MIT-style OSS), Node.js 18+, a locally installed Chrome/Chromium binary (stable channel by default)


<!-- MANUAL ADDITIONS START -->

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
