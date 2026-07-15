# Contract: iN2N Daemon HTTP API & n2n-mcp Tool Delta

New surfaces added for iN2N. All additive; existing `/n2n/*` eN2N routes and `n2n-mcp` tools are unchanged.

## Daemon HTTP routes (`bgp-daemon-v2.py`)

| Method & path | Purpose | Body / returns |
|---------------|---------|----------------|
| `GET /n2n/risk` | This claw's risk identity | `{ role, risk_name, description, enabled_stacks, self_member_id? }` |
| `POST /n2n/risk` | Set/update role & risk config (install/reconfig) | `{ role, risk_name?, description?, enabled_stacks?, border_endpoint? }` → enforces single-Border (FR-003) |
| `GET /n2n/members` | Border: list members + scope + health + state | `[ { member_id, display_name, profile, scope, state, health, transport_binding } ]` |
| `POST /n2n/members/remove` | Border: remove a member (unpin) | `{ member_id }` → confirm-gated |
| `GET /n2n/members/health` | Border: per-member health incl. quarantine/alerts | `[ { member_id, state, last_seen, auth_failures, in_flight } ]` |
| `POST /n2n/enroll/token` | Border: issue single-use enrollment token | `{ label?, ttl_seconds? }` → `{ token, token_hash, expires_at }` |
| `POST /n2n/route` | Border: route an operator request to a member | `{ request_text, target_hint? }` → `{ task_id, member_id }` or `{ error: ERR_NO_CAPABLE_MEMBER }` |

(iN2N `in2n/enroll` and `in2n/hello` are **channel** JSON-RPC methods over the internal transport, not HTTP — see the transport/enrollment contracts.)

## `n2n-mcp` tools (`server.py`) — additions

| Tool | Role | Purpose |
|------|------|---------|
| `n2n_risk_status()` | any | show this claw's role, risk, enabled stacks; on a Border, member count/health summary |
| `n2n_member_list()` | Border | list members with scope + health + state |
| `n2n_member_add(profile \| custom_skills, name)` | Border | provision a member from a catalog-derived profile or a custom skill set (issues a token, prints join instructions) |
| `n2n_member_remove(member_id)` | Border | remove + unpin (confirm with operator first) |
| `n2n_enroll_token(label?, ttl_seconds?)` | Border | issue a single-use enrollment token for a member to join |
| `n2n_route(request_text, target_hint?)` | Border | ask the Border to route a task-shaped request to the right member; returns a task_id for long work |
| `n2n_member_health(member_id?)` | Border | per-member channel state, last-seen, in-flight tasks, quarantine alerts |

Reused unchanged from 053 for the internal task lifecycle: `n2n_task_status`, `n2n_task_result`, `n2n_task_cancel` (they key on `task_id`, agnostic to en2n/in2n).

Standalone claws expose these tools as no-ops/`role=standalone` responses (SC-008): `n2n_risk_status` reports standalone; member/route tools report "this claw is standalone (a risk of one)".

## Environment (`.env.example` additions)

| Var | Default | Meaning |
|-----|---------|---------|
| `N2N_ROLE` | `standalone` | `standalone` \| `border` \| `member` |
| `N2N_RISK_NAME` | (unset) | the risk's name (border/member) |
| `N2N_ENABLED_STACKS` | `en2n` | border: `en2n` \| `in2n` \| `both` |
| `N2N_IN2N_PORT` | (reuse mesh port) | optional dedicated iN2N listener on the Border |
| `N2N_BORDER_ENDPOINT` | (unset) | member: host:port to dial the Border |
| `N2N_QUARANTINE_THRESHOLD` | `5` | consecutive auth/health failures before auto-quarantine |

## Operator TUI / CLI surface (`scripts/netclaw` + `scripts/lib/tui.sh`)

Follows Nick's established TUI format (PRs #96 installer TUI, #115 `netclaw` command tree, #117 peering lifecycle) — reuse the primitives, do not invent a new prompt style.

### Installer prompts (`scripts/lib/install-steps.sh → component_install_n2n`)

Built from `scripts/lib/tui.sh` primitives, matching the component picker's look/feel and off-TTY degradation:

| Step | Primitive | Options / behavior |
|------|-----------|--------------------|
| Standalone vs risk | `tui_menu` | `Standalone NetClaw` · `Part of a risk` |
| Risk name / description | `read` (as installer already does for text) | free text; skipped when standalone |
| Role | `tui_menu` | `Border Claw` · `Member Claw` |
| Border stacks | `tui_menu` | `eN2N only` · `iN2N only` · `Both` (Border only) |
| Seed / add members | `tui_menu` per profile + `tui_checklist` for Custom | profiles from `scripts/in2n-profiles.py`; Custom uses the category-headed `CL_IDS/CL_LABELS/CL_ON` checklist |
| Confirm | `tui_yesno` | matches installer confirmation style |

### `netclaw` command — Risk sub-tree (mirrors `peering_menu` / `netclaw peering`)

Interactive (`main_menu` gains a **Risk (iN2N members)** entry → `risk_menu`, dispatched by `TUI_CHOICE` exactly like `peering_menu`):

```
Risk — <risk-name> (<role>)
  Overview (role · stacks · member count/health)
  Members (list scope · state · in-flight)
  Add member (profile | custom)
  Remove member
  Enrollment token (issue single-use)
  ← Back
```

Non-interactive (mirrors `netclaw peering [status|bgp|n2n|ngrok]`), reading the daemon HTTP API via the existing `api_get`/`api_post` helpers:

| Command | Maps to |
|---------|---------|
| `netclaw risk status` | `GET /n2n/risk` (+ member summary on a Border) |
| `netclaw risk members` | `GET /n2n/members` |
| `netclaw risk add <profile\|custom> <name>` | provision + `POST /n2n/enroll/token` |
| `netclaw risk remove <member_id>` | `POST /n2n/members/remove` (confirm-gated) |
| `netclaw risk token [label]` | `POST /n2n/enroll/token` |
| `netclaw risk route "<request>"` | `POST /n2n/route` |

Standalone claws: `netclaw risk status` reports `standalone (a risk of one)`; the sub-menu entry is hidden or shows the standalone note (SC-008).

## HUD (`ui/netclaw-visual/`)

- `server.js` `/api/n2n` folds in `role`, and for a Border its `members` (id, scope badge, state, in-flight tasks).
- `src/main.js` renders a **risk view**: the Border node at the hub with member spokes; each spoke shows scope badge, health (active/unreachable/quarantined), and live in-flight task progress. A standalone claw renders as today (single node).

## Backwards-compatibility assertions

- With `N2N_ROLE=standalone` (default), no iN2N route/listener/registry is active; the daemon behaves exactly as pre-054 (SC-008).
- eN2N routes/tools and the mesh `n2n/hello` path are byte-for-byte unchanged (SC-009).
