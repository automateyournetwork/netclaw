# Contract — The counting invariant

**Status**: verified live, 2026-08-05 | **Spec**: [../spec.md](../spec.md)

This is the load-bearing contract of feature 096. Everything else is plumbing.

---

## The invariant

> **A total may be reported to a human only if it came from `esql`, or from a `search` carrying
> `"track_total_hits": true` in its `query_body`. Any other total is unbounded-wrong.**

---

## Why

Elasticsearch stops counting matches at 10,000 and marks the result:

```json
"hits": { "total": { "value": 10000, "relation": "gte" } }
```

`relation: "gte"` means *at least 10,000*. The MCP server renders this as:

```
Total results: 10000, showing 10.
```

**The qualifier is gone.** A capped floor and an exact count produce byte-identical output. No
inspection of the response can tell them apart.

## Verified behaviour

Against an index containing exactly **10,075** matching documents:

| Call | Output | Correct |
|---|---|---|
| `_count` API (ground truth, outside MCP) | `10075` | — |
| `search` `{"query":{"term":{"severity":"error"}}}` | `Total results: 10000, showing 10.` | ✗ |
| `search` `{… , "size": 5}` | `Total results: 10000, showing 5.` | ✗ |
| `search` `{… , "track_total_hits": true}` | `Total results: 10075, showing 1.` | ✓ |
| `esql` `FROM … \| WHERE … \| STATS c = COUNT(*)` | `[{"c":10075}]` | ✓ |

Changing `size` alters only the `showing` figure. **It does not fix the total** — a plausible-looking
remedy that does not work, and therefore worth stating explicitly.

## Severity

The error is **unbounded**. The cap is fixed at 10,000 regardless of index size:

| True matches | Reported by unguarded `search` | Error |
|---|---|---|
| 10,075 | 10,000 | 0.7% |
| 100,000 | 10,000 | 10× |
| 1,000,000 | 10,000 | 100× |

An answer that is wrong by two orders of magnitude, with nothing in the response to signal it, is
indistinguishable from a correct one at the point of use.

## Obligations

**On the skill** (`workspace/skills/elasticsearch-logs/SKILL.md`):

1. Any question of the form *how many / how often / which is most / top N* MUST use `esql`, or
   `search` with `track_total_hits: true`.
2. Unguarded `search` is for retrieving **example documents only** — never for counting.
3. A total obtained without a guard MUST NOT be stated as a number.

**On the installer** (`component_install_elastic`): state the rule at install time, because an
operator calling the tool directly bypasses the skill entirely.

**On the catalog entry**: state the rule in the description, because that is what an operator reads
when choosing the component.

## Related failures elsewhere in this repo

Same class, previously reproduced and blocked:

- **R13 / spec 091** — Zeek discards invalid-checksum packets by default, losing `http.log` entirely
  and miscounting `conn.log`.
- **R15 / spec 094** — a BMC timeout establishes nothing about the host, and must never be emitted
  as a downed host.
- **R5 / spec 095** — `sites_sle` on an empty Mist org returns `count: 1` with no metrics, so *no
  telemetry* and *no problems* share a shape.

In each case the wrong reading is the natural one. That is the signature of this defect class.
