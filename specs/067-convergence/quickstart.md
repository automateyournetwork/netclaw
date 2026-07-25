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
