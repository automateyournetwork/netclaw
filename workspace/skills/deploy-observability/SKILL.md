---
name: deploy-observability
description: "Deploy the observability stack (OTEL Collector, VictoriaMetrics, Loki, Grafana) alongside the Nautobot Workshop ContainerLab topology. Use when the user wants to add monitoring to the lab, deploy the observability stack, or enable Grafana/Prometheus for the lab devices."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["docker"], "env": [] } } }
---

# Deploy Observability Stack

## When to Use
- User asks to deploy monitoring/observability for the lab
- User wants Grafana dashboards for the ContainerLab devices
- User asks to enable SNMP polling or syslog collection for lab devices
- As Step 21 of the full demo-lab-setup workflow

## Prerequisites
- Route to the remote lab subnet 192.168.220.0/24 (lab moved to another VM; local Docker uses netclaw-obs)
- SNMP community `public` configured on lab devices (default for IOL/cEOS)
- Docker and docker compose available on the host

## Procedure

### Step 1: Verify ContainerLab Network Exists

```bash
# Local clab-mgmt no longer required/used by observability stack.
# Verify host routing to remote lab instead:
ip route get 192.168.220.11 >/dev/null && echo "ROUTE OK to lab" || echo "No route to 192.168.220.0/24"
```

**GATE:** Output must be `PASS`. If FAIL, the ContainerLab topology is not running — deploy it first.

### Step 2: Deploy Observability Stack

```bash
cd /home/ubuntu/netclaw/observability
docker compose -f docker-compose.observability.yml up -d
```

**GATE:** All 4 containers start without error. Verify:
```bash
docker compose -f docker-compose.observability.yml ps --format "{{.Name}} {{.Status}}" | grep -c "Up"
```
Expected: `4`

### Step 3: Wait for Services to Initialize

```bash
sleep 15
```

### Step 4: Validate VictoriaMetrics

```bash
curl -sf http://localhost:8428/health && echo "PASS" || echo "FAIL"
```

**GATE:** Must return `PASS`.

### Step 5: Validate Loki

```bash
curl -sf http://localhost:3100/ready && echo "PASS" || echo "FAIL"
```

**GATE:** Must return `PASS`.

### Step 6: Validate Grafana

```bash
curl -sf http://localhost:3000/api/health | grep -q "ok" && echo "PASS" || echo "FAIL"
```

**GATE:** Must return `PASS`.

### Step 7: Validate OTEL Collector

```bash
docker logs otel-collector 2>&1 | grep -q "Everything is ready" && echo "PASS" || echo "COLLECTING"
```

**GATE:** If `COLLECTING`, wait 30s and retry. OTEL starts polling immediately but logs readiness after first collection cycle.

### Step 8: Verify Metrics Flowing

Wait 90 seconds after deployment for first SNMP poll cycle, then:

```bash
curl -sf "http://localhost:8428/api/v1/query?query=interface_status" | python3 -c "import sys,json; r=json.load(sys.stdin); print(f'PASS ({len(r[\"data\"][\"result\"])} series)' if r['data']['result'] else 'FAIL')"
```

**GATE:** Must show `PASS` with series count > 0. If FAIL after 2 minutes, check SNMP community on devices.

### Step 9: Verify Grafana Dashboards Provisioned

```bash
curl -sf -u admin:netclaw "http://localhost:3000/api/search?query=Network" | python3 -c "import sys,json; r=json.load(sys.stdin); print(f'PASS ({len(r)} dashboards)' if r else 'FAIL')"
```

**GATE:** Must show `PASS (2 dashboards)`.

## Device SNMP + Syslog Configuration

SNMP and syslog are managed through the golden config pipeline — not manual CLI:

1. The `observability` config context (`config_contexts/observability.yml`) defines SNMP community and syslog target
2. Jinja templates (`ios/observability.j2`, `eos/observability.j2`) render the platform-specific config
3. Run `ansible-playbook pb.build-lab.yml --tags build` to regenerate intended configs
4. Run `ansible-playbook pb.build-lab.yml --tags deploy` to push to devices

