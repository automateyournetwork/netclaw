# Part 13: Back to Monitoring — Deploying the Observability Stack on a Lab Network

*Building Convergence Series — Part 13*

---

In Parts 1 through 6, I built an observability pipeline on my home network: OpenTelemetry Collector polling SNMP, VictoriaMetrics storing time-series, Loki aggregating syslog, Grafana rendering dashboards. It worked. But it wasn't reproducible — you couldn't clone my repo and run it because you don't have my switches.

In Parts 7 through 9, I tried to build a custom AI agent to consume that telemetry. That was the overengineered mistake. The pivot to NetClaw (an OpenClaw-based agent with MCP integrations) replaced 3,800 lines of custom Python with skill definitions and MCP server calls.

Parts 10 through 12 proved NetClaw works: spec-driven MCP development, golden config bootstrap, and a five-model comparison running the full demo.

Now we're back to observability. Same pipeline. But this time it's portable — anyone with Docker and ContainerLab can run it.

---

## The Architecture

```
ContainerLab (18 devices)                         
├── 10 Cisco IOL (P1-P4, PE1-PE3, CE1-CE2, RR1)  
└── 8 Arista cEOS (West/East Spine01-02, Leaf01-02)
        │                                          
        ├── SNMP (udp/161) ──→ OTEL Collector (.200)
        │                           │
        │                           ├── metrics ──→ VictoriaMetrics (.201)
        │                           └── logs ────→ Loki (.202)
        │
        └── Syslog (udp/1514) ──→ OTEL Collector ──→ Loki
                                                          │
                                                          ▼
                                                    Grafana (.203)
                                                          │
                                                          ▼
                                                    NetClaw (Grafana MCP + Prometheus MCP)
```

Everything lives on the `clab-mgmt` Docker network (192.168.220.0/24) — the same network ContainerLab uses for device management. No NAT, no port forwarding, no routing tricks. The OTEL Collector can reach every device directly.

---

## What Changed from Parts 1-3

| Aspect | Parts 1-3 (Home Network) | Part 13 (Lab) |
|--------|--------------------------|---------------|
| Devices | Physical switches, personal IPs | 18 ContainerLab nodes, reproducible |
| SNMP config | Manual CLI | Golden Config pipeline (Nautobot config context → Jinja → Ansible) |
| Deployment | Manual docker-compose on a NUC | One `docker compose up -d` alongside the lab |
| Consumer | Custom Python agent (deleted) | NetClaw via Grafana MCP (75 tools) + Prometheus MCP (6 tools) |
| Portability | Zero — tied to my hardware | Clone, deploy, monitor in 15 minutes |

The key insight: **the observability stack is now managed the same way as the network itself** — through source-of-truth-driven automation.

---

## SNMP and Syslog via Golden Config

This is the part that matters most. We don't SSH into devices and type `snmp-server community public RO`. That config is managed through the same pipeline as OSPF, BGP, and MPLS:

### 1. Config Context (Source of Truth)

```yaml
# config_contexts/observability.yml
_metadata:
  name: Observability
  description: SNMP and syslog configuration for the observability stack
  weight: 200
  is_active: true
  roles:
    - name: "Provider Router"
    - name: "Provider Edge Router"
    - name: "Provider Route Reflector"
    - name: "Customer Edge Router"
    - name: "Datacenter Spine"
    - name: "Datacenter Leaf"
observability:
  snmp:
    community: public
    access: ro
  syslog:
    host: 192.168.220.200
    port: 1514
    transport: udp
    trap_level: informational
```

This applies to every device role in the lab. Change the syslog host? Update one YAML file. Nautobot validates it against the schema, golden config generates the intended state, compliance detects drift.

### 2. Jinja Templates

**IOS (`ios/observability.j2`):**
```jinja
{% set obs = config_context['observability'] %}
{% if obs['snmp'] is defined %}
{% set snmp = obs['snmp'] %}
{% if snmp['access'] == 'ro' %}
snmp-server community {{ snmp['community'] }} RO
{% else %}
snmp-server community {{ snmp['community'] }} RW
{% endif %}
{% endif %}
{% if obs['syslog'] is defined %}
{% set syslog = obs['syslog'] %}
logging host {{ syslog['host'] }} transport {{ syslog['transport'] }} port {{ syslog['port'] }}
logging trap {{ syslog['trap_level'] }}
{% endif %}
```

