# Contract: Home adapters

## Config file: `config/convergence.yaml`

```yaml
site: home
deploy: docker | k3s

firewall:
  type: none | pfsense | generic-snmp
  # env: PFSENSE_*

wireless:
  type: none | unifi | generic-snmp
  unifi:
    host: https://192.0.2.10:11443
    site: default
    # env: UNIFI_API_KEY
  # generic-snmp = optional AP/controller IF-MIB path (NOT campus switch SNMP)

sot:
  type: none | nautobot | netbox
  # env: NAUTOBOT_* / NETBOX_*

metrics:
  prometheus_url: http://prometheus:9090
  # optional loki_url, victoriametrics_url

# --- Greenfield device telemetry (optional PR — see device-telemetry-greenfield.md)
# Distinct from wireless.generic-snmp: these are campus switches / wired infrastructure.
device_telemetry:
  snmp:
    enabled: false
    engine: snmp_exporter     # snmp_exporter (v1) | otel (reserved)
    version: v2c
    poll_interval: 60s
    # Phase 10: targets carry vendor/template for apply pipeline
    targets: []               # [{ name, ip, role, vendor?, template? }]
    # role: switch|firewall|other
    # vendor/template: cisco|pfsense|generic (see contracts/telemetry-setup.md)
    # community / v3 secrets: SNMP_COMMUNITY, SNMP_V3_* in env — never in yaml
  syslog:
    enabled: false
    listen: "0.0.0.0:1514"
    # peer IP → device_name mapping uses snmp.targets names when present

agent_observability:
  token_exporter:
    enabled: false            # host systemd: openclaw-token-exporter :9110
    port: 9110
  log_forward:
    enabled: false            # rsyslog/journal → Convergence Loki
    include: [gateway, mesh, alert-receiver]

grafana:
  provision_network_dashboards: true
  provision_agent_dashboards: true

agent:
  alert_receiver_url: http://127.0.0.1:8099
  investigator_member: auto   # resolve guardian-claw
  discord_enabled: true
```

## Runtime interface (logical)

| Method | Returns |
|--------|---------|
| `metrics.health(site)` | score, latency_ms, loss_ratio, bandwidth_bps, alert_count |
| `wireless.status(site)` | aps[{name,mac,clients,radios[{band,channel,width,retries}]}] |
| `firewall.security_summary(site)` | blocks_1h, blocks_24h |
| `inventory.lookup(query)` | optional SoT records |
| `devices.switch_health(site)` *(optional)* | switches[{name,ip,ifaces_down,errors_5m}] when device_snmp enabled |

### Adapter boundaries (do not conflate)

| Adapter | Scope |
|---------|--------|
| `wireless.unifi` | UniFi Integration API / REST exporter |
| `wireless.generic-snmp` | Non-UniFi **APs** IF-MIB via snmp_exporter |
| **`device_telemetry.snmp`** | **Switches / wired infra** (e.g. Catalyst 3850) via OTEL SNMP or modules |
| `agent_observability.*` | NetClaw host token metrics + agent log ship |

UniFi v1: Prometheus `unifi_*` + optional MCP.  
Device SNMP greenfield (plumbing): see [`device-telemetry-greenfield.md`](../device-telemetry-greenfield.md).  
Device SNMP setup productization (inventory → templates → apply → boards):
[`telemetry-setup.md`](../telemetry-setup.md) ·
[`telemetry-setup.md` contract](./telemetry-setup.md).
