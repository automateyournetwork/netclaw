# Tasks: Read/Write Access Class on Per-Peer Grants

**Input**: specs/190-grant-access-class/ (spec.md, plan.md, research.md, data-model.md, contracts/access-class.md)
**Tests**: Requested (spec FR-015, SC-001..SC-004): all in `tests/n2n/test_grant_access_class_190.py`.
Run: `cd /Users/john.capobianco/netclaw && /private/tmp/claude-503/ra-venv/bin/python -m pytest -q tests/n2n/<file>`

## Phase 1: Setup

- [ ] T001 Baseline: run `tests/n2n/test_authorization.py tests/n2n/test_peer_limits_189.py` and record the result in specs/190-grant-access-class/verification.md

## Phase 2: Foundational (blocks all stories)

- [ ] T002 Add `("invocation_grant","access_class","TEXT NOT NULL DEFAULT 'read_write'")` to the ALTER list and `SCHEMA_190` (`tool_classification` table) executed next to SCHEMA_189 in mcp-servers/protocol-mcp/bgp/federation/manager.py
- [ ] T003 Add constants `ACCESS_CLASSES`, `TARGET_CLASSES`, node default env `N2N_GRANT_DEFAULT_ACCESS`, and `Authorizer.effective_class(target_type, target_name)` (operator row, else annotation row, else unclassified; knowledge types always read) in mcp-servers/protocol-mcp/bgp/federation/authorization.py

## Phase 3: US1 + US2 - read-only grants, backward compatible (P1)

**Independent test**: read grant allows read target, refuses write and unclassified; legacy/omitted class behaves as today.

- [ ] T004 [US1] Extend `Authorizer.grant(..., access_class=None)`: resolve default, validate (ValueError on bad value), supersede an active grant with a different class for the same (peer,type,name), return id; `list_grants` already returns the column in mcp-servers/protocol-mcp/bgp/federation/authorization.py
- [ ] T005 [US1] Add the class check in `authorize()` between grant lookup and rate check: refuse with `Decision(False,"not_allowlisted",grant,"<type> '<name>' not allowlisted for <peer>")` and write audit row `access_class_denied` via `self.audit` in mcp-servers/protocol-mcp/bgp/federation/authorization.py
- [ ] T006 [US2] Tests: legacy row (insert without column value / pre-existing rows) behaves read_write; omitted class stored read_write; node default env `read` applies only to new grants; invalid class ValueError, nothing stored; supersede behavior in tests/n2n/test_grant_access_class_190.py
- [ ] T007 [US1] Tests: decision matrix grant class x target class (read/write/unclassified) x type (tool, skill, knowledge, knowledge_replica); refusal debits nothing, no rate slot, no approval, no limit action under teardown; admission after reclassification refuses in tests/n2n/test_grant_access_class_190.py

## Phase 4: US3 - Classification management (P1)

- [ ] T008 [US3] Add `Authorizer.classify(type,name,access)`, `clear_classification`, `import_annotations(server, tools)`, `list_classifications()` with validation and audit rows (`classified`, `classification_cleared`, `classification_imported`) in mcp-servers/protocol-mcp/bgp/federation/authorization.py
- [ ] T009 [US3] Tests: annotation true/false/absent mapping, override precedence, clear returns to annotation, invalid input rejected without change, audit rows in tests/n2n/test_grant_access_class_190.py

## Phase 5: US4 - Skill delegation (P1)

- [ ] T010 [US4] Tests through `Invoker.handle_task_submit` and `handle_tools_call` with a fake channel: read grant on unclassified skill refused (-32001) regardless of text; classified read allowed past the gate; same text outcomes identical; no task row created on refusal in tests/n2n/test_grant_access_class_190.py

## Phase 6: US5 + US6 - Interactions, card, knowledge (P2)

- [ ] T011 [US5] Add advisory `tool_access` per MCP server and `access` per skill to the card in mcp-servers/protocol-mcp/bgp/federation/inventory.py (default-tolerant, secret scan unchanged, visibility unchanged)
- [ ] T012 [US5] Tests: read grant + requires_approval on write tool refused before approval; on read tool approval required and approval does not widen; card hints present, visibility unaffected, hints never used for authorization; iN2N `already_trusted` subject to same check in tests/n2n/test_grant_access_class_190.py
- [ ] T013 [US6] Tests: read grant for `knowledge` allowed; `knowledge` grant does not allow `knowledge_replica`; inventory get unaffected in tests/n2n/test_grant_access_class_190.py

## Phase 7: Operator surface

- [ ] T014 Daemon: `/n2n/grants` accepts/returns `access_class` (400 on invalid), `/n2n/classifications` GET/POST, one-step trust `access_class` in mcp-servers/protocol-mcp/bgp-daemon-v2.py; tests for routes in tests/n2n/test_grant_access_class_190.py
- [ ] T015 n2n-mcp tools `n2n_grant(access_class)`, `n2n_classify`, `n2n_import_annotations`, `n2n_list_classifications` in mcp-servers/n2n-mcp/server.py; re-pin its sha256 in config/hermes-hud-tool-policy.json

## Phase 8: Docs and polish

- [ ] T016 Normative draft text (new "Grant Access Class" section with the decision table, cards, trust-en2n cross-reference, security considerations, change history, method/error notes) in docs/ietf/draft-capobianco-ncfed-00.md
- [ ] T017 [P] New docs/N2N-GRANT-ACCESS-CLASS.md; update docs/N2N-PEER-LIMITS.md relationship section; update workspace/skills/n2n-federation/SKILL.md; check docs/reference/interfaces.json for n2n tool entries
- [ ] T018 Full `tests/n2n` run and compare to the known 17 chromadb failures; reconcile-mcp.py comparison; write real results and not-verified items in specs/190-grant-access-class/verification.md

## Dependencies
T001 -> T002 -> T003 -> T004,T005 -> T006,T007. T008 after T003. T010,T012,T013 after T005. T011 after T003. T014 after T004,T008. T015 after T014. T016-T017 after design stable. T018 last.

## MVP
Phase 2 + Phase 3 (T002-T007) delivers the enforced field; the rest completes the operator surface and documentation.
