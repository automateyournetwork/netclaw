# 02 — SP Core Topology

## Overview

The SP core is a classic ISP backbone with:
- 2 Route Reflectors (RR1, RR2)
- 4 P routers (SP1–SP4) forming a square ring
- 3 PE routers (SPE1–SPE3) at the edge, dual-homed into the ring

All internal routing uses IS-IS or OSPF (area 0) for the underlay, with LDP or
Segment Routing for MPLS label distribution. iBGP (AS 65000) with VPNv4/VPNv6
address families carries customer routes via the route reflectors.

## Topology Diagram

```
              RR1                    RR2
               │                     │
         10.0.0.20/31          10.0.0.22/31
               │                     │
             SP1 ─── 10.0.0.0/31 ─── SP2
            / │ \                   / │ \
  10.0.0.16  │  10.0.0.6       10.0.0.2  │  10.0.0.8
      /      │       \         /      │       \
   SPE3      │       SP3 ─── SP4      │      SPE1
      \      │       /    10.0.0.4    \│      /
  10.0.0.18  │  10.0.0.14         10.0.0.12  10.0.0.10
              \  /                       \  /
             SPE2                       (alt paths)
```

## Device Roles

| Device | Role | Function |
|--------|------|----------|
| RR1 | Route Reflector | iBGP VPNv4/v6 route reflection (cluster-id 1) |
| RR2 | Route Reflector | iBGP VPNv4/v6 route reflection (cluster-id 1) |
| SP1 | P router | Core transit, MPLS forwarding only |
| SP2 | P router | Core transit, MPLS forwarding only |
| SP3 | P router | Core transit, MPLS forwarding only |
| SP4 | P router | Core transit, MPLS forwarding only |
| SPE1 | PE router | Customer A attachment, VRF CUST-A |
| SPE2 | PE router | Customer B attachment, VRF CUST-B |
| SPE3 | PE router | Customer C attachment, VRF CUST-C |

## CML Node Types

| Device | CML Image | vCPU | RAM | Notes |
|--------|-----------|------|-----|-------|
| RR1, RR2 | CSR1000v or IOSv | 1 | 3 GB | Lightweight — no forwarding traffic |
| SP1–SP4 | CSR1000v or IOSv | 1 | 3 GB | MPLS P routers |
| SPE1–SPE3 | CSR1000v (or XRv9k) | 1 | 4 GB | VRF + MPLS + eBGP to CEs |

## IGP Design

- **Protocol:** IS-IS (Level 2 only) or OSPF area 0
- **Metric style:** Wide metrics
- **All P2P links:** `network point-to-point` (no DR election)
- **Loopbacks:** Advertised as /32 (passive interface)
- **BFD:** Enabled on all IGP adjacencies for fast convergence

## MPLS Design

- **Label distribution:** LDP (or Segment Routing if using XRv9k)
- **LDP sync:** Enabled with IGP (prevents black-holing during LDP convergence)
- **Explicit null:** Enabled for QoS preservation at egress PE

## BGP Design

- **AS:** 65000 (all routers)
- **Route Reflectors:** RR1 + RR2 (redundant, same cluster-id)
- **Clients:** SPE1, SPE2, SPE3 (PE routers only)
- **Address families:** VPNv4 unicast, VPNv6 unicast
- **Update source:** Loopback0
- **Next-hop-self:** On RRs (or leave unchanged — PEs already in iBGP)

### BGP Session Map

```
SPE1 ──→ RR1 (vpnv4, vpnv6)
SPE1 ──→ RR2 (vpnv4, vpnv6)
SPE2 ──→ RR1 (vpnv4, vpnv6)
SPE2 ──→ RR2 (vpnv4, vpnv6)
SPE3 ──→ RR1 (vpnv4, vpnv6)
SPE3 ──→ RR2 (vpnv4, vpnv6)
```

P routers (SP1–SP4) do NOT participate in BGP — they are MPLS-only transit.

## Convergence Targets

| Event | Target | Mechanism |
|-------|--------|-----------|
| Link failure | < 50 ms | BFD (10ms interval × 3) |
| Node failure | < 1 sec | IGP SPF + LDP convergence |
| PE failure | < 3 sec | BGP hold timer + BFD |
