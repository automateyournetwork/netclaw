"""Token footer formatter for response display.

Formats the mandatory token/cost footer appended to every NetClaw interaction.
"""

from __future__ import annotations

from typing import Optional

from . import CostEstimate, TokenCount


def format_footer(
    token_count: TokenCount,
    cost: CostEstimate,
    gcf_savings: int = 0,
    session_summary: Optional[dict] = None,
) -> str:
    """Format the mandatory token footer for display.

    Returns a string like:
    Tokens: 1,245 in / 382 out / 1,627 total | Cost: $0.0158 | GCF saved: 412 tokens ($0.0041) | Session: 15,832 tokens ($0.14)

    Args:
        token_count: Current interaction's token count.
        cost: Current interaction's cost estimate.
        gcf_savings: Tokens saved by GCF in this interaction.
        session_summary: Optional session totals to append.
    """
    # Current interaction
    parts = []

    in_tokens = f"{token_count.input_tokens:,}"
    out_tokens = f"{token_count.output_tokens:,}"
    total = f"{token_count.total_tokens:,}"
    estimated_marker = " (estimated)" if token_count.estimated else ""

    parts.append(f"Tokens: {in_tokens} in / {out_tokens} out / {total} total{estimated_marker}")
    parts.append(f"Cost: ${cost.total_cost:.4f}")

    # GCF savings
    if gcf_savings > 0:
        from .cost_calculator import get_pricing

        pricing = get_pricing(cost.model)
        savings_cost = (gcf_savings / 1_000_000) * pricing.input_price_per_1m
        parts.append(f"GCF saved: {gcf_savings:,} tokens (${savings_cost:.4f})")

    # Session totals
    if session_summary:
        session_tokens = session_summary.get("total_tokens", 0)
        session_cost = session_summary.get("total_cost_usd", 0.0)
        parts.append(f"Session: {session_tokens:,} tokens (${session_cost:.2f})")

    return " | ".join(parts)
