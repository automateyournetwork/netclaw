import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import aws_api
import campaign as c
import lifecycle as life
from test_campaign import packet,NOW


class AWSAPITests(unittest.TestCase):
    def test_network_interface_uses_aws_tagset_field(self):
        import json
        raw={'NetworkInterfaces':[{'NetworkInterfaceId':'eni-abcdef01234567890','Status':'in-use',
             'TagSet':[{'Key':'netclaw-spec','Value':'199'}]}]}
        with tempfile.TemporaryDirectory() as directory:
            api=aws_api.ReadAPI('test','us-east-2',Path(directory).resolve(),
                lambda *a,**k:SimpleNamespace(returncode=0,stdout=json.dumps(raw),stderr=''))
            observed=api.observe({'kind':'eni','id':'eni-abcdef01234567890',
                'account':'123456789012','region':'us-east-2'},'123456789012')
            self.assertEqual(observed['tags'],{'netclaw-spec':'199'})
            self.assertEqual(observed['state'],'in-use')

    def test_reads_cannot_write_and_denial_never_means_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            api=aws_api.ReadAPI('test','us-east-2',Path(directory).resolve(),
                lambda *a,**k:SimpleNamespace(returncode=254,stdout='',stderr='An error occurred (UnauthorizedOperation) when calling DescribeInstances: denied'))
            with self.assertRaises(ValueError):api.read('ec2','terminate-instances')
            with self.assertRaises(aws_api.QueryError):api.observe({'kind':'instance','id':'i-abcdef01234567890',
                'account':'123456789012','region':'us-east-2'},'123456789012')

    def test_only_exact_not_found_is_absence(self):
        with tempfile.TemporaryDirectory() as directory:
            api=aws_api.ReadAPI('test','us-east-2',Path(directory).resolve(),
                lambda *a,**k:SimpleNamespace(returncode=254,stdout='',stderr='An error occurred (InvalidInstanceID.NotFound) when calling DescribeInstances: gone'))
            observation=api.observe({'kind':'instance','id':'i-abcdef01234567890',
                'account':'123456789012','region':'us-east-2'},'123456789012')
            self.assertTrue(observation['absent'])

    def test_custody_requires_original_creation_and_refuses_baseline(self):
        state=c.new_campaign('123456789012');p=packet(state,run_id='nc199-abcdef012345');c.reserve(state,p,NOW)
        response={'Vpc':{'VpcId':'vpc-abcdef01234567890'}}
        entry=state['reservations'][p['attempt_id']]
        entry['actions']={'vpc':{'state':'observed','response':response,'response_sha256':c.digest(response),'resolved_request_sha256':'a'*64}}
        obs={'id':response['Vpc']['VpcId'],'account':p['account'],'region':p['region'],'query_succeeded':True,'absent':False,
            'tags':{'netclaw-spec':'199','netclaw-run':p['run_id'],'netclaw-stage':'1'}}
        with self.assertRaises(ValueError):aws_api.record_creation(state,p,'vpc',obs,[obs['id']])
        with self.assertRaises(ValueError):aws_api.record_creation(state,p,'vpc',dict(obs,id='vpc-00000000000000000'),[])
        record=aws_api.record_creation(state,p,'vpc',obs,[])
        self.assertEqual(entry['custody'][obs['id']]['record_sha256'],c.digest(record))

    def test_unknown_launch_can_only_be_reconciled_to_original_token_and_placement(self):
        state=c.new_campaign('123456789012');p=packet(state,run_id='nc199-abcdef012345')
        req={'ClientToken':p['client_token'],'ImageId':'ami-abcdef01234567890','InstanceType':'m7i.large',
             'NetworkInterfaces':[{'SubnetId':'subnet-abcdef01234567890','Groups':['sg-abcdef01234567890']}],
             'Placement':{'AvailabilityZone':'us-east-2a'},'KeyName':p['run_id'],
             'TagSpecifications':[{'ResourceType':'instance','Tags':[{'Key':'netclaw-run','Value':p['run_id']}]}]}
        action={'name':'instance','service':'ec2','operation':'run-instances','region':'us-east-2','request':req}
        p['actions']={'instance':c.digest(action)};c.reserve(state,p,NOW);life.begin_action(state,p,action,NOW)
        life.finish_action(state,p,action,error='TimeoutError')
        observed={'Instances':[{'InstanceId':'i-abcdef01234567890','ClientToken':req['ClientToken'],
            'ImageId':req['ImageId'],'InstanceType':req['InstanceType'],'SubnetId':req['NetworkInterfaces'][0]['SubnetId'],
            'Placement':req['Placement'],'KeyName':req['KeyName'],'MetadataOptions':{'HttpTokens':'required'},
            'SecurityGroups':[{'GroupId':'sg-abcdef01234567890'}],'Tags':req['TagSpecifications'][0]['Tags']}]}
        for field,value in [('ClientToken','new-token'),('SubnetId','subnet-foreign'),('KeyName','foreign')]:
            altered=copy.deepcopy(observed);altered['Instances'][0][field]=value
            with self.assertRaises(ValueError):life.reconcile_created(state,p,action,altered,NOW,NOW)
        life.reconcile_created(state,p,action,observed,NOW,NOW)
        self.assertEqual(state['reservations'][p['attempt_id']]['state'],'sent')
        with self.assertRaises(ValueError):life.begin_action(state,p,action,NOW)


if __name__=='__main__':unittest.main()
