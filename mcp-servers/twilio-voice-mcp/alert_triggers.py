"""
Alert Triggers for NetClaw Voice Integration
Feature 043: Full Voice Integration

Handles proactive outbound calls for critical events.
Loads trigger configuration and initiates calls via Twilio.
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

import httpx

logger = logging.getLogger("voice-alerts")

# Twilio configuration
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")
WEBHOOK_BASE_URL = os.environ.get("VOICE_WEBHOOK_URL", "http://localhost:5001")

# Alert triggers config path
ALERT_TRIGGERS_PATH = Path.home() / ".openclaw" / "voice" / "alert_triggers.json"


# ═══════════════════════════════════════════════════════════════════════════════
# T013: AlertTrigger Config Loading
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AlertTrigger:
    """Configuration for a proactive alert trigger."""

    trigger_id: str
    name: str
    enabled: bool = True
    event_source: str = ""
    event_filter: dict = field(default_factory=dict)
    recipient_phone: str = ""
    message_template: str = ""
    cooldown_minutes: int = 15
    notes: str = ""

    # Runtime state (not persisted)
    last_triggered: Optional[datetime] = None

    def matches_event(self, event_source: str, event_data: dict) -> bool:
        """Check if this trigger matches an incoming event."""
        if not self.enabled:
            return False

        if self.event_source and self.event_source != event_source:
            return False

        # Check event filter
        for key, expected_value in self.event_filter.items():
            actual_value = event_data.get(key)
            if actual_value is None:
                return False

            # Handle list values (any match)
            if isinstance(expected_value, list):
                if actual_value not in expected_value:
                    return False
            elif str(actual_value).lower() != str(expected_value).lower():
                return False

        return True

    def is_in_cooldown(self) -> bool:
        """Check if trigger is in cooldown period."""
        if self.last_triggered is None:
            return False

        cooldown_end = self.last_triggered + timedelta(minutes=self.cooldown_minutes)
        return datetime.utcnow() < cooldown_end

    def format_message(self, event_data: dict) -> str:
        """Format the message template with event data."""
        message = self.message_template
        for key, value in event_data.items():
            placeholder = "{" + key + "}"
            if placeholder in message:
                message = message.replace(placeholder, str(value))
        return message

    @classmethod
    def from_dict(cls, data: dict) -> "AlertTrigger":
        """Create from dictionary."""
        return cls(
            trigger_id=data.get("trigger_id", ""),
            name=data.get("name", "Unnamed Trigger"),
            enabled=data.get("enabled", True),
            event_source=data.get("event_source", ""),
            event_filter=data.get("event_filter", {}),
            recipient_phone=data.get("recipient_phone", ""),
            message_template=data.get("message_template", "Alert: {title}"),
            cooldown_minutes=data.get("cooldown_minutes", 15),
            notes=data.get("notes", "")
        )


class AlertTriggerManager:
    """Manages alert trigger configuration and matching."""

    def __init__(self, config_path: Path = None):
        self.config_path = config_path or ALERT_TRIGGERS_PATH
        self._triggers: list[AlertTrigger] = []
        self._settings: dict = {}
        self._loaded = False

    def load_config(self) -> bool:
        """Load alert triggers from configuration file."""
        if not self.config_path.exists():
            logger.warning(f"Alert triggers config not found: {self.config_path}")
            return False

        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)

            self._triggers = [
                AlertTrigger.from_dict(t)
                for t in data.get("triggers", [])
            ]
            self._settings = data.get("settings", {})
            self._loaded = True

            logger.info(f"Loaded {len(self._triggers)} alert triggers")
            return True

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load alert triggers: {e}")
            return False

    def reload_config(self) -> bool:
        """Reload configuration from file."""
        return self.load_config()

    def get_matching_triggers(
        self,
        event_source: str,
        event_data: dict
    ) -> list[AlertTrigger]:
        """
        Find all triggers that match an event.

        Args:
            event_source: Source of the event (e.g., "pagerduty", "datadog")
            event_data: Event details

        Returns:
            List of matching triggers (not in cooldown)
        """
        if not self._loaded:
            self.load_config()

        matching = []
        for trigger in self._triggers:
            if trigger.matches_event(event_source, event_data):
                if not trigger.is_in_cooldown():
                    matching.append(trigger)
                else:
                    logger.debug(f"Trigger {trigger.trigger_id} is in cooldown")

        return matching

    def get_trigger_by_id(self, trigger_id: str) -> Optional[AlertTrigger]:
        """Get a specific trigger by ID."""
        if not self._loaded:
            self.load_config()

        for trigger in self._triggers:
            if trigger.trigger_id == trigger_id:
                return trigger
        return None

    def get_all_triggers(self) -> list[AlertTrigger]:
        """Get all configured triggers."""
        if not self._loaded:
            self.load_config()
        return self._triggers.copy()

    def get_enabled_triggers(self) -> list[AlertTrigger]:
        """Get only enabled triggers."""
        if not self._loaded:
            self.load_config()
        return [t for t in self._triggers if t.enabled]

    @property
    def max_calls_per_hour(self) -> int:
        """Get max calls per hour limit from settings."""
        return self._settings.get("max_calls_per_hour", 5)

    @property
    def default_cooldown_minutes(self) -> int:
        """Get default cooldown from settings."""
        return self._settings.get("default_cooldown_minutes", 15)


# ═══════════════════════════════════════════════════════════════════════════════
# T014: Outbound Call Initiation with Twilio
# ═══════════════════════════════════════════════════════════════════════════════

class OutboundCallManager:
    """Manages outbound calls via Twilio for proactive alerts."""

    def __init__(
        self,
        account_sid: str = None,
        auth_token: str = None,
        from_number: str = None,
        webhook_base_url: str = None
    ):
        self.account_sid = account_sid or TWILIO_ACCOUNT_SID
        self.auth_token = auth_token or TWILIO_AUTH_TOKEN
        self.from_number = from_number or TWILIO_PHONE_NUMBER
        self.webhook_base_url = webhook_base_url or WEBHOOK_BASE_URL

        # Tracking for rate limiting
        self._calls_this_hour: list[datetime] = []
        self._max_per_hour = 5

    def _check_rate_limit(self) -> bool:
        """Check if we're within hourly rate limit."""
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        self._calls_this_hour = [
            t for t in self._calls_this_hour if t > hour_ago
        ]
        return len(self._calls_this_hour) < self._max_per_hour

    def _record_call(self) -> None:
        """Record a call for rate limiting."""
        self._calls_this_hour.append(datetime.utcnow())

    async def initiate_alert_call(
        self,
        to_number: str,
        message: str,
        trigger_id: str = None
    ) -> dict:
        """
        Initiate an outbound call for an alert.

        Args:
            to_number: Recipient phone number (E.164 format)
            message: Message to speak when call is answered
            trigger_id: Optional trigger ID for tracking

        Returns:
            Dict with call status and details
        """
        # Validate configuration
        if not all([self.account_sid, self.auth_token, self.from_number]):
            return {
                "success": False,
                "error": "Twilio not configured (missing account_sid, auth_token, or from_number)"
            }

        if not to_number:
            return {
                "success": False,
                "error": "No recipient phone number specified"
            }

        # Check rate limit
        if not self._check_rate_limit():
            return {
                "success": False,
                "error": f"Rate limit exceeded ({self._max_per_hour} calls/hour)"
            }

        # Build TwiML for the call
        # The call will speak the message and then allow interaction
        twiml_url = f"{self.webhook_base_url}/webhooks/twilio/voice/alert-call"

        try:
            # Twilio REST API call
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Calls.json",
                    auth=(self.account_sid, self.auth_token),
                    data={
                        "To": to_number,
                        "From": self.from_number,
                        "Url": twiml_url,
                        "StatusCallback": f"{self.webhook_base_url}/webhooks/twilio/voice/status",
                        "StatusCallbackEvent": ["initiated", "ringing", "answered", "completed"],
                        # Pass message in URL params for the webhook to use
                        "Url": f"{twiml_url}?message={message[:500]}&trigger_id={trigger_id or ''}"
                    }
                )

                if response.status_code in (200, 201):
                    call_data = response.json()
                    self._record_call()

                    logger.info(f"Initiated alert call to {to_number}: {call_data.get('sid')}")
                    return {
                        "success": True,
                        "call_sid": call_data.get("sid"),
                        "status": call_data.get("status"),
                        "to": to_number,
                        "trigger_id": trigger_id
                    }
                else:
                    logger.error(f"Twilio API error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Twilio API error: {response.status_code}",
                        "details": response.text
                    }

        except Exception as e:
            logger.error(f"Failed to initiate call: {e}")
            return {
                "success": False,
                "error": str(e)
            }


