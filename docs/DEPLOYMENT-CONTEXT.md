# NetClaw-Convergence — Deployment Context & WSL Migration Guide

**Purpose:** Single source of truth for how *this* fork (`netclaw-convergence`)
is deployed, and what it takes to run it on the WSL host that also manages the
observability (OB) stack — so both projects live in one IDE window.

**Last updated:** 2026-07-21

---

## Current Deployment (as-is)

| Component | Where | Notes |
|-----------|-------|-------|
| NetClaw border + members | host `Netclaw` @ **192.168.3.252** | this repo checked out at `/home/ubuntu/netclaw` |
| OB stack (Prometheus, Alertmanager, Grafana, Loki, VictoriaMetrics) | **K3s cluster, 192.168.13.0/24** | managed from WSL |
| Alertmanager (external) | **192.168.13.204:9093** | MetalLB LoadBalancer IP |
| Prometheus/Loki/VM | via Grafana proxy `https://grafana.internal.byrnbaker.me` | ClusterIP, not directly reachable |
| pfSense firewall | **192.168.3.1:440** | REST API v2 |
| UniFi controller | **192.168.100.10:11443** | |
| Nautobot (SoT) | `https://nautobot.internal.byrnbaker.me` | |
| Network Guardian dashboard | `https://network-guardian.localedgedatacenter.com` | event diary API |

**The migration goal:** move the NetClaw runtime onto the **WSL host** (where the
OB stack / K3s is managed), so the netclaw-convergence repo and the OB stack repo
are editable in the same IDE window and the two evolve together.

---

## Runtime Stack (what NetClaw needs)

| Dependency | Version here | Install |
|-----------|--------------|---------|
| Node.js | v24.15.0 (nvm) | `nvm install 24` |
| OpenClaw | 2026.7.1 | `npm i -g openclaw` |
| Python venv | 3.12 | `python3 -m venv .venv && .venv/bin/pip install -e mcp-servers/*/` |
| systemd (user units) | — | WSL needs `systemd=true` in `/etc/wsl.conf` |

### systemd user services (the running pieces)
```
openclaw-gateway.service              # the brain/gateway on :18789
openclaw-token-exporter.service       # Prometheus token/cost metrics
netclaw-mesh.service                  # BGP + NCFED eN2N + iN2N Border
netclaw-member-byrns-risk-*.service   # iN2N members (cml, guardian-claw, pyats, secops, viz)
netclaw-alert-receiver.service        # Alertmanager webhook → investigation (:8099)
```

All run as `User=ubuntu`, `WorkingDirectory` under `/home/ubuntu/netclaw`, using
`/home/ubuntu/netclaw/.venv/bin/python` and the nvm-managed `openclaw`.

---

## WSL Migration Checklist

### 1. WSL prerequisites
```ini
# /etc/wsl.conf  — REQUIRED for systemd user services
[boot]
systemd=true
```
Restart WSL (`wsl --shutdown` from Windows) after editing.

### 2. Clone + toolchain
```bash
git clone git@github.com:byrn-baker/netclaw-convergence.git ~/netclaw
cd ~/netclaw
# Node via nvm
nvm install 24 && npm i -g openclaw
# Python venv + MCP servers
python3 -m venv .venv
.venv/bin/pip install -e mcp-servers/rag-mcp   # + other pip-installable MCP servers
```

### 3. Config that must move with you
- **`.env`** — NOT in git (108 vars). Copy it securely from 192.168.3.252.
  Contains all API keys, device creds, ISP details, Guardian token.
- **`~/.openclaw/openclaw.json`** — the live gateway config (MCP servers, model
  providers, allowlist, hooks). NOT in the repo (repo has `config/openclaw.json`
  as the template). The repo template now carries the anthropic provider fix and
  wildcard allowlist (commit 88338bb) so a fresh deploy is closer to correct.
- **`~/.openclaw/.env`** — the file OpenClaw reads for `${VAR}` substitution in
  `openclaw.json`. Must contain RAG_*, NETCLAW_DIR, ANTHROPIC_API_KEY, etc.
- **`~/.openclaw/rag/`** — the RAG vector store (ingested docs). Copy if you want
  to keep BISQUE/RAG knowledge; otherwise re-ingest.
