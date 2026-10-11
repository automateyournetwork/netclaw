# Privacy

The extension connects only to installations you explicitly select and bind. Local
connections use a private stdio process. SSH connections use your existing SSH
configuration and strict known-host checking. Provider keys remain on the backend.

Connection profiles contain nonsecret paths and installation identities in private
extension-host storage. They are not registered for Settings Sync. Chat draft
retention is opt-in. Conversation identifiers and admission receipts are retained
to resume existing work without resubmitting uncertain requests. Canvas content is
saved when you choose Save or Send. Backend journals, artifacts and GAIT evidence
belong to the selected installation.

RAG uploads require a selected file and review of its name, size, digest and
destination. The backend retains that file and indexes it in its existing RAG
store. No workspace is automatically ingested. Search uses the backend's installed
local embedding models. Adding a search result to context does not invoke an LLM;
selecting it in a submitted Chat or Canvas request sends it to NetClaw's configured
runtime and potentially its model provider. Review the backend's provider settings
and retention policy before submitting private material.

The extension sends no product telemetry. Local Avatar assets do not require an
external media service. Diagnostic export opens a local preview before you save
it. Credentials, runtime homes, audit databases and backend code are excluded from
the VSIX by an explicit file allowlist.

Uninstalling the extension does not stop backend services or remove their retained
documents, investigations or audit records. The editor may retain extension-host
storage after uninstall; remove only reviewed local extension data if desired.

An unrestricted terminal agent running as the same OS user can access that user's
files independently of this extension. The assistant MCP surface is not an OS
sandbox and cannot establish independent human approval against such an agent.
