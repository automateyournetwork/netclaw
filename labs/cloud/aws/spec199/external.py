"""Exact Azure/GCP resources for the final Spec199 stage; no discovery by tag.

All writes consume a durable intent before HTTP. Unknown responses retain their
reservation. VM/disk incarnations are never replaced by names or tags. Azure
named containers have separate original-creation and empty-child gates. Credentials
are obtained from existing CLI sessions in memory and never enter receipts.
"""
import base64
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import campaign as c
import lifecycle as life
from preflight import save

AZ='https://management.azure.com'
GC='https://compute.googleapis.com/compute/v1'
VERSIONS={'group':'2025-04-01','network':'2024-05-01','compute':'2025-04-01'}
DISK_VERSION='2025-01-02'


def google_path(value):
    for origin in (GC,'https://www.googleapis.com/compute/v1'):
        if value.startswith(origin+'/projects/'):return value[len(origin):]
    c.need(value.startswith('/projects/'),'google_resource_origin_required')
    return value


def parent_id(action):
    for token in ('/virtualNetworkPeerings/','/securityRules/'):
        if token in action['id']:return action['id'].split(token)[0]
    return None


def readiness(config,now):
    """Validate fresh successful quota/image/shape observations, not empty denials."""
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
    from labs.ha.r10_preflight import region_report
    evidence=config.get('readiness',{})
    c.need(evidence.get('azure_subscription')==config['azure_subscription'] and evidence.get('gcp_project')==config['gcp_project']
           and evidence.get('azure_state')=='Enabled','external_account_readiness_required')
    rows=evidence.get('nodes',{});c.need(set(rows)=={n['cloud']+'-'+n['code'] for n in config['nodes']},'six_external_reports_required')
    for n in config['nodes']:
        row=rows[n['cloud']+'-'+n['code']];raw=row['raw']
        c.need(row.get('query_succeeded') and 0<=now-row.get('observed_at',0)<=900
               and c.digest(raw)==row.get('raw_sha256'),'fresh_external_readiness_required')
        if n['cloud']=='azure':
            report=region_report(n['region'],{n['size']:raw['skus']},raw['usage'],sizes=(n['size'],))
            c.need(report['verdict']=='go' and raw['image']['name']==n['image_version'] and raw['image']['architecture']=='x64','azure_capacity_image_required')
        else:
            quotas={q['metric']:q['limit']-q['usage'] for q in raw['region']['quotas']}
            c.need(raw['region']['name']==n['region'] and raw['zone']['name']==n['zone'] and raw['zone']['status']=='UP'
                and quotas.get('CPUS',0)>=2 and quotas.get('IN_USE_ADDRESSES',0)>=1 and quotas.get('DISKS_TOTAL_GB',0)>=40
                and raw['machine']['guestCpus']==2 and raw['machine']['memoryMb']==8192
                and raw['image']['status']=='READY' and raw['image']['architecture']=='X86_64'
                and n['image']=='projects/ubuntu-os-cloud/global/images/'+raw['image']['name'],'gcp_capacity_image_required')
    prices=config.get('pricing',{})
    c.need(prices.get('query_succeeded') and 0<=now-prices.get('observed_at',0)<=900
        and c.digest(prices['raw'])==prices.get('raw_sha256'),'fresh_external_prices_required')
    c.need(set(prices['rates'])==set(rows),'six_external_rates_required')
    hours=c.money('2');storage=c.money('0');compute=c.money('0');ips=c.money('0')
    for rate in prices['rates'].values():
        c.need(all(c.money(rate[k])>0 for k in ('compute_hour','disk_month','ip_hour')),'gross_external_rates_required')
        compute+=c.money(rate['compute_hour'])*hours
        storage+=c.money(rate['disk_month'])*c.money('26')/c.money('720')
        ips+=c.money(rate['ip_hour'])*hours
    components=config['cost_components']
    c.need(c.money(components['compute'])>=compute and c.money(components['storage_and_hold'])>=storage
        and c.money(components['public_ipv4'])>=ips and c.money(components['provider'])>=c.money('2.16'), 'external_cost_floor_required')


