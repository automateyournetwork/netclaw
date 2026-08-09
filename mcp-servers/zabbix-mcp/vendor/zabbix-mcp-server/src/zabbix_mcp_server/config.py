#!/usr/bin/env python3
"""
Centralized configuration for Zabbix MCP Server.

This module defines all environment variable names and provides
utility functions for parsing configuration values.
"""

import logging
import os
from typing import Optional


class EnvVars:
    """Environment variable names."""

    ZABBIX_URL = "ZABBIX_URL"
    ZABBIX_TOKEN = "ZABBIX_TOKEN"
    ZABBIX_USER = "ZABBIX_USER"
    ZABBIX_PASSWORD = "ZABBIX_PASSWORD"
    READ_ONLY = "READ_ONLY"
    VERIFY_SSL = "VERIFY_SSL"
    ZABBIX_API_WHITELIST = "ZABBIX_API_WHITELIST"
    ZABBIX_API_BLACKLIST = "ZABBIX_API_BLACKLIST"
    ZABBIX_SKIP_VERSION_CHECK = "ZABBIX_SKIP_VERSION_CHECK"
    ZABBIX_API_TIMEOUT = "ZABBIX_API_TIMEOUT"
    ZABBIX_MCP_TRANSPORT = "ZABBIX_MCP_TRANSPORT"
    ZABBIX_MCP_HOST = "ZABBIX_MCP_HOST"
    ZABBIX_MCP_PORT = "ZABBIX_MCP_PORT"
    ZABBIX_MCP_STATELESS_HTTP = "ZABBIX_MCP_STATELESS_HTTP"
    AUTH_TYPE = "AUTH_TYPE"
    DEBUG = "DEBUG"


def parse_bool_env(var_name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable.

    Args:
        var_name: Name of the environment variable
        default: Default value if not set

    Returns:
        Boolean value parsed from environment variable
    """
    value = os.getenv(var_name, str(default)).lower()
    return value in ("true", "1", "yes")


def parse_int_env(var_name: str, default: int) -> int:
    """Parse an integer environment variable.

    Args:
        var_name: Name of the environment variable
        default: Default value if not set or invalid

    Returns:
        Integer value parsed from environment variable
    """
    value = os.getenv(var_name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_env(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """Get an environment variable value.

    Args:
        var_name: Name of the environment variable
        default: Default value if not set

    Returns:
        Environment variable value or default
    """
    return os.getenv(var_name, default)


def setup_logging(debug: bool = False) -> None:
    """Setup centralized logging configuration.

    Args:
        debug: If True, set logging level to DEBUG, otherwise INFO
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
