"""Bounded, fixed-origin read-only adapter for the pinned Convergence flow API."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import math
import re

import httpx

from settings import MESSAGES, ReadError, Settings, ip

MAX_BYTES = 1024 * 1024
DEADLINE_SECONDS = 20
WINDOWS = {"15m": 900, "1h": 3600, "6h": 21600, "24h": 86400}


def error_result(code: str) -> dict:
    return {"ok": False, "error": {"code": code, "message": MESSAGES[code]}}


def timestamp(value, code="compatibility") -> datetime:
    if not isinstance(value, str) or len(value) > 40 or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})", value
    ):
        raise ReadError(code)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        raise ReadError(code) from None

def interval(start, end, code="compatibility"):
    first, last = timestamp(start, code), timestamp(end, code)
    if not 0 < (last - first).total_seconds() <= 86400:
        raise ReadError(code)
    return first, last


def obj(value):
    if not isinstance(value, dict):
        raise ReadError("compatibility")
    return value

def text(value, maximum=4096):
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ReadError("compatibility")
    return value

def number(value, nullable=False):
    if nullable and value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise ReadError("compatibility")
    return value

def array(value, maximum):
    if not isinstance(value, list) or len(value) > maximum:
        raise ReadError("compatibility")
    return value

def coverage(value):
    value = obj(value)
    if value.get("mode") not in ("demo", "host", "network"):
        raise ReadError("compatibility")
    result = {"mode": value["mode"], "label": text(value.get("label"), 120),
              "description": text(value.get("description"))}
    if "detail" in value:
        result["detail"] = text(value["detail"], 240)
    return result

def counters(value):
    value = obj(value)
    if not all(key in value for key in ("bytes", "packets", "records")):
        raise ReadError("compatibility")
    return {key: number(value[key], nullable=True) for key in ("bytes", "packets", "records")}

def base(value, settings):
    value = obj(value)
    if value.get("site") != settings.site:
        raise ReadError("compatibility")
    return {"site": settings.site, "coverage": coverage(value.get("coverage"))}

def validate_summary(value, settings, requested_range, exporter):
    result = base(value, settings)
    status = value.get("status")
    if status not in ("active", "empty", "not_configured"):
        raise ReadError("compatibility")
    observed = array(value.get("exporters"), 128)
    allowed = {ip(x) for x in settings.exporters}
    if any(ip(x) not in allowed for x in observed):
        raise ReadError("compatibility")
    result.update(status=status, exporters=[ip(x) for x in observed])
    if status == "not_configured":
        if observed:
            raise ReadError("compatibility")
        result["reason"] = "The configured site has no flow source."
        return result
    if not observed or value.get("range") != requested_range:
        raise ReadError("compatibility")
    actual_exporter = value.get("exporter")
    if (actual_exporter is None) != (exporter is None):
        raise ReadError("compatibility")
    if exporter is not None and (ip(actual_exporter) != ip(exporter) or ip(exporter) not in {ip(x) for x in observed}):
        raise ReadError("compatibility")
    first, last = interval(value.get("start"), value.get("end"))
    if (last - first).total_seconds() != WINDOWS[requested_range]:
        raise ReadError("compatibility")
    timestamp(value.get("read_at"))
    result.update(range=requested_range, start=value["start"], end=value["end"],
                  read_at=value["read_at"], exporter=ip(actual_exporter) if actual_exporter else None)
    total = counters(value.get("total"))
    received = value["total"].get("last_received")
    if received is not None and not first <= timestamp(received) <= last:
        raise ReadError("compatibility")
    total["last_received"] = received
    if status == "active" and not total["records"]:
        raise ReadError("compatibility")
    if status == "empty" and total["records"] not in (None, 0):
        raise ReadError("compatibility")
    result["total"] = total
    for key, fields in (("sources", ("src_addr",)), ("destinations", ("dst_addr",)),
                        ("conversations", ("src_addr", "dst_addr"))):
        rows = []
        for row in array(value.get(key), 20):
            record = counters(row)
            for name in fields:
                record[name] = ip(row.get(name))
            rows.append(record)
        result[key] = rows
    result["sampling"] = [{"rate": number(obj(row).get("rate"), nullable=True),
                           "records": number(row.get("records"))}
                          for row in array(value.get("sampling"), 10)]
    result["basis"] = text(value.get("basis"))
    result["limitations"] = [text(line) for line in array(value.get("limitations"), 20)]
    if not result["limitations"]:
        raise ReadError("compatibility")
    return result

def validate_evidence(value, settings, address, start, end, exporter):
    result = base(value, settings)
    if ip(value.get("address")) != ip(address) or value.get("limit") != 100:
        raise ReadError("compatibility")
    first, last = interval(start, end)
    if interval(value.get("start"), value.get("end")) != (first, last):
        raise ReadError("compatibility")
    result.update(address=ip(value["address"]), start=value["start"], end=value["end"], limit=100)
    allowed = {ip(x) for x in settings.exporters}
    records = []
    for row in array(value.get("records"), 100):
        row = obj(row)
        source, destination, sampler = (ip(row.get(name)) for name in ("src_addr", "dst_addr", "sampler_address"))
        when = timestamp(row.get("_time"))
        if (ip(address) not in (source, destination) or sampler not in allowed
                or (exporter is not None and sampler != ip(exporter)) or not first <= when <= last):
            raise ReadError("compatibility")
        record = {"_time": row["_time"], "src_addr": source, "dst_addr": destination, "sampler_address": sampler}
        if "proto" in row:
            protocol = row["proto"]
            # GoFlow2's JSON formatter emits names such as UDP/TCP; other
            # exporters retain the numeric IP protocol identifier.
            if isinstance(protocol, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", protocol):
                record["proto"] = protocol
            else:
                numeric = int(protocol) if isinstance(protocol, str) and protocol.isdecimal() else protocol
                if isinstance(numeric, bool) or not isinstance(numeric, int) or not 0 <= numeric <= 255:
                    raise ReadError("compatibility")
                record["proto"] = numeric
        for key in ("src_port", "dst_port", "bytes", "packets", "sampling_rate", "in_if", "out_if", "src_vlan", "dst_vlan", "vlan_id"):
            if key not in row:
                continue
            numeric = row[key]
            if isinstance(numeric, str):
                if not re.fullmatch(r"\d{1,30}(?:\.\d{1,9})?", numeric):
                    raise ReadError("compatibility")
            else:
                number(numeric)
            record[key] = numeric
        if "bytes" not in record or "packets" not in record:
            raise ReadError("compatibility")
        records.append(record)
    result["records"] = records
    result["basis"] = text(value.get("basis"))
    return result


VM_PATTERNS = ("port_scan", "network_sweep", "protected_network_contact")
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")


def count(value, maximum=None, nullable=False):
    if nullable and value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or (maximum is not None and value > maximum):
        raise ReadError("compatibility")
    return value

def flag(value):
    if not isinstance(value, bool):
        raise ReadError("compatibility")
    return value

def choice(value, allowed):
    if value not in allowed:
        raise ReadError("compatibility")
    return value

def vm_coverage(value):
    value = obj(value)
    result = {key: flag(value.get(key)) for key in ("fresh", "inventory_ok", "packet_capture_ok", "history_limited",
                                                     "metadata_cap_reached", "policy_configured")}
    if value.get("sampled") is not True:
        raise ReadError("compatibility")
    result["sampled"] = True
    for key in ("capture_drops_total", "capture_drops_recent_delta", "events_discarded_total", "events_discarded_recent_delta"):
        result[key] = count(value.get(key), nullable=True)
    for key in ("snapshot_count", "history_count", "missing_uuid_vm_count", "excluded_identity_events",
                "metadata_count", "allowlisted_tuple_count"):
        result[key] = count(value.get(key))
    result["counter_delta_seconds"] = number(value.get("counter_delta_seconds"), nullable=True)
    result["snapshot_span_seconds"] = number(value.get("snapshot_span_seconds"))
    result["max_snapshot_gap_seconds"] = number(value.get("max_snapshot_gap_seconds"), nullable=True)
    result["limitations"] = [text(line, 512) for line in array(value.get("limitations"), 96)]
    return result

def vm_inventory(value, nic_budget):
    vm = obj(value)
    uuid = vm.get("vm_uuid")
    if uuid is not None and not (isinstance(uuid, str) and UUID.fullmatch(uuid)):
        raise ReadError("compatibility")
    vm_id = count(vm.get("vm_id"))
    if not vm_id:
        raise ReadError("compatibility")
    nics = []
    for nic in array(vm.get("nics"), nic_budget):
        nic = obj(nic)
        name, tap = nic.get("name"), nic.get("tap")
        if not (isinstance(name, str) and re.fullmatch(r"net\d{1,3}", name)) or tap != f"tap{vm_id}i{name[3:]}":
            raise ReadError("compatibility")
        index = count(nic.get("ifindex"), nullable=True)
        nics.append({"name": name, "tap": tap, "ifindex": index,
                     "capture_state": choice(nic.get("capture_state"), ("observing", "unsupported", "absent", "error"))})
    if len({nic["name"] for nic in nics}) != len(nics):
        raise ReadError("compatibility")
    return {"vm_id": vm_id, "vm_uuid": uuid,
            "power_state": choice(vm.get("power_state"), ("running", "stopped", "unknown")),
            "capture_state": choice(vm.get("capture_state"), ("observing", "partial", "unavailable", "stopped")),
            "finding_count": count(vm.get("finding_count")), "nics": nics}

def vm_finding(value, vms):
    finding = obj(value)
    if not (isinstance(finding.get("id"), str) and re.fullmatch(r"[0-9a-f]{20}", finding["id"])):
        raise ReadError("compatibility")
    kind = choice(finding.get("kind"), VM_PATTERNS)
    choice(finding.get("severity"), ("review",))
    vm = vms.get((finding.get("vm_id"), finding.get("vm_uuid")))
    first, last = number(finding.get("first_seen")), number(finding.get("last_seen"))
    if vm is None or vm["vm_uuid"] is None or first > last:
        raise ReadError("compatibility")
    evidence = obj(finding.get("evidence"))
    result = {"unique_tcp_five_tuples": count(evidence.get("unique_tcp_five_tuples")),
              "unique_destination_ports": count(evidence.get("unique_destination_ports"), 65536),
              "unique_destination_ips": count(evidence.get("unique_destination_ips")),
              "destination_ip": None if evidence.get("destination_ip") is None else ip(evidence["destination_ip"]),
              "destination_port": count(evidence.get("destination_port"), 65535, nullable=True)}
    if (kind == "port_scan" and result["unique_destination_ports"] < 20) or (
            kind == "network_sweep" and result["unique_destination_ips"] < 20):
        raise ReadError("compatibility")
    taps = {(nic["tap"], nic["ifindex"]) for nic in vm["nics"]}
    examples = []
    for row in array(evidence.get("examples"), 5):
        row = obj(row)
        protocol = choice(row.get("protocol"), ("tcp", "udp", "icmp", "icmpv6"))
        ports = [count(row.get(key), 65535, nullable=True) for key in ("src_port", "dst_port")]
        when = number(row.get("observed_at"))
        if ((None in ports) != (protocol not in ("tcp", "udp")) or (row.get("tap"), row.get("ifindex")) not in taps
                or not first <= when <= last):
            raise ReadError("compatibility")
        examples.append({"src_ip": ip(row.get("src_ip")), "dst_ip": ip(row.get("dst_ip")), "src_port": ports[0],
                         "dst_port": ports[1], "protocol": protocol, "tap": row["tap"], "ifindex": row["ifindex"],
                         "observed_at": when})
    result["examples"] = examples
    return {"id": finding["id"], "kind": kind, "severity": "review", "vm_id": vm["vm_id"], "vm_uuid": vm["vm_uuid"],
            "first_seen": first, "last_seen": last, "caveat": text(finding.get("caveat"), 512), "evidence": result}

def vm_source(value, settings, synthetic):
    source = obj(value)
    if source.get("site", settings.site) != settings.site:
        raise ReadError("compatibility")
    kind = choice(source.get("kind"), ("synthetic",) if synthetic else ("proxmox",))
    budget = 1024
    vms = {}
    for row in array(source.get("vms"), 256):
        vm = vm_inventory(row, budget)
        budget -= len(vm["nics"])
        if vm["vm_id"] in {key[0] for key in vms}:
            raise ReadError("compatibility")
        vms[(vm["vm_id"], vm["vm_uuid"])] = vm
    summary = obj(source.get("summary"))
    summary = {"finding_count": count(summary.get("finding_count")), "affected_vm_count": count(summary.get("affected_vm_count")),
               "findings_truncated": flag(summary.get("findings_truncated")),
               "assessment": choice(summary.get("assessment"), ("review", "no_patterns_observed", "insufficient_evidence"))}
    findings = [vm_finding(row, vms) for row in array(source.get("findings"), 100)]
    if (len({f["id"] for f in findings}) != len(findings) or summary["finding_count"] < len(findings)
            or summary["affected_vm_count"] > len(vms)
            or (not summary["findings_truncated"] and summary["finding_count"] != len(findings))
            or sum(vm["finding_count"] for vm in vms.values()) != summary["finding_count"]):
        raise ReadError("compatibility")
    return {"id": text(source.get("id"), 512), "node": text(source.get("node"), 512), "kind": kind,
            "status": choice(source.get("status"), ("reporting", "stale", "unknown")),
            "last_contact": number(source.get("last_contact"), nullable=True),
            "observed_at": number(source.get("observed_at"), nullable=True),
            "coverage": vm_coverage(source.get("coverage")), "summary": summary,
            "findings": findings, "vms": list(vms.values())}

def validate_vm_security(value, settings):
    """The service's VM Security assessment, without its guest-heartbeat block."""
    value = obj(value)
    status = choice(value.get("status"), ("configured", "not_configured", "unavailable"))
    if status == "unavailable":
        raise ReadError("unavailable")
    sources = array(value.get("sources"), 256)
    if status == "not_configured":
        if sources:
            raise ReadError("compatibility")
        return {"site": settings.site, "status": status, "sources": []}
    if value.get("site") != settings.site or value.get("window_seconds") != 300:
        raise ReadError("compatibility")
    synthetic = flag(value.get("synthetic"))
    projected = [vm_source(row, settings, synthetic) for row in sources]
    if len({s["id"] for s in projected}) != len(projected) or len({s["node"] for s in projected}) != len(projected):
        raise ReadError("compatibility")
    return {"site": settings.site, "status": status, "synthetic": synthetic,
            "generated_at": number(value.get("generated_at")), "window_seconds": 300, "sources": projected}


