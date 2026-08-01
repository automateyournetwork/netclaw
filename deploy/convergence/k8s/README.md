# NetClaw Convergence — K3s / Kustomize (080 Phase 4)

Minimal stack matching Docker Home (`deploy/convergence/docker-compose.yml`):

| Service | K8s object | Role |
|---------|------------|------|
| postgres | StatefulSet + PVC | Events diary |
| prometheus | StatefulSet + PVC | Metrics + rules |
| alertmanager | Deployment | Webhook → host **alert-receiver** |
| blackbox | Deployment | WAN / edge probes |
| convergence-api | Deployment + ClusterIP + NodePort **30080** | HOME tab API |
| unifi-exporter | Deployment | Optional Wi‑Fi metrics (needs `UNIFI_API_KEY`) |

Namespace: **`netclaw-convergence`** (isolated from pilot `observability`).

## Layout

```text
k8s/
  base/                    # T040 — full service base (+ T070 Nautobot SoT env)
  components/
    generic-snmp-wireless/ # T071 — opt-in second wireless vendor
    full-stack/             # T072 — opt-in Loki, VictoriaMetrics, Grafana, speedtest
  overlays/greenfield/       # apply this for a clean cluster (base only)
  overlays/greenfield-full/  # base + both components (T071 + T072)
  overlays/pilot/            # T041 stub + see OVERLAY-PILOT.md
  secret.example.yaml
  OVERLAY-PILOT.md      # T041 notes vs k3s-observability-stack
  SMOKE.md              # T042 checklist
  smoke-k8s.sh
```

## Quick start

```bash
cd /path/to/netclaw

# 1. Secrets
cp deploy/convergence/k8s/secret.example.yaml deploy/convergence/k8s/secret.yaml
# edit: PGPASSWORD, JWT_SECRET, API_KEYS key, optional UNIFI_API_KEY
kubectl apply -f deploy/convergence/k8s/secret.yaml

# 2. Alert webhook (agent plane host)
# edit deploy/convergence/k8s/base/configs/alertmanager.yml  →  your alert-receiver URL

# 3. Build & load convergence-api image (k3s example)
docker build -t netclaw-convergence-api:local ui/convergence-api
docker save netclaw-convergence-api:local | sudo k3s ctr images import -

# 4. Apply
kubectl apply -k deploy/convergence/k8s/overlays/greenfield

# 5. Smoke
./deploy/convergence/k8s/smoke-k8s.sh
# or walk SMOKE.md
```

### Wire the HUD

```bash
# Port-forward:
kubectl -n netclaw-convergence port-forward svc/convergence-api 3080:3000
# Or NodePort on a node IP: http://<node-ip>:30080

# ~/.openclaw/.env
HOME_API_URL=http://127.0.0.1:3080
HOME_API_TOKEN=dev-convergence-api-key-change-me   # must match API_KEYS[].key
systemctl --user restart netclaw-hud.service
```

## Optional components (T071, T072, Phase 8)

Kustomize [Components](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/#components)
extend the base stack — same idea as Docker Compose profiles:

| Component | Adds | K8s equivalent of Docker profile |
|-----------|------|-----------------------------------|
| [`components/generic-snmp-wireless/`](./components/generic-snmp-wireless/) | Second wireless vendor via `snmp_exporter` (T071) | `generic-snmp-wireless` |
| [`components/full-stack/`](./components/full-stack/) | Loki, VictoriaMetrics, Grafana, speedtest CronJob (T072) | `full` / `speedtest` |
| [`components/device-snmp/`](./components/device-snmp/) | Campus switch IF-MIB via snmp_exporter (Phase 8) | `device-snmp` |
| [`components/device-syslog/`](./components/device-syslog/) | Promtail UDP 1514 → Loki (Phase 8 T091) | `full` + `device-syslog` |

Prebuilt overlays:

```bash
# T071 + T072
kubectl apply -k deploy/convergence/k8s/overlays/greenfield-full

# Phase 8 device telemetry (full-stack + SNMP + syslog)
kubectl apply -k deploy/convergence/k8s/overlays/greenfield-device-telemetry
```

Or add components to your own overlay:

```yaml
resources:
  - ../../base
components:
  - ../../components/full-stack
  - ../../components/device-snmp
  - ../../components/device-syslog
```

Each SNMP component's README documents a **manual Prometheus config edit** —
kustomize's `configMapGenerator` embeds file contents verbatim and cannot
merge scrape jobs into the existing `prometheus.yml` ConfigMap.

Syslog uses **hostPort 1514/UDP** on the node running Promtail — point campus
devices at the node IP (see `components/device-syslog/README.md`).

## Pilot cluster

If you already run `k3s-observability-stack`, read **[OVERLAY-PILOT.md](./OVERLAY-PILOT.md)** before applying greenfield. Short version: greenfield uses a **different namespace** and can dual-run; do not blindly replace pilot resource names.

## Docker vs K3s

| Mode | Use when |
|------|----------|
| Docker | Single host lab / easy trial (`deploy/convergence/docker-compose.yml`) |
| K3s | Cluster already (or prefer) running OBS; product packaging for multi-node |

Agent + **guardian-claw** stay on the NetClaw host by default.
