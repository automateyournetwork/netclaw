# R04a verification — in progress

No completion or live client success is claimed yet. R04 remains accepted/merged/retired.

## Actual pre-fix reproduction (T003)

On source44cfe290, isolated actual VS Code1.109.0 activated the unchanged extension. The real `netclaw.addConnection` command accepted a friendly name and HTTPS address through native input UI, then displayed the host-local URL rejection. No profile was saved and no network connection was attempted. A reserved `.invalid` origin was deliberately sufficient because validation occurs before networking. Private receipt and screenshot: `roadmap-r04a-20261103/reproduction/`.

The initially selected installed editor1.108.0 refused extension engine^1.109; this separate compatibility failure is retained in editor.log. The supported cached editor is isolated; the owner's installed editor was not upgraded. CUA is unavailable in this session; actual native input automation used the existing Playwright/editor-harness approach.

## Source verification

- Python3.12: protected capability/handler consistency plus existing edge enrollment:7 passed. Protected Edge now advertises no legacy text/voice/media/recovery support, matching its refused Ask handler; local enrollment remains unchanged.
- Node24.19: existing protected production ingress/server, owner authorization and reference recovery suites:30 passed. No server route/authority broadening.

## Available native targets

Actual `xcrun devicectl list devices` found a paired available physical iPhone14,5. iOS26.5 iPhone17Pro simulator is also installed. Inventory is not execution qualification. Use an isolated qualification app identity to preserve existing phone data; no physical/simulator success claimed yet.

## Startup and limits

`pyats_list_devices` initialization failed because the configured pyATS HTTP runtime was unavailable. No device was accessed and no runtime upgrade was attempted. GAIT branch/checkout/kickoff succeeded. Source1.18.4, extension1.5.0 and Mobile1.0.3+6 unchanged. This is the fifth bounded optional pass; no further optional loop. R05 awaits human evidence acceptance; entire-roadmap release/publication hold remains.
