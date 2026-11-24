> **Current resumption — 2026-11-24:** Spec200 and all Byrn PRs are merged. The primary `/Users/john.capobianco/netclaw` checkout is back on198 with current main incorporated. Read [Git resumption](git-resumption-20261124.md) first, then the latest r10k/r10l verification finding; the older Wi-Fi hypothesis below is superseded. Live acceptance, the separate cloud budget and publication limits remain open.

# Spec 198 / R10: prompt to start the session that closes the last three live gaps

**2026-11-22 update:** This is the deferred Azure continuation, not the current
task. John authorized a commit/push checkpoint and inserted Spec200 Genie before
resuming198, followed by199AWS. Read `checkpoint-20261122.md` first. Historical
statements below that source is uncommitted or push is unauthorized are
superseded by that scoped checkpoint authorization. Live acceptance, cloud
spending boundaries and publication holds remain.

Paste everything below the line into a fresh Claude Code session in /Users/john.capobianco/netclaw (branch 198-azure-multicloud-ha).

---

You are resuming spec 198 (R10 Azure + multi-cloud, branch `198-azure-multicloud-ha`, saved as an incomplete source checkpoint, not merged or released). Read first, in this order: `specs/198-azure-multicloud-ha/checkpoint-20261122.md`, `handoff.md` (last section), `verification.md` (last three sections), `contracts/cross-cloud-federation.md` (including "Live findings" and the offline qualified-code table), `mesh-design.md`, and the memory file `r10c-live-run.md`. Do not re-derive what they already establish.

**State:** everything is torn down and verified empty (Azure, GCP, DNS, watchdogs, members); ledger est. USD 13.06 including a USD 5 reserve (about USD 8 real), owner cap USD 25, pause at USD 15 (the ledger counts the reserve, so a new run needs the owner's explicit OK to pass the pause: ask once, up front). Hosted Sonnet only, no Ollama. Offline work, docs, the VS Code connection Rename/Remove menus, the federation code (`ha/federation.py`, 29 tests) and the nearest-Border admission change (`ha/internal.py`, `ha/member.py`, 3 tests; HA/protected suites 1481 pass) are done offline. Qualified-code changes are listed for owner review and must not be merged/pushed/published without approval; the release gate holds.

**The three open live gaps to close (this is the whole job):**
1. An operation entered on an AZURE Border completes on a GCP member (durable ACK). Azure to GCP relays and is authorized in the GCP ledger, but members refused (`agent_produced_no_tool_evidence`).
2. Cross-group operations (both directions) through EVERY follower Border, not just leaders. The union catalog from all six Borders is already proven; execution through followers is not.
3. A completed GCP operation after a real leader change (Azure's is proven: epoch 33 to 85).
Then rerun the local-plus-cross matrix across all six Borders with durable ACKs, record it, tear everything down, and confirm.

**Known causes and rules from the last runs (do not relearn):**
- The operator's unstable Wi-Fi, laptop sleep (kills the member processes) and Mac memory pressure made hosted-model calls fail. REQUIRE from the owner before launching: stable (ideally wired) network, Mac awake and plugged in for the whole run; do not run more than about 8 members per group; restart Docker Desktop first and verify a container can reach api.anthropic.com in under a second.
- Members admit through one Border: the lowest node id (old) or nearest (new offline change, built into a fresh prepare because the source manifest is signed). Verify the nearest-Border change live; if admissions still time out, measure before changing anything else.
- Each failed or refused operation permanently fences its member (enroll spares; 8+ NetBox plus 2 subnet per group). Successful members can be reused. Warm demo.netbox.dev before NetBox operations (`r10_ops.py --warm-netbox`).
- Ledger projection: use `R10_HOURS=5` (reserved window) so the projection stays honest; the watchdogs use the same window. Never lower a cap to dodge the pause; ask.
- Azure sizes/regions/key: `Standard_D2as_v7` in canadacentral/eastus2/swedencentral, `AZ_SSH_KEY=~/.ssh/nc198_azure`; GCP `e2-standard-2` in northamerica-northeast1/europe-west1/asia-southeast1, project netclaw-506315. ACME contact is the established one used in earlier runs (never the owner's work email, never in outside calls). Credentials live in `~/.openclaw/.env` (GoDaddy, NetBox, new NetBox key already stored) and repo `.env` (Anthropic); never print them.

**How to run (all scripted):** `az login` and `gcloud auth login` first; `R10_GO=mesh AZ_RUN=<id>-YYYYMMDD GC_RUN=<id>-YYYYMMDD R10_HOURS=5 R10_GUARD_DIR=$HOME/.local/share/netclaw/r10-run-r10d-20261115/gen2/guard R10_ACME_EMAIL=<established contact> bash scripts/ha-r10-mesh-up.sh` (builds both groups, members, firewalls, federation; prints six HUD URLs); `labs/ha/r10_ops.py` (`catalog`, `op`, `sweep`, `matrix`); takeover/rotation via `scripts/ha-r10-build-group.sh kill-node|start-node|rotate <code>` (with the group env from `genv` in the mesh-up script); teardown with `scripts/ha-r10-teardown-all.sh` (prints a verification block; also closes ledger entries). Python tooling venv: `~/.local/share/netclaw/r10-venv` (recreate with py3.10 and the pinned packages in handoff.md if missing). Tell the owner when the HUD URLs are up so they can test them in VS Code.

**Then (small):** T034 Azure billing reconciliation (cost data lags a day; Cost Management filtered to tag `netclaw-spec=198`, compare with the ledger), update `tasks.md` T027 and `verification.md` with the final matrix, optionally refresh the mesh doc status and the WordPress draft (owner review only, never publish), and report. Known unrelated: `python3 scripts/reconcile-mcp.py` exits 1 (unstartable servers, an unbounded `humanrail-mcp-server` pin); it failed before this spec.

Behavior rules for this session: keep the owner informed in short plain status; confirm before anything that needs approval (passing the USD 15 pause, tearing down early, anything published/pushed/committed); never tear down before the owner agrees unless the watchdog deadline forces it, and say so beforehand.
