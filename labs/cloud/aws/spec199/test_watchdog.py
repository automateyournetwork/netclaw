import copy
import json
import unittest
import campaign as c
import lifecycle as life
import watchdog as w


class WatchdogTests(unittest.TestCase):
    def setUp(self):self.actions=w.stop_actions('123456789012','us-east-2','nc199-abcdef012345','2026-11-25T23:00:00Z')

    def journal(self):
        data={'instance':{'Instances':[{'InstanceId':'i-abcdef01234567890'}]},
              'stop-role':{'Role':{'Arn':'arn:aws:iam::123456789012:role/nc199-abcdef012345-stop'}}}
        return {k:{'state':'observed','response':v,'response_sha256':c.digest(v)} for k,v in data.items()}

    def test_trust_is_group_and_source_account(self):
        trust=json.loads(self.actions[1]['request']['AssumeRolePolicyDocument'])['Statement'][0]
        self.assertEqual(trust['Condition']['StringEquals']['aws:SourceAccount'],'123456789012')
        self.assertEqual(trust['Condition']['ArnEquals']['aws:SourceArn'],
                         'arn:aws:scheduler:us-east-2:123456789012:schedule-group/nc199-abcdef012345-stop')

    def test_role_only_stops_exact_instance(self):
        policy=json.loads(life.resolve(self.actions[2]['request'],self.journal())['PolicyDocument'])['Statement'][0]
        self.assertEqual(policy['Action'],['ec2:StopInstances'])
        self.assertEqual(policy['Resource'],['arn:aws:ec2:us-east-2:123456789012:instance/i-abcdef01234567890'])
        self.assertNotIn('*',json.dumps(policy))

    def test_pending_or_changed_dependency_refused(self):
        journal=self.journal();journal['instance']['state']='unknown'
        with self.assertRaises(ValueError):life.resolve(self.actions[3]['request'],journal)
        journal=self.journal();journal['instance']['response']['Instances'][0]['InstanceId']='i-foreign'
        with self.assertRaises(ValueError):life.resolve(self.actions[3]['request'],journal)

    def test_schedule_binding_no_delivery_claim(self):
        expected=life.resolve(self.actions[3]['request'],self.journal())
        self.assertFalse(w.verify_schedule(expected,expected,100)['future_delivery_proven'])
        for field,value in [('State','DISABLED'),('ScheduleExpression','rate(1 hour)'),('ActionAfterCompletion','NONE')]:
            observed=copy.deepcopy(expected);observed[field]=value
            with self.assertRaises(ValueError):w.verify_schedule(observed,expected,100)
        observed=copy.deepcopy(expected);observed['Target']['RoleArn']='foreign'
        with self.assertRaises(ValueError):w.verify_schedule(observed,expected,100)
        with self.assertRaisesRegex(ValueError,'expired'):
            w.verify_schedule(expected,expected,c.stamp('2026-11-25T23:00:00Z'))


if __name__=='__main__':unittest.main()
