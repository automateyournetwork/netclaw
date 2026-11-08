"""Quorum-gated NCFED node retirement and serialized etcd voter changes.

Etcd membership is private consensus administration, never an NCFED member API.
Unknown membership requests remain pending until actual membership proves their
outcome. A timer or repeated command cannot turn an unknown request into a retry.
"""
import copy
import re
import uuid

from .. import protected_contract as c
from .config import HAError, check, endpoint


class Lifecycle:
    def __init__(self, authority):
        self.authority = authority

    def _transition(self, node_id, destination):
        self.authority.manifest.node(node_id)
        def transition(rows):
            control = rows['control'][0]
            node = control['nodes'][node_id]
            check(node['state'] != 'retired', 'node_retired', 403)
            check(destination != 'retired' or node['state'] == 'drained', 'drain_required', 409)
            if destination in ('drained', 'retired'):
                check(any(k != node_id and v['state'] == 'active' for k, v in control['nodes'].items()),
                      'last_active_border', 409)
            changed = node['state'] != destination
            node['state'] = destination
            control['membership_revision'] += int(changed)
            if destination == 'retired':
                control['revocation_revision'] += 1
            result = {'node_id': node_id, 'state': destination,
                      'membership_revision': control['membership_revision'],
                      'revocation_revision': control['revocation_revision']}
            return [('control', control, None)], result
        return self.authority.mutate('node_' + destination, [], transition)[0]

    def drain(self, node_id):
        # Caller closes channels only after this returns. A self-drain makes all
        # subsequent authority mutations fail even while the old lease exists.
        return self._transition(node_id, 'drained')

    def retire(self, node_id):
        return self._transition(node_id, 'retired')

    def resume(self, node_id):
        # Resume is only a reversible drain. Retirement needs a newly signed
        # generation with fresh node/install/key IDs through fenced recovery.
        return self._transition(node_id, 'active')

    def status(self):
        rows = self.authority.snapshot(['lifecycle/voter-change'])
        control, revision = rows['control']
        leader, epoch = rows['leader']
        return {**self.authority.manifest.audience, 'active': control['active'],
                'capacity_frozen': control.get('recovery', {}).get('capacity_frozen', False),
                'membership_revision': control['membership_revision'],
                'revocation_revision': control['revocation_revision'], 'revision': revision,
                'nodes': copy.deepcopy(control['nodes']),
                'leader_node_id': leader.get('node_id') if leader else None, 'authority_epoch': epoch,
                'voter_change': rows['lifecycle/voter-change'][0]}


def validate_members(rows):
    check(isinstance(rows, list) and 2 <= len(rows) <= 4, 'unsafe_voter_inventory')
    seen, peers, normalized = set(), set(), []
    for row in rows:
        c.exact(row, 'id learner peer_urls')
        check(isinstance(row['id'], str) and re.fullmatch('[1-9][0-9]{0,19}', row['id'])
              and row['id'] not in seen and type(row['learner']) is bool, 'unsafe_voter_inventory')
        check(isinstance(row['peer_urls'], list) and len(row['peer_urls']) == 1, 'unsafe_voter_inventory')
        address = row['peer_urls'][0]; endpoint(address, 'https')
        check(address not in peers, 'unsafe_voter_inventory')
        seen.add(row['id']); peers.add(address)
        normalized.append(copy.deepcopy(row))
    voters = sum(not row['learner'] for row in normalized)
    check(2 <= voters <= 3 and len(normalized) - voters <= 1, 'unsafe_voter_inventory')
    return sorted(normalized, key=lambda row: int(row['id']))


