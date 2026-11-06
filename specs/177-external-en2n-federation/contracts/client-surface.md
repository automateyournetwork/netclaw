# R06 Client Surface

## Discovery and boundary

`/api/runtime` explicitly advertises versioned ordinary federation, installation UUID, Border role, workspace features and truthful open-lab attribution. Ordinary mode has no protectedProfile/protectedOperations/protectedProduction claim. Identity/mode changes close the connection. Existing protected schema remains unchanged.

Exact ordinary capability: `capabilities.externalFederation =
{schema:1, execution:"ordinary", peerChat:true}` alongside the existing
`remoteHud:{schema:1,features:[...]}`. Cloud discovery accepts either the complete
existing protected capability set or this exact ordinary capability, never a
mixture. A protected profile may additionally advertise peer chat only after
separate verified integration; R06 does not grant that capability to it.

The private cloud edge uses an explicitly selected
`mode:"ordinary-federation"` configuration with an exact loopback `daemonUrl`.
It validates owned installation/role binding in private `ordinary-cloud.json` (schemaVersion1, installationId, role:border, access.mode:open-lab), absence of a protected profile in
the fresh ordinary home, the configured workspace backend identity and private
asset/configuration hashes. The existing protected config shape remains exact.
No profile is chosen merely from a missing credential or failed protected check.

Trusted exact HTTPS origin, bounded bodies, native installation binding, no cookie/ticket login and explicit route allowlist. Daemon/admin/BGP config/generic proxy/shell/provider/MCP stay private. Native consent/export controls are not published.

## Peer workflow

Existing POST `/api/n2n/chat` requires an advertised peer-chat capability, bounded exact peer/text/optional session fields and selected permitted peer. Preserve peer-owned context, source/remote-untrusted attribution and aligned deadlines. No retry on timeout/lost response.

Bounded peer projection retains skills/MCP tools/chat/freshness/version/state/in-flight fields needed by existing views, never private paths/keys/member topology. VS Code keeps Name+URL normal workspace, existing picker/chat, and hides unavailable protected operations. Local lifecycle stays local.

## Mobile

Existing scanner/device identity/enrollment/WSS reused. Ordinary enrollment opens ordinary conversation; protected enrollment retains its own operation screen and guards. No silent mode conversion.

Ask Border admission/status/result/push retains original request. Bounded external peer/request/task provenance comes from actual federation activity, never model prose. Persist through conversation storage/reconnect; missing source remains unknown. Enrolled device remains local requester.

Actual browser/editor/iPhone simulator acceptance and unchanged effect counts after restart are required, separate from fixtures.
