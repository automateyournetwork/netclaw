import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import campaign as c
import regional
from test_preflight import fixture

NOW=1795641000
ACCOUNT='123456789012'
REGIONS=('us-east-2','us-east-1','us-west-2')


def evidence():
    result=[]
    for region in REGIONS:
        raw=fixture();raw['types']['data']['InstanceTypes'][0].update(InstanceType='m7i-flex.large',FreeTierEligible=True)
        raw['offerings']['data']['InstanceTypeOfferings'][0].update(InstanceType='m7i-flex.large',Location=region+'a')
        raw['credits']={'ok':True,'data':{'accountPlanType':'FREE','accountPlanStatus':'ACTIVE'}}
        product={'product':{'attributes':dict(regionCode=region,instanceType='m7i-flex.large',operatingSystem='Linux',tenancy='Shared',preInstalledSw='NA',capacitystatus='Used')},'terms':{'OnDemand':{'t':{'priceDimensions':{'h':{'unit':'Hrs','beginRange':'0','pricePerUnit':{'USD':'0.09576'}}}}}}}
        raw['price']={'ok':True,'data':{'PriceList':[json.dumps(product)]}}
        result.append({'region':region,'instance_type':'m7i-flex.large','observed_at':NOW,'raw':raw,'raw_sha256':c.digest(raw)})
    return result


def choices():
    return [dict(code=code,region=region,zone=region+'a',vpc_cidr=f'10.199.{n}.0/24',subnet_cidr=f'10.199.{n}.0/26',private_ip=f'10.199.{n}.10') for n,(code,region) in enumerate(zip(('nne1','nne2','ew1'),REGIONS),21)]


def plan(rows=None, selected=None):
    return regional.draft(ACCOUNT,'nc199-abcdef012345',rows or evidence(),selected or choices(),
        deadline='2026-11-25T23:00:00Z',operator_cidr='8.8.8.8/32',public_key='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFixture fixture',now=NOW)


