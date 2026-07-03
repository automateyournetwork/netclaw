# Feature Specification: DefenseClaw Security Integration

**Feature Branch**: `027-netshell-security`
**Created**: 2026-04-11
**Updated**: 2026-04-16
**Status**: Draft
**Input**: User description: "Integrate Cisco DefenseClaw as the production security layer for NetClaw"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Production Security with DefenseClaw (Priority: P1)

As an enterprise user deploying NetClaw in production, I want a comprehensive security solution that automatically handles sandboxing, scans skills/MCPs before execution, inspects LLM calls, and logs everything to my SIEM so that I meet compliance requirements without manual configuration.

**Why this priority**: DefenseClaw is the complete solution - it handles OpenShell sandbox setup automatically, scans components before execution, provides runtime guardrails, and includes enterprise integrations (Splunk, OTLP). This is the only security option needed.

**Independent Test**: Can be fully tested by enabling DefenseClaw during installation, loading a skill, and verifying: (1) sandbox is active, (2) skill was scanned, (3) LLM calls are inspected, (4) audit logs appear in configured SIEM.

**Acceptance Scenarios**:

1. **Given** install.sh is running, **When** user is prompted "Enable DefenseClaw (recommended)?", **Then** they can answer Yes to enable production security
2. **Given** DefenseClaw is enabled, **When** a skill is loaded, **Then** it is automatically scanned for security issues before execution
3. **Given** DefenseClaw is enabled, **When** CodeGuard detects a HIGH/CRITICAL finding, **Then** the component is auto-blocked
4. **Given** DefenseClaw is enabled, **When** an LLM call is made, **Then** prompts and completions are inspected for secrets and injection patterns
5. **Given** DefenseClaw is enabled, **When** a tool is invoked, **Then** the invocation is evaluated against security rules before execution
6. **Given** DefenseClaw is enabled with SIEM, **When** any security event occurs, **Then** it is forwarded to Splunk HEC or OTLP endpoint

---

### User Story 2 - Runtime Guardrails (Priority: P1)

As a security engineer, I want real-time inspection of all agent activities so that dangerous operations are blocked before they execute, not just logged after the fact.

**Why this priority**: DefenseClaw's guardrails provide active protection. This differentiates production deployments from hobby mode.

**Independent Test**: Can be fully tested by enabling guardrails in action mode and attempting dangerous operations (shell commands, secret exfiltration, prompt injection).

**Acceptance Scenarios**:

1. **Given** DefenseClaw guardrails are in action mode, **When** a tool tries to execute a shell command, **Then** it is blocked per command rules
2. **Given** DefenseClaw guardrails are in action mode, **When** a prompt contains a secret pattern, **Then** it is redacted or blocked
3. **Given** DefenseClaw guardrails are in action mode, **When** a cognitive file attack is detected, **Then** the operation is blocked
4. **Given** guardrails trigger, **When** the event is logged, **Then** a webhook notification is sent (if configured)

---

### User Story 3 - Hobby Mode (No Security) (Priority: P2)

As a hobby user experimenting with NetClaw, I want to skip security features so that I can get started quickly without Docker or additional dependencies.

**Why this priority**: Preserves the current easy onboarding experience. Most users start in hobby mode and upgrade to DefenseClaw when ready for production.

**Independent Test**: Can be fully tested by declining DefenseClaw during installation and verifying NetClaw runs with full host access.

**Acceptance Scenarios**:

1. **Given** install.sh is running, **When** user declines DefenseClaw, **Then** installation completes without security features
2. **Given** hobby mode is active, **When** user runs NetClaw, **Then** it operates with full user privileges (no sandbox)
3. **Given** hobby mode is active, **When** user wants security later, **Then** they can run defenseclaw-enable.sh to upgrade

---

### User Story 4 - Tool Management (Priority: P2)

As a network administrator, I want to block or allow specific tools so that I can enforce the principle of least privilege.

**Why this priority**: Fine-grained control over what tools can execute is essential for production security.

**Independent Test**: Can be fully tested by blocking a tool via `defenseclaw tool block` and verifying invocation is denied.

**Acceptance Scenarios**:

1. **Given** DefenseClaw is enabled, **When** admin runs `defenseclaw tool block delete_file --reason "destructive"`, **Then** the tool is blocked
2. **Given** a tool is blocked, **When** a skill tries to invoke it, **Then** the invocation is denied with logged reason
3. **Given** DefenseClaw is enabled, **When** admin runs `defenseclaw alerts`, **Then** they see all blocked invocations

---

### Edge Cases

- What happens when DefenseClaw installation fails? Clear error message with manual install instructions.
- What happens when a skill passes scan but has runtime issues? Guardrails provide second layer of protection.
- What happens when SIEM endpoint is unreachable? Local fallback logging with retry queue.
- How do users upgrade from hobby mode? Run `defenseclaw init --enable-guardrail`.

## Requirements *(mandatory)*

### Functional Requirements

#### Installation & Configuration
- **FR-001**: Install script MUST offer DefenseClaw as the recommended security option
- **FR-002**: Install script MUST check for Docker, Python 3.10+, Go 1.25+, and Node.js 20+ before enabling DefenseClaw
- **FR-003**: Install script MUST allow users to decline security (hobby mode)
- **FR-004**: System MUST provide enable/disable scripts for DefenseClaw
- **FR-005**: System MUST store security choice in openclaw.json configuration

