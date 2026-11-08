"""Single quorum authority; durable application decisions are never leased."""
import asyncio
import copy
import re
import secrets
import uuid

from ..protected_contract import encode, sha256
from .config import HAError, check

MAX_DECISIONS = 8192


class Authority:
    def __init__(self, store, manifest, node_id, *, audit=None):
        self.store, self.manifest, self.node_id = store, manifest, node_id
        manifest.node(node_id)
        self.incarnation = str(uuid.uuid4())
        self.leader, self.epoch, self.lease_id = None, None, None
        self.audit = audit
        self._renewal_task = None

    def bootstrap(self, *, create=False):
        current, _ = self.store.read('control')
        if current is None:
            check(create, 'cluster_uninitialized', 503)
            initial = {
                'schema_version': 1, **self.manifest.audience,
                'manifest_sha256': sha256(self.manifest.value),
                'manifest_revision': self.manifest.revision,
                'active': True, 'membership_revision': 1, 'revocation_revision': 0,
                'decision_count': 0, 'operation_count': 0,
                'nodes': {node['node_id']: {'state': 'active', 'key_id': node['key_id']}
                          for node in self.manifest.nodes},
            }
            # Explicit first creation only. Existing state is never reset, even
            # when its counters or unresolved reservations look inconvenient.
            try:
                self.store.txn([('control', 'revision', 0), ('leader', 'revision', 0)],
                               [('control', initial, None)])
            except HAError as exc:
                if exc.code != 'commit_unknown':
                    raise
                observed, _ = self.store.read('control')
                check(observed == initial, 'commit_unknown', 503)
        return self._validate(self.store.read('control')[0])

    def _validate(self, control):
        check(isinstance(control, dict), 'cluster_uninitialized', 503)
        check(control.get('schema_version') == 1
              and {k: control.get(k) for k in ('cluster_id', 'generation')} == self.manifest.audience,
              'cluster_changed', 409)
        check(control.get('manifest_sha256') == sha256(self.manifest.value)
              and control.get('manifest_revision') == self.manifest.revision,
              'manifest_changed', 409)
        node = control.get('nodes', {}).get(self.node_id)
        check(isinstance(node, dict) and node.get('state') != 'retired', 'node_retired', 403)
        check(node.get('key_id') == self.manifest.node(self.node_id)['key_id'], 'node_key_changed', 403)
        check(type(control.get('active')) is bool, 'invalid_control_state', 503)
        check(type(control.get('decision_count')) is int and 0 <= control['decision_count'] <= MAX_DECISIONS,
              'invalid_control_state', 503)
        return control

    def snapshot(self, keys=()):
        check(len(keys) <= 12 and len(set(keys)) == len(keys)
              and not set(keys) & {'control', 'leader'}, 'invalid_snapshot')
        rows = self.store.read_many(['control', 'leader', *keys])
        self._validate(rows['control'][0])
        return rows

    def current(self):
        rows = self.snapshot()
        control, _ = rows['control']; leader, epoch = rows['leader']
        check(control['active'], 'recovery_fenced', 503)
        check(isinstance(leader, dict) and leader.get('generation') == self.manifest.generation,
              'authority_unavailable', 503)
        node = control['nodes'].get(leader.get('node_id'))
        check(node and node.get('state') == 'active', 'authority_unavailable', 503)
        return leader, epoch

    def campaign(self):
        rows = self.snapshot()
        control, revision = rows['control']; current, epoch = rows['leader']
        check(control['active'], 'recovery_fenced', 503)
        check(control['nodes'][self.node_id]['state'] == 'active', 'node_drained', 403)
        if current is not None:
            if current == self.leader and epoch == self.epoch:
                return self.renew()
            self.leader, self.epoch, self.lease_id = None, None, None
            return False
        lease = self.store.lease(self.manifest.limits['leader_lease_s'])
        candidate = {'node_id': self.node_id, 'incarnation': self.incarnation,
                     'generation': self.manifest.generation, 'election_nonce': secrets.token_hex(32)}
        try:
            committed, epoch = self.store.txn([('control', 'revision', revision), ('leader', 'revision', 0)],
                                             [('leader', candidate, lease)])
        except HAError as exc:
            if exc.code != 'commit_unknown':
                raise
            observed, epoch = self.store.read('leader')
            check(observed == candidate, 'commit_unknown', 503)
            committed = True
        if committed:
            self.leader, self.epoch, self.lease_id = candidate, epoch, lease
        return committed

    def renew(self):
        if self.leader is None or self.lease_id is None:
            return False
        rows = self.snapshot()
        control, _ = rows['control']; current, epoch = rows['leader']
        if (not control['active'] or control['nodes'][self.node_id]['state'] != 'active'
                or current != self.leader or epoch != self.epoch):
            self.leader, self.epoch, self.lease_id = None, None, None
            return False
        self.store.keepalive(self.lease_id)
        return True

    def mutate(self, action, keys, transition):
        """One linearized decision, with retries only after a definite CAS miss.

        transition receives a private snapshot and returns (writes, public result).
        It must be pure: no model, tool, external effect or local authority write.
        Exact decision readback can reconcile an ambiguous commit; it cannot issue
        another mutation or renew a member's expired admission challenge.
        """
        check(isinstance(action, str) and re.fullmatch(r'[a-z][a-z0-9_.-]{0,79}', action), 'invalid_action')
        check(self.leader is not None, 'not_leader', 409)
        leader, epoch = copy.deepcopy(self.leader), self.epoch
        decision_id = str(uuid.uuid4())
        decision_key = 'decisions/' + decision_id
        for _ in range(4):
            rows = self.snapshot(keys)
            control, control_revision = rows['control']
            current, current_epoch = rows['leader']
            check(current == leader and current_epoch == epoch, 'stale_authority', 409)
            check(control['active'], 'recovery_fenced', 503)
            check(control['nodes'][self.node_id]['state'] == 'active', 'node_drained', 403)
            check(control['decision_count'] < MAX_DECISIONS, 'state_capacity', 503)
            writes, result = transition(copy.deepcopy(rows))
            check(isinstance(writes, list) and 1 <= len(writes) <= 12, 'transaction_capacity')
            seen, new_control = set(), copy.deepcopy(control)
            for key, value, lease in writes:
                check(key not in seen and key != 'leader' and not key.startswith('decisions/'), 'invalid_authority_write')
                check(key == 'control' or key in keys, 'unobserved_authority_write')
                check(lease is None, 'durable_record_cannot_expire')
                seen.add(key)
                if key == 'control':
                    new_control = copy.deepcopy(value)
            check({k: new_control.get(k) for k in ('schema_version', 'cluster_id', 'generation',
                                                   'manifest_sha256', 'manifest_revision')}
                  == {k: control[k] for k in ('schema_version', 'cluster_id', 'generation',
                                              'manifest_sha256', 'manifest_revision')}, 'identity_mutation_refused')
            new_control['decision_count'] = control['decision_count'] + 1
            writes = [(key, value, lease) for key, value, lease in writes if key != 'control']
            writes.append(('control', new_control, None))
            check(len(encode(result)) <= 64 * 1024, 'result_capacity')
            decision = {'decision_id': decision_id, 'action': action, 'leader': leader, 'epoch': epoch,
                        'writes_sha256': sha256([[key, value] for key, value, _ in writes]),
                        'result_sha256': sha256(result)}
            comparisons = [('control', 'revision', control_revision), ('leader', 'value', leader),
                           ('leader', 'revision', epoch), (decision_key, 'revision', 0)]
            comparisons.extend((key, 'revision', rows[key][1]) for key in keys)
            try:
                committed, revision = self.store.txn(comparisons, writes + [(decision_key, decision, None)])
            except HAError as exc:
                if exc.code != 'commit_unknown':
                    raise
                try:
                    observed, revision = self.store.read(decision_key)
                except HAError:
                    raise HAError('commit_unknown', 503) from None
                check(observed == decision, 'commit_unknown', 503)
                committed = True
            if committed:
                if self.audit:
                    # Failure cannot undo the committed claim; propagate as an
                    # unknown audit outcome, never a safe-to-retry refusal.
                    try:
                        self.audit(action, revision, decision)
                    except Exception:
                        raise HAError('audit_outcome_unknown', 503) from None
                return result, revision
        raise HAError('state_contention', 409)

    async def start_renewal(self):
        check(self._renewal_task is None, 'renewal_already_started', 409)
        async def worker():
            while True:
                try:
                    if self.leader is None:
                        await asyncio.to_thread(self.campaign)
                    else:
                        await asyncio.to_thread(self.renew)
                except HAError:
                    # Retain uncertainty. Only a future quorum observation can
                    # establish current authority; a loop tick never grants it.
                    pass
                await asyncio.sleep(self.manifest.limits['renewal_s'])
        self._renewal_task = asyncio.create_task(worker())

    async def stop_renewal(self):
        if self._renewal_task:
            task, self._renewal_task = self._renewal_task, None
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
