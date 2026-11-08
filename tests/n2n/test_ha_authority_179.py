"""State-machine tests; real quorum qualification is a separate integration gate."""
import copy
import threading

import pytest

from bgp.federation.ha.config import HAError, Manifest
from bgp.federation.ha.authority import Authority
from test_ha_contract_179 import manifest_fixture


class MemoryStore:
    def __init__(self):
        self.rows, self.revision, self.lock = {}, 0, threading.RLock()
        self.available, self.lose_reply = True, False
        self.mutations = 0

    def read(self, key):
        if not self.available:
            raise HAError('no_quorum', 503)
        with self.lock:
            return copy.deepcopy(self.rows.get(key, (None, 0)))

    def read_many(self, keys):
        with self.lock:
            return {key: self.read(key) for key in keys}

    def txn(self, comparisons, writes):
        if not self.available:
            raise HAError('commit_unknown', 503)
        with self.lock:
            self.mutations += 1
            for key, kind, expected in comparisons:
                value, revision = self.rows.get(key, (None, 0))
                if (revision if kind == 'revision' else value) != expected:
                    return False, max(self.revision, 1)
            self.revision += 1
            for key, value, lease in writes:
                self.rows[key] = (copy.deepcopy(value), self.revision)
            if self.lose_reply:
                self.lose_reply = False
                raise HAError('commit_unknown', 503)
            return True, self.revision

    def lease(self, ttl):
        return '123'

    def keepalive(self, lease):
        if not self.available:
            raise HAError('commit_unknown', 503)

    def revoke_lease(self, lease):
        with self.lock:
            self.rows.pop('leader', None)


def cluster():
    value, _, _ = manifest_fixture()
    manifest = Manifest(value)
    store = MemoryStore()
    nodes = [Authority(store, manifest, node['node_id']) for node in manifest.nodes]
    nodes[0].bootstrap(create=True)
    return store, nodes


def add_claim(rows):
    if rows['claims/one'][0] is not None:
        raise HAError('admission_spent', 409)
    return [('claims/one', {'spent': True}, None)], {'admitted': True}


def test_one_authority_and_durable_decision():
    store, nodes = cluster()
    assert nodes[0].campaign()
    assert not nodes[1].campaign()
    answer, revision = nodes[0].mutate('admit', ['claims/one'], add_claim)
    assert answer == {'admitted': True}
    assert store.read('claims/one')[1] == revision
    with pytest.raises(HAError, match='not_leader'):
        nodes[1].mutate('admit', ['claims/one'], add_claim)


def test_stale_authority_fenced_even_without_observing_new_epoch():
    store, nodes = cluster()
    nodes[0].campaign()
    old_epoch = nodes[0].epoch
    store.revoke_lease('123')
    assert nodes[1].campaign()
    assert nodes[1].epoch > old_epoch
    with pytest.raises(HAError, match='stale_authority'):
        nodes[0].mutate('admit', ['claims/one'], add_claim)
    assert store.read('claims/one') == (None, 0)


def test_quorum_loss_never_changes_claim_and_renewal_is_not_permission():
    store, nodes = cluster()
    nodes[0].campaign()
    store.available = False
    with pytest.raises(HAError, match='no_quorum'):
        nodes[0].mutate('admit', ['claims/one'], add_claim)
    store.available = True
    assert store.read('claims/one') == (None, 0)
    assert nodes[0].renew()
    assert store.read('claims/one') == (None, 0)


def test_committed_lost_reply_reconciles_exact_decision_without_second_mutation():
    store, nodes = cluster()
    nodes[0].campaign()
    before = store.mutations
    store.lose_reply = True
    answer, revision = nodes[0].mutate('admit', ['claims/one'], add_claim)
    assert answer == {'admitted': True}
    assert store.mutations == before + 1
    assert store.read('claims/one')[1] == revision
    with pytest.raises(HAError, match='admission_spent'):
        nodes[0].mutate('admit', ['claims/one'], add_claim)


def test_retired_node_and_fenced_restore_cannot_campaign():
    store, nodes = cluster()
    control, revision = store.read('control')
    control['nodes'][nodes[0].node_id]['state'] = 'retired'
    store.txn([('control', 'revision', revision)], [('control', control, None)])
    with pytest.raises(HAError, match='node_retired'):
        nodes[0].campaign()
    control, revision = store.read('control')
    control['active'] = False
    store.txn([('control', 'revision', revision)], [('control', control, None)])
    with pytest.raises(HAError, match='recovery_fenced'):
        nodes[1].campaign()


def test_bootstrap_is_explicit_and_never_resets_consumed_state():
    store, nodes = cluster()
    nodes[0].campaign()
    nodes[0].mutate('admit', ['claims/one'], add_claim)
    nodes[1].bootstrap(create=True)
    assert store.read('claims/one')[0] == {'spent': True}
    empty = Authority(MemoryStore(), nodes[0].manifest, nodes[0].node_id)
    with pytest.raises(HAError, match='cluster_uninitialized'):
        empty.bootstrap()
