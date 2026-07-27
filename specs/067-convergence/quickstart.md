# Quickstart: NetClaw Home (067)

## Spec / tracking
```bash
cd /path/to/netclaw
ls specs/067-convergence/
# Track work in tasks.md — update checkboxes as slices land
```

## PR1 — HUD tabs
```bash
cd ui/netclaw-visual
npm install
npm run build
systemctl --user restart netclaw-hud.service
# Open http://localhost:3001 → COMMAND | HOME
```

## PR2 — Live HOME (dual-run pilot Guardian)
```bash
# ~/.openclaw/.env
HOME_API_URL=https://network-guardian.example.com
HOME_API_TOKEN=<api-key>
systemctl --user restart netclaw-hud.service
```

## PR3 — Docker minimal (this host)

Single-host stack: **postgres + prometheus + alertmanager + blackbox + convergence-api**  
Optional: **unifi-exporter** (`--profile unifi`).

```bash
cd /path/to/netclaw

# 1. Local secrets (never commit .env)
cp deploy/convergence/.env.example deploy/convergence/.env
# Edit: PGPASSWORD, JWT_SECRET, API_KEYS key, ALERT_RECEIVER_URL
# Keep single-quotes around JSON values in .env so Compose preserves them.

# 2. Render Alertmanager → host alert-receiver webhook
./deploy/convergence/render-config.sh
# Default: http://host.docker.internal:8099/webhook
# Ensure alert-receiver is listening on the host (e.g. :8099)

# 3. Start core stack
docker compose -f deploy/convergence/docker-compose.yml --env-file deploy/convergence/.env up -d --build

# 4. Smoke
./deploy/convergence/smoke-docker.sh

# 5. Point HUD at local convergence-api
# ~/.openclaw/.env
#   HOME_API_URL=http://127.0.0.1:3080
#   HOME_API_TOKEN=dev-convergence-api-key-change-me   # must match API_KEYS[].key
systemctl --user restart netclaw-hud.service
# Open http://localhost:3001 → HOME
```

### Optional UniFi metrics

```bash
# deploy/convergence/.env
#   UNIFI_HOST=https://<controller>
#   UNIFI_API_KEY=<Integration API key>
docker compose -f deploy/convergence/docker-compose.yml --env-file deploy/convergence/.env --profile unifi up -d
```

See [deploy/convergence/README.md](../../deploy/convergence/README.md) and [adapters/unifi](../../deploy/convergence/adapters/unifi/README.md).

### Default ports

| Service | Port |
|---------|------|
| convergence-api | 3080 |
| prometheus | 9090 |
| alertmanager | 9093 |
| blackbox | 9115 |
| unifi-exporter | 9899 |

## PR4 — K3s minimal

Same logical services as Docker, namespace `netclaw-convergence` (does not replace pilot `observability`).

```bash
cd /path/to/netclaw

# 1. Secrets
cp deploy/convergence/k8s/secret.example.yaml deploy/convergence/k8s/secret.yaml
# edit PGPASSWORD, JWT_SECRET, API_KEYS; optional UNIFI_API_KEY
kubectl apply -f deploy/convergence/k8s/secret.yaml

# 2. Alert webhook → agent alert-receiver (edit before apply)
#    deploy/convergence/k8s/base/configs/alertmanager.yml

# 3. Image on cluster nodes
docker build -t netclaw-convergence-api:local ui/convergence-api
docker save netclaw-convergence-api:local | sudo k3s ctr images import -

# 4. Apply + smoke
kubectl apply -k deploy/convergence/k8s/overlays/greenfield
./deploy/convergence/k8s/smoke-k8s.sh
# Full checklist: deploy/convergence/k8s/SMOKE.md
# Pilot dual-run notes: deploy/convergence/k8s/OVERLAY-PILOT.md

# 5. HUD
# kubectl -n netclaw-convergence port-forward svc/convergence-api 3080:3000
# or NodePort :30080
# HOME_API_URL=http://127.0.0.1:3080
# HOME_API_TOKEN=<API_KEYS key>
```

## PR5 — Installer + guardian ensure

