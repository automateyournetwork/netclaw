"""Once-frozen Stage5 endpoint binding. No broad or mutable peer allowlists."""
import ipaddress
import re
import time
import campaign as c
import external
import lifecycle as life

RECIPE='spec199-nine-host-six-foreign-peers-7445-v1'


def verify_bound_authorities(bindings):
    from matrix import contracts
    _,verify,_=contracts();clusters=set();anchors=set();node_ids=set()
    c.need(set(bindings.get('authorities',{}))=={'aws','azure','gcp'},'three_signed_authorities_required')
    for cloud,pin in bindings['authorities'].items():
        m=verify(pin['manifest'],pin['anchor_certificate'],expected_key_id=pin['anchor_key_id'])
        c.need(c.digest(pin['manifest'])==bindings['manifests'][cloud] and len(m.nodes)==3
               and m.cluster_id not in clusters and m.anchor_key_id not in anchors,'separate_signed_authorities_required')
        clusters.add(m.cluster_id);anchors.add(m.anchor_key_id)
        hosts=[n for n in bindings['nodes'] if n['cloud']==cloud]
        c.need({n['node_id'] for n in hosts}=={n['node_id'] for n in m.nodes},'bound_manifest_hosts_changed')
        for host in hosts:
            n=next(n for n in m.nodes if n['node_id']==host['node_id'])
            c.need(n['node_id'] not in node_ids and n['endpoints']['https']=='https://'+host['dns'], 'bound_manifest_endpoint_changed')
            node_ids.add(n['node_id'])


def child_actions(packet,plan,bindings):
    c.need(packet['stage']==5 and packet.get('mesh_recipe')==RECIPE,'mesh_recipe_required')
    c.need(bindings['packet_sha256']==c.digest(packet) and bindings['external_plan_sha256']==c.digest(plan),'mesh_parent_changed')
    nodes=bindings['nodes'];c.need(len(nodes)==len({n['key'] for n in nodes})==9,'nine_distinct_hosts_required')
    c.need(len({n['public'] for n in nodes})==9 and all(ipaddress.ip_address(n['public']).is_global for n in nodes),'distinct_public_hosts_required')
    c.need(set(bindings['manifests'])=={'aws','azure','gcp'} and len(set(bindings['manifests'].values()))==3
           and all(re.fullmatch('[a-f0-9]{64}',v) for v in bindings['manifests'].values()),'three_separate_manifests_required')
    c.need(all(len([n for n in nodes if n['cloud']==cl])==3 for cl in ('aws','azure','gcp')),'three_hosts_each_cloud_required')
    actions=[]
    for n in nodes:
        peers=sorted(p['public']+'/32' for p in nodes if p['cloud']!=n['cloud']);c.need(len(peers)==6,'six_foreign_peers_required')
        if n['cloud']=='aws':
            for direction in ('ingress','egress'):
                actions.append(dict(name=n['code']+'-mesh-'+direction,service='ec2',operation='authorize-security-group-'+direction,region=n['region'],
                    request={'GroupId':n['security_group_id'],'IpPermissions':[{'IpProtocol':'tcp','FromPort':7445,'ToPort':7445,'IpRanges':[{'CidrIp':ip,'Description':'Frozen Spec199 peer'} for ip in peers]}]}))
        elif n['cloud']=='azure':
            rid=n['nsg_id']+'/securityRules/final-mesh'
            actions.append(dict(name=n['key']+'-mesh',cloud='azure',kind='mesh-rule',id=rid,url=external.AZ+rid+'?api-version='+external.VERSIONS['network'],method='PUT',depends=[n['key']+'-nsg'],body={'properties':dict(priority=120,protocol='Tcp',access='Allow',direction='Inbound',sourcePortRange='*',sourceAddressPrefixes=peers,destinationAddressPrefix='*',destinationPortRange='7445')}))
    peers=sorted(n['public']+'/32' for n in nodes if n['cloud']!='gcp');collection='/projects/'+plan['gcp_project']+'/global/firewalls';name=packet['run_id']+'-final-mesh'
    actions.append(dict(name='gcp-final-mesh',cloud='gcp',kind='firewall',id=collection+'/'+name,url=external.GC+collection,read_url=external.GC+collection+'/'+name,method='POST',depends=['gcp-network'],body=dict(name=name,description=plan['description'],network=external.GC+'/projects/'+plan['gcp_project']+'/global/networks/'+packet['run_id'],direction='INGRESS',priority=1000,sourceRanges=peers,targetTags=[packet['run_id']],allowed=[{'IPProtocol':'tcp','ports':['7445']}])))
    return actions


