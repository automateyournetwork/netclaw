"""In-memory delegation metrics tracking."""

from typing import Dict
from models import DelegationMetrics, DomainMetrics

# Approximate cost per 1K tokens for Frontier model (Claude Opus 4)
FRONTIER_INPUT_COST_PER_1K = 0.015
FRONTIER_OUTPUT_COST_PER_1K = 0.075


class MetricsTracker:
    """Track delegation metrics for the current session."""

    def __init__(self):
        self._metrics = DelegationMetrics()

    def record_delegation(
        self,
        domain: str,
        model: str,
        generation_time_ms: int,
        estimated_tokens: int,
        success: bool,
    ):
        """Record a delegation event."""
        self._metrics.total_delegations += 1
        self._metrics.total_generation_time_ms += generation_time_ms

        # Estimate Frontier tokens saved:
        # The prompt + response that would have gone to Claude
        # Conservative estimate: local tokens ≈ what Frontier would have used
        if success:
            self._metrics.estimated_frontier_tokens_saved += estimated_tokens
            cost_saved = (estimated_tokens / 1000) * (
                FRONTIER_INPUT_COST_PER_1K * 0.3 + FRONTIER_OUTPUT_COST_PER_1K * 0.7
            )
            self._metrics.estimated_cost_saved_usd += cost_saved

        # Per-domain tracking
        if domain not in self._metrics.per_domain:
            self._metrics.per_domain[domain] = DomainMetrics(
                domain=domain,
                model=model,
            )

        dm = self._metrics.per_domain[domain]
        dm.call_count += 1
        dm.total_tokens_generated += estimated_tokens

        # Running average latency
        dm.avg_latency_ms = (
            (dm.avg_latency_ms * (dm.call_count - 1) + generation_time_ms) / dm.call_count
        )

        # Running success rate
        total_successes = int(dm.success_rate * (dm.call_count - 1)) + (1 if success else 0)
        dm.success_rate = total_successes / dm.call_count

    def get_metrics(self) -> DelegationMetrics:
        """Get current session metrics."""
        return self._metrics

    def get_summary(self) -> str:
        """Get a human-readable metrics summary."""
        m = self._metrics
        if m.total_delegations == 0:
            return "No delegations this session."

        lines = [
            f"Delegation Summary:",
            f"  Total delegations: {m.total_delegations}",
            f"  Total local inference time: {m.total_generation_time_ms}ms",
            f"  Estimated Frontier tokens saved: {m.estimated_frontier_tokens_saved:,}",
            f"  Estimated cost saved: ${m.estimated_cost_saved_usd:.4f}",
            f"",
            f"  Per-domain breakdown:",
        ]
        for domain, dm in m.per_domain.items():
            lines.append(
                f"    {domain}: {dm.call_count} calls, "
                f"avg {dm.avg_latency_ms:.0f}ms, "
                f"{dm.total_tokens_generated:,} tokens, "
                f"{dm.success_rate*100:.0f}% success"
            )
        return "\n".join(lines)

    def reset(self):
        """Reset metrics (e.g., for a new session)."""
        self._metrics = DelegationMetrics()
