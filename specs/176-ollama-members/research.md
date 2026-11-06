# Research: adopt Thermidor's final working solution

Read on 2026-11-05. Reference checkout: `../../../thermidor/` from this folder,
resolved locally as `/Users/john.capobianco/thermidor`. NetClaw baseline is
`db0c9682d4997d51a15f75cbf2df83b97d3c3f45`; Thermidor HEAD is
`ebc91b3621bc874541a115e6d544f3a1fb267f6f`. Exact inspected file hashes are in
[thermidor-reference.json](thermidor-reference.json). Thermidor has unrelated dirty
Spec005 HA work, including `operation_broker.py`; never bulk-copy that working tree.

## Primary evidence and decisions

All Thermidor paths below are relative to the sibling checkout. Its
`docs/thermidor-ollama-members.md`, `specs/004-ollama-open-weight/evidence.md` and
`labs/ollama/README.md` are the primary reference, beyond NetClaw's copied handoff.
The final evidence records three successes per host and combined local28s/cloud150s,
two approvals, two real inference turns and one scoped tool effect per child,
positive token usage, eight collector ACKs per child and zero provider charges.
Those results and the old trial lifetime are historical; none are NetClaw R05 evidence.
NetClaw must use its own result/ACK contract, not adopt an arbitrary eight-ACK count.

| Decision | Rationale and exact Thermidor reference | Alternative considered |
|---|---|---|
| Pinned Ollama0.40.11 / Qwen3:0.6b Q4_K_M, CPU only | Final proven profile; `labs/ollama/model-lock.json`, `src/thermidor/ollama_profile.py` | Latest model, GPU, broad provider compatibility add unneeded qualification |
| Existing OpenClaw + DefenseClaw + native MCP | Proven native keyless guard; `guard_adapter.py:_safe_configuration`, `model_admission.py:ModelAdmission._fetch` | New runtime/equivalent guard unnecessary unless the installed artifact actually fails |
| Immutable calculator-v4 instruction adaptation | `model_admission.py:calculator_prompt`; earlier text/JSON-only completions failed exact-tool acceptance | Merely demanding `tool_choice=required` did not force a call |
| Trusted `reasoning_effort=none` | `/no_think` alone failed; setting derives from signed profile | Accepting model/caller overrides breaks profile authority |
| One compact JSON text MCP result | `labs/cloud/member_broker.py`; text plus structuredContent duplicated the second-turn result,964→420bytes after correction | Raising context/latency to accommodate duplicate serialization |
| Final swap-disabled capacity/retention | `evidence.md`:512MiB fixture hid swap; actual agent OOM;1,536MiB passed. Cloud30s retention forced reload;120s succeeded | Reusing preliminary capacities or using swap to hide inadequate RAM |
| Durable provider-wide uncertainty latch plus per-request claims | `ollama_profile.py:ProviderLatch`; uncertain dispatch survives restart | Retry timeout automatically because arithmetic is read-only/free |
| Stable parent references, child approvals | `calculator_execution.py:CalculatorCoordinator`, `contracts/calculator.md` | Treat parent creation or one approval as authorization for both |
| NetClaw native subnet summary tools | Existing `workspace/skills/subnet-calculator/SKILL.md`, `protected_mcp.py` | Copy Thermidor calculator as a second execution backend; unnecessary for R05 |
| Preserve current NetClaw transport/principals | Accepted R04a/R04b and current contracts | Import Tailscale policy, expired trial state or a user-login scheme |

## Concrete adaptation gaps

1. `scripts/lib/protected_provider.py` and `scripts/protected-guard.py` fix the
   upstream/model to Anthropic Sonnet. Add an explicit Ollama profile and trusted
   local route while keeping existing hosted behavior and its unknown fence intact.
2. `protected_contract.py:validate_tool_arguments` currently permits only canonical
   IPv4 `/24–/30` for protected subnet work. The skill describes IPv6, but the inspected ignored native clone at
   `mcp-servers/subnet-calculator-mcp`, commit
   `5178da6f83ebd894fa7331a62e1087ec9550751b`, exposes only IPv4. It iterates whole
   networks despite a preview filter, repeatedly calls `list(network)`, overflows
   neighbor arithmetic and uses N−2 at `/31,/32`. T006 must qualify and pin corrected
   existing upstream source or supply a tracked small patch to that same MCP via
   `scripts/patches/subnet-calculator-bounded.patch` and the scoped installer.
   Add native IPv6, bounded arithmetic and edge fixes before broadening admission;
   preserve old runtime/history identities. Do not edit only the ignored clone or
   claim capabilities from the skill description.
