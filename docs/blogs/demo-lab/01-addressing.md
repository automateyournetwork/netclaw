# 01 — Addressing Plan

## Design Principles

- IPv4 and IPv6 dual-stack throughout
- ULA (`fd10::/16`) for IPv6 — mirrors IPv4 structure in the prefix
- SP underlay uses `10.x.x.x` space; customer/DC uses RFC 1918 `172.16.x` and `192.168.x`
- Last octet/nibble kept consistent between v4 and v6 for easy cross-reference

---

## OOB Management Network

| Purpose | Subnet | VRF | Gateway |
|---------|--------|-----|---------|
| Management | `192.168.3.0/24` | `MGMT-VRF` | `192.168.3.1` |

All router Gi1 interfaces are placed in `MGMT-VRF` and connected to the
`mgmt-switch` → `lab-mgmt` external connector, which bridges to the Proxmox
management network.

### Management IP Assignments (Gi1 / Management1, VRF MGMT-VRF)

**Cisco (IOS-XE) — Gi1:**

| Device | IPv4 | Interface |
|--------|------|-----------|
| BORDER1 | `192.168.3.19/24` | Gi1 |
| RR1 | `192.168.3.20/24` | Gi1 |
| RR2 | `192.168.3.21/24` | Gi1 |
| SP1 | `192.168.3.22/24` | Gi1 |
| SP2 | `192.168.3.23/24` | Gi1 |
| SP3 | `192.168.3.24/24` | Gi1 |
| SP4 | `192.168.3.25/24` | Gi1 |
| SPE1 | `192.168.3.26/24` | Gi1 |
| SPE2 | `192.168.3.27/24` | Gi1 |
| SPE3 | `192.168.3.28/24` | Gi1 |
| CE1 | `192.168.3.29/24` | Gi1 |
| CE2 | `192.168.3.30/24` | Gi1 |
| CE3 | `192.168.3.31/24` | Gi1 |

**Arista (EOS) — Management1, VRF MGMT-VRF:**

| Device | IPv4 | Interface |
|--------|------|-----------|
| DCA-Spine01 | `192.168.3.40/24` | Management1 |
| DCA-Spine02 | `192.168.3.41/24` | Management1 |
| DCA-Leaf01 | `192.168.3.42/24` | Management1 |
| DCA-Leaf02 | `192.168.3.43/24` | Management1 |
| DCA-Leaf03 | `192.168.3.44/24` | Management1 |
| DCB-Spine01 | `192.168.3.50/24` | Management1 |
| DCB-Spine02 | `192.168.3.51/24` | Management1 |
| DCB-Leaf01 | `192.168.3.52/24` | Management1 |
| DCB-Leaf02 | `192.168.3.53/24` | Management1 |
| DCB-Leaf03 | `192.168.3.54/24` | Management1 |
| DCC-Spine01 | `192.168.3.60/24` | Management1 |
| DCC-Spine02 | `192.168.3.61/24` | Management1 |
| DCC-Leaf01 | `192.168.3.62/24` | Management1 |
| DCC-Leaf02 | `192.168.3.63/24` | Management1 |
| DCC-Leaf03 | `192.168.3.64/24` | Management1 |

### Management VRF config (IOS-XE, all Cisco routers)

```ios
vrf definition MGMT-VRF
 address-family ipv4

interface GigabitEthernet1
 vrf forwarding MGMT-VRF
 ip address 192.168.3.X 255.255.255.0
 no shutdown

ip route vrf MGMT-VRF 0.0.0.0 0.0.0.0 192.168.3.1
```

### Management VRF config (EOS, all Arista switches)

```eos
vrf instance MGMT-VRF

interface Management1
   vrf MGMT-VRF
   ip address 192.168.3.X/24
   no shutdown

ip route vrf MGMT-VRF 0.0.0.0/0 192.168.3.1
```

---

## SP Underlay

