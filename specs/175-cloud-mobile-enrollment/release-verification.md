# Spec175 release verification

## Scope and versions

On November5 the owner explicitly authorized packaging, commit/PR/merge, a source
patch, VS Code publication, changed Mobile app release, release notes, a throwaway
QR screenshot, a maintainer note, a website draft and return to main. This closes
R04b acceptance while preserving the full stop before R05. The broader cloud
roadmap rollout hold remains. The explicit patch request overrides the default
minor bump convention for this scoped enrollment usability release.

Versions: source **1.18.6**, extension **1.6.1**, Mobile **1.0.4 (7)**. Source main
was rechecked at209cba6f /1.18.5 before preparation. Components distribute through
separate GitHub, Marketplace and App Store lifecycles. Publication is being
verified; a prepared package is not a published release.

## Qualification

[Technical verification](verification.md) records four actual HUD/editor QR paths,
native simulator refusals, same-key reconnect, successful signed read/ACK and
cold/background recovery. The final successful operation had1attempt,2provider
calls,2inferences,1native MCP call and1NetBox HTTP request. Member/Border recovery
collectors agree;3historical rows remain unchanged. Cleanup restores101containers
and50networks and preserves all411new operation evidence files.

The iOS simulator uses a test-only CPU image decoder and Keychain P256 identity.
Physical camera/Secure Enclave, Android hardware and Windows/Linux editor
qualification remain open. No final merged-source redeployment is implied.

## Release artifacts and checks

Local release checks passed: release metadata1.18.6, all6release-helper tests,
162spec artifact checks (4legacy exceptions), fullHUD499/499 and extension194passed
with3explicit platform/opt-in skips and zero failures. TypeScript check passed.

The root environment's declaration reconciliation found an existing ignored
`mcp-servers/humanrail-mcp-server` checkout with an unbounded MCP dependency. That
checkout is absent from tracked source and was left untouched. All six required
surfaces passed from clean tracked6a8a0a2f source in the isolated app-release
worktree: catalog, dependencies, docs, meraki-ids, packages and portability. This
records the local installation warning separately from the release-source result.

A final HUD display regression was fixed before release: a response arriving
between timer ticks could initially display121seconds for a120second offer. The
issuance response now refreshes the display clock. The focused test fails on the
old code and passes with the fix; authoritative expiry behavior is unchanged.

Final archive digests, source commits, PR/CI/release URLs and App Store processing
state will be recorded here as observed. Website content is a local draft in the
separate modern_website repository; no website deployment is authorized.
