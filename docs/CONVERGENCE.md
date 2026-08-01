# NetClaw Convergence

**Convergence** is the site operations product path inside NetClaw: HUD **HOME**
tab, metrics stack, device adapters, investigation diary, and the
Alertmanager → alert-receiver → guardian-claw loop.

| Spec | Code | Deploy |
|------|------|--------|
| [`specs/080-convergence/`](../specs/080-convergence/) | [`ui/convergence-api/`](../ui/convergence-api/) · HUD HOME | [`deploy/convergence/`](../deploy/convergence/) |
| Tasks | T070–T073 complete (SoT, SNMP wireless, full OBS, k8s components) | [quickstart](../specs/080-convergence/quickstart.md) |

**Not renamed:** `guardian-claw` (iN2N investigator identity).  
**Legacy pilot:** external `network-guardian-web` in k3s-observability-stack (dual-run via env aliases).

### Models (brain vs alert triage)

Set once in **repo `.env`**, apply with script or HUD:

| SoT | Apply |
|-----|--------|
| `NETCLAW_BRAIN_MODEL` | Interactive Border / chat |
| `NETCLAW_ALERT_TRIAGE_MODEL` | T2 investigation hooks |

```bash
./scripts/netclaw-apply-models.sh show|apply|preset split
# HUD: Convergence → Models → Apply & restart gateway
```

Full operator guide: [`docs/MODELS.md`](./MODELS.md) · env layout: [`ENV-AND-LAYOUT.md`](./ENV-AND-LAYOUT.md).

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

## Telemetry architecture

See **[`CONVERGENCE-TELEMETRY-ARCHITECTURE.md`](./CONVERGENCE-TELEMETRY-ARCHITECTURE.md)** for:

- System diagram (OTel Collector → Loki/VictoriaLogs + Prometheus/VictoriaMetrics)
- What gets structured at ingest (filterlog CSV, Cisco mnemonics, RFC3164 fields)
- Label cardinality rules (FR-042)
- Metric names, log-derived metrics, alert rules
- Retention tiers (14d interactive, 365d long-term)
- Inventory and setup flow (Nautobot or manual → apply → boards)
- Key decisions with rationale
- Phase 12: RAG-driven vendor profiles (new platform = one markdown doc)

---

## Quick start — local Docker (primary path)

Same host runs: agent plane + compose stack + alert-receiver.

```bash
# 1) Install profile (once)
./scripts/install.sh --profile convergence && ./scripts/setup.sh

# 2) Stack env
cp -n deploy/convergence/.env.example deploy/convergence/.env
# Edit: API_KEYS[].key, PGPASSWORD, JWT_SECRET, UNIFI_* if using Wi‑Fi metrics

# 3) Agent plane (~/.openclaw/.env) — match token to API_KEYS
#   CONVERGENCE_API_URL=http://127.0.0.1:3080
#   CONVERGENCE_API_TOKEN=<same as API_KEYS[].key>

# 4) Alert receiver (host systemd) — diary URL = local API
# services/alert-receiver/.env:
#   NETWORK_GUARDIAN_URL=http://127.0.0.1:3080
#   NETWORK_GUARDIAN_TOKEN=<same key>
#   OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789
#   OPENCLAW_HOOK_TOKEN=<gateway hook token>
sudo cp scripts/systemd/netclaw-alert-receiver.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now netclaw-alert-receiver
curl -fsS http://127.0.0.1:8099/health

# 5) Bring stack up (optional --profile unifi)
cd deploy/convergence
./render-config.sh    # writes AM webhook → host.docker.internal:8099
docker compose -f docker-compose.yml --env-file .env --profile unifi up -d --build
./smoke-docker.sh

# 6) HUD
systemctl --user restart netclaw-hud.service
# Open http://127.0.0.1:3001 → HOME  (status: /api/home/status → configured:true)
```

**Verified path:** Alertmanager → `host.docker.internal:8099/webhook` → alert-receiver
→ gateway/investigation → POST diary on `convergence-api` (`/api/events`).

Full OBS overlay: `docker-compose.full.yml` + `--profile full`

