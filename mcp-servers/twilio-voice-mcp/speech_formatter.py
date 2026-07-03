"""
Speech Formatter for NetClaw Voice Integration
Feature 043: Full Voice Integration

Formats ANY MCP response for natural speech output.
Handles IPs, UUIDs, numbers, lists, timestamps, and sensitive data detection.
"""

import re
from datetime import datetime
from typing import Any
from abc import ABC, abstractmethod


# ═══════════════════════════════════════════════════════════════════════════════
# T003: SpeechFormatter Base Class
# ═══════════════════════════════════════════════════════════════════════════════

class SpeechFormatter(ABC):
    """Base class for speech formatting."""

    @abstractmethod
    def format(self, text: str) -> str:
        """Format text for speech output."""
        pass

    @abstractmethod
    def can_format(self, text: str) -> bool:
        """Check if this formatter can handle the text."""
        pass


class CompositeSpeechFormatter(SpeechFormatter):
    """Applies multiple formatters in sequence."""

    def __init__(self, formatters: list[SpeechFormatter] = None):
        self.formatters = formatters or []

    def add_formatter(self, formatter: SpeechFormatter) -> None:
        """Add a formatter to the chain."""
        self.formatters.append(formatter)

    def format(self, text: str) -> str:
        """Apply all formatters in sequence."""
        result = text
        for formatter in self.formatters:
            if formatter.can_format(result):
                result = formatter.format(result)
        return result

    def can_format(self, text: str) -> bool:
        """Returns True if any formatter can handle the text."""
        return any(f.can_format(text) for f in self.formatters)


# ═══════════════════════════════════════════════════════════════════════════════
# T004: Generic Formatters (IPs, UUIDs, numbers, lists, timestamps)
# ═══════════════════════════════════════════════════════════════════════════════

class IPAddressFormatter(SpeechFormatter):
    """Format IP addresses for natural speech."""

    # IPv4 pattern
    IPV4_PATTERN = re.compile(r'\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b')
    # IPv6 simplified pattern
    IPV6_PATTERN = re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b')

    def can_format(self, text: str) -> bool:
        return bool(self.IPV4_PATTERN.search(text) or self.IPV6_PATTERN.search(text))

    def format(self, text: str) -> str:
        # Format IPv4: "10.0.0.1" -> "10 dot 0 dot 0 dot 1"
        def format_ipv4(match):
            parts = [match.group(i) for i in range(1, 5)]
            return " dot ".join(parts)

        result = self.IPV4_PATTERN.sub(format_ipv4, text)

        # IPv6: Replace with abbreviated form
        result = self.IPV6_PATTERN.sub("an IPv6 address", result)

        return result


class UUIDFormatter(SpeechFormatter):
    """Format UUIDs for speech - abbreviate or omit."""

    # Standard UUID pattern
    UUID_PATTERN = re.compile(
        r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'
    )
    # Short ID pattern (8+ hex chars that look like IDs)
    SHORT_ID_PATTERN = re.compile(r'\b[0-9a-fA-F]{8,}\b')

    def can_format(self, text: str) -> bool:
        return bool(self.UUID_PATTERN.search(text))

    def format(self, text: str) -> str:
        def abbreviate_uuid(match):
            uuid = match.group(0)
            # Get last 4 characters for reference
            suffix = uuid[-4:].upper()
            return f"identifier ending in {suffix}"

        return self.UUID_PATTERN.sub(abbreviate_uuid, text)


class NumberFormatter(SpeechFormatter):
    """Format large numbers for natural speech."""

    # Large numbers (more than 4 digits)
    LARGE_NUMBER_PATTERN = re.compile(r'\b(\d{5,})\b')

    def can_format(self, text: str) -> bool:
        return bool(self.LARGE_NUMBER_PATTERN.search(text))

    def format(self, text: str) -> str:
        def format_large_number(match):
            num = int(match.group(1))
            if num >= 1_000_000_000:
                return f"{num / 1_000_000_000:.1f} billion"
            elif num >= 1_000_000:
                return f"{num / 1_000_000:.1f} million"
            elif num >= 1_000:
                return f"{num / 1_000:.1f} thousand"
            return match.group(0)

        return self.LARGE_NUMBER_PATTERN.sub(format_large_number, text)


