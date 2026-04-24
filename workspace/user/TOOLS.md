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
- API Token: configured in ~/.openclaw/.env as NAUTOBOT_TOKEN
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

## Platform Credentials

All credentials are in `~/.openclaw/.env`. Never put credentials in skill files or this document.

```
### Connection Details (reference only — actual values in .env)
- pyATS Testbed       → PYATS_TESTBED_PATH
- Nautobot            → NAUTOBOT_URL, NAUTOBOT_TOKEN
```
