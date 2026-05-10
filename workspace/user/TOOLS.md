# TOOLS.md — Local Infrastructure Notes

Skills define *how* tools work. This file is for *your* specifics — the environment details unique to your deployment.

## Network Devices — Nautobot Workshop Topology

Management network: 192.168.220.0/24 (ContainerLab `clab-mgmt` network, auto-created by clab deploy)

### SP Core (Cisco IOL 17.12.01)
```
P1   → 192.168.220.2,  P router,        IOS-XE (IOL)
P2   → 192.168.220.3,  P router,        IOS-XE (IOL)
P3   → 192.168.220.4,  P router,        IOS-XE (IOL)
P4   → 192.168.220.5,  P router,        IOS-XE (IOL)
PE1  → 192.168.220.6,  PE router,       IOS-XE (IOL)
PE2  → 192.168.220.7,  PE router,       IOS-XE (IOL)
PE3  → 192.168.220.8,  PE router,       IOS-XE (IOL)
CE1  → 192.168.220.9,  CE router,       IOS-XE (IOL)
CE2  → 192.168.220.10, CE router,       IOS-XE (IOL)
RR1  → 192.168.220.11, Route Reflector, IOS-XE (IOL)
```

### West DC Fabric (Arista cEOS 4.34.0F)
```
West-Spine01 → 192.168.220.12, Spine, EOS
West-Spine02 → 192.168.220.13, Spine, EOS
West-Leaf01  → 192.168.220.14, Leaf,  EOS
West-Leaf02  → 192.168.220.15, Leaf,  EOS
```

### East DC Fabric (Arista cEOS 4.34.0F)
```
East-Spine01 → 192.168.220.16, Spine, EOS
East-Spine02 → 192.168.220.17, Spine, EOS
East-Leaf01  → 192.168.220.18, Leaf,  EOS
East-Leaf02  → 192.168.220.19, Leaf,  EOS
```

### DNS Servers (Arista cEOS 4.34.0F)
```
DNS-01 → 192.168.220.20, DNS server, EOS
DNS-02 → 192.168.220.21, DNS server, EOS
```

