# Operational guardrails

## Single-user rule

Treat this EVE-NG instance as single-user. Do not start a new lab if another lab is already running. If stopping another lab would be required, ask the user first.

## Node-ID rule

Preserve existing node IDs. Do not renumber or replace node IDs in an existing saved lab as a workaround unless the user explicitly asks. For new labs, choose a sensible node-ID range up front when possible; if cross-lab status ambiguity appears, fix runtime/status scoping by lab UUID rather than rewriting node IDs.

## Missing-image rule

Before declaring a requested image unavailable:
1. Check local image inventory.
2. Inspect `ishare2` inventory (use `/usr/sbin/ishare2` if needed).
3. Offer exact candidate image names found.
4. Do not silently substitute another image.

## Link-edit safety

Do not add, move, or remove EVE links while affected nodes are running. Re-read topology after link edits; do not trust the write response alone.
