# SOUL-DEFENSE: Security Principles for NetClaw

This document extends the [NetClaw SOUL](../SOUL.md) with detailed security principles and compliance guidance for DefenseClaw-protected deployments.

---

## Overview

DefenseClaw implements the security principles defined in SOUL.md (P18-P25). This document provides operational guidance for applying those principles in enterprise environments.

---

## Security Posture Guidance

### When to Use Observe Mode

**Observe mode** (default) logs all security events without blocking operations. Use when:

- **Onboarding new deployments** - Understand what operations your workflows require
- **Testing and development** - Avoid blocking legitimate development activities
- **Auditing existing workflows** - Discover what tools and permissions are actually used
- **Low-risk environments** - Lab, training, or hobby deployments

```bash
defenseclaw setup guardrail --mode observe
```

### When to Use Action Mode

**Action mode** actively blocks dangerous operations. Use when:

- **Production deployments** - Protect critical infrastructure
- **Compliance requirements** - SOC2, PCI-DSS, HIPAA mandates enforcement
- **High-value targets** - Financial systems, healthcare, government
- **After baseline established** - Once you understand normal operation patterns

```bash
defenseclaw setup guardrail --mode action --restart
```

### Transition Strategy

1. Deploy with **observe mode** for 2-4 weeks
2. Review alerts and tune policies
3. Create exceptions for legitimate tools
4. Enable **action mode** in phases (dev → staging → production)

---

## Security Principles (SOUL P18-P25)

### P18: Sandbox by Default

> "All code execution occurs within isolated sandbox environments."

**Implementation:**
- DefenseClaw automatically configures OpenShell sandbox
- Landlock restricts filesystem access
- seccomp limits system calls
- Network namespaces control egress

**Verification:**
```bash
# Check sandbox is active
defenseclaw status sandbox
```

### P19: Scan Before Execute

> "All components are scanned for security issues before execution."

**Implementation:**
- CodeGuard static analysis runs automatically
- HIGH/CRITICAL findings block execution
- Scan results logged to audit database

**Verification:**
```bash
# Scan all skills
for skill in $(ls workspace/skills/); do
  defenseclaw skill scan "$skill"
done
```

### P20: Principle of Least Privilege

> "Components receive only the permissions they need."

**Implementation:**
- Use `tool block` to deny unnecessary capabilities
- Create allowlists for trusted operations
- Review tool usage in audit logs

**Example Policy:**
```bash
# Block destructive operations by default
defenseclaw tool block "*_delete*" --reason "P20: least privilege"
defenseclaw tool block "*_destroy*" --reason "P20: least privilege"
defenseclaw tool block "shell_*" --reason "P20: least privilege"
```

### P21: Audit Everything

> "All operations are logged for compliance and forensics."

**Implementation:**
- SQLite audit database at `~/.defenseclaw/audit.db`
- All tool calls, scans, blocks logged
- SIEM integration for real-time monitoring

**Verification:**
```bash
# Export recent audit
defenseclaw alerts --export json --limit 1000 > audit.json
```

### P22: Defense in Depth

> "Multiple security layers provide redundant protection."

**Implementation:**
- Layer 1: CodeGuard scanning (preventive)
- Layer 2: Guardrails (detective/preventive)
- Layer 3: OpenShell sandbox (containment)
- Layer 4: Audit logging (forensic)

### P23: Fail Secure

> "Security failures default to denial."

**Implementation:**
- Component scan failures → blocked
- Guardrail errors → block (action mode)
- Gateway crash → no execution allowed

### P24: Transparency

> "Security decisions are visible and explainable."

**Implementation:**
- All blocks include reason in alerts
- Scan findings show exact code location
- Audit trail for compliance review

### P25: User Override

> "Authorized users can override security decisions when needed."

**Implementation:**
```bash
# Add exception for false positive
defenseclaw exception add <component> --finding <id> --reason "reviewed and approved"

# Temporarily allow blocked tool
defenseclaw tool allow <tool> --expires 1h --reason "emergency maintenance"
```

---

## Compliance Mapping

### SOC2 Type II

| SOC2 Criteria | DefenseClaw Control |
|---------------|---------------------|
| CC6.1 Logical access controls | Guardrail tool blocking |
| CC6.6 Security event monitoring | Audit database + SIEM |
| CC6.7 Unauthorized activity prevention | Action mode guardrails |
| CC7.2 Malicious software detection | CodeGuard scanning |
| CC7.3 Security incident monitoring | Alert notifications |

**Evidence Collection:**
```bash
# Generate SOC2 audit report
defenseclaw alerts --export json --after 2026-01-01 > soc2-evidence.json
```

### PCI-DSS v4.0

| PCI Requirement | DefenseClaw Control |
|-----------------|---------------------|
| 5.3.2 Anti-malware on all systems | CodeGuard scanning |
| 10.2 Audit trail for security events | Audit database |
| 10.3 Immediate alert on security events | SIEM + webhooks |
| 12.10.1 Incident response | Action mode blocking |

