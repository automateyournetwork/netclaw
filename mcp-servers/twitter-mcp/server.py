#!/usr/bin/env python3
"""
Twitter MCP Server for NetClaw

Provides Twitter/X integration for posting tweets, threads, and media.
Implements content guardrails to prevent sensitive data leakage.

Free Tier Capabilities:
- Post tweets (text only)
- Post threads (multiple tweets)
- Post tweets with media
- Delete tweets
- Check rate limits

Environment Variables:
- TWITTER_API_KEY: Twitter API Key (Consumer Key)
- TWITTER_API_SECRET: Twitter API Secret (Consumer Secret)
- TWITTER_ACCESS_TOKEN: Twitter Access Token (OAuth 1.0a for posting)
- TWITTER_ACCESS_SECRET: Twitter Access Token Secret (OAuth 1.0a for posting)
- TWITTER_OAUTH2_TOKEN: OAuth 2.0 Bearer Token (for reading mentions - pay-as-you-go)
- TWITTER_HEARTBEAT_ENABLED: Enable autonomous heartbeat tweets (default: false)
- TWITTER_HEARTBEAT_INTERVAL: Seconds between heartbeat tweets (default: 14400 = 4 hours)
- TWITTER_MENTION_POLL_INTERVAL: Seconds between mention polling (default: 300 = 5 minutes)
"""

import os
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path

import tweepy
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server
from dotenv import load_dotenv

from guardrails import prepare_tweet, validate_content, GuardrailAction
from tweet_threading import create_thread, validate_thread
from mentions import (
    fetch_mentions_with_retry, fetch_mentions_oauth2, classify_mention,
    get_authenticated_user_id, get_authenticated_user_id_oauth2,
    get_conversation_context, ProcessedMentionTracker, InteractionHistory,
    Mention, MentionCategory, fetch_own_tweets_with_netclaw, parse_netclaw_command
)
from replies import (
    generate_reply_prompt, validate_reply_content, post_reply,
    prepare_reply_for_posting, ReplyAuditLog
)

# Load environment variables
env_path = Path.home() / ".openclaw" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("twitter-mcp")

# Initialize MCP server
server = Server("twitter-mcp")

# Twitter client (initialized lazily)
_twitter_client: Optional[tweepy.Client] = None
_twitter_api_v1: Optional[tweepy.API] = None

# Content categories for heartbeat tweets
CONTENT_CATEGORIES = ["tip", "hot_take", "til", "achievement", "musing", "community"]
_current_category_index = 0

# In-memory tweet history (used when Memory MCP is not available)
# Format: {tweet_id: {content, category, timestamp, is_heartbeat}}
_local_tweet_history: dict = {}

# Tweet history namespace for Memory MCP
TWITTER_HISTORY_NAMESPACE = "twitter_history"
TWITTER_CONFIG_NAMESPACE = "twitter_config"

# ============================================================================
# SAFETY CONTROLS - Prevent runaway reply loops
# ============================================================================
# MASTER KILL SWITCH - Replies are OFF until explicitly enabled
# To enable: export TWITTER_REPLIES_ENABLED=true
TWITTER_REPLIES_ENABLED = os.environ.get("TWITTER_REPLIES_ENABLED", "false").lower() == "true"

# Hard limit on replies per heartbeat cycle - prevents spam even if other checks fail
MAX_REPLIES_PER_CYCLE = 3

logger.info(f"🔒 TWITTER_REPLIES_ENABLED = {TWITTER_REPLIES_ENABLED}")
# ============================================================================
HISTORY_RETENTION_DAYS = 30
SIMILARITY_THRESHOLD = 0.85

# Mention tracking (Feature 040)
_mention_tracker: ProcessedMentionTracker = ProcessedMentionTracker()
_interaction_history: InteractionHistory = InteractionHistory()
_reply_audit_log: ReplyAuditLog = ReplyAuditLog()
_authenticated_user_id: str | None = None

# Anthropic API for contextual replies
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


async def generate_contextual_reply(author: str, tweet_text: str, category: str) -> str:
    """
    Use Claude to generate a contextual reply that ACTUALLY responds to what the person said.
    This proves NetClaw is reading and understanding tweets, not just posting canned responses.
    """
    if not ANTHROPIC_API_KEY:
        # Fallback to basic contextual response if no API key
        logger.warning("No ANTHROPIC_API_KEY - using basic contextual reply")
        return generate_basic_contextual_reply(author, tweet_text, category)

    try:
        system_prompt = """You are NetClaw (@John_Capobianco), a CCIE-certified AI network engineer on Twitter.
Generate a SHORT, contextual reply (under 250 chars to leave room for @mention and hashtag).

CRITICAL RULES:
1. Actually RESPOND to what they said - reference specific things they mentioned
2. Be helpful, technical when appropriate, friendly always
3. Show you READ their tweet by referencing their specific words/topic
4. Keep it SHORT - Twitter has limits
5. Don't include @username or #netclaw - those are added automatically
6. Be authentic - don't sound like a bot with generic responses

Examples of GOOD contextual replies:
- If they ask about BGP: "BGP route reflectors can definitely help scale your iBGP mesh! What's your current topology?"
- If they praise NetClaw: "Glad the automation is helping! Which feature saved you the most time?"
- If they mention a problem: "That OSPF adjacency issue sounds frustrating - have you checked the MTU settings on both ends?"

Examples of BAD generic replies (NEVER DO THIS):
- "Thanks for the kind words! The network never sleeps!"
- "Great question! NetClaw is always here to help!"
- "Thanks for reaching out!"
"""

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 150,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Tweet from @{author} (category: {category}):\n\n\"{tweet_text}\"\n\nGenerate a contextual reply:"
                        }
                    ]
                }
            )

            if response.status_code != 200:
                logger.error(f"Claude API error: {response.status_code} - {response.text}")
                return generate_basic_contextual_reply(author, tweet_text, category)

            result = response.json()
            reply_content = ""
            for block in result.get("content", []):
                if block.get("type") == "text":
                    reply_content += block.get("text", "")

            # Clean up and format
            reply_content = reply_content.strip()
            # Remove any @username if Claude added it
            if reply_content.startswith(f"@{author}"):
                reply_content = reply_content[len(f"@{author}"):].strip()

            # Add @mention and hashtag
            full_reply = f"@{author} {reply_content}"
            if "#netclaw" not in full_reply.lower():
                full_reply += " #netclaw"

            # Ensure under 280 chars
            if len(full_reply) > 280:
                # Truncate reply content
                max_content_len = 280 - len(f"@{author}  #netclaw") - 3
                reply_content = reply_content[:max_content_len] + "..."
                full_reply = f"@{author} {reply_content} #netclaw"

            logger.info(f"Generated contextual reply for @{author}: {full_reply[:50]}...")
            return full_reply

    except Exception as e:
        logger.error(f"Error generating contextual reply: {e}")
        return generate_basic_contextual_reply(author, tweet_text, category)


def generate_basic_contextual_reply(author: str, tweet_text: str, category: str) -> str:
    """
    Fallback: Generate a basic but still somewhat contextual reply without Claude.
    At minimum, reference something specific from their tweet.
    """
    tweet_lower = tweet_text.lower()

    # Try to find specific topics to reference
    if "bgp" in tweet_lower:
        reply = f"@{author} BGP questions are my favorite! What's the specific scenario you're working with? #netclaw"
    elif "ospf" in tweet_lower:
        reply = f"@{author} OSPF can be tricky - area design matters a lot. What topology are you dealing with? #netclaw"
    elif "automation" in tweet_lower or "automate" in tweet_lower:
        reply = f"@{author} Automation is the way! What are you looking to automate - configs, monitoring, or something else? #netclaw"
    elif "cml" in tweet_lower or "lab" in tweet_lower:
        reply = f"@{author} Labs are essential for testing! I run mine on CML - great for automation testing too. #netclaw"
    elif "cisco" in tweet_lower:
        reply = f"@{author} Cisco gear is bread and butter! What platform are you working with? #netclaw"
    elif "help" in tweet_lower or "question" in tweet_lower or "?" in tweet_text:
        # They're asking something - acknowledge it
        words = tweet_text.split()[:5]
        topic_hint = " ".join(words)
        reply = f"@{author} I see you're asking about '{topic_hint}...' - happy to dig into that! #netclaw"
    elif category == "friendly":
        # Extract a word or two they used to reference
        words = [w for w in tweet_text.split() if len(w) > 4 and w.lower() not in ["netclaw", "thanks", "thank"]]
        if words:
            reply = f"@{author} Appreciate it! Your mention of '{words[0]}' resonates - that's what we're all about! #netclaw"
        else:
            reply = f"@{author} Thanks for the support! What network challenge can I help you tackle next? #netclaw"
    else:
        # Last resort - but still try to be somewhat specific
        first_words = " ".join(tweet_text.split()[:4])
        reply = f"@{author} Interesting - '{first_words}...' Got my attention! Tell me more? #netclaw"

    return reply


