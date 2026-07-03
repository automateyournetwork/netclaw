---
name: eve-lab-topology-build
description: Build or rewire EVE-NG lab topology. Use when creating or deleting virtual networks, connecting node interfaces to networks, inspecting topology links, checking interface mappings, or listing available node templates before wiring a lab.
user-invocable: true
metadata: {"openclaw":{"emoji":"🧩","requires":{"bins":["python3"],"env":["EVE_URL","EVE_USER","EVE_PASSWORD"]}}}
---

# EVE Lab Topology Build

Use this skill for **network objects and interface wiring** inside an existing EVE-NG lab.

## Workflow

1. Read the current topology first with `eve_get_topology` or `eve_list_node_interfaces`.
2. Before rewiring, follow `{baseDir}/references/wiring-guardrails.md`.
3. Create or reuse the required network object.
4. Connect interfaces only after confirming IDs from `{baseDir}/references/network-and-interface-reference.md`.
5. Re-read topology after the change; do not trust the write response alone.

## Available tools

- `eve_get_topology`
- `eve_list_networks`
- `eve_create_network`
- `eve_delete_network`
- `eve_list_node_interfaces`
- `eve_connect_interface`
- `eve_list_node_types`

## When to read references

- Read `{baseDir}/references/wiring-guardrails.md` for stop/start, direct-segment, node-ID, and image-verification rules.
- Read `{baseDir}/references/network-and-interface-reference.md` for network types and interface-index guidance.
