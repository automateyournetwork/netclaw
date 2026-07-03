# Feature Specification: Ollama Domain Expert Delegation MCP (NetClaw Demo Edition)

**Feature Branch**: `037-ollama-domain-experts`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "Point NetClaw's Frontier model to an Ollama MCP that delegates domain-specific tasks to local LLMs — OSPF expert, BGP expert, RFC design validator, Nautobot expert — specifically tuned to handle the failure modes observed during previous NetClaw demo runs."

## Problem Statement: Why Single LLMs Fail the Demo

The NetClaw SP core demo (6-node FRR lab, Nautobot SOT, config push, validate) has been run dozens of times with various LLMs. Consistent failure modes emerge:

1. **GraphQL query construction** — Models guess at Nautobot's BGP model hierarchy, write invalid queries, or query wrong fields (e.g., putting `bgp_peerings` filter syntax wrong)
2. **BGP extra_attributes misplacement** — Models put `route-reflector-client` on PeerEndpoint or PeerGroup objects instead of PeerGroupAddressFamily. This is the #1 config bug.
3. **JSON-in-JSON parameter encoding** — `nautobot_run_job(data='{"deployment_name": "Netclaw Demo"}')` confuses models that try to pass dicts or double-encode
4. **Config generation from data** — Translating GraphQL response → valid FRR vtysh commands requires understanding both the Nautobot object model AND FRR syntax simultaneously
5. **Multi-device context overflow** — Generating configs for 6 devices in sequence causes context to balloon, the model forgets earlier query results, starts looping
6. **Network statement hallucination** — Models add `network <loopback>/32` under BGP (wrong — OSPF handles loopback reachability in this design)
7. **Tool selection confusion** — With 40+ MCP tools available, models call wrong tools (golden_config instead of nautobot_run_job, REST endpoints instead of GraphQL)

**The solution**: Offload the domain-specific "hard thinking" to local experts that are purpose-built for exactly these tasks, while the Frontier model handles orchestration, validation, and user interaction.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - FRR Config Generation from Nautobot Data (Priority: P1)

As the Frontier model orchestrating the demo, I need to delegate "given this GraphQL response for device P1, generate the complete FRR vtysh config" to a local expert that deeply understands FRR syntax, the Nautobot BGP/OSPF object model, and the rules for deriving config from data.

**Why this priority**: Phase 3 (config generation + push) is where demos fail most often. The local expert eliminates the most expensive and error-prone step — it receives structured device data and returns ready-to-push vtysh commands.

**Independent Test**: Feed the expert a sample GraphQL response for RR1 (the hardest case — peer groups, route-reflector-client extra_attribute, 5 peers) and verify it produces the exact vtysh config needed.

**Acceptance Scenarios**:

1. **Given** a GraphQL response containing device P1's interfaces (lo, eth1, eth2, eth3), IP addresses, OSPF interface configurations (area 0, point-to-point), and BGP data (routing instance, no peer group, direct neighbor statements to RR1), **When** the Frontier delegates to `ollama_generate_config(domain="frr", ...)`, **Then** the local expert returns a complete, valid `docker exec clab-netclaw-demo-p1 vtysh -c "configure terminal" ...` command string that can be executed directly.

2. **Given** a GraphQL response for RR1 containing the IBGP peer group with PeerGroupAddressFamily.extra_attributes={"route-reflector-client": true, "next-hop-self": true}, **When** delegated, **Then** the expert generates `neighbor IBGP route-reflector-client` and `neighbor IBGP next-hop-self` UNDER `address-family ipv4 unicast` — never at the router-bgp level.

3. **Given** any device's GraphQL data, **When** delegated, **Then** the expert NEVER adds `network <loopback>/32` under BGP. Only OSPF handles loopback reachability.

4. **Given** the expert receives malformed or incomplete GraphQL data, **When** it cannot generate a valid config, **Then** it returns a structured error explaining what's missing rather than hallucinating values.

