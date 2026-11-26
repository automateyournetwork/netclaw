import copy
import unittest
import campaign as c
import qualify


class QualifyTests(unittest.TestCase):
    def case(self):
        packet={'stage':1,'account':'123456789012','region':'us-east-2','run_id':'nc199-abcdef012345'}
        record=dict(packet,kind='instance',id='i-abcdef01234567890',create_request_sha256='a'*64)
        raw={'Placement':{'AvailabilityZone':'us-east-2a'},'PrivateIpAddress':'10.199.11.10','PublicIpAddress':'8.8.8.8',
             'MetadataOptions':{'HttpTokens':'required','HttpPutResponseHopLimit':1}}
        observed=dict(record,query_succeeded=True,observed_at=100,state='running',absent=False,raw=raw,raw_sha256=c.digest(raw),
            tags={'netclaw-spec':'199','netclaw-run':packet['run_id'],'netclaw-stage':'1'})
        return packet,record,observed

    def test_single_voter_is_never_labeled_ha(self):
        p,r,o=self.case();node=qualify.single_node(r,o,p,100)
        self.assertEqual(node['voter_count'],1);self.assertFalse(node['ha_qualified'])

    def test_policy_matches_kernel_resolved_interpreter(self):
        import sys
        sys.path.insert(0,str(qualify.REPO))
        from labs.ha.r09a_policy import build_policy
        policy=build_policy(qualify.single_policy('nne1'))
        self.assertEqual(policy['network_policies']['etcd']['binaries'],
                         [{'path':'/usr/local/bin/python3.12'}])
        self.assertEqual(len(policy['network_policies']['etcd']['endpoints']),1)

    def test_private_member_route_does_not_change_default_public_route(self):
        import sys
        sys.path.insert(0,str(qualify.REPO))
        from labs.ha.r09_prepare import member_endpoint
        node={'internal':'10.199.11.40','public':'8.8.8.8'}
        self.assertEqual(member_endpoint(node),'8.8.8.8')
        self.assertEqual(member_endpoint(node,True),'10.199.11.40')
        for address in ('127.0.0.1','169.254.169.254','8.8.8.8'):
            with self.assertRaises(SystemExit):member_endpoint(dict(node,internal=address),True)

    def test_foreign_stale_or_unconfined_host_refused(self):
        for changed in ('account','age','imds','role','address'):
            p,r,o=self.case()
            if changed=='account':o['account']='000000000000'
            if changed=='age':o['observed_at']=1
            if changed=='imds':o['raw']['MetadataOptions']['HttpTokens']='optional'
            if changed=='role':o['raw']['IamInstanceProfile']={'Arn':'foreign'}
            if changed=='address':o['raw']['PrivateIpAddress']='10.0.0.10'
            o['raw_sha256']=c.digest(o['raw'])
            with self.assertRaises(ValueError):qualify.single_node(r,o,p,100)

    def test_console_pin_rejects_missing_or_multiple_identity(self):
        console='boot\nNETCLAW_199_HOST_KEYS_BEGIN\nssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFixture host\nNETCLAW_199_HOST_KEYS_END\n'
        self.assertTrue(qualify.host_key(console,'8.8.8.8').startswith('8.8.8.8 ssh-ed25519 '))
        for text in ('',console+console,console.replace('ssh-ed25519','ssh-rsa')):
            with self.assertRaises(ValueError):qualify.host_key(text,'8.8.8.8')

    def test_linux_member_requires_verified_images_and_short_owned_path(self):
        images={name:{'Id':'sha256:'+'a'*64,'Architecture':'amd64','Os':'linux','rootfs_verified':True}
                for name in ('agent','relay','guard')}
        runtime={'guard':{},'relay_transport':'tcp','state_dir':'old'}
        bound=qualify.linux_member_runtime(runtime,'/home/ubuntu/nc199m-1234abcd',images)
        self.assertEqual(bound['relay_transport'],'unix');self.assertEqual(runtime['relay_transport'],'tcp')
        for field,value in [('Architecture','arm64'),('rootfs_verified',False),('Id','latest')]:
            changed=copy.deepcopy(images);changed['relay'][field]=value
            with self.assertRaises(ValueError):qualify.linux_member_runtime(runtime,'/home/ubuntu/nc199m-1234abcd',changed)
        with self.assertRaises(ValueError):qualify.linux_member_runtime(runtime,'/home/ubuntu/old-member',images)

    def test_placement_is_not_native_execution_acceptance(self):
        packet,record,_=self.case();packet['stage']=record['stage']=2
        metadata={'accountId':packet['account'],'instanceId':record['id'],'region':packet['region'],'architecture':'x86_64'}
        member={'binding':dict(installation_id='fresh',member_id='fresh',key_id='fresh',enrollment_generation='fresh')}
        result=qualify.member_placement(packet,record,metadata,member,'/home/ubuntu/nc199m-1234abcd')
        self.assertFalse(result['native_execution_verified']);self.assertTrue(result['shares_border_host'])
        for field in ('accountId','instanceId','region','architecture'):
            with self.assertRaises(ValueError):qualify.member_placement(packet,record,dict(metadata,**{field:'foreign'}),member,'/home/ubuntu/nc199m-1234abcd')

    def test_task_preflight_refuses_missing_dependency_relay_or_changed_schema(self):
        validation={'role_validate':'valid','closure_import':'ok','control_only':False}
        relay={'unix_relay_passed':True,'no_provider_or_device':True,'socket_mode':'0o600','response':{'effect':False}}
        mcp={'binding_validated':True,'mcp_initialized':True,'tool_schema_sha256':'a'*64,'tool_calls':0,'inference_calls':0}
        self.assertFalse(qualify.member_readiness(validation,relay,mcp,'a'*64)['native_execution_verified'])
        for target,field,value in [('validation','closure_import','failed:missing_dependency'),
                                   ('validation','control_only',True),('relay','unix_relay_passed',False),
                                   ('relay','socket_mode','0o666'),('mcp','mcp_initialized',False),('mcp','binding_validated',False),
                                   ('mcp','tool_schema_sha256','b'*64),('mcp','tool_calls',1),
                                   ('mcp','inference_calls',True)]:
            inputs=copy.deepcopy({'validation':validation,'relay':relay,'mcp':mcp})
            inputs[target][field]=value
            with self.assertRaises(ValueError):qualify.member_readiness(**inputs,expected_schema='a'*64)

    def test_mcp_manifest_preserves_closure_and_pins_resolved_interpreter(self):
        original={'schemaVersion':1,'files':{'pyvenv.cfg':'a'*64},'symlinks':{'bin/python':'/owned/native/python3.12'}}
        result=qualify.member_mcp_manifest(original,'b'*64)
        self.assertEqual(set(result),{'files','symlinks','executable_sha256'})
        self.assertEqual(result['executable_sha256'],'b'*64)
        self.assertEqual(result['files'],original['files']);self.assertEqual(result['symlinks'],original['symlinks'])
        result['files'].clear();self.assertTrue(original['files'])
        with self.assertRaises(ValueError):qualify.member_mcp_manifest({'files':{},'symlinks':{}},'b'*64)


if __name__=='__main__':unittest.main()
