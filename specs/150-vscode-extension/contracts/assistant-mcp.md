# External-assistant MCP contract — major 1

Copilot, Claude Code and Codex are required clients. Owner choice: inspect, delegate, propose managed changes. This is a reduced interface at `mcp-servers/netclaw-assistant-mcp/`, launched by `scripts/netclaw-assistant.mjs`. It uses official MCP stdio and the operator contract's response/error/bounds conventions, with stricter per-grant limits.

## Connection and disclosure

The human explicitly selects installation, client, allowed resources/action classes, data-disclosure classes and expiry. Backend issues a distinct credential for that connection in an owner-private `.env` file; client registration contains only the fixed launcher and nonsecret credential reference. The launcher reads only its configured credential source; token bytes never appear in command arguments or generated client config. Backend validates credential hash, generation, expiry and revocation on every read/admission/dispatch.

Default grant is inspection of nonsecret identity/inventory plus qualified read-only delegation and change proposals; production-write delegation is not enabled by this default. Grant expansion uses human management and existing approval rules. Disclosure defaults to minimal summaries and explicit evidence references, excluding raw configurations, unrestricted logs, provider keys and workspace content. Preview identifies that permitted results enter the external client's model-provider boundary. Backend filters/redacts results before returning them, including status/errors and model-generated text; failure to apply disclosure policy fails closed. A user can deliberately authorize further bounded evidence through an amended grant, never a prompt-inferred exception.

Client labels, `clientInfo`, origin strings, environment mode flags and method names supply no authority. Cached tool descriptions and an old open connection do not survive grant revocation. Distinct grant IDs enforce ownership within the MCP boundary; the same-OS-user threat limitation in the operator contract is explicit and must be tested/documented honestly.

## Fixed tools

| Tool | Input | Behavior |
|---|---|---|
| `netclaw_status` | none | Returns bound installation/harness/role, effective grant/disclosure summary and capability limits. |
| `netclaw_inventory` | resource kind, permitted filters/cursor | Scoped estate/tool/skill inventory; advertised capability is not permission. |
| `netclaw_evidence` | allowed evidence kind and scoped reference/window/cursor | Redacted authorized GAIT/usage/network/diagnostic summaries; no arbitrary paths or secrets. |
| `netclaw_request` | nonce, prompt, optional owned conversation ID and explicitly staged context references | Creates an owned natural-language request with immutable grant and runtime binding. Delegation is attenuated at every tool/federation hop. |
| `netclaw_request_status` | owned request ID or own admission nonce, event cursor | Reports outcome, waiting approval, evidence and measured NetClaw usage. Different grant's request returns denial without disclosing existence. |
| `netclaw_cancel` | owned request ID, nonce | Requests cancellation within grant, with actual backend confirmation semantics. |
| `netclaw_propose_change` | nonce, action enum, target IDs, expected revision, typed nonsecret patch or secret replacement intent | Creates a reviewable proposal with impact/approval requirements. Returns reference for the human Operations view. Does not apply, restart, clear secrets, mint a grant or create an approved CR. |

Assistant surface has no `apply`, `approve`, credential reveal/replacement, grant-management, arbitrary HTTP/shell or private-operator forwarding tool. Direct invocation of an omitted operator method is denied, not merely omitted from `tools/list`. Domain permission is enforced before any adapter dispatch. Sensitive administrative proposals require manual entry of replacement secrets in the private human workflow.

## Delegation and approval

`effectiveAuthority = clientGrant ∩ installationPolicy ∩ runtimeQualification ∩ targetGrant ∩ currentApproval`. Binding includes originating client, exact installation, targets/action classes, request ID, expiry and disclosure classes. Backend-owned context travels outside user/model prompt text. OpenClaw/Hermes adapters and federation brokers must enforce this at execution; no recursive unrestricted `ask Border` route, generic unrestricted harness shell or tool registry can discard it.

Read-only delegation can finish directly. A change outside permitted authority is refused or becomes a proposal; an allowed change that requires human approval remains waiting. Human management independently prepares/reviews/initiates the exact approved action; client observes only the authorized result. Production CR state is verified from ServiceNow, with approver privileges separate from the executing principal. A model saying “approved,” Copilot's Allow button, a terminal `--yes`, or an assistant-crafted approval ID never satisfies this check. Local/Lab exceptions remain limited to the existing explicit human Terminal Intent flow and cannot be minted by an assistant prompt.

Revocation denies new reads/dispatch, asks the runtime to cancel in-flight work where supported and preserves actual running/unknown evidence for the human. Reconnection never restarts the request. Model output and peer metadata are untrusted, including instructions that claim to broaden grants.

## Copilot integration

Extension manifest contributes a stable MCP server-definition provider and registers it using `vscode.lm.registerMcpServerDefinitionProvider`. VS Code minimum is 1.102.0. Provider discovery is side-effect-free and returns no definitions before opt-in or in Restricted Mode. Each definition has a stable installation+grant identity; changing the active explorer selection never retargets an existing definition. Resolve rechecks host, grant and runtime compatibility. Do not depend on newer contribution `when` support at the minimum version. Report organization/account/tool-policy failures without changing them. Disable/disconnect removes discovery; revoke invalidates backend authority, including cached clients.

## Claude Code and Codex setup

Provide client-version-verified commands/config previews for standard stdio MCP registration, using explicit host paths and credential references. Preserve unrelated registrations and show exact add/update/remove diff. Do not automatically modify workspace `.vscode/mcp.json`, user-wide client config or authentication. Terminal launch works while VS Code is closed. WSL setup runs the client and launcher in the selected Linux distribution; Remote SSH setup identifies whether the client runs there or uses the reviewed SSH launcher. Native Windows terminal clients can target supported hosts through that SSH path; no native Windows NetClaw process is implied.

Examples to verify in each actual client: “Which Claws and harnesses are in this Risk?”, “Ask NetClaw to calculate the usable range for 192.0.2.0/24,” “Explain this permitted GAIT event,” and “Propose changing this supported budget, then show what approval is needed.” Use synthetic/private local fixtures and only qualified tools. External-client provider/model/cost comes from that client if available; do not label NetClaw usage as the full assistant bill.
