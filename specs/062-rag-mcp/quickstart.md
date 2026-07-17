# Quickstart: Agentic RAG Knowledge Base (rag-mcp)

## Install

```bash
# Via the modular installer (default-on component)
./scripts/install.sh                 # rag-mcp included in recommended profile
# or enable just this component later:
./scripts/install.sh --components rag-mcp
```

The install step: pips `mcp-servers/rag-mcp` (editable), creates `~/.openclaw/rag/`, pre-downloads the embedding model (`BAAI/bge-small-en-v1.5`, ~130 MB) and reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`, ~80 MB), offers optional LibreOffice install (legacy DOC/XLS/PPT/VSD support), and registers `rag-mcp` in `config/openclaw.json`. After this, the system is fully offline.

## Teach NetClaw something (three ways)

```text
# 1. Slack: drag a PDF into the NetClaw channel
you>  (attach wlc-9800-upgrade-guide.pdf) learn this — it's a vendor guide
netclaw> Learned "WLC 9800 Upgrade Guide" (vendor, 84 pages, 217 chunks, documents).
         Try asking: "What are the pre-upgrade checks for the 9800?"

# 2. URL (with crawl-scope confirmation)
you>  ingest https://vendor.example/wlc-9800-upgrade-guide
netclaw> That page links to 6 same-domain pages. Ingest just the page, or all 7?
you>  all 7
netclaw> Ingested 7 pages into documents. …

# 3. HUD: open the Knowledge panel → drag file → watch parsing → chunking → embedding → done
```

## Ask (agentic retrieval — NetClaw decides)

```text
you>  upgrade the lab WLC following our customer standards
netclaw> (decomposes, searches vendor guide + customer standard, critiques, refines ≤3 rounds/sub-query)
         Per [Customer WLAN Standard §2.1 — ingested 2026-07-16] maintenance window is required…
         Pre-checks per [WLC 9800 Upgrade Guide §4.2, p.31 — ingested 2026-07-16]: …
         Now checking live state via pyATS…   ← live state ALWAYS from MCP, never RAG
```

Routing rules (SOUL.md four-source hierarchy): fundamentals → answered directly; past sessions/decisions → Memory MCP; uploaded docs/standards → `rag_search`; current network state → live MCP servers. Misses are reported honestly with an offer to ingest.

## Snapshots (opt-in only, never automatic)

```text
you>  snapshot the core routers' BGP tables so we can compare next month
netclaw> Scope: PE1, PE2 — "show ip bgp" via pyATS, into snapshot_core-bgp_<timestamp>. Confirm?
you>  yes
netclaw> Stored 48 chunks. Redactions: password: 2, snmp_community: 1, bgp_auth_key: 0 …
# a month later
netclaw> From snapshot core-bgp — captured 2026-07-16 14:02 UTC — 31 days ago (live state available via MCP): …
```

## Manage the corpus

```text
rag_list        # documents + snapshots (separate), full metadata
rag_stats       # corpus totals + retrieval telemetry
rag_delete / rag_reindex     # HIIL-confirmed, GAIT-committed
rag_update_metadata          # fix doc_type/title/version
```

Or use the HUD Knowledge panel table (delete/re-index with confirm dialogs, snapshot age badges).

## Evaluate (after you collect real documents)

```bash
# Author a golden set (no fixture docs ship with the repo):
cp tests/fixtures/rag/golden_set.example.yaml tests/fixtures/rag/golden_set.yaml
# … fill in ≥20 Q&A pairs over your ingested docs, then:
pytest tests/integration/test_rag_eval.py -v   # hit-rate@5 ≥ 0.85 to pass; skips if no golden set
pytest tests/unit/test_rag_* tests/integration/test_rag_mcp.py   # mechanics suite, fully offline, no models needed
```

## Key env vars (`.env`)

```bash
RAG_DATA_DIR=~/.openclaw/rag
RAG_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5     # upgrade: BAAI/bge-base-en-v1.5
RAG_RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RAG_RERANK_ENABLED=true                         # false for low-resource hosts
RAG_MAX_DOC_MB=100
RAG_MAX_DOC_PAGES=1000
RAG_CRAWL_MAX_PAGES=30
RAG_SNAPSHOT_WARN_DAYS=90
RAG_MAX_ROUNDS=3
```

## Boundaries to remember

- **RAG ≠ Memory**: `~/.openclaw/rag/` (user-uploaded knowledge) is fully separate from `~/.openclaw/memory/` (NetClaw's own experience). Neither writes into the other.
- **RAG ≠ live state**: current network questions always go to MCP servers; the only live data in RAG is an explicitly confirmed, secret-scrubbed, timestamped snapshot.
- **Every RAG claim is cited**; anything NetClaw can't cite, it won't attribute to the knowledge base.
