# Device syslog → Loki (Phase 8 greenfield, Phase 10 T141)

Receives syslog from switches/firewalls and ships it to Convergence **Loki**.

## Path

```text
devices --RFC3164/BSD--> syslog-gateway :1514 udp+tcp
        --RFC5424 octet-framed--> promtail :1601 --> Loki
```

**Why the gateway exists.** Promtail's `syslog` target parses IETF **RFC5424
only**. Cisco IOS-XE and pfSense emit **RFC3164/BSD** by default, and promtail
rejects those streams outright:

```text
error parsing syslog stream: expecting a version value in the range 1-999
```

That failure is silent from the operator's side — the port is open, packets
arrive, and Loki stays empty. Reconfiguring every customer device to emit RFC5424
is not an acceptable product default (spec FR-035), so a syslog-ng front-end
accepts vendor-default syslog and re-emits RFC5424.

**Do not point devices at :1601.** That bypasses the gateway and re-creates the
silent drop.

### Timestamps

The gateway stamps messages with **receive time** (`keep-timestamp(no)`), not the
device's own timestamp. RFC3164 carries no timezone and no year, so trusting it
shifts every line by the device's UTC offset — observed live on pfSense: lines
landed ~6h in the past, outside every "last 15m" dashboard window while ingest
metrics looked perfectly healthy. Operators whose devices are NTP-synced and emit
RFC5424 (with real offsets) can set `keep-timestamp(yes)` in
`deploy/convergence/syslog-gateway/syslog-ng.conf`.

## Requirements

- Loki up (`--profile full` on `docker-compose.full.yml`)
- Promtail + syslog-gateway (`--profile full` or `--profile device-syslog`)

```bash
cd deploy/convergence
docker compose -f docker-compose.yml -f docker-compose.full.yml \
  --env-file .env --profile full --profile device-syslog up -d
```

Default listen: **UDP + TCP 1514** on the host (`SYSLOG_HOST_PORT`).

## Labels

| Label | Source |
|-------|--------|
| `job` | static `device-syslog` |
| `device_name`, `host` | syslog message hostname; falls back to the sending IP |
| `app` | syslog app-name / program (`filterlog`, `unbound`, `kea-dhcp4`, …) |
| `level` | syslog severity |
| `site` | static |

`device_name` lands as the sending **IP** when the device does not put a hostname
in the header (common on Cisco unless `logging origin-id hostname` is set, and on
some pfSense builds). Prefer configuring the device to send its hostname so
`device_name` matches the SNMP inventory (e.g. `HomeSwitch01`).

## Device config (example IOS-XE)

```text
logging host <netclaw-host-ip> transport udp port 1514
logging trap informational
logging origin-id hostname          ! makes device_name = hostname, not IP
service timestamps log datetime msec localtime show-timezone
ntp server <ntp-host>               ! keep clocks honest
```

pfSense: Status → System Logs → Settings → Remote Logging, target
`<netclaw-host-ip>:1514`.

## Test

```bash
# BSD/RFC3164 — the vendor default. This must work end to end.
printf '<134>Jul 27 20:59:02 pfsense filterlog[12345]: smoke test\n' \
  | nc -u -w1 127.0.0.1 1514

# Ingest health: entries climbing, parse errors flat at 0
curl -s http://127.0.0.1:9080/metrics \
  | grep -E 'promtail_syslog_target_(entries|parsing_errors)_total'

# Query Loki
curl -sG 'http://127.0.0.1:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={job="device-syslog"}' \
  --data-urlencode 'limit=5' --data-urlencode 'direction=backward' | head -c 500
```

Prometheus scrapes promtail (`job=promtail`) so this can never regress silently.
Alerts: `SyslogIngestParseFailing`, `SyslogIngestNoEntries`, `LogShipDown` in
`prometheus/alerts/device.rules.yml`.

## Agent logs (T093)

Host rsyslog template: `scripts/rsyslog-netclaw-convergence.conf`  
Point `*.* @127.0.0.1:1514` (or host LAN IP) at the gateway.

Optional: bind-mount host logs into Promtail:

```yaml
# compose override idea
volumes:
  - /tmp/bgp-daemon-v2.log:/var/log/netclaw/mesh.log:ro
```

## K3s (T091 + T141)

```bash
# Overlay: base + full-stack (Loki) + device-snmp + device-syslog
kubectl apply -k deploy/convergence/k8s/overlays/greenfield-device-telemetry
```

Component: `deploy/convergence/k8s/components/device-syslog/`

- One Deployment, two containers: `syslog-gateway` (syslog-ng, **hostPort 1514
  udp+tcp** = the syslog destination) and `promtail` (RFC5424 on pod-local 1601)
- Pushes to in-cluster `http://loki:3100/loki/api/v1/push`
- Labels match Docker

See component README for smoke curls and IOS-XE examples.
