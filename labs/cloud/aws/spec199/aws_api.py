"""Read-only AWS observations and creation provenance for the private lifecycle."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import uuid
import campaign as c
import lifecycle as life
from preflight import save

READS = {('sts','get-caller-identity'),('ec2','describe-instances'),('ec2','describe-volumes'),
    ('ec2','describe-network-interfaces'),('ec2','describe-key-pairs'),('ec2','describe-vpcs'),
    ('ec2','describe-subnets'),('ec2','describe-security-groups'),('ec2','describe-route-tables'),
    ('ec2','describe-internet-gateways'),('ec2','describe-vpc-peering-connections'),('ec2','get-console-output'),
    ('iam','get-role'),('iam','get-role-policy'),('iam','list-role-policies'),
    ('iam','list-attached-role-policies'),('iam','list-instance-profiles-for-role'),
    ('scheduler','get-schedule'),('scheduler','get-schedule-group'),
    ('scheduler','list-tags-for-resource'),('scheduler','list-schedules')}
EC2 = {
    'instance':('describe-instances','InstanceIds','Reservations','InstanceId','InvalidInstanceID.NotFound'),
    'volume':('describe-volumes','VolumeIds','Volumes','VolumeId','InvalidVolume.NotFound'),
    'eni':('describe-network-interfaces','NetworkInterfaceIds','NetworkInterfaces','NetworkInterfaceId','InvalidNetworkInterfaceID.NotFound'),
    'key-pair':('describe-key-pairs','KeyPairIds','KeyPairs','KeyPairId','InvalidKeyPair.NotFound'),
    'vpc':('describe-vpcs','VpcIds','Vpcs','VpcId','InvalidVpcID.NotFound'),
    'subnet':('describe-subnets','SubnetIds','Subnets','SubnetId','InvalidSubnetID.NotFound'),
    'security-group':('describe-security-groups','GroupIds','SecurityGroups','GroupId','InvalidGroup.NotFound'),
    'route-table':('describe-route-tables','RouteTableIds','RouteTables','RouteTableId','InvalidRouteTableID.NotFound'),
    'internet-gateway':('describe-internet-gateways','InternetGatewayIds','InternetGateways','InternetGatewayId','InvalidInternetGatewayID.NotFound'),
    'vpc-peering':('describe-vpc-peering-connections','VpcPeeringConnectionIds','VpcPeeringConnections','VpcPeeringConnectionId','InvalidVpcPeeringConnectionID.NotFound'),
}
ORIGINS = {
    'vpc':('vpc','Vpc.VpcId'),'subnet':('subnet','Subnet.SubnetId'),
    'internet-gateway':('igw','InternetGateway.InternetGatewayId'),
    'route-table':('route-table','RouteTable.RouteTableId'),
    'security-group':('security-group','GroupId'),'key-pair':('key','KeyPairId'),
    'instance':('instance','Instances.0.InstanceId'), 'role':('stop-role','Role.RoleId'),
    'schedule-group':('stop-group','ScheduleGroupArn'), 'schedule':('stop-schedule','ScheduleArn'),
}


class QueryError(RuntimeError):
    def __init__(self, code): self.code=code;super().__init__(code)


class ReadAPI:
    def __init__(self, profile, region, root, invoke=None):
        self.profile,self.region,self.root=profile,region,c.owned_directory(Path(root))
        self.invoke=invoke or subprocess.run

    def read(self, service, operation, request=None):
        c.need((service,operation) in READS,'read_operation_not_allowed')
        stem='read-'+str(uuid.uuid4());path=self.root/(stem+'-request.json')
        save(path,request or {})
        result=self.invoke(['aws',service,operation,'--profile',self.profile,'--region',self.region,
            '--cli-input-json','file://'+str(path),'--output','json','--no-cli-pager',
            '--cli-connect-timeout','8','--cli-read-timeout','20'],capture_output=True,text=True,
            timeout=60,check=False,env=dict(os.environ,AWS_MAX_ATTEMPTS='1',AWS_PAGER=''))
        save(self.root/(stem+'-response.json'),{'returncode':result.returncode,'stdout':result.stdout,
            'stderr':result.stderr,'observed_at':datetime.now(timezone.utc).isoformat()})
        if result.returncode:
            match=re.search(r'An error occurred \(([^)]+)\)',result.stderr)
            raise QueryError(match[1] if match else 'unclassified_read_failure')
        return json.loads(result.stdout or '{}')

    def account(self): return self.read('sts','get-caller-identity')['Account']

    def observe(self, record, account):
        c.need(record['account']==account and record['region']==self.region,'observation_scope_mismatch')
        kind=record['kind'];base={'id':record['id'],'kind':kind,'account':account,'region':self.region,
            'query_succeeded':True,'observed_at':datetime.now(timezone.utc).timestamp()}
        try:
            if kind in EC2:
                op,field,collection,id_field,_=EC2[kind]
                data=self.read('ec2',op,{field:[record['id']]});rows=data[collection]
                if kind=='instance':rows=[v for row in rows for v in row['Instances']]
                c.need(len(rows)==1 and rows[0][id_field]==record['id'],'exact_observation_required')
                raw=rows[0]
                state=raw.get('Status' if kind in ('eni','vpc-peering') else 'State')
                if isinstance(state,dict):state=state.get('Code' if kind=='vpc-peering' else 'Name')
                absent=(kind=='instance' and state=='terminated') or (kind=='vpc-peering' and state=='deleted')
                base.update(absent=absent,state=state,default=raw.get('IsDefault',False) or raw.get('GroupName')=='default',
                    attachments=raw.get('Attachments',[]),attachment=raw.get('Attachment'),
                    associations=raw.get('Associations',[]),tags={t['Key']:t['Value'] for t in
                        raw.get('TagSet' if kind=='eni' else 'Tags',[])})
            elif kind=='role':
                raw=self.read('iam','get-role',{'RoleName':record['name']})['Role']
                c.need(raw['RoleId']==record['id'],'immutable_role_id_mismatch')
                base.update(name=raw['RoleName'],created_at=raw['CreateDate'],absent=False,
                    tags={t['Key']:t['Value'] for t in raw.get('Tags',[])},
                    inline_policies=self.read('iam','list-role-policies',{'RoleName':record['name']})['PolicyNames'],
                    attached_policies=self.read('iam','list-attached-role-policies',{'RoleName':record['name']})['AttachedPolicies'],
                    instance_profiles=self.read('iam','list-instance-profiles-for-role',{'RoleName':record['name']})['InstanceProfiles'])
                if base['inline_policies']==['StopOwnedInstance']:
                    base['policy_document']=self.read('iam','get-role-policy',{'RoleName':record['name'],
                        'PolicyName':'StopOwnedInstance'})['PolicyDocument']
            elif kind in ('schedule','schedule-group'):
                req={'Name':record['name']}
                if kind=='schedule':req['GroupName']=record['group']
                raw=self.read('scheduler','get-'+kind,req)
                c.need(raw['Arn']==record['id'],'schedule_arn_mismatch')
                tag_arn=record['group_arn'] if kind=='schedule' else record['id']
                base.update(name=raw['Name'],created_at=raw['CreationDate'],absent=False,
                    tags={t['Key']:t['Value'] for t in self.read('scheduler','list-tags-for-resource',{'ResourceArn':tag_arn})['Tags']})
                if kind=='schedule':base['group']=raw['GroupName']
                else:base['schedules']=self.read('scheduler','list-schedules',{'GroupName':record['name']})['Schedules']
            else:raise ValueError('unsupported_observation_kind')
        except QueryError as exc:
            expected=EC2[kind][4] if kind in EC2 else 'NoSuchEntity' if kind=='role' else 'ResourceNotFoundException'
            if exc.code!=expected:raise
            return dict(base,absent=True)
        base.update(raw=raw,raw_sha256=c.digest(raw),observed_at=datetime.now(timezone.utc).timestamp())
        return base


def record_creation(state, packet, kind, observed, baseline_ids, descriptor=None):
    """Only an ID from this attempt's observed creation can enter cleanup custody."""
    entry=state['reservations'][packet['attempt_id']]
    c.need(entry['packet_sha256']==c.digest(packet),'reservation_mismatch')
    namespace='';region=packet['region']
    if descriptor is None:
        c.need(kind in ORIGINS,'unsupported_creation_kind');origin,path=ORIGINS[kind]
    else:
        c.need(packet.get('resource_origins',{}).get(descriptor['key'])==descriptor
               and descriptor['kind']==kind,'frozen_creation_descriptor_required')
        origin,path=descriptor['action'],descriptor['path'];namespace=descriptor.get('namespace','')
        region=life.packet_region(packet,descriptor['region'])
    journal=entry['actions']
    identity=life.resolve({'$ref':origin+'.'+path},journal)
    c.need(identity not in baseline_ids,'baseline_resource_refused')
    record={'kind':kind,'id':identity,'account':packet['account'],'region':region,
            'run_id':packet['run_id'],'stage':packet['stage'],
            'create_request_sha256':journal[origin]['resolved_request_sha256']}
    if descriptor is not None:
        c.need(journal[origin].get('region')==region,'creation_region_changed')
        record.update(origin_action=origin,journal_namespace=namespace)
        if kind=='route-table':record['vpc_cidr']=descriptor['vpc_cidr']
        if kind=='vpc-peering':
            request=journal[origin]['request']
            c.need(c.digest(request)==journal[origin]['resolved_request_sha256'],'creation_request_changed')
            record.update(requester_vpc=request['VpcId'],accepter_vpc=request['PeerVpcId'],
                          peer_region=request['PeerRegion'])
    if kind in ('role','schedule','schedule-group'):
        record.update(name=observed['name'],created_at=observed['created_at'])
    if kind=='schedule':record.update(group=observed['group'],group_arn=life.resolve({'$ref':namespace+'stop-group.ScheduleGroupArn'},journal))
    life.ownership(record,observed,packet['account'],region,packet['run_id'],packet['stage'])
    c.need(observed.get('query_succeeded') is True and observed.get('absent') is False,'created_resource_observation_required')
    custody=entry.setdefault('custody',{})
    c.need(identity not in custody,'custody_already_recorded')
    custody[identity]={'record':record,'record_sha256':c.digest(record),'observation_sha256':c.digest(observed),'disposition':'present'}
    state['revision']+=1
    return record


