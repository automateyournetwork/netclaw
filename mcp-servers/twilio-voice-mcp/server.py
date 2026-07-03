#!/usr/bin/env python3
"""
Twilio Voice MCP Server
Feature 042: Twilio Voice MCP Integration

Provides:
- Webhook endpoints for Twilio voice callbacks
- Voice call tools (initiate, check rate limit, get history)
- Call logging to Memory MCP
- Integration with @twilio-alpha/mcp for outbound calls
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import pytz
from twilio.rest import Client
from twilio.request_validator import RequestValidator

from guardrails import (
    sanitize_for_voice,
    check_rate_limit,
    record_call,
    can_call_now,
    is_whitelisted,
    validate_phone_number,
    normalize_phone_number,
    is_emergency_category,
    pre_call_check,
    load_config
)

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("twilio-voice-mcp")

# Environment variables
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_API_KEY_SID = os.environ.get("TWILIO_API_KEY_SID", "")
TWILIO_API_SECRET = os.environ.get("TWILIO_API_SECRET", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")
TWILIO_WEBHOOK_URL = os.environ.get("TWILIO_WEBHOOK_URL", "")

# Initialize Twilio client
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_API_KEY_SID and TWILIO_API_SECRET:
    try:
        twilio_client = Client(TWILIO_API_KEY_SID, TWILIO_API_SECRET, TWILIO_ACCOUNT_SID)
        logger.info("Twilio client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Twilio client: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# T012: Call Logging (Memory MCP integration)
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory call log (will be persisted via Memory MCP in production)
_call_log: list[dict] = []


def create_call_record(
    direction: str,
    phone_number: str,
    status: str,
    triggered_by: str,
    twilio_call_sid: str = None,
    content_spoken: str = None,
    duration_seconds: int = 0,
    trigger_id: str = None,
    retry_count: int = 0
) -> dict:
    """
    Create a call record for logging.

    Args:
        direction: "inbound" or "outbound"
        phone_number: E.164 format
        status: "completed", "failed", "no-answer", "busy", "rejected"
        triggered_by: What caused the call (e.g., "emergency", "user_request", "daily_briefing")
        twilio_call_sid: Twilio's call SID
        content_spoken: Sanitized content that was spoken
        duration_seconds: Call duration
        trigger_id: Related incident ID, command, or schedule
        retry_count: Number of retry attempts

    Returns:
        CallRecord dict
    """
    return {
        "call_id": str(uuid.uuid4()),
        "twilio_call_sid": twilio_call_sid,
        "direction": direction,
        "phone_number": normalize_phone_number(phone_number),
        "duration_seconds": duration_seconds,
        "status": status,
        "content_spoken": content_spoken,
        "transcript": None,  # For inbound calls
        "timestamp": datetime.now(pytz.UTC).isoformat(),
        "ended_at": None,
        "triggered_by": triggered_by,
        "trigger_id": trigger_id,
        "retry_count": retry_count
    }


def log_call(record: dict) -> None:
    """Log a call record."""
    global _call_log
    _call_log.append(record)
    logger.info(f"Call logged: {record['call_id']} - {record['direction']} - {record['status']}")


def get_call_history(
    direction: str = "all",
    since: datetime = None,
    limit: int = 10
) -> list[dict]:
    """
    Retrieve call history.

    Args:
        direction: "inbound", "outbound", or "all"
        since: Filter calls after this timestamp
        limit: Maximum number of records

    Returns:
        List of CallRecord dicts
    """
    global _call_log
    results = []

    for record in reversed(_call_log):  # Most recent first
        if direction != "all" and record["direction"] != direction:
            continue

        if since:
            try:
                record_ts = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
                if record_ts < since:
                    continue
            except (ValueError, TypeError):
                continue

        results.append(record)
        if len(results) >= limit:
            break

    return results


def update_call_status(call_id: str, status: str, duration_seconds: int = None) -> bool:
    """
    Update call status after completion.

    Args:
        call_id: The call record ID
        status: New status
        duration_seconds: Call duration if known

    Returns:
        True if updated, False if not found
    """
    global _call_log
    for record in _call_log:
        if record["call_id"] == call_id:
            record["status"] = status
            record["ended_at"] = datetime.now(pytz.UTC).isoformat()
            if duration_seconds is not None:
                record["duration_seconds"] = duration_seconds
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# T014-T018: Emergency Call Logic
# ═══════════════════════════════════════════════════════════════════════════════

async def initiate_voice_call(
    to: str,
    message: str,
    priority: str = "normal",
    triggered_by: str = "user_request",
    trigger_id: str = None
) -> dict:
    """
    Initiate an outbound voice call.

    Args:
        to: Phone number to call (E.164 format)
        message: Message to speak (will be sanitized)
        priority: "emergency" or "normal"
        triggered_by: What triggered this call
        trigger_id: Related ID (incident, command, etc.)

    Returns:
        Result dict with success status and details
    """
    # Pre-call validation
    can_call, reason, details = pre_call_check(to, priority, _call_log)

    if not can_call:
        logger.warning(f"Call blocked: {reason}")
        return {
            "success": False,
            "message": reason,
            "details": details
        }

    # Sanitize message for voice
    safe_message = sanitize_for_voice(message)

    # Create call record
    record = create_call_record(
        direction="outbound",
        phone_number=to,
        status="initiating",
        triggered_by=triggered_by,
        content_spoken=safe_message,
        trigger_id=trigger_id
    )

    if not twilio_client:
        record["status"] = "failed"
        log_call(record)
        return {
            "success": False,
            "message": "Twilio client not configured",
            "call_id": record["call_id"]
        }

    try:
        # Load config for voice selection
        config = load_config()
        voice = config.get("voice", "Polly.Matthew")

        # Create TwiML for the call
        twiml = f"""
        <Response>
            <Say voice="{voice}">{safe_message}</Say>
        </Response>
        """

        # Initiate call via Twilio API
        call = twilio_client.calls.create(
            to=normalize_phone_number(to),
            from_=TWILIO_PHONE_NUMBER,
            twiml=twiml.strip(),
            status_callback=f"{TWILIO_WEBHOOK_URL}/status" if TWILIO_WEBHOOK_URL else None,
            status_callback_event=["initiated", "ringing", "answered", "completed"]
        )

        record["twilio_call_sid"] = call.sid
        record["status"] = "initiated"
        log_call(record)
        record_call()  # For rate limiting

        logger.info(f"Call initiated: {call.sid} to {to}")

        return {
            "success": True,
            "call_sid": call.sid,
            "call_id": record["call_id"],
            "status": "initiated",
            "message": f"Call initiated to {details.get('whitelist_entry', {}).get('label', to)}"
        }

    except Exception as e:
        record["status"] = "failed"
        log_call(record)
        logger.error(f"Failed to initiate call: {e}")
        return {
            "success": False,
            "message": f"Failed to initiate call: {str(e)}",
            "call_id": record["call_id"]
        }


async def initiate_emergency_call(
    source: str,
    event_data: dict,
    message: str = None
) -> dict:
    """
    Initiate an emergency call based on an event.

    Args:
        source: Event source (e.g., "pagerduty")
        event_data: Event details
        message: Optional custom message (generated from event if not provided)

    Returns:
        Result dict
    """
    # Check if this is an emergency category
    is_emergency, category = is_emergency_category(source, event_data)

    if not is_emergency:
        return {
            "success": False,
            "message": f"Event does not match any emergency category",
            "source": source
        }

    # Get first whitelisted number for emergency calls
    config = load_config()
    whitelist = config.get("whitelist", [])
    target_phone = None

    for entry in whitelist:
        if entry.get("can_receive_calls", True):
            target_phone = entry.get("phone_number")
            break

    if not target_phone:
        return {
            "success": False,
            "message": "No whitelisted phone numbers for emergency calls"
        }

    # Generate message from event if not provided
    if not message:
        category_name = category.get("description", category.get("category_name", "Emergency"))
        event_summary = event_data.get("summary", event_data.get("description", "Critical event detected"))
        message = f"NetClaw Emergency Alert. {category_name}. {event_summary}"

    return await initiate_voice_call(
        to=target_phone,
        message=message,
        priority="emergency",
        triggered_by=f"emergency_{source}",
        trigger_id=event_data.get("incident_id") or event_data.get("id")
    )


# ═══════════════════════════════════════════════════════════════════════════════
# T011: MCP Server Setup
# ═══════════════════════════════════════════════════════════════════════════════

server = Server("twilio-voice-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Twilio Voice tools."""
    return [
        Tool(
            name="twilio_voice_call",
            description="Initiate an outbound voice call with a message. Validates against whitelist, rate limits, and quiet hours.",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Phone number to call (E.164 format, e.g., +18734550127)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Message to speak (max 1000 chars, will be sanitized)",
                        "maxLength": 1000
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["emergency", "normal"],
                        "default": "normal",
                        "description": "Emergency calls bypass quiet hours"
                    }
                },
                "required": ["to", "message"]
            }
        ),
        Tool(
            name="twilio_voice_emergency_call",
            description="Initiate an emergency call based on a critical event. Auto-approves if event matches emergency categories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Event source (e.g., 'pagerduty', 'netclaw_monitoring')"
                    },
                    "event_data": {
                        "type": "object",
                        "description": "Event details including severity, status, summary"
                    },
                    "message": {
                        "type": "string",
                        "description": "Optional custom message"
                    }
                },
                "required": ["source", "event_data"]
            }
        ),
        Tool(
            name="twilio_voice_check_rate_limit",
            description="Check if a call can be made within current rate limits.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="twilio_voice_get_call_history",
            description="Retrieve call history from the log.",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["inbound", "outbound", "all"],
                        "default": "all"
                    },
                    "since_hours": {
                        "type": "integer",
                        "description": "Filter calls from the last N hours",
                        "default": 24
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "maximum": 100
                    }
                }
            }
        ),
        Tool(
            name="twilio_voice_validate_number",
            description="Validate a phone number format and check whitelist status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "Phone number to validate"
                    }
                },
                "required": ["phone_number"]
            }
        ),
        Tool(
            name="twilio_voice_check_quiet_hours",
            description="Check if quiet hours are currently active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "priority": {
                        "type": "string",
                        "enum": ["emergency", "normal"],
                        "default": "normal"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    if name == "twilio_voice_call":
        result = await initiate_voice_call(
            to=arguments.get("to", ""),
            message=arguments.get("message", ""),
            priority=arguments.get("priority", "normal"),
            triggered_by="user_request"
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "twilio_voice_emergency_call":
        result = await initiate_emergency_call(
            source=arguments.get("source", ""),
            event_data=arguments.get("event_data", {}),
            message=arguments.get("message")
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "twilio_voice_check_rate_limit":
        allowed, reason, stats = check_rate_limit(_call_log)
        result = {
            "allowed": allowed,
            "reason": reason,
            "hourly_remaining": stats["hourly_remaining"],
            "daily_remaining": stats["daily_remaining"],
            "next_available": None if allowed else "Rate limit will reset in ~1 hour"
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "twilio_voice_get_call_history":
        direction = arguments.get("direction", "all")
        since_hours = arguments.get("since_hours", 24)
        limit = arguments.get("limit", 10)

        since = datetime.now(pytz.UTC) - timedelta(hours=since_hours)
        calls = get_call_history(direction, since, limit)

        result = {
            "calls": calls,
            "total": len(calls),
            "filter": {
                "direction": direction,
                "since_hours": since_hours
            }
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "twilio_voice_validate_number":
        phone = arguments.get("phone_number", "")
        valid, msg = validate_phone_number(phone)
        whitelisted, entry = is_whitelisted(phone, "outbound")

        result = {
            "phone_number": phone,
            "normalized": normalize_phone_number(phone) if valid else None,
            "valid_format": valid,
            "validation_message": msg,
            "whitelisted": whitelisted,
            "whitelist_label": entry.get("label") if entry else None
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "twilio_voice_check_quiet_hours":
        priority = arguments.get("priority", "normal")
        can_call, reason = can_call_now(priority)

        result = {
            "can_call": can_call,
            "reason": reason,
            "priority": priority,
            "current_time": datetime.now(pytz.UTC).isoformat()
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


# ═══════════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Run the MCP server."""
    logger.info("Starting Twilio Voice MCP Server")
    logger.info(f"Twilio Account: {TWILIO_ACCOUNT_SID[:10]}..." if TWILIO_ACCOUNT_SID else "Twilio not configured")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