**EOS (`eos/observability.j2`):**
```jinja
{% set obs = config_context['observability'] %}
{% if obs['snmp'] is defined %}
{% set snmp = obs['snmp'] %}
snmp-server community {{ snmp['community'] }} {{ snmp['access'] }}
{% endif %}
{% if obs['syslog'] is defined %}
{% set syslog = obs['syslog'] %}
logging host {{ syslog['host'] }} {{ syslog['port'] }} protocol {{ syslog['transport'] }}
logging trap {{ syslog['trap_level'] }}
{% endif %}
```

### 3. Platform Template Integration

Every platform template now includes the observability snippet:

```jinja
{% if config_context['observability'] is defined %}
{% include '/ios/observability.j2' %}
{% endif %}
```

This include exists in **two places** — and both must stay in sync:

| Template Set | Location | Used By |
|---|---|---|
| **Ansible templates** | `Nautobot-Workshop/ansible-lab/roles/build_lab_config/templates/` | `ansible-playbook pb.build-lab.yml --tags build` → generates configs locally, `--tags deploy` pushes them |
| **Golden config templates** | `nautobot_workshop_golden_config_templates/` (GitHub repo synced to Nautobot) | Nautobot Golden Config plugin → generates intended configs for compliance |

The Ansible templates are what physically deploy config to devices. The golden config templates are what Nautobot uses to generate the "intended" state for compliance comparison. If you add observability to the Ansible templates but forget the golden config templates, compliance will flag every device as non-compliant — it'll see SNMP/syslog lines in the backup that don't exist in the intended config.

All 7 platform templates (4 IOS roles + 3 EOS roles) include the observability snippet in both repos. The `ios/observability.j2` and `eos/observability.j2` files are identical across both template sets.

The result: `--tags build` regenerates configs with SNMP and syslog included. `--tags deploy` pushes them. Golden config compliance detects if someone removes the SNMP community manually — because the intended config (generated from the same template + config context) still expects it.

---

## The Docker Compose

```yaml
# observability/docker-compose.observability.yml
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.104.0
    volumes:
      - ./otel-collector/otel-config.yaml:/etc/otelcol-contrib/config.yaml:ro
    ports:
      - "4317:4317"
      - "1514:1514/udp"
    networks:
      clab-mgmt:
        ipv4_address: 192.168.220.200

  victoriametrics:
    image: victoriametrics/victoria-metrics:v1.101.0
    command: ["--storageDataPath=/storage", "--retentionPeriod=30d"]
    networks:
      clab-mgmt:
        ipv4_address: 192.168.220.201

  loki:
    image: grafana/loki:3.1.0
    networks:
      clab-mgmt:
        ipv4_address: 192.168.220.202

  grafana:
    image: grafana/grafana:11.1.0
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=netclaw
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
    networks:
      clab-mgmt:
        ipv4_address: 192.168.220.203

networks:
  clab-mgmt:
    external: true
```

Four containers. Static IPs on the lab management network. Grafana auto-provisions datasources and dashboards on first boot.

---

## OTEL Collector Configuration

The collector runs two SNMP receiver instances — one for Cisco, one for Arista — polling every 60 seconds:

```yaml
receivers:
  snmp/cisco:
    collection_interval: 60s
    version: v2c
    community: public
    targets:
      - endpoint: udp://192.168.220.2:161   # P1
      - endpoint: udp://192.168.220.3:161   # P2
      # ... all 10 Cisco IOL devices
    metrics:
      system.cpu.utilization:
        scalar_oids:
          - oid: "1.3.6.1.4.1.9.9.109.1.1.1.1.8.1"  # cpmCPUTotal5minRev
      interface.octets.in:
        column_oids:
          - oid: "1.3.6.1.2.1.31.1.1.1.6"  # ifHCInOctets
      interface.status:
        column_oids:
          - oid: "1.3.6.1.2.1.2.2.1.8"     # ifOperStatus

  snmp/arista:
    collection_interval: 60s
    version: v2c
    community: public
    targets:
      - endpoint: udp://192.168.220.12:161  # West-Spine01
      # ... all 8 Arista cEOS devices

  syslog:
    udp:
      listen_address: "0.0.0.0:1514"
    protocol: rfc3164

exporters:
  prometheusremotewrite:
    endpoint: "http://victoriametrics:8428/api/v1/write"
  loki:
    endpoint: "http://loki:3100/loki/api/v1/push"
```

