# Eight API Families, One That Answers, and a Regex That Lied

**Draft for review — not published.** Constitution Principle XVII requires John's sign-off first.

*By John Capobianco and Claude · 2026-07-31*

Roadmap item R2 was meant to close a top-five netops question NetClaw could not answer: *is this build
affected by an advisory, past end-of-life, or hitting a known bug?* We shipped a third of that. Not
because we ran out of time, but because measuring first showed the rest is not reachable — and the part
we did ship taught us something uncomfortable about how a vulnerability check fails.

## Seven of eight families return 403

The plan named four Cisco Support API families. A community server already existed with 46 tools across
eight of them, which looked like an easy adoption.

We tested with real credentials before writing the spec. PSIRT openVuln returned 200. Bug Search, Case,
EoX and Serial-to-Info returned **403**. CX Cloud returned **504** on all seven paths we tried. The API
Console grant covers PSIRT and nothing else.

So we didn't adopt the 46-tool server. Seven-eighths of that manifest would have been dead surface — and
a tool manifest isn't free, it costs tokens on every single turn to advertise capabilities that answer
403. NetClaw ships six tools against the one family that works.

**Be clear about what this means: EoL/EoS lookup is still not delivered.** It was half of R2's value, and
it is not descoped for convenience — it is unreachable with the entitlement we have. "Is this switch past
end-of-support?" remains a question NetClaw cannot answer.

## IOS-XR isn't an OS on this API

We tried `iosxr` with 7.5.2, 6.6.3 and 24.1.1. All three returned **404 with an empty body**, while an
`iosxe` control in the same session returned 200. The supported families reject a bad version with
`INVALID_<OS>_VERSION` — which proves the OS was recognised and only the version rejected. IOS-XR
returns nothing of the kind. The path doesn't exist.

This one is worth saying out loud to users rather than quietly working around, because NetClaw *can* talk
to IOS-XR through pyATS. An operator will reasonably assume the version check works. It doesn't, and
pretending otherwise by returning an empty list would be worse than refusing.

## The formats contradict each other

We assumed one normalisation rule: Cisco rejects `17.3(1)` and accepts `17.3.1`, so fold the
parenthesised build into a dotted one. We verified that on IOS-XE and moved on.

Then we probed the other six families, and the assumption inverted:

| OSType | Accepted | Rejected |
|---|---|---|
| `iosxe` | `17.3.1` | `17.3(1)` |
| `ios` | `15.2(4)E` | `15.2.4E` |
| `nxos` | `9.3(5)` | `9.3.5` |
| `asa` | `9.16.1` | `9.16(1)` |
| `aci` | `15.2(3e)` | `15.2(3)e`, `5.2(3e)` |

`ios` and `nxos` **require** exactly the form `iosxe` rejects. `aci` wants the letter suffix inside the
parentheses where `ios` wants it outside. And `aci` means the *switch image* version — the APIC
controller version an operator would naturally read off the box is refused outright.

Our single global rule would have broken `ios` and `nxos` on every call. The conversion now runs in
whichever direction the family needs.

There's a smaller, happier consequence: we'd designed a `normaliser_verified` flag on the assumption that
only IOS-XE could be tested. All seven turned out testable directly against the API, and testing them is
precisely what exposed the contradiction. The flag stays anyway — a future Cisco OSType will arrive
unverified, and the mechanism that says so has to already exist.

## The bug that mattered: a regex that answered confidently about the wrong software

Our version tokeniser ended with `\b`. On `17.3(1)` at end-of-string, `\b` cannot match after the closing
paren — both neighbours are non-word characters. So the regex engine did what regex engines do: it
backtracked, dropped the parenthesised group, and returned `17.3`.

`17.3` is a perfectly valid IOS-XE version. It queried the API cleanly, got a 200, and came back with a
plausible advisory count **for software the device isn't running**. No error. No warning. A confident
answer to a question nobody asked.

That is the whole argument for the rule we'd written into the spec before we found the bug: **a
normalisation failure must never be reported as an empty advisory list.** We'd been thinking about the
empty case. The truncation case is worse, because an empty list at least looks suspicious.

Normalisation is now anchored — a candidate that doesn't match in its entirety is rejected, never
salvaged. A second bug the same live call caught: an unanchored `re.sub` intended to strip a trailing
product fragment matched from the *first word* of a real `show version` banner and deleted the whole
string, so valid input normalised to nothing.

Both bugs were invisible to the offline tests we'd already written. They surfaced the moment we pointed
the thing at the real API.

## "No advisories" is not "not vulnerable"

This is the distinction the whole feature is built to protect, and it's the one a reader will otherwise
get wrong.

Five outcomes. Two look identical in the data — an empty `advisories` list:

- `none_published` — Cisco has published nothing for this version.
- `normalisation_failed` / `api_error` — **the question was never asked.**

An empty list reads as a clean bill of health. If a parse failure collapsed into `none_published`, the
tool would tell an operator a device is safe when nothing was checked. So the rule lives inside the
normaliser, not the tool layer: if the normaliser can emit a version that reaches the API, the confusion
is already possible no matter how careful everything downstream is.

`check_versions` reports outcome counts for exactly this reason. Before you call a fleet clean, look at
how many devices were never checked.

And even `none_published` isn't "secure" — it means Cisco published nothing matching that exact version
string. The skill instructs NetClaw never to say "not vulnerable."

## Proven on live hardware

pyATS read **IOS-XE 17.16.1a** off a live CML router. PSIRT returned **26 advisories: 14 High, 11 Medium,
1 Critical** — `cisco-sa-http-code-exec-WmfP3h3O`, CVSS 9.0, CVE-2025-20363. The raw `show version`
banner and the Genie-parsed version normalised identically. No human typed a version.

That chain — device to advisory with nothing typed in between — was the actual point of R2, and it's the
part that works.

## The budget shapes the design

5 calls/second and 30/minute, shared across every caller of the credential. The per-minute limit is the
real constraint, and it's tight enough that a naive fleet sweep exhausts it in two seconds.

The order is contractual: **de-duplicate → cache → pace → back off.** De-duplication first, because it's
the largest win by far and costs a dictionary lookup — 60 devices running 12 distinct versions cost 12
calls, not 60. Pacing an un-de-duplicated sweep doesn't fix anything; it just spreads the same excess
over more minutes.

## What we'd tell someone starting R3

Measure before you spec. This is the fourth roadmap item in a row where doing so changed the shape of the
work — and R2 is the starkest: the feature came out one-eighth the size the plan assumed, and the two
worst bugs were only visible against the live API.

An adjacent lesson from the same session: `pyATS` on this host imports only from a stranded Python 3.13
site-packages, not the 3.14 the rest of NetClaw runs on. The chain verification ran as two processes —
which is how it works in production anyway. Worth knowing before someone tries to put pyATS and a
3.14-installed server in one.
