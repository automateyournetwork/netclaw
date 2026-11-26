"""Pure first-stage AWS plan. All writes are executed by the once-only journal."""
import base64
from datetime import datetime, timezone
import ipaddress
import re
import campaign as c
import watchdog


def first_border(account, region, zone, prefix, deadline, client_token, ami, operator_cidr, public_key, instance_type, stage=1):
    c.need(type(stage) is int and stage in (1,2,3), 'single_host_stage_required')
    c.need(region == 'us-east-2' and zone in {region+x for x in 'abc'}, 'first_stage_ohio_required')
    return _border(account, region, zone, prefix, deadline, client_token, ami,
                   operator_cidr, public_key, instance_type, stage)


def _border(account, region, zone, prefix, deadline, client_token, ami, operator_cidr,
            public_key, instance_type, stage, vpc_cidr='10.199.11.0/24',
            subnet_cidr='10.199.11.0/26', private_ip=None):
    """Pure shared template. Regional callers must validate the complete region set."""
    c.need(re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d', region)
           and re.fullmatch(re.escape(region)+r'[a-z]', zone), 'region_zone_mismatch')
    vpc_network=ipaddress.ip_network(vpc_cidr,strict=True)
    subnet_network=ipaddress.ip_network(subnet_cidr,strict=True)
    c.need(vpc_network.version==4 and vpc_network.subnet_of(ipaddress.ip_network('10.199.0.0/16'))
           and subnet_network.subnet_of(vpc_network), 'owned_network_required')
    if private_ip is not None:
        address=ipaddress.ip_address(private_ip)
        c.need(address in subnet_network and 4<=int(address)-int(subnet_network.network_address)
               <subnet_network.num_addresses-1, 'usable_private_host_required')
    c.need(re.fullmatch(r'ami-[0-9a-f]{17}', ami), 'pinned_image_required')
    c.need(instance_type in ('m7i.large','m7i-flex.large'),'reviewed_eight_gib_type_required')
    address = ipaddress.ip_network(operator_cidr, strict=True)
    c.need(address.version == 4 and address.prefixlen == 32 and address.network_address.is_global,
           'single_public_operator_address_required')
    c.need(re.fullmatch(r'[A-Za-z0-9_-]{16,64}', client_token), 'client_token_required')
    c.need(public_key.startswith('ssh-ed25519 ') and '\n' not in public_key.strip(), 'ephemeral_ed25519_key_required')
    guards = watchdog.stop_actions(account, region, prefix, deadline, stage=stage)
    tags = [{'Key':key,'Value':value} for key,value in {
        'Name':prefix, 'netclaw-spec':'199', 'netclaw-run':prefix, 'netclaw-stage':str(stage)}.items()]
    def tagged(kind): return [{'ResourceType':kind,'Tags':tags}]
    def ref(path): return {'$ref':path}
    def action(name, operation, request):
        return {'name':name,'service':'ec2','operation':operation,'region':region,'request':request}
    vpc, subnet, igw, route, group = [ref(path) for path in (
        'vpc.Vpc.VpcId','subnet.Subnet.SubnetId','igw.InternetGateway.InternetGatewayId',
        'route-table.RouteTable.RouteTableId','security-group.GroupId')]
    cutoff = datetime.fromtimestamp(c.stamp(deadline), timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    # A fresh host receives a finite power-off timer before package/runtime work.
    # Cloud stop remains separate and root EBS is retained by stop for recovery.
    boot = f'''#!/bin/bash
set -euo pipefail
umask 077
cat >/etc/systemd/system/netclaw-199-deadline.service <<'UNIT'
[Unit]
Description=Spec199 finite owned host deadline
[Service]
Type=oneshot
ExecStart=/usr/bin/systemctl poweroff
UNIT
cat >/etc/systemd/system/netclaw-199-deadline.timer <<'UNIT'
[Unit]
Description=Spec199 finite owned host deadline
[Timer]
OnCalendar={cutoff}
Persistent=true
AccuracySec=1s
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now netclaw-199-deadline.timer
echo NETCLAW_199_HOST_KEYS_BEGIN >/dev/console
cat /etc/ssh/ssh_host_ed25519_key.pub >/dev/console
echo NETCLAW_199_HOST_KEYS_END >/dev/console
'''
    ingress = [{'IpProtocol':'tcp','FromPort':port,'ToPort':port,
                'IpRanges':[{'CidrIp':operator_cidr,'Description':'Exact owner client'}]} for port in (22,443,7444)]
    egress = [{'IpProtocol':'tcp','FromPort':port,'ToPort':port,'IpRanges':[{'CidrIp':'0.0.0.0/0'}]}
              for port in (80,443)]
    return guards[:2] + [
        action('vpc','create-vpc',{'CidrBlock':vpc_cidr,'InstanceTenancy':'default','TagSpecifications':tagged('vpc')}),
        action('subnet','create-subnet',{'VpcId':vpc,'CidrBlock':subnet_cidr,'AvailabilityZone':zone,'TagSpecifications':tagged('subnet')}),
        action('igw','create-internet-gateway',{'TagSpecifications':tagged('internet-gateway')}),
        action('igw-attach','attach-internet-gateway',{'VpcId':vpc,'InternetGatewayId':igw}),
        action('route-table','create-route-table',{'VpcId':vpc,'TagSpecifications':tagged('route-table')}),
        action('default-route','create-route',{'RouteTableId':route,'DestinationCidrBlock':'0.0.0.0/0','GatewayId':igw}),
        action('route-association','associate-route-table',{'RouteTableId':route,'SubnetId':subnet}),
        action('security-group','create-security-group',{'VpcId':vpc,'GroupName':prefix,
            'Description':'Spec199 owner only ingress and HTTPS bootstrap','TagSpecifications':tagged('security-group')}),
        action('egress-close','revoke-security-group-egress',{'GroupId':group,'IpPermissions':[
            {'IpProtocol':'-1','IpRanges':[{'CidrIp':'0.0.0.0/0'}]}]}),
        action('egress','authorize-security-group-egress',{'GroupId':group,'IpPermissions':egress}),
        action('ingress','authorize-security-group-ingress',{'GroupId':group,'IpPermissions':ingress}),
        action('key','import-key-pair',{'KeyName':prefix,'PublicKeyMaterial':base64.b64encode(public_key.strip().encode()).decode(),
                                     'TagSpecifications':tagged('key-pair')}),
        action('instance','run-instances',{'ImageId':ami,'InstanceType':instance_type,'MinCount':1,'MaxCount':1,
            'ClientToken':client_token,'KeyName':prefix,'Placement':{'AvailabilityZone':zone},
            'NetworkInterfaces':[{'DeviceIndex':0,'SubnetId':subnet,'Groups':[group],
                                  **({'PrivateIpAddress':private_ip} if private_ip is not None else {}),
                                  'AssociatePublicIpAddress':True,'DeleteOnTermination':True}],
            'MetadataOptions':{'HttpTokens':'required','HttpPutResponseHopLimit':1,'HttpEndpoint':'enabled','HttpProtocolIpv6':'disabled'},
            'InstanceInitiatedShutdownBehavior':'stop','DisableApiTermination':False,
            'BlockDeviceMappings':[{'DeviceName':'/dev/sda1','Ebs':{'VolumeSize':40,'VolumeType':'gp3',
                'Encrypted':True,'DeleteOnTermination':True}}],
            'UserData':base64.b64encode(boot.encode()).decode(),
            'TagSpecifications':tagged('instance')+tagged('volume')+tagged('network-interface')}),
    ] + guards[2:]
