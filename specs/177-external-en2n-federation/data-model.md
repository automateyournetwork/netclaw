# R06 Data Model

Reuse existing authority/storage; no parallel peer/task system.

| Entity | Existing fields/addition | Validation/lifecycle |
|---|---|---|
| Installation | Selected home/config, UUID, owner.json, risk, key/cert | Fresh owned home; no foreign fallback/protected-marker removal |
| Endpoint | Existing schema2 address/TLS/app trust and revision | Strict validation; separate listen/dial and iN2N/eN2N |
| Peer | Existing peer and consent rows | Actual possession identity; nonfederated→one-sided→federated→revoked |
| Export/grant | Visibility and invocation_grant | Independent visibility/authority; exact approval and budget revalidation |
| Request/chat/task | Existing task/audit/chat and client_request | Original owner/ID preserved; no uncertain replay or context mixing |
| Ordinary cloud surface | Additive private mode/capability | Exact origin/installation/backend; no protected flags or operations; mode change refuses |
| External provenance | Optional bounded task/client metadata | Native peer and remote request/task references; remote-untrusted; never inferred from model/user text |
| Deployment | New private IaC/claims/source/expiry/evidence | Known/unknown outcomes retained; owned cleanup after export |

Public projections exclude keys/tokens/private paths/environment and member topology. Optional client provenance is backward compatible. Provider secrets stay in the separate private gateway/guard service; signer state remains private to federation.
