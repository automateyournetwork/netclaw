# Video Script: Back to Monitoring — Deploying the Observability Stack on a Lab Network

**Target length:** 12-15 minutes
**Format:** Screen recording with voiceover, architecture diagrams, terminal demos
**Publish:** YouTube + cross-post clips to X and LinkedIn

---

## INTRO (0:00 - 1:30)

### Visual: Architecture diagram (before/after)

**Script:**

> Six months ago I built an observability pipeline on my home network — OTEL Collector polling SNMP from my switches, VictoriaMetrics for metrics, Loki for logs, Grafana for dashboards. It worked great. But nobody could reproduce it because they don't have my hardware.
>
> Then I spent three weeks building a custom AI agent to consume that telemetry. That was the overengineered mistake — Parts 7 through 9 of this series.
>
> Today we're bringing the observability stack back. Same pipeline. But now it runs on a ContainerLab topology that anyone can clone and deploy. And instead of a custom agent, NetClaw — a CCIE-level AI coworker — consumes the telemetry through standard MCP integrations.
>
> By the end of this video, you'll have 18 network devices being monitored by a full observability stack, with Grafana dashboards showing interface traffic, CPU, memory, and errors. All from one docker compose command.

---

## THE LAB (1:30 - 3:00)

### Visual: ContainerLab topology diagram, terminal showing `containerlab inspect`

**Script:**

> Here's the lab. The Nautobot Workshop gives us 18 devices on a Docker network called clab-mgmt — 192.168.220.0/24.
>
> Ten Cisco IOL routers: four provider core, three provider edge, two customer edge, one route reflector. Eight Arista cEOS switches: two spines and two leaves in each of two data centers — West and East.
>
> Every device has a management IP on this network. That's where we'll poll SNMP and receive syslog.

**Action:** Show `sudo containerlab inspect -t containerlab-topology.yml` output with device IPs.

---

## SNMP + SYSLOG VIA GOLDEN CONFIG (3:00 - 5:30)

### Visual: VS Code showing config context YAML, Jinja template, rendered config

**Script:**

> Here's the key decision for this part: we don't SSH into devices and type SNMP commands. The observability config is managed through the same golden config pipeline as everything else — OSPF, BGP, MPLS.
>
> First, a config context. This YAML file defines what we want: SNMP community "public" read-only, syslog to 192.168.220.200 port 1514 over UDP. The metadata section assigns it to every device role in the lab.
>
> Second, Jinja templates. One for IOS, one for EOS. They read the config context and render platform-specific CLI. IOS gets `snmp-server community public RO` and `logging host` with transport UDP. EOS gets `snmp-server community public ro` and `logging host` with protocol UDP — slightly different syntax, same intent.
>
> Third, every platform template now includes the observability snippet with a conditional check. If the config context exists, render it. If not, skip it. No errors, no empty lines.
>
> The result: run Ansible build and deploy, and every device gets SNMP and syslog configured. Golden config compliance will flag any device where someone removes it manually. The observability config is now part of the intended state.

**Action:**
1. Show `config_contexts/observability.yml`
2. Show `ios/observability.j2` and `eos/observability.j2`
3. Show the `{% include %}` line in `provider_router.j2`
4. Run `ansible-playbook pb.build-lab.yml --tags build` (show intended config output with SNMP lines)
5. Run `--tags deploy`

---

## THE OBSERVABILITY STACK (5:30 - 8:00)

### Visual: docker-compose file, then terminal showing containers starting

**Script:**

> Four containers. That's the entire observability stack.
>
> OTEL Collector at .200 — polls SNMP every 60 seconds and receives syslog on UDP 1514. VictoriaMetrics at .201 — Prometheus-compatible time-series database, 30-day retention. Loki at .202 — log aggregation. Grafana at .203 — dashboards, auto-provisioned with datasources and two network dashboards.
>
> All four join the clab-mgmt network with static IPs. They can reach every device directly — no port forwarding, no NAT.
>
> Let's bring it up.

