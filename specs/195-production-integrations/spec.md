# Spec 195 — optional IP reputation and threat intelligence integrations

Operators need to discover and install a GreyNoise Community IPv4 lookup and the community threat intelligence server through NetClaw. Operators who also configure models with decimal prices need the installer to read the MCP section of that configuration.

- FR1. Expose the GreyNoise Community lookup as an optional managed component. Validate input before making a request, use a bounded timeout and support anonymous and keyed requests. Report failures without disclosing credentials.
- FR2. Install the community threat intelligence server from its reviewed source through the component catalog. Make the launcher and required configuration discoverable. Existing installations must be able to add or re-run either component.
- FR3. Loading MCP registrations must accept decimal numbers elsewhere in the configuration. Continue applying the existing strict validation to the MCP subtree and to Claw Plan records.
- FR4. The generated launch commands must start in their selected runtimes and answer MCP tool discovery. Installing these components alongside RAG must preserve ingestion and retrieval of cited results.
