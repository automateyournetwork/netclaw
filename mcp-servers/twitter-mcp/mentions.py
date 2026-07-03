"""
Twitter Mentions Module

Handles mention detection, classification, and tracking for bidirectional Twitter interaction.
Part of feature 040-twitter-mentions.
"""

import os
import re
import json
import logging
import asyncio
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import tweepy

logger = logging.getLogger("twitter-mcp.mentions")


class MentionCategory(Enum):
    """Classification categories for incoming mentions."""
    NETCLAW_REQUEST = "netclaw_request"
    TECHNICAL_NETWORK = "technical_network"
    FRIENDLY = "friendly"
    OFF_TOPIC = "off_topic"
    SPAM = "spam"
    SELF_COMMAND = "self_command"  # John's own tweets with #netclaw commands


@dataclass
class Mention:
    """Represents a Twitter mention."""
    tweet_id: str
    author_id: str
    author_handle: str
    text: str
    created_at: datetime
    conversation_id: Optional[str] = None
    in_reply_to_tweet_id: Optional[str] = None
    category: Optional[MentionCategory] = None
    processed: bool = False
    processed_at: Optional[datetime] = None


@dataclass
class ConversationContext:
    """Thread context for a mention."""
    conversation_id: str
    tweets: List[Dict[str, Any]] = field(default_factory=list)
    fetched_at: Optional[datetime] = None


# Keywords for classification
NETCLAW_KEYWORDS = [
    "netclaw", "automation", "diagram", "mcp", "skill", "pyats",
    "openclaw", "automate", "script", "topology"
]

NETWORK_KEYWORDS = [
    "ospf", "bgp", "eigrp", "isis", "vlan", "routing", "switching",
    "firewall", "aci", "cisco", "juniper", "f5", "palo", "fortigate",
    "meraki", "arista", "nexus", "catalyst", "asa", "ftd", "ise",
    "netbox", "nautobot", "ansible", "terraform", "nso",
    "mpls", "vpn", "ipsec", "ssl", "tls", "acl", "nat", "dhcp", "dns",
    "snmp", "syslog", "netconf", "restconf", "yang", "grpc", "gnmi",
    "interface", "trunk", "port-channel", "lacp", "stp", "rstp",
    "qos", "cef", "arp", "mac", "layer2", "layer3", "subnet", "cidr"
]

FRIENDLY_KEYWORDS = [
    "thanks", "thank you", "thx", "ty", "hello", "hi", "hey",
    "awesome", "great", "love", "cool", "nice", "congrats",
    "welcome", "appreciate"
]


