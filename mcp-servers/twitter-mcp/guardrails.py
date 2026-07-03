"""
Content Guardrails for Twitter Integration

Validates and sanitizes tweet content to prevent sensitive data leakage.
Implements patterns for IP addresses, credentials, customer names, and internal naming.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class GuardrailAction(Enum):
    """Action to take when a guardrail pattern matches."""
    PASS = "pass"
    SANITIZE = "sanitize"
    BLOCK = "block"


@dataclass
class GuardrailMatch:
    """Result of a guardrail pattern match."""
    pattern_name: str
    action: GuardrailAction
    original: str
    replacement: Optional[str] = None
    description: str = ""


@dataclass
class GuardrailResult:
    """Result of guardrail validation."""
    passed: bool
    content: str
    matches: list[GuardrailMatch]
    blocked_reason: Optional[str] = None


# Guardrail pattern definitions
GUARDRAIL_PATTERNS = {
    "ipv4": {
        "pattern": r"\b(?!192\.0\.2\.|198\.51\.100\.|203\.0\.113\.)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "description": "Non-documentation IPv4 addresses",
        "action": GuardrailAction.SANITIZE,
        "replacement": "192.0.2.x",
    },
    "ipv6": {
        "pattern": r"\b(?!2001:db8:)[A-Fa-f0-9]{1,4}(:[A-Fa-f0-9]{1,4}){7}\b",
        "description": "Non-documentation IPv6 addresses",
        "action": GuardrailAction.SANITIZE,
        "replacement": "2001:db8::x",
    },
    "ipv6_compressed": {
        "pattern": r"\b(?!2001:db8::)[A-Fa-f0-9:]{17,}\b",
        "description": "Compressed IPv6 addresses",
        "action": GuardrailAction.SANITIZE,
        "replacement": "2001:db8::x",
    },
    "mac_address": {
        "pattern": r"\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b",
        "description": "MAC addresses",
        "action": GuardrailAction.BLOCK,
        "replacement": None,
    },
    "credential_pattern": {
        "pattern": r"\b(password|secret|key|token|credential|api_key|apikey|auth)s?\s*[=:]\s*\S+",
        "description": "Credential assignments",
        "action": GuardrailAction.BLOCK,
        "replacement": None,
    },
    "internal_hostname": {
        "pattern": r"\b(corp|internal|private|customer|prod|staging|dev)-[\w-]+\b",
        "description": "Internal naming conventions",
        "action": GuardrailAction.BLOCK,
        "replacement": None,
    },
    "aws_key": {
        "pattern": r"\bAKIA[0-9A-Z]{16}\b",
        "description": "AWS Access Key ID",
        "action": GuardrailAction.BLOCK,
        "replacement": None,
    },
    "private_key": {
        "pattern": r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
        "description": "Private key header",
        "action": GuardrailAction.BLOCK,
        "replacement": None,
    },
}

# Customer blocklist - can be extended via configuration
CUSTOMER_BLOCKLIST: set[str] = set()

# Required elements
REQUIRED_HASHTAG = "#netclaw"
MAX_TWEET_LENGTH = 280


def add_customer_to_blocklist(customer_name: str) -> None:
    """Add a customer name to the blocklist."""
    CUSTOMER_BLOCKLIST.add(customer_name.lower())


def remove_customer_from_blocklist(customer_name: str) -> None:
    """Remove a customer name from the blocklist."""
    CUSTOMER_BLOCKLIST.discard(customer_name.lower())


def validate_content(content: str, skip_guardrails: bool = False) -> GuardrailResult:
    """
    Validate tweet content against all guardrail patterns.

    Args:
        content: The tweet content to validate
        skip_guardrails: If True, skip all guardrail checks (not recommended)

    Returns:
        GuardrailResult with validation status and any modifications
    """
    if skip_guardrails:
        return GuardrailResult(
            passed=True,
            content=content,
            matches=[],
            blocked_reason=None
        )

    matches: list[GuardrailMatch] = []
    modified_content = content
    blocked = False
    blocked_reason = None

    # Check each guardrail pattern
    for name, config in GUARDRAIL_PATTERNS.items():
        pattern = re.compile(config["pattern"], re.IGNORECASE)
        found_matches = pattern.findall(modified_content)

        for match_text in found_matches:
            # Handle tuple matches from groups
            if isinstance(match_text, tuple):
                match_text = match_text[0] if match_text else ""

            action = config["action"]

            match_result = GuardrailMatch(
                pattern_name=name,
                action=action,
                original=match_text,
                replacement=config.get("replacement"),
                description=config["description"]
            )
            matches.append(match_result)

            if action == GuardrailAction.BLOCK:
                blocked = True
                blocked_reason = f"Content blocked: {config['description']} detected"
            elif action == GuardrailAction.SANITIZE and config.get("replacement"):
                # Replace the matched content with safe alternative
                modified_content = pattern.sub(config["replacement"], modified_content)

    # Check customer blocklist
    content_lower = modified_content.lower()
    for customer in CUSTOMER_BLOCKLIST:
        if customer in content_lower:
            matches.append(GuardrailMatch(
                pattern_name="customer_blocklist",
                action=GuardrailAction.BLOCK,
                original=customer,
                description="Customer name in blocklist"
            ))
            blocked = True
            blocked_reason = "Content blocked: Customer name detected"

    return GuardrailResult(
        passed=not blocked,
        content=modified_content,
        matches=matches,
        blocked_reason=blocked_reason
    )


def ensure_hashtag(content: str) -> str:
    """
    Ensure the content includes the #netclaw hashtag.

    Args:
        content: The tweet content

    Returns:
        Content with #netclaw hashtag added if missing
    """
    if REQUIRED_HASHTAG.lower() not in content.lower():
        # Add hashtag at the end if there's room
        if len(content) + len(REQUIRED_HASHTAG) + 1 <= MAX_TWEET_LENGTH:
            return f"{content} {REQUIRED_HASHTAG}"
        else:
            # Try to fit it by trimming content
            max_content_len = MAX_TWEET_LENGTH - len(REQUIRED_HASHTAG) - 4  # " ..." + " #netclaw"
            return f"{content[:max_content_len]}... {REQUIRED_HASHTAG}"
    return content


def validate_length(content: str) -> tuple[bool, int]:
    """
    Check if content fits within tweet length limit.

    Args:
        content: The tweet content

    Returns:
        Tuple of (is_valid, character_count)
    """
    length = len(content)
    return length <= MAX_TWEET_LENGTH, length


def prepare_tweet(content: str, skip_guardrails: bool = False) -> GuardrailResult:
    """
    Full tweet preparation: validate, sanitize, ensure hashtag.

    Args:
        content: Raw tweet content
        skip_guardrails: Skip guardrail checks (not recommended)

    Returns:
        GuardrailResult with prepared content or block reason
    """
    # First, validate against guardrails
    result = validate_content(content, skip_guardrails)

    if not result.passed:
        return result

    # Ensure hashtag is present
    result.content = ensure_hashtag(result.content)

    # Check final length
    is_valid, length = validate_length(result.content)
    if not is_valid:
        result.passed = False
        result.blocked_reason = f"Content exceeds 280 characters ({length} chars). Consider using a thread."

    return result
