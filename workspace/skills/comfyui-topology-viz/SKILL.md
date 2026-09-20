---
name: comfyui-topology-viz
description: "Turn a network topology into one stylized, AI-generated still image via a self-hosted ComfyUI instance — reuses the same topology model as threejs-network-viz (any of 8 topology-source integrations, or a freeform description). Use when the operator asks for a stylized, flashy, or AI-generated image/picture/illustration of a network topology. Stills only — no video/animation."
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["node"]
      env: ["COMFYUI_URL"]
---

# ComfyUI Network Topology Visualization Skill

**Version**: 1.0.0
**Feature**: 120-comfyui-topology-viz
**Status**: Active

## Overview

Turns a network topology into one stylized, AI-generated still image via a self-hosted ComfyUI
instance — a different rendering path from NetClaw's existing three.js (`threejs-network-viz`),
Blender (`blender-3d-viz`), and UE5 (`ue5-network-viz`) skills, which all produce navigable 3D
scenes. This skill produces one flat, "flashy" illustration per request instead, reusing the same
canonical topology model spec 046's three.js skill already assembles from any of NetClaw's
existing topology-source integrations, or a freeform description.

**v1 scope is stills only.** Video (traffic flybys, packet-tracing animations) and stylized
test-result cards are explicitly out of scope for this version — likely follow-on specs, not built
here (spec.md FR-016).

## Prerequisites

### Required

- **A separately running ComfyUI instance** — this skill does not install or manage ComfyUI
  itself, only connects to one you already have running. Get ComfyUI from
  https://github.com/comfyanonymous/ComfyUI or the ComfyUI Desktop app.
- **`COMFYUI_URL`** in `.env` (see `.env.example`) — your ComfyUI instance's endpoint, e.g.
  `http://127.0.0.1:8000`. Required; there is no assumed default (FR-005), because
  `comfyui-mcp`'s own built-in defaults (`8000` for ComfyUI Desktop, `8188` for a manual install)
  are easy to mix up with your actual instance's port.
- **At least one image-generation checkpoint installed in ComfyUI** (Stable Diffusion 1.5, SDXL,
  or Flux) — see "If you get 'no usable model found'" below if you haven't installed one yet.
- The vendored `comfyui-mcp` server (`mcp-servers/comfyui-mcp/`), cloned and built via
  `npm install && npm run build`, registered as `comfyui-mcp` in `config/openclaw.json`.

### Topology sources

Any of NetClaw's existing topology-of-record or lab-emulation integrations — Cisco Modeling Labs,
GNS3, containerlab, EVE-NG, Nautobot, NetBox/Infrahub, IP Fabric, or Forward Networks — or a
freeform plain-language description requiring no live source at all.

## Natural Language Commands

### Render a live topology as a stylized still image (User Story 1)

```
"Give me a stylized AI image of the CML lab topology"
"Render my GNS3 project as a ComfyUI image"
"Make a flashy image of this network"
```

NetClaw retrieves the topology from the named (or clarified) source, checks what image-generation
checkpoints ComfyUI has installed, generates one image, and tells you where it was saved:
`workspace/output/comfyui-topology-viz/comfyui-<timestamp>-<request-id>.png` (plus a sidecar
`.json` recording the prompt and checkpoint used) — and which checkpoint was used (FR-006a).

### Sketch a topology without a live source (User Story 3)

```
"Make a flashy image of this topology: a router r1 connected to a switch sw1"
```

Same generation pipeline as a live-sourced request, just parsed from your plain-language
description instead.

### If something isn't available (User Story 2)

Every failure NetClaw can detect gets a specific, distinct message — never a hang or a generic
error:

| Condition | What NetClaw tells you |
|---|---|
| ComfyUI unreachable at the configured `COMFYUI_URL` (or `comfyui-mcp` silently connected to a *different* instance instead — see Known Limitations) | The configured endpoint could not be reached |
| ComfyUI reachable, but no installed checkpoint is suitable for image generation | What kind of model to install (SD1.5/SDXL/Flux) and where |
| ComfyUI itself reports the generation job failed | The generation failed — as distinct from a reachability or missing-model problem |
| A generation is already running | Wait for it to finish (or fail) and ask again — this skill runs one job at a time, never two concurrently |
| A named topology source is unreachable | The sourcing failure, distinct from anything ComfyUI-side |
| The topology has zero devices | Nothing to visualize — no generation is attempted |

There is **no NetClaw-imposed timeout** on generation itself — real GPU image-generation time
varies with model, workflow, and hardware, so a submitted job is tracked to ComfyUI's own
completed/failed status rather than being given up on early.

## If you get "no usable model found"

Expected on a fresh ComfyUI install with no checkpoints downloaded yet — not a NetClaw bug. Install
at least one Stable Diffusion 1.5, SDXL, or Flux checkpoint into ComfyUI's `models/checkpoints`
directory (ComfyUI Manager, or a manual download into that folder), then ask again.

