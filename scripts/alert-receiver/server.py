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
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks
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

# Serialize scoping so concurrent alerts never leave the shared skills dir in a
# partially-written state. Created lazily on the running event loop.
_scope_lock: Optional["asyncio.Lock"] = None

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("alert-receiver")

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


async def lookup_device_nautobot(hostname: str) -> Optional[dict]:
    """Query Nautobot for device info by hostname."""
    if not NAUTOBOT_URL or not NAUTOBOT_TOKEN:
        return None

    try:
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            resp = await client.get(
                f"{NAUTOBOT_URL}/api/dcim/devices/",
                params={"name": hostname},
                headers={
                    "Authorization": f"Token {NAUTOBOT_TOKEN}",
                    "Accept": "application/json",
                },
            )
            if resp.status_code != 200:
                log.warning(f"Nautobot returned {resp.status_code} for device '{hostname}'")
                return None

            data = resp.json()
            results = data.get("results", [])
            if not results:
                log.info(f"Device '{hostname}' not found in Nautobot")
                return None

            device = results[0]
            primary_ip = device.get("primary_ip", {})
            return {
                "name": device.get("name", hostname),
                "ip": primary_ip.get("address", "").split("/")[0] if primary_ip else "",
                "platform": device.get("platform", {}).get("name", "") if device.get("platform") else "",
                "role": device.get("role", {}).get("name", "") if device.get("role") else "",
                "site": device.get("location", {}).get("name", "") if device.get("location") else "",
                "status": device.get("status", {}).get("value", "") if isinstance(device.get("status"), dict) else str(device.get("status", "")),
                "source": "nautobot",
            }
    except Exception as e:
        log.warning(f"Nautobot lookup failed for '{hostname}': {e}")
        return None


async def lookup_device_inventory(hostname: str) -> Optional[dict]:
    """Fallback lookup from local inventory.yaml."""
    if not INVENTORY_FILE.exists():
        return None

    try:
        import yaml
        inventory = yaml.safe_load(INVENTORY_FILE.read_text()) or {}
        devices = inventory.get("devices", {})

        # Try direct hostname match first
        if hostname in devices:
            dev = devices[hostname]
            return {
                "name": hostname,
                "ip": dev.get("ip", ""),
                "platform": dev.get("platform", ""),
                "role": dev.get("role", ""),
                "site": dev.get("site", ""),
                "status": "active",
                "source": "local-inventory",
            }

        # Try matching by IP address
        for name, dev in devices.items():
            if dev.get("ip") == hostname:
                return {
                    "name": name,
                    "ip": dev.get("ip", ""),
                    "platform": dev.get("platform", ""),
                    "role": dev.get("role", ""),
                    "site": dev.get("site", ""),
                    "status": "active",
                    "source": "local-inventory",
                }
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


async def scope_skills_for_alert(alert: Alert, device_info: dict) -> None:
    """Scope the runtime skills directory to the alert-relevant subset.

    Runs the skill selector (scripts/skill-selector/select_skills.py) as a
    subprocess with --apply. Fail-open: any error leaves the existing catalog in
    place so the investigation still has its skills. Serialized via a lock so
    concurrent alerts don't corrupt the shared directory.
    """
    if not SKILL_SCOPING_ENABLED:
        return
    if alert.status != "firing":
        return  # resolved alerts just post an all-clear; no scoping needed

    global _scope_lock
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
                return

            if proc.returncode != 0:
                log.warning(
                    f"Skill scoping failed (exit {proc.returncode}): "
                    f"{stderr.decode(errors='replace')[:200]} — proceeding with existing catalog"
                )
                return

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
        except FileNotFoundError:
            log.warning(
                f"Skill selector not found at {SKILL_SELECTOR_SCRIPT} — "
                "proceeding with existing catalog"
            )
        except Exception as e:
            log.warning(f"Skill scoping error: {e} — proceeding with existing catalog")


async def trigger_netclaw(alert: Alert, device_info: dict):
    """Send enriched alert to OpenClaw gateway to trigger investigation."""
    message = build_investigation_prompt(alert, device_info)

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
                else:
                    log.error(f"OpenClaw gateway returned {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log.error(f"Failed to trigger NetClaw: {e}")
    else:
        # No gateway configured — log the investigation prompt for manual pickup
        log.warning("No OpenClaw gateway configured — logging investigation prompt")
        log.info(f"INVESTIGATION PROMPT:\n{message}")

    # Post to Discord if configured
    if DISCORD_WEBHOOK_URL and alert.status == "firing":
        await post_discord(alert, device_info)


def build_investigation_prompt(alert: Alert, device_info: dict) -> str:
    """Build the investigation prompt NetClaw will receive."""
    parts = [
        f"ALERT RECEIVED — {alert.labels.alertname}",
        f"Status: {alert.status}",
        f"Severity: {alert.labels.severity}",
        f"Device: {device_info['name']} ({device_info['ip']})",
        f"Role: {device_info['role']} | Platform: {device_info['platform']} | Site: {device_info['site']}",
        f"Summary: {alert.annotations.summary}",
    ]

    if alert.annotations.description:
        parts.append(f"Description: {alert.annotations.description}")

    parts.append("")
    parts.append("INSTRUCTIONS:")
    parts.append(f"1. The device '{device_info['name']}' at IP {device_info['ip']} has triggered alert '{alert.labels.alertname}'.")

    if device_info["platform"] == "pfsense":
        parts.append("2. Use the pfSense MCP tools to investigate (get system status, interfaces, logs).")
    elif device_info["platform"] in ("ios", "iosxe", "nxos"):
        parts.append("2. Use pyATS to run diagnostic commands on this device.")
    elif device_info["platform"] == "proxmox":
        parts.append("2. Use the Proxmox MCP tools to check VM/container and node health.")
    else:
        parts.append("2. Use available tools (SNMP, SSH, MCP) to investigate the device.")

    parts.append("3. Query Prometheus for recent metric history if relevant.")
    parts.append("4. Produce a triage report: what's wrong, likely cause, and recommended action.")
    parts.append("5. Do NOT remediate without explicit human approval.")

    if alert.status == "resolved":
        parts = [
            f"ALERT RESOLVED — {alert.labels.alertname}",
            f"Device: {device_info['name']} ({device_info['ip']})",
            "The alert has cleared. Post a brief all-clear confirmation.",
        ]

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
    except Exception as e:
        log.warning(f"Discord post failed: {e}")


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
        # Process each alert in the background so we return 200 quickly
        background_tasks.add_task(process_alert, alert)

    return {
        "status": "accepted",
        "alerts_received": len(payload.alerts),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def process_alert(alert: Alert):
    """Enrich alert with device info and trigger NetClaw."""
    instance = alert.labels.instance
    if not instance:
        # Try to extract hostname from other labels
        instance = alert.labels.model_extra.get("device_name", "") or alert.labels.model_extra.get("host", "")

    if not instance:
        log.warning(f"Alert {alert.labels.alertname} has no instance/device_name label — skipping")
        return

    device_info = await lookup_device(instance)
    log.info(f"  Device resolved: {device_info['name']} → {device_info['ip']} (source: {device_info['source']})")

    # Scope the runtime skills directory to this alert before investigation.
    await scope_skills_for_alert(alert, device_info)

    await trigger_netclaw(alert, device_info)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    log.info(f"Starting NetClaw Alert Receiver on {HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level=LOG_LEVEL.lower())
