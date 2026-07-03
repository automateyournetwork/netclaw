"""
Context Manager for NetClaw Voice Integration
Feature 043: Full Voice Integration

Manages per-caller conversation context via Memory MCP.
Enables multi-turn conversations and context persistence across calls.
"""

import os
import json
import logging
import httpx
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

logger = logging.getLogger("voice-context")

# Memory MCP endpoint (if running locally)
MEMORY_MCP_URL = os.environ.get("MEMORY_MCP_URL", "http://localhost:8765")


# ═══════════════════════════════════════════════════════════════════════════════
# T006: ConversationContext Dataclass
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConversationContext:
    """
    Per-caller conversation context for voice sessions.

    Tracks:
    - Caller identity
    - Current session info
    - Recent conversation history
    - Referenced entities (devices, labs, incidents)
    - User preferences
    """

    # Caller identity
    caller_id: str
    caller_name: str = "User"
    caller_role: str = "user"

    # Session info
    session_id: str = ""
    call_start_time: str = ""
    last_interaction: str = ""

    # Conversation state
    turn_count: int = 0
    recent_topics: list[str] = field(default_factory=list)
    recent_messages: list[dict] = field(default_factory=list)

    # Referenced entities (for pronoun resolution)
    current_device: str = ""
    current_lab: str = ""
    current_incident: str = ""
    current_project: str = ""

    # User preferences
    preferred_voice: str = "Polly.Matthew"
    verbosity: str = "normal"  # "brief", "normal", "detailed"

    # Metadata
    total_calls: int = 0
    facts_stored: list[str] = field(default_factory=list)

    # Custom preferences (Slack channel, preferred tools, etc.)
    preferences: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationContext":
        """Create from dictionary."""
        # Handle missing fields gracefully
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)

    def add_message(self, role: str, content: str, max_messages: int = 10) -> None:
        """Add a message to recent history."""
        self.recent_messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        # Keep only recent messages
        if len(self.recent_messages) > max_messages:
            self.recent_messages = self.recent_messages[-max_messages:]

    def add_topic(self, topic: str, max_topics: int = 5) -> None:
        """Track a conversation topic."""
        if topic and topic not in self.recent_topics:
            self.recent_topics.append(topic)
            if len(self.recent_topics) > max_topics:
                self.recent_topics = self.recent_topics[-max_topics:]

    def update_entity_reference(self, entity_type: str, entity_name: str) -> None:
        """Update the currently referenced entity for pronoun resolution."""
        if entity_type == "device":
            self.current_device = entity_name
        elif entity_type == "lab":
            self.current_lab = entity_name
        elif entity_type == "incident":
            self.current_incident = entity_name
        elif entity_type == "project":
            self.current_project = entity_name

    def get_entity_context(self) -> str:
        """Get a summary of currently referenced entities."""
        parts = []
        if self.current_device:
            parts.append(f"Current device: {self.current_device}")
        if self.current_lab:
            parts.append(f"Current lab: {self.current_lab}")
        if self.current_incident:
            parts.append(f"Current incident: {self.current_incident}")
        if self.current_project:
            parts.append(f"Current project: {self.current_project}")
        return "; ".join(parts) if parts else "No specific entities referenced yet."


# ═══════════════════════════════════════════════════════════════════════════════
# T007: ContextManager with Memory MCP Integration
# ═══════════════════════════════════════════════════════════════════════════════

