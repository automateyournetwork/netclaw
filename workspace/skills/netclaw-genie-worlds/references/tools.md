# Execution controls

Tools are on `genie-worlds-mcp`; clients may prefix names with that server name.
All inputs are closed. UUIDs are generated and retained by the caller before
mutating requests. Source/model/path/key/duration overrides are not accepted.

| Tool | Required input | Meaning |
| --- | --- | --- |
| `genie_world_prepare` | `request_id`; exactly one `synthetic_fixture_id` or `private_snapshot_ref` | Local draft and opaque `projection_ref`; no provider call. |
| `genie_world_start` | `request_id`, `projection_ref`, `review_ref` | Consume existing exact review, using the shared ledger/worker. |
| `genie_world_status` | `operation_id` | Retained state, usage, terminal confirmation and `control_requests`. |
| `genie_world_event` | `request_id`, `operation_id`, `event_id` | Fixed event returned by synthetic preparation; human viewer readiness required. |
| `genie_world_stop` | `request_id`, `operation_id` | Backend completion request; read status for actual outcome. |
| `genie_world_evidence` | `operation_id` | Artifact hashes, recording failures, session evidence; no raw media or private facts. |

Start uses its request UUID as the operation UUID. Identical duplicate requests
retain the original result; conflicting payloads are refused. For events/stops,
`control_requests` records `pending`, `accepted`, `refused` or `unknown`. These
describe handling of the command, not visual success, provider termination or cost.
`event_state:sent` is a transport observation only.

On a lost response, use original status/evidence. Do not automatically resend.
An `unknown` session or unreconciled usage blocks later admission. No tool clears
these holds. `terminal_confirmed` and `usage_state` answer different questions.
`live_world_proven:false` and `acceptance:null` must never be rewritten by the agent.

The current synthetic policy targets 20 seconds, a 30-second deadline from send,
10-second first-frame timeout, 3-second viewer-loss deadline and 5-second terminal
grace. Google currently documents a 120-second service maximum. The one-attempt
US$15 reservation is a conservative contingency, not a hard provider billing cap.
Review current prices and actual packet authority before any paid start.