**Action:**
1. Show `docker-compose.observability.yml` (highlight `networks: clab-mgmt: external: true`)
2. Run `docker compose -f docker-compose.observability.yml up -d`
3. Show `docker compose ps` — all 4 containers running
4. Wait ~90 seconds

---

## OTEL COLLECTOR CONFIG (8:00 - 9:30)

### Visual: otel-config.yaml with highlights on receivers and exporters

**Script:**

> The OTEL Collector config has two SNMP receiver blocks — one for Cisco, one for Arista. Each lists every device IP as a target.
>
> For Cisco, we poll the cpmCPUTotal5minRev OID for CPU, ciscoMemoryPoolUsed for memory, and standard IF-MIB OIDs for interface counters — octets, packets, errors, and operational status. Each metric gets tagged with device_name and interface_name from the ifDescr OID.
>
> For Arista, same interface OIDs — they use standard MIBs. No vendor-specific CPU/memory OIDs needed for cEOS in this lab.
>
> The syslog receiver listens on UDP 1514 using RFC 3164 format — that's what both IOS and EOS send by default.
>
> Metrics go to VictoriaMetrics via Prometheus remote write. Logs go to Loki. Simple pipeline, no transforms needed.

**Action:** Scroll through `otel-config.yaml`, highlight the target lists and metric definitions.

---

## VERIFYING METRICS (9:30 - 10:30)

### Visual: Terminal curl commands, then Grafana dashboards

**Script:**

> Let's verify data is flowing. A quick curl to VictoriaMetrics asking for interface_status metrics...
>
> [show result] — we've got series for every interface on every device. The SNMP polling is working.
>
> Now let's check Grafana. Two dashboards were auto-provisioned: Network Device Health and Interface Status.
>
> Device Health shows CPU and memory for the Cisco devices, interface counts as a stat panel, and error rates across the fleet. Interface Status lets me drill into a specific device — here's West-Spine01 — and see per-interface traffic rates, packet rates, and errors.

**Action:**
1. Run `curl -s "http://localhost:8428/api/v1/query?query=interface_status" | python3 -c "..."` — show series count
2. Open Grafana at localhost:3000
3. Navigate to Network Device Health dashboard — show CPU panel
4. Navigate to Interface Status — select a device, show traffic graphs

---

## NETCLAW INTEGRATION (10:30 - 12:00)

### Visual: Environment variables, then brief NetClaw conversation

**Script:**

> The last piece: connecting NetClaw. Two environment variables point the existing Grafana MCP and Prometheus MCP servers at our lab stack.
>
> GRAFANA_URL points to .203 port 3000. PROMETHEUS_URL points to VictoriaMetrics at .201 port 8428 — VictoriaMetrics is Prometheus-compatible, so the Prometheus MCP works against it directly.
>
> Now NetClaw has 81 tools for querying this data — 75 from Grafana MCP, 6 from Prometheus MCP. It can search dashboards, run PromQL queries, check alerts, search Loki logs, and render panel images.
>
> Next week in Part 14, we'll write the skills that make NetClaw use these tools proactively — a NOC watch skill that checks interface errors and CPU, and an alert triage skill that correlates Grafana alerts with pyATS device state. Three SKILL.md files replacing thousands of lines of custom code.

**Action:**
1. Show the export commands for GRAFANA_URL and PROMETHEUS_URL
2. (Optional) Quick NetClaw query: "query prometheus for interface_status" — show it returning data

---

## RECAP + WHAT'S NEXT (12:00 - 13:00)

### Visual: Architecture diagram with checkmarks

**Script:**

> Let's recap what we built today:
>
> - A config context in Nautobot that defines SNMP and syslog settings for all 18 devices
> - Jinja templates that render platform-specific config for IOS and EOS
> - A four-container observability stack that joins the lab network directly
> - OTEL Collector polling SNMP every 60 seconds and receiving syslog
> - VictoriaMetrics storing metrics with 30-day retention
> - Loki aggregating device logs
> - Grafana with two pre-provisioned dashboards
> - NetClaw wired to query it all via MCP
>
> The entire thing is in the netclaw repo under the observability directory. Clone it, deploy ContainerLab, run docker compose up, and you have a monitored network in minutes.
>
> Next week: wiring NetClaw to this stack with skills that turn telemetry into actionable intelligence. Subscribe so you don't miss it.

