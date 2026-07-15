"""Domain-based model routing for Ollama expert delegation."""

import os
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class DomainConfig:
    """Configuration for a single domain expert."""
    domain: str
    model: str
    description: str
    temperature: float = 0.1
    top_p: float = 0.9
    num_predict: int = 4096


# Default domain descriptions — add new domains here when creating experts
DOMAIN_DESCRIPTIONS = {
    "ospf": "OSPF protocol expert — area design, LSA types, SPF, config generation (RFC 2328/5340)",
    "bgp": "BGP protocol expert — path selection, communities, policy, route reflection (RFC 4271)",
    "mpls": "MPLS/SR expert — label distribution, traffic engineering, segment routing",
    "acl": "Access control list expert — filtering, CoPP, security policy generation",
    "rfc": "RFC design validator — validates network designs against IETF standards",
    "frr": "FRR config generation expert — generates vtysh commands from structured device data",
    "nautobot": "Nautobot API/GraphQL expert — models hierarchy, job execution patterns",
    "netbox": "NetBox API expert — DCIM/IPAM models, GraphQL queries",
    "graphql": "GraphQL query builder — constructs valid queries from natural language intent",
    "state": "Protocol state summarizer — compresses show command output into structured JSON",
    "compress": "Context compressor — reduces API responses to minimal task-relevant JSON",
    "general": "General network config generation — multi-protocol, multi-platform",
}


@dataclass
class DomainRouter:
    """Routes domain requests to appropriate Ollama models based on env config.

    The router discovers configured domains from environment variables:
        OLLAMA_MODEL_<DOMAIN>=<ollama-model-tag>
        OLLAMA_TEMP_<DOMAIN>=<temperature>  (optional, default 0.1)

    Any domain name can be used — just set the env var and the router picks it up.
    """

    _registry: Dict[str, DomainConfig] = field(default_factory=dict)
    _fallback_model: str = "qwen2.5-coder:7b"

    def __post_init__(self):
        self._load_from_env()

    def _load_from_env(self):
        """Load domain → model mappings from environment variables.

        Scans for OLLAMA_MODEL_* env vars. Any OLLAMA_MODEL_<NAME> creates
        a domain entry for <name> (lowercased).

        Examples:
            OLLAMA_MODEL_OSPF=my-ospf-expert:7b
            OLLAMA_MODEL_BGP=my-bgp-expert:7b
            OLLAMA_MODEL_CUSTOM_DOMAIN=some-model:latest
            OLLAMA_MODEL_GENERAL=qwen2.5-coder:7b
            OLLAMA_MODEL_FALLBACK=qwen2.5-coder:7b
        """
        self._fallback_model = os.environ.get("OLLAMA_MODEL_FALLBACK", "qwen2.5-coder:7b")

        # Scan all env vars for OLLAMA_MODEL_* pattern
        for key, value in os.environ.items():
            if key.startswith("OLLAMA_MODEL_") and key != "OLLAMA_MODEL_FALLBACK":
                domain = key[len("OLLAMA_MODEL_"):].lower()
                temp_key = f"OLLAMA_TEMP_{domain.upper()}"
                temperature = float(os.environ.get(temp_key, "0.1"))

                self._registry[domain] = DomainConfig(
                    domain=domain,
                    model=value,
                    description=DOMAIN_DESCRIPTIONS.get(domain, f"{domain} domain expert"),
                    temperature=temperature,
                )

    def get_model(self, domain: str) -> str:
        """Get the Ollama model name for a given domain.

        Falls back to the general model, then to the fallback model.
        """
        if domain in self._registry:
            return self._registry[domain].model

        # Try "general" domain as intermediate fallback
        if "general" in self._registry:
            return self._registry["general"].model

        return self._fallback_model

    def get_config(self, domain: str) -> DomainConfig:
        """Get full domain configuration including generation parameters."""
        if domain in self._registry:
            return self._registry[domain]

        return DomainConfig(
            domain=domain,
            model=self.get_model(domain),
            description=f"Fallback model handling {domain} domain",
            temperature=0.1,
        )

    def get_generation_options(self, domain: str) -> Dict[str, float]:
        """Get Ollama generation options for a domain."""
        config = self.get_config(domain)
        return {
            "temperature": config.temperature,
            "top_p": config.top_p,
            "num_predict": config.num_predict,
        }

    def list_configured_domains(self) -> Dict[str, DomainConfig]:
        """List all configured domain experts."""
        return dict(self._registry)

    @property
    def fallback_model(self) -> str:
        return self._fallback_model

    def is_domain_configured(self, domain: str) -> bool:
        """Check if a specific domain has an explicit model configured."""
        return domain in self._registry
