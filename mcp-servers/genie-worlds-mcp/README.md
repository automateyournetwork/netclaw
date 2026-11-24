# Genie worlds MCP

Six stdio tools over the existing loopback manager, using official Python MCP
SDK 2.3.0. Run `server.py` in an isolated Python 3.12 environment with the pinned
requirement. Set `NETCLAW_GENIE_CONTROL_FILE` to the manager's owner-private
`mcp-control.json`. The process receives no Google key or device credential.

The manager writes this separate control capability on startup. It allows only
prepare/start/status/event/stop/evidence. It cannot create reviews, read snapshot
contents, bootstrap a browser or connect to the viewer WebSocket. Backend source,
state and review controls remain the authority. This is application isolation,
not OS isolation from another process running as the same user.

`genie_world_prepare` accepts one registered synthetic fixture or private snapshot
reference. Private preparation returns only bounded metadata; private-derived
world drafts remain local unless an exact operator-pinned grant authorizes the selected projection. The first hosted
qualification uses the independent synthetic fixture. A prepared draft or
successful MCP call does not establish Google generation or Risk enrollment.

See the [workflow skill](../../workspace/skills/netclaw-genie-worlds/SKILL.md) and
[actual production evidence](../../specs/200-genie-network-worlds/production-recordings.md).

Install with `scripts/install.sh --add genie-worlds`; configure through `scripts/setup.sh` or the source-backed VS Code wizard. See [complete setup guide](../../docs/GENIE-WORLDS.md).
