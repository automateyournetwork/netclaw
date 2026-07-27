# Device syslog → OTel Collector → Loki + VictoriaLogs

**Phase 11 (T146–T149).** Decision record:
[`specs/067-convergence/otel-convergence.md`](../../../../specs/067-convergence/otel-convergence.md)

## Path

```text
devices --syslog RFC3164--> otel-collector :1514 udp+tcp
                              ├── parse to structured fields
                              ├──> Loki          (14d, interactive, bounded labels)
                              └──> VictoriaLogs  (365d, long-term, full fields)
```

One collector, no gateway hop. The T141 syslog-ng front-end is **retired** — it
existed only because promtail's syslog target parses RFC5424 only, and the OTel
syslog receiver speaks rfc3164 natively.

Promtail still runs, but only for **host** sources (OpenClaw file logs, systemd
journal). It no longer touches device syslog.

## What you get per log line

| Field | Source | Loki | VictoriaLogs |
|---|---|---|---|
| `device_name` | inventory map on sender IP → message hostname → sender IP | label | field |
| `site`, `service.name` | static | label | field |
| `level` / `severity_text` | parsed priority | label (`level`) | field |
| `appname`, `facility`, `priority`, `proc_id` | RFC3164 parse | field | field |
| `mnemonic`, `sev_level`, `sequence` | Cisco vendor parse | field | field |
| `action`, `reason`, `direction`, `fw_interface`, `protocol`, `ip_version` | pfSense filterlog parse | field | field |
| `src_ip`, `dst_ip`, `src_port`, `dst_port`, `tracker` | pfSense filterlog parse | field (**never a label**) | field |
| `message` | parsed body | line body | `_msg` |

**Labels are a bounded set on purpose.** `appname` and `mnemonic` are structured
fields, never labels — see the cardinality note below.

## Vendor reality (measured, not assumed)

| Vendor | Format actually sent | Handling |
|---|---|---|
| pfSense | RFC3164, frequently **without a hostname** | Parsed by the rfc3164 receiver; `device_name` comes from the sender IP via the inventory map |
| Cisco IOS/IOS-XE | **Not RFC3164-compliant** — `<189>1834: *Jul 27 22:12:00.456: %LINK-3-UPDOWN: ...` (sequence number, `*`-prefixed timestamp, no hostname) | rfc3164 parse fails, then a `regex_parser` operator extracts `priority`, `sequence`, `device_time`, `mnemonic`, `sev_level`, `message` |
| Anything else | unknown | Passes through with a raw body and a correct `device_name`. **Never dropped** (FR-035). |

That Cisco quirk is why the pilot stack used a raw `udplog` receiver. Here the
lines are structured instead, which is the point of the migration.

## Why labels stay bounded

The previous promtail path derived an `app` **label** from the first token before
the colon. On Cisco that token is the mnemonic (`%SEC_LOGIN-5-LOGIN_SUCCESS`), and
IOS has hundreds — so every new message type minted a new Loki stream. Unbounded
label cardinality. The collector keeps those values as fields and promotes only
`device_name`, `site`, `service.name` (plus Loki's own `level`).

## Timestamps

The collector stamps **receive time** (`set(time, observed_time)`), not the
device's timestamp. RFC3164 carries no timezone and no year; trusting it put live
pfSense lines ~6h in the past — outside every "last 15m" panel while ingest
metrics looked healthy. Devices with NTP and RFC5424 could keep device time; this
fleet cannot.

## Device identity mapping

`otel-config.yaml` holds a generated block:

```yaml
# BEGIN netclaw-convergence-device-map
- set(attributes["device_name"], "HomeSwitch01") where attributes["net.peer.ip"] == "192.168.3.2"
# END netclaw-convergence-device-map
```

Sender IP wins over the hostname in the message: it is authoritative, present on
every datagram, and cannot be shaped by message content. T154 will generate this
block from `convergence.yaml` inventory so operators never hand-edit it.

## Run it

```bash
cd deploy/convergence
docker compose -f docker-compose.yml -f docker-compose.full.yml \
  --env-file .env --profile full --profile device-syslog up -d
```

Listens on **UDP + TCP 1514** (`SYSLOG_HOST_PORT`) — unchanged from the gateway,
so existing device config and generated checklists stay valid.

## Device config

```text
! Cisco IOS-XE
logging host <netclaw-host-ip> transport udp port 1514
logging trap informational
logging origin-id hostname     ! optional; sender-IP mapping already names the device
```

pfSense: **Status → System Logs → Settings → Remote Logging**, target
`<netclaw-host-ip>:1514`.

## Verify

```bash
# ingest health — accepted climbing, refused flat at 0
curl -s http://127.0.0.1:8888/metrics | grep -E \
  '^otelcol_(receiver_(accepted|refused)|exporter_(sent|send_failed))_log_records'

# Loki (bounded labels)
curl -sG http://127.0.0.1:3100/loki/api/v1/query \
  --data-urlencode 'query=sum by (device_name) (count_over_time({job="device-syslog"}[5m]))'

# VictoriaLogs (same line, full structured fields)
curl -sG http://127.0.0.1:9428/select/logsql/query --data-urlencode 'query=* | stats count() as n'

# every provisioned board query: OK / EMPTY / FAIL
./deploy/convergence/smoke-log-panels.sh
```

Prometheus scrapes the collector as `job=otel-collector`. Alerts:
`SyslogIngestRefusing`, `LogExportFailing`, `SyslogIngestNoEntries`,
`LogIngestDown` (and `HostLogShipDown` for promtail).

## Firewall log detail (filterlog)

pfSense `filterlog` CSV is parsed at ingest into fields, so firewall analysis is
field-based rather than positional-regex-based:

```logql
# top blocked sources
topk(15, sum by (attributes_src_ip) (count_over_time(
  {job="device-syslog"} | json | attributes_appname="filterlog"
  | attributes_action="block" [1h])))

# blocks by segment
sum by (attributes_fw_interface) (rate(
  {job="device-syslog"} | json | attributes_appname="filterlog"
  | attributes_action="block" [5m]))
```

Measured coverage: **100%** of live filterlog lines. v4 appears with 23 and 29
fields, v6 with 20 and 22, and ICMP variants carry no ports — so the port group is
optional. Requiring it dropped ~35% of records in the first cut.

**src_ip and dst_ip are fields, never labels.** External scanner IPs are unbounded;
promoting them would explode Loki stream count. Grouping at query time is safe.

**Enrichment is not done here.** GeoIP/ASN/reputation lookups happen in NetClaw's
`pfsense-threat-intel` skill at investigation time, where AbuseIPDB (1k/day) and
GreyNoise budgets are spent only on IPs that survive triage — not on every one of
~17k filterlog lines per 30 minutes. pfBlockerNG on pfSense itself continues to do
reputation-based blocking before anything reaches this pipeline.

## Known cosmetic artifact

The `loki.resource.labels` hint attribute is visible as a field in VictoriaLogs.
Both exporters share one pipeline, so the hint cannot be stripped for one branch
without splitting pipelines via a `forward` connector — not worth the complexity
for a metadata field.

## K3s

Still the promtail-based `components/device-syslog` until **T156** ports this
collector. Docker is the leading edge of Phase 11.
