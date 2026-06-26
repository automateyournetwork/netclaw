---
name: monitoring-onboard
description: "Configure network devices to send telemetry to the existing observability stack. Supports pfSense, Cisco IOS/IOS-XE switches, Proxmox hosts, and Linux servers. Generates Prometheus scrape configs and alert rules."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": [] } } }
---

# Monitoring Onboard

Configure network devices and infrastructure to report into the existing observability stack at **192.168.3.250** (Prometheus, Grafana, Loki, Alertmanager, goflow2).

## When to Use

- User asks to "set up monitoring" for a new device or set of devices
- A new device is added to the network and needs telemetry configured
- User wants to add SNMP, syslog, NetFlow, or node_exporter to a device
- User wants to generate Prometheus scrape configs or alert rules

## Observability Stack Reference

| Service | Address | Accepts |
|---------|---------|---------|
| Prometheus | 192.168.3.250:9090 | Scrapes HTTP /metrics endpoints |
| Loki | 192.168.3.250:514 (TCP+UDP) | Syslog (RFC3164/RFC5424) |
| goflow2 | 192.168.3.250:2055/udp | NetFlow/IPFIX |
| goflow2 | 192.168.3.250:6343/udp | sFlow |
| Alertmanager | 192.168.3.250:9093 | Receives alerts from Prometheus |
| Grafana | 192.168.3.250:3000 | Dashboard UI |

Prometheus remote-write receiver is enabled at: `POST http://192.168.3.250:9090/api/v1/write`

## Procedure by Device Type

### pfSense

1. **SNMP** — Enable via pfSense MCP or WebUI:
   - System → SNMP → Enable, community `public` (read-only), bind to LAN
   - Or use pfSense MCP: `pfsense_configure_service` to enable SNMP

2. **Syslog** — Configure remote syslog:
   - Status → System Logs → Settings → Remote Log Servers
   - Add: `192.168.3.250:514` (UDP), log: firewall, system, resolver
   - Or use pfSense MCP to push syslog config

3. **NetFlow** — Install softflowd package:
   - Diagnostics → Package Manager → install `softflowd`
   - Configure: interface=LAN/WAN, collector=192.168.3.250:2055, version=9

4. **Prometheus scrape** — pfSense doesn't have native node_exporter. Options:
   - Install `prometheus-node-exporter-lite` package if available
   - Or use SNMP exporter on the Prometheus side to scrape pfSense SNMP

### Cisco IOS / IOS-XE Switches

Use pyATS MCP to configure:

```
! SNMP
snmp-server community public RO
snmp-server host 192.168.3.250 version 2c public

! Syslog
logging host 192.168.3.250 transport udp port 514
logging trap informational
logging source-interface <mgmt-interface>

! NetFlow (IOS-XE with Flexible NetFlow)
flow exporter NETCLAW-EXPORT
 destination 192.168.3.250
 transport udp 2055
 export-protocol netflow-v9
 source <mgmt-interface>

flow monitor NETCLAW-MONITOR
 exporter NETCLAW-EXPORT
 record netflow ipv4 original-input

interface <monitored-interface>
 ip flow monitor NETCLAW-MONITOR input
 ip flow monitor NETCLAW-MONITOR output
```

### Proxmox Hosts

1. **node_exporter** — Install on each Proxmox node:
   ```bash
   apt-get install -y prometheus-node-exporter
   systemctl enable --now prometheus-node-exporter
   ```

2. **Syslog** — Configure rsyslog forwarding:
   ```bash
   echo '*.* @192.168.3.250:514' > /etc/rsyslog.d/50-obs.conf
   systemctl restart rsyslog
   ```

3. **Proxmox PVE exporter** (optional — exposes VM/container metrics):
   ```bash
   pip install prometheus-pve-exporter
   # Run as service, scrape from Prometheus
   ```

### Linux Servers (generic)

1. **node_exporter**:
   ```bash
   sudo apt-get install -y prometheus-node-exporter
   ```

2. **Syslog**:
   ```bash
   echo '*.* @192.168.3.250:514' | sudo tee /etc/rsyslog.d/50-obs.conf
   sudo systemctl restart rsyslog
   ```

## Prometheus Configuration Generation

After configuring devices, generate the scrape config addition:

```yaml
# Add to prometheus.yml on OBS VM (192.168.3.250)
# Then reload: curl -X POST http://192.168.3.250:9090/-/reload

  - job_name: 'network_devices'
    scrape_interval: 30s
    static_configs:
      - targets:
          - '<device_ip>:9100'
        labels:
          instance: '<device_name>'
          role: '<device_role>'
```

For SNMP-based targets, use the SNMP exporter pattern:

```yaml
  - job_name: 'snmp_network'
    scrape_interval: 60s
    metrics_path: /snmp
    params:
      module: [if_mib]
    static_configs:
      - targets:
          - '<device_ip>'
        labels:
          instance: '<device_name>'
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: 'snmp-exporter:9116'  # SNMP exporter address
```

## Alert Rules Generation

Generate standard alert rules for the device type:

```yaml
# Save as: prometheus/alerts/<device_name>.rules.yml
groups:
  - name: <device_name>_alerts
    rules:
      - alert: InstanceDown
        expr: up{instance="<device_name>"} == 0
        for: 2m
        labels:
          severity: critical
          device_name: "<device_name>"
        annotations:
          summary: "{{ $labels.instance }} is unreachable"
          description: "{{ $labels.instance }} has been down for more than 2 minutes."

      - alert: HighCPU
        expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle",instance="<device_name>"}[5m])) * 100) > 85
        for: 5m
        labels:
          severity: warning
          device_name: "<device_name>"
        annotations:
          summary: "High CPU on {{ $labels.instance }}"

      - alert: HighMemory
        expr: (1 - node_memory_MemAvailable_bytes{instance="<device_name>"} / node_memory_MemTotal_bytes{instance="<device_name>"}) * 100 > 90
        for: 5m
        labels:
          severity: warning
          device_name: "<device_name>"
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
```

## Procedure Summary

1. **Identify** — What device type? What IP? What telemetry does it support?
2. **Configure device** — Push SNMP/syslog/NetFlow config using appropriate MCP or SSH
3. **Generate scrape config** — Produce the prometheus.yml snippet
4. **Generate alert rules** — Produce device-specific alerting rules
5. **Reload Prometheus** — `curl -X POST http://192.168.3.250:9090/-/reload`
6. **Verify** — Query Prometheus for `up{instance="<device>"}` to confirm scrape works
7. **Update inventory** — Add device to `scripts/alert-receiver/inventory.yaml` or Nautobot

## Integration

| Skill | When |
|-------|------|
| `alert-triage` | After monitoring is configured and alerts start firing |
| `pfsense-*` | pfSense device configuration |
| `pyats-*` | Cisco device configuration |
| `proxmox-*` | Proxmox node management |