def freeze(state,packet,plan,bindings,now):
    c.validate_packet(state,packet,now)
    entry=state['reservations'][packet['attempt_id']]
    c.need(entry['packet_sha256']==c.digest(packet) and entry['state']=='sent','active_mesh_reservation_required')
    c.need('mesh_binding' not in entry,'mesh_binding_already_frozen')
    c.need(packet.get('external_plan_sha256')==c.digest(plan),'external_plan_changed')
    external_nodes={n['key']:n for n in plan['nodes']}
    c.need(all(entry.get('external_actions',{}).get(a['name'],{}).get('state')=='observed' for a in plan['actions']),
           'unresolved_external_actions')
    c.need(all(entry.get('actions',{}).get(name,{}).get('state')=='observed' for name in packet['actions']),
           'unresolved_aws_actions')
    verify_bound_authorities(bindings)
    for node in bindings['nodes']:
        obs=node['observation'];c.need(obs['query_succeeded'] and obs['absent'] is False
            and 0<=now-obs['observed_at']<=30 and c.digest(obs['raw'])==obs['raw_sha256'],'fresh_bound_host_required')
        if node['cloud']=='aws':
            row=entry['custody'].get(node['id'],{});rec=row.get('record',{})
            c.need(row.get('record_sha256')==c.digest(rec) and rec.get('kind')=='instance'
                   and rec.get('origin_action')==node['code']+'-instance' and rec.get('region')==node['region'],'owned_bound_host_required')
            raw=obs['raw'];c.need(raw.get('InstanceId')==node['id'] and raw.get('PublicIpAddress')==node['public']
                and raw.get('PrivateIpAddress')==node['internal'] and raw.get('Placement',{}).get('AvailabilityZone')==node['zone'],'bound_host_changed')
            groups=[r['record']['id'] for r in entry['custody'].values() if r['record'].get('origin_action')==node['code']+'-security-group']
            c.need(groups==[node['security_group_id']],'bound_security_group_changed')
            life.ownership(rec,obs,packet['account'],node['region'],packet['run_id'],5)
            c.need(raw.get('State',{}).get('Name')=='running' and raw['Placement'].get('AvailabilityZoneId')==packet.get('zones',{}).get(node['zone']),
                   'running_exact_az_required')
        else:
            slot=external_nodes[node['key']];c.need(slot['id']==node['id'] and slot['region']==node['region'],'bound_host_changed')
            rec=entry['external_custody'][node['id']]['record'];action=next(a for a in plan['actions'] if a['name']==slot['vm_action'])
            actual=external.identity(action,obs,plan);c.need(actual['immutable_id']==rec['immutable_id'],'bound_incarnation_changed')
            raw=obs['raw']
            if node['cloud']=='gcp':
                nic=raw['networkInterfaces'][0];c.need(raw.get('status')=='RUNNING' and nic['networkIP']==node['internal'] and nic['accessConfigs'][0]['natIP']==node['public'],'bound_address_changed')
            else:
                c.need(raw['properties'].get('provisioningState')=='Succeeded','running_external_host_required')
                c.need(node['nsg_id']==slot['nsg_id'],'bound_security_group_changed')
                ip=node['ip_observation'];c.need(ip['query_succeeded'] and not ip['absent'] and 0<=now-ip['observed_at']<=30
                    and c.digest(ip['raw'])==ip['raw_sha256'] and ip['raw'].get('id','').lower()==slot['ip_id'].lower()
                    and ip['raw']['properties']['ipAddress']==node['public'],'bound_address_changed')
                nic=node['nic_observation'];c.need(nic['query_succeeded'] and not nic['absent'] and 0<=now-nic['observed_at']<=30
                    and c.digest(nic['raw'])==nic['raw_sha256'] and nic['raw'].get('id','').lower()==slot['nic_id'].lower()
                    and nic['raw']['properties']['ipConfigurations'][0]['properties']['privateIPAddress']==node['internal']
                    and raw['properties']['networkProfile']['networkInterfaces'][0]['id'].lower()==slot['nic_id'].lower(),'bound_address_changed')
                interface=nic['raw']['properties'];conf=interface['ipConfigurations'][0]['properties']
                c.need(interface['networkSecurityGroup']['id'].lower()==slot['nsg_id'].lower()
                       and conf['subnet']['id'].lower()==(slot['vnet_id']+'/subnets/owned').lower()
                       and conf['publicIPAddress']['id'].lower()==slot['ip_id'].lower(),'bound_nic_attachments_changed')
                for kind,sample in [('ip',ip),('nic',nic)]:
                    a=next(a for a in plan['actions'] if a['name']==slot['key']+'-'+kind)
                    external.verify_owned(entry['external_custody'][a['id']]['record'],a,sample,plan,now)
    actions=child_actions(packet,plan,bindings)
    entry['mesh_binding']={'value':bindings,'sha256':c.digest(bindings),'actions':actions,'actions_sha256':c.digest(actions)}
    state['revision']+=1
    return c.digest(bindings)


def authorized(entry,packet):
    row=entry.get('mesh_binding',{})
    c.need(packet.get('mesh_recipe')==RECIPE and row.get('sha256')==c.digest(row.get('value'))
           and row['value']['packet_sha256']==c.digest(packet) and row.get('actions_sha256')==c.digest(row.get('actions')),'mesh_binding_changed')
    return {a['name']:a for a in row['actions']}