class ListFormatter(SpeechFormatter):
    """Format long lists for speech - summarize if too many items."""

    MAX_ITEMS_SPOKEN = 5

    def can_format(self, text: str) -> bool:
        # Check for bullet points or numbered lists
        lines = text.split('\n')
        list_lines = [l for l in lines if l.strip().startswith(('-', '*', '•')) or
                      re.match(r'^\s*\d+[\.\)]\s', l)]
        return len(list_lines) > self.MAX_ITEMS_SPOKEN

    def format(self, text: str) -> str:
        lines = text.split('\n')
        list_items = []
        non_list_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('-', '*', '•')) or re.match(r'^\d+[\.\)]\s', stripped):
                # Extract item content
                item = re.sub(r'^[-*•\d\.\)]+\s*', '', stripped)
                list_items.append(item)
            else:
                non_list_lines.append(line)

        if len(list_items) <= self.MAX_ITEMS_SPOKEN:
            return text

        # Summarize: show first few, mention total
        summary_items = list_items[:self.MAX_ITEMS_SPOKEN]
        remaining = len(list_items) - self.MAX_ITEMS_SPOKEN

        result_parts = []
        for line in non_list_lines:
            if line.strip():
                result_parts.append(line)

        result_parts.append(f"Here are the first {self.MAX_ITEMS_SPOKEN} of {len(list_items)} items:")
        for item in summary_items:
            result_parts.append(f"  {item}")
        result_parts.append(f"Plus {remaining} more items.")

        return '\n'.join(result_parts)


class TimestampFormatter(SpeechFormatter):
    """Format timestamps for natural speech."""

    # ISO timestamp pattern
    ISO_PATTERN = re.compile(
        r'\b(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b'
    )
    # Unix timestamp (10-13 digits)
    UNIX_PATTERN = re.compile(r'\b(1[4-9]\d{8}|1[4-9]\d{11})\b')

    def can_format(self, text: str) -> bool:
        return bool(self.ISO_PATTERN.search(text) or self.UNIX_PATTERN.search(text))

    def format(self, text: str) -> str:
        def format_iso(match):
            try:
                year, month, day = match.group(1), match.group(2), match.group(3)
                hour, minute = match.group(4), match.group(5)

                dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
                now = datetime.now()

                # Relative time for recent timestamps
                diff = now - dt
                if diff.days == 0:
                    if diff.seconds < 3600:
                        mins = diff.seconds // 60
                        return f"{mins} minutes ago" if mins > 1 else "just now"
                    else:
                        hours = diff.seconds // 3600
                        return f"{hours} hours ago" if hours > 1 else "an hour ago"
                elif diff.days == 1:
                    return "yesterday"
                elif diff.days < 7:
                    return f"{diff.days} days ago"
                else:
                    return dt.strftime("%B %d")
            except (ValueError, TypeError):
                return match.group(0)

        def format_unix(match):
            try:
                ts = int(match.group(1))
                if ts > 1e12:  # Milliseconds
                    ts = ts // 1000
                dt = datetime.fromtimestamp(ts)
                now = datetime.now()
                diff = now - dt

                if diff.days == 0:
                    return "today"
                elif diff.days == 1:
                    return "yesterday"
                elif diff.days < 7:
                    return f"{diff.days} days ago"
                else:
                    return dt.strftime("%B %d")
            except (ValueError, OSError):
                return match.group(0)

        result = self.ISO_PATTERN.sub(format_iso, text)
        result = self.UNIX_PATTERN.sub(format_unix, result)
        return result


class MACAddressFormatter(SpeechFormatter):
    """Format MAC addresses for speech."""

    MAC_PATTERN = re.compile(r'\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b')

    def can_format(self, text: str) -> bool:
        return bool(self.MAC_PATTERN.search(text))

    def format(self, text: str) -> str:
        def format_mac(match):
            mac = match.group(0)
            # Just mention the last 4 characters
            suffix = mac[-5:].replace(':', '').replace('-', '').upper()
            return f"MAC address ending in {suffix}"

        return self.MAC_PATTERN.sub(format_mac, text)


# ═══════════════════════════════════════════════════════════════════════════════
# T005: Sensitive Data Detection (never speak credentials)
# ═══════════════════════════════════════════════════════════════════════════════

