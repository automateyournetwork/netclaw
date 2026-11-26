"""Explicit Ohio amendment fixtures; never claim regional or live acceptance."""
import copy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import campaign as c
import regional
import regional_run as rr
import qualify
import matrix
from preflight import save
from test_regional import ACCOUNT, NOW, evidence, choices
from test_matrix import world, cell_fixture


def az_inputs():
    row=evidence()[0];raw=row['raw']
    raw['offerings']['data']['InstanceTypeOfferings']=[dict(InstanceType=row['instance_type'],LocationType='availability-zone',Location='us-east-2'+z) for z in 'abc']
    raw['zones']={'ok':True,'data':{'AvailabilityZones':[dict(ZoneName='us-east-2'+z,ZoneId='use2-az'+str(i),RegionName='us-east-2',ZoneType='availability-zone',State='available',OptInStatus='opt-in-not-required') for i,z in enumerate('abc',1)]}}
    raw['credits']={'ok':False,'error':'ResourceNotFoundException'}
    row['owner_paid_upgrade']=dict(account=ACCOUNT,confirmed_by='owner',plan='PAID',gross_budget_usd='100',credit_balance='unknown')
    row['owner_paid_upgrade_sha256']=c.digest(row['owner_paid_upgrade'])
    row['launch_permissions']={z:dict(account=ACCOUNT,region='us-east-2',observed_at=NOW,error='DryRunOperation',request=dict(DryRun=True,ImageId=raw['image']['data']['Images'][0]['ImageId'],InstanceType=row['instance_type'],Placement={'AvailabilityZone':z},MinCount=1,MaxCount=1)) for z in ('us-east-2a','us-east-2b','us-east-2c')}
    row['raw_sha256']=c.digest(raw)
    nodes=choices()
    for i,n in enumerate(nodes):n.update(region='us-east-2',zone='us-east-2'+'abc'[i],zone_id='use2-az'+str(i+1))
    return [row],nodes


def az_plan(rows=None,nodes=None):
    r,n=az_inputs()
    return regional.draft(ACCOUNT,'nc199-abcdef012345',rows if rows is not None else r,nodes if nodes is not None else n,
        deadline='2026-11-25T23:00:00Z',operator_cidr='8.8.8.8/32',public_key='ssh-ed25519 AAAA fixture',now=NOW,
        scope='ohio-three-az',scope_amendment_sha256='f'*64)