class RegionalTests(unittest.TestCase):
    def test_plan_has_three_isolated_hosts_and_full_pairwise_routes_without_writes(self):
        with patch('subprocess.run') as invoke:
            p=plan();invoke.assert_not_called()
        self.assertFalse(p['activation_ready']);self.assertEqual(len(p['nodes']),3)
        self.assertEqual(len([a for a in p['actions'] if a['operation']=='run-instances']),3)
        self.assertEqual(len([a for a in p['actions'] if a['operation']=='create-vpc-peering-connection']),3)
        self.assertEqual(len([a for a in p['actions'] if a['operation']=='create-tags']),3)
        self.assertEqual(len(p['peer_routes']),6)
        self.assertEqual(len(set(a['name'] for a in p['actions'])),len(p['actions']))
        roles=[a['request']['RoleName'] for a in p['actions'] if a['operation']=='create-role']
        self.assertEqual(len(set(roles)),3)  # IAM names are account-global.
        for a in p['actions']:
            if a['operation']=='run-instances':
                self.assertNotIn('IamInstanceProfile',a['request'])
                self.assertEqual(a['request']['MetadataOptions']['HttpPutResponseHopLimit'],1)
                self.assertEqual(a['request']['MaxCount'],1)
            if a['name'].endswith('peer-ingress'):
                self.assertEqual({x['FromPort'] for x in a['request']['IpPermissions']},set(regional.PEER_PORTS))
                self.assertTrue(all(x['IpRanges'][0]['CidrIp'].endswith('/32') for x in a['request']['IpPermissions']))

    def test_refs_and_acceptance_regions_match_the_three_host_graph(self):
        p=plan();seen=set()
        def refs(v):
            if isinstance(v,list):return sum((refs(x) for x in v),[])
            if isinstance(v,dict):
                if set(v)=={'$ref'}:return [v['$ref'].split('.')[0]]
                return sum((refs(x) for x in v.values()),[])
            return []
        for a in p['actions']:
            self.assertTrue(set(refs(a['request']))<=seen,a['name']);seen.add(a['name'])
            if a['operation']=='accept-vpc-peering-connection':
                creator=next(x for x in p['actions'] if x['name']==a['request']['VpcPeeringConnectionId']['$ref'].split('.')[0])
                self.assertEqual(a['region'],creator['request']['PeerRegion'])
                self.assertNotEqual(a['region'],creator['region'])

    def test_owned_aws_hosts_render_narrow_production_policy(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
        from labs.ha.r09a_policy import build_policy, cluster_host
        p=plan()
        for spec in p['sandbox_policy_inputs'].values():
            policy=build_policy(spec)
            voters=policy['network_policies']['etcd']
            self.assertEqual(len(voters['endpoints']),3)
            self.assertEqual(voters['binaries'],[{'path':'/usr/local/bin/python3.12'}])
            for endpoint in voters['endpoints']:
                self.assertEqual(endpoint['allowed_ips'],[p['hosts'][endpoint['host']]+'/32'])
                self.assertEqual(endpoint['tls'],'skip')  # Preserve end-to-end strict TLS.
        for host in ('metadata.aws.internal','nc199-*-nne1.aws.internal','nc199-abcdef012345-nne1.evil.internal','10.199.21.10'):
            self.assertFalse(cluster_host(host))

    def test_denial_unknown_stale_account_and_price_substitution_fail_closed(self):
        for bad in ('denied','unknown','stale','account','price','hash','free_type'):
            rows=evidence();r=rows[1]
            if bad=='denied':r['raw']['instances']={'ok':False,'error':'UnauthorizedOperation'}
            if bad=='unknown':r['raw'].pop('quota')
            if bad=='stale':r['observed_at']=NOW-901
            if bad=='account':r['raw']['identity']['data']['Account']='000000000000'
            if bad=='price':r['raw']['price']=rows[0]['raw']['price']
            if bad=='free_type':r['raw']['types']['data']['InstanceTypes'][0]['FreeTierEligible']=False
            if bad!='hash':r['raw_sha256']=c.digest(r['raw'])
            else:r['raw_sha256']='0'*64
            with self.subTest(bad=bad),self.assertRaises(ValueError):plan(rows)

    def test_duplicate_regions_overlap_reserved_addresses_and_unobserved_zone_rejected(self):
        for bad in ('region','cidr','reserved','zone','duplicate_code','expired'):
            nodes=choices()
            if bad=='region':nodes[1]['region']=nodes[0]['region']
            if bad=='cidr':nodes[1].update(vpc_cidr=nodes[0]['vpc_cidr'],subnet_cidr=nodes[0]['subnet_cidr'],private_ip=nodes[0]['private_ip'])
            if bad=='reserved':nodes[1]['private_ip']='10.199.22.1'
            if bad=='zone':nodes[1]['zone']=nodes[1]['region']+'b'
            if bad=='duplicate_code':nodes[1]['code']=nodes[0]['code']
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                if bad=='expired':regional.draft(ACCOUNT,'nc199-abcdef012345',evidence(),nodes,deadline='2020-01-01T00:00:00Z',operator_cidr='8.8.8.8/32',public_key='ssh-ed25519 fixture',now=NOW)
                else:plan(selected=nodes)

    def test_changed_route_or_inactive_foreign_peering_refused(self):
        p=plan();expected=p['peer_routes'][0];peer_id='pcx-0123456789abcdef0';route_id='rtb-0123456789abcdef0'
        peer={'VpcPeeringConnectionId':peer_id,'Status':{'Code':'active'},'RequesterVpcInfo':{'OwnerId':ACCOUNT,'Region':expected['source_region'],'VpcId':'vpc-0123456789abcdef0'},'AccepterVpcInfo':{'OwnerId':ACCOUNT,'Region':expected['target_region'],'VpcId':'vpc-1123456789abcdef0'},'Tags':[{'Key':'netclaw-run','Value':p['run_id']},{'Key':'netclaw-stage','Value':'4'},{'Key':'netclaw-spec','Value':'199'}]}
        binding=dict(expected,peering_id=peer_id,route_table_id=route_id,source_vpc_id='vpc-0123456789abcdef0',target_vpc_id='vpc-1123456789abcdef0',requester_region=expected['source_region'])
        route={'RouteTableId':route_id,'VpcId':binding['source_vpc_id'],'Routes':[{'DestinationCidrBlock':expected['destination'],'VpcPeeringConnectionId':peer_id,'State':'active','Origin':'CreateRoute'}],'Tags':copy.deepcopy(peer['Tags'])}
        obs=lambda raw:dict(query_succeeded=True,observed_at=NOW,raw=raw,account=ACCOUNT,region=expected['source_region'])
        self.assertTrue(regional.verify_peer_route(p,binding,obs(peer),obs(route),NOW))
        for bad in ('target','blackhole','account','run','route_id','stale','reverse'):
            a,b=copy.deepcopy(peer),copy.deepcopy(route);at=NOW
            if bad=='target':b['Routes'][0]['VpcPeeringConnectionId']='pcx-2123456789abcdef0'
            if bad=='blackhole':a['Status']['Code']='pending-acceptance'
            if bad=='account':a['AccepterVpcInfo']['OwnerId']='000000000000'
            if bad=='run':b['Tags'][0]['Value']='other'
            if bad=='route_id':b['RouteTableId']='rtb-2123456789abcdef0'
            if bad=='stale':at=NOW+31
            if bad=='reverse':a['RequesterVpcInfo']['Region']=expected['target_region']
            with self.subTest(bad=bad),self.assertRaises(ValueError):regional.verify_peer_route(p,binding,obs(a),obs(b),at)
        reverse=dict(p['peer_routes'][1],peering_id=peer_id,route_table_id=route_id,
                     source_vpc_id=binding['target_vpc_id'],target_vpc_id=binding['source_vpc_id'])
        table=copy.deepcopy(route);table['VpcId']=reverse['source_vpc_id'];table['Routes'][0]['DestinationCidrBlock']=reverse['destination']
        observation=lambda raw:dict(query_succeeded=True,observed_at=NOW,raw=raw,account=ACCOUNT,region=reverse['source_region'])
        self.assertTrue(regional.verify_peer_route(p,reverse,observation(peer),observation(table),NOW))
        with self.assertRaises(ValueError):regional.verify_peer_route(p,reverse,obs(peer),obs(table),NOW)

    def test_timing_binds_complete_fresh_measurements_to_frozen_manifest(self):
        m={'cluster_id':'cluster','generation':'generation','revision':1,'limits':{'admission_ms':9000,'clock_uncertainty_ms':250},'nodes':[{'node_id':n} for n in ('a','b','c')]};sha=c.digest(m)
        rows=[{'source':a,'target':b,'manifest_sha256':sha,'observed_at':NOW,'admission_roundtrip_ms':1200} for a in ('a','b','c') for b in ('a','b','c') if a!=b]
        value=regional.timing_check(m,sha,rows,NOW);self.assertEqual(value['manifest_wait_seconds'],9)
        for bad in ('stale_manifest','missing','duplicate','slow','stale_sample'):
            samples=copy.deepcopy(rows);expected=sha
            if bad=='stale_manifest':expected='0'*64
            if bad=='missing':samples.pop()
            if bad=='duplicate':samples[-1]=samples[0]
            if bad=='slow':samples[0]['admission_roundtrip_ms']=8500
            if bad=='stale_sample':samples[0]['observed_at']=NOW-31
            with self.subTest(bad=bad),self.assertRaises(ValueError):regional.timing_check(m,expected,samples,NOW)
