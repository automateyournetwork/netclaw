# Contract: Home adapters

## Config file: `config/home-noc.yaml`

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

sot:
  type: none | nautobot | netbox
  # env: NAUTOBOT_* / NETBOX_*

metrics:
  prometheus_url: http://prometheus:9090
  # optional loki_url, victoriametrics_url

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

UniFi v1: Prometheus `unifi_*` + optional MCP `integration_get_ap_radios`.