class MultiAZTests(unittest.TestCase):
    def test_explicit_mode_and_aggregate_quota_plan_attestation_and_az_provenance(self):
        graph=az_plan();self.assertEqual(graph['qualification_scope'],'ohio-three-az')
        self.assertEqual({n['region'] for n in graph['nodes']},{'us-east-2'})
        self.assertEqual(len({n['zone_id'] for n in graph['nodes']}),3)
        self.assertFalse(graph['activation_ready'])
        rows,nodes=az_inputs()
        with self.assertRaises(ValueError):regional.ready_regions(ACCOUNT,rows,NOW)
        for bad in ('quota','zone','zone_id','missing_zones','missing_upgrade','denied_plan','missing_permission','wrong_ami','permission_stale','wrong_account','free_ineligible'):
            rows,nodes=az_inputs();r=rows[0]
            if bad=='quota':r['raw']['quota']['data']['Quota']['Value']=4
            if bad=='zone':nodes[1]['zone']=nodes[0]['zone']
            if bad=='zone_id':nodes[1]['zone_id']=nodes[0]['zone_id']
            if bad=='missing_zones':r['raw'].pop('zones')
            if bad=='missing_upgrade':r.pop('owner_paid_upgrade')
            if bad=='denied_plan':r['raw']['credits']['error']='AccessDeniedException'
            if bad=='missing_permission':r['launch_permissions'].pop('us-east-2c')
            if bad=='wrong_ami':r['launch_permissions']['us-east-2a']['request']['ImageId']='ami-deadbeef'
            if bad=='permission_stale':r['launch_permissions']['us-east-2a']['observed_at']=NOW-901
            if bad=='wrong_account':r['owner_paid_upgrade']['account']='000000000000'
            if bad=='free_ineligible':
                r['raw']['credits']={'ok':True,'data':dict(accountPlanType='FREE',accountPlanStatus='ACTIVE')}
                r['raw']['types']['data']['InstanceTypes'][0]['FreeTierEligible']=False
            r['raw_sha256']=c.digest(r['raw'])
            with self.subTest(bad=bad),self.assertRaises(ValueError):az_plan(rows,nodes)

    def test_same_region_peering_verifies_both_directions_by_node_and_vpc(self):
        graph=az_plan();tags=[dict(Key=k,Value=v) for k,v in {'netclaw-spec':'199','netclaw-stage':'4','netclaw-run':graph['run_id']}.items()]
        a,b='vpc-0123456789abcdef0','vpc-1123456789abcdef0';pcx='pcx-0123456789abcdef0';rtb='rtb-0123456789abcdef0'
        peer=dict(VpcPeeringConnectionId=pcx,Status={'Code':'active'},Tags=tags,
                  RequesterVpcInfo=dict(OwnerId=ACCOUNT,Region='us-east-2',VpcId=a),
                  AccepterVpcInfo=dict(OwnerId=ACCOUNT,Region='us-east-2',VpcId=b))
        obs=lambda raw:dict(query_succeeded=True,observed_at=NOW,raw=raw,account=ACCOUNT,region='us-east-2')
        for i,route in enumerate(graph['peer_routes'][:2]):
            binding=dict(route,peering_id=pcx,route_table_id=rtb,source_vpc_id=(a,b)[i],target_vpc_id=(b,a)[i])
            table=dict(RouteTableId=rtb,VpcId=binding['source_vpc_id'],Tags=tags,
                       Routes=[dict(DestinationCidrBlock=route['destination'],VpcPeeringConnectionId=pcx,State='active',Origin='CreateRoute')])
            self.assertTrue(regional.verify_peer_route(graph,binding,obs(peer),obs(table),NOW))
            swapped=copy.deepcopy(peer);swapped['RequesterVpcInfo'],swapped['AccepterVpcInfo']=swapped['AccepterVpcInfo'],swapped['RequesterVpcInfo']
            with self.assertRaises(ValueError):regional.verify_peer_route(graph,binding,obs(swapped),obs(table),NOW)

    def test_cost_is_three_hosts_and_scope_is_frozen_in_packet(self):
        rows,nodes=az_inputs();graph=az_plan()
        pricing={'us-east-2':dict(observed_at=NOW,raw={'fixture':True},raw_sha256=c.digest({'fixture':True}),
                    rates=dict(ipv4_usd_hour='0.005',gp3_usd_gb_month='0.08',egress_usd_gb='0.09',peering_usd_gb='0.01'))}
        costs=rr.cost_components(graph,rows,pricing,7200,NOW)
        self.assertEqual(len(costs),3)
        self.assertEqual(sum(c.money(x['compute']) for x in costs.values()),c.money('0.09576')*6)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();state=c.new_campaign(ACCOUNT);state.update(accepted_stage=3,receipts={'3':{'sha256':'a'*64}});save(root/'prior.json',state)
            config=dict(account=ACCOUNT,predecessor_ledger=str(root/'prior.json'),lease_seconds=7200,reports=rows,pricing=pricing,nodes=nodes,
                        operator_cidr='8.8.8.8/32',source_sha='b'*40,baseline_ids=[],aws_reservation='4',external_reservation='1',
                        qualification_scope='ohio-three-az',scope_amendment_sha256='f'*64)
            rows[0]['observed_at']=NOW+.5
            def keygen(args,**kwargs):
                key=Path(args[-1]);save(key,{});key.with_name(key.name+'.pub').write_text('ssh-ed25519 AAAA fixture')
            with patch.object(rr,'datetime') as dt,patch.object(rr.subprocess,'run',side_effect=keygen):
                dt.now.return_value=datetime.fromtimestamp(NOW+.75,timezone.utc);rr.plan(config,root/'new')
            _,packet,_,_=rr.load(root/'new');self.assertEqual(packet['regions'],['us-east-2'])
            self.assertEqual(len(packet['zones']),3)
            for change in ({'qualification_scope':'three-region'},{'zones':{'us-east-2a':'use2-az1'}},{'scope_amendment_sha256':''}):
                with self.assertRaises(ValueError):c.validate_packet(state,dict(packet,**change),NOW+1)

    def test_matrix_preserves_ohio_provenance_and_azure_gcp_regions(self):
        original,keys=world(5);groups=copy.deepcopy(original['groups']);aws=groups['aws']
        ids=list(aws['regions']);aws.update(qualification_scope='ohio-three-az',scope_amendment_sha256='f'*64,
            regions={n:'us-east-2' for n in ids},zones={n:'us-east-2'+'abc'[i] for i,n in enumerate(ids)},zone_ids={n:'use2-az'+str(i+1) for i,n in enumerate(ids)})
        result=matrix.freeze(5,groups,original['anchors'],original['start_ms'],original['deadline_ms'])
        self.assertEqual(len(result['cells']),27)
        for cell in result['cells']:
            a,art=cell_fixture(result,keys,cell)
            self.assertTrue(matrix.verify_cell(result,c.digest(result),a,c.digest(a),art)['original_signatures_verified'])
            if cell['ingress_cloud']=='aws':self.assertIn(cell['ingress_zone_id'],aws['zone_ids'].values())
        for bad in ('implicit','one_az','azure_collapse','azure_scope'):
            changed=copy.deepcopy(groups)
            if bad=='implicit':changed['aws'].pop('qualification_scope')
            if bad=='one_az':changed['aws']['zone_ids']={n:'use2-az1' for n in ids}
            if bad=='azure_collapse':changed['azure']['regions']={n:'eastus' for n in changed['azure']['regions']}
            if bad=='azure_scope':changed['azure']['qualification_scope']='ohio-three-az'
            with self.subTest(bad=bad),self.assertRaises(ValueError):matrix.freeze(5,changed,original['anchors'],original['start_ms'],original['deadline_ms'])

    def test_physical_placement_needs_actual_az_id_and_distinct_hosts(self):
        graph=az_plan();packet=dict(stage=4,account=ACCOUNT,run_id=graph['run_id'],regions=['us-east-2'],
            qualification_scope='ohio-three-az',regional_graph_sha256=c.digest(graph));custody={};observations={}
        for i,n in enumerate(graph['nodes']):
            identity='i-'+str(i+1)*17
            record=dict(kind='instance',id=identity,account=ACCOUNT,region='us-east-2',run_id=packet['run_id'],stage=4,origin_action=n['code']+'-instance',create_request_sha256='a'*64)
            custody[identity]=dict(record=record,record_sha256=c.digest(record))
            raw=dict(Placement=dict(AvailabilityZone=n['zone'],AvailabilityZoneId=n['zone_id']),PrivateIpAddress=n['private_ip'],PublicIpAddress=f'8.8.8.{i+1}',ImageId=n['ami'],InstanceType=n['instance_type'],MetadataOptions=dict(HttpTokens='required',HttpPutResponseHopLimit=1))
            observations[identity]=dict(record,raw=raw,raw_sha256=c.digest(raw),query_succeeded=True,observed_at=NOW,state='running',absent=False,
                tags={'netclaw-spec':'199','netclaw-stage':'4','netclaw-run':packet['run_id']})
        self.assertEqual(len(qualify.regional_nodes(packet,graph,custody,observations,NOW)),3)
        identity=next(iter(observations));observations[identity]['raw']['Placement']['AvailabilityZoneId']='use2-az9'
        observations[identity]['raw_sha256']=c.digest(observations[identity]['raw'])
        with self.assertRaisesRegex(ValueError,'actual_az_id_required'):qualify.regional_nodes(packet,graph,custody,observations,NOW)
