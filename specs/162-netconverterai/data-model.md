# Spec162 data model

All entities are installation-scoped. Secrets and raw configurations stay in private storage; public/exported evidence contains bounded non-secret summaries. No model-visible field issues approval.

## ConnectionBinding

Fields: installation ID, mode (`hosted-readonly` / `local-terminal`), fixed API/MCP destinations, operator account reference, credential keyed fingerprint, canonical workspace/executable references, executable/version provenance, privacy cap, capability-schema digest and observed timestamp.

The account label does not prove tenant identity. An endpoint, credential, executable, workspace or relevant capability change invalidates associated unconsumed approval. No automatic cross-binding fallback.

## SubmissionRequest and DisclosureGrant

Request: opaque ID, installation/task binding, source file identity, frozen artifact ID, SHA-256/bytes, operation, source/target/device-class, normalized validated options, connection fingerprint, creation time and canonical review digest.

Grant: exact request/digest, trusted operator approval origin, issued/expiry time, consumed timestamp and attempt ID. Default lifetime five minutes; bounded maximum one hour. Approval cannot be supplied as a tool boolean or minted by a model-facing tool.

States: `prepared → approved → attempting → submitted`; `prepared/approved → invalidated|expired|declined`; `attempting → unknown|refused`; submitted jobs subsequently have provider-specific bounded status. Mark attempting and consume the grant in one transaction before the external call. Unknown never transitions back to approved for replay. Reconciliation can attach confirmed job evidence, not invent a new submission.

## Artifact

Opaque ID, installation/run/request/job references, role (`source`, `candidate`, `baseline`, `rollback`, `report`, `capture`), canonical confined path, hash, byte length, producer/time and verification status.

Reject path traversal, symlinks, hardlinks where they break ownership, nonregular files, oversized content and conflicting existing output. Inspect through descriptors; never trust path metadata alone. Frozen source sits inside the selected workspace so privacy policy is inherited. Artifact identity/digest must be checked before every execution use. Hash integrity does not imply semantic correctness.

## TwinRun and OwnedResource

Run: ID, purpose/reference migration, selected platform/MCP binding, exact tool-schema evidence, image/template/version/digest/architecture, entitlement and capacity observations, isolated networks, approved lifecycle scope, endpoint inventory, source/candidate artifact references, expected assertions and current state.

Resource: run ID, provider ID, exact platform object ID, kind, ownership proof, creation attempt, observed status and retention/recovery decision. Do not match ownership by display name alone.

States: `proposed → eligible → provisioning → booting → ready → preparing_apply → applying → verifying → verified|failed|blocked|unknown`. Some phases are unavailable for a platform; report why. Unknown creation or apply requires read-only reconciliation. Retained resources remain explicit and are not deleted automatically.

## CandidateApplyBinding

Extend the existing API-owned Terminal Intent record: candidate ID/hash/bytes, selected endpoint identities, active testbed fingerprint, exact configuration tool, verification profile, trusted task/harness binding and one-use attempt.

Only the existing reviewed UI/API workflow plus real baseline/rollback checks can issue the apply capability. It binds issuer, record revision, installation/task, candidate, endpoint, tool and expiry. Reading an arbitrary apply-phase record or receiving a model-supplied run ID is not sufficient. Runtime configuration-tool authorization remains independently required. Hermes Local/Lab APPLY remains unavailable.

Candidate bytes, endpoint identity, testbed fingerprint, policy/record revision or route changes invalidate the capability. Claim an attempt atomically before mutation. Configuration, diffs and command logs stay private. Unknown outcome requires inspection rather than another claim.

## ValidationRecord

Fields: run/step ID, evidence class (`controlled-peer`, `static-model`, `live-virtual`, `live-device`), producer/version, input/image hashes, assertion/expected result, observed result, query/parse status, timestamps, supporting artifact IDs and limitation codes.

Verdicts: `passed`, `failed`, `blocked`, `not_applicable`, `not_run`, `unknown`. Never collapse these to a single percent. Differential equality is valid only when the corresponding queries executed successfully with adequate parse/feature coverage. NAT needs actual represented NAT assertions and observations.

## ReviewPackage

References to evidence, observed/proposed diagrams, Jev assessment if available, failed/untested checks, manual actions, rollback/recovery plan, retained-resource inventory and draft ticket/document paths. Publication/ticket state is separate from preparation. No conversion result or advisory probability is a production approval.
