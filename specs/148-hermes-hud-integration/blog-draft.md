# Draft: Bringing Hermes into the NetClaw HUD

**Local draft — not published. Spec 148 acceptance is complete for the owner-approved Mac/WSL scope; source version 1.7.0.**

The shared NetClaw HUD previously assumed OpenClaw behind its chat and runtime panels.
Spec 148 adds an explicit Hermes selection so a Hermes deployment can use the HUD's
Chat, Canvas and local Avatar. The browser still opens port 3000. Requests go through
the HUD API on port 3001, a private MCP bridge, and a dedicated authenticated Hermes
companion on loopback port 8643. This companion uses the real Hermes agent and selected
provider configuration; it does not attach to or restart an ordinary Hermes gateway.

Each installation has its own identity, ownership bindings, transcripts and browser
storage. Canvas captures the context at each branch point. Chat and local Avatar share
one conversation. A lost submission response stays uncertain until status provides
evidence, and polling never resends the operation. Tool evidence comes from recorded
dispatch and results rather than an assistant claiming that it ran something.

The first qualification is deliberately small: a reviewed read-only subnet calculator
and its installed skill. Other MCPs need qualification before they can run through this
companion. Configuration APPLY, attachments, model/effort overrides, hosted Avatar and
federation are unavailable for Hermes here. Federation belongs to spec 149. This work
does not yet claim general Hermes network-tool parity.

Mac acceptance passed 369 HUD tests, 27 Canvas suites, 238 installer/HUD tests and 25
subtests. Six real-process tests cover pinned Hermes, actual MCP tools, ownership,
provider/configuration failures, lost admission, process restarts, cooperative stop and
zero replay. Live Anthropic acceptance passed on Mac and WSL, including contextual
follow-up, an installed skill and the actual subnet MCP result. Real Chromium on Mac
and Edge on Windows exercised Chat, local Avatar and independent Canvas branches.
Repeated installation and HUD upgrade preserved seeded configuration and saved work.
Existing OpenClaw live Chat, Canvas, Avatar and structured Terminal Intent also passed.

Acceptance exposed and corrected deadline propagation, pre-admission error attribution,
an empty Hermes Settings panel and background title inference outside the protected
hook. Auxiliary title generation and automatic context compression are disabled in the
private profile. The owner gateway and HUD were preserved. Exact tested platforms and
explicitly unverified environments are recorded in [closure.md](closure.md). This
remains an unpublished local draft; it is not a claim that a release has been published.
