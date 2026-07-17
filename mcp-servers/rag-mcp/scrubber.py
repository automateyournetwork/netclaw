"""Secret scrubbing for rag_snapshot (FR-072).

Deterministic regex redaction of credentials in live network output before
vectorization. Each secret class is replaced with <REDACTED:type> and counted
per type — zero counts are reported explicitly so the absence of scrubbing is
distinguishable from scrubber failure.
"""

import re
from typing import Dict, Tuple

# Order matters: more specific patterns first. Each entry: (type, compiled regex)
# The regexes replace ONLY the secret portion via the 'secret' named group.
_PATTERNS = [
    # Cisco enable secret/password with type 5/7/8/9 hashes
    (
        "enable_secret",
        re.compile(r"(?m)^(?P<prefix>\s*enable\s+(?:secret|password)(?:\s+level\s+\d+)?(?:\s+[5789])?\s+)(?P<secret>\S+)"),
    ),
    # username ... secret/password [type]
    (
        "user_secret",
        re.compile(r"(?m)^(?P<prefix>\s*username\s+\S+\s+(?:privilege\s+\d+\s+)?(?:secret|password)(?:\s+[05789])?\s+)(?P<secret>\S+)"),
    ),
    # SNMP community strings
    (
        "snmp_community",
        re.compile(r"(?m)^(?P<prefix>\s*snmp-server\s+community\s+)(?P<secret>\S+)"),
    ),
    # TACACS / RADIUS server keys
    (
        "aaa_key",
        re.compile(r"(?m)^(?P<prefix>\s*(?:tacacs|radius)(?:-server)?\s+(?:host\s+\S+\s+)?key(?:\s+[07])?\s+)(?P<secret>\S+)"),
    ),
    (
        "aaa_key",
        re.compile(r"(?m)^(?P<prefix>\s*key(?:\s+[07])?\s+)(?P<secret>\S+)(?=\s*$)"),
    ),
    # BGP / OSPF / ISIS authentication keys and key-strings
    (
        "routing_auth_key",
        re.compile(r"(?m)^(?P<prefix>\s*neighbor\s+\S+\s+password(?:\s+[07])?\s+)(?P<secret>\S+)"),
    ),
    (
        "routing_auth_key",
        re.compile(r"(?m)^(?P<prefix>\s*(?:ip\s+ospf|isis)\s+(?:authentication-key|message-digest-key\s+\d+\s+md5)(?:\s+[07])?\s+)(?P<secret>\S+)"),
    ),
    (
        "routing_auth_key",
        re.compile(r"(?m)^(?P<prefix>\s*key-string(?:\s+[07])?\s+)(?P<secret>\S+)"),
    ),
    (
        "routing_auth_key",
        re.compile(r"(?m)^(?P<prefix>\s*(?:area\s+\S+\s+)?authentication-key(?:\s+[07])?\s+)(?P<secret>\S+)"),
    ),
    # IPsec / IKE pre-shared keys
    (
        "pre_shared_key",
        re.compile(r"(?m)^(?P<prefix>\s*(?:crypto\s+isakmp\s+key\s+|pre-shared-key(?:\s+(?:local|remote))?\s+)(?:[06]\s+)?)(?P<secret>\S+)"),
    ),
    # Juniper $9$ obfuscated secrets (anywhere in line)
    (
        "juniper_secret",
        re.compile(r"(?P<prefix>)(?P<secret>\"?\$9\$[^\s;\"]+\"?)"),
    ),
    # Cisco type 5/8/9 hash strings appearing anywhere ($1$/$8$/$9$ MD5/scrypt/sha256)
    (
        "password_hash",
        re.compile(r"(?P<prefix>)(?P<secret>\$(?:1|8|9)\$[A-Za-z0-9./$]{8,})"),
    ),
    # Generic 'password <string>' lines (catch-all, after the specific ones)
    (
        "password",
        re.compile(r"(?m)^(?P<prefix>\s*(?:\S+\s+)?password(?:\s+[07])?\s+)(?P<secret>\S+)\s*$"),
    ),
]

# Every type we scrub — the report includes zeros for all of them (FR-072)
SECRET_TYPES = [
    "enable_secret",
    "user_secret",
    "snmp_community",
    "aaa_key",
    "routing_auth_key",
    "pre_shared_key",
    "juniper_secret",
    "password_hash",
    "password",
    "username_adjacent",
]


def scrub(content: str) -> Tuple[str, Dict[str, int]]:
    """Redact secrets. Returns (scrubbed_text, per-type counts incl. zeros)."""
    counts = {t: 0 for t in SECRET_TYPES}

    for secret_type, pattern in _PATTERNS:

        def _sub(m, secret_type=secret_type):
            counts[secret_type] += 1
            return f"{m.group('prefix')}<REDACTED:{secret_type}>"

        content = pattern.sub(_sub, content)

    # Usernames adjacent to (now-redacted) secrets (FR-072)
    username_pattern = re.compile(
        r"(?m)^(\s*username\s+)(\S+)(\s+(?:privilege\s+\d+\s+)?(?:secret|password))"
    )

    def _sub_username(m):
        counts["username_adjacent"] += 1
        return f"{m.group(1)}<REDACTED:username_adjacent>{m.group(3)}"

    content = username_pattern.sub(_sub_username, content)

    return content, counts
