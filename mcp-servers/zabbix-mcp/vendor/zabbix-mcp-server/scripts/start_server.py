#!/usr/bin/env python3
"""
Startup script for Zabbix MCP Server

This script validates the environment configuration and starts the MCP server
with proper error handling and logging.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zabbix_mcp_server.config import parse_bool_env


def setup_logging() -> None:
    """Setup logging configuration."""
    log_level = logging.DEBUG if parse_bool_env("DEBUG") else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def check_environment() -> bool:
    """Check if required environment variables are set.

    Returns:
        bool: True if environment is properly configured
    """
    logger = logging.getLogger(__name__)
    required_vars = ["ZABBIX_URL"]
    missing_vars: List[str] = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f" - {var}")
        print("\nPlease set these variables or create a .env file")
        return False

    # Check authentication configuration
    token = os.getenv("ZABBIX_TOKEN")
    user = os.getenv("ZABBIX_USER")
    password = os.getenv("ZABBIX_PASSWORD")

    if not token and not (user and password):
        logger.error("Authentication not configured")
        print("Error: Authentication not configured")
        print("Please set either:")
        print(" - ZABBIX_TOKEN (recommended)")
        print(" - Both ZABBIX_USER and ZABBIX_PASSWORD")
        return False

    # Check transport configuration
    transport = os.getenv("ZABBIX_MCP_TRANSPORT", "stdio").lower()
    if transport not in ["stdio", "streamable-http"]:
        logger.error(f"Invalid ZABBIX_MCP_TRANSPORT: {transport}")
        print(f"Error: Invalid ZABBIX_MCP_TRANSPORT: {transport}")
        print("Valid values are: stdio, streamable-http")
        return False

    if transport == "streamable-http":
        auth_type = os.getenv("AUTH_TYPE", "").lower()
        if auth_type != "no-auth":
            logger.error("AUTH_TYPE must be 'no-auth' for streamable-http transport")
            print(
                "Error: AUTH_TYPE must be set to 'no-auth' when using streamable-http transport"
            )
            return False

    return True


def show_configuration() -> None:
    """Display current configuration."""
    logger = logging.getLogger(__name__)

    print("\n" + "=" * 50)
    print("Zabbix MCP Server Configuration")
    print("=" * 50)

    # Zabbix URL
    zabbix_url = os.getenv("ZABBIX_URL", "Not configured")
    print(f"Zabbix URL: {zabbix_url}")
    logger.info(f"Zabbix URL: {zabbix_url}")

    # Authentication method
    if os.getenv("ZABBIX_TOKEN"):
        auth_method = "API Token"
        logger.info("Authentication: API Token")
    elif os.getenv("ZABBIX_USER"):
        auth_method = f"Username/Password ({os.getenv('ZABBIX_USER')})"
        logger.info(
            f"Authentication: Username/Password for user {os.getenv('ZABBIX_USER')}"
        )
    else:
        auth_method = "Not configured"
        logger.warning("Authentication: Not configured")

    print(f"Authentication: {auth_method}")

    # Transport configuration
    transport = os.getenv("ZABBIX_MCP_TRANSPORT", "stdio")
    print(f"Transport: {transport}")
    logger.info(f"Transport: {transport}")

    if transport == "streamable-http":
        host = os.getenv("ZABBIX_MCP_HOST", "127.0.0.1")
        port = os.getenv("ZABBIX_MCP_PORT", "8000")
        stateless = os.getenv("ZABBIX_MCP_STATELESS_HTTP", "false")
        auth_type = os.getenv("AUTH_TYPE", "Not set")

        print(f" - Host: {host}")
        print(f" - Port: {port}")
        print(f" - Stateless: {stateless}")
        print(f" - Auth Type: {auth_type}")

        logger.info(
            f"HTTP Transport - Host: {host}, Port: {port}, Stateless: {stateless}, Auth: {auth_type}"
        )

    # Read-only mode
    read_only = parse_bool_env("READ_ONLY", default=False)
    read_only_str = "Enabled" if read_only else "Disabled"
    print(f"Read-only mode: {read_only_str}")
    logger.info(f"Read-only mode: {read_only_str}")

    # SSL verification
    verify_ssl = parse_bool_env("VERIFY_SSL", default=True)
    verify_ssl_str = "Enabled" if verify_ssl else "Disabled"
    print(f"SSL verification: {verify_ssl_str}")
    logger.info(f"SSL verification: {verify_ssl_str}")

    # Debug mode
    debug_mode = parse_bool_env("DEBUG", default=False)
    debug_str = "Enabled" if debug_mode else "Disabled"
    print(f"Debug mode: {debug_str}")
    logger.info(f"Debug mode: {debug_str}")

    print("=" * 50)
    print()


def main() -> None:
    """Main startup function."""
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)

    print("Starting Zabbix MCP Server...")
    logger.info("Starting Zabbix MCP Server")

    try:
        # Check environment configuration
        if not check_environment():
            logger.error("Environment validation failed")
            sys.exit(1)

        # Show configuration
        show_configuration()

        # Import and run the server
        logger.info("Importing server module")
        from zabbix_mcp_server import main as server_main

        logger.info("Starting MCP server")
        print("🚀 Starting MCP server...")
        print("Press Ctrl+C to stop")
        print()

        server_main()

    except ImportError as e:
        logger.error(f"Import error: {e}")
        print(f"Error importing server: {e}")
        print("Please install dependencies: uv sync")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        print("\n👋 Server stopped by user")

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
