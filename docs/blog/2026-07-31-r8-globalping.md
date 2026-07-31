# Looking At Ourselves From Outside, And The Billing Model I Got Backwards

**Draft for review — not published.** Constitution Principle XVII requires John's sign-off first.

*By John Capobianco and Claude · 2026-07-31*

NetClaw has always been able to prove a router is healthy. It has never been able to tell you whether anyone
outside can reach it.

Every device-facing integration — pyATS, the multivendor driver, gNMI, SuzieQ, Batfish — looks at the network
from *within* the administrative domain. So when someone says "the site is slow from Singapore", NetClaw could
check every interface, every routing table, every counter, and still have nothing to say about the actual
question.

Roadmap item R8 fixed that with Globalping: ~4,800 probes across ~1,390 autonomous systems, exposed as an
official remote MCP. It was rated the highest value-per-effort item in our original scan, and that held up —
**we wrote no server at all.** One registration, one skill.

Which is precisely why the skill had to be right. When a feature is a registration plus prose, the prose *is*
the implementation.

## Three ways to get nothing back

The engineering here is one distinction:

| What comes back | What it means |
|---|---|
| `no_probes_found` | **The measurement never ran.** No probe matched your location filter. |
| `finished`, 0 of N successful | **The target didn't answer.** A real finding. |
| Private/internal target | Out of scope. Refused before we call out. |

The first is a trap. It arrives failure-shaped, and read carelessly it looks like a total outage — when it
actually says *nothing whatsoever* about the target. An agent that reports it as unreachability escalates an
incident that doesn't exist.

That's the same shape as the problem we'd just solved in R2 ("no advisories" is not "not vulnerable"), and it
got the same treatment: explicitly named states, and a skill that spells out the difference in words rather
than assuming the reader will infer it.

The third one is worth a note too. Globalping refuses RFC1918, loopback and link-local addresses itself, with
genuinely good error messages. We refuse them **first anyway** — because by the time the server tells you no,
your internal hostname has already been transmitted to a third party. That's a disclosure control, not a
correctness one.

## The part where I was wrong

My first research pass measured the rate limit and concluded: **one call costs one measurement, regardless of
how many probes it uses.** A 100-probe global test costs the same as a single-probe test. Breadth is free.

I built guidance on that. It went into the spec, the skill, the task list, the contract document, the
quickstart, and the offline test assertions. I even wrote a satisfying little narrative around it — *this spec
inverts the previous one's budget strategy; R2 needed aggressive de-duplication, R8 rewards breadth.* Two
adjacent specs, opposite instincts, a nice lesson about not carrying habits across domains.

It was wrong. A controlled test — one call at a time, reading the remaining budget either side — showed:

| `limit` | cost |
|---|---|
| 1 | **1** |
| 5 | **5** |
| 20 | **20** |

**Cost equals probe count.** The billing is per probe.

Here's how I fooled myself: 35 exploratory calls had moved the allowance from 500 to 465. Thirty-five calls,
thirty-five units, therefore per-call billing. But most of those calls happened to use `limit: 1`. I inferred
a billing model from an uncontrolled sample and the arithmetic coincidentally agreed.

The skill I'd written was actively telling the agent to do the wrong thing — reach for wide probe counts
because they're free. In practice five 100-probe tests exhaust the hourly allowance.

Two things I'd keep from this:

**The narrative I liked was the tell.** "This spec inverts the previous one" was a satisfying story, and a
satisfying story is exactly the place an uncontrolled inference survives scrutiny. I was pleased with the
symmetry, so I didn't go back and test the claim it rested on.

**The test suite now asserts the absence of the wrong claim**, not just the presence of the right one. A stale
sentence sitting next to a corrected one is worse than either alone, because a reader can't tell which is
current. That assertion exists specifically because this mistake happened.

## The vendor's own example doesn't work

`AS13335` appears as a location example **in Globalping's own tool schema**. It never returns probes.
Cloudflare hosts none. Neither does AS15169 (Google). AS3320, AS16509 and AS174 do.

We'd previously logged an unresolved "Globalping location syntax bug" from an earlier scan. That turned out to
be two separate things conflated: a genuine syntax issue (`London,UK` fails — `+` is the AND separator, not a
comma) and a probe-availability fact (`AS13335` is perfectly valid syntax pointing at an ASN with no probes).

The consequence is worse than a documentation nit. Anyone learning the syntax from the vendor's example tries
`AS13335`, gets `no_probes_found`, and concludes ASN filtering is broken — when it works fine. A wrong lesson
learned from the vendor's own documentation is stickier than no documentation.

Only ~1,390 of the internet's autonomous systems host a probe. We confirmed that by pulling the probe list
directly rather than trusting either the docs or our own inference. Twice bitten.

## Twelve tools, five of which do anything

The endpoint advertises 12 tools. **Six of them take only the `context` argument** — `help`, `authStatus`,
`compareLocations`, `get_more_tools`, `limits`, `locations`. The actual measurement capability is five tools:
ping, traceroute, dns, mtr, http.

Worth remembering when comparing integrations by tool count across a roadmap. A tool count is not a capability
count.

## An unusual privacy surface

Every Globalping tool requires a `context` parameter: 15-25 words of natural language explaining *why* you're
making the call, which the vendor states is used for "analytics and user intent tracking".

No other NetClaw integration asks for anything like this. Every other one sends the data the operation needs.
This one asks for a description of your intent.

We didn't gate it per call — a confirmation prompt on every ping would make the integration useless and train
people to click through, which is worse than no gate. Instead NetClaw sends a generic, task-shaped sentence
with no customer name, internal hostname, ticket reference or topology detail in it, and the skill says
plainly that the field leaves the building, so an operator can decline the integration outright if that's
unacceptable in their environment.

We recorded the reasoning rather than waving it through, because "it's just analytics" is exactly the sentence
that would let a customer name out the door.

(It's also not enforced — calls succeed with `context` omitted. We send it anyway; depending on
unenforced-required behaviour means every call breaks at once the day they start enforcing it.)

## What we'd tell someone starting R9

Same lesson as the last four roadmap items, with a sharper edge: **measure before you spec, and then check
whether you actually measured what you think you measured.**

R2's rescope came from measuring. R8's core semantics came from measuring. But R8's budget error *also* came
from measuring — badly, without controls, and then wrapping the result in a story I found appealing. The
discipline isn't "run a command against the live API". It's "vary one thing at a time and confirm the
mechanism".
