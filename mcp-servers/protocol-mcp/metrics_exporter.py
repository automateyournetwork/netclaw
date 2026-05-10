#!/usr/bin/env python3
"""
Protocol MCP — Prometheus Metrics Exporter

Exposes BGP route stability metrics at /metrics for scraping by
VictoriaMetrics (or any Prometheus-compatible scraper).

Metrics exported:
  bgp_route_announcements_total   — counter per prefix/peer
  bgp_route_withdrawals_total     — counter per prefix/peer
  bgp_route_flap_penalty          — gauge per prefix (RFC 2439 penalty)
  bgp_route_suppressed            — gauge per prefix (1=suppressed, 0=not)
  bgp_rib_size                    — gauge (total routes in loc-rib)
  bgp_peer_prefixes_received      — gauge per peer
  bgp_peer_state                  — gauge per peer (1=Established, 0=other)

Runs as a background thread inside the Protocol MCP server process.
Listens on port 9179 (BGP port 179 + 9000 offset).

Environment Variables:
  PROTOCOL_METRICS_PORT  — HTTP port for /metrics (default: 9179)
  PROTOCOL_METRICS_ENABLED — set "true" to enable (default: true)
"""

import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Optional

logger = logging.getLogger("protocol-metrics")

# ---------------------------------------------------------------------------
# Metric storage (thread-safe via GIL for simple counters/gauges)
# ---------------------------------------------------------------------------

_announcements: Dict[str, int] = {}   # key: "prefix|peer" → count
_withdrawals: Dict[str, int] = {}     # key: "prefix|peer" → count
_flap_penalties: Dict[str, float] = {}  # key: prefix → penalty
_suppressed: Dict[str, int] = {}      # key: prefix → 0 or 1
_rib_size: int = 0
_peer_prefixes: Dict[str, int] = {}   # key: peer_ip → prefix count
_peer_states: Dict[str, int] = {}     # key: peer_ip → 1=Established


def record_announcement(prefix: str, peer: str) -> None:
    """Record a route announcement event."""
    key = f"{prefix}|{peer}"
    _announcements[key] = _announcements.get(key, 0) + 1


def record_withdrawal(prefix: str, peer: str) -> None:
    """Record a route withdrawal event."""
    key = f"{prefix}|{peer}"
    _withdrawals[key] = _withdrawals.get(key, 0) + 1


def update_flap_penalty(prefix: str, penalty: float, suppressed: bool) -> None:
    """Update flap damping state for a prefix."""
    _flap_penalties[prefix] = penalty
    _suppressed[prefix] = 1 if suppressed else 0


def update_rib_size(size: int) -> None:
    """Update total RIB size gauge."""
    global _rib_size
    _rib_size = size


def update_peer_state(peer_ip: str, state_name: str, prefixes: int) -> None:
    """Update peer state and prefix count."""
    _peer_states[peer_ip] = 1 if state_name == "Established" else 0
    _peer_prefixes[peer_ip] = prefixes


# ---------------------------------------------------------------------------
# Prometheus text format renderer
# ---------------------------------------------------------------------------

def _render_metrics() -> str:
    """Render all metrics in Prometheus exposition format."""
    lines = []

    # bgp_route_announcements_total
    lines.append("# HELP bgp_route_announcements_total Total BGP route announcements")
    lines.append("# TYPE bgp_route_announcements_total counter")
    for key, count in _announcements.items():
        prefix, peer = key.split("|", 1)
        lines.append(f'bgp_route_announcements_total{{prefix="{prefix}",peer="{peer}"}} {count}')

    # bgp_route_withdrawals_total
    lines.append("# HELP bgp_route_withdrawals_total Total BGP route withdrawals")
    lines.append("# TYPE bgp_route_withdrawals_total counter")
    for key, count in _withdrawals.items():
        prefix, peer = key.split("|", 1)
        lines.append(f'bgp_route_withdrawals_total{{prefix="{prefix}",peer="{peer}"}} {count}')

    # bgp_route_flap_penalty
    lines.append("# HELP bgp_route_flap_penalty RFC 2439 flap damping penalty")
    lines.append("# TYPE bgp_route_flap_penalty gauge")
    for prefix, penalty in _flap_penalties.items():
        lines.append(f'bgp_route_flap_penalty{{prefix="{prefix}"}} {penalty:.1f}')

    # bgp_route_suppressed
    lines.append("# HELP bgp_route_suppressed Route suppressed by flap damping (1=yes)")
    lines.append("# TYPE bgp_route_suppressed gauge")
    for prefix, val in _suppressed.items():
        lines.append(f'bgp_route_suppressed{{prefix="{prefix}"}} {val}')

    # bgp_rib_size
    lines.append("# HELP bgp_rib_size Total routes in Loc-RIB")
    lines.append("# TYPE bgp_rib_size gauge")
    lines.append(f"bgp_rib_size {_rib_size}")

    # bgp_peer_prefixes_received
    lines.append("# HELP bgp_peer_prefixes_received Prefixes received from peer")
    lines.append("# TYPE bgp_peer_prefixes_received gauge")
    for peer, count in _peer_prefixes.items():
        lines.append(f'bgp_peer_prefixes_received{{peer="{peer}"}} {count}')

    # bgp_peer_state
    lines.append("# HELP bgp_peer_state BGP peer state (1=Established, 0=other)")
    lines.append("# TYPE bgp_peer_state gauge")
    for peer, state in _peer_states.items():
        lines.append(f'bgp_peer_state{{peer="{peer}"}} {state}')

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            body = _render_metrics().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress access logs


def start_metrics_server(port: int = 9179) -> Optional[threading.Thread]:
    """Start the metrics HTTP server in a background daemon thread."""
    try:
        server = HTTPServer(("0.0.0.0", port), _MetricsHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info("Metrics exporter listening on :%d/metrics", port)
        return thread
    except Exception as exc:
        logger.warning("Failed to start metrics exporter: %s", exc)
        return None