| Purpose | IPv4 | IPv6 |
|---------|------|------|
| P2P links | `10.0.0.0/24` | `fd10:0:0::/48` |
| Loopbacks | `10.1.0.0/24` | `fd10:0:1::/48` |

### P2P links (SP core) — /31 IPv4, /127 IPv6

| Link | IPv4 | IPv6 | A side (intf) | B side (intf) |
|------|------|------|---------------|---------------|
| SP1 ↔ SP2 | `10.0.0.0/31` | `fd10:0:0::0/127` | SP1 Gi2 | SP2 Gi2 |
| SP2 ↔ SP4 | `10.0.0.2/31` | `fd10:0:0::2/127` | SP2 Gi3 | SP4 Gi2 |
| SP3 ↔ SP4 | `10.0.0.4/31` | `fd10:0:0::4/127` | SP3 Gi5 | SP4 Gi5 |
| SP1 ↔ SP3 | `10.0.0.6/31` | `fd10:0:0::6/127` | SP1 Gi3 | SP3 Gi3 |
| SP2 ↔ SPE1 | `10.0.0.8/31` | `fd10:0:0::8/127` | SP2 Gi4 | SPE1 Gi2 |
| SP4 ↔ SPE1 | `10.0.0.10/31` | `fd10:0:0::10/127` | SP4 Gi4 | SPE1 Gi4 |
| SP4 ↔ SPE2 | `10.0.0.12/31` | `fd10:0:0::12/127` | SP4 Gi3 | SPE2 Gi2 |
| SP3 ↔ SPE2 | `10.0.0.14/31` | `fd10:0:0::14/127` | SP3 Gi4 | SPE2 Gi3 |
| SP1 ↔ SPE3 | `10.0.0.16/31` | `fd10:0:0::16/127` | SP1 Gi4 | SPE3 Gi2 |
| SP3 ↔ SPE3 | `10.0.0.18/31` | `fd10:0:0::18/127` | SP3 Gi4 | SPE3 Gi3 |
| SP1 ↔ RR1 | `10.0.0.20/31` | `fd10:0:0::20/127` | SP1 Gi5 | RR1 Gi2 |
| SP2 ↔ RR2 | `10.0.0.22/31` | `fd10:0:0::22/127` | SP2 Gi5 | RR2 Gi2 |
| SP1 ↔ BORDER1 | `10.0.0.24/31` | `fd10:0:0::24/127` | SP1 Gi6 | BORDER1 Gi2 |
| SP2 ↔ BORDER1 | `10.0.0.26/31` | `fd10:0:0::26/127` | SP2 Gi6 | BORDER1 Gi3 |

**PE uplink summary (dual-homed, diverse P routers):**
- SPE1: SP2 (Gi2) + SP4 (Gi4)
- SPE2: SP4 (Gi2) + SP3 (Gi3)
- SPE3: SP1 (Gi2) + SP3 (Gi3)

### Loopbacks — /32 IPv4, /128 IPv6

| Device | IPv4 | IPv6 |
|--------|------|------|
| RR1 | `10.1.0.1/32` | `fd10:0:1::1/128` |
| RR2 | `10.1.0.2/32` | `fd10:0:1::2/128` |
| SP1 | `10.1.0.3/32` | `fd10:0:1::3/128` |
| SP2 | `10.1.0.4/32` | `fd10:0:1::4/128` |
| SP3 | `10.1.0.5/32` | `fd10:0:1::5/128` |
| SP4 | `10.1.0.6/32` | `fd10:0:1::6/128` |
| SPE1 | `10.1.0.7/32` | `fd10:0:1::7/128` |
| SPE2 | `10.1.0.8/32` | `fd10:0:1::8/128` |
| SPE3 | `10.1.0.9/32` | `fd10:0:1::9/128` |
| BORDER1 | `10.1.0.10/32` | `fd10:0:1::10/128` |

---

## PE-CE Links (inside VRFs)

