# Defaults and options

## Defaults

| Parameter | Default |
|---|---|
| Redundancy | Single-link tolerance |
| Routing | OSPF single area for campus; eBGP at WAN edges |
| Scale | Smallest viable design for the stated topology type |
| Images | IOL L3 for routers, IOL L2 for switches, VPCS for hosts |
| Scope | Design + build plan, no config unless asked |

Always label defaults explicitly.

## Requirements summary artifacts

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

State which single failures the design must survive.

## Option tables

### L2 vs L3 access
| Option | Use when | Trade-off |
|---|---|---|
| L3 access | Scalability and fast convergence matter | More complex config |
| L2 access + L3 at distribution | Simpler access layer | Larger L2 failure domain |
| Collapsed core | Small labs | Less redundancy |

### Routing
| Protocol | Fits well | Avoid when |
|---|---|---|
| OSPF single area | Campus and small WAN labs | Large inter-domain designs |
| eBGP | ISP/SP, inter-DC, WAN edges | Pure campus interior |
| IS-IS | SP core | Typical enterprise campus labs |
| Static | Tiny or stub labs | Anything needing failover |