class ConvergenceClient:
    def __init__(self, settings: Settings, transport=None):
        self.settings = settings
        self.transport = transport

    async def _read(self, path, params):
        async with httpx.AsyncClient(verify=True, follow_redirects=False, trust_env=False,
                                     timeout=DEADLINE_SECONDS, transport=self.transport) as client:
            async with client.stream("GET", self.settings.endpoint + path,
                                     params={"site": self.settings.site, **params},
                                     headers={"Authorization": "Bearer " + self.settings.token,
                                              "Accept": "application/json", "Accept-Encoding": "identity"}) as response:
                if response.status_code in (401, 403):
                    raise ReadError("unauthorized")
                if response.status_code != 200:
                    raise ReadError("unavailable")
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise ReadError("compatibility")
                if response.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
                    raise ReadError("compatibility")
                length = response.headers.get("content-length")
                if length is not None and (not length.isdecimal() or int(length) > MAX_BYTES):
                    raise ReadError("compatibility")
                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    if len(body) + len(chunk) > MAX_BYTES:
                        raise ReadError("compatibility")
                    body.extend(chunk)
                try:
                    return json.loads(body, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                except (ValueError, UnicodeError, RecursionError):
                    raise ReadError("compatibility") from None

    async def _request(self, path, params, validate):
        try:
            value = await asyncio.wait_for(self._read(path, params), timeout=DEADLINE_SECONDS)
            result = validate(value)
            # Projected API text remains untrusted. Never reflect a credential even
            # if an incorrectly configured backend embeds it in an allowed field.
            def sensitive(value):
                if isinstance(value, str):
                    return self.settings.token in value or self.settings.endpoint in value
                if isinstance(value, dict):
                    return any(sensitive(item) for item in value.values())
                if isinstance(value, list):
                    return any(sensitive(item) for item in value)
                return False
            if sensitive(result):
                raise ReadError("compatibility")
            return {"ok": True, "data": result}
        except ReadError as error:
            return error_result(error.code)
        except (asyncio.TimeoutError, httpx.TimeoutException):
            return error_result("timeout")
        except (httpx.HTTPError, OSError):
            return error_result("unavailable")
        except Exception:
            return error_result("compatibility")

    async def summary(self, range="1h", exporter=None):
        try:
            if not isinstance(range, str) or range not in WINDOWS:
                raise ReadError("invalid_argument")
            exporter = self.settings.exporter(exporter)
        except ReadError as error:
            return error_result(error.code)
        params = {"range": range}
        if exporter:
            params["exporter"] = exporter
        return await self._request("/api/flows", params,
            lambda value: validate_summary(value, self.settings, range, exporter))

    async def evidence(self, address, start, end, exporter=None):
        try:
            address = ip(address, "invalid_argument")
            first, last = interval(start, end, "invalid_argument")
            if (last - datetime.now(timezone.utc)).total_seconds() > 60:
                raise ReadError("invalid_argument")
            exporter = self.settings.exporter(exporter)
        except ReadError as error:
            return error_result(error.code)
        params = {"address": address, "start": start, "end": end}
        if exporter:
            params["exporter"] = exporter
        return await self._request("/api/flows/records", params,
            lambda value: validate_evidence(value, self.settings, address, start, end, exporter))

    async def vm_security(self):
        return await self._request("/api/security/vms", {},
            lambda value: validate_vm_security(value, self.settings))