```bash
cd /path/to/netclaw

# Install Convergence components (catalog profile)
./scripts/install.sh --profile convergence
# Or add: ./scripts/install.sh --add "convergence-core convergence-metrics visual-hud"

# Credentials + adapters (only prompts for selected components)
./scripts/setup.sh
# Summary line: risk=… investigator=… convergence-api=… deploy=…

# Idempotent investigator ensure (standalone OK anytime)
python3 scripts/ensure-guardian-claw.py
# Existing guardian-claw → no-op; missing → provision + staging scaffold

# Config example
cp config/convergence.example.yaml ~/.openclaw/convergence.yaml

# HUD unit template: scripts/systemd/netclaw-hud.service
# Pilot deprecation path: deploy/convergence/DEPRECATION-PILOT.md
```

## PR6 — HOME Triage loop

1. Open HUD → **HOME** → **Triage**
2. Escalated cases list on the left; select one for notes + feedback
3. **Correct / Partial / Incorrect / Resolve** → `PATCH /api/events/:id`
4. **Need More** → `POST /api/events/:id/reinvestigate` (reopens as investigating; convergence-api may call host `ALERT_RECEIVER_URL` `/reinvestigate`)
5. Diary and triage show **RAG id** when `rag_document_id` is set

Contract: `specs/067-convergence/contracts/convergence-api.md`

## Deploy mode choice
| Mode | Use when |
|------|----------|
| Docker | Single host lab / easy trial |
| K3s | Already run OBS in cluster (like this pilot) |

Agent + **guardian-claw** stay on the NetClaw host by default.

---

## Greenfield device SNMP (Phase 8, optional)

Campus switches (e.g. Catalyst) — **not** wireless `generic-snmp-wireless`.

```bash
cd deploy/convergence
# Sample targets HomeSwitch01/02/04 in prometheus/prometheus.yml
# Community: adapters/device-snmp/snmp.yml → auths.public_v2.community

docker compose --env-file .env --profile device-snmp up -d
docker compose --env-file .env exec prometheus wget -qO- --post-data='' http://127.0.0.1:9090/-/reload

curl -s 'http://127.0.0.1:9117/snmp?target=192.168.3.2&module=if_mib&auth=public_v2' | head
curl -sG 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=count by (device_name) (ifOperStatus{job="device_snmp"})'

# Formal smoke (T088) — requires ≥1 healthy device_snmp target + device_name labels
./deploy/convergence/smoke-device-snmp.sh
```

Generate scrape fragment:

```bash
python3 scripts/render-device-snmp-scrape.py \
  --targets deploy/convergence/adapters/device-snmp/targets.example.yml
```

### NetClaw agent metrics (optional)

```bash
systemctl --user enable --now openclaw-token-exporter   # scripts/openclaw-metrics
# job netclaw-openclaw scrapes host.docker.internal:9110
```

Full detail: [`device-telemetry-greenfield.md`](./device-telemetry-greenfield.md).

### Device syslog + Loki (optional)

```bash
cd deploy/convergence
docker compose -f docker-compose.yml -f docker-compose.full.yml \
  --env-file .env --profile full --profile device-syslog up -d
# switches: logging host <this-ip> transport udp port 1514
logger -n 127.0.0.1 -P 1514 -d -t HomeSwitch01 'test'
```

Agent rsyslog: `sudo cp scripts/rsyslog-netclaw-convergence.conf /etc/rsyslog.d/60-netclaw-convergence.conf`

### K3s greenfield device telemetry (Phase 8)

```bash
kubectl apply -f deploy/convergence/k8s/secret.yaml
kubectl apply -k deploy/convergence/k8s/overlays/greenfield-device-telemetry
# Patch prometheus-config with device_snmp scrape targets (see device-snmp README)
# Syslog: hostPort 1514/udp on the node — logging host <node-ip> transport udp port 1514
```

HOME Devices and Overview pick up `ifOperStatus{job="device_snmp"}` automatically
when Prometheus has series (no pilot OBS required). Grafana board:
**Convergence — Campus Switches (device_snmp)** under full-stack / Docker full.

Grafana for Convergence Docker is on host port **:3300** (not :3000). Prefer
recording rules `interface_*` / label `interface_name` for named legends once
Phase 10 templates are applied.

## Phase 10 — Telemetry setup productization

**Goal:** inventory (manual or Nautobot) → vendor SNMP templates → apply →
named interfaces → curated boards → device checklist. No hand-edit of
Prometheus for day-1 greenfield.

**Detail:** [`telemetry-setup.md`](./telemetry-setup.md) · tasks T120–T138.

### Apply path (PR1 — T125–T128, T135–T136) ✅

