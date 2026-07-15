"""Pydantic models for Ollama Domain Expert MCP requests and responses."""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field


# --- Request Models ---

class DeviceInterface(BaseModel):
    name: str
    ip_address: Optional[str] = None
    description: Optional[str] = None
    area: Optional[str] = None
    peer_as: Optional[int] = None


class DeviceContext(BaseModel):
    hostname: str
    role: Optional[str] = None  # pe, p, rr, ce, spine, leaf
    platform: str = "frr"  # frr, ios-xe, ios-xr, nx-os, junos, eos
    interfaces: List[DeviceInterface] = Field(default_factory=list)
    router_id: Optional[str] = None
    asn: Optional[int] = None


class ConfigGenerationRequest(BaseModel):
    domain: str  # ospf, bgp, mpls, acl, general
    task: str
    device_context: DeviceContext
    constraints: List[str] = Field(default_factory=list)


class DesignValidationRequest(BaseModel):
    design: str
    rfcs: List[str]
    validation_focus: str = "all"  # syntax, design-rules, security, scalability, all


class DomainQueryRequest(BaseModel):
    domain: str
    question: str
    context: Optional[str] = None


# --- Response Models ---

class ConfigGenerationResponse(BaseModel):
    success: bool
    domain: str
    model_used: str
    config: str
    explanation: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    generation_time_ms: int = 0
    estimated_tokens: int = 0


class Finding(BaseModel):
    severity: str  # error, warning, info
    rule: str
    message: str
    rfc: Optional[str] = None
    suggestion: Optional[str] = None


class DesignValidationResponse(BaseModel):
    success: bool
    valid: bool
    model_used: str
    findings: List[Finding] = Field(default_factory=list)
    rfc_references: List[str] = Field(default_factory=list)
    generation_time_ms: int = 0


class ExpertQueryResponse(BaseModel):
    success: bool
    domain: str
    model_used: str
    answer: str
    confidence: Optional[str] = None  # high, medium, low
    references: List[str] = Field(default_factory=list)
    generation_time_ms: int = 0


class ExpertInfo(BaseModel):
    domain: str
    model: str
    available: bool
    description: str


class HealthCheckResponse(BaseModel):
    ollama_reachable: bool
    ollama_url: str
    available_models: List[str] = Field(default_factory=list)
    configured_experts: List[ExpertInfo] = Field(default_factory=list)
    gpu_info: Optional[str] = None


# --- Metrics Models ---

class DomainMetrics(BaseModel):
    domain: str
    model: str
    call_count: int = 0
    avg_latency_ms: float = 0.0
    total_tokens_generated: int = 0
    success_rate: float = 1.0


class DelegationMetrics(BaseModel):
    total_delegations: int = 0
    total_generation_time_ms: int = 0
    estimated_frontier_tokens_saved: int = 0
    estimated_cost_saved_usd: float = 0.0
    per_domain: Dict[str, DomainMetrics] = Field(default_factory=dict)
