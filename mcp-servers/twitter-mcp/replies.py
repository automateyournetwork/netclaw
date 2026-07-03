"""
Twitter Replies Module

Handles reply generation, posting, and audit logging for bidirectional Twitter interaction.
Part of feature 040-twitter-mentions.
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

import tweepy

from guardrails import prepare_tweet, GuardrailAction
from tweet_threading import create_thread

logger = logging.getLogger("twitter-mcp.replies")


class ReplyStatus(Enum):
    """Status of a reply."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    POSTED = "posted"
    REJECTED = "rejected"


@dataclass
class Reply:
    """Represents a reply to a mention."""
    in_reply_to_tweet_id: str
    text: str
    status: ReplyStatus = ReplyStatus.DRAFT
    reply_id: Optional[str] = None
    is_thread: bool = False
    thread_ids: Optional[List[str]] = None
    generated_at: Optional[datetime] = None
    approved: bool = False
    approved_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None


# Reply generation prompt template
REPLY_PROMPT_TEMPLATE = """You are @John_Capobianco, a CCIE-certified network engineer with deep expertise
in network automation, Cisco technologies, and NetClaw. Generate a helpful, technically accurate
reply to this Twitter mention.

**Mention from @{author_handle}:**
{mention_text}

{context_section}

**Guidelines:**
- Be helpful, accurate, and professional
- Use CCIE-level technical depth when appropriate
- Keep response under 280 characters if possible
- If longer, it will be split into a thread
- Include relevant commands or quick tips when applicable
- End with #netclaw hashtag
- Be friendly but not overly casual

**Generate a reply:**"""


def generate_reply_prompt(
    mention_text: str,
    author_handle: str,
    conversation_context: Optional[List[str]] = None,
    user_history: Optional[Dict] = None
) -> str:
    """
    Generate a prompt for reply generation.

    Args:
        mention_text: The mention to reply to
        author_handle: @username of the person who mentioned
        conversation_context: Optional list of parent tweet texts
        user_history: Optional interaction history with this user

    Returns:
        Formatted prompt string
    """
    context_section = ""

    if conversation_context:
        context_section += "\n**Conversation context:**\n"
        for i, ctx in enumerate(conversation_context[-3:], 1):  # Last 3 tweets
            context_section += f"{i}. {ctx}\n"

    if user_history:
        interaction_count = user_history.get("interaction_count", 0)
        topics = user_history.get("topics", [])
        if interaction_count > 1:
            context_section += f"\n**Prior interaction:** You've interacted {interaction_count} times before."
            if topics:
                context_section += f" Topics discussed: {', '.join(topics[-3:])}."

    return REPLY_PROMPT_TEMPLATE.format(
        author_handle=author_handle,
        mention_text=mention_text,
        context_section=context_section
    )


def validate_reply_content(text: str, skip_guardrails: bool = False) -> Dict[str, Any]:
    """
    Validate reply content through guardrails.

    Args:
        text: Reply text to validate
        skip_guardrails: Whether to skip guardrail checks

    Returns:
        Dict with 'valid', 'text', and optional 'reason'
    """
    if skip_guardrails:
        return {"valid": True, "text": text}

    result = prepare_tweet(text, skip_guardrails=False)

    if result.action == GuardrailAction.BLOCK:
        return {
            "valid": False,
            "text": text,
            "reason": f"Content blocked by guardrails: {', '.join(result.violations)}"
        }

    # Return sanitized text
    return {
        "valid": True,
        "text": result.sanitized_content,
        "warnings": result.violations if result.action == GuardrailAction.SANITIZE else []
    }


def prepare_reply_for_posting(text: str) -> Dict[str, Any]:
    """
    Prepare a reply for posting, handling length and threading.

    Args:
        text: Reply text

    Returns:
        Dict with 'is_thread', 'tweets' (list of tweet texts)
    """
    # Ensure #netclaw hashtag
    if "#netclaw" not in text.lower():
        if len(text) + 10 <= 280:
            text = text.rstrip() + " #netclaw"

    if len(text) <= 280:
        return {
            "is_thread": False,
            "tweets": [text]
        }

    # Need to split into thread
    thread_result = create_thread(text)
    return {
        "is_thread": True,
        "tweets": thread_result.tweets
    }


