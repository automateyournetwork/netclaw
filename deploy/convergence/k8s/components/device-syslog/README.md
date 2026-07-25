# K3s component: device-syslog (Phase 8 T091)

UDP syslog receiver (Promtail) → Convergence **Loki**.

Parity of Docker:

```bash
docker compose -f docker-compose.yml -f docker-compose.full.yml \
  --profile full --profile device-syslog up -d
```

## Prerequisites

- `components/full-stack` (or any overlay that deploys Service `loki` on port 3100)
- Namespace `netclaw-convergence` (same as base / full-stack)

## Include in an overlay

```yaml
# overlays/greenfield-device-telemetry/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
components:
  - ../../components/full-stack
  - ../../components/device-snmp
  - ../../components/device-syslog
```

```bash
kubectl apply -k deploy/convergence/k8s/overlays/greenfield-device-telemetry
```

## Network path

| Path | How |
|------|-----|
| Campus devices → node | **hostPort 1514/UDP** on the node running the pod |
| In-cluster Service | `promtail-device-syslog:1514/udp` |
| Host rsyslog (agent) | `*.* @<node-ip>:1514` — see `scripts/rsyslog-netclaw-convergence.conf` |

IOS-XE example:

```text
logging host <k3s-node-ip> transport udp port 1514
logging trap informational
```

Prefer a hostname that matches SNMP `device_name` labels (e.g. `HomeSwitch01`).

## Smoke

```bash
# From a host that can reach the node IP
logger -n <node-ip> -P 1514 -d -t HomeSwitch01 'k3s convergence syslog smoke'

# Query Loki (port-forward if needed)
kubectl -n netclaw-convergence port-forward svc/loki 3100:3100 &
curl -sG 'http://127.0.0.1:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={job="device-syslog"}' \
  --data-urlencode 'limit=5'
```

## Labels

| Label | Source |
|-------|--------|
| `job` | `device-syslog` |
| `device_name` / `host` | syslog message hostname |
| `app` | syslog app name |
| `peer_ip` | connection peer |
| `site` | `home` (edit ConfigMap for multi-site) |

## Relation to pilot OBS

Pilot `k3s-observability-stack` rsyslog collectors stay in namespace `observability`.
This component is self-contained for greenfield Convergence.
