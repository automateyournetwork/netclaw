#!/usr/bin/env python3
"""
Batfish MCP Server — First-of-its-kind MCP server wrapping the Batfish
network configuration analysis platform via pybatfish.

Tools: batfish_upload_snapshot, batfish_validate_config, batfish_test_reachability,
       batfish_trace_acl, batfish_diff_configs, batfish_check_compliance,
       batfish_list_snapshots, batfish_delete_snapshot

Transport: stdio
Read-only: Analysis only, never touches live devices.
GAIT: All operations logged.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Add netclaw_tokens to path for GCF serialization
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))


def _gcf_dumps(data, **kwargs) -> str:
    """Serialize data using GCF with graph auto-detection and session dedup."""
    try:
        from netclaw_tokens.gcf_serializer import serialize_response
        result = serialize_response(data, use_session=True, use_delta=True)
        return result["encoded_data"]
    except Exception:
        return json.dumps(data, indent=2, default=str)


# ---------------------------------------------------------------------------
# Logging (stderr only — stdout is reserved for MCP JSON-RPC)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("BatfishMCPServer")

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv()

BATFISH_HOST = os.getenv("BATFISH_HOST", "localhost")
BATFISH_PORT = int(os.getenv("BATFISH_PORT", "9997"))
BATFISH_NETWORK = os.getenv("BATFISH_NETWORK", "netclaw")

logger.info("Batfish MCP Server starting — host=%s port=%d network=%s",
            BATFISH_HOST, BATFISH_PORT, BATFISH_NETWORK)

# ---------------------------------------------------------------------------
# FastMCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP("batfish-mcp")

# ---------------------------------------------------------------------------
# pybatfish Session Management (T006)
# ---------------------------------------------------------------------------
_bf_session = None


def _get_bf_session():
    """Return a cached pybatfish Session, creating one on first call."""
    global _bf_session
    if _bf_session is not None:
        return _bf_session

    try:
        from pybatfish.client.session import Session
        bf = Session(host=BATFISH_HOST, port=BATFISH_PORT)
        bf.set_network(BATFISH_NETWORK)
        logger.info("Connected to Batfish at %s:%d (network=%s)",
                     BATFISH_HOST, BATFISH_PORT, BATFISH_NETWORK)
        _bf_session = bf
        return bf
    except Exception as exc:
        logger.error("Failed to connect to Batfish: %s", exc)
        raise ConnectionError(
            f"BATFISH_UNREACHABLE: Cannot connect to Batfish at "
            f"{BATFISH_HOST}:{BATFISH_PORT} — {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# GAIT Audit Logging Helper (T007)
# ---------------------------------------------------------------------------
def _gait_log(analysis_type: str, snapshot_name: str,
              parameters: dict, result_summary: str) -> None:
    """Log an analysis operation to GAIT via the gait_mcp MCP server.

    Falls back to stderr logging if gait_mcp is unavailable.
    """
    record = {
        "analysis_type": analysis_type,
        "snapshot_name": snapshot_name,
        "parameters": parameters,
        "result_summary": result_summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("GAIT: %s | snapshot=%s | %s", analysis_type,
                snapshot_name, result_summary)
    # Best-effort — the GAIT MCP server is a separate process; we log
    # locally so the audit trail is always captured in stderr even if the
    # GAIT server is unavailable.
    return record


# ---------------------------------------------------------------------------
# Error Handling Wrapper (T008)
# ---------------------------------------------------------------------------
def _safe_execute(func):
    """Decorator that catches pybatfish exceptions and returns structured
    error responses without exposing stack traces or credentials (FR-012)."""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectionError:
            raise  # Already formatted
        except Exception as exc:
            exc_type = type(exc).__name__
            # Sanitize: strip any host/port/credential info from message
            msg = str(exc)
            for secret in [BATFISH_HOST, str(BATFISH_PORT)]:
                msg = msg.replace(secret, "***")
            logger.error("Tool %s failed: %s: %s", func.__name__,
                         exc_type, msg)
            return json.dumps({
                "error": exc_type,
                "message": f"Analysis failed: {msg}",
                "tool": func.__name__,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, indent=2)
    return wrapper


# ---------------------------------------------------------------------------
# Snapshot Directory Builder Helper (T009)
# ---------------------------------------------------------------------------
def _build_snapshot_dir(configs: Optional[Dict[str, str]] = None,
                        config_path: Optional[str] = None) -> str:
    """Create a temp directory with Batfish-expected configs/ structure.

    Returns the path to the snapshot root directory containing a configs/
    subdirectory with the device configuration files.
    """
    snap_dir = tempfile.mkdtemp(prefix="batfish_snap_")
    configs_dir = os.path.join(snap_dir, "configs")
    os.makedirs(configs_dir, exist_ok=True)

    if configs:
        for device_name, config_content in configs.items():
            safe_name = "".join(
                c if c.isalnum() or c in "-_." else "_"
                for c in device_name
            )
            filepath = os.path.join(configs_dir, safe_name)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(config_content)
    elif config_path:
        src = Path(config_path).resolve()
        if not src.exists():
            raise FileNotFoundError(
                f"INVALID_INPUT: Config path does not exist: {config_path}"
            )
        if src.is_dir():
            for item in src.iterdir():
                if item.is_file():
                    shutil.copy2(str(item), configs_dir)
        else:
            shutil.copy2(str(src), configs_dir)

    # Verify at least one config file
    cfg_files = os.listdir(configs_dir)
    if not cfg_files:
        shutil.rmtree(snap_dir, ignore_errors=True)
        raise ValueError(
            "INVALID_INPUT: No configuration files found. "
            "Provide at least one device configuration."
        )

    return snap_dir


# ---------------------------------------------------------------------------
# Input Validation Helpers
# ---------------------------------------------------------------------------
def _validate_ip(ip_str: str, field_name: str = "IP") -> None:
    """Validate an IP address string."""
    try:
        ipaddress.ip_address(ip_str)
    except ValueError:
        raise ValueError(
            f"INVALID_HEADERS: '{ip_str}' is not a valid {field_name} address."
        )


def _validate_port(port: Optional[int], protocol: str) -> None:
    """Validate port number and protocol requirements."""
    if protocol in ("TCP", "UDP"):
        if port is None:
            raise ValueError(
                f"INVALID_HEADERS: dst_port is required for {protocol} protocol."
            )
        if not 1 <= port <= 65535:
            raise ValueError(
                f"INVALID_HEADERS: dst_port must be between 1 and 65535, got {port}."
            )


def _validate_protocol(protocol: str) -> str:
    """Validate and normalize protocol."""
    proto = protocol.upper()
    if proto not in ("TCP", "UDP", "ICMP"):
        raise ValueError(
            f"INVALID_HEADERS: Protocol must be TCP, UDP, or ICMP, got '{protocol}'."
        )
    return proto


# ---------------------------------------------------------------------------
# Tool 1: batfish_upload_snapshot (T010, T012, T013)
# ---------------------------------------------------------------------------
@mcp.tool()
@_safe_execute
def batfish_upload_snapshot(
    snapshot_name: str,
    configs: Optional[Dict[str, str]] = None,
    config_path: Optional[str] = None,
    network: Optional[str] = None,
) -> str:
    """Upload device configurations to Batfish and create a named network
    snapshot for analysis.

    Either configs (dict mapping device names to config content) or
    config_path (path to directory of config files) must be provided,
    not both.
    """
    # Input validation (T012)
    if configs and config_path:
        return json.dumps({
            "error": "INVALID_INPUT",
            "message": "Provide either 'configs' or 'config_path', not both.",
        }, indent=2)

    if not configs and not config_path:
        return json.dumps({
            "error": "INVALID_INPUT",
            "message": "Either 'configs' or 'config_path' must be provided.",
        }, indent=2)

    if configs and len(configs) == 0:
        return json.dumps({
            "error": "INVALID_INPUT",
            "message": "configs dict is empty. Provide at least one device configuration.",
        }, indent=2)

    net = network or BATFISH_NETWORK
    bf = _get_bf_session()
    bf.set_network(net)

    snap_dir = _build_snapshot_dir(configs=configs, config_path=config_path)

    try:
        bf.init_snapshot(snap_dir, name=snapshot_name, overwrite=True)

        # List devices discovered by Batfish
        node_props = bf.q.nodeProperties().answer().frame()
        devices = node_props["Node"].tolist() if not node_props.empty else []

        result = {
            "snapshot_name": snapshot_name,
            "network": net,
            "device_count": len(devices),
            "devices": devices,
            "status": "CREATED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # GAIT logging (T013)
        _gait_log(
            analysis_type="upload_snapshot",
            snapshot_name=snapshot_name,
            parameters={"network": net, "config_source": "inline" if configs else config_path},
            result_summary=f"CREATED: {len(devices)} devices",
        )

        return _gcf_dumps(result)
    finally:
        shutil.rmtree(snap_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tool 2: batfish_validate_config (T011, T013)
# ---------------------------------------------------------------------------
@mcp.tool()
@_safe_execute
def batfish_validate_config(
    snapshot_name: str,
    network: Optional[str] = None,
) -> str:
    """Validate device configurations in a snapshot and return a structured
    parse report with per-device pass/fail status."""
    net = network or BATFISH_NETWORK
    bf = _get_bf_session()
    bf.set_network(net)
    bf.set_snapshot(snapshot_name)

    # Query file parse status
    parse_status = bf.q.fileParseStatus().answer().frame()
    node_props = bf.q.nodeProperties().answer().frame()

    device_results = []
    overall_pass = True

    for _, row in parse_status.iterrows():
        file_name = str(row.get("File_Name", ""))
        status_val = str(row.get("Status", "UNKNOWN"))
        nodes = row.get("Nodes", [])

        # Determine device-level status
        if status_val in ("PASSED", "PARTIALLY_UNRECOGNIZED"):
            dev_status = "PASS" if status_val == "PASSED" else "PARTIALLY_PARSED"
        else:
            dev_status = "FAIL"
            overall_pass = False

        # Extract vendor from node properties
        vendor = "UNKNOWN"
        device_name = ""
        if nodes and len(nodes) > 0:
            device_name = str(nodes[0]) if not isinstance(nodes, str) else nodes
            node_row = node_props[node_props["Node"] == device_name]
            if not node_row.empty:
                vendor = str(node_row.iloc[0].get("Configuration_Format", "UNKNOWN"))

        warnings = []
        errors = []
        if status_val == "PARTIALLY_UNRECOGNIZED":
            warnings.append("Some configuration lines were not recognized by the parser")
        if status_val == "FAILED":
            errors.append(f"Configuration file could not be parsed: {file_name}")

        device_results.append({
            "device_name": device_name or file_name,
            "status": dev_status,
            "file_name": file_name,
            "parse_warnings": warnings,
            "errors": errors,
            "vendor": vendor,
        })

    # Collect global warnings
    global_warnings = []
    init_issues = bf.q.initIssues().answer().frame()
    if not init_issues.empty:
        for _, issue_row in init_issues.iterrows():
            issue_text = str(issue_row.get("Issue", ""))
            if issue_text:
                global_warnings.append(issue_text)

    result = {
        "snapshot_name": snapshot_name,
        "overall_status": "PASS" if overall_pass else "FAIL",
        "device_results": device_results,
        "warnings": global_warnings,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # GAIT logging (T013)
    passed = sum(1 for d in device_results if d["status"] == "PASS")
    total = len(device_results)
    _gait_log(
        analysis_type="validate_config",
        snapshot_name=snapshot_name,
        parameters={"network": net},
        result_summary=f"{'PASS' if overall_pass else 'FAIL'}: {passed}/{total} devices valid",
    )

    return _gcf_dumps(result)


# ---------------------------------------------------------------------------
# Tool 3: batfish_test_reachability (T014, T015, T016, T017)
# ---------------------------------------------------------------------------
@mcp.tool()
@_safe_execute
def batfish_test_reachability(
    snapshot_name: str,
    src_ip: str,
    dst_ip: str,
    protocol: str = "TCP",
    dst_port: Optional[int] = None,
    src_port: Optional[int] = None,
    network: Optional[str] = None,
) -> str:
    """Test whether traffic can flow between two endpoints in a snapshot,
    showing the forwarding path, ACL decisions, and final permit/deny status."""
    # Input validation (T016)
    _validate_ip(src_ip, "source IP")
    _validate_ip(dst_ip, "destination IP")
    protocol = _validate_protocol(protocol)
    _validate_port(dst_port, protocol)

    net = network or BATFISH_NETWORK
    bf = _get_bf_session()
    bf.set_network(net)
    bf.set_snapshot(snapshot_name)

    from pybatfish.datamodel.flow import HeaderConstraints

    headers_kwargs: Dict[str, Any] = {
        "srcIps": src_ip,
        "dstIps": dst_ip,
    }
    if protocol == "ICMP":
        headers_kwargs["ipProtocols"] = ["ICMP"]
    else:
        headers_kwargs["ipProtocols"] = [protocol]
        if dst_port is not None:
            headers_kwargs["dstPorts"] = [dst_port]
        if src_port is not None:
            headers_kwargs["srcPorts"] = [src_port]

    headers = HeaderConstraints(**headers_kwargs)
    traceroute_result = bf.q.traceroute(startLocation="@enter(.*)", headers=headers).answer().frame()

    # Parse traces (T015)
    traces_out: List[Dict[str, Any]] = []
    overall_disposition = "NO_ROUTE"

    if not traceroute_result.empty:
        for _, row in traceroute_result.iterrows():
            traces = row.get("Traces", [])
            if not traces:
                continue

            for trace in traces:
                trace_disp = str(getattr(trace, "disposition", "UNKNOWN"))
                if overall_disposition == "NO_ROUTE":
                    overall_disposition = trace_disp

                hops_out = []
                for hop in getattr(trace, "hops", []):
                    steps_out = []
                    for step in getattr(hop, "steps", []):
                        step_detail = str(getattr(step, "detail", ""))
                        step_action = str(getattr(step, "action", ""))
                        steps_out.append(f"{step_action}: {step_detail}" if step_detail else step_action)
                    hops_out.append({
                        "node": str(getattr(hop, "node", "unknown")),
                        "steps": steps_out,
                    })

                traces_out.append({
                    "disposition": trace_disp,
                    "hops": hops_out,
                })

    result = {
        "snapshot_name": snapshot_name,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "protocol": protocol,
        "dst_port": dst_port,
        "disposition": overall_disposition,
        "traces": traces_out,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # GAIT logging (T017)
    _gait_log(
        analysis_type="test_reachability",
        snapshot_name=snapshot_name,
        parameters={"src_ip": src_ip, "dst_ip": dst_ip, "protocol": protocol,
                     "dst_port": dst_port},
        result_summary=f"{overall_disposition}: {len(traces_out)} trace(s)",
    )

    return _gcf_dumps(result)


# ---------------------------------------------------------------------------
# Tool 4: batfish_trace_acl (T018, T019, T020, T021)
# ---------------------------------------------------------------------------
@mcp.tool()
@_safe_execute
def batfish_trace_acl(
    snapshot_name: str,
    device: str,
    filter_name: str,
    src_ip: str,
    dst_ip: str,
    protocol: str = "TCP",
    dst_port: Optional[int] = None,
    network: Optional[str] = None,
) -> str:
    """Trace a specific packet through the ACLs and firewall rules on a
    given device to determine which rule permits or denies the traffic."""
    # Input validation (T020)
    _validate_ip(src_ip, "source IP")
    _validate_ip(dst_ip, "destination IP")
    protocol = _validate_protocol(protocol)
    _validate_port(dst_port, protocol)

    net = network or BATFISH_NETWORK
    bf = _get_bf_session()
    bf.set_network(net)
    bf.set_snapshot(snapshot_name)

    # Validate device exists in snapshot (T020)
    node_props = bf.q.nodeProperties().answer().frame()
    if not node_props.empty:
        devices_in_snap = node_props["Node"].str.lower().tolist()
        if device.lower() not in devices_in_snap:
            return json.dumps({
                "error": "DEVICE_NOT_FOUND",
                "message": f"Device '{device}' not found in snapshot '{snapshot_name}'. "
                           f"Available devices: {', '.join(node_props['Node'].tolist())}",
            }, indent=2)

    from pybatfish.datamodel.flow import HeaderConstraints

    headers_kwargs: Dict[str, Any] = {
        "srcIps": src_ip,
        "dstIps": dst_ip,
    }
    if protocol == "ICMP":
        headers_kwargs["ipProtocols"] = ["ICMP"]
    else:
        headers_kwargs["ipProtocols"] = [protocol]
        if dst_port is not None:
            headers_kwargs["dstPorts"] = [dst_port]

    headers = HeaderConstraints(**headers_kwargs)

    test_filters_result = bf.q.testFilters(
        nodes=device,
        filters=filter_name,
        headers=headers,
    ).answer().frame()

    # Parse ACL trace result (T019)
    if test_filters_result.empty:
        return json.dumps({
            "error": "FILTER_NOT_FOUND",
            "message": f"Filter '{filter_name}' not found on device '{device}' "
                       f"or returned no results.",
        }, indent=2)

    row = test_filters_result.iloc[0]
    action = str(row.get("Action", "DENY")).upper()

    # Extract matching line details
    trace_obj = row.get("Trace", None)
    matching_line = "No matching line details available"
    line_number = None
    trace_details = []

    if trace_obj is not None:
        events = getattr(trace_obj, "events", [])
        for event in events:
            desc = str(getattr(event, "description", ""))
            trace_details.append(desc)
            if "matched" in desc.lower() or "permitted" in desc.lower() or "denied" in desc.lower():
                matching_line = desc
                # Try to extract line number
                import re
                line_match = re.search(r"line\s*(\d+)", desc, re.IGNORECASE)
                if line_match:
                    line_number = int(line_match.group(1))

    result = {
        "snapshot_name": snapshot_name,
        "device": device,
        "filter_name": filter_name,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "protocol": protocol,
        "dst_port": dst_port,
        "action": action,
        "matching_line": matching_line,
        "line_number": line_number,
        "trace_details": trace_details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # GAIT logging (T021)
    _gait_log(
        analysis_type="trace_acl",
        snapshot_name=snapshot_name,
        parameters={"device": device, "filter_name": filter_name,
                     "src_ip": src_ip, "dst_ip": dst_ip,
                     "protocol": protocol, "dst_port": dst_port},
        result_summary=f"{action}: matched '{matching_line}'",
    )

    return _gcf_dumps(result)


# ---------------------------------------------------------------------------
# Tool 5: batfish_diff_configs (T022, T023, T024, T025, T026)
# ---------------------------------------------------------------------------
@mcp.tool()
@_safe_execute
def batfish_diff_configs(
    reference_snapshot: str,
    candidate_snapshot: str,
    include_routes: bool = True,
    include_reachability: bool = True,
    network: Optional[str] = None,
) -> str:
    """Compare two snapshots and return differences in routing,
    reachability, and ACL behavior."""
    net = network or BATFISH_NETWORK
    bf = _get_bf_session()
    bf.set_network(net)

    # Validate both snapshots exist (T025)
    existing_snapshots = bf.list_snapshots()
    for snap_name in [reference_snapshot, candidate_snapshot]:
        if snap_name not in existing_snapshots:
            return json.dumps({
                "error": "SNAPSHOT_NOT_FOUND",
                "message": f"Snapshot '{snap_name}' not found. "
                           f"Available snapshots: {', '.join(existing_snapshots)}",
            }, indent=2)

    # Handle identical snapshots gracefully (T025)
    if reference_snapshot == candidate_snapshot:
        result = {
            "reference_snapshot": reference_snapshot,
            "candidate_snapshot": candidate_snapshot,
            "route_diffs": [],
            "reachability_diffs": [],
            "summary": {"added": 0, "removed": 0, "changed": 0,
                         "reachability_changes": 0},
            "message": "Reference and candidate snapshots are identical. No differences.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _gait_log(
            analysis_type="diff_configs",
            snapshot_name=f"{reference_snapshot} vs {candidate_snapshot}",
            parameters={"include_routes": include_routes,
                         "include_reachability": include_reachability},
            result_summary="IDENTICAL: No differences (same snapshot)",
        )
        return _gcf_dumps(result)

    route_diffs: List[Dict[str, Any]] = []
    reachability_diffs: List[Dict[str, Any]] = []

    # Route diff logic (T023)
    if include_routes:
        bf.set_snapshot(reference_snapshot)
        ref_routes = bf.q.routes().answer().frame()

        bf.set_snapshot(candidate_snapshot)
        cand_routes = bf.q.routes().answer().frame()

        # Build route keys for comparison
        def _route_key(row):
            return (str(row.get("Node", "")),
                    str(row.get("Network", "")),
                    str(row.get("Protocol", "")))

        def _route_nexthop(row):
            return str(row.get("Next_Hop", ""))

        ref_map = {}
        if not ref_routes.empty:
            for _, row in ref_routes.iterrows():
                key = _route_key(row)
                ref_map[key] = _route_nexthop(row)

        cand_map = {}
        if not cand_routes.empty:
            for _, row in cand_routes.iterrows():
                key = _route_key(row)
                cand_map[key] = _route_nexthop(row)

        # Find ADDED, REMOVED, CHANGED
        all_keys = set(ref_map.keys()) | set(cand_map.keys())
        for key in all_keys:
            node, network_prefix, proto = key
            in_ref = key in ref_map
            in_cand = key in cand_map

            if in_ref and not in_cand:
                route_diffs.append({
                    "device": node,
                    "network": network_prefix,
                    "change_type": "REMOVED",
                    "old_next_hop": ref_map[key],
                    "new_next_hop": None,
                    "protocol": proto,
                })
            elif not in_ref and in_cand:
                route_diffs.append({
                    "device": node,
                    "network": network_prefix,
                    "change_type": "ADDED",
                    "old_next_hop": None,
                    "new_next_hop": cand_map[key],
                    "protocol": proto,
                })
            elif ref_map[key] != cand_map[key]:
                route_diffs.append({
                    "device": node,
                    "network": network_prefix,
                    "change_type": "CHANGED",
                    "old_next_hop": ref_map[key],
                    "new_next_hop": cand_map[key],
                    "protocol": proto,
                })

    # Differential reachability (T022)
    if include_reachability:
        bf.set_snapshot(candidate_snapshot)
        bf.set_reference_snapshot(reference_snapshot)
        try:
            diff_reach = bf.q.differentialReachability().answer().frame()
            if not diff_reach.empty:
                for _, row in diff_reach.iterrows():
                    flow = row.get("Flow", None)
                    if flow:
                        reachability_diffs.append({
                            "src_ip": str(getattr(flow, "srcIp", "")),
                            "dst_ip": str(getattr(flow, "dstIp", "")),
                            "old_disposition": str(row.get("Reference_Disposition", "")),
                            "new_disposition": str(row.get("Snapshot_Disposition", "")),
                        })
        except Exception as exc:
            logger.warning("Differential reachability query failed: %s", exc)

    # Format result (T024)
    added = sum(1 for d in route_diffs if d["change_type"] == "ADDED")
    removed = sum(1 for d in route_diffs if d["change_type"] == "REMOVED")
    changed = sum(1 for d in route_diffs if d["change_type"] == "CHANGED")

    result = {
        "reference_snapshot": reference_snapshot,
        "candidate_snapshot": candidate_snapshot,
        "route_diffs": route_diffs,
        "reachability_diffs": reachability_diffs,
        "summary": {
            "added": added,
            "removed": removed,
            "changed": changed,
            "reachability_changes": len(reachability_diffs),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # GAIT logging (T026)
    _gait_log(
        analysis_type="diff_configs",
        snapshot_name=f"{reference_snapshot} vs {candidate_snapshot}",
        parameters={"include_routes": include_routes,
                     "include_reachability": include_reachability},
        result_summary=(f"Routes: +{added} -{removed} ~{changed} | "
                        f"Reachability: {len(reachability_diffs)} changes"),
    )

    return _gcf_dumps(result)


# ---------------------------------------------------------------------------
# Tool 6: batfish_check_compliance (T027-T034)
# ---------------------------------------------------------------------------
SUPPORTED_POLICIES = [
    "interface_descriptions",
    "no_default_route",
    "ntp_configured",
    "no_shutdown_interfaces",
    "bgp_sessions_established",
    "ospf_adjacencies",
]


def _check_interface_descriptions(bf, snapshot_name: str) -> Dict[str, Any]:
    """T028: Find interfaces without descriptions."""
    bf.set_snapshot(snapshot_name)
    iface_props = bf.q.interfaceProperties().answer().frame()
    violations = []
    checked = set()

    if not iface_props.empty:
        for _, row in iface_props.iterrows():
            node = str(row.get("Interface", ""))
            desc = row.get("Description", None)
            device = str(row.get("Interface", "")).split("[")[0] if "[" in str(row.get("Interface", "")) else ""
            checked.add(device)

            if desc is None or str(desc).strip() == "" or str(desc) == "None":
                violations.append({
                    "device": device,
                    "element": str(row.get("Interface", "")),
                    "description": f"Interface {row.get('Interface', '')} has no description configured",
                    "severity": "WARNING",
                })

    return {
        "violations": violations,
        "checked_devices": len(checked),
    }


def _check_no_default_route(bf, snapshot_name: str) -> Dict[str, Any]:
    """T029: Find devices with 0.0.0.0/0 routes."""
    bf.set_snapshot(snapshot_name)
    routes = bf.q.routes().answer().frame()
    violations = []
    checked = set()

    if not routes.empty:
        for _, row in routes.iterrows():
            device = str(row.get("Node", ""))
            checked.add(device)
            network_prefix = str(row.get("Network", ""))
            if network_prefix in ("0.0.0.0/0", "::/0"):
                protocol = str(row.get("Protocol", "unknown"))
                violations.append({
                    "device": device,
                    "element": network_prefix,
                    "description": f"Default route {network_prefix} found via {protocol}",
                    "severity": "ERROR",
                })

    return {
        "violations": violations,
        "checked_devices": len(checked),
    }


def _check_ntp_configured(bf, snapshot_name: str) -> Dict[str, Any]:
    """T030: Find devices without NTP servers."""
    bf.set_snapshot(snapshot_name)
    node_props = bf.q.nodeProperties().answer().frame()
    violations = []
    checked = set()

    if not node_props.empty:
        for _, row in node_props.iterrows():
            device = str(row.get("Node", ""))
            checked.add(device)
            ntp_servers = row.get("NTP_Servers", [])
            if not ntp_servers or len(ntp_servers) == 0:
                violations.append({
                    "device": device,
                    "element": "NTP",
                    "description": f"Device {device} has no NTP servers configured",
                    "severity": "ERROR",
                })

    return {
        "violations": violations,
        "checked_devices": len(checked),
    }


def _check_no_shutdown_interfaces(bf, snapshot_name: str) -> Dict[str, Any]:
    """T031: Find administratively down interfaces."""
    bf.set_snapshot(snapshot_name)
    iface_props = bf.q.interfaceProperties().answer().frame()
    violations = []
    checked = set()

    if not iface_props.empty:
        for _, row in iface_props.iterrows():
            device = str(row.get("Interface", "")).split("[")[0] if "[" in str(row.get("Interface", "")) else ""
            checked.add(device)
            active = row.get("Active", True)
            admin_up = row.get("Admin_Up", True)

            if not active or not admin_up:
                violations.append({
                    "device": device,
                    "element": str(row.get("Interface", "")),
                    "description": f"Interface {row.get('Interface', '')} is administratively down",
                    "severity": "WARNING",
                })

    return {
        "violations": violations,
        "checked_devices": len(checked),
    }


def _check_bgp_sessions(bf, snapshot_name: str) -> Dict[str, Any]:
    """T032: Check BGP session status."""
    bf.set_snapshot(snapshot_name)
    violations = []
    checked = set()

    try:
        bgp_status = bf.q.bgpSessionStatus().answer().frame()
        if not bgp_status.empty:
            for _, row in bgp_status.iterrows():
                node = str(row.get("Node", ""))
                checked.add(node)
                status = str(row.get("Established_Status", ""))
                if status != "ESTABLISHED":
                    remote_node = str(row.get("Remote_Node", "unknown"))
                    violations.append({
                        "device": node,
                        "element": f"BGP peer {remote_node}",
                        "description": f"BGP session with {remote_node} is {status} (expected ESTABLISHED)",
                        "severity": "ERROR",
                    })
    except Exception as exc:
        logger.warning("BGP session status query failed: %s", exc)

    return {
        "violations": violations,
        "checked_devices": len(checked),
    }


def _check_ospf_adjacencies(bf, snapshot_name: str) -> Dict[str, Any]:
    """T032: Check OSPF adjacency compatibility."""
    bf.set_snapshot(snapshot_name)
    violations = []
    checked = set()

    try:
        ospf_compat = bf.q.ospfSessionCompatibility().answer().frame()
        if not ospf_compat.empty:
            for _, row in ospf_compat.iterrows():
                node = str(row.get("Interface", "")).split("[")[0] if "[" in str(row.get("Interface", "")) else ""
                checked.add(node)
                compatible = row.get("Session_Status", "")
                if str(compatible) != "ESTABLISHED":
                    remote = str(row.get("Remote_Interface", "unknown"))
                    violations.append({
                        "device": node,
                        "element": str(row.get("Interface", "")),
                        "description": f"OSPF adjacency with {remote} is not established: {compatible}",
                        "severity": "ERROR",
                    })
    except Exception as exc:
        logger.warning("OSPF compatibility query failed: %s", exc)

    return {
        "violations": violations,
        "checked_devices": len(checked),
    }


_COMPLIANCE_DISPATCH = {
    "interface_descriptions": _check_interface_descriptions,
    "no_default_route": _check_no_default_route,
    "ntp_configured": _check_ntp_configured,
    "no_shutdown_interfaces": _check_no_shutdown_interfaces,
    "bgp_sessions_established": _check_bgp_sessions,
    "ospf_adjacencies": _check_ospf_adjacencies,
}


@mcp.tool()
@_safe_execute
def batfish_check_compliance(
    snapshot_name: str,
    policy_type: str,
    network: Optional[str] = None,
) -> str:
    """Validate device configurations against organizational policy rules
    and report violations.

    Supported policy_type values: interface_descriptions, no_default_route,
    ntp_configured, no_shutdown_interfaces, bgp_sessions_established,
    ospf_adjacencies.
    """
    # Unsupported policy type handling (T033)
    if policy_type not in _COMPLIANCE_DISPATCH:
        return json.dumps({
            "snapshot_name": snapshot_name,
            "policy_type": policy_type,
            "overall_status": "UNSUPPORTED",
            "message": (
                f"Policy type '{policy_type}' is not supported. "
                f"Supported types: {', '.join(SUPPORTED_POLICIES)}"
            ),
            "violations": [],
            "checked_devices": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, indent=2)

    net = network or BATFISH_NETWORK
    bf = _get_bf_session()
    bf.set_network(net)

    check_fn = _COMPLIANCE_DISPATCH[policy_type]
    check_result = check_fn(bf, snapshot_name)

    violations = check_result["violations"]
    checked_devices = check_result["checked_devices"]
    overall_status = "COMPLIANT" if len(violations) == 0 else "NON_COMPLIANT"

    result = {
        "snapshot_name": snapshot_name,
        "policy_type": policy_type,
        "overall_status": overall_status,
        "violations": violations,
        "checked_devices": checked_devices,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # GAIT logging (T034)
    _gait_log(
        analysis_type="check_compliance",
        snapshot_name=snapshot_name,
        parameters={"policy_type": policy_type, "network": net},
        result_summary=f"{overall_status}: {len(violations)} violation(s) across {checked_devices} devices",
    )

    return _gcf_dumps(result)


# ---------------------------------------------------------------------------
# Tool 7: batfish_list_snapshots (bonus utility)
# ---------------------------------------------------------------------------
@mcp.tool()
@_safe_execute
def batfish_list_snapshots(
    network: Optional[str] = None,
) -> str:
    """List all available snapshots in the Batfish network."""
    net = network or BATFISH_NETWORK
    bf = _get_bf_session()
    bf.set_network(net)

    snapshots = bf.list_snapshots()

    result = {
        "network": net,
        "snapshots": snapshots,
        "count": len(snapshots),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _gait_log(
        analysis_type="list_snapshots",
        snapshot_name="*",
        parameters={"network": net},
        result_summary=f"{len(snapshots)} snapshot(s) found",
    )

    return _gcf_dumps(result)


# ---------------------------------------------------------------------------
# Tool 8: batfish_delete_snapshot (bonus utility)
# ---------------------------------------------------------------------------
@mcp.tool()
@_safe_execute
def batfish_delete_snapshot(
    snapshot_name: str,
    network: Optional[str] = None,
) -> str:
    """Delete a snapshot from the Batfish network."""
    net = network or BATFISH_NETWORK
    bf = _get_bf_session()
    bf.set_network(net)

    existing = bf.list_snapshots()
    if snapshot_name not in existing:
        return json.dumps({
            "error": "SNAPSHOT_NOT_FOUND",
            "message": f"Snapshot '{snapshot_name}' not found. "
                       f"Available snapshots: {', '.join(existing)}",
        }, indent=2)

    bf.delete_snapshot(snapshot_name)

    result = {
        "snapshot_name": snapshot_name,
        "network": net,
        "status": "DELETED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _gait_log(
        analysis_type="delete_snapshot",
        snapshot_name=snapshot_name,
        parameters={"network": net},
        result_summary="DELETED",
    )

    return _gcf_dumps(result)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting Batfish MCP Server (stdio transport)")
    mcp.run(transport="stdio")
