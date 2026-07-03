"""
Twilio Voice MCP Guardrails
Feature 042: Twilio Voice MCP Integration

Content filtering, rate limiting, quiet hours, and whitelist validation
to ensure safe and controlled voice communication.
"""

import re
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import pytz

# Configuration path
CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "twilio-voice.json"


def load_config() -> dict:
    """Load Twilio voice configuration from JSON file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {
        "whitelist": [],
        "quiet_hours": [],
        "emergency_categories": [],
        "rate_limits": {"hourly_max": 3, "daily_max": 10},
        "voice": "Polly.Matthew"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# T007: Content Sanitization for Voice
# ═══════════════════════════════════════════════════════════════════════════════

def sanitize_for_voice(text: str) -> str:
    """
    Sanitize text content before TTS to remove sensitive information.

    Filters:
    - IP addresses → "an IP address"
    - MAC addresses → "a MAC address"
    - Credentials (passwords, secrets, keys, tokens) → "[redacted]"
    - API keys → "[redacted API key]"
    - Email addresses → "an email address" (optional, may be useful)

    Args:
        text: Raw text to sanitize

    Returns:
        Sanitized text safe for voice output
    """
    if not text:
        return text

    # IPv4 addresses: Replace with generic description
    # Pattern: 1-3 digits, dot, repeated 4 times
    text = re.sub(
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        'an IP address',
        text
    )

    # IPv6 addresses (simplified pattern)
    text = re.sub(
        r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
        'an IPv6 address',
        text
    )
    text = re.sub(
        r'\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b',
        'an IPv6 address',
        text
    )

    # MAC addresses: Various formats (XX:XX:XX:XX:XX:XX, XX-XX-XX-XX-XX-XX)
    text = re.sub(
        r'\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b',
        'a MAC address',
        text
    )

    # Credential patterns: password=xxx, secret=xxx, key=xxx, token=xxx
    text = re.sub(
        r'(password|passwd|secret|api[_-]?key|api[_-]?secret|token|auth[_-]?token|access[_-]?token|bearer)\s*[:=]\s*\S+',
        r'\1: [redacted]',
        text,
        flags=re.IGNORECASE
    )

    # API keys with common prefixes (sk-, pk-, ghp_, etc.)
    text = re.sub(
        r'\b(sk|pk|ghp|gho|ghu|ghs|ghg|glpat|xox[abp]|xox[abp]?-[0-9]+)-[A-Za-z0-9_-]{20,}\b',
        '[redacted API key]',
        text
    )

    # Generic long hex strings (potential secrets, hashes)
    text = re.sub(
        r'\b[0-9a-fA-F]{32,}\b',
        '[redacted hash]',
        text
    )

    # Base64 encoded strings that look like secrets (very long, no spaces)
    text = re.sub(
        r'\b[A-Za-z0-9+/]{40,}={0,2}\b',
        '[redacted encoded value]',
        text
    )

    # Twilio-specific: Account SID, Auth Token patterns
    text = re.sub(
        r'\bAC[0-9a-f]{32}\b',
        '[Twilio Account SID]',
        text,
        flags=re.IGNORECASE
    )
    text = re.sub(
        r'\bSK[0-9a-f]{32}\b',
        '[Twilio API Key]',
        text,
        flags=re.IGNORECASE
    )

    return text


# ═══════════════════════════════════════════════════════════════════════════════
# T008: Rate Limiting
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory rate limit tracking (persisted to Memory MCP in server.py)
_call_timestamps: list[datetime] = []


def check_rate_limit(call_history: list[dict] = None) -> tuple[bool, str, dict]:
    """
    Check if a call can be made within rate limits.

    Args:
        call_history: Optional list of call records from Memory MCP
                     Each record should have 'timestamp' field

    Returns:
        Tuple of (allowed: bool, reason: str, stats: dict)
    """
    config = load_config()
    rate_limits = config.get("rate_limits", {"hourly_max": 3, "daily_max": 10})
    hourly_max = rate_limits.get("hourly_max", 3)
    daily_max = rate_limits.get("daily_max", 10)

    now = datetime.now(pytz.UTC)
    hour_ago = now - timedelta(hours=1)
    day_ago = now - timedelta(days=1)

    # Use provided history or in-memory tracking
    if call_history:
        # Parse timestamps from call history
        hourly_count = 0
        daily_count = 0
        for record in call_history:
            try:
                ts_str = record.get("timestamp", "")
                if ts_str:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = pytz.UTC.localize(ts)
                    if ts >= hour_ago:
                        hourly_count += 1
                    if ts >= day_ago:
                        daily_count += 1
            except (ValueError, TypeError):
                continue
    else:
        # Use in-memory tracking
        global _call_timestamps
        _call_timestamps = [ts for ts in _call_timestamps if ts >= day_ago]
        hourly_count = sum(1 for ts in _call_timestamps if ts >= hour_ago)
        daily_count = len(_call_timestamps)

    stats = {
        "hourly_count": hourly_count,
        "hourly_max": hourly_max,
        "hourly_remaining": max(0, hourly_max - hourly_count),
        "daily_count": daily_count,
        "daily_max": daily_max,
        "daily_remaining": max(0, daily_max - daily_count),
    }

    if hourly_count >= hourly_max:
        return False, f"Hourly rate limit reached ({hourly_count}/{hourly_max})", stats

    if daily_count >= daily_max:
        return False, f"Daily rate limit reached ({daily_count}/{daily_max})", stats

    return True, "OK", stats


def record_call(timestamp: datetime = None) -> None:
    """
    Record a call for rate limiting purposes.

    Args:
        timestamp: Call timestamp (defaults to now)
    """
    global _call_timestamps
    if timestamp is None:
        timestamp = datetime.now(pytz.UTC)
    _call_timestamps.append(timestamp)


# ═══════════════════════════════════════════════════════════════════════════════
# T009: Quiet Hours
# ═══════════════════════════════════════════════════════════════════════════════

def is_quiet_hours(timezone_str: str = None, check_time: datetime = None) -> tuple[bool, Optional[dict]]:
    """
    Check if current time is within quiet hours.

    Args:
        timezone_str: Override timezone (uses config default if not provided)
        check_time: Time to check (defaults to now)

    Returns:
        Tuple of (is_quiet: bool, matching_rule: dict or None)
    """
    config = load_config()
    quiet_hours_config = config.get("quiet_hours", [])

    if not quiet_hours_config:
        return False, None

    for rule in quiet_hours_config:
        if not rule.get("enabled", True):
            continue

        tz_str = timezone_str or rule.get("timezone", "America/Toronto")
        try:
            tz = pytz.timezone(tz_str)
        except pytz.UnknownTimeZoneError:
            tz = pytz.UTC

        now = check_time or datetime.now(tz)
        if now.tzinfo is None:
            now = tz.localize(now)
        else:
            now = now.astimezone(tz)

        # Check day of week if specified
        days = rule.get("days_of_week", [])
        if days and now.weekday() not in [int(d) for d in days]:
            continue

        # Parse start and end times
        try:
            start_parts = rule.get("start_time", "22:00").split(":")
            end_parts = rule.get("end_time", "07:00").split(":")
            start_hour, start_min = int(start_parts[0]), int(start_parts[1])
            end_hour, end_min = int(end_parts[0]), int(end_parts[1])
        except (ValueError, IndexError):
            continue

        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        # Handle overnight quiet hours (e.g., 22:00 - 07:00)
        if start_minutes > end_minutes:
            # Quiet hours span midnight
            if current_minutes >= start_minutes or current_minutes < end_minutes:
                return True, rule
        else:
            # Quiet hours within same day
            if start_minutes <= current_minutes < end_minutes:
                return True, rule

    return False, None


def can_call_now(priority: str = "normal", timezone_str: str = None) -> tuple[bool, str]:
    """
    Check if a call can be made now considering quiet hours.

    Args:
        priority: "emergency" bypasses quiet hours, "normal" respects them
        timezone_str: Override timezone

    Returns:
        Tuple of (can_call: bool, reason: str)
    """
    is_quiet, rule = is_quiet_hours(timezone_str)

    if not is_quiet:
        return True, "Not in quiet hours"

    # Check if emergency calls can bypass
    if priority == "emergency":
        if rule and rule.get("p1_override", True):
            return True, "Emergency call bypassing quiet hours"
        return False, "Emergency override disabled for this quiet hours rule"

    return False, f"Quiet hours active ({rule.get('start_time', '?')} - {rule.get('end_time', '?')})"


# ═══════════════════════════════════════════════════════════════════════════════
# T010: Whitelist Validation
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to E.164 format.

    Args:
        phone: Phone number in various formats

    Returns:
        Normalized E.164 format (+1XXXXXXXXXX)
    """
    if not phone:
        return phone

    # Remove all non-digit characters except leading +
    has_plus = phone.startswith("+")
    digits = re.sub(r'[^\d]', '', phone)

    # Add country code if missing (assume US/Canada)
    if len(digits) == 10:
        digits = "1" + digits

    return "+" + digits if digits else phone