```bash
# 1. Inventory: edit config/convergence.yaml (or copy example)
#    device_telemetry.snmp.targets: name, ip, role, vendor, template
cp config/convergence.example.yaml ~/.openclaw/convergence.yaml   # optional
# secrets: SNMP_COMMUNITY in deploy/convergence/.env only

# 2. Apply (managed Prom section + snmp modules + checklist + reload)
./scripts/convergence-telemetry-apply.sh
# dry-run:
./scripts/convergence-telemetry-apply.sh --dry-run

# 3. Verify (T136 / SC-010)
./deploy/convergence/smoke-device-snmp.sh
curl -sG 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=count by (device_name) (interface_status{interface_name!=""})'
# Grafana: http://127.0.0.1:3300 → folder Convergence
# Checklist: deploy/convergence/generated/device-config-checklist.md
```

### Wizard / SoT (PR2 — T129–T131, T137) ✅

```bash
# Interactive menu (manual | nautobot | netbox | yaml):
./scripts/convergence-telemetry-setup.sh

# Nautobot → select → write ~/.openclaw/convergence.yaml (needs NAUTOBOT_*)
./scripts/convergence-telemetry-setup.sh --mode nautobot --select all --write
# dry-run only (no write):
./scripts/convergence-telemetry-setup.sh --mode nautobot --select all --dry-run

# Manual CSV: name=ip[:vendor]
./scripts/convergence-telemetry-setup.sh --mode manual \
  --csv 'HomeSwitch01=192.168.3.2:cisco,pfSense-FW01=192.168.3.1:pfsense' --write

# Import targets YAML
./scripts/convergence-telemetry-setup.sh --mode yaml \
  --import deploy/convergence/adapters/device-snmp/targets.example.yml --write

# Chain apply after write:
./scripts/convergence-telemetry-setup.sh --mode nautobot --select 'HomeSwitch,pfSense' --write --apply

# Smoke (T137) — no live Prom mutation required
./deploy/convergence/smoke-telemetry-setup.sh
# MODE=yaml ./deploy/convergence/smoke-telemetry-setup.sh

# Device config MoP: deploy/convergence/adapters/device-snmp/device-config-snippets.md
# Generated checklist (after apply): deploy/convergence/generated/device-config-checklist.md
```

### Holistic Grafana suite (Network · Security · NetClaw)

Grafana: **http://127.0.0.1:3300** → folder **Convergence**  
Doc: [`deploy/convergence/grafana/README.md`](../../deploy/convergence/grafana/README.md)

| Board | UID | Story |
|-------|-----|--------|
| **Network** | `convergence-network` | Health, WAN, named campus IF, UniFi, edge |
| **Security** | `convergence-security` | Firing alerts, edge/guest access, syslog/auth |
| **NetClaw** | `convergence-netclaw` | Tokens by provider, investigations T0–T2, gateway/N2N logs |

Legacy pilot boards are under `grafana/provisioning/dashboards/legacy/` (not loaded).

Open items on this suite (spec US10): pfSense block/DNS **metrics** depth still has
no installable exporter (T143) — though `filterlog` and `unbound` **logs** now
reach Loki via T141, so Security's log sections are live. Mesh/N2N log panels
should move off message-regex onto `job`/`unit` selectors (T142).

#### Independent test (SC-010–SC-013)