---

### User Story 2 - Nautobot SOT Intent Expert (Priority: P2)

As the Frontier model, I need a Nautobot expert that serves three roles: (1) constructing correct GraphQL queries, (2) interpreting Nautobot's structured BGP + OSPF data models into config intent, and (3) validating that generated configs accurately represent what BOTH the BGP Models and IGP Models plugins declare as the intended state.

**Why this priority**: Wrong queries are the second most common failure, but the deeper problem is that even when queries succeed, models misinterpret the data. The Nautobot expert bridges the gap between "what the SOT says" and "what the config should be" — combining BGP and OSPF intent into a unified validation.

**Independent Test**: Give the expert the full GraphQL response for RR1 and a candidate FRR config. It should validate that the config correctly represents BOTH the OSPF intent (areas, network types, passive-interface) AND the BGP intent (peer group, address family, extra_attributes placement) — or flag specific discrepancies.

**Acceptance Scenarios**:

1. **Given** the Frontier needs device data for config generation, **When** it asks the Nautobot expert to construct the query, **Then** the expert returns a valid GraphQL query that includes: `devices(name:)`, `bgp_routing_instances(device:)` with peer_groups → address_families → extra_attributes, `bgp_peerings` with both endpoints, and `ospf_interface_configurations`.

2. **Given** a GraphQL response and a generated config for P1, **When** the Frontier invokes `ollama_validate_config_against_sot`, **Then** the Nautobot expert checks 15 validation points covering OSPF (area, network_type, passive-interface, router-id) AND BGP (ASN, peers, extra_attributes) and returns pass/fail with specific issues.

3. **Given** a config that incorrectly adds `network 10.255.255.2/32` under BGP, **When** validated against the SOT, **Then** the expert flags it as an error: "network statement under BGP not expressed in Nautobot models — OSPF handles loopback reachability."

4. **Given** a config for RR1 that puts `route-reflector-client` at the router-bgp level instead of under address-family, **When** validated, **Then** the expert flags: "extra_attributes from PeerGroupAddressFamily must appear UNDER address-family ipv4 unicast, not at global BGP level."

5. **Given** a config that is missing an interface's OSPF configuration that exists in `ospf_interface_configurations`, **When** validated, **Then** the expert flags: "Interface eth2 has OSPF area 0.0.0.0 in SOT but 'ip ospf area' is missing from config."

---

### User Story 3 - BGP Design Expert (Priority: P3)

As the Frontier model, I need a BGP expert that understands iBGP route reflection, peer-group semantics, and the exact relationship between Nautobot's BGP model objects and FRR config stanzas — specifically to prevent the "extra_attributes on wrong object" class of errors.

**Why this priority**: BGP config is where the most nuanced errors occur. The expert must understand both the data model AND the protocol semantics to generate correct configs.

**Independent Test**: Present the BGP expert with a description of this topology (AS 65000, RR1 with 5 iBGP clients, IBGP peer-group) and ask it to explain which Nautobot object gets `route-reflector-client`. It must answer correctly every time.

**Acceptance Scenarios**:

1. **Given** a question about where route-reflector-client is configured, **When** asked, **Then** the expert correctly states: "On the route reflector (RR1), in the PeerGroupAddressFamily for the IBGP peer-group under address-family ipv4 unicast. Never on spoke-side objects."

2. **Given** BGP data from GraphQL showing RR1's peer group "IBGP" with address_families[0].extra_attributes={"route-reflector-client":true}, **When** asked to generate the FRR stanza, **Then** it produces:
   ```
   address-family ipv4 unicast
    neighbor IBGP activate
    neighbor IBGP route-reflector-client
    neighbor IBGP next-hop-self
   exit-address-family
   ```

3. **Given** spoke device data (P1, P2, P3, P4, PE1) showing NO peer_group and NO extra_attributes on their endpoint address families, **When** asked to generate BGP config, **Then** the expert generates direct neighbor statements with `activate` under address-family, but NO route-reflector-client, NO next-hop-self (only the RR does that).

