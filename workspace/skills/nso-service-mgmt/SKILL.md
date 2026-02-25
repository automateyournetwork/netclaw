---
name: nso-service-mgmt
description: Cisco NSO service management — discover service types, list service instances, orchestrate network services
version: 1.0.0
tags: [nso, services, orchestration, automation]
---

# NSO Service Management

Manage NSO services — discover what service types are available, list deployed service instances, and understand the orchestration layer that provisions configuration across multiple devices.

## MCP Server

- **Command**: `cisco-nso-mcp-server` (pip-installed, stdio transport)
- **Requires**: `NSO_ADDRESS`, `NSO_USERNAME`, `NSO_PASSWORD` environment variables

## Available Tools

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `get_service_types` | none | List all available service types in NSO (L3VPN, VPLS, ACL, etc.) |
| `get_services` | `service_type` | List all service instances for a given service type |

## What Are NSO Services?

NSO services are the core value of NSO. Instead of configuring devices one at a time, you define a service (e.g., "L3VPN between Site-A and Site-B") and NSO:

1. **Translates** the service intent into per-device CLI/NETCONF configuration
2. **Deploys** the config to all affected devices transactionally
3. **Tracks** what config belongs to which service (service meta-data)
4. **Enables rollback** — delete the service and all its config is cleanly removed

Common service types include:
- **L3VPN** — Layer 3 VPN provisioning across PE routers
- **L2VPN / VPLS** — Layer 2 VPN / VPLS services
- **ACL Management** — Centralized ACL provisioning
- **QoS Policies** — Quality of service templates across devices
- **Interface Provisioning** — Standardized interface configurations
- **Firewall Rules** — Security policy deployment
- **Custom Services** — Any service package developed for your environment

## Workflow: Service Discovery

When a user asks "what services does NSO have?" or "what can NSO provision?":

1. **Get service types**: `get_service_types` to list all available service packages
2. **For each type**: `get_services` to list deployed instances
3. **Report**: Table of service types, instance counts, and deployment status

## Workflow: Service Inventory Report

When a user needs to understand what's deployed:

1. **List service types**: `get_service_types`
2. **For each interesting type**: `get_services` with the service type name
3. **Cross-reference with devices**: Use `get_device_config` (nso-device-ops) to see the config NSO deployed
4. **Report**: Service name, type, affected devices, deployment status

## Workflow: Service Health Check

When validating that NSO services are properly deployed:

1. **List services**: `get_service_types` → `get_services` for each type
2. **Check device sync**: For each device in a service, run `check_device_sync` (nso-device-ops)
3. **Flag issues**: If a device is out of sync, the service config may have drifted
4. **Report**: Service health summary — in-sync vs out-of-sync devices per service

## Workflow: Pre-Change Service Impact Analysis

Before making manual device changes:

1. **List services**: `get_service_types` → `get_services` for each type
2. **Identify affected services**: Which services touch the device being changed?
3. **Warn the user**: "R1 has 3 active L3VPN services — manual changes may conflict with NSO"
4. **Recommend**: Use NSO services for changes instead of direct CLI, or re-sync after manual changes

## Integration with Other Skills

| Scenario | Skills Involved |
|----------|----------------|
| Audit deployed services | nso-service-mgmt + nso-device-ops (verify device configs match services) |
| Service drift detection | nso-service-mgmt + nso-device-ops (check_device_sync) |
| Document services | nso-service-mgmt → github-ops (commit service inventory to repo) |
| Service impact analysis | nso-service-mgmt + pyATS (verify service is working at network level) |
| Service report delivery | nso-service-mgmt → msgraph-teams or Slack (post service inventory) |
| Lab service testing | nso-service-mgmt + cml-lab-lifecycle (test services against CML lab) |

## NSO Service Concepts

| Concept | Meaning |
|---------|---------|
| **Service Type** | A service package (e.g., l3vpn) — defines what parameters are needed and how to translate to device config |
| **Service Instance** | A deployed service (e.g., "l3vpn-siteA-siteB") — a specific instantiation with actual parameters |
| **Service Meta-Data** | NSO tracks which config lines belong to which service — enables clean rollback |
| **FASTMAP** | NSO's algorithm that maps service intent to device config — handles create, modify, delete |
| **Reactive FASTMAP** | Services that react to external events (e.g., device state changes) |
| **Nano Services** | Multi-step services with state machines for complex provisioning workflows |
| **Service Package** | The code (YANG models + templates + logic) that defines a service type |

## Example Slack Conversations

**"What services are running on NSO?"**
→ get_service_types → list of available service packages
→ get_services for each type → count of deployed instances
→ Report: "NSO has 4 service types: l3vpn (12 instances), acl-mgmt (8 instances), qos-policy (5 instances), interface-std (20 instances)"

**"Show me all L3VPN services"**
→ get_services("l3vpn") → list of all L3VPN instances with their parameters
→ Report: "12 L3VPN services deployed across 6 PE routers"

**"Are any services out of sync?"**
→ get_service_types → get_services for each → get affected devices
→ check_device_sync for each affected device
→ Report: "2 of 12 L3VPN services have out-of-sync devices: PE1, PE3"

**"What services touch router PE1?"**
→ get_service_types → get_services for each → filter for PE1
→ Report: "PE1 participates in: l3vpn-customer-a, l3vpn-customer-b, qos-gold, acl-mgmt-edge"

## Important Rules

- **Services are read-only in this MCP** — you can discover and inspect services but not create/modify/delete them
- **Service drift is critical** — if `check_device_sync` shows out-of-sync, service config may not match intended state
- **Manual changes conflict with services** — warn users that direct CLI changes on NSO-managed devices can break service tracking
- **Record in GAIT** — log all service discovery and audit operations for audit trail

## Environment Variables

Same as nso-device-ops:
- `NSO_SCHEME`, `NSO_ADDRESS`, `NSO_PORT`, `NSO_USERNAME`, `NSO_PASSWORD`, `NSO_VERIFY`, `NSO_TIMEOUT`
