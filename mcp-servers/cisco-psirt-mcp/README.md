# Cisco PSIRT Advisory MCP Server

Answers one question: **is the software this device is running affected by a published
Cisco security advisory?**

Spec: [078-cisco-psirt-vulnerability](../../specs/078-cisco-psirt-vulnerability/) ·
Roadmap item **R2** · Server id `cisco-psirt` · Transport **stdio** · **Read-only**

## The distinction this server exists to preserve

An empty advisory list is **not** a clean bill of health. Five outcomes keep the two
apart:

| `outcome` | Meaning |
|---|---|
| `advisories_found` | Cisco has published advisories for this version |
| `none_published` | Cisco has published **nothing** for this version — **not** "the device is secure" |
| `normalisation_failed` | The version could not be parsed. **Nothing was checked.** |
| `unsupported_ostype` | Not a PSIRT OS family — includes `iosxr` and every non-Cisco platform |
| `api_error` | Auth failure, rate limit, or a version Cisco has no record of |

All five are **successful tool calls carrying a typed outcome**, never protocol errors,
so the agent can read *why* and act rather than seeing an opaque failure.

`normalisation_failed` and `api_error` both mean the question went unasked. Collapsing
either into an empty list would tell an operator a device is safe when nothing was
checked — which is why the rule is enforced inside `normalise.py`, not in the tool layer.

## Tools

| Tool | Purpose |
|---|---|
| `check_version` | Advisories for one `(ostype, version)` |
| `check_versions` | A fleet, de-duplicated by version first |
| `check_cve` | Cisco advisories covering a CVE id |
| `check_advisory` | One advisory by id |
| `list_recent` | Advisories by severity over a date range |
| `psirt_status` | Auth state, rate budget, cache stats, supported families |

Prefer `check_versions` over looping `check_version`: it de-duplicates, so 60 devices on
12 distinct versions cost 12 calls rather than 60.

## It never contacts a device

There is no transport here and no device credential. The caller supplies the version,
collected by `pyATS` (Cisco) or `multivendor-cli` (everything else). The offline test
suite asserts that no device-transport module is imported anywhere in this directory, so
the property cannot erode quietly.

## Version formats differ per family — and contradict each other

Every row below is a live 200 measured on 2026-07-31:

| OSType | Accepted | Rejected | Advisories |
|---|---|---|---|
| `iosxe` | `17.3.1`, `17.03.01`, `17.3.1a` | `17.3(1)` | 122 |
| `ios` | `15.2(4)E`, `15.2(4)E10` | `15.2.4E` | 74 / 30 |
| `nxos` | `9.3(5)` | `9.3.5` | 33 |
| `asa` | `9.16.1` | `9.16(1)` | 65 |
| `ftd` | `7.0.1` | `7.2(0)` | 90 |
| `fmc` | `7.0.1` | — | 34 |
| `aci` | `15.2(3e)`, `16.0(3e)` | `5.2(3e)`, `5.2.3` | 10 / 8 |

Note the contradiction: `iosxe` rejects the parenthesised form that `ios` **requires**.
The normaliser therefore runs in both directions, chosen per family, and `aci` needs the
letter suffix *inside* the parentheses where `ios` needs it outside. A single global rule
would silently break `ios` and `nxos` on every call.

**ACI wants the switch image version** (`15.2(3e)`), not the APIC controller version —
`5.2(3e)` is rejected. An operator reading the number off an APIC will hand over
something this API refuses.

A wrong format returns HTTP 406 `"<OS> version not found"`, surfaced as `api_error` — never
as an empty list. That 406 also covers a correctly formatted version Cisco has no record
of, so it means "no record", not necessarily "you formatted it wrongly". Either way the
question went unanswered.

## What is NOT available

Measured, not inferred from Cisco's documentation, which describes all of these as
available. Stated here so nobody re-litigates them:

| Capability | Result | Consequence |
|---|---|---|
| **IOS-XR** (`iosxr`) | **404** on 7.5.2, 6.6.3, 24.1.1 against an `iosxe` 200 control | Not an OSType. Refused, never attempted. Use `check_cve` for IOS-XR devices. |
| **Bug / EoX / Case / Serial-to-Info** | **403** under the API Console grant | Out of scope (FR-016) |
| **CX Cloud** | **504** on all seven paths tried | Out of scope; needs a separate tenant subscription (FR-017) |

IOS-XR is worth flagging to users, because NetClaw *can* reach IOS-XR through pyATS, so
per-version checking is reasonably expected to work.

## Rate limits

**5 calls/second and 30 calls/minute**, shared across every caller of the credential.
30/minute is the binding constraint. Enforcement order is contractual:

1. **De-duplicate** by `(ostype, normalised version)` — the largest win, a dict lookup.
2. **Serve from the 6-hour disk cache**.
3. **Pace** what remains.
4. **Back off** on 429, then report rather than hang.

De-duplication is first because pacing an un-de-duplicated sweep just spreads the same
excess over more minutes.

## Environment

| Variable | Purpose | Required |
|---|---|---|
| `CISCO_CLIENT_ID` | OAuth2 client id | **yes** |
| `CISCO_CLIENT_SECRET` | OAuth2 client secret | **yes** |
| `CISCO_PSIRT_CACHE_DIR` | default `~/.openclaw/cisco-psirt` | no |
| `CISCO_PSIRT_CACHE_TTL_S` | default `21600` (6h) | no |

Register a **Service** application with the **Client Credentials** grant at
[apiconsole.cisco.com](https://apiconsole.cisco.com) and select *Cisco PSIRT openVuln API*.

The OAuth token is held **in memory only** and refreshed proactively at 60 seconds
remaining — a fleet sweep can outlive the 3600s lifetime, and discovering expiry via a
mid-sweep 401 turns a predictable event into a partial failure. Advisories are cached on
disk; the token never is. No credential value appears in any result, log line or error
message: errors name the environment variable, never its contents.

## Install

```bash
# Via the modular installer (recommended)
./scripts/install.sh          # select the "cisco-psirt" component, or the
                              # security or cisco profile

# Manually
python3 -m pip install -r mcp-servers/cisco-psirt-mcp/requirements.txt
```

Pins are **bounded** (`mcp>=1.2.0,<2`, `httpx>=0.27.0,<1`). The upper bound on `mcp` is
load-bearing: `mcp` 2.0.0 removed `mcp.server.fastmcp`, which this server imports.

## Tests

```bash
./tests/cisco-psirt/run-tests.sh      # offline, no network, no rate budget consumed
./tests/cisco-psirt/live-api.sh       # opt-in; spends real API calls
```

The default suite substitutes a counting stub for the API client, so running the tests
never competes with using the product. 100 offline checks.
