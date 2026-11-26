"""Offline lifecycle tests. No AWS permissions or live execution are implied."""
import copy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import aws_api
import campaign as c
import cleanup
import lifecycle as life
import regional_run as rr
import qualify
from preflight import save
from test_regional import ACCOUNT, NOW, choices, evidence, plan


def prepared(root,stage=4,predecessor=None,seconds=7200):
    state=c.new_campaign(ACCOUNT);state['accepted_stage']=stage-1 if predecessor is None else predecessor
    state['receipts'][str(state['accepted_stage'])]={'sha256':'a'*64};save(root/'prior.json',state)
    pricing={r['region']:{'observed_at':NOW,'raw':{'fixture':True},'raw_sha256':c.digest({'fixture':True}),
        'rates':{'ipv4_usd_hour':'0.005','gp3_usd_gb_month':'0.08','egress_usd_gb':'0.09','peering_usd_gb':'0.01'}} for r in evidence()}
    config=dict(stage=stage,account=ACCOUNT,predecessor_ledger=str(root/'prior.json'),lease_seconds=seconds,reports=evidence(),
        pricing=pricing,nodes=choices(),operator_cidr='8.8.8.8/32',source_sha='b'*40,baseline_ids=[],
        aws_reservation='4',external_reservation='1')
    def keygen(args,**kwargs):
        assert args[0]=='ssh-keygen'
        key=Path(args[-1]);save(key,{});key.with_name(key.name+'.pub').write_text('ssh-ed25519 AAAA fixture')
    with patch.object(rr,'datetime') as dt,patch.object(rr.subprocess,'run',side_effect=keygen):
        dt.now.return_value=datetime.fromtimestamp(NOW,timezone.utc);rr.plan(config,root/'new')
    return rr.load(root/'new')


