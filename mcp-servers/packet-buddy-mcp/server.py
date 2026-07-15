#!/usr/bin/env python3
"""Packet Buddy MCP Server — pcap analysis via tshark + AI.

Wraps tshark as MCP tools so NetClaw can analyze packet captures
uploaded via Slack or placed on disk.

Environment variables:
    PCAP_UPLOAD_DIR  — directory for uploaded pcaps (default: /tmp/netclaw-pcaps)
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

from fastmcp import FastMCP

PCAP_DIR = Path(os.environ.get("PCAP_UPLOAD_DIR", "/tmp/netclaw-pcaps"))
PCAP_DIR.mkdir(parents=True, exist_ok=True)

mcp = FastMCP(
    "packet-buddy-mcp",
    instructions=(
        "Packet Buddy MCP — analyze network packet captures (.pcap/.pcapng) "
        "using tshark. Upload a pcap file, then use tools to summarize traffic, "
        "extract conversations, filter by protocol, and inspect individual packets."
    ),
)


def _run_tshark(pcap_path: str, args: list[str], max_lines: int = 500) -> str:
    """Run tshark with given args against a pcap file."""
    if not Path(pcap_path).exists():
        return f"Error: file not found: {pcap_path}"
    cmd = ["tshark", "-nlr", pcap_path] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr:
            output += f"\n[tshark stderr]: {result.stderr.strip()}"
        lines = output.split("\n")
        if len(lines) > max_lines:
            output = "\n".join(lines[:max_lines])
            output += f"\n\n... truncated ({len(lines)} total lines, showing {max_lines})"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: tshark timed out after 60 seconds"
    except FileNotFoundError:
        return "Error: tshark not installed. Install with: apt install tshark"


@mcp.tool()
async def list_pcaps() -> str:
    """List all pcap files available for analysis."""
    pcaps = sorted(PCAP_DIR.glob("*.pcap*"))
    pcaps += sorted(PCAP_DIR.glob("*.cap"))
    if not pcaps:
        return f"No pcap files found in {PCAP_DIR}. Upload a .pcap file first."
    lines = [f"Pcap files in {PCAP_DIR}:"]
    for p in pcaps:
        size = p.stat().st_size
        if size > 1_000_000:
            size_str = f"{size / 1_000_000:.1f} MB"
        else:
            size_str = f"{size / 1_000:.1f} KB"
        lines.append(f"  {p.name}  ({size_str})")
    return "\n".join(lines)


@mcp.tool()
async def pcap_summary(pcap_file: str) -> str:
    """Get a high-level summary of a pcap file: packet count, duration, protocols.

    Args:
        pcap_file: filename (looked up in PCAP_UPLOAD_DIR) or absolute path
    """
    pcap_path = _resolve_pcap(pcap_file)

    capinfos = subprocess.run(
        ["capinfos", pcap_path], capture_output=True, text=True, timeout=30
    )
    if capinfos.returncode == 0:
        return capinfos.stdout.strip()

    return _run_tshark(pcap_path, ["-qz", "io,stat,0"])


@mcp.tool()
async def pcap_protocol_hierarchy(pcap_file: str) -> str:
    """Show the protocol hierarchy (breakdown by protocol) in a pcap.

    Args:
        pcap_file: filename or absolute path to pcap
    """
    pcap_path = _resolve_pcap(pcap_file)
    return _run_tshark(pcap_path, ["-qz", "io,phs"])


@mcp.tool()
async def pcap_conversations(pcap_file: str, layer: str = "ip") -> str:
    """Show network conversations (who talked to whom).

    Args:
        pcap_file: filename or absolute path to pcap
        layer: conversation layer — ip, tcp, udp, or eth (default: ip)
    """
    pcap_path = _resolve_pcap(pcap_file)
    valid_layers = ["eth", "ip", "ipv6", "tcp", "udp"]
    if layer not in valid_layers:
        return f"Invalid layer '{layer}'. Use one of: {', '.join(valid_layers)}"
    return _run_tshark(pcap_path, ["-qz", f"conv,{layer}"])


@mcp.tool()
async def pcap_endpoints(pcap_file: str, layer: str = "ip") -> str:
    """Show top endpoints by traffic volume.

    Args:
        pcap_file: filename or absolute path to pcap
        layer: endpoint layer — ip, tcp, udp, or eth (default: ip)
    """
    pcap_path = _resolve_pcap(pcap_file)
    valid_layers = ["eth", "ip", "ipv6", "tcp", "udp"]
    if layer not in valid_layers:
        return f"Invalid layer '{layer}'. Use one of: {', '.join(valid_layers)}"
    return _run_tshark(pcap_path, ["-qz", f"endpoints,{layer}"])


@mcp.tool()
async def pcap_filter(
    pcap_file: str, display_filter: str, max_packets: int = 100
) -> str:
    """Filter packets using a Wireshark display filter expression.

    Args:
        pcap_file: filename or absolute path to pcap
        display_filter: Wireshark display filter (e.g. "tcp.port==80", "dns", "icmp")
        max_packets: max packets to return (default 100)
    """
    pcap_path = _resolve_pcap(pcap_file)
    return _run_tshark(
        pcap_path, ["-Y", display_filter, "-c", str(max_packets)]
    )


@mcp.tool()
async def pcap_packet_detail(
    pcap_file: str, packet_number: int
) -> str:
    """Show full decode of a specific packet by number.

    Args:
        pcap_file: filename or absolute path to pcap
        packet_number: 1-based packet number to inspect
    """
    pcap_path = _resolve_pcap(pcap_file)
    # Jump to the specific frame
    return _run_tshark(
        pcap_path,
        ["-Y", f"frame.number=={packet_number}", "-V", "-c", "1"],
    )


@mcp.tool()
async def pcap_dns_queries(pcap_file: str) -> str:
    """Extract all DNS queries and responses from a pcap.

    Args:
        pcap_file: filename or absolute path to pcap
    """
    pcap_path = _resolve_pcap(pcap_file)
    return _run_tshark(
        pcap_path,
        ["-Y", "dns", "-T", "fields",
         "-e", "frame.number",
         "-e", "ip.src", "-e", "ip.dst",
         "-e", "dns.qry.name", "-e", "dns.resp.addr",
         "-E", "header=y", "-E", "separator=\t"],
    )


@mcp.tool()
async def pcap_http_requests(pcap_file: str) -> str:
    """Extract HTTP request methods, URIs, and hosts from a pcap.

    Args:
        pcap_file: filename or absolute path to pcap
    """
    pcap_path = _resolve_pcap(pcap_file)
    return _run_tshark(
        pcap_path,
        ["-Y", "http.request", "-T", "fields",
         "-e", "frame.number",
         "-e", "ip.src", "-e", "ip.dst",
         "-e", "http.request.method",
         "-e", "http.host",
         "-e", "http.request.uri",
         "-E", "header=y", "-E", "separator=\t"],
    )


@mcp.tool()
async def pcap_to_json(
    pcap_file: str, display_filter: str = "", max_packets: int = 20
) -> str:
    """Export packets as JSON (full protocol decode) for detailed AI analysis.

    Args:
        pcap_file: filename or absolute path to pcap
        display_filter: optional Wireshark display filter
        max_packets: max packets to export (default 20, keep small for context)
    """
    pcap_path = _resolve_pcap(pcap_file)
    args = ["-T", "json", "-c", str(max_packets)]
    if display_filter:
        args = ["-Y", display_filter] + args
    return _run_tshark(pcap_path, args, max_lines=2000)


@mcp.tool()
async def pcap_expert_info(pcap_file: str) -> str:
    """Show tshark expert info — warnings, errors, notes about the capture.

    Args:
        pcap_file: filename or absolute path to pcap
    """
    pcap_path = _resolve_pcap(pcap_file)
    return _run_tshark(pcap_path, ["-qz", "expert"])


@mcp.tool()
async def save_pcap_from_base64(filename: str, base64_data: str) -> str:
    """Save a base64-encoded pcap file to the analysis directory.

    Use this when a user uploads a pcap via Slack — the file content
    arrives as base64. This decodes and saves it for analysis.

    Args:
        filename: name for the saved file (e.g. "capture.pcap")
        base64_data: base64-encoded pcap file content
    """
    import base64

    if not filename.endswith((".pcap", ".pcapng", ".cap")):
        filename += ".pcap"
    dest = PCAP_DIR / filename
    try:
        raw = base64.b64decode(base64_data)
        dest.write_bytes(raw)
        return f"Saved {len(raw)} bytes to {dest}"
    except Exception as e:
        return f"Error saving pcap: {e}"


def _resolve_pcap(pcap_file: str) -> str:
    """Resolve a pcap filename to an absolute path."""
    p = Path(pcap_file)
    if p.is_absolute() and p.exists():
        return str(p)
    candidate = PCAP_DIR / p.name
    if candidate.exists():
        return str(candidate)
    return str(PCAP_DIR / pcap_file)


if __name__ == "__main__":
    mcp.run(transport="stdio")