def _safe_int(value: str, default: int) -> int:
    """Safely convert env var to int, handling bash-style defaults and empty values."""
    if not value or value.startswith("${"):
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_mention_poll_config() -> dict:
    """Get mention polling configuration from environment."""
    return {
        "interval": _safe_int(os.environ.get("TWITTER_MENTION_POLL_INTERVAL", ""), 300),
    }


def get_oauth2_token() -> Optional[str]:
    """Get OAuth 2.0 token from environment, auto-refreshing if needed."""
    return os.environ.get("TWITTER_OAUTH2_ACCESS_TOKEN") or os.environ.get("TWITTER_OAUTH2_TOKEN")


def refresh_oauth2_token() -> Optional[str]:
    """
    Refresh the OAuth 2.0 access token using the refresh token.
    Returns the new access token, or None if refresh failed.
    """
    refresh_token = os.environ.get("TWITTER_OAUTH2_REFRESH_TOKEN")
    client_id = os.environ.get("TWITTER_CLIENT_ID")
    client_secret = os.environ.get("TWITTER_CLIENT_SECRET")

    if not refresh_token or not client_id:
        logger.warning("Cannot refresh OAuth2 token: missing TWITTER_OAUTH2_REFRESH_TOKEN or TWITTER_CLIENT_ID")
        return None

    try:
        import requests

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id
        }

        if client_secret:
            auth = (client_id, client_secret)
        else:
            auth = None

        response = requests.post(
            "https://api.twitter.com/2/oauth2/token",
            data=data,
            auth=auth,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code == 200:
            tokens = response.json()
            new_access_token = tokens.get("access_token")
            new_refresh_token = tokens.get("refresh_token")

            # Update environment variables
            os.environ["TWITTER_OAUTH2_ACCESS_TOKEN"] = new_access_token
            if new_refresh_token:
                os.environ["TWITTER_OAUTH2_REFRESH_TOKEN"] = new_refresh_token

            # Also update the .env file for persistence
            _update_env_file(new_access_token, new_refresh_token)

            logger.info("OAuth2 token refreshed successfully")
            return new_access_token
        else:
            logger.error(f"Failed to refresh OAuth2 token: {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error refreshing OAuth2 token: {e}")
        return None


def _update_env_file(access_token: str, refresh_token: Optional[str] = None):
    """Update the .env file with new tokens."""
    import re

    env_path = Path.home() / ".openclaw" / ".env"
    if not env_path.exists():
        return

    try:
        content = env_path.read_text()

        # Update access token
        if "TWITTER_OAUTH2_ACCESS_TOKEN=" in content:
            content = re.sub(
                r'TWITTER_OAUTH2_ACCESS_TOKEN=.*',
                f'TWITTER_OAUTH2_ACCESS_TOKEN={access_token}',
                content
            )
        else:
            content += f"\nTWITTER_OAUTH2_ACCESS_TOKEN={access_token}"

        # Update refresh token if provided
        if refresh_token:
            if "TWITTER_OAUTH2_REFRESH_TOKEN=" in content:
                content = re.sub(
                    r'TWITTER_OAUTH2_REFRESH_TOKEN=.*',
                    f'TWITTER_OAUTH2_REFRESH_TOKEN={refresh_token}',
                    content
                )
            else:
                content += f"\nTWITTER_OAUTH2_REFRESH_TOKEN={refresh_token}"

        env_path.write_text(content)
        logger.info("Updated .env file with new tokens")

    except Exception as e:
        logger.error(f"Failed to update .env file: {e}")


def get_oauth2_token_with_refresh() -> Optional[str]:
    """Get OAuth 2.0 token, automatically refreshing if expired."""
    import requests

    token = get_oauth2_token()
    if not token:
        return None

    # Test if token is still valid
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get("https://api.twitter.com/2/users/me", headers=headers)

    if response.status_code == 401:
        # Token expired, try to refresh
        logger.info("OAuth2 token expired, attempting refresh...")
        token = refresh_oauth2_token()

    return token


async def get_user_id() -> str:
    """Get or cache the authenticated user ID."""
    global _authenticated_user_id
    if _authenticated_user_id is None:
        # Use OAuth 1.0a (tweepy client) - it doesn't expire like OAuth 2.0 tokens
        client = get_twitter_client()
        _authenticated_user_id = await get_authenticated_user_id(client)
    return _authenticated_user_id


def get_twitter_client() -> tweepy.Client:
    """Get or create the Twitter API v2 client."""
    global _twitter_client

    if _twitter_client is None:
        api_key = os.environ.get("TWITTER_API_KEY")
        api_secret = os.environ.get("TWITTER_API_SECRET")
        access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
        access_secret = os.environ.get("TWITTER_ACCESS_SECRET")

        if not all([api_key, api_secret, access_token, access_secret]):
            raise ValueError(
                "Twitter credentials not configured. Please set TWITTER_API_KEY, "
                "TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, and TWITTER_ACCESS_SECRET "
                "in ~/.openclaw/.env"
            )

        _twitter_client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
            wait_on_rate_limit=True
        )

    return _twitter_client


def get_twitter_api_v1() -> tweepy.API:
    """Get or create the Twitter API v1.1 client (for media uploads)."""
    global _twitter_api_v1

    if _twitter_api_v1 is None:
        api_key = os.environ.get("TWITTER_API_KEY")
        api_secret = os.environ.get("TWITTER_API_SECRET")
        access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
        access_secret = os.environ.get("TWITTER_ACCESS_SECRET")

        if not all([api_key, api_secret, access_token, access_secret]):
            raise ValueError("Twitter credentials not configured")

        auth = tweepy.OAuth1UserHandler(
            api_key, api_secret, access_token, access_secret
        )
        _twitter_api_v1 = tweepy.API(auth)

    return _twitter_api_v1


def get_heartbeat_config() -> dict:
    """Get heartbeat configuration from environment."""
    return {
        "enabled": os.environ.get("TWITTER_HEARTBEAT_ENABLED", "false").lower() == "true",
        "interval": _safe_int(os.environ.get("TWITTER_HEARTBEAT_INTERVAL", ""), 14400),
    }


def get_next_category() -> str:
    """Get the next content category for heartbeat rotation."""
    global _current_category_index
    category = CONTENT_CATEGORIES[_current_category_index]
    _current_category_index = (_current_category_index + 1) % len(CONTENT_CATEGORIES)
    return category


# =============================================================================
# Memory Integration (US3)
# =============================================================================

def store_tweet_history(
    tweet_id: str,
    content: str,
    category: Optional[str] = None,
    is_heartbeat: bool = False,
    thread_root: Optional[str] = None
) -> None:
    """
    Store a tweet in history for deduplication and audit trail.

    Stores in local memory. Memory MCP integration can be added later
    for persistent storage across sessions.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    entry = {
        "tweet_id": tweet_id,
        "content": content,
        "category": category,
        "timestamp": timestamp,
        "is_heartbeat": is_heartbeat,
        "thread_root": thread_root,
    }

    _local_tweet_history[tweet_id] = entry
    logger.info(f"Stored tweet {tweet_id} in history")

    # Cleanup old entries (>30 days)
    cleanup_old_history()


def cleanup_old_history() -> int:
    """
    Remove tweet history entries older than HISTORY_RETENTION_DAYS.

    Returns:
        Number of entries removed
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=HISTORY_RETENTION_DAYS)
    removed = 0

    to_remove = []
    for tweet_id, entry in _local_tweet_history.items():
        try:
            entry_time = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            if entry_time < cutoff:
                to_remove.append(tweet_id)
        except (KeyError, ValueError):
            continue

    for tweet_id in to_remove:
        del _local_tweet_history[tweet_id]
        removed += 1

    if removed > 0:
        logger.info(f"Cleaned up {removed} old tweet history entries")

    return removed


