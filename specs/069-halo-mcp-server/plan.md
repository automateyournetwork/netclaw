# Implementation Plan: HaloPSA / HaloITSM MCP Server

**Branch**: `069-halo-mcp-server` | **Date**: 2026-07-24 | **Spec**: [spec.md](spec.md)

## Summary

Add a FastMCP/stdio MCP server (`halo-mcp`) plus skills that expose **18 tools — 17 read-only + 1 gated write** against the Halo (HaloPSA / HaloITSM / HaloCRM) REST API. The single write, `halo_create_change_request`, is **confirm-before-submit**: with `submit=false` (default) it assembles and returns the exact `POST /api/Tickets` array body as a preview and performs no HTTP write; only a follow-up call with `submit=true` (after explicit operator approval) creates the ticket. Auth is OAuth2 **client-credentials** (cloud). All required Coherence Checklist artifacts are updated in the same PR.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: FastMCP (`fastmcp>=2.0.0`), `httpx>=0.27.0`, `python-dotenv>=1.0.0`
**Storage**: N/A (stateless proxy to the Halo REST API; in-memory bearer-token cache + optional in-memory rate-limit window only). The change ticket type an org uses is remembered in **Memory MCP** by the skills, not by this server.
**Testing**: offline component smoke in `quickstart.md` (config fail-fast, resolver, gated-write preview-vs-submit, 18-tool inventory); live end-to-end deferred to a token-holding operator.
**Target Platform**: Windows / macOS / Linux (anywhere openclaw runs)
**Project Type**: MCP server (single Python package under `mcp-servers/halo-mcp/`)
**Performance Goals**: page-based pagination with a `HALO_MAX_PAGES` truncation guard; optional proactive rate limiter (`HALO_RATE_LIMIT`, default off — 429 `Retry-After` backoff always on)
**Constraints**: stdio JSON-RPC only (stdout reserved for the protocol; all logging to stderr); no persistent state; credentials only in env vars; exactly one write path and it is gated
**Scale/Scope**: 18 tools across 6 tool modules, ~1.4k LOC server + client + models + utils + skills + spec

## Constitution Check

| Principle | How this plan satisfies it |
|-----------|----------------------------|
| **I (Safety-first)** | Exactly one write; it defaults to a no-write preview. Discovery + review reads precede any change. |
| **II (Read-Before-Write)** | 17 reads ship alongside 1 write; the change flow *requires* reads first (list types → read schema → read a sample ticket → assemble → preview). |
| **III (Change-Gated)** | The write is confirm-before-submit — `submit=false` makes no HTTP call and returns the exact body for human review; `submit=true` is required to create. Halo's native CAB/approval runs after creation. |
| **V (MCP-Native)** | FastMCP entry point, stdio transport, JSON-RPC lifecycle handled by FastMCP itself. |
| **VIII (Verify After)** | The submit path returns `{"created": true, "ticket": {...}}` echoing the created object so the caller can verify Halo committed. |
| **XI (Artifact Coherence)** | Every artifact slot covered — see "Project Structure" and `checklists/requirements.md`. |
| **XIII (Credential Safety)** | `HALO_CLIENT_SECRET` read from env only; never logged (startup log prints base_url/tenant/scope, not the secret); token held in memory; `.env.example` documents without values. |
| **XV (Backwards Compat)** | No shared schemas changed; the new MCP slot is additive only; existing MCPs/skills untouched. |
| **XVI (SDD)** | spec, plan, tasks, data-model, contracts, research, quickstart, checklists all present under `specs/069-halo-mcp-server/`. |
| **XVII (Milestone Blog)** | Blog draft tracked as a closing task; if the WordPress MCP is unavailable, saved as markdown for manual publish. |

No principle violations to document under Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/069-halo-mcp-server/
├── spec.md              ✓ shipped
├── plan.md              ✓ this file
├── tasks.md             ✓ shipped
├── data-model.md        ✓ shipped
├── research.md          ✓ shipped
├── quickstart.md        ✓ shipped
├── gait-session-log.md  ✓ shipped
├── contracts/
│   └── mcp-tools.md     ✓ shipped
└── checklists/
    └── requirements.md  ✓ shipped
```

### Source Code (repository root)

```text
mcp-servers/halo-mcp/
├── halo_mcp_server.py           # FastMCP entry — 18 @mcp.tool() wrappers + singleton client
├── clients/halo_client.py       # async httpx client: OAuth2 token, get/get_all/post, 401 refresh, 429 backoff
├── tools/
│   ├── _common.py               # _build_params, _single_result/_list_result, error envelopes
│   ├── ticket_types.py          # halo_list_ticket_types, halo_get_ticket_type
│   ├── fields.py                # halo_list_fields, halo_get_field
│   ├── tickets.py               # 4 reads + halo_create_change_request (the gated write)
│   ├── assets.py                # halo_get_asset, halo_list_assets, halo_get_asset_relationships
│   ├── context.py               # halo_list_clients/sites/users/contracts
│   └── knowledge.py             # halo_list_kb_articles, halo_get_kb_article
├── models/responses.py          # curated dataclasses (Ticket, TicketType, FieldInfo, Asset, ...)
├── utils/
│   ├── constants.py             # API_PREFIX, AUTH_TOKEN_PATH, DEFAULT_* (Halo vocabulary notes)
│   ├── resolver.py              # name→id resolution (exact→substring; Ambiguous/NotFound)
│   ├── pagination.py            # extract_list() for page results
│   ├── rate_limiter.py          # SlidingWindowRateLimiter + parse_retry_after
│   └── toon_helper.py           # TOON serialization shim (JSON fallback)
├── requirements.txt
├── .env.example
└── README.md

workspace/skills/
├── halo-change-request/SKILL.md      # discover → confirm → remember → learn → assemble → confirm-before-submit → create
├── halo-asset-context/SKILL.md       # review an asset (Device) with its related tickets + CMDB/CI relationships
└── halo-ticket-context/SKILL.md      # review a ticket's resolution context — detail, actions, linked assets, KB
```

**Structure Decision**: Mirror the cleanest existing REST-MCP layout (`tools/` + `clients/` + `models/` + `utils/` separation, per-tool-domain modules, a singleton client created lazily with fail-fast config validation). The change ticket type's per-org identity is deliberately kept **out** of the server and pushed to the skills + Memory MCP, so the server stays a stateless primitive layer.

## Complexity Tracking

> No constitution violations to justify. The one write is gated by design; the per-org discovery problem is solved with reads + skills + Memory rather than server-side state.