---

### User Story 4 - OSPF Expert (Priority: P4)

As the Frontier model, I need an OSPF expert that generates correct FRR OSPF config blocks from Nautobot OSPF interface configuration data — interface-level `ip ospf area`, network type, passive-interface rules.

**Why this priority**: OSPF config is simpler than BGP but still a common source of errors (wrong area format, missing passive-interface on loopback, wrong network type).

**Independent Test**: Give the expert a list of interfaces with their areas and network types, get back valid FRR OSPF stanzas.

**Acceptance Scenarios**:

1. **Given** OSPF interface data showing eth1 in area 0.0.0.0 with network_type point-to-point, **When** delegated, **Then** the expert generates `ip ospf area 0.0.0.0` and `ip ospf network point-to-point` under that interface.

2. **Given** the loopback interface, **When** generating OSPF config, **Then** the expert ALWAYS adds `passive-interface lo` under `router ospf` and `ip ospf area 0.0.0.0` under `interface lo`.

3. **Given** the router-id from Nautobot (e.g., "10.255.255.1/32"), **When** generating the router ospf section, **Then** the expert strips the /32 mask and produces `ospf router-id 10.255.255.1`.

---

### User Story 5 - Kiro IDE + Local Ollama Integration (Priority: P5)

As a developer using Kiro IDE, I want the same ollama-experts MCP pointed at my local AI host (192.168.30.50:11434) so that I can iterate on the demo workflow — testing config generation, validating GraphQL queries — without burning Frontier tokens.

**Why this priority**: Development workflow benefit. Iterate faster on the demo skill by testing expert responses locally.

**Independent Test**: Configure the MCP in Kiro, ask it to generate a config from sample data, verify response.

**Acceptance Scenarios**:

1. **Given** the ollama-experts MCP configured in `.kiro/settings/mcp.json` pointing to 192.168.30.50:11434, **When** I ask it to generate an FRR config from device data, **Then** it delegates to the local model and returns structured config.

2. **Given** I'm editing the demo SKILL.md and want to validate a GraphQL query, **When** I ask the Nautobot expert "is this query correct?", **Then** it validates the field names and relationships against its training data.

---

### User Story 6 - Token Savings Tracking (Priority: P6)

As a cost-conscious operator, I want to see how many Frontier tokens were saved by local delegation during a demo run.

**Acceptance Scenarios**:

1. **Given** a full demo run delegated 6 config generation tasks, **When** I ask for stats, **Then** I see ~6000-8000 tokens saved (the equivalent output the Frontier would have generated).

---

### Edge Cases

