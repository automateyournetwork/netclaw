import asyncio
import pytest
from bgp.federation import chroma_store_bridge as bridge
from bgp.federation.replication import local_replica_identity
from test_replication_lifecycle import _service, _federate, _page
from conftest import _await_terminal


@pytest.mark.parametrize('failure', ['repeat-start', 'promotion', 'registry', 'duplicate', 'store-busy'])
def test_failed_update_preserves_prior_replica(manager, monkeypatch, tmp_path, failure):
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)
    cid = 'knowledge:documents'
    async def manifest(*args):
        return {'embedding_model': 'BAAI/bge-small-en-v1.5', 'chunk_count': 1}
    async def batch(*args):
        return _page(0, ['old'], [[0.1, 0.1]], ['retained'], 'old-document')
    svc.invoker.fetch_replicate_manifest = manifest
    svc.invoker.fetch_replicate_batch = batch
    async def run():
        first = svc.replication.start(peer, cid)
        assert (await _await_terminal(svc, first))['state'] == 'completed'
        identity = local_replica_identity(peer, cid)
        before = bridge.registry().list_documents()
        if failure == 'repeat-start':
            async def broken(*args):
                raise RuntimeError('fixture interrupted transfer')
            svc.invoker.fetch_replicate_batch = broken
            second = svc.replication.start(peer, cid)
        elif failure == 'promotion':
            def broken(*args, **kwargs):
                raise RuntimeError('fixture promotion failed')
            monkeypatch.setattr(bridge._chroma_module().ChromaStore, 'promote_staging', broken)
            second = svc.replication.resync(peer, cid)
        elif failure == 'registry':
            def broken(*args, **kwargs):
                raise RuntimeError('fixture registry publication failed')
            monkeypatch.setattr(bridge._registry_module().Registry, 'publish_replica', broken)
            second = svc.replication.resync(peer, cid)
        elif failure == 'store-busy':
            from contextlib import contextmanager
            @contextmanager
            def busy():
                raise RuntimeError('fixture shared RAG store busy')
                yield
            monkeypatch.setattr(bridge, 'publication_lock', busy)
            second = svc.replication.resync(peer, cid)
        else:
            async def duplicate_manifest(*args):
                return {'embedding_model': 'BAAI/bge-small-en-v1.5', 'chunk_count': 2}
            svc.invoker.fetch_replicate_manifest = duplicate_manifest
            second = svc.replication.resync(peer, cid)
        assert (await _await_terminal(svc, second))['state'] == 'failed'
        assert bridge.chroma_store().get_chunks_page(identity, 0, 10)['texts'] == ['retained']
        assert bridge.registry().list_documents() == before
        assert not any('__staging_' in name for name in bridge.chroma_store().collection_names())
    asyncio.run(run())
