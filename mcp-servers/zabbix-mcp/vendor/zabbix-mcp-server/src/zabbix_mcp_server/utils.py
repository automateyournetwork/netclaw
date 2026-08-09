import re
import json
import logging
from typing import Any, List, Optional

from .config import EnvVars, parse_bool_env, get_env


logger = logging.getLogger(__name__)


MAX_REGEX_PATTERN_LENGTH = 200
DANGEROUS_REGEX_PATTERNS = [
    r"(\.\*)\*",
    r"(\.\*)\+",
    r"([a-z]\+)\+",
    r"([a-z]\+)\{",
    r"(\.\+)\+",
    r"(\.\+)\*",
]


def is_read_only() -> bool:
    """Check if the server is running in read-only mode.

    Returns:
        True if READ_ONLY is enabled, False otherwise.
    """
    return parse_bool_env(EnvVars.READ_ONLY, default=True)


def is_read_operation(method: str) -> bool:
    """Check if a Zabbix API method is a read operation.

    Args:
        method: Zabbix API method name (e.g., 'host.get', 'item.create')

    Returns:
        True if the method is a read operation, False otherwise.
    """
    if "." not in method:
        return False

    operation = method.split(".")[-1].lower()
    read_operations = {"get", "version", "check", "export"}

    return operation in read_operations


def format_response(data: Any) -> str:
    """Format API response data as JSON string.

    Args:
        data: Data to format (can be any JSON-serializable type)

    Returns:
        JSON string representation of the data.
    """
    return json.dumps(data, indent=2, default=str)


def is_safe_regex(pattern_str: str) -> bool:
    """Check if a regex pattern is safe to use.

    Args:
        pattern_str: The regex pattern string to check.

    Returns:
        True if the pattern is safe, False otherwise.
    """
    if len(pattern_str) > MAX_REGEX_PATTERN_LENGTH:
        return False
    pattern_lower = pattern_str.lower()
    for dangerous in DANGEROUS_REGEX_PATTERNS:
        if dangerous in pattern_lower:
            return False
    return True


def parse_regex_patterns(env_var: Optional[str]) -> List[re.Pattern]:
    """Parse comma-separated regex patterns from environment variable.

    Args:
        env_var: The environment variable value containing comma-separated patterns.

    Returns:
        List of compiled regex patterns.
    """
    patterns: List[re.Pattern] = []
    if not env_var:
        return patterns
    for pattern_str in env_var.split(","):
        pattern_str = pattern_str.strip()
        if pattern_str:
            if not is_safe_regex(pattern_str):
                logger.warning(
                    f"Regex pattern rejected (too long or potentially dangerous): {pattern_str}"
                )
                continue
            try:
                compiled = re.compile(pattern_str)
                patterns.append(compiled)
            except re.error as e:
                logger.warning(f"Invalid regex pattern: {pattern_str}: {e}")
    return patterns


def _check_blacklist(method: str, patterns: List[re.Pattern]) -> None:
    """Check if method matches any blacklist pattern.

    Args:
        method: Zabbix API method name to check
        patterns: List of compiled blacklist patterns

    Raises:
        ValueError: If method matches a blacklist pattern
    """
    for pattern in patterns:
        if pattern.match(method):
            raise ValueError(
                f"Method '{method}' is blacklisted. "
                f"Blacklist pattern '{pattern.pattern}' matched."
            )


def _check_whitelist(
    method: str, patterns: List[re.Pattern], whitelist_str: str
) -> None:
    """Check if method matches any whitelist pattern.

    Args:
        method: Zabbix API method name to check
        patterns: List of compiled whitelist patterns
        whitelist_str: Original whitelist string for error message

    Raises:
        ValueError: If method doesn't match any whitelist pattern
    """
    for pattern in patterns:
        if pattern.match(method):
            return

    whitelist_display = whitelist_str if whitelist_str else r".*"
    raise ValueError(
        f"Method '{method}' is not in whitelist. "
        f"Whitelist patterns: {whitelist_display}"
    )


def check_method_allowed(method: str) -> None:
    """Check if a Zabbix API method is allowed by whitelist/blacklist.

    Args:
        method: Zabbix API method name to check.

    Raises:
        ValueError: If the method is not allowed.
    """
    whitelist_env = get_env(EnvVars.ZABBIX_API_WHITELIST)
    blacklist_env = get_env(EnvVars.ZABBIX_API_BLACKLIST)

    whitelist_patterns = (
        parse_regex_patterns(whitelist_env) if whitelist_env else [re.compile(r".*")]
    )
    blacklist_patterns = parse_regex_patterns(blacklist_env)

    _check_blacklist(method, blacklist_patterns)
    _check_whitelist(method, whitelist_patterns, whitelist_env)
