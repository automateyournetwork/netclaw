# Data Model: Auvik API MCP Server (036)

**Phase 1 output.** Entities mirror the Auvik JSON:API resource objects (`{id, type, attributes{…}, relationships{…}}`). The MCP shapes each into a flat dataclass (`models/responses.py`) holding `id`, `type`, and the listed attribute fields; `to_dict()` drops `None`, `to_json()` serializes via TOON with a JSON fallback. Field names below are the exact `attributes.*` keys from the spec.

## Inventory entities

### Device (`/v1/inventory/device/info`)
`id`, `type` · `deviceName`, `ipAddresses[]`, `deviceType` (enum, 48 vals), `makeModel`, `vendorName`, `softwareVersion`, `firmwareVersion`, `serialNumber`, `description`, `lastModified`, `lastSeenTime`, `onlineStatus` (enum).

### DeviceDetail (`/v1/inventory/device/detail`, `/detail/extended`)
`discoveryStatus` (object: `snmp`/`login`/`wmi`/`vmware`, each enum `disabled…privileged`), `manageStatus` (bool), `trafficInsightsStatus` (enum). Extended detail requires `filter[deviceType]`.

### DeviceLifecycle (`/v1/inventory/device/lifecycle`)
`deviceName`, `salesAvailability`, `softwareMaintenanceStatus`, `securitySoftwareMaintenanceStatus`, `lastSupportStatus` (all four share lifecycle enum: `covered, available, expired, securityOnly, unpublished, empty`).

### DeviceWarranty (`/v1/inventory/device/warranty`)
`deviceName`, `serviceCoverageStatus`, `serviceAttachmentStatus`, `contractRenewalAvailability`, `warrantyCoverageStatus`, `warrantyExpirationDate`, `recommendedSoftwareVersion`.

### Network (`/v1/inventory/network/info`, `/detail`)
`id`, `type` · `networkType` (enum), `scanStatus`, `description`, `scope` (detail: `private|public`), collector fields (`primaryCollector`, `secondaryCollectors`), `deviceCount`/`devices` (relationship).

### Interface (`/v1/inventory/interface/info`)
`id`, `type` · `interfaceType` (enum, 30 vals), `parentDevice` (relationship), `adminStatus`, `operationalStatus` (enum), `macAddress`, `index`, `description`.

### Component (`/v1/inventory/component/info`)
`id`, `type` · `deviceId`/`deviceName` (filterable), `componentType`, `currentStatus` (enum `ok|degraded|failed`), `name`, `modifiedAt`.

### Configuration (`/v1/inventory/configuration`)
`id`, `type` · `backupTime`, `isRunning` (bool). Device link + config body are JSON:API **relationships**; the single-fetch `/{id}` returns the fuller record (use it to retrieve the backup detail).

### Tenant (`/v1/tenants`, `/v1/tenants/detail`)
List: `domainPrefix`, `tenantType` (enum `corporateIt|client|multiClient`). Detail: + `displayName`, `enabled` (bool), `subscribed` (bool), `subscriptionOwner`, `running` (bool), `trialStartDate`, `trialEndDate`, `address` (nested).

### EntityNote (`/v1/inventory/entity/note`)
`id`, `type` · `entityId`, `entityType` (enum `root|device|network|interface`), `entityName`, `lastModifiedBy`, `modifiedAt`, `body`.

### EntityAudit (`/v1/inventory/entity/audit`)
`id`, `type` · `user`, `category` (enum), `status` (enum), `modifiedAt`, `details`.

### Usage (`/v1/billing/usage/client`, `/device/{id}`)
Scope = client | device. Billed device counts/metrics over `fromDate`…`thruDate`.

## Alerts entity

### Alert (`/v1/alert/history/info`)
`id`, `type` · `name`, `severity` (enum `unknown|emergency|critical|warning|info`), `status` (enum `created|resolved|paused|unpaused`), `alertDefinitionId`, `specificationId`, `entityId`/`entityType` (relationship), `detectedOn`, `description`, `dismissed` (bool), `dispatched` (bool), `externalTicket[]`.

## Performance entities

### Statistic (`/v1/stat/{device|deviceAvailability|interface|service|component/{componentType}|oid}/{statId}`)
`statId` (enum per category), entity reference (`deviceId`/`interfaceId`/`serviceId`/`componentId`/`oid`), `interval` (`minute|hour|day`), and a series of `{time, value}` points under `attributes`. OID stat is point-in-time (no interval/time window).

### SnmpPollerSetting (`/v1/settings/snmppoller`, `/{snmpPollerSettingId}`, `/{snmpPollerSettingId}/devices`)
`snmpPollerSettingId`, `name`, `oid`, `type` (`string|numeric`), `useAs` (`serialNo|poller`), device bindings (the `/devices` sub-resource).

### SnmpPollerHistory (`/v1/stat/snmppoller/string`, `/int`)
String history: `{time, value}` series, no interval (`compact` bool option). Numeric history: interval-bucketed `{time, value}` series. Both require `tenants` + `fromTime`.

## Cross-cutting (internal) types

### ResolutionCandidate
Returned when a name/IP/partial is ambiguous: `{ id, name, ipAddress, entityType, tenant }`. The tool returns the candidate list and asks the operator to choose; it never auto-selects.

### PageResult
Internal aggregate from `client.get_all()`: `{ items[], page_count, truncated (bool), next_cursor }`. `truncated=true` + `next_cursor` when `AUVIK_MAX_PAGES` capped the walk.

### ToolError
Uniform error envelope: `{ error: { code, message, details } }` (e.g., `code` ∈ `ValidationError, AuthError, NotFound, Ambiguous, RateLimited, UpstreamError`).
