"""Consensus-client failure semantics; HTTP fixtures do not qualify quorum."""
import base64
import json
import uuid

import httpx
import pytest

from bgp.federation.certs import create_self_signed
from bgp.federation.ha.config import HAError
from bgp.federation.ha.store import EtcdStore


def client(tmp_path, handler):
    cert, key = create_self_signed('etcd-fixture')
    (tmp_path / 'cert.pem').write_text(cert)
    (tmp_path / 'key.pem').write_text(key)
    store = EtcdStore(['https://voter-a.test:2379', 'https://voter-b.test:2379'],
                      prefix=f'/netclaw/ha/{uuid.uuid4()}/{uuid.uuid4()}/',
                      ca=tmp_path / 'cert.pem', certificate=tmp_path / 'cert.pem',
                      private_key=tmp_path / 'key.pem', username='border-a',
                      password='test-only-long-password')
    store.client.close()
    store.client = httpx.Client(transport=httpx.MockTransport(handler))
    store._token = 'fixture-token'
    return store


def test_write_timeout_is_single_attempt_even_with_other_endpoints(tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        raise httpx.ReadTimeout('private exception must not escape')
    store = client(tmp_path, handler)
    with pytest.raises(HAError, match='commit_unknown'):
        store.txn([('leader', 'revision', 0)], [('leader', {'node': 'a'}, '123')])
    assert len(requests) == 1
    store.close()


def test_reads_can_try_surviving_endpoint_and_are_linearizable(tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        assert json.loads(request.content)['serializable'] is False
        if len(requests) == 1:
            raise httpx.ConnectError('offline')
        return httpx.Response(200, json={'header': {'revision': '9'}, 'kvs': []})
    store = client(tmp_path, handler)
    assert store.read('leader') == (None, 0)
    assert len(requests) == 2
    store.close()


def test_cas_compares_value_and_revision_and_only_leader_has_lease(tmp_path):
    captured = []
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={'succeeded': True, 'header': {'revision': '11'}})
    store = client(tmp_path, handler)
    assert store.txn([('leader', 'revision', 8), ('leader', 'value', {'node': 'a'})],
                     [('claims/one', {'spent': True}, None)]) == (True, 11)
    assert [c['target'] for c in captured[0]['compare']] == ['MOD', 'VALUE']
    assert 'lease' not in captured[0]['success'][0]['request_put']
    with pytest.raises(HAError, match='durable_record_cannot_expire'):
        store.txn([], [('claims/two', {'spent': True}, '123')])
    assert len(captured) == 1
    store.close()


@pytest.mark.parametrize('key', ['../leader', '/leader', 'state//one', 'a' * 300, 'member?secret'])
def test_unsafe_key_never_reaches_consensus(tmp_path, key):
    store = client(tmp_path, lambda request: pytest.fail('invalid key reached HTTP'))
    with pytest.raises(HAError):
        store.read(key)
    store.close()


def test_malformed_response_is_not_empty_state(tmp_path):
    store = client(tmp_path, lambda request: httpx.Response(200, json={
        'kvs': [{'value': 'not base64', 'mod_revision': '2'}]}))
    with pytest.raises(HAError, match='invalid_etcd_response'):
        store.read('leader')
    store.close()


def test_duplicate_json_response_is_rejected(tmp_path):
    store = client(tmp_path, lambda request: httpx.Response(200, content=b'{"kvs":[],"kvs":[]}'))
    with pytest.raises(HAError, match='invalid_etcd_response'):
        store.read('leader')
    store.close()


def test_exact_record_decode(tmp_path):
    value = {'spent': True}
    store = client(tmp_path, lambda request: httpx.Response(200, json={'kvs': [{
        'value': base64.b64encode(json.dumps(value).encode()).decode(), 'mod_revision': '18'}]}))
    assert store.read('claims/one') == (value, 18)
    store.close()


@pytest.mark.parametrize('reply', [
    httpx.Response(503, content=b'unavailable'),
    httpx.Response(200, content=b'{'),
    httpx.Response(200, json={'succeeded': 'true', 'header': {'revision': '3'}}),
])
def test_ambiguous_mutation_acknowledgements_never_retry(tmp_path, reply):
    requests = []
    def handler(request):
        requests.append(request)
        return reply
    store = client(tmp_path, handler)
    with pytest.raises(HAError, match='commit_unknown'):
        store.txn([], [('claims/one', {'spent': True}, None)])
    assert len(requests) == 1
    store.close()


def test_read_http_unavailability_can_use_another_voter(tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(503) if len(requests) == 1 else httpx.Response(200, json={'kvs': []})
    store = client(tmp_path, handler)
    assert store.read('leader') == (None, 0)
    assert len(requests) == 2
    store.close()