class ProcessedMentionTracker:
    """
    Tracks processed mentions to prevent duplicate handling.
    Uses FILE-BASED persistence to survive restarts.
    """

    def __init__(self, memory_client=None):
        """
        Initialize the tracker with file-based persistence.
        """
        self.memory_client = memory_client
        self._local_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(hours=72)  # 3 days retention

        # File-based persistence
        self._storage_dir = Path.home() / ".openclaw" / "twitter"
        self._storage_file = self._storage_dir / "processed_mentions.json"
        self._load_from_file()

    def _load_from_file(self):
        """Load processed mentions from disk on startup."""
        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            if self._storage_file.exists():
                with open(self._storage_file, 'r') as f:
                    data = json.load(f)
                    # Convert ISO strings back to datetime for TTL checking
                    now = datetime.utcnow()
                    for mention_id, info in data.items():
                        processed_at = datetime.fromisoformat(info.get("processed_at", now.isoformat()))
                        if now - processed_at < self._cache_ttl:
                            self._local_cache[mention_id] = info
                logger.info(f"🔒 Loaded {len(self._local_cache)} processed mentions from disk")
        except Exception as e:
            logger.warning(f"Failed to load processed mentions: {e}")
            self._local_cache = {}

    def _save_to_file(self):
        """Persist processed mentions to disk."""
        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            with open(self._storage_file, 'w') as f:
                json.dump(self._local_cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save processed mentions: {e}")

    async def is_processed(self, mention_id: str) -> bool:
        """Check if a mention has already been processed."""
        # Check local cache (loaded from file on startup)
        if mention_id in self._local_cache:
            info = self._local_cache[mention_id]
            processed_at = datetime.fromisoformat(info.get("processed_at", datetime.utcnow().isoformat()))
            if datetime.utcnow() - processed_at < self._cache_ttl:
                return True
            else:
                del self._local_cache[mention_id]
                self._save_to_file()

        return False

    async def mark_processed(self, mention_id: str, action: str, reply_id: Optional[str] = None):
        """
        Mark a mention as processed and persist to disk.
        """
        now = datetime.utcnow()
        self._local_cache[mention_id] = {
            "processed_at": now.isoformat(),
            "action": action,
            "reply_id": reply_id
        }
        # Persist immediately
        self._save_to_file()
        logger.info(f"🔒 Marked mention {mention_id} as processed ({action})")

    def cleanup_cache(self):
        """Remove expired entries from cache and save."""
        now = datetime.utcnow()
        expired = []
        for mid, info in self._local_cache.items():
            processed_at = datetime.fromisoformat(info.get("processed_at", now.isoformat()))
            if now - processed_at >= self._cache_ttl:
                expired.append(mid)
        for mid in expired:
            del self._local_cache[mid]
        if expired:
            self._save_to_file()
            logger.info(f"🔒 Cleaned up {len(expired)} expired mentions")


def classify_mention(text: str, author_data: Optional[Dict] = None) -> MentionCategory:
    """
    Classify a mention into response categories.

    Args:
        text: The mention text
        author_data: Optional author metadata for spam detection

    Returns:
        MentionCategory indicating how to handle the mention
    """
    text_lower = text.lower()

    # Check for spam first
    if author_data and is_likely_spam(author_data, text):
        return MentionCategory.SPAM

    # Check for NetClaw-related requests
    if any(kw in text_lower for kw in NETCLAW_KEYWORDS):
        return MentionCategory.NETCLAW_REQUEST

    # Check for technical network topics
    if any(kw in text_lower for kw in NETWORK_KEYWORDS):
        return MentionCategory.TECHNICAL_NETWORK

    # Check for friendly engagement
    if any(kw in text_lower for kw in FRIENDLY_KEYWORDS):
        return MentionCategory.FRIENDLY

    # Default to off-topic
    return MentionCategory.OFF_TOPIC


def is_likely_spam(author_data: Dict, tweet_text: str) -> bool:
    """
    Detect likely spam/bot accounts using heuristics.

    Heuristics per research.md:
    1. Account created within last 7 days
    2. Following/followers ratio > 100:1
    3. Username contains 8+ digits
    4. Known spam patterns

    Args:
        author_data: Author metadata from Twitter API
        tweet_text: The mention text

    Returns:
        True if likely spam, False otherwise
    """
    # Check account age
    created_at_str = author_data.get("created_at")
    if created_at_str:
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            if (datetime.now(created_at.tzinfo) - created_at).days < 7:
                logger.debug(f"Spam heuristic: Account too new")
                return True
        except (ValueError, TypeError):
            pass

    # Check follower ratio
    public_metrics = author_data.get("public_metrics", {})
    following = public_metrics.get("following_count", 0)
    followers = public_metrics.get("followers_count", 1)
    if following > 0 and followers > 0:
        ratio = following / max(followers, 1)
        if ratio > 100:
            logger.debug(f"Spam heuristic: Following/followers ratio {ratio}")
            return True

    # Check username for excessive digits
    username = author_data.get("username", "")
    digit_count = sum(1 for c in username if c.isdigit())
    if digit_count >= 8:
        logger.debug(f"Spam heuristic: Username has {digit_count} digits")
        return True

    # Check for common spam patterns in text
    spam_patterns = [
        r"crypto", r"nft", r"giveaway", r"airdrop",
        r"dm me", r"check bio", r"click link",
        r"\$\d+k", r"make money", r"earn \$"
    ]
    text_lower = tweet_text.lower()
    for pattern in spam_patterns:
        if re.search(pattern, text_lower):
            logger.debug(f"Spam heuristic: Matched pattern '{pattern}'")
            return True

    return False


async def get_authenticated_user_id(client: tweepy.Client) -> str:
    """
    Get the authenticated user's Twitter ID.

    Args:
        client: Authenticated tweepy Client

    Returns:
        User ID string for the authenticated account
    """
    # Get the authenticated user's info
    me = client.get_me(user_fields=["id", "username"])
    if me and me.data:
        logger.info(f"Authenticated as @{me.data.username} (ID: {me.data.id})")
        return str(me.data.id)
    raise ValueError("Could not get authenticated user ID")


async def get_authenticated_user_id_oauth2(oauth2_token: str) -> str:
    """
    Get the authenticated user's Twitter ID using OAuth 2.0.

    Args:
        oauth2_token: OAuth 2.0 Bearer Token

    Returns:
        User ID string for the authenticated account
    """
    headers = {
        "Authorization": f"Bearer {oauth2_token}",
        "Content-Type": "application/json"
    }
    response = requests.get(
        "https://api.twitter.com/2/users/me",
        headers=headers
    )
    if response.status_code == 200:
        data = response.json()
        user_id = data["data"]["id"]
        username = data["data"]["username"]
        logger.info(f"Authenticated as @{username} (ID: {user_id})")
        return user_id
    raise ValueError(f"Could not get authenticated user ID: {response.text}")


async def fetch_mentions(
    client: tweepy.Client,
    user_id: str,
    limit: int = 10,
    since_id: Optional[str] = None
) -> List[Mention]:
    """
    Fetch recent mentions for a user.

    Args:
        client: Authenticated tweepy Client
        user_id: Twitter user ID to get mentions for
        limit: Maximum number of mentions to return
        since_id: Only return mentions newer than this tweet ID

    Returns:
        List of Mention objects
    """
    try:
        response = client.get_users_mentions(
            id=user_id,
            max_results=min(limit, 100),
            since_id=since_id,
            tweet_fields=["created_at", "conversation_id", "in_reply_to_user_id", "author_id"],
            expansions=["author_id"],
            user_fields=["username", "created_at", "public_metrics"]
        )

        if not response or not response.data:
            return []

        # Build author lookup
        authors = {}
        if response.includes and "users" in response.includes:
            for user in response.includes["users"]:
                authors[str(user.id)] = {
                    "username": user.username,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "public_metrics": user.public_metrics if hasattr(user, "public_metrics") else {}
                }

        mentions = []
        for tweet in response.data:
            author_id = str(tweet.author_id)
            author_data = authors.get(author_id, {})

            mention = Mention(
                tweet_id=str(tweet.id),
                author_id=author_id,
                author_handle=author_data.get("username", "unknown"),
                text=tweet.text,
                created_at=tweet.created_at or datetime.utcnow(),
                conversation_id=str(tweet.conversation_id) if tweet.conversation_id else None,
                in_reply_to_tweet_id=str(tweet.in_reply_to_user_id) if tweet.in_reply_to_user_id else None
            )

            # Classify the mention
            mention.category = classify_mention(tweet.text, author_data)

            mentions.append(mention)

        return mentions

    except tweepy.TooManyRequests as e:
        logger.warning(f"Rate limited when fetching mentions: {e}")
        raise
    except Exception as e:
        logger.error(f"Error fetching mentions: {e}")
        raise


async def fetch_mentions_oauth2(
    oauth2_token: str,
    user_id: str,
    limit: int = 10,
    since_id: Optional[str] = None
) -> List[Mention]:
    """
    Fetch recent mentions using OAuth 2.0 (required for pay-as-you-go tier).

    Args:
        oauth2_token: OAuth 2.0 Bearer Token
        user_id: Twitter user ID to get mentions for
        limit: Maximum number of mentions to return
        since_id: Only return mentions newer than this tweet ID

    Returns:
        List of Mention objects
    """
    headers = {
        "Authorization": f"Bearer {oauth2_token}",
        "Content-Type": "application/json"
    }

    params = {
        "max_results": max(5, min(limit, 100)),  # API requires between 5-100
        "tweet.fields": "created_at,conversation_id,in_reply_to_user_id,author_id",
        "expansions": "author_id",
        "user.fields": "username,created_at,public_metrics"
    }
    if since_id:
        params["since_id"] = since_id

    try:
        response = requests.get(
            f"https://api.twitter.com/2/users/{user_id}/mentions",
            headers=headers,
            params=params
        )

        if response.status_code == 429:
            raise tweepy.TooManyRequests(response)

        if response.status_code != 200:
            logger.error(f"Error fetching mentions: {response.text}")
            return []

        data = response.json()

        if "data" not in data:
            return []

        # Build author lookup
        authors = {}
        if "includes" in data and "users" in data["includes"]:
            for user in data["includes"]["users"]:
                authors[user["id"]] = {
                    "username": user["username"],
                    "created_at": user.get("created_at"),
                    "public_metrics": user.get("public_metrics", {})
                }

        mentions = []
        for tweet in data["data"]:
            author_id = tweet["author_id"]
            author_data = authors.get(author_id, {})

            mention = Mention(
                tweet_id=tweet["id"],
                author_id=author_id,
                author_handle=author_data.get("username", "unknown"),
                text=tweet["text"],
                created_at=datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00")) if tweet.get("created_at") else datetime.utcnow(),
                conversation_id=tweet.get("conversation_id"),
                in_reply_to_tweet_id=tweet.get("in_reply_to_user_id")
            )

            # Classify the mention
            mention.category = classify_mention(tweet["text"], author_data)

            mentions.append(mention)

        return mentions

    except Exception as e:
        logger.error(f"Error fetching mentions: {e}")
        raise


async def fetch_own_tweets_with_netclaw(
    oauth2_token: str,
    user_id: str,
    limit: int = 10,
    since_id: Optional[str] = None
) -> List[Mention]:
    """
    Fetch John's own recent tweets that contain #netclaw (self-commands).

    This allows John to post a tweet like:
    "Hey #netclaw is the CML environment healthy? Make me a markmap!"

    And have the heartbeat cycle pick it up as a command to execute.

    Args:
        oauth2_token: OAuth 2.0 Bearer Token
        user_id: Twitter user ID (John's ID)
        limit: Maximum number of tweets to return
        since_id: Only return tweets newer than this ID

    Returns:
        List of Mention objects with category=SELF_COMMAND
    """
    headers = {
        "Authorization": f"Bearer {oauth2_token}",
        "Content-Type": "application/json"
    }

    params = {
        "max_results": max(5, min(limit, 100)),
        "tweet.fields": "created_at,conversation_id,in_reply_to_user_id,author_id",
        "exclude": "retweets,replies"  # Only original tweets, not replies
    }
    if since_id:
        params["since_id"] = since_id

    try:
        response = requests.get(
            f"https://api.twitter.com/2/users/{user_id}/tweets",
            headers=headers,
            params=params
        )

        if response.status_code == 429:
            raise tweepy.TooManyRequests(response)

        if response.status_code != 200:
            logger.error(f"Error fetching own tweets: {response.text}")
            return []

        data = response.json()

        if "data" not in data:
            return []

        commands = []
        for tweet in data["data"]:
            text = tweet["text"].lower()

            # Only include tweets with #netclaw
            if "#netclaw" not in text:
                continue

            command = Mention(
                tweet_id=tweet["id"],
                author_id=user_id,
                author_handle="John_Capobianco",  # It's John's own tweet
                text=tweet["text"],
                created_at=datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00")) if tweet.get("created_at") else datetime.utcnow(),
                conversation_id=tweet.get("conversation_id"),
                in_reply_to_tweet_id=None,
                category=MentionCategory.SELF_COMMAND
            )
            commands.append(command)

        logger.info(f"Found {len(commands)} #netclaw self-commands")
        return commands

    except Exception as e:
        logger.error(f"Error fetching own tweets: {e}")
        raise


def parse_netclaw_command(text: str) -> Dict[str, Any]:
    """
    Parse a #netclaw command from a tweet.

    Examples:
        "Hey #netclaw is CML healthy?" -> {"action": "health_check", "target": "cml"}
        "#netclaw make a markmap of the topology" -> {"action": "markmap", "target": "topology"}
        "#netclaw check BGP peers" -> {"action": "check", "target": "bgp"}

    Returns:
        Dict with parsed command details
    """
    text_lower = text.lower()

    # Remove the #netclaw tag and common prefixes
    clean = re.sub(r'#netclaw', '', text_lower, flags=re.IGNORECASE)
    clean = re.sub(r'^(hey|hi|hello|please|can you|could you)\s*,?\s*', '', clean.strip())

    command = {
        "raw_text": text,
        "clean_text": clean.strip(),
        "action": "unknown",
        "target": None,
        "details": {}
    }

    # Detect action type
    if any(word in clean for word in ["health", "healthy", "status", "check"]):
        command["action"] = "health_check"
    elif any(word in clean for word in ["markmap", "mindmap", "mind map", "diagram"]):
        command["action"] = "markmap"
    elif any(word in clean for word in ["topology", "topo"]):
        command["action"] = "topology"
    elif any(word in clean for word in ["bgp", "peer", "neighbor"]):
        command["action"] = "bgp_check"
    elif any(word in clean for word in ["interface", "port"]):
        command["action"] = "interface_check"
    elif any(word in clean for word in ["config", "configuration"]):
        command["action"] = "config_check"
    elif any(word in clean for word in ["rfc", "validate", "compliance"]):
        command["action"] = "rfc_validate"

    # Detect target system
    if "cml" in clean or "cisco modeling" in clean:
        command["target"] = "cml"
    elif "netbox" in clean:
        command["target"] = "netbox"
    elif "pyats" in clean or "genie" in clean:
        command["target"] = "pyats"
    elif "network" in clean:
        command["target"] = "network"

    return command


async def fetch_mentions_with_retry(
    client: tweepy.Client,
    user_id: str,
    limit: int = 10,
    since_id: Optional[str] = None,
    max_retries: int = 3
) -> List[Mention]:
    """
    Fetch mentions with exponential backoff on rate limits.

    Args:
        client: Authenticated tweepy Client
        user_id: Twitter user ID
        limit: Maximum mentions to return
        since_id: Only return newer mentions
        max_retries: Maximum retry attempts

    Returns:
        List of Mention objects
    """
    for attempt in range(max_retries):
        try:
            return await fetch_mentions(client, user_id, limit, since_id)
        except tweepy.TooManyRequests:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 60  # 1, 2, 4 minutes
                logger.warning(f"Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                logger.error("Rate limit exceeded after all retries")
                raise
    return []


async def get_conversation_context(
    client: tweepy.Client,
    tweet_id: str,
    max_depth: int = 5
) -> ConversationContext:
    """
    Retrieve conversation context (parent tweets) for a mention.

    Args:
        client: Authenticated tweepy Client
        tweet_id: The tweet ID to get context for
        max_depth: Maximum number of parent tweets to retrieve

    Returns:
        ConversationContext with parent tweets
    """
    context = ConversationContext(conversation_id="", fetched_at=datetime.utcnow())
    tweets = []
    current_id = tweet_id

    for _ in range(max_depth):
        try:
            response = client.get_tweet(
                id=current_id,
                tweet_fields=["conversation_id", "in_reply_to_user_id", "author_id", "created_at"],
                expansions=["author_id", "referenced_tweets.id"],
                user_fields=["username"]
            )

            if not response or not response.data:
                break

            tweet = response.data

            # Set conversation ID from first tweet
            if not context.conversation_id and tweet.conversation_id:
                context.conversation_id = str(tweet.conversation_id)

            # Get author info
            author_username = "unknown"
            if response.includes and "users" in response.includes:
                for user in response.includes["users"]:
                    if str(user.id) == str(tweet.author_id):
                        author_username = user.username
                        break

            tweets.append({
                "tweet_id": str(tweet.id),
                "author_handle": author_username,
                "text": tweet.text,
                "created_at": tweet.created_at.isoformat() if tweet.created_at else None
            })

            # Find parent tweet
            parent_id = None
            if response.includes and "tweets" in response.includes:
                for ref_tweet in response.includes["tweets"]:
                    # This is the replied-to tweet
                    parent_id = str(ref_tweet.id)
                    break

            if not parent_id:
                break

            current_id = parent_id

        except Exception as e:
            logger.warning(f"Error fetching conversation context: {e}")
            break

    # Reverse to get chronological order (oldest first)
    context.tweets = list(reversed(tweets))
    return context


class InteractionHistory:
    """Manages interaction history with Twitter users via Memory MCP."""

    def __init__(self, memory_client=None):
        self.memory_client = memory_client

    async def get_history(self, username: str) -> Optional[Dict]:
        """Get interaction history for a user."""
        if not self.memory_client:
            return None

        try:
            key = f"twitter_user_{username.lower()}"
            return await self.memory_client.recall(key)
        except Exception as e:
            logger.warning(f"Error getting user history: {e}")
            return None

    async def update_history(
        self,
        username: str,
        user_id: str,
        topic: Optional[str] = None
    ):
        """Update interaction history for a user."""
        if not self.memory_client:
            return

        try:
            key = f"twitter_user_{username.lower()}"
            existing = await self.memory_client.recall(key) or {}

            now = datetime.utcnow().isoformat()
            history = {
                "user_handle": username,
                "user_id": user_id,
                "first_interaction": existing.get("first_interaction", now),
                "last_interaction": now,
                "interaction_count": existing.get("interaction_count", 0) + 1,
                "topics": existing.get("topics", []),
                "sentiment": existing.get("sentiment", "neutral")
            }

            if topic and topic not in history["topics"]:
                history["topics"].append(topic)
                # Keep only last 10 topics
                history["topics"] = history["topics"][-10:]

            await self.memory_client.remember(key, history, ttl_days=30)

        except Exception as e:
            logger.warning(f"Error updating user history: {e}")
