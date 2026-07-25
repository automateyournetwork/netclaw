#!/usr/bin/env python3
"""NetClaw Alert Receiver — accepts Alertmanager webhooks, enriches with SoT, triggers investigation.

Usage:
    python server.py                     # Uses .env for config
    uvicorn server:app --host 0.0.0.0 --port 8099  # Direct uvicorn

Alertmanager webhook config (on OBS VM):
    receivers:
      - name: netclaw
        webhook_configs:
          - url: http://192.168.3.252:8099/webhook
            send_resolved: true
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

load_dotenv(Path(__file__).parent / ".env")

HOST = os.getenv("ALERT_RECEIVER_HOST", "0.0.0.0")
PORT = int(os.getenv("ALERT_RECEIVER_PORT", "8099"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

NAUTOBOT_URL = os.getenv("NAUTOBOT_URL", "").rstrip("/")
NAUTOBOT_TOKEN = os.getenv("NAUTOBOT_TOKEN", "")

OPENCLAW_GATEWAY_URL = os.getenv("OPENCLAW_GATEWAY_URL", "").rstrip("/")
OPENCLAW_HOOK_TOKEN = os.getenv("OPENCLAW_HOOK_TOKEN", "")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
# Discord channel the agent posts its triage FINDINGS to (via the native
# `openclaw message send` bridge). Distinct from DISCORD_WEBHOOK_URL, which is
# the receiver's immediate "alert received" notice.
DISCORD_ALERT_CHANNEL_ID = os.getenv("DISCORD_ALERT_CHANNEL_ID", "")

# Alerts to suppress from the Discord webhook (known noise, not worth human attention).
# Comma-separated alert names. These still trigger investigation if the gateway is
# configured — they just don't post the "alert received" notice to Discord.
DISCORD_SUPPRESS_ALERTS = set(
    a.strip() for a in os.getenv("DISCORD_SUPPRESS_ALERTS", "").split(",") if a.strip()
)

# Network Guardian dashboard — curated event diary for investigation outcomes.
# When configured, the receiver POSTs events to the Guardian API so customers
# and operators see investigation results in the dashboard.
NETWORK_GUARDIAN_URL = os.getenv("NETWORK_GUARDIAN_URL", "").rstrip("/")
NETWORK_GUARDIAN_TOKEN = os.getenv("NETWORK_GUARDIAN_TOKEN", "")
# Home pilot only has site id "home" in Guardian Postgres. Nautobot location
# names (e.g. "House") and unresolved devices ("unknown") must map here or
# POST fails with FK 500s.
GUARDIAN_DEFAULT_SITE = os.getenv("GUARDIAN_DEFAULT_SITE", "home").strip() or "home"
# Comma-separated aliases that normalize to GUARDIAN_DEFAULT_SITE.
_GUARDIAN_SITE_ALIASES = {
    a.strip().casefold()
    for a in os.getenv(
        "GUARDIAN_SITE_ALIASES",
        "house,home,unknown,unresolved,,none,null",
    ).split(",")
}

# Stage 7 — prior-case RAG search injected into investigation prompts.
# Opt-out with RAG_PRIOR_SEARCH=false if models not cached / RAG down.
RAG_PRIOR_SEARCH = os.getenv("RAG_PRIOR_SEARCH", "true").lower() in ("1", "true", "yes")
RAG_PRIOR_K = int(os.getenv("RAG_PRIOR_K", "3"))
# Auto-snapshot resolved Guardian cases that already have notes but no rag_document_id
# when /snapshot is called, and optional backfill endpoint.

# Known noisy IoT devices that generate excessive blocks but are benign.
# Comma-separated IPs. These hosts are suppressed from ExcessiveBlocks-type
# alerts: logged as INFO to Guardian instead of triggering a full investigation.
NOISY_IOT_HOSTS = [
    ip.strip() for ip in os.getenv("NOISY_IOT_HOSTS", "").split(",") if ip.strip()
]

# ---------------------------------------------------------------------------
# Investigation safety rails (prevent OpenClaw MCP fan-out storms)
# ---------------------------------------------------------------------------
# Cap concurrent hook triggers. Each investigation can spawn a full MCP set.
MAX_CONCURRENT_INVESTIGATIONS = max(
    1, int(os.getenv("MAX_CONCURRENT_INVESTIGATIONS", "2"))
)
# Reject new investigations once this many have been accepted in the last 60s.
MAX_INVESTIGATIONS_PER_MINUTE = max(
    1, int(os.getenv("MAX_INVESTIGATIONS_PER_MINUTE", "3"))
)
# Do not re-hook the same fingerprint within this window (seconds).
INVESTIGATION_DEDUP_TTL = max(
    60, int(os.getenv("INVESTIGATION_DEDUP_TTL", "1800"))
)
# Minimum severity that may auto-investigate: info | warning | critical
# (info is excluded by default — dashboard-only signals).
INVESTIGATE_MIN_SEVERITY = os.getenv("INVESTIGATE_MIN_SEVERITY", "warning").strip().lower()
# Comma-separated alertnames that never auto-investigate (legacy noisy rules).
INVESTIGATE_DENY_ALERTNAMES = {
    a.strip()
    for a in os.getenv(
        "INVESTIGATE_DENY_ALERTNAMES",
        "SwitchInterfaceDown,SwitchIdlePortsPresent,NetclawAgentMetricsDown",
    ).split(",")
    if a.strip()
}
# Comma-separated alertnames always allowed even if severity is info.
INVESTIGATE_ALLOW_ALERTNAMES = {
    a.strip()
    for a in os.getenv("INVESTIGATE_ALLOW_ALERTNAMES", "").split(",")
    if a.strip()
}
# Honor label investigate=false|no|0|never (default true when absent).
# Set INVESTIGATE_REQUIRE_LABEL=true to only investigate when investigate=true.
INVESTIGATE_REQUIRE_LABEL = os.getenv(
    "INVESTIGATE_REQUIRE_LABEL", "false"
).lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Nautobot intent-reconcile (webhook → propose → Discord approval → apply).
# Opt-in and deliberately narrow: the webhook fires for ALL interface changes,
# but the receiver only proposes for allowed models on allowed device roles.
# Nothing applies without an explicit Discord approval (handled by the agent).
# ---------------------------------------------------------------------------
RECONCILE_ENABLED = os.getenv("RECONCILE_ENABLED", "false").lower() in ("1", "true", "yes")
NAUTOBOT_WEBHOOK_SECRET = os.getenv("NAUTOBOT_WEBHOOK_SECRET", "")
# Nautobot object models we act on (comma-separated). Start: interface only.
RECONCILE_ALLOWED_MODELS = [
    m.strip().lower() for m in os.getenv("RECONCILE_ALLOWED_MODELS", "interface").split(",") if m.strip()
]
# Device roles the agent is allowed to touch (comma-separated, case-insensitive
# substring match against the Nautobot role). Switches only to start.
RECONCILE_ALLOWED_ROLES = [
    r.strip().lower() for r in os.getenv("RECONCILE_ALLOWED_ROLES", "switch").split(",") if r.strip()
]
# Discord channel for reconcile proposals/approvals (defaults to the alert channel).
RECONCILE_CHANNEL_ID = os.getenv("RECONCILE_CHANNEL_ID", os.getenv("DISCORD_ALERT_CHANNEL_ID", ""))

# Local inventory fallback (hostname → device info)
INVENTORY_FILE = Path(__file__).parent / "inventory.yaml"

# ---------------------------------------------------------------------------
# Skill scoping (see docs/architecture/skill-context-scoping.md)
# Opt-in: scopes the runtime skills directory to the alert-relevant subset
# before triggering investigation, shrinking the injected skill index.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

SKILL_SCOPING_ENABLED = os.getenv("SKILL_SCOPING_ENABLED", "false").lower() in ("1", "true", "yes")
SKILL_SELECTOR_SCRIPT = os.getenv(
    "SKILL_SELECTOR_SCRIPT",
    str(REPO_ROOT / "scripts" / "skill-selector" / "select_skills.py"),
)
SKILL_SELECTOR_PYTHON = os.getenv("SKILL_SELECTOR_PYTHON", sys.executable)
SKILL_CATALOG_DIR = os.getenv("SKILL_CATALOG_DIR", str(REPO_ROOT / "workspace" / "skills"))
SKILL_TARGET_DIR = os.getenv(
    "SKILL_TARGET_DIR", os.path.expanduser("~/.openclaw/workspace/skills")
)
SKILL_SELECTOR_PINS = os.getenv(
    "SKILL_SELECTOR_PINS",
    "alert-triage,gait-session-tracking,memory-management,humanrail-escalation,"
    "pyats-network,pyats-troubleshoot",
)
SKILL_SELECTOR_K = os.getenv("SKILL_SELECTOR_K", "8")
# keyword is fast and dependency-light for the hot path; set to auto/embeddings
# if you want semantic ranking (requires sentence-transformers).
SKILL_SELECTOR_RANKER = os.getenv("SKILL_SELECTOR_RANKER", "keyword")
SKILL_SELECTOR_TIMEOUT = float(os.getenv("SKILL_SELECTOR_TIMEOUT", "60"))
# After triggering, restore the full catalog so interactive sessions aren't left
# with the scoped subset. The fresh alert session reads skills at session start
# (a few seconds after trigger), so we wait before restoring.
SKILL_RESTORE_AFTER_TRIGGER = os.getenv(
    "SKILL_RESTORE_AFTER_TRIGGER", "true"
).lower() in ("1", "true", "yes")
SKILL_RESTORE_DELAY = float(os.getenv("SKILL_RESTORE_DELAY", "8"))

# Serialize scoping so concurrent alerts never leave the shared skills dir in a
# partially-written state. Created lazily on the running event loop.
_scope_lock: Optional["asyncio.Lock"] = None
# Monotonic counter: each successful scope bumps it. A scheduled restore only
# runs if it's still the latest scope (no newer alert has re-scoped since).
_scope_generation: int = 0

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("alert-receiver")

# ---------------------------------------------------------------------------
# Prometheus Metrics (exposed at /metrics)
# ---------------------------------------------------------------------------

class Metrics:
    """Simple counter/gauge metrics for the alert receiver."""

    def __init__(self):
        self.alerts_received_total = 0
        self.alerts_firing_total = 0
        self.alerts_resolved_total = 0
        self.investigations_triggered_total = 0
        self.investigations_suppressed_total = 0
        self.investigations_suppressed_policy_total = 0
        self.investigations_suppressed_dedup_total = 0
        self.investigations_suppressed_rate_total = 0
        self.investigations_suppressed_concurrency_total = 0
        self.investigations_in_flight = 0
        self.discord_posts_total = 0
        self.guardian_events_posted_total = 0
        self.guardian_events_failed_total = 0
        self._investigation_durations = []  # last 100

    def record_investigation_duration(self, seconds: float):
        self._investigation_durations.append(seconds)
        if len(self._investigation_durations) > 100:
            self._investigation_durations = self._investigation_durations[-100:]

    @property
    def avg_investigation_duration(self) -> float:
        if not self._investigation_durations:
            return 0.0
        return sum(self._investigation_durations) / len(self._investigation_durations)

    def render(self) -> str:
        lines = [
            "# HELP netclaw_alerts_received_total Total alerts received from Alertmanager",
            "# TYPE netclaw_alerts_received_total counter",
            f"netclaw_alerts_received_total {self.alerts_received_total}",
            "",
            "# HELP netclaw_alerts_firing_total Firing alerts received",
            "# TYPE netclaw_alerts_firing_total counter",
            f"netclaw_alerts_firing_total {self.alerts_firing_total}",
            "",
            "# HELP netclaw_alerts_resolved_total Resolved alerts received",
            "# TYPE netclaw_alerts_resolved_total counter",
            f"netclaw_alerts_resolved_total {self.alerts_resolved_total}",
            "",
            "# HELP netclaw_investigations_triggered_total Investigations triggered (sent to OpenClaw)",
            "# TYPE netclaw_investigations_triggered_total counter",
            f"netclaw_investigations_triggered_total {self.investigations_triggered_total}",
            "",
            "# HELP netclaw_investigations_suppressed_total Investigations suppressed (all reasons)",
            "# TYPE netclaw_investigations_suppressed_total counter",
            f"netclaw_investigations_suppressed_total {self.investigations_suppressed_total}",
            "",
            "# HELP netclaw_investigations_suppressed_policy_total Suppressed by investigate label/deny list/severity",
            "# TYPE netclaw_investigations_suppressed_policy_total counter",
            f"netclaw_investigations_suppressed_policy_total {self.investigations_suppressed_policy_total}",
            "",
            "# HELP netclaw_investigations_suppressed_dedup_total Suppressed by fingerprint dedup TTL",
            "# TYPE netclaw_investigations_suppressed_dedup_total counter",
            f"netclaw_investigations_suppressed_dedup_total {self.investigations_suppressed_dedup_total}",
            "",
            "# HELP netclaw_investigations_suppressed_rate_total Suppressed by per-minute rate limit",
            "# TYPE netclaw_investigations_suppressed_rate_total counter",
            f"netclaw_investigations_suppressed_rate_total {self.investigations_suppressed_rate_total}",
            "",
            "# HELP netclaw_investigations_suppressed_concurrency_total Suppressed by concurrency cap",
            "# TYPE netclaw_investigations_suppressed_concurrency_total counter",
            f"netclaw_investigations_suppressed_concurrency_total {self.investigations_suppressed_concurrency_total}",
            "",
            "# HELP netclaw_investigations_in_flight Currently running investigation hooks",
            "# TYPE netclaw_investigations_in_flight gauge",
            f"netclaw_investigations_in_flight {self.investigations_in_flight}",
            "",
            "# HELP netclaw_discord_posts_total Discord notifications sent",
            "# TYPE netclaw_discord_posts_total counter",
            f"netclaw_discord_posts_total {self.discord_posts_total}",
            "",
            "# HELP netclaw_guardian_events_posted_total Events posted to Guardian API",
            "# TYPE netclaw_guardian_events_posted_total counter",
            f"netclaw_guardian_events_posted_total {self.guardian_events_posted_total}",
            "",
            "# HELP netclaw_guardian_events_failed_total Failed Guardian API posts",
            "# TYPE netclaw_guardian_events_failed_total counter",
            f"netclaw_guardian_events_failed_total {self.guardian_events_failed_total}",
            "",
            "# HELP netclaw_investigation_duration_seconds_avg Average investigation duration (last 100)",
            "# TYPE netclaw_investigation_duration_seconds_avg gauge",
            f"netclaw_investigation_duration_seconds_avg {self.avg_investigation_duration:.2f}",
            "",
        ]
        return "\n".join(lines) + "\n"


metrics = Metrics()

# Investigation admission control (process-wide)
_investigation_sem: Optional[asyncio.Semaphore] = None
_investigation_recent: list[float] = []  # timestamps of accepted triggers
_investigation_dedup: dict[str, float] = {}  # fingerprint -> last trigger mono time
_investigation_gate_lock: Optional[asyncio.Lock] = None


def _get_investigation_sem() -> asyncio.Semaphore:
    global _investigation_sem
    if _investigation_sem is None:
        _investigation_sem = asyncio.Semaphore(MAX_CONCURRENT_INVESTIGATIONS)
    return _investigation_sem


def _get_investigation_gate_lock() -> asyncio.Lock:
    global _investigation_gate_lock
    if _investigation_gate_lock is None:
        _investigation_gate_lock = asyncio.Lock()
    return _investigation_gate_lock


def _label_get(labels: "AlertLabel", key: str, default: str = "") -> str:
    """Read a label including AM extra labels (investigate, device_name, …)."""
    val = getattr(labels, key, None)
    if val is not None and str(val) != "":
        return str(val)
    extra = getattr(labels, "model_extra", None) or {}
    if key in extra and extra[key] is not None and str(extra[key]) != "":
        return str(extra[key])
    # pydantic v2 sometimes stores extras as attributes when extra=allow
    try:
        data = labels.model_dump() if hasattr(labels, "model_dump") else {}
        if key in data and data[key] is not None and str(data[key]) != "":
            return str(data[key])
    except Exception:
        pass
    return default


_SEVERITY_RANK = {"info": 0, "none": 0, "": 0, "warning": 1, "warn": 1, "critical": 2, "error": 2}


def should_auto_investigate(alert: "Alert") -> tuple[bool, str]:
    """Policy gate: may this firing alert open an OpenClaw hook session?

    Returns (allowed, reason). Resolved alerts never investigate.
    """
    if alert.status != "firing":
        return False, "resolved"

    name = (alert.labels.alertname or "").strip()
    if name in INVESTIGATE_DENY_ALERTNAMES:
        return False, f"deny_list:{name}"

    inv = _label_get(alert.labels, "investigate", "").strip().lower()
    if inv in ("false", "no", "0", "never", "off"):
        return False, "label:investigate=false"
    if INVESTIGATE_REQUIRE_LABEL and inv not in ("true", "yes", "1", "on"):
        return False, "label:investigate_required"

    if name in INVESTIGATE_ALLOW_ALERTNAMES:
        return True, "allow_list"

    sev = (alert.labels.severity or "warning").strip().lower()
    min_rank = _SEVERITY_RANK.get(INVESTIGATE_MIN_SEVERITY, 1)
    if _SEVERITY_RANK.get(sev, 1) < min_rank:
        return False, f"severity:{sev}<{INVESTIGATE_MIN_SEVERITY}"

    # High-cardinality signals must opt in via investigate=true (already checked)
    if _label_get(alert.labels, "cardinality", "").strip().lower() == "high" and inv not in (
        "true",
        "yes",
        "1",
        "on",
    ):
        return False, "cardinality:high"

    return True, "ok"


async def admit_investigation(fingerprint: str) -> tuple[bool, str]:
    """Rate limit + dedup + concurrency. Call release_investigation() after work.

    Concurrency is non-blocking: at capacity we suppress rather than queue,
    because a queue re-creates the storm when the gateway recovers from OOM.
    """
    now = time.monotonic()
    fp = fingerprint or f"anon-{now}"
    sem = _get_investigation_sem()

    async with _get_investigation_gate_lock():
        global _investigation_recent
        _investigation_recent = [t for t in _investigation_recent if now - t < 60.0]
        cutoff = now - float(INVESTIGATION_DEDUP_TTL)
        for k in [k for k, t in _investigation_dedup.items() if t < cutoff]:
            _investigation_dedup.pop(k, None)

        last = _investigation_dedup.get(fp)
        if last is not None and (now - last) < float(INVESTIGATION_DEDUP_TTL):
            metrics.investigations_suppressed_dedup_total += 1
            metrics.investigations_suppressed_total += 1
            return False, "dedup"

        if len(_investigation_recent) >= MAX_INVESTIGATIONS_PER_MINUTE:
            metrics.investigations_suppressed_rate_total += 1
            metrics.investigations_suppressed_total += 1
            return False, "rate_limit"

    # Non-blocking semaphore acquire (outside lock to avoid deadlock)
    try:
        await asyncio.wait_for(sem.acquire(), timeout=0.01)
    except asyncio.TimeoutError:
        metrics.investigations_suppressed_concurrency_total += 1
        metrics.investigations_suppressed_total += 1
        return False, "concurrency"

    async with _get_investigation_gate_lock():
        _investigation_dedup[fp] = time.monotonic()
        _investigation_recent.append(time.monotonic())
        metrics.investigations_in_flight += 1
    return True, "admitted"


def release_investigation() -> None:
    """Release concurrency slot after trigger_netclaw finishes."""
    try:
        _get_investigation_sem().release()
    except ValueError:
        pass
    metrics.investigations_in_flight = max(0, metrics.investigations_in_flight - 1)

# ---------------------------------------------------------------------------
# Models (Alertmanager webhook payload)
# ---------------------------------------------------------------------------


class AlertLabel(BaseModel):
    alertname: str = ""
    instance: str = ""
    severity: str = ""
    job: str = ""
    # Allow any extra labels
    model_config = {"extra": "allow"}


class AlertAnnotation(BaseModel):
    summary: str = ""
    description: str = ""
    model_config = {"extra": "allow"}


class Alert(BaseModel):
    status: str  # "firing" or "resolved"
    labels: AlertLabel
    annotations: AlertAnnotation
    startsAt: str = ""
    endsAt: str = ""
    generatorURL: str = ""
    fingerprint: str = ""


class AlertmanagerPayload(BaseModel):
    version: str = "4"
    groupKey: str = ""
    status: str = ""  # "firing" or "resolved"
    receiver: str = ""
    alerts: list[Alert] = []
    groupLabels: dict = {}
    commonLabels: dict = {}
    commonAnnotations: dict = {}
    externalURL: str = ""


# ---------------------------------------------------------------------------
# SoT Lookup
# ---------------------------------------------------------------------------


def _nested_name(obj) -> str:
    """Nautobot nested objects expose 'name'; brief refs expose 'display'."""
    if isinstance(obj, dict):
        return obj.get("name") or obj.get("display") or ""
    return ""


def _ip_from_nautobot_device(device: dict) -> str:
    """Extract mgmt IP from a Nautobot *device* (dcim.devices).

    Modern Nautobot (2.x/3.x) exposes primary_ip4 / primary_ip6, not the older
    combined ``primary_ip`` field. Prefer IPv4, then IPv6. Use ``host`` when
    present, else strip the prefix from ``address`` / ``display``.
    """
    for key in ("primary_ip4", "primary_ip6", "primary_ip"):
        obj = device.get(key)
        if not obj:
            continue
        if isinstance(obj, str):
            return obj.split("/")[0].strip()
        if not isinstance(obj, dict):
            continue
        host = (obj.get("host") or "").strip()
        if host:
            return host
        for addr_key in ("address", "display"):
            raw = (obj.get(addr_key) or "").strip()
            if raw:
                # "192.168.3.1/24" or "192.168.3.1/24: Global"
                return raw.split("/")[0].split(":")[0].strip()
    return ""


def _device_dict_from_nautobot(device: dict, fallback_name: str) -> dict:
    status = device.get("status")
    if isinstance(status, dict):
        status_val = status.get("value") or status.get("label") or status.get("name") or ""
    else:
        status_val = str(status or "")
    return {
        "name": device.get("name", fallback_name),
        "ip": _ip_from_nautobot_device(device),
        "platform": _nested_name(device.get("platform")),
        "role": _nested_name(device.get("role")),
        "site": _nested_name(device.get("location")),
        "status": status_val,
        "source": "nautobot",
    }


def _pick_best_nautobot_device(results: list, query: str) -> Optional[dict]:
    """Choose the best device when Nautobot returns multiple name matches.

    Alert labels are often short (pfsense, r640) while SoT names are longer
    (pfSense-FW01, r640-pve). Prefer exact casefold name, then startswith,
    then shortest name containing the query.
    """
    if not results:
        return None
    if len(results) == 1:
        return results[0]

    q = (query or "").casefold()
    scored = []
    for d in results:
        name = d.get("name") or ""
        n = name.casefold()
        if n == q:
            score = (0, len(n))
        elif n.startswith(q) or q.startswith(n):
            score = (1, len(n))
        elif q in n or n in q:
            score = (2, len(n))
        else:
            score = (3, len(n))
        scored.append((score, d))
    scored.sort(key=lambda x: x[0])
    return scored[0][1]


async def lookup_device_nautobot(hostname: str) -> Optional[dict]:
    """Query Nautobot for device info by hostname / short alert label.

    Tries exact name, case-insensitive exact (name__ie), then substring
    (name__ic), then free-text q=. Picks the best match when multiple hit.
    """
    if not NAUTOBOT_URL or not NAUTOBOT_TOKEN:
        return None

    headers = {
        "Authorization": f"Token {NAUTOBOT_TOKEN}",
        "Accept": "application/json",
    }
    # depth=1 expands role/platform/location so they carry a "name".
    attempts = [
        {"name": hostname, "depth": 1},
        {"name__ie": hostname, "depth": 1},
        {"name__ic": hostname, "depth": 1},
        {"q": hostname, "depth": 1},
    ]

    try:
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            for params in attempts:
                resp = await client.get(
                    f"{NAUTOBOT_URL}/api/dcim/devices/",
                    params=params,
                    headers=headers,
                )
                if resp.status_code != 200:
                    # Unknown filter on some Nautobot versions — try next strategy
                    if resp.status_code == 400:
                        continue
                    log.warning(
                        f"Nautobot returned {resp.status_code} for device '{hostname}' "
                        f"(params={list(params.keys())})"
                    )
                    continue

                results = (resp.json() or {}).get("results") or []
                if not results:
                    continue

                device = _pick_best_nautobot_device(results, hostname)
                if not device:
                    continue

                info = _device_dict_from_nautobot(device, hostname)
                if info["name"].casefold() != hostname.casefold():
                    log.info(
                        f"Nautobot resolved alert host '{hostname}' → '{info['name']}' "
                        f"(via {list(params.keys())[0]})"
                    )
                return info

            log.info(f"Device '{hostname}' not found in Nautobot")
            return None
    except Exception as e:
        log.warning(f"Nautobot lookup failed for '{hostname}': {e}")
        return None


async def lookup_device_inventory(hostname: str) -> Optional[dict]:
    """Fallback lookup from local inventory.yaml.

    Supports:
      - exact and case-insensitive key match
      - IP match
      - optional per-device ``aliases: [pfsense, fw01]`` lists
    """
    if not INVENTORY_FILE.exists():
        return None

    try:
        import yaml
        inventory = yaml.safe_load(INVENTORY_FILE.read_text()) or {}
        devices = inventory.get("devices", {}) or {}
        q = (hostname or "").casefold()

        def _from_entry(name: str, dev: dict) -> dict:
            return {
                "name": dev.get("nautobot_name") or name,
                "ip": dev.get("ip", ""),
                "platform": dev.get("platform", ""),
                "role": dev.get("role", ""),
                "site": dev.get("site", ""),
                "status": "active",
                "source": "local-inventory",
            }

        # Direct / case-insensitive key
        if hostname in devices:
            return _from_entry(hostname, devices[hostname])
        for name, dev in devices.items():
            if name.casefold() == q:
                return _from_entry(name, dev)

        # Aliases
        for name, dev in devices.items():
            aliases = dev.get("aliases") or []
            if not isinstance(aliases, list):
                continue
            for alias in aliases:
                if str(alias).casefold() == q:
                    return _from_entry(name, dev)

        # IP match
        for name, dev in devices.items():
            if dev.get("ip") == hostname:
                return _from_entry(name, dev)
    except Exception as e:
        log.warning(f"Local inventory lookup failed: {e}")

    return None


async def lookup_device(hostname: str) -> dict:
    """Try Nautobot first, fall back to local inventory."""
    # Strip port if present (alertmanager instance often includes :port)
    clean_host = hostname.split(":")[0]

    result = await lookup_device_nautobot(clean_host)
    if result:
        return result

    result = await lookup_device_inventory(clean_host)
    if result:
        return result

    return {
        "name": clean_host,
        "ip": clean_host,  # Assume the hostname IS the IP if we can't resolve
        "platform": "unknown",
        "role": "unknown",
        "site": "unknown",
        "status": "unknown",
        "source": "unresolved",
    }


# ---------------------------------------------------------------------------
# NetClaw Trigger
# ---------------------------------------------------------------------------


async def scope_skills_for_alert(alert: Alert, device_info: dict) -> Optional[int]:
    """Scope the runtime skills directory to the alert-relevant subset.

    Runs the skill selector (scripts/skill-selector/select_skills.py) as a
    subprocess with --apply. Fail-open: any error leaves the existing catalog in
    place so the investigation still has its skills. Serialized via a lock so
    concurrent alerts don't corrupt the shared directory.

    Returns the scope generation number on success (for a later restore), or
    None if scoping was skipped or failed.
    """
    if not SKILL_SCOPING_ENABLED:
        return None
    if alert.status != "firing":
        return None  # resolved alerts just post an all-clear; no scoping needed

    global _scope_lock, _scope_generation
    if _scope_lock is None:
        _scope_lock = asyncio.Lock()

    alert_ctx = json.dumps({
        "alertname": alert.labels.alertname,
        "summary": alert.annotations.summary,
        "description": alert.annotations.description,
        "device_platform": device_info.get("platform", ""),
        "device_role": device_info.get("role", ""),
        "severity": alert.labels.severity,
    })

    cmd = [
        SKILL_SELECTOR_PYTHON, SKILL_SELECTOR_SCRIPT,
        "--alert", alert_ctx,
        "--catalog", SKILL_CATALOG_DIR,
        "--target", SKILL_TARGET_DIR,
        "--pin", SKILL_SELECTOR_PINS,
        "--k", SKILL_SELECTOR_K,
        "--ranker", SKILL_SELECTOR_RANKER,
        "--apply", "--json",
    ]

    async with _scope_lock:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=SKILL_SELECTOR_TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                log.warning("Skill scoping timed out — proceeding with existing catalog")
                return None

            if proc.returncode != 0:
                log.warning(
                    f"Skill scoping failed (exit {proc.returncode}): "
                    f"{stderr.decode(errors='replace')[:200]} — proceeding with existing catalog"
                )
                return None

            _scope_generation += 1
            my_gen = _scope_generation
            try:
                result = json.loads(stdout.decode(errors="replace"))
                log.info(
                    f"Skills scoped for {alert.labels.alertname}: "
                    f"{result['selected_size']}/{result['catalog_size']} skills, "
                    f"index ~{result['index_tokens_saved']} tokens saved "
                    f"({result['index_tokens_saved_pct']}%) — {result['selected']}"
                )
            except (json.JSONDecodeError, KeyError):
                log.info(f"Skills scoped for {alert.labels.alertname} (unparsed selector output)")
            return my_gen
        except FileNotFoundError:
            log.warning(
                f"Skill selector not found at {SKILL_SELECTOR_SCRIPT} — "
                "proceeding with existing catalog"
            )
            return None
        except Exception as e:
            log.warning(f"Skill scoping error: {e} — proceeding with existing catalog")
            return None


async def restore_skills_after_trigger(scope_gen: int) -> None:
    """After the alert session has read the scoped dir, restore the full catalog
    so interactive sessions aren't left with the reduced set. Skips the restore
    if a newer alert has re-scoped since (its own restore will handle it)."""
    if not (SKILL_SCOPING_ENABLED and SKILL_RESTORE_AFTER_TRIGGER):
        return
    if scope_gen is None:
        return

    await asyncio.sleep(SKILL_RESTORE_DELAY)

    global _scope_lock, _scope_generation
    if _scope_lock is None:
        _scope_lock = asyncio.Lock()

    async with _scope_lock:
        if scope_gen != _scope_generation:
            # A newer alert re-scoped after us; leave its scope in place.
            log.info(
                f"Skip restore (gen {scope_gen} superseded by {_scope_generation}) — "
                "a newer alert owns the current scope"
            )
            return
        cmd = [
            SKILL_SELECTOR_PYTHON, SKILL_SELECTOR_SCRIPT,
            "--restore-all",
            "--catalog", SKILL_CATALOG_DIR,
            "--target", SKILL_TARGET_DIR,
            "--apply", "--json",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=SKILL_SELECTOR_TIMEOUT
            )
            if proc.returncode == 0:
                log.info("Restored full skill catalog after triage (interactive-safe resting state)")
            else:
                log.warning(
                    f"Skill restore failed (exit {proc.returncode}): "
                    f"{stderr.decode(errors='replace')[:200]}"
                )
        except asyncio.TimeoutError:
            proc.kill()
            log.warning("Skill restore timed out")
        except Exception as e:
            log.warning(f"Skill restore error: {e}")


async def trigger_netclaw(alert: Alert, device_info: dict):
    """Send enriched alert to OpenClaw gateway to trigger investigation.

    Stage 6 lifecycle: open (or complete) the Guardian case *before* the hook
    so the investigation prompt can carry ``guardian_event_id`` for PATCH.
    """
    guardian_event_id = None
    if alert.status == "resolved":
        # Prefer closing the open investigating case over a second diary row.
        guardian_event_id = await complete_guardian_event_resolved(alert, device_info)
        if not guardian_event_id:
            guardian_event_id = await post_guardian_event(
                alert, device_info, status="resolved"
            )
    else:
        guardian_event_id = await post_guardian_event(
            alert, device_info, status="investigating"
        )

    message = build_investigation_prompt(
        alert, device_info, guardian_event_id=guardian_event_id
    )

    if OPENCLAW_GATEWAY_URL and OPENCLAW_HOOK_TOKEN:
        try:
            payload = {
                "status": alert.status,
                "alerts": [
                    {
                        "status": alert.status,
                        "fingerprint": alert.fingerprint,
                        "labels": {
                            "alertname": alert.labels.alertname,
                            "instance": alert.labels.instance,
                            "severity": alert.labels.severity,
                            "device_name": device_info["name"],
                            "device_ip": device_info["ip"],
                            "device_role": device_info["role"],
                            "device_platform": device_info["platform"],
                        },
                        "annotations": {
                            "summary": alert.annotations.summary,
                            "description": alert.annotations.description,
                            "investigation_prompt": message,
                            **(
                                {"guardian_event_id": guardian_event_id}
                                if guardian_event_id
                                else {}
                            ),
                        },
                    }
                ],
            }

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{OPENCLAW_GATEWAY_URL}/hooks/alert",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {OPENCLAW_HOOK_TOKEN}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code in (200, 202):
                    log.info(f"Triggered NetClaw investigation for {alert.labels.alertname} on {device_info['name']}")
                    metrics.investigations_triggered_total += 1
                else:
                    log.error(f"OpenClaw gateway returned {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log.error(f"Failed to trigger NetClaw: {e}")
    else:
        # No gateway configured — log the investigation prompt for manual pickup
        log.warning("No OpenClaw gateway configured — logging investigation prompt")
        log.info(f"INVESTIGATION PROMPT:\n{message}")

    # Post to Discord if configured — but suppress known-noise alerts that don't
    # warrant human attention or investigation (they just clutter the channel).
    if DISCORD_WEBHOOK_URL and alert.status == "firing":
        if alert.labels.alertname not in DISCORD_SUPPRESS_ALERTS:
            await post_discord(alert, device_info)
        else:
            log.info(f"Discord suppressed for {alert.labels.alertname} (in suppress list)")


def _search_prior_investigations(alert: Alert, device_info: dict) -> list:
    """Stage 7: query RAG for prior investigation snapshots (fail-open).

    Searches collection alias ``investigations`` (all snapshot_* corpora).
    Returns a list of short hit dicts for prompt injection.
    """
    if not RAG_PRIOR_SEARCH:
        return []
    query = f"{alert.labels.alertname} {device_info.get('name', '')} {alert.annotations.summary or ''}".strip()
    if not query:
        return []
    try:
        rag_path = REPO_ROOT / "mcp-servers" / "rag-mcp"
        if str(rag_path) not in sys.path:
            sys.path.insert(0, str(rag_path))
        from rag_mcp_server import rag_search as _rag_search

        result = _rag_search(query=query, k=RAG_PRIOR_K, collection="investigations")
        if not result.get("success"):
            log.warning(
                "RAG prior search failed: %s",
                (result.get("error") or {}).get("message", result),
            )
            return []
        data = result.get("data") or {}
        hits = []
        for r in data.get("results") or []:
            text = (r.get("chunk_text") or r.get("text") or "").strip()
            if not text:
                continue
            meta = r.get("metadata") or {}
            hits.append({
                "score": r.get("score"),
                "low_confidence": r.get("low_confidence"),
                "title": meta.get("title") or meta.get("document_id") or "",
                "collection": meta.get("collection") or data.get("collection"),
                "excerpt": text[:600],
            })
        if hits:
            log.info(
                "RAG prior search: %d hit(s) for %s (collections=%s, %sms)",
                len(hits),
                alert.labels.alertname,
                data.get("collections_searched"),
                data.get("latency_ms"),
            )
        return hits
    except Exception as e:
        log.warning("RAG prior search error (continuing without priors): %s", e)
        return []


def build_investigation_prompt(
    alert: Alert,
    device_info: dict,
    guardian_event_id: Optional[str] = None,
) -> str:
    """Build the investigation prompt NetClaw will receive."""
    parts = [
        f"ALERT RECEIVED — {alert.labels.alertname}",
        f"Status: {alert.status}",
        f"Severity: {alert.labels.severity}",
        f"Device: {device_info['name']} ({device_info['ip']})",
        f"Role: {device_info['role']} | Platform: {device_info['platform']} | Site: {device_info['site']}",
        f"Summary: {alert.annotations.summary}",
        f"Alert fingerprint: {alert.fingerprint}",
        f"Guardian site: {normalize_guardian_site(device_info.get('site'))}",
    ]
    if guardian_event_id:
        parts.append(f"Guardian event id: {guardian_event_id}")

    if alert.annotations.description:
        parts.append(f"Description: {alert.annotations.description}")

    # Stage 7: inject prior investigation hits as FACTS (receiver already searched).
    # Avoids relying on the model to call rag_search before tools.
    prior_hits = _search_prior_investigations(alert, device_info)
    if prior_hits:
        parts.append("")
        parts.append("PRIOR INVESTIGATION HITS (from local RAG — Stage 7):")
        for i, h in enumerate(prior_hits, 1):
            conf = "low-confidence" if h.get("low_confidence") else "ok"
            parts.append(
                f"  [{i}] score={h.get('score')} ({conf}) "
                f"title={h.get('title') or 'n/a'}"
            )
            parts.append(f"      {h['excerpt'].replace(chr(10), ' ')[:400]}")
        parts.append(
            "  Use these priors to skip redundant diagnostics when the root "
            "cause class matches; still verify live state on the device."
        )
    else:
        parts.append("")
        parts.append(
            "PRIOR INVESTIGATION HITS: none indexed yet for this alert "
            "(or RAG unavailable)."
        )

    parts.append("")
    parts.append("INSTRUCTIONS:")
    parts.append(f"1. The device '{device_info['name']}' at IP {device_info['ip']} has triggered alert '{alert.labels.alertname}'.")

    # RAG search for prior investigations (member path may still re-query)
    parts.append(
        "1b. Review PRIOR INVESTIGATION HITS above. Optionally re-query RAG:\n"
        f"   rag_search(query=\"{alert.labels.alertname} {device_info['name']}\", "
        "collection=\"investigations\")\n"
        "   If a prior investigation matches, reference its root cause and skip "
        "redundant diagnostic steps after a quick live confirm."
    )

    if device_info["platform"] == "pfsense":
        parts.append("2. Use the pfSense MCP tools to investigate (get system status, interfaces, logs).")
        # Specific procedure for internal host excessive blocks
        if "excessiveblocks" in alert.labels.alertname.lower() or "internal" in alert.labels.alertname.lower():
            parts.append(
                "\n   SPECIFIC PROCEDURE FOR INTERNAL HOST BLOCKS:\n"
                "   a) Identify the device: use `get_arp_table` and `search_dhcp_leases`\n"
                "      to find the hostname, MAC, and device type at the blocked IP.\n"
                "   b) Check WHAT is being blocked: use `get_firewall_log` filtered by\n"
                "      the source IP. Look at destination IPs, ports, and protocols.\n"
                "   c) Enrich destination IPs: for each external destination being blocked,\n"
                "      determine if it is a known service (AWS/Google/CDN = likely IoT cloud),\n"
                "      use `greynoise_community_lookup` and ASN/geo lookup.\n"
                "   d) Determine the verdict:\n"
                "      - BENIGN: IoT device phoning home (Ring, Nest, smart TV, etc.)\n"
                "        hitting a GeoIP or pfBlockerNG list. Recommendation: whitelist\n"
                "        the destination or suppress the alert for this source.\n"
                "      - SUSPICIOUS: unknown device, unusual ports (IRC, Tor, crypto mining),\n"
                "        destinations with bad reputation. Recommendation: ESCALATE.\n"
                "   e) Include in your report: device identity, what it tried to reach,\n"
                "      why it was blocked (which rule), and your verdict with reasoning.\n"
                "   f) If benign, suggest a specific fix (whitelist entry or alert exception)."
            )
    elif device_info["platform"] in ("ios", "iosxe", "nxos"):
        parts.append("2. Use pyATS to run diagnostic commands on this device.")
    elif device_info["platform"] == "proxmox":
        parts.append("2. Use the Proxmox MCP tools to check VM/container and node health.")
    else:
        parts.append("2. Use available tools (SNMP, SSH, MCP) to investigate the device.")

    parts.append("3. Query Prometheus for recent metric history if relevant.")
    parts.append(
        "4. For any EXTERNAL/public source IP in this alert (e.g. port scans, "
        "WAN blocks, suspicious connections), enrich it before concluding:\n"
        "   - `greynoise_community_lookup` — is it benign internet noise / a "
        "known scanner (Censys, Shodan) or targeted? (free, no key)\n"
        "   - `threatintel_lookup_ip` / `abuseipdb_check` / `otx_get_pulses` — "
        "reputation, abuse reports, and threat pulses.\n"
        "   - gtrace `asn_lookup` / `geo_lookup` — who owns the IP and where.\n"
        "   Skip enrichment for private/RFC1918 addresses."
    )
    parts.append("5. Produce a triage report: what's wrong, likely cause, and recommended action.")
    parts.append("6. Do NOT remediate without explicit human approval.")

    # NOTE: Discord delivery (Step 7) and Guardian event logging (Step 8) are
    # defined in the alert-triage skill file itself — NOT here. Putting "POST to
    # <url>" or "run via exec: openclaw message send" in this payload causes the
    # model to (correctly) flag it as prompt injection from an untrusted webhook
    # and refuse. The skill is trusted content; the payload carries facts only.
    # Role fact (not a URL/command): Border must n2n_route first per skill.
    parts.append(
        "7. You are the Border brain for this alert. Per the alert-triage skill, "
        "your first tool call is n2n_route(target_hint=\"alert-triage\"); then "
        "poll until completed. Do not investigate with device tools first. "
        "Member delivery (Discord/Guardian) is defined in the skill."
    )

    if alert.status == "resolved":
        parts = [
            f"ALERT RESOLVED — {alert.labels.alertname}",
            f"Device: {device_info['name']} ({device_info['ip']})",
            f"Alert fingerprint: {alert.fingerprint}",
            f"Guardian site: {normalize_guardian_site(device_info.get('site'))}",
        ]
        if guardian_event_id:
            parts.append(f"Guardian event id: {guardian_event_id}")
        parts.append(
            "The alert has cleared. Follow the alert-triage skill to post a brief "
            "all-clear confirmation to the alerts channel and complete the Guardian "
            "case (PATCH if event id present)."
        )

    return "\n".join(parts)


async def post_discord(alert: Alert, device_info: dict):
    """Post alert notification to Discord webhook."""
    severity_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(
        alert.labels.severity, "⚪"
    )
    content = (
        f"{severity_emoji} **{alert.labels.alertname}** on `{device_info['name']}` ({device_info['ip']})\n"
        f"> {alert.annotations.summary}\n"
        f"Severity: {alert.labels.severity} | Status: {alert.status}"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(DISCORD_WEBHOOK_URL, json={"content": content})
            metrics.discord_posts_total += 1
    except Exception as e:
        log.warning(f"Discord post failed: {e}")


# ---------------------------------------------------------------------------
# Network Guardian Events API
# ---------------------------------------------------------------------------


def normalize_guardian_site(site: Optional[str]) -> str:
    """Map inventory/Nautobot location names onto a Guardian ``sites.id``.

    Home pilot Guardian only seeds ``home``. Nautobot location ``House`` and
    unresolved ``unknown`` must not be POSTed raw — they FK-fail with HTTP 500.
    """
    raw = (site or "").strip()
    if not raw or raw.casefold() in _GUARDIAN_SITE_ALIASES:
        return GUARDIAN_DEFAULT_SITE
    if raw.casefold() == GUARDIAN_DEFAULT_SITE.casefold():
        return GUARDIAN_DEFAULT_SITE
    # Free-text location display names (spaces, mixed case) → default.
    if " " in raw or not raw.replace("-", "").replace("_", "").isalnum():
        return GUARDIAN_DEFAULT_SITE
    return raw.casefold() if raw.casefold() != "unknown" else GUARDIAN_DEFAULT_SITE


def _guardian_headers() -> dict:
    return {
        "Authorization": f"Bearer {NETWORK_GUARDIAN_TOKEN}",
        "Content-Type": "application/json",
    }


async def post_guardian_event(alert: Alert, device_info: dict, status: str = "investigating"):
    """Post an event to the Network Guardian dashboard diary.

    Called when an alert is received to create the initial diary entry.
    Returns the event UUID so the investigation prompt can carry it for PATCH.
    """
    if not NETWORK_GUARDIAN_URL or not NETWORK_GUARDIAN_TOKEN:
        return None

    site = normalize_guardian_site(device_info.get("site"))
    severity_map = {"critical": "alert", "warning": "watch", "info": "info"}
    severity = severity_map.get(alert.labels.severity, "info")

    # For resolved alerts, post an "ok" event
    if alert.status == "resolved":
        severity = "ok"
        status = "resolved"

    payload = {
        "message": f"{alert.labels.alertname}: {alert.annotations.summary}" if alert.status == "firing"
                   else f"{alert.labels.alertname} resolved on {device_info['name']}",
        "severity": severity,
        "category": categorize_alert(alert.labels.alertname),
        "source": "netclaw",
        "alert_name": alert.labels.alertname,
        "alert_fingerprint": alert.fingerprint,
        "status": status,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{NETWORK_GUARDIAN_URL}/api/events?site={site}",
                json=payload,
                headers=_guardian_headers(),
            )
            if resp.status_code == 201:
                event = resp.json()
                log.info(
                    f"Guardian event created: {event.get('id')} "
                    f"({alert.labels.alertname}) site={site}"
                )
                metrics.guardian_events_posted_total += 1
                return event.get("id")
            else:
                log.warning(f"Guardian event POST failed: {resp.status_code} {resp.text[:200]}")
                metrics.guardian_events_failed_total += 1
                return None
    except Exception as e:
        log.warning(f"Guardian event POST error: {e}")
        metrics.guardian_events_failed_total += 1
        return None


async def patch_guardian_event(
    event_id: str,
    site: str,
    *,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    message: Optional[str] = None,
    investigation_notes: Optional[str] = None,
    root_cause: Optional[str] = None,
) -> bool:
    """PATCH an existing Guardian diary entry (investigation outcome lifecycle)."""
    if not NETWORK_GUARDIAN_URL or not NETWORK_GUARDIAN_TOKEN or not event_id:
        return False

    body = {}
    if status is not None:
        body["status"] = status
    if severity is not None:
        body["severity"] = severity
    if message is not None:
        body["message"] = message
    if investigation_notes is not None:
        body["investigation_notes"] = investigation_notes
    if root_cause is not None:
        body["root_cause"] = root_cause
    if not body:
        return False

    site = normalize_guardian_site(site)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                f"{NETWORK_GUARDIAN_URL}/api/events/{event_id}?site={site}",
                json=body,
                headers=_guardian_headers(),
            )
            if resp.status_code == 200:
                log.info(f"Guardian event patched: {event_id} status={status}")
                return True
            log.warning(
                f"Guardian event PATCH failed: {resp.status_code} {resp.text[:200]}"
            )
            metrics.guardian_events_failed_total += 1
            return False
    except Exception as e:
        log.warning(f"Guardian event PATCH error: {e}")
        metrics.guardian_events_failed_total += 1
        return False


async def find_open_guardian_event(
    fingerprint: str, site: str, *, limit: int = 50
) -> Optional[str]:
    """Find the newest open (investigating/logged) event for an alert fingerprint."""
    if not NETWORK_GUARDIAN_URL or not NETWORK_GUARDIAN_TOKEN or not fingerprint:
        return None

    site = normalize_guardian_site(site)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{NETWORK_GUARDIAN_URL}/api/events?site={site}&limit={limit}"
                f"&fingerprint={fingerprint}",
                headers=_guardian_headers(),
            )
            if resp.status_code != 200:
                # Older Guardian builds may lack fingerprint filter — fall back.
                resp = await client.get(
                    f"{NETWORK_GUARDIAN_URL}/api/events?site={site}&limit={limit}",
                    headers=_guardian_headers(),
                )
            if resp.status_code != 200:
                return None
            events = resp.json().get("events") or []
            open_statuses = {"investigating", "logged"}
            for ev in events:
                if ev.get("alert_fingerprint") != fingerprint:
                    continue
                if ev.get("status") in open_statuses:
                    return ev.get("id")
    except Exception as e:
        log.warning(f"Guardian event lookup error: {e}")
    return None


async def complete_guardian_event_resolved(
    alert: Alert, device_info: dict
) -> Optional[str]:
    """On alert resolve: PATCH open case by fingerprint if one exists."""
    site = normalize_guardian_site(device_info.get("site"))
    event_id = await find_open_guardian_event(alert.fingerprint, site)
    if not event_id:
        return None
    ok = await patch_guardian_event(
        event_id,
        site,
        status="resolved",
        severity="ok",
        message=f"{alert.labels.alertname} resolved on {device_info['name']}",
        root_cause="alert-cleared",
        investigation_notes=(
            f"Alertmanager resolved {alert.labels.alertname} on "
            f"{device_info['name']} ({device_info['ip']})."
        ),
    )
    return event_id if ok else None


def categorize_alert(alert_name: str) -> str:
    """Map alert name to a category for the Guardian dashboard."""
    name = (alert_name or "").lower()
    if any(k in name for k in ("internet", "wan", "latency", "loss", "edge")):
        return "wan"
    if any(k in name for k in ("wifi", "ap", "access", "retries", "unifi")):
        return "wifi"
    if any(k in name for k in ("speed", "bandwidth", "sla")):
        return "bandwidth"
    if any(k in name for k in ("port", "scan", "threat", "block")):
        return "security"
    if any(k in name for k in ("monitor", "stale", "exporter")):
        return "monitoring"
    return "system"


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NetClaw Alert Receiver",
    description="Accepts Alertmanager webhooks, enriches with SoT, triggers NetClaw investigation.",
    version="1.0.0",
)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    return metrics.render()


async def _fetch_guardian_event(event_id: str, site: str) -> Optional[dict]:
    """Load one Guardian event by scanning recent pages (home pilot scale)."""
    if not NETWORK_GUARDIAN_URL or not NETWORK_GUARDIAN_TOKEN:
        return None
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{NETWORK_GUARDIAN_URL}/api/events?site={site}&limit=100",
            headers={"Authorization": f"Bearer {NETWORK_GUARDIAN_TOKEN}"},
        )
        if resp.status_code != 200:
            return None
        events = resp.json().get("events", [])
        return next((e for e in events if e.get("id") == event_id), None)


async def _snapshot_event_to_rag(event: dict, site: str) -> dict:
    """Build narrative + rag_snapshot + PATCH rag_document_id. Shared by /snapshot."""
    event_id = event.get("id")
    if event.get("rag_document_id"):
        return {
            "status": "skipped",
            "message": "already linked",
            "snapshot_id": event.get("rag_document_id"),
            "event_id": event_id,
        }
    if not (event.get("investigation_notes") or event.get("root_cause")):
        return {
            "status": "skipped",
            "message": "no investigation_notes or root_cause to snapshot",
            "event_id": event_id,
        }

    parts = [
        f"# Investigation: {event.get('alert_name', 'Unknown Alert')}",
        f"Site: {site}",
        f"Date: {event.get('timestamp', 'unknown')}",
        f"Category: {event.get('category', 'general')}",
        f"Severity: {event.get('severity', 'info')}",
        f"Status: {event.get('status', 'unknown')}",
        "",
        "## Alert Summary",
        event.get("message", "No message"),
        "",
    ]
    if event.get("investigation_notes"):
        parts += ["## Investigation Notes", event["investigation_notes"], ""]
    if event.get("root_cause"):
        parts += ["## Root Cause", event["root_cause"], ""]
    if event.get("expert_feedback"):
        parts += [
            "## Expert Feedback",
            event["expert_feedback"],
            f"Quality rating: {event.get('feedback_quality', 'unrated')}",
            "",
        ]
    content = "\n".join(parts)
    label = (event.get("alert_name") or "investigation").replace(" ", "-").lower()
    # Keep label filesystem-safe for snapshot collection names
    label = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in label)[:80]

    rag_path = REPO_ROOT / "mcp-servers" / "rag-mcp"
    if str(rag_path) not in sys.path:
        sys.path.insert(0, str(rag_path))
    from rag_mcp_server import rag_snapshot as _rag_snapshot

    result = _rag_snapshot(
        label=label,
        content=content,
        source_description=f"Network Guardian investigation: {event.get('alert_name', 'unknown')}",
        devices=[],
        commands=[],
    )
    if not result.get("success"):
        error = result.get("error", {}) or {}
        return {
            "status": "error",
            "message": f"RAG ingestion failed: {error.get('message', 'unknown')}",
            "code": error.get("code"),
            "event_id": event_id,
        }

    snapshot_id = result.get("data", {}).get("snapshot_id")
    log.info(f"RAG snapshot created: {snapshot_id} for event {event_id}")

    async with httpx.AsyncClient(timeout=10) as client:
        patch_resp = await client.patch(
            f"{NETWORK_GUARDIAN_URL}/api/events/{event_id}?site={site}",
            json={"rag_document_id": snapshot_id},
            headers={
                "Authorization": f"Bearer {NETWORK_GUARDIAN_TOKEN}",
                "Content-Type": "application/json",
            },
        )
        if patch_resp.status_code == 200:
            log.info(f"Guardian event {event_id} linked to RAG snapshot {snapshot_id}")
        else:
            log.warning(f"Failed to PATCH Guardian event: {patch_resp.status_code}")

    return {
        "status": "success",
        "snapshot_id": snapshot_id,
        "collection": result.get("data", {}).get("collection"),
        "chunk_count": result.get("data", {}).get("chunk_count"),
        "event_id": event_id,
    }


@app.post("/snapshot")
async def snapshot_to_rag(request: Request):
    """Snapshot a resolved Guardian event into the RAG knowledge base.

    Called by: alert-triage skill Step 9, Guardian "Snapshot to RAG" button.
    Reads the event from Guardian API, builds a narrative, ingests into RAG,
    and PATCHes the event with the rag_document_id.

    Body: { "event_id": "uuid", "site": "home" }
    """
    body = await request.json()
    event_id = body.get("event_id")
    site = body.get("site", "home")

    if not event_id:
        return {"status": "error", "message": "event_id required"}

    if not NETWORK_GUARDIAN_URL or not NETWORK_GUARDIAN_TOKEN:
        return {"status": "error", "message": "NETWORK_GUARDIAN_URL/TOKEN not configured"}

    try:
        event = await _fetch_guardian_event(event_id, site)
        if not event:
            return {"status": "error", "message": f"Event {event_id} not found"}
        return await _snapshot_event_to_rag(event, site)
    except ImportError as e:
        log.error(f"Cannot import rag-mcp: {e} — is it installed?")
        return {
            "status": "error",
            "message": "RAG MCP not available (not installed or models not cached). "
                       "Run: pip install -e mcp-servers/rag-mcp",
        }
    except Exception as e:
        log.error(f"RAG snapshot error: {e}")
        return {"status": "error", "message": f"Snapshot failed: {e}"}


@app.post("/reinvestigate")
async def reinvestigate(request: Request):
    """Operator feedback loop: re-open a Guardian case and re-trigger alert-triage.

    Called when the triage board marks a case ``needs_more_context`` (Need More).

    Body: {
      "event_id": "uuid",
      "site": "home",
      "expert_feedback": "optional free text from operator"
    }
    """
    body = await request.json()
    event_id = body.get("event_id")
    site = body.get("site", "home")
    expert_feedback = (body.get("expert_feedback") or "").strip()

    if not event_id:
        return {"status": "error", "message": "event_id required"}
    if not NETWORK_GUARDIAN_URL or not NETWORK_GUARDIAN_TOKEN:
        return {"status": "error", "message": "NETWORK_GUARDIAN_URL/TOKEN not configured"}
    if not (OPENCLAW_GATEWAY_URL and OPENCLAW_HOOK_TOKEN):
        return {"status": "error", "message": "OpenClaw gateway not configured"}

    event = await _fetch_guardian_event(event_id, site)
    if not event:
        return {"status": "error", "message": f"Event {event_id} not found"}

    # Re-open case so it appears under Investigating (not lost as "resolved")
    await patch_guardian_event(
        event_id,
        site,
        status="investigating",
        investigation_notes=(
            (event.get("investigation_notes") or "")
            + ("\n\n[operator:needs_more_context] " + expert_feedback if expert_feedback else
               "\n\n[operator:needs_more_context] Operator requested deeper investigation.")
        ),
    )
    # Store feedback quality on the event (status already set above)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.patch(
                f"{NETWORK_GUARDIAN_URL}/api/events/{event_id}?site={site}",
                json={
                    "expert_feedback": expert_feedback or "Operator requested more context",
                    "feedback_quality": "needs_more_context",
                },
                headers=_guardian_headers(),
            )
    except Exception as e:
        log.warning(f"Failed to store operator feedback on reinvestigate: {e}")

    alert_name = event.get("alert_name") or "ManualReinvestigate"
    summary = event.get("message") or f"Re-investigate {alert_name}"
    # Prefer device hints from message / notes
    device_name = "unknown"
    for token in (summary, event.get("investigation_notes") or ""):
        # crude: first "on <name>" or known patterns
        if " on " in token:
            tail = token.split(" on ", 1)[1]
            device_name = tail.split(":")[0].split("(")[0].strip()[:80]
            break

    device_info = await lookup_device(device_name if device_name != "unknown" else "pfsense")
    # Build a follow-up prompt (facts only + prior notes + operator ask)
    parts = [
        f"OPERATOR FOLLOW-UP — needs more context",
        f"Guardian event id: {event_id}",
        f"Alert name: {alert_name}",
        f"Device: {device_info.get('name')} ({device_info.get('ip')})",
        f"Prior root_cause: {event.get('root_cause') or 'n/a'}",
        f"Prior message: {summary}",
        "",
        "PRIOR INVESTIGATION NOTES:",
        event.get("investigation_notes") or "(none)",
        "",
        "OPERATOR REQUEST:",
        expert_feedback or "Provide more diagnostic depth. The prior conclusion was too shallow.",
        "",
        "INSTRUCTIONS:",
        "1. You are the Border brain. First tool call: n2n_route(target_hint=\"alert-triage\").",
        "2. Do not restate the shallow 'chronic interference, no action' answer without NEW evidence.",
        "3. Gather deeper data: radio channel/power/width if available, client counts per band,",
        "   neighboring AP overlap, time-series retries, and whether 5 GHz capacity can absorb load.",
        "4. Update the SAME Guardian event via PATCH (do not open a duplicate case).",
        "5. Discord + RAG snapshot per alert-triage skill when complete.",
        "6. If still non-actionable, say exactly what config change would fix it (channel, width,",
        "   band steering, min RSSI) even if human must approve.",
    ]
    message = "\n".join(parts)

    try:
        payload = {
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "fingerprint": event.get("alert_fingerprint") or f"reinvest-{event_id[:8]}",
                    "labels": {
                        "alertname": alert_name,
                        "instance": device_info.get("ip") or device_info.get("name") or "unknown",
                        "severity": "warning",
                        "device_name": device_info.get("name"),
                        "device_ip": device_info.get("ip"),
                        "device_role": device_info.get("role"),
                        "device_platform": device_info.get("platform"),
                    },
                    "annotations": {
                        "summary": f"Operator reinvestigate: {summary[:120]}",
                        "description": expert_feedback or "needs_more_context",
                        "investigation_prompt": message,
                        "guardian_event_id": event_id,
                    },
                }
            ],
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{OPENCLAW_GATEWAY_URL}/hooks/alert",
                json=payload,
                headers={
                    "Authorization": f"Bearer {OPENCLAW_HOOK_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code not in (200, 202):
                return {
                    "status": "error",
                    "message": f"gateway {resp.status_code}: {resp.text[:200]}",
                    "event_id": event_id,
                }
        metrics.investigations_triggered_total += 1
        log.info(f"Reinvestigate triggered for event {event_id} ({alert_name})")
        return {
            "status": "accepted",
            "event_id": event_id,
            "message": "Case reopened as investigating; alert-triage re-triggered",
        }
    except Exception as e:
        log.error(f"Reinvestigate failed: {e}")
        return {"status": "error", "message": str(e), "event_id": event_id}


@app.post("/snapshot/backfill")
async def snapshot_backfill(request: Request):
    """Stage 7 helper: snapshot recent resolved Guardian events missing rag_document_id.

    Body (optional): { "site": "home", "limit": 30, "status": "resolved" }
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    site = (body or {}).get("site", "home")
    limit = min(int((body or {}).get("limit") or 30), 100)
    status = (body or {}).get("status", "resolved")

    if not NETWORK_GUARDIAN_URL or not NETWORK_GUARDIAN_TOKEN:
        return {"status": "error", "message": "NETWORK_GUARDIAN_URL/TOKEN not configured"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{NETWORK_GUARDIAN_URL}/api/events?site={site}&limit={limit}&status={status}",
            headers={"Authorization": f"Bearer {NETWORK_GUARDIAN_TOKEN}"},
        )
        if resp.status_code != 200:
            return {"status": "error", "message": f"Guardian API {resp.status_code}"}
        events = resp.json().get("events") or []

    results = []
    for event in events:
        if event.get("rag_document_id"):
            results.append({"event_id": event.get("id"), "status": "skipped", "reason": "already linked"})
            continue
        if not (event.get("investigation_notes") or event.get("root_cause")):
            results.append({"event_id": event.get("id"), "status": "skipped", "reason": "no notes"})
            continue
        try:
            r = await _snapshot_event_to_rag(event, site)
            results.append(r)
        except Exception as e:
            results.append({"event_id": event.get("id"), "status": "error", "message": str(e)})

    ok = sum(1 for r in results if r.get("status") == "success")
    return {"status": "done", "snapshotted": ok, "total": len(results), "results": results}


