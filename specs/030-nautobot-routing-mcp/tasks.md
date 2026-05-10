# Tasks: nautobot-routing-mcp

**Input**: `specs/030-nautobot-routing-mcp/spec.md`
**Output**: `mcp-servers/nautobot-routing-mcp/`
**Prerequisites**: Nautobot running with BGP Models + IGP Models plugins, lab devices with BGP/OSPF

---

## Phase 1: Server Scaffold

- [ ] T001 Create `mcp-servers/nautobot-routing-mcp/` directory structure
- [ ] T002 Create `server.py` with FastMCP scaffold, env var loading, logging
- [ ] T003 Create `nautobot_client.py` — shared async HTTP client (reuse pattern from golden-config-mcp)
- [ ] T004 Create `bgp_helpers.py` — BGP object chain resolution (find_or_create_asn, find_routing_instance, find_peering_by_ips)
- [ ] T005 Create `requirements.txt` (httpx, fastmcp, mcp)
- [ ] T006 Register in `config/openclaw.json` with `.venv/bin/python3` path
- [ ] T007 Add to `.gitignore` exceptions

**Checkpoint**: Server starts, connects to Nautobot, no tools yet.

---

## Phase 2: BGP Read Tools

- [ ] T008 Implement `routing_get_bgp_summary(device=)` — full BGP topology via single GraphQL query
- [ ] T009 Implement `routing_get_bgp_peers(device=)` — peer table with remote AS, source IP, group, enabled
- [ ] T010 Implement `routing_get_bgp_peer_detail(device, peer_ip)` — both endpoints, AFIs, full peering object
- [ ] T011 Implement `routing_get_peer_groups(device=)` — groups with member count, AFIs
- [ ] T012 Implement `routing_get_autonomous_systems()` — all ASNs in the model

**Checkpoint**: LLM can get complete BGP topology in 1 call. SC-002 met.

---

## Phase 3: BGP Write Tools

- [ ] T013 Implement `routing_create_autonomous_system(asn, description=)` — idempotent ASN creation
- [ ] T014 Implement `routing_create_routing_instance(device, asn, router_id=)` — idempotent instance creation
- [ ] T015 Implement `routing_create_peering(device, local_ip, peer_ip, peer_asn, peer_group=, afi=, description=)` — full chain in one call
- [ ] T016 Implement `routing_delete_peering(device, peer_ip)` — find and delete peering + endpoints
- [ ] T017 Implement `routing_create_peer_group(device, name, remote_asn=, source_interface=, afi=)` — group + AFIs
- [ ] T018 Implement `routing_delete_peer_group(device, name)` — delete group (fail if members)
- [ ] T019 Implement `routing_add_peer_to_group(device, peer_ip, group)` — update endpoint's peer_group
- [ ] T020 Implement `routing_remove_peer_from_group(device, peer_ip)` — clear endpoint's peer_group

**Checkpoint**: LLM can create full peering in 1 call. SC-001, SC-004, SC-006 met.

---

## Phase 4: OSPF Tools

- [ ] T021 Implement `routing_get_ospf_summary(device=)` — OSPF instances, areas, interfaces, costs
- [ ] T022 Implement `routing_get_ospf_interfaces(device=, area=)` — interface table with area/cost
- [ ] T023 Implement `routing_create_ospf_instance(device, process_id, router_id=)` — idempotent
- [ ] T024 Implement `routing_add_ospf_interface(device, interface, area, cost=, network_type=)` — add to OSPF
- [ ] T025 Implement `routing_remove_ospf_interface(device, interface)` — remove from OSPF

**Checkpoint**: LLM can manage OSPF interfaces in 1 call. SC-005 met.

---

## Phase 5: Reconciliation Tools

- [ ] T026 Implement `routing_reconcile_bgp(device, live_peers)` — compare model vs pyATS output
- [ ] T027 Implement `routing_reconcile_ospf(device, live_neighbors)` — compare model vs pyATS output

**Checkpoint**: LLM can detect routing drift in 1 call. SC-003 met.

---

## Phase 6: Integration & Deprecation

- [ ] T028 Add deprecation warnings to BGP/OSPF tools in nautobot-mcp-v2
- [ ] T029 Update `workspace/user/TOOLS.md` with routing MCP server documentation
- [ ] T030 Test: create peering for NetClaw Protocol MCP (RR1 ↔ 10.255.255.1, AS 65099)
- [ ] T031 Test: reconcile BGP for RR1 against live `show bgp summary` output
- [ ] T032 Test: add OSPF interface, verify in model, remove it

**Checkpoint**: End-to-end workflows verified. SC-007 met.

---

## Execution Order

```
Phase 1 (scaffold) → Phase 2 (BGP reads) → Phase 3 (BGP writes) → Phase 4 (OSPF) → Phase 5 (reconciliation) → Phase 6 (integration)
```

Phase 2+3 are highest value — once the LLM can read and write BGP peerings in single calls, the Protocol MCP ↔ Nautobot SoT workflow is unblocked.

---

## Test Data (Lab)

The Nautobot Workshop lab has:
- **58 peerings** across 10 IOS devices (iBGP via RR1, eBGP PE↔CE)
- **116 peer endpoints** (2 per peering)
- **~5 ASNs** (65000 for SP, 65001/65002 for CEs, 65099 for NetClaw)
- **OSPF** on all SP core devices (P1-P4, PE1-PE3, RR1) in area 0
- **EVPN/VXLAN** BGP on DC fabric (separate from SP BGP)

Good test cases:
- `routing_get_bgp_summary(device="RR1")` — should show all iBGP clients + NetClaw eBGP peer
- `routing_create_peering(device="RR1", local_ip="10.255.255.2/30", peer_ip="10.255.255.1/30", peer_asn=65099)` — NetClaw peering
- `routing_reconcile_bgp(device="PE1", live_peers=...)` — compare model vs live
- `routing_get_ospf_interfaces(device="P1")` — should show all P1 OSPF interfaces in area 0
