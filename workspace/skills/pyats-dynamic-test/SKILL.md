---
name: pyats-dynamic-test
description: "Generate and execute deterministic pyATS aetest validation scripts - interface state, OSPF neighbors, BGP paths, ping matrices, and custom compliance tests"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# Dynamic pyATS Test Execution

Generate and execute deterministic pyATS aetest validation scripts using the `pyats_run_dynamic_test` tool. This skill covers how to write complete aetest scripts with embedded TEST_DATA, pass them as the `test_script` parameter, and interpret results.

## When to Use

- Automated pass/fail validation after configuration changes
- Compliance checks that require multi-step assertions
- Regression testing before and after maintenance windows
- Data-driven validation across multiple interfaces, neighbors, or routes
- Any scenario where you need a formal test report with PASSED/FAILED verdicts

## How the Tool Works

The `pyats_run_dynamic_test` tool accepts a **complete Python aetest script as a string**. The script is executed in a sandboxed environment with a 300-second timeout.

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_dynamic_test '{"test_script":"<FULL PYTHON SOURCE CODE>"}'
```

The `test_script` parameter takes the **entire Python source code** as a single JSON string. Newlines are encoded as `\n`, quotes as `\"`.

## Script Template Structure

Every aetest script follows this structure:

```
1. Imports (logging, aetest)
2. TEST_DATA dict (all expected values as a Python literal)
3. CommonSetup class (connect to devices)
4. Testcase class(es) (test methods with assertions)
5. CommonCleanup class (disconnect)
6. if __name__ == "__main__": aetest.main()
```

### Rules for TEST_DATA

- Must be a **Python dict literal** defined at module level
- Contains all expected values the test will validate against
- Cannot be loaded from files, network, or environment variables
- Keeps the test deterministic and self-documenting

### Rules for the Script

- **Banned imports:** os, sys, subprocess, shutil, socket, pathlib, pickle, yaml, requests, urllib, http, ssl
- **Banned functions:** `__import__()`, `eval()`, `exec()`, `compile()`, `open()`, `json.loads()`
- The script cannot connect to devices directly; embed all validation data inline in TEST_DATA
- Use `logger.info()` for verbose output and `self.failed()` or `assert` for test verdicts

## Example 1: Interface State Validation

