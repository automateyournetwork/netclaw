# catc-mcp — Catalyst Center, read-only

**Spec 087.** All **514 read-only** Catalyst Center operations via **10 tools**.
Manifest **1,821 / 5,000 tokens**.

## The problem this solves

Cisco released an official Catalyst Center MCP server. Measured by running its own loader:

| | Tools | Manifest |
|---|---|---|
| Upstream default bundle | **515** | **64,420 tokens — 12.9× the ceiling** |
| Curating to ~15 tools | 15 | ~4,200 — but covers ~3% of the API |
| **This: 8 dispatchers + find + describe** | **10** | **1,821 — all 514 reachable** |

Candidates previously rejected here were 53, 111, 237, 313 tools. 515 is the largest surface evaluated.
So the engineering is not adoption — it is **making the whole surface reachable within a budget**.

## Adopt the catalogue, not the runtime

NetClaw uses Cisco's **generated tool definitions** (Apache-2.0, `release/2.3.7.11`) — each carrying `uri`,
`method` and `parameterLocation` — with its own thin client. See [NOTICE.md](./NOTICE.md).

That single decision avoids three upstream properties:

1. **`fastmcp>=2.0.0` unbounded** → resolves 3.x, colliding with five NetClaw servers pinning `<3`. The
   third occurrence of the hazard that blocked spec 083.
2. **Streamable HTTP on port 7001** — every other NetClaw MCP server is stdio.
3. **A container**, which would otherwise be needed purely to isolate (1).

Dependencies here are `mcp` and `httpx`. Nothing else.

## The 10 tools

`catc_find(query, group, limit)` — **start here.** Searches all 514 operations locally; does not contact the
appliance. Operation names are generated from Cisco's API spec and are **not guessable**.

`catc_describe_operation(name)` — full parameter schema on demand.

`catc_devices` · `catc_sites` · `catc_wireless` · `catc_health` · `catc_compliance` · `catc_software` ·
`catc_events` · `catc_other` — each takes `(operation, params)`.

The 11,836-token operation index deliberately lives *behind* `catc_find` rather than in the manifest. That is
what keeps this affordable.

## Read-only, twice over

Only **GET** operations are catalogued. The single mutating operation in the upstream bundle
(`api_complianceRemediation`, POST) is **excluded from the catalogue entirely** — a tool absent from the
catalogue cannot be dispatched.

The upstream README is explicit that its catalogue *"does not enforce read-only access"*. NetClaw's two
controls are **curation** (structural — nothing else is reachable) and **the account's own RBAC**. Use a
dedicated least-privilege account.

## The distinction, and why every response is stamped

**An empty inventory is not an empty network.** Zero devices means *this controller manages none* —
discovery may not have run, RBAC may scope the account, a filter may have excluded everything, or you may be
querying the wrong appliance.

That last one is not hypothetical. The DevNet always-on sandboxes **share credentials and are not
equivalent**:

```
sandboxdnac.cisco.com   -> 4 devices, 25 sites
sandboxdnac2.cisco.com  -> 0 devices,  1 site    (authenticates perfectly)
```

An inventory answer from the second is indistinguishable from a real empty estate. So `_envelope()` is a
chokepoint: **every** response carries `appliance` and `observed_at`, and an empty result **or a zero count**
carries an explicit caveat naming the causes.

The zero-count case was found by live testing — a bare `0` from a count endpoint reads even more like data
than an empty list does, and the empty-list branch never fired for it.

**And "Catalyst Center says unreachable" is not "the device is down."** It is one controller's last poll.

## Typed outcomes

`ok` · `empty` · `unreachable` · `auth_failed` · `forbidden` · `not_configured` · `refused` · `error`

`unreachable`, `auth_failed` and `empty` are three different facts. Keeping them apart needed a real fix:
`httpx.HTTPStatusError` subclasses `httpx.HTTPError`, so a 401 on the token endpoint was initially reported
as `unreachable`. A distinct `AuthRejected` exception fixes it — caught by the live test suite, not by
review.

## Tests

```bash
bash tests/catc/run-tests.sh                                     # static
CATC_TEST_HOST=https://sandboxdnac.cisco.com \
CATC_TEST_EMPTY_HOST=https://sandboxdnac2.cisco.com \
CATC_TEST_USER=\ CATC_TEST_PASS=\ \
  bash tests/catc/run-tests.sh                                   # + live
```

The DevNet sandbox credentials are published on developer.cisco.com; they are deliberately not
committed here.

43 assertions. The live suite proves the central claim by querying **both** sandboxes — verifying against
only the populated one would prove nothing about the distinction.

## Regenerating for another Catalyst Center version

Upstream is version-coupled: the branch name is the supported appliance version. See NOTICE.md. Re-derive
`catalog/*.json`, keep GET only, and update the pinned count in `tests/catc/test_catalogue.py` deliberately.

## Boundaries

`pyats`/`multivendor-cli` read **the device** — when they disagree with the controller, the device is right.
`netbox`/`nautobot` hold **intended** state; this reports **discovered** state.
`devnet-catalyst-search` searches **documentation**; this queries **an appliance**.