### Tear down old `netclaw-home` stack

```bash
docker compose -p netclaw-home down --remove-orphans
docker volume rm netclaw-home_home-amdata netclaw-home_home-pgdata netclaw-home_home-promdata 2>/dev/null || true
```

---

## Flip Docker → K3s (same agent plane)

Agent plane (HUD, alert-receiver, OpenClaw) stays on the host. Only the **stack**
moves into the cluster.

| | Docker local | K3s |
|--|--------------|-----|
| Namespace / project | compose `netclaw-convergence` | K8s NS `netclaw-convergence` |
| API reachability | `http://127.0.0.1:3080` | NodePort **30080** or port-forward |
| AM → webhook | `host.docker.internal:8099` | Host IP or NodePort to alert-receiver (e.g. `http://192.168.3.252:8099/webhook`) |
| Agent env | `CONVERGENCE_API_URL=http://127.0.0.1:3080` | `CONVERGENCE_API_URL=http://<node>:30080` |

```bash
# A) Stop Docker stack (optional — free ports)
cd deploy/convergence
docker compose -f docker-compose.yml --env-file .env --profile unifi down

# B) Secrets + apply
cp deploy/convergence/k8s/secret.example.yaml /tmp/convergence-secret.yaml
# fill API_KEYS, PGPASSWORD, JWT, UNIFI_API_KEY
kubectl apply -f /tmp/convergence-secret.yaml
kubectl apply -k deploy/convergence/k8s/overlays/greenfield
# or greenfield-full for Loki/VM/Grafana components

# C) Point agent plane at NodePort
# ~/.openclaw/.env  CONVERGENCE_API_URL=http://127.0.0.1:30080
# services/alert-receiver/.env  NETWORK_GUARDIAN_URL=http://127.0.0.1:30080
sudo systemctl restart netclaw-alert-receiver
systemctl --user restart netclaw-hud.service

# D) Patch Alertmanager webhook if not using host.docker.internal
# In secret/config: ALERT_RECEIVER_URL=http://<host-LAN-IP>:8099/webhook
```

Smoke: `deploy/convergence/k8s/SMOKE.md` · offline `./deploy/convergence/k8s/smoke-k8s.sh`

**Do not** deploy into the pilot `observability` namespace (legacy Network Guardian).

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
| HUD top tab | **CONVERGENCE** (internal route id remains `home`) |
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
- [specs/080-convergence/quickstart.md](../specs/080-convergence/quickstart.md)  
- [services/alert-receiver/README.md](../services/alert-receiver/README.md)  
- **Greenfield PR (not built yet):** campus switch SNMP + NetClaw agent
  metrics/logs as optional components —
  [`specs/080-convergence/device-telemetry-greenfield.md`](../specs/080-convergence/device-telemetry-greenfield.md)
  (distinct from optional AP-only `generic-snmp-wireless`)

### Phase 8 greenfield status

| Capability | Status | How to enable |
|------------|--------|----------------|
| Campus switch IF-MIB SNMP | **Shipped** | `--profile device-snmp` / K3s `device-snmp` |
| Device syslog → Loki | **Shipped** | `--profile full` + promtail (UDP 1514) |
| K3s syslog component | **Shipped** | `k8s/components/device-syslog` (T091) |
| HOME Devices + Overview SNMP KPI | **Shipped** | `ifOperStatus{job="device_snmp"}` (T087) |
| Setup wizard SNMP/syslog prompts | **Shipped** | when `convergence-device-snmp` / `-syslog` selected (T083) |
| NetClaw token/cost metrics | **Shipped** | `openclaw-token-exporter` + job `netclaw-openclaw` |
| NetClaw agent log ship | **Template** | `scripts/rsyslog-netclaw-convergence.conf` |
| Grafana NetClaw quota board | **Shipped** | `--profile full` provisions dashboards |
| Network switch Grafana board | **Shipped** | `device-snmp-switches.json` |
| Alert → investigation safety rails | **Shipped** | [CONVERGENCE-ALERT-SAFETY.md](./CONVERGENCE-ALERT-SAFETY.md) |