def record_instance_dependents(state, packet, instance_observed, observations, baseline_ids):
    """Record the root disks/ENIs actually attached to the positively owned VM."""
    entry=state['reservations'][packet['attempt_id']]
    c.need(entry['packet_sha256']==c.digest(packet),'reservation_mismatch')
    parent=entry.get('custody',{}).get(instance_observed['id'],{}).get('record')
    c.need(parent and parent['kind']=='instance','owned_instance_required')
    region=life.packet_region(packet,parent['region'])
    life.ownership(parent,instance_observed,packet['account'],region,packet['run_id'],packet['stage'])
    raw=instance_observed['raw']
    c.need(c.digest(raw)==instance_observed['raw_sha256'],'instance_observation_changed')
    expected={('volume',x['Ebs']['VolumeId']) for x in raw.get('BlockDeviceMappings',[]) if 'Ebs' in x}
    expected|={('eni',x['NetworkInterfaceId']) for x in raw.get('NetworkInterfaces',[])}
    c.need(any(kind=='volume' for kind,_ in expected) and any(kind=='eni' for kind,_ in expected),
           'root_volume_and_interface_not_yet_observed')
    c.need(expected and {(o['kind'],o['id']) for o in observations}==expected,'complete_dependent_inventory_required')
    result=[]
    for obs in observations:
        c.need(obs['id'] not in baseline_ids,'baseline_resource_refused')
        record={'kind':obs['kind'],'id':obs['id'],'account':packet['account'],'region':region,
            'run_id':packet['run_id'],'stage':packet['stage'],'create_request_sha256':parent['create_request_sha256'],
            'parent_instance':parent['id'],'depends_on_absence':[parent['id']]}
        life.ownership(record,obs,packet['account'],region,packet['run_id'],packet['stage'])
        c.need(obs['query_succeeded'] and not obs['absent'],'live_dependent_required')
        c.need(obs['id'] not in entry['custody'],'custody_already_recorded')
        entry['custody'][obs['id']]={'record':record,'record_sha256':c.digest(record),
            'observation_sha256':c.digest(obs),'disposition':'present'}
        result.append(record)
    entry['custody'][parent['id']]['dependents_recorded']=True
    state['revision']+=1
    return result
