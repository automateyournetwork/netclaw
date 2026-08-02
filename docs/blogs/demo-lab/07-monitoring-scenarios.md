# 07 — Monitoring & Failure Scenarios

## Overview

The demo lab is designed so that every failure scenario produces observable,
alertable symptoms across multiple layers: network (BGP/MPLS), transport
(latency/loss), and application (error rates, replication lag).

---

## Monitoring Stack (deployed in DC1 Prometheus + DC2 Loki)

| Component | Location | Scrapes/Receives |
|-----------|----------|------------------|
| Prometheus | DC1 | All node-exporters, app metrics, blackbox probes |
| Grafana | DC1 | Queries Prometheus + Loki |
| Loki | DC2 | Receives logs from all DCs via Promtail/OTEL |
| OTEL Collector | Each DC | Local metrics/traces → DC1 Prometheus |
| Blackbox exporter | DC1 | HTTP/ICMP probes to all DCs |
| node-exporter | Every node | Host CPU/memory/disk/network |
| postgres_exporter | DC1, DC2 | PG metrics (replication lag, connections) |

---

## Failure Scenarios

### Scenario 1: CE Link Failure (DC1 isolated)

**Action:** Shut CE1 Gi2 (uplink to SPE1)

**Impact:**
- DC1 loses all connectivity to DC2/DC3
- PostgreSQL replication to DC2 stops
- Prometheus can't scrape DC2/DC3 targets
- Loki stops receiving DC1 logs

**Observables:**

| Layer | Metric/Alert | Expected |
|-------|--------------|----------|
| Network | PE-CE BGP peer state | `Idle` on SPE1 for CUST-A |
| Network | BFD session | Down |
| Transport | Blackbox ICMP to DC1 nodes | 100% loss |
| Application | `pg_stat_replication_lag_bytes` | Flatlines (no new WAL) |
| Application | Prometheus `up` metric for DC1 targets | `0` |
| Logs | Loki ingestion rate from DC1 | Drops to 0 |

**Recovery:** `no shut` on CE1 Gi2 → BGP reconverges → replication catches up

---

### Scenario 2: SP Core Link Failure (traffic reroutes)

**Action:** Shut the SP1 ↔ SP2 link (`10.0.0.0/31`)

**Impact:**
- Traffic between SPE1-side and SPE2-side reroutes via SP3/SP4
- Latency increases (longer MPLS path)
- No outage, but degraded performance

**Observables:**

| Layer | Metric/Alert | Expected |
|-------|--------------|----------|
| Network | IS-IS/OSPF adjacency | SP1-SP2 goes down |
| Network | MPLS label switch path | Changes (new next-hop) |
| Transport | RTT between DC1 ↔ DC2 | Increases ~2-5ms |
| Application | API response latency (p99) | Slight increase |
| Application | PG replication lag | Temporary spike during reconvergence |

**Good for demonstrating:** BFD fast-reroute, IGP convergence timing, LFA/TI-LFA

---

### Scenario 3: K3s Worker Node Failure

**Action:** `shutdown` k3s-w1 VM (or `kubectl drain`)

**Impact:**
- Pods on k3s-w1 get evicted, rescheduled to k3s-w2
- Brief service disruption during pod rescheduling

**Observables:**

| Layer | Metric/Alert | Expected |
|-------|--------------|----------|
| K8s | Node status | `NotReady` for k3s-w1 |
| K8s | Pod restarts | Pods rescheduled on k3s-w2 |
| Application | HTTP 5xx rate | Spike during rescheduling |
| Host | node-exporter `up` | `0` for k3s-w1 |

---

### Scenario 4: Database Primary Failure

**Action:** Kill PostgreSQL process on DC1

**Impact:**
- All API servers lose DB connectivity
- DC2 replica stops receiving WAL
- If failover is configured, DC2 promotes to primary

**Observables:**

| Layer | Metric/Alert | Expected |
|-------|--------------|----------|
| Application | `pg_up` | `0` on DC1 |
| Application | API 5xx rate | 100% (no DB) |
| Application | `pg_stat_replication_lag_bytes` on DC2 | Stops increasing |
| Application | Connection pool exhaustion | All connections in `waiting` state |

---

### Scenario 5: Cross-DC Bandwidth Saturation

