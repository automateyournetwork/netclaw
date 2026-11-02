# R02 execution parity matrix

Status: implementation integrated in stages; real provider/device acceptance and
final independent review remain open. Fixture evidence is labelled explicitly.
The scope is the selected protected profile, not a retroactive guarantee for
legacy installations. See [verification](verification.md) and the
[local runtime packet](runtime-review.md).

| Required guarantee | Baseline / implementation decision | Current evidence and remaining limit |
|---|---|---|
| Trusted approving principal | Existing HUD conversation binding was insufficient. Added private native owner tickets, one-use consumption, server sessions and revocation. | Actual CLI/HTTP/Chrome login, revocation and logout passed; owner only, no SSO/RBAC claim. |
| Exact immutable review | Added catalog-bound operation, stable client nonce, member/model/tool/argument review digest and explicit decision. | Actual browser review and refresh passed with synthetic effects; real read pending. |
| Signed, expiring approval | Reused enrolled P-256 trust with new domain-separated canonical approval schema. | Independent signature/tamper/expiry tests and actual strict iN2N signed exchange passed. |
| Durable one-use authority | Added atomic SQLite admission, executor and effect claims with retained spent authority. | Separate-process races, process death and repeated decisions passed; no timeout-to-retry reset. |
| Exact tool effect gate | Added trusted broker wrapping the actual callback, fixed read schema and frozen adapter/source/inventory. | Changed tool/device/arguments refuse in tests; actual execute-once pyATS read pending. |
| Runtime revision matches approval | Bind signed model/tool revisions to immutable images, guard policy/configuration and adapter/source closure. | Independent audit found missing recomputation; correction and recheck pending before live activation. |
| Provider credentials remain at guard | Separate per-operation guard container, fixed Anthropic origin, no model/Border provider key. | Actual guard startup/child-environment inspection passed; full native operation credential inspection pending. Trusted guard processes share UID/filesystem. |
| Device credentials remain at broker | Fresh dedicated stdio child with only three credential aliases; no agent/Border testbed mount. | Frozen inputs and environment boundary tests passed; real child and transcript inspection pending. |
| Guard cannot be bypassed | Explicit protected lifecycle, refusal of legacy execution and HUD APIs, isolated agent network and fixed relay. | Actual legacy API/WebSocket and strict-wire refusals passed; actual isolated harness egress probe passed. Final native-runtime bypass evidence pending. |
| Inference is bounded despite SDK retries | Added outer two-turn fence plus inner durable provider request deduplication. | Actual official guard: four retries caused one stub upstream dispatch; two unique requests allowed, third refused; unknown dispatch stayed spent across restart. Real provider counts pending. |
| Tool executes once and parsing does not re-read | Dedicated adapter executes once, then calls the parser with captured output; strict private host-key trust. | Offline actual pyATS load and generated Unicon SSH arguments passed; exact-node CML/SSH public-key match passed. Real parsed output pending. |
| Unknown is distinct from failure/completion | Durable claims survive lost replies, deadlines, process death and incomplete cleanup. | Independent crash/deadline tests passed; actual guard unknown/restart test passed against stub. Real-operation recovery pending. |
| Signed member result and durable Border ACK | Added result/ACK schemas, frozen trusted authority and verified persistence before completion. | Actual TLS exchange and independent cryptographic receipt inspection passed with synthetic effects; real result pending. |
| Recovery never starts a new effect | Status/reconciliation uses the existing operation, receipt and ACK. Browser stores only operation references. | Actual browser refresh caused zero decision/prepare replays; strict-wire lost-ACK and full restart retained one synthetic effect. Real read/restart comparison pending. |
| Attributable required audit | Extended GAIT with principal/correlation and mandatory pre-boundary emission; retained pending audit after effects. | Actual GAIT commits in strict-wire fixture, process-safe serialization and audit-unavailable tests passed. Real read correlation pending. |
| Preserve installations and release boundaries | Explicit opt-in, fresh private homes, unchanged original inventories, no cloud/release changes. | Original inventories re-hashed unchanged. Relevant legacy regression/build checks passed at earlier checkpoints; final regression and human R02 gate pending. |

OpenClaw and Hermes each require their own actual read evidence. Hermes uses the
qualified HTTP guard adapter and MCP broker; native Hermes hook enforcement is
outside this qualification. The trusted Mac host/Docker daemon is not an
untrusted tenant. Arbitrary models/providers, other platforms and device writes
remain unqualified. R03–R05 are not started by this matrix.
