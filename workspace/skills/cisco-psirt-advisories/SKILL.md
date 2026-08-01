---
name: cisco-psirt-advisories
description: "Check whether a running Cisco software version is affected by a published PSIRT security advisory - by OS version, CVE, or advisory ID, with severity and CVSS. Covers IOS, IOS-XE, NX-OS, ASA, FTD, FMC and ACI. Use when asked if a device or fleet is vulnerable, when triaging a Cisco CVE, or when auditing software versions against Cisco advisories."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["CISCO_PSIRT_MCP_SCRIPT", "MCP_CALL", "CISCO_CLIENT_ID", "CISCO_CLIENT_SECRET"] } } }
---

# Cisco PSIRT Advisory Checks

Answers one question well: **is the software this device is running affected by a Cisco
security advisory?**

## Read this first — an empty result is not a clean bill of health

Every tool returns one of five `outcome` values. Two of them look similar in the data
and mean completely different things:

| `outcome` | What it means |
|---|---|
| `advisories_found` | Cisco has published advisories for this version |
| `none_published` | Cisco has published **nothing** for this version — **NOT "the device is secure"** |
| `normalisation_failed` | The version could not be parsed. **Nothing was checked.** |
| `unsupported_ostype` | Not a PSIRT OS family (includes `iosxr` and every non-Cisco platform) |
| `api_error` | Auth failure, rate limit, or a version Cisco has no record of |

**Never report "no advisories" as "not vulnerable".** `none_published` means Cisco has
published nothing matching that exact version string. It says nothing about
unpatched-but-unpublished issues, configuration weaknesses, or anything outside Cisco's
PSIRT process.

**Never treat `normalisation_failed` or `api_error` as good news.** Both mean the question
went unasked. In a fleet sweep, check the `outcome_summary` counts before telling anyone
the fleet is clean — devices in those two buckets were never checked at all.

## The two-step chain

This server **never contacts a device**. It has no transport, no credentials for your
network, and no way to read a version. You supply the version:

**Step 1 — read the version off the device.**

```bash
# Cisco platforms: pyATS
python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" run_show_command \
  '{"device_name":"cat9k-1","command":"show version"}'

# Anything else, or when pyATS has no parser: the multivendor CLI driver
python3 $MCP_CALL "python3 -u $MULTIVENDOR_MCP_SCRIPT" device_run_command \
  '{"device":"rtr-1","command":"show version"}'
```

**Step 2 — pass it here.** Full `show version` output is fine; the banner is parsed.

```bash
python3 $MCP_CALL "python3 -u $CISCO_PSIRT_MCP_SCRIPT" check_version \
  '{"ostype":"iosxe","version":"17.3.1"}'
```

Do not skip step 1 and guess a version. The server refuses to infer one — a guessed
version returns advisories for software the device is not running, which is worse than
no answer.

## Available Tools

### 1. `check_version` — is this version affected?

```bash
python3 $MCP_CALL "python3 -u $CISCO_PSIRT_MCP_SCRIPT" check_version \
  '{"ostype":"iosxe","version":"17.3.1"}'
```

- `ostype` (required): `ios` | `iosxe` | `nxos` | `asa` | `fmc` | `ftd` | `aci`
- `version` (required): bare version or full `show version` output
- `refresh` (optional, default `false`): bypass the 6-hour cache

Verified: `iosxe` + `17.3.1` returns **122 advisories**.

### 2. `check_versions` — a fleet in one call

```bash
python3 $MCP_CALL "python3 -u $CISCO_PSIRT_MCP_SCRIPT" check_versions \
  '{"devices":[{"name":"cat9k-1","ostype":"iosxe","version":"17.3.1"},
               {"name":"n9k-1","ostype":"nxos","version":"9.3(5)"}]}'
```

**Prefer this over looping `check_version`.** It de-duplicates by version first, so 60
devices running 12 distinct versions cost 12 API calls rather than 60 — the difference
between one-third of the per-minute budget and twice it. One device failing never aborts
the others.

### 3. `check_cve` — which Cisco advisories cover this CVE?

```bash
python3 $MCP_CALL "python3 -u $CISCO_PSIRT_MCP_SCRIPT" check_cve '{"cve":"CVE-2024-20353"}'
```

### 4. `check_advisory` — one advisory by id

```bash
python3 $MCP_CALL "python3 -u $CISCO_PSIRT_MCP_SCRIPT" check_advisory \
  '{"advisory_id":"cisco-sa-bootp-WuBhNBxA"}'
```

