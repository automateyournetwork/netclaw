---
title: "Make It Mean It: turning a NetClaw risk's 'production mode' from a label into fail-closed enforcement"
date: 2026-07-13
authors: [John, Claude]
status: draft
target: WordPress MCP (present to John for review before publishing — Constitution XVII)
spec: specs/057-in2n-production-enforcement/
---

# Make It Mean It

Yesterday we [decomposed a 190-skill monolith into a risk of NetClaws](2026-07-12-in2n-risk.md) —
a Border Claw routing to 27 focused members, live, without dropping the federation
we share with Nick and Byrn. In the "what's next" of that post we admitted something
uncomfortable: the risk had a `production` mode, but it was a **flag, not a
guarantee**. We had verified, on the running system, that "production":

- did **not** actually sandbox members — they ran as plain host processes;
- did **not** guard model I/O — when the DefenseClaw proxy was down, calls silently
  fell back to a direct provider, bypassing the guardrails entirely;
- did **not** write the immutable git audit trail our own constitution mandates
  (the emit hook was a stub);
- and wasn't even **durable** — the mesh daemon was a shell-detached process that
  died on session churn and took the whole federation layer down with it.

A security-adjacent product that *says* "production" while enforcing none of it is
worse than one that says nothing. This is the story of feature 057: making the word
mean what it says — or honestly refusing to say it.

## The one rule: never lie about your posture

The cornerstone requirement wasn't sandboxing or guarding. It was **honesty**. The
Border must report exactly one of:

- `testing` — guards intentionally off, for fast iteration;
- `production — enforced` — member sandbox (host-level kernel confinement),
  DefenseClaw model-guard, and GAIT git audit are all *verified active right now*;
- `production — DEGRADED (<controls> missing)` — naming precisely what's missing.

And it must **never** report `enforced` while any control is down. A false
"production" claim is the one outcome the whole feature exists to prevent.

That reframing is what made the rest tractable. Enforcement isn't a boolean you set
once; it's a live property you probe and re-derive. So posture is computed from
three independent control probes, cached briefly, and recomputed both by a
background poller (to keep the HUD and the operator heartbeat fresh) and —
crucially — *synchronously before every delegation*, which is the only place a
fail-closed guarantee can actually be made.

## Three controls, two kinds

The three controls aren't equal, and pretending they were would have been its own
kind of dishonesty. We split them by what they protect:

