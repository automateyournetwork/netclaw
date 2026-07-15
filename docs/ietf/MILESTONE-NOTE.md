# Milestone note (draft for John — Constitution XVII)

**Milestone:** NCFED written up as an IETF Internet-Draft (`draft-capobianco-ncfed-00`, Experimental).

**One paragraph (blog seed):**

> We wrote NetClaw's federation protocol down properly. NCFED — the wire that lets
> independently-operated NetClaws discover, invoke, and delegate to each other, and
> that coordinates one operator's Border and members — is now a full IETF
> Internet-Draft, `draft-capobianco-ncfed-00`. It documents exactly what runs today
> (nothing was changed to write it): the first-octet trick that lets NCFED share a
> single TCP port with BGP, the 13-octet handshake keyed by AS/router-id, the
> length-prefixed framing with its zero-length-frame heartbeat, the JSON-RPC layer
> that carries MCP tool calls and A2A task delegation, and the two trust models —
> mutual consent between operators (eN2N) and enrollment-token + trust-on-first-use
> pinning within a risk (iN2N). The Security Considerations are written the way a
> reviewer would attack it: port-sharing with BGP, TOFU, cleartext-by-default, agent
> delegation, and DoS — each named and mitigated honestly. The plan is to bring it to
> the IETF `agentproto` effort, where NCFED slots in not as a competitor to MCP or
> A2A but as the cross-operator federation/identity/transport layer that *carries*
> them — the multi-operator case the adjacent `draft-yan-a2a-device-agent-applicability`
> explicitly doesn't cover.

**Publish flow:** present to John; on approval, draft the full post via the WordPress
MCP (do not publish without review — Constitution XVII).