Verify that all expected interfaces are in up/up state.

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_dynamic_test '{"test_script":"import logging\nfrom pyats import aetest\n\nlogger = logging.getLogger(__name__)\n\nTEST_DATA = {\n    \"device\": \"R1\",\n    \"expected_interfaces\": {\n        \"GigabitEthernet1\": {\"status\": \"up\", \"protocol\": \"up\"},\n        \"GigabitEthernet2\": {\"status\": \"up\", \"protocol\": \"up\"},\n        \"GigabitEthernet3\": {\"status\": \"up\", \"protocol\": \"up\"},\n        \"Loopback0\": {\"status\": \"up\", \"protocol\": \"up\"}\n    }\n}\n\nclass CommonSetup(aetest.CommonSetup):\n    @aetest.subsection\n    def connect_to_device(self, testbed):\n        device = testbed.devices[TEST_DATA[\"device\"]]\n        device.connect(learn_hostname=True, log_stdout=False)\n        self.parent.parameters[\"device\"] = device\n\nclass InterfaceStateValidation(aetest.Testcase):\n    @aetest.setup\n    def gather_interface_data(self):\n        device = self.parent.parameters[\"device\"]\n        self.parsed = device.parse(\"show ip interface brief\")\n        logger.info(\"Parsed interface data: %s\", self.parsed)\n\n    @aetest.test\n    def verify_interface_status(self):\n        interfaces = self.parsed.get(\"interface\", {})\n        failed_interfaces = []\n        for intf_name, expected in TEST_DATA[\"expected_interfaces\"].items():\n            if intf_name not in interfaces:\n                failed_interfaces.append(f\"{intf_name}: NOT FOUND in device output\")\n                continue\n            actual = interfaces[intf_name]\n            actual_status = actual.get(\"status\", \"unknown\")\n            actual_protocol = actual.get(\"protocol\", \"unknown\")\n            if actual_status != expected[\"status\"] or actual_protocol != expected[\"protocol\"]:\n                failed_interfaces.append(\n                    f\"{intf_name}: expected {expected[\"status\"]}/{expected[\"protocol\"]}, \"\n                    f\"got {actual_status}/{actual_protocol}\"\n                )\n            else:\n                logger.info(\"PASS: %s is %s/%s\", intf_name, actual_status, actual_protocol)\n        if failed_interfaces:\n            self.failed(\"Interface state failures:\\n\" + \"\\n\".join(failed_interfaces))\n        else:\n            self.passed(\"All interfaces in expected state\")\n\nclass CommonCleanup(aetest.CommonCleanup):\n    @aetest.subsection\n    def disconnect(self, testbed):\n        for device in testbed.devices.values():\n            if device.connected:\n                device.disconnect()\n\nif __name__ == \"__main__\":\n    aetest.main()"}'
```

**What this tests:**
- Connects to R1 via the testbed
- Parses `show ip interface brief` with Genie
- Checks each expected interface exists and is up/up
- Reports per-interface PASS/FAIL with details

## Example 2: OSPF Neighbor Validation

Verify that expected OSPF neighbors are present and in FULL state.

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_dynamic_test '{"test_script":"import logging\nfrom pyats import aetest\n\nlogger = logging.getLogger(__name__)\n\nTEST_DATA = {\n    \"device\": \"R1\",\n    \"ospf_process\": \"1\",\n    \"expected_neighbors\": [\n        {\"neighbor_id\": \"2.2.2.2\", \"interface\": \"GigabitEthernet1\", \"state\": \"FULL\"},\n        {\"neighbor_id\": \"3.3.3.3\", \"interface\": \"GigabitEthernet2\", \"state\": \"FULL\"}\n    ]\n}\n\nclass CommonSetup(aetest.CommonSetup):\n    @aetest.subsection\n    def connect_to_device(self, testbed):\n        device = testbed.devices[TEST_DATA[\"device\"]]\n        device.connect(learn_hostname=True, log_stdout=False)\n        self.parent.parameters[\"device\"] = device\n\nclass OSPFNeighborValidation(aetest.Testcase):\n    @aetest.setup\n    def gather_ospf_data(self):\n        device = self.parent.parameters[\"device\"]\n        self.parsed = device.parse(\"show ip ospf neighbor\")\n        logger.info(\"OSPF neighbor data: %s\", self.parsed)\n\n    @aetest.test\n    def verify_neighbor_count(self):\n        interfaces = self.parsed.get(\"interfaces\", {})\n        total_neighbors = sum(\n            len(nbrs.get(\"neighbors\", {})) for nbrs in interfaces.values()\n        )\n        expected_count = len(TEST_DATA[\"expected_neighbors\"])\n        if total_neighbors < expected_count:\n            self.failed(\n                f\"Expected at least {expected_count} OSPF neighbors, found {total_neighbors}\"\n            )\n        else:\n            self.passed(f\"Found {total_neighbors} OSPF neighbors (expected {expected_count})\")\n\n    @aetest.test\n    def verify_each_neighbor(self):\n        interfaces = self.parsed.get(\"interfaces\", {})\n        failures = []\n        for expected in TEST_DATA[\"expected_neighbors\"]:\n            intf = expected[\"interface\"]\n            nbr_id = expected[\"neighbor_id\"]\n            if intf not in interfaces:\n                failures.append(f\"{intf}: interface not found in OSPF output\")\n                continue\n            neighbors = interfaces[intf].get(\"neighbors\", {})\n            if nbr_id not in neighbors:\n                failures.append(f\"{nbr_id} on {intf}: neighbor not found\")\n                continue\n            actual_state = neighbors[nbr_id].get(\"state\", \"unknown\")\n            if expected[\"state\"] not in actual_state.upper():\n                failures.append(\n                    f\"{nbr_id} on {intf}: expected {expected[\"state\"]}, got {actual_state}\"\n                )\n            else:\n                logger.info(\"PASS: %s on %s is %s\", nbr_id, intf, actual_state)\n        if failures:\n            self.failed(\"OSPF neighbor failures:\\n\" + \"\\n\".join(failures))\n        else:\n            self.passed(\"All expected OSPF neighbors verified\")\n\nclass CommonCleanup(aetest.CommonCleanup):\n    @aetest.subsection\n    def disconnect(self, testbed):\n        for device in testbed.devices.values():\n            if device.connected:\n                device.disconnect()\n\nif __name__ == \"__main__\":\n    aetest.main()"}'
```

**What this tests:**
- Parses `show ip ospf neighbor` with Genie structured parser
- Verifies total neighbor count meets minimum expected
- Checks each expected neighbor by router ID, interface, and adjacency state
- Distinguishes between missing neighbors and wrong-state neighbors

## Example 3: BGP Path Validation