| Link | IPv4 | IPv6 | A side (intf) | B side (intf) |
|------|------|------|---------------|---------------|
| SPE1 ↔ CE1 | `172.16.1.0/31` | `fd10:c:1::/127` | SPE1 Gi5 | CE1 Gi2 |
| SPE2 ↔ CE2 | `172.16.2.0/31` | `fd10:c:2::/127` | SPE2 Gi5 | CE2 Gi2 |
| SPE3 ↔ CE3 | `172.16.3.0/31` | `fd10:c:3::/127` | SPE3 Gi5 | CE3 Gi2 |

---

## DC-A P2P Links (CE1 → Arista Fabric)

| Purpose | IPv4 | IPv6 |
|---------|------|------|
| DC-A P2P links | `10.1.1.0/24` | `fd10:1:1::/48` |
| DC-A Loopbacks | `10.2.1.0/24` | `fd10:2:1::/48` |

### CE to Spines

| Link | IPv4 | IPv6 | A side (intf) | B side (intf) |
|------|------|------|---------------|---------------|
| CE1 ↔ DCA-Spine01 | `10.1.1.0/31` | `fd10:1:1::0/127` | CE1 Gi3 | Spine01 Eth1 |
| CE1 ↔ DCA-Spine02 | `10.1.1.2/31` | `fd10:1:1::2/127` | CE1 Gi4 | Spine02 Eth1 |

### Spine to Leaf

| Link | IPv4 | IPv6 | A side (intf) | B side (intf) |
|------|------|------|---------------|---------------|
| DCA-Spine01 ↔ DCA-Leaf01 | `10.1.1.4/31` | `fd10:1:1::4/127` | Spine01 Eth2 | Leaf01 Eth1 |
| DCA-Spine01 ↔ DCA-Leaf02 | `10.1.1.6/31` | `fd10:1:1::6/127` | Spine01 Eth3 | Leaf02 Eth1 |
| DCA-Spine01 ↔ DCA-Leaf03 | `10.1.1.8/31` | `fd10:1:1::8/127` | Spine01 Eth4 | Leaf03 Eth1 |
| DCA-Spine02 ↔ DCA-Leaf01 | `10.1.1.10/31` | `fd10:1:1::10/127` | Spine02 Eth2 | Leaf01 Eth2 |
| DCA-Spine02 ↔ DCA-Leaf02 | `10.1.1.12/31` | `fd10:1:1::12/127` | Spine02 Eth3 | Leaf02 Eth2 |
| DCA-Spine02 ↔ DCA-Leaf03 | `10.1.1.14/31` | `fd10:1:1::14/127` | Spine02 Eth4 | Leaf03 Eth2 |

### DC-A Loopbacks

| Device | IPv4 | IPv6 |
|--------|------|------|
| CE1 | `10.2.1.1/32` | `fd10:2:1::1/128` |
| DCA-Spine01 | `10.2.1.2/32` | `fd10:2:1::2/128` |
| DCA-Spine02 | `10.2.1.3/32` | `fd10:2:1::3/128` |
| DCA-Leaf01 | `10.2.1.4/32` | `fd10:2:1::4/128` |
| DCA-Leaf02 | `10.2.1.5/32` | `fd10:2:1::5/128` |
| DCA-Leaf03 | `10.2.1.6/32` | `fd10:2:1::6/128` |

---

## DC-B P2P Links (CE2 → Arista Fabric)

| Purpose | IPv4 | IPv6 |
|---------|------|------|
| DC-B P2P links | `10.1.2.0/24` | `fd10:1:2::/48` |
| DC-B Loopbacks | `10.2.2.0/24` | `fd10:2:2::/48` |

### CE to Spines

| Link | IPv4 | IPv6 | A side (intf) | B side (intf) |
|------|------|------|---------------|---------------|
| CE2 ↔ DCB-Spine01 | `10.1.2.0/31` | `fd10:1:2::0/127` | CE2 Gi3 | Spine01 Eth1 |
| CE2 ↔ DCB-Spine02 | `10.1.2.2/31` | `fd10:1:2::2/127` | CE2 Gi4 | Spine02 Eth1 |

