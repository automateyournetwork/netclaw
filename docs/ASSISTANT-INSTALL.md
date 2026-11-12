# Assistant-guided installation

Open **NetClaw: Set Up a New NetClaw**, then **NetClaw: Connect assistant for new setup**. Copilot uses the extension's setup MCP definition. Claude Code and Codex receive a native registration preview using the editor runtime, so setup does not depend on a Node executable in the terminal's PATH. Review the registration before running it. Keep the owning VS Code window open.

Use **NetClaw: Add setup skill to project** to place the stamped [shared install skill](../installer/assistant-skills/netclaw-install/SKILL.md) in the selected deployment project: `.github/skills` for Copilot, `.claude/skills` for Claude Code, or `.agents/skills` for Codex. A different existing skill is preserved and reported as a collision. This deployment skill is separate from NetClaw's development Spec Kit skills and operational skill inventory.

The eight closed setup tools observe, browse the catalog, draft, validate, explain, stage native review, request native secret entry and observe status. They do not apply, resume, clean up, send messages, return secret values or accept shell commands. Client auto-approval cannot authorize installation. Secret entry returns presence only; reports use structural redaction.

An assistant should state the existing-claw disclosure, ask only missing decisions in wizard order, and record assumptions/unresolved choices. Start with an [intent example](INTENT-PROMPTS.md). After validation, **stage** the current plan hash, inspect the visible wizard, and use its **Review installation** button yourself. Review always names each home, provider, service and source revision.

Without an active editor/broker, reopen setup. The assistant must not work around that boundary with terminal installation commands. This is an API authority boundary, not an OS sandbox for other tools the assistant already possesses. Actual three-client UI qualification remains separate from the passing protocol/transcript fixtures.

## Static or dynamic pyATS inventory (Spec160)

Select pyATS, then choose **Testbed mode & sources** in the VS Code setup wizard
or static/dynamic in the terminal plan. Existing-runtime `scripts/setup.sh --testbed-only`
configures the selected home. Dynamic mode stores selected sources privately and
creates no dummy YAML; setup performs no inventory fetch or device operation.
Source service credentials and device login references remain separate.

The managed MCP requires scoped, complete, fresh records, then actual schema and
credential validation before explicit activation. Inventory belongs to one MCP
process; separate one-shot calls do not share it. Use a persistent client or the
bounded session helper. The HUD static editor and collector grants are separate.
Readiness reports source access, candidate, activation and execution independently.
See [Dynamic testbeds](DYNAMIC-TESTBEDS.md) for all source contracts, unavailable
reader gaps, restart behavior and feasible qualification. Existing runtimes require
an explicit reviewed component upgrade; source selection alone does not install it.

## Deploying to GCP

The installer, this wizard flow and the Claw Plan flow can place a Border or Member in your own GCP project
(`NetClaw: Deploy a Border or Member to GCP`, or `scripts/netclaw-gcp.py`). See [NetClaw in GCP](NETCLAW-IN-GCP.md).
GCP deployments are **NOT behind any authentication**: keep every URL private; users, SSO and RBAC are a much later
roadmap phase (R15-R17).

An assistant may explain GCP topologies and prepare the `netclaw-gcp.py plan` command, but must show the no-authentication warning first and must never pass `--ack-no-auth`, `--confirm-cost` or `--confirm-list-sha256` on the user's behalf; those are the user's decisions.