def boot(deadline, public_key):
    cutoff=datetime.fromtimestamp(c.stamp(deadline),timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    # Cloud-init creates the same unprivileged operator on both external clouds.
    return '#cloud-config\n'+json.dumps({'users':[{'name':'ubuntu','groups':['sudo'],'shell':'/bin/bash',
        'sudo':'ALL=(ALL) NOPASSWD:ALL','lock_passwd':True,'ssh_authorized_keys':[public_key.strip()]}],
        'ssh_pwauth':False,'write_files':[
        {'path':'/etc/systemd/system/netclaw-199-deadline.service','content':'[Service]\nType=oneshot\nExecStart=/usr/bin/systemctl poweroff\n'},
        {'path':'/etc/systemd/system/netclaw-199-deadline.timer','content':'[Timer]\nOnCalendar='+cutoff+'\nPersistent=true\nAccuracySec=1s\n[Install]\nWantedBy=timers.target\n'}],
        'runcmd':['systemctl daemon-reload','systemctl enable --now netclaw-199-deadline.timer',
        'echo NETCLAW_199_HOST_KEYS_BEGIN > /dev/console; cat /etc/ssh/ssh_host_ed25519_key.pub > /dev/console; echo NETCLAW_199_HOST_KEYS_END > /dev/console']})


def plan(graph, config, public_key):
    c.need(graph['stage']==5,'final_stage_required')
    readiness(config,time.time())
    run=graph['run_id'];tags={'netclaw-spec':'199','netclaw-run':run,'netclaw-stage':'5'}
    desc='Spec199 '+run+' stage5';operator=config['operator_cidr']
    net=ipaddress.ip_network(operator);c.need(net.prefixlen==32 and net.network_address.is_global,'exact_operator_required')
    sub=config['azure_subscription'];project=config['gcp_project'];uuid.UUID(sub)
    c.need(project=='netclaw-506315','reviewed_project_required')
    nodes=config['nodes'];c.need(len(nodes)==6,'six_external_nodes_required')
    for cloud in ('azure','gcp'):
        selected=[n for n in nodes if n['cloud']==cloud]
        c.need(len(selected)==len({n['region'] for n in selected})==len({n['code'] for n in selected})==3,'three_external_regions_required')
    user_data=boot(graph['deadline'],public_key);actions=[];slots=[]
    def az(name,kind,rid,body,version,depends=()):
        action=dict(name=name,cloud='azure',kind=kind,id=rid,url=AZ+rid+'?api-version='+version,
                    method='PUT',body=body,depends=list(depends));actions.append(action);return action
    def gc(name,kind,collection,body,depends=()):
        rid=collection+'/'+body['name'];action=dict(name=name,cloud='gcp',kind=kind,id=rid,url=GC+collection,
            read_url=GC+rid,method='POST',body=body,depends=list(depends));actions.append(action);return action
    group='/subscriptions/'+sub+'/resourceGroups/rg-'+run
    az('azure-group','group',group,dict(location=nodes[0]['region'] if nodes[0]['cloud']=='azure' else 'canadacentral',tags=tags),VERSIONS['group'])
    network='/projects/'+project+'/global/networks/'+run
    gc('gcp-network','network','/projects/'+project+'/global/networks',dict(name=run,description=desc,autoCreateSubnetworks=False,routingConfig={'routingMode':'GLOBAL'}))
    privates={cl:[n['private_ip']+'/32' for n in nodes if n['cloud']==cl] for cl in ('azure','gcp')}
    for n in nodes:
        cl,code,region=n['cloud'],n['code'],n['region'];stem=run+'-'+code;key=cl+'-'+code
        slot=dict(n,key=key,name=stem)
        c.need(ipaddress.ip_address(n['private_ip']) in ipaddress.ip_network(n['cidr']),'exact_subnet_required')
        if cl=='azure':
            base=group+'/providers/Microsoft.Network/';vnet=base+'virtualNetworks/vnet-'+stem
            nsg=base+'networkSecurityGroups/nsg-'+stem;pip=base+'publicIPAddresses/pip-'+stem;nic=base+'networkInterfaces/nic-'+stem
            subnet=vnet+'/subnets/owned';vm=group+'/providers/Microsoft.Compute/virtualMachines/'+stem
            def rule(name,priority,ports,sources,access='Allow'):
                return dict(name=name,properties=dict(priority=priority,protocol='Tcp' if access=='Allow' else '*',access=access,direction='Inbound',sourcePortRange='*',destinationAddressPrefix='*',
                    **({'sourceAddressPrefix':sources[0]} if len(sources)==1 else {'sourceAddressPrefixes':sources}),
                    **({'destinationPortRange':ports[0]} if len(ports)==1 else {'destinationPortRanges':ports})))
            watcher=base+'networkWatchers/nw-'+stem
            az(key+'-watcher','watcher',watcher,dict(location=region,tags=tags,properties={}),VERSIONS['network'],['azure-group'])
            az(key+'-vnet','vnet',vnet,dict(location=region,tags=tags,properties={'addressSpace':{'addressPrefixes':[n['cidr']]},'subnets':[{'name':'owned','properties':{'addressPrefix':n['cidr']}}]}),VERSIONS['network'],[key+'-watcher'])
            rules=[rule('operator',100,['22','443','7444'],[operator]),rule('authority',110,['2380','12379','7443','7444'],privates[cl]),rule('deny-other-inbound',4000,['*'],['*'],'Deny')]
            az(key+'-nsg','nsg',nsg,dict(location=region,tags=tags,properties={'securityRules':rules}),VERSIONS['network'],['azure-group'])
            az(key+'-ip','ip',pip,dict(location=region,tags=tags,sku={'name':'Standard'},properties={'publicIPAllocationMethod':'Static','publicIPAddressVersion':'IPv4'}),VERSIONS['network'],['azure-group'])
            az(key+'-nic','nic',nic,dict(location=region,tags=tags,properties={'networkSecurityGroup':{'id':nsg},'ipConfigurations':[{'name':'primary','properties':{'primary':True,'privateIPAllocationMethod':'Static','privateIPAddress':n['private_ip'],'subnet':{'id':subnet},'publicIPAddress':{'id':pip}}}]}),VERSIONS['network'],[key+'-vnet',key+'-nsg',key+'-ip'])
            c.need(n['size']=='Standard_D2as_v7' and n['image_version']!='latest','pinned_external_shape_image_required')
            body=dict(location=region,tags=tags,properties={'hardwareProfile':{'vmSize':n['size']},'storageProfile':{
                'imageReference':{'publisher':'Canonical','offer':'ubuntu-24_04-lts','sku':'server','version':n['image_version']},
                'osDisk':{'name':'os-'+stem,'createOption':'FromImage','diskSizeGB':40,'deleteOption':'Delete','managedDisk':{'storageAccountType':'StandardSSD_LRS'}}},
                'osProfile':{'computerName':stem,'adminUsername':'ubuntu','customData':base64.b64encode(user_data.encode()).decode(),'linuxConfiguration':{'disablePasswordAuthentication':True,'ssh':{'publicKeys':[{'path':'/home/ubuntu/.ssh/authorized_keys','keyData':public_key.strip()}]}}},
                'networkProfile':{'networkInterfaces':[{'id':nic,'properties':{'primary':True,'deleteOption':'Detach'}}]},
                'diagnosticsProfile':{'bootDiagnostics':{'enabled':True}}})
            az(key+'-vm','vm',vm,body,VERSIONS['compute'],[key+'-nic'])
            slot.update(id=vm,vm_action=key+'-vm',nsg_id=nsg,ip_id=pip,nic_id=nic,vnet_id=vnet,
                        disk_id=group+'/providers/Microsoft.Compute/disks/os-'+stem)
        else:
            zone=n['zone'];collection='/projects/'+project+'/regions/'+region+'/subnetworks'
            subnet=collection+'/'+stem;vm='/projects/'+project+'/zones/'+zone+'/instances/'+stem
            c.need(n['size']=='e2-standard-2' and n['image'].startswith('projects/ubuntu-os-cloud/global/images/ubuntu-2404-'),'pinned_external_shape_image_required')
            gc(key+'-subnet','subnet',collection,dict(name=stem,description=desc,network=GC+network,ipCidrRange=n['cidr']),['gcp-network'])
            gc(key+'-disk','disk','/projects/'+project+'/zones/'+zone+'/disks',dict(name='os-'+stem,description=desc,labels=tags,sizeGb='40',type='projects/'+project+'/zones/'+zone+'/diskTypes/pd-standard',sourceImage=n['image']))
            disk='/projects/'+project+'/zones/'+zone+'/disks/os-'+stem
            body=dict(name=stem,description=desc,labels=tags,machineType='zones/'+zone+'/machineTypes/'+n['size'],tags={'items':[run]},
                disks=[{'boot':True,'autoDelete':True,'type':'PERSISTENT','source':GC+disk}],
                networkInterfaces=[{'network':GC+network,'subnetwork':GC+subnet,'networkIP':n['private_ip'],'accessConfigs':[{'name':'External NAT','type':'ONE_TO_ONE_NAT','networkTier':'PREMIUM'}]}],
                metadata={'items':[{'key':'user-data','value':user_data},{'key':'block-project-ssh-keys','value':'true'},{'key':'enable-oslogin','value':'false'},{'key':'ssh-keys','value':'ubuntu:'+public_key.strip()}]},
                serviceAccounts=[],scheduling={'terminationTime':graph['deadline'],'instanceTerminationAction':'STOP','automaticRestart':False})
            gc(key+'-vm','vm','/projects/'+project+'/zones/'+zone+'/instances',body,[key+'-subnet',key+'-disk','gcp-owner','gcp-authority'])
            slot.update(id=vm,vm_action=key+'-vm',disk_id=disk)
        slots.append(slot)
    for name,ports,sources in [('owner',['22','443','7444'],[operator]),('authority',['2380','12379','7443','7444'],privates['gcp'])]:
        gc('gcp-'+name,'firewall','/projects/'+project+'/global/firewalls',dict(name=run+'-'+name,description=desc,network=GC+network,direction='INGRESS',priority=1000,sourceRanges=sources,targetTags=[run],allowed=[{'IPProtocol':'tcp','ports':ports}]),['gcp-network'])
    azure=[n for n in slots if n['cloud']=='azure']
    for a in azure:
        for b in azure:
            if a==b:continue
            az(a['key']+'-peer-'+b['code'],'peering',a['vnet_id']+'/virtualNetworkPeerings/to-'+b['code'],
               {'properties':{'remoteVirtualNetwork':{'id':b['vnet_id']},'allowVirtualNetworkAccess':True,'allowForwardedTraffic':False,'allowGatewayTransit':False,'useRemoteGateways':False}},VERSIONS['network'],[a['key']+'-vnet',b['key']+'-vnet'])
    # Topological ordering is deterministic; every dependency must be explicit.
    pending=actions[:];ordered=[];seen=set()
    while pending:
        ready=[a for a in pending if set(a['depends'])<=seen];c.need(ready,'invalid_external_dependencies')
        for a in ready:ordered.append(a);seen.add(a['name']);pending.remove(a)
    return dict(schema=1,stage=5,run_id=run,deadline=graph['deadline'],azure_subscription=sub,gcp_project=project,
                description=desc,tags=tags,nodes=slots,actions=ordered,cost_components=config['cost_components'],max_operations=27,
                readiness_sha256=c.digest(config['readiness']),pricing_sha256=c.digest(config['pricing']))


class API:
    def __init__(self):self.tokens={}
    def token(self,cloud):
        cached=self.tokens.get(cloud)
        if cached and time.time()-cached[0]<300:return cached[1]
        cmd=['az','account','get-access-token','--resource',AZ+'/', '--query','accessToken','-o','tsv'] if cloud=='azure' else ['gcloud','auth','print-access-token']
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=45);c.need(p.returncode==0,'cloud_session_required')
        token=p.stdout.strip();c.need(bool(token) and not any(x.isspace() for x in token),'valid_cloud_token_required')
        self.tokens[cloud]=(time.time(),token);return token
    def request(self,cloud,method,url,body=None,headers=None):
        c.need(url.startswith((AZ+'/' if cloud=='azure' else GC+'/')),'cloud_api_origin_required')
        raw=None if body is None else json.dumps(body).encode()
        req=urllib.request.Request(url,data=raw,method=method,headers={'Authorization':'Bearer '+self.token(cloud),'Content-Type':'application/json',**(headers or {})})
        try:
            with urllib.request.urlopen(req,timeout=60) as r:return {'status':r.status,'body':json.loads(r.read() or b'{}'),
                'headers':{k:v for k,v in r.headers.items() if k.lower() in ('azure-asyncoperation','location','retry-after','date','etag','x-ms-request-id')}}
        except urllib.error.HTTPError as e:
            return {'status':e.code,'body':json.loads(e.read() or b'{}')}
    def observe(self,action):
        r=self.request(action['cloud'],'GET',action.get('read_url',action['url']))
        c.need(r['status'] in (200,404),'successful_external_observation_required')
        value=dict(query_succeeded=True,observed_at=time.time(),absent=r['status']==404,raw=r['body'],raw_sha256=c.digest(r['body']))
        parent=parent_id(action)
        if parent and not value['absent']:
            value['parent_observation']=self.observe(dict(cloud='azure',url=AZ+parent+'?api-version='+VERSIONS['network'],id=parent))
        return value


