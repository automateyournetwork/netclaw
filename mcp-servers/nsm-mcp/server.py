#!/usr/bin/env python3
"""nsm-mcp — offline network-security-monitoring analysis for NetClaw (read-only).

Runs **Zeek** (session and protocol metadata) and **Suricata** (signature alerting) over a
packet capture that already exists on disk. Nothing here sniffs a live interface, and nothing
here writes to a network device: the input is a .pcap/.pcapng file and the output is analysis.

Roadmap R13, spec 091. Complements the existing `packet-buddy-mcp` (tshark, 12 tools), which
decodes individual packets; Zeek answers "what sessions happened" and Suricata answers "did
any of it match a known-bad signature". Arkime is deliberately out of scope -- it requires a
mandatory OpenSearch/Elasticsearch cluster and ~12-16 GB, which is a platform, not a tool.

Every response is built by `envelope.emit()`, which refuses to return an alert verdict
without Suricata's signature count and refuses to return Zeek findings without the checksum
posture. Both refusals exist because both failure modes were reproduced live:

    Suricata, stock config:  0 signatures processed -> 0 alerts, two non-fatal warnings
    Zeek, default checksums: no http.log at all, and conn.log wrong (3 rows vs 2)

In both cases the tool exits 0 and looks like it worked. See envelope.py.
"""

from __future__ import annotations

import os
import sys

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from envelope import PostureError, emit, suricata_posture, zeek_posture  # noqa: E402
import runner  # noqa: E402

mcp = FastMCP("nsm-mcp")

# Analyses are cached per (pcap, mode) so a session pivot does not re-run Zeek on every
# question. Keyed by absolute path + mtime so an edited capture is never served stale.
_zeek_cache: dict[tuple, tuple[str, bool, str]] = {}
_suri_cache: dict[tuple, tuple[str, int, bool, str]] = {}


def _preflight() -> str | None:
    if not runner.docker_available():
        return ("docker is not available or its daemon is not reachable. Zeek and Suricata run "
                "from pinned containers here because zeek has no apt candidate on this "
                "platform and suricata needs root to install.")
    return None


def _zeek(pcap: str, ignore_checksums: bool):
    key = (pcap, os.path.getmtime(pcap), ignore_checksums)
    if key not in _zeek_cache:
        _zeek_cache[key] = runner.run_zeek(pcap, ignore_checksums)
    out, invalid, _ = _zeek_cache[key]
    return out, invalid, zeek_posture(not ignore_checksums, invalid)


def _suricata(pcap: str):
    key = (pcap, os.path.getmtime(pcap))
    if key not in _suri_cache:
        _suri_cache[key] = runner.run_suricata(pcap)
    out, sigs, no_rules, _ = _suri_cache[key]
    present, age = runner.ruleset_state()
    return out, sigs, suricata_posture(sigs, present and not no_rules, age)


@mcp.tool()
def nsm_status() -> dict:
    """Report whether NSM analysis is possible here, and whether Suricata can actually alert.

    Call this first. It answers three questions a caller cannot otherwise distinguish from an
    empty result: is docker reachable, is a Suricata ruleset present, and how old is it.
    """
    err = _preflight()
    present, age = runner.ruleset_state()
    data = {
        "docker_available": runner.docker_available(),
        "zeek": {"image": runner.ZEEK_IMAGE, "version": runner.ZEEK_VERSION},
        "suricata": {"image": runner.SURICATA_IMAGE, "version": runner.SURICATA_VERSION},
        "ruleset_present": present,
        "ruleset_age_days": age,
        "nsm_home": runner.NSM_HOME,
    }
    gaps = []
    if not present:
        gaps.append("No Suricata ruleset. Suricata would load 0 signatures and report 0 "
                    "alerts regardless of what the traffic contains. Run nsm_update_rules.")
    elif age is not None and age > 7:
        gaps.append(f"Suricata ruleset is {age} days old; recent signatures are missing.")
    return emit("nsm_status", data=data, gaps=gaps or None, error=err)


@mcp.tool()
def nsm_update_rules() -> dict:
    """Fetch the Emerging Threats Open ruleset so Suricata can alert. Requires network access.

    Without this, Suricata is inert: measured at 0 signatures and 0 alerts on stock config
    versus 52,205 signatures after an update.
    """
    err = _preflight()
    if err:
        return emit("nsm_update_rules", error=err)
    try:
        return emit("nsm_update_rules", data=runner.update_rules())
    except runner.NsmError as exc:
        return emit("nsm_update_rules", error=str(exc))