class SensitiveDataFormatter(SpeechFormatter):
    """Detect and redact sensitive data that should never be spoken."""

    # Credential patterns
    CREDENTIAL_PATTERNS = [
        # password=xxx, secret=xxx, key=xxx, token=xxx
        (re.compile(
            r'(password|passwd|secret|api[_-]?key|api[_-]?secret|token|auth[_-]?token|'
            r'access[_-]?token|bearer|private[_-]?key|ssh[_-]?key)\s*[:=]\s*\S+',
            re.IGNORECASE
        ), r'\1: [redacted for security]'),

        # API keys with common prefixes
        (re.compile(
            r'\b(sk|pk|ghp|gho|ghu|ghs|ghg|glpat|xox[abp]|AKIA|AIza)[A-Za-z0-9_-]{16,}\b'
        ), '[redacted API key]'),

        # AWS access keys
        (re.compile(r'\bAKIA[A-Z0-9]{16}\b'), '[AWS access key]'),

        # Generic long hex strings (potential secrets)
        (re.compile(r'\b[0-9a-fA-F]{40,}\b'), '[redacted credential]'),

        # Base64 encoded secrets (long, no spaces)
        (re.compile(r'\b[A-Za-z0-9+/]{50,}={0,2}\b'), '[redacted encoded value]'),

        # Twilio-specific
        (re.compile(r'\bAC[0-9a-f]{32}\b', re.IGNORECASE), '[Twilio account ID]'),
        (re.compile(r'\bSK[0-9a-f]{32}\b', re.IGNORECASE), '[Twilio API key]'),

        # Private keys
        (re.compile(r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----[\s\S]+?-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----'),
         '[private key redacted]'),

        # SSH keys
        (re.compile(r'ssh-(?:rsa|ed25519|ecdsa)\s+[A-Za-z0-9+/=]+'), '[SSH key redacted]'),
    ]

    # Words that indicate sensitive context
    SENSITIVE_CONTEXT_WORDS = [
        'password', 'secret', 'credential', 'token', 'key', 'auth',
        'private', 'confidential', 'sensitive'
    ]

    def can_format(self, text: str) -> bool:
        text_lower = text.lower()
        # Check for sensitive context words
        if any(word in text_lower for word in self.SENSITIVE_CONTEXT_WORDS):
            return True
        # Check for pattern matches
        for pattern, _ in self.CREDENTIAL_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def format(self, text: str) -> str:
        result = text
        for pattern, replacement in self.CREDENTIAL_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    @classmethod
    def contains_sensitive_data(cls, text: str) -> bool:
        """Check if text contains sensitive data without modifying it."""
        for pattern, _ in cls.CREDENTIAL_PATTERNS:
            if pattern.search(text):
                return True
        return False


class JSONFormatter(SpeechFormatter):
    """Format JSON responses for natural speech."""

    JSON_PATTERN = re.compile(r'\{[^{}]*\}|\[[^\[\]]*\]')

    def can_format(self, text: str) -> bool:
        return bool(self.JSON_PATTERN.search(text))

    def format(self, text: str) -> str:
        # Don't try to parse complex JSON, just make it more speakable
        result = text
        # Replace common JSON artifacts
        result = re.sub(r'[{}\[\]"]', ' ', result)
        result = re.sub(r'\s*:\s*', ': ', result)
        result = re.sub(r'\s*,\s*', ', ', result)
        result = re.sub(r'\s+', ' ', result)
        return result.strip()


# ═══════════════════════════════════════════════════════════════════════════════
# Main Speech Formatter Factory
# ═══════════════════════════════════════════════════════════════════════════════

def create_speech_formatter() -> CompositeSpeechFormatter:
    """Create a fully configured speech formatter with all formatters."""
    formatter = CompositeSpeechFormatter()

    # Order matters: sensitive data first, then structural, then cosmetic
    formatter.add_formatter(SensitiveDataFormatter())
    formatter.add_formatter(UUIDFormatter())
    formatter.add_formatter(IPAddressFormatter())
    formatter.add_formatter(MACAddressFormatter())
    formatter.add_formatter(TimestampFormatter())
    formatter.add_formatter(NumberFormatter())
    formatter.add_formatter(ListFormatter())
    formatter.add_formatter(JSONFormatter())

    return formatter


def format_for_speech(text: str) -> str:
    """
    Format text for natural speech output.

    This is the main entry point for the speech formatting pipeline.
    It applies all formatters in the correct order.

    Args:
        text: Raw text to format

    Returns:
        Text formatted for natural speech
    """
    if not text:
        return text

    formatter = create_speech_formatter()
    return formatter.format(text)


def is_safe_to_speak(text: str) -> bool:
    """
    Check if text is safe to speak aloud (no sensitive data).

    Args:
        text: Text to check

    Returns:
        True if safe to speak, False if contains sensitive data
    """
    return not SensitiveDataFormatter.contains_sensitive_data(text)


# ═══════════════════════════════════════════════════════════════════════════════
# Utility Functions
# ═══════════════════════════════════════════════════════════════════════════════

def summarize_for_voice(text: str, max_sentences: int = 3) -> str:
    """
    Summarize long text to a reasonable length for voice.

    Args:
        text: Text to summarize
        max_sentences: Maximum number of sentences to keep

    Returns:
        Summarized text
    """
    if not text:
        return text

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)

    if len(sentences) <= max_sentences:
        return text

    # Take first few sentences and add summary
    result = ' '.join(sentences[:max_sentences])
    remaining = len(sentences) - max_sentences

    if remaining > 0:
        result += f" And {remaining} more details available."

    return result


def make_speakable(text: str, max_length: int = 500) -> str:
    """
    Full pipeline: format, check safety, summarize if needed.

    Args:
        text: Raw text to process
        max_length: Maximum character length for output

    Returns:
        Text ready for TTS
    """
    if not text:
        return "No information available."

    # Format for speech
    result = format_for_speech(text)

    # Summarize if too long
    if len(result) > max_length:
        result = summarize_for_voice(result)

    # Final length check
    if len(result) > max_length:
        result = result[:max_length - 20] + "... and more details."

    return result
