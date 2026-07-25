# Device syslog → Loki (Phase 8 greenfield)

Receives UDP syslog from switches/firewalls and ships to Convergence **Loki**
via Promtail.

## Requirements

- Loki up (`--profile full` on `docker-compose.full.yml`)
- Promtail (`--profile full` or `--profile device-syslog`)

```bash
cd deploy/convergence
docker compose -f docker-compose.yml -f docker-compose.full.yml \
  --env-file .env --profile full --profile device-syslog up -d
```

Default listen: **UDP 1514** on the host (`SYSLOG_HOST_PORT`).

## Switch config (example IOS-XE)

```text
logging host <netclaw-host-ip> transport udp port 1514
logging trap informational
```

Use a hostname that matches `device_name` labels used in SNMP targets
(e.g. `HomeSwitch01`) when possible.

## Test

```bash
# From NetClaw host (or any host that can reach :1514)
logger -n 127.0.0.1 -P 1514 -d -t HomeSwitch01 'convergence syslog smoke test'

# Query Loki (after a few seconds)
curl -sG 'http://127.0.0.1:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={job="device-syslog"}' \
  --data-urlencode 'limit=5' | head -c 500
```

## Agent logs (T093)

Host rsyslog template: `scripts/rsyslog-netclaw-convergence.conf`  
Point `*.* @127.0.0.1:1514` (or host LAN IP) when using this Promtail receiver
instead of the pilot OBS collector.

Optional: bind-mount host logs into Promtail:

```yaml
# compose override idea
volumes:
  - /tmp/bgp-daemon-v2.log:/var/log/netclaw/mesh.log:ro
```

## K3s (T091)

```bash
# Overlay: base + full-stack (Loki) + device-snmp + device-syslog
kubectl apply -k deploy/convergence/k8s/overlays/greenfield-device-telemetry
```

Component: `deploy/convergence/k8s/components/device-syslog/`

- Promtail Deployment with **hostPort 1514/UDP** (node IP = syslog destination)
- Pushes to in-cluster `http://loki:3100/loki/api/v1/push`
- Labels match Docker: `job=device-syslog`, `device_name` from syslog hostname

See component README for smoke curls and IOS-XE examples.