@mcp.tool()
def nsm_analyze(pcap: str, ignore_checksums: bool = True) -> dict:
    """Analyse a capture with both Zeek and Suricata and summarise what each could see.

    `ignore_checksums` defaults to True, the opposite of Zeek's own default, because Zeek
    otherwise DISCARDS packets whose TCP checksum is invalid -- which is normal for captures
    taken from a NIC with checksum offloading, including NetClaw's own capture skills. Set it
    to False only when you specifically want Zeek's stock validating behaviour.
    """
    err = _preflight()
    if err:
        return emit("nsm_analyze", pcap=pcap, error=err)
    try:
        path = runner.resolve_pcap(pcap)
        zout, _, zp = _zeek(path, ignore_checksums)
        sout, sigs, sp = _suricata(path)
        _, counts, _ = runner.read_eve(sout)
        alerts, _, alert_total = runner.read_eve(sout, "alert", limit=25)
        logs = runner.zeek_logs(zout)
        conn_rows = 0
        if "conn" in logs:
            _, conn_rows = runner.read_zeek_log(zout, "conn", limit=0)
        return emit(
            "nsm_analyze", pcap=path,
            zeek=zp, suricata=sp,
            zeek_findings={"logs_produced": logs, "connections": conn_rows},
            alert_verdict=alert_total,
            data={"suricata_event_counts": counts,
                  "alert_sample": [
                      {"signature": a.get("alert", {}).get("signature"),
                       "category": a.get("alert", {}).get("category"),
                       "severity": a.get("alert", {}).get("severity"),
                       "src_ip": a.get("src_ip"), "dest_ip": a.get("dest_ip")}
                      for a in alerts],
                  "zeek_output_dir": zout, "suricata_output_dir": sout},
        )
    except (runner.NsmError, PostureError) as exc:
        return emit("nsm_analyze", pcap=pcap, error=str(exc))


@mcp.tool()
def nsm_sessions(pcap: str, ignore_checksums: bool = True, limit: int = 100,
                 service: str | None = None) -> dict:
    """List the sessions Zeek reconstructed from a capture (its conn.log).

    This is the session-pivot entry point: every Zeek log shares a `uid` with conn.log, so a
    connection found here can be followed into dns, http, ssl and the rest via
    nsm_protocol_log. Optionally filter by Zeek's `service` field (dns, http, ssl…).
    """
    err = _preflight()
    if err:
        return emit("nsm_sessions", pcap=pcap, error=err)
    try:
        path = runner.resolve_pcap(pcap)
        zout, _, zp = _zeek(path, ignore_checksums)
        rows, total = runner.read_zeek_log(zout, "conn", limit=max(limit, 1))
        if service:
            rows = [r for r in rows if r.get("service") == service]
        keep = ("uid", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p",
                "proto", "service", "duration", "orig_bytes", "resp_bytes", "conn_state")
        return emit(
            "nsm_sessions", pcap=path, zeek=zp,
            zeek_findings=[{k: r.get(k) for k in keep if k in r} for r in rows],
            data={"total_connections": total, "returned": len(rows),
                  "truncated": total > len(rows),
                  "available_logs": runner.zeek_logs(zout),
                  "zeek_output_dir": zout},
        )
    except (runner.NsmError, PostureError) as exc:
        return emit("nsm_sessions", pcap=pcap, error=str(exc))


@mcp.tool()
def nsm_protocol_log(pcap: str, log: str, ignore_checksums: bool = True,
                     limit: int = 100, uid: str | None = None) -> dict:
    """Read one Zeek protocol log (dns, http, ssl, weird, notice…) from a capture.

    Pass `uid` to follow a specific connection from nsm_sessions. Call nsm_sessions first if
    you do not know which logs this capture produced -- asking for a log Zeek did not write
    returns the list of ones it did, rather than an empty result that reads as 'no such
    traffic'.
    """
    err = _preflight()
    if err:
        return emit("nsm_protocol_log", pcap=pcap, error=err)
    try:
        path = runner.resolve_pcap(pcap)
        zout, _, zp = _zeek(path, ignore_checksums)
        rows, total = runner.read_zeek_log(zout, log, limit=max(limit, 1))
        if uid:
            rows = [r for r in rows if r.get("uid") == uid]
        return emit(
            "nsm_protocol_log", pcap=path, zeek=zp, zeek_findings=rows,
            data={"log": log, "total_rows": total, "returned": len(rows),
                  "truncated": total > len(rows),
                  "available_logs": runner.zeek_logs(zout)},
        )
    except (runner.NsmError, PostureError) as exc:
        return emit("nsm_protocol_log", pcap=pcap, error=str(exc))


@mcp.tool()
def nsm_alerts(pcap: str, limit: int = 100, min_severity: int | None = None) -> dict:
    """List Suricata's signature alerts for a capture, with its detection posture attached.

    The posture is not decoration. If Suricata loaded 0 signatures, an empty alert list means
    the detector was off, and this tool will say so inline rather than let '0 alerts' be read
    as 'clean traffic'.
    """
    err = _preflight()
    if err:
        return emit("nsm_alerts", pcap=pcap, error=err)
    try:
        path = runner.resolve_pcap(pcap)
        sout, sigs, sp = _suricata(path)
        events, counts, total = runner.read_eve(sout, "alert", limit=max(limit, 1))
        out = []
        for a in events:
            al = a.get("alert", {})
            if min_severity is not None and (al.get("severity") or 99) > min_severity:
                continue
            out.append({"timestamp": a.get("timestamp"),
                        "signature": al.get("signature"), "signature_id": al.get("signature_id"),
                        "category": al.get("category"), "severity": al.get("severity"),
                        "src_ip": a.get("src_ip"), "src_port": a.get("src_port"),
                        "dest_ip": a.get("dest_ip"), "dest_port": a.get("dest_port"),
                        "proto": a.get("proto")})
        return emit(
            "nsm_alerts", pcap=path, suricata=sp, alert_verdict=out,
            data={"total_alerts": total, "returned": len(out),
                  "truncated": total > len(out),
                  "event_counts": counts, "suricata_output_dir": sout},
        )
    except (runner.NsmError, PostureError) as exc:
        return emit("nsm_alerts", pcap=pcap, error=str(exc))


if __name__ == "__main__":
    mcp.run(transport="stdio")
