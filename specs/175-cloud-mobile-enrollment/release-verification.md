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
separate GitHub, Marketplace and App Store lifecycles. The observed outcomes below distinguish published artifacts, Apple review
and the source tag; a prepared package is not a published release.

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

Exact archive digests, source commits, PR/CI URLs and observed store states are
recorded below. Website content is a local draft in the
separate modern_website repository; no website deployment is authorized.


The actual HUD screenshot is [docs/images/mobile-qr-enrollment.png](../../docs/images/mobile-qr-enrollment.png),
SHA256 `9f68a61e6196d4af290cf90de19625f3adefadaf61393663954057e521e2d6f6`.
It came from the disposable local fixture. Authority reported expired at
2026-11-05T15:34:08Z; no device enrolled. Private safety receipt
`surfaces/public-copy-final/expired-safety.json` has SHA256
`a1331b27886258b40127ab439d59b42ff228e5e75fb080e651a983e7a6075ae4`.
Only the owned screenshot services were stopped; ports13179/13305/13306/13443
were verified closed. The article is seeded with `draft:true` at
`../modern_website/content/articles/2026-11-05-netclaw-mobile-qr-enrollment.md`,
with its matching `public/images/netclaw-mobile-qr/hud-mobile-enrollment.png`.
Existing unrelated website changes are preserved. No website deployment occurred.


## Integration and exact artifact provenance

[PR328](https://github.com/automateyournetwork/netclaw/pull/328) merged at
2026-11-05T15:57:47Z as `bdb77bfbeb227693d7cd124fa87c461e865bb5b2` after all40checks
passed. The checked head is `04f9ec4237fadd2d834db50881797b86f4752ec9`.
[Mobile CI](https://github.com/automateyournetwork/netclaw/actions/runs/42057126581)
passed Flutter analysis/tests and actual iOS/Watch simulator builds.
[MCP contracts](https://github.com/automateyournetwork/netclaw/actions/runs/42057126537),
[HUD](https://github.com/automateyournetwork/netclaw/actions/runs/42057126559),
[extension](https://github.com/automateyournetwork/netclaw/actions/runs/42057126590),
[convergence](https://github.com/automateyournetwork/netclaw/actions/runs/42057126440)
and [release metadata](https://github.com/automateyournetwork/netclaw/actions/runs/42057126601)
also passed.

The VSIX was packaged from clean checked head04f9ec42, version1.6.1,
4,663,980bytes,71ZIP entries,64runtime/resource files verified. SHA256:
`08097193b666e574a2e739152b103dc272c35a2062d6f9ade274c37522c71338`.
The exact archive loaded in native Code1.145 with a clone of the existing profile;
Overview and enabled Mobile generation passed with no new QR or workload. The
normal installation was updated to that exact archive. Two settings files, five
NetClaw databases, five state files,17other extensions/registry and the original
window/terminal processes were preserved. The original extension host was not
restarted; installed files do not prove which code an already-running host uses.

Mobile1.0.4(7) was built from clean `6a8a0a2f027a7efedec996493c42e21ef86918a7`,
production `lib/main.dart`, real retained Firebase configuration and no test
harness assets/defines. All484Flutter tests, analysis and production iOS build
passed. Five app/extension bundles share1.0.4(7), with verified distribution
signatures/profiles. The24,586,732byteIPA has SHA256
`7e8582066526cae1cd2c48e4573d34c1c3d5b60f9e054e53e9a73807a9079069`.
Apple validation and one upload succeeded; delivery/build
`0f2cc475-606c-491a-8e30-aa67015855d4` processed VALID and APP_STORE_ELIGIBLE
with zero processing errors/warnings. The local uploader’s resume-path warning
is retained alongside authoritative delivery success and processing evidence.

Root verified the merged extension/HUD trees equal the VSIX source and the
merged Mobile/archive-script trees equal the IPA source. Final publication
records change documentation only, not those product trees. Private signed
packages, credentials and authority exports remain outside source.


## App Store submission

Version1.0.4(7) was submitted once at2026-11-05T16:00:35Z. Both authoritative
version and review states are **WAITING_FOR_REVIEW**, release type AFTER_APPROVAL;
review `78863eef-0ab9-439b-b6f4-91a582bfa468` refers to version
`cc0b884a-a33a-4001-a1ce-736cfc5b21fb` and the exact validated build above.
[Sanitized release receipt](evidence/mobile-release-1.0.4.json).

The [App Store listing](https://apps.apple.com/us/app/netclaw/id6800859524) remains
public1.0.2 /READY_FOR_SALE at this checkpoint. Apple approval and public1.0.4
availability are pending; submission is not a public release. Existing contact
details and all15screenshots were preserved. Review instructions now describe
HUD/editor QR enrollment and capability-dependent views, with no fabricated
review endpoint or owner-pilot access. Legacy username/password fields were
cleared because they do not enroll this companion app. Physical-device
qualification remains separate. No action or approval from the owner is pending
for this submitted version; Apple controls the review outcome.


## Marketplace publication

Extension **1.6.1 is published and publicly available**. The reviewed archive was
submitted once at2026-11-05T15:58:40Z after PR328 merged; no rebuild or duplicate
submission occurred. Marketplace initially queued validation. At16:08:08Z the
anonymous official gallery reported validated latest1.6.1, the item page returned
HTTP200 and an independent versioned download succeeded. The decoded archive’s
SHA256 equals the reviewed VSIX exactly, with all71files byte-identical and no
server-added files. [Public Marketplace page](https://marketplace.visualstudio.com/items?itemName=NetClaw.netclaw)
· [versioned download](https://marketplace.visualstudio.com/_apis/public/gallery/publishers/NetClaw/vsextensions/netclaw/1.6.1/vspackage)
· [verification receipt](evidence/marketplace-1.6.1.json).

## Source release and handoff

The source release is [v1.18.6](https://github.com/automateyournetwork/netclaw/releases/tag/v1.18.6).
The final documentation record is merged and its exact-main checks must pass
before creating the annotated tag; the tag’s metadata check must pass before
publishing. The release attaches the verified VSIX, SHA256SUMS and a final
[publication receipt](https://github.com/automateyournetwork/netclaw/releases/download/v1.18.6/release-verification.json)
containing the observed tag target, CI and publication metadata. That receipt is
created after publication, avoiding a self-referential commit claim in this file.

The owner receives the source/Marketplace/App Store links,
[maintainer note](../../docs/communications/2026-11-05-mobile-qr-maintainers.md),
[HUD screenshot](../../docs/images/mobile-qr-enrollment.png) and local website
draft. Website import/timeline validation passed in an isolated copy; `draft:true`
keeps this article out of public posts/search. Existing unrelated website edits
remain untouched. No website deployment or external announcement was performed.
GAIT and daily memory retain the final publication trail. R04b is30/30; stop before
R05. Apple’s pending review does not start or authorize another roadmap stage.
