# Cloud Border → on-prem member answer

Cloud HUD: https://r01-gcp-montreal.lobsternet.automateyournetwork.com/

This is an actual public HTTPS Chat API request through the cloud Border's
OpenClaw gateway using the owner's Anthropic Sonnet4.6. It invoked the existing
`n2n_route` tool, traversed the authenticated iN2N connection, and executed the
existing subnet calculator MCP on the separate Mac member. It is not pyATS.

Question: delegate `192.0.2.0/28` to `r01-20261101/onprem` and return usable range,
broadcast, netmask and host count from its actual tool result.

| Evidence | Observed value |
|---|---|
| Cloud Border | GCP Montréal, installation `f03c0a7c-5444-4cd6-b745-394471cf328a` |
| On-prem member | Mac, `r01-20261101/onprem`, installation `6ac7ac12-a8f9-4e98-966f-6433a8df95c8` |
| Model | `anthropic/claude-sonnet-4-6` on both |
| Federation task | `23f0a74f-0d54-4926-8938-eaa4482fced0` |
| Correlated request | `d21b912a-6d6c-4d1e-a975-dc74be5e7f1a` |
| Member start / completion UTC | 2026-11-01 21:06:27 / 21:06:36 |
| Actual member tool | `subnet-calc-mcp__subnet_calculator`, `{"cidr":"192.0.2.0/28"}` |
| Tool call correlation | `toolu_01LbkXRWd2PAFfKhZaep65fY`, matching call and result |
| Task state | completed on member and cloud |
| Usable range | 192.0.2.1–192.0.2.14 |
| Broadcast | 192.0.2.15 |
| Netmask | 255.255.255.240 |
| Usable hosts | 14 |
| Member recorded usage | 7,933 tokens; cloud task projection does not carry this usage |

The cloud response cites that member and task ID and returns the same values.
The Border's tool policy has only federation status/route/task reads; the member's
policy has only its subnet calculator. No shell, filesystem, device, pyATS or
external-message tools were granted. No on-prem inbound TCP listener was needed.

Private receipts under `~/.local/share/netclaw/spec168-direct-cloud-pivot-20261101/`:
`border-sonnet-request.json`, `border-sonnet-response.json`, `cloud-answer-task.json`,
`onprem-answer-task.json`, `onprem-calculator-tool-proof.json`, `answer-proof-index.json`.
The last two retain the member transcript hash and matching tool-call/result IDs.

Preserved failed attempts: Sonnet5.5 rejected the pinned runtime's thinking format;
initial gateway startup and missing MCP API binding prevented dispatch; two tasks
reached the member but failed because the fresh external subnet source lacked the
existing reviewed FastMCP migration. Applying that exact source-hash-checked patch
fixed the member. No failed attempt is counted as a successful answer. The full
browser settings path and RAG evidence are recorded in verification.md.

This qualifies this scoped lab example only. Production controls, general execution
parity, existing pyATS workloads, HA and multi-user authorization remain later work.

## Normal browser Chat proof

The same question was submitted with the public HUD's **Message NetClaw** composer
and **Send message** button. HTTPS returned200 with zero browser JavaScript errors.
The visible answer cited member `r01-20261101/onprem` and federation task
`845cd3b1-2848-4873-b67e-d1589528cefa`, with the same four subnet values above.

| Correlation | Actual browser request |
|---|---|
| Cloud / member task state | completed / completed |
| Correlated request | `55f13e96-c885-4600-92da-d951a11ced86` |
| Member start / completion UTC | 2026-11-01 21:11:04 / 21:11:12 |
| Actual tool | `subnet-calc-mcp__subnet_calculator`, `{"cidr":"192.0.2.0/28"}` |
| Matching call / result ID | `toolu_01XvNXcaeNfu6Xif3Wi8T1SY` |
| Member transcript SHA256 | `ba9babec6343e54230fe15eda3c386d6fda2a2c8624ef5ee5c7bf1002b0fd63c` |
| Member recorded usage | 7,933 tokens; cloud task projection usage unavailable |

Receipts: `browser-question-proof.json`, `browser-cloud-answer-task.json`,
`browser-onprem-answer-task.json`, `browser-onprem-tool-proof.json` and the
visually inspected `cloud-border-onprem-answer.png`.

The initial browser attempt failed in the settings CLI before any model message.
A direct native RPC diagnostic succeeded after69.98s of CLI startup. The pilot's
bounded120s settings-CLI override resolved that small-host startup delay; the
native RPC retains its10s timeout. The failed receipt remains preserved.

## RAG and Canvas

The browser uploaded a harmless public lab guide, which indexed as
`doc_26e1d37b1406` at21:18:55Z, one ready chunk. Actual dense/BM25/reranked retrieval
returned the correct member and subnet excerpt with citation
`[R01 public cloud lab guide — ingested 2026-11-01]` and score0.9938.
**Use evidence in Canvas → Add to canvas draft** transferred the full excerpt,
source path, retrieval time and citation into the actual Canvas composer.
This is distinct from the on-prem execution proof above: retrieval uses local
cloud CPU models, while the member answer uses the owner's Anthropic credential.

`browser-rag-canvas.json`, `full-hud-rag-retrieval.png` and
`full-hud-rag-canvas.png` record the successful flow. A first handoff assertion
looked for a textarea; Canvas uses an input. Its acknowledged handoff and screenshot
were retained, then the corrected selector verified the actual input value.
No repeated upload was needed for that test correction.

RAG's first upload was interrupted after overlapping helper startup caused high
load. No document was committed. The HUD now serializes RAG calls, coalesces list/
stats polls, bounds pending work, preserves read-after-write order and never
replays a mutation. Three new regression tests pass; the subsequent browser
upload and retrieval passed. This protects calls from this HUD process;
independently launched RAG clients still require operator coordination.

The final browser flow also **sent the retrieved context from Canvas**. It returned
HTTP200 through the cloud gateway, citing the lab guide and correctly identifying
the Mac member and192.0.2.1–192.0.2.14 host range. Zero JavaScript errors.
`browser-rag-canvas-answer.json` and visually inspected
`full-hud-canvas-answer.png` retain this separate Canvas answer. Model-generated
additional reference suggestions are not treated as independently retrieved evidence.
