# Routed-lab collection and verification commands

Owner expansion, 2026-11-22: R1/R2 point-to-point /31, OSPF underlay, loopback
IPv4 iBGP overlay, router-on-stick VLAN10/20 on R1/SW1 and VLAN30/40 on R2/SW2,
access ports and STP. Exact addressing, CML wiring, candidates, baselines and
rollback stay in the private `.spec200-local/routed-lab*` change records.
See [actual routed-lab qualification](routed-lab-qualification.md) for outcomes
and retained failures.

These are role-scoped native pyATS commands, not one unbounded `learn all` call.
An unsupported command or parser produces an explicit unavailable/raw-only result;
never substitute configuration, infer health or silently retry. Exact peer,
interface, VLAN, prefix and probe arguments come from the frozen private plan.

| Layer | Devices | Command(s) | Facts / verification |
| --- | --- | --- | --- |
| Identity | All four | `show version` | OS/image/platform/uptime |
| Interface summary | All four | `show ip interface brief`; `show interfaces description` | Names, administrative/operational state and intended role |
| Interface evidence | All four | `show interfaces` twice, ≥10 seconds apart | Raw counters/errors/discards when provided, state, MTU; rates require verified continuity and timing |
| CDP | All four | `show cdp`; `show cdp interface`; `show cdp neighbors detail` | Global enablement, per-port discovery and observed neighbor/port claims |
| LLDP | All four | `show lldp`; `show lldp interface`; `show lldp neighbors detail` | Global/per-port state, chassis/port claims, timers and conflicts |
| Protocol scope | R1/R2 | `show ip protocols` | Actual processes, router IDs, passive interfaces and filtering |
| OSPF process | R1/R2 | `show ip ospf` | Process/router/area identity and SPF state |
| OSPF adjacency | R1/R2 | `show ip ospf neighbor detail` | Expected peer FULL state, timers and interface |
| OSPF link type | R1/R2 | `show ip ospf interface brief`; `show ip ospf interface Ethernet0/1` | Area0, point-to-point type, cost, hello/dead timers and adjacency count |
| OSPF LSDB | R1/R2 | `show ip ospf database router` | Router LSAs supporting the underlay; not a physical adjacency substitute |
| iBGP session | R1/R2 | `show ip bgp summary`; `show ip bgp neighbors <peer-loopback>` | AS, Established state, loopback endpoints, capabilities and prefix counts |
| iBGP routes | R1/R2 | `show ip bgp` | Originated/received VLAN prefixes, best path, next hop, AS path and attributes |
| Per-peer advertisements | R1/R2 | `show ip bgp neighbors <peer-loopback> advertised-routes`; `show ip bgp neighbors <peer-loopback> routes` | Exported and accepted peer routes; `received-routes` is not used because it requires an additional inbound-storage feature |
| BGP filters | R1/R2 | `show ip prefix-list` | Exact local/remote VLAN allowlists; no broad redistribution |
| Installed routes | R1/R2 | `show ip route`; `show ip route ospf`; `show ip route bgp`; `show ip route connected` | OSPF loopback reachability, BGP remote VLAN routes and directly connected local VLANs |
| Forwarding | R1/R2 | `show ip cef <remote-prefix>` | Resolved forwarding next hop; separate from BGP/RIB presence |
| Router-on-stick | R1/R2 | `show interfaces Ethernet0/2`; `show interfaces Ethernet0/2.<vlan>`; `show ip interface Ethernet0/2.<vlan>` | Physical uplink, dot1Q tag, gateway address, state and counters |
| VLAN database | SW1/SW2 | `show vlan brief` | Actual VLAN existence, names and access-port membership |
| Trunks | SW1/SW2 | `show interfaces trunk`; `show interfaces Ethernet0/1 switchport` | Operational dot1Q trunk, explicit allowed VLANs, native VLAN and DTP state |
| Access ports | SW1/SW2 | `show interfaces status`; `show interfaces Ethernet0/2 switchport`; `show interfaces Ethernet0/3 switchport` | Access VLAN assignment and physical state; stopped PCs are not healthy hosts |
| STP overview | SW1/SW2 | `show spanning-tree summary`; `show spanning-tree root` | Rapid-PVST mode, per-VLAN roots and priorities |
| STP VLAN evidence | SW1/SW2 | `show spanning-tree vlan <vlan> detail` | Root identity, port role/state, topology-change evidence |
| STP port protection | SW1/SW2 | `show spanning-tree interface <data-port> detail`; `show spanning-tree inconsistentports` | Router-facing trunk/host edge behavior, BPDU Guard and consistency findings |
| Port faults | SW1/SW2 | `show interfaces status err-disabled`; `show errdisable recovery`; `show interfaces counters errors` | Error-disable causes and error counters; no automatic recovery or counter clearing |
| Endpoint evidence | SW1/SW2; R1/R2 | `show mac address-table dynamic`; `show ip arp` | Learned MAC/VLAN/port and ARP/IP correlations; not proof of end-to-end reachability |
| Logs | All four | `show logging` | Bounded post-change errors, adjacency and native-VLAN warnings |
| Change audit only | All four | `show running-config`; `show startup-config` | Exact delta, management exclusions, intended protocol scope and saved-state verification; raw configurations never go to Google |
| Active verification | R1/R2 | `ping <peer-loopback> source Loopback0 repeat 5`; `ping <remote-gateway-or-running-PC> source <local-VLAN-gateway> repeat 5` | Actual control-plane and bidirectional inter-VLAN data-path tests |

The initial six-read collector profile remains a separate source contract. This
expanded list is the requested routed-lab profile and verification scope; it is
not implemented merely by documenting it. Run bounded waves, two concurrent
devices maximum, one command at a time per device, 30-second show bounds and
retained per-command outcomes. Freeze each wave's exact commands before execution;
no automatic perpetual polling or scope growth. Configuration and save operations
use the separate authorized native configuration tool, never the read collector.

Configuration facts and routing outcomes stay local. A later Google projection
can describe reviewed roles, relationships, VLAN/OSPF/BGP layers and coarse state
only after the exact outbound data is reviewed. The first Google proof remains
independent fiction. Generated links, traffic or route changes are illustration,
not measured protocol behavior.

## Design checks

- OSPF carries only the router interconnect and loopbacks; VLAN networks use iBGP.
- Two routers need one iBGP adjacency, with loopback update-source, next-hop-self
  and explicit VLAN import/export prefix filters. No route reflector is needed.
- Management addressing/exclusions and the pre-existing management default remain
  separate from the dynamic data network. No static data routes are introduced.
- Router-facing trunks terminate on routing-only ports, so trunk PortFast/BPDU
  Guard is appropriate for this topology. Do not apply that policy to a future
  inter-switch trunk. Host access ports use PortFast and BPDU Guard; no BPDU filter.
- The installed IOL-L2 rejected `spanning-tree portfast edge trunk`; the initial
  partial attempt is retained and reconciled before the compatible legacy spelling.
- CML PC boot configuration is intended state. Actual booted status and ping/ARP/MAC
  observations are separate; stopped PCs cannot pass reachability acceptance.

Command references: [Cisco BGP](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/iproute_bgp/command/irg-cr-book/bgp-m1.html),
[Cisco OSPF interface commands](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/iproute_ospf/command/iro-cr-book/m_ospf-i1.html),
[Cisco STP commands](https://www.cisco.com/c/en/us/td/docs/ios/lanswitch/command/reference/lsw_book/lsw_s2.html).