Alternatively, run the golden config intended + compliance jobs in Nautobot to detect drift.

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / netclaw |
| VictoriaMetrics | http://localhost:8428 | none |
| Loki | http://localhost:3100 | none |
| OTEL Collector | http://localhost:4317 (gRPC) | none |

## NetClaw Integration

After deployment, configure NetClaw's Grafana and Prometheus MCP servers:

```bash
export GRAFANA_URL=http://localhost:3000
export GRAFANA_USERNAME=admin
export GRAFANA_PASSWORD=netclaw
export PROMETHEUS_URL=http://localhost:8428
```

These enable the `grafana-observability` and `prometheus-monitoring` skills to query lab metrics.

## Teardown

```bash
cd /home/ubuntu/netclaw/observability
docker compose -f docker-compose.observability.yml down -v
```

## GAIT Audit Trail

Record deployment in GAIT:
```
Operation: deploy-observability
Components: otel-collector, victoriametrics, loki, grafana
Network: netclaw-obs (internal Docker bridge); lab devices via host routing to 192.168.220.0/24
Devices monitored: 18 (10 Cisco IOL + 8 Arista cEOS)
Metrics: CPU, memory, interface octets/packets/errors/status
Logs: syslog via UDP 1514
```

## Step 10: Register VMs in Nautobot (Optional / Legacy)

**Note:** The OBS stack now runs on this host using the `netclaw-obs` internal Docker network (published on the host's management IP, e.g. 192.168.3.252).
The old 192.168.220.20x / clab-mgmt assignments are obsolete after the lab move and local bridge removal.
You can skip this step entirely or register the services using the host's actual IP for SoT tracking.
The example below is kept for reference only and will create stale data if used as-is.

After the stack is healthy, register the containers as virtual machines in Nautobot for IP tracking and SoT completeness (legacy):

```
nautobot_create_virtual_machine(name="otel-collector", cluster="Observability", role="Monitoring", comments="SNMP polling + syslog ingestion")
nautobot_create_vm_interface(virtual_machine="otel-collector", name="eth0", description="host-mgmt")
nautobot_assign_ip_to_vm(virtual_machine="otel-collector", interface="eth0", address="192.168.3.252/24")

nautobot_create_virtual_machine(name="victoriametrics", cluster="Observability", role="Monitoring", comments="Prometheus-compatible metrics storage")
nautobot_create_vm_interface(virtual_machine="victoriametrics", name="eth0", description="host-mgmt")
nautobot_assign_ip_to_vm(virtual_machine="victoriametrics", interface="eth0", address="192.168.3.252/24")

nautobot_create_virtual_machine(name="loki", cluster="Observability", role="Monitoring", comments="Log aggregation")
nautobot_create_vm_interface(virtual_machine="loki", name="eth0", description="host-mgmt")
nautobot_assign_ip_to_vm(virtual_machine="loki", interface="eth0", address="192.168.3.252/24")

nautobot_create_virtual_machine(name="grafana", cluster="Observability", role="Monitoring", comments="Dashboards + visualization")
nautobot_create_vm_interface(virtual_machine="grafana", name="eth0", description="host-mgmt")
nautobot_assign_ip_to_vm(virtual_machine="grafana", interface="eth0", address="192.168.3.252/24")
```

**GATE:** All 4 VMs created with primary IPs assigned (using host IP). Verify:
```
nautobot_get_virtual_machines(cluster="Observability")
```
Expected: 4 VMs with the host management IP (e.g. 192.168.3.252).

**Note:** Requires the "Observability" cluster and "Monitoring" role to exist in Nautobot. Create them first if they don't exist.
Use the host's current management IP (check with `ip addr show eth0` or similar; commonly 192.168.3.252 on the interconnect).