def check_duplicate_content(content: str, days: int = 7) -> tuple[bool, Optional[str]]:
    """
    Check if content is a duplicate of recent tweets.

    Uses simple string matching. For semantic similarity,
    integrate with Memory MCP's embedding search.

    Args:
        content: The content to check
        days: Number of days to look back

    Returns:
        Tuple of (is_duplicate, matching_tweet_id or None)
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    content_lower = content.lower().strip()

    # Remove hashtag for comparison
    content_normalized = content_lower.replace("#netclaw", "").strip()

    for tweet_id, entry in _local_tweet_history.items():
        try:
            entry_time = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            if entry_time < cutoff:
                continue

            stored_content = entry["content"].lower().strip()
            stored_normalized = stored_content.replace("#netclaw", "").strip()

            # Exact match
            if content_normalized == stored_normalized:
                return True, tweet_id

            # High similarity (simple check - >90% overlap)
            if len(content_normalized) > 20 and len(stored_normalized) > 20:
                # Check if one is substring of other
                if content_normalized in stored_normalized or stored_normalized in content_normalized:
                    return True, tweet_id

        except (KeyError, ValueError):
            continue

    return False, None


def get_recent_tweets(limit: int = 10, category: Optional[str] = None) -> list[dict]:
    """
    Get recent tweets from history.

    Args:
        limit: Maximum number of tweets to return
        category: Filter by category (optional)

    Returns:
        List of tweet entries, newest first
    """
    entries = list(_local_tweet_history.values())

    # Filter by category if specified
    if category:
        entries = [e for e in entries if e.get("category") == category]

    # Sort by timestamp descending
    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return entries[:limit]


def get_recent_activities_summary() -> str:
    """
    Generate a summary of recent activities for achievement tweets.

    This would ideally pull from Memory MCP's activity logs,
    but for now provides a template for content generation.

    Returns:
        Summary string for content generation
    """
    recent = get_recent_tweets(limit=20)
    heartbeat_count = sum(1 for t in recent if t.get("is_heartbeat"))
    manual_count = len(recent) - heartbeat_count

    # Count categories
    categories = {}
    for t in recent:
        cat = t.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    summary = f"Recent Twitter activity:\n"
    summary += f"- Total tweets: {len(recent)}\n"
    summary += f"- Heartbeat: {heartbeat_count}, Manual: {manual_count}\n"
    summary += f"- Categories: {categories}\n"

    return summary


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Twitter tools."""
    return [
        Tool(
            name="twitter_post_tweet",
            description=(
                "Post a new tweet to Twitter. Content is validated against guardrails "
                "before posting. Always includes #netclaw hashtag. Max 280 characters."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Tweet content (max 280 characters including hashtag)"
                    },
                    "skip_guardrails": {
                        "type": "boolean",
                        "description": "Skip content guardrails (not recommended)",
                        "default": False
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="twitter_post_thread",
            description=(
                "Post a thread of multiple tweets for content exceeding 280 characters. "
                "Automatically splits at sentence boundaries. Each tweet in thread counts "
                "against rate limit."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Full content to be split into a thread"
                    },
                    "skip_guardrails": {
                        "type": "boolean",
                        "description": "Skip content guardrails (not recommended)",
                        "default": False
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="twitter_post_tweet_with_media",
            description=(
                "Post a tweet with an attached image. Supports PNG, JPG, GIF formats. "
                "Uses Twitter API v1.1 for media upload, v2 for tweet posting."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Tweet content (max 280 characters)"
                    },
                    "media_path": {
                        "type": "string",
                        "description": "Absolute path to the image file to attach"
                    },
                    "alt_text": {
                        "type": "string",
                        "description": "Alt text for accessibility (max 1000 characters)"
                    },
                    "skip_guardrails": {
                        "type": "boolean",
                        "description": "Skip content guardrails (not recommended)",
                        "default": False
                    }
                },
                "required": ["content", "media_path"]
            }
        ),
        Tool(
            name="twitter_delete_tweet",
            description="Delete a previously posted tweet by ID. Use with caution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tweet_id": {
                        "type": "string",
                        "description": "The ID of the tweet to delete"
                    }
                },
                "required": ["tweet_id"]
            }
        ),
        Tool(
            name="twitter_get_rate_limits",
            description=(
                "Check current Twitter API rate limit status for posting. "
                "Free tier allows 50 tweets per 24 hours."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="twitter_generate_heartbeat_content",
            description=(
                "Generate content for a heartbeat tweet. Rotates through content categories: "
                "tip, hot_take, til, achievement, musing, community. Returns the category "
                "and suggested prompt for content generation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Specific category to use (optional, auto-rotates if not provided)",
                        "enum": ["tip", "hot_take", "til", "achievement", "musing", "community"]
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="twitter_check_duplicate",
            description=(
                "Check if content is a duplicate of recent tweets (last 7 days). "
                "Use before posting heartbeat content to avoid repetition."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Content to check for duplicates"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 7)",
                        "default": 7
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="twitter_get_history",
            description=(
                "Get recent tweet history for review. Shows tweets posted by NetClaw "
                "with timestamp, category, and content preview."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of tweets to return (default: 10)",
                        "default": 10
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by content category (optional)",
                        "enum": ["tip", "hot_take", "til", "achievement", "musing", "community"]
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="twitter_post_heartbeat",
            description=(
                "Post a heartbeat tweet with category tracking and duplicate checking. "
                "Use this for autonomous heartbeat tweets to ensure proper history tracking."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Tweet content"
                    },
                    "category": {
                        "type": "string",
                        "description": "Content category",
                        "enum": ["tip", "hot_take", "til", "achievement", "musing", "community"]
                    }
                },
                "required": ["content", "category"]
            }
        ),
        # Feature 040: Bidirectional Twitter Interaction Tools
        Tool(
            name="twitter_get_mentions",
            description=(
                "Fetch recent @mentions of the configured Twitter account. "
                "Returns unprocessed mentions for review and response."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of mentions to return (default: 10, max: 100)",
                        "default": 10
                    },
                    "since_id": {
                        "type": "string",
                        "description": "Only return mentions newer than this tweet ID"
                    },
                    "include_processed": {
                        "type": "boolean",
                        "description": "Include already-processed mentions (default: false)",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="twitter_get_conversation",
            description=(
                "Retrieve conversation context for a tweet. "
                "Returns parent tweets in the thread for context-aware replies."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tweet_id": {
                        "type": "string",
                        "description": "The tweet ID to get conversation context for"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum number of parent tweets to retrieve (default: 5, max: 10)",
                        "default": 5
                    }
                },
                "required": ["tweet_id"]
            }
        ),
        Tool(
            name="twitter_classify_mention",
            description=(
                "Classify a mention into response categories: "
                "netclaw_request, technical_network, friendly, off_topic, or spam."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tweet_id": {
                        "type": "string",
                        "description": "The mention tweet ID to classify"
                    },
                    "text": {
                        "type": "string",
                        "description": "The mention text (optional if tweet_id provided)"
                    },
                    "author_data": {
                        "type": "object",
                        "description": "Author metadata for spam detection (optional)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="twitter_generate_reply",
            description=(
                "Generate a CCIE-level reply for a mention. "
                "Does NOT post - returns draft for human approval."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "mention_id": {
                        "type": "string",
                        "description": "The tweet ID being replied to"
                    },
                    "mention_text": {
                        "type": "string",
                        "description": "The mention text to respond to"
                    },
                    "author_handle": {
                        "type": "string",
                        "description": "@username of the mention author"
                    },
                    "conversation_context": {
                        "type": "array",
                        "description": "Array of parent tweet texts for context",
                        "items": {"type": "string"}
                    },
                    "user_history": {
                        "type": "object",
                        "description": "Prior interaction history with this user (optional)"
                    }
                },
                "required": ["mention_id", "mention_text", "author_handle"]
            }
        ),
        Tool(
            name="twitter_reply_to_tweet",
            description=(
                "Post a reply to a specific tweet. "
                "REQUIRES human approval before posting (Constitution Principle XIV)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "in_reply_to_tweet_id": {
                        "type": "string",
                        "description": "The tweet ID to reply to"
                    },
                    "text": {
                        "type": "string",
                        "description": "Reply content (max 280 characters, or will be split into thread)"
                    },
                    "approved": {
                        "type": "boolean",
                        "description": "Human approval confirmation (MUST be true to post)",
                        "default": False
                    }
                },
                "required": ["in_reply_to_tweet_id", "text", "approved"]
            }
        ),
        Tool(
            name="twitter_mark_processed",
            description=(
                "Mark a mention as processed (skipped or replied). "
                "Prevents duplicate handling on next poll."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "mention_id": {
                        "type": "string",
                        "description": "The tweet ID to mark as processed"
                    },
                    "action": {
                        "type": "string",
                        "description": "What was done with the mention",
                        "enum": ["replied", "skipped_off_topic", "skipped_spam", "flagged_review"]
                    },
                    "reply_id": {
                        "type": "string",
                        "description": "The reply tweet ID if action was 'replied'"
                    }
                },
                "required": ["mention_id", "action"]
            }
        ),
        Tool(
            name="twitter_get_user_history",
            description=(
                "Retrieve interaction history with a Twitter user from Memory MCP."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "@username to look up (without @)"
                    }
                },
                "required": ["username"]
            }
        ),
        Tool(
            name="twitter_heartbeat_cycle",
            description=(
                "Combined heartbeat cycle: 1) Check for new mentions in threads with #netclaw, "
                "2) Auto-respond to unprocessed mentions, 3) Optionally post heartbeat tweet. "
                "This is the main polling function that should be called periodically."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "post_heartbeat": {
                        "type": "boolean",
                        "description": "Whether to post a heartbeat tweet this cycle (default: false)",
                        "default": False
                    },
                    "heartbeat_category": {
                        "type": "string",
                        "description": "Content category for heartbeat (tip, hot_take, til, achievement, musing, community)",
                        "enum": ["tip", "hot_take", "til", "achievement", "musing", "community"]
                    },
                    "heartbeat_content": {
                        "type": "string",
                        "description": "Pre-generated heartbeat content (if post_heartbeat=true)"
                    },
                    "respond_to_netclaw_only": {
                        "type": "boolean",
                        "description": "Only respond to mentions in threads containing #netclaw (default: true)",
                        "default": True
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, don't actually post replies - just report what would happen",
                        "default": False
                    }
                },
                "required": []
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    if name == "twitter_post_tweet":
        return await post_tweet(
            content=arguments["content"],
            skip_guardrails=arguments.get("skip_guardrails", False)
        )

    elif name == "twitter_post_thread":
        return await post_thread(
            content=arguments["content"],
            skip_guardrails=arguments.get("skip_guardrails", False)
        )

    elif name == "twitter_post_tweet_with_media":
        return await post_tweet_with_media(
            content=arguments["content"],
            media_path=arguments["media_path"],
            alt_text=arguments.get("alt_text"),
            skip_guardrails=arguments.get("skip_guardrails", False)
        )

    elif name == "twitter_delete_tweet":
        return await delete_tweet(tweet_id=arguments["tweet_id"])

    elif name == "twitter_get_rate_limits":
        return await get_rate_limits()

    elif name == "twitter_generate_heartbeat_content":
        return await generate_heartbeat_content(
            category=arguments.get("category")
        )

    elif name == "twitter_check_duplicate":
        return await check_duplicate(
            content=arguments["content"],
            days=arguments.get("days", 7)
        )

    elif name == "twitter_get_history":
        return await get_history(
            limit=arguments.get("limit", 10),
            category=arguments.get("category")
        )

    elif name == "twitter_post_heartbeat":
        return await post_tweet_with_history(
            content=arguments["content"],
            category=arguments["category"],
            is_heartbeat=True
        )

    # Feature 040: Bidirectional Twitter Interaction
    elif name == "twitter_get_mentions":
        return await handle_get_mentions(
            limit=arguments.get("limit", 10),
            since_id=arguments.get("since_id"),
            include_processed=arguments.get("include_processed", False)
        )

    elif name == "twitter_get_conversation":
        return await handle_get_conversation(
            tweet_id=arguments["tweet_id"],
            max_depth=arguments.get("max_depth", 5)
        )

    elif name == "twitter_classify_mention":
        return await handle_classify_mention(
            tweet_id=arguments.get("tweet_id"),
            text=arguments.get("text"),
            author_data=arguments.get("author_data")
        )

    elif name == "twitter_generate_reply":
        return await handle_generate_reply(
            mention_id=arguments["mention_id"],
            mention_text=arguments["mention_text"],
            author_handle=arguments["author_handle"],
            conversation_context=arguments.get("conversation_context"),
            user_history=arguments.get("user_history")
        )

    elif name == "twitter_reply_to_tweet":
        return await handle_reply_to_tweet(
            in_reply_to_tweet_id=arguments["in_reply_to_tweet_id"],
            text=arguments["text"],
            approved=arguments.get("approved", False)
        )

    elif name == "twitter_mark_processed":
        return await handle_mark_processed(
            mention_id=arguments["mention_id"],
            action=arguments["action"],
            reply_id=arguments.get("reply_id")
        )

    elif name == "twitter_get_user_history":
        return await handle_get_user_history(
            username=arguments["username"]
        )

    elif name == "twitter_heartbeat_cycle":
        return await handle_heartbeat_cycle(
            post_heartbeat=arguments.get("post_heartbeat", False),
            heartbeat_category=arguments.get("heartbeat_category"),
            heartbeat_content=arguments.get("heartbeat_content"),
            respond_to_netclaw_only=arguments.get("respond_to_netclaw_only", True),
            dry_run=arguments.get("dry_run", False)
        )

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def post_tweet(content: str, skip_guardrails: bool = False) -> list[TextContent]:
    """Post a single tweet."""
    try:
        # Validate and prepare content
        result = prepare_tweet(content, skip_guardrails)

        if not result.passed:
            return [TextContent(
                type="text",
                text=f"Tweet blocked by guardrails: {result.blocked_reason}\n\n"
                     f"Guardrail matches:\n" +
                     "\n".join(f"- {m.pattern_name}: {m.description}" for m in result.matches)
            )]

        # Post to Twitter
        client = get_twitter_client()
        response = client.create_tweet(text=result.content)

        tweet_id = response.data["id"]
        url = f"https://twitter.com/i/web/status/{tweet_id}"

        # Store in history
        store_tweet_history(
            tweet_id=tweet_id,
            content=result.content,
            category=None,  # Will be set by heartbeat if applicable
            is_heartbeat=False
        )

        # Build response
        response_text = f"Tweet posted successfully!\n\n"
        response_text += f"**Tweet ID**: {tweet_id}\n"
        response_text += f"**URL**: {url}\n"
        response_text += f"**Content**: {result.content}\n"

        if result.matches:
            sanitized = [m for m in result.matches if m.action == GuardrailAction.SANITIZE]
            if sanitized:
                response_text += f"\n**Sanitized**: {len(sanitized)} patterns replaced"

        return [TextContent(type="text", text=response_text)]

    except tweepy.TweepyException as e:
        logger.error(f"Twitter API error: {e}")
        return [TextContent(type="text", text=f"Twitter API error: {str(e)}")]
    except Exception as e:
        logger.error(f"Error posting tweet: {e}")
        return [TextContent(type="text", text=f"Error posting tweet: {str(e)}")]


async def post_tweet_with_history(
    content: str,
    category: Optional[str] = None,
    is_heartbeat: bool = False,
    skip_guardrails: bool = False
) -> list[TextContent]:
    """Post a tweet and store in history with metadata."""
    try:
        # Check for duplicates first
        is_dup, dup_id = check_duplicate_content(content)
        if is_dup:
            return [TextContent(
                type="text",
                text=f"Content appears to be a duplicate of recent tweet {dup_id}. "
                     f"Please generate different content to avoid repetition."
            )]

        # Validate and prepare content
        result = prepare_tweet(content, skip_guardrails)

        if not result.passed:
            return [TextContent(
                type="text",
                text=f"Tweet blocked by guardrails: {result.blocked_reason}"
            )]

        # Post to Twitter
        client = get_twitter_client()
        response = client.create_tweet(text=result.content)

        tweet_id = response.data["id"]
        url = f"https://twitter.com/i/web/status/{tweet_id}"

        # Store in history with metadata
        store_tweet_history(
            tweet_id=tweet_id,
            content=result.content,
            category=category,
            is_heartbeat=is_heartbeat
        )

        response_text = f"Tweet posted successfully!\n\n"
        response_text += f"**Tweet ID**: {tweet_id}\n"
        response_text += f"**URL**: {url}\n"
        response_text += f"**Content**: {result.content}\n"
        if category:
            response_text += f"**Category**: {category}\n"
        response_text += f"**Heartbeat**: {is_heartbeat}\n"

        return [TextContent(type="text", text=response_text)]

    except tweepy.TweepyException as e:
        logger.error(f"Twitter API error: {e}")
        return [TextContent(type="text", text=f"Twitter API error: {str(e)}")]
    except Exception as e:
        logger.error(f"Error posting tweet: {e}")
        return [TextContent(type="text", text=f"Error posting tweet: {str(e)}")]


async def post_thread(content: str, skip_guardrails: bool = False) -> list[TextContent]:
    """Post a thread of tweets."""
    try:
        # Validate content first
        validation = validate_content(content, skip_guardrails)
        if not validation.passed:
            return [TextContent(
                type="text",
                text=f"Thread blocked by guardrails: {validation.blocked_reason}"
            )]

        # Use sanitized content
        content_to_thread = validation.content

        # Split into thread
        thread_result = create_thread(content_to_thread)

        # Validate thread
        errors = validate_thread(thread_result)
        if errors:
            return [TextContent(
                type="text",
                text=f"Thread validation failed:\n" + "\n".join(errors)
            )]

        # Post each tweet in thread
        client = get_twitter_client()
        tweet_ids = []
        previous_tweet_id = None

        for tweet in thread_result.tweets:
            numbered_content = tweet.numbered_content

            if previous_tweet_id:
                # Reply to previous tweet
                response = client.create_tweet(
                    text=numbered_content,
                    in_reply_to_tweet_id=previous_tweet_id
                )
            else:
                # First tweet
                response = client.create_tweet(text=numbered_content)

            tweet_id = response.data["id"]
            tweet_ids.append(tweet_id)
            previous_tweet_id = tweet_id

        thread_root_id = tweet_ids[0]
        url = f"https://twitter.com/i/web/status/{thread_root_id}"

        response_text = f"Thread posted successfully!\n\n"
        response_text += f"**Thread Root ID**: {thread_root_id}\n"
        response_text += f"**URL**: {url}\n"
        response_text += f"**Tweet Count**: {len(tweet_ids)}\n"
        response_text += f"**Tweet IDs**: {', '.join(tweet_ids)}\n"

        return [TextContent(type="text", text=response_text)]

    except tweepy.TweepyException as e:
        logger.error(f"Twitter API error: {e}")
        return [TextContent(type="text", text=f"Twitter API error: {str(e)}")]
    except Exception as e:
        logger.error(f"Error posting thread: {e}")
        return [TextContent(type="text", text=f"Error posting thread: {str(e)}")]


async def post_tweet_with_media(
    content: str,
    media_path: str,
    alt_text: Optional[str] = None,
    skip_guardrails: bool = False
) -> list[TextContent]:
    """Post a tweet with an attached image."""
    try:
        # Validate content
        result = prepare_tweet(content, skip_guardrails)
        if not result.passed:
            return [TextContent(
                type="text",
                text=f"Tweet blocked by guardrails: {result.blocked_reason}"
            )]

        # Verify media file exists
        media_file = Path(media_path)
        if not media_file.exists():
            return [TextContent(
                type="text",
                text=f"Media file not found: {media_path}"
            )]

        # Upload media using v1.1 API
        api_v1 = get_twitter_api_v1()
        media = api_v1.media_upload(str(media_file))
        media_id = media.media_id_string

        # Add alt text if provided
        if alt_text:
            api_v1.create_media_metadata(media_id, alt_text=alt_text[:1000])

        # Post tweet with media using v2 API
        client = get_twitter_client()
        response = client.create_tweet(
            text=result.content,
            media_ids=[media_id]
        )

        tweet_id = response.data["id"]
        url = f"https://twitter.com/i/web/status/{tweet_id}"

        response_text = f"Tweet with media posted successfully!\n\n"
        response_text += f"**Tweet ID**: {tweet_id}\n"
        response_text += f"**Media ID**: {media_id}\n"
        response_text += f"**URL**: {url}\n"
        response_text += f"**Content**: {result.content}\n"

        return [TextContent(type="text", text=response_text)]

    except tweepy.TweepyException as e:
        logger.error(f"Twitter API error: {e}")
        return [TextContent(type="text", text=f"Twitter API error: {str(e)}")]
    except Exception as e:
        logger.error(f"Error posting tweet with media: {e}")
        return [TextContent(type="text", text=f"Error posting tweet with media: {str(e)}")]


async def delete_tweet(tweet_id: str) -> list[TextContent]:
    """Delete a tweet by ID."""
    try:
        client = get_twitter_client()
        client.delete_tweet(id=tweet_id)

        return [TextContent(
            type="text",
            text=f"Tweet deleted successfully.\n\n**Deleted ID**: {tweet_id}"
        )]

    except tweepy.TweepyException as e:
        logger.error(f"Twitter API error: {e}")
        return [TextContent(type="text", text=f"Twitter API error: {str(e)}")]
    except Exception as e:
        logger.error(f"Error deleting tweet: {e}")
        return [TextContent(type="text", text=f"Error deleting tweet: {str(e)}")]


async def get_rate_limits() -> list[TextContent]:
    """Get current rate limit status."""
    try:
        # Note: Twitter Free tier has limited rate limit visibility
        # We'll return what we know about the limits
        config = get_heartbeat_config()

        response_text = "Twitter API Rate Limits (Free Tier)\n\n"
        response_text += "**Posting Limits**:\n"
        response_text += "- Tweets per 24 hours: 50\n"
        response_text += "- Tweets per 15 minutes: ~17\n"
        response_text += "\n**Heartbeat Configuration**:\n"
        response_text += f"- Enabled: {config['enabled']}\n"
        response_text += f"- Interval: {config['interval']} seconds ({config['interval'] // 3600} hours)\n"

        # Calculate heartbeat usage
        tweets_per_day = 86400 // config['interval'] if config['enabled'] else 0
        response_text += f"- Estimated heartbeat tweets/day: {tweets_per_day}\n"
        response_text += f"- Remaining for manual tweets: ~{50 - tweets_per_day}/day\n"

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error getting rate limits: {e}")
        return [TextContent(type="text", text=f"Error getting rate limits: {str(e)}")]


async def generate_heartbeat_content(category: Optional[str] = None) -> list[TextContent]:
    """Generate prompt for heartbeat content."""
    try:
        # Use provided category or rotate to next
        selected_category = category if category else get_next_category()

        # Category-specific prompts
        prompts = {
            "tip": (
                "Generate a CCIE-level network engineering tip about one of these topics: "
                "BGP, OSPF, EIGRP, MPLS, EVPN/VXLAN, STP, QoS, or security. "
                "Be direct and technical. Include the #netclaw hashtag. Max 280 characters."
            ),
            "hot_take": (
                "Generate an opinionated but defensible hot take about network engineering. "
                "Something that might spark discussion among network engineers. "
                "Be bold but professional. Include the #netclaw hashtag. Max 280 characters."
            ),
            "til": (
                "Generate a 'Today I Learned' tweet about a network engineering fact, "
                "RFC detail, or protocol behavior. Reference the RFC number if applicable. "
                "Include the #netclaw hashtag. Max 280 characters."
            ),
            "achievement": (
                "Generate a tweet celebrating a sanitized network engineering achievement. "
                "Examples: auditing devices, troubleshooting issues, analyzing configs. "
                "Do NOT include real IPs, hostnames, or customer names. "
                "Include the #netclaw hashtag. Max 280 characters."
            ),
            "musing": (
                "Generate a reflective tweet about being an AI network engineer. "
                "What's unique about the AI perspective on networking? "
                "Be thoughtful and authentic. Include the #netclaw hashtag. Max 280 characters."
            ),
            "community": (
                "Generate a tweet with career advice or community insight for network engineers. "
                "Could be about certifications, skills, workplace dynamics, or industry trends. "
                "Include the #netclaw hashtag. Max 280 characters."
            ),
        }

        prompt = prompts.get(selected_category, prompts["tip"])

        response_text = f"Heartbeat Content Generation\n\n"
        response_text += f"**Category**: {selected_category}\n\n"
        response_text += f"**Prompt**:\n{prompt}\n\n"
        response_text += "Generate content following this prompt, then use twitter_post_tweet to post it."

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error generating heartbeat content: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def check_duplicate(content: str, days: int = 7) -> list[TextContent]:
    """Check if content is a duplicate of recent tweets."""
    try:
        is_dup, dup_id = check_duplicate_content(content, days)

        if is_dup:
            response_text = f"**Duplicate Detected**\n\n"
            response_text += f"Content matches tweet ID: {dup_id}\n"
            response_text += f"Please generate different content to avoid repetition."
        else:
            response_text = f"**No Duplicate Found**\n\n"
            response_text += f"Content is unique within the last {days} days.\n"
            response_text += f"Safe to post."

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error checking duplicate: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def get_history(limit: int = 10, category: Optional[str] = None) -> list[TextContent]:
    """Get recent tweet history."""
    try:
        tweets = get_recent_tweets(limit=limit, category=category)

        if not tweets:
            return [TextContent(
                type="text",
                text="No tweets found in history."
            )]

        response_text = f"**Tweet History** (last {len(tweets)} tweets)\n\n"

        for i, tweet in enumerate(tweets, 1):
            tweet_id = tweet.get("tweet_id", "unknown")
            content = tweet.get("content", "")
            timestamp = tweet.get("timestamp", "unknown")
            cat = tweet.get("category", "manual")
            is_hb = "🤖" if tweet.get("is_heartbeat") else "👤"

            # Truncate content for display
            content_preview = content[:60] + "..." if len(content) > 60 else content

            response_text += f"{i}. {is_hb} [{cat}] {timestamp[:10]}\n"
            response_text += f"   ID: {tweet_id}\n"
            response_text += f"   \"{content_preview}\"\n\n"

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# =============================================================================
# Feature 040: Bidirectional Twitter Interaction Handlers
# =============================================================================

async def handle_get_mentions(
    limit: int = 10,
    since_id: Optional[str] = None,
    include_processed: bool = False
) -> list[TextContent]:
    """Fetch recent @mentions."""
    try:
        user_id = await get_user_id()

        # Use OAuth 2.0 if available (required for pay-as-you-go tier)
        oauth2_token = get_oauth2_token()
        if oauth2_token:
            mentions = await fetch_mentions_oauth2(
                oauth2_token=oauth2_token,
                user_id=user_id,
                limit=min(limit, 100),
                since_id=since_id
            )
        else:
            client = get_twitter_client()
            mentions = await fetch_mentions_with_retry(
                client=client,
                user_id=user_id,
                limit=min(limit, 100),
                since_id=since_id
            )

        if not mentions:
            return [TextContent(
                type="text",
                text="No new mentions found."
            )]

        # Filter out processed mentions unless requested
        if not include_processed:
            unprocessed = []
            for m in mentions:
                if not await _mention_tracker.is_processed(m.tweet_id):
                    unprocessed.append(m)
            mentions = unprocessed

        if not mentions:
            return [TextContent(
                type="text",
                text="No unprocessed mentions found. Use include_processed=true to see all."
            )]

        response_text = f"**Twitter Mentions** ({len(mentions)} found)\n\n"

        for i, mention in enumerate(mentions, 1):
            category_emoji = {
                MentionCategory.NETCLAW_REQUEST: "🤖",
                MentionCategory.TECHNICAL_NETWORK: "🔧",
                MentionCategory.FRIENDLY: "👋",
                MentionCategory.OFF_TOPIC: "❓",
                MentionCategory.SPAM: "🚫"
            }.get(mention.category, "❓")

            response_text += f"{i}. {category_emoji} @{mention.author_handle}\n"
            response_text += f"   ID: {mention.tweet_id}\n"
            response_text += f"   Category: {mention.category.value if mention.category else 'unclassified'}\n"
            response_text += f"   Time: {mention.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            response_text += f"   Text: \"{mention.text[:100]}{'...' if len(mention.text) > 100 else ''}\"\n\n"

        response_text += "\nTo respond, use twitter_generate_reply with the mention details."

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error fetching mentions: {e}")
        return [TextContent(type="text", text=f"Error fetching mentions: {str(e)}")]


async def handle_get_conversation(
    tweet_id: str,
    max_depth: int = 5
) -> list[TextContent]:
    """Get conversation context for a tweet."""
    try:
        client = get_twitter_client()
        context = await get_conversation_context(
            client=client,
            tweet_id=tweet_id,
            max_depth=min(max_depth, 10)
        )

        if not context.tweets:
            return [TextContent(
                type="text",
                text=f"No conversation context found for tweet {tweet_id}."
            )]

        response_text = f"**Conversation Context** (conversation ID: {context.conversation_id})\n\n"

        for i, tweet in enumerate(context.tweets, 1):
            response_text += f"{i}. @{tweet['author_handle']}"
            if tweet.get('created_at'):
                response_text += f" ({tweet['created_at'][:10]})"
            response_text += f"\n"
            response_text += f"   \"{tweet['text'][:150]}{'...' if len(tweet['text']) > 150 else ''}\"\n\n"

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        return [TextContent(type="text", text=f"Error getting conversation: {str(e)}")]


async def handle_classify_mention(
    tweet_id: Optional[str] = None,
    text: Optional[str] = None,
    author_data: Optional[dict] = None
) -> list[TextContent]:
    """Classify a mention into response categories."""
    try:
        if not text and not tweet_id:
            return [TextContent(
                type="text",
                text="Error: Either tweet_id or text must be provided."
            )]

        # If only tweet_id provided, we'd need to fetch the tweet
        # For now, require text
        if not text:
            return [TextContent(
                type="text",
                text="Error: text parameter required for classification."
            )]

        category = classify_mention(text, author_data)

        category_descriptions = {
            MentionCategory.NETCLAW_REQUEST: "Request related to NetClaw capabilities (automation, diagrams, etc.)",
            MentionCategory.TECHNICAL_NETWORK: "Technical networking question (BGP, OSPF, etc.)",
            MentionCategory.FRIENDLY: "Friendly engagement (thanks, hello, etc.)",
            MentionCategory.OFF_TOPIC: "Not related to networking or NetClaw",
            MentionCategory.SPAM: "Likely spam or bot account"
        }

        response_text = f"**Mention Classification**\n\n"
        response_text += f"**Category**: {category.value}\n"
        response_text += f"**Description**: {category_descriptions.get(category, 'Unknown')}\n\n"

        # Recommend action
        if category == MentionCategory.SPAM:
            response_text += "**Recommendation**: Skip - likely spam account."
        elif category == MentionCategory.OFF_TOPIC:
            response_text += "**Recommendation**: Consider skipping - not relevant to NetClaw/networking."
        elif category == MentionCategory.NETCLAW_REQUEST:
            response_text += "**Recommendation**: Generate reply - user is asking about NetClaw."
        elif category == MentionCategory.TECHNICAL_NETWORK:
            response_text += "**Recommendation**: Generate reply - technical network question."
        elif category == MentionCategory.FRIENDLY:
            response_text += "**Recommendation**: Generate brief friendly reply."

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error classifying mention: {e}")
        return [TextContent(type="text", text=f"Error classifying mention: {str(e)}")]


async def handle_generate_reply(
    mention_id: str,
    mention_text: str,
    author_handle: str,
    conversation_context: Optional[list] = None,
    user_history: Optional[dict] = None
) -> list[TextContent]:
    """Generate a reply for a mention (does NOT post)."""
    try:
        # Generate the prompt for reply
        prompt = generate_reply_prompt(
            mention_text=mention_text,
            author_handle=author_handle,
            conversation_context=conversation_context,
            user_history=user_history
        )

        response_text = f"**Reply Generation**\n\n"
        response_text += f"**To**: @{author_handle}\n"
        response_text += f"**In Reply To**: {mention_id}\n"
        response_text += f"**Original**: \"{mention_text[:100]}{'...' if len(mention_text) > 100 else ''}\"\n\n"
        response_text += f"**Generation Prompt**:\n{prompt}\n\n"
        response_text += "---\n\n"
        response_text += "Generate the reply content, then use `twitter_reply_to_tweet` with:\n"
        response_text += f"- in_reply_to_tweet_id: \"{mention_id}\"\n"
        response_text += f"- text: [your generated reply]\n"
        response_text += f"- approved: true (after human confirms)\n\n"
        response_text += "**IMPORTANT**: Per Constitution Principle XIV, human approval is REQUIRED before posting."

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error generating reply: {e}")
        return [TextContent(type="text", text=f"Error generating reply: {str(e)}")]


async def handle_reply_to_tweet(
    in_reply_to_tweet_id: str,
    text: str,
    approved: bool = False
) -> list[TextContent]:
    """Post a reply to a tweet (requires human approval)."""
    try:
        if not approved:
            # Show draft and request approval
            response_text = f"**Reply Draft** (NOT POSTED)\n\n"
            response_text += f"**Replying to**: {in_reply_to_tweet_id}\n"
            response_text += f"**Content**: \"{text}\"\n"
            response_text += f"**Length**: {len(text)} characters\n\n"

            if len(text) > 280:
                response_text += "⚠️ Content exceeds 280 characters - will be posted as a thread.\n\n"

            response_text += "---\n\n"
            response_text += "**Human approval required** (Constitution Principle XIV)\n\n"
            response_text += "To post this reply, call twitter_reply_to_tweet again with `approved: true`.\n"
            response_text += "To modify, generate a new reply or edit the text."

            return [TextContent(type="text", text=response_text)]

        # Approved - proceed with posting
        client = get_twitter_client()
        result = await post_reply(
            client=client,
            text=text,
            in_reply_to_tweet_id=in_reply_to_tweet_id,
            approved=True
        )

        if not result["success"]:
            return [TextContent(
                type="text",
                text=f"Reply posting failed: {result['error']}"
            )]

        # Log the reply
        await _reply_audit_log.log_reply(
            mention_id=in_reply_to_tweet_id,
            reply_id=result["reply_id"],
            reply_text=text,
            author_handle="unknown"  # Would need to pass this in
        )

        response_text = f"**Reply Posted Successfully!**\n\n"
        response_text += f"**Reply ID**: {result['reply_id']}\n"
        response_text += f"**URL**: {result['url']}\n"
        response_text += f"**In Reply To**: {in_reply_to_tweet_id}\n"

        if result.get("is_thread"):
            response_text += f"**Thread IDs**: {', '.join(result['thread_ids'])}\n"

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error posting reply: {e}")
        return [TextContent(type="text", text=f"Error posting reply: {str(e)}")]


async def handle_mark_processed(
    mention_id: str,
    action: str,
    reply_id: Optional[str] = None
) -> list[TextContent]:
    """Mark a mention as processed."""
    try:
        await _mention_tracker.mark_processed(
            mention_id=mention_id,
            action=action,
            reply_id=reply_id
        )

        response_text = f"**Mention Marked as Processed**\n\n"
        response_text += f"**Mention ID**: {mention_id}\n"
        response_text += f"**Action**: {action}\n"
        if reply_id:
            response_text += f"**Reply ID**: {reply_id}\n"
        response_text += "\nThis mention will be filtered from future twitter_get_mentions calls."

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error marking mention processed: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_user_history(username: str) -> list[TextContent]:
    """Get interaction history with a Twitter user."""
    try:
        # Remove @ if present
        username = username.lstrip("@")

        history = await _interaction_history.get_history(username)

        if not history:
            response_text = f"**No interaction history found for @{username}**\n\n"
            response_text += "This is a new user - no prior interactions recorded."
            return [TextContent(type="text", text=response_text)]

        response_text = f"**Interaction History: @{username}**\n\n"
        response_text += f"**User ID**: {history.get('user_id', 'unknown')}\n"
        response_text += f"**First Interaction**: {history.get('first_interaction', 'unknown')}\n"
        response_text += f"**Last Interaction**: {history.get('last_interaction', 'unknown')}\n"
        response_text += f"**Total Interactions**: {history.get('interaction_count', 0)}\n"

        topics = history.get("topics", [])
        if topics:
            response_text += f"**Topics Discussed**: {', '.join(topics)}\n"

        response_text += f"**Sentiment**: {history.get('sentiment', 'neutral')}\n"

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error getting user history: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_heartbeat_cycle(
    post_heartbeat: bool = False,
    heartbeat_category: str | None = None,
    heartbeat_content: str | None = None,
    respond_to_netclaw_only: bool = True,
    dry_run: bool = False
) -> list[TextContent]:
    """
    Combined heartbeat cycle that:
    1. Fetches recent mentions
    2. Finds mentions in threads containing #netclaw
    3. Auto-responds to unprocessed mentions
    4. Optionally posts a heartbeat tweet
    """
    import requests
    from requests_oauthlib import OAuth1

    response_parts = []
    response_parts.append("## Twitter Heartbeat Cycle\n")

    try:
        # Get OAuth2 token with auto-refresh
        oauth2_token = get_oauth2_token_with_refresh()

        if oauth2_token:
            # Use OAuth2 (preferred - supports all features)
            headers = {"Authorization": f"Bearer {oauth2_token}"}
            auth = None  # Not needed for OAuth2
            use_oauth2 = True
            response_parts.append("**Auth**: OAuth 2.0 (auto-refresh enabled)\n")
        else:
            # Fallback to OAuth 1.0a
            auth = OAuth1(
                os.environ['TWITTER_API_KEY'],
                os.environ['TWITTER_API_SECRET'],
                os.environ['TWITTER_ACCESS_TOKEN'],
                os.environ['TWITTER_ACCESS_SECRET']
            )
            headers = {}
            use_oauth2 = False
            response_parts.append("**Auth**: OAuth 1.0a (fallback)\n")

        # Step 1: Get authenticated user ID
        if use_oauth2:
            user_response = requests.get("https://api.twitter.com/2/users/me", headers=headers)
        else:
            user_response = requests.get("https://api.twitter.com/2/users/me", auth=auth)

        if user_response.status_code != 200:
            return [TextContent(type="text", text=f"Error authenticating: {user_response.text}")]
        user_id = user_response.json()["data"]["id"]
        username = user_response.json()["data"]["username"]
        response_parts.append(f"**Authenticated as**: @{username} (ID: {user_id})\n")

        # Step 2: Fetch recent mentions
        mentions_params = {
            "max_results": 20,
            "tweet.fields": "created_at,conversation_id,author_id",
            "expansions": "author_id",
            "user.fields": "username"
        }
        if use_oauth2:
            mentions_response = requests.get(
                f"https://api.twitter.com/2/users/{user_id}/mentions",
                headers=headers,
                params=mentions_params
            )
        else:
            mentions_response = requests.get(
                f"https://api.twitter.com/2/users/{user_id}/mentions",
                auth=auth,
                params=mentions_params
            )

        mentions = []
        if mentions_response.status_code == 200:
            mentions_data = mentions_response.json()
            authors = {u["id"]: u["username"] for u in mentions_data.get("includes", {}).get("users", [])}

            for tweet in mentions_data.get("data", []):
                mention = Mention(
                    tweet_id=tweet["id"],
                    author_id=tweet["author_id"],
                    author_handle=authors.get(tweet["author_id"], "unknown"),
                    text=tweet["text"],
                    created_at=datetime.fromisoformat(tweet.get("created_at", "").replace("Z", "+00:00")) if tweet.get("created_at") else datetime.now(timezone.utc),
                    conversation_id=tweet.get("conversation_id"),
                    category=classify_mention(tweet["text"])
                )
                mentions.append(mention)

        response_parts.append(f"**Mentions found**: {len(mentions)}\n\n")

        # Step 3.5: CRITICAL - Filter out OLD mentions (only last 2 hours)
        # This prevents replying to old tweets that predate our tracking
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=2)
        recent_mentions = []
        old_skipped = 0
        for m in mentions:
            if m.created_at and m.created_at >= cutoff_time:
                recent_mentions.append(m)
            else:
                old_skipped += 1
                # Mark old ones as processed so we never see them again
                await _mention_tracker.mark_processed(m.tweet_id, "too_old")

        if old_skipped > 0:
            response_parts.append(f"**Skipped {old_skipped} old mentions** (older than 2 hours)\n")
        mentions = recent_mentions

        # Step 4: Filter to unprocessed mentions - ACTUALLY CHECK THE TRACKER!
        unprocessed = []
        for m in mentions:
            is_processed = await _mention_tracker.is_processed(m.tweet_id)
            if not is_processed:
                unprocessed.append(m)
        response_parts.append(f"**Unprocessed mentions**: {len(unprocessed)}\n")

        # Step 5: Check each mention for #netclaw - STRICT FILTERING
        # Only respond if #netclaw is explicitly in the mention text
        replies_posted = 0
        mentions_skipped = 0

        # ============ SAFETY CHECK: Master kill switch ============
        if not TWITTER_REPLIES_ENABLED:
            response_parts.append("\n⛔ **REPLIES DISABLED** - Set TWITTER_REPLIES_ENABLED=true to enable\n")
            for mention in unprocessed:
                await _mention_tracker.mark_processed(mention.tweet_id, "replies_disabled")
                mentions_skipped += 1
            response_parts.append(f"Marked {mentions_skipped} mentions as processed (replies disabled).\n")
            unprocessed = []  # Clear so the loop below doesn't run

        for mention in unprocessed:
            # ============ SAFETY CHECK: Never reply to ourselves ============
            if mention.author_id == user_id:
                logger.info(f"Skipping self-mention {mention.tweet_id}")
                await _mention_tracker.mark_processed(mention.tweet_id, "self_mention_skip")
                mentions_skipped += 1
                continue

            # STRICT: Only respond if #netclaw is EXPLICITLY in the mention text
            has_netclaw = "#netclaw" in mention.text.lower()

            # If respond_to_netclaw_only is True (default), ONLY respond to #netclaw mentions
            # This prevents replying to random mentions in threads
            should_respond = has_netclaw if respond_to_netclaw_only else True

            if not should_respond:
                mentions_skipped += 1
                # Mark as skipped to prevent re-processing
                await _mention_tracker.mark_processed(mention.tweet_id, "skipped_no_netclaw")
                continue

            # ============ SAFETY CHECK: Hard rate limit ============
            if replies_posted >= MAX_REPLIES_PER_CYCLE:
                response_parts.append(f"\n⚠️ **RATE LIMIT HIT** - Already posted {MAX_REPLIES_PER_CYCLE} replies this cycle")
                response_parts.append(f"\nMarking remaining {len(unprocessed) - replies_posted - mentions_skipped} mentions as rate-limited.\n")
                # Mark remaining as rate-limited
                await _mention_tracker.mark_processed(mention.tweet_id, "rate_limited")
                mentions_skipped += 1
                continue

            # Generate a CONTEXTUAL reply using Claude - actually READ what they said!
            category = mention.category.value if mention.category else "unknown"
            author = mention.author_handle or "user"
            tweet_text = mention.text

            # Use Claude to generate a contextual reply
            reply_text = await generate_contextual_reply(
                author=author,
                tweet_text=tweet_text,
                category=category
            )

            if dry_run:
                response_parts.append(f"\n**[DRY RUN]** Would reply to @{author}: {reply_text[:50]}...")
            else:
                # Post the reply (must use OAuth 1.0a for posting)
                post_auth = OAuth1(
                    os.environ['TWITTER_API_KEY'],
                    os.environ['TWITTER_API_SECRET'],
                    os.environ['TWITTER_ACCESS_TOKEN'],
                    os.environ['TWITTER_ACCESS_SECRET']
                )
                url = "https://api.twitter.com/2/tweets"
                payload = {
                    "text": reply_text,
                    "reply": {"in_reply_to_tweet_id": mention.tweet_id}
                }
                resp = requests.post(url, auth=post_auth, json=payload)

                if resp.status_code == 201:
                    reply_id = resp.json()['data']['id']
                    response_parts.append(f"\n✅ Replied to @{author} (ID: {reply_id})")
                    replies_posted += 1

                    # Mark as processed - MUST AWAIT!
                    await _mention_tracker.mark_processed(mention.tweet_id, "replied", reply_id)
                else:
                    response_parts.append(f"\n❌ Failed to reply to @{author}: {resp.status_code}")
                    # Mark as processed even on failure to prevent retry loops
                    await _mention_tracker.mark_processed(mention.tweet_id, "failed_to_reply")

        response_parts.append(f"\n\n**Summary**: {replies_posted} replies posted, {mentions_skipped} skipped\n")

        # Step 6: Check for John's own #netclaw commands
        response_parts.append("\n---\n## Self-Commands (John's #netclaw tweets)\n")
        try:
            # Use OAuth2 for reading (with auto-refresh), fallback to OAuth1
            own_tweets_params = {
                "max_results": 10,
                "tweet.fields": "created_at,conversation_id",
                "exclude": "retweets,replies"
            }
            if use_oauth2:
                own_tweets_response = requests.get(
                    f"https://api.twitter.com/2/users/{user_id}/tweets",
                    headers=headers,
                    params=own_tweets_params
                )
            else:
                own_tweets_response = requests.get(
                    f"https://api.twitter.com/2/users/{user_id}/tweets",
                    auth=auth,
                    params=own_tweets_params
                )
            self_commands = []
            if own_tweets_response.status_code == 200:
                own_data = own_tweets_response.json()
                for tweet in own_data.get("data", []):
                    if "#netclaw" in tweet["text"].lower():
                        cmd = Mention(
                            tweet_id=tweet["id"],
                            author_id=user_id,
                            author_handle="John_Capobianco",
                            text=tweet["text"],
                            created_at=datetime.fromisoformat(tweet.get("created_at", "").replace("Z", "+00:00")) if tweet.get("created_at") else datetime.now(timezone.utc),
                            conversation_id=tweet.get("conversation_id"),
                            category=MentionCategory.SELF_COMMAND
                        )
                        self_commands.append(cmd)
            response_parts.append(f"**Self-commands found**: {len(self_commands)}\n")

            commands_processed = 0
            for cmd in self_commands:
                # Skip if already processed
                if await _mention_tracker.is_processed(cmd.tweet_id):
                    continue

                # Parse the command
                parsed = parse_netclaw_command(cmd.text)
                response_parts.append(f"\n**Command**: {cmd.text[:80]}...")
                response_parts.append(f"\n  - Action: {parsed['action']}")
                response_parts.append(f"\n  - Target: {parsed['target']}")

                # Generate response based on command type
                if parsed['action'] == 'health_check' and parsed['target'] == 'cml':
                    reply_text = "🔍 Checking CML environment health... I'll run pyATS to verify device connectivity and report back! #netclaw"
                    # TODO: Actually call CML/pyATS tools and include results
                elif parsed['action'] == 'markmap':
                    reply_text = "🗺️ Creating a markmap visualization... Stand by for the mind map! #netclaw"
                    # TODO: Actually call markmap MCP and attach image
                elif parsed['action'] == 'bgp_check':
                    reply_text = "🔄 Checking BGP peer status... Running neighbor verification now! #netclaw"
                elif parsed['action'] == 'rfc_validate':
                    reply_text = "📋 Running RFC compliance validation... This may take a moment! #netclaw"
                else:
                    reply_text = f"📬 Received your #netclaw command! Processing: {parsed['clean_text'][:100]}"

                if dry_run:
                    response_parts.append(f"\n  - **[DRY RUN]** Would reply: {reply_text[:50]}...")
                else:
                    # Post reply (must use OAuth 1.0a for posting)
                    post_auth = OAuth1(
                        os.environ['TWITTER_API_KEY'],
                        os.environ['TWITTER_API_SECRET'],
                        os.environ['TWITTER_ACCESS_TOKEN'],
                        os.environ['TWITTER_ACCESS_SECRET']
                    )
                    url = "https://api.twitter.com/2/tweets"
                    payload = {
                        "text": reply_text,
                        "reply": {"in_reply_to_tweet_id": cmd.tweet_id}
                    }
                    resp = requests.post(url, auth=post_auth, json=payload)

                    if resp.status_code == 201:
                        reply_id = resp.json()['data']['id']
                        response_parts.append(f"\n  - ✅ Replied (ID: {reply_id})")
                        await _mention_tracker.mark_processed(cmd.tweet_id, "self_command_ack", reply_id)
                        commands_processed += 1
                    else:
                        response_parts.append(f"\n  - ❌ Failed: {resp.status_code}")
                        # Mark as processed even on failure to prevent retry loops
                        await _mention_tracker.mark_processed(cmd.tweet_id, "self_command_failed")

            response_parts.append(f"\n\n**Self-commands processed**: {commands_processed}\n")

        except Exception as e:
            response_parts.append(f"\n⚠️ Error checking self-commands: {e}\n")

        # Step 7: Optionally post heartbeat tweet
        if post_heartbeat and heartbeat_content:
            if dry_run:
                response_parts.append(f"\n**[DRY RUN]** Would post heartbeat: {heartbeat_content[:50]}...")
            else:
                result = await post_tweet_with_history(
                    content=heartbeat_content,
                    category=heartbeat_category,
                    is_heartbeat=True
                )
                response_parts.append(f"\n**Heartbeat posted**: {heartbeat_category}")

        return [TextContent(type="text", text="\n".join(response_parts))]

    except Exception as e:
        logger.error(f"Error in heartbeat cycle: {e}")
        return [TextContent(type="text", text=f"Error in heartbeat cycle: {str(e)}")]


async def main():
    """Run the MCP server."""
    logger.info("Starting Twitter MCP Server")

    # Verify credentials are configured
    required_vars = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_SECRET"
    ]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        logger.warning(f"Missing Twitter credentials: {missing}")
        logger.warning("Twitter tools will fail until credentials are configured")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
