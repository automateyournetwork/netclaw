# Environment files & repository layout

How secrets and config are split for NetClaw Convergence (and the wider monorepo).

## Do not put one giant `.env` in every folder

| Location | Role | Commit? |
|----------|------|---------|
| **`~/.openclaw/.env`** (preferred) or **repo `.env`** | **Agent plane** — LLM keys, MCP credentials, Nautobot/UniFi tokens for skills, `CONVERGENCE_API_URL` / `CONVERGENCE_API_TOKEN` for HUD | **No** (gitignored) |
| **`deploy/convergence/.env`** | **Stack plane** — Postgres, JWT, `API_KEYS` for convergence-api, Alertmanager webhook URL, UNIFI_* for exporters | **No** |
| **`services/alert-receiver/.env`** | **Host webhook service** — gateway URL, Discord, skill scoping, Nautobot webhook secret | **No** |
| **`*.env.example`** next to each of the above | Documented templates only | **Yes** |
| **`mcp-servers/*/.env.example`** | Optional local-dev templates for that MCP | **Yes** |
| **`migration-staging/members/*/.env`** | Generated member slices (least privilege) | **No** |

### Why not a single root `.env` for everything?

1. **Docker Compose** only injects what you pass via `--env-file`; stacking the entire agent secret set into the API container is a least-privilege leak.
2. **systemd alert-receiver** and **OpenClaw** already load `~/.openclaw/.env` (or their own).
3. **Member claws** get a *slice* of secrets (`in2n-profiles`) — not the monorepo root file.

### Recommended practice

```text
~/.openclaw/.env          ← human + agent (one place for CONVERGENCE_API_*, NAUTOBOT_*, UNIFI_API_KEY for skills)
deploy/convergence/.env   ← compose only; API_KEYS key == CONVERGENCE_API_TOKEN above
services/alert-receiver/.env  ← can symlink values from openclaw or stay small
```

Keep **tokens identical** across planes where they must match (HUD token ↔ `API_KEYS[].key`).

**Investigation diary alignment (critical for T2 close-out):**  
`services/alert-receiver` and **guardian-claw** must write to the **same** diary API.
For Docker Convergence that is `http://127.0.0.1:3080` with the same
`API_KEYS` / `NETWORK_GUARDIAN_TOKEN`.  
Member SoT: `migration-staging/members/guardian-claw/.env`  
(`NETWORK_GUARDIAN_URL` / `HOME_API_URL`). If the member still points at the
k3s pilot Guardian URL, cases open on Docker and close on pilot (or nowhere).

Agent env (preferred names):

```bash
CONVERGENCE_API_URL=http://127.0.0.1:3080
CONVERGENCE_API_TOKEN=dev-convergence-api-key-change-me
# Still accepted: HOME_API_URL / HOME_API_TOKEN / NETWORK_GUARDIAN_*
```

Stack env (`deploy/convergence/.env`):

```bash
API_KEYS='[{"id":"hud","name":"HUD","key":"dev-convergence-api-key-change-me","role":"admin","sites":["home"]}]'
ALERT_RECEIVER_URL=http://host.docker.internal:8099/webhook
```

Templates: [`.env.example`](../.env.example), [`deploy/convergence/.env.example`](../deploy/convergence/.env.example), [`services/alert-receiver/.env.example`](../services/alert-receiver/.env.example).

### LLM models (brain vs alert triage)

**Do not** hand-edit model ids only in `~/.openclaw/openclaw.json` as your long-term
workflow. Use the model SoT variables in **repo `.env`** (or Convergence → Models),
then apply:

| Variable | Role |
|----------|------|
| `NETCLAW_BRAIN_MODEL` | Interactive main / HUD chat |
| `NETCLAW_ALERT_TRIAGE_MODEL` | T2 investigation hooks (thin `alert` agent) |
| `NETCLAW_ALERT_FALLBACK_MODEL` | Optional alert fallback |
| `OLLAMA_BASE_URL` / `OLLAMA_API_KEY` | Synced into gateway systemd env on apply |

