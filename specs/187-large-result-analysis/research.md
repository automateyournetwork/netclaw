# Research: spec 187

## R1. Where is the 20,000-char cap?
Evidence: only the issue's quoted code (`renderToolSearchControlText`, OpenClaw 2026.10.8
`dist/code-mode-json-*.mjs`). OpenClaw is not installed in this environment and not in this
repository; `grep` of the repo finds no such limit in NetClaw servers (pyATS_MCP, multivendor-cli-mcp,
analysis-mcp return whole results). Conclusion: upstream, unverified by us. Why it exists is not
knowable from NetClaw; do not claim it. Design budget: 15,000 chars inline (cap 20,000 includes a
~300-char wrapper per the issue).

## R2. Approach options
1. Raise/patch the cap: rejected (upstream, issue says not to remove it).
2. Server-side aggregation tools per producer: rejected as primary (every producer x every
   question); one generic declarative surface is smaller and auditable.
3. Retention + handle + declarative query (chosen). Matches issue's "trusted local aggregation or
   bounded access to retained complete results".
4. DuckDB/SQL: rejected; spec 092's own notes show a SQL surface is a filesystem client needing
   engine sandboxing; declarative triples need none and add no dependency.

## R3. Query language
`(field, op, literal)` list (AND), ops eq/ne/startswith/endswith/contains/in/gt/ge/lt/le/exists/
not_exists; `group_by`; time window with explicit no-timestamp gap. Dict collections expose key as
`_key` (Genie `interface` maps are keyed by interface name). No regex (ReDoS) and no expressions.

## R4. Completeness semantics
`complete` is false for any of: retention truncated, page, scan budget, stream drops/gaps,
unplaceable timestamps. Producer field-filtering is a note, not a truncation, so the three
cases in the issue (complete / field filtered / record list truncated) are distinguishable.

## R5. Producer integration reality
`pyATS_MCP` is not tracked (`.gitignore` `mcp-servers/*`); installer clones a pinned upstream
(`scripts/setup-pyats-runtime.py`, `migrate-pyats-http.py`). Editing it here would be an
uncommittable local patch, so integration targets tracked `multivendor-cli-mcp`.

## R6. Installer coupling
`scripts/lib/catalog.sh` is generated from `config/components/catalog.json` by
`scripts/build-catalog.py`; the component was added to the JSON and regenerated.