**Action:** Run `iperf3` between DC1 and DC2 to saturate the path

**Impact:**
- PG replication lag increases
- Log delivery to Loki delays
- API latency increases

**Observables:**

| Layer | Metric/Alert | Expected |
|-------|--------------|----------|
| Network | Interface utilization on PE-CE links | Near line rate |
| Network | QoS queue drops (if configured) | Non-zero |
| Transport | Packet loss on ICMP probes | Intermittent |
| Application | PG replication lag | Steadily increasing |
| Application | Loki ingestion delay | Increasing |
| Application | API p99 latency | 2-5x baseline |

**Good for demonstrating:** QoS/DSCP marking, traffic policing, congestion alerts

---

### Scenario 6: DNS Failure in DC3

**Action:** Kill CoreDNS pods in DC3

**Impact:**
- DC3 services can't resolve names
- MinIO backup writes fail (can't resolve endpoints)
- DC3 API returns errors

**Observables:**

| Layer | Metric/Alert | Expected |
|-------|--------------|----------|
| Application | CoreDNS `up` | `0` in DC3 |
| Application | DNS query failure rate | 100% in DC3 |
| Application | MinIO write errors | Connection failures |
| Application | DC3 API error rate | Spike |

---

### Scenario 7: Full DC Partition (VRF withdrawal)

**Action:** `clear ip bgp 65001` on SPE1 (or shut PE-CE link)

**Impact:**
- VPNv4 routes for CUST-A withdrawn from all PEs
- DC1 becomes completely unreachable from DC2/DC3
- Simulates catastrophic customer isolation

**Observables:**

| Layer | Metric/Alert | Expected |
|-------|--------------|----------|
| Network | VPNv4 prefix count on RR | Decreases |
| Network | PE-CE BGP state | `Idle` |
| Transport | All cross-DC probes to DC1 | Fail |
| Application | All services depending on DC1 | Error |
| Logs | Nothing from DC1 reaches Loki | Ingestion drops |

---

## Alert Rules (Prometheus)

```yaml
groups:
  - name: demo-lab.rules
    rules:
      # Network layer
      - alert: BGPPeerDown
        expr: bgp_peer_state{state!="established"} == 1
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "BGP peer {{ $labels.peer }} is down on {{ $labels.device }}"

      # Transport layer
      - alert: CrossDCLatencyHigh
        expr: probe_duration_seconds{job="blackbox-cross-dc"} > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Cross-DC latency above 50ms: {{ $labels.instance }}"

      # Application layer
      - alert: PostgresReplicationLag
        expr: pg_stat_replication_lag_bytes > 10485760
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "PG replication lag > 10MB on {{ $labels.instance }}"

      - alert: APIErrorRateHigh
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "API 5xx rate > 5% on {{ $labels.instance }}"

      - alert: NodeDown
        expr: up{job=~"node-dc.*"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Node {{ $labels.instance }} is unreachable"

      - alert: LokiIngestionDrop
        expr: rate(loki_distributor_bytes_received_total[5m]) == 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Loki receiving no data — possible upstream connectivity issue"
```

---

## Grafana Dashboards

| Dashboard | Panels |
|-----------|--------|
| **SP Core Health** | IGP adjacency map, MPLS label paths, BFD states, link utilization |
| **Cross-DC Connectivity** | RTT heatmap, packet loss, blackbox probe results |
| **K3s Cluster Status** | Node status per DC, pod counts, resource usage |
| **Application Health** | HTTP request rate/latency/errors, DB connections, replication lag |
| **Log Pipeline** | Loki ingestion rate per DC, error log rate, missing sources |
| **Failure Timeline** | Annotation-based view showing when failures were injected and recovered |

---

## Demo Script (suggested order)

1. **Baseline:** Show all dashboards green, all probes passing
2. **Scenario 2:** Kill a core link → show reroute with latency increase
3. **Scenario 5:** Saturate DC1↔DC2 → show replication lag and QoS
4. **Scenario 1:** Kill CE1 link → show full DC1 isolation cascade
5. **Scenario 4:** Kill PG primary → show application failure + failover
6. **Recovery:** Bring everything back → show convergence and catch-up

Each scenario takes 2-5 minutes to demonstrate, including recovery.
