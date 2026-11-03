# Immutable member device selector v1

Optional additive runtime wrapper, exact keys:

```json
{"schemaVersion":1,"profiles":[{"model_profile_id":"pinned-profile-id","tool_call":{},"runtime":{}}]}
```

`profiles` has1–16 entries. `tool_call` contains exactly the existing seven signed
fields (tool, tool_schema_sha256, arguments, arguments_sha256, device_ref,
inventory_revision, endpoint_sha256), validated by the existing contract; no
limits/expiry/paths are added. Tool implementation pins remain in the existing
model/runtime binding; no signed wire field changes.
`runtime` is one complete existing DockerExecutor configuration. Its complete
model_profile.profile_id equals model_profile_id. Selector comparison uses the
**complete** signed model_profile and tool_call, not IDs/arguments alone.

The wrapper covers exactly the Cartesian product of current catalog model_profiles
and tools once per pair. Reject duplicates/unknown keys, duplicate model IDs,
duplicate (tool, canonical arguments) catalog identities, missing/extra coverage,
inconsistent same-ID model profiles or same-call pins and mismatched derived
runtime/tool/inventory/endpoint pins. All profiles share the same durable state_dir.
Retain immutable canonical in-memory snapshots of the existing private profile; do not mutate shared config for selection. Existing
single-runtime configuration remains accepted with unchanged behavior.

`ProfiledExecutor(config, manager=...)` provides run(payload,gate),
validate_catalog(catalog,runtime_config=...), and close(). Validate full config and
configuration at construction, then catalog at service startup before admission and each catalog reread. Runtime/profile edits
require restart and cannot silently change a live selector. Build children only
from validated immutable snapshots; each retains a one-device frozen inventory,
known_hosts, scoped aliases, source pins and existing durable inference ledger.
The service cancels/awaits workers before closing child connections.

A pure catalog validator in protected_contract.py has no Docker imports on Border.
The factory in protected_runtime.py recognizes the wrapper; normal runtime falls
through to existing DockerExecutor. Root owns service hooks and role validation;
selector lane owns protected_selection.py, factory dispatch, pure validator/tests.
