# Architecture decision: OTel Collector as the Convergence telemetry hub

**Status**: Accepted 2026-07-27 (operator decision)  
**Supersedes**: promtail + syslog-gateway log ingest (T141), snmp_exporter metric
collection (T126/T128) — both stay until the phased cutover below completes.  
**Spec**: [`spec.md`](./spec.md) US11 / FR-036–FR-042 · tasks T145–T156

## Decision

Convergence adopts **OpenTelemetry Collector** as the single ingest hub for
device telemetry, matching the pilot `k3s-observability-stack` design:

```text
                       ┌─────────────────────────────────────────┐
   devices ──syslog──▶ │                                          │──▶ Loki (14d)
   (RFC3164/5424)      │            otel-collector                │──▶ VictoriaLogs (365d)
                       │  syslog receiver  ·  snmp receivers      │
   devices ◀──SNMP───  │                                          │──▶ VictoriaMetrics
                       └─────────────────────────────────────────┘    (prometheusremotewrite)
```

- **Logs**: dual-export to **Loki** (14d, interactive) and **VictoriaLogs**
  (365d, long-term) — the pilot's split.
- **Metrics**: OTel SNMP receivers replace `snmp_exporter`, exported via
  `prometheusremotewrite`.
- **Prometheus stays** for scrape-based collectors it already owns (blackbox,
  unifi-exporter, alert-receiver, token exporter, promtail-replacement health)
  and remains the alerting engine.

## Why (operator rationale, recorded)

1. **Structured logs, not flat lines.** A parser at ingest produces typed fields
   (facility, severity, hostname, appname, structured data) instead of a raw line
   that every consumer has to regex. This is the primary driver.
2. **Scales better.** One collector process handles syslog + SNMP + (later) flows
   rather than three sidecars, and OTel's batching/queueing is built for volume.
3. **Already invested.** The pilot config is proven against this exact fleet
   (3 Cisco switches, pfSense, UniFi APs) and was written by the operator.

## Verified facts (measured, not assumed)

Probed with `otel/opentelemetry-collector-contrib:0.104.0` against HomeSwitch01
(`deploy/convergence/otel/probe-snmp-names.yaml`, read-only SNMP):

### Metric names are already identical — no rename needed

| OTel metric | Prometheus name emitted | Current Convergence name | Match |
|---|---|---|---|
| `interface.status` (gauge, `{state}`) | `interface_status` | `interface_status` | ✅ |
| `interface.octets.in` (sum, `By`) | `interface_octets_in_bytes_total` | `interface_octets_in_bytes_total` | ✅ |
| `interface.errors.in` (sum, `{errors}`) | `interface_errors_in_total` | `interface_errors_in_total` | ✅ |
| `interface.admin.status` (gauge) | `interface_admin_status` | *(not collected today)* | ➕ new |

The unit-suffix behaviour of `prometheusremotewrite` (`By` → `_bytes`, monotonic
sum → `_total`, annotation units like `{errors}`/`{state}` dropped) lands exactly
on the names the Phase 10 recording rules already synthesise. **The
`device-recording.rules.yml` label_replace chain becomes unnecessary** — OTel
emits the final names directly.

### Labels get cleaner, and match what the boards want

Probe output:

```text
interface_status{device_name="HomeSwitch01",interface_name="GigabitEthernet1/0/1",site="home"} 1
```

versus snmp_exporter today:

```text
interface_status{device_name="HomeSwitch02",ifDescr="GigabitEthernet0/0",ifIndex="1",
                 ifName="Gi0/0",instance="192.168.3.3",interface_name="GigabitEthernet0/0",
                 job="device_snmp",role="switch",site="home",snmp_module="cisco",vendor="cisco"}
```

OTel drops `ifIndex` / `ifName` / `ifDescr` at the source — the same redundancy
the Network board panel had to exclude by hand. Good outcome, but see the
compatibility gap below.

### `interface_admin_status` is a free win

Collecting `ifAdminStatus` (OID `1.3.6.1.2.1.2.2.1.7`) alongside `ifOperStatus`
finally distinguishes **administratively shut** from **link failed**. Today
`SwitchLinkLost` has to infer intent from "was oper-up 15m ago, still admin up".

## Compatibility gap and how it is closed

Existing alert rules and dashboards select on `job="device_snmp"`, and some on
`role`/`vendor`/`instance`. OTel's `prometheusremotewrite` derives:

| Prometheus label | From OTel |
|---|---|
| `job` | resource attr `service.name` |
| `instance` | resource attr `service.instance.id` |

So the cutover **preserves every existing selector** by setting, per device
pipeline:

```yaml
processors:
  resource/homeswitch01:
    attributes:
      - {key: service.name,        value: device_snmp,     action: upsert}   # → job
      - {key: service.instance.id, value: "192.168.3.2",   action: upsert}   # → instance
      - {key: device_name,         value: HomeSwitch01,    action: upsert}
      - {key: role,                value: switch,          action: upsert}
      - {key: vendor,              value: cisco,           action: upsert}
      - {key: site,                value: home,            action: upsert}
```

This deviates from the pilot (which uses `service.name: network-devices`, giving
`job="network-devices"`) — a deliberate choice so **no dashboard, alert rule, or
recording rule has to change** during the metric cutover. Documented here so the
divergence from the pilot is intentional rather than accidental.