def identity(action, observed, plan):
    c.need(observed['query_succeeded'] and not observed['absent'] and c.digest(observed['raw'])==observed['raw_sha256'],'external_observation_changed')
    r=observed['raw'];cl=action['cloud'];kind=action['kind']
    if cl=='gcp':
        c.need(google_path(r.get('selfLink',''))==action['id'] and str(r.get('id','')).isdigit(),'external_resource_identity_required')
        c.need(r.get('description')==plan['description'],'foreign_external_resource')
        immutable=str(r['id'])
    else:
        c.need(r.get('id','').lower()==action['id'].lower(),'external_resource_identity_required')
        if kind not in ('peering','mesh-rule'):c.need(all(r.get('tags',{}).get(k)==v for k,v in plan['tags'].items()),'foreign_external_resource')
        props=r.get('properties',{})
        immutable=props.get('vmId') or props.get('resourceGuid') or r.get('systemData',{}).get('createdAt')
        parent=parent_id(action)
        if parent:
            po=observed.get('parent_observation',{});pr=po.get('raw',{});guid=pr.get('properties',{}).get('resourceGuid')
            c.need(po.get('query_succeeded') and not po.get('absent') and c.digest(pr)==po.get('raw_sha256')
                   and pr.get('id','').lower()==parent.lower() and guid
                   and all(pr.get('tags',{}).get(k)==v for k,v in plan['tags'].items()),'owned_parent_identity_required')
            wanted=action['body']['properties']
            c.need(all(props.get(k)==v for k,v in wanted.items()),'external_child_configuration_changed')
            immutable='owned-parent:'+guid+':'+action['id'].rsplit('/',1)[-1]
        if kind=='group':
            # ARM2025 also omits systemData in this actual subscription. A group
            # is a named container, never a VM incarnation: bind its exact owned
            # namespace and require original201 creation plus empty-only delete.
            immutable='owned-group:'+c.digest({'id':action['id'].lower(),'location':r.get('location'),'tags':r.get('tags')})
        if not immutable:immutable=r.get('etag')
        c.need(bool(immutable),'external_resource_identity_required')
    return dict(cloud=cl,kind=kind,id=action['id'],immutable_id=immutable,action_name=action['name'],
                run_id=plan['run_id'],stage=5,action_sha256=c.digest(action),observed_sha256=c.digest(observed))


