#!/usr/bin/env python3
"""Fast live health diagnostics for the EVE-NG MCP server.

This is intentionally separate from the static smoke test. It exercises each
major MCP capability against a real EVE-NG API endpoint and reports PASS/WARN/
FAIL per capability.

Default mode is read-only. Add --mutating to run reversible operational checks
(start/stop VPCS nodes and startup-config set/wipe on a stopped IOS/IOL node).

Target profiles:
  local is the default and forces EVE_URL=http://127.0.0.1 unless EVE_LOCAL_URL is set.
  external uses EVE_EXTERNAL_URL, defaulting to http://192.168.100.231.

Examples:
  python3 test_eve_live_health.py                       # local read-only
  python3 test_eve_live_health.py --mutating            # local mutating
  python3 test_eve_live_health.py --target external     # external read-only

Environment overrides:
  EVE_HEALTH_TARGET=local|external
  EVE_LOCAL_URL=http://127.0.0.1
  EVE_LOCAL_CONSOLE_HOST=127.0.0.1
  EVE_EXTERNAL_URL=http://192.168.100.231
  EVE_EXTERNAL_CONSOLE_HOST=192.168.100.231
  EVE_HEALTH_SAFE_LAB=/8-mcp-link-test.unl
  EVE_HEALTH_CONFIG_LAB=/2-square-eigrp.unl
  EVE_HEALTH_CONFIG_NODE=R1
  EVE_HEALTH_CONSOLE_NODE=N1
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Callable

SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_DIR))


def _preparse_target() -> str:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--target", choices=("local", "external", "both"), default=os.getenv("EVE_HEALTH_TARGET", "local"))
    args, _ = parser.parse_known_args()
    return args.target


def _apply_target_profile(target: str) -> None:
    # Force local by default, even if the shell has stale EVE_URL=.231.
    if target == "external":
        os.environ["EVE_URL"] = os.getenv("EVE_EXTERNAL_URL", "http://192.168.100.231")
        os.environ["EVE_CONSOLE_HOST"] = os.getenv("EVE_EXTERNAL_CONSOLE_HOST", "192.168.100.231")
        for key in ("EVE_USER", "EVE_PASSWORD"):
            value = os.getenv(f"EVE_EXTERNAL_{key.removeprefix('EVE_')}")
            if value:
                os.environ[key] = value
    else:
        os.environ["EVE_URL"] = os.getenv("EVE_LOCAL_URL", "http://127.0.0.1")
        os.environ["EVE_CONSOLE_HOST"] = os.getenv("EVE_LOCAL_CONSOLE_HOST", "127.0.0.1")
        for key in ("EVE_USER", "EVE_PASSWORD"):
            value = os.getenv(f"EVE_LOCAL_{key.removeprefix('EVE_')}")
            if value:
                os.environ[key] = value
    os.environ.setdefault("EVE_CACHE_TTL", "0")


TARGET = _preparse_target()
_apply_target_profile(TARGET)

import tools_config  # noqa: E402
import tools_console_exec  # noqa: E402
import tools_lab  # noqa: E402
import tools_network  # noqa: E402
import tools_node  # noqa: E402
from eve_client import get_client, handle_eve_response, normalize_lab_path, resolve_node_id, node_is_running, correct_local_nodes_status  # noqa: E402


SAFE_LAB = os.getenv("EVE_HEALTH_SAFE_LAB", "/8-mcp-link-test.unl")
CONFIG_LAB = os.getenv("EVE_HEALTH_CONFIG_LAB", "/2-square-eigrp.unl")
CONFIG_NODE = os.getenv("EVE_HEALTH_CONFIG_NODE", "R1")
CONSOLE_NODE = os.getenv("EVE_HEALTH_CONSOLE_NODE", "N1")


@dataclass
class Result:
    capability: str
    status: str
    duration_ms: int
    detail: str


def ok(output: str) -> bool:
    return "success: true" in output


def compact(output: str, max_len: int = 180) -> str:
    text = " ".join(line.strip() for line in output.splitlines() if line.strip())
    return text[:max_len] + ("..." if len(text) > max_len else "")


def run_case(name: str, fn: Callable[[], str]) -> Result:
    start = time.monotonic()
    try:
        detail = fn()
        status = "PASS"
    except AssertionError as exc:
        detail = str(exc)
        status = "FAIL"
    except Exception as exc:  # live diagnostics should report all failures, not stop at first
        detail = f"{type(exc).__name__}: {exc}"
        status = "FAIL"
    duration_ms = int((time.monotonic() - start) * 1000)
    return Result(name, status, duration_ms, detail)


def require_success(name: str, output: str) -> str:
    if not ok(output):
        raise AssertionError(f"{name} did not return success: {compact(output)}")
    return compact(output)


def case_system_status() -> str:
    return require_success("eve_status", tools_lab.eve_status())


def case_system_auth() -> str:
    return require_success("eve_auth", tools_lab.eve_auth())


def case_images() -> str:
    all_images = tools_lab.eve_list_images(page=1, page_size=3)
    iol_images = tools_lab.eve_list_images("iol", page=1, page_size=3)
    qemu_images = tools_lab.eve_list_images("qemu", page=1, page_size=3)
    for name, output in [("all images", all_images), ("iol images", iol_images), ("qemu images", qemu_images)]:
        require_success(name, output)
    return "image listing OK for all/iol/qemu"


def case_lab_lifecycle_read() -> str:
    labs = tools_lab.eve_list_labs("/", page=1, page_size=10)
    require_success("eve_list_labs", labs)
    lab = tools_lab.eve_get_lab(SAFE_LAB)
    require_success("eve_get_lab", lab)
    return f"lab list/get OK using {SAFE_LAB}"


def case_node_read() -> str:
    nodes = tools_node.eve_list_nodes(SAFE_LAB, page=1, page_size=10)
    require_success("eve_list_nodes", nodes)
    node = tools_node.eve_get_node(SAFE_LAB, CONSOLE_NODE)
    require_success("eve_get_node", node)
    return f"node list/get OK using {SAFE_LAB}:{CONSOLE_NODE}"


def case_network_topology() -> str:
    topo = tools_network.eve_get_topology(SAFE_LAB)
    require_success("eve_get_topology", topo)
    nets = tools_network.eve_list_networks(SAFE_LAB, page=1, page_size=10)
    require_success("eve_list_networks", nets)
    ifaces = tools_network.eve_list_node_interfaces(SAFE_LAB, CONSOLE_NODE)
    require_success("eve_list_node_interfaces", ifaces)
    types = tools_network.eve_list_node_types()
    require_success("eve_list_node_types", types)
    return f"topology/network/interface/type reads OK using {SAFE_LAB}"


def case_config_read() -> str:
    summary = tools_config.eve_list_config_summaries(CONFIG_LAB, page=1, page_size=10)
    require_success("eve_list_config_summaries", summary)
    cfg = tools_config.eve_get_node_config(CONFIG_LAB, CONFIG_NODE)
    require_success("eve_get_node_config", cfg)
    return f"config summary/get OK using {CONFIG_LAB}:{CONFIG_NODE}"


def case_console_discover() -> str:
    discover = tools_console_exec.eve_discover_node(SAFE_LAB, CONSOLE_NODE)
    require_success("eve_discover_node", discover)
    return f"console discover OK using {SAFE_LAB}:{CONSOLE_NODE}"


def case_lab_export() -> str:
    export = tools_lab.eve_export_lab(SAFE_LAB)
    require_success("eve_export_lab", export)
    return f"lab export OK using {SAFE_LAB}"



def case_runtime_status_scope() -> str:
    """Regression: EVE API can leak status across labs that reuse node IDs.

    The MCP layer should correct local status by lab UUID runtime directory, so a
    lab without its own runtime processes must not show UP only because another
    lab has the same numeric node IDs running.
    """
    if not os.environ.get("EVE_URL", "").startswith(("http://127.0.0.1", "http://localhost")):
        return "runtime scope check skipped for non-local target"
    labs: list[tuple[str, str, set[str]]] = []
    root_dir = Path("/opt/unetlab/labs")
    if not root_dir.exists():
        return "runtime scope check skipped; local lab directory not present"
    for lab_file in root_dir.rglob("*.unl"):
        try:
            root = ET.parse(lab_file).getroot()
        except Exception:
            continue
        node_ids = {node.get("id") for node in root.findall(".//node") if node.get("id")}
        if node_ids:
            labs.append(("/" + str(lab_file.relative_to(root_dir)), root.get("id") or "", node_ids))
    client = get_client()
    checked = 0
    for i, (lab_a, uuid_a, ids_a) in enumerate(labs):
        for lab_b, uuid_b, ids_b in labs[i + 1:]:
            overlap = ids_a & ids_b
            if not overlap or not uuid_a or not uuid_b:
                continue
            for lab_path, uuid in ((lab_a, uuid_a), (lab_b, uuid_b)):
                runtime_dir = Path("/opt/unetlab/tmp/0") / uuid
                if runtime_dir.exists():
                    continue
                raw = handle_eve_response(client.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes", no_cache=True))
                if not isinstance(raw, dict):
                    continue
                corrected = correct_local_nodes_status(client, lab_path, raw)
                leaking = [nid for nid in overlap if isinstance(raw.get(str(nid)), dict) and node_is_running(raw[str(nid)])]
                still_up = [nid for nid in overlap if isinstance(corrected.get(str(nid)), dict) and node_is_running(corrected[str(nid)])]
                checked += 1
                if still_up:
                    raise AssertionError(f"status leak not corrected for {lab_path}: node IDs {still_up} still running")
                if leaking:
                    return f"corrected leaked raw EVE status for {lab_path}: node IDs {sorted(leaking)}"
    return f"runtime scope OK; checked {checked} duplicate-ID stopped lab candidates"

def ensure_stopped(lab_path: str, node: str) -> None:
    output = tools_node.eve_stop_node(lab_path, node)
    require_success("eve_stop_node", output)


def case_node_start_stop() -> str:
    start = tools_node.eve_start_lab(SAFE_LAB)
    require_success("eve_start_lab", start)
    stop = tools_node.eve_stop_lab(SAFE_LAB)
    require_success("eve_stop_lab", stop)
    return f"start/stop lab OK using {SAFE_LAB}"


def case_config_set_wipe() -> str:
    client = get_client()
    node_id = resolve_node_id(client, CONFIG_LAB, CONFIG_NODE)
    nodes_before = handle_eve_response(client.get(f"/api/labs{normalize_lab_path(CONFIG_LAB)}/nodes", no_cache=True)) or {}
    node_before = nodes_before.get(str(node_id), {}) if isinstance(nodes_before, dict) else {}
    if node_is_running(node_before):
        ensure_stopped(CONFIG_LAB, CONFIG_NODE)
    original = tools_config.eve_get_node_config(CONFIG_LAB, CONFIG_NODE)
    # This diagnostic intentionally leaves the node in zero-config mode after validating set/wipe.
    set_output = tools_config.eve_set_node_config(CONFIG_LAB, CONFIG_NODE, "hostname HealthDiag\nno ip domain lookup\nend\n")
    require_success("eve_set_node_config", set_output)
    get_output = tools_config.eve_get_node_config(CONFIG_LAB, CONFIG_NODE)
    require_success("eve_get_node_config after set", get_output)
    if "HealthDiag" not in get_output:
        raise AssertionError("set config succeeded but expected hostname marker was not readable")
    wipe_output = tools_config.eve_wipe_node_config(CONFIG_LAB, CONFIG_NODE)
    require_success("eve_wipe_node_config", wipe_output)
    return f"config set/get/wipe OK using {CONFIG_LAB}:{CONFIG_NODE}; original was {compact(original, 80)}"


def case_console_vpcs_exec() -> str:
    start = tools_node.eve_start_node(SAFE_LAB, CONSOLE_NODE)
    require_success("eve_start_node", start)
    try:
        exec_output = tools_console_exec.eve_exec_vpcs(SAFE_LAB, CONSOLE_NODE, ["show ip"], command_timeout=5, prompt_timeout=8)
        require_success("eve_exec_vpcs", exec_output)
    finally:
        stop = tools_node.eve_stop_node(SAFE_LAB, CONSOLE_NODE)
        require_success("eve_stop_node", stop)
    return f"VPCS console exec OK using {SAFE_LAB}:{CONSOLE_NODE}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fast live EVE-NG MCP operation health diagnostics")
    parser.add_argument("--target", choices=("local", "external", "both"), default=TARGET, help="EVE profile to test (default: local)")
    parser.add_argument("--mutating", action="store_true", help="run reversible start/stop and config set/wipe checks")
    parser.add_argument("--fail-fast", action="store_true", help="stop after the first failed capability")
    args = parser.parse_args()

    if args.target == "both":
        script = Path(__file__).resolve()
        base_cmd = [sys.executable, str(script)]
        if args.mutating:
            base_cmd.append("--mutating")
        if args.fail_fast:
            base_cmd.append("--fail-fast")
        overall = 0
        for target in ("local", "external"):
            print(f"\n=== {target.upper()} EVE HEALTH ===")
            result = subprocess.run(base_cmd + ["--target", target], text=True)
            overall = overall or result.returncode
            if args.fail_fast and result.returncode != 0:
                break
        return overall

    read_only_cases: list[tuple[str, Callable[[], str]]] = [
        ("system.status", case_system_status),
        ("system.auth", case_system_auth),
        ("system.images", case_images),
        ("lab.read", case_lab_lifecycle_read),
        ("node.read", case_node_read),
        ("node.runtime_scope", case_runtime_status_scope),
        ("network.topology", case_network_topology),
        ("config.read", case_config_read),
        ("console.discover", case_console_discover),
        ("lab.export", case_lab_export),
    ]
    mutating_cases: list[tuple[str, Callable[[], str]]] = [
        ("node.start_stop", case_node_start_stop),
        ("config.set_wipe", case_config_set_wipe),
        ("console.vpcs_exec", case_console_vpcs_exec),
    ]

    print(f"TARGET: {args.target} url={os.environ.get('EVE_URL')} console={os.environ.get('EVE_CONSOLE_HOST')}")
    cases = read_only_cases + (mutating_cases if args.mutating else [])
    results: list[Result] = []
    for name, fn in cases:
        result = run_case(name, fn)
        results.append(result)
        print(f"{result.status:4} {result.capability:18} {result.duration_ms:5}ms  {result.detail}")
        if args.fail_fast and result.status == "FAIL":
            break

    if not args.mutating:
        print("WARN mutating checks skipped; rerun with --mutating for start/stop/config/console execution diagnostics")

    failed = [r for r in results if r.status == "FAIL"]
    print(f"SUMMARY: {len(results) - len(failed)}/{len(results)} capabilities passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
