"""Lightweight response shapes for the Claroty MCP server.

These dataclasses project the xDome attributes a NetClaw operator typically
wants. Field names match the **real** xDome schemas (verified against the
OpenAPI ``components.schemas.<Resource>.fields_enum`` entries):

- Devices use ``asset_id``/``uid``, ``local_name``, ``manufacturer``,
  ``ip_list``/``mac_list`` — there is no ``id``, ``name``, or ``vendor``.
- Sites use ``id``/``name``/``devices_count``.
- Alerts use ``alert_name``/``alert_class``/``category``/``status``.
- Vulnerabilities use ``cve_ids`` (list), ``cvss_v3_score``,
  ``affected_devices_count``.

If you need a field that's not modelled here, pass through ``raw`` alongside
the projected dataclass.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class Device:
    """An xDome managed device (OT / IoT / IoMT asset)."""

    asset_id: Optional[str] = None
    uid: Optional[str] = None
    local_name: Optional[str] = None
    ip_list: list[str] = field(default_factory=list)
    mac_list: list[str] = field(default_factory=list)
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    purdue_level: Optional[str] = None
    device_category: Optional[str] = None
    device_type: Optional[str] = None
    criticality: Optional[str] = None
    risk_score: Optional[float] = None
    labels: list[str] = field(default_factory=list)


@dataclass
class Alert:
    """An xDome security alert."""

    id: Optional[Any] = None  # xDome alert IDs are integers
    alert_name: Optional[str] = None
    alert_type_name: Optional[str] = None
    alert_class: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    devices_count: Optional[int] = None
    detected_time: Optional[str] = None
    updated_time: Optional[str] = None


@dataclass
class Vulnerability:
    """An xDome vulnerability finding.

    Note on ``id`` vs ``name``: ``name`` is the human-friendly identifier
    (typically a CVE id like ``"CVE-YYYY-NNNNN"`` or a vendor advisory id
    like ``"cisco-sa-sdwan-rpa2-v69WY2SW"``). ``id`` is xDome's internal
    unique identifier — that's what
    ``/api/v1/vulnerabilities/{vulnerability_id}/devices`` expects in
    the path. Passing ``name`` as the URL path parameter returns 404.
    """

    id: Optional[str] = None
    name: Optional[str] = None
    vulnerability_type: Optional[str] = None
    cve_ids: list[str] = field(default_factory=list)
    cvss_v3_score: Optional[float] = None
    cvss_v3_vector_string: Optional[str] = None
    description: Optional[str] = None
    affected_devices_count: Optional[int] = None
    is_known_exploited: Optional[bool] = None
    published_date: Optional[str] = None


@dataclass
class Site:
    """A Claroty xDome site (physical or logical grouping)."""

    id: Optional[Any] = None
    name: Optional[str] = None
    location: Optional[str] = None
    country_code: Optional[str] = None
    description: Optional[str] = None
    devices_count: Optional[int] = None
    site_group_id: Optional[Any] = None
    site_group_name: Optional[str] = None


@dataclass
class Server:
    """A physical / virtual xDome server / management node."""

    server_name: Optional[str] = None
    server_location: Optional[str] = None
    server_status: Optional[str] = None
    site_id: Optional[Any] = None
    model: Optional[str] = None
    os_version: Optional[str] = None
    serial_number: Optional[str] = None
    num_of_interfaces: Optional[int] = None
    management_ip: Optional[str] = None
    uptime_days: Optional[float] = None


def to_dict(obj: Any) -> dict:
    """Convert a dataclass to a plain dict (GCF-friendly)."""
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return dict(obj) if obj else {}


def _as_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def from_xdome_device(raw: dict) -> Device:
    """Best-effort map an xDome device dict to a Device dataclass."""
    return Device(
        asset_id=raw.get("asset_id"),
        uid=raw.get("uid"),
        local_name=raw.get("local_name"),
        ip_list=_as_list(raw.get("ip_list")),
        mac_list=_as_list(raw.get("mac_list")),
        manufacturer=raw.get("manufacturer"),
        model=raw.get("model"),
        os_name=raw.get("os_name"),
        os_version=raw.get("os_version"),
        purdue_level=str(raw.get("purdue_level")) if raw.get("purdue_level") is not None else None,
        device_category=raw.get("device_category"),
        device_type=raw.get("device_type"),
        criticality=raw.get("criticality"),
        risk_score=raw.get("risk_score"),
        labels=_as_list(raw.get("labels")),
    )


def from_xdome_alert(raw: dict) -> Alert:
    """Best-effort map an xDome alert dict to an Alert dataclass."""
    return Alert(
        id=raw.get("id"),
        alert_name=raw.get("alert_name"),
        alert_type_name=raw.get("alert_type_name"),
        alert_class=raw.get("alert_class"),
        category=raw.get("category"),
        status=raw.get("status"),
        description=raw.get("description"),
        devices_count=raw.get("devices_count"),
        detected_time=raw.get("detected_time"),
        updated_time=raw.get("updated_time"),
    )


def from_xdome_vulnerability(raw: dict) -> Vulnerability:
    """Best-effort map an xDome vulnerability dict to a Vulnerability dataclass.

    Captures ``id`` if xDome returned it (even when ``id`` wasn't in the
    requested fields list — xDome appears to include it implicitly).
    Callers that pass the result to ``get_vulnerable_devices`` MUST use
    ``id``, not ``name``.
    """
    return Vulnerability(
        id=(str(raw["id"]) if raw.get("id") is not None else None),
        name=raw.get("name"),
        vulnerability_type=raw.get("vulnerability_type"),
        cve_ids=_as_list(raw.get("cve_ids")),
        cvss_v3_score=raw.get("cvss_v3_score"),
        cvss_v3_vector_string=raw.get("cvss_v3_vector_string"),
        description=raw.get("description"),
        affected_devices_count=raw.get("affected_devices_count"),
        is_known_exploited=raw.get("is_known_exploited"),
        published_date=raw.get("published_date"),
    )


def from_xdome_site(raw: dict) -> Site:
    """Best-effort map an xDome site dict to a Site dataclass."""
    return Site(
        id=raw.get("id"),
        name=raw.get("name"),
        location=raw.get("location"),
        country_code=raw.get("country_code"),
        description=raw.get("description"),
        devices_count=raw.get("devices_count"),
        site_group_id=raw.get("site_group_id"),
        site_group_name=raw.get("site_group_name"),
    )


def from_xdome_server(raw: dict) -> Server:
    """Best-effort map an xDome server dict to a Server dataclass."""
    return Server(
        server_name=raw.get("server_name"),
        server_location=raw.get("server_location"),
        server_status=raw.get("server_status"),
        site_id=raw.get("site_id"),
        model=raw.get("model"),
        os_version=raw.get("os_version"),
        serial_number=raw.get("serial_number"),
        num_of_interfaces=raw.get("num_of_interfaces"),
        management_ip=raw.get("management_ip"),
        uptime_days=raw.get("uptime_days"),
    )
