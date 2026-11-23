# Provider adapter contract — Spec200

Version1, planning-only. The implementation must pin the SDK and validate native
fixtures before live admission. Provider method shapes below come from official
sources linked in [research.md](../research.md); local contracts are separate.

## Supported lifecycle

| Step | Documented provider operation | Local requirement |
| --- | --- | --- |
| Create | `interactions.create({model:'genie-4',api_version:'v1beta'})` | Durable send marker and reservation first. Per-request `retries:{strategy:'none'}`; inspect actual SDK request options and assert one send under fault. |
| Connect | `interactions.connect(id,{transport:'websocket',api_version:'v1beta'},{timeout_ms:30000})` | Worker only; local10s first-frame/30s total deadline can stop earlier. One connection/receiver, no automatic resume. |
| Setup | `world_setup` event with `world_prompt.text` | Exactly once, frozen synthetic text; optional image excluded initially. Exact SDK event serialization captured in contract fixture. |
| Move | `user_action` with `action:key_down/key_up`, `input:key_w/key_a/key_s/key_d` or documented arrows | Allowlisted enum, key state deduplicated,<=10Hz; no arbitrary provider event passthrough. |
| Fictional change | `send(text)` or typed input text | One frozen event text,one send default. No prompts composed from device output. |
| Complete | `session.complete()` | Request only. Continue receive loop until actual terminal event. |
| Abort | `session.cancel()` | Best-effort request/close,not confirmed server termination. |
| Detach | SDK disconnect/detach | Never evidence of stopped generation/billing. |

This is a semantic binding, not a copied runnable SDK example. At P3 build
fixtures using the pinned SDK's actual types and serialization, including
constructor/API-key handling and exact `send` envelope. Do not invent a REST
world endpoint. Any incompatible SDK change stops qualification and updates this
contract before paid use. Reference the [official guide](https://aistudio.google.com/docs/genie)
and [pinned implementation](https://raw.githubusercontent.com/googleapis/js-genai/v3.6.1/src/_interactions_websocket.ts).

## Receive and media

`step.delta` with `delta.type=video` carries base64 JPEG in `delta.data`.
Decode/validate bounded bytes in worker and relay binary locally with sequence
and received timestamp.24fps/1280×720 are documented model output properties,
not a guaranteed local display rate. Audio deltas contain signed16LE stereo
PCM48kHz; optional,off in first proof. Unexpected media type/oversize becomes a
recorded contract error and stop request. No media travels in MCP messages.

Exactly one async receiver handles frames, provider errors and terminal events.
Persist `interaction.completed` with optional status/created/updated/usage
fields. Missing status/usage must remain missing. A terminal error fails the
world trial; missing usage leaves settlement open. Check actual events against
[completion schema](https://raw.githubusercontent.com/googleapis/js-genai/v3.6.1/src/gaos/models/interactions/live-interaction-completed-event.ts).

## Errors and reconciliation

- Invalid local input/credential absence before transport: refused/failed_pre_send.
- Auth/entitlement/quota response: preserve exact provider result, no retry or
  alternate account. Classify no-effect only with positive protocol evidence.
- Create timeout/reset/5xx after send: unknown, including when no provider ID
  arrives. Keep account hold and reservation; do not submit again.
- Lost stream: release input and request completion only if original channel
  still usable. If receipt cannot arrive, preserve unknown.
- Complete timeout5s: one best-effort cancel; no local success shortcut.
- GET original provider ID is a future qualified reconciliation capability;
  never recreate. Generic background cancel is not a qualified live kill switch.
- No resumption, durable scene graph, structured routing output or device tools.

Test transport fault behavior offline before any generation; later live evidence
must show actual complete receipt and usage. Official max120s bounds planning
exposure only; it cannot manufacture a receipt after a host/network failure.

## Credential and egress contract

Selected installation's private dotenv provides `GEMINI_API_KEY` to the worker
at launch. Validate nonempty presence without logging value. User may supply a
private local credential path through native setup; no secrets in chat, CLI
arguments, MCP arguments, browser or source. No automatic search/copy of another
claw's secrets. Pin Google API destination from SDK documentation; no caller-
provided base URL, proxy credentials, outbound file fetch or user webhooks.

Only frozen independent synthetic prompt/event/(optional synthetic image)
bytes cross this boundary. Record exact outbound hash before send. SDK debug
logging is disabled; redact authorization headers and provider tokens before
any diagnostic persistence. No private observation/identifier mapping is sent.

## Live packet prerequisite

Exact fixture hash,SDK/lockfile/runtime hashes,model/API version,account reference,
price snapshot,120s maximum exposure assumption,20s target/30s local deadline,
US$15 proposed reservation and stop/reconciliation limitations must be visible
before execution. No key in the packet. A change invalidates its review. One
allowance is for one attempt; a crash or ugly scene does not authorize another.


## Reviewed application source closure — pass30

The live packet binds26 repository files: every local JavaScript runtime module,
the package/lockfile, all served viewer assets and synthetic fixture assets.
Admission compares an explicit frozen manifest with the current runtime/asset
inventory before verifying byte hashes and loading the private credential.
Added modules/assets, missing files and source symlinks fail closed; a new exact
source review is required. Tests separately check relative import coverage and
mutate each formerly omitted viewer dependency in an isolated synthetic checkout.
Installed third-party dependency bytes are not attested by this source inventory;
the existing package lock/installation qualification remains required. This is
source integrity evidence, not authorization or live-world acceptance.