## Architecture

| Module | Responsibility |
|---|---|
| `topology_model.py` | Canonical `Device`/`Interface`/`Link`/`TopologySnapshot` types (ported from `threejs-network-viz`, trimmed of 3D-only concepts) |
| `materials.py` | Hostname-based device-role inference (ported, trimmed of color tables) |
| `sources.py` | One adapter per topology source (8 live integrations + freeform), plus source-selection disambiguation (ported) |
| `generation_model.py` | NEW entities: `GenerationRequest`, `ModelAvailabilityCheck`, `GeneratedImage`, the six-`kind` `GenerationFailure` taxonomy |
| `comfyui_client.py` | MCP stdio client wrapper around the vendored `comfyui-mcp` server — discovery, template selection, async submission, no-timeout polling, plus the ControlNet workflow builder and image upload |
| `prompt_builder.py` | `TopologySnapshot` → a bounded-length, role/count-summarized generation prompt |
| `topology_renderer.py` | Deterministic (NOT AI) box/line structure diagram, fed to ComfyUI's Canny node as ControlNet conditioning — the structural-accuracy pipeline (research.md §10) |
| `label_overlay.py` | Burns real, correct hostname labels onto the completed generation deterministically — Canny-conditioned text is too lossy for Flux to reproduce reliably (research.md §10) |
| `generation.py` | Orchestrates the full call sequence and every failure classification; picks the structural ControlNet path when available, falls back to plain txt2img otherwise; enforces the single-in-flight-job guard — **unmodified since spec 120** (spec 121 FR-012) |
| `output.py` | Overlays labels (if structural path used) and copies the completed image into `workspace/output/comfyui-topology-viz/` with a timestamped name + sidecar JSON, never overwriting — **unmodified since spec 120** |
| `federated_generation.py` | **NEW (spec 121)** — the actual entry point `__init__.py` now calls. Routes each request between the federated path (below) and `generation.run_generation()`'s existing pipeline (called as-is, never modified) |

See `contracts/comfyui-generation-contract.md` for spec 120's exact fallback call sequence, and
`specs/121-federated-topology-viz/contracts/` for the two new federated-stage tool contracts.

## The federated path (spec 121)

**Same entry point, no new command** — every "give me a stylized image" request goes through this
skill exactly as before; which path actually produced the delivered image is now visible in the
response as `generation_path`:

| `generation_path` | Meaning |
|---|---|
| `federated` | Both stages ran on an operator-configured federation member (e.g. `<your-risk>/viz`): a deterministic, correct-by-construction diagram (real role icons, real labels, real connections — no diffusion model involved), then a diffusion image-edit pass that restyled it without altering structure. This is the strongest correctness guarantee this skill can offer (spec 121 SC-001). |
| `federated_partial` | The structural diagram (correct, unstyled) was produced on the configured federation member, but the styling stage failed or that half of the member was unreachable — you still get the correct diagram, not nothing, with `reason` telling you styling didn't complete. |
| `fallback` | Spec 120's original Flux+ControlNet+Canny pipeline (unchanged) — used for a freeform request (no real device data for the structural stage to work from) or when the configured federation member itself is unreachable. `reason` says which. |

Both new stages run as separate MCP servers (`mcp-servers/topology-diagram-mcp/`,
`mcp-servers/image-style-mcp/`) invoked from Border via `n2n/tools/call` on the live
your configured federation member — Border never renders or diffuses anything itself for this path (FR-005).
See `specs/121-federated-topology-viz/research.md` for the full design, including four real gaps
found and fixed in the shared federation infrastructure itself (R10) to make this actually work —
this was the first working internal `n2n/tools/call` in the codebase.

