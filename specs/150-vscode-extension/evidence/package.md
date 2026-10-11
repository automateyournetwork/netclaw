# VSIX development evidence — 2026-10-10

This is a private development candidate, not a Marketplace release. T070 remains
unchecked because its full platform and running-backend preservation gates are
not closed by these Mac fixture checks.

## Artifact inspected

- Identity: `NetClaw.netclaw`, version `0.1.0`.
- Source: `99fe7528eb68da3f3d67ae1c688fcc80d880f951`.
- File: `extensions/netclaw-vscode/netclaw-0.1.0.vsix` (ignored build output).
- Bytes: `2769087`.
- SHA-256: `2235cbf13b5d1821f103dd95058625a99c55042c8fc9c2868178dc61a627db0b`.
- ZIP: 24 entries (22 explicit extension files plus generated VSIX manifest and
  content types). Source, backend implementation, dependencies, `.env`, private
  state and test artifacts are excluded. README image/privacy URLs resolve to
  the source commit's extension subdirectory.

`npm --prefix extensions/netclaw-vscode run test:package` checks the exact
allowlist with planted synthetic secret/state files. It passed. The actual ZIP
was also inspected for forbidden paths and source-pinned documentation links.

## Actual editor lifecycle

`node tests/vscode/package-acceptance.mjs` uses the downloaded VS Code 1.102.0
macOS arm64 executable with its own user-data/extensions directories and a
separate test-driver extension. It asserts that NetClaw is loaded from the
installed VSIX path, rather than the source development extension.

The initial artifact at source `9b4a0ffcda18eaf750d3befa85f5e1387cd25616`, SHA-256
`1fdc1e611c93342b0d1af7ad943f4f4688bdbb04a0d9981468590c9a91efda17`, passed clean
installation, upgrade, disable, uninstall and rollback. The prior version 0.0.1
is an explicitly constructed candidate fixture, not an invented published
release. Its saved profile/installation binding survived upgrade and reinstall;
the synthetic backend config and environment remained byte-identical.

A later repeat hit an abort in the minimum editor CLI during uninstall. It is
retained as a failed run. The separate sequential rerun passed all five phases
for the exact artifact listed above, including retained profiles and unchanged
backend configuration. No extension assertion failure was observed before that CLI failure.
The cause of the native editor crash has not been established.

## Limits

These checks do not demonstrate real Windows/WSL, Remote SSH, a running owner
installation or a public Marketplace install. The scripted Linux editor runner
is not Windows desktop's WSL extension host. Keep those acceptance rows open.
No publisher authentication or publication command was executed.