- **`~/.openclaw/memory/`** — MemPalace memory store.
- **`~/.openclaw/n2n/`** — federation DB, keys, grants (peer trust with John/Nick).

### 4. Addresses that change on WSL
Because NetClaw would run ON the WSL host (same L2/L3 as the K3s cluster if WSL
is bridged, or NAT'd if not), revisit:
- `PROMETHEUS_URL` / `LOKI_URL` / `GRAFANA_URL` — still via the Grafana proxy, no change
- **Alertmanager webhook target** — Alertmanager (192.168.13.204:9093) must be
  able to reach the alert-receiver. On WSL under NAT, the receiver's `:8099`
  may not be reachable from the cluster without a port-proxy or bridged networking.
  This is the #1 thing to validate post-move.
- `OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789` — stays local, fine.

### 5. systemd unit files
Copy `~/.config/systemd/user/netclaw-*.service` and `openclaw-*.service`, then:
```bash
systemctl --user daemon-reload
systemctl --user enable --now openclaw-gateway netclaw-mesh netclaw-alert-receiver
loginctl enable-linger $USER   # so user services survive logout (WSL: keep a session)
```

---

## Critical Config Facts (learned the hard way)

See `docs/blog/2026-07-21-alert-investigation-debugging.md` for the full story.

1. **Model allowlist** (`agents.defaults.models` in openclaw.json) gates which
   models the agent may use. Uses wildcards: `moonshot/kimi-k3`, `anthropic/*`,
   `ollama/*`.
2. **Provider registration** (`models.providers.<name>.models[]`) is separate and
   also required. Anthropic `api` must be `anthropic-messages` (not `anthropic`).
3. **Model IDs are real API IDs** — query `curl https://api.anthropic.com/v1/models`.
   Current: `claude-sonnet-5`, `claude-haiku-4-5-20251001`, `claude-opus-4-8`.
4. **Heartbeat is disabled** — all `HEARTBEAT.md` files are empty. See
   `.kiro/steering/heartbeat-disabled.md`. Do NOT let upstream re-enable it; it
   burns tokens (243K context × every 30 min).
5. **Always restart via systemd**, never `kill -HUP`:
   `systemctl --user restart openclaw-gateway`.
6. **Model routing:** border = `NETCLAW_BRAIN_MODEL`; alert hook =
   `NETCLAW_ALERT_TRIAGE_MODEL`; members set per-member `N2N_MEMBER_MODEL`.
   **SoT + apply:** edit repo `.env`, then `./scripts/netclaw-apply-models.sh apply`
   (or Convergence → Models). Do not rely on hand-edited `openclaw.json` alone.
   Recommended Anthropic pair when funded: brain `anthropic/claude-sonnet-5`,
   alert `anthropic/claude-haiku-4-5-20251001` (full guide: `docs/MODELS.md`).

---

## Known Cost/Architecture Gaps (see docs/known-issues.md)

- **243K MCP tool-schema bloat** — every session loads all 800+ MCP tools.
  Mitigated for alert investigations via delegation to guardian-claw (scoped
  toolset, no bloat).
- **guardian-claw delegation restored** — the alert-triage skill now instructs
  the border to delegate via `n2n_route` (trusted skill content, not webhook
  payload). guardian-claw runs on `ollama/deepseek-v4-flash:cloud` (free, 1M
  context). Cost per alert: ~$0.01 (down from ~$0.73 on Sonnet 5 direct).

---

## Keeping in Sync with Upstream

- `origin` = your fork (`byrn-baker/netclaw-convergence`)
- `upstream` = `automateyournetwork/netclaw`
- Pull upstream: `git fetch upstream && git merge upstream/main`
- **Protected local changes** (guarded by `.kiro/steering/`):
  - Heartbeat disabled (`HEARTBEAT.md` files empty)
  - Convergence-specific skills: `isp-sla-claim`, band-aware Wi-Fi alerts
  - `.env` model/address config
- Upstream blog posts in `docs/blog/` (n2n, rag, cert, etc.) are John's milestone
  records — leave them; deleting causes merge churn. Your own posts are dated and
  clearly attributed (e.g. the 2026-07-21 debugging post-mortem).