```bash
# SC-010 — apply lab inventory → named interfaces within ~5m
./scripts/convergence-telemetry-apply.sh --config config/convergence.example.yaml
./deploy/convergence/smoke-device-snmp.sh
curl -sG 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=count(interface_status{interface_name!=""})'

# SC-011 — Nautobot select → yaml (no live apply required)
./deploy/convergence/smoke-telemetry-setup.sh   # MODE=nautobot

# SC-012 — named campus interface legends (:3300)
# Open http://127.0.0.1:3300 → Convergence → Network → "Campus switching"
# Legends/table show interface_name (e.g. GigabitEthernet1/0/1), not ifIndex-only

# SC-014 — exactly three provisioned boards, legacy parked
ls deploy/convergence/grafana/provisioning/dashboards/json/    # 3 files
ls deploy/convergence/grafana/provisioning/dashboards/legacy/   # inert pilot boards

# SC-016 — vendor-default (RFC3164) syslog ingest  [T141 — shipped]
# devices -> :1514 syslog-gateway (RFC3164->RFC5424) -> promtail :1601 -> Loki
printf '<134>Jul 27 20:59:02 pfsense filterlog[12345]: smoke test\n' \
  | nc -u -w1 127.0.0.1 1514

# entries climbing, parse errors must stay 0
curl -s http://127.0.0.1:9080/metrics \
  | grep -E 'promtail_syslog_target_(entries|parsing_errors)_total'

# streams labelled by device_name / app, stamped at receive time (not 6h behind)
curl -sG http://127.0.0.1:3100/loki/api/v1/query \
  --data-urlencode 'query=sum by (device_name,app) (count_over_time({job="device-syslog"}[5m]))'

# ingest can no longer fail silently — promtail is scraped and alerted on
curl -sG 'http://127.0.0.1:9090/api/v1/query' --data-urlencode 'query=up{job="promtail"}'

# SC-013 — checklist has syslog host:port + SNMP_COMMUNITY env name
grep -E 'SNMP_COMMUNITY|Syslog destination|1514' \
  deploy/convergence/generated/device-config-checklist.md

# Alerts: investigate labels + named-interface annotations
curl -s http://127.0.0.1:9090/api/v1/rules | python3 -c \
  "import sys,json; print([r['name'] for g in json.load(sys.stdin)['data']['groups'] for r in g['rules'] if r.get('type')=='alerting'])"
```

## Models (brain vs alert triage)

**Source of truth:** repo `.env` (or Convergence tab → **Models**):

| Variable | Used for |
|----------|----------|
| `NETCLAW_BRAIN_MODEL` | Interactive main / HUD chat (`agents.defaults`) |
| `NETCLAW_ALERT_TRIAGE_MODEL` | T2 investigations (`hooks.mappings[alert].model` + agent `alert`) |
| `NETCLAW_ALERT_FALLBACK_MODEL` | Optional alert fallback |
| `OLLAMA_BASE_URL` / `OLLAMA_API_KEY` | Synced into `~/.openclaw/gateway.systemd.env` |

```bash
# Edit netclaw/.env, then project into live OpenClaw + restart gateway:
./scripts/netclaw-apply-models.sh show
./scripts/netclaw-apply-models.sh apply
./scripts/netclaw-apply-models.sh preset cloud-flash   # or local | split
./scripts/netclaw-apply-models.sh set \
  --brain ollama/voytas26/openclaw-qwen3vl-8b-opt \
  --alert ollama/deepseek-v4-flash:cloud
```

HUD: **Convergence → Models** → edit / preset → **Apply & restart gateway**
(`POST /api/models` on the HUD server).

OpenClaw does **not** auto-reload model ids from `.env` alone — always run apply
(or the HUD button) so `openclaw.json` + `gateway.systemd.env` stay in sync.

## Investigation policy (Phase 9 — cost control)

**Default product posture:** most alerts should **not** open multi-tool LLM
investigations. Policy file (when Phase 9 is implemented):

```text
~/.openclaw/investigation-policy.yaml
```

Seed example (after T107): `deploy/convergence/config/investigation-policy.example.yaml`

| Preset | Behavior |
|--------|----------|
| `observe-only` | T0 only — metrics / Discord / diary; no auto multi-tool LLM |
| `triage-cheap` | T1 one-shot summarize allowed where configured |
| `investigate-critical` | T2 only for explicit allowlisted alertnames |

**Open T2 as hygiene improves** (no code deploy): add an `allow_t2` entry for the
alertname, reload policy (≤60s cache or SIGHUP). Preset for a small critical set:

```bash
./scripts/netclaw-investigation-policy.sh seed-investigate-critical
# opens WanHardDown / SwitchLinkLost(critical) / DeviceSnmpExporterDown only
```

See [`investigation-policy.md`](./investigation-policy.md).

**Thin T2 agent (required before real auto-investigate is affordable):**

```bash
# Ensure hook:alert runs as agent id `alert` with a slim MCP allowlist
# (interactive `main` keeps the full zoo).
./scripts/netclaw-alert-agent-profile.sh apply
./scripts/netclaw-alert-agent-profile.sh validate
./scripts/netclaw-investigation-policy.sh show
```

Without the thin profile, an allowlisted T2 still hits the full interactive MCP
set on `main` — high schema tax. Seed:
`deploy/convergence/config/alert-agent.example.json`.

Related safety for SNMP: do not reintroduce per-idle-port investigate=true rules
([`docs/CONVERGENCE-ALERT-SAFETY.md`](../../docs/CONVERGENCE-ALERT-SAFETY.md)).
