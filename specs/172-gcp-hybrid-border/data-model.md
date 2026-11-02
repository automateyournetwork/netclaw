# R03 entities and transitions

- **Role activation v1** binds installation_id, role(border/member), protected=true,
  runtime_kind, absolute owned home/source/interpreter/build paths, source hashes,
  explicit environment references, listener definitions and service identities.
  Border requires control_only=true, exact HTTPS origin and strict registry;
  rejects member runtime/catalog/provider/device fields. It cannot initialize or
  select an ambient home. Validation precedes service generation/start.
- **Device selector v1** contains1–16 entries. Each binds a complete model profile,
  complete tool-call profile and immutable existing DockerExecutor config. Full
  signed equality must produce exactly one entry; no fallback or shared mutation.
  Existing single-runtime format remains supported. Duplicate model IDs/catalog
  tool+canonical-argument identities are rejected where ambiguous.
- **Protected operation** retains all R02 fields and transitions. Review→approve/
  deny→claim→effect→receipt→durable ACK, with unknown outcomes spent. No schema or
  authority expansion; one device/tool per approval, at most two inference calls.
- **Browser references v2**: at most32 nonce/optional-ID records scoped to selected
  installation. Migrate the old one-reference format; no secrets/results/reviews.
  Remove only terminal references meeting the ingress contract predicate; unresolved records never silently
  overwritten. Restoration reads status only; explicit reconcile may retrieve existing receipt or redeliver existing ACK, never execute. Explicit owner ID recovery
  remains available; fresh-browser discovery is not claimed.
- **Cloud plan manifest**: selected project/region/zone, unique deployment/state,
  exact saved-plan and source hashes, resources/labels/expiry, DNS, IAM, ports,
  service units, cost bounds, approval evidence and teardown retention/residue.
  Proposed→reviewed/delegated→applied→qualified→evidence exported→destroy reviewed/
  delegated→retired. Missing delegation or unresolved spend gate prevents mutation.

All durable identity/ledger changes remain private and atomic. Source contains
only schemas/templates/sanitized evidence, never credentials, tokens or tfstate.