def begin(state,packet,plan,action,baseline,now):
    c.validate_packet(state,packet,now);c.need(packet.get('external_plan_sha256')==c.digest(plan),'external_plan_changed')
    entry=state['reservations'][packet['attempt_id']]
    c.need(entry['packet_sha256']==c.digest(packet) and entry['state'] in ('reserved','sent'),'reservation_not_active')
    expected={a['name']:a for a in plan['actions']}
    if action['name'] not in expected and entry.get('mesh_binding'):
        import mesh
        expected.update({k:v for k,v in mesh.authorized(entry,packet).items() if 'cloud' in v})
    c.need(expected.get(action['name'])==action,'external_action_not_frozen')
    journal=entry.setdefault('external_actions',{});c.need(action['name'] not in journal,'external_action_already_sent')
    c.need(all(journal.get(k,{}).get('state')=='observed' for k in action['depends']),'external_dependencies_unobserved')
    c.need(baseline['query_succeeded'] and baseline['absent'] and 0<=now-baseline['observed_at']<=30,'fresh_external_absence_required')
    journal[action['name']]=dict(state='sent',action_sha256=c.digest(action),baseline_sha256=c.digest(baseline),sent_at=now)
    entry['state']='sent';state['revision']+=1


def apply_once(root,packet,plan,action,api):
    import run
    run.verify_source(root,packet)
    if action['kind']=='vm':require_guard(root,packet)
    baseline=api.observe(action)
    c.transaction(root,lambda s:begin(s,packet,plan,action,baseline,time.time()))
    path=Path(root)/('external-'+action['name'])
    save(path.with_suffix('.intent.json'),dict(action=action,baseline=baseline))
    try:
        headers={'If-None-Match':'*'} if action['cloud']=='azure' and action['kind']=='vm' else {}
        response=api.request(action['cloud'],action['method'],action['url'],action['body'],headers)
        save(path.with_suffix('.response.json'),response)
        c.need(response['status'] in (200,201,202),'external_write_requires_reconciliation')
        def returned(s):
            row=s['reservations'][packet['attempt_id']]['external_actions'][action['name']]
            row.update(state='returned',response_sha256=c.digest(response));s['revision']+=1
        c.transaction(root,returned)
    except Exception:
        def unknown(s):
            s['reservations'][packet['attempt_id']]['external_actions'][action['name']]['state']='unknown'
            s['reservations'][packet['attempt_id']]['state']='unknown';s['revision']+=1
        c.transaction(root,unknown);raise
    return response


def record_created(root,packet,plan,action,observation):
    rec=identity(action,observation,plan)
    if action['kind']=='group':
        receipt=c.read_private(Path(root)/('external-'+action['name']+'.response.json'))
        request_id={k.lower():v for k,v in receipt.get('headers',{}).items()}.get('x-ms-request-id')
        c.need(receipt.get('status')==201 and request_id and receipt['body'].get('id','').lower()==action['id'].lower(),
               'original_group_create_201_required')
        rec.update(creation_request_id=request_id,creation_receipt_sha256=c.digest(receipt),identity_kind='owned_named_container_empty_delete_only')
    raw=observation['raw'];c.need(raw.get('properties',{}).get('provisioningState','Succeeded')=='Succeeded','external_creation_pending')
    if action['cloud']=='gcp' and action['kind'] in ('vm','disk'):
        c.need(raw.get('status')==('RUNNING' if action['kind']=='vm' else 'READY'),'external_creation_pending')
    def record(s):
        entry=s['reservations'][packet['attempt_id']];row=entry['external_actions'][action['name']]
        c.need(row['state']=='returned' and row.get('operation_verified') and row['action_sha256']==c.digest(action),'returned_external_creation_required')
        c.need(rec['id'] not in entry.setdefault('external_custody',{}),'external_custody_already_recorded')
        entry['external_custody'][rec['id']]=dict(record=rec,record_sha256=c.digest(rec))
        row.update(state='observed',observation_sha256=c.digest(observation));s['revision']+=1
    c.transaction(root,record);save(Path(root)/('external-'+action['name']+'.observed.json'),observation);return rec


def action_for(entry,plan,record):
    actions={a['name']:a for a in plan['actions']}
    actions.update({a['name']:a for a in entry.get('mesh_binding',{}).get('actions',[]) if 'cloud' in a})
    if record['kind']=='implicit-disk':
        slot=next(n for n in plan['nodes'] if n.get('disk_id')==record['id'] and n['cloud']=='azure')
        return dict(name=record['action_name'],cloud='azure',kind='implicit-disk',id=record['id'],
                    url=AZ+record['id']+'?api-version='+DISK_VERSION,parent=slot['id'])
    action=actions[record['action_name']]
    c.need(action['id']==record['id'] and c.digest(action)==record['action_sha256'],'external_custody_changed')
    return action


