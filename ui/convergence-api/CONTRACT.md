# convergence-api response contract

The shapes `modules/convergence/HomeView.js` depends on. Enforced by
`tests/contract/test_convergence_api.py`.

## Why this file exists

The client used to guess: `d.edge || d.firewall`, `d.devices || d || d.items`,
`ap.status || (ap.up === 1 ? 'online' : ...)`. That tolerance is why nobody
noticed the contract was undocumented — the view kept rendering *something* no
matter what came back, so a shape change showed up as a quietly empty panel
rather than an error.

Anything listed **required** here is something the view breaks or silently blanks
without. Optional fields may be absent; the view must degrade, not throw.

## Conventions

- Every site-scoped endpoint takes `?site=<id>` and echoes `site` back.
- `status` strings the view understands: `online`, `up`, `offline`, `down`, plus
  `healthy` / `degraded` / `unhealthy` for threshold-derived values. Anything else
  renders as-is and is styled neutrally.
- Absent data is `null`, not `0`. `0` means measured zero — the view renders `—`
  for `null` and `0` for zero, and conflating them misreports health.
- Degraded features return **200 with an explanation**, never a bare empty body.
  See `unavailable` below.

## `GET /api/health?site=`

| Field | Req | Notes |
|---|---|---|
| `site` | yes | echo |
| `healthScore.value` | yes | number 0–100 |
| `healthScore.status` | yes | threshold string |
| `wanLatency.value` / `.unit` / `.status` | no | `null` value when unmeasured |
| `wanLoss`, `speedtest`, `alertCount`, `devices` | no | same shape family |

## `GET /api/devices?site=`

| Field | Req | Notes |
|---|---|---|
| `site` | yes | echo |
| `switches[]` | yes | may be empty; **must be an array** |
| `switches[].name` | yes | matched against the pyATS testbed for the Console action |
| `switches[].model` | yes | display only; never a hardcoded per-device guess |
| `switches[].status` | yes | |
| `switches[].portsUp` / `.portsTotal` | no | `null` when the exporter has no IF-MIB data |
| `edge[]` / `firewall[]` | no | the view accepts either key; `edge` preferred |
| `accessPoints[]`, `wanProbes[]` | no | arrays when present |
| `summary` | no | counters only; the view never derives truth from it |
| `mgmt` | no | management URLs for name links |

Switch discovery is config-driven (`switches.match` / `switches.models` per site
in `SITES_CONFIG`), defaulting to every device reporting `interface_status`.

## `GET /api/sites`

| Field | Req | Notes |
|---|---|---|
| `sites[]` | yes | already scope-filtered per caller |
| `sites[].id` | yes | used as `?site=` |
| `sites[].name` | no | falls back to `id` |
| `sites[].healthy` | no | `true`/`false`/`null`; `false` marks the option |

The client picks the first entry when its stored site is not on offer, so **order
is meaningful**: the most sensible default belongs first.

## `GET /api/events?site=` and `GET /api/events/escalated?site=`

| Field | Req | Notes |
|---|---|---|
| `site` | yes | echo |
| `events[]` | yes | may be empty; **must be an array** |
| `unavailable` | no | `true` when the store is unreachable |
| `reason` | no | required *when* `unavailable` is true |

`unavailable` is the important one. Postgres is optional, and an empty diary and
an unreachable diary look identical without it — the view says "unavailable" for
the second case rather than implying nothing has happened.

Writes (`POST /api/events`, `PATCH /api/events/:id`,
`POST /api/events/:id/reinvestigate`) answer **503** with `error` and `hint` when
the store is unavailable, never 500.

## `GET /healthz`

| Field | Req | Notes |
|---|---|---|
| `status` | yes | `ok` whenever the API serves, **even with Postgres down** |
| `features.diary` | yes | `available` \| `unavailable` |
| `database.enabled` / `.available` | yes | |
| `database.reason` | no | populated when unavailable |

`status` deliberately stays `ok` when an optional dependency is missing, so the
container is not restarted over a feature the deployment may not use.

## Changing this contract

Update this file and the test in the same commit. Adding an optional field is
safe. Removing or renaming a **required** field is a breaking change for the
HUD module and needs a matching change there.