Metrics collected: CPU utilization, memory utilization, interface octets in/out, packets in/out, errors in/out, and operational status. All tagged with `device_name` and `interface_name` labels.

---

## Grafana Dashboards

Two dashboards ship pre-provisioned:

**Network Device Health** — fleet-wide view:
- CPU utilization per device (thresholds: green < 60%, yellow < 85%, red ≥ 85%)
- Memory utilization per device
- Interface count per device (stat panel showing "alive" devices)
- Error rate across all interfaces

**Interface Status** — per-device drill-down:
- Interface operational status table (up/down)
- Inbound/outbound traffic in bits/s
- Packet rates
- Error rates with threshold coloring

---

## Wiring NetClaw

After the stack is running, two environment variables connect NetClaw's existing MCP servers:

```bash
export GRAFANA_URL=http://192.168.220.203:3000
export GRAFANA_USERNAME=admin
export GRAFANA_PASSWORD=netclaw
export PROMETHEUS_URL=http://192.168.220.201:8428
```

Now when you ask NetClaw "what's the health of the SP core?", it can:
1. Query VictoriaMetrics via the Prometheus MCP for CPU/memory metrics
2. Query Grafana via the Grafana MCP for dashboard state and alerts
3. Cross-reference with pyATS for live device state
4. Synthesize a report combining telemetry + CLI output

That's Week 2's topic.

---

## Registering the Stack in Nautobot

Four containers with static IPs on a shared network — that's infrastructure. It belongs in the source of truth. We model the observability containers as virtual machines in Nautobot so their IPs are tracked, their roles are documented, and any future reconciliation knows they're intentional.

This is where the Nautobot MCP v2 shines. Instead of clicking through the Nautobot UI to create a cluster, four VMs, interfaces, and IP assignments, you tell NetClaw what you want:

### Example Prompts

> "Register the observability stack containers in Nautobot as VMs — otel-collector at .200, victoriametrics at .201, loki at .202, grafana at .203 on the clab-mgmt network"

> "Create a Monitoring cluster in Nautobot and add the four observability VMs with their IPs"

> "I need the OTEL collector, VictoriaMetrics, Loki, and Grafana tracked in Nautobot as virtual machines on 192.168.220.0/24"

### What NetClaw Does (MCP Tool Calls)

Behind the scenes, NetClaw uses the Nautobot MCP v2 virtualization tools:

```
1. nautobot_create_virtual_machine(
     name="otel-collector", cluster="Observability", role="Monitoring",
     comments="OTEL Collector — SNMP polling + syslog ingestion")

2. nautobot_create_vm_interface(
     virtual_machine="otel-collector", name="eth0",
     description="clab-mgmt network")

3. nautobot_assign_ip_to_vm(
     virtual_machine="otel-collector", interface="eth0",
     address="192.168.220.200/24", set_primary=True)

... repeated for victoriametrics (.201), loki (.202), grafana (.203)
```

Four VMs, four interfaces, four IPs — 12 MCP calls total. The LLM figures out the sequence from your natural language request.

### The Tools

The Nautobot MCP v2 server (`mcp-servers/nautobot-mcp-v2/server.py`) provides these virtualization tools:

| Tool | Purpose |
|------|--------|
| `nautobot_get_virtual_machines` | Query VMs by name, cluster, role, status |
| `nautobot_create_virtual_machine` | Create a VM in a cluster with role, vCPUs, memory, disk |
| `nautobot_create_vm_interface` | Add a network interface to a VM |
| `nautobot_assign_ip_to_vm` | Create an IP and assign it to a VM interface, optionally set as primary |

All write tools are ITSM-gated — in production they require a ServiceNow CR number. In lab mode (`ITSM_LAB_MODE=true`), the gate is bypassed.

### Why This Matters

