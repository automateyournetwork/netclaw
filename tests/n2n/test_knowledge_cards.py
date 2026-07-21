"""Feature 064 US1: knowledge advertised on the capability card.

Covers T008 (per-collection entries + absence), T009 (content-free / no-secrets),
T010 (per-peer visibility + topic-only), T010a (card size independent of corpus
size, SC-005).
"""

import json
import sqlite3

import pytest

from bgp.federation import knowledge as kn
from bgp.federation.inventory import InventoryBuilder


def _make_rag_db(dirpath, docs):
    """Write a minimal feature-062 rag.db `documents` table. Each doc is a dict
    with at least collection/title/doc_type/page_count/chunk_count; source_path
    and content_hash are populated to prove they never reach the card."""
    dirpath.mkdir(parents=True, exist_ok=True)
    db = dirpath / "rag.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE documents (id TEXT, collection TEXT, title TEXT, doc_type TEXT, "
        "page_count INT, chunk_count INT, ingest_status TEXT, source_path TEXT, "
        "content_hash TEXT)")
    for i, d in enumerate(docs):
        conn.execute(
            "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?)",
            (f"doc_{i}", d.get("collection", "documents"), d.get("title"),
             d.get("doc_type"), d.get("page_count", 0), d.get("chunk_count", 0),
             d.get("ingest_status", "ready"),
             "/home/secret/path/original.pdf", "deadbeefcafe" * 4))
    conn.commit()
    conn.close()
    return db


def _repo(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "openclaw.json").write_text(json.dumps({"mcpServers": {}}))
    (tmp_path / "workspace" / "skills").mkdir(parents=True)
    env = tmp_path / ".env"
    env.write_text("SOME_SECRET=xyzzy-secret-123\n")
    return tmp_path, str(env)


def _builder(manager, tmp_path, rag_dir, monkeypatch):
    monkeypatch.setenv("RAG_DATA_DIR", str(rag_dir))
    monkeypatch.delenv("N2N_KNOWLEDGE_TOPIC_ONLY", raising=False)
    repo, env = _repo(tmp_path)
    return InventoryBuilder(manager, repo_root=str(repo),
                            openclaw_config=str(repo / "config" / "openclaw.json"),
                            env_path=env)


# ---- T008 -----------------------------------------------------------------

def test_one_entry_per_collection_with_counts(manager, tmp_path, monkeypatch):
    _make_rag_db(tmp_path / "rag", [
        {"collection": "documents", "title": "Automate Your Network",
         "doc_type": "install-guide", "page_count": 212, "chunk_count": 389},
        {"collection": "runbooks", "title": "BGP Runbook",
         "doc_type": "runbook", "page_count": 10, "chunk_count": 20},
    ])
    b = _builder(manager, tmp_path, tmp_path / "rag", monkeypatch)
    inv = b.build("as65007-7.7.7.7")
    ids = {e["collection_id"]: e for e in inv["knowledge"]}
    assert set(ids) == {"knowledge:documents", "knowledge:runbooks"}
    docs = ids["knowledge:documents"]
    assert docs["doc_count"] == 1 and docs["page_count"] == 212 and docs["chunk_count"] == 389
    assert docs["retrieval"] == "n2n/knowledge/query"
    assert "install-guide" in docs["tags"]


def test_no_ready_docs_means_no_knowledge(manager, tmp_path, monkeypatch):
    _make_rag_db(tmp_path / "rag", [
        {"collection": "documents", "title": "Draft", "doc_type": "x",
         "ingest_status": "pending"}])
    b = _builder(manager, tmp_path, tmp_path / "rag", monkeypatch)
    inv = b.build("as65007-7.7.7.7")
    assert inv["knowledge"] == []


def test_no_rag_db_means_no_knowledge(manager, tmp_path, monkeypatch):
    b = _builder(manager, tmp_path, tmp_path / "empty", monkeypatch)  # no rag.db
    inv = b.build("as65007-7.7.7.7")
    assert inv["knowledge"] == []


# ---- T009 -----------------------------------------------------------------