---

## OUTRO (13:00 - 13:30)

**Script:**

> All the code is linked in the description — the netclaw repo for the observability stack, and the Nautobot Workshop repo for the config context and template changes. If you're following along with the series, this is where observability meets AI-driven automation. See you in Part 14.

---

## B-ROLL / CUTAWAY SHOTS

- ContainerLab topology diagram (from the README or generated)
- Architecture diagram showing data flow
- Split screen: config context YAML on left, rendered IOS config on right
- Grafana dashboard with live metrics populating
- Terminal showing docker compose logs scrolling

## THUMBNAIL

Text: "MONITOR 18 DEVICES" + Grafana dashboard screenshot + OTEL/Grafana/VictoriaMetrics logos

## DESCRIPTION

```
Deploy a full observability stack (OTEL Collector, VictoriaMetrics, Loki, Grafana) on a ContainerLab network lab — portable, reproducible, and wired to an AI network agent.

Part 13 of the "Building Convergence" series: from network observability to AI-driven automation.

What's covered:
- SNMP + syslog config managed through Nautobot Golden Config (config contexts + Jinja templates)
- OTEL Collector polling 18 devices (Cisco IOL + Arista cEOS)
- VictoriaMetrics for metrics, Loki for logs, Grafana for dashboards
- NetClaw integration via Grafana MCP + Prometheus MCP

Links:
- NetClaw repo: https://github.com/automateyournetwork/netclaw
- Nautobot Workshop: https://github.com/byrn-baker/Nautobot-Workshop
- Blog post: [link]
- Series playlist: [link]

Timestamps:
0:00 Intro — why we're back to monitoring
1:30 The lab topology (18 ContainerLab devices)
3:00 SNMP + syslog via Golden Config pipeline
5:30 The observability stack (docker compose)
8:00 OTEL Collector configuration deep dive
9:30 Verifying metrics in Grafana
10:30 Wiring NetClaw to the stack
12:00 Recap and what's next

#NetworkAutomation #Observability #NetClaw #Nautobot #GoldenConfig #ContainerLab #OpenTelemetry #Grafana #SNMP
```

---

## SOCIAL CLIPS

### X Thread (publish day of video)

1. "The observability stack is back — but now it's portable. 18 ContainerLab devices, OTEL Collector, VictoriaMetrics, Loki, Grafana. One docker compose command. Thread 🧵"

2. "Key decision: SNMP and syslog config isn't manual CLI. It's a Nautobot config context + Jinja template. Same pipeline as OSPF and BGP. Golden config compliance catches drift."

3. "The OTEL Collector polls all 18 devices every 60s via SNMP. Interface octets, packets, errors, operational status. Cisco-specific OIDs for CPU and memory. All tagged with device_name."

4. "NetClaw connects via Grafana MCP (75 tools) + Prometheus MCP (6 tools). Next week: skills that turn this telemetry into 'your SP core has 3 interfaces erroring, here's what I found via pyATS.'"

5. "Full code: github.com/automateyournetwork/netclaw/tree/main/observability — clone it, deploy ContainerLab, docker compose up. Video link below."

### LinkedIn Post (publish day after video)

> Observability for network labs — the reproducible way.
>
> I just published Part 13 of the Building Convergence series. The observability stack (OTEL, VictoriaMetrics, Loki, Grafana) is back, but now it runs on a ContainerLab topology that anyone can clone.
>
> The interesting part: SNMP and syslog configuration is managed through Nautobot Golden Config — config contexts define the intent, Jinja templates render platform-specific CLI, and compliance jobs detect drift. The monitoring config is treated exactly like routing protocol config.
>
> This sets up Part 14 where NetClaw (an AI network agent) consumes the telemetry via MCP integrations and correlates it with live device state. Three skill definitions replacing thousands of lines of custom code.
>
> Video + code in comments.
>
> #NetworkAutomation #Observability #Nautobot #GoldenConfig #NetClaw #OpenTelemetry #ContainerLab