- What if the local model generates config with wrong interface names (e.g., "Loopback0" instead of "lo")?
- What if Ollama is mid-generation when the demo needs to move fast (audience waiting)?
- How does the Frontier know whether to trust the local model's output or regenerate?
- What if the GraphQL schema changes after a Nautobot plugin update?
- How does the system handle the vtysh command length limit (very long configs may need splitting)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an MCP server that routes delegation requests to domain-specific Ollama models.
- **FR-002**: System MUST support these domain experts: `frr` (config generation), `nautobot` (GraphQL + API patterns), `bgp` (BGP design + extra_attributes), `ospf` (OSPF config).
- **FR-003**: The `frr` domain expert MUST accept a structured device data payload (GraphQL response or equivalent) and return complete, executable vtysh commands.
- **FR-004**: The `nautobot` domain expert MUST know the Nautobot BGP Models plugin hierarchy AND the IGP Models plugin hierarchy and validate configs against both.
- **FR-005**: The `nautobot` expert MUST be able to validate a generated FRR config against the SOT data, checking that both BGP intent (peerings, peer groups, extra_attributes) and OSPF intent (areas, network types, passive-interface) are correctly represented.
- **FR-005a**: The system MUST expose an `ollama_validate_config_against_sot` tool that accepts a config string + SOT data and returns structured pass/fail with specific issues.
- **FR-006**: The `frr` expert MUST NEVER add `network <loopback>/32` under BGP for SP core devices.
- **FR-007**: The `frr` expert MUST render extra_attributes as FRR commands ONLY under `address-family ipv4 unicast`, never at router-bgp global level.
- **FR-008**: System MUST support `OLLAMA_BASE_URL` env var for remote Ollama instances (default: http://192.168.30.50:11434).
- **FR-009**: System MUST timeout after configurable duration (default 60s for 32B models on user's hardware).
- **FR-010**: System MUST return structured JSON responses with `success`, `config` (or `query`), `warnings`, and `generation_time_ms` fields.
- **FR-011**: System MUST be usable from both OpenClaw (NetClaw) and Kiro IDE without modification.
- **FR-012**: Modelfiles MUST embed demo-specific rules (no network statements, extra_attributes placement, FRR syntax specifics) directly into the system prompt.
- **FR-013**: The `nautobot` expert MUST know that `nautobot_run_job` data parameter is a JSON **string** not a dict.
- **FR-014**: System MUST handle Ollama connection failures gracefully — return error so Frontier falls back to doing it itself.
- **FR-015**: The `frr` expert MUST generate configs with correct push order awareness — interfaces before routing protocols.

### Key Entities

- **Domain Expert**: A named Ollama model with a curated system prompt containing demo-specific rules and failure prevention.
- **Device Data Payload**: The structured output from a `nautobot_graphql` call containing interfaces, IPs, OSPF configs, BGP routing instances, peerings, and extra_attributes.
- **vtysh Command String**: The complete `docker exec clab-netclaw-demo-<node> vtysh -c "configure terminal" -c "..." -c "..."` ready for shell execution.
- **GraphQL Query Template**: A pre-validated query structure that the Nautobot expert knows returns all needed data for config generation.
- **Extra Attributes Map**: The JSON object on PeerGroupAddressFamily that maps to FRR address-family commands (route-reflector-client → neighbor X route-reflector-client).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The `frr` expert generates valid, pushable FRR config for all 6 demo devices (PE1, P1-P4, RR1) from their GraphQL data — 100% success rate after Modelfile tuning.
- **SC-002**: The `frr` expert NEVER produces `network <loopback>/32` under BGP — validated by automated string check.
- **SC-003**: The `frr` expert ALWAYS puts route-reflector-client under address-family on RR1, never at global BGP level — validated by config parse.
- **SC-004**: The `nautobot` expert generates syntactically valid GraphQL queries that return data when executed against the running Nautobot instance.
- **SC-005**: Full demo Phase 3 (config generation for 6 devices) completes in under 3 minutes using delegation to local 32B model on user's hardware.
- **SC-006**: Frontier token savings of at least 60% on Phase 3 compared to Frontier generating all configs itself.
- **SC-007**: The same MCP server works in both OpenClaw and Kiro without any code changes.
- **SC-008**: Config generated by local expert, when pushed to fresh ContainerLab containers, results in OSPF FULL adjacencies and BGP Established sessions on first attempt at least 80% of the time.

## Assumptions

- User has Ollama running on 192.168.30.50:11434 with `qwen2.5-coder:32b-instruct-q8_0` available (confirmed from earlier inventory).
- The Nautobot design job creates consistent data structures — the same GraphQL response shape every time.
- FRR vtysh syntax is stable across the `frrouting/frr:latest` container image versions used in the lab.
- The 32B model has sufficient capability to follow structured system prompts with explicit rules (confirmed by live test earlier in this session).
- ContainerLab topology remains at 6 nodes (PE1, P1-P4, RR1) for the demo — expert models are tuned for this specific topology.
- The Frontier model (Claude/Qwen/DeepSeek) can effectively validate outputs by comparing against expected patterns (e.g., "does this config have network statements under BGP? reject.").