**If your viz federation member is down**: `systemctl --user start netclaw-member-<your-risk>-viz.service` (service name derived from your own risk/member name, per your N2N federation setup)
(it's `enabled`, so a host reboot brings it back automatically).

## Two generation paths (spec 120's fallback pipeline, used when the federated path isn't)

- **Structural (preferred, when Flux + a ControlNet are installed)**: the topology is rendered as
  a plain geometric box/line diagram, ComfyUI's Canny node extracts edges from it, and Flux paints
  over those edges — the generated image's structure (which device connects to which) is
  guaranteed accurate because it comes from deterministic code, not the diffusion model. Real
  hostname labels are overlaid afterward, also deterministically. Verified end-to-end
  (2026-08-28): exactly the right devices, exactly the right connections, correct legible labels.
- **Plain txt2img (fallback)**: used only when the ControlNet pipeline's models aren't all
  installed. Generates from a text-only prompt with no structural guarantee — the diffusion model
  is free-associating from a description, not reproducing an accurate diagram. Verified working
  (produces a real image) but visually confirmed by the user to not resemble the actual topology.

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `COMFYUI_URL` | Yes | Endpoint of your own already-running ComfyUI instance |

## Known Limitations

- **Stills only (v1).** No video/animation output, no stylized test-result cards — see Overview.
- **One job at a time.** A second request while one is generating is rejected outright, not
  queued.
- **`comfyui-mcp` can silently substitute a different ComfyUI instance than the one configured.**
  Found live during implementation: if the configured `COMFYUI_URL` is unreachable, `comfyui-mcp`
  falls back to port-scanning common local ports and connects to *whatever* ComfyUI it finds there
  instead of failing — even for a completely non-routable configured host. `comfyui_client.py`
  guards against this by verifying the response's `comfyuiUrl`/`discoverySource` actually match
  what was configured, treating a mismatch as `backend_unreachable` rather than silently
  generating against the wrong instance. See research.md §8. If you run more than one ComfyUI
  instance on the same network, double-check `COMFYUI_URL` is exactly right.
- **`comfyui-mcp`'s own `npm audit` reports 10 vulnerabilities** (1 low, 2 moderate, 7 high) in
  transitive dependencies it bundles for its own internal HTTP/WebSocket handling (`hono`,
  `path-to-regexp`, `qs`, `sharp`, `ws`) — all in libraries used for `comfyui-mcp`'s own internal
  serving/media-processing, not exposed to this skill's stdio-only, sandboxed usage. Tracked as a
  non-blocking follow-up, matching the same treatment `sketchfab-mcp-server`'s own audit findings
  received in spec 046 — do not run `npm audit fix --force` (it force-upgrades `sharp` with a
  breaking change) without testing the server still builds and runs afterward.
- **`comfyui-mcp`'s own task tracker (`get_task_result`/`get_task`/`list_tasks`) is unreliable —
  do not poll it.** Live-verified: it got permanently stuck reporting `{"status": "working"}` for
  a job ComfyUI itself had already completed successfully ~19 seconds earlier; its WebSocket
  completion listener silently failed to update. Completion is instead tracked by polling
  ComfyUI's own `/history/{promptId}` endpoint directly (`comfyui_client.get_prompt_history()`),
  and the finished image is downloaded straight from ComfyUI's own `/view` endpoint — neither
  depends on anything `comfyui-mcp` reports about task status or file location. See research.md
  §9. `get_task_result` is kept in `comfyui_client.py` for diagnostics only.
- **A stdio teardown race in our own client, not comfyui-mcp**, was also found and fixed: calling
  `run_workflow` intermittently raised `anyio.BrokenResourceError` even though the job had
  actually submitted and completed successfully every time (confirmed against ComfyUI's own
  history) — a race between trailing stdio traffic and our client's `async with` teardown. Fixed
  by capturing the result before the context managers close (research.md §9).
- **Verified end-to-end, plain path** (2026-08-27): a real freeform topology produced a genuine
  512×512 PNG in ~21.5 seconds using `sd_xl_base_1.0.safetensors`, correctly attributed in both
  the returned path and the sidecar JSON — but visually confirmed not to resemble the actual
  topology (abstract line-art, no real structure).
- **`sources.from_freeform()` mis-parsed connector clauses with inline role declarations.**
  `"core1 connects to a switch called sw1"` took the article "a" as the device name instead of
  "sw1" — creating a phantom device and leaving the real one disconnected. Invisible in the plain
  path (which never exposes exact link structure in its prompt) but exposed immediately once the
  structural renderer made the parsed graph directly visible. Fixed in `sources.py`; the identical
  bug still exists in `threejs-network-viz/sources.py` (this was ported from there) but was left
  untouched per FR-014. See research.md §10.
- **Canny-edge text reconstruction is unreliable.** Baking hostnames into the structure image and
  relying on Flux to reproduce them through Canny conditioning produced garbled nonsense, not
  real text. Fixed by never asking the diffusion model to render text at all — see the two
  generation paths section above and `label_overlay.py`. See research.md §10.
- **Verified end-to-end, structural path** (2026-08-28): the same freeform topology produced a
  genuinely correct diagram in 41.9s — exactly 3 devices, the real `core1↔sw1↔fw1` chain, correct
  legible labels. Remaining imperfections are cosmetic (generic device icons rather than
  role-specific ones, decorative hallucinated background clutter, thin/dashed rather than
  "glowing" connection lines) — prompt-tuning opportunities, not correctness bugs.
- **~25GB of Flux/ControlNet models installed on the ComfyUI host** for the structural path — see
  `specs/120-comfyui-topology-viz/model-inventory.md` for the full list and cleanup guidance if
  disk space is needed back.

See `specs/120-comfyui-topology-viz/tasks.md` for the full implementation history and
`research.md` for the technical decisions and live findings behind this skill's design.