def is_whitelisted(phone_number: str, direction: str = "outbound") -> tuple[bool, Optional[dict]]:
    """
    Check if a phone number is in the whitelist.

    Args:
        phone_number: E.164 format phone number
        direction: "outbound" (can_receive_calls) or "inbound" (can_initiate_calls)

    Returns:
        Tuple of (is_allowed: bool, whitelist_entry: dict or None)
    """
    config = load_config()
    whitelist = config.get("whitelist", [])

    normalized = normalize_phone_number(phone_number)

    for entry in whitelist:
        entry_number = normalize_phone_number(entry.get("phone_number", ""))
        if entry_number == normalized:
            if direction == "outbound":
                if entry.get("can_receive_calls", True):
                    return True, entry
            elif direction == "inbound":
                if entry.get("can_initiate_calls", True):
                    return True, entry
            else:
                # Unknown direction, just check if in whitelist
                return True, entry

    return False, None


def validate_phone_number(phone_number: str) -> tuple[bool, str]:
    """
    Validate a phone number format.

    Args:
        phone_number: Phone number to validate

    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    if not phone_number:
        return False, "Phone number is required"

    normalized = normalize_phone_number(phone_number)

    # E.164 format: + followed by 1-15 digits
    if not re.match(r'^\+[1-9]\d{1,14}$', normalized):
        return False, f"Invalid E.164 format: {phone_number}"

    return True, f"Valid phone number: {normalized}"


def get_whitelist_entry(phone_number: str) -> Optional[dict]:
    """
    Get the whitelist entry for a phone number.

    Args:
        phone_number: E.164 format phone number

    Returns:
        Whitelist entry dict or None
    """
    _, entry = is_whitelisted(phone_number, direction="outbound")
    return entry


# ═══════════════════════════════════════════════════════════════════════════════
# Emergency Category Detection
# ═══════════════════════════════════════════════════════════════════════════════

def is_emergency_category(source: str, event_data: dict) -> tuple[bool, Optional[dict]]:
    """
    Check if an event matches an emergency category.

    Args:
        source: Event source (e.g., "pagerduty", "netclaw_monitoring")
        event_data: Event details to match against patterns

    Returns:
        Tuple of (is_emergency: bool, matching_category: dict or None)
    """
    config = load_config()
    categories = config.get("emergency_categories", [])

    for category in categories:
        if not category.get("enabled", True):
            continue

        if category.get("source", "") != source:
            continue

        pattern = category.get("match_pattern", "")
        if not pattern:
            continue

        # Simple pattern matching
        # Format: "key:value" or "key:(val1|val2)" or "key1:val1 AND key2:val2"
        event_str = json.dumps(event_data).lower()
        pattern_lower = pattern.lower()

        # Handle AND conditions
        if " and " in pattern_lower:
            conditions = pattern_lower.split(" and ")
            all_match = True
            for cond in conditions:
                cond = cond.strip()
                if ":" in cond:
                    key, val = cond.split(":", 1)
                    # Handle OR pattern (val1|val2)
                    if val.startswith("(") and val.endswith(")"):
                        val_options = val[1:-1].split("|")
                        if not any(v.strip() in event_str for v in val_options):
                            all_match = False
                            break
                    elif val not in event_str:
                        all_match = False
                        break
            if all_match:
                return True, category
        else:
            # Simple key:value match
            if ":" in pattern_lower:
                key, val = pattern_lower.split(":", 1)
                if val in event_str:
                    return True, category

    return False, None


# ═══════════════════════════════════════════════════════════════════════════════
# Comprehensive Pre-Call Check
# ═══════════════════════════════════════════════════════════════════════════════

def pre_call_check(
    phone_number: str,
    priority: str = "normal",
    call_history: list[dict] = None
) -> tuple[bool, str, dict]:
    """
    Perform all pre-call validations.

    Args:
        phone_number: Target phone number
        priority: "emergency" or "normal"
        call_history: Optional call history from Memory MCP

    Returns:
        Tuple of (can_call: bool, reason: str, details: dict)
    """
    details = {
        "phone_valid": False,
        "phone_whitelisted": False,
        "rate_limit_ok": False,
        "quiet_hours_ok": False,
        "priority": priority
    }

    # 1. Validate phone number format
    valid, msg = validate_phone_number(phone_number)
    if not valid:
        return False, msg, details
    details["phone_valid"] = True
    details["phone_normalized"] = normalize_phone_number(phone_number)

    # 2. Check whitelist
    whitelisted, entry = is_whitelisted(phone_number, direction="outbound")
    if not whitelisted:
        return False, f"Phone number not in whitelist: {phone_number}", details
    details["phone_whitelisted"] = True
    details["whitelist_entry"] = entry

    # 3. Check rate limits
    allowed, reason, stats = check_rate_limit(call_history)
    details["rate_limit_stats"] = stats
    if not allowed:
        # Emergency calls still respect rate limits but log warning
        if priority != "emergency":
            return False, reason, details
        details["rate_limit_warning"] = reason
    details["rate_limit_ok"] = True

    # 4. Check quiet hours
    can_call, qh_reason = can_call_now(priority)
    details["quiet_hours_reason"] = qh_reason
    if not can_call:
        return False, qh_reason, details
    details["quiet_hours_ok"] = True

    return True, "All pre-call checks passed", details
