---
name: anta-validation
description: Validate Arista EOS network state with structured pass/fail verdicts using ANTA. Use for "is this switch healthy", "did my change break anything", "verify BGP/interfaces/hardware are correct", "run a health check on this device". Read-only. A test for a feature the device does not run reports not_applicable — never a failure — and no health percentage is ever emitted.
---

# ANTA validation — the assertion layer

Every other NetClaw source **reads** state. This one **asserts** on it and returns a verdict you can
act on.

**Server**: `anta-mcp` (NetClaw-authored over ANTA 1.9.0, Apache-2.0, own virtualenv) · 4 tools ·
1,272 tokens · **208 tests** in the catalogue

## Which plane answers — read this before reaching for another server

Three servers touch Arista. They answer different questions, and picking the wrong one gives a
confidently wrong answer.

| Plane | Server | Answers |
|---|---|---|
| **Validation** | **this skill** | *does the state match what it should be* — pass/fail |
| Management | `arista-cvp-mcp` | *what does CloudVision say* — inventory, tags, compliance as CVP sees it |
| Device CLI | `pyats-*`, `multivendor-cli` | *what is the raw state* — show-command output |

**Use this skill to assert, not to fetch.** If the question is "what is the interface MTU", that is
the CLI plane. If the question is "is the MTU what it should be", that is this one.

## The verdicts — five, and they never merge

| Verdict | Means | Never counts as |
|---|---|---|
| `pass` | tested, expectation held | — |
| `fail` | tested, expectation did not hold | — |
| **`not_applicable`** | **the feature is not configured — nothing was tested** | `fail` |
| `skipped` | ANTA declined to run it | `pass` |
| `error` | device unreachable or the run broke | `fail` |

### `not_applicable` is the one that matters

ANTA natively reports a test for an unconfigured feature as a **failure**. Measured on a lab switch:

```
VerifyBGPPeerCount → failure
  "'show bgp summary vrf all' failed on veos1: BGP inactive"
```

That device has **no BGP at all**. Reporting it as a failure claims a BGP fault where there is no
BGP. The server reclassifies it to `not_applicable` and keeps the original message.

**When you report results**: say "BGP: not applicable — this device does not run BGP", never "BGP
test failed".

### There is no health percentage, and you should not compute one

`passed / total` is meaningless when `not_applicable` and `skipped` sit in the denominator. Forty
tests of which thirty are not applicable is not "25% healthy" — it is ten real answers and thirty
non-answers. The server **refuses** to emit a percentage. Report the five counts.

## Workflow

**1. Find the tests** (contacts no device):

```
anta_list_tests: category="routing.bgp"        # or keyword="ntp", or both
```

**2. Learn what a test needs** (contacts no device):

```
anta_describe_test: test="VerifyEOSVersion"    # returns its input schema
```

Do this whenever a test takes inputs. A test run without required inputs is reported as `skipped`
with the requirements listed — it does **not** guess a default and silently test the wrong thing.

**3. Run them**:

```
anta_run_tests:
  host: "172.20.20.4"
  tests: ["VerifyEOSVersion", "VerifyUptime", "VerifyNTP"]
  inputs: {"VerifyEOSVersion": {"versions": ["4.36.1F"]}, "VerifyUptime": {"minimum": 3600}}
```

Or by category: `category: "hardware"`.

## Reading a result honestly

- **An unreachable device returns `error` with zero results.** It is not a broken device — nothing
  was tested. Say "could not reach the device", never "the device failed its tests".
- **An empty selection returns `no_tests_selected`.** No test matched. That is not a healthy device.
- **A `fail` names observed and expected.** Quote both — "NTP expected synchronised, actual
  unsynchronised" is actionable; "NTP test failed" is not.

## Credentials and scope

`ANTA_USERNAME` / `ANTA_PASSWORD` come from the environment and are **never** tool arguments and
never appear in output. `ANTA_VERIFY_TLS` defaults to `false` because lab switches ship self-signed
certificates — and the setting is **always disclosed** in the response as `tls_verified`, so a
downgrade is visible rather than silent.

## Boundaries

- **EOS only.** ANTA is Arista's framework. This is not multivendor validation, and it must not be
  described as such.
- **Read-only.** ANTA tests; it does not configure. There is no remediation path here — if a test
  fails, fixing it goes through the normal change process with its CR gating.
- **On demand.** This is not continuous monitoring. For "what was it doing over time", use
  `zabbix-metrics-history`.
