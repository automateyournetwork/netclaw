> Planning completed on2026-11-22. This original brief is retained as the
> requirements source. For implementation resume,read resume.md and plan.md;
> do not regenerate completed artifacts or rerun branch creation. Latest owner
> instruction selects the isolated checkout and requires skill/MCP controls over
> the official API. No live world or native integration has been qualified.

# Spec200: Genie-to-Genie specification and planning kickoff

Paste the following into a fresh session after `/clear`.

---

We are starting Spec200, **Genie-to-Genie: evidence-grounded, explorable network
worlds**. Act as my NetClaw product architect and implementation planner. Use
Spec Kit to refine the existing specification and produce a complete plan.
This turn is specification and planning, not a paid generation or deployment.

## Workspace and roadmap

Work in `/Users/john.capobianco/netclaw-spec200-genie`, branch
`200-genie-network-worlds`. Check the branch and working tree first. Reuse
`specs/200-genie-network-worlds/`; do not create201, rerun branch creation, or
replace this with a generic world-model project. `.specify/feature.json` already
selects200. Branch `198-azure-multicloud-ha` and its matching origin branch hold
the saved, unfinished198Azure/GCP checkpoint at `856bbc88`.
Do not merge that unfinished implementation
into200.199is reserved forAWS. Order: prove and complete feasible200, then
resume198, then199. No merge, release, version bump, Marketplace publication,
blog publication or cloud activation is requested by this planning turn.

Follow repository startup/GAIT instructions. Read SOUL.md, USER.md, TOOLS.md,
AGENTS.md, the constitution and applicable skills. Then read this feature's
spec.md, research.md, verification.md, resume.md and synthetic-world-prompt.txt.
Treat the verified evidence and explicit gaps as the starting point.

## The product idea

Let me ask NetClaw to turn a bounded network snapshot into an explorable,
interactive environment. Cisco pyATS Genie supplies measured facts; Google
Genie supplies an imaginative spatial presentation. The useful result is a
network walkthrough for explanation, training and incident storytelling.

Start with a small network museum: routers as routing halls, switches as
distribution rooms, observed links as corridors and status as lighting. Keep
this mapping replaceable. Explain why it helps the operator and what fidelity
it requires. Do not promise that visual corridors implement routing or that
generated traffic predicts forwarding behavior.

Maintain two explicit layers: authoritative local facts with provenance and
uncertainty, and the generated illustration. Facts, labels, observations and
the legend should remain readable outside the generated video. Never infer
device health from a world, invent unseen links, or apply configurations from
world interactions. A text-to-image preview alone is not the requested world.

## Established facts and access gaps

The2026-11-22 read-only checks authenticated CML at the private controller, version2.10,
ready=true. R1/R2/SW1/SW2 were all observed BOOTED after I started SW1. Each
returned an actual pyATS show-version result parsed as IOS17.18.2. R1/R2
management interfaces were up/up. Native subnet MCP passed192.0.2.0/24 with
256addresses and254usable. No neighbor topology or routing-health certification
was established. Docker29.9.2 is running after I started it.

Successful pyATS checks used the existing isolated R02runtime and private
testbeds with strict saved host keys. Default native runtime discovery is still
broken; repository testbed has invalid defaults.arguments placement and stale
switch addresses. Existing bounded subnet artifact works; old repository subnet
source has an MCP2 import incompatibility. Design a small read-only collector
qualification task without silently replacing installations, changing SSH trust
or broadening this into unrelated repairs. Raw private evidence locations are
in verification.md. Recheck current state only when needed; do not redo an
entire lab health audit just to write the plan.

Google's November19announcement and official docs establish a real `genie-4`
API through Live Interactions with Python/JavaScript and WebRTC/WebSocket.
Reverify the official contract and SDK versions before designing the adapter:

- https://aistudio.google.com/docs/genie
- https://aistudio.google.com/docs/models/genie-4
- https://aistudio.google.com/docs/pricing#genie-4
- https://deepmind.google/models/genie/prompt-guide/
- https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_Genie_4.ipynb

I have Project Genie browser access. Paid Gemini API entitlement has not been
tested, no key was configured in the two inspected dotenv files, and CUA was
unavailable in the prior session. Ask for a private local credential path only
when needed, never a secret in chat. Missing runtime access must not block
completion of the specification and plan; retain it as an execution gate.

## Architecture decisions to resolve

1. Prefer the official API. Decide the smallest adapter and local viewer needed
   for a proof. Reuse suitable NetClaw audit, evidence and lifecycle components;
   avoid creating a new framework or cloud service just for this experiment.
2. Define a bounded observation → normalized facts → scene description pipeline.
   Include provenance, timestamps, stale/unknown states, observed versus assumed
   links, input limits, and handling of untrusted device strings. Choose exact
   read-only collection commands only after reviewing existing capabilities.
3. Keep real private configurations, credentials and topology local. First
   hosted proof uses an independent synthetic scenario. Anonymized names alone
   do not make topology public. If a real-data world requires an exception,
   identify the exact outbound projection for later owner review; do not invent
   an exception or assume approval. No private uploads during planning.
4. Decide whether text alone is sufficient or a locally rendered16:9reference
   image would improve the scene. Do not require another image-generation
   subscription merely to run this experiment.
5. Keep streaming in the viewer, not inside MCP responses. Assess a small MCP
   control wrapper and a reusable NetClaw skill as optional interfaces around
   the same session lifecycle. Distinguish Google's documentation MCP from
   an execution MCP; do not install an unrelated product named Genie.
6. Define creation, navigation, one fictional event, terminal completion,
   usage evidence, deadlines and unknown outcomes. The backend owns the long-lived
   key and termination responsibility. Closing a tab does not stop generation.
   No automatic new session or replay after uncertain creation/completion.
7. Document separate HUD, VS Code and Mobile impact decisions. Keep the first
   proof standalone unless existing integration materially simplifies it.
   Do not promise editable3Dmeshes, durable scene graphs or capabilities absent
   from the current documented service.

## Feasibility and acceptance

Plan a short, finite synthetic trial first: approximately20seconds, one scene,
deliberate navigation and one link-status lighting event. Previously verified
pricing was approximatelyUS$0.10/second; refresh it and distinguish a local
timer/estimate from a service-enforced cap. Establish the actual access and
finite trial allowance before execution; do not create a paid account.

Define go/no-go criteria for recognizability, navigation, observed event outcome,
object/link drift, usable evidence and confirmed termination. Preserve model
failures instead of changing criteria to claim success. If fidelity is poor,
state whether it remains useful for storytelling; do not call it a digital twin.
No200completion claim until an actual generated world is reviewed.

## Deliverables and working style

Use speckit-specify to refine the existing spec without creating a second
feature; use speckit-clarify only for consequential unresolved choices, then
speckit-plan. Produce a coherent spec.md, plan.md, research.md, data-model.md,
contracts/, quickstart.md and refreshed requirements checklist/verification.
Plan phases, dependencies, meaningful tests, evidence capture and completion
gates. Keep tasks generation and implementation as subsequent stages.

Use sensible defaults and continue independent planning while access questions
remain pending. Ask at most three questions that would actually change the
design. Keep me informed. End with the chosen design, what is already proven,
the remaining live gates, and the exact next implementation step.
