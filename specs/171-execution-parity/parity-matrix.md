# R02 execution parity matrix

Both corrected native harnesses pass exact-command, signed-result, recovery and
independent security/evidence review. T001–T035 are complete; the human T036 gate
remains open. The implicit Unicon probe found in the first run was corrected and
fresh full transcripts contain only the approved command. Evidence is detailed in
[verification.md](verification.md); exact pins and limits are in
[runtime-review.md](runtime-review.md). These guarantees apply to the selected
protected profile. They are not retroactive claims about legacy installations.

Code abbreviations below link to the implementation:
[owner](../../mcp-servers/protocol-mcp/bgp/federation/protected_owner.py),
[contract](../../mcp-servers/protocol-mcp/bgp/federation/protected_contract.py),
[store](../../mcp-servers/protocol-mcp/bgp/federation/protected_store.py),
[service](../../mcp-servers/protocol-mcp/bgp/federation/protected_service.py),
[runtime](../../mcp-servers/protocol-mcp/bgp/federation/protected_runtime.py),
[Docker](../../mcp-servers/protocol-mcp/bgp/federation/protected_docker.py),
[provider fence](../../scripts/lib/protected_provider.py),
[pyATS adapter](../../scripts/lib/protected_pyats.py),
[HUD](../../ui/netclaw-visual/src/hud-server/protected-operations.js),
[GAIT](../../mcp-servers/protocol-mcp/bgp/federation/gait.py).

| Reference guarantee | Baseline and implementation decision | Acceptance evidence and qualification limit |
|---|---|---|
| Trusted approving principal | Existing conversation binding was insufficient. Added owner tickets, one-use consumption, server sessions and revocation in owner/HUD. | Actual native CLI, HTTP and Chrome login/revocation/logout pass. Owner only; SSO/RBAC remains later. |
| Exact immutable review | Added catalog-bound scope, stable client nonce, review digest and explicit decision in service/HUD. | Both actual browser reviews completed one authorized read; refresh sent no prepare/decision replay. |
| Signed, expiring approval | Reused enrolled P-256 trust; added domain-separated strict schemas in contract/service. | Independent signature tests and actual wire tamper/expiry refusals. Expiry probes are validly signed, already-expired specimens. |
| Durable one-use authority | Added atomic admission/executor/effect claims and retained spent authority in store/service. | Separate-process first-admission races; actual concurrent completed-approval replay preserves provider/tool hashes. These are distinct tests. |
| Exact tool effect gate | Added broker callback gate and frozen tool schema/source/inventory in runtime/Docker/pyATS adapter. | Each native member captured the exact reviewed R1 read once. Owner/wire argument mutations refuse; raw HTTP/MCP negative qualification is recorded separately. |
| Approved revisions match actual inputs | Added derived runtime/tool revisions for images, guard policy/config, source closure, native CLI/Python and endpoint identity in Docker. | Independent review found and corrected the initial comparison-only gap. Recomputed bindings pass; drift tests refuse before forwarding/effect. |
| Provider credentials stay at guard | Separate guard container and fixed provider origin in Docker/provider fence. | Both real guarded operations, guard health and exact credential-byte scan pass. Trusted guard shares UID/filesystem with its runner. |
| Device credentials stay at broker | Dedicated child gets three device aliases; no agent/Border inventory or secret mount. | Actual adapter read, source/environment checks and 86-file Border/model/provider-body credential scan pass. Original testbeds unchanged. |
| Guard/broker cannot be bypassed within qualified topology | Protected lifecycle refuses legacy execution/HUD routes; isolated agent network uses a fixed relay in Docker/service/HUD. | Actual legacy HTTP/WebSocket and strict-wire refusals; official guard authentication/action/injection tests use a controlled upstream. Separate direct-container egress and raw MCP refusal evidence are identified in verification; no compromised-host guarantee. |
| Inference stays bounded despite SDK retries | Outer two-turn runtime fence plus durable provider-request deduplication. | Each real operation has two finished provider claims. Actual official SDK retries to a local stub dispatch once; a third unique request refuses; unknown remains spent after restart. |
| Execute once, parse captured output | Dedicated pyATS adapter executes once and passes raw output to its parser; strict endpoint key and qualified native dependency pins. | Both corrected native transcripts contain exactly one approved read and zero setup commands; parsed IOS-XE 17.18.2. Earlier implicit discovery finding remains visible. |
| Unknown remains distinct from failure/completion | Durable claims and explicit uncertain/cleanup states in store/service/runtime. | Real SSH timeout remains unknown/spent. Independent 14-check native restart/reconcile proof adds no provider/tool/container execution. |
| Signed result and durable Border ACK | Added bound result/ACK schemas and verified persistence in contract/service. | Actual native receipts and browser verified payloads retained; independent signature/GAIT inspection recorded in verification. ACK persistence and ACK delivery are distinct. |
| Recovery never repeats an effect | Original identity drives status/reconcile/ACK, with no executor reentry in service. | Final actual OpenClaw submit-reply loss, Hermes ACK-reply loss and full process restart preserve original results/counters, independently checked against retained pre/post snapshots. |
| Attributable required audit | Extended existing GAIT with principal/correlation and mandatory pre-boundary emission. | Actual read/refusal GAIT commits, independent signature/audit correlation, concurrent audit serialization and unavailable-audit tests. No parallel replacement audit system. |
| Preserve installations and release boundaries | Explicit opt-in and fresh private homes; existing code paths retained. | 311 protected, 219 legacy/installer, 436 HUD, eight Node boundary checks and build pass. Original inventories unchanged; no cloud change, release or version bump. |

OpenClaw 2026.7.1-2 and Hermes v0.21.6 are separately qualified with Sonnet 4.6
for this read on a Mac-hosted Linux ARM64 Docker runtime. Hermes uses the HTTP
guard adapter and MCP broker; native Hermes hooks are unqualified. The host and
Docker daemon are trusted. Arbitrary providers/models, other platforms, physical
mobile use, cloud execution, device writes and multi-user controls remain outside
R02 acceptance. R03–R05 retain their own ordered human acceptance/resource gates.
