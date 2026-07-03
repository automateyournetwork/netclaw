# Quickstart: DefenseClaw Security Validation

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Created**: 2026-04-11
**Updated**: 2026-04-16

## Prerequisites

1. Docker installed and running
2. Python 3.10+, Go 1.25+, Node.js 20+
3. NetClaw installed

## Enable DefenseClaw

### Option A: During Installation

```bash
./scripts/install.sh
# When prompted:
# Enable DefenseClaw (recommended)? [y/N]: y
```

### Option B: After Installation

```bash
./scripts/defenseclaw-enable.sh
```

### Option C: Manual

```bash
# Install DefenseClaw
curl -LsSf https://raw.githubusercontent.com/cisco-ai-defense/defenseclaw/main/scripts/install.sh | bash

# Initialize with guardrails
defenseclaw init --enable-guardrail
```

---

## Scenario 1: Verify Installation (FR-001, FR-006)

**Goal**: Confirm DefenseClaw is installed and running.

### Steps

1. Check DefenseClaw CLI:
   ```bash
   defenseclaw --version
   # Expected: DefenseClaw 1.x.x
   ```

2. Check gateway is running:
   ```bash
   pgrep defenseclaw-gateway
   # Expected: Process ID shown
   ```

3. Check OpenClaw integration:
   ```bash
   ls ~/.defenseclaw/extensions/defenseclaw
   # Expected: TypeScript plugin files
   ```

### Pass Criteria
- [ ] DefenseClaw CLI available
- [ ] Gateway process running
- [ ] Extension installed

---

## Scenario 2: Component Scanning (FR-007, FR-008, SC-002)

**Goal**: Verify skills/MCPs are scanned before execution.

### Steps

1. Scan a skill:
   ```bash
   defenseclaw skill scan pyats-health-check
   ```

2. **Expected Result**:
   ```
   Scanning skill: pyats-health-check
   ✓ No HIGH/CRITICAL findings
   Status: ALLOWED
   ```

3. Create a test skill with a credential:
   ```bash
   mkdir -p /tmp/bad-skill
   echo 'API_KEY="sk-12345"' > /tmp/bad-skill/config.py
   defenseclaw skill scan /tmp/bad-skill
   ```

4. **Expected Result**:
   ```
   Scanning skill: /tmp/bad-skill
   ✗ HIGH: Hardcoded credential detected
     Location: config.py:1
   Status: BLOCKED
   ```

### Pass Criteria
- [ ] Clean skill passes scan
- [ ] Skill with credential detected and blocked
- [ ] Severity level shown

---

## Scenario 3: Runtime Guardrails (FR-011, FR-014, SC-003)

**Goal**: Verify guardrails inspect and block dangerous operations.

### Steps

1. Enable action mode:
   ```bash
   defenseclaw setup guardrail --mode action --restart
   ```

2. Start NetClaw and attempt dangerous operation:
   ```
   User: Run shell command: rm -rf /
   ```

3. **Expected Result**:
   ```
   [DefenseClaw] Operation blocked
   Category: command
   Reason: Shell command execution not allowed
   ```

4. Check alerts:
   ```bash
   defenseclaw alerts
   ```

5. **Expected Result**: Alert logged with details

### Pass Criteria
- [ ] Dangerous command blocked
- [ ] Alert logged
- [ ] Category identified

---

## Scenario 4: Tool Management (FR-015, FR-016, FR-017)

**Goal**: Verify tool blocking and allowing works.

### Steps

1. Block a specific tool:
   ```bash
   defenseclaw tool block delete_file --reason "destructive operation"
   ```

2. List blocked tools:
   ```bash
   defenseclaw tool list
   ```

3. **Expected Result**:
   ```
   Blocked Tools:
   - delete_file (reason: destructive operation)
   ```

4. Attempt to use blocked tool:
   ```
   User: Delete the file /tmp/test.txt
   ```

5. **Expected Result**:
   ```
   [DefenseClaw] Tool blocked: delete_file
   Reason: destructive operation
   ```

6. Allow the tool:
   ```bash
   defenseclaw tool allow delete_file
   ```

### Pass Criteria
- [ ] Tool blocked via CLI
- [ ] Block enforced at runtime
- [ ] Tool can be unblocked

