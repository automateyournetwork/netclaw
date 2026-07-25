# NetClaw Convergence

**Convergence** is the site operations product path inside NetClaw: HUD **HOME**
tab, metrics stack, device adapters, investigation diary, and the
Alertmanager → alert-receiver → guardian-claw loop.

| Spec | Code | Deploy |
|------|------|--------|
| [`specs/067-convergence/`](../specs/067-convergence/) | [`ui/convergence-api/`](../ui/convergence-api/) · HUD HOME | [`deploy/convergence/`](../deploy/convergence/) |
| Tasks | T070–T073 complete (SoT, SNMP wireless, full OBS, k8s components) | [quickstart](../specs/067-convergence/quickstart.md) |

**Not renamed:** `guardian-claw` (iN2N investigator identity).  
**Legacy pilot:** external `network-guardian-web` in k3s-observability-stack (dual-run via env aliases).

---

## Planes (where things run)

```
┌─────────────────────────────────────────────────────────────┐
│  Agent plane (host)                                         │
│  • OpenClaw gateway + Border                                │
│  • guardian-claw member                                     │
│  • HUD :3001 (ui/netclaw-visual)                            │
│  • alert-receiver :8099  →  services/alert-receiver/        │
│  • Config: ~/.openclaw/.env  (or repo .env)                 │
└───────────────────────────┬─────────────────────────────────┘
                            │ HOME tab /api/home/* proxy
                            │ AM webhook / reinvestigate
┌───────────────────────────▼─────────────────────────────────┐
│  Stack plane (Docker Compose or K3s)                        │
│  • convergence-api :3080 (service name + image)             │
│  • postgres, prometheus, alertmanager, blackbox             │
│  • optional: unifi-exporter, snmp-wireless, full-stack      │
│  • Config: deploy/convergence/.env                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick start

```bash
# 1) Install profile
./scripts/install.sh --profile convergence
./scripts/setup.sh

# 2) Stack env (compose secrets only)
cp deploy/convergence/.env.example deploy/convergence/.env
# Set API_KEYS[].key and match agent-plane token below

# 3) Agent plane (HUD + skills)
# ~/.openclaw/.env:
#   CONVERGENCE_API_URL=http://127.0.0.1:3080
#   CONVERGENCE_API_TOKEN=<same key as API_KEYS>

# 4) Alert receiver (host)
cd services/alert-receiver && cp .env.example .env   # or share root secrets
# sudo cp scripts/systemd/netclaw-alert-receiver.service /etc/systemd/system/
# sudo systemctl enable --now netclaw-alert-receiver

# 5) Bring stack up
./deploy/convergence/render-config.sh
docker compose -f deploy/convergence/docker-compose.yml \
  --env-file deploy/convergence/.env up -d --build
./deploy/convergence/smoke-docker.sh
```

Full OBS overlay: `docker-compose.full.yml` + `--profile full`  
K3s: `deploy/convergence/k8s/` (namespace `netclaw-convergence`)

---

## Alert path (must not be “standalone forever”)

```
Prometheus rules → Alertmanager → services/alert-receiver :8099/webhook
       → OpenClaw/Border → guardian-claw (alert-triage skill)
       → POST/PATCH convergence-api /api/events  (diary)
       → optional Discord + RAG snapshot
```

Triage **Need More** → convergence-api → `ALERT_RECEIVER_URL` `/reinvestigate`
(set in `deploy/convergence/.env` to `http://host.docker.internal:8099/webhook`).

Details: `services/alert-receiver/README.md`, skill `workspace/skills/alert-triage/`.

---

## Knowledge / UniFi API docs

Vendor manuals go in RAG (`~/.openclaw/rag`), not the live Integration API:

- OpenAPI: `https://developer.ui.com/network/v{version}/openapi.json` (type **vendor**)
- Runbook: [knowledge-rag-home-ops.md](./runbooks/knowledge-rag-home-ops.md)

---

## Naming cheat sheet

| Concept | Name |
|---------|------|
| Product / paths | **Convergence** |
| HUD top tab | **HOME** (product surface label) |
| Docker/K8s service | **`convergence-api`** |
| Image | `netclaw-convergence-api:local` |
| Agent env (preferred) | `CONVERGENCE_API_URL` / `CONVERGENCE_API_TOKEN` |
| Aliases | `HOME_API_*`, `NETWORK_GUARDIAN_*` |
| Investigator claw | **guardian-claw** (unchanged) |
| Compose project / K8s NS | `netclaw-convergence` |

---

## Related docs

- [ENV-AND-LAYOUT.md](./ENV-AND-LAYOUT.md) — where secrets live; do not scatter `.env` copies  
- [deploy/convergence/README.md](../deploy/convergence/README.md)  
- [specs/067-convergence/quickstart.md](../specs/067-convergence/quickstart.md)  
- [services/alert-receiver/README.md](../services/alert-receiver/README.md)  
