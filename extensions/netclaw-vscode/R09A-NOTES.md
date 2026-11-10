# R09A (spec 183) — VS Code notes and G12 disposition

## What changed

- New read-only command **NetClaw: Show Node Posture** (`netclaw.showNodePosture`, contributed in `package.json`, registered in `src/extension.ts`).
- New client `src/client/posture.ts`: `fetchNodePosture`, `validatePosture`, `formatPosture`.
- Tests: `test/posture.test.mjs` (5 tests).
- No version bump, no packaging, nothing published.

## How it behaves

- Applies only to a **cloud Border** connection (`mode === "remote-border"`); otherwise it says so.
- Reads `GET <origin>/api/hud/posture` on the already verified HTTPS origin (the ingress serves it itself; see `labs/ha/hud_ingress_r09.mjs` and `specs/183-openshell-defenseclaw-gcp/contracts/node-posture.md`). Same fetch hygiene as the owner client: no redirects, no cache, no cookies, size cap (16 KiB), JSON only.
- Validates the payload strictly (exact keys, no secret-looking text, components outside the sandbox must carry a disposition and must not claim enforcement). A malformed or oversize payload is ignored with a clear message.
- Shows a markdown summary: sandbox name/phase/policy version and hash/Landlock mode, components inside and outside the sandbox with dispositions, guard mode/state/fail-closed/last block, and the observation time. It states that this is the node's self-report and **not proof of enforcement**; components outside the sandbox are never described as OpenShell-enforced.
- A Border without a posture (older builds) gives a 404 message that nothing is implied about its confinement.
- The command is registered directly, not through the cloud-command allow-list in `src/views/owner.ts` (unchanged), because it is a read of the verified origin and that file was outside this change's scope.

## G12 disposition (VS Code impact)

**Affected, small, additive.** Connecting to a sandboxed Border works exactly as before (same URLs, same cluster trust, same region/role display). The one new capability is the posture view above.

**How a guard-blocked request is presented (reused, not new):**
- Protected operations: the existing owner/operation flow shows refusal and failure states and results through `presentOperationDocument` / `operationEvidence`; DefenseClaw does not change that contract.
- Workspace chat: a refused or blocked model request surfaces through the existing HUD error path (`HudError`: "NetClaw refused <route> (HTTP n). <scrubbed reason>"), truncated and scrubbed.
- No new client UI was added for blocked requests.

## Verified vs not verified

Verified (automated): posture validation (valid and 16 invalid shapes), fetch behavior against a loopback server (200, 404, 503, redirect, cookie, wrong content type, bad JSON, oversize, contract mismatch, unreachable), formatting, that the command is declared and registered directly with its remote-border guard, and that the cloud allow-list is unchanged. `tsc --noEmit` and `npm run build` pass; `npm test` shows 215 passing, 3 skipped and the same 2 managed-launcher failures that already fail on pristine `HEAD`.

Not verified: the command running inside a real VS Code window against a live sandboxed Border (no editor host was run); how DefenseClaw's block message actually reads in VS Code chat; the Mobile app (G13 is a separate disposition, task T036).