class EtcdMembership:
    """Concrete private admin transport; its credentials are never exposed.

    The configured etcd cluster MUST retain strict-reconfig-check=true (default).
    Add always uses a learner. Promotion additionally requires etcd's own caught-up
    learner check. This class never uses --force-new-cluster or blind HTTP retries.
    """
    def __init__(self, admin_store):
        self.store = admin_store

    def members(self):
        result = self.store._request('/v3/cluster/member/list', {'linearizable': True}, read_only=True)
        try:
            rows = [{'id': str(row['ID']), 'learner': row.get('isLearner', False),
                     'peer_urls': row['peerURLs']} for row in result['members']]
            return validate_members(rows)
        except HAError:
            raise
        except Exception:
            raise HAError('unsafe_voter_inventory', 503) from None

    def change(self, action, target):
        if action == 'add_learner':
            body, path = {'peerURLs': [target], 'isLearner': True}, 'add'
        else:
            body, path = {'ID': target}, {'remove': 'remove', 'promote': 'promote'}[action]
        return self.store._request('/v3/cluster/member/' + path, body)


class VoterChanges:
    KEY = 'lifecycle/voter-change'

    def __init__(self, authority, membership):
        self.authority, self.membership = authority, membership

    @staticmethod
    def _plan(action, target, before):
        check(action in ('remove', 'add_learner', 'promote'), 'invalid_voter_action')
        voters = [r for r in before if not r['learner']]
        matching = [r for r in before if r['id'] == target]
        if action == 'add_learner':
            endpoint(target, 'https')
            check(len(before) < 4 and not any(r['learner'] for r in before)
                  and not any(target in r['peer_urls'] for r in before), 'unsafe_voter_change', 409)
        else:
            check(len(matching) == 1, 'unknown_voter', 404)
            if action == 'remove':
                check(matching[0]['learner'] or len(voters) == 3, 'unsafe_voter_change', 409)
            else:
                check(matching[0]['learner'] and len(voters) == 2, 'unsafe_voter_change', 409)

    def prepare(self, action, target):
        before = validate_members(self.membership.members())
        self._plan(action, target, before)
        plan = {'change_id': str(uuid.uuid4()), 'action': action, 'target': target,
                'before': before, 'state': 'prepared'}
        def transition(rows):
            previous = rows[self.KEY][0]
            check(previous is None or previous.get('state') == 'completed', 'voter_change_in_progress', 409)
            return [(self.KEY, plan, None)], plan
        return self.authority.mutate('voter_prepare', [self.KEY], transition)[0]

    def apply(self, change_id):
        c.uuid_field(change_id)
        observed = validate_members(self.membership.members())
        def transition(rows):
            plan = rows[self.KEY][0]
            check(plan and plan['change_id'] == change_id, 'voter_change_not_found', 404)
            check(plan['state'] == 'prepared', 'voter_change_outcome_unknown', 409)
            check(plan['before'] == observed, 'voter_inventory_changed', 409)
            self._plan(plan['action'], plan['target'], observed)
            plan['state'] = 'submitted'
            return [(self.KEY, plan, None)], plan
        plan = self.authority.mutate('voter_submit', [self.KEY], transition)[0]
        # The durable submitted marker precedes the one external request. Any
        # failure, including a process crash here, requires read-only reconcile.
        self.membership.change(plan['action'], plan['target'])
        return self.reconcile(change_id)

    def reconcile(self, change_id):
        c.uuid_field(change_id)
        after = validate_members(self.membership.members())
        def transition(rows):
            plan = rows[self.KEY][0]
            check(plan and plan['change_id'] == change_id, 'voter_change_not_found', 404)
            if plan['state'] == 'completed':
                return [(self.KEY, plan, None)], plan
            check(plan['state'] == 'submitted', 'voter_change_not_submitted', 409)
            before, action, target = plan['before'], plan['action'], plan['target']
            if action == 'remove':
                expected = [r for r in before if r['id'] != target]
                complete = after == expected
            elif action == 'promote':
                expected = [dict(r, learner=False) if r['id'] == target else r for r in before]
                complete = after == expected
            else:
                added = [r for r in after if r['id'] not in {v['id'] for v in before}]
                complete = (len(added) == 1 and added[0]['learner'] and added[0]['peer_urls'] == [target]
                            and [r for r in after if r not in added] == before)
            check(complete, 'voter_change_outcome_unknown', 409)
            plan.update(state='completed', after=after)
            control = rows['control'][0]; control['membership_revision'] += 1
            return [(self.KEY, plan, None), ('control', control, None)], plan
        return self.authority.mutate('voter_reconcile', [self.KEY], transition)[0]
