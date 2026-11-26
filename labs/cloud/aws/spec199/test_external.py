"""Final-stage custody fixtures. No cloud execution, permission or spend proof."""
import copy
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import campaign as c
import external as e
import mesh
from preflight import save
from test_regional_run import prepared


def config():
    nodes=[]
    for i,(cl,regions) in enumerate([('azure',['canadacentral','eastus2','swedencentral']),('gcp',['northamerica-northeast1','europe-west1','asia-southeast1'])]):
        for j,(code,region) in enumerate(zip(['nne1','ew1','ase1'],regions)):
            nodes.append(dict(cloud=cl,code=code,region=region,zone=region+'-b',cidr=f'10.199.{31+i*10+j}.0/24',private_ip=f'10.199.{31+i*10+j}.10',
                size='Standard_D2as_v7' if cl=='azure' else 'e2-standard-2',image_version='24.04.202611170',image='projects/ubuntu-os-cloud/global/images/ubuntu-2404-noble-amd64-v20261125'))
    result=dict(nodes=nodes,operator_cidr='8.8.8.8/32',azure_subscription='11111111-1111-4111-8111-111111111111',gcp_project='netclaw-506315',cost_components={'compute':'1.2','storage_and_hold':'0.3','public_ipv4':'0.06','provider':'2.2','transfer':'0.2'})
    reports={};rates={}
    for n in nodes:
        key=n['cloud']+'-'+n['code']
        if n['cloud']=='azure':
            raw=dict(skus=[{'name':n['size'],'family':'fixtureFamily','restrictions':[]}],usage=[{'name':{'value':v},'limit':10,'currentValue':0} for v in ('cores','fixtureFamily')],image={'name':n['image_version'],'architecture':'x64'})
        else:
            raw=dict(region={'name':n['region'],'quotas':[{'metric':k,'limit':v,'usage':0} for k,v in [('CPUS',10),('IN_USE_ADDRESSES',8),('DISKS_TOTAL_GB',1000)]]},zone={'name':n['zone'],'status':'UP'},machine={'guestCpus':2,'memoryMb':8192},image={'name':n['image'].rsplit('/',1)[-1],'status':'READY','architecture':'X86_64'})
        reports[key]=dict(query_succeeded=True,observed_at=time.time(),raw=raw,raw_sha256=c.digest(raw));rates[key]={'compute_hour':'0.1','disk_month':'1','ip_hour':'0.005'}
    result['readiness']=dict(azure_subscription=result['azure_subscription'],gcp_project=result['gcp_project'],azure_state='Enabled',nodes=reports)
    result['pricing']=dict(query_succeeded=True,observed_at=time.time(),raw={'fixture':True},raw_sha256=c.digest({'fixture':True}),rates=rates)
    return result


def fixture(root):
    root,p,aws,g=prepared(root,stage=5)
    plan=e.plan(g,config(),'ssh-ed25519 AAAA fixture')
    p.update(external_plan_sha256=c.digest(plan),mesh_recipe=mesh.RECIPE)
    state=c.read_private(root/'campaign.json');state['reservations'][p['attempt_id']]['packet_sha256']=c.digest(p)
    return root,p,plan,state