- **Containment** — the member sandbox (a compromised member is confined at the
  kernel level) and the DefenseClaw model-guard + component scan (prompts,
  completions, and a member's skills/MCPs are inspected). If either is unavailable
  in production, a delegation is **refused, fail-closed**. No unconfined, no
  unguarded execution. Ever.
- **Audit** — the GAIT git immutable trail. If it's down, the delegation still
  **runs** (it's fully contained) but every result is loudly flagged
  `audit-degraded`. Losing the immutable record is a compliance problem, not a
  containment breach — so it warns rather than blocks. An operator can tighten this
  to strict-all (block on *any* gap) with one env var.

That per-control policy — containment blocks, audit warns — is the design decision
we spent the most time getting right, and it's the one we're most confident about.

## The bug that proved the point

We built it spec-first (specify → clarify → plan → tasks → analyze → implement),
120 tests, then flipped the live Border to production. It reported:

> **production — DEGRADED (sandbox, model-guard missing)** — "openshell CLI not
> found on PATH", "defenseclaw CLI not found on PATH"

Both tools were installed. But the daemon runs as a `systemd --user` service, and
its `PATH` didn't include `~/.local/bin`. So from the daemon's point of view the
enforcement CLIs genuinely weren't reachable — and the posture *correctly refused to
claim enforced*. The honesty property caught a real deployment bug the moment it
could have mattered. One line in the service unit (`Environment=PATH=…`) later:

> **production — enforced** — sandbox ✓, model-guard ✓, audit ✓

Then a real delegation to the IP Fabric member came back `enforcement: enforced`,
and the immutable trail recorded it:

> `gait: delegation johns-risk/ipfabric by johns-risk/border` — cross-referenced to
> the SQLite audit row.

Nick and Byrn stayed federated the whole time.

## Two things that weren't what we assumed

Building this honestly meant *finding out* how the security tools actually work —
and two assumptions were wrong.

**OpenShell can't run a live-infrastructure member.** The plan was "launch each
member inside the NVIDIA OpenShell sandbox." We stood one up — and it's a fully
isolated, **empty, network-egress-denied container**: no `openclaw`, no member home,
no route to a device or API. A member whose entire job is querying live IP Fabric
can't do anything in there. We even reverse-engineered OpenShell's (undocumented, on
our box) policy schema and got least-privilege egress working — then hit the wall
that running the real member needs a whole custom image. So we pivoted the sandbox
to **host-level kernel confinement**: each member runs as a hardened `systemd` unit
(`NoNewPrivileges`, read-only system via `ProtectSystem=strict`, the operator's
master `.env` made *inaccessible*, private `/tmp`, and syscall/namespace limits on
native Linux). The member keeps its real tools and network — so it actually works —
while a compromised one can't escalate or read another member's secrets. OpenShell
remains available for isolated *code* execution; it just isn't the right primitive
for a live-infra agent.

**`defenseclaw tool inspect` doesn't exist.** Our first model-guard called a CLI
subcommand that isn't real — and so did a latent line in the frozen 056 code. The
actual DefenseClaw model guard is its **LLM guardrail proxy**: a Go proxy on `:4000`
that OpenClaw routes every prompt and response through for inspection. So "guarded"
means the proxy is *up and in the path* — not that a per-call command returned zero.
We fixed the probe to check the proxy, stood the proxy up, and corrected the 056 bug
to the real `defenseclaw tool status`. The lesson that keeps repeating: **honesty
forces you to learn the tool, not assume it.**

Both fixes were caught the same way — the posture refused to say `enforced` when the
guarantee wasn't real.

## What it buys: focus and token economy

The reason for all of this isn't only security — it's *focus*. The monolith carried
**~194 skills and ~37–52 MCP servers** — hundreds to thousands of tool schemas — in
**every** turn's context before you said a word. A risk splits that:

- the **Border** carries **zero** domain skills — just ~32 broker tools — and
  reasons about *routing*;
- each **member** carries only its slice: **~3 specialty skills + its one vendor's
  MCP server** (e.g. the IP Fabric member: IP Fabric + memory, nothing else).

That's roughly a **15–30× reduction in per-claw tool-schema context**, and — just as
important — each claw's model is focused on one job instead of diluted across 190
capabilities. Layer on **tiered models** (Opus on the Border for routing; Sonnet,
Haiku, or local Ollama on members) and the economy compounds.

## The A2A card grew a security + capability face

Federated claws exchange **A2A capability cards**. We taught the card to advertise
two new things (no secrets, ever): the risk's **posture** (`production — enforced` /
`degraded` / `testing`, with per-control status) and the claw's **LLM capability**
(its model family/tier and whether it's guardrail-routed). Now a peer — John's,
Nick's, Byrn's — doesn't just learn *what* a neighbour can do; it learns whether that
neighbour is actually enforcing its guardrails, and how capable its reasoning model
is, so it can route and trust accordingly. The HUD shows the same: local posture,
controls, and model; and a peer's advertised posture and model when you inspect it.

## Durable by construction

The recurring outage from 056 — the federation layer silently dying while the
gateway stayed up — is gone. The mesh daemon and every always-on member now run as
`systemd --user` services (`Restart=always`, survive session/terminal churn and
reboot), generated repeatably by a service generator, not hand-authored. One unit
per member, so restarts are independent and `systemctl status` tells the truth per
member. Single-owner is enforced: a member with a running unit is never
double-launched by the cold-start path.

And when something *does* break, the Border now distinguishes **daemon-down** vs
**member-down** vs **backend-unreachable** — so the operator heartbeat says "the CML
device is unreachable," not "a member flapped." (In 056 it misdiagnosed a poll bug
as a member flap; that class of lie is fixed too.)

## What we learned

- **Honesty is a feature, not a disclaimer.** The single most valuable thing the
  risk does now is refuse to overstate itself — and that refusal found a real bug on
  the first live run.
- **Enforcement is a live property, not a setting.** Probe it at the moment it
  matters (before each delegation), or you don't have it.
- **Not all controls are equal.** Separating containment (block) from audit (warn)
  kept production usable without weakening the guarantee that matters.
- **Reuse the security you have — but verify how it actually works.** DefenseClaw's
  guard is a proxy, not a CLI call; OpenShell suits isolated code, not live-infra
  agents. Honesty made us learn both instead of assuming. The wire protocol — and
  the eN2N core with Nick and Byrn — never changed.
- **The result, live:** a real production delegation to the *confined* IP Fabric
  member returned real data — *"11 snapshots total (8 loaded, 3 unloaded)"* — under
  systemd confinement, with the DefenseClaw proxy in the path and GAIT committing on
  both sides, posture `production — enforced`. 120/120 tests green.

We set out to make one word — `production` — tell the truth. Now the Border either
enforces it, or looks you in the eye and says exactly which guarantee it can't make.

---

*Written by John and Claude. Spec 057, built spec-through-implement and validated
live on the running Border `johns-risk` — posture, sandbox, guard, immutable GAIT
trail, and durable services all exercised against the real system, with Nick
(AS 65007) and Byrn (AS 65099) federated throughout.*
