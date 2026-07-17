# Teaching NetClaw to Read: An Offline, Agentic RAG Knowledge Base

*Draft for WordPress — by John Capobianco & Claude (NetClaw milestone, Feature 062). Present to John for review before publishing (Constitution XVII).*

---

NetClaw can query live routers, reconcile NetBox, and file ServiceNow changes — but until today, it couldn't read the 300-page vendor upgrade guide sitting in your downloads folder, or your customer's WLAN standards document. Feature 062 changes that: NetClaw now has a fully **offline, free, local** document knowledge base, and users teach it by simply dropping files into Slack, the HUD's new Knowledge panel, or pasting a URL.

## What we built

A new FastMCP server, `rag-mcp`, with ten tools and one governing idea: **retrieval is a tool, not a pipeline**. NetClaw decides when to search its knowledge base, critiques what comes back, refines its queries within a hard budget (3 rounds per sub-query), and cites every single claim — `[WLC 9800 Upgrade Guide §4.2, p.31 — ingested 2026-07-01]`. If the corpus doesn't cover a topic, it says so and offers to ingest a document, rather than hallucinating.

Under the hood:

- **Ingestion**: PDF, Markdown, HTML, TXT, DOCX, XLSX, PPTX, and Visio VSDX parsed natively; legacy DOC/XLS/PPT/VSD via LibreOffice headless. Structure-aware chunking splits on headings, keeps CLI blocks and tables atomic, and prefixes every chunk with a document breadcrumb.
- **Retrieval**: hybrid — dense vectors (bge-small, local) AND BM25 keyword search with a networking-aware tokenizer, so `Gi0/0/1` and `CVE-2026-1234` are always findable. Reciprocal rank fusion, then a local cross-encoder reranker. Zero network calls at query time, zero paid services.
- **Snapshots**: an opt-in-only door for live data. "Snapshot the core BGP tables so we can compare next month" — scope confirmed first, secrets scrubbed (with per-type redaction counts, zeros included), and every later retrieval leads with the capture age.

## The decision that mattered most: RAG is not memory

NetClaw already has a Memory MCP — its own experience: facts, session summaries, decisions. Mid-design, John drew a hard line: the knowledge base holds what **users** upload; memory holds what **NetClaw** learns. They live in separate stores (`~/.openclaw/rag/` vs `~/.openclaw/memory/`), and neither writes into the other. SOUL.md now teaches a four-source hierarchy: answer fundamentals from parametric knowledge, past sessions from Memory, documents from RAG, and current network state from live MCP tools — never from a vector store.

## Lessons learned

- **Spec-driven pays off**: specify → clarify (5 targeted questions) → plan → analyze (10 findings, all remediated pre-implement) → implement. The clarifications (per-sub-query budgets, log-only chunk IDs, operator-supplied golden sets, default-on installer) each killed a class of rework.
- **Structural gates beat prose rules**: the URL crawler's scope token makes "confirm before crawling" a protocol property, not a hope; the HIIL `confirmed=true` flag does the same for deletion.
- **Honest evaluation**: the golden-set harness ships with a format and a skip — not fake fixtures. It runs when John supplies real documents, and reports skipped, never passed, until then.

65 offline tests, a new HUD panel with live ingestion progress, installer integration, and full artifact coherence (Constitution XI checklist green). NetClaw now reads the docs — and shows its work.

*What was built: rag-mcp server, `rag` skill, HUD Knowledge panel, four-source routing guidance. Why it matters: cited, offline document knowledge with zero hallucinated authority. Key decisions: RAG/memory separation, hybrid retrieval, opt-in snapshots. Lessons: structural gates, honest misses, spec-driven flow.*