Verify that a specific route exists in the BGP table with the expected next-hop and AS path.

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_dynamic_test '{"test_script":"import logging\nfrom pyats import aetest\n\nlogger = logging.getLogger(__name__)\n\nTEST_DATA = {\n    \"device\": \"R1\",\n    \"expected_routes\": [\n        {\n            \"prefix\": \"10.0.0.0/8\",\n            \"next_hop\": \"10.1.1.2\",\n            \"as_path\": \"65002\",\n            \"origin\": \"IGP\"\n        },\n        {\n            \"prefix\": \"172.16.0.0/16\",\n            \"next_hop\": \"10.1.1.2\",\n            \"as_path\": \"65002 65003\",\n            \"origin\": \"IGP\"\n        }\n    ]\n}\n\nclass CommonSetup(aetest.CommonSetup):\n    @aetest.subsection\n    def connect_to_device(self, testbed):\n        device = testbed.devices[TEST_DATA[\"device\"]]\n        device.connect(learn_hostname=True, log_stdout=False)\n        self.parent.parameters[\"device\"] = device\n\nclass BGPPathValidation(aetest.Testcase):\n    @aetest.setup\n    def gather_bgp_data(self):\n        device = self.parent.parameters[\"device\"]\n        self.parsed = device.parse(\"show ip bgp\")\n        logger.info(\"BGP table parsed successfully\")\n\n    @aetest.test\n    def verify_bgp_routes(self):\n        vrf_default = self.parsed.get(\"vrf\", {}).get(\"default\", {})\n        address_family = vrf_default.get(\"address_family\", {}).get(\"ipv4 unicast\", {})\n        prefixes = address_family.get(\"prefixes\", {})\n        failures = []\n        for route in TEST_DATA[\"expected_routes\"]:\n            prefix = route[\"prefix\"]\n            if prefix not in prefixes:\n                failures.append(f\"{prefix}: NOT FOUND in BGP table\")\n                continue\n            paths = prefixes[prefix].get(\"index\", {})\n            found_match = False\n            for idx, path in paths.items():\n                nh = path.get(\"next_hop\", \"\")\n                if nh == route[\"next_hop\"]:\n                    found_match = True\n                    logger.info(\"PASS: %s via %s found in BGP table\", prefix, nh)\n                    break\n            if not found_match:\n                failures.append(\n                    f\"{prefix}: expected next-hop {route[\"next_hop\"]}, not found in any path\"\n                )\n        if failures:\n            self.failed(\"BGP path failures:\\n\" + \"\\n\".join(failures))\n        else:\n            self.passed(\"All expected BGP routes verified\")\n\nclass CommonCleanup(aetest.CommonCleanup):\n    @aetest.subsection\n    def disconnect(self, testbed):\n        for device in testbed.devices.values():\n            if device.connected:\n                device.disconnect()\n\nif __name__ == \"__main__\":\n    aetest.main()"}'
```

**What this tests:**
- Parses the full BGP table with Genie
- Navigates the VRF/address-family/prefix hierarchy
- Checks each expected prefix exists with the correct next-hop
- Reports missing prefixes and next-hop mismatches separately

## Example 4: Ping Reachability Matrix

Execute a ping matrix between device pairs and validate reachability.

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_dynamic_test '{"test_script":"import logging\nfrom pyats import aetest\n\nlogger = logging.getLogger(__name__)\n\nTEST_DATA = {\n    \"ping_matrix\": [\n        {\"device\": \"R1\", \"destination\": \"10.1.1.2\", \"source\": \"GigabitEthernet1\", \"min_success\": 80},\n        {\"device\": \"R1\", \"destination\": \"10.2.2.2\", \"source\": \"GigabitEthernet2\", \"min_success\": 80},\n        {\"device\": \"R1\", \"destination\": \"8.8.8.8\", \"source\": \"GigabitEthernet1\", \"min_success\": 100},\n        {\"device\": \"R1\", \"destination\": \"1.1.1.1\", \"source\": \"Loopback0\", \"min_success\": 100}\n    ]\n}\n\nclass CommonSetup(aetest.CommonSetup):\n    @aetest.subsection\n    def connect_all_devices(self, testbed):\n        devices = {}\n        for entry in TEST_DATA[\"ping_matrix\"]:\n            dev_name = entry[\"device\"]\n            if dev_name not in devices:\n                device = testbed.devices[dev_name]\n                device.connect(learn_hostname=True, log_stdout=False)\n                devices[dev_name] = device\n        self.parent.parameters[\"devices\"] = devices\n\nclass PingReachabilityMatrix(aetest.Testcase):\n    @aetest.test\n    def execute_ping_matrix(self):\n        devices = self.parent.parameters[\"devices\"]\n        results = []\n        failures = []\n        for entry in TEST_DATA[\"ping_matrix\"]:\n            device = devices[entry[\"device\"]]\n            dst = entry[\"destination\"]\n            src = entry.get(\"source\", \"\")\n            min_pct = entry[\"min_success\"]\n            try:\n                if src:\n                    ping_result = device.ping(dst, source=src, count=5, timeout=10)\n                else:\n                    ping_result = device.ping(dst, count=5, timeout=10)\n                logger.info(\n                    \"PASS: %s -> %s from %s: reachable\",\n                    entry[\"device\"], dst, src or \"default\"\n                )\n                results.append({\n                    \"device\": entry[\"device\"],\n                    \"destination\": dst,\n                    \"status\": \"PASS\"\n                })\n            except Exception as e:\n                msg = f\"{entry[\"device\"]} -> {dst} from {src or \"default\"}: FAILED ({str(e)[:80]})\"\n                logger.error(msg)\n                failures.append(msg)\n                results.append({\n                    \"device\": entry[\"device\"],\n                    \"destination\": dst,\n                    \"status\": \"FAIL\"\n                })\n        logger.info(\"\\n=== PING MATRIX RESULTS ===\")\n        for r in results:\n            logger.info(\"%s -> %s: %s\", r[\"device\"], r[\"destination\"], r[\"status\"])\n        if failures:\n            self.failed(\n                f\"{len(failures)}/{len(TEST_DATA[\"ping_matrix\"])} pings failed:\\n\"\n                + \"\\n\".join(failures)\n            )\n        else:\n            self.passed(f\"All {len(results)} pings successful\")\n\nclass CommonCleanup(aetest.CommonCleanup):\n    @aetest.subsection\n    def disconnect_all(self, testbed):\n        for device in testbed.devices.values():\n            if device.connected:\n                device.disconnect()\n\nif __name__ == \"__main__\":\n    aetest.main()"}'
```