**Configuration:**
```bash
# Enable PCI-compliant settings
defenseclaw config set guardrail.mode action
defenseclaw config set scan.severity_threshold MEDIUM
defenseclaw config siem --type splunk --endpoint $SPLUNK_URL
```

### HIPAA

| HIPAA Safeguard | DefenseClaw Control |
|-----------------|---------------------|
| 164.312(b) Audit controls | Audit database |
| 164.312(c)(1) Integrity | CodeGuard + guardrails |
| 164.312(d) Authentication | Tool blocking |
| 164.312(e)(1) Transmission security | Sandbox network isolation |

**Configuration:**
```bash
# Enable HIPAA-compliant settings
defenseclaw config set guardrail.rules.sensitive-path true
defenseclaw tool block "*_export*" --reason "HIPAA: data export control"
```

---

## Risk Assessment Matrix

Use this matrix to determine appropriate security posture:

| Environment | Risk Level | Recommended Mode | SIEM Required |
|-------------|------------|------------------|---------------|
| Production (customer data) | HIGH | action | Yes |
| Production (internal) | MEDIUM | action | Recommended |
| Staging | MEDIUM | observe | Recommended |
| Development | LOW | observe | Optional |
| Lab/Training | LOW | observe | No |
| Hobby/Personal | LOW | disabled | No |

---

## Incident Response

### Severity Levels

| Level | Examples | Response |
|-------|----------|----------|
| CRITICAL | Active credential theft, C2 communication | Immediate isolation, escalate |
| HIGH | Blocked shell execution, sensitive file access | Review within 1 hour |
| MEDIUM | Failed scan, policy violation | Review within 24 hours |
| LOW | Informational events | Weekly review |

### Response Playbook

1. **Alert received** - Check `defenseclaw alerts`
2. **Assess severity** - CRITICAL/HIGH requires immediate action
3. **Isolate if needed** - Disable component or skill
4. **Investigate** - Review audit trail and tool calls
5. **Remediate** - Fix or remove offending component
6. **Document** - Record incident and response

### Emergency Isolation

```bash
# Block all tool execution
defenseclaw tool block "*" --reason "emergency isolation"

# Disable guardrails (allows investigation)
defenseclaw setup guardrail --disable

# Stop gateway
pkill defenseclaw-gateway
```

---

## Best Practices

### 1. Start Permissive, Tighten Gradually

Don't enable action mode on day one. Observe first, then restrict.

### 2. Review Alerts Daily

Set up daily alert review process:
```bash
defenseclaw alerts --after "$(date -d yesterday +%Y-%m-%d)"
```

### 3. Document Exceptions

Every exception needs a reason:
```bash
defenseclaw exception add tool-x --reason "Business justification: approved by Security Team on 2026-04-16"
```

### 4. Test Before Production

Test security policies in staging before production rollout.

### 5. Monitor SIEM Dashboards

Create dashboards for:
- Blocked operations by category
- Component scan failures
- New tool usage patterns
- Alert volume trends

---

## MCP-Specific Security Considerations

### IP Fabric Integration

IP Fabric provides network assurance capabilities through a remote MCP server built into IP Fabric appliances. Security considerations:

**API Token Security:**
- API tokens grant read access to network topology, configuration, and state data
- Tokens are never exposed to the AI model — only query results are processed
- Use RBAC to scope token permissions to only required data
- Rotate tokens periodically per organizational policy

**Data Sensitivity:**
- Network topology and device inventory are sensitive intelligence
- Path analysis may reveal internal network architecture
- Intent violations may expose compliance gaps
- Treat all IP Fabric data with appropriate classification

**RBAC Recommendations:**
- **SOC Analysts**: Read-only health and path analysis
- **Network Engineers**: Full read access, path analysis with diagrams
- **Security/Compliance**: Intent validation and compliance views
- **Administrators**: Full access including intent rule configuration

**Credential Storage:**
```bash
# Store in .env file (not committed to git)
IPFABRIC_HOST=https://ipfabric.example.com
IPFABRIC_API_TOKEN=your-api-token-here
```

**Network Connectivity:**
- IP Fabric MCP uses HTTPS (port 443)
- Requires network path from NetClaw host to IP Fabric appliance
- Consider firewall rules for access control
- No VPN required if appliance is network-accessible

### Check Point Integration

Check Point MCPs provide access to security policies, threat intelligence, and gateway diagnostics. See checkpoint-security skill for credential requirements.

---

## Related Documentation

- [SOUL.md](../SOUL.md) - Core NetClaw principles (P18-P25 are security)
- [DEFENSECLAW.md](DEFENSECLAW.md) - Technical configuration guide
- [UPGRADE-TO-DEFENSECLAW.md](UPGRADE-TO-DEFENSECLAW.md) - Migration guide
- [IPFABRIC.md](IPFABRIC.md) - IP Fabric integration guide
