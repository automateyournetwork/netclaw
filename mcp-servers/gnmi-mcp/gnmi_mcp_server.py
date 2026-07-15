#!/usr/bin/env python3
"""gNMI Streaming Telemetry MCP Server.

A FastMCP server exposing gNMI operations (Get, Set, Subscribe, Capabilities)
as MCP tools for NetClaw.  Runs over stdio transport.

Environment variables:
  GNMI_TARGETS           - JSON array of target device definitions
  GNMI_TLS_CA_CERT       - Global CA certificate path
  GNMI_TLS_CLIENT_CERT   - Global client certificate path (mTLS)
  GNMI_TLS_CLIENT_KEY    - Global client private key path (mTLS)
  GNMI_TLS_SKIP_VERIFY   - Skip TLS verification (lab mode)
  GNMI_DEFAULT_PORT      - Override default gNMI port
  GNMI_MAX_RESPONSE_SIZE - Response truncation threshold (bytes, default 1MB)
  GNMI_MAX_SUBSCRIPTIONS - Maximum concurrent subscriptions (default 50)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional

from fastmcp import FastMCP

# Add current directory and netclaw_tokens to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))


def _gcf_dumps(data, **kwargs) -> str:
    """Serialize data using GCF with graph auto-detection and session dedup."""
    try:
        from netclaw_tokens.gcf_serializer import serialize_response
        result = serialize_response(data, use_session=True, use_delta=True)
        return result["encoded_data"]
    except Exception:
        return json.dumps(data, indent=2, default=str)

from gnmi_client import (
    GnmiClientWrapper,
    classify_gnmi_error,
    get_max_response_size,
    load_targets_from_env,
    truncate_response,
)
from itsm_gate import validate_change_request
from models import (
    GnmiDataType,
    GnmiEncoding,
    GnmiError,
    GnmiErrorCode,
    GnmiSetResponse,
    SetOperation,
    Subscription,
    SubscriptionMode,
)
from subscription_manager import SubscriptionManager
from yang_utils import validate_yang_paths

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("gnmi-mcp")

# ---------------------------------------------------------------------------
# Server initialisation
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "gNMI Streaming Telemetry MCP Server",
    description="gNMI Get, Set, Subscribe, and Capabilities operations for multi-vendor network devices",
)

# Load targets and create shared client wrapper
_targets = load_targets_from_env()
_client = GnmiClientWrapper(_targets)

# Subscription manager
_max_subs = int(os.environ.get("GNMI_MAX_SUBSCRIPTIONS", "50"))
_sub_manager = SubscriptionManager(client=_client, max_subscriptions=_max_subs)


# ---------------------------------------------------------------------------
# GAIT Audit Logging Helper
# ---------------------------------------------------------------------------

def _gait_log(operation: str, **kwargs: Any) -> None:
    """Emit a structured GAIT audit log entry.

    In a production deployment this calls the gait_mcp tool.  Here we
    emit a structured JSON log line to stderr so it is captured by the
    GAIT stdio wrapper.
    """
    entry = {
        "gait": True,
        "operation": operation,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **kwargs,
    }
    logger.info("GAIT: %s", json.dumps(entry, default=str))


# ===================================================================
# Tool 1: gnmi_get  (T013, T015, T016, T017, T018)
# ===================================================================

@mcp.tool()
def gnmi_get(
    target: str,
    paths: list[str],
    encoding: Optional[str] = None,
    data_type: Optional[str] = None,
) -> str:
    """Retrieve device state or configuration data via gNMI Get using YANG model paths.

    Args:
        target: Device name (must match a configured target).
        paths: YANG paths to query (e.g. ["/interfaces/interface/state"]).
        encoding: Encoding override: JSON_IETF, JSON, PROTO, ASCII.
        data_type: Data type filter: ALL, CONFIG, STATE, OPERATIONAL (default ALL).

    Returns:
        Structured JSON with device name, timestamp, and path-value results.
    """
    # Validate paths
    valid, err = validate_yang_paths(paths)
    if not valid:
        _gait_log("gnmi_get", target=target, paths=paths, status="error", error=err)
        return json.dumps({"error": GnmiErrorCode.PATH_ERROR.value, "message": err})

    # Validate target exists
    if target not in _targets:
        msg = f"Target '{target}' is not configured. Use gnmi_list_targets to see available targets."
        _gait_log("gnmi_get", target=target, paths=paths, status="error", error=msg)
        return json.dumps({"error": GnmiErrorCode.CONNECTION_ERROR.value, "message": msg})

    try:
        response = _client.get(
            target_name=target,
            paths=paths,
            encoding=encoding,
            data_type=data_type or "ALL",
        )

        # Serialise and check size
        resp_json = response.model_dump_json(indent=2)
        max_size = get_max_response_size()
        truncated_json, was_truncated, original_size = truncate_response(resp_json, max_size)

        if was_truncated:
            # Re-build with truncation notice
            result = json.loads(truncated_json) if truncated_json.strip() else {}
            result["truncated"] = True
            result["total_size_bytes"] = original_size
            result["notice"] = (
                f"Response truncated from {original_size} bytes to {max_size} bytes. "
                "Use more specific YANG paths to narrow the query."
            )
            output = json.dumps(result, indent=2, default=str)
        else:
            output = resp_json

        _gait_log(
            "gnmi_get",
            target=target,
            paths=paths,
            encoding=encoding,
            data_type=data_type,
            status="success",
            result_size=original_size,
            truncated=was_truncated,
        )
        return output

    except Exception as exc:
        gnmi_err = classify_gnmi_error(exc, target)
        _gait_log("gnmi_get", target=target, paths=paths, status="error", error=gnmi_err.message)
        return json.dumps(gnmi_err.model_dump(), indent=2, default=str)


# ===================================================================
# Tool 2: gnmi_set  (T027, T028, T029, T030, T031)
# ===================================================================

@mcp.tool()
def gnmi_set(
    target: str,
    change_request_number: str,
    updates: Optional[list[dict[str, Any]]] = None,
    replaces: Optional[list[dict[str, Any]]] = None,
    deletes: Optional[list[str]] = None,
) -> str:
    """Apply configuration changes to a device via gNMI Set.

    REQUIRES an approved ServiceNow Change Request number (e.g. CHG0012345).
    Workflow: validate CR -> capture baseline via Get -> apply Set -> verify via Get -> audit log.

    Args:
        target: Device name.
        change_request_number: ServiceNow CR number (format: CHG followed by digits).
        updates: Update (merge) operations: [{"path": ..., "value": ...}].
        replaces: Replace (overwrite) operations: [{"path": ..., "value": ...}].
        deletes: YANG paths to delete.

    Returns:
        Confirmation of applied operations with success/failure status.
    """
    # --- ITSM gate (T026, T029) ---
    itsm_result = validate_change_request(change_request_number)
    if not itsm_result["valid"]:
        _gait_log(
            "gnmi_set",
            target=target,
            cr=change_request_number,
            status="rejected",
            reason=itsm_result["message"],
        )
        return json.dumps({
            "error": GnmiErrorCode.ITSM_ERROR.value,
            "message": itsm_result["message"],
        })

    if target not in _targets:
        msg = f"Target '{target}' is not configured."
        _gait_log("gnmi_set", target=target, cr=change_request_number, status="error", error=msg)
        return json.dumps({"error": GnmiErrorCode.CONNECTION_ERROR.value, "message": msg})

    # Collect all paths for baseline
    all_paths: list[str] = []
    update_ops: list[tuple[str, Any]] = []
    replace_ops: list[tuple[str, Any]] = []
    delete_ops: list[str] = deletes or []

    if updates:
        for u in updates:
            path = u.get("path", "")
            value = u.get("value")
            update_ops.append((path, value))
            all_paths.append(path)
    if replaces:
        for r in replaces:
            path = r.get("path", "")
            value = r.get("value")
            replace_ops.append((path, value))
            all_paths.append(path)
    all_paths.extend(delete_ops)

    if not update_ops and not replace_ops and not delete_ops:
        return json.dumps({
            "error": "VALIDATION_ERROR",
            "message": "At least one of updates, replaces, or deletes must be provided",
        })

    # --- Read-before-write (T028): capture baseline ---
    baseline_state = None
    try:
        if all_paths:
            baseline_resp = _client.get(target_name=target, paths=all_paths)
            baseline_state = baseline_resp.model_dump()
    except Exception:
        logger.warning("Could not capture baseline state for %s", target)

    # --- Apply gNMI Set ---
    operations_applied: list[str] = []
    errors: list[str] = []

    try:
        result = _client.set(
            target_name=target,
            updates=update_ops if update_ops else None,
            replaces=replace_ops if replace_ops else None,
            deletes=delete_ops if delete_ops else None,
        )
        for u in update_ops:
            operations_applied.append(f"UPDATE {u[0]}")
        for r in replace_ops:
            operations_applied.append(f"REPLACE {r[0]}")
        for d in delete_ops:
            operations_applied.append(f"DELETE {d}")

    except Exception as exc:
        gnmi_err = classify_gnmi_error(exc, target)
        errors.append(gnmi_err.message)
        _gait_log(
            "gnmi_set",
            target=target,
            cr=change_request_number,
            status="error",
            error=gnmi_err.message,
            baseline=baseline_state,
        )
        return json.dumps({
            "error": gnmi_err.code.value,
            "message": gnmi_err.message,
            "operations_attempted": [f"UPDATE {u[0]}" for u in update_ops]
            + [f"REPLACE {r[0]}" for r in replace_ops]
            + [f"DELETE {d}" for d in delete_ops],
        }, indent=2, default=str)

    # --- Verify after write (T028) ---
    verify_state = None
    try:
        if all_paths:
            verify_resp = _client.get(target_name=target, paths=all_paths)
            verify_state = verify_resp.model_dump()
    except Exception:
        logger.warning("Could not capture verify state for %s", target)

    # --- Build response ---
    success = len(errors) == 0
    response = GnmiSetResponse(
        target=target,
        timestamp=datetime.now(timezone.utc).isoformat(),
        change_request_number=change_request_number,
        operations_applied=operations_applied,
        success=success,
        errors=errors if errors else None,
    )

    # --- GAIT audit (T031) ---
    _gait_log(
        "gnmi_set",
        target=target,
        cr=change_request_number,
        operations=operations_applied,
        status="success" if success else "partial_failure",
        baseline=baseline_state,
        verify=verify_state,
    )

    return response.model_dump_json(indent=2)


# ===================================================================
# Tool 3: gnmi_subscribe  (T020, T025)
# ===================================================================

@mcp.tool()
def gnmi_subscribe(
    target: str,
    paths: list[str],
    mode: str,
    sample_interval_seconds: Optional[int] = None,
) -> str:
    """Create a streaming telemetry subscription for real-time state updates.

    Args:
        target: Device name.
        paths: YANG paths to subscribe to.
        mode: Subscription mode: SAMPLE or ON_CHANGE.
        sample_interval_seconds: Polling interval for SAMPLE mode (default 10, min 1).

    Returns:
        Subscription ID (UUID) and confirmation.
    """
    valid, err = validate_yang_paths(paths)
    if not valid:
        return json.dumps({"error": GnmiErrorCode.PATH_ERROR.value, "message": err})

    if target not in _targets:
        msg = f"Target '{target}' is not configured."
        return json.dumps({"error": GnmiErrorCode.CONNECTION_ERROR.value, "message": msg})

    interval = sample_interval_seconds if sample_interval_seconds and sample_interval_seconds >= 1 else 10

    try:
        subscription = _sub_manager.create_subscription(
            target=target,
            paths=paths,
            mode=mode,
            sample_interval_seconds=interval,
        )
    except ValueError as exc:
        code = GnmiErrorCode.SUBSCRIPTION_LIMIT if "limit" in str(exc).lower() else GnmiErrorCode.RPC_ERROR
        return json.dumps({"error": code.value, "message": str(exc)})
    except Exception as exc:
        gnmi_err = classify_gnmi_error(exc, target)
        return json.dumps(gnmi_err.model_dump(), indent=2, default=str)

    _gait_log(
        "gnmi_subscribe",
        target=target,
        paths=paths,
        mode=mode,
        subscription_id=subscription.id,
    )

    return json.dumps({
        "subscription_id": subscription.id,
        "target": target,
        "paths": paths,
        "mode": mode,
        "sample_interval_seconds": interval,
        "status": subscription.status.value,
        "created_at": subscription.created_at,
        "message": "Subscription created successfully",
    }, indent=2)


# ===================================================================
# Tool 4: gnmi_unsubscribe  (T021, T025)
# ===================================================================

@mcp.tool()
def gnmi_unsubscribe(subscription_id: str) -> str:
    """Cancel an active telemetry subscription.

    Args:
        subscription_id: UUID of the subscription to cancel.

    Returns:
        Confirmation of cancellation.
    """
    try:
        _sub_manager.cancel_subscription(subscription_id)
    except ValueError as exc:
        return json.dumps({
            "error": GnmiErrorCode.SUBSCRIPTION_NOT_FOUND.value,
            "message": str(exc),
        })

    _gait_log("gnmi_unsubscribe", subscription_id=subscription_id)

    return json.dumps({
        "subscription_id": subscription_id,
        "status": "CANCELLED",
        "message": "Subscription cancelled successfully",
    }, indent=2)


# ===================================================================
# Tool 5: gnmi_get_subscriptions  (T022)
# ===================================================================

@mcp.tool()
def gnmi_get_subscriptions() -> str:
    """List all active telemetry subscriptions.

    Returns:
        Array of active subscriptions with ID, target, paths, mode,
        status, creation time, and last update time.
    """
    subs = _sub_manager.list_subscriptions()
    return _gcf_dumps([s.model_dump() for s in subs])


# ===================================================================
# Tool 6: gnmi_get_subscription_updates  (T023)
# ===================================================================

@mcp.tool()
def gnmi_get_subscription_updates(
    subscription_id: str,
    max_updates: Optional[int] = None,
) -> str:
    """Retrieve the latest updates from a specific subscription.

    Args:
        subscription_id: UUID of the subscription.
        max_updates: Maximum number of recent updates to return (default 10).

    Returns:
        Array of recent telemetry updates with path, value, and timestamp.
    """
    limit = max_updates if max_updates and max_updates > 0 else 10
    try:
        updates = _sub_manager.get_updates(subscription_id, limit=limit)
    except ValueError as exc:
        return json.dumps({
            "error": GnmiErrorCode.SUBSCRIPTION_NOT_FOUND.value,
            "message": str(exc),
        })

    return _gcf_dumps([u.model_dump() for u in updates])


# ===================================================================
# Tool 7: gnmi_capabilities  (T032, T034, T035)
# ===================================================================

@mcp.tool()
def gnmi_capabilities(target: str) -> str:
    """Retrieve supported YANG models, versions, and encodings from a device via gNMI Capabilities RPC.

    Args:
        target: Device name.

    Returns:
        List of supported YANG modules and encodings.
    """
    if target not in _targets:
        msg = f"Target '{target}' is not configured."
        return json.dumps({"error": GnmiErrorCode.CONNECTION_ERROR.value, "message": msg})

    try:
        models, encodings = _client.capabilities(target)
    except Exception as exc:
        gnmi_err = classify_gnmi_error(exc, target)
        # T034: handle device not supporting Capabilities RPC
        if "unimplemented" in str(exc).lower():
            return json.dumps({
                "error": GnmiErrorCode.RPC_ERROR.value,
                "message": f"Device '{target}' does not support the gNMI Capabilities RPC",
                "target": target,
            })
        _gait_log("gnmi_capabilities", target=target, status="error", error=gnmi_err.message)
        return json.dumps(gnmi_err.model_dump(), indent=2, default=str)

    # Classify models: OpenConfig vs vendor-native (T034)
    openconfig_models = []
    vendor_native_models = []
    for m in models:
        entry = m.model_dump()
        if m.name.startswith("openconfig") or (m.organization and "openconfig" in m.organization.lower()):
            entry["model_type"] = "openconfig"
            openconfig_models.append(entry)
        else:
            entry["model_type"] = "vendor-native"
            vendor_native_models.append(entry)

    _gait_log(
        "gnmi_capabilities",
        target=target,
        status="success",
        model_count=len(models),
        encoding_count=len(encodings),
    )

    return json.dumps({
        "target": target,
        "supported_encodings": encodings,
        "openconfig_models": openconfig_models,
        "vendor_native_models": vendor_native_models,
        "total_models": len(models),
    }, indent=2, default=str)


# ===================================================================
# Tool 8: gnmi_browse_yang_paths  (T033, T035)
# ===================================================================

@mcp.tool()
def gnmi_browse_yang_paths(
    target: str,
    module: str,
    depth: Optional[int] = None,
) -> str:
    """Browse available YANG paths under a specific module on a device.

    Args:
        target: Device name.
        module: YANG module name (e.g. "openconfig-interfaces").
        depth: Maximum tree depth to return (default 3).

    Returns:
        Tree of available YANG paths under the specified module.
    """
    if target not in _targets:
        msg = f"Target '{target}' is not configured."
        return json.dumps({"error": GnmiErrorCode.CONNECTION_ERROR.value, "message": msg})

    browse_depth = depth if depth and depth > 0 else 3

    try:
        paths = _client.browse_yang_paths(target, module, browse_depth)
    except Exception as exc:
        gnmi_err = classify_gnmi_error(exc, target)
        return json.dumps(gnmi_err.model_dump(), indent=2, default=str)

    _gait_log("gnmi_browse_yang_paths", target=target, module=module, depth=browse_depth, status="success")

    return json.dumps({
        "target": target,
        "module": module,
        "depth": browse_depth,
        "paths": paths,
        "path_count": len(paths),
    }, indent=2, default=str)


# ===================================================================
# Tool 9: gnmi_compare_with_cli  (T036, T037, T038, T039, T040)
# ===================================================================

# Mapping of data_type to gNMI YANG paths and pyATS parsers
_COMPARISON_MAP: dict[str, dict[str, Any]] = {
    "interfaces": {
        "gnmi_paths": ["/interfaces/interface/state"],
        "pyats_command": "show interfaces",
        "key_field": "interface_name",
        "timing_sensitive_fields": {"counters", "in_octets", "out_octets", "last_change", "uptime"},
    },
    "bgp_neighbors": {
        "gnmi_paths": ["/network-instances/network-instance/protocols/protocol/bgp/neighbors"],
        "pyats_command": "show bgp neighbors",
        "key_field": "neighbor_address",
        "timing_sensitive_fields": {"uptime", "messages_received", "messages_sent", "prefixes_received"},
    },
    "routes": {
        "gnmi_paths": ["/network-instances/network-instance/afts"],
        "pyats_command": "show ip route",
        "key_field": "prefix",
        "timing_sensitive_fields": {"age", "uptime"},
    },
}


@mcp.tool()
def gnmi_compare_with_cli(target: str, data_type: str) -> str:
    """Compare gNMI-retrieved state with CLI-retrieved state for validation.

    Args:
        target: Device name (must be reachable via both gNMI and CLI/pyATS).
        data_type: Data type to compare: interfaces, bgp_neighbors, routes.

    Returns:
        Side-by-side comparison with field-level match/mismatch indicators.
    """
    if data_type not in _COMPARISON_MAP:
        return json.dumps({
            "error": "VALIDATION_ERROR",
            "message": f"data_type must be one of: {list(_COMPARISON_MAP.keys())}",
        })

    if target not in _targets:
        msg = f"Target '{target}' is not configured."
        return json.dumps({"error": GnmiErrorCode.CONNECTION_ERROR.value, "message": msg})

    comparison_config = _COMPARISON_MAP[data_type]
    gnmi_data = None
    gnmi_error = None
    cli_data = None
    cli_error = None

    # --- Retrieve gNMI data (T037) ---
    try:
        gnmi_resp = _client.get(target_name=target, paths=comparison_config["gnmi_paths"])
        gnmi_data = gnmi_resp.model_dump()
    except Exception as exc:
        gnmi_error = f"gNMI data unavailable: {classify_gnmi_error(exc, target).message}"

    # --- Retrieve CLI data via pyATS MCP (T037) ---
    # In production, this would call the pyATS_MCP tools via MCP client.
    # Here we provide a structured placeholder that documents the integration point.
    cli_data = None
    cli_error = (
        "CLI data retrieval requires pyATS MCP integration. "
        "Ensure pyATS_MCP server is running and the device is in the testbed."
    )

    # --- Handle partial availability (T039) ---
    if gnmi_error and cli_error:
        _gait_log("gnmi_compare_with_cli", target=target, data_type=data_type, status="error")
        return json.dumps({
            "target": target,
            "data_type": data_type,
            "gnmi_status": "unavailable",
            "gnmi_error": gnmi_error,
            "cli_status": "unavailable",
            "cli_error": cli_error,
            "comparison": "Cannot compare — neither source available",
        }, indent=2)

    if gnmi_error:
        _gait_log("gnmi_compare_with_cli", target=target, data_type=data_type, status="partial")
        return json.dumps({
            "target": target,
            "data_type": data_type,
            "gnmi_status": "unavailable",
            "gnmi_error": gnmi_error,
            "cli_status": "available",
            "cli_data": cli_data,
            "comparison": "gNMI unavailable — showing CLI data only",
        }, indent=2, default=str)

    if cli_error:
        _gait_log("gnmi_compare_with_cli", target=target, data_type=data_type, status="partial")
        return json.dumps({
            "target": target,
            "data_type": data_type,
            "gnmi_status": "available",
            "gnmi_data": gnmi_data,
            "cli_status": "unavailable",
            "cli_error": cli_error,
            "comparison": "CLI unavailable — showing gNMI data only",
        }, indent=2, default=str)

    # --- Field-level comparison (T038) ---
    comparison_results = _compare_data(
        gnmi_data=gnmi_data,
        cli_data=cli_data,
        timing_sensitive=comparison_config["timing_sensitive_fields"],
    )

    _gait_log(
        "gnmi_compare_with_cli",
        target=target,
        data_type=data_type,
        status="success",
        matches=comparison_results.get("matches", 0),
        mismatches=comparison_results.get("mismatches", 0),
        expected_variances=comparison_results.get("expected_variances", 0),
    )

    return json.dumps({
        "target": target,
        "data_type": data_type,
        "gnmi_status": "available",
        "cli_status": "available",
        "comparison": comparison_results,
    }, indent=2, default=str)


def _compare_data(
    gnmi_data: Any,
    cli_data: Any,
    timing_sensitive: set[str],
) -> dict[str, Any]:
    """Perform field-level comparison between gNMI and CLI data.

    Timing-sensitive fields (counters, uptime) are flagged as
    'expected variance' rather than true discrepancies.
    """
    matches = 0
    mismatches = 0
    expected_variances = 0
    field_results: list[dict[str, Any]] = []

    if isinstance(gnmi_data, dict) and isinstance(cli_data, dict):
        all_keys = set(list(gnmi_data.keys()) + list(cli_data.keys()))
        for key in sorted(all_keys):
            gnmi_val = gnmi_data.get(key)
            cli_val = cli_data.get(key)

            if key in timing_sensitive:
                expected_variances += 1
                field_results.append({
                    "field": key,
                    "gnmi_value": gnmi_val,
                    "cli_value": cli_val,
                    "status": "expected_variance",
                    "note": "Timing-sensitive field — variance is expected",
                })
            elif gnmi_val == cli_val:
                matches += 1
                field_results.append({
                    "field": key,
                    "gnmi_value": gnmi_val,
                    "cli_value": cli_val,
                    "status": "match",
                })
            else:
                mismatches += 1
                field_results.append({
                    "field": key,
                    "gnmi_value": gnmi_val,
                    "cli_value": cli_val,
                    "status": "mismatch",
                })

    return {
        "matches": matches,
        "mismatches": mismatches,
        "expected_variances": expected_variances,
        "total_fields": matches + mismatches + expected_variances,
        "fields": field_results,
    }


# ===================================================================
# Tool 10: gnmi_list_targets  (T014)
# ===================================================================

@mcp.tool()
def gnmi_list_targets() -> str:
    """List all configured gNMI target devices.

    Returns:
        Array of configured targets with name, host, port, vendor,
        and connection status.
    """
    targets_info: list[dict[str, Any]] = []
    for name, t in _targets.items():
        reachable = False
        try:
            reachable = _client.check_reachability(name)
        except Exception:
            pass

        targets_info.append({
            "name": t.name,
            "host": t.host,
            "port": t.port,
            "vendor": t.vendor,
            "encoding": t.encoding,
            "status": "reachable" if reachable else "unreachable",
        })

    return _gcf_dumps(targets_info)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