# ---------------------------------------------------------------------------
# Nautobot webhook → intent-reconcile proposal
# ---------------------------------------------------------------------------


def _verify_nautobot_signature(raw_body: bytes, signature: str) -> bool:
    """Nautobot signs the raw body with HMAC-SHA512 (X-Hook-Signature header)."""
    if not NAUTOBOT_WEBHOOK_SECRET:
        # No secret configured: refuse rather than trust an unsigned change.
        return False
    if not signature:
        return False
    expected = hmac.new(
        NAUTOBOT_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


@app.post("/nautobot-webhook")
async def nautobot_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive a Nautobot change webhook, gate it, and propose a reconcile.

    The webhook may fire for ALL interface changes; we only propose for allowed
    models on allowed device roles. Nothing is applied here — the agent posts a
    proposal to Discord and waits for explicit approval.
    """
    raw = await request.body()
    sig = request.headers.get("X-Hook-Signature", "")

    if not RECONCILE_ENABLED:
        return {"status": "disabled"}

    if not _verify_nautobot_signature(raw, sig):
        log.warning("Nautobot webhook rejected: bad or missing HMAC signature")
        return {"status": "rejected", "reason": "signature"}

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        log.error(f"Nautobot webhook parse error: {e}")
        return {"status": "error", "message": "invalid json"}

    model = str(payload.get("model", "")).lower()
    event = str(payload.get("event", "")).lower()  # created | updated | deleted
    if model not in RECONCILE_ALLOWED_MODELS:
        log.info(f"Nautobot webhook ignored: model '{model}' not in scope")
        return {"status": "ignored", "reason": "model-out-of-scope"}

    background_tasks.add_task(process_nautobot_change, payload, model, event)
    return {"status": "accepted", "model": model, "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat()}


def _role_allowed(role: str) -> bool:
    role = (role or "").lower()
    return any(r in role for r in RECONCILE_ALLOWED_ROLES)


async def process_nautobot_change(payload: dict, model: str, event: str):
    """Resolve the device, gate by role, and hand a reconcile proposal to NetClaw."""
    data = payload.get("data") or {}
    snapshots = payload.get("snapshots") or {}

    # Extract the device name from the interface object.
    dev = data.get("device") or {}
    device_name = dev.get("name") if isinstance(dev, dict) else (dev or "")
    if not device_name:
        log.warning("Nautobot webhook: could not resolve device name — skipping")
        return

    device_info = await lookup_device(device_name)
    if not _role_allowed(device_info.get("role", "")):
        log.info(f"Nautobot change on {device_name} (role="
                 f"{device_info.get('role')}) not in allowed roles — skipping")
        return

    prompt = build_reconcile_prompt(model, event, data, snapshots, device_info)

    if OPENCLAW_GATEWAY_URL and OPENCLAW_HOOK_TOKEN:
        try:
            body = {
                "event": event,
                "model": model,
                "device": device_info,
                "annotations": {"reconcile_prompt": prompt},
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{OPENCLAW_GATEWAY_URL}/hooks/reconcile",
                    json=body,
                    headers={"Authorization": f"Bearer {OPENCLAW_HOOK_TOKEN}",
                             "Content-Type": "application/json"},
                )
                if resp.status_code in (200, 202):
                    log.info(f"Reconcile proposal triggered: {model} {event} on {device_name}")
                else:
                    log.error(f"Gateway /hooks/reconcile returned {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log.error(f"Failed to trigger reconcile: {e}")
    else:
        log.warning("No OpenClaw gateway configured — logging reconcile prompt")
        log.info(f"RECONCILE PROMPT:\n{prompt}")


def build_reconcile_prompt(model: str, event: str, data: dict,
                           snapshots: dict, device_info: dict) -> str:
    iface = data.get("name", "?")
    pre = (snapshots.get("prechange") or {})
    post = (snapshots.get("postchange") or {})
    parts = [
        f"NAUTOBOT INTENT CHANGE — {model} {event}",
        f"Device: {device_info['name']} ({device_info['ip']}) | "
        f"role={device_info['role']} platform={device_info['platform']}",
        f"Interface: {iface}",
        "",
        "Webhook snapshot (TRIGGER CONTEXT ONLY — not the comparison):",
        "Prechange (Nautobot):",
        json.dumps(pre, indent=2, default=str)[:1200] if pre else "  (none — created)",
        "",
        "Postchange (Nautobot):",
        json.dumps(post, indent=2, default=str)[:1200] if post else "  (none — deleted)",
        "",
        "INSTRUCTIONS — follow the intent-reconcile skill:",
        "1. SCOPE GUARD: you may only reconcile DEVICE INTERFACE changes on "
        "switches. If this is not an interface change on a switch, STOP and post "
        "a one-line note that it is out of scope. Never touch firewalls.",
        "2. Do NOT diff prechange vs postchange. Read the INTENDED state from "
        "Nautobot (nautobot-sot) AND the ACTUAL live state from the device "
        "(pyATS: 'show running-config interface <if>' and 'show interfaces <if>'), "
        "then compare intent vs actual across ALL fields: enabled/admin-state, "
        "mode, access VLAN, trunk allowed VLANs, MTU, description.",
        "3. ADMIN STATE IS A FIRST-CLASS CHECK: if Nautobot has enabled=false but "
        "the port is administratively UP on the device (or vice-versa), that is "
        "drift — propose the shutdown/no shutdown to match intent. A no-op is only "
        "valid when the device already matches Nautobot on every field; say what "
        "you compared. Then RENDER the exact config and dry-run it. Do NOT apply.",
        "4. Write the pending change and post a proposal to the Discord alerts "
        "channel asking for `approve <id>` or `deny <id>`.",
        "5. Apply ONLY after an explicit human approval arrives, using the "
        "pyats-config-mgmt baseline→apply→verify→rollback workflow.",
    ]
    if RECONCILE_CHANNEL_ID:
        parts.append(f"6. Post the proposal (and later the result) to Discord "
                     f"channel {RECONCILE_CHANNEL_ID} via `openclaw message send`.")
    return "\n".join(parts)


@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive Alertmanager webhook and trigger investigation."""
    body = await request.json()

    try:
        payload = AlertmanagerPayload(**body)
    except Exception as e:
        log.error(f"Failed to parse Alertmanager payload: {e}")
        return {"status": "error", "message": str(e)}

    log.info(
        f"Received webhook: status={payload.status}, "
        f"alerts={len(payload.alerts)}, receiver={payload.receiver}"
    )

    for alert in payload.alerts:
        log.info(
            f"  Alert: {alert.labels.alertname} | "
            f"instance={alert.labels.instance} | "
            f"severity={alert.labels.severity} | "
            f"status={alert.status}"
        )
        # Track metrics
        metrics.alerts_received_total += 1
        if alert.status == "firing":
            metrics.alerts_firing_total += 1
        else:
            metrics.alerts_resolved_total += 1
        # Process each alert in the background so we return 200 quickly
        background_tasks.add_task(process_alert, alert)

    return {
        "status": "accepted",
        "alerts_received": len(payload.alerts),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def process_alert(alert: Alert):
    """Enrich alert with device info and maybe trigger NetClaw investigation.

    Investigation is gated by policy (investigate label / deny list / severity),
    fingerprint dedup, per-minute rate limit, and a concurrency semaphore so a
    high-cardinality alert never opens dozens of OpenClaw hook sessions (each
    of which eagerly spawns the full MCP set).
    """
    instance = alert.labels.instance
    if not instance:
        # Try to extract hostname from other labels
        extra = alert.labels.model_extra or {}
        instance = (
            _label_get(alert.labels, "device_name")
            or extra.get("device_name", "")
            or extra.get("host", "")
            or _label_get(alert.labels, "host")
        )

    if not instance:
        log.warning(f"Alert {alert.labels.alertname} has no instance/device_name label — skipping")
        return

    device_info = await lookup_device(instance)
    log.info(f"  Device resolved: {device_info['name']} → {device_info['ip']} (source: {device_info['source']})")

    # Resolved → diary only (complete open case); never start a new investigation.
    if alert.status == "resolved":
        await complete_guardian_event_resolved(alert, device_info)
        return

    # Check if this is a known noisy IoT device generating excessive blocks.
    # If so, log as INFO to Guardian and skip full investigation + Discord.
    if _is_noisy_iot_suppressed(alert, device_info):
        log.info(f"  Suppressed (known noisy IoT): {alert.labels.alertname} for {device_info['ip']}")
        metrics.investigations_suppressed_total += 1
        await post_guardian_event(alert, device_info, status="resolved")
        return

    allowed, policy_reason = should_auto_investigate(alert)
    if not allowed:
        log.info(
            f"  Investigation skipped ({policy_reason}): "
            f"{alert.labels.alertname} fp={alert.fingerprint[:12] if alert.fingerprint else '-'}"
        )
        metrics.investigations_suppressed_policy_total += 1
        metrics.investigations_suppressed_total += 1
        # Still record a light diary entry for visibility without hooking OpenClaw
        await post_guardian_event(alert, device_info, status="logged")
        # Optional Discord for non-suppressed names at info severity is intentional no-op
        if (
            alert.labels.alertname not in DISCORD_SUPPRESS_ALERTS
            and (alert.labels.severity or "").lower() in ("warning", "critical")
            and policy_reason.startswith("deny_list")
        ):
            # Deny-listed but still human-visible once (optional) — skip by default
            pass
        return

    admitted, admit_reason = await admit_investigation(alert.fingerprint or instance)
    if not admitted:
        log.warning(
            f"  Investigation admission denied ({admit_reason}): "
            f"{alert.labels.alertname} fp={alert.fingerprint[:12] if alert.fingerprint else '-'} "
            f"— diary only (prevents MCP fan-out)"
        )
        await post_guardian_event(alert, device_info, status="logged")
        return

    try:
        # Scope the runtime skills directory to this alert before investigation.
        scope_gen = await scope_skills_for_alert(alert, device_info)

        await trigger_netclaw(alert, device_info)

        # After the fresh alert session has read the scoped dir, restore the full
        # catalog so interactive sessions aren't left with the reduced set.
        await restore_skills_after_trigger(scope_gen)
    finally:
        release_investigation()


def _is_noisy_iot_suppressed(alert: Alert, device_info: dict) -> bool:
    """Check if this alert should be suppressed for a known noisy IoT device."""
    if not NOISY_IOT_HOSTS:
        return False

    # Only suppress "excessive blocks" type alerts, not other alert types
    alert_lower = alert.labels.alertname.lower()
    if "excessive" not in alert_lower and "internal" not in alert_lower:
        return False

    # Check if the affected IP is in the noisy list
    # The IP might be in the instance label, summary, or description
    for noisy_ip in NOISY_IOT_HOSTS:
        if noisy_ip in (device_info.get("ip", "") or ""):
            return True
        if noisy_ip in (alert.annotations.summary or ""):
            return True
        if noisy_ip in (alert.annotations.description or ""):
            return True
        if noisy_ip in (alert.labels.instance or ""):
            return True

    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    log.info(f"Starting NetClaw Alert Receiver on {HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level=LOG_LEVEL.lower())