async def process_event_for_alerts(
    event_source: str,
    event_data: dict,
    trigger_manager: AlertTriggerManager = None,
    call_manager: OutboundCallManager = None
) -> list[dict]:
    """
    Process an incoming event and trigger any matching alerts.

    Args:
        event_source: Source of the event (e.g., "pagerduty")
        event_data: Event details
        trigger_manager: Optional AlertTriggerManager instance
        call_manager: Optional OutboundCallManager instance

    Returns:
        List of call results for each triggered alert
    """
    if trigger_manager is None:
        trigger_manager = AlertTriggerManager()

    if call_manager is None:
        call_manager = OutboundCallManager()

    # Find matching triggers
    triggers = trigger_manager.get_matching_triggers(event_source, event_data)

    if not triggers:
        logger.debug(f"No matching triggers for event from {event_source}")
        return []

    results = []
    for trigger in triggers:
        # Format message
        message = trigger.format_message(event_data)

        # Initiate call
        result = await call_manager.initiate_alert_call(
            to_number=trigger.recipient_phone,
            message=message,
            trigger_id=trigger.trigger_id
        )

        # Update trigger state
        if result.get("success"):
            trigger.last_triggered = datetime.utcnow()

        results.append({
            "trigger_id": trigger.trigger_id,
            "trigger_name": trigger.name,
            **result
        })

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton Instances
# ═══════════════════════════════════════════════════════════════════════════════

_trigger_manager: Optional[AlertTriggerManager] = None
_call_manager: Optional[OutboundCallManager] = None


def get_trigger_manager() -> AlertTriggerManager:
    """Get singleton AlertTriggerManager instance."""
    global _trigger_manager
    if _trigger_manager is None:
        _trigger_manager = AlertTriggerManager()
        _trigger_manager.load_config()
    return _trigger_manager


def get_call_manager() -> OutboundCallManager:
    """Get singleton OutboundCallManager instance."""
    global _call_manager
    if _call_manager is None:
        _call_manager = OutboundCallManager()
    return _call_manager
