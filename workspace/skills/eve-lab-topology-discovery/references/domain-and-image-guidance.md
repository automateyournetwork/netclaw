# Domain and image guidance

## Image selection

| Role | Recommended image | Notes |
|---|---|---|
| L3 router / PE / P | Cisco IOL L3 | Lightweight |
| L2 switch | Cisco IOL L2 | Good VLAN/STP support |
| Host | VPCS | Minimal RAM |
| Linux host | Alpine/TinyCore | Use when VPCS is insufficient |
| Arista switch | vEOS-lab | Higher RAM use |
| Juniper router | vMX or vSRX | Heavy RAM footprint |
| NX-OS switch | NX-OSv 9000 | Use when NX-OS behavior matters |

## Domain guidance

### Enterprise Campus
- Collapsed core for small labs; three-tier for larger ones.
- Dual uplinks from access to distribution are the baseline.

### Enterprise Branch / WAN
- Hub-and-spoke for small branch counts.
- BGP at WAN edges; OSPF/EIGRP internally.

### ISP / Service Provider
- Keep P / PE / CE roles explicit.
- IS-IS or OSPF in the core.

### Data Center
- Use leaf-spine beyond very small labs.
- No leaf-to-leaf or spine-to-spine links in leaf-spine.

### Hybrid / Multi-domain
- Keep domain boundaries explicit.
- Name redistribution points directly.
