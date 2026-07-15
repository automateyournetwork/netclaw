"""netclaw_tokens — Token counting, cost tracking, and GCF serialization for NetClaw.

This shared library provides:
  - Token counting via Anthropic API with local estimation fallback
  - GCF serialization for MCP server responses (55-83% token savings)
  - Model-aware cost calculation (Opus, Sonnet, Haiku)
  - Session-level cumulative tracking with per-tool breakdown
  - Mandatory token footer formatting for every interaction
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TokenCount:
    """A record of token usage for a single LLM interaction or tool call."""

    input_tokens: int = 0
    output_tokens: int = 0
    model: str = "claude-opus-4-6"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    estimated: bool = False
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class CostEstimate:
    """Calculated USD cost for a TokenCount."""

    input_cost: float = 0.0
    output_cost: float = 0.0
    cache_discount: float = 0.0
    total_cost: float = 0.0
    model: str = "claude-opus-4-6"


@dataclass
class ModelPricing:
    """Pricing configuration for a specific model."""

    model_name: str = ""
    input_price_per_1m: float = 0.0
    output_price_per_1m: float = 0.0
    cache_discount_pct: float = 90.0


@dataclass
class GCFResponse:
    """An MCP tool response serialized in GCF format."""

    gcf_data: str = ""
    json_token_count: int = 0
    gcf_token_count: int = 0
    savings_tokens: int = 0
    savings_pct: float = 0.0
    fallback_used: bool = False


# Legacy alias
TOONResponse = GCFResponse


@dataclass
class ToolUsageRecord:
    """Per-tool tracking entry in the session ledger."""

    tool_name: str = ""
    call_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    gcf_savings_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def avg_tokens_per_call(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.total_tokens / self.call_count


__all__ = [
    # Dataclasses
    "TokenCount",
    "CostEstimate",
    "ModelPricing",
    "GCFResponse",
    "TOONResponse",  # legacy alias
    "ToolUsageRecord",
    # Functions (lazy imports to avoid circular dependencies)
    "count_tokens",
    "count_message_tokens",
    "calculate_cost",
    "get_pricing",
    "serialize_response",
    "format_footer",
    # Classes
    "SessionLedger",
]


def __getattr__(name: str):
    """Lazy imports for module-level functions and classes."""
    if name in ("count_tokens", "count_message_tokens"):
        from .counter import count_tokens, count_message_tokens
        return count_tokens if name == "count_tokens" else count_message_tokens
    if name in ("calculate_cost", "get_pricing"):
        from .cost_calculator import calculate_cost, get_pricing
        return calculate_cost if name == "calculate_cost" else get_pricing
    if name == "serialize_response":
        from .gcf_serializer import serialize_response
        return serialize_response
    if name == "format_footer":
        from .footer import format_footer
        return format_footer
    if name == "SessionLedger":
        from .session_ledger import SessionLedger
        return SessionLedger
    raise AttributeError(f"module 'netclaw_tokens' has no attribute {name!r}")