**What this tests:**
- Connects to all unique devices referenced in the ping matrix
- Executes pings from each device to each destination with optional source interface
- Collects pass/fail results into a summary matrix
- Fails the test if any ping drops below the minimum success threshold

## Writing Your Own Test Scripts

### Step 1: Collect Data First

Before writing a dynamic test, collect the device data you need using the other pyATS tools:

```bash
# Gather current state
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip ospf neighbor"}'
```

### Step 2: Build TEST_DATA from Collected Output

Use the collected output to populate the `TEST_DATA` dictionary with the expected values. This makes the test deterministic -- it validates that the network matches the known-good state.

### Step 3: Write the Script Following the Template

```python
import logging
from pyats import aetest

logger = logging.getLogger(__name__)

TEST_DATA = {
    # All expected values go here as Python literals
}

class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def connect_to_device(self, testbed):
        device = testbed.devices["R1"]
        device.connect(learn_hostname=True, log_stdout=False)
        self.parent.parameters["device"] = device

class YourTestcase(aetest.Testcase):
    @aetest.setup
    def gather_data(self):
        device = self.parent.parameters["device"]
        self.parsed = device.parse("show COMMAND")

    @aetest.test
    def verify_something(self):
        # Compare self.parsed against TEST_DATA
        # Use self.passed(), self.failed(), or assert statements
        pass

class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def disconnect(self, testbed):
        for device in testbed.devices.values():
            if device.connected:
                device.disconnect()

if __name__ == "__main__":
    aetest.main()
```

### Step 4: Serialize and Invoke

Convert the script to a single-line JSON string (replace newlines with `\n`, escape quotes) and pass it as the `test_script` parameter.

## Interpreting Results

The tool returns the aetest execution results:

- **Passed** -- All assertions succeeded, the network state matches TEST_DATA
- **Failed** -- One or more assertions did not match; the failure message explains what was wrong
- **Errored** -- The script itself had a runtime error (syntax error, import violation, timeout)
- **Blocked** -- CommonSetup failed (could not connect to device), so testcases were skipped

## Integration with Other Skills

- Use **pyats-health-check** to collect device state, then write dynamic tests to formalize pass/fail criteria for that state
- Use **pyats-config-mgmt** Phase 4 (post-change verification) to trigger dynamic tests after configuration changes
- Use **pyats-routing** data to build BGP/OSPF validation tests with real expected values
- Use **pyats-parallel-ops** to run dynamic tests as part of fleet-wide validation sweeps
