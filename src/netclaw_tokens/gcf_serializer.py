"""GCF serialization for MCP server responses.

Supports three encoding modes, auto-selected:
- Generic profile: flat tabular data (arrays of objects)
- Graph profile: network topology data (devices + sessions/links/adjacencies)
- Graph profile with session dedup: bare references for previously-sent symbols
- Delta encoding: only added/removed symbols and edges on re-query

The serializer auto-detects graph-shaped data and uses the most efficient
encoding available. Falls back to JSON on any error.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("netclaw_tokens.gcf_serializer")

# ---------------------------------------------------------------------------
# NETCLAW_GCF_MODE controls which GCF features are active.
#
#   full    - graph auto-detect + session dedup + delta encoding (default)
#   graph   - graph auto-detect, no session state
#   generic - generic profile only, no graph detection
#   off     - JSON passthrough, GCF disabled entirely
#
# Set via environment variable. Operators choose based on their model tier
# and deployment requirements.
# ---------------------------------------------------------------------------
_GCF_MODE = os.environ.get("NETCLAW_GCF_MODE", "full").lower()


def _resolve_mode() -> tuple[bool, bool, bool]:
    """Return (prefer_graph, use_session, use_delta) from NETCLAW_GCF_MODE."""
    if _GCF_MODE == "full":
        return True, True, True
    elif _GCF_MODE == "graph":
        return True, False, False
    elif _GCF_MODE == "generic":
        return False, False, False
    elif _GCF_MODE == "off":
        return False, False, False
    else:
        logger.warning("Unknown NETCLAW_GCF_MODE=%s, defaulting to full", _GCF_MODE)
        return True, True, True

# Keys that indicate an array contains node-like records
_NODE_KEYS = frozenset({
    "hostname", "router_id", "device", "node", "switch", "router",
    "neighbor", "name", "host", "ifname", "mgmt_ip",
})

# Keys that indicate an array contains edge-like records (has source+target)
_EDGE_SRC_KEYS = frozenset({"source", "src", "from", "local", "source_device"})
_EDGE_TGT_KEYS = frozenset({"target", "tgt", "to", "remote", "target_device", "dest", "destination"})

# Keys used for edge type classification
_EDGE_TYPE_KEYS = frozenset({
    "state", "session_type", "link_type", "edge_type", "type",
    "relationship", "connection_type",
})

# Keys that provide a natural identifier for a node
_ID_KEYS = ("hostname", "router_id", "name", "device", "host", "node", "switch", "mgmt_ip")


def _estimate_token_count(text: str) -> int:
    return max(1, len(text) // 4)


def _is_binary_data(data: Any) -> bool:
    if isinstance(data, (bytes, bytearray)):
        return True
    if isinstance(data, str):
        try:
            data.encode("utf-8")
            return False
        except (UnicodeEncodeError, UnicodeDecodeError):
            return True
    return False


def _find_id_key(record: dict) -> str | None:
    for key in _ID_KEYS:
        if key in record:
            return key
    return None


def _detect_graph_arrays(data: Any) -> tuple[list | None, list | None, str | None, str | None]:
    """Detect node-like and edge-like arrays in the data.

    Returns (nodes, edges, nodes_key, edges_key) or (None, None, None, None).
    """
    if not isinstance(data, dict):
        return None, None, None, None

    node_candidates = []
    edge_candidates = []

    for key, value in data.items():
        if not isinstance(value, list) or len(value) == 0:
            continue
        if not isinstance(value[0], dict):
            continue

        sample_keys = set(value[0].keys())

        has_src = bool(sample_keys & _EDGE_SRC_KEYS)
        has_tgt = bool(sample_keys & _EDGE_TGT_KEYS)
        if has_src and has_tgt:
            edge_candidates.append(key)
            continue

        has_id = bool(sample_keys & _NODE_KEYS)
        if has_id:
            node_candidates.append(key)

    if node_candidates and edge_candidates:
        return data[node_candidates[0]], data[edge_candidates[0]], node_candidates[0], edge_candidates[0]

    return None, None, None, None


def _find_edge_keys(edge_record: dict) -> tuple[str | None, str | None, str | None]:
    src_key = None
    tgt_key = None
    type_key = None

    for k in edge_record:
        if k in _EDGE_SRC_KEYS and src_key is None:
            src_key = k
        if k in _EDGE_TGT_KEYS and tgt_key is None:
            tgt_key = k
        if k in _EDGE_TYPE_KEYS and type_key is None:
            type_key = k

    return src_key, tgt_key, type_key


def _classify_role(role: str) -> int:
    """Map network role to GCF distance (0=targets, 1=related, 2=extended)."""
    role = role.lower()
    if role in ("spine", "superspine", "dr", "route-reflector", "border", "abr", "asbr", "core"):
        return 0
    elif role in ("leaf", "bdr", "pe", "border-leaf", "aggregation"):
        return 1
    return 2


def _build_payload(nodes: list[dict], edges: list[dict]):
    """Build a GCF Payload from node and edge dicts."""
    from gcf import Payload, Symbol, Edge

    id_key = _find_id_key(nodes[0]) if nodes else None
    if not id_key:
        raise ValueError("Cannot determine node identifier key")

    symbols = []
    name_set = set()
    for node in nodes:
        qname = str(node.get(id_key, ""))
        if not qname or qname in name_set:
            continue
        name_set.add(qname)

        role = str(node.get("role", node.get("tier", ""))).lower()
        symbols.append(Symbol(
            qualified_name=qname,
            kind="svc",
            score=0.0,
            provenance="network",
            distance=_classify_role(role),
        ))

    src_key, tgt_key, type_key = _find_edge_keys(edges[0]) if edges else (None, None, None)
    gcf_edges = []
    for edge in edges:
        src = str(edge.get(src_key, "")) if src_key else ""
        tgt = str(edge.get(tgt_key, "")) if tgt_key else ""
        etype = str(edge.get(type_key, "connected")) if type_key else "connected"

        if src in name_set and tgt in name_set:
            gcf_edges.append(Edge(
                source=src,
                target=tgt,
                edge_type=etype,
            ))

    return Payload(
        tool="network_topology",
        symbols=symbols,
        edges=gcf_edges,
    )


# ---------------------------------------------------------------------------
# Session state for dedup and delta
# ---------------------------------------------------------------------------

class GCFSessionManager:
    """Manages GCF session state for dedup and delta encoding.

    One instance per MCP server. Tracks transmitted symbols across calls.
    """

    def __init__(self):
        self._session = None
        self._last_payload = None

    def _ensure_session(self):
        if self._session is None:
            from gcf import Session
            self._session = Session()

    @property
    def active(self) -> bool:
        return self._session is not None

    @property
    def symbols_transmitted(self) -> int:
        if self._session is None:
            return 0
        return self._session.size()

    def encode_with_session(self, payload) -> str:
        """Encode with session dedup. Previously-sent symbols become bare refs."""
        from gcf import encode_with_session
        self._ensure_session()
        result = encode_with_session(payload, self._session)
        self._last_payload = payload
        return result

    def encode_delta(self, new_payload) -> str | None:
        """Encode only the diff from the last payload. Returns None if no previous."""
        if self._last_payload is None:
            return None

        from gcf import encode_delta, DeltaPayload, Symbol, Edge

        old_names = {s.qualified_name for s in self._last_payload.symbols}
        new_names = {s.qualified_name for s in new_payload.symbols}

        old_edges = {(e.source, e.target, e.edge_type) for e in self._last_payload.edges}
        new_edges = {(e.source, e.target, e.edge_type) for e in new_payload.edges}

        removed_names = old_names - new_names
        added_names = new_names - old_names
        removed_edge_tuples = old_edges - new_edges
        added_edge_tuples = new_edges - old_edges

        # Not worth a delta if everything changed
        if len(removed_names) + len(added_names) > len(new_names) * 0.5:
            return None

        old_sym_map = {s.qualified_name: s for s in self._last_payload.symbols}
        new_sym_map = {s.qualified_name: s for s in new_payload.symbols}

        delta = DeltaPayload(
            tool="network_topology",
            removed=[old_sym_map[n] for n in removed_names if n in old_sym_map],
            added=[new_sym_map[n] for n in added_names if n in new_sym_map],
            removed_edges=[
                Edge(source=s, target=t, edge_type=et)
                for s, t, et in removed_edge_tuples
            ],
            added_edges=[
                Edge(source=s, target=t, edge_type=et)
                for s, t, et in added_edge_tuples
            ],
        )

        result = encode_delta(delta)
        self._last_payload = new_payload
        return result

    def reset(self):
        """Reset session state."""
        self._session = None
        self._last_payload = None


# Global session manager (one per process)
_session_manager = GCFSessionManager()


def get_session_manager() -> GCFSessionManager:
    """Get the global session manager."""
    return _session_manager


# ---------------------------------------------------------------------------
# Main serialize function
# ---------------------------------------------------------------------------

def serialize_response(
    data: Any,
    prefer_graph: bool = True,
    use_session: bool = False,
    use_delta: bool = False,
) -> dict:
    """Serialize data to GCF format with auto graph detection.

    Feature flags are overridden by NETCLAW_GCF_MODE env var:
      full    - all features (default)
      graph   - graph auto-detect, no session/delta
      generic - generic profile only
      off     - JSON passthrough

    Args:
        data: Any JSON-serializable data structure.
        prefer_graph: If True, auto-detect graph-shaped data and use graph
            profile. If False, always use generic profile.
        use_session: If True, use session dedup for graph data (bare refs
            for previously-transmitted symbols).
        use_delta: If True, attempt delta encoding against the last payload.
            Falls back to session encoding if delta is not worthwhile.

    Returns:
        Dict with: encoded_data, json_token_count, gcf_token_count,
        savings_tokens, savings_pct, fallback_used, profile_used.
    """
    # Apply mode overrides
    mode_graph, mode_session, mode_delta = _resolve_mode()
    prefer_graph = prefer_graph and mode_graph
    use_session = use_session and mode_session
    use_delta = use_delta and mode_delta

    try:
        json_str = json.dumps(data, indent=2, default=str)
    except (TypeError, ValueError):
        json_str = str(data)

    json_token_count = _estimate_token_count(json_str)

    # Off mode: JSON passthrough
    if _GCF_MODE == "off":
        return _result(json_str, json_token_count, json_token_count, True, "json")

    if _is_binary_data(data):
        logger.debug("Binary data detected; skipping GCF, using JSON")
        return _result(json_str, json_token_count, json_token_count, True, "json")

    # Try graph profile first if preferred
    if prefer_graph:
        nodes, edges, _, _ = _detect_graph_arrays(data)
        if nodes is not None and edges is not None:
            try:
                payload = _build_payload(nodes, edges)

                # Try delta first
                if use_delta:
                    delta_str = _session_manager.encode_delta(payload)
                    if delta_str is not None:
                        gcf_token_count = _estimate_token_count(delta_str)
                        return _result(delta_str, json_token_count, gcf_token_count, False, "delta")

                # Try session dedup
                if use_session:
                    gcf_str = _session_manager.encode_with_session(payload)
                    gcf_token_count = _estimate_token_count(gcf_str)
                    return _result(gcf_str, json_token_count, gcf_token_count, False, "graph+session")

                # Plain graph encoding
                from gcf import encode
                gcf_str = encode(payload)
                if use_session or use_delta:
                    _session_manager._last_payload = payload
                gcf_token_count = _estimate_token_count(gcf_str)
                return _result(gcf_str, json_token_count, gcf_token_count, False, "graph")

            except Exception as exc:
                logger.debug(
                    "Graph profile failed (%s: %s); trying generic",
                    type(exc).__name__, exc,
                )

    # Fall back to generic profile
    try:
        from gcf import encode_generic

        gcf_str = encode_generic(data)
        gcf_token_count = _estimate_token_count(gcf_str)
        return _result(gcf_str, json_token_count, gcf_token_count, False, "generic")
    except Exception as exc:
        logger.warning(
            "GCF serialization failed (%s: %s); falling back to JSON",
            type(exc).__name__, exc,
        )
        return _result(json_str, json_token_count, json_token_count, True, "json")


def _result(encoded_data, json_tokens, gcf_tokens, fallback, profile):
    savings_tokens = max(0, json_tokens - gcf_tokens)
    savings_pct = (savings_tokens / json_tokens * 100.0) if json_tokens > 0 else 0.0
    return {
        "encoded_data": encoded_data,
        "json_token_count": json_tokens,
        "gcf_token_count": gcf_tokens,
        "savings_tokens": savings_tokens,
        "savings_pct": round(savings_pct, 1),
        "fallback_used": fallback,
        "profile_used": profile,
    }
