# NCFED grant access class (read vs write)

Spec 190, issue #344. Normative text: `docs/ietf/draft-capobianco-ncfed-00.md`, section "Grant Access Class".
The default-deny model is unchanged: a peer still needs a grant for every tool, skill or collection.

## Model

A grant has an access class, a ceiling:

| Grant class | Target read | Target write | Target unclassified |
|---|---|---|---|
| `read` | allow | refuse | refuse |
| `read_write` (default) | allow | allow | allow |

Refusal is -32001 NOT_ALLOWLISTED with the same text as an ungranted target (no classification oracle). The audit row has decision `access_class_denied`.

Legacy grants and grants that omit the class are `read_write`, so nothing changes on upgrade. `N2N_GRANT_DEFAULT_ACCESS=read` makes NEW grants default to `read`; the class is stored on each grant, so existing grants do not change.
A grant that differs only in class from an active grant for the same peer, type and name replaces it (the old one is revoked, and any approval bound to it stops being valid).

## Classifying targets

Resolution order for a tool or skill: operator override, imported annotation (tools only), unclassified.

```text
n2n_classify("tool", "cml-mcp/list_labs", "read")      # override
n2n_classify("tool", "cml-mcp/list_labs")              # clear the override
n2n_import_annotations("cml-mcp", '[{"name":"list_labs","annotations":{"readOnlyHint":true}}]')
n2n_list_classifications()
```

`readOnlyHint` true is read, false is write, absent stores nothing. Import is an explicit operator action; annotations are never fetched from a peer or at call time. An annotation is the tool author's hint, not proof.

Skills are read only if the operator classifies them read. The request text is never inspected. The federation layer cannot check that a read-classified skill does not write inside its own agent turn; that remains with the gateway scope approvals and sandbox.

`knowledge` and `knowledge_replica` targets are always read. They stay separate grants (`knowledge` does not allow replication). Card and inventory pull are not grant-controlled and stay governed by `n2n_set_visibility`.

## Interactions

- Approval: the class check runs first. A refused call creates no approval; approval never widens the class.
- Limits (spec 189): reads and writes share the same counters. A class refusal is not debited, takes no rate slot and never starts warn/teardown. Because of that a peer can probe without consuming budget; each probe is one audit row, review `access_class_denied`.
- Re-check: `admit()` re-runs the check, so reclassifying or replacing a grant while a request waits takes effect at admission. Work already running is not interrupted.
- Card: `mcp_servers[].tool_access` (tool to read/write) and `skills[].access` appear only for classified targets, absence means unclassified. Advisory only, never used to authorize.
- iN2N: the same check runs for internal channels. The Border does not forward the class to a member. A member-specialty skill aggregated by a Border is unclassified unless classified, so it needs a `read_write` grant.

## Operator surface

Daemon: `POST /n2n/grants` (`access_class`), `GET /n2n/grants`, `GET|POST /n2n/classifications`, `POST /n2n/trust` (`access_class`). Invalid values return HTTP 400 and change nothing.
Audit: grant rows with a `read` class have outcome `success:read`; classification changes are rows with `target_type='classification'` (`classified`, `classification_cleared`, `classification_imported`).

## Known limits

Not done in this spec: separate budgets per class, live annotation ingestion, Border-to-member class forwarding, an `admin` class.
