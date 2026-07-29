# Domain signature library

Problem Analysis compressed into lookups. For a fault in a given domain, match the observed **signature**
to what it **eliminates or points to**, and use the **specification prompts** to fill the IS/IS-NOT grid
faster. Signatures are just IS/IS-NOT boundaries that recur so often they can be pre-listed. Confirm with
tools; don't conclude from the table alone.

## Routing / BGP

Prompts — WHERE: which prefixes vs. which fine? which peer/VRF/AS-path? one direction or both? WHEN:
correlate to flap timers, route-refresh, peer maintenance, policy commits, dampening. WHAT: route
missing, present-not-best, present-not-installed, or installed-but-blackholed (four different problems).
EXTENT: one prefix/peer or whole table? spreading?

| Signature | Eliminates / points to |
|---|---|
| Route present but not selected best | Best-path attribute issue (local-pref, MED, AS-path len, weight, origin) — not a peering problem |
| Session flaps on a regular interval | Keepalive/hold-timer mismatch, MTU/PMTUD on peering link, or underlay flap — not policy |
| Best route chosen but traffic blackholes | RIB/FIB inconsistency or recursive next-hop resolution failure — not control-plane selection |
| Only one direction affected | Return-path policy or asymmetric next-hop; specify both directions separately |

## Wireless / RF

Prompts — WHERE: which APs, band (2.4/5/6 GHz), area, SSID? (a floor plan is part of the spec). WHEN:
time-of-day/week (client density, interference, DFS radar) matters enormously. WHAT: association vs
authentication vs roaming failure vs good-signal-poor-throughput — separate the RF problem from the AAA
problem (they present identically to the user). EXTENT: all clients or certain device types/drivers?

| Signature | Eliminates / points to |
|---|---|
| Fails on 5/6 GHz, fine on 2.4 | DFS channel changes, min-RSSI/band-steering, coverage holes — not authentication |
| Association fine, drops at auth | AAA/RADIUS/certificate — not RF. Specify the RADIUS server/realm, not the AP |
| Only one client model affected | Client driver/powersave/band support — not the WLAN; exclude from infra PA |
| Degrades at predictable busy hours | Contention/co-channel/capacity — a design issue, not a "reboot" fault |

## Firewall / Security policy

Prompts — WHERE: which policy/rule, zone pair, NAT, UTM profile? which direction? WHEN: policy commits,
signature/feed auto-updates, cert rotations, HA failovers. WHAT: dropped at policy, by UTM/inspection, NAT
failure, session-state failure, or decryption failure (a flow debug names the drop reason — use it).

| Signature | Eliminates / points to |
|---|---|
| Forward works, return dropped | Stateful session not established, or asymmetric routing across an HA pair — not a simple deny |
| Breaks after a feed/signature update | Threat/geo/IPS feed false-positive or new category block — not the base policy |
| Only HTTPS to certain sites breaks | Deep-inspection/decryption or SNI filtering — not L3/L4 reachability |
| Long sessions drop at a fixed interval | Idle/session timeout or HA session-sync gap — not congestion |

## SD-WAN / overlay

Prompts — WHERE: which site, underlay transport, overlay tunnel, app/SLA class? (separate overlay from
underlay). WHEN: path-quality SLA thresholds triggering failover, controller/orchestrator pushes,
transport events. WHAT: tunnel down vs up-but-steering-wrong (SLA steering can look like a fault while
working as designed). EXTENT: one app class/site or fleet-wide (implicates controller/policy)?

| Signature | Eliminates / points to |
|---|---|
| Traffic on "wrong" path but app works | Working-as-designed SLA steering or app-path policy — check policy intent before calling it a fault |
| Repeated failover flaps between transports | A transport near an SLA threshold or over-tight thresholds causing hysteresis — tune, don't replace |
| Fleet-wide simultaneous change | Controller/orchestrator push or template change — one root, many sites; specify last template version |
| Overlay down but underlay up | IPsec/overlay parameter or controller reachability — not the transport circuit |

## DNS / DHCP / core services

Prompts — WHAT: **resolution vs connectivity** (the most misattributed distinction); within DNS —
NXDOMAIN vs SERVFAIL vs timeout vs wrong-answer (different cause families). WHERE: which resolver, zone
(internal vs forwarded), client scope; for DHCP — scope, relay, server in a pair. WHEN: lease renewals,
zone-transfer schedules, cache TTL expiry, patch windows.

| Signature | Eliminates / points to |
|---|---|
| External names resolve, internal don't | Authoritative/zone-transfer or conditional-forwarder issue on a specific resolver — not the network |
| Fails on one resolver, retry succeeds | Per-server problem (stale zone, overloaded recursion) masked as "slowness" — specify per resolver |
| Clients get no/duplicate IP intermittently | DHCP scope exhaustion, rogue server, or relay/helper misconfig — not DNS, not connectivity |
| "Site down" but ping-by-IP works | It's resolution, not reachability — re-specify the defect before touching the path |

## Cloud / hybrid connectivity

Prompts — WHERE: connection type (IPsec-over-internet vs private circuit), VPC/VNet, region,
peering/transit, direction. WHAT: underlay circuit vs BGP session vs route propagation into the cloud
route table vs cloud-side security group/NACL (four layers, all present as "can't reach the workload").
WHEN: cloud-console change events, MTU-related onset (overlay+IPsec shrinks MTU), BGP reconvergence.

| Signature | Eliminates / points to |
|---|---|
| Circuit/tunnel up, BGP up, one prefix unreachable | Route-table propagation or a security-group/NACL rule — not transport or tunnel |
| Small packets pass, larger flows to cloud stall | MTU/MSS (overlay+IPsec overhead); needs MSS clamping — not routing/security |
| Breaks right after a cloud-console change | Cloud-side route-table or security-group edit — specify the change event first |
| Reachable from one region/VPC not a peered one | Transit/peering route-propagation or a missing route — not on-prem |

## Performance / throughput

Prompts — WHAT: loss vs latency vs jitter vs throughput ceiling (four different problems; "slow" is not a
spec). WHERE: which segment, direction, flow size? WHEN+EXTENT: utilization-correlated (congestion) vs
constant (config/MTU) vs distance-correlated (BDP/window)?

| Signature | Eliminates / points to |
|---|---|
| Small transfers fine, large ones stall | MTU/PMTUD blackhole or TCP window/BDP limit — not a link fault (no interface errors) |
| Throughput tracks utilization crossing CIR | Congestion/policing — shaping/QoS issue, not hardware |
| Poor throughput only over long distances | Bandwidth-delay-product / TCP window scaling — a tuning issue, not loss |
| Interface errors present (CRC/input) | Physical layer — optic, fiber, duplex. The one signature that DOES point at hardware |