def record_azure_disk(root,packet,plan,slot,vm_observation,disk_observation):
    """Azure's create-VM response owns exactly its original named OS disk."""
    disk_id=vm_observation['raw']['properties']['storageProfile']['osDisk']['managedDisk']['id']
    c.need(disk_id.lower()==slot['disk_id'].lower(),'unexpected_implicit_disk')
    d=disk_observation['raw'];props=d['properties']
    c.need(disk_observation['query_succeeded'] and not disk_observation['absent']
           and d['id'].lower()==disk_id.lower() and props.get('uniqueId')
           and c.stamp(props['timeCreated'])>=c.stamp(packet['created_at'])
           and props.get('diskSizeGB')==40 and props.get('provisioningState')=='Succeeded','owned_implicit_disk_required')
    rec=dict(cloud='azure',kind='implicit-disk',id=slot['disk_id'],immutable_id=props['uniqueId'],
        action_name=slot['key']+'-implicit-disk',parent=slot['id'],run_id=packet['run_id'],stage=5,observed_sha256=c.digest(disk_observation))
    def record(s):
        entry=s['reservations'][packet['attempt_id']];c.need(slot['id'] in entry['external_custody'],'owned_vm_required')
        c.need(rec['id'] not in entry['external_custody'],'external_custody_already_recorded')
        entry['external_custody'][rec['id']]=dict(record=rec,record_sha256=c.digest(rec));s['revision']+=1
    c.transaction(root,record);save(Path(root)/('external-'+rec['action_name']+'.observed.json'),disk_observation)
    return rec


def verify_owned(record,action,observed,plan,now):
    c.need(observed['query_succeeded'] and 0<=now-observed['observed_at']<=30,'fresh_external_observation_required')
    c.need(c.digest(observed['raw'])==observed['raw_sha256'],'external_observation_changed')
    if observed['absent']:return
    if record['kind']=='implicit-disk':
        c.need(observed['raw'].get('id','').lower()==record['id'].lower()
               and observed['raw'].get('properties',{}).get('uniqueId')==record['immutable_id'],'external_incarnation_changed')
        return
    actual=identity(action,observed,plan)
    c.need(actual['immutable_id']==record['immutable_id'],'external_incarnation_changed')


def verify_parent_contents(record,action,observed):
    """Refuse Azure parent cascades over unrecorded rules, subnets or attachments."""
    if record['cloud']!='azure' or record['kind'] not in ('nsg','vnet'):return
    props=observed['raw']['properties'];wanted=action['body']['properties']
    if record['kind']=='nsg':
        expected={r['name']:r['properties'] for r in wanted['securityRules']}
        actual=props.get('securityRules',[])
        c.need(len(actual)==len(expected) and {r['name'] for r in actual}==set(expected)
               and all(all(r['properties'].get(k)==v for k,v in expected[r['name']].items()) for r in actual),
               'foreign_nsg_rules_preserved')
        c.need(not props.get('networkInterfaces') and not props.get('subnets'),'attached_nsg_preserved')
    else:
        subnets=props.get('subnets',[]);expected=wanted['subnets']
        c.need(len(subnets)==len(expected)==1 and subnets[0]['name']==expected[0]['name']
               and all(subnets[0]['properties'].get(k)==v for k,v in expected[0]['properties'].items())
               and props.get('addressSpace')==wanted['addressSpace'],'foreign_vnet_subnets_preserved')
        sp=subnets[0]['properties']
        c.need(not props.get('virtualNetworkPeerings')
               and not any(sp.get(k) for k in ('ipConfigurations','privateEndpoints','serviceAssociationLinks',
                   'resourceNavigationLinks','delegations','networkSecurityGroup','routeTable','natGateway')),
               'attached_vnet_preserved')