class ContextManager:
    """
    Manages conversation context with persistence via Memory MCP.

    Provides:
    - Per-caller context loading/saving
    - Conversation history management
    - Entity reference tracking for pronoun resolution
    """

    def __init__(self, memory_mcp_url: str = None):
        self.memory_mcp_url = memory_mcp_url or MEMORY_MCP_URL
        self._local_cache: dict[str, ConversationContext] = {}
        self._context_dir = Path.home() / ".openclaw" / "voice" / "contexts"
        self._context_dir.mkdir(parents=True, exist_ok=True)

    def _get_context_file(self, caller_id: str) -> Path:
        """Get the local file path for a caller's context."""
        # Sanitize caller ID for filename
        safe_id = caller_id.replace("+", "").replace("-", "").replace(" ", "")
        return self._context_dir / f"{safe_id}.json"

    async def load_context(self, caller_id: str, caller_name: str = "User") -> ConversationContext:
        """
        Load context for a caller from Memory MCP or local cache.

        Args:
            caller_id: Phone number in E.164 format
            caller_name: Optional caller name from whitelist

        Returns:
            ConversationContext for the caller
        """
        # Check local cache first
        if caller_id in self._local_cache:
            ctx = self._local_cache[caller_id]
            ctx.last_interaction = datetime.utcnow().isoformat()
            return ctx

        # Try to load from local file (fallback if Memory MCP unavailable)
        context_file = self._get_context_file(caller_id)
        if context_file.exists():
            try:
                with open(context_file, "r") as f:
                    data = json.load(f)
                    ctx = ConversationContext.from_dict(data)
                    ctx.caller_name = caller_name or ctx.caller_name
                    ctx.last_interaction = datetime.utcnow().isoformat()
                    self._local_cache[caller_id] = ctx
                    logger.info(f"Loaded context for {caller_id} from file")
                    return ctx
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load context file: {e}")

        # Try Memory MCP
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.memory_mcp_url}/tools/recall",
                    json={
                        "query": f"voice_context_{caller_id}",
                        "limit": 1
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("results"):
                        ctx_data = data["results"][0].get("content", {})
                        if isinstance(ctx_data, str):
                            ctx_data = json.loads(ctx_data)
                        ctx = ConversationContext.from_dict(ctx_data)
                        ctx.caller_name = caller_name or ctx.caller_name
                        ctx.last_interaction = datetime.utcnow().isoformat()
                        self._local_cache[caller_id] = ctx
                        logger.info(f"Loaded context for {caller_id} from Memory MCP")
                        return ctx
        except Exception as e:
            logger.debug(f"Memory MCP unavailable: {e}")

        # Create new context
        ctx = ConversationContext(
            caller_id=caller_id,
            caller_name=caller_name,
            call_start_time=datetime.utcnow().isoformat(),
            last_interaction=datetime.utcnow().isoformat()
        )
        self._local_cache[caller_id] = ctx
        logger.info(f"Created new context for {caller_id}")
        return ctx

    async def save_context(self, ctx: ConversationContext) -> bool:
        """
        Save context to Memory MCP and local file.

        Args:
            ctx: ConversationContext to save

        Returns:
            True if save successful
        """
        ctx.last_interaction = datetime.utcnow().isoformat()

        # Always save to local file as backup
        context_file = self._get_context_file(ctx.caller_id)
        try:
            with open(context_file, "w") as f:
                json.dump(ctx.to_dict(), f, indent=2)
            logger.debug(f"Saved context to {context_file}")
        except IOError as e:
            logger.warning(f"Failed to save context file: {e}")

        # Try to save to Memory MCP
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.memory_mcp_url}/tools/store",
                    json={
                        "key": f"voice_context_{ctx.caller_id}",
                        "content": ctx.to_dict(),
                        "tags": ["voice", "context", ctx.caller_id]
                    }
                )
                if response.status_code == 200:
                    logger.debug(f"Saved context to Memory MCP for {ctx.caller_id}")
                    return True
        except Exception as e:
            logger.debug(f"Memory MCP save failed: {e}")

        # Update local cache
        self._local_cache[ctx.caller_id] = ctx
        return True

    async def clear_context(self, caller_id: str) -> bool:
        """
        Clear context for a caller.

        Args:
            caller_id: Phone number to clear context for

        Returns:
            True if cleared successfully
        """
        # Clear local cache
        if caller_id in self._local_cache:
            del self._local_cache[caller_id]

        # Clear local file
        context_file = self._get_context_file(caller_id)
        if context_file.exists():
            try:
                context_file.unlink()
            except IOError:
                pass

        # Try to clear from Memory MCP
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{self.memory_mcp_url}/tools/forget",
                    json={"key": f"voice_context_{ctx.caller_id}"}
                )
        except Exception:
            pass

        logger.info(f"Cleared context for {caller_id}")
        return True

    def get_cached_context(self, caller_id: str) -> Optional[ConversationContext]:
        """Get context from local cache without loading."""
        return self._local_cache.get(caller_id)


# ═══════════════════════════════════════════════════════════════════════════════
# T008: Context Injection into Claude System Prompt
# ═══════════════════════════════════════════════════════════════════════════════