class ExternalTests(unittest.TestCase):
    def watcher_case(self, root):
        _,p,plan,state=fixture(root);a=next(x for x in plan['actions'] if x['kind']=='watcher');now=c.stamp(p['created_at'])
        raw=dict(id=a['id'],name=a['id'].rsplit('/',1)[-1],type='Microsoft.Network/networkWatchers',location=a['body']['location'],tags=plan['tags'],etag='original-revision',properties={'provisioningState':'Succeeded','runningOperationIds':[]})
        initial=dict(query_succeeded=True,absent=False,observed_at=now,raw=raw,raw_sha256=c.digest(raw));rec=e.identity(a,initial,plan)
        response=dict(status=201,headers={'x-ms-request-id':'original-request'},body={**raw,'etag':'create-response-revision'});baseline=dict(query_succeeded=True,absent=True,observed_at=now);operation=dict(status=200,body={'status':'Succeeded'})
        entry=state['reservations'][p['attempt_id']];entry['external_actions']={a['name']:dict(state='observed',operation_verified=True,action_sha256=c.digest(a),baseline_sha256=c.digest(baseline),response_sha256=c.digest(response),observation_sha256=c.digest(initial),operation_receipt_sha256=c.digest(operation),sent_at=now)}
        group=next(x['id'] for x in plan['actions'] if x['kind']=='group');events=[dict(resourceId=a['id'],operationName={'value':'Microsoft.Network/networkWatchers/write'},status={'value':status},correlationId='same-original-write',eventTimestamp=e.datetime.fromtimestamp(now,e.timezone.utc).isoformat()) for status in ('Started','Succeeded')]
        proof=dict(intent=dict(action=a,baseline=baseline),response=response,initial=initial,operation=operation,
            children={child:dict(url=e.AZ+a['id']+'/'+child+'?api-version='+e.VERSIONS['network'],observed_at=now,status=200,body={'value':[]}) for child in ('packetCaptures','connectionMonitors','flowLogs')},
            group_resources=dict(url=e.AZ+group+'/resources?api-version='+e.VERSIONS['group'],observed_at=now,status=200,body={'value':[{'id':a['id']}]}),
            activity=dict(group_id=group,observed_at=now,pages=[dict(status=200,body={'value':events})]))
        obs=copy.deepcopy(initial);obs['raw']['etag']='current-revision';obs['raw_sha256']=c.digest(obs['raw']);obs['watcher_cleanup_evidence']=proof
        return entry,rec,a,obs,plan,now

    def test_watcher_cleanup_uses_original_creation_not_mutable_etag(self):
        with tempfile.TemporaryDirectory() as d:
            values=self.watcher_case(Path(d).resolve());before=c.digest(values[1]);e.verify_watcher_retirement(*values)
            self.assertEqual(before,c.digest(values[1]))
            with self.assertRaisesRegex(ValueError,'incarnation_changed'):e.verify_owned(values[1],values[2],values[3],values[4],values[5])

    def test_watcher_cleanup_refuses_missing_or_rewritten_creation(self):
        with tempfile.TemporaryDirectory() as d:
            values=self.watcher_case(Path(d).resolve())
            for key in ('response','initial','operation','intent'):
                bad=copy.deepcopy(values);bad[3]['watcher_cleanup_evidence'][key]={}
                with self.assertRaises(ValueError):e.verify_watcher_retirement(*bad)
            bad=copy.deepcopy(values);proof=bad[3]['watcher_cleanup_evidence'];proof['response']['status']=200;bad[0]['external_actions'][bad[2]['name']]['response_sha256']=c.digest(proof['response'])
            with self.assertRaisesRegex(ValueError,'original_watcher_201'):e.verify_watcher_retirement(*bad)

    def test_watcher_cleanup_preserves_changed_configuration_or_children(self):
        with tempfile.TemporaryDirectory() as d:
            values=self.watcher_case(Path(d).resolve());bad=copy.deepcopy(values);bad[3]['raw']['extra']='new';bad[3]['raw_sha256']=c.digest(bad[3]['raw'])
            with self.assertRaisesRegex(ValueError,'configuration_changed'):e.verify_watcher_retirement(*bad)
            for child in ('packetCaptures','connectionMonitors','flowLogs'):
                for update in ({'value':[{'id':'foreign'}]},{'value':[],'nextLink':'unread-page'}):
                    bad=copy.deepcopy(values);bad[3]['watcher_cleanup_evidence']['children'][child]['body']=update
                    with self.assertRaisesRegex(ValueError,'children_or_unknown'):e.verify_watcher_retirement(*bad)
            bad=copy.deepcopy(values);bad[3]['watcher_cleanup_evidence']['group_resources']['body']['value'].append({'id':values[2]['id']+'/unknownChild/x'})
            with self.assertRaisesRegex(ValueError,'descendants_or_unknown'):e.verify_watcher_retirement(*bad)

    def test_watcher_cleanup_refuses_other_mutation_history_or_incomplete_reads(self):
        with tempfile.TemporaryDirectory() as d:
            values=self.watcher_case(Path(d).resolve())
            for change in ('delete','other-write','unread-page','stale'):
                bad=copy.deepcopy(values);history=bad[3]['watcher_cleanup_evidence']['activity'];event=history['pages'][0]['body']['value'][0]
                if change=='delete':event['operationName']['value']='Microsoft.Network/networkWatchers/delete'
                elif change=='other-write':event['correlationId']='someone-else'
                elif change=='unread-page':history['pages'][0]['body']['nextLink']='unread-page'
                else:history['observed_at']-=31
                with self.assertRaises(ValueError):e.verify_watcher_retirement(*bad)

    def test_implicit_disk_uses_disk_api_for_observation_and_retirement(self):
        with tempfile.TemporaryDirectory() as d:
            _,p,plan,_=fixture(Path(d).resolve());slot=next(n for n in plan['nodes'] if n['cloud']=='azure')
            record=dict(kind='implicit-disk',id=slot['disk_id'],action_name=slot['key']+'-implicit-disk')
            action=e.action_for({},plan,record)
            self.assertEqual(action['url'],e.AZ+slot['disk_id']+'?api-version=2025-01-02')
            self.assertNotEqual(e.DISK_VERSION,e.VERSIONS['compute'])

    def test_nsg_cleanup_preserves_foreign_rules_and_attachments(self):
        with tempfile.TemporaryDirectory() as d:
            _,_,plan,_=fixture(Path(d).resolve());a=next(a for a in plan['actions'] if a['kind']=='nsg')
            record=dict(cloud='azure',kind='nsg');obs={'raw':copy.deepcopy(a['body'])}
            e.verify_parent_contents(record,a,obs)
            bad=copy.deepcopy(obs);bad['raw']['properties']['securityRules'].append({'name':'foreign','properties':{}})
            with self.assertRaisesRegex(ValueError,'foreign_nsg'):e.verify_parent_contents(record,a,bad)
            bad=copy.deepcopy(obs);bad['raw']['properties']['networkInterfaces']=[{'id':'foreign'}]
            with self.assertRaisesRegex(ValueError,'attached_nsg'):e.verify_parent_contents(record,a,bad)

    def test_vnet_cleanup_preserves_foreign_subnets_peerings_and_links(self):
        with tempfile.TemporaryDirectory() as d:
            _,_,plan,_=fixture(Path(d).resolve());a=next(a for a in plan['actions'] if a['kind']=='vnet')
            record=dict(cloud='azure',kind='vnet');obs={'raw':copy.deepcopy(a['body'])}
            e.verify_parent_contents(record,a,obs)
            bad=copy.deepcopy(obs);bad['raw']['properties']['subnets'].append({'name':'foreign','properties':{}})
            with self.assertRaisesRegex(ValueError,'foreign_vnet'):e.verify_parent_contents(record,a,bad)
            bad=copy.deepcopy(obs);bad['raw']['properties']['virtualNetworkPeerings']=[{'id':'foreign'}]
            with self.assertRaisesRegex(ValueError,'attached_vnet'):e.verify_parent_contents(record,a,bad)
            for key in ('ipConfigurations','privateEndpoints','routeTable','delegations'):
                bad=copy.deepcopy(obs);bad['raw']['properties']['subnets'][0]['properties'][key]=[{'id':'foreign'}]
                with self.assertRaisesRegex(ValueError,'attached_vnet'):e.verify_parent_contents(record,a,bad)

    def test_plan_pins_all_six_hosts_no_default_network_or_cloud_service_identity(self):
        with tempfile.TemporaryDirectory() as d:
            _,p,plan,_=fixture(Path(d).resolve())
            self.assertEqual(len(plan['nodes']),6)
            seen=set()
            for a in plan['actions']:
                self.assertLessEqual(set(a['depends']),seen);seen.add(a['name'])
                self.assertIn(p['run_id'],a['id']);self.assertNotIn('/networks/default',a['id'])
                if a['kind']=='vm' and a['cloud']=='gcp':
                    self.assertEqual(a['body']['serviceAccounts'],[])
                    self.assertEqual(a['body']['scheduling']['terminationTime'],p['deadline'])
                    self.assertEqual(a['body']['scheduling']['instanceTerminationAction'],'STOP')
                if a['kind']=='vm' and a['cloud']=='azure':
                    self.assertNotIn('identity',a['body']);self.assertNotEqual(a['body']['properties']['storageProfile']['imageReference']['version'],'latest')
            self.assertEqual(len([a for a in plan['actions'] if a['kind']=='peering']),6)

    def test_external_create_unknown_cannot_replay_or_advance(self):
        with tempfile.TemporaryDirectory() as d:
            root,p,plan,state=fixture(Path(d).resolve());a=plan['actions'][0];now=c.stamp(p['created_at'])
            baseline=dict(query_succeeded=True,absent=True,observed_at=now)
            e.begin(state,p,plan,a,baseline,now)
            state['reservations'][p['attempt_id']]['external_actions'][a['name']]['state']='unknown'
            with self.assertRaisesRegex(ValueError,'already_sent'):e.begin(state,p,plan,a,baseline,now)
            child=next(x for x in plan['actions'] if a['name'] in x['depends'])
            with self.assertRaisesRegex(ValueError,'dependencies'):e.begin(state,p,plan,child,baseline,now)
            changed=copy.deepcopy(plan);changed['nodes'][0]['region']='different'
            with self.assertRaisesRegex(ValueError,'plan_changed'):e.begin(state,p,changed,a,baseline,now)

    def test_foreign_recreated_or_unexported_resource_cannot_be_deleted(self):
        with tempfile.TemporaryDirectory() as d:
            root,p,plan,state=fixture(Path(d).resolve());a=next(x for x in plan['actions'] if x['cloud']=='gcp' and x['kind']=='network');now=c.stamp(p['created_at'])
            raw=dict(selfLink=e.GC+a['id'],id='12345',description=plan['description'])
            obs=dict(query_succeeded=True,absent=False,observed_at=now,raw=raw,raw_sha256=c.digest(raw))
            rec=e.identity(a,obs,plan);entry=state['reservations'][p['attempt_id']]
            entry['external_custody']={rec['id']:dict(record=rec,record_sha256=c.digest(rec))}
            changed=copy.deepcopy(obs);changed['raw']['id']='54321';changed['raw_sha256']=c.digest(changed['raw'])
            with self.assertRaisesRegex(ValueError,'incarnation_changed'):e.verify_owned(rec,a,changed,plan,now)
            changed['raw']['description']='foreign';changed['raw_sha256']=c.digest(changed['raw'])
            with self.assertRaisesRegex(ValueError,'foreign'):e.verify_owned(rec,a,changed,plan,now)
            with self.assertRaises(ValueError),patch.object(e.API,'request') as request:
                e.retire_once(root,p,plan,rec,obs,{},root,dict(schema=1,quiescent=False),e.API())
            request.assert_not_called()

    def test_mesh_recipe_exact_six_peers_per_host_and_immutable_binding(self):
        with tempfile.TemporaryDirectory() as d:
            root,p,plan,state=fixture(Path(d).resolve());nodes=[]
            for i,cl in enumerate(('aws','azure','gcp')):
                for j in range(3):nodes.append(dict(key=cl+'-'+str(j),cloud=cl,code='n'+str(j),region='us-east-2',public=f'8.8.{i}.{j+1}',security_group_id='sg-'+str(j),nsg_id='/owned/nsg-'+str(j)))
            value=dict(packet_sha256=c.digest(p),external_plan_sha256=c.digest(plan),nodes=nodes,manifests={cl:str(i+1)*64 for i,cl in enumerate(('aws','azure','gcp'))})
            actions=mesh.child_actions(p,plan,value);self.assertEqual(len(actions),10)
            for a in actions:
                if 'service' in a:self.assertEqual(len(a['request']['IpPermissions'][0]['IpRanges']),6)
            entry=state['reservations'][p['attempt_id']];entry['mesh_binding']=dict(value=value,sha256=c.digest(value),actions=actions,actions_sha256=c.digest(actions))
            self.assertEqual(len(mesh.authorized(entry,p)),10)
            entry['mesh_binding']['value']['nodes'][0]['public']='1.1.1.1'
            with self.assertRaisesRegex(ValueError,'binding_changed'):mesh.authorized(entry,p)

    @patch.object(mesh, "verify_bound_authorities")
    def test_binding_can_only_be_frozen_once_after_actual_identity_and_address_checks(self, _authority):
        with tempfile.TemporaryDirectory() as d:
            root,p,plan,state=fixture(Path(d).resolve());entry=state['reservations'][p['attempt_id']];entry['state']='sent'
            entry['custody']={};entry['external_custody']={};entry['external_actions']={a['name']:{'state':'observed'} for a in plan['actions']};entry['actions']={name:{'state':'observed'} for name in p['actions']};now=c.stamp(p['created_at'])
            nodes=[]
            def obs(raw):return dict(query_succeeded=True,absent=False,observed_at=now,raw=raw,raw_sha256=c.digest(raw))
            for j in range(3):
                code='n'+str(j);rid='i-'+str(j+1)*17;sg='sg-'+str(j+1)*17;pub='8.9.0.'+str(j+1);private='10.199.21.'+str(j+10)
                rec=dict(id=rid,kind='instance',origin_action=code+'-instance',region='us-east-2',account=p['account'],run_id=p['run_id'],stage=5,create_request_sha256='a'*64)
                entry['custody'][rid]=dict(record=rec,record_sha256=c.digest(rec))
                recsg=dict(id=sg,kind='security-group',origin_action=code+'-security-group')
                entry['custody'][sg]=dict(record=recsg,record_sha256=c.digest(recsg))
                nodes.append(dict(key='aws-'+code,cloud='aws',code=code,id=rid,region='us-east-2',zone='us-east-2'+'abc'[j],public=pub,internal=private,security_group_id=sg,observation=obs(dict(InstanceId=rid,PublicIpAddress=pub,PrivateIpAddress=private,Placement={'AvailabilityZone':'us-east-2'+'abc'[j]},State={'Name':'running'}))))
                nodes[-1]['observation'].update(id=rid,account=p['account'],region='us-east-2',tags=plan['tags'])
            for j,slot in enumerate(plan['nodes']):
                pub='8.9.1.'+str(j+1);node=dict(slot,public=pub,internal=slot['private_ip'])
                action=next(a for a in plan['actions'] if a['name']==slot['vm_action'])
                if slot['cloud']=='gcp':raw=dict(selfLink=e.GC+slot['id'],id=str(j+12345),description=plan['description'],status='RUNNING',networkInterfaces=[{'networkIP':slot['private_ip'],'accessConfigs':[{'natIP':pub}]}])
                else:
                    raw=dict(id=slot['id'],tags=plan['tags'],properties={'vmId':'vm-'+str(j),'provisioningState':'Succeeded','networkProfile':{'networkInterfaces':[{'id':slot['nic_id']}]}})
                    node['ip_observation']=obs(dict(id=slot['ip_id'],tags=plan['tags'],properties={'resourceGuid':'ip-'+str(j),'ipAddress':pub}))
                    node['nic_observation']=obs(dict(id=slot['nic_id'],tags=plan['tags'],properties={'resourceGuid':'nic-'+str(j),'networkSecurityGroup':{'id':slot['nsg_id']},'ipConfigurations':[{'properties':{'privateIPAddress':slot['private_ip'],'subnet':{'id':slot['vnet_id']+'/subnets/owned'},'publicIPAddress':{'id':slot['ip_id']}}}]}))
                    for kind in ('ip','nic'):
                        item=next(a for a in plan['actions'] if a['name']==slot['key']+'-'+kind);rc=e.identity(item,node[kind+'_observation'],plan)
                        entry['external_custody'][rc['id']]=dict(record=rc,record_sha256=c.digest(rc))
                node['observation']=obs(raw);rec=e.identity(action,node['observation'],plan)
                entry['external_custody'][slot['id']]=dict(record=rec,record_sha256=c.digest(rec));nodes.append(node)
            value=dict(packet_sha256=c.digest(p),external_plan_sha256=c.digest(plan),nodes=nodes,manifests={cl:str(i+1)*64 for i,cl in enumerate(('aws','azure','gcp'))})
            for field,new in [('public','1.1.1.1'),('id','foreign')]:
                bad=copy.deepcopy(value);bad['nodes'][0][field]=new
                with self.subTest(field=field),self.assertRaises(ValueError):mesh.freeze(copy.deepcopy(state),p,plan,bad,now)
            mesh.freeze(state,p,plan,value,now)
            with self.assertRaisesRegex(ValueError,'already_frozen'):mesh.freeze(state,p,plan,value,now)

    def test_three_bound_manifests_require_actual_signatures_and_exact_nodes(self):
        from test_matrix import world
        matrix,_=world();bindings={'authorities':{},'manifests':{},'nodes':[]}
        for cloud,group in matrix['groups'].items():
            pin=dict(group['enrollment'],anchor_key_id=matrix['anchors'][cloud]);bindings['authorities'][cloud]=pin
            bindings['manifests'][cloud]=c.digest(pin['manifest'])
            for n in pin['manifest']['manifest']['nodes']:
                bindings['nodes'].append(dict(cloud=cloud,node_id=n['node_id'],dns=n['endpoints']['https'].removeprefix('https://')))
        mesh.verify_bound_authorities(bindings)
        bad=copy.deepcopy(bindings);bad['nodes'][0]['dns']='foreign.invalid'
        with self.assertRaises(ValueError):mesh.verify_bound_authorities(bad)
        bad=copy.deepcopy(bindings);bad['authorities']['aws']['manifest']['manifest']['limits']['admission_ms']=8999
        with self.assertRaises(Exception):mesh.verify_bound_authorities(bad)

    def test_google_canonical_origins_and_foreign_origin_refusal(self):
        wanted='/projects/example/zones/zone-a/instances/owned'
        for origin in (e.GC,'https://www.googleapis.com/compute/v1'):
            self.assertEqual(e.google_path(origin+wanted),wanted)
        with self.assertRaises(ValueError):e.google_path('https://evil.invalid'+wanted)

    def test_vm_creation_requires_verified_live_guard(self):
        with tempfile.TemporaryDirectory() as d:
            root,p,plan,state=fixture(Path(d).resolve());action=next(a for a in plan['actions'] if a['kind']=='vm')
            with patch.object(e.API,'request') as request,self.assertRaises(FileNotFoundError):
                e.apply_once(root,p,plan,action,e.API())
            request.assert_not_called()

    def test_network_retirement_keeps_unknown_launch_and_live_dependents(self):
        with tempfile.TemporaryDirectory() as d:
            root,p,plan,state=fixture(Path(d).resolve());now=c.stamp(p['created_at']);entry=state['reservations'][p['attempt_id']]
            action=next(a for a in plan['actions'] if a['name']=='gcp-network')
            raw=dict(selfLink=e.GC+action['id'],id='123',description=plan['description']);obs=dict(query_succeeded=True,absent=False,observed_at=now,raw=raw,raw_sha256=c.digest(raw))
            rec=e.identity(action,obs,plan);entry['external_custody']={rec['id']:dict(record=rec,record_sha256=c.digest(rec))}
            vm=next(a for a in plan['actions'] if a['kind']=='vm');entry['external_actions']={vm['name']:{'state':'unknown'}}
            with self.assertRaisesRegex(ValueError,'unknown_external_compute'):e.begin_retire(state,p,plan,rec,obs,{},'a'*64,now)
            entry['external_actions']={};child=next(a for a in plan['actions'] if 'gcp-network' in a['depends']);entry['external_actions'][child['name']]={'state':'returned'}
            with self.assertRaisesRegex(ValueError,'unknown_child'):e.begin_retire(state,p,plan,rec,obs,{},'a'*64,now)

    def test_azure_stop_acceptance_is_not_deallocation(self):
        with tempfile.TemporaryDirectory() as d:
            root,p,plan,state=fixture(Path(d).resolve());a=next(x for x in plan['actions'] if x['cloud']=='azure' and x['kind']=='vm')
            raw=dict(id=a['id'],tags=plan['tags'],properties={'vmId':'original-vm'})
            obs=dict(query_succeeded=True,absent=False,observed_at=time.time(),raw=raw,raw_sha256=c.digest(raw));rec=e.identity(a,obs,plan)
            c.transaction(root,lambda s:s.update(state))
            save(root/('guard-stop-'+c.digest(rec)[:24]+'.result.json'),dict(status=202,body={},headers={'Location':e.AZ+'/original-operation'}))
            api=e.API()
            with patch.object(api,'observe',return_value=obs),patch.object(api,'request',return_value={'status':202,'body':{}}):
                self.assertFalse(e.stopped_observation(root,p,plan,rec,api)['stopped'])
            for power,wanted in [('PowerState/stopped',False),('PowerState/deallocated',True)]:
                with patch.object(api,'observe',return_value=obs),patch.object(api,'request',side_effect=[{'status':200,'body':{'status':'Succeeded'}},{'status':200,'body':{'statuses':[{'code':power}]}}]):
                    self.assertEqual(e.stopped_observation(root,p,plan,rec,api)['stopped'],wanted)

    def test_external_custody_and_unknown_work_block_settlement(self):
        with tempfile.TemporaryDirectory() as d:
            root,p,plan,state=fixture(Path(d).resolve());entry=state['reservations'][p['attempt_id']]
            entry['external_actions']={'created':{'state':'unknown'}}
            disposition=dict(evidence_sha256='a'*64,no_open_resources=True,no_uncertain_work=True)
            with self.assertRaisesRegex(ValueError,'external_actions'):c.settle(state,p['attempt_id'],{'aws':'0','external':'0'},disposition)
            entry['external_actions']['created']['state']='observed';entry['external_custody']={'owned':{'disposition':'present'}}
            with self.assertRaisesRegex(ValueError,'external_resources'):c.settle(state,p['attempt_id'],{'aws':'0','external':'0'},disposition)

if __name__=='__main__':unittest.main()