## Logs: improve on the pilot

The pilot uses the `udplog` receiver — raw datagrams, with `transform` statements
mapping sender IP → `device_name`. The body stays an unparsed line, which is the
very thing the operator wants to move away from.

Convergence uses the **`syslog` receiver** instead:

```yaml
receivers:
  syslog/devices:
    udp:
      listen_address: 0.0.0.0:1514
    protocol: rfc3164        # vendor default for Cisco IOS-XE and pfSense
    location: UTC
    on_error: send           # never silently drop a malformed line
```

Consequences:

- **Structured at ingest**: `facility`, `severity`, `hostname`, `appname`,
  `message` become attributes. No `|~` regex in dashboards.
- **The T141 syslog-gateway becomes unnecessary.** OTel's syslog receiver speaks
  rfc3164 natively; the syslog-ng front-end existed only because promtail speaks
  RFC5424 only. Retire it at cutover.
- **The Cisco `app`-label cardinality bug goes away.** syslog-ng inferred
  `app` from the first token before `:`, which on Cisco is the *mnemonic*
  (`%SEC_LOGIN-5-LOGIN_SUCCESS`) — unbounded label cardinality. OTel keeps the
  mnemonic in the body/attributes and only promotes a bounded label set.
- **Timestamps**: keep using receive time (`keep-timestamp` equivalent off /
  no `time_parser` on the rfc3164 branch) for the reason documented in T141 —
  RFC3164 carries no timezone, and live pfSense lines landed ~6h in the past.

Promoted Loki labels stay bounded and explicit: `device_name`, `site`,
`service.name`, `severity`. Everything else rides as structured metadata /
VictoriaLogs fields.

### Vendor format reality (measured during Phase 2)

| Vendor | What it actually sends | Result |
|---|---|---|
| pfSense | RFC3164, often **without a hostname** | parses; `device_name` from sender IP map |
| Cisco IOS/IOS-XE | **not RFC3164**: `<189>1834: *Jul 27 22:12:00.456: %LINK-3-UPDOWN: ...` | rfc3164 parse fails → vendor `regex_parser` extracts `priority`/`sequence`/`device_time`/`mnemonic`/`sev_level`/`message` |
| unknown | — | raw body retained, `device_name` still correct, never dropped (FR-035) |

This explains the pilot's choice of the raw `udplog` receiver: strict syslog
parsing does fail on this fleet. Convergence keeps the structured parse and adds a
vendor fallback rather than giving up on structure.

**Resource-attribute smearing.** Promoting labels with
`set(resource.attributes[...], attributes[...])` in a log-context transform is
wrong: a resource is shared by every record in its group, so the last device
processed wins for the whole batch. Measured live — a record from 172.19.0.1 came
out with resource `device_ip=192.168.3.1`. Use `groupbyattrs`, which re-partitions
records into one resource per distinct attribute set.

## Phased cutover

Logs first: smaller blast radius, and it retires a component that is one day old
with nothing depending on it.

| Phase | Tasks | Ends with |
|---|---|---|
| **1 Spec** | T145 | This doc + spec US11/FR-036–FR-042 + tasks |
| **2 Logs** | T146–T149 | otel-collector receives device syslog → Loki + VictoriaLogs; promtail + syslog-gateway retired for device syslog; Security board queries structured attributes |
| **3 Agent logs** | T150 | OpenClaw files + systemd journal via OTel `filelog` / `journald` receivers (or promtail retained for host-only scraping — decide with measurements, not guesses) |
| **4 SNMP** | T151–T153 | OTel SNMP receivers replace snmp_exporter; `device-recording.rules.yml` retired; `interface_admin_status` added |
| **5 Wizard** | T154–T155 | `render-convergence-telemetry.py` emits OTel receiver blocks instead of snmp_exporter modules; inventory schema unchanged |
| **6 K3s parity** | T156 | `components/otel-collector` replaces `components/device-syslog`; greenfield overlays updated |

Dual-run is allowed within a phase (both collectors writing) as long as the
duplicate-series risk is called out — see Risks.

## Risks

| Risk | Mitigation |
|---|---|
| Duplicate series during SNMP dual-run (snmp_exporter + OTel both emitting `interface_status{job="device_snmp"}`) | Do **not** dual-run identical `job` labels. Cut over per device, or stage OTel with `service.name: device_snmp_otel`, compare, then flip. |
| VictoriaMetrics has no writer today, so the 365d claim is currently fiction | Phase 4 wires `prometheusremotewrite` → VictoriaMetrics. Until then docs must not claim 365d. |
| OTel config is heavier for a new operator than a scrape config | The wizard (Phase 5) generates it; operators edit `convergence.yaml`, never the collector config by hand. |
| Losing `ifIndex` breaks anything keyed on it | Confirmed nothing on the provisioned boards or in the alert pack selects `ifIndex`; it was display-only and already removed. |
| `on_error: send` could ingest garbage as log bodies | Preferred over silent drop (FR-035 lesson). Parse failures remain countable in collector metrics. |

## Non-goals for this migration

- NetFlow/sFlow (goflow2) — separate component, later.
- Traces / OTLP application telemetry — Convergence has no tracing story yet.
- Replacing blackbox, unifi-exporter, alert-receiver, or the token exporter.
- Migrating pilot PVCs or historical TSDB/log data.
