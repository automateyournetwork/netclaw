# Draft: Bringing Hermes into the NetClaw HUD

**Local draft — not published. Acceptance and release are pending.**

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

Mac automated validation passed 366 HUD tests, 27 Canvas suites, installer regressions,
and a real pinned Hermes fixture with a controlled local provider and real subnet MCP.
That fixture exercises five turns, HTTP/MCP integration, ownership, memory exclusion,
forbidden tool rejection and history compaction. It is not proof of a live paid provider.
Windows/WSL, real-browser and owner-provider acceptance remain open. The current owner
HUD was not restarted. Release metadata will advance only after the required acceptance
checks, documented in this spec's validation record, are complete.
