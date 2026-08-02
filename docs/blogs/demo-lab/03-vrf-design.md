# 03 — VRF / L3VPN Design

## Overview

Each datacenter represents a separate customer connected to the SP via MPLS
L3VPN. The PEs host VRFs and run eBGP with the customer CE routers. VPN routes
are carried across the core via MP-BGP VPNv4/VPNv6 through the route reflectors.

## VRF Table

| DC | Customer | VRF Name | RD | RT Import | RT Export | PE | CE ASN |
|----|----------|----------|-----|-----------|-----------|-----|--------|
| DC1 | Customer A | `CUST-A` | `65000:100` | `65000:100` | `65000:100` | SPE1 | 65001 |
| DC2 | Customer B | `CUST-B` | `65000:200` | `65000:200` | `65000:200` | SPE2 | 65002 |
| DC3 | Customer C | `CUST-C` | `65000:300` | `65000:300` | `65000:300` | SPE3 | 65003 |

## PE-CE Peering

| PE | VRF | PE IP | CE IP | CE ASN | AFI |
|----|-----|-------|-------|--------|-----|
| SPE1 | CUST-A | `172.16.1.0` | `172.16.1.1` | 65001 | IPv4 + IPv6 |
| SPE2 | CUST-B | `172.16.2.0` | `172.16.2.1` | 65002 | IPv4 + IPv6 |
| SPE3 | CUST-C | `172.16.3.0` | `172.16.3.1` | 65003 | IPv4 + IPv6 |

## PE VRF Configuration (IOS-XE example)

```ios
! SPE1
vrf definition CUST-A
 rd 65000:100
 address-family ipv4
  route-target export 65000:100
  route-target import 65000:100
 address-family ipv6
  route-target export 65000:100
  route-target import 65000:100

interface GigabitEthernet3
 description PE-CE link to DC1 (Customer A)
 vrf forwarding CUST-A
 ip address 172.16.1.0 255.255.255.254
 ipv6 address fd10:c:1::/127
 no shutdown

router bgp 65000
 address-family ipv4 vrf CUST-A
  neighbor 172.16.1.1 remote-as 65001
  neighbor 172.16.1.1 activate
 address-family ipv6 vrf CUST-A
  neighbor fd10:c:1::1 remote-as 65001
  neighbor fd10:c:1::1 activate
```

## CE Configuration (IOS-XE example)

```ios
! CE1 (DC1 — Customer A)
router bgp 65001
 bgp router-id 172.16.1.1
 neighbor 172.16.1.0 remote-as 65000
 address-family ipv4
  network 192.168.100.0 mask 255.255.255.0
  neighbor 172.16.1.0 activate
 address-family ipv6
  network fd10:a:100::/64
  neighbor fd10:c:1:: remote-as 65000
  neighbor fd10:c:1:: activate

interface GigabitEthernet2
 description Uplink to SPE1
 ip address 172.16.1.1 255.255.255.254
 ipv6 address fd10:c:1::1/127
 no shutdown

interface GigabitEthernet3
 description DC1 LAN (to K3s nodes)
 ip address 192.168.100.1 255.255.255.0
 ipv6 address fd10:a:100::1/64
 no shutdown
```

## Route Flow

```
DC1 servers (192.168.100.0/24)
  → advertised by CE1 via eBGP to SPE1 (VRF CUST-A)
    → SPE1 exports as VPNv4 with RD 65000:100, RT 65000:100
      → MP-iBGP to RR1/RR2
        → RR reflects to SPE2, SPE3
          → SPE2 imports into CUST-B? NO (RT doesn't match)
          → Customers are isolated by default
```

## Inter-Customer Connectivity (Optional Extranet)

To demonstrate shared services (e.g., a central DNS or monitoring server
reachable by all customers):

```ios
! On SPE1 — add a shared services VRF
vrf definition SHARED-SVC
 rd 65000:999
 address-family ipv4
  route-target export 65000:999
  route-target import 65000:100
  route-target import 65000:200
  route-target import 65000:300

! On each customer VRF — import shared services
vrf definition CUST-A
 address-family ipv4
  route-target import 65000:999   ! <-- add this line
```

This gives all customers access to SHARED-SVC routes while remaining isolated
from each other — classic hub-and-spoke extranet topology.

## Monitoring Points

| What to monitor | How | Alert condition |
|-----------------|-----|-----------------|
| PE-CE BGP session state | `show bgp vpnv4 unicast all summary` | Peer state != Established |
| VRF route count | `show bgp vpnv4 unicast vrf CUST-A summary` | Route count drops to 0 |
| RT import/export | Config audit | Unexpected RT leaking |
| VPNv4 prefix count on RR | `show bgp vpnv4 unicast all` | Total VPN routes change unexpectedly |
| PE-CE BFD | `show bfd neighbors` | Session down |