def verify_watcher_retirement(entry,record,action,observed,plan,now):
    """Watcher ETags are revisions, not incarnation GUIDs. Keep original custody.

    This narrow named-container proof does not claim atomic incarnation fencing;
    Activity Log corroborates history but can lag. All other kinds stay strict.
    """
    c.need(record['cloud']=='azure' and record['kind']=='watcher','watcher_only')
    c.need(observed.get('query_succeeded') and not observed.get('absent')
           and 0<=now-observed.get('observed_at',0)<=30,'fresh_external_observation_required')
    identity(action,observed,plan)  # exact resource path, tags and raw digest
    proof=observed.get('watcher_cleanup_evidence',{});original=entry['external_actions'][action['name']]
    c.need(original.get('state')=='observed' and original.get('operation_verified')
           and original['action_sha256']==record['action_sha256']==c.digest(action),'original_watcher_action_required')
    intent=proof.get('intent',{});baseline=intent.get('baseline',{});response=proof.get('response',{});initial=proof.get('initial',{});operation=proof.get('operation',{})
    c.need(c.digest(intent.get('action'))==c.digest(action) and c.digest(baseline)==original['baseline_sha256']
           and baseline.get('query_succeeded') and baseline.get('absent'),'original_watcher_absence_required')
    c.need(c.digest(response)==original['response_sha256'] and response.get('status')==201
           and any(k.lower()=='x-ms-request-id' and v for k,v in response.get('headers',{}).items()),'original_watcher_201_required')
    c.need(c.digest(operation)==original['operation_receipt_sha256'] and operation.get('status')==200
           and operation.get('body',{}).get('status')=='Succeeded','original_watcher_completion_required')
    c.need(c.digest(initial)==original['observation_sha256']==record['observed_sha256']
           and initial.get('query_succeeded') and not initial.get('absent')
           and c.digest(initial.get('raw'))==initial.get('raw_sha256')
           and record['immutable_id']==initial['raw'].get('etag'),'original_watcher_custody_required')
    body=observed['raw'];normalized=lambda value:{k:v for k,v in value.items() if k!='etag'}
    c.need(normalized(body)==normalized(initial['raw'])==normalized(response.get('body',{})),
           'watcher_configuration_changed')
    c.need(body.get('name')==action['id'].rsplit('/',1)[-1] and body.get('type')=='Microsoft.Network/networkWatchers'
           and body.get('location')==action['body']['location'] and body.get('tags')==plan['tags']
           and body.get('properties')=={'provisioningState':'Succeeded','runningOperationIds':[]},'watcher_not_empty_named_container')
    children=proof.get('children',{});c.need(set(children)=={'packetCaptures','connectionMonitors','flowLogs'},'watcher_child_inventories_required')
    for child,value in children.items():
        c.need(value.get('url')==AZ+action['id']+'/'+child+'?api-version='+VERSIONS['network']
               and 0<=now-value.get('observed_at',0)<=30 and value.get('status')==200
               and value.get('body',{}).get('value')==[] and not value.get('body',{}).get('nextLink'),'watcher_children_or_unknown_preserved')
    group=proof.get('group_resources',{});group_id=next(a['id'] for a in plan['actions'] if a['kind']=='group')
    c.need(group.get('url')==AZ+group_id+'/resources?api-version='+VERSIONS['group']
           and 0<=now-group.get('observed_at',0)<=30 and group.get('status')==200
           and isinstance(group.get('body',{}).get('value'),list) and not group['body'].get('nextLink')
           and not any(x.get('id','').lower().startswith(action['id'].lower()+'/') for x in group['body']['value']),
           'watcher_descendants_or_unknown_preserved')
    history=proof.get('activity',{});pages=history.get('pages',[])
    c.need(history.get('group_id')==group_id and 0<=now-history.get('observed_at',0)<=30
           and pages and all(x.get('status')==200 for x in pages)
           and not pages[-1].get('body',{}).get('nextLink'),'watcher_activity_incomplete')
    events=[x for page in pages for x in page['body']['value']]
    c.need(not any(x.get('resourceId','').lower()==group_id.lower()
                  and ('delete' in x.get('operationName',{}).get('value','').lower()
                       or 'move' in x.get('operationName',{}).get('value','').lower()) for x in events),'watcher_parent_history_changed')
    events=[x for x in events if x.get('resourceId','').lower()==action['id'].lower()]
    c.need(events and all(x.get('operationName',{}).get('value')=='Microsoft.Network/networkWatchers/write'
                         and x.get('status',{}).get('value') in ('Started','Succeeded') for x in events)
           and len({x.get('correlationId') for x in events})==1 and bool(events[0].get('correlationId'))
           and sum(x.get('status',{}).get('value')=='Started' for x in events)==1
           and any(x.get('status',{}).get('value')=='Succeeded' for x in events),'watcher_history_changed')
    start=next(x for x in events if x['status']['value']=='Started')
    c.need(abs(c.stamp(start['eventTimestamp'])-original['sent_at'])<30,'watcher_original_write_unmatched')


def watcher_retirement_observation(root,packet,plan,record,api):
    entry=c.read_private(Path(root)/'campaign.json')['reservations'][packet['attempt_id']];action=action_for(entry,plan,record)
    proof={key:c.read_private(Path(root)/('external-'+action['name']+'.'+suffix+'.json'))
           for key,suffix in [('intent','intent'),('response','response'),('initial','observed')]}
    wanted=entry['external_actions'][action['name']]['operation_receipt_sha256']
    operations=[c.read_private(p) for p in Path(root).glob('operation-'+action['name']+'-*.json')]
    matches=[x for x in operations if c.digest(x)==wanted];c.need(len(matches)==1,'original_watcher_completion_required');proof['operation']=matches[0]
    group_id=next(a['id'] for a in plan['actions'] if a['kind']=='group');end=datetime.now(timezone.utc).isoformat()
    where="eventTimestamp ge '"+packet['created_at']+"' and eventTimestamp le '"+end+"' and resourceGroupName eq '"+group_id.rsplit('/',1)[-1]+"'"
    url=AZ+'/subscriptions/'+plan['azure_subscription']+'/providers/Microsoft.Insights/eventtypes/management/values?api-version=2015-04-01&$filter='+urllib.parse.quote(where);pages=[]
    for _ in range(20):
        value=api.request('azure','GET',url);c.need(value['status']==200,'watcher_activity_unavailable');pages.append(value);url=value['body'].get('nextLink')
        if not url:break
    c.need(not url,'watcher_activity_incomplete');proof['activity']=dict(observed_at=time.time(),group_id=group_id,start=packet['created_at'],end=end,pages=pages)
    proof['children']={}
    for child in ('packetCaptures','connectionMonitors','flowLogs'):
        url=AZ+action['id']+'/'+child+'?api-version='+VERSIONS['network'];proof['children'][child]=dict(api.request('azure','GET',url),url=url,observed_at=time.time())
    url=AZ+group_id+'/resources?api-version='+VERSIONS['group'];proof['group_resources']=dict(api.request('azure','GET',url),url=url,observed_at=time.time())
    observation=api.observe(action);observation['watcher_cleanup_evidence']=proof
    verify_watcher_retirement(entry,record,action,observation,plan,time.time())
    save(Path(root)/('watcher-retirement-evidence-'+action['name']+'-'+uuid.uuid4().hex+'.json'),dict(record_sha256=c.digest(record),source_sha256=__import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest(),observation=observation,identity_limit='Exact named-resource custody; ETag is a revision; activity history can lag; no immutable GUID or atomic If-Match claim'))
    return observation


