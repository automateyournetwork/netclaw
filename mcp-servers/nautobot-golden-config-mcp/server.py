"""Nautobot Golden Config MCP Server — high-level config lifecycle tools.

Provides one-call tools for the golden config pipeline: generate intended,
backup, compliance, remediate, and full pipeline. Reduces LLM context burn
from 10+ API calls to 1-3 tool calls.

Environment Variables:
    NAUTOBOT_URL          — Nautobot instance URL (required)
    NAUTOBOT_TOKEN        — Nautobot API token (required)
    NAUTOBOT_TIMEOUT      — API request timeout in seconds (default: 60)
    NAUTOBOT_VERIFY_SSL   — Verify SSL certificates (default: false)
    GOLDEN_CONFIG_POLL_INTERVAL — Seconds between job status polls (default: 5)
    GOLDEN_CONFIG_JOB_TIMEOUT   — Max seconds to wait for job completion (default: 300)
    ITSM_ENABLED          — Require ServiceNow CR for write ops (default: false)
    ITSM_LAB_MODE         — Bypass ITSM in lab mode (default: true)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

from nautobot_client import NautobotClient, NautobotError
from job_runner import (
    run_job_and_wait,
    JOB_INTENDED,
    JOB_BACKUP,
    JOB_COMPLIANCE,
    JOB_DEPLOY,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("nautobot-golden-config-mcp")

# ── Startup validation ───────────────────────────────────────────────

for var in ("NAUTOBOT_URL", "NAUTOBOT_TOKEN"):
    if not os.environ.get(var):
        logger.error(f"Required environment variable {var} is not set.")
        sys.exit(1)

mcp = FastMCP("nautobot-golden-config-mcp")
client = NautobotClient()

ITSM_ENABLED = os.environ.get("ITSM_ENABLED", "false").lower() == "true"
ITSM_LAB_MODE = os.environ.get("ITSM_LAB_MODE", "true").lower() == "true"


def _check_itsm(cr_number: Optional[str]) -> Optional[str]:
    if ITSM_ENABLED and not ITSM_LAB_MODE:
        if not cr_number:
            return "Write operation blocked: ITSM is enabled. Provide a cr_number parameter."
    return None


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


async def _resolve_device_ids(device: Optional[str]) -> Optional[list[str]]:
    """Resolve device name(s) to UUIDs for job filtering. Returns None if no filter."""
    if not device:
        return None
    # Support comma-separated device names
    names = [n.strip() for n in device.split(",")]
    ids = []
    for name in names:
        query = f'{{ devices(name: "{_esc(name)}") {{ id }} }}'
        data = await client.graphql(query)
        devices_list = data.get("devices", [])
        if devices_list:
            ids.append(devices_list[0]["id"])
        else:
            raise NautobotError(f"Device '{name}' not found in Nautobot.")
    return ids


# ═══════════════════════════════════════════════════════════════════════
# PHASE 2: CONFIG LIFECYCLE TOOLS (Core Pipeline)
# ═══════════════════════════════════════════════════════════════════════


@mcp.tool()
async def golden_config_generate_intended(device: Optional[str] = None) -> str:
    """Generate intended config for device(s) from Jinja templates + SoT data.

    Triggers Nautobot's IntendedJob which renders templates using config contexts
    and the SoT aggregation query. Waits for completion.

    Args:
        device: Device name (e.g. 'RR1') or comma-separated names. If omitted, runs for all devices in scope.
    """
    logger.info(f"golden_config_generate_intended device={device}")
    try:
        device_ids = await _resolve_device_ids(device)
        data = {}
        if device_ids:
            data["device"] = device_ids
        result = await run_job_and_wait(client, JOB_INTENDED, data)
        result["operation"] = "generate_intended"
        result["device_filter"] = device
        return json.dumps(result, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def golden_config_backup(device: Optional[str] = None) -> str:
    """Pull running config backup from device(s) into Nautobot.

    Triggers Nautobot's BackupJob which connects to devices and stores their
    running configuration. Waits for completion.

    Args:
        device: Device name or comma-separated names. If omitted, backs up all devices in scope.
    """
    logger.info(f"golden_config_backup device={device}")
    try:
        device_ids = await _resolve_device_ids(device)
        data = {}
        if device_ids:
            data["device"] = device_ids
        result = await run_job_and_wait(client, JOB_BACKUP, data)
        result["operation"] = "backup"
        result["device_filter"] = device
        return json.dumps(result, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def golden_config_compliance(device: Optional[str] = None) -> str:
    """Run compliance check — compare intended vs backup config for device(s).

    Triggers Nautobot's ComplianceJob which diffs intended against backup per
    compliance feature/rule. Waits for completion, then returns summary.

    Args:
        device: Device name or comma-separated names. If omitted, checks all devices in scope.
    """
    logger.info(f"golden_config_compliance device={device}")
    try:
        device_ids = await _resolve_device_ids(device)
        data = {}
        if device_ids:
            data["device"] = device_ids
        result = await run_job_and_wait(client, JOB_COMPLIANCE, data)

        # If completed, fetch compliance summary
        if result.get("status") == "completed" and device:
            try:
                filt = f'device: "{_esc(device.split(",")[0].strip())}"' if "," not in device else ""
                if filt:
                    query = f"""{{ config_compliances({filt}) {{
                        device {{ name }} rule {{ feature {{ name }} }} compliance missing extra
                    }} }}"""
                    comp_data = await client.graphql(query)
                    records = comp_data.get("config_compliances", [])
                    summary = []
                    for r in records:
                        summary.append({
                            "device": r.get("device", {}).get("name"),
                            "feature": r.get("rule", {}).get("feature", {}).get("name"),
                            "compliant": r.get("compliance"),
                            "missing": bool(r.get("missing")),
                            "extra": bool(r.get("extra")),
                        })
                    result["compliance_summary"] = summary
            except Exception:
                pass  # Non-critical enrichment

        result["operation"] = "compliance"
        result["device_filter"] = device
        return json.dumps(result, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def golden_config_full_pipeline(device: Optional[str] = None) -> str:
    """Run the full config pipeline: intended → backup → compliance in sequence.

    This is the one-call equivalent of running all three jobs. Returns the final
    compliance status after all steps complete.

    Args:
        device: Device name or comma-separated names. If omitted, runs for all devices in scope.
    """
    logger.info(f"golden_config_full_pipeline device={device}")
    results = {"operation": "full_pipeline", "device_filter": device, "steps": {}}

    try:
        device_ids = await _resolve_device_ids(device)
        data = {}
        if device_ids:
            data["device"] = device_ids

        # Step 1: Generate intended
        intended = await run_job_and_wait(client, JOB_INTENDED, data)
        results["steps"]["intended"] = intended.get("status")
        if intended.get("status") == "failed":
            results["error"] = "Intended job failed"
            results["steps"]["intended_detail"] = intended
            return json.dumps(results, indent=2, default=str)

        # Step 2: Backup
        backup = await run_job_and_wait(client, JOB_BACKUP, data)
        results["steps"]["backup"] = backup.get("status")
        if backup.get("status") == "failed":
            results["error"] = "Backup job failed"
            results["steps"]["backup_detail"] = backup
            return json.dumps(results, indent=2, default=str)

        # Step 3: Compliance
        compliance = await run_job_and_wait(client, JOB_COMPLIANCE, data)
        results["steps"]["compliance"] = compliance.get("status")

        # Fetch compliance summary
        if compliance.get("status") == "completed" and device and "," not in device:
            try:
                query = f"""{{ config_compliances(device: "{_esc(device.strip())}") {{
                    device {{ name }} rule {{ feature {{ name }} }} compliance missing extra
                }} }}"""
                comp_data = await client.graphql(query)
                records = comp_data.get("config_compliances", [])
                results["compliance_summary"] = [
                    {
                        "device": r.get("device", {}).get("name"),
                        "feature": r.get("rule", {}).get("feature", {}).get("name"),
                        "compliant": r.get("compliance"),
                    }
                    for r in records
                ]
            except Exception:
                pass

        results["status"] = "completed" if all(
            s == "completed" for s in results["steps"].values()
        ) else "partial"
        return json.dumps(results, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def golden_config_remediate(
    device: str,
    cr_number: Optional[str] = None,
) -> str:
    """Push intended config to a non-compliant device to fix drift. ITSM-gated.

    Deploys the intended configuration to the device to bring it into compliance.
    This is a write operation that modifies device configuration.

    Args:
        device: Device name (required — remediation targets a specific device)
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"golden_config_remediate device={device} cr={cr_number}")
    try:
        device_ids = await _resolve_device_ids(device)
        if not device_ids:
            return json.dumps({"error": f"Device '{device}' not found"})

        # Check if there are config plans to deploy, or trigger deploy directly
        # First check compliance state
        query = f"""{{ config_compliances(device: "{_esc(device)}") {{
            compliance rule {{ feature {{ name }} }}
        }} }}"""
        comp_data = await client.graphql(query)
        records = comp_data.get("config_compliances", [])
        non_compliant = [r for r in records if not r.get("compliance")]

        if not non_compliant:
            return json.dumps({
                "status": "already_compliant",
                "device": device,
                "message": "Device is already compliant. No remediation needed.",
            })

        # Trigger deploy job
        data = {"device": device_ids}
        result = await run_job_and_wait(client, JOB_DEPLOY, data)
        result["operation"] = "remediate"
        result["device"] = device
        result["non_compliant_features"] = [
            r.get("rule", {}).get("feature", {}).get("name") for r in non_compliant
        ]
        return json.dumps(result, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════
# CONFIG INSPECTION TOOLS (Phase 3 preview — essential for usability)
# ═══════════════════════════════════════════════════════════════════════


@mcp.tool()
async def golden_config_get_intended(device: str) -> str:
    """Get the rendered intended config for a device.

    Returns the full intended configuration text as generated by golden config
    templates + SoT data.

    Args:
        device: Device name (e.g. 'RR1')
    """
    logger.info(f"golden_config_get_intended device={device}")
    try:
        resp = await client.rest_get(
            "plugins/golden-config/golden-config", {"device": device}
        )
        results = resp.get("results", [])
        if not results:
            return json.dumps({"device": device, "intended_config": None,
                             "message": "No golden config record. Run golden_config_generate_intended first."})
        record = results[0]
        return json.dumps({
            "device": device,
            "intended_config": record.get("intended_config"),
            "last_success": record.get("intended_last_success_date"),
        }, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def golden_config_get_backup(device: str) -> str:
    """Get the latest backup config for a device.

    Returns the running configuration as last pulled from the device.

    Args:
        device: Device name (e.g. 'RR1')
    """
    logger.info(f"golden_config_get_backup device={device}")
    try:
        resp = await client.rest_get(
            "plugins/golden-config/golden-config", {"device": device}
        )
        results = resp.get("results", [])
        if not results:
            return json.dumps({"device": device, "backup_config": None,
                             "message": "No golden config record. Run golden_config_backup first."})
        record = results[0]
        return json.dumps({
            "device": device,
            "backup_config": record.get("backup_config"),
            "last_success": record.get("backup_last_success_date"),
        }, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def golden_config_get_compliance_diff(device: str) -> str:
    """Get the compliance diff for a device — what's missing and what's extra per feature.

    Returns a human-readable diff showing which config lines are missing from the
    device (should be there but aren't) and which are extra (on device but not intended).

    Args:
        device: Device name (e.g. 'RR1')
    """
    logger.info(f"golden_config_get_compliance_diff device={device}")
    try:
        query = f"""{{ config_compliances(device: "{_esc(device)}") {{
            device {{ name }}
            rule {{ feature {{ name }} platform {{ name }} }}
            compliance actual intended missing extra ordered
        }} }}"""
        data = await client.graphql(query)
        records = data.get("config_compliances", [])
        if not records:
            return json.dumps({"device": device, "message": "No compliance data. Run golden_config_compliance first."})

        diffs = []
        for r in records:
            feature = r.get("rule", {}).get("feature", {}).get("name", "unknown")
            entry = {
                "feature": feature,
                "compliant": r.get("compliance"),
            }
            if not r.get("compliance"):
                entry["missing"] = r.get("missing") or ""
                entry["extra"] = r.get("extra") or ""
            diffs.append(entry)

        compliant_count = sum(1 for d in diffs if d["compliant"])
        return json.dumps({
            "device": device,
            "total_features": len(diffs),
            "compliant": compliant_count,
            "non_compliant": len(diffs) - compliant_count,
            "diffs": diffs,
        }, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def golden_config_get_compliance_summary(
    device: Optional[str] = None,
    feature: Optional[str] = None,
) -> str:
    """Get compliance status across devices and features.

    Returns a table showing device, feature, compliant status, and last run time.

    Args:
        device: Filter by device name (optional)
        feature: Filter by compliance feature name (optional)
    """
    logger.info(f"golden_config_get_compliance_summary device={device} feature={feature}")
    try:
        filters = []
        if device:
            filters.append(f'device: "{_esc(device)}"')
        filt_str = f"({', '.join(filters)})" if filters else ""

        query = f"""{{ config_compliances{filt_str} {{
            device {{ name }}
            rule {{ feature {{ name }} }}
            compliance
        }} }}"""
        data = await client.graphql(query)
        records = data.get("config_compliances", [])

        # Filter by feature if specified
        if feature:
            records = [r for r in records if r.get("rule", {}).get("feature", {}).get("name") == feature]

        summary = []
        for r in records:
            summary.append({
                "device": r.get("device", {}).get("name"),
                "feature": r.get("rule", {}).get("feature", {}).get("name"),
                "compliant": r.get("compliance"),
            })

        compliant_count = sum(1 for s in summary if s["compliant"])
        return json.dumps({
            "total": len(summary),
            "compliant": compliant_count,
            "non_compliant": len(summary) - compliant_count,
            "summary": summary,
        }, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════
# PHASE 4: TEMPLATE & CONTEXT TOOLS
# ═══════════════════════════════════════════════════════════════════════


@mcp.tool()
async def golden_config_get_templates(device: Optional[str] = None) -> str:
    """List golden config templates that apply to a device (based on platform/role).

    If device is specified, shows which template path resolves for that device.
    If omitted, returns the golden config settings showing template path patterns.

    Args:
        device: Device name (optional) — resolves the template path for this device
    """
    logger.info(f"golden_config_get_templates device={device}")
    try:
        # Get GC settings for template path pattern
        settings = await client.rest_get("plugins/golden-config/golden-config-settings")
        results = settings.get("results", [])
        if not results:
            return json.dumps({"error": "No golden config settings found. Configure golden config first."})

        setting = results[0]
        jinja_path = setting.get("jinja_path_template", "")
        jinja_repo = setting.get("jinja_repository")

        info = {
            "jinja_path_template": jinja_path,
            "jinja_repository": jinja_repo.get("name") if isinstance(jinja_repo, dict) else jinja_repo,
        }

        if device:
            # Resolve what template path this device would use
            query = f"""{{ devices(name: "{_esc(device)}") {{
                name platform {{ name network_driver }} role {{ name }}
                location {{ name }}
            }} }}"""
            data = await client.graphql(query)
            devices_list = data.get("devices", [])
            if not devices_list:
                return json.dumps({"error": f"Device '{device}' not found"})
            dev = devices_list[0]
            info["device"] = device
            info["platform"] = dev.get("platform", {}).get("name")
            info["network_driver"] = dev.get("platform", {}).get("network_driver")
            info["role"] = dev.get("role", {}).get("name")
            # Show resolved path (best effort — Jinja rendering happens server-side)
            info["resolved_path_hint"] = jinja_path.replace(
                "{{obj.platform.network_driver}}", dev.get("platform", {}).get("network_driver") or "unknown"
            ).replace(
                "{{obj.platform.name}}", dev.get("platform", {}).get("name") or "unknown"
            )

        return json.dumps(info, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def golden_config_render_preview(device: str) -> str:
    """Render a preview of what the intended config would look like for a device.

    Returns the most recently generated intended config. To get a fresh render,
    call golden_config_generate_intended first.

    Args:
        device: Device name (e.g. 'RR1')
    """
    logger.info(f"golden_config_render_preview device={device}")
    try:
        resp = await client.rest_get(
            "plugins/golden-config/golden-config", {"device": device}
        )
        results = resp.get("results", [])
        if not results or not results[0].get("intended_config"):
            return json.dumps({
                "device": device,
                "preview": None,
                "message": "No intended config available. Run golden_config_generate_intended first.",
            })
        return json.dumps({
            "device": device,
            "preview": results[0]["intended_config"],
            "generated": results[0].get("intended_last_success_date"),
        }, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def golden_config_get_device_context(device: str) -> str:
    """Get the merged config context for a device as golden config templates see it.

    Returns the full merged config context dict — all config contexts that apply
    to this device based on role, location, platform, tenant, tags.

    Args:
        device: Device name (e.g. 'RR1')
    """
    logger.info(f"golden_config_get_device_context device={device}")
    try:
        resp = await client.rest_get("dcim/devices", {"name": device})
        devices_list = resp.get("results", [])
        if not devices_list:
            return json.dumps({"error": f"Device '{device}' not found"})
        device_id = devices_list[0]["id"]
        detail = await client.rest_get(f"dcim/devices/{device_id}")
        config_context = detail.get("config_context", {})
        return json.dumps({
            "device": device,
            "config_context": config_context,
        }, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def golden_config_update_device_context(
    device: str,
    key: str,
    value: str,
    cr_number: Optional[str] = None,
) -> str:
    """Update a key in a device's config context. ITSM-gated.

    Finds the config context that applies to this device and updates the specified
    key. If the key is nested, use dot notation (e.g. 'observability.syslog_server').

    Args:
        device: Device name (e.g. 'RR1')
        key: Config context key to update (e.g. 'mgmt_vrf' or 'observability.syslog_server')
        value: New value as JSON string (e.g. '"MGMT"' or '{"host": "10.0.0.1", "port": 514}')
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"golden_config_update_device_context device={device} key={key} cr={cr_number}")
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value  # treat as plain string

    keys = key.split(".")

    try:
        # Find config contexts that apply to this device
        # Get device's role ID
        query = f"""{{ devices(name: "{_esc(device)}") {{
            id role {{ name id }}
        }} }}"""
        dev_data = await client.graphql(query)
        devices_list = dev_data.get("devices", [])
        if not devices_list:
            return json.dumps({"error": f"Device '{device}' not found"})

        dev = devices_list[0]
        role_id = dev.get("role", {}).get("id")
        top_key = keys[0]  # First segment of the dotted key path

        # Find config contexts scoped to this device's role
        ctx_resp = await client.rest_get("extras/config-contexts", {"limit": 100})
        contexts = ctx_resp.get("results", [])

        # Strategy: prefer context that already has the top-level key AND matches role
        target_ctx = None
        role_matched = []
        for ctx in contexts:
            ctx_role_ids = [r.get("id") for r in ctx.get("roles", [])]
            if role_id and role_id in ctx_role_ids:
                role_matched.append(ctx)

        # Among role-matched, prefer one with existing top_key
        for ctx in role_matched:
            if top_key in (ctx.get("data") or {}):
                target_ctx = ctx
                break
        # Fallback: first role-matched context
        if not target_ctx and role_matched:
            target_ctx = role_matched[0]
        # Fallback: any context with the top_key
        if not target_ctx:
            for ctx in contexts:
                if top_key in (ctx.get("data") or {}):
                    target_ctx = ctx
                    break
        # Fallback: first context with no role filter (global)
        if not target_ctx:
            for ctx in contexts:
                if not ctx.get("roles"):
                    target_ctx = ctx
                    break
        if not target_ctx:
            return json.dumps({"error": "No config context found for this device. Create one first."})

        # Update the key in the context data
        ctx_data = target_ctx.get("data", {})
        obj = ctx_data
        for k in keys[:-1]:
            if k not in obj:
                obj[k] = {}
            obj = obj[k]
        obj[keys[-1]] = parsed_value

        # PATCH the config context
        await client.rest_patch(
            f"extras/config-contexts/{target_ctx['id']}",
            {"data": ctx_data},
        )

        return json.dumps({
            "updated": True,
            "config_context": target_ctx.get("name"),
            "key": key,
            "value": parsed_value,
            "device": device,
        }, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def golden_config_update_template(
    path: str,
    content: str,
    commit_message: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Update a golden config Jinja template file. ITSM-gated.

    This updates the template content. The actual commit to git should be done
    via the GitHub MCP server or by syncing the git repository in Nautobot.

    NOTE: This tool stores the template content locally. Use the GitHub MCP to
    commit it to the repo, then call nautobot_sync_git_repository to pull changes.

    Args:
        path: Template file path relative to repo root (e.g. 'cisco_ios/main.j2')
        content: New template content (full file)
        commit_message: Git commit message (optional)
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"golden_config_update_template path={path} cr={cr_number}")
    return json.dumps({
        "status": "template_prepared",
        "path": path,
        "content_length": len(content),
        "commit_message": commit_message or f"Update template {path}",
        "next_steps": [
            "Use GitHub MCP to commit this content to the jinja templates repository",
            "Then call nautobot_sync_git_repository to pull changes into Nautobot",
            "Then call golden_config_generate_intended to regenerate configs",
        ],
        "content": content,
    }, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════════
# PHASE 5: SETUP TOOLS
# ═══════════════════════════════════════════════════════════════════════


@mcp.tool()
async def golden_config_get_settings() -> str:
    """Get the current golden config settings — repos, path templates, SoT query, scope.

    Returns the full configuration of the golden config plugin including which
    git repositories are linked, path templates for backup/intended/jinja, and
    the SoT aggregation query.
    """
    logger.info("golden_config_get_settings")
    try:
        resp = await client.rest_get("plugins/golden-config/golden-config-settings")
        results = resp.get("results", [])
        if not results:
            return json.dumps({"settings": None, "message": "No golden config settings configured."})

        setting = results[0]
        # Extract key fields into a concise summary
        summary = {
            "id": setting.get("id"),
            "backup_repository": setting.get("backup_repository"),
            "intended_repository": setting.get("intended_repository"),
            "jinja_repository": setting.get("jinja_repository"),
            "backup_path_template": setting.get("backup_path_template"),
            "intended_path_template": setting.get("intended_path_template"),
            "jinja_path_template": setting.get("jinja_path_template"),
            "sot_agg_query": setting.get("sot_agg_query"),
            "dynamic_group": setting.get("dynamic_group"),
        }
        return json.dumps(summary, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def golden_config_create_compliance_feature(
    name: str,
    description: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a compliance feature (e.g., 'observability', 'bgp', 'ospf', 'aaa'). ITSM-gated.

    Compliance features define categories of configuration that are checked
    independently. Each feature gets its own compliance rule with a match pattern.

    Args:
        name: Feature name (e.g. 'observability', 'ntp', 'logging')
        description: Optional description of what this feature covers
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"golden_config_create_compliance_feature name={name} cr={cr_number}")
    try:
        payload = {"name": name, "slug": name.lower().replace(" ", "_")}
        if description:
            payload["description"] = description
        result = await client.rest_post("plugins/golden-config/compliance-feature", payload)
        return json.dumps({"created": True, "feature": result}, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def golden_config_create_compliance_rule(
    feature: str,
    platform: str,
    match_config: str,
    config_ordered: bool = False,
    config_remediation: bool = False,
    description: Optional[str] = None,
    cr_number: Optional[str] = None,
) -> str:
    """Create a compliance rule linking a feature to a platform with a config match pattern. ITSM-gated.

    Rules define which config lines belong to a feature on a given platform.
    The match_config is a regex or literal that identifies the config section.

    Args:
        feature: Compliance feature name (e.g. 'aaa', 'ntp')
        platform: Platform name (e.g. 'cisco_ios', 'arista_eos')
        match_config: Config line(s) to match for this feature (regex pattern)
        config_ordered: Whether line order matters for compliance (default: False)
        config_remediation: Whether to generate remediation config (default: False)
        description: Optional description
        cr_number: ServiceNow change request number (required if ITSM enabled)
    """
    blocked = _check_itsm(cr_number)
    if blocked:
        return json.dumps({"error": blocked})

    logger.info(f"golden_config_create_compliance_rule feature={feature} platform={platform} cr={cr_number}")
    try:
        # Resolve feature ID
        feat_data = await client.graphql(
            f'{{ compliance_features(name: "{_esc(feature)}") {{ id }} }}'
        )
        feats = feat_data.get("compliance_features", [])
        if not feats:
            return json.dumps({"error": f"Feature '{feature}' not found. Create it first with golden_config_create_compliance_feature."})
        feat_id = feats[0]["id"]

        # Resolve platform ID
        plat_data = await client.graphql(
            f'{{ platforms(name: "{_esc(platform)}") {{ id }} }}'
        )
        plats = plat_data.get("platforms", [])
        if not plats:
            return json.dumps({"error": f"Platform '{platform}' not found in Nautobot."})
        plat_id = plats[0]["id"]

        payload = {
            "feature": feat_id,
            "platform": plat_id,
            "match_config": match_config,
            "config_type": "cli",
            "config_ordered": config_ordered,
            "config_remediation": config_remediation,
        }
        if description:
            payload["description"] = description

        result = await client.rest_post("plugins/golden-config/compliance-rule", payload)
        return json.dumps({"created": True, "rule": result}, indent=2, default=str)
    except NautobotError as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run(transport="stdio")
