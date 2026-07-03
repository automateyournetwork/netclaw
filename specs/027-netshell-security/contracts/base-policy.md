# Contract: Base Policy Schema

**Feature**: [../spec.md](../spec.md) | **Data Model**: [../data-model.md](../data-model.md)

## Purpose

Defines the schema for `netshell/policies/base.yaml` - the root sandbox policy that establishes default security controls for all NetClaw operations.

## Schema (YAML)

```yaml
# Required fields
version: 1                          # Schema version (integer, must be 1)
name: string                        # Policy identifier (e.g., "netclaw-base")
description: string                 # Optional human description

# Filesystem Policy (Landlock LSM - locked at creation)
filesystem_policy:
  workspace:                        # Required: writable paths
    - path: string                  # Absolute path (required)
      permissions: [string]         # Required: read, write, execute
  read_only: [string]               # Optional: read-only paths
  denied: [string]                  # Required: explicitly blocked paths

# Landlock Settings
landlock:
  enabled: boolean                  # Required: enable Landlock LSM
  restrict_self: boolean            # Required: restrict sandbox filesystem
  exec_paths: [string]              # Required: paths where execution allowed

# Process Policy (seccomp - locked at creation)
process:
  user: string                      # Required: Unix user
  group: string                     # Required: Unix group
  no_new_privs: boolean             # Required: prevent privilege escalation
  seccomp:
    profile: string                 # Required: restricted|permissive
    deny: [string]                  # Required: blocked syscalls
  limits:                           # Optional
    max_processes: integer
    max_open_files: integer
    max_memory_mb: integer

# Network Policy (hot-reloadable)
network_policies:
  default_action: string            # Required: deny|allow
  log_allowed: boolean              # Optional: log allowed connections
  log_denied: boolean               # Optional: log denied connections
  core_egress:                      # Required: always-allowed endpoints
    - name: string                  # Required: rule identifier
      host: string                  # Required: hostname/IP/CIDR/pattern
      ports: [integer]              # Required: allowed ports
      protocols: [string]           # Required: https|http|tcp|udp
      methods: [string]             # Optional: HTTP methods
  mcp_egress: []                    # Populated by compiler
  blocked:                          # Optional: explicit blocks
    - host: string

# Inference Routing (optional)
inference:
  enabled: boolean
  backends:
    - name: string
      endpoint: string
      credential_env: string|null
  default_backend: string

# Credential Injection
credentials:
  inject: [string]                  # Required: env vars to inject
  rotation:                         # Optional
    enabled: boolean
    interval_hours: integer

# Audit Logging
audit:
  enabled: boolean                  # Required
  format: string                    # Required: ocsf
  events: [string]                  # Required: event types
  destinations:                     # Required
    - type: string                  # file|syslog|webhook
      path: string                  # For type=file
      address: string               # For type=syslog
      url: string                   # For type=webhook

# ITSM Integration (optional)
itsm:
  enabled: boolean
  provider: string                  # servicenow
  require_approval: [string]        # Tool names requiring CR
  auto_approve: [string]            # Tool names auto-approved
```

## Validation Rules

1. **version** must equal 1
2. **filesystem_policy.denied** must include sensitive paths: `/root`, `/home`, `/etc/shadow`
3. **landlock.enabled** must be `true` for production
4. **process.no_new_privs** must be `true`
5. **process.seccomp.deny** must include: `ptrace`, `mount`, `reboot`, `init_module`
6. **network_policies.default_action** must be `deny`
7. **network_policies.core_egress** must include Anthropic API
8. **credentials.inject** must never appear in filesystem_policy.workspace
9. **audit.enabled** must be `true` for production
10. **audit.format** must be `ocsf`

## Example (Minimal)

```yaml
version: 1
name: netclaw-minimal
filesystem_policy:
  workspace:
    - path: /workspace
      permissions: [read, write, execute]
  denied:
    - /root
    - /home
    - /etc/shadow
landlock:
  enabled: true
  restrict_self: true
  exec_paths: [/workspace, /usr/bin]
process:
  user: netclaw
  group: netclaw
  no_new_privs: true
  seccomp:
    profile: restricted
    deny: [ptrace, mount, reboot]
network_policies:
  default_action: deny
  core_egress:
    - name: anthropic-api
      host: api.anthropic.com
      ports: [443]
      protocols: [https]
credentials:
  inject: [ANTHROPIC_API_KEY]
audit:
  enabled: true
  format: ocsf
  events: [tool_invocation, policy_violation]
  destinations:
    - type: file
      path: /workspace/logs/audit/netshell.log
```

## Immutable vs Hot-Reloadable

| Section | Immutable | Hot-Reloadable | Notes |
|---------|-----------|----------------|-------|
| filesystem_policy | Yes | No | Landlock locked at sandbox creation |
| landlock | Yes | No | Kernel-level, cannot change |
| process | Yes | No | seccomp locked at creation |
| network_policies | No | Yes | Can update without restart |
| inference | No | Yes | Backend routing changeable |
| credentials | No | Yes | New credentials on restart |
| audit | No | Yes | Destination changes allowed |
| itsm | No | Yes | Approval rules changeable |