def build_context_prompt(ctx: ConversationContext) -> str:
    """
    Build a context section for injection into Claude's system prompt.

    This enables Claude to:
    - Address the user by name
    - Resolve pronouns ("it", "that lab", etc.)
    - Reference previous conversation topics
    - Maintain conversation continuity

    Args:
        ctx: ConversationContext for the current caller

    Returns:
        Context section to inject into system prompt
    """
    parts = []

    # Caller info
    parts.append(f"## Caller Context")
    parts.append(f"- Name: {ctx.caller_name}")
    parts.append(f"- Role: {ctx.caller_role}")
    parts.append(f"- Call count: {ctx.total_calls + 1}")

    # Entity references for pronoun resolution
    if ctx.current_device or ctx.current_lab or ctx.current_incident or ctx.current_project:
        parts.append(f"\n## Current References")
        parts.append("When the user says 'it', 'that', or similar pronouns, they likely mean:")
        if ctx.current_device:
            parts.append(f"- Device: {ctx.current_device}")
        if ctx.current_lab:
            parts.append(f"- Lab: {ctx.current_lab}")
        if ctx.current_incident:
            parts.append(f"- Incident: {ctx.current_incident}")
        if ctx.current_project:
            parts.append(f"- Project: {ctx.current_project}")

    # Recent topics
    if ctx.recent_topics:
        parts.append(f"\n## Recent Topics")
        parts.append(f"We've discussed: {', '.join(ctx.recent_topics)}")

    # Recent conversation history
    if ctx.recent_messages:
        parts.append(f"\n## Recent Conversation")
        for msg in ctx.recent_messages[-5:]:  # Last 5 messages
            role = "User" if msg["role"] == "user" else "NetClaw"
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            parts.append(f"- {role}: {content}")

    # Facts stored about this caller
    if ctx.facts_stored:
        parts.append(f"\n## Known Facts")
        for fact in ctx.facts_stored[-5:]:
            parts.append(f"- {fact}")

    # User preferences (Slack channel, preferred tools, etc.)
    if ctx.preferences:
        parts.append(f"\n## User Preferences")
        if ctx.preferences.get("slack_channel"):
            parts.append(f"- Default Slack channel: {ctx.preferences['slack_channel']} (ID: {ctx.preferences.get('slack_channel_id', 'unknown')})")
        if ctx.preferences.get("mind_map_tool"):
            parts.append(f"- For mind maps, use the {ctx.preferences['mind_map_tool']} skill")
        if ctx.preferences.get("default_output_channel"):
            parts.append(f"- Send outputs to: {ctx.preferences['default_output_channel']}")
        # Include any other preferences
        for key, value in ctx.preferences.items():
            if key not in ["slack_channel", "slack_channel_id", "mind_map_tool", "default_output_channel"]:
                parts.append(f"- {key}: {value}")

    return "\n".join(parts)


def inject_context_into_prompt(base_prompt: str, ctx: ConversationContext) -> str:
    """
    Inject conversation context into Claude's system prompt.

    Args:
        base_prompt: The base system prompt
        ctx: ConversationContext for the current caller

    Returns:
        System prompt with context injected
    """
    context_section = build_context_prompt(ctx)

    # Insert context after the first section of the base prompt
    if "\n\n" in base_prompt:
        first_section, rest = base_prompt.split("\n\n", 1)
        return f"{first_section}\n\n{context_section}\n\n{rest}"
    else:
        return f"{base_prompt}\n\n{context_section}"


def extract_entity_from_response(response: str, ctx: ConversationContext) -> None:
    """
    Extract and track entity references from Claude's response.

    Updates the context with any devices, labs, or incidents mentioned.

    Args:
        response: Claude's response text
        ctx: ConversationContext to update
    """
    import re

    # Device patterns (router names, switch names, etc.)
    device_patterns = [
        r'(?:router|switch|device|node)\s+["\']?([A-Za-z0-9_-]+)["\']?',
        r'([A-Z][a-z0-9-]*[0-9]+)',  # e.g., R1, SW-Core-01
    ]

    for pattern in device_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            ctx.update_entity_reference("device", matches[0])
            break

    # Lab patterns
    lab_patterns = [
        r'lab\s+["\']?([A-Za-z0-9_-]+)["\']?',
        r'["\']([^"\']+)["\'](?:\s+lab|\s+is\s+(?:running|stopped))',
    ]

    for pattern in lab_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            ctx.update_entity_reference("lab", matches[0])
            break

    # Incident patterns
    incident_patterns = [
        r'incident\s+(?:#)?([A-Z0-9-]+)',
        r'(?:INC|P[0-9])[0-9-]+',
    ]

    for pattern in incident_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            ctx.update_entity_reference("incident", matches[0])
            break


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton Context Manager
# ═══════════════════════════════════════════════════════════════════════════════

_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get the singleton ContextManager instance."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
