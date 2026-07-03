# Feature Specification: Claroty xDome MCP Server

**Feature Branch**: `035-claroty-mcp`
**Created**: 2026-06-08
**Status**: Draft
**Input**: Add a Claroty xDome MCP server + skills to NetClaw covering OT / IoT / IoMT asset discovery, alert triage, vulnerability response, and topology visualisation.

## User Scenarios & Testing

### User Story 1 — OT asset discovery and classification (Priority: P1)

A NetClaw operator working at a manufacturing site needs to enumerate every OT device under Claroty xDome management, filter by Purdue level and device purpose, and classify any newly discovered device with the right Purdue layer.

**Why this priority**: Asset visibility is the foundation of every other OT workflow. Without it the operator cannot triage alerts, reason about CVE exposure, or render topology.

**Independent Test**: With `NETCLAW_LAB_MODE=true` and a valid `CLAROTY_API_TOKEN`, invoke the `claroty-asset-inventory` skill with the question "list the first 50 OT devices at site X" and verify the response includes device IDs, names, IPs, vendors, Purdue levels, and site IDs.

**Acceptance Scenarios**:

1. **Given** a configured xDome tenant, **When** the operator asks "list the first 50 OT devices at site warehouse-east", **Then** `list_devices(site_id="warehouse-east", limit=50)` returns a GCF-formatted device table.
2. **Given** a device with no Purdue level set, **When** the operator asks "set device 7a2c to Purdue level 2 under CHG0012345", **Then** the ITSM gate validates the CR and (in lab mode) the xDome write succeeds.
3. **Given** an invalid CR format, **When** the operator attempts a write, **Then** the tool returns `{"itsm_gate": {"valid": false, ...}, "applied": false}` without calling xDome.

### User Story 2 — Risk triage across alerts and vulnerabilities (Priority: P2)

A security operator handling an OT incident needs to look at open alerts, compute the affected device set for a CVE, mark a CVE as not-relevant on a specific device (mitigated by network ACL), and label / assign the alert during the hunt.

**Why this priority**: Triage workflows are where the day-to-day operator value lives, but they depend on asset discovery being in place (User Story 1).

**Independent Test**: With a valid token, invoke the `claroty-risk-triage` skill end-to-end: list alerts → get blast radius → suppress a CVE → label alerts → assign alerts. All 6 ITSM-gated write tools accept a valid `CHG\d+` CR in lab mode.

**Acceptance Scenarios**:

1. **Given** open alerts in xDome, **When** the operator asks "list all open high-severity alerts at site X", **Then** `list_alerts(severity="high", status="open", site_id="X")` returns a severity-sorted alert table.
2. **Given** an alert ID, **When** the operator asks for its blast radius, **Then** `get_alert_with_devices(alert_id="...")` returns the alert plus the affected device list in a single response.
3. **Given** a vulnerability that is mitigated on a specific device, **When** the operator asks "mark CVE-X as not-relevant for device Y under CHG0013001", **Then** `set_vulnerability_relevance` is gated and applied.

### User Story 3 — OT topology and zone audit (Priority: P3)

A network engineer reviewing OT segmentation needs to visualise the observed device-to-device communication map, list segmentation zones, and produce an exportable diagram of the OT topology at a site.

**Why this priority**: Visualisation is high-value but lower frequency than asset discovery or triage; rendering happens after the data is in place.

**Independent Test**: Invoke `claroty-ot-topology` with "show me the communication map for device 7a2c as an inline topology" and verify the response includes edges suitable for Canvas / A2UI or draw.io rendering.

**Acceptance Scenarios**:

1. **Given** a device with observed traffic, **When** the operator asks for its communication map, **Then** `get_device_communication_map(device_id="...")` returns edge data the topology renderer can consume.
2. **Given** a configured xDome tenant, **When** the operator asks "list all zones", **Then** `list_organization_zones()` returns the zone catalog with device counts.
3. **Given** a device + time range, **When** the operator asks for OT activity events, **Then** `list_ot_activity_events` returns a paginated event series.

### Edge Cases

- xDome returns HTTP 429: the client honors `Retry-After` and retries up to 5 times.
- xDome returns a paginated list of fewer items than `limit`: the paginator stops cleanly.
- ServiceNow MCP is unreachable when verifying a CR: gate logs a warning and proceeds with `state: "unverified"` (matches the gnmi-mcp pattern).
- Missing `CLAROTY_API_TOKEN`: server fails fast at start with a logged ERROR.
- Invalid Purdue level string: xDome returns a 400 — the tool returns the error dict, no retry.