def begin_retire(state,packet,plan,record,observed,all_vm_observations,export_sha,now):
    entry=state['reservations'][packet['attempt_id']];row=entry.get('external_custody',{}).get(record['id'],{})
    c.need(row.get('record_sha256')==c.digest(record),'recorded_external_custody_required')
    action=action_for(entry,plan,record)
    if record['cloud']=='azure' and record['kind']=='watcher':verify_watcher_retirement(entry,record,action,observed,plan,now)
    else:verify_owned(record,action,observed,plan,now)
    c.need(not observed['absent'],'external_absent_reconcile_only')
    verify_parent_contents(record,action,observed)
    if record['kind'] not in ('vm','disk','implicit-disk'):
        for launch in (a for a in plan['actions'] if a['kind']=='vm'):
            original=entry.get('external_actions',{}).get(launch['name'],{})
            if not original:continue
            c.need(original.get('state') in ('observed','rejected'),'unknown_external_compute_keeps_network')
            c.need(original.get('state')=='rejected' or launch['id'] in entry['external_custody'],'unrecorded_external_compute_keeps_network')
        for item in entry['external_custody'].values():
            if item['record']['kind']=='vm':
                sample=all_vm_observations.get(item['record']['id'],{})
                c.need(sample.get('query_succeeded') and sample.get('absent') and 0<=now-sample['observed_at']<=30,'external_vm_keeps_network')
    all_actions=plan['actions']+[a for a in entry.get('mesh_binding',{}).get('actions',[]) if 'cloud' in a]
    for child in all_actions:
        if action['name'] not in child.get('depends',[]):continue
        if child['id'] not in entry.get('external_custody',{}):
            c.need(child['name'] not in entry.get('external_actions',{}),'unknown_child_keeps_parent');continue
        sample=all_vm_observations.get(child['id'],{})
        c.need(sample.get('query_succeeded') and sample.get('absent') and 0<=now-sample['observed_at']<=30,'external_child_keeps_parent')
    if record['kind'] in ('disk','implicit-disk'):
        raw=observed['raw'];c.need(not raw.get('users') and not raw.get('managedBy') and raw.get('properties',{}).get('diskState','Unattached')=='Unattached','external_disk_still_attached')
    name='retire-'+c.digest(record)[:24];journal=entry.setdefault('external_cleanup',{})
    c.need(name not in journal,'external_cleanup_already_sent')
    journal[name]=dict(state='sent',record_sha256=c.digest(record),observation_sha256=c.digest(observed),export_sha256=export_sha,sent_at=now)
    state['revision']+=1
    return name,action


def retire_once(root,packet,plan,record,observation,all_vm_observations,export_root,manifest,api):
    sha=life.verify_export(export_root,manifest,[record['id']])
    if record['cloud']=='azure' and record['kind']=='watcher':
        observation=watcher_retirement_observation(root,packet,plan,record,api)
    if record['kind']=='vm':
        entry=c.read_private(Path(root)/'campaign.json')['reservations'][packet['attempt_id']]
        raw=observation['raw'];slot=next(n for n in plan['nodes'] if n['id']==record['id'])
        if record['cloud']=='gcp':
            attached=[google_path(d['source']) for d in raw.get('disks',[])]
        else:
            profile=raw['properties']['storageProfile'];c.need(profile.get('dataDisks',[])==[],'foreign_vm_disks_preserved')
            attached=[profile['osDisk']['managedDisk']['id']]
        c.need(len(attached)==1 and attached[0].lower()==slot['disk_id'].lower(),'foreign_vm_disks_preserved')
        disk=entry.get('external_custody',{}).get(slot['disk_id'],{});c.need(disk.get('record_sha256')==c.digest(disk.get('record')),'attached_disk_custody_required')
        disk_action=action_for(entry,plan,disk['record']);disk_obs=api.observe(disk_action)
        verify_owned(disk['record'],disk_action,disk_obs,plan,time.time());c.need(not disk_obs['absent'],'attached_disk_observation_required')
        life.verify_export(export_root,manifest,[record['id'],slot['disk_id']])
    if record['kind']=='group':
        children=api.request('azure','GET',AZ+record['id']+'/resources?api-version='+VERSIONS['group'])
        c.need(children['status']==200 and children['body'].get('value')==[] and not children['body'].get('nextLink'),
               'nonempty_group_preserved')
    name,action=c.transaction(root,lambda s:begin_retire(s,packet,plan,record,observation,all_vm_observations,sha,time.time()))
    result=api.request(record['cloud'],'DELETE',action.get('read_url',action['url']))
    save(Path(root)/('external-cleanup-'+name+'.json'),result)
    def finish(s):
        row=s['reservations'][packet['attempt_id']]['external_cleanup'][name]
        row.update(state='returned' if result['status'] in (200,202,204) else 'unknown',response_sha256=c.digest(result));s['revision']+=1
    c.transaction(root,finish);c.need(result['status'] in (200,202,204),'external_cleanup_requires_reconciliation')
    return result


def confirm_absence(state,packet,record,observations):
    life.verify_absence(observations,[record['id']]);entry=state['reservations'][packet['attempt_id']]
    row=entry['external_custody'][record['id']];c.need(row['record_sha256']==c.digest(record),'external_custody_changed')
    row.update(disposition='absent',absence_sha256=c.digest(observations));state['revision']+=1


def stop_once(root,packet,plan,record,observation,api):
    """Finite guard may stop compute without destroying unexported evidence."""
    c.need(record['kind']=='vm' and time.time()>=c.stamp(packet['deadline']),'expired_owned_vm_required')
    entry=c.read_private(Path(root)/'campaign.json')['reservations'][packet['attempt_id']]
    c.need(entry['external_custody'][record['id']]['record_sha256']==c.digest(record),'owned_vm_required')
    action=action_for(entry,plan,record);verify_owned(record,action,observation,plan,time.time())
    if observation['absent']:return {'already_absent':True}
    name='guard-stop-'+c.digest(record)[:24];path=Path(root)/(name+'.intent.json')
    save(path,dict(record_sha256=c.digest(record),observation_sha256=c.digest(observation),at=time.time()))
    url=(AZ+record['id']+'/deallocate?api-version='+VERSIONS['compute']) if record['cloud']=='azure' else GC+record['id']+'/stop'
    result=api.request(record['cloud'],'POST',url,{})
    save(Path(root)/(name+'.result.json'),result);c.need(result['status'] in (200,202),'guard_stop_requires_reconciliation')
    return result