#### DefenseClaw Core Features
- **FR-006**: DefenseClaw MUST automatically set up OpenShell sandbox (no manual OpenShell install required)
- **FR-007**: DefenseClaw MUST scan all skills, MCPs, and plugins before execution
- **FR-008**: DefenseClaw MUST auto-block components with HIGH/CRITICAL scan findings
- **FR-009**: DefenseClaw MUST provide CodeGuard static analysis (credentials, eval, shell, SQL injection, path traversal)
- **FR-010**: DefenseClaw MUST inspect LLM prompts and completions across Anthropic, OpenAI, Azure, Gemini, OpenRouter, Ollama, and Bedrock
- **FR-011**: DefenseClaw MUST evaluate tool calls against six rule categories: secret, command, sensitive-path, c2, cognitive-file, trust-exploit

#### Enterprise Integration
- **FR-012**: DefenseClaw MUST support SIEM integration via Splunk HEC and OTLP HTTP export
- **FR-013**: DefenseClaw MUST support webhook notifications to Slack, PagerDuty, and Webex
- **FR-014**: DefenseClaw guardrails MUST support observe mode (logging only) and action mode (enforcement)

#### Tool Management
- **FR-015**: DefenseClaw MUST support blocking specific tools via CLI
- **FR-016**: DefenseClaw MUST support allowing specific tools via CLI
- **FR-017**: DefenseClaw MUST log all tool block/allow decisions with reason

#### Backward Compatibility
- **FR-018**: Hobby mode MUST operate identically to current NetClaw behavior (no sandbox, full access)
- **FR-019**: System MUST provide clear upgrade path from hobby mode to DefenseClaw

### Key Entities

- **Security Mode**: Configuration determining protection level (DefenseClaw enabled or Hobby mode)
- **Sandbox**: OpenShell-managed isolated execution environment
- **Scan Result**: Output from DefenseClaw component scanning (severity, findings, block decision)
- **Guardrail**: Runtime inspection rule that evaluates and optionally blocks operations
- **Tool Rule**: Block/allow decision for a specific tool with reason
- **Audit Record**: Immutable log entry capturing tool invocations, scan results, and policy decisions

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: DefenseClaw installation completes in under 5 minutes on standard hardware
- **SC-002**: Component scanning adds less than 2 seconds latency to skill loading
- **SC-003**: Guardrail inspection adds less than 10 milliseconds latency per operation
- **SC-004**: 100% of HIGH/CRITICAL scan findings result in auto-block
- **SC-005**: 100% of tool invocations are logged when DefenseClaw is enabled
- **SC-006**: Audit logs support SOC2 Type II, PCI-DSS, and HIPAA evidence requirements
- **SC-007**: Users can switch from hobby mode to DefenseClaw without data loss
- **SC-008**: SIEM events arrive at endpoint within 5 seconds of occurrence

## Assumptions

- DefenseClaw is available at https://github.com/cisco-ai-defense/defenseclaw and installable via curl script
- Users enabling DefenseClaw have Docker, Python 3.10+, Go 1.25+, and Node.js 20+ installed
- DefenseClaw's SQLite audit logging is acceptable for most use cases; SIEM integration is optional
- Guardrails default to observe mode; users explicitly enable action mode when ready
- DefenseClaw TypeScript plugin integrates with OpenClaw without modification to NetClaw code
- Existing NetShell artifacts (policies, scripts) will be removed or archived as DefenseClaw replaces them

## Cleanup

The following artifacts from the original NetShell attempt should be removed/archived:

- `netshell/` directory - DefenseClaw handles all security
- `netshell/policies/*.yaml` - DefenseClaw has its own policy system
- `netshell/scripts/*.py` - DefenseClaw provides its own CLI
- References in SOUL.md P18-P25 - Update to reference DefenseClaw
- References in CLAUDE.md - Update to reference DefenseClaw
- NetShell section in install.sh - Replace with DefenseClaw

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SECURITY MODE SELECTION                          │
│                                                                          │
│   ┌──────────────────────────┐          ┌─────────────────────────┐     │
│   │      DefenseClaw         │          │      Hobby Mode         │     │
│   │     (Recommended)        │          │    (No Protection)      │     │
│   └────────────┬─────────────┘          └─────────────────────────┘     │
│                │                                                         │
│   ┌────────────▼─────────────┐                                          │
│   │     OPENSHELL SANDBOX    │  (DefenseClaw auto-setup)                │
│   │  • Landlock filesystem   │                                          │
│   │  • seccomp syscalls      │                                          │
│   │  • Network isolation     │                                          │
│   └────────────┬─────────────┘                                          │
│                │                                                         │
│   ┌────────────▼─────────────┐                                          │
│   │   DEFENSECLAW GATEWAY    │                                          │
│   ├──────────────────────────┤                                          │
│   │  • Component scanning    │                                          │
│   │  • CodeGuard analysis    │                                          │
│   │  • LLM inspection        │                                          │
│   │  • Tool guardrails       │                                          │
│   │  • SIEM integration      │                                          │
│   └──────────────────────────┘                                          │
└─────────────────────────────────────────────────────────────────────────┘
```