class RegionalLifecycleTests(unittest.TestCase):
    def test_final_stage_requires_retired_predecessor_and_two_hour_deadline(self):
        with tempfile.TemporaryDirectory() as d:
            root,p,actions,g=prepared(Path(d).resolve(),stage=5)
            self.assertEqual(p['stage'],5);self.assertEqual(g['stage'],5)
            self.assertEqual(c.read_private(root/'campaign.json')['accepted_stage'],4)
            for a in actions:
                for tagset in a['request'].get('TagSpecifications',[]):
                    self.assertEqual({t['Key']:t['Value'] for t in tagset['Tags']}['netclaw-stage'],'5')
        for options in ({'predecessor':3},{'seconds':7201}):
            with tempfile.TemporaryDirectory() as d,self.assertRaises(ValueError):
                prepared(Path(d).resolve(),stage=5,**options)

    def test_private_frozen_plan_has_exact_global_and_regional_custody(self):
        with tempfile.TemporaryDirectory() as d:
            root,p,actions,g=prepared(Path(d).resolve())
            self.assertEqual(len(p['regions']),3);self.assertEqual(len(p['resource_origins']),33)
            self.assertEqual((root/'packet.json').stat().st_mode & 0o777,0o600)
            roles=[a['request']['RoleName'] for a in actions if a['operation']=='create-role']
            self.assertEqual(len(set(roles)),3)
            state=c.read_private(root/'campaign.json')
            self.assertEqual(state['accepted_stage'],3)
            self.assertEqual(state['reservations'][p['attempt_id']]['state'],'reserved')
            with patch.object(rr.run,'source_closure',return_value={}):
                with self.assertRaisesRegex(ValueError,'lifecycle_source_changed'):rr.load(root)
                rr.load(root,True)  # Cleanup remains possible after code updates.

    def test_region_escape_changed_action_and_unknown_are_not_resent(self):
        with tempfile.TemporaryDirectory() as d:
            root,p,actions,_=prepared(Path(d).resolve());a=actions[0]
            state=c.read_private(root/'campaign.json')
            with self.assertRaisesRegex(ValueError,'action_region_mismatch'):
                life.begin_action(state,p,dict(a,region='eu-west-1'),NOW)
            with self.assertRaisesRegex(ValueError,'action_not_frozen'):
                life.begin_action(state,p,dict(a,request={}),NOW)
            calls=[]
            def timeout(*args,**kwargs):calls.append(args);raise TimeoutError()
            with patch.object(life,'datetime') as dt:
                dt.now.return_value.timestamp.return_value=NOW
                with self.assertRaises(TimeoutError):life.execute_once(root,p,a,'fixture',ACCOUNT,timeout)
                with self.assertRaises(ValueError):life.execute_once(root,p,a,'fixture',ACCOUNT,timeout)
            self.assertEqual(len(calls),1)

    def test_region_creation_descriptor_cannot_be_substituted(self):
        with tempfile.TemporaryDirectory() as d:
            root,p,actions,_=prepared(Path(d).resolve());state=c.read_private(root/'campaign.json')
            desc=p['resource_origins']['nne2-vpc'];action=next(a for a in actions if a['name']==desc['action'])
            life.begin_action(state,p,action,NOW);life.finish_action(state,p,action,response={'Vpc':{'VpcId':'vpc-1234567890abcdef0'}})
            seed=rr.seed(p,desc,state['reservations'][p['attempt_id']]['actions'])
            obs=dict(seed,query_succeeded=True,absent=False,tags={'netclaw-spec':'199','netclaw-stage':'4','netclaw-run':p['run_id']})
            with self.assertRaisesRegex(ValueError,'frozen_creation_descriptor_required'):
                aws_api.record_creation(state,p,'vpc',obs,[],dict(desc,region=p['region']))
            record=aws_api.record_creation(state,p,'vpc',obs,[],desc)
            self.assertEqual(record['region'],'us-east-1');self.assertEqual(record['origin_action'],'nne2-vpc')

    def test_unknown_prefixed_instance_retains_guard_even_if_another_is_absent(self):
        with tempfile.TemporaryDirectory() as d:
            root,p,_,_=prepared(Path(d).resolve());state=c.read_private(root/'campaign.json');entry=state['reservations'][p['attempt_id']]
            record=dict(kind='vpc',id='vpc-1234567890abcdef0',account=ACCOUNT,region='us-east-1',run_id=p['run_id'],stage=4,create_request_sha256='a'*64)
            entry['custody']={record['id']:{'record':record,'record_sha256':c.digest(record)}}
            obs=dict(record,query_succeeded=True,observed_at=NOW,absent=False,tags={'netclaw-spec':'199','netclaw-run':p['run_id'],'netclaw-stage':'4'})
            entry['actions']={'nne2-instance':{'operation':'run-instances','state':'unknown'}}
            with self.assertRaisesRegex(ValueError,'unknown_compute_keeps_guard_and_network'):
                cleanup.begin(state,p,record,obs,{},'f'*64,NOW)

    def test_regional_route_cleanup_refuses_foreign_route_and_uses_owned_association(self):
        record=dict(kind='route-table',id='rtb-1234567890abcdef0',region='us-east-1',origin_action='nne2-route-table',
                    journal_namespace='nne2-',vpc_cidr='10.199.22.0/24')
        response={'AssociationId':'rtbassoc-1234567890abcdef0'}
        journal={'nne2-route-association':{'state':'observed','response':response,'response_sha256':c.digest(response)}}
        raw={'Routes':[{'DestinationCidrBlock':record['vpc_cidr'],'GatewayId':'local','Origin':'CreateRouteTable','State':'active'}]}
        obs=dict(query_succeeded=True,observed_at=NOW,absent=False,raw=raw,raw_sha256=c.digest(raw),
            associations=[{'RouteTableAssociationId':response['AssociationId'],'Main':False}])
        action=cleanup.deletion(record,obs,NOW,journal)
        self.assertEqual(action['request'],response)
        raw['Routes'].append({'DestinationCidrBlock':'10.0.0.0/8','GatewayId':'vgw-12345678','Origin':'CreateRoute','State':'active'})
        obs['raw_sha256']=c.digest(raw)
        with self.assertRaisesRegex(ValueError,'foreign_route_refused'):cleanup.deletion(record,obs,NOW,journal)

    def test_foreign_peering_endpoint_refused_before_accept_or_delete(self):
        p={'stage':4,'account':ACCOUNT,'run_id':'nc199-abcdef012345'}
        record=dict(kind='vpc-peering',id='pcx-1234567890abcdef0',account=ACCOUNT,region='us-east-2',peer_region='us-east-1',
            run_id=p['run_id'],stage=4,origin_action='peer-a-b',create_request_sha256='a'*64,
            requester_vpc='vpc-1234567890abcdef0',accepter_vpc='vpc-2234567890abcdef0')
        raw={'RequesterVpcInfo':dict(OwnerId=ACCOUNT,Region=record['region'],VpcId=record['requester_vpc']),
            'AccepterVpcInfo':dict(OwnerId=ACCOUNT,Region=record['peer_region'],VpcId=record['accepter_vpc']),
            'Status':{'Code':'pending-acceptance'}}
        obs=dict(record,query_succeeded=True,observed_at=NOW,absent=False,raw=raw,raw_sha256=c.digest(raw),
            tags={'netclaw-spec':'199','netclaw-run':p['run_id'],'netclaw-stage':'4'})
        self.assertEqual(rr.peer_guard(p,record,obs,NOW),'pending-acceptance')
        raw['AccepterVpcInfo']['OwnerId']='000000000000';obs['raw_sha256']=c.digest(raw)
        with self.assertRaisesRegex(ValueError,'peering_endpoint_changed'):rr.peer_guard(p,record,obs,NOW)
        with self.assertRaisesRegex(ValueError,'peering_endpoint_changed'):cleanup.deletion(record,obs,NOW)

    def test_host_placement_requires_actual_exact_three_regions(self):
        g=plan();p=dict(stage=4,account=ACCOUNT,run_id=g['run_id'],regions=[n['region'] for n in g['nodes']],regional_graph_sha256=c.digest(g))
        custody={};observations={}
        for i,n in enumerate(g['nodes']):
            identity='i-'+str(i+1)*17
            record=dict(kind='instance',id=identity,account=ACCOUNT,region=n['region'],run_id=p['run_id'],stage=4,
                origin_action=n['code']+'-instance',create_request_sha256='a'*64)
            custody[identity]={'record':record,'record_sha256':c.digest(record)}
            raw=dict(Placement={'AvailabilityZone':n['zone']},PrivateIpAddress=n['private_ip'],PublicIpAddress=f'8.8.8.{i+1}',
                ImageId=n['ami'],InstanceType=n['instance_type'],MetadataOptions={'HttpTokens':'required','HttpPutResponseHopLimit':1})
            observations[identity]=dict(record,raw=raw,raw_sha256=c.digest(raw),state='running',absent=False,observed_at=NOW,query_succeeded=True,
                tags={'netclaw-spec':'199','netclaw-run':p['run_id'],'netclaw-stage':'4'})
        self.assertEqual(len(qualify.regional_nodes(p,g,custody,observations,NOW)),3)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve()/'runtime'
            with patch('subprocess.run') as proc:
                prepared=qualify.prepare_regional(root,p,g,custody,observations,NOW)
                proc.assert_not_called()
            self.assertEqual(prepared['admission_ms'],9000);self.assertFalse(prepared['ha_qualified'])
            from bgp.federation.ha.config import verify_manifest
            from bgp.federation.protected_contract import key_id
            envelope=c.read_private(root/'identity/manifest.json');cert=(root/'identity/root.crt').read_text()
            manifest=verify_manifest(envelope,cert,expected_key_id=key_id(cert))
            self.assertEqual(manifest.limits['admission_ms'],9000)
            self.assertEqual({n['endpoints']['in2n']['host'] for n in manifest.nodes},set(g['hosts'].values()))
        observations[identity]['raw']['PrivateIpAddress']='10.199.99.10'
        observations[identity]['raw_sha256']=c.digest(observations[identity]['raw'])
        with self.assertRaisesRegex(ValueError,'regional_host_changed'):qualify.regional_nodes(p,g,custody,observations,NOW)

    def test_entire_regional_graph_captures_39_owned_resources_without_real_aws(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            root,p,actions,_=prepared(Path(d).resolve());resources={};calls=[];counter=0
            class FakeAPI:
                def __init__(self,profile,region,root):self.region=region
                def account(self):return ACCOUNT
                def observe(self,record,account):
                    self_scope=record['region']==self.region and account==ACCOUNT
                    if not self_scope:raise AssertionError('cross-region observation')
                    raw=copy.deepcopy(resources[record['id']])
                    return dict(record,query_succeeded=True,absent=False,observed_at=NOW,raw=raw,raw_sha256=c.digest(raw),
                        tags={'netclaw-spec':'199','netclaw-run':p['run_id'],'netclaw-stage':'4'},
                        name=raw.get('Name'),created_at='2026-11-25T18:30:00Z',group=raw.get('GroupName'))
            def invoke(argv,**kwargs):
                nonlocal counter
                self.assertEqual(argv[0],'aws');op=argv[2];region=argv[argv.index('--region')+1]
                request=json.loads(Path(argv[argv.index('--cli-input-json')+1][7:]).read_text());calls.append((op,region));counter+=1
                def rid(prefix):return prefix+'-'+format(counter,'017x')
                response={};raw={};identity=None
                simple={'create-vpc':('vpc','Vpc','VpcId'),'create-subnet':('subnet','Subnet','SubnetId'),
                    'create-internet-gateway':('igw','InternetGateway','InternetGatewayId'),
                    'create-route-table':('rtb','RouteTable','RouteTableId')}
                if op in simple:
                    prefix,collection,field=simple[op];identity=rid(prefix);raw={field:identity};response={collection:raw}
                    raw['Tags']=request['TagSpecifications'][0]['Tags']
                    if op=='create-route-table':raw.update(VpcId=request['VpcId'],Routes=[])
                elif op=='create-security-group':
                    identity=rid('sg');response={'GroupId':identity};raw={'IpPermissionsEgress':[{'IpProtocol':'-1','IpRanges':[{'CidrIp':'0.0.0.0/0'}],
                        'Ipv6Ranges':[],'PrefixListIds':[],'UserIdGroupPairs':[]}]}
                elif op=='import-key-pair':identity=rid('key');response={'KeyPairId':identity}
                elif op=='associate-route-table':response={'AssociationId':rid('rtbassoc')}
                elif op=='create-route':
                    route={k:v for k,v in request.items() if k!='RouteTableId'}
                    resources[request['RouteTableId']]['Routes'].append(dict(route,State='active',Origin='CreateRoute'))
                elif op=='run-instances':
                    identity=rid('i');vid,eid=rid('vol'),rid('eni')
                    raw={'InstanceId':identity,'BlockDeviceMappings':[{'Ebs':{'VolumeId':vid}}],
                         'NetworkInterfaces':[{'NetworkInterfaceId':eid}]};response={'Instances':[raw]}
                    resources[vid]={};resources[eid]={}
                elif op=='create-role':
                    identity='AROAFIXTURE'+str(counter);raw={'Name':request['RoleName']}
                    response={'Role':{'RoleId':identity,'Arn':'arn:aws:iam::'+ACCOUNT+':role/'+request['RoleName']}}
                elif op in ('create-schedule-group','create-schedule'):
                    kind='schedule-group' if op=='create-schedule-group' else 'schedule'
                    identity='arn:aws:scheduler:'+region+':'+ACCOUNT+':'+kind+'/'+request['Name'];raw={'Name':request['Name'],'GroupName':request.get('GroupName')}
                    response={'ScheduleGroupArn' if kind=='schedule-group' else 'ScheduleArn':identity}
                elif op=='create-vpc-peering-connection':
                    identity=rid('pcx');raw={'VpcPeeringConnectionId':identity,'Status':{'Code':'pending-acceptance'},
                        'Tags':request['TagSpecifications'][0]['Tags'],
                        'RequesterVpcInfo':dict(OwnerId=ACCOUNT,Region=region,VpcId=request['VpcId']),
                        'AccepterVpcInfo':dict(OwnerId=ACCOUNT,Region=request['PeerRegion'],VpcId=request['PeerVpcId'])}
                    response={'VpcPeeringConnection':raw}
                elif op=='accept-vpc-peering-connection':resources[request['VpcPeeringConnectionId']]['Status']={'Code':'active'}
                if identity:resources[identity]=copy.deepcopy(raw)
                return SimpleNamespace(returncode=0,stdout=json.dumps(response),stderr='')
            with patch.object(rr.aws_api,'ReadAPI',FakeAPI),patch.object(life.subprocess,'run',side_effect=invoke),\
                    patch.object(rr,'datetime') as dt,patch.object(life,'datetime') as ldt:
                dt.now.return_value=datetime.fromtimestamp(NOW,timezone.utc);ldt.now.return_value=dt.now.return_value
                for action in actions:rr.apply_one(root,p,actions,action['name'],'fixture')
                graph=c.read_private(root/'regional.json')
                self.assertEqual(rr.verify_routes(root,p,graph,'fixture')['verified_directed_routes'],6)
            entry=c.read_private(root/'campaign.json')['reservations'][p['attempt_id']]
            self.assertEqual(len(calls),len(actions));self.assertEqual(len(entry['custody']),39)
            self.assertEqual({row['record']['region'] for row in entry['custody'].values()},set(p['regions']))
            self.assertTrue(all(row['state']=='observed' for row in entry['actions'].values()))
            self.assertEqual(sum(row.get('dependents_recorded',False) for row in entry['custody'].values()),3)

    def test_peering_absence_requires_both_region_reads(self):
        packet={'account':ACCOUNT,'stage':4,'regions':['us-east-2','us-east-1','us-west-2']}
        record=dict(kind='vpc-peering',id='pcx-1234567890abcdef0',region='us-east-2',peer_region='us-east-1',account=ACCOUNT)
        calls=[]
        class API:
            def __init__(self,profile,region,root):self.region=region
            def account(self):return ACCOUNT
            def observe(self,r,account):
                calls.append(self.region)
                return dict(id=r['id'],absent=self.region=='us-east-2',query_succeeded=True,observed_at=NOW)
        with patch.object(rr.aws_api,'ReadAPI',API):
            with self.assertRaisesRegex(ValueError,'peering_other_region_still_present'):
                rr.observe_record(Path('/unused'),packet,'fixture',record)
        self.assertEqual(calls,['us-east-2','us-east-1'])


if __name__=='__main__':unittest.main()
