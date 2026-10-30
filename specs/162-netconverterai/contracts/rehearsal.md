# Virtual migration rehearsal contract

## Tool discovery and eligibility

Discover the installed lab MCP schema first; static skill examples may be stale. Record exact image/template identity, actual image availability, OS/version/architecture, entitlement, resource capacity and management/bootstrap path. Templates alone do not prove images exist. Select a conversion direction supported by both NetConverter account capability and the actual target OS.

CML has topology/node lifecycle and optional CLI support; containerlab has deploy/inspect/exec but no generic private file staging; EVE templates are not installed-image evidence; GNS3 has lifecycle/templates but no existing configuration apply tool. Remote startup-config paths are remote-host paths. No path or capability is invented to fill these gaps.

## Provisioning

Require explicit run scope and isolated management/data networks. Record ownership and attempted creation before calls. Reconcile uncertain results using exact provider object IDs and run ownership. Do not adopt/modify an existing lab by name or attach to production. Bootstrap configuration needs its own authorized scope and must not conceal the migration candidate. A target without a qualified management/configuration path is ineligible for apply.

## Artifact-bound configuration

Extend the existing Terminal Intent candidate-selection UI and API record. The reviewed candidate's ID/hash and exact endpoints/tool/testbed are immutable for that request. Preserve existing read-only baseline/rollback capture before APPLY.

The API issues a bounded one-use apply capability only during its real authorized transition. The configuration tool receives an artifact reference plus trusted context, reads the candidate locally, verifies all bindings and atomically records its attempt. The existing configuration tool identity, dangerous-command guard and runtime policies still apply. A denied original route must deny the artifact form. A model-provided boolean, arbitrary record path or text saying APPLY grants nothing.

### Issuer and consumer

Use an API-owned per-installation signing key and private grant directory outside model-controlled plan/artifact paths. The signed schema-1 claim contains a random opaque nonce, installation/task/harness binding, API record ID and revision, request hash, policy revision, exact tool identity, endpoint identity digest, active testbed digest, candidate artifact ID/hash/size, baseline and rollback hashes, and a short expiry (maximum five minutes). Only the existing API transition issues it after validating the reviewed candidate and baseline/rollback evidence. No grant issuer is exposed through MCP, a generic file helper or the setup wizard.

The existing configuration tool's artifact form accepts only an opaque grant reference and artifact reference. It uses a fixed trusted grant root/verification-key reference from installation configuration, verifies signature and every bound field against current trusted state, and atomically claims the nonce in a private durable ledger before execution. It must reject closed/changed records, wrong harness/task, changed policy/endpoint/testbed/bytes, expiry and reuse. Verification of the capability never replaces the runtime's existing permission to call that exact configuration tool. An integration unable to preserve the original tool denial is unavailable.

Private files and signatures defend the declared API/tool boundary; they are not a sandbox against a malicious same-OS-user process that can read signing material or rewrite trusted runtime files. Preserve the existing deployment's filesystem/tool restrictions and state this limit without claiming cryptographic protection against the local owner.

Implement through the existing managed pyATS configuration entrypoint with an optional mutually exclusive artifact reference, rather than creating a second tool name that bypasses its policy. Keep actual command/diff/baseline content in private artifacts and suppress raw logging at this boundary. API-owned context/capability issuer and consumer must be verified together; do not ship a tool that trusts a phase field alone.

Local/Lab requires explicitly designated SSH identities and the existing API-created record. Hermes Local/Lab APPLY is unavailable. Production and vendor-specific tools keep their approved ServiceNow/config-tool requirements. No raw SSH/console/container exec fallback after denial.

## Verification

Use a persistent pyATS process for dynamic inventory, validation, activation and subsequent operations. Verify actual target identity before apply and actual readback/commit before behavior tests. Compare source and target against one assertion matrix where both are available:

- permitted and denied TCP/UDP paths, including negative controls;
- routes, next hops, VRFs, selected OSPF/BGP adjacency and convergence assertions;
- NAT translation evidenced by traffic plus session/counter/capture observations when applicable;
- unchanged management connectivity and rollback/recovery checks within scope.

Each assertion records executed/planned/unsupported status and its evidence class. Static Batfish queries require explicit query success and parse coverage; partial parsing or caught exceptions cannot become a passing equivalence result. FRR peers may drive traffic but cannot replace the target firewall or establish a native unsupported conversion.

## Recovery and retention

On configuration timeout, inspect actual state before any further write. Failed tests preserve failure status even after successful recovery. Retain run-owned resources by default; provide explicit scoped stop/recovery instructions. Never automatically invoke delete, wipe, destroy or snapshot restore under a cleanup label.

## Required tests

Prove no apply in PREPARE, no apply with mutated candidate/endpoint/testbed/route or wrong harness, no grant issuance by model tools, no duplicate apply across concurrency/restart and no artifact-form bypass of a denied configuration tool. Verify resource-ownership reconciliation and no unowned/destructive cleanup. Qualify a real supported vendor target separately from simulated peers and FRR orchestration exercises.
