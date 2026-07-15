"""Cumulative session-level token tracking with per-tool breakdown.

Thread-safe accumulator that tracks token usage across all tool calls
in a session, with per-tool granularity for cost optimization analysis.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from . import CostEstimate, TokenCount, ToolUsageRecord

__all__ = ["SessionLedger"]


class SessionLedger:
    """Thread-safe session-level token accumulator."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.session_id: str = str(uuid.uuid4())
        self.started_at: datetime = datetime.now(timezone.utc)
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_cost: float = 0.0
        self.total_gcf_savings: int = 0
        self.total_call_count: int = 0
        self.tool_breakdown: Dict[str, ToolUsageRecord] = {}

    def record(
        self,
        tool_name: str,
        token_count: TokenCount,
        cost: CostEstimate,
        gcf_savings: int = 0,
    ) -> None:
        """Record a tool call's token usage. Thread-safe.

        Args:
            tool_name: MCP tool identifier.
            token_count: Token count for this call.
            cost: Cost estimate for this call.
            gcf_savings: Tokens saved by GCF serialization.
        """
        with self._lock:
            self.total_input_tokens += token_count.input_tokens
            self.total_output_tokens += token_count.output_tokens
            self.total_cost += cost.total_cost
            self.total_gcf_savings += gcf_savings
            self.total_call_count += 1

            if tool_name not in self.tool_breakdown:
                self.tool_breakdown[tool_name] = ToolUsageRecord(
                    tool_name=tool_name
                )

            record = self.tool_breakdown[tool_name]
            record.call_count += 1
            record.total_input_tokens += token_count.input_tokens
            record.total_output_tokens += token_count.output_tokens
            record.total_cost += cost.total_cost
            record.gcf_savings_tokens += gcf_savings

    def get_summary(self) -> dict:
        """Return session totals as a dictionary.

        Returns:
            Dict with total_input_tokens, total_output_tokens, total_tokens,
            total_cost_usd, total_gcf_savings, tool_count, call_count.
        """
        with self._lock:
            return {
                "session_id": self.session_id,
                "started_at": self.started_at.isoformat(),
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "total_tokens": self.total_input_tokens + self.total_output_tokens,
                "total_cost_usd": round(self.total_cost, 6),
                "total_gcf_savings": self.total_gcf_savings,
                "tool_count": len(self.tool_breakdown),
                "call_count": self.total_call_count,
            }

    def get_per_tool_breakdown(self) -> List[dict]:
        """Return ranked list of tool usage records, sorted by total tokens desc.

        Each entry contains: tool_name, call_count, input_tokens, output_tokens,
        total_tokens, cost, gcf_savings, avg_tokens_per_call.
        """
        with self._lock:
            records = []
            for record in self.tool_breakdown.values():
                records.append({
                    "tool_name": record.tool_name,
                    "call_count": record.call_count,
                    "input_tokens": record.total_input_tokens,
                    "output_tokens": record.total_output_tokens,
                    "total_tokens": record.total_tokens,
                    "cost": round(record.total_cost, 6),
                    "gcf_savings": record.gcf_savings_tokens,
                    "avg_tokens_per_call": round(record.avg_tokens_per_call, 1),
                })

            # Sort by total tokens descending
            records.sort(key=lambda r: r["total_tokens"], reverse=True)
            return records

    def get_gait_summary(self) -> dict:
        """Return summary formatted for GAIT session log inclusion.

        Includes session totals and per-tool breakdown for audit trail.
        """
        summary = self.get_summary()
        summary["per_tool_breakdown"] = self.get_per_tool_breakdown()
        return summary

    def reset(self) -> None:
        """Reset all counters. Used at session start."""
        with self._lock:
            self.session_id = str(uuid.uuid4())
            self.started_at = datetime.now(timezone.utc)
            self.total_input_tokens = 0
            self.total_output_tokens = 0
            self.total_cost = 0.0
            self.total_gcf_savings = 0
            self.total_call_count = 0
            self.tool_breakdown.clear()
