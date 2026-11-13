# Implementation plan

Seek maintainer agreement on the local, build-time extension model and profile boundary first. A downstream application owns its own component and release. NetClaw owns dashboard navigation, access decisions, load errors and the packaging contract.

1. Define the explicit build input, package manifest and stable ID rules. Resolve entries within the selected local package, handle symlinks deterministically and reject invalid configuration with an actionable build error. Produce an empty registry for a stock build.
2. Integrate that registry into React navigation and route resolution at the point where the host already has its runtime and installation. Use the host's existing view lifecycle and an error boundary around each extension. Use a synthetic read-only fixture as the example.
3. Verify stock and extended builds. Exercise local owner, unsupported profile, direct-link, navigation failure, installation change and uninstall paths. Compare stock API exposure before and after. Document install, rebuild and removal.

A subsequent design would be required for scoped host-side services, classic HUD integration or another supported client. Operational migration of any downstream dashboard depends on its own data access and parity checks.
