---
name: eve-ng-console-ops
description: Execute live CLI commands on running EVE-NG nodes over telnet console. Use when running show commands, making live config changes, verifying protocol state, testing connectivity, checking console readiness, or interacting with IOS, Junos, VPCS, EOS, or NX-OS nodes.
user-invocable: true
metadata: {"openclaw":{"requires":{"bins":["python3"],"env":["EVE_URL","EVE_USER","EVE_PASSWORD"]}}}
---

# EVE-NG Console Operations

Use this skill for **live console interaction** with running nodes.

## Workflow

1. Discover the node console first.
2. Determine the landed mode before sending commands.
3. Use the OS-specific execution tool.
4. For config changes, verify command results in the returned transcript before claiming success.
5. Read `{baseDir}/references/console-guardrails.md` when boot state, mode handling, or Junos commit behavior matters.

## Available tools

- `eve_discover_node`
- `eve_exec_ios`
- `eve_exec_junos`
- `eve_exec_vpcs`
- `eve_exec_eos`
- `eve_exec_nxos`
