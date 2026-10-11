# Publishing NetClaw for VS Code

Publisher: `NetClaw`, reported created by the owner. Extension identity:
`NetClaw.netclaw`. Browser sign-in to the publisher portal does not authenticate
the local publishing CLI. No extension has been published by this implementation.

The locked `@vscode/vsce` 4.0.0 dependency provides both a CLI and a Node API
(`createVSIX`, `listFiles`, `publishVSIX`). Automation is supported. The current
workflow builds reviewable candidate artifacts and has no publishing step.

## Local authentication chosen by the owner

Using the same Microsoft account that owns the publisher, create an Azure DevOps
organization if needed. For current PAT authentication, create a short-lived token
with **Marketplace → Manage** and **All accessible organizations**. In your own
interactive terminal, from the source checkout:

```bash
npm --prefix extensions/netclaw-vscode run publisher:login
npm --prefix extensions/netclaw-vscode run publisher:verify
```

Enter the token only at the hidden local prompt. Do not put it in chat, Git, a
command argument, the extension manifest or a handoff document. `vsce` uses the
system credential store when available; if it reports a clear-text fallback,
cancel that login and configure an available local credential store or Entra
authentication instead. Authentication can be done on the eventual publishing
host after WSL qualification returns.

Microsoft's current documentation retires global Azure DevOps PATs on
**December 1, 2026** and recommends Microsoft Entra ID workload identity for durable
automation. That setup additionally needs an authorized Entra identity and publisher
membership; the personal Microsoft publisher account alone does not create it.
Recheck the supported method at release time. See the official
[publishing and authentication guide](https://code.visualstudio.com/api/working-with-extensions/publishing-extension).

## Release review

Before publication, finish the remaining Spec150 features, real WSL and other
platform rows, named-client tests, package install/update/preservation checks,
Spec149 dependencies and requirement traceability. Record the exact backend
source, extension version, VSIX SHA-256 and sanitized qualification evidence.

The owner returns the WSL results to the Mac implementation session for review
and finalization. Publish only that reviewed artifact, without silently rebuilding
it under an already approved version. Public Marketplace completion requires an
observed clean Marketplace installation and connection, not just a successful
upload command.
