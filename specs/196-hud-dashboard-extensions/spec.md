# Optional locally installed HUD views

**Status** Proposed for maintainer discussion.

## User scenarios

1. An operator installs a trusted local UI package and chooses to enable its view on their local NetClaw dashboard. For example, a downstream monitoring project maintains its own timeline and drill-down views. Today that project must edit NetClaw's navigation and React component tree to integrate them.
2. A user upgrades NetClaw without enabling an extension. Existing dashboard navigation, built-in Convergence evidence, chat and classic HUD keep working with the stock installation.
3. An operator removes or disables a view. A bookmark to it leads to an unavailable view or the normal dashboard. Other views stay usable if a package fails to load.

## Proposed requirements

- The operator explicitly selects trusted local packages when building the dashboard. Each supplies a stable namespaced ID, display label and dashboard component. Reject duplicate IDs, collisions with built-ins, invalid entry paths and malformed declarations. Use the same validated IDs for navigation and deep links.
- Show enabled views only in an eligible local owner session. Re-evaluate eligibility on profile, installation and session changes. Deny stale deep links and clear extension state on an installation change. Preview, protected operations, remote workspaces and public or read-only labs retain their existing exposure.
- Load the component on navigation. Report a failed extension within that view. Removing a package and rebuilding must restore a stock installation. The browser bundle must contain only explicitly selected extension code. The selection is an administrative trust decision because installed JavaScript runs in the HUD origin.
- Keep server-held credentials, owner checks and installation/site enforcement on the service that owns each data route. Phase one supplies a browser view hook. Any new backend data or write route needs its own access contract and review.

## Acceptance

A synthetic package appears once, opens with keyboard navigation and a deep link, and survives a page refresh. With no configured package the existing navigation and API are identical. Rebuilding without the package removes its code and route. Tests cover collisions, broken entry points, a component that throws, profile restrictions and switching installations. Existing built-in Convergence and classic HUD tests continue to pass.
