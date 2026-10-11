"""Multiple HUD/editor/runtime processes must not sweep a live ingestion."""
import multiprocessing
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / 'mcp-servers/rag-mcp'))
from storage.coordination import StoreLock


def _hold(directory, started, finish):
    with StoreLock(directory).hold():
        started.set()
        assert finish.wait(10)


def test_second_process_cannot_recover_an_active_writer(tmp_path):
    context = multiprocessing.get_context('spawn')
    started, finish = context.Event(), context.Event()
    process = context.Process(target=_hold, args=(str(tmp_path), started, finish))
    process.start()
    try:
        assert started.wait(10)
        with StoreLock(tmp_path).hold(blocking=False) as acquired:
            assert not acquired
    finally:
        finish.set()
        process.join(10)
        if process.is_alive():
            process.terminate()
            process.join()
    assert process.exitcode == 0
    with StoreLock(tmp_path).hold(blocking=False) as acquired:
        assert acquired


def test_store_lock_is_reentrant_for_reindex_and_nested_ingest(tmp_path):
    lock = StoreLock(tmp_path)
    with lock.hold():
        with lock.hold(blocking=False) as acquired:
            assert acquired


def test_keyword_cache_observes_updates_from_another_client(tmp_path):
    from storage.bm25_store import BM25Store
    first, second = BM25Store(tmp_path), BM25Store(tmp_path)
    first.add('documents', [{'chunk_id': 'first', 'text': 'OSPF'}])
    assert first.search('documents', 'BGP', 3) == []
    second.add('documents', [{'chunk_id': 'second', 'text': 'BGP'}])
    assert first.search('documents', 'BGP', 3)[0]['chunk_id'] == 'second'
