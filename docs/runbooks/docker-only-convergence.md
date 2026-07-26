# Docker-only Convergence (pilot k3s scaled down)

**Date:** 2026-07-26  
**Goal:** Single OBS + diary path for E2E testing — **Docker Compose Convergence**, not the k3s `observability` pilot.

## What was done

1. **k3s namespace `observability`**: all Deployments / StatefulSets scaled to **0**; node-exporter DaemonSet pinned off; speedtest CronJob **suspended**. PVCs/data retained (reversible).
2. **Env SoT** pointed at local Docker ports:

| Variable | Docker value |
|----------|----------------|
| `CONVERGENCE_API_URL` / `HOME_API_URL` / `NETWORK_GUARDIAN_URL` | `http://127.0.0.1:3080` |
| Token | match `deploy/convergence/.env` `API_KEYS[].key` (e.g. `dev-home-api-key-change-me`) |
| `PROMETHEUS_URL` | `http://127.0.0.1:9090` |
| `ALERTMANAGER_URL` | `http://127.0.0.1:9093` |
| `GRAFANA_URL` | `http://127.0.0.1:3300` |
| `LOKI_URL` | `http://127.0.0.1:3100` |
| `VICTORIAMETRICS_URL` | `http://127.0.0.1:8428` |

Files updated: `netclaw/.env`, `~/.openclaw/.env`, `services/alert-receiver/.env`,  
`migration-staging/members/guardian-claw/.env`, `secops/.env`, `gateway.systemd.env`.

3. **Agent plane** remains host systemd (OpenClaw, alert-receiver, members) — only OBS/diary is Docker.

## Verify pilot is down

```bash
kubectl -n observability get deploy,sts,pods
# expect READY 0/0, no Running pods (Completed jobs OK)
```

## Verify Docker path

```bash
docker ps --format '{{.Names}}' | grep netclaw-convergence
curl -sf http://127.0.0.1:3080/healthz
curl -sf http://127.0.0.1:9090/-/ready
curl -sf http://127.0.0.1:3001/api/home/status   # dualRun should be false
./scripts/netclaw-apply-models.sh show
./deploy/convergence/smoke-device-snmp.sh
```

## Bring pilot back (if needed)

```bash
kubectl -n observability scale deploy --all --replicas=1
# StatefulSets: scale each to 1 as needed
kubectl -n observability scale sts prometheus --replicas=1
# … loki, victoriametrics, guardian-postgres, etc.
kubectl -n observability patch cronjob speedtest -p '{"spec":{"suspend":false}}'
# Restore node-exporter nodeSelector if required
```

Then re-point env to pilot URLs only if you intentionally dual-run again (not recommended).

## Why pilot was taken down

Both stacks could webhook the same host alert-receiver and write **different** diary backends. That broke T2 close-out (case opened on Docker, closed on pilot). Docker-only keeps one pipe.
