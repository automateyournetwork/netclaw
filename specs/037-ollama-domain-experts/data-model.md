# Data Model: Ollama Domain Expert Delegation

## MCP Tool Schemas

### Tool: `ollama_generate_config`

Generate network device configuration using a domain-specific local model.

```json
{
  "name": "ollama_generate_config",
  "description": "Delegate config generation to a local Ollama domain expert model. Returns FRR/IOS/NX-OS configuration blocks.",
  "inputSchema": {
    "type": "object",
    "required": ["domain", "task", "device_context"],
    "properties": {
      "domain": {
        "type": "string",
        "enum": ["ospf", "bgp", "mpls", "acl", "general"],
        "description": "Network domain to route the request to the appropriate expert model"
      },
      "task": {
        "type": "string",
        "description": "Natural language description of what config to generate"
      },
      "device_context": {
        "type": "object",
        "properties": {
          "hostname": { "type": "string" },
          "role": { "type": "string", "enum": ["pe", "p", "rr", "ce", "spine", "leaf"] },
          "platform": { "type": "string", "enum": ["frr", "ios-xe", "ios-xr", "nx-os", "junos", "eos"] },
          "interfaces": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "name": { "type": "string" },
                "ip_address": { "type": "string" },
                "description": { "type": "string" },
                "area": { "type": "string" },
                "peer_as": { "type": "integer" }
              }
            }
          },
          "router_id": { "type": "string" },
          "asn": { "type": "integer" }
        }
      },
      "constraints": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Optional constraints (e.g., 'use MD5 authentication', 'passive-interface on loopbacks')"
      }
    }
  }
}
```

### Tool: `ollama_validate_design`

Validate a network design against RFC standards and best practices.

```json
{
  "name": "ollama_validate_design",
  "description": "Validate a network design or configuration against RFC standards using the RFC domain expert model.",
  "inputSchema": {
    "type": "object",
    "required": ["design", "rfcs"],
    "properties": {
      "design": {
        "type": "string",
        "description": "The network design or configuration to validate"
      },
      "rfcs": {
        "type": "array",
        "items": { "type": "string" },
        "description": "RFC numbers to validate against (e.g., ['2328', '4271', '5340'])"
      },
      "validation_focus": {
        "type": "string",
        "enum": ["syntax", "design-rules", "security", "scalability", "all"],
        "description": "What aspect to focus validation on"
      }
    }
  }
}
```

### Tool: `ollama_domain_query`

Ask a domain expert a technical question (analysis, explanation, troubleshooting).

```json
{
  "name": "ollama_domain_query",
  "description": "Ask a domain-specific technical question to a local expert model. For analysis, explanations, and troubleshooting guidance.",
  "inputSchema": {
    "type": "object",
    "required": ["domain", "question"],
    "properties": {
      "domain": {
        "type": "string",
        "enum": ["ospf", "bgp", "mpls", "acl", "rfc", "general"],
        "description": "Network domain for expert routing"
      },
      "question": {
        "type": "string",
        "description": "Technical question to answer"
      },
      "context": {
        "type": "string",
        "description": "Optional additional context (show command output, topology info, etc.)"
      }
    }
  }
}
```

### Tool: `ollama_list_experts`

List available domain expert models and their status.

```json
{
  "name": "ollama_list_experts",
  "description": "List configured domain expert models, their status, and capabilities.",
  "inputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

### Tool: `ollama_health_check`

Verify Ollama connectivity and model availability.

```json
{
  "name": "ollama_health_check",
  "description": "Check Ollama instance connectivity, available models, and GPU memory status.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "verbose": {
        "type": "boolean",
        "description": "Include detailed model info (size, quantization, last used)"
      }
    }
  }
}
```

## Response Schemas

### ConfigGenerationResponse

```python
class ConfigGenerationResponse(BaseModel):
    success: bool
    domain: str                    # Which domain expert handled this
    model_used: str                # Actual Ollama model name (e.g., "netclaw-ospf:latest")
    config: str                    # Generated configuration block
    explanation: Optional[str]     # Why this config was generated this way
    warnings: List[str]            # Any concerns about the generated config
    generation_time_ms: int        # How long the local model took
    estimated_tokens: int          # Approximate tokens used by local model
```

### DesignValidationResponse

```python
class DesignValidationResponse(BaseModel):
    success: bool
    valid: bool                    # Overall pass/fail
    model_used: str
    findings: List[Finding]        # Individual validation results
    rfc_references: List[str]      # Specific RFC sections referenced
    generation_time_ms: int

class Finding(BaseModel):
    severity: str                  # "error", "warning", "info"
    rule: str                      # What was checked
    message: str                   # Human-readable finding
    rfc: Optional[str]             # Which RFC this relates to
    suggestion: Optional[str]      # How to fix
```

### ExpertQueryResponse

```python
class ExpertQueryResponse(BaseModel):
    success: bool
    domain: str
    model_used: str
    answer: str                    # The expert's response
    confidence: Optional[str]     # "high", "medium", "low" — self-assessed
    references: List[str]          # RFCs or standards referenced
    generation_time_ms: int
```

## Domain → Model Registry

The mapping is configured via environment variables:

```bash
# Model names in Ollama
OLLAMA_MODEL_OSPF=netclaw-ospf:latest
OLLAMA_MODEL_BGP=netclaw-bgp:latest
OLLAMA_MODEL_RFC=netclaw-rfc-design:latest
OLLAMA_MODEL_MPLS=netclaw-mpls:latest
OLLAMA_MODEL_ACL=netclaw-acl:latest
OLLAMA_MODEL_GENERAL=deepseek-coder-v2:16b

# Fallback if domain model not available
OLLAMA_MODEL_FALLBACK=deepseek-coder-v2:16b
```

## Metrics (In-Memory Per Session)

```python
class DelegationMetrics(BaseModel):
    total_delegations: int
    total_generation_time_ms: int
    estimated_frontier_tokens_saved: int
    estimated_cost_saved_usd: float
    per_domain: Dict[str, DomainMetrics]

class DomainMetrics(BaseModel):
    domain: str
    model: str
    call_count: int
    avg_latency_ms: float
    total_tokens_generated: int
    success_rate: float
```
