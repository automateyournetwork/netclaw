import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import campaign as c
import lifecycle as life
from preflight import save
from test_campaign import packet, NOW


class LifecycleTests(unittest.TestCase):
    def record(self):
        return {'account':'123456789012','region':'us-east-2','run_id':'run','stage':1,
                'kind':'instance','id':'i-abcdef01234567890','create_request_sha256':'a'*64}

    def observed(self):
        return dict(self.record(),tags={'netclaw-spec':'199','netclaw-run':'run','netclaw-stage':'1'})

    def test_foreign_default_and_changed_ids_refused(self):
        for changes in ({'id':'i-00000000000000000'},{'account':'000000000000'},
                        {'default':True},{'baseline':True},{'tags':{'netclaw-spec':'198'}}):
            with self.assertRaises(ValueError):
                life.ownership(self.record(),dict(self.observed(),**changes),'123456789012','us-east-2','run',1)
        self.assertTrue(life.ownership(self.record(),self.observed(),'123456789012','us-east-2','run',1))

    def test_export_bytes_are_verified_not_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();save(root/'state.json',{'state':'original'})
            raw=(root/'state.json').read_bytes()
            manifest={'schema':1,'quiescent':True,'resource_ids':['owned'],
                'files':[{'path':'state.json','size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}]}
            self.assertTrue(life.verify_export(root,manifest,['owned']))
            (root/'state.json').write_bytes(b'changed')
            with self.assertRaises(ValueError):life.verify_export(root,manifest,['owned'])
            with self.assertRaises(ValueError):life.verify_export(root,manifest,['foreign'])

    def test_export_symlink_and_escape_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();save(root/'actual',{})
            (root/'link').symlink_to(root/'actual')
            for name in ('../actual','/etc/passwd','link'):
                manifest={'schema':1,'quiescent':True,'resource_ids':['owned'],
                    'files':[{'path':name,'size':0,'sha256':'a'*64}]}
                with self.assertRaises(ValueError):life.verify_export(root,manifest,['owned'])

    def test_absence_requires_success_and_repeated_separated_observations(self):
        rows=[{'observed_at':n,'resources':{'i':{'query_succeeded':True,'absent':True}}} for n in (10,13)]
        self.assertTrue(life.verify_absence(rows,['i']))
        for altered in (rows[:1],[rows[0],dict(rows[1],observed_at=11)],
                        [rows[0],{'observed_at':13,'resources':{'i':{'query_succeeded':False,'absent':True}}}]):
            with self.assertRaises(ValueError):life.verify_absence(altered,['i'])

    def test_unknown_create_is_durable_and_never_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();state=c.new_campaign('123456789012')
            action={'name':'vpc','service':'ec2','operation':'create-vpc','region':'us-east-2','request':{'CidrBlock':'10.199.1.0/24'}}
            item=packet(state,actions={'vpc':c.digest(action)})
            c.reserve(state,item,NOW);save(root/'campaign.json',state)
            invoke=lambda *args,**kwargs: (_ for _ in ()).throw(TimeoutError('uncertain'))
            with patch.object(life,'datetime') as dt:
                dt.now.return_value.timestamp.return_value=NOW
                with self.assertRaises(TimeoutError):life.execute_once(root,item,action,'test',state['account'],invoke)
                with self.assertRaises(ValueError):life.execute_once(root,item,action,'test',state['account'],invoke)
            saved=c.read_private(root/'campaign.json')['reservations'][item['attempt_id']]
            self.assertEqual(saved['state'],'unknown');self.assertEqual(saved['actions']['vpc']['state'],'unknown')

    def test_unfrozen_action_and_generic_destruction_refused(self):
        state=c.new_campaign('123456789012');item=packet(state);c.reserve(state,item,NOW)
        action={'name':'vpc','service':'ec2','operation':'create-vpc','region':'us-east-2','request':{}}
        with self.assertRaisesRegex(ValueError,'not_frozen'):life.begin_action(state,item,action,NOW)
        destructive=dict(action,operation='delete-vpc')
        with self.assertRaisesRegex(ValueError,'verified_cleanup'):life.execute_once('/unused',item,destructive,'test',state['account'])

    def test_only_definite_free_plan_rejection_with_original_absence_can_close_unknown(self):
        state=c.new_campaign('123456789012');item=packet(state)
        action={'name':'instance','service':'ec2','operation':'run-instances','region':'us-east-2',
                'request':{'ClientToken':item['client_token']}}
        item['actions']={'instance':c.digest(action)};c.reserve(state,item,NOW)
        life.begin_action(state,item,action,NOW);life.finish_action(state,item,action,error='RuntimeError')
        rows=[{'observed_at':NOW+n,'query_succeeded':True,'client_token':item['client_token'],'instances':[]} for n in (1,4)]
        returned={'returncode':254,'stdout':'','stderr':'An error occurred (InvalidParameterCombination) when calling the RunInstances operation: The specified instance type is not eligible for Free Tier.'}
        for changed in (dict(returned,stderr='connection timed out'),dict(returned,returncode=255)):
            with self.assertRaises(ValueError):life.reconcile_free_plan_rejection(state,item,action,changed,rows)
        wrong=copy.deepcopy(rows);wrong[1]['client_token']='another'
        with self.assertRaises(ValueError):life.reconcile_free_plan_rejection(state,item,action,returned,wrong)
        life.reconcile_free_plan_rejection(state,item,action,returned,rows)
        self.assertEqual(state['reservations'][item['attempt_id']]['actions']['instance']['state'],'rejected')
        with self.assertRaises(ValueError):life.begin_action(state,item,action,NOW)


if __name__ == '__main__':unittest.main()
