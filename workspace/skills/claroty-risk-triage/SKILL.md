---
name: claroty-risk-triage
description: "Triage Claroty xDome alerts and vulnerabilities, compute blast radius, correlate with NVD CVE data, and drive ITSM-gated workflow actions (acknowledge, label, assign, set relevance)."
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["CLAROTY_API_URL", "CLAROTY_API_TOKEN"]
---

# Claroty Risk Triage

Unified alert + vulnerability triage for OT / IoT / IoMT environments via Claroty xDome. Alerts and vulnerabilities are bundled into one skill because real incident response crosses the boundary constantly — operators investigate an alert, pivot to the affected device's CVE list, and back to the alert label.

## When to Use

- Triaging Claroty xDome alerts by severity, site, or assignee
- Computing the blast radius of an alert (which devices, which protocols)
- Inspecting vulnerability findings, filtering by CVSS, and listing affected devices
- Marking a CVE as not-relevant for a specific device (mitigation in place, compensating control, patched out-of-band)
- Acknowledging, labelling, or assigning alerts during a hunt
- Handing off to `ise-incident-response` for endpoint quarantine or to `servicenow-change-workflow` for a remediation CR

## MCP Server

- **Server**: `claroty-mcp`
- **Command**: `python3 -u mcp-servers/claroty-mcp/claroty_mcp_server.py` (stdio transport)
- **Auth**: Bearer token via `CLAROTY_API_TOKEN`
- **ITSM**: Write operations require a `CHG\d+` CR; bypassed in `NETCLAW_LAB_MODE=true`

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `list_alerts` | `severity?, status?, site_id?, assignee?, limit?, offset?, max_items?` | List security alerts with filters |
| `get_alert_with_devices` | `alert_id, device_limit?` | Alert + affected devices in one call |
| `list_vulnerabilities` | `severity?, cvss_min?, cve_contains?, limit?, offset?, max_items?` | List CVE-aligned findings |
| `get_vulnerable_devices` | `vulnerability_id, limit?, offset?` | Devices affected by one CVE (blast radius) |
| `acknowledge_alert` | `alert_id, resolution, cr_number, note?` | **Write (ITSM-gated)** — set resolution state |
| `set_vulnerability_relevance` | `device_id, vulnerability_id, relevant, cr_number, note?` | **Write (ITSM-gated)** — suppress / re-enable CVE on a device |
| `label_alerts` | `alert_ids, labels, cr_number, replace?` | **Write (ITSM-gated)** — apply / replace labels |
| `assign_alerts` | `alert_ids, assignee, cr_number, note?` | **Write (ITSM-gated)** — assign alerts to a user / queue |

Compose with:

- `nvd_get_cve` from the **nvd-cve** skill for full CVSS vector decomposition
- `ise-incident-response` skill for endpoint quarantine
- `servicenow-change-workflow` skill to open a remediation CR if the alert demands a config change

## Workflow Examples

### Triage all high-severity open alerts

```
"List all open high-severity alerts at site warehouse-east"
```

Calls `list_alerts(severity="high", status="open", site_id="warehouse-east")`. Returns severity-sorted alert table.

### Blast-radius investigation

```
"Show me alert a1b2c3 and every device it touches"
```

Calls `get_alert_with_devices(alert_id="a1b2c3")` and renders the alert metadata plus affected devices. From there, pivot to `list_vulnerabilities` filtered by site to understand combined risk.

### CVE blast radius across the fleet

```
"What devices are vulnerable to CVE-2024-12345? Correlate with NVD for full context."
```

1. `list_vulnerabilities(cve_contains="2024-12345")` → xDome finding ID.
2. `get_vulnerable_devices(vulnerability_id="<id>")` → affected device list.
3. `nvd_get_cve(cve_id="CVE-2024-12345")` (nvd-cve skill) → CVSS vector, references, fix availability.
4. Optionally `list_devices` with cross-reference to Nautobot to confirm criticality.

### Suppress a known false positive

```
"Mark CVE-2024-12345 as not-relevant for device 7a2c (mitigated by network ACL) under CHG0013001"
```

Calls `set_vulnerability_relevance(device_id="7a2c...", vulnerability_id="<id>", relevant=False, cr_number="CHG0013001", note="mitigated by network ACL")`.

### Label and assign an alert during a hunt

```
"Label alerts [a1, a2, a3] as 'ransomware-candidate' and assign to alice under CHG0013002"
```

1. `label_alerts(alert_ids=[...], labels=["ransomware-candidate"], cr_number="CHG0013002")`.
2. `assign_alerts(alert_ids=[...], assignee="alice", cr_number="CHG0013002")`.

### Acknowledge after remediation

```
"Acknowledge alert a1b2c3 as resolved with a note pointing at CHG0013001's evidence"
```

Calls `acknowledge_alert(alert_id="a1b2c3", resolution="resolved", cr_number="CHG0013001", note="...")`.

## ITSM gating

Identical to other Claroty write tools: `CHG\d+` format, ServiceNow "Implement" state check (skipped in lab mode). Rejected gate returns `{"itsm_gate": {...}, "applied": false}` and the xDome write is not made.

## ISE handoff pattern

If a Claroty alert resolves to "compromised endpoint", do **NOT** call ISE quarantine from inside this skill. Hand off to `ise-incident-response` per Principle XIV (human-in-the-loop for external actions). That skill enforces the human decision point before any quarantine action.

## Token scope expectations

If a write tool returns `applied: false` and an `error` object with `status_code: 403`, the ITSM gate passed and the body was correctly built — xDome rejected at RBAC. The token in `CLAROTY_API_TOKEN` lacks write scope on the relevant resource (alerts for `acknowledge_alert`/`label_alerts`/`assign_alerts`; vulnerabilities for `set_vulnerability_relevance`). Don't retry — escalate to whoever provisions xDome API tokens. The wrapper surfaces xDome's response body verbatim so you can see exactly which scope is missing.
