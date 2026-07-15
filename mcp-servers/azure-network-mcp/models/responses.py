"""Structured response models for Azure Network MCP Server."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional
import json


def to_dict(obj) -> dict:
    """Convert a dataclass to dict, filtering None values."""
    if hasattr(obj, '__dataclass_fields__'):
        return {k: to_dict(v) for k, v in asdict(obj).items() if v is not None}
    elif isinstance(obj, list):
        return [to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items() if v is not None}
    return obj


def to_json(obj) -> str:
    """Serialize a dataclass or list of dataclasses using GCF with JSON fallback."""
    if isinstance(obj, list):
        data = [to_dict(item) for item in obj]
    else:
        data = to_dict(obj)
    try:
        from utils.gcf_helper import gcf_dumps
        return gcf_dumps(data)
    except Exception:
        return json.dumps(data, indent=2)


# --- VNet Models ---

@dataclass
class Subnet:
    name: str
    id: str
    address_prefix: str
    nsg_id: Optional[str] = None
    nsg_name: Optional[str] = None
    route_table_id: Optional[str] = None
    route_table_name: Optional[str] = None
    delegations: list[str] = field(default_factory=list)
    service_endpoints: list[str] = field(default_factory=list)
    private_endpoints: list[str] = field(default_factory=list)
    provisioning_state: Optional[str] = None


@dataclass
class VNetPeering:
    name: str
    id: str
    remote_vnet_id: str
    peering_state: str
    allow_vnet_access: bool = True
    allow_forwarded_traffic: bool = False
    allow_gateway_transit: bool = False
    use_remote_gateways: bool = False


@dataclass
class VNet:
    name: str
    id: str
    resource_group: str
    location: str
    address_space: list[str] = field(default_factory=list)
    subnets: list[Subnet] = field(default_factory=list)
    peerings: list[VNetPeering] = field(default_factory=list)
    dns_servers: list[str] = field(default_factory=list)
    provisioning_state: Optional[str] = None
    tags: dict[str, str] = field(default_factory=dict)
    subnet_count: int = 0
    peering_count: int = 0


# --- NSG Models ---

@dataclass
class SecurityRule:
    name: str
    priority: int
    direction: str
    access: str
    protocol: str
    source_address_prefix: Optional[str] = None
    source_address_prefixes: list[str] = field(default_factory=list)
    source_port_range: Optional[str] = None
    destination_address_prefix: Optional[str] = None
    destination_address_prefixes: list[str] = field(default_factory=list)
    destination_port_range: Optional[str] = None
    description: Optional[str] = None


@dataclass
class NetworkSecurityGroup:
    name: str
    id: str
    resource_group: str
    location: str
    security_rules: list[SecurityRule] = field(default_factory=list)
    default_rules: list[SecurityRule] = field(default_factory=list)
    associated_subnets: list[str] = field(default_factory=list)
    associated_nics: list[str] = field(default_factory=list)
    is_orphaned: bool = False
    tags: dict[str, str] = field(default_factory=dict)


# --- Compliance Models ---

@dataclass
class ComplianceFinding:
    rule_id: str
    rule_name: str
    severity: str
    resource_id: str
    resource_name: str
    description: str
    remediation: str
    nsg_rule_name: Optional[str] = None


# --- ExpressRoute Models ---

@dataclass
class ExpressRoutePeering:
    name: str
    peering_type: str
    state: str
    primary_peer_address_prefix: Optional[str] = None
    secondary_peer_address_prefix: Optional[str] = None
    vlan_id: Optional[int] = None
    azure_asn: Optional[int] = None
    peer_asn: Optional[int] = None


@dataclass
class ExpressRouteCircuit:
    name: str
    id: str
    resource_group: str
    location: str
    sku_name: Optional[str] = None
    sku_tier: Optional[str] = None
    sku_family: Optional[str] = None
    bandwidth_in_mbps: Optional[int] = None
    peering_location: Optional[str] = None
    service_provider_name: Optional[str] = None
    provisioning_state: Optional[str] = None
    circuit_provisioning_state: Optional[str] = None
    peerings: list[ExpressRoutePeering] = field(default_factory=list)


# --- VPN Gateway Models ---

@dataclass
class VPNConnection:
    name: str
    id: str
    connection_type: str
    connection_status: str
    routing_weight: int = 0
    shared_key_set: bool = False
    egress_bytes_transferred: int = 0
    ingress_bytes_transferred: int = 0


@dataclass
class VPNGateway:
    name: str
    id: str
    resource_group: str
    location: str
    sku: Optional[str] = None
    gateway_type: Optional[str] = None
    vpn_type: Optional[str] = None
    active_active: bool = False
    bgp_settings: Optional[dict] = None
    connections: list[VPNConnection] = field(default_factory=list)
    provisioning_state: Optional[str] = None


# --- Firewall Models ---

@dataclass
class RuleCollection:
    name: str
    priority: int
    action_type: str
    rule_type: str
    rules: list[dict] = field(default_factory=list)


@dataclass
class RuleCollectionGroup:
    name: str
    priority: int
    rule_collections: list[RuleCollection] = field(default_factory=list)


@dataclass
class FirewallPolicy:
    name: str
    id: str
    threat_intelligence_mode: Optional[str] = None
    dns_proxy_enabled: bool = False
    intrusion_detection_mode: Optional[str] = None
    rule_collection_groups: list[RuleCollectionGroup] = field(default_factory=list)


@dataclass
class AzureFirewall:
    name: str
    id: str
    resource_group: str
    location: str
    sku_tier: Optional[str] = None
    provisioning_state: Optional[str] = None
    firewall_policy_id: Optional[str] = None
    threat_intel_mode: Optional[str] = None
    ip_configurations: list[dict] = field(default_factory=list)


# --- Load Balancer Models ---

@dataclass
class HealthProbe:
    name: str
    protocol: str
    port: int
    request_path: Optional[str] = None
    interval_in_seconds: int = 15
    number_of_probes: int = 2


@dataclass
class BackendPool:
    name: str
    id: str
    members: list[dict] = field(default_factory=list)
    health_status: list[dict] = field(default_factory=list)


@dataclass
class LoadBalancer:
    name: str
    id: str
    resource_group: str
    location: str
    sku: Optional[str] = None
    type: Optional[str] = None
    frontend_ip_configs: list[dict] = field(default_factory=list)
    backend_pools: list[BackendPool] = field(default_factory=list)
    health_probes: list[HealthProbe] = field(default_factory=list)
    load_balancing_rules: list[dict] = field(default_factory=list)
    nat_rules: list[dict] = field(default_factory=list)
    provisioning_state: Optional[str] = None


# --- Route Table Models ---

@dataclass
class Route:
    name: str
    address_prefix: str
    next_hop_type: str
    next_hop_ip: Optional[str] = None


@dataclass
class RouteTable:
    name: str
    id: str
    resource_group: str
    location: str
    routes: list[Route] = field(default_factory=list)
    associated_subnets: list[str] = field(default_factory=list)
    disable_bgp_route_propagation: bool = False


# --- Private Endpoint Models ---

@dataclass
class PrivateEndpoint:
    name: str
    id: str
    resource_group: str
    location: str
    subnet_id: Optional[str] = None
    private_ip: Optional[str] = None
    service_connection: Optional[dict] = None
    private_dns_zones: list[str] = field(default_factory=list)
    provisioning_state: Optional[str] = None


# --- DNS Models ---

@dataclass
class DnsRecordSet:
    name: str
    type: str
    ttl: int
    records: list[str] = field(default_factory=list)


@dataclass
class DnsZone:
    name: str
    id: str
    resource_group: str
    zone_type: str
    record_count: int = 0
    name_servers: list[str] = field(default_factory=list)
    linked_vnets: list[str] = field(default_factory=list)