### Spine to Leaf

| Link | IPv4 | IPv6 | A side (intf) | B side (intf) |
|------|------|------|---------------|---------------|
| DCB-Spine01 ↔ DCB-Leaf01 | `10.1.2.4/31` | `fd10:1:2::4/127` | Spine01 Eth2 | Leaf01 Eth1 |
| DCB-Spine01 ↔ DCB-Leaf02 | `10.1.2.6/31` | `fd10:1:2::6/127` | Spine01 Eth3 | Leaf02 Eth1 |
| DCB-Spine01 ↔ DCB-Leaf03 | `10.1.2.8/31` | `fd10:1:2::8/127` | Spine01 Eth4 | Leaf03 Eth1 |
| DCB-Spine02 ↔ DCB-Leaf01 | `10.1.2.10/31` | `fd10:1:2::10/127` | Spine02 Eth2 | Leaf01 Eth2 |
| DCB-Spine02 ↔ DCB-Leaf02 | `10.1.2.12/31` | `fd10:1:2::12/127` | Spine02 Eth3 | Leaf02 Eth2 |
| DCB-Spine02 ↔ DCB-Leaf03 | `10.1.2.14/31` | `fd10:1:2::14/127` | Spine02 Eth4 | Leaf03 Eth2 |

### DC-B Loopbacks

| Device | IPv4 | IPv6 |
|--------|------|------|
| CE2 | `10.2.2.1/32` | `fd10:2:2::1/128` |
| DCB-Spine01 | `10.2.2.2/32` | `fd10:2:2::2/128` |
| DCB-Spine02 | `10.2.2.3/32` | `fd10:2:2::3/128` |
| DCB-Leaf01 | `10.2.2.4/32` | `fd10:2:2::4/128` |
| DCB-Leaf02 | `10.2.2.5/32` | `fd10:2:2::5/128` |
| DCB-Leaf03 | `10.2.2.6/32` | `fd10:2:2::6/128` |

---

## DC-C P2P Links (CE3 → Arista Fabric)

| Purpose | IPv4 | IPv6 |
|---------|------|------|
| DC-C P2P links | `10.1.3.0/24` | `fd10:1:3::/48` |
| DC-C Loopbacks | `10.2.3.0/24` | `fd10:2:3::/48` |

### CE to Spines

| Link | IPv4 | IPv6 | A side (intf) | B side (intf) |
|------|------|------|---------------|---------------|
| CE3 ↔ DCC-Spine01 | `10.1.3.0/31` | `fd10:1:3::0/127` | CE3 Gi3 | Spine01 Eth1 |
| CE3 ↔ DCC-Spine02 | `10.1.3.2/31` | `fd10:1:3::2/127` | CE3 Gi4 | Spine02 Eth1 |

### Spine to Leaf

| Link | IPv4 | IPv6 | A side (intf) | B side (intf) |
|------|------|------|---------------|---------------|
| DCC-Spine01 ↔ DCC-Leaf01 | `10.1.3.4/31` | `fd10:1:3::4/127` | Spine01 Eth2 | Leaf01 Eth1 |
| DCC-Spine01 ↔ DCC-Leaf02 | `10.1.3.6/31` | `fd10:1:3::6/127` | Spine01 Eth3 | Leaf02 Eth1 |
| DCC-Spine01 ↔ DCC-Leaf03 | `10.1.3.8/31` | `fd10:1:3::8/127` | Spine01 Eth4 | Leaf03 Eth1 |
| DCC-Spine02 ↔ DCC-Leaf01 | `10.1.3.10/31` | `fd10:1:3::10/127` | Spine02 Eth2 | Leaf01 Eth2 |
| DCC-Spine02 ↔ DCC-Leaf02 | `10.1.3.12/31` | `fd10:1:3::12/127` | Spine02 Eth3 | Leaf02 Eth2 |
| DCC-Spine02 ↔ DCC-Leaf03 | `10.1.3.14/31` | `fd10:1:3::14/127` | Spine02 Eth4 | Leaf03 Eth2 |