Once the observability VMs are in Nautobot:

- **IP conflict detection** — Nautobot knows .200-.203 are allocated. If someone tries to assign those IPs to a new device, it flags the conflict.
- **Topology awareness** — the VMs appear in the clab-mgmt prefix. NetClaw can reconcile "what's on this subnet" against live ARP tables.
- **Golden config integration** — the OTEL Collector IP (192.168.220.200) in the observability config context can be validated against what Nautobot says it should be. Change the collector IP in one place, and compliance catches the drift everywhere.
- **Documentation as code** — no wiki page listing "observability stack IPs." It's in the SoT, queryable via GraphQL, visible in the UI.

### A Real Conversation

```
You:  Register the observability containers in Nautobot. They're on the
      clab-mgmt network — otel-collector .200, victoriametrics .201,
      loki .202, grafana .203. Put them in a Monitoring cluster.

NetClaw: I'll create the Observability cluster and register all four VMs.

         ✅ Created cluster "Observability" (type: Docker)
         ✅ Created VM "otel-collector" → eth0 → 192.168.220.200/24 (primary)
         ✅ Created VM "victoriametrics" → eth0 → 192.168.220.201/24 (primary)
         ✅ Created VM "loki" → eth0 → 192.168.220.202/24 (primary)
         ✅ Created VM "grafana" → eth0 → 192.168.220.203/24 (primary)

         All 4 VMs registered in Nautobot under the Observability cluster
         with role "Monitoring". IPs assigned on the 192.168.220.0/24 prefix.

You:  What VMs are in the Observability cluster?

NetClaw: [calls nautobot_get_virtual_machines(cluster="Observability")]

         | Name             | IP               | Status | Role       |
         |------------------|------------------|--------|------------|
         | otel-collector   | 192.168.220.200  | Active | Monitoring |
         | victoriametrics  | 192.168.220.201  | Active | Monitoring |
         | loki             | 192.168.220.202  | Active | Monitoring |
         | grafana          | 192.168.220.203  | Active | Monitoring |
```

---

## Deploying with NetClaw — The Skill in Action

You don't run those docker commands manually. You tell NetClaw to do it. The `deploy-observability` skill handles the entire deployment with self-validating gates at every step.

### Example Prompts

Any of these will trigger the skill:

> "Deploy the observability stack for the lab"

> "I need Grafana monitoring on my ContainerLab devices"

> "Set up SNMP polling and syslog collection for the lab network"

> "Enable the monitoring pipeline — OTEL, VictoriaMetrics, Loki, Grafana"

NetClaw recognizes the intent, selects the `deploy-observability` skill, and executes it step by step.

### What the Skill Does

The skill (`workspace/skills/deploy-observability/SKILL.md`) is a 9-step gated procedure:

| Step | Action | Gate |
|------|--------|------|
| 1 | Verify `clab-mgmt` Docker network exists | PASS/FAIL — stops if ContainerLab isn't running |
| 2 | `docker compose up -d` the 4 containers | All 4 containers report "Up" |
| 3 | Wait 15s for service initialization | — |
| 4 | Validate VictoriaMetrics health endpoint | HTTP 200 from `:8428/health` |
| 5 | Validate Loki readiness | HTTP 200 from `:3100/ready` |
| 6 | Validate Grafana health | `"ok"` in `:3000/api/health` response |
| 7 | Validate OTEL Collector logs | "Everything is ready" in container logs |
| 8 | Verify metrics flowing (after 90s) | `interface_status` query returns > 0 series |
| 9 | Verify Grafana dashboards provisioned | 2 dashboards found via API |

Every gate has explicit pass/fail criteria. If a gate fails, NetClaw reports the failure and suggests remediation — it doesn't improvise or skip ahead.

### No Custom MCP Server Required

The deployment itself uses standard shell commands — `docker compose`, `curl`, `docker logs`. NetClaw executes these directly. There's no "observability MCP server" because there's nothing to abstract:

- The stack is 4 containers with a static compose file
- Validation is HTTP health checks and a PromQL query
- The complexity is in the *configuration* (OTEL config, Grafana provisioning), not the deployment

The MCP servers come into play *after* deployment:

