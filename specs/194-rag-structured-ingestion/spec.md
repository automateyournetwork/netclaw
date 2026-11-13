# Spec 194 — structured JSON and appliance URLs in the RAG knowledge base

Operators need to ingest an API description from a local file, an attachment or a URL and retrieve cited endpoint details. A browser-rendered documentation portal can yield an empty HTML shell. Some LAN HTTPS servers need an HTTP/2-capable client or an explicit certificate exception.

- FR1. Accept JSON through all existing document entry points. Recognize OpenAPI and Swagger JSON, retain method and path headings with their operation details, and index ordinary JSON as text. Invalid JSON produces a structured parse error.
- FR2. HTML preview reports extractable text length, thin-page and likely SPA-shell flags, and actionable guidance. Preview performs no writes.
- FR3. Verify TLS by default. Allow the caller to disable verification for a selected request. Use system curl with HTTP/2 negotiation on local HTTPS endpoints when supported. Preserve document byte limits, crawl confirmation and public URL behavior.
- FR4. Document these options in the generic skill and server reference. Existing callers and indexed documents continue to work.

The existing HUD upload form accepts the same new extension as the MCP. No new HUD control, site-specific skill text, new MCP tool, model download or schema migration is required.
