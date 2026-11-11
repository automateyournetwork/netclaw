# Research: spec 190

## R1 Where the class lives
Decision: on the grant (`access_class`), as a ceiling. Alternative: separate grant rows per verb (read grant, write grant). Rejected: doubles the grant surface, and "no write grant" would then mean today's full behavior for legacy rows. Alternative: tool-name convention. Rejected: unreliable.

## R2 Vocabulary
Grant: `read` | `read_write`. Target: `read` | `write` | `unclassified`. Decision table (normative):

| Grant class | Target read | Target write | Target unclassified |
|---|---|---|---|
| read | allow | refuse | refuse |
| read_write | allow | allow | allow (today's behavior) |

Refuse = NOT_ALLOWLISTED. `knowledge` and `knowledge_replica` targets are always read. No `admin` class: nothing in the current model distinguishes it.

## R3 Classification sources
Order: operator override, imported annotation, unclassified. Annotation mapping: `readOnlyHint: true` read; `false` write; absent unclassified. Intake is an explicit operator import of a `tools/list`-shaped payload. Not fetched live and never taken from a peer. Live ingestion at execution is deferred (needs a tools/list round trip before authorization; not verified here).

## R4 Skills
Only operator override can make a skill read. No SKILL.md self-declaration. Request text is never inspected. The federation layer cannot verify a read-classified skill does not write inside its agent turn; that remains with the gateway scope approvals and sandbox.

## R5 Ordering and wire
Check sits after grant lookup and before rate, budget, approval. Refusal uses NOT_ALLOWLISTED with the same reason text as an ungranted target; audit decision `access_class_denied` records the truth locally. No new error code (avoids an oracle and avoids a wire change).

## R6 Card
Advisory optional fields: per `mcp_servers[]` entry `tool_access: {tool: read|write|unclassified}`, per `skills[]` entry `access: read|write|unclassified`. Receivers MUST NOT authorize from them. Old peers ignore unknown members (the card already carries extension members such as `invocable_tools`, `qualification`). The card secret-scan still runs.

## R7 Duplicate grants
A new grant with a different class than an active grant for the same (peer, type, name) revokes the old one. Same class keeps today's insertion behavior.

## R8 Limits (spec 189)
Reads and writes share counters. Class refusals are before rate and budget so they are never debited and never trigger warn/teardown. Separate per-class budgets deferred.

## R9 iN2N
`authorize()` runs for `already_trusted` callers, so the same check applies. Member `scope` (capability list used for routing) is unchanged. No Border-to-member forwarding of the class (limitation).

## R10 Not verified
Upstream MCP specification wording for annotations was not re-read for this spec; only the `readOnlyHint` field name is relied on, treated as an operator-imported hint, never as proof.