### DC-C Loopbacks

| Device | IPv4 | IPv6 |
|--------|------|------|
| CE3 | `10.2.3.1/32` | `fd10:2:3::1/128` |
| DCC-Spine01 | `10.2.3.2/32` | `fd10:2:3::2/128` |
| DCC-Spine02 | `10.2.3.3/32` | `fd10:2:3::3/128` |
| DCC-Leaf01 | `10.2.3.4/32` | `fd10:2:3::4/128` |
| DCC-Leaf02 | `10.2.3.5/32` | `fd10:2:3::5/128` |
| DCC-Leaf03 | `10.2.3.6/32` | `fd10:2:3::6/128` |

---

## DC Server/Host Subnets (on Leafs — VXLAN VNIs)

| DC | VLAN | Subnet (IPv4) | Subnet (IPv6) | VNI | Purpose |
|----|------|---------------|---------------|-----|---------|
| DC-A | 100 | `192.168.100.0/24` | `fd10:a:100::/64` | 10100 | Server/K3s |
| DC-A | 101 | `192.168.101.0/24` | `fd10:a:101::/64` | 10101 | Storage |
| DC-B | 200 | `192.168.200.0/24` | `fd10:a:200::/64` | 10200 | Server/K3s |
| DC-B | 201 | `192.168.201.0/24` | `fd10:a:201::/64` | 10201 | Storage |
| DC-C | 300 | `192.168.300.0/24` | `fd10:a:300::/64` | 10300 | Server/K3s |
| DC-C | 301 | `192.168.301.0/24` | `fd10:a:301::/64` | 10301 | Storage |

### K3s Node Addresses

| DC | Node | IPv4 | IPv6 | Leaf | Role |
|----|------|------|------|------|------|
| DC-A | k3s-m1 | `192.168.100.10` | `fd10:a:100::10` | Leaf01 | K3s server |
| DC-A | k3s-w1 | `192.168.100.11` | `fd10:a:100::11` | Leaf02 | K3s agent |
| DC-A | k3s-w2 | `192.168.100.12` | `fd10:a:100::12` | Leaf03 | K3s agent |
| DC-B | k3s-m2 | `192.168.200.10` | `fd10:a:200::10` | Leaf01 | K3s server |
| DC-B | k3s-w3 | `192.168.200.11` | `fd10:a:200::11` | Leaf02 | K3s agent |
| DC-B | k3s-w4 | `192.168.200.12` | `fd10:a:200::12` | Leaf03 | K3s agent |
| DC-C | k3s-m3 | `192.168.300.10` | `fd10:a:300::10` | Leaf01 | K3s server |
| DC-C | k3s-w5 | `192.168.300.11` | `fd10:a:300::11` | Leaf02 | K3s agent |

---

## ASN Assignments

| Entity | ASN | Purpose |
|--------|-----|---------|
| SP Core | 65000 | iBGP (all P/PE/RR) |
| Customer A (CE1) | 65001 | eBGP PE-CE |
| Customer B (CE2) | 65002 | eBGP PE-CE |
| Customer C (CE3) | 65003 | eBGP PE-CE |
| DC-A Spines | 65101 | eBGP underlay (DC-A fabric) |
| DC-A Leaf01 | 65111 | eBGP underlay |
| DC-A Leaf02 | 65112 | eBGP underlay |
| DC-A Leaf03 | 65113 | eBGP underlay |
| DC-B Spines | 65201 | eBGP underlay (DC-B fabric) |
| DC-B Leaf01 | 65211 | eBGP underlay |
| DC-B Leaf02 | 65212 | eBGP underlay |
| DC-B Leaf03 | 65213 | eBGP underlay |
| DC-C Spines | 65301 | eBGP underlay (DC-C fabric) |
| DC-C Leaf01 | 65311 | eBGP underlay |
| DC-C Leaf02 | 65312 | eBGP underlay |
| DC-C Leaf03 | 65313 | eBGP underlay |
