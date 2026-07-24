# T042 — kubectl apply smoke checklist (NetClaw Home K3s)

Manual checklist after applying the greenfield stack. Automated subset: `./smoke-k8s.sh`.

## Prerequisites

- [ ] `kubectl` points at the target cluster (`kubectl cluster-info`)
- [ ] Default StorageClass exists (`kubectl get storageclass`) — PVCs for postgres + prometheus
- [ ] Image available on nodes: `netclaw-home-api:local`  
      ```bash
      docker build -t netclaw-home-api:local ui/home-api
      # k3s example:
      docker save netclaw-home-api:local | sudo k3s ctr images import -
      ```
- [ ] Secrets applied:
  ```bash
  cp deploy/home/k8s/secret.example.yaml deploy/home/k8s/secret.yaml
  # edit PGPASSWORD, JWT_SECRET, API_KEYS, optional UNIFI_API_KEY
  kubectl apply -f deploy/home/k8s/secret.yaml
  ```
- [ ] Alertmanager webhook host reachable from the cluster (edit `base/configs/alertmanager.yml`)

## Apply

```bash
# Dry-run build
kubectl kustomize deploy/home/k8s/overlays/greenfield | head

# Apply
kubectl apply -k deploy/home/k8s/overlays/greenfield
```

- [ ] `kubectl apply -k …` exits 0
- [ ] No unexpected resource collisions (especially if pilot `observability` is present — different namespace)

## Workloads

```bash
kubectl -n netclaw-home get pods,svc,pvc
kubectl -n netclaw-home rollout status deploy/home-api --timeout=120s
kubectl -n netclaw-home rollout status deploy/alertmanager --timeout=120s
kubectl -n netclaw-home rollout status deploy/blackbox --timeout=120s
kubectl -n netclaw-home rollout status sts/postgres --timeout=180s
kubectl -n netclaw-home rollout status sts/prometheus --timeout=180s
```

| Check | Pass criteria |
|-------|----------------|
| [ ] postgres | Pod Running, Ready 1/1 |
| [ ] prometheus | Pod Running, Ready 1/1 |
| [ ] alertmanager | Pod Running, Ready 1/1 |
| [ ] blackbox | Pod Running, Ready 1/1 |
| [ ] home-api | Pod Running, Ready 1/1 |
| [ ] unifi-exporter | Running (may be Ready with empty metrics if no API key) |
| [ ] PVCs | Bound (postgres-data, prometheus-data) |

## HTTP / API

Port-forward (or use NodePort 30080 on a node IP):

```bash
kubectl -n netclaw-home port-forward svc/home-api 3080:3000 &
kubectl -n netclaw-home port-forward svc/prometheus 9090:9090 &
kubectl -n netclaw-home port-forward svc/alertmanager 9093:9093 &
```

| Check | Command / expectation |
|-------|------------------------|
| [ ] home-api healthz | `curl -fsS http://127.0.0.1:3080/healthz` → 200 |
| [ ] prometheus ready | `curl -fsS http://127.0.0.1:9090/-/ready` → 200 |
| [ ] alertmanager ready | `curl -fsS http://127.0.0.1:9093/-/ready` → 200 |
| [ ] authenticated health | `curl -fsS -H "Authorization: Bearer <API_KEYS.key>" 'http://127.0.0.1:3080/api/health?site=home'` → 200 JSON |
| [ ] prom targets | `curl -fsS http://127.0.0.1:9090/api/v1/targets` → activeTargets ≥ 1 |
| [ ] NodePort (optional) | `curl -fsS http://<node-ip>:30080/healthz` → 200 |

## Config sanity

| Check | Pass criteria |
|-------|----------------|
| [ ] Alertmanager webhook | ConfigMap `alertmanager-config` contains agent webhook URL (not empty) |
| [ ] Prometheus scrape DNS | Targets resolve `blackbox:9115`, `home-api` probe, `unifi-exporter:9899` |
| [ ] Secrets not in git | `secret.yaml` untracked / gitignored |

## HUD wire-up

```bash
# ~/.openclaw/.env
HOME_API_URL=http://127.0.0.1:3080   # or http://<node-ip>:30080
HOME_API_TOKEN=<same as API_KEYS key>
systemctl --user restart netclaw-hud.service
```

- [ ] Open HUD → **HOME** → Overview shows live (not degraded) data
- [ ] If dual-run with pilot: confirm you changed URL off pilot Guardian intentionally

## Cleanup (lab only)

```bash
kubectl delete -k deploy/home/k8s/overlays/greenfield
kubectl delete -f deploy/home/k8s/secret.yaml
# PVCs may remain — delete if you want a clean slate:
# kubectl -n netclaw-home delete pvc --all
```

## Automated script

```bash
./deploy/home/k8s/smoke-k8s.sh           # build + optional live checks if cluster reachable
./deploy/home/k8s/smoke-k8s.sh --apply   # also kubectl apply -k greenfield (after secrets)
```
