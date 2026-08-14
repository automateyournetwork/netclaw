# Phase 0 Research, Lantronix Percepxion OOB integration

## R1, Vendor, or external/on-demand?

Checked `docs/ADDING-AN-MCP.md`'s classification table against both repos. "Vendored,
pre-registered" fits a stable third-party target adopted and pinned (`zabbix-mcp`: frozen source
under `mcp-servers/zabbix-mcp/vendor/`, pinned to commit `0722f48`, "adopted unmodified"). Neither
Percepxion nor SLC fits that shape: both are Lantronix's own repos, under active co-development
by the author submitting this integration. Confirmed directly, both took real commits in the
week this spec was written (a permission-model bug fix, a new CLI-output-retrieval endpoint, a
dependency lockfile refresh, on `percepxion-mcp-server`; a matching dependency refresh and a
documentation correction on `slc-mcp-server`). Vendoring a frozen copy would be stale before the
PR merges.

**Decision: external/on-demand**, same classification as `pyats` and `aap-automation`. Verified
`aap-automation`'s `SKILL.md` as the closest real precedent, external GitHub repo, `git clone` +
`uv sync`/`pip install -e .`, no `config/openclaw.json` entry, no `specs/` directory (predates
the spec-driven requirement, but structurally identical to what this integration needs).

## R2, One skill or two?

Considered splitting into `percepxion-fleet-ops` (Percepxion only) and `slc-console-ops`
(slc-mcp-server only), mirroring how Auvik's four capability slices
(`auvik-inventory`/`auvik-lifecycle`/`auvik-network-alerts`/`auvik-performance`) are split per
capability rather than bundled.

Rejected: Auvik's split works because each slice is a self-contained capability against **one**
MCP server. Here, the highest-value content is not either server's tool list individually, it's
the **routing rule between them**, when a question needs Percepxion's fleet-wide async view
versus slc-mcp-server's single-device synchronous view, and the connection-string computation
that bridges "I need to reach a managed device attached to this console server" from Percepxion's
device/port model to slc-mcp-server's direct-SSH model. Splitting the skill would either duplicate
that routing content in both files or strand it in one, leaving the other skill silent about a
distinction that determines correctness (a wrong tool choice here sends a live command to the
wrong device via a serial port, not a soft error).

**Decision: one skill**, explicit disambiguation section up front (Key Terms), matching how
`zabbix-availability` handles its sibling relationship with `zabbix-metrics-history` in spirit,
inline here rather than cross-file since the routing decision itself is the content, not a
side-note.

## R3, The dedicated-venv requirement

Both servers pin `fastmcp>=3.1.0,<4.0`. `scripts/lib/install-steps.sh`'s `component_install_zabbix()`
documents that five vendored servers pin `fastmcp<3`
(`netbox-mcp-server`, `CiscoFMC-MCP-server-community`, `Wikipedia_MCP`, `rag-mcp`, `ISE_MCP`) and
a shared install breaks all five, explicitly citing spec 076's cryptography incident as the same
failure shape recurring. Zabbix's install function solves it with a dedicated venv
(`netclaw_venv_create`, `uv venv` fallback, packages installed with `--python` naming the venv
interpreter explicitly, never `netclaw_pip_install` which targets the shared interpreter this
exists to protect).

**Decision:** both `component_install_percepxion()` and `component_install_slc()` follow the same
pattern. Unlike Zabbix, these are external/on-demand (clone into `$MCP_DIR`, not
`mcp-servers/<name>/`), but the isolation reasoning is identical, the version conflict is about
`fastmcp` 3.x versus five other servers, not about vendored-versus-external classification.

## R4, Does `pyats`'s shared-install pattern apply instead?

`component_install_pyats()` and `component_install_junos()` (also external/on-demand) install via
`netclaw_pip_install` into the shared interpreter, no dedicated venv. Checked whether that's the
right template instead of Zabbix's.

**Rejected as the template.** Neither pyATS nor JunOS pins `fastmcp` at all (pyATS's dependency
set is `pyats[full] mcp pydantic python-dotenv`, unconstrained on `fastmcp`; JunOS MCP's
`requirements.txt` has no `fastmcp` entry). They don't carry the conflict Zabbix's comment warns
about, so their shared-install pattern is safe for them and would not be for Percepxion/SLC,
which do pin `fastmcp` 3.x. The two external-install patterns already coexisting in
`install-steps.sh` (shared-interpreter for no-conflict packages, dedicated-venv for
version-conflicting ones) settled which one applies here by inspection, not by guessing.

## R5, A live root-cause finding folded into the skill, not just this spec

While preparing this integration, live testing against `percepxion-mcp-server` (pre-v1.1.0)
found that `get_job_group` never returns CLI command output text, only job status and metadata,
contrary to what the skill's original draft assumed throughout. Traced to the actual mechanism:
Percepxion's own WebUI console-editor fetches output via a second, undocumented REST call
(`POST /v1/telemetry/result/search`), absent from both local copies of Percepxion's OpenAPI spec.
This became `get_cli_command_output`, shipped in `percepxion-mcp-server` v1.1.0 the same week.
Corrected at all 8 sites in the skill body where the prior draft's "retrieve the output with
`get_job_group`" instruction appeared, this is spec.md's FR-002.
