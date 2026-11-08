# Inventory before (read-only, 2026-11-08)

Project netclaw-506315, account ptcapo@gmail.com. Only gcloud list/describe calls were used.

## Instances
```
NAME                  ZONE                       MACHINE_TYPE  STATUS   NAT_IP       LABELS
netclaw-r01-20261101  northamerica-northeast1-a  e2-small      RUNNING  34.95.60.45  expires=2026-12-01,goog-terraform-provisioned=true,roadmap=r01,spec=168
```
## Addresses
```
NAME                             ADDRESS/RANGE  TYPE      PURPOSE  NETWORK  REGION                   SUBNET  STATUS
netclaw-r01-20261101-primary     34.47.13.89    EXTERNAL                    northamerica-northeast1          RESERVED
netclaw-r01-20261101-relocation  34.95.60.45    EXTERNAL                    northamerica-northeast1          IN_USE
```
## Networks and subnets
```
NAME                  SUBNET_MODE  BGP_ROUTING_MODE  IPV4_RANGE  GATEWAY_IPV4  INTERNAL_IPV6_RANGE
default               AUTO         REGIONAL
netclaw-r01-20261101  CUSTOM       REGIONAL
NAME                  REGION                   NETWORK               RANGE
default               europe-west1             default               10.132.0.0/20
default               asia-southeast1          default               10.148.0.0/20
default               northamerica-northeast1  default               10.162.0.0/20
netclaw-r01-20261101  northamerica-northeast1  netclaw-r01-20261101  10.168.0.0/28
default               europe-west12            default               10.210.0.0/20
default               europe-west10            default               10.214.0.0/20
```
## Firewall rules
```
NAME                                 NETWORK               SOURCE_RANGES       ALLOW
default-allow-icmp                   default               0.0.0.0/0           icmp
default-allow-internal               default               10.128.0.0/9        tcp:0-65535,udp:0-65535,icmp
default-allow-rdp                    default               0.0.0.0/0           tcp:3389
default-allow-ssh                    default               0.0.0.0/0           tcp:22
netclaw-r01-20261101-iap             netclaw-r01-20261101  35.235.240.0/20     tcp:22
netclaw-r01-20261101-public-lab-hud  netclaw-r01-20261101  0.0.0.0/0           tcp:80,tcp:443
netclaw-r01-20261101-transport       netclaw-r01-20261101  142.120.176.129/32  tcp:42101,tcp:42102
```
## Disks
```
NAME                  LOCATION                   LOCATION_SCOPE  SIZE_GB  TYPE         STATUS
netclaw-r01-20261101  northamerica-northeast1-a  zone            20       pd-standard  READY
```
## Regional quotas (CPUS, IN_USE_ADDRESSES, STATIC_ADDRESSES, SSD/DISKS_TOTAL_GB)
```
northamerica-northeast1 {'CPUS': (1.0, 200.0), 'IN_USE_ADDRESSES': (1.0, 8.0), 'STATIC_ADDRESSES': (2.0, 8.0), 'DISKS_TOTAL_GB': (20.0, 4096.0)}
europe-west1 {'CPUS': (0.0, 200.0), 'IN_USE_ADDRESSES': (0.0, 8.0), 'STATIC_ADDRESSES': (0.0, 8.0), 'DISKS_TOTAL_GB': (0.0, 4096.0)}
asia-southeast1 {'CPUS': (0.0, 100.0), 'IN_USE_ADDRESSES': (0.0, 8.0), 'STATIC_ADDRESSES': (0.0, 8.0), 'DISKS_TOTAL_GB': (0.0, 4096.0)}
```
## e2-medium availability
```
e2-medium	northamerica-northeast1-a	2	4096
e2-medium	europe-west1-b	2	4096
e2-medium	asia-southeast1-a	2	4096
```
## Enabled APIs (compute, iap, billingbudgets)
```
billingbudgets.googleapis.com
cloudbilling.googleapis.com
compute.googleapis.com
iap.googleapis.com
```
