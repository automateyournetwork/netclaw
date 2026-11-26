import copy
from datetime import datetime, timezone
import multiprocessing
from pathlib import Path
import tempfile
import unittest
import uuid
import campaign as c
from preflight import save

NOW = datetime(2026, 11, 25, 18, tzinfo=timezone.utc).timestamp()


def packet(state, **changes):
    result = {'schema': 1, 'campaign_id': state['campaign_id'], 'account': state['account'],
        'stage': 1, 'source_sha': 'a'*40, 'region': 'us-east-2', 'attempt_id': str(uuid.uuid4()),
        'client_token': uuid.uuid4().hex, 'created_at': '2026-11-25T18:00:00Z',
        'deadline': '2026-11-25T20:00:00Z', 'costs': {'aws': '10', 'external': '1'},
        'resources': [{'kind': 'instance', 'name': 'border'}]}
    result.update(changes); return result


def concurrent_reserve(root, item, queue):
    try: c.transaction(root, lambda state: c.reserve(state, item, NOW)); queue.put('ok')
    except ValueError as e: queue.put(str(e))


class CampaignTests(unittest.TestCase):
    def setUp(self): self.state = c.new_campaign('123456789012')

    def test_order_and_lease(self):
        for item in [packet(self.state, stage=5), packet(self.state, deadline='2026-11-25T18:00:00Z'),
                     packet(self.state, deadline='2026-11-26T00:00:01Z')]:
            with self.assertRaises(ValueError): c.reserve(self.state, item, NOW)
        self.assertFalse(self.state['reservations'])

    def test_budget_reserve_and_pause(self):
        with self.assertRaisesRegex(ValueError, 'pause'): c.reserve(self.state, packet(self.state, costs={'aws': '76', 'external': '0'}), NOW)
        with self.assertRaisesRegex(ValueError, 'external_ceiling'): c.reserve(self.state, packet(self.state, costs={'aws': '1', 'external': '10'}), NOW)
        c.reserve(self.state, packet(self.state, costs={'aws': '75', 'external': '0'}), NOW)
        with self.assertRaisesRegex(ValueError, 'pause'): c.reserve(self.state, packet(self.state), NOW)

    def test_invalid_money(self):
        for value in ('NaN', '-1', 'Infinity', True, 0.1):
            with self.assertRaises(ValueError): c.money(value)

    def test_duplicate_attempt_and_token_not_reusable(self):
        item = packet(self.state); c.reserve(self.state, item, NOW)
        with self.assertRaisesRegex(ValueError, 'consumed'): c.reserve(self.state, item, NOW)
        with self.assertRaisesRegex(ValueError, 'token_consumed'): c.reserve(self.state, packet(self.state, client_token=item['client_token']), NOW)

    def test_unknown_holds_full_cost_and_cannot_resend(self):
        item = packet(self.state); c.reserve(self.state, item, NOW); c.mark_sent(self.state, item, NOW)
        c.mark_unknown(self.state, item['attempt_id'])
        with self.assertRaises(ValueError): c.mark_sent(self.state, item, NOW)
        with self.assertRaisesRegex(ValueError, 'retained'): c.settle(self.state, item['attempt_id'], {'aws':'0','external':'0'}, {})
        self.assertEqual(c.totals(self.state)['aws']['held'], 10)

    def test_request_change_and_account_substitution_refused(self):
        item = packet(self.state); c.reserve(self.state, item, NOW)
        changed = dict(item, region='us-west-2')
        with self.assertRaises(ValueError): c.mark_sent(self.state, changed, NOW)
        with self.assertRaises(ValueError): c.reserve(self.state, packet(self.state, account='000000000000'), NOW)

    def test_accept_requires_retirement_and_receipt(self):
        item = packet(self.state); c.reserve(self.state, item, NOW)
        receipt = {'stage': 1, 'accepted': True, 'sha256': 'b'*64}
        with self.assertRaises(ValueError): c.accept(self.state, 1, receipt)
        c.settle(self.state, item['attempt_id'], {'aws':'1','external':'0.1'},
                 {'evidence_sha256':'c'*64,'no_open_resources':True,'no_uncertain_work':True})
        c.accept(self.state, 1, receipt)
        next_item = packet(self.state, stage=2, predecessor_sha256='b'*64)
        c.reserve(self.state, next_item, NOW)
        self.assertEqual(self.state['accepted_stage'], 1)

    def test_failed_transaction_is_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); save(root/'campaign.json', self.state)
            before = (root/'campaign.json').read_bytes()
            def bad(state): state['spent']['aws']='99'; raise ValueError('fail')
            with self.assertRaises(ValueError): c.transaction(root,bad)
            self.assertEqual((root/'campaign.json').read_bytes(),before)

    def test_concurrent_reservations_cannot_overdraw(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); save(root/'campaign.json', self.state)
            ctx=multiprocessing.get_context('fork');queue=ctx.Queue()
            items=[packet(self.state,costs={'aws':'40','external':'0'}) for _ in range(2)]
            processes=[ctx.Process(target=concurrent_reserve,args=(root,item,queue)) for item in items]
            for process in processes:process.start()
            for process in processes:process.join(10);self.assertEqual(process.exitcode,0)
            results=[queue.get(timeout=2) for _ in processes]
            self.assertEqual(results.count('ok'),1)
            state=c.read_private(root/'campaign.json')
            self.assertEqual(c.totals(state)['aws']['protected_total'],45)


if __name__ == '__main__': unittest.main()