```bash
# Edit netclaw/.env, then:
./scripts/netclaw-apply-models.sh show
./scripts/netclaw-apply-models.sh apply
# or presets / one-shot:
./scripts/netclaw-apply-models.sh preset split|cloud-flash|local
./scripts/netclaw-apply-models.sh set --brain anthropic/claude-sonnet-5 \
  --alert anthropic/claude-haiku-4-5-20251001
```

Full guide (including Sonnet/Haiku recommendations): **[MODELS.md](./MODELS.md)**.

Editing `.env` alone does **not** reconfigure a running gateway — always **apply**
(script or HUD **Convergence → Models → Apply & restart gateway**).

---

## Repository map (Convergence-focused)

```text
netclaw/
├── README.md                 # Product overview + workstream links
├── docs/
│   ├── CONVERGENCE.md        # This product path (start here)
│   ├── ENV-AND-LAYOUT.md     # This file
│   ├── MODELS.md             # Brain / alert model SoT + apply script
│   └── runbooks/             # Operator procedures
├── specs/067-convergence/    # Spec kit + tasks
├── ui/
│   ├── netclaw-visual/       # HUD (COMMAND | HOME | Models)
│   └── convergence-api/      # HOME backend (Node)
├── deploy/convergence/       # Docker + K3s for OBS + convergence-api
├── services/
│   └── alert-receiver/       # Alertmanager / Nautobot webhooks (host systemd)
├── scripts/
│   ├── install.sh / setup.sh # Installer
│   ├── netclaw-apply-models.sh  # .env → openclaw models + gateway restart
│   ├── netclaw-investigation-policy.sh
│   ├── netclaw-alert-agent-profile.sh
│   ├── lib/                  # catalog, install-steps
│   ├── systemd/              # unit templates
│   └── in2n-*.py             # risk / member helpers
├── workspace/skills/         # alert-triage, wifi-diagnosis, rag, …
└── mcp-servers/              # Vendor MCPs (each may ship .env.example)
```

### What moved

| Old | New |
|-----|-----|
| `deploy/home/` | `deploy/convergence/` |
| `ui/home-api/` | `ui/convergence-api/` |
| Docker/K8s service `home-api` | service **`convergence-api`** |
| `scripts/alert-receiver/` | **`services/alert-receiver/`** |

Installer catalog: `convergence-core`, `convergence-metrics`, `convergence-unifi`, …  
Profile: `./scripts/install.sh --profile convergence`

---

## Scripts sprawl (honest status)

`scripts/` still holds many historical Part 15 / lab / enablement helpers. For
**Convergence day-to-day** you mainly need:

| Script / service | Purpose |
|------------------|---------|
| `install.sh` + `setup.sh` | Install + env wizard |
| `ensure-guardian-claw.py` | Investigator member |
| `services/alert-receiver/` | Webhooks (not optional for live triage) |
| `deploy/convergence/*` | Stack lifecycle |
| `docs-site-to-pdf.py` | Optional RAG crawl of HTML docs |
| `mcp-call.py` | Tooling for MCP smoke |

Part 15 BGP lab scripts under `scripts/` (if present) are **lab**, not Convergence.
See [scripts/README.md](../scripts/README.md) for the current map.

---

## Checklist: new machine

1. [ ] Clone repo; `./scripts/install.sh --profile convergence`
2. [ ] Fill `~/.openclaw/.env` (`CONVERGENCE_API_*`, SoT tokens, Discord)
3. [ ] `cp deploy/convergence/.env.example deploy/convergence/.env` and match API key
4. [ ] Install `services/alert-receiver` systemd unit; confirm `:8099/health`
5. [ ] `docker compose … up` or kustomize apply
6. [ ] HUD → HOME shows live data; fire a test alert end-to-end
