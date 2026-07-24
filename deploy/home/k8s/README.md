# NetClaw Home — K3s / Kustomize (067 Phase 4)

Minimal stack matching Docker Home (`deploy/home/docker-compose.yml`):

| Service | K8s object | Role |
|---------|------------|------|
| postgres | StatefulSet + PVC | Events diary |
| prometheus | StatefulSet + PVC | Metrics + rules |
| alertmanager | Deployment | Webhook → host **alert-receiver** |
| blackbox | Deployment | WAN / edge probes |
| home-api | Deployment + ClusterIP + NodePort **30080** | HOME tab API |
| unifi-exporter | Deployment | Optional Wi‑Fi metrics (needs `UNIFI_API_KEY`) |

Namespace: **`netclaw-home`** (isolated from pilot `observability`).

## Layout

```text
k8s/
  base/                 # T040 — full service base
  overlays/greenfield/  # apply this for a clean cluster
  overlays/pilot/       # T041 stub + see OVERLAY-PILOT.md
  secret.example.yaml
  OVERLAY-PILOT.md      # T041 notes vs k3s-observability-stack
  SMOKE.md              # T042 checklist
  smoke-k8s.sh
```

## Quick start

```bash
cd /path/to/netclaw

# 1. Secrets
cp deploy/home/k8s/secret.example.yaml deploy/home/k8s/secret.yaml
# edit: PGPASSWORD, JWT_SECRET, API_KEYS key, optional UNIFI_API_KEY
kubectl apply -f deploy/home/k8s/secret.yaml

# 2. Alert webhook (agent plane host)
# edit deploy/home/k8s/base/configs/alertmanager.yml  →  your alert-receiver URL

# 3. Build & load home-api image (k3s example)
docker build -t netclaw-home-api:local ui/home-api
docker save netclaw-home-api:local | sudo k3s ctr images import -

# 4. Apply
kubectl apply -k deploy/home/k8s/overlays/greenfield

# 5. Smoke
./deploy/home/k8s/smoke-k8s.sh
# or walk SMOKE.md
```

### Wire the HUD

```bash
# Port-forward:
kubectl -n netclaw-home port-forward svc/home-api 3080:3000
# Or NodePort on a node IP: http://<node-ip>:30080

# ~/.openclaw/.env
HOME_API_URL=http://127.0.0.1:3080
HOME_API_TOKEN=dev-home-api-key-change-me   # must match API_KEYS[].key
systemctl --user restart netclaw-hud.service
```

## Pilot cluster

If you already run `k3s-observability-stack`, read **[OVERLAY-PILOT.md](./OVERLAY-PILOT.md)** before applying greenfield. Short version: greenfield uses a **different namespace** and can dual-run; do not blindly replace pilot resource names.

## Docker vs K3s

| Mode | Use when |
|------|----------|
| Docker | Single host lab / easy trial (`deploy/home/docker-compose.yml`) |
| K3s | Cluster already (or prefer) running OBS; product packaging for multi-node |

Agent + **guardian-claw** stay on the NetClaw host by default.