def require_guard(root,packet):
    h=c.read_private(Path(root)/'external-guard-live.json');now=time.time()
    c.need(h.get('packet_sha256')==c.digest(packet) and 0<=now-h.get('at',0)<=15,'live_finite_guard_required')
    pid=h.get('pid');c.need(type(pid) is int and pid>1,'live_finite_guard_required')
    os.kill(pid,0)
    check=subprocess.run(['ps','-p',str(pid),'-o','uid=','-o','command='],capture_output=True,text=True,timeout=5)
    fields=check.stdout.strip().split(maxsplit=1)
    c.need(check.returncode==0 and len(fields)==2 and fields[0]==str(os.getuid())
           and str(Path(__file__).with_name('external_guard.py'))+' --root '+str(root) in fields[1],'live_finite_guard_required')


def operation_complete(root,packet,action,api):
    """Read the original asynchronous operation; never repeat its mutation."""
    result=c.read_private(Path(root)/('external-'+action['name']+'.response.json'))
    if action['cloud']=='gcp':
        link=result['body'].get('selfLink');c.need(link,'original_operation_required')
        current=api.request('gcp','GET',GC+google_path(link));body=current['body']
        c.need(current['status']==200 and body.get('id')==result['body'].get('id'),'original_operation_changed')
        save(Path(root)/('operation-'+action['name']+'-'+uuid.uuid4().hex+'.json'),current)
        if body.get('status')!='DONE':return False
        c.need(not body.get('error'),'original_operation_failed')
    else:
        headers={k.lower():v for k,v in result.get('headers',{}).items()};url=headers.get('azure-asyncoperation')
        if url:
            current=api.request('azure','GET',url);body=current['body']
            c.need(current['status']==200,'original_operation_unavailable')
            save(Path(root)/('operation-'+action['name']+'-'+uuid.uuid4().hex+'.json'),current)
            if body.get('status') in ('InProgress','Running','Accepted'):return False
            c.need(body.get('status')=='Succeeded','original_operation_failed')
        else:current=result
    def observed(s):
        row=s['reservations'][packet['attempt_id']]['external_actions'][action['name']]
        c.need(row['state']=='returned','returned_original_operation_required')
        row.update(operation_verified=True,operation_receipt_sha256=c.digest(current));s['revision']+=1
    c.transaction(root,observed);return True


def adopt_for_guard(root,packet,plan,action,observation):
    """Bind a possibly successful original VM create for stop/export only.

    Does not clear uncertainty or authorize further creates/provider work.
    """
    c.need(action in plan['actions'] and action['kind']=='vm','frozen_vm_slot_required')
    actual=identity(action,observation,plan);raw=observation['raw'];body=action['body']
    if action['cloud']=='gcp':
        created=c.stamp(raw['creationTimestamp'])
        c.need(google_path(raw['machineType']).endswith('/'+body['machineType'])
               and raw['networkInterfaces'][0]['networkIP']==body['networkInterfaces'][0]['networkIP']
               and [google_path(d['source']) for d in raw['disks']]==[google_path(d['source']) for d in body['disks']], 'original_vm_shape_changed')
    else:
        props=raw['properties'];created=c.stamp(props['timeCreated'])
        c.need(props['hardwareProfile']==body['properties']['hardwareProfile']
            and props['storageProfile']['imageReference']['version']==body['properties']['storageProfile']['imageReference']['version']
            and [n['id'].lower() for n in props['networkProfile']['networkInterfaces']]==[n['id'].lower() for n in body['properties']['networkProfile']['networkInterfaces']], 'original_vm_shape_changed')
    def adopt(s):
        entry=s['reservations'][packet['attempt_id']];original=entry.get('external_actions',{}).get(action['name'],{})
        c.need(entry['packet_sha256']==c.digest(packet) and original.get('action_sha256')==c.digest(action)
            and original.get('baseline_sha256') and original.get('state') in ('sent','unknown','returned','observed')
            and created>=original['sent_at']-5,'original_vm_creation_required')
        custody=entry.setdefault('external_custody',{});prior=custody.get(actual['id'])
        if prior:
            c.need(prior['record']['immutable_id']==actual['immutable_id'],'external_incarnation_changed');return prior['record']
        actual['guard_adoption_only']=True
        custody[actual['id']]=dict(record=actual,record_sha256=c.digest(actual));s['revision']+=1;return actual
    rec=c.transaction(root,adopt);save(Path(root)/('guard-adoption-'+action['name']+'-'+uuid.uuid4().hex+'.json'),observation);return rec


def stopped_observation(root,packet,plan,record,api):
    """202 is only acceptance: require the original stop and actual billing state."""
    entry=c.read_private(Path(root)/'campaign.json')['reservations'][packet['attempt_id']]
    action=action_for(entry,plan,record);obs=api.observe(action);verify_owned(record,action,obs,plan,time.time())
    if obs['absent']:return {'stopped':False,'absent':True,'observation':obs}
    path=Path(root)/('guard-stop-'+c.digest(record)[:24]+'.result.json')
    if path.exists():
        receipt=c.read_private(path);headers={k.lower():v for k,v in receipt.get('headers',{}).items()}
        url=headers.get('azure-asyncoperation') or headers.get('location') if record['cloud']=='azure' else receipt.get('body',{}).get('selfLink')
        if url:
            if record['cloud']=='gcp':url=GC+google_path(url)
            op=api.request(record['cloud'],'GET',url)
            if op['status']==202:return {'stopped':False,'operation_pending':True}
            c.need(op['status']==200 and not op['body'].get('error'),'original_stop_operation_failed')
            status=op['body'].get('status')
            if status not in (None,'Succeeded','DONE'):return {'stopped':False,'operation_pending':True}
    if record['cloud']=='gcp':
        return dict(stopped=obs['raw'].get('status')=='TERMINATED',state=obs['raw'].get('status'),observation=obs)
    view=api.request('azure','GET',AZ+record['id']+'/instanceView?api-version='+VERSIONS['compute'])
    c.need(view['status']==200,'azure_power_state_unavailable')
    states=[s['code'] for s in view['body'].get('statuses',[]) if s.get('code','').startswith('PowerState/')]
    return dict(stopped=states==['PowerState/deallocated'],power_states=states,observation=obs,instance_view=view)
