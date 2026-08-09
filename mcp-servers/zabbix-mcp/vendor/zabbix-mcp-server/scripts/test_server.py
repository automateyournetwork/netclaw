#!/usr/bin/env python3
"""
Test script for Zabbix MCP Server

This script validates the server configuration and tests basic functionality
to ensure everything is working correctly with the unified zabbix_api tool.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def setup_logging() -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def test_import() -> bool:
    """Test if the server module can be imported.

    Returns:
        bool: True if import successful
    """
    try:
        print("🔍 Testing module import...")
        from zabbix_mcp_server import get_zabbix_client, is_read_operation, is_read_only

        print("✅ Module import successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("Please install dependencies: uv sync")
        return False
    except Exception as e:
        print(f"❌ Unexpected import error: {e}")
        return False


def test_environment() -> bool:
    """Test environment configuration.

    Returns:
        bool: True if environment is properly configured
    """
    print("\n🔍 Testing environment configuration...")

    zabbix_url = os.getenv("ZABBIX_URL")
    if not zabbix_url:
        print("❌ ZABBIX_URL not configured")
        return False

    print(f"✅ ZABBIX_URL: {zabbix_url}")

    token = os.getenv("ZABBIX_TOKEN")
    user = os.getenv("ZABBIX_USER")
    password = os.getenv("ZABBIX_PASSWORD")

    if token:
        print("✅ Authentication: API Token configured")
    elif user and password:
        print(f"✅ Authentication: Username/Password configured ({user})")
    else:
        print("❌ Authentication not configured")
        print("Please set either ZABBIX_TOKEN or both ZABBIX_USER and ZABBIX_PASSWORD")
        return False

    read_only = os.getenv("READ_ONLY", "false").lower() in ("true", "1", "yes")
    print(f"ℹ️  Read-only mode: {'Enabled' if read_only else 'Disabled'}")

    verify_ssl = os.getenv("VERIFY_SSL", "true").lower() in ("true", "1", "yes")
    print(f"ℹ️  SSL verification: {'Enabled' if verify_ssl else 'Disabled'}")

    return True


def test_connection() -> bool:
    """Test basic connection to Zabbix.

    Returns:
        bool: True if connection successful
    """
    print("\n🔍 Testing Zabbix connection...")

    try:
        from zabbix_mcp_server import get_zabbix_client

        client = get_zabbix_client()
        version_info = client.apiinfo.version()

        print(f"✅ Connected to Zabbix API version: {version_info}")
        return True

    except ValueError as e:
        if "environment variable" in str(e).lower():
            print(f"❌ Configuration error: {e}")
        else:
            print(f"❌ Connection failed: {e}")
        return False

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_unified_tool() -> bool:
    """Test the unified zabbix_api tool logic.

    Returns:
        bool: True if tool logic works correctly
    """
    print("\n🔍 Testing unified zabbix_api tool logic...")

    try:
        from zabbix_mcp_server import get_zabbix_client, is_read_operation

        print(" - Testing is_read_operation function...")
        # Test read operations (should return True)
        assert is_read_operation("host.get") == True, (
            "host.get should be read operation"
        )
        assert is_read_operation("item.get") == True, (
            "item.get should be read operation"
        )
        assert is_read_operation("apiinfo.version") == True, (
            "apiinfo.version should be read operation"
        )
        assert is_read_operation("template.get") == True, (
            "template.get should be read operation"
        )
        assert is_read_operation("problem.get") == True, (
            "problem.get should be read operation"
        )
        # Test write operations (should return False)
        assert is_read_operation("host.create") == False, (
            "host.create should NOT be read operation"
        )
        assert is_read_operation("host.update") == False, (
            "host.update should NOT be read operation"
        )
        assert is_read_operation("host.delete") == False, (
            "host.delete should NOT be read operation"
        )
        assert is_read_operation("host.massadd") == False, (
            "host.massadd should NOT be read operation"
        )
        assert is_read_operation("event.acknowledge") == False, (
            "event.acknowledge should NOT be read operation"
        )
        print(" ✅ Read operation detection working")

        client = get_zabbix_client()

        print(" - Testing apiinfo.version...")
        version = client.apiinfo.version()
        print(f" ✅ API version: {version}")

        print(" - Testing hostgroup.get...")
        groups = client.hostgroup.get(limit=1)
        if groups:
            print(f" ✅ Retrieved {len(groups)} host group(s)")
        else:
            print(" ⚠️  No host groups found (this might be normal)")

        print(" - Testing host.get...")
        hosts = client.host.get(limit=1, output=["hostid", "name"])
        if hosts:
            print(f" ✅ Retrieved {len(hosts)} host(s)")
            # Verify only requested fields are returned
            host_keys = set(hosts[0].keys())
            expected_keys = {"hostid", "name"}
            if host_keys == expected_keys:
                print(f" ✅ Output limited to requested fields: {list(host_keys)}")
            else:
                print(f" ⚠️  Expected fields {expected_keys}, got {host_keys}")
        else:
            print(" ⚠️  No hosts found (this might be normal)")

        print(" - Testing item.get...")
        items = client.item.get(limit=1)
        if items:
            print(f" ✅ Retrieved {len(items)} item(s)")
        else:
            print(" ⚠️  No items found (this might be normal)")

        print(" - Testing template.get...")
        templates = client.template.get(limit=1)
        if templates:
            print(f" ✅ Retrieved {len(templates)} template(s)")
        else:
            print(" ⚠️  No templates found (this might be normal)")

        # Test that output='extend' works but returns more fields
        print(" - Testing output='extend' (should return more fields)...")
        hosts_extend = client.host.get(limit=1, output="extend")
        if hosts_extend and len(hosts_extend[0].keys()) > 2:
            print(
                f" ✅ output='extend' returns {len(hosts_extend[0].keys())} fields (as expected)"
            )
        else:
            print(" ⚠️  output='extend' returned fewer fields than expected")

        print("✅ Unified tool logic tests successful")
        return True

    except AssertionError as e:
        print(f"❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unified tool logic tests failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_read_only_mode() -> bool:
    """Test read-only mode functionality.

    Returns:
        bool: True if read-only mode works correctly
    """
    read_only = os.getenv("READ_ONLY", "false").lower() in ("true", "1", "yes")

    if not read_only:
        print("\n⏭️  Skipping read-only mode test (not enabled)")
        return True

    print("\n🔍 Testing read-only mode...")

    try:
        from zabbix_mcp_server import is_read_operation, is_read_only

        print(" - Verifying read-only mode is enabled...")
        if not is_read_only():
            print(" ❌ Read-only mode should be enabled")
            return False
        print(" ✅ Read-only mode is enabled")

        print(" - Testing read operation detection...")
        if is_read_operation("hostgroup.create"):
            print(" ❌ hostgroup.create should NOT be a read operation")
            return False
        if not is_read_operation("hostgroup.get"):
            print(" ❌ hostgroup.get should be a read operation")
            return False
        print(" ✅ Read operation detection working correctly")

        print(" - Verifying write operations are blocked...")
        if not is_read_only() or is_read_operation("hostgroup.create"):
            print(
                " ⚠️  Cannot test blocking - read-only not enabled or operation is read"
            )
            return True

        print(" ✅ Write operations would be blocked in read-only mode")
        return True

    except Exception as e:
        print(f"❌ Unexpected error testing read-only mode: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_transport_config() -> bool:
    """Test transport configuration.

    Returns:
        bool: True if transport configuration is valid
    """
    print("\n🔍 Testing transport configuration...")

    try:
        from zabbix_mcp_server import get_transport_config

        config = get_transport_config()
        transport = config["transport"]

        print(f"✅ Transport type: {transport}")

        if transport == "streamable-http":
            print(f" - Host: {config['host']}")
            print(f" - Port: {config['port']}")
            print(f" - Stateless: {config['stateless_http']}")

            auth_type = os.getenv("AUTH_TYPE", "").lower()
            if auth_type == "no-auth":
                print(" ✅ AUTH_TYPE correctly set to 'no-auth'")
            else:
                print(" ❌ AUTH_TYPE must be set to 'no-auth' for HTTP transport")
                return False
        else:
            print(" ✅ STDIO transport configured correctly")

        return True

    except ValueError as e:
        print(f"❌ Transport configuration error: {e}")
        return False

    except Exception as e:
        print(f"❌ Unexpected error testing transport: {e}")
        return False


def show_summary(tests_passed: int, total_tests: int) -> None:
    """Show test summary.

    Args:
        tests_passed: Number of tests that passed
        total_tests: Total number of tests
    """
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    if tests_passed == total_tests:
        print(f"🎉 All {total_tests} tests passed!")
        print("✅ The Zabbix MCP Server is ready to use")
        print("\nNext steps:")
        print("1. Configure your MCP client (see MCP_SETUP.md)")
        print("2. Start the server: uv run python src/zabbix_mcp_server/server.py")
        print("3. Test with your MCP client")
        print("\nExample zabbix_api calls:")
        print(
            "  - Get hosts: zabbix_api(method='host.get', params={'output': ['hostid', 'name']})"
        )
        print(
            "  - Get items: zabbix_api(method='item.get', params={'hostids': ['10084'], 'output': ['itemid', 'name']})"
        )
        print(
            " - Get problems: zabbix_api(method='problem.get', params={'output': ['eventid', 'name'], 'recent': True})"
        )
        print("\n⚠️  AVOID using 'output': 'extend' - it's slow and verbose!")
        print("💡 Use specific fields instead: {'output': ['field1', 'field2']}")

    else:
        print(f"❌ {tests_passed}/{total_tests} tests passed")
        print("Please fix the issues above before using the server")

    print("=" * 50)


def main() -> None:
    """Main test function."""
    setup_logging()

    print("🧪 Zabbix MCP Server Test Suite")
    print("=" * 50)

    tests = [
        ("Module Import", test_import),
        ("Environment Configuration", test_environment),
        ("Transport Configuration", test_transport_config),
        ("Zabbix Connection", test_connection),
        ("Unified zabbix_api Tool", test_unified_tool),
        ("Read-Only Mode", test_read_only_mode),
    ]

    tests_passed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                tests_passed += 1
        except KeyboardInterrupt:
            print("\n\n⏹️  Tests interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error in {test_name}: {e}")

    show_summary(tests_passed, len(tests))

    if tests_passed == len(tests):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
