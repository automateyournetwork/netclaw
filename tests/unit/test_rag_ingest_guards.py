"""RAG consent boundaries against actual server wiring and temporary storage."""
import importlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'mcp-servers/rag-mcp'))


@pytest.fixture(autouse=True)
def isolated_gait_audit(tmp_path, monkeypatch):
    """Keep real audit writes local even when gait-ai is installed on the host."""
    monkeypatch.chdir(tmp_path)
    try:
        from gait.repo import GaitRepo
    except ImportError:
        return
    repo = GaitRepo(tmp_path)
    repo.init()
    monkeypatch.setattr(GaitRepo, 'discover', staticmethod(lambda *args, **kwargs: repo))

@pytest.fixture(scope='module')
def server(tmp_path_factory):
    # Set before import: server startup must never inspect the operator's corpus.
    with pytest.MonkeyPatch.context() as patch:
        directory = tmp_path_factory.mktemp('rag-guards')
        patch.setenv('RAG_DATA_DIR', str(directory))
        module = importlib.import_module('rag_mcp_server')
        # Integration tests may already have imported the module during collection.
        # Keep these 2-dimensional fault fixtures out of their 64-dimensional corpus.
        for name, suffix in [('DATA_DIR', ''), ('DB_PATH', 'rag.db'), ('CHROMA_DIR', 'chroma'),
                             ('BM25_DIR', 'bm25'), ('SOURCES_DIR', 'sources'), ('INTAKE_DIR', 'intake')]:
            patch.setattr(module.config, name, directory / suffix)
        module.config.ensure_dirs()
        registry = module.Registry(module.config.DB_PATH)
        patch.setattr(module, 'registry', registry)
        patch.setattr(module, 'chroma', module.ChromaStore(module.config.CHROMA_DIR))
        patch.setattr(module, 'bm25', module.BM25Store(module.config.BM25_DIR))
        patch.setattr(module, 'store_lock', module.StoreLock(directory))
        yield module
        registry._conn.close()


@pytest.mark.parametrize('mime,body', [('text/html', b'<a href="/next">next</a>'), ('text/plain', b'guide')])
def test_invalid_linked_scope_never_ingests(server, monkeypatch, mime, body):
    monkeypatch.setattr(server, 'fetch', lambda *args, **kwargs: (body, mime))
    ingested = []
    monkeypatch.setattr(server, '_ingest_fetched', lambda *args: ingested.append(args) or server.success_response({}))
    response = server._do_ingest_url('https://docs.example/start', mode='ingest', include_linked=True, scope_token_value='invalid')
    assert response['error']['code'] == 'SCOPE_TOKEN_INVALID'
    assert ingested == []


def test_failed_chroma_count_is_not_an_empty_corpus(server, monkeypatch):
    def unavailable(*args):
        raise OSError('synthetic private storage details')
    monkeypatch.setattr(server.chroma, '_collection', unavailable)
    result = server._do_search('route evidence')
    assert result['error']['code'] == 'STORAGE_UNAVAILABLE'
    assert 'corpus_empty' not in str(result)
    assert 'private storage details' not in str(result)


def test_valid_scope_preserves_linked_ingestion(server, monkeypatch):
    body = b'<a href="/next">next</a>'
    monkeypatch.setattr(server, 'fetch', lambda *args, **kwargs: (body, 'text/html'))
    ingested = []
    monkeypatch.setattr(server, '_ingest_fetched', lambda *args: ingested.append(args[0]) or server.success_response({}))
    monkeypatch.setattr(server, 'gait_log', lambda *args: None)
    url = 'https://docs.example/start'
    preview = server._do_ingest_url(url)
    assert ingested == []
    response = server._do_ingest_url(url, mode='ingest', include_linked=True, scope_token_value=preview['data']['scope_token'])
    assert response['data']['ingested'] == 2
    assert ingested == [url, 'https://docs.example/next']


def test_startup_removes_interrupted_chunks_from_both_persistent_indexes(tmp_path):
    import os
    import subprocess
    code = '''
import config
config.ensure_dirs()
from storage.registry import Registry
from storage.chroma_store import ChromaStore
from storage.bm25_store import BM25Store
registry = Registry(config.DB_PATH)
doc = registry.new_document('document', 'Interrupted', 'fixture', 'other', 'hash', 'documents')
registry.set_status(doc, 'embedding')
chroma = ChromaStore(config.CHROMA_DIR)
chroma.add_chunks('documents', ['chunk1'], [[1.,0.]], ['interrupted route'], [{'document_id':doc}])
bm25 = BM25Store(config.BM25_DIR)
bm25.add('documents', [{'chunk_id':'chunk1','text':'interrupted route'}])
assert bm25.search('documents','interrupted',5)
import rag_mcp_server
assert not rag_mcp_server.chroma.get_document_chunks('documents',doc)
assert not BM25Store(config.BM25_DIR).search('documents','interrupted',5), 'orphaned BM25 entry survived startup'
'''
    env = {**os.environ, 'RAG_DATA_DIR':str(tmp_path), 'PYTHONPATH':str(Path(__file__).resolve().parents[2] / 'mcp-servers/rag-mcp')}
    result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_attachment_limits_before_decode_and_strict_validation(server, monkeypatch):
    import base64
    monkeypatch.setattr(server.config, 'MAX_DOC_MB', 4 / (1024 * 1024))
    assert server._do_ingest_base64('doc.txt', 'not base64')['error']['code'] == 'DOC_TOO_LARGE'
    assert server._do_ingest_base64('doc.txt', '!===')['error']['code'] == 'PARSE_FAILED'
    # Same encoded length as the maximum, but decoded data exceeds it.
    assert server._do_ingest_base64('doc.txt', base64.b64encode(b'12345').decode())['error']['code'] == 'DOC_TOO_LARGE'
    def forbidden(*args, **kwargs):
        raise AssertionError('Oversized input must be rejected before decoding')
    monkeypatch.setattr(server.base64, 'b64decode', forbidden)
    assert server._do_ingest_base64('doc.txt', 'a' * 12)['error']['code'] == 'DOC_TOO_LARGE'


