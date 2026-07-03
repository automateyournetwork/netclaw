# Wiring guardrails

- Stop affected endpoint nodes before changing interface wiring.
- Do not stop the whole lab unless the change is broad or runtime state is ambiguous.
- When adding a device, attach it directly to the intended existing segment when possible. Do not invent an extra transit bridge unless the user explicitly asks for it.
- Preserve existing EVE node IDs. Do not renumber or replace node IDs in an existing lab as a workaround unless the user explicitly asks.
- Before building a brand-new topology, choose a clean node-ID range up front where possible; after creation, fix runtime/status scoping bugs in tooling instead of rewriting IDs.
- Before claiming a topology can be built, verify required images exist locally. If an image is missing, inspect `ishare2` inventory and offer exact candidate image names instead of silently substituting another platform.
