# Discovery workflow

Use this reference when requirements are incomplete or when design trade-offs need structure.

## Minimal discovery rule

- Ask at most 5 questions in one turn.
- Group related questions.
- Offer labeled defaults for anything the user skips.
- If the request is already specific enough, skip directly to requirements summarization.

## Preferred question bank

1. Topology type — campus, branch/WAN, ISP/SP, data center, or hybrid?
2. Scale — how many sites, tiers, or devices?
3. Hierarchy / fabric style — three-tier, collapsed core, leaf-spine, hub-spoke, flat mesh?
4. Routing / control plane — OSPF, EIGRP, BGP, IS-IS, static, or undecided?
5. Redundancy target — single-link tolerance, single-node tolerance, or best-effort?
6. Image / platform choices — Cisco IOL, IOS-XE CSR, vMX, vEOS, NX-OSv, VPCS, or open?
7. Host resource limits — RAM and vCPU available for the lab?
8. Scope — design only, design + build, or design + build + config?
9. Existing lab — extend an existing `.unl`, or start from scratch?

## Default policy

| Parameter | Default |
|---|---|
| Redundancy | Single-link tolerance |
| Routing | OSPF single area for campus; eBGP at WAN edges |
| Scale | Smallest viable design for the stated topology type |
| Images | IOL L3 for routers, IOL L2 for switches, VPCS for hosts |
| Scope | Design + build plan, no config unless asked |

Always label defaults explicitly.

## Design output inputs

Produce these before final design validation:

### Connectivity matrix

```text
NODE      ROLE          LINKS  NEIGHBORS
CORE1     core          2      DIST1, DIST2
DIST1     distribution  3      CORE1, CORE2, ACC1
ACC1      access        2      DIST1, DIST2
HOST1     host          1      ACC1
```

### Required links list

```text
CORE1 <-> DIST1
CORE2 <-> DIST1
DIST1 <-> ACC1
ACC1  <-> HOST1
```

### Resilience declaration

State explicitly which single failures the design must survive.

## Design options

### L2 vs L3 access

| Option | Use when | Trade-off |
|---|---|---|
| L3 access | Scalability and fast convergence matter | More complex addressing/config |
| L2 access + L3 at distribution | Simpler access layer is preferred | STP dependency, wider failure domain |
| Collapsed core | Small labs | Less redundancy and scale |

### Routing options

| Protocol | Fits well | Avoid when |
|---|---|---|
| OSPF single area | Campus and small WAN labs | Large inter-domain designs |
| OSPF multi-area | Larger enterprise designs | Small labs where complexity adds no value |
| eBGP | ISP/SP, inter-DC, WAN edges | Pure campus interior |
| IS-IS | SP core | Typical enterprise campus labs |
| EIGRP | Cisco-only enterprise labs | Multi-vendor labs |
| Static | Stubs and tiny labs | Anything requiring failover |

### Redundancy levels

| Level | Meaning |
|---|---|
| Full redundancy | No single device or link should be a SPOF |
| Partial redundancy | Balanced design with some accepted SPOFs |
| Best-effort | Minimal node count, limited failover |

## Image selection

| Role | Recommended image | Notes |
|---|---|---|
| L3 router / PE / P | Cisco IOL L3 | Lightweight, good protocol support |
| L2 switch | Cisco IOL L2 | Good VLAN/STP lab choice |
| Host | VPCS | Minimal RAM |
| Linux host | Alpine/TinyCore | Use when VPCS is insufficient |
| Arista switch | vEOS-lab | More RAM required |
| Juniper router | vMX or vSRX | Heavy RAM footprint |
| NX-OS switch | NX-OSv 9000 | Use for NX-OS / EVPN-specific labs |

## Domain guidance

### Enterprise Campus
- Use collapsed core for small labs; three-tier beyond that.
- Dual uplinks from access to distribution are the baseline redundancy target.
- OSPF or EIGRP internally; HSRP/VRRP at gateway tier if needed.

### Enterprise Branch / WAN
- Hub-and-spoke for small branch counts; partial mesh when branch-to-branch traffic matters.
- BGP at WAN edges; OSPF/EIGRP internally.

### ISP / Service Provider
- Separate P, PE, and CE roles clearly.
- IS-IS or OSPF in the core; BGP at service boundaries.

### Data Center
- Use leaf-spine beyond very small labs.
- No leaf-to-leaf or spine-to-spine links in a true leaf-spine design.
- eBGP underlay; EVPN/VXLAN only when requested.

### Hybrid / Multi-domain
- Keep domain boundaries explicit.
- Name redistribution or route-leak points directly.
