---
name: evpn-vxlan-fabric
description: "EVPN/VXLAN fabric audit and troubleshooting — VTEPs, VNIs, route types, multihoming, underlay/overlay validation. Use when troubleshooting VXLAN overlay reachability, auditing leaf-spine fabric health, debugging silent hosts or asymmetric flooding, or validating anycast gateway and ESI multihoming state."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# EVPN/VXLAN Fabric

## Primary Backends

- `pyats-network`
- `pyats-routing`
- `pyats-topology`
- `netbox-reconcile`

## Focus Areas

- VTEP reachability and loopback consistency
- VXLAN VNI to VLAN mapping
- EVPN route types 2, 3, and 5
- Anycast gateway consistency
- Multihoming and Ethernet Segment state
- Underlay routing health vs overlay symptoms

## When to Use

- EVPN MAC/IP reachability issues
- Silent hosts or asymmetric flooding complaints
- Anycast gateway or ARP suppression problems
- Leaf-spine underlay failures impacting overlay forwarding
- Data-center fabric audit and documentation

## Workflow: Overlay Reachability

1. Verify underlay reachability between VTEPs.
2. Check BGP EVPN session health and route-type presence.
3. Validate VNI mapping, bridge domains, and anycast gateway settings.
4. Cross-check local MAC learning against EVPN advertisements.
5. Reconcile intended VLAN/VNI mappings against NetBox or ACI intent.

## Workflow: Multihoming / ESI Trouble

1. Confirm the access device and leaf pair are both healthy.
2. Validate Ethernet Segment identifiers and DF election state.
3. Check for duplicate MAC movement or split-horizon symptoms.
4. Verify LACP state, access VLANs, and host-facing port consistency.

## Important Rules

- **Always validate the underlay before blaming the overlay**
- **Do not push fabric config without approved change control**
- **Use route-type evidence, not assumptions, to explain forwarding**
