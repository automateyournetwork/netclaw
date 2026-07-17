"""Evaluation harness for the RAG knowledge base (FR-080 – FR-082).

Runs ONLY when an operator-supplied golden set exists at
tests/fixtures/rag/golden_set.yaml (no fixture documents ship with the repo —
see golden_set.example.yaml for the format and setup steps). Without it the
whole module is SKIPPED — reported as skipped, never as passed.

Metrics:
- hit-rate@5: expected document appears in the top-5 results (pass >= 0.85)
- rerank lift: hit-rate with the reranker enabled vs disabled
- faithfulness: each entry's answer_facts substrings appear in retrieved chunks

Fully offline: uses the locally cached embedding/reranker models against the
operator's real corpus (point RAG_DATA_DIR at the store that holds the
golden-set documents before running).
"""

import sys
from pathlib import Path

import pytest

GOLDEN_PATH = Path(__file__).parent.parent / "fixtures" / "rag" / "golden_set.yaml"

if not GOLDEN_PATH.exists():
    pytest.skip(
        "no golden set supplied — copy golden_set.example.yaml to golden_set.yaml "
        "and author >=20 Q&A pairs over your ingested documents (FR-080)",
        allow_module_level=True,
    )

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "rag-mcp"))

import yaml  # noqa: E402

import rag_mcp_server as server  # noqa: E402


def _load_golden():
    with open(GOLDEN_PATH) as f:
        entries = yaml.safe_load(f)
    assert isinstance(entries, list) and entries, "golden_set.yaml must be a list of entries"
    return entries


def _run_eval(rerank_enabled: bool):
    server.reranker.enabled = rerank_enabled
    entries = _load_golden()
    hits, faithful, total = 0, 0, len(entries)
    for entry in entries:
        filters = (
            {"doc_type": entry["doc_type_filter"]} if entry.get("doc_type_filter") else None
        )
        resp = server._do_search(entry["question"], k=5, filters=filters)
        assert resp["success"], resp
        results = resp["data"]["results"]
        titles = {r["title"] for r in results}
        ids = {r.get("chunk_id", "").rsplit("_", 1)[0] for r in results}
        if entry["expected_doc"] in titles or entry["expected_doc"] in ids:
            hits += 1
        blob = " ".join(r["chunk_text"].lower() for r in results)
        if all(fact.lower() in blob for fact in entry.get("answer_facts", [])):
            faithful += 1
    return hits / total, faithful / total, total


def test_hit_rate_at_5_meets_threshold():
    hit_rate, faithfulness, total = _run_eval(rerank_enabled=True)
    print(f"\ngolden set: {total} questions | hit-rate@5={hit_rate:.2f} | faithfulness={faithfulness:.2f}")
    assert hit_rate >= 0.85, f"hit-rate@5 {hit_rate:.2f} below the 0.85 threshold (FR-081)"


def test_rerank_lift_reported():
    with_rerank, _, _ = _run_eval(rerank_enabled=True)
    without_rerank, _, _ = _run_eval(rerank_enabled=False)
    lift = with_rerank - without_rerank
    print(f"\nrerank lift: {with_rerank:.2f} (on) vs {without_rerank:.2f} (off) -> {lift:+.2f}")
    # Informational: lift is reported, not gated — small corpora can tie.
    assert with_rerank >= without_rerank - 0.10, "reranker materially degrades hit-rate"


def test_faithfulness_reported():
    _, faithfulness, total = _run_eval(rerank_enabled=True)
    print(f"\nfaithfulness (answer facts present in retrieved chunks): {faithfulness:.2f} over {total}")
    assert faithfulness > 0, "no entry's answer facts were found in retrieved chunks"