## Requirements

### Functional Requirements

- **FR-001**: System MUST list xDome devices with site / Purdue / purpose / name filters.
- **FR-002**: System MUST fetch a single device by ID with full attributes.
- **FR-003**: System MUST return the device-to-device communication map for a device or site.
- **FR-004**: System MUST list alerts with severity / status / site / assignee filters.
- **FR-005**: System MUST return an alert plus its affected devices in one composite call.
- **FR-006**: System MUST list vulnerabilities with severity, CVSS-min, and CVE-substring filters.
- **FR-007**: System MUST list devices affected by a single vulnerability (blast radius).
- **FR-008**: System MUST list sites and fetch a single site by ID.
- **FR-009**: System MUST list edge sensor / collector locations (read-only).
- **FR-010**: System MUST list xDome servers and their interfaces.
- **FR-011**: System MUST list OT activity events with device / site / time-range filters.
- **FR-012**: System MUST fetch the xDome audit log with user / action / time filters.
- **FR-013**: System MUST list organization zones.
- **FR-014**: System MUST acknowledge an alert (set resolution state) — ITSM-gated.
- **FR-015**: System MUST set a vulnerability's relevance for a device — ITSM-gated.
- **FR-016**: System MUST assign a Purdue level to a device — ITSM-gated.
- **FR-017**: System MUST set a custom attribute on a device — ITSM-gated.
- **FR-018**: System MUST label one or more alerts (set or replace) — ITSM-gated.
- **FR-019**: System MUST assign one or more alerts to a user — ITSM-gated.
- **FR-020**: System MUST validate every write tool's CR with `validate_change_request` from `utils/itsm_gate.py` and reject malformed or non-Implement CRs (lab-mode bypass via `NETCLAW_LAB_MODE`).
- **FR-021**: System MUST cap outgoing requests at `CLAROTY_RATE_LIMIT_PER_MIN` and honor `Retry-After` on 429 responses.

### Key Entities

- **Device**: id, name, ip_address, mac_address, vendor, model, os, device_type, device_purpose, purdue_level, site_id/name, risk_score, last_seen, first_seen.
- **Alert**: id, title, severity, status, type, description, site, assignee, labels, affected_device_count, created_at, updated_at.
- **Vulnerability**: id, cve_id, title, severity, cvss_score, description, affected_device_count, first_seen, last_seen.
- **Site**: id, name, description, address, device_count, group_id.
- **EdgeLocation**: id, name, site_id, status, last_heartbeat, version.
- **Server**: id, name, ip_address, role, status, version.
- **OTActivityEvent**: id, timestamp, device_id, event_type, description, severity.
- **AuditEntry**: id, timestamp, user, action, target, details.
- **OrganizationZone**: id, name, description, device_count.

## Success Criteria

### Measurable Outcomes

- **SC-001**: An operator can list, filter, and inspect any OT device in xDome in fewer than 3 chat turns.
- **SC-002**: 100% of write tools call `validate_change_request` before any xDome POST — verified by reading the source and by smoke test #5 in `quickstart.md`.
- **SC-003**: When 50 list_devices calls are issued concurrently, the rate limiter prevents any 429 from reaching the user.
- **SC-004**: Adding Claroty does not regress any existing skill — `pyats-health-check` continues to pass after the merge.
- **SC-005**: The Coherence Checklist in `.specify/memory/constitution.md` passes with every box ticked, with the artifacts listed in `checklists/requirements.md`.

## Assumptions

- The operator has a valid xDome API token with read + write scopes for the asset, alert, vulnerability, and user-action endpoints.
- ServiceNow integration is optional at v1; in production the CR state check still falls back to "unverified" if the servicenow-mcp is offline (mirrors the gnmi-mcp pattern).
- Edge sensor lifecycle (add/update/delete locations, generate/rotate API keys), site CRUD, organisation policy CRUD, and CMMS upsert are deferred to a follow-up spec.
- Rendering primitives (Canvas A2UI, draw.io, nwdiag) are provided by existing skills — the topology skill is a data + composition skill, not a renderer.