async def post_reply(
    client: tweepy.Client,
    text: str,
    in_reply_to_tweet_id: str,
    approved: bool = False
) -> Dict[str, Any]:
    """
    Post a reply to a tweet.

    IMPORTANT: Requires approved=True per Constitution Principle XIV.

    Args:
        client: Authenticated tweepy Client
        text: Reply text
        in_reply_to_tweet_id: Tweet ID to reply to
        approved: Human approval confirmation (MUST be True)

    Returns:
        Dict with 'success', 'reply_id', 'thread_ids', 'error'
    """
    if not approved:
        return {
            "success": False,
            "error": "Human approval required before posting (Constitution Principle XIV)"
        }

    # Validate content
    validation = validate_reply_content(text)
    if not validation["valid"]:
        return {
            "success": False,
            "error": validation["reason"]
        }

    # Prepare for posting
    prepared = prepare_reply_for_posting(validation["text"])

    try:
        if not prepared["is_thread"]:
            # Single tweet reply
            response = client.create_tweet(
                text=prepared["tweets"][0],
                in_reply_to_tweet_id=in_reply_to_tweet_id
            )
            return {
                "success": True,
                "reply_id": str(response.data["id"]),
                "is_thread": False,
                "url": f"https://twitter.com/i/web/status/{response.data['id']}"
            }
        else:
            # Thread reply
            thread_ids = []
            current_reply_to = in_reply_to_tweet_id

            for tweet_text in prepared["tweets"]:
                response = client.create_tweet(
                    text=tweet_text,
                    in_reply_to_tweet_id=current_reply_to
                )
                tweet_id = str(response.data["id"])
                thread_ids.append(tweet_id)
                current_reply_to = tweet_id

            return {
                "success": True,
                "reply_id": thread_ids[0],
                "thread_ids": thread_ids,
                "is_thread": True,
                "url": f"https://twitter.com/i/web/status/{thread_ids[0]}"
            }

    except tweepy.TooManyRequests:
        return {
            "success": False,
            "error": "Rate limit exceeded. Try again later."
        }
    except tweepy.Forbidden as e:
        return {
            "success": False,
            "error": f"Twitter API forbidden: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error posting reply: {e}")
        return {
            "success": False,
            "error": f"Failed to post reply: {str(e)}"
        }


async def verify_reply_threaded(
    client: tweepy.Client,
    reply_id: str,
    expected_parent_id: str
) -> bool:
    """
    Verify that a reply is correctly threaded to its parent.

    Args:
        client: Authenticated tweepy Client
        reply_id: The reply tweet ID
        expected_parent_id: Expected parent tweet ID

    Returns:
        True if correctly threaded, False otherwise
    """
    try:
        response = client.get_tweet(
            id=reply_id,
            tweet_fields=["conversation_id", "in_reply_to_user_id"],
            expansions=["referenced_tweets.id"]
        )

        if not response or not response.data:
            return False

        # Check referenced tweets for the parent
        if response.includes and "tweets" in response.includes:
            for ref_tweet in response.includes["tweets"]:
                if str(ref_tweet.id) == expected_parent_id:
                    return True

        return False

    except Exception as e:
        logger.warning(f"Error verifying reply threading: {e}")
        return False


class ReplyAuditLog:
    """Logs reply activity to Memory MCP for audit trail."""

    def __init__(self, memory_client=None):
        self.memory_client = memory_client

    async def log_reply(
        self,
        mention_id: str,
        reply_id: str,
        reply_text: str,
        author_handle: str,
        approved_by: str = "human"
    ):
        """Log a posted reply for audit."""
        if not self.memory_client:
            logger.info(f"Reply audit (no memory): {mention_id} -> {reply_id}")
            return

        try:
            key = f"twitter_reply_{reply_id}"
            value = {
                "mention_id": mention_id,
                "reply_id": reply_id,
                "reply_text": reply_text,
                "author_handle": author_handle,
                "approved_by": approved_by,
                "posted_at": datetime.utcnow().isoformat()
            }
            await self.memory_client.remember(key, value, ttl_days=7)
            logger.info(f"Reply audit logged: {mention_id} -> {reply_id}")

        except Exception as e:
            logger.warning(f"Error logging reply audit: {e}")

    async def get_recent_replies(self, limit: int = 10) -> List[Dict]:
        """Get recent reply audit logs."""
        # This would require a list/search operation in Memory MCP
        # For now, return empty - individual lookups work via key
        return []
