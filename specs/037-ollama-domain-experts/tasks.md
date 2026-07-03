# Tasks: Ollama Domain Expert Delegation MCP (NetClaw Demo Edition)

**Input**: Design documents from `/specs/037-ollama-domain-experts/`

**Focus**: Specifically tuned for the NetClaw SP core demo's failure modes — GraphQL construction, BGP extra_attributes, FRR config generation from SOT data, and Nautobot job patterns.

## Phase 1: Setup

- [ ] T001 Create `mcp-servers/ollama-experts/` directory structure ✅ DONE
- [ ] T002 Create `requirements.txt` with dependencies ✅ DONE
- [ ] T003 [P] Create core Python modules (models.py, router.py, ollama_client.py, metrics.py, server.py) ✅ DONE

---

## Phase 2: Create Domain Expert Modelfiles on Ollama Host

**Purpose**: Build the specialized models on 192.168.30.50 using curated system prompts

- [ ] T004 Copy Modelfiles to Ollama host and create models:
  - `ollama create netclaw-ospf -f Modelfile.ospf`
  - `ollama create netclaw-bgp -f Modelfile.bgp`
  - `ollama create netclaw-rfc-design -f Modelfile.rfc-design`
  - `ollama create netclaw-frr-codegen -f Modelfile.frr-codegen`
  - `ollama create netclaw-nautobot -f Modelfile.nautobot`
- [ ] T005 Verify all models appear in `ollama list` on 192.168.30.50
- [ ] T006 Run quick smoke test: ask each model a domain question, verify structured response

**Checkpoint**: 5 domain expert models available on the Ollama host

---

## Phase 3: User Story 1 — FRR Config Generation (P1) 🎯 MVP

**Goal**: Frontier delegates "generate vtysh config for device X from this data" to local model

- [ ] T007 [US1] Test: Feed netclaw-frr-codegen the actual GraphQL response for each demo device (PE1, P1-P4, RR1) and validate output
- [ ] T008 [US1] Iterate on Modelfile.frr-codegen system prompt until all 6 devices generate correct config
- [ ] T009 [US1] Validate: No `network <loopback>/32` under BGP in ANY generated config
- [ ] T010 [US1] Validate: RR1 config has `route-reflector-client` INSIDE address-family block
- [ ] T011 [US1] Validate: Spoke configs have NO route-reflector-client anywhere
- [ ] T012 [US1] Validate: All configs use interface-level `ip ospf area` (not network statements)
- [ ] T013 [US1] Validate: Generated configs actually converge when pushed to fresh lab (OSPF FULL, BGP Established)

**Checkpoint**: netclaw-frr-codegen reliably generates pushable configs for all 6 devices

---

## Phase 4: User Story 2 — Nautobot Expert (P2)

**Goal**: Frontier delegates "what GraphQL query do I need?" and "how do I run this job?" to local model

- [ ] T014 [US2] Test: Ask netclaw-nautobot to construct the master GraphQL query for device P1
- [ ] T015 [US2] Test: Ask it "where does route-reflector-client live in the data model?"
- [ ] T016 [US2] Test: Ask it "how do I run the design builder job?" — verify it returns correct JSON-string-in-data pattern
- [ ] T017 [US2] Iterate on Modelfile.nautobot until all 3 tests pass consistently (5/5 runs)

**Checkpoint**: netclaw-nautobot correctly guides API usage patterns

---

## Phase 5: User Story 3 — BGP Expert (P3)

**Goal**: BGP expert prevents extra_attributes misplacement

- [ ] T018 [US3] Update Modelfile.bgp with demo-specific rules about PeerGroupAddressFamily
- [ ] T019 [US3] Test: Ask "where does route-reflector-client go?" — must answer PeerGroupAddressFamily every time
- [ ] T020 [US3] Test: Given RR1's data, generate the BGP stanza — verify address-family placement
- [ ] T021 [US3] Test: Given spoke data, generate BGP stanza — verify NO RR knobs appear

**Checkpoint**: BGP expert never misplaces extra_attributes

---

## Phase 6: User Story 4 — OSPF Expert (P4)

**Goal**: OSPF expert generates correct interface-level config

- [ ] T022 [US4] Verify Modelfile.ospf includes interface-level OSPF rules (not network statements)
- [ ] T023 [US4] Test: Given interface data with areas and network types, generate OSPF block
- [ ] T024 [US4] Validate: passive-interface lo always present, area in dotted notation

**Checkpoint**: OSPF expert generates correct FRR OSPF config

---

## Phase 7: Integration with NetClaw

**Goal**: Wire the MCP server into the OpenClaw config so the Frontier model can delegate

- [ ] T025 Add `ollama-experts` entry to `config/openclaw-demo.json` with all env vars
- [ ] T026 [P] Add OLLAMA_MODEL_* vars to `.env.example`
- [ ] T027 Test full demo flow: Frontier orchestrates, delegates config gen to local expert, pushes to devices, validates
- [ ] T028 Measure: Count Frontier tokens used with delegation vs without

**Checkpoint**: Full demo runs successfully with delegation active

---

## Phase 8: Kiro Integration (P5)

- [ ] T029 [US5] Verify the existing Ollama MCP in Kiro works with 192.168.30.50:11434 ✅ CONFIRMED
- [ ] T030 [US5] Document: How to add ollama-experts MCP to Kiro's mcp.json
- [ ] T031 [US5] Test: From Kiro, invoke ollama_generate_config with sample device data

**Checkpoint**: Kiro can delegate to domain experts

---

## Phase 9: Fine-Tuning Path (Future — P3 from original spec)

**Goal**: Progressive improvement from system-prompt-only to fine-tuned models

- [ ] T032 [US3-FT] Collect training data: Run demo 10 times, capture all correct GraphQL→config pairs
- [ ] T033 [US3-FT] Format as JSONL: instruction/input/output triplets from successful demo runs
- [ ] T034 [US3-FT] QLoRA fine-tune netclaw-frr-codegen on collected data (follow training/README.md)
- [ ] T035 [US3-FT] Benchmark: Compare fine-tuned vs system-prompt-only on 20 test cases
- [ ] T036 [US3-FT] If fine-tuned model wins on >80% of cases, promote to production

**Checkpoint**: Data pipeline for progressive model improvement

---

## Dependencies & Execution Order

- **Phase 1**: ✅ Complete (scaffolding done)
- **Phase 2**: Create models on Ollama host — can start immediately
- **Phase 3**: MVP — requires Phase 2 (models exist)
- **Phase 4-6**: Can run in parallel after Phase 2
- **Phase 7**: Requires Phase 3 passing (FRR expert works)
- **Phase 8**: Requires Phase 2 minimum (models exist for Kiro to call)
- **Phase 9**: Future — collect data from successful Phase 7 runs

### Critical Path

Phase 2 → Phase 3 → Phase 7 → Demo working with delegation

All other phases add value but are not blocking for the core demo flow.
