# Tasks: Enhanced Nautobot MCP Server v2

**Input**: Design documents from `/specs/027-nautobot-mcp-v2/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.md, quickstart.md

**Tests**: Not explicitly requested. Test tasks omitted.

**Organization**: Tasks grouped by user story for independent implementation.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

**Purpose**: Project directory, dependencies, and skeleton

- [x] T001 Create directory `mcp-servers/nautobot-mcp-v2/`
- [x] T002 Create `mcp-servers/nautobot-mcp-v2/requirements.txt` with dependencies: mcp, httpx, python-dotenv
- [x] T003 [P] Create skill directory `workspace/skills/nautobot-sot/`

---

## Phase 2: Foundational (Blocking)

**Purpose**: Nautobot client and server skeleton — BLOCKS all user stories

- [x] T004 Implement NautobotClient class in `mcp-servers/nautobot-mcp-v2/nautobot_client.py` with:
  - Config from env vars (NAUTOBOT_URL, NAUTOBOT_TOKEN, NAUTOBOT_VERIFY_SSL, NAUTOBOT_TIMEOUT)
  - httpx.AsyncClient setup with auth header, SSL config, timeout
  - `graphql(query, variables)` method — POST to /api/graphql/ with JSON body, return data dict
  - `rest_get(endpoint, params)` method — GET to /api/{endpoint}/, return response dict
  - `rest_post(endpoint, data)` method — POST to /api/{endpoint}/, return response dict
  - `rest_patch(endpoint_with_id, data)` method — PATCH to /api/{endpoint}/{id}/, return response dict
  - `resolve_id(object_type, name)` method — GraphQL lookup to resolve human-readable name to UUID for status, role, location, device, namespace
  - Error handling: connection errors, auth failures (401/403), timeouts, GraphQL errors. Never expose token in errors.
- [x] T005 Create FastMCP server skeleton in `mcp-servers/nautobot-mcp-v2/server.py`:
  - Initialize FastMCP("nautobot-mcp-v2"), configure logging to stderr
  - Validate required env vars on startup (NAUTOBOT_URL, NAUTOBOT_TOKEN)
  - Import and instantiate NautobotClient
  - ITSM gating helper: `check_itsm(cr_number)` returns error string if blocked, None if allowed
- [x] T006 [P] Implement `nautobot_test_connection` tool in `server.py` — call GraphQL `{ __typename }` and REST `/api/status/`, return connection status

**Checkpoint**: Client can make authenticated GraphQL and REST requests. Server skeleton runs via stdio.

---

## Phase 3: User Story 1 — Query Devices and Interfaces (P1) 🎯 MVP

**Goal**: Query devices and interfaces from Nautobot via GraphQL.

**Independent Test**: `nautobot_get_devices()` returns HomeSwitch01, HomeSwitch02, pfSense-FW01.

- [x] T007 [US1] Implement `nautobot_get_devices` tool in `server.py`:
  - Build GraphQL query with fields: name, serial, status{name}, role{name}, platform{name}, location{name}, device_type{model, manufacturer{name}}, primary_ip4{address}, primary_ip6{address}, comments
  - Apply filters: name, location, role, platform, status, q, limit, offset
  - Format response with device count and data array
- [x] T008 [US1] Implement `nautobot_get_interfaces` tool in `server.py`:
  - Build GraphQL query with fields: name, type, enabled, status{name}, description, mac_address, mtu, mode, device{name}, untagged_vlan{vid,name}, tagged_vlans{vid,name}, ip_addresses{address}, label, lag{name}
  - Apply filters: device, name, type, enabled, status, has_ip_addresses, limit, offset
  - Format response with interface count and data array

**Checkpoint**: US1 complete. Can query devices and interfaces.

---

## Phase 4: User Story 2 — Query VLANs, Prefixes, IPs, Cables (P2)

**Goal**: Complete read coverage for all core Nautobot objects.

- [x] T009 [P] [US2] Implement `nautobot_get_vlans` tool in `server.py`:
  - GraphQL fields: vid, name, status{name}, locations{name}, vlan_group{name}, tenant{name}, role{name}, description
  - Filters: vid, name, location, vlan_group, status, limit, offset
- [x] T010 [P] [US2] Implement `nautobot_get_prefixes` tool in `server.py`:
  - GraphQL fields: prefix, status{name}, locations{name}, role{name}, tenant{name}, description
  - Filters: prefix, status, location, tenant, limit, offset
- [x] T011 [P] [US2] Implement `nautobot_get_ip_addresses` tool in `server.py`:
  - GraphQL fields: address, status{name}, dns_name, description, tenant{name}, ip_address_assignments{interface{name, device{name}}}
  - Filters: address, status, q, limit, offset
  - Note: device/interface filtering requires post-query filtering on interface_assignments or using the q search
- [x] T012 [P] [US2] Implement `nautobot_get_cables` tool in `server.py`:
  - GraphQL fields: id, type, status{name}, label, color, length, length_unit, termination_a_type, termination_a_id, termination_b_type, termination_b_id
  - Filters: status, limit, offset
  - Resolve termination UUIDs to device+interface names via additional GraphQL query
  - Device filter: post-query filter on resolved endpoint names

**Checkpoint**: US2 complete. Full read coverage for devices, interfaces, VLANs, prefixes, IPs, cables.

---

## Phase 5: User Story 3 — Write Operations with ITSM Gating (P3)

**Goal**: Create and update Nautobot records via REST API with ITSM approval gating.

- [x] T013 [US3] Implement `nautobot_create_ip_address` tool in `server.py`:
  - Check ITSM gating via `check_itsm(cr_number)`
  - Resolve status name to UUID via `resolve_id("status", status)`
  - Resolve namespace name to UUID via `resolve_id("namespace", namespace)`
  - POST to /api/ipam/ip-addresses/ with {address, status, namespace, dns_name, description, tenant}
  - If device+interface provided: resolve device+interface to interface UUID, then POST to /api/ipam/ip-address-to-interface/ to create assignment
  - Return created IP details
- [x] T014 [P] [US3] Implement `nautobot_create_vlan` tool in `server.py`:
  - Check ITSM gating
  - Resolve status, location UUIDs
  - POST to /api/ipam/vlans/ with {vid, name, status, description, tenant}
  - If location provided: POST to /api/ipam/vlan-location-assignments/ to associate
  - Return created VLAN details
- [x] T015 [P] [US3] Implement `nautobot_create_prefix` tool in `server.py`:
  - Check ITSM gating
  - Resolve status, namespace UUIDs
  - POST to /api/ipam/prefixes/ with {prefix, status, namespace, description, tenant}
  - Return created prefix details
- [x] T016 [US3] Implement `nautobot_update_object` tool in `server.py`:
  - Check ITSM gating
  - Resolve object to UUID based on object_type + identifier:
    - device: GraphQL lookup by name
    - interface: GraphQL lookup by device name + interface name
    - ip_address: GraphQL lookup by address
    - vlan: GraphQL lookup by vid
    - prefix: GraphQL lookup by prefix
    - cable: direct UUID
  - GET current state via REST for old values
  - PATCH to appropriate REST endpoint with updates JSON
  - Return old + new values for changed fields

**Checkpoint**: US3 complete. Can create IPs, VLANs, prefixes and update any object with ITSM gating.

---

## Phase 6: User Story 4 — Raw GraphQL (P4)

**Goal**: Expose arbitrary GraphQL query capability.

- [x] T017 [US4] Implement `nautobot_graphql` tool in `server.py`:
  - Accept query string and optional variables JSON string
  - Parse variables from JSON string if provided
  - Call NautobotClient.graphql(query, variables)
  - Return raw GraphQL response data
  - Handle GraphQL errors (return error messages, not stack traces)

**Checkpoint**: US4 complete. Power users can run any GraphQL query.

---

## Phase 7: User Story 5 — Reconciliation (P5)

**Goal**: Compare live device state against Nautobot SoT.

- [x] T018 [US5] Create reconciliation engine in `mcp-servers/nautobot-mcp-v2/reconcile.py`:
  - `reconcile_interfaces(nautobot_interfaces, live_interfaces)` function
  - Match by interface name (case-insensitive)
  - Compare fields: enabled, description, mtu, ip_addresses
  - Categorize: matches, mismatches (with per-field diffs), device_only, nautobot_only
  - Return ReconciliationReport dict
- [x] T019 [US5] Implement `nautobot_reconcile` tool in `server.py`:
  - Accept device_name and live_interfaces (JSON string)
  - Parse live_interfaces JSON
  - Query Nautobot interfaces for device via GraphQL
  - Call reconcile_interfaces() from reconcile.py
  - Return structured diff report with summary

**Checkpoint**: US5 complete. Can reconcile live device state against Nautobot.

---

## Phase 7b: Virtualization (Post-MVP Extension)

**Goal**: Manage virtual machines in Nautobot for tracking containers, VMs, and cloud instances.

- [x] T030 [P] Add `cluster` and `virtual_machine` to resolve_id query map in `nautobot_client.py`
- [x] T031 Implement `nautobot_get_virtual_machines` tool in `server.py`:
  - GraphQL fields: id, name, status{name}, role{name}, cluster{name}, vcpus, memory, disk, comments, primary_ip4{address}, interfaces{name, enabled, mac_address, ip_addresses{address}}
  - Filters: name, cluster, role, status, limit, offset
- [x] T032 Implement `nautobot_create_virtual_machine` tool in `server.py`:
  - Check ITSM gating
  - Resolve status, cluster, role UUIDs
  - POST to /api/virtualization/virtual-machines/
  - Return created VM details
- [x] T033 [P] Implement `nautobot_create_vm_interface` tool in `server.py`:
  - Check ITSM gating
  - Resolve virtual_machine UUID
  - POST to /api/virtualization/interfaces/
  - Return created interface details
- [x] T034 Implement `nautobot_assign_ip_to_vm` tool in `server.py`:
  - Check ITSM gating
  - Create IP address via REST
  - Resolve VM interface via GraphQL (vm_interfaces query)
  - POST to /api/ipam/ip-address-to-interface/ with vm_interface
  - Optionally PATCH VM to set primary_ip4
  - Return assignment confirmation

**Checkpoint**: Can create VMs, interfaces, and assign IPs. Used by deploy-observability skill to register containers in Nautobot.

---

## Phase 8: Polish & Artifact Coherence

**Purpose**: Documentation, configuration, and artifact coherence.

- [x] T020 [P] Create `mcp-servers/nautobot-mcp-v2/README.md` with tool inventory (13 tools), env vars, transport, install instructions, examples
- [x] T021 [P] Create `workspace/skills/nautobot-sot/SKILL.md` with purpose, tools used, workflow steps, env vars
- [x] T022 [P] Update `.env.example` with NAUTOBOT_URL, NAUTOBOT_TOKEN, NAUTOBOT_VERIFY_SSL, NAUTOBOT_TIMEOUT, ITSM_ENABLED, ITSM_LAB_MODE
- [x] T023 [P] Update `workspace-override/TOOLS.md` with nautobot-mcp-v2 entry (32 tools)
- [x] T024 [P] Update `workspace-override/SOUL.md` with nautobot-sot skill and v2 capabilities
- [x] T025 [P] Update `README.md` with v2 description, updated tool/skill counts
- [x] T026 Update `config/openclaw.json` to point nautobot-mcp at v2 server.py with new env vars
- [x] T027 [P] Update `scripts/install.sh` with v2 dependency installation
- [x] T028 [P] Update `ui/netclaw-visual/` HUD with updated Nautobot node (v2 capabilities)
- [x] T029 [P] Update `Dockerfile` to install v2 requirements and copy v2 server files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational. MVP target.
- **US2 (Phase 4)**: Depends on Foundational. Can run in parallel with US1.
- **US3 (Phase 5)**: Depends on Foundational (needs resolve_id). Can start after Phase 2.
- **US4 (Phase 6)**: Depends on Foundational only. Can run in parallel with US1-US3.
- **US5 (Phase 7)**: Depends on US1 (needs interface query). Should follow Phase 3.
- **Polish (Phase 8)**: Depends on all user stories.

### Parallel Opportunities

- T001, T002, T003 (Setup) — all parallel
- T004 and T006 partially parallel (T006 needs client from T004)
- T009, T010, T011, T012 (US2 tools) — all parallel
- T013, T014, T015 (US3 create tools) — T014 and T015 parallel, T013 first (establishes pattern)
- T017 (US4) — independent of US1-US3
- All Phase 8 tasks marked [P] — parallel

## Implementation Strategy

### MVP First (US1 Only)

1. Phase 1: Setup (T001-T003)
2. Phase 2: Foundational (T004-T006)
3. Phase 3: US1 — devices + interfaces (T007-T008)
4. **STOP and VALIDATE**: Test against live Nautobot at 192.168.3.253
5. Deploy if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (devices + interfaces) → MVP!
3. US2 (VLANs + prefixes + IPs + cables) → Full read coverage
4. US3 (writes with ITSM) → SoT management
5. US4 (raw GraphQL) → Power user escape hatch
6. US5 (reconciliation) → Capstone workflow
7. Phase 8 (Polish) → Feature complete

---

## Notes

- [P] tasks = different files, no dependencies
- v2 server lives in new directory; v1 preserved for reference
- openclaw.json entry name stays "nautobot-mcp" — just points to new server
- ITSM defaults: ITSM_ENABLED=false, ITSM_LAB_MODE=true (safe for home lab)
- All GraphQL queries verified working against live Nautobot 3.1.0 at 192.168.3.253