### 5. `list_recent` — what has Cisco published lately?

```bash
python3 $MCP_CALL "python3 -u $CISCO_PSIRT_MCP_SCRIPT" list_recent \
  '{"severity":"critical","start_date":"2026-01-01","end_date":"2026-07-31"}'
```

Verified: `critical` across 2026 to date returns **15 advisories**.

### 6. `psirt_status` — check the budget before a sweep

```bash
python3 $MCP_CALL "python3 -u $CISCO_PSIRT_MCP_SCRIPT" psirt_status '{}'
```

Reports auth state, remaining rate budget, cache statistics, and which OS families are
supported. Contains no credential values. Worth calling before a large sweep.

## Version formats differ per family — and they contradict each other

This is the most common source of a wrong answer. The server normalises for you, but you
must collect the **right number** in the first place.

| OSType | Format Cisco expects | Example |
|---|---|---|
| `iosxe` | dotted | `17.3.1`, `17.03.01`, `17.3.1a` |
| `ios` | parenthesised, letter outside | `15.2(4)E`, `15.2(4)E10` |
| `nxos` | parenthesised | `9.3(5)` |
| `asa` | dotted | `9.16.1` |
| `ftd` / `fmc` | dotted | `7.0.1` |
| `aci` | parenthesised, letter **inside** | `15.2(3e)`, `16.0(3e)` |

Note the contradiction: `iosxe` **rejects** `17.3(1)` while `ios` **rejects** `15.2.4E`.
The same-looking transformation runs in opposite directions depending on family. The
server handles the conversion; pass whatever the device reported.

**ACI is the trap.** It wants the **switch image version** (`15.2(3e)`), not the APIC
controller version — `5.2(3e)` is rejected outright. Collect it from a switch, not the
APIC.

## IOS-XR is not supported, and this will surprise you

`iosxr` is **not an OSType on this API**. Every version tried (7.5.2, 6.6.3, 24.1.1)
returns HTTP 404, against an `iosxe` 200 control in the same session.

This is worth flagging to the user rather than working around silently, because NetClaw
*can* reach IOS-XR devices through pyATS — so an operator will reasonably expect the
version check to work. For IOS-XR, fall back to `check_cve` or advisory lookup by
product id, and say plainly that per-version checking is unavailable for that platform.

## Where this ends and `nvd-cve` begins

Both answer vulnerability questions; they are not interchangeable, and neither is a
substitute for the other.

| Question | Use |
|---|---|
| "Is this Cisco version affected by a Cisco advisory?" | **this skill** |
| "What is CVE-2024-20353, what is its CVSS, what is affected?" | `nvd-cve` |
| "Has Cisco issued an advisory for this CVE?" | **this skill** (`check_cve`) |
| "Does any vendor have a known CVE matching this software?" | `nvd-cve` |

**Either can legitimately be empty while the other is not.** Cisco may publish an
advisory before an NVD entry exists; NVD may hold a CVE for which Cisco has issued no
advisory. When a security question matters, check both and say which one answered.

## Rate limits are shared and tight

5 calls/second and **30 calls/minute**, shared across every caller of the credential.
30/minute is the real constraint. The server handles this automatically — de-duplicating
by version, serving from a 6-hour cache, pacing, and backing off on 429 — but two habits
defeat it:

- **Looping `check_version` per device** instead of using `check_versions`.
- **Passing `refresh: true` routinely.** It disables the cache. Use it during an incident
  when cache age is itself the question, not as a default.

## What this API does not provide

Measured, not inferred from documentation — do not spend time re-testing these:

- **Bug, EoX, Case and Serial-to-Info APIs** return **403** under the API Console grant.
- **CX Cloud** returns **504** on all seven paths tried. It needs a separate tenant
  subscription.
- **IOS-XR** returns **404**, as above.

## Reporting results to a user

Lead with the count and the worst severity, not the whole list. Then, if the answer was
`none_published`, say what that does and does not mean — the distinction is the point of
this skill, and it is the part a reader will otherwise get wrong.

Good: *"cat9k-1 on IOS-XE 17.3.1 has 122 published advisories, 4 of them Critical
(highest CVSS 9.8). Recommend reviewing the Critical set first."*

Good: *"n9k-1 on NX-OS 9.3(5) — Cisco has published no advisory matching this exact
version. That is not confirmation the device is secure; it means nothing is published for
this version string."*

Bad: *"n9k-1 is not vulnerable."* Never say this.