def test_card_is_content_free(manager, tmp_path, monkeypatch):
    _make_rag_db(tmp_path / "rag", [
        {"collection": "documents", "title": "Automate Your Network",
         "doc_type": "install-guide", "page_count": 212, "chunk_count": 389}])
    b = _builder(manager, tmp_path, tmp_path / "rag", monkeypatch)
    inv = b.build("as65007-7.7.7.7")
    blob = json.dumps(inv["knowledge"])
    assert "/home/secret/path" not in blob          # no source_path
    assert "deadbeefcafe" not in blob               # no content_hash
    # only the allowed keys are present
    for e in inv["knowledge"]:
        kn.assert_entry_clean(e)


def test_no_secrets_guard_covers_knowledge(manager, tmp_path, monkeypatch):
    # a secret value that leaks into a description must trip _assert_no_secrets
    _make_rag_db(tmp_path / "rag", [
        {"collection": "documents", "title": "xyzzy-secret-123 leak",
         "doc_type": "x", "page_count": 1, "chunk_count": 1}])
    b = _builder(manager, tmp_path, tmp_path / "rag", monkeypatch)
    with pytest.raises(ValueError):
        b.build("as65007-7.7.7.7")


def test_assert_entry_clean_rejects_forbidden_key():
    with pytest.raises(ValueError):
        kn.assert_entry_clean({"collection_id": "knowledge:x", "source_path": "/etc/passwd"})


# ---- T010 -----------------------------------------------------------------

def test_per_peer_visibility(manager, tmp_path, monkeypatch):
    _make_rag_db(tmp_path / "rag", [
        {"collection": "documents", "title": "Book", "doc_type": "g",
         "page_count": 1, "chunk_count": 1}])
    b = _builder(manager, tmp_path, tmp_path / "rag", monkeypatch)
    # hide 'documents' from peer X only
    manager._conn.execute(
        "INSERT OR REPLACE INTO visibility_setting (item_type,item_name,visibility,peer_list) "
        "VALUES ('knowledge','documents','hidden',NULL)")
    manager._conn.commit()
    inv_x = b.build("as65099-9.9.9.9")
    assert inv_x["knowledge"] == []
    # a fresh collection visible to a permitted peer when not hidden
    manager._conn.execute("DELETE FROM visibility_setting WHERE item_type='knowledge'")
    manager._conn.commit()
    inv_y = b.build("as65007-7.7.7.7")
    assert any(e["collection_id"] == "knowledge:documents" for e in inv_y["knowledge"])


def test_topic_only_omits_titles(manager, tmp_path, monkeypatch):
    _make_rag_db(tmp_path / "rag", [
        {"collection": "documents", "title": "Automate Your Network",
         "doc_type": "install-guide", "page_count": 1, "chunk_count": 1}])
    b = _builder(manager, tmp_path, tmp_path / "rag", monkeypatch)
    monkeypatch.setenv("N2N_KNOWLEDGE_TOPIC_ONLY", "1")
    inv = b.build("as65007-7.7.7.7")
    e = inv["knowledge"][0]
    assert "Automate Your Network" not in e["description"]   # title suppressed
    assert "install-guide" in e["description"]               # tag/topic kept
    assert e["doc_count"] == 1


# ---- T010a (SC-005) -------------------------------------------------------

def test_card_size_independent_of_corpus_size(manager, tmp_path, monkeypatch):
    small = [{"collection": "documents", "title": "Automate Your Network",
              "doc_type": "install-guide", "page_count": 212, "chunk_count": 389}]
    # 10x the documents/pages/chunks in the SAME collection
    big = [{"collection": "documents", "title": "Automate Your Network",
            "doc_type": "install-guide", "page_count": 2120, "chunk_count": 3890}
           for _ in range(10)]
    e_small = kn.build_entries(db_path=_make_rag_db(tmp_path / "s", small))
    e_big = kn.build_entries(db_path=_make_rag_db(tmp_path / "b", big))
    assert len(e_small) == len(e_big) == 1
    # entry byte size does not scale with corpus size (counts are ints; titles deduped)
    assert abs(len(json.dumps(e_big[0])) - len(json.dumps(e_small[0]))) < 40
