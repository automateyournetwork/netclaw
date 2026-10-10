# Capability card contract

Add `harness` beside existing `llm`, `mcp_servers`, `skills` and `posture`:

```json
{"harness":{"type":"hermes","version":"0.21.6","source":"local-observation","observed_at":"2026-10-10T00:00:00Z","status":"known"}}
```

Illustrative version/time only. Producers read the selected installed runtime; do not invoke a provider. Consumers re-label provenance peer-advertised/member-advertised and retain receipt freshness. Authenticated identity is not software attestation.

Type max64, version max128, safe visible identifier characters only; reject secrets/commands/paths/markup. Missing/malformed object becomes unknown with null values. Unknown safe type is unrecognized, retained for forward compatibility. Missing version stays null. Invalid dates become unavailable. No missing harness implies OpenClaw. `version` at card top remains its existing inventory sequence; enrollment `runtime_kind` remains process/mobile/etc.

Internal member projection and health storage retain sanitized harness information. External card represents only the advertising Border's runtime; never serialize member topology. Model/tool inventory remains separate from eligibility, execution evidence and posture. New/old card interoperability, malformed fields, escaped HUD rendering, freshness and absence are acceptance cases.

Version provenance is local to the selected executable/source manifest. A compiled compatibility manifest alone is not proof that a selected node runs that source: qualify/inspect installed source before advertising a known version. Status observation must never start an agent/provider. If source identity/version cannot be established, keep version null. Existing OpenClaw version discovery must inspect the selected installation and use a bounded local probe only.
