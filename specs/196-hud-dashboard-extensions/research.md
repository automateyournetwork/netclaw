# Existing integration points

The [React dashboard](../../ui/netclaw-visual/src/dashboard/Dashboard.jsx) filters built-in views by runtime capability and profile and renders each view explicitly. A downstream dashboard component therefore needs a NetClaw source edit today. Classic HUD startup uses [a separate entry point](../../ui/netclaw-visual/src/main.js). A browser-only dashboard extension can leave classic startup alone.

The [built-in Convergence service](../../ui/netclaw-visual/src/hud-server/convergence.js) validates the request, owner binding and installation and limits the site's data access. A downstream view does not inherit authority to mount a token-bearing catch-all proxy. The [earlier retained-evidence design](../161-convergence-proposal/plan.md) describes a narrower built-in workflow. This proposal gives other locally installed views their own names without displacing it.

Build-time selection fits the existing Vite build and makes the operator's trust decision explicit. Runtime URL imports add browser-origin code loading, offline availability and provenance concerns. A generic Express plug-in interface also grants server privileges well beyond rendering a view. Maintainer review should decide whether the smaller browser integration belongs in the HUD.
