# Mac development checkpoint — 2026-10-10

This is implementation evidence, not release acceptance. The owner authorized
steps 1–5 after the planning review, selected a Windows/WSL handoff, selected local
publisher authentication and explicitly requested an integrated RAG panel.

Work is isolated on `150-vscode-extension-implementation`, based on the actual
WSL baseline commit `aa2795313b487e00ccbe85d53f6a78db07b10a94`. The original Mac
checkout and owner runtime homes were preserved. Tests use newly allocated homes,
identities, loopback fixtures and private editor profiles. No real device command,
paid provider request, client credential change or Marketplace publication is
part of this checkpoint.

## Implemented checkpoint

- Locked extension and two private MCP packages; stable VS Code 1.102 APIs, exact
  mobile PNG, native Activity Bar navigation and installation-bound profiles.
- Existing installation identity, OS principal, strict operator/assistant surfaces,
  private journal, nonce tombstones, independent workers, proposal/verification
  framework, environment keep/replace/clear and installation-specific real GAIT.
- Operator Chat, Canvas and local Avatar; durable request admission, explicit
  context, context-preserving branches and versioned HUD Canvas import/export.
- Dedicated RAG panel and native command; existing collections, reviewed upload,
  detached indexing, citation search and explicit Chat/Canvas context selection.
  Shared RAG operation ownership prevents recovery sweeps from interrupting live
  ingestion. Keyword caches observe writes from other processes; replica
  publication joins the same ownership mechanism and preserves old content on failure.
- Candidate README, changelog, privacy, screenshots and exact VSIX file allowlist;
  CI builds a development artifact and does not publish.

## Observed checks

| Check | Result and scope |
|---|---|
| Backend JavaScript behavior | `node --test tests/operator/*.test.mjs tests/assistant-clients/*.test.mjs`: **42 pass, 4 explicitly skipped** opt-in process tests. No failures. |
| Extension unit checks | `npm --prefix extensions/netclaw-vscode test`: **8 pass**; profile isolation/stale storage, safe SSH quoting, hostile content, Canvas restore and inert RAG citations. |
| TypeScript and bundling | `npm run check` and `npm run build` pass in the extension package. |
| Actual desktop editor | VS Code **1.102.0**, macOS arm64, kernel **25.5.0**, private profile: **13 assertion groups pass**. Real MCP identity on separate synthetic OpenClaw/Hermes homes; actual rendered Chat, Canvas, Avatar and RAG. |
| RAG in the editor | Actual `rag-mcp` and cached BGE embeddings retrieve a synthetic uploaded document with its citation. Opening views, typing drafts, branching and retrieval dispatch no LLM operation. Screenshots were visually inspected. |
| Real RAG worker | `rag-process.test.mjs` with explicit test interpreter/cache and live GAIT: **1 pass**, about **13.3 seconds**. Upload → facade close → detached indexing → new facade → ready collection → real local model retrieval → selected context; nonce replay causes no second index operation. |
| RAG regression | Isolated Python 3.12: `pytest -q tests/unit/test_rag_*.py tests/integration/test_rag_mcp.py`: **95 pass**. Hash embeddings in the mechanics integration tests are distinct from the real-model process/editor tests. |
| Replica preservation | Isolated federation Python 3.12: `pytest -q tests/n2n/test_replication_lifecycle.py tests/n2n/test_replication_preservation.py`: **11 pass**, including busy-store cleanup without replacing the prior replica. |
| Existing HUD regression | Earlier checkpoint: existing HUD unit suite **372 pass**, including reused Avatar defaults and environment writer behavior. |
| Actual OpenClaw process | Earlier opt-in test: **1 pass**, installed **2026.7.1-2 (0790d9f)** with supported Node, private gateway and deterministic loopback provider; two contextual turns, stable nonce and facade disposal. No external provider or production tool qualification implied. |
| Actual Hermes process | Earlier opt-in test: **1 pass**, pinned **v0.21.6**, source `818c13be1dc4fd28987e1e881a9408224afd4535`, isolated Python 3.14 companion/3.12 bridge and deterministic loopback provider; two contextual turns and preserved companion. |
| Real GAIT/config worker | Earlier opt-in actual installed GAIT and detached environment worker test: **1 pass** after facade disposal, using a synthetic secret and private installation. |
| Package allowlist | **1 pass**: only 22 allowed runtime/documentation/media files; synthetic `.env`, credential JSON and private database files excluded. A preliminary VSIX contained 24 ZIP entries including the generated manifest and content-types file. |

Build/backend Node: **24.19.0**, explicitly selected from an isolated installed
toolchain. Unsupported system Node was not upgraded or selected for this work.
RAG process tests use a new private Python 3.12 environment, FastMCP **4.0.11**,
MCP **2.3.0**, Chroma **1.5.9**, sentence-transformers **5.7.0**, torch **2.14.1**,
`BAAI/bge-small-en-v1.5` and `cross-encoder/ms-marco-MiniLM-L-6-v2`. Public model
weights were cached in a private test directory; actual search/index tests run
with Hugging Face and Transformers offline flags.

## Failures found and corrected

- VS Code's stale whole-extension Memento events could erase newly saved profiles.
  Atomic private per-profile files now survive actual editor runs and stale-event tests.
- Canvas's initial webview-ready event sent an empty graph over the host graph.
  Ready no longer supplies a document; a behavioral regression covers branching.
- Cancelling while the runtime opened could still dispatch a prompt. The worker
  checks cancellation before inference; its regression verifies zero submissions.
- Concurrent RAG clients could sweep active ingestion and read stale keyword
  caches. Cross-process ownership and cache fingerprints now coordinate the store.
- Existing RAG tests shared a 2-dimensional fault corpus with the 64-dimensional
  integration corpus when collected together. Fault fixtures now own separate
  registry/vector/keyword stores; the combined suite passes.
- Default `vsce` monorepo URL rewriting produced broken README image/privacy
  paths. Packaging now requires committed source and explicitly pins URLs to its
  commit and extension subdirectory.

## Still open

Only T001–T004 and T020 are checked. Other tasks contain partial implementations
and remain unchecked until all their requirements pass. Assistant NL delegation
is explicitly refused until runtime/per-hop grant enforcement is complete;
assistant inventory/denial/grant fixtures are not named-client acceptance.
Federation mutation/delegation, owned service lifecycle, full security/intent,
provider/runtime/budget transactions, memory/GCF/meeting/Jev/mobile workflows,
installer/catalog coherence and the remaining release evidence are still required.

No WSL, native Linux, Remote SSH, second-distribution, actual Copilot/Claude Code/
Codex or public Marketplace acceptance is claimed here. The owner WSL baseline's
unsupported Node, absent live stable identity/management components and Spec149
Linux/WSL qualification remain dependencies. See the separate WSL evidence.