3. Thermidor's prompt uses its own tool names/arguments. Adapt the v4 pattern to the
   exact offered NetClaw native schema and approved CIDR. Preserve actual messages,
   refuse prose-only/bare-JSON/empty tool proposals, and require the generated tool call.
4. Native IPv6 summaries may represent large counts approximately. Independent
   verification must normalize exact counts as decimal strings, compare all claimed
   arithmetic, preserve relevant facts, reject contradictions and identify absent
   native fields. The authoritative normalized result must not come from narration.
5. Existing child authority is sufficient, but clients persist a single operation.
   Add one durable parent mapping and bounded two-child references/capability across
   HUD, VS Code and enrolled Mobile. Do not create a second approval ledger.
6. Current container limits differ. Adopt the final profile and verify actual
   enforcement. Model loopback UID confinement needs its owned ephemeral worker
   connections as well as guard access, while excluding broker/service ports.

The latch must be member/provider-instance scoped, with operation attribution,
not merely a new database per operation. A fresh operation ID cannot escape an
uncertain runner. Retain per-request dispatch claims as well as this shared latch.

## Failure lessons to carry into acceptance

| Thermidor lesson | R05 requirement / verification |
|---|---|
| Agent implicit swap made early fixture capacity misleading | FR-006; inspect actual memory+swap/cgroups and OOM state on ARM64/AMD64 |
| Cloud cache unloaded between turns | FR-006/009;120s cloud retention, then observe eventual unload |
| Model worker could not reach its own ephemeral listener | FR-005; narrow model-owned worker permission, explicitly excluding broker ports; positive control as well as denials |
| Guard management readiness preceded proxy listener | Preflight with non-inference listener readiness; never retry a spent canary |
| Blocking history verification delayed control callbacks | FR-007; yield outside transactions, then revalidate authority; bounded status/read load |
| Timeout did not terminate the process tree | FR-007; persistent member/runner unknown latch and verified owned-process recovery before fresh work, even under a new operation ID |
| Export copy did not prove collector reconciliation | FR-009; verify actual signed result and durable ACK in the existing authority |
| Existing assignment changes could relabel history | FR-003/012; immutable historical profile/binding generation and retained original actors |

## Test reuse map

| Thermidor test file / named case | NetClaw target and behavior |
|---|---|
| `tests/test_subnet_calculator.py`, `test_enormous_space_is_bounded_and_uses_decimal_strings` | `tests/n2n/test_protected_calculator_176.py`: independent `/31,/32,/127,/128`, enormous space, no enumeration, exact strings |
| `tests/test_calculator_routing.py`, `test_combined_request_keeps_two_distinct_sequential_children` | Same target: exactly two different families; reject extra/contradictory input; deterministic routing |
| `tests/test_calculator_execution.py` | `test_protected_combined_176.py`: no work on prepare, separate signed approvals, changed authority, unknown/cancel/recovery |
| `tests/test_ollama_profile.py` | `test_protected_ollama_176.py`: immutable historical profiles, retention, latch restart and verified recovery |
| `tests/test_model_admission.py` | `test_protected_ollama_guard_176.py`: trusted profile/prompt/controls, preserved real conversation, zero cost, hosted/local separation |
| `tests/test_guard_adapter.py`, `test_native_ollama_guard_keeps_strict_inspection`, `test_local_route_cannot_enable_general_upstream_or_hosted_credentials` | Same guard target: strict/action/closed, caller-header refusal, no dummy key or general private-upstream access |
| `tests/test_cloud_broker.py`, `test_calculator_mcp_exact_tool_guard_result_and_once_only`, `test_calculator_result_cannot_be_model_arithmetic_or_extra_text` | `test_protected_calculator_176.py`: real native MCP, exact call once, compact result, independent proof |
| `tests/test_ollama_deployment.py` | `test_protected_ollama_deployment_176.py`: five-role confinement, worker ports, headroom, collisions and no spent-journal replay |
| `src/thermidor/assets/ui/thermidor-visual/src/cloud/client.test.js` | Existing HUD tests plus extension/Mobile tests: persist before POST, lost response GET recovery, reconnect never repeats POST |

Port behavioral cases, not Thermidor-specific authorities/fixtures. Summary-only
scope omits subdivision execution; its bounded-arithmetic lessons remain useful.
No tests or model calls were run against Thermidor during this preparation.
