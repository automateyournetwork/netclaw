import base64
import copy
import unittest
import campaign as c
import lifecycle as life
import network


class NetworkTests(unittest.TestCase):
    def args(self):
        return dict(account='123456789012',region='us-east-2',zone='us-east-2a',prefix='nc199-abcdef012345',
            deadline='2026-11-25T23:00:00Z',client_token='frozen-attempt-00000001',ami='ami-abcdef01234567890',
            operator_cidr='8.8.8.8/32',public_key='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBogus fixture',instance_type='m7i-flex.large')

    def test_no_default_network_mutation_or_cloud_credentials(self):
        actions=network.first_border(**self.args())
        for action in actions:life.validate_action(action)
        vm=next(x['request'] for x in actions if x['name']=='instance')
        self.assertEqual(vm['MaxCount'],1)
        self.assertEqual(vm['MetadataOptions']['HttpTokens'],'required')
        self.assertNotIn('IamInstanceProfile',vm)
        self.assertEqual(vm['NetworkInterfaces'][0]['SubnetId'],{'$ref':'subnet.Subnet.SubnetId'})
        self.assertTrue(vm['BlockDeviceMappings'][0]['Ebs']['Encrypted'])
        boot=base64.b64decode(vm['UserData']).decode()
        self.assertIn('2026-11-25 23:00:00 UTC',boot)
        self.assertIn('ssh_host_ed25519_key.pub',boot)
        self.assertNotIn('ssh_host_ed25519_key\n',boot)

    def test_operator_and_region_are_exact(self):
        for changes in ({'operator_cidr':'0.0.0.0/0'},{'operator_cidr':'10.0.0.1/32'},
                        {'zone':'us-east-1a'},{'region':'us-east-1'},{'ami':'latest'}):
            with self.assertRaises(ValueError):network.first_border(**dict(self.args(),**changes))
        ingress=next(x['request'] for x in network.first_border(**self.args()) if x['name']=='ingress')
        self.assertEqual([x['FromPort'] for x in ingress['IpPermissions']],[22,443,7444])
        self.assertTrue(all(x['IpRanges'][0]['CidrIp']=='8.8.8.8/32' for x in ingress['IpPermissions']))

    def test_later_single_host_stage_tags_include_independent_stop(self):
        for stage in (2,3):
            actions=network.first_border(**self.args(),stage=stage)
            for name in ('stop-group','stop-role','instance'):
                request=next(a['request'] for a in actions if a['name']==name)
                groups=[request['Tags']] if 'Tags' in request else [s['Tags'] for s in request['TagSpecifications']]
                for tags in groups:self.assertEqual(next(t['Value'] for t in tags if t['Key']=='netclaw-stage'),str(stage))
        for stage in (True,0,4,5):
            with self.assertRaises(ValueError):network.first_border(**self.args(),stage=stage)

    def test_all_dependencies_precede_their_consumers(self):
        known=set()
        def refs(value):
            if isinstance(value,list):return sum((refs(x) for x in value),[])
            if isinstance(value,dict):
                if '$ref' in value:return [value['$ref'].split('.')[0]]
                return sum((refs(x) for x in value.values()),[])
            return []
        for action in network.first_border(**self.args()):
            self.assertTrue(set(refs(action['request']))<=known,action['name'])
            self.assertNotIn(action['name'],known);known.add(action['name'])


if __name__=='__main__':unittest.main()