def test_same_name_attachments_are_isolated_and_cleaned(server, monkeypatch):
    import base64
    import threading
    from concurrent.futures import ThreadPoolExecutor
    barrier = threading.Barrier(2)
    staged = []
    legacy = server.config.INTAKE_DIR / 'shared.txt'
    legacy.write_bytes(b'legacy')
    def ingest(path, *args, **kwargs):
        staged.append(Path(path))
        barrier.wait(timeout=5)
        return Path(path).read_bytes()
    monkeypatch.setattr(server, '_do_ingest', ingest)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda value: server._do_ingest_base64('../shared.txt', base64.b64encode(value).decode()), [b'one', b'two']))
    assert results == [b'one', b'two']
    assert len(set(staged)) == 2
    assert all(p.name == 'shared.txt' and not p.parent.exists() for p in staged)
    assert legacy.read_bytes() == b'legacy'


def test_attachment_staging_cleans_up_on_ingest_error(server, monkeypatch):
    paths = []
    def fail(path, *args, **kwargs):
        paths.append(Path(path))
        raise RuntimeError('synthetic ingest failure')
    monkeypatch.setattr(server, '_do_ingest', fail)
    with pytest.raises(RuntimeError):
        server._do_ingest_base64('doc.txt', 'eA==')
    assert not paths[0].parent.exists()
    assert server._do_ingest_base64('..', 'eA==')['error']['code'] == 'PARSE_FAILED'


@pytest.mark.parametrize('explicit_reindex', [False, True])
def test_failed_replacement_preserves_ready_document_and_source(server, monkeypatch, tmp_path, explicit_reindex):
    def index(doc_id, parsed, collection, doc_type, source):
        cid = doc_id + '_0'
        server.chroma.add_chunks(collection, [cid], [[1., 0.]], ['retained operational evidence'], [{'document_id': doc_id}])
        server.bm25.add(collection, [{'chunk_id': cid, 'text': 'retained operational evidence'}])
        return 1
    monkeypatch.setattr(server, '_index_parsed_document', index)
    monkeypatch.setattr(server, 'gait_log', lambda *args: None)
    path = tmp_path/'original.md';path.write_text('Original working guidance ' + str(tmp_path))
    title = 'Replacement regression ' + str(tmp_path)
    first = server._do_ingest(str(path), title=title)
    assert first['success'], first
    original_id = first['data']['document_id']
    prior = server.registry.get(original_id)
    retained = Path(prior['source_path']);contents = retained.read_bytes()
    def partial_failure(*args):
        index(*args)
        raise RuntimeError('synthetic embedding persistence failure')
    monkeypatch.setattr(server, '_index_parsed_document', partial_failure)
    path.write_text('Replacement guidance ' + str(tmp_path))
    if explicit_reindex:
        failed = server._do_reindex(original_id, confirmed=True)
    else:
        failed = server._do_ingest(str(path), title=title)
    assert failed['success'] is False
    assert server.registry.get(original_id)['ingest_status'] == 'ready'
    assert retained.read_bytes() == contents
    assert server.chroma.get_document_chunks(prior['collection'], original_id)
    failed_rows = [r for r in server.registry.list_documents() if r['title'] == title and r['id'] != original_id]
    assert len(failed_rows) == 1
    assert not server.chroma.get_document_chunks(prior['collection'], failed_rows[0]['id'])
    keyword_ids = server.bm25._load(prior['collection'])[0]
    assert original_id + '_0' in keyword_ids
    assert failed_rows[0]['id'] + '_0' not in keyword_ids
    monkeypatch.setattr(server, '_index_parsed_document', index)
    done = server._do_reindex(original_id, confirmed=True)
    assert done['success'] and done['data']['document_id'] != original_id
    assert server.registry.get(original_id) is None
    assert not retained.exists()
    assert Path(server.registry.get(done['data']['document_id'])['source_path']).read_bytes() == contents