### Credentials
- All devices: admin / admin
- Nautobot: admin / admin (http://localhost:8080)

## Platform Details

### Nautobot 2.4.10
- URL: http://localhost:8080
- Default credentials: admin / admin
- Default API Token: `0123456789abcdef0123456789abcdef01234567` (from creds.env)
- Set `NAUTOBOT_CREATE_SUPERUSER=true` in creds.env before first start
- API Token configured in ~/.openclaw/.env as NAUTOBOT_TOKEN
- Plugins: golden-config, design-builder, bgp-models, device-lifecycle-mgmt, ssot, device-onboarding, plugin-nornir
- Data populated via Design Builder "Nautobot Workshop Demo Initial Data" job

### ContainerLab
- Topology: ~/Nautobot-Workshop/clabs/nautobot-workshop-topology.clab.yml
- Lab name: nautobot_workshop
- Management network: clab-mgmt (192.168.220.0/24, auto-created by clab deploy)
- Inspect: `sudo clab inspect --topo ~/Nautobot-Workshop/clabs/nautobot-workshop-topology.clab.yml`

### Ansible
- Playbook: ~/Nautobot-Workshop/ansible-lab/pb.build-lab.yml
- Tags: clab (topology), build (configs), deploy (push configs)
- Vault password: ~/.vault-pass.txt

## Protocols in the Lab

- **OSPF:** SP core (P1-P4, PE1-PE3, RR1) — area 0
- **MPLS/LDP:** SP core P-to-P and P-to-PE links
- **BGP:** iBGP between PE routers via RR1; eBGP PE-to-CE
- **EVPN/VXLAN:** West and East DC fabrics (spine-leaf)
- **MLAG:** Leaf pairs (West-Leaf01/02, East-Leaf01/02)

## Protocol MCP — BGP Participation

NetClaw participates as a live BGP peer via the **Protocol MCP server** (built-in, scapy-based). This is NOT ExaBGP, GoBGP, BIRD, or any external daemon. The speaker is implemented in Python using raw scapy packets.

**CRITICAL RULES:**
- DO NOT install or use ExaBGP, GoBGP, BIRD, FRR, or any external BGP daemon
- DO NOT try to build a new BGP implementation
- DO NOT modify the Protocol MCP server code to add external dependencies
- USE ONLY the built-in tools: `bgp_get_peers`, `bgp_get_rib`, `bgp_inject_route`, `bgp_withdraw_route`, `bgp_adjust_local_pref`, `protocol_summary`
- The Protocol MCP server handles all BGP session management internally via scapy

**Architecture — GRE Tunnel Peering:**

The management interfaces on ContainerLab devices are in VRF `clab-mgmt`. BGP peering in a VRF won't reflect routes to the global table (where PE1/PE2/PE3 live). So we use a GRE tunnel to bridge into the global routing domain:

```
NetClaw Host (192.168.220.1)                    RR1 (192.168.220.11)
     │                                               │
     │  GRE tunnel (transport via clab-mgmt L2)      │
     │  local: 192.168.220.1                         │
     │  remote: 192.168.220.11                       │
     │                                               │
     ├─ gre-rr1 interface: 10.255.255.1/30           ├─ Tunnel0: 10.255.255.2/30
     │  (global table on host)                       │  (global table on RR1)
     │                                               │
     └─ eBGP session: 10.255.255.1 ──────────────── 10.255.255.2
        AS 65099                                     AS 65000
```

The GRE tunnel's underlay uses the clab-mgmt IPs (reachable at L2), but the tunnel interface itself lives in the global routing table on RR1. This means routes injected by NetClaw get reflected to PE1/PE2/PE3 via iBGP — exactly like a real eBGP peer.

**Host-side GRE setup (run once, or add to a startup script):**
```bash
sudo ip tunnel add gre-rr1 mode gre remote 192.168.220.11 local 192.168.220.1
sudo ip addr add 10.255.255.1/30 dev gre-rr1
sudo ip link set gre-rr1 up
```

**RR1-side config (apply via pyATS or SSH):**
```
interface Tunnel0
 ip address 10.255.255.2 255.255.255.252
 tunnel source Ethernet0/0
 tunnel destination 192.168.220.1
!
router bgp 65000
 neighbor 10.255.255.1 remote-as 65099
 neighbor 10.255.255.1 description NetClaw-Protocol-MCP
 neighbor 10.255.255.1 update-source Tunnel0
 address-family ipv4 unicast
  neighbor 10.255.255.1 activate
  neighbor 10.255.255.1 route-map NETCLAW-IN in
  neighbor 10.255.255.1 route-map NETCLAW-OUT out
!
route-map NETCLAW-IN permit 10
 set local-preference 50
!
route-map NETCLAW-OUT permit 10
```

**Environment variables (set in openclaw.json):**
```
NETCLAW_ROUTER_ID=4.4.4.4
NETCLAW_LOCAL_AS=65099
NETCLAW_BGP_PEERS=[{"ip":"10.255.255.2","as":65000}]
```

**How it works:**
- The Protocol MCP server starts when the OpenClaw gateway launches
- It initializes a BGP speaker using scapy raw sockets (requires cap_net_raw on Python binary)
- It establishes an eBGP session with RR1 at 10.255.255.2 via the GRE tunnel
- RR1 reflects injected routes to PE1/PE2/PE3 via iBGP (global table)
- All 10 protocol tools are then available to the agent
- Metrics are exported at :9179/metrics (Prometheus format) for the observability stack

## Golden Config and Data Source Git Repos

These repos are pre-built and ready for Nautobot:
- Data source (config contexts, schemas, jobs): https://github.com/byrn-baker/Nautobot-Workshop-Datasource
- Templates: https://github.com/byrn-baker/nautobot_workshop_golden_config_templates
- Intended configs: https://github.com/byrn-baker/nautobot_workshop_golden_config_intended_configs
- Backup configs: https://github.com/byrn-baker/nautobot_workshop_golden_config_backup_configs
- Properties: https://github.com/byrn-baker/nautobot_workshop_golden_config_properties
- SoT/config: https://github.com/byrn-baker/golden_config_git

## Golden Config MCP Server (nautobot-golden-config-mcp)

Dedicated MCP server for golden config lifecycle operations. Replaces the scattered golden config tools in nautobot-mcp-v2 with purpose-built, one-call tools.

**Config Lifecycle (one call per operation):**
- `golden_config_generate_intended(device=)` — render intended config from templates + SoT
- `golden_config_backup(device=)` — pull running config from device(s)
- `golden_config_compliance(device=)` — compare intended vs backup
- `golden_config_full_pipeline(device=)` — run all three in sequence
- `golden_config_remediate(device=, cr_number=)` — push intended to fix drift (ITSM-gated)

**Config Inspection (one call per query):**
- `golden_config_get_intended(device=)` — get rendered intended config text
- `golden_config_get_backup(device=)` — get latest backup config text
- `golden_config_get_compliance_diff(device=)` — per-feature diffs (missing/extra)
- `golden_config_get_compliance_summary(device=, feature=)` — compliance table

**Template & Context:**
- `golden_config_get_templates(device=)` — list templates for a device
- `golden_config_render_preview(device=)` — preview rendered config
- `golden_config_get_device_context(device=)` — merged config context
- `golden_config_update_device_context(device=, key=, value=)` — update context key
- `golden_config_update_template(path=, content=)` — prepare template for git commit

**Setup:**
- `golden_config_get_settings()` — current GC settings (repos, paths, query)
- `golden_config_create_compliance_feature(name=)` — create feature
- `golden_config_create_compliance_rule(feature=, platform=, match_config=)` — create rule

## Platform Credentials

All credentials are in `~/.openclaw/.env`. Never put credentials in skill files or this document.

```
### Connection Details (reference only — actual values in .env)
- pyATS Testbed       → PYATS_TESTBED_PATH
- Nautobot            → NAUTOBOT_URL, NAUTOBOT_TOKEN
- Proxmox             → PROXMOX_HOST, PROXMOX_TOKEN_NAME, PROXMOX_TOKEN_VALUE
```
