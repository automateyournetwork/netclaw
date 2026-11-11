# Data Model: spec 190

## invocation_grant (extended)
Existing columns plus `access_class TEXT NOT NULL DEFAULT 'read_write'` (values `read`, `read_write`). Validation at the Authorizer API (CHECK not used so ALTER stays portable). Legacy rows take the default.

## tool_classification (new)
| column | type | note |
|---|---|---|
| target_type | TEXT | `tool` or `skill` |
| target_name | TEXT | `server/tool` or skill name |
| access | TEXT | `read` or `write` |
| source | TEXT | `operator` or `annotation` |
| updated_at | TEXT | UTC |
Primary key (target_type, target_name, source). Effective class: `operator` row, else `annotation` row, else unclassified. Clearing an override deletes only the `operator` row.

## Effective-class function
`effective_class(target_type, target_name)`: knowledge/knowledge_replica -> `read`; tool/skill -> per above; any other type -> `unclassified`.

## Decision additions
No new fields on `Decision`; refusal is `Decision(False, "not_allowlisted", grant, reason)`. Audit decision string `access_class_denied` (written by invocation handlers via a `Decision.reason_code` free attribute is avoided; instead `Authorizer` records the audit row itself through `self.audit`, as spec 189 limit events do).