---

## Scenario 5: Audit Logging (FR-012, SC-005, SC-006)

**Goal**: Verify all operations are logged.

### Steps

1. Run several operations:
   ```
   User: List Meraki organizations
   User: Get SuzieQ devices
   ```

2. View audit logs:
   ```bash
   defenseclaw alerts --limit 10
   ```

3. **Expected Result**: Each operation logged with:
   - Timestamp
   - Tool name
   - Outcome (success/blocked)

4. Export for compliance:
   ```bash
   defenseclaw alerts --export json > audit-export.json
   ```

### Pass Criteria
- [ ] All operations logged
- [ ] Exportable format
- [ ] Sufficient detail for SOC2

---

## Scenario 6: SIEM Integration (FR-012, SC-008)

**Goal**: Verify events can be sent to external SIEM.

### Steps (Optional - requires SIEM)

1. Configure Splunk HEC:
   ```bash
   defenseclaw config siem --type splunk \
     --endpoint https://splunk.example.com:8088 \
     --token $SPLUNK_HEC_TOKEN
   ```

2. Generate test event:
   ```bash
   defenseclaw tool block test_tool --reason "SIEM test"
   ```

3. Verify event in Splunk:
   - Search: `source="defenseclaw"`
   - Expected: Event with block details

### Pass Criteria
- [ ] SIEM configured without error
- [ ] Events appear in SIEM
- [ ] Within 5 seconds (SC-008)

---

## Scenario 7: Hobby Mode (FR-003, FR-018)

**Goal**: Verify NetClaw works without DefenseClaw.

### Steps

1. Disable DefenseClaw:
   ```bash
   ./scripts/defenseclaw-disable.sh
   ```

2. Start NetClaw:
   ```bash
   openclaw gateway
   ```

3. **Expected Result**: NetClaw starts normally without security prompts

4. Verify no sandboxing:
   ```bash
   # No defenseclaw-gateway process
   pgrep defenseclaw-gateway
   # Expected: No output
   ```

### Pass Criteria
- [ ] NetClaw runs without DefenseClaw
- [ ] No security overhead
- [ ] Full host access

---

## Scenario 8: Upgrade from Hobby Mode (FR-019)

**Goal**: Verify users can enable DefenseClaw after initial install.

### Steps

1. Start in hobby mode (DefenseClaw disabled)

2. Run enable script:
   ```bash
   ./scripts/defenseclaw-enable.sh
   ```

3. **Expected Result**:
   ```
   Checking prerequisites...
   ✓ Docker running
   ✓ Python 3.10+
   ✓ Go 1.25+
   ✓ Node.js 20+

   Installing DefenseClaw...
   ✓ DefenseClaw installed

   Initializing guardrails...
   ✓ Guardrails enabled (observe mode)

   DefenseClaw is now active.
   ```

4. Verify upgrade:
   ```bash
   defenseclaw --version
   defenseclaw alerts
   ```

### Pass Criteria
- [ ] Enable script runs successfully
- [ ] Prerequisites checked
- [ ] DefenseClaw active after enable

---

## Performance Validation

### Installation Time (SC-001)

```bash
time curl -LsSf https://raw.githubusercontent.com/cisco-ai-defense/defenseclaw/main/scripts/install.sh | bash
# Target: < 5 minutes
```

### Scan Latency (SC-002)

```bash
time defenseclaw skill scan pyats-health-check
# Target: < 2 seconds
```

### Guardrail Latency (SC-003)

```bash
# Measure with and without DefenseClaw
# Difference should be < 10ms per operation
```

---

## Summary Checklist

| Scenario | User Story | Status |
|----------|------------|--------|
| 1. Verify Installation | US1 | [ ] Pass |
| 2. Component Scanning | US1 | [ ] Pass |
| 3. Runtime Guardrails | US2 | [ ] Pass |
| 4. Tool Management | US4 | [ ] Pass |
| 5. Audit Logging | US1 | [ ] Pass |
| 6. SIEM Integration | US1 | [ ] Pass |
| 7. Hobby Mode | US3 | [ ] Pass |
| 8. Upgrade from Hobby | US3 | [ ] Pass |
