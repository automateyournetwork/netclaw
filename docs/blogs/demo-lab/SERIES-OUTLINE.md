# SP Demo Lab Blog Series — Outline

## Premise

You have a Proxmox host running CML with 28 virtual network devices (13 IOS-XE,
15 Arista EOS) and 8 K3s VMs. Management interfaces are up on 192.168.3.0/24.
Nothing else is configured. This series takes you from that starting point to a
fully monitored multi-tenant SP network with NetClaw acting as your NOC.

## Prerequisites (assumed done, not covered)

- Proxmox host with CML VM deployed
- 28 network nodes in CML: RR1-2, SP1-4, SPE1-3, CE1-3, BORDER1, 3×DC fabrics (5 Arista each)
- 8 K3s VMs created on Proxmox bridges (vmbr100/200/300)
- All management interfaces configured per `01-addressing.md` and reachable via SSH
- A Linux workstation/VM on the management network (where NetClaw will live)

## Series Arc

### Part 1 — Nautobot: Your Source of Truth (Day 0)

**Goal**: Deploy Nautobot and populate it with the complete lab topology so every
subsequent step pulls from SoT rather than spreadsheets.

- Deploy Nautobot via Docker Compose on the management network
- Create the data model: Locations (SP-Core, DC-A, DC-B, DC-C), Roles
  (P-Router, PE-Router, RR, CE-Router, Spine, Leaf, Border), Manufacturers,
  Platforms (cisco_iosxe, arista_eos)
- Design Job: bulk-create all 28 devices with interfaces, IPs, and cabling
- Design Job: prefixes, VRFs (MGMT-VRF, CUST-A/B/C), VLANs, ASNs, BGP peering
- Verify: Nautobot topology view matches the design docs

### Part 2 — SP Core: IS-IS, MPLS, and BGP (Day 1)

**Goal**: Configure the service provider backbone — the routers know how to
forward packets and signal labels.

- Generate golden configs from Nautobot data (nautobot-golden-config or Jinja2)
- Push IS-IS/OSPF underlay to P routers (SP1–SP4) and PEs
- Enable MPLS LDP on all core interfaces
- Configure iBGP VPNv4/v6 with route reflectors (RR1/RR2)
- BFD on all IGP adjacencies
- Verify: `show mpls forwarding-table`, `show bgp vpnv4 unicast summary` from pyATS

### Part 3 — PE-CE and Customer VRFs (Day 2)

**Goal**: Attach customers to the MPLS cloud — each DC can reach its own VRF.

- Configure VRFs on PEs (CUST-A, CUST-B, CUST-C) with RT import/export
- Configure eBGP PE-CE sessions (SPE1↔CE1 AS65001, SPE2↔CE2 AS65002, SPE3↔CE3 AS65003)
- Verify: routes in VRF tables, end-to-end ping CE1↔CE2 via MPLS
- Register BGP sessions in Nautobot

### Part 4 — Datacenter Fabrics: Arista Leaf-Spine (Day 3)

**Goal**: Build the three Arista EVPN/VXLAN fabrics behind each CE.

- eBGP underlay between CE and spines, spines and leafs
- VXLAN with EVPN for server VLANs (VNI 10100/10200/10300)
- Anycast gateway on leafs for server subnets
- Verify: `show bgp evpn summary`, `show vxlan vtep`, LLDP neighbors
- Register all in Nautobot (interfaces, IPs, EVPN VNIs)

### Part 5 — K3s Clusters and Application Workloads (Day 4)

**Goal**: Bootstrap K3s in each DC and deploy distributed services that generate
real cross-site traffic.

- Bootstrap 3 K3s clusters (1 server + 2 agents each)
- Deploy: PostgreSQL primary (DC-A) + replica (DC-B), API servers (all DCs),
  MinIO backup (DC-C), Redis cache (DC-A)
- Verify: cross-DC replication working, API serving from all DCs

### Part 6 — Observability Stack: Prometheus, Loki, Grafana (Day 5)

**Goal**: Deploy the monitoring infrastructure that will feed NetClaw.

- Deploy Convergence stack on the management VM (Docker Compose)
- Pull device inventory from Nautobot (`--mode nautobot`)
- OTel Collector: SNMP polling all 28 devices + syslog receiver
- Prometheus: node-exporter on K3s nodes, blackbox cross-DC probes, app metrics
- Loki: log aggregation from all DCs via OTel
- Grafana: Network / Security / NetClaw boards on :3300
- Verify: all targets up, dashboards populated

### Part 7 — SuzieQ: State History for Investigations (Day 6)

**Goal**: Deploy the state-history plane so investigations can look backward in time.

- Enable `device_telemetry.state.suzieq` in convergence.yaml
- Apply: `convergence-telemetry-apply.sh` renders inventory from Nautobot targets
- `docker compose --profile suzieq up -d`
- Verify: `smoke-suzieq.sh` passes, BGP/route/interface tables populated
- Test time-travel: shut a link, wait, query `view=changes`

### Part 8 — NetClaw: Your AI NOC (Day 7)

**Goal**: Deploy NetClaw with the full Convergence pipeline — alerts fire,
investigations run, diary entries appear.

- Install NetClaw (recommended profile + convergence)
- Configure investigation policy: T0 default, T2 for BGPPeerDown and CrossDCLatencyHigh
- Wire alert-receiver to Alertmanager webhook
- Ensure guardian-claw member for investigations
- Point `SUZIEQ_API_URL` at the live REST API
- Test: shut a PE-CE link → alert fires → T2 investigation queries SuzieQ →
  root cause posted to diary with before/after state

### Part 9 — Failure Scenarios: Proving the Stack (Day 8+)

**Goal**: Run through each scenario from `07-monitoring-scenarios.md` and show
what the stack sees, what NetClaw investigates, and what the operator gets.

- Scenario 1: CE link failure → full DC isolation cascade
- Scenario 2: Core link failure → IGP reconvergence, MPLS reroute
- Scenario 5: Bandwidth saturation → QoS and congestion
- Scenario 7: VRF withdrawal → catastrophic partition
- Each scenario: what fired, what T2 found, what the diary shows

### Part 10 — Nautobot Golden Config: Compliance and Remediation (Bonus)

**Goal**: Close the loop — Nautobot holds intended state, NetClaw detects drift,
golden-config remediates.

- Define compliance rules (NTP, logging, SNMP community, BGP timers)
- Run compliance jobs — show what's out of policy
- `suzieq_assert` before and after a remediation push
- The full circle: SoT → config → monitor → detect drift → investigate → fix

---

## Relationship to existing design docs (01–07)

The design docs are the **what**. This series is the **how**. Each blog post
references the relevant design doc but doesn't duplicate it:

| Blog Part | References |
|-----------|------------|
| Part 1 | 01-addressing (all IPs/ASNs), all topology docs |
| Part 2 | 02-sp-core-topology |
| Part 3 | 03-vrf-design |
| Part 4 | 04-datacenter-design |
| Part 5 | 05-cml-proxmox-integration, 06-services-distribution |
| Part 6–9 | 07-monitoring-scenarios |
| Part 10 | Nautobot golden-config (new) |

---

## Target audience

Network engineers who can configure an IGP and know what EVPN is, but want to
see how SoT-driven automation + AI-assisted monitoring works end to end on a
realistic topology. Not a "hello world" — a reference implementation they can
reproduce on their own Proxmox/CML setup.

---

## Where to publish

- Primary: localedgedatacenter.com/blog (Cloudflare Worker, new route)
- Cross-post: dev.to, LinkedIn articles
- Repo: `netclaw/docs/blogs/demo-lab/` (source of truth for content)
