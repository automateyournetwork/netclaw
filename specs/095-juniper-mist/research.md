# Phase 0 Research — Juniper Mist (R5)

**Date**: 2026-08-05 | **Plan**: [plan.md](plan.md) | **Measurements**: [VERIFICATION.md](VERIFICATION.md)

> Written after `spec.md` in the same session, before merge. Every finding below was measured live
> against Juniper's endpoint with the operator's own credential — nothing is quoted from
> documentation except two header names, which measurement then confirmed.

---

## R1 — Which server, and is adoption the shape?

**Decision**: Juniper's official remote MCP was the only serious candidate. **Adoption is not
available.**

`https://mcp.ai.juniper.net/mcp/mist` — first-party, remote, no install. The 089 (Meraki) precedent
suggested this would be the cleanest possible integration.

It measures **7 tools / 11,783 tokens — 2.36× the 5,000 ceiling.**

**Alternatives considered**: `junos-mcp-server` (already present; covers *devices*, not Mist
assurance — a different question); community Mist servers (not evaluated, since the first-party
option exists and the blocker is manifest size, which a community wrapper would not improve).

---

## R2 — Reaching the server at all: two undocumented-by-default requirements

| Attempt | Result |
|---|---|
| `Authorization: Token <t>` | `no supported Authorization scheme found in request` |
| `Authorization: Bearer <t>`, no region header | `authentication failed: Mist API rejected credentials (HTTP 401)` |
| `Bearer` + `X-Mist-Base-URL: https://api.ac5.mist.com` | **success** |

Two failures that look identical from the client and are not:

- The Mist **REST API** accepts `Authorization: Token`. The **MCP server accepts only `Bearer`.**
- Without `X-Mist-Base-URL` the server defaults to `api.mist.com`, where a valid `ac5` token is
  rejected with a **401 that reads as a bad credential, not a wrong region**.

**Both clouds 401 identically to an unauthenticated request**, so a 401 alone cannot distinguish a
bad token from a wrong region. The region must come from the operator's `manage.<region>.mist.com`
URL, never inferred from a failure.

`X-Mist-Org-ID` is accepted but does **not** populate the per-call `org_id` argument.

---

## R3 — Manifest cost (the gate)

**Decision**: Fails, decisively.

| Tool | Tokens |
|---|---|
| `search_mist_data` | 4,229 |
| `get_mist_insights` | 2,815 |
| `get_mist_stats` | 2,542 |
| `get_mist_config` | 1,879 |
| `find_mist_entity` | 1,776 |
| `get_mist_constants` | 812 |
| `get_mist_self` | 669 |
| **Manifest** | **11,746** |
| `instructions` | 37 |
| **Total** | **11,783 — 2.36×** |

**~1,678 tokens per tool** — the opposite failure mode from every prior rejection. Catalyst Center
(087) failed at 515 tools averaging ~283 each; this fails at *seven*.

---

## R4 — Can a subset be loaded?

**Decision**: **No.** `config/openclaw.json` entries use only `command`, `args`, `env`, `headers`,
`url` across all 101 registered servers. There is no tool-filtering key.

The three cheapest tools would fit (3,257 tokens) but exclude every assurance capability R5 exists
to obtain.

---

## R5 — A methodological finding: chars/4 under-reports

**Decision**: Estimation is unsafe near the ceiling.

The roadmap has estimated manifests at chars÷4 throughout (089's 818 chars → ~204 tokens is exactly
that). Applied here it gives **10,052** against a measured **11,783** — a **17% under-report**.

Dense JSON schemas tokenize worse than prose. Safe for the low-cost adoptions it has been used on;
**any measurement within ~20% of 5,000 must be counted, not estimated.**

---

## R6 — Two defects in the shipped schemas

**6.1 `get_mist_insights` requires a parameter its schema never declares.** The schema lists
`duration, end_time, insight_type, limit, next_cursor, org_id, page, params, site_id, start_time` —
no `query_type`. Yet supplying `query_type` at the top level gets it **silently dropped** and then
reported missing. The working form nests it inside the undeclared generic `params` object.

**A model working from the schema alone cannot construct a valid SLE call** — and SLE is the single
most valuable capability for R5's purpose.

**6.2 `X-Mist-Org-ID` does not populate `org_id`.** Every org-scoped call must repeat it explicitly.

Not all errors are this soft: `stats_type` and `search_type` are strict enums that reject invalid
values loudly, naming the full valid set. **The inconsistency is the hazard.**

---

## R7 — Read-only posture, and a credential finding

All seven tools are read-shaped; the manifest contains no create/update/delete/reboot verb, so no
mutating operation is reachable **through this server** regardless of credential.

But `GET /api/v1/self` returns `role: admin` for the operator's token — full write reach over the
org **through the REST API**. Nothing in the design uses it; an **Observer-role org token** is made
a requirement on the build path, not a preference.

---

## R8 — What the empty org can and cannot establish

Org `NetClaw`: **1 site, 0 devices, 0 inventory, 0 alarms, 0 licences** (`trial_enabled: true`).

Proven: identity, org resolution, constants (**284 device models** — a real, non-trivial payload),
and that every org-scoped query returns a well-formed zero.

**Not proven**: that any assurance payload parses correctly. The one tool exercised against real
data is `get_mist_constants`, a **static catalogue** that touches no org state.

### The trap, stated precisely

`sites_sle` returns **`count: 1`** — a non-zero count, a real site ID, and **no SLE metrics**. Asked
"how is wireless health at this site?", a model receiving that can report the site as healthy.

It is not healthy. It has no APs, no clients, no telemetry. **A site with no data and a site with no
problems are the same shape in this response.**

Same class as R15's box-vs-network distinction and R13's zero-signature Suricata: an absence
rendered as a negative finding. NetClaw's discipline is to reproduce such traps and block them
structurally — which requires an org where the difference is observable.

---

## R9 — Adopt, build, or defer?

**Decision**: Reject adoption (R3/R4); specify the build; **gate it** (R8).

Contrast with 096 (Elastic), decided the same day: there the manifest measured 1,094 tokens and the
one defect had a verified mitigation, so adoption proceeded despite a deprecated upstream. **The
manifest cost is what separates the two outcomes**, not a preference for adopting or building.