| MCP Server | Tools | Role |
|---|---|---|
| **Grafana MCP** (`mcp-grafana`) | 75+ | Query dashboards, run PromQL via Grafana, search Loki logs, manage alerts, track incidents |
| **Prometheus MCP** (`prometheus-mcp-server`) | 6 | Direct PromQL against VictoriaMetrics, metric discovery, scrape target health |

These are pre-configured in `config/openclaw.json` — they just need the environment variables pointing at the lab stack.

### A Real Conversation

Here's what the interaction looks like in practice:

```
You:  Deploy the observability stack for the lab

NetClaw: 🔍 Checking prerequisites...
         ✅ clab-mgmt network exists (192.168.220.0/24)

         🚀 Deploying observability stack...
         ✅ 4/4 containers running (otel-collector, victoriametrics, loki, grafana)

         🏥 Validating services...
         ✅ VictoriaMetrics healthy (192.168.220.201:8428)
         ✅ Loki ready (192.168.220.202:3100)
         ✅ Grafana healthy (192.168.220.203:3000)
         ✅ OTEL Collector collecting

         ⏳ Waiting for first SNMP poll cycle (90s)...
         ✅ 142 metric series flowing
         ✅ 2 dashboards provisioned (Network Device Health, Interface Status)

         📊 Stack deployed. Grafana: http://localhost:3000 (admin/netclaw)
         The Grafana MCP and Prometheus MCP are now connected to the lab metrics.
```

After this, you can immediately ask:

> "What's the CPU utilization across the SP core?"

> "Are there any interface errors in the last hour?"

> "Show me the traffic rate on West-Spine01's uplinks"

NetClaw uses the Grafana MCP to run PromQL queries against VictoriaMetrics and returns the results — no dashboard clicking required.

### The Skill Definition

For those building their own OpenClaw skills, here's the anatomy. The skill is a single markdown file at `workspace/skills/deploy-observability/SKILL.md`:

```yaml
---
name: deploy-observability
description: "Deploy the observability stack (OTEL Collector, VictoriaMetrics,
  Loki, Grafana) alongside the Nautobot Workshop ContainerLab topology."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["docker"], "env": [] } } }
---
```

The frontmatter tells OpenClaw:
- **name** — skill identifier for routing
- **description** — used for intent matching (when should this skill fire?)
- **user-invocable** — can be triggered directly by the user
- **requires.bins** — `docker` must be available on the host
- **requires.env** — no mandatory environment variables (the stack creates its own)

The body is the numbered procedure with gates. OpenClaw's agent reads it and executes each step, evaluating gates before proceeding. It's a runbook that the AI follows — not code that runs autonomously.

---

## Running It Manually

If you prefer the CLI over talking to an AI:

```bash
# 1. Deploy ContainerLab topology (if not already running)
cd ~/Nautobot-Workshop/clabs
sudo containerlab deploy -t containerlab-topology.yml

# 2. Build and deploy configs (includes SNMP + syslog)
cd ~/Nautobot-Workshop/ansible-lab
ansible-playbook pb.build-lab.yml --tags build
ansible-playbook pb.build-lab.yml --tags deploy

# 3. Deploy observability stack
cd ~/netclaw/observability
docker compose -f docker-compose.observability.yml up -d

# 4. Wait 90 seconds for first SNMP poll, then verify
curl -s "http://localhost:8428/api/v1/query?query=interface_status" | \
  python3 -c "import sys,json; r=json.load(sys.stdin); print(f'{len(r[\"data\"][\"result\"])} series')"

# 5. Open Grafana
# http://localhost:3000 (admin/netclaw)
```

---

## What's Next

Part 14 connects NetClaw to this stack. We'll write the `lab-noc-watch` and `lab-alert-triage` skills — three SKILL.md files that replace the 3,800 lines of custom Python from Parts 7-8. Same capability, zero custom code.

The promise from Part 1 was "from observability to AI-driven automation." We're almost there. The telemetry pipeline is back. The AI agent is ready. Next week we wire them together.

---

*All code for this post is in the [netclaw/observability](https://github.com/automateyournetwork/netclaw/tree/main/observability) directory and the [Nautobot-Workshop](https://github.com/byrn-baker/Nautobot-Workshop) config context additions.*
