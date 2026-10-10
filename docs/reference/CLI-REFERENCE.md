# NetClaw CLI and interface reference

Repository script entry points, non-vendored Python/shell launchers, npm scripts and Node service/preview launchers. Static declarations include positional args, defaults and choices when present; delegated upstream/runtime CLIs require their installed help. MCP source signatures are not runtime schema attestations.

Generated with `python3 scripts/build-hud-reference.py`. Nothing is executed during extraction.

## Modalities

Canvas branching chat; HUD dashboards; terminal/TUI; Slack and WebEx; mobile text, voice, QR/deep links and camera/microphone capture; MCP stdio/HTTP; external eN2N and internal iN2N delegation. Availability depends on installed/configured integrations. Mobile has no local LLM runtime; Border or a delegated member answers.

## Top-level command

Run `scripts/netclaw` for the interactive menu. `tui` delegates to OpenClaw (`openclaw tui`) or Hermes (`hermes --tui`). `install` forwards arguments to scripts/install.sh. `help`, `-h`, `--help` display the built-in summary.

`peering`: status (default), bgp, n2n, ngrok, up, down, announce.

`risk`: status (default), members, health, add <profile|custom> <name> [csv-skills], remove <member>, role <role> <risk-name> [stacks], edge-check (aliases edge_check/preflight), token [--edge] [label], enroll-mobile [label] (alias enroll_mobile), route <request> [capability].

`chats`: list, <id-prefix> to tail, --watch (alias watch) [seconds]. `link` recreates the local launcher symlink. These commands may mutate state; documentation is not authorization to run them.

## HTTP and MCP

[HUD OpenAPI JSON](hud-openapi.json) inventories every registered HUD HTTP route. Generic schemas remain unspecified; detailed schemas exist for RAG retrieval/upload. [Machine-readable reference](interfaces.json) includes source-declared MCP signatures and daemon route conditions. MCP is JSON-RPC, not REST; use tools/list from the installed server for authoritative schemas. This reference does not contact servers, execute tools or include configuration values.

## .specify/extensions/git/scripts/bash/auto-commit.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--cached`, `--exclude-standard`, `--is-inside-work-tree`, `--others`, `--quiet`

```text
L6: # Usage: auto-commit.sh <event_name>
L13: echo "Usage: $0 <event_name>" >&2
L40: if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
L121: if git diff --quiet HEAD 2>/dev/null && git diff --cached --quiet 2>/dev/null && [ -z "$(git ls-files --others --exclude-standard 2>/dev/null)" ]; then
```

## .specify/extensions/git/scripts/bash/create-new-feature.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--abbrev-ref`, `--all`, `--allow-existing-branch`, `--arg`, `--dry-run`, `--heads`, `--help`, `--is-inside-work-tree`, `--json`, `--list`, `--number`, `--prune`, `--short-name`, `--show-toplevel`, `--timestamp`

```text
L19: case "$arg" in
L20: --json)
L23: --dry-run)
L26: --allow-existing-branch)
L29: --short-name)
L31: echo 'Error: --short-name requires a value' >&2
L37: echo 'Error: --short-name requires a value' >&2
L42: --number)
L44: echo 'Error: --number requires a value' >&2
L50: echo 'Error: --number requires a value' >&2
L55: echo 'Error: --number must be a non-negative integer' >&2
L59: --timestamp)
L62: --help|-h)
L63: echo "Usage: $0 [--json] [--dry-run] [--allow-existing-branch] [--short-name <name>] [--number N] [--timestamp] <feature_description>"
L66: echo "  --json              Output in JSON format"
L67: echo "  --dry-run           Compute branch name without creating the branch"
L68: echo "  --allow-existing-branch  Switch to branch if it already exists instead of failing"
L69: echo "  --short-name <name> Provide a custom short name (2-4 words) for the branch"
L70: echo "  --number N          Specify branch number manually (overrides auto-detection)"
L71: echo "  --timestamp         Use timestamp prefix (YYYYMMDD-HHMMSS) instead of sequential numbering"
L72: echo "  --help, -h          Show this help message"
L78: echo "  $0 'Add user authentication system' --short-name 'user-auth'"
L79: echo "  $0 'Implement OAuth2 integration for API' --number 5"
L80: echo "  $0 --timestamp --short-name 'user-auth' 'Add user authentication'"
L84: *)
L93: echo "Usage: $0 [--json] [--dry-run] [--allow-existing-branch] [--short-name <name>] [--number N] [--timestamp] <feature_description>" >&2
L154: remote_highest=$(GIT_TERMINAL_PROMPT=0 git ls-remote --heads "$remote" 2>/dev/null | sed 's|.*refs/heads/||' | _extract_highest_number)
L175: git fetch --all --prune >/dev/null 2>&1 || true
L195: # ---------------------------------------------------------------------------
L202: # ---------------------------------------------------------------------------
L240: elif git rev-parse --show-toplevel >/dev/null 2>&1; then
L241: REPO_ROOT=$(git rev-parse --show-toplevel)
L256: elif git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
L328: # Warn if --number and --timestamp are both specified
L330: >&2 echo "[specify] Warning: --number is ignored when --timestamp is used"
L384: current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
L385: if git branch --list "$BRANCH_NAME" | grep -q .; then
L397: >&2 echo "Error: Branch '$BRANCH_NAME' already exists. Rerun to get a new timestamp or use a different --short-name."
L400: >&2 echo "Error: Branch '$BRANCH_NAME' already exists. Please use a different feature name or specify a different number with --number."
L424: --arg branch_name "$BRANCH_NAME" \
L425: --arg feature_num "$FEATURE_NUM" \
L429: --arg branch_name "$BRANCH_NAME" \
L430: --arg feature_num "$FEATURE_NUM" \
```

## .specify/extensions/git/scripts/bash/git-common.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--is-inside-work-tree`

```text
L11: git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1
```

## .specify/extensions/git/scripts/bash/initialize-repo.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--allow-empty`, `--is-inside-work-tree`

```text
L44: if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
L52: _git_out=$(git commit --allow-empty -q -m "$COMMIT_MSG" 2>&1) || { echo "[specify] Error: git commit failed: $_git_out" >&2; exit 1; }
```

## .specify/integrations/codex/scripts/update-context.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--show-toplevel`

```text
L15: git_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
```

## .specify/scripts/bash/check-prerequisites.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--arg`, `--argjson`, `--help`, `--include-tasks`, `--json`, `--paths-only`, `--require-tasks`

```text
L8: # Usage: ./check-prerequisites.sh [OPTIONS]
L11: #   --json              Output in JSON format
L12: #   --require-tasks     Require tasks.md to exist (for implementation phase)
L13: #   --include-tasks     Include tasks.md in AVAILABLE_DOCS list
L14: #   --paths-only        Only output path variables (no validation)
L15: #   --help, -h          Show help message
L31: case "$arg" in
L32: --json)
L35: --require-tasks)
L38: --include-tasks)
L41: --paths-only)
L44: --help|-h)
L46: Usage: check-prerequisites.sh [OPTIONS]
L51: --json              Output in JSON format
L52: --require-tasks     Require tasks.md to exist (for implementation phase)
L53: --include-tasks     Include tasks.md in AVAILABLE_DOCS list
L54: --paths-only        Only output path variables (no prerequisite validation)
L55: --help, -h          Show this help message
L59: ./check-prerequisites.sh --json
L62: ./check-prerequisites.sh --json --require-tasks --include-tasks
L65: ./check-prerequisites.sh --paths-only
L70: *)
L71: echo "ERROR: Unknown option '$arg'. Use --help for usage information." >&2
L93: --arg repo_root "$REPO_ROOT" \
L94: --arg branch "$CURRENT_BRANCH" \
L95: --arg feature_dir "$FEATURE_DIR" \
L96: --arg feature_spec "$FEATURE_SPEC" \
L97: --arg impl_plan "$IMPL_PLAN" \
L98: --arg tasks "$TASKS" \
L164: --arg feature_dir "$FEATURE_DIR" \
L165: --argjson docs "$json_docs" \
```

## .specify/scripts/bash/common.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--abbrev-ref`, `--is-inside-work-tree`, `--show-toplevel`

```text
L9: # Use -- to handle paths starting with - (e.g., -P, -L)
L38: if git rev-parse --show-toplevel >/dev/null 2>&1; then
L39: git rev-parse --show-toplevel
L59: git -C "$repo_root" rev-parse --abbrev-ref HEAD
L114: git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1
L315: case "$(basename "$ext")" in .*) continue;; esac
```

## .specify/scripts/bash/create-new-feature.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--all`, `--arg`, `--help`, `--json`, `--list`, `--number`, `--prune`, `--short-name`, `--timestamp`

```text
L13: case "$arg" in
L14: --json)
L17: --short-name)
L19: echo 'Error: --short-name requires a value' >&2
L24: # Check if the next argument is another option (starts with --)
L26: echo 'Error: --short-name requires a value' >&2
L31: --number)
L33: echo 'Error: --number requires a value' >&2
L39: echo 'Error: --number requires a value' >&2
L44: --timestamp)
L47: --help|-h)
L48: echo "Usage: $0 [--json] [--short-name <name>] [--number N] [--timestamp] <feature_description>"
L51: echo "  --json              Output in JSON format"
L52: echo "  --short-name <name> Provide a custom short name (2-4 words) for the branch"
L53: echo "  --number N          Specify branch number manually (overrides auto-detection)"
L54: echo "  --timestamp         Use timestamp prefix (YYYYMMDD-HHMMSS) instead of sequential numbering"
L55: echo "  --help, -h          Show this help message"
L58: echo "  $0 'Add user authentication system' --short-name 'user-auth'"
L59: echo "  $0 'Implement OAuth2 integration for API' --number 5"
L60: echo "  $0 --timestamp --short-name 'user-auth' 'Add user authentication'"
L63: *)
L72: echo "Usage: $0 [--json] [--short-name <name>] [--number N] [--timestamp] <feature_description>" >&2
L137: git fetch --all --prune >/dev/null 2>&1 || true
L186: # Convert to lowercase and split into words
L189: # Filter words: remove stop words and words shorter than 3 chars (unless they're uppercase acronyms in original)
L236: # Warn if --number and --timestamp are both specified
L238: >&2 echo "[specify] Warning: --number is ignored when --timestamp is used"
L289: if git branch --list "$BRANCH_NAME" | grep -q .; then
L291: >&2 echo "Error: Branch '$BRANCH_NAME' already exists. Rerun to get a new timestamp or use a different --short-name."
L293: >&2 echo "Error: Branch '$BRANCH_NAME' already exists. Please use a different feature name or specify a different number with --number."
L323: --arg branch_name "$BRANCH_NAME" \
L324: --arg spec_file "$SPEC_FILE" \
L325: --arg feature_num "$FEATURE_NUM" \
```

## .specify/scripts/bash/setup-plan.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--arg`, `--help`, `--json`

```text
L10: case "$arg" in
L11: --json)
L14: --help|-h)
L15: echo "Usage: $0 [--json]"
L16: echo "  --json    Output results in JSON format"
L17: echo "  --help    Show this help message"
L20: *)
L56: --arg feature_spec "$FEATURE_SPEC" \
L57: --arg impl_plan "$IMPL_PLAN" \
L58: --arg specs_dir "$FEATURE_DIR" \
L59: --arg branch "$CURRENT_BRANCH" \
L60: --arg has_git "$HAS_GIT" \
```

## .specify/scripts/bash/update-agent-context.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L37: # Usage: ./update-agent-context.sh [agent_type]
L262: case "$lang" in
L272: *)
L374: printf '%s\n' "---" "description: Project Development Guidelines" "globs: [\"**/*\"]" "alwaysApply: true" "---" "" > "$frontmatter_file"
L518: if ! head -1 "$temp_file" | grep -q '^---'; then
L521: printf '%s\n' "---" "description: Project Development Guidelines" "globs: [\"**/*\"]" "alwaysApply: true" "---" "" > "$frontmatter_file"
L617: case "$agent_type" in
L618: claude)
L621: gemini)
L624: copilot)
L627: cursor-agent)
L630: qwen)
L633: opencode)
L636: codex)
L639: windsurf)
L642: junie)
L645: kilocode)
L648: auggie)
L651: roo)
L654: codebuddy)
L657: qodercli)
L660: amp)
L663: shai)
L666: tabnine)
L669: kiro-cli)
L672: agy)
L675: bob)
L678: vibe)
L681: kimi)
L684: trae)
L687: pi)
L690: iflow)
L693: generic)
L696: *)
L786: log_info "Usage: $0 [claude|gemini|copilot|cursor-agent|qwen|opencode|codex|windsurf|junie|kilocode|auggie|roo|codebuddy|amp|shai|tabnine|kiro-cli|agy|bob|vibe|qodercli|kimi|trae|pi|iflow|generic]"
```

## benchmarks/audit124/gcf_cost.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--iterations`

```text
L14: argparse.ArgumentParser()
L14: p.add_argument('--iterations',type=int,default=20)
```

## benchmarks/gcf_graph_benchmark.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L10: Usage:
```

## benchmarks/gcf_vs_toon_benchmark.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L6: Usage:
```

## blender_addon.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## captures/analysis-20260714/build_report2.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## lab/frr-testbed/scripts/setup-gre.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--format`

```text
L24: # --- Step 0: Fix IPv6 sysctl in each container via nsenter ---
L27: PID=$(docker inspect "$CTR" --format '{{.State.Pid}}' 2>/dev/null || echo "")
L43: # --- Step 1: Host peering IPv6 address on Docker bridge ---
L64: # --- Step 2: GRE tunnel (IPv6 outer — ip6gre) ---
L72: # --- Step 3: IPv6 inner addressing on host GRE ---
L77: # --- Step 4: GRE tunnel inside Edge1 + IPv6 inner address ---
L87: # --- Step 5: Host identity route + IPv6 routes to lab networks via GRE ---
```

## lab/frr-testbed/scripts/teardown-gre.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## lab/frr-testbed/scripts/verify.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--format`

```text
L19: # --- Container health ---
L20: echo "--- Container Status ---"
L22: if docker ps --format '{{.Names}}' | grep -q "^${c}$"; then
L30: # --- OSPFv3 convergence ---
L31: echo "--- OSPFv3 Neighbors ---"
L55: # --- Loopback reachability via OSPFv3 routing table ---
L57: echo "--- Loopback Reachability (OSPFv3 routing table) ---"
L71: # --- MP-BGP IPv6 unicast convergence ---
L74: echo "--- MP-BGP IPv6 Unicast Sessions ---"
L95: # --- Route propagation ---
L96: echo "--- IPv6 Route Propagation ---"
L109: # --- GRE tunnel + eBGP to WSL NetClaw (optional) ---
L110: echo "--- GRE Tunnel (host side) ---"
L128: # --- eBGP to WSL NetClaw ---
L129: echo "--- eBGP to WSL NetClaw ---"
L138: # --- Summary ---
```

## labs/multivendor-r1/frr-ssh/start.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/analysis-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/anta-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/auvik-mcp/auvik_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/azure-network-mcp/azure_network_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/batfish-mcp/batfish_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/bgp-intel-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/catc-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/cisco-psirt-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/claroty-mcp/claroty_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/document-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/eve-ng-mcp-server/eve_ng_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/eve-ng-mcp-server/tests/test_eve_live_health.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--fail-fast`, `--mutating`, `--target`

```text
L49: argparse.ArgumentParser(add_help=False)
L50: parser.add_argument("--target", choices=("local", "external", "both"), default=os.getenv("EVE_HEALTH_TARGET", "local"))
L286: argparse.ArgumentParser(description="Fast live EVE-NG MCP operation health diagnostics")
L287: parser.add_argument("--target", choices=("local", "external", "both"), default=TARGET, help="EVE profile to test (default: local)")
L288: parser.add_argument("--mutating", action="store_true", help="run reversible start/stop and config set/wipe checks")
L289: parser.add_argument("--fail-fast", action="store_true", help="stop after the first failed capability")
```

## mcp-servers/eve-ng-mcp-server/tests/test_eve_skills_smoke.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--help`

```text
```

## mcp-servers/fortinet-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/gnmi-mcp/gnmi_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/gns3-mcp-server/gns3_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/gns3-mcp-server/tests/test_gns3_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/halo-mcp/halo_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/hermes-hud-mcp/hermes_api.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--home`, `--installation`, `--port`, `--source`

```text
L135: argparse.ArgumentParser()
L135: parser.add_argument('--home',required=True)
L135: parser.add_argument('--source',required=True)
L135: parser.add_argument('--installation',required=True)
L135: parser.add_argument('--port',type=int,default=8643)
```

## mcp-servers/hermes-hud-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/image-style-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/ipfix-mcp/ipfix_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/jev-mcp/audit_worker.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/jev-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--env-file`, `--read-task-id`, `--status`

```text
L113: argparse.ArgumentParser(description=__doc__)
L114: parser.add_argument("--status", action="store_true", help="Print secret-free local status without inference")
L115: parser.add_argument("--env-file", metavar="PATH", help="Load allowlisted literal Jev settings from this operator-selected environment file")
L116: parser.add_argument("--read-task-id", help="Operator-owned task binding for a read-only assessment process; never a model argument")
```

## mcp-servers/memory-mcp/memory_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/multivendor-cli-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/n2n-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/nautobot-golden-config-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/nautobot-mcp-v2/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/nautobot-routing-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/netclaw-dot-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/nsm-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/ollama-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/packet-buddy-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/protocol-mcp/bgp-daemon-v2.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--break-system-packages`, `--edge`

```text
```

## mcp-servers/protocol-mcp/bgp-daemon.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/protocol-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/rag-mcp/rag_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/redfish-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/snmptrap-mcp/snmptrap_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/suzieq-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/syslog-mcp/syslog_mcp_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/tavus-pal-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/topology-diagram-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/tts-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/twilio-voice-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/twilio-voice-mcp/webhook_server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L12: Usage:
```

## mcp-servers/twitter-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L2095: for cmd in self_commands:
```

## mcp-servers/worldlabs-marble-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## mcp-servers/zoom-rtms-mcp/server.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/add-skill-licenses.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--add-frontmatter`, `--dry-run`, `--license`, `--path`

```text
L148: argparse.ArgumentParser(description="Add missing license fields to skill files")
L149: parser.add_argument("--dry-run", action="store_true", help="Show what would change")
L150: parser.add_argument("--license", default="Apache-2.0", help="License identifier (default: Apache-2.0)")
L151: parser.add_argument("--path", default=None, help="Path to skills directory")
L152: parser.add_argument("--add-frontmatter", action="store_true", help="Add frontmatter to files without it")
L7: Usage:
```

## scripts/apply-fastmcp-patches.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--check`, `--component`, `--root`

```text
L88: argparse.ArgumentParser(description=__doc__)
L89: parser.add_argument('--root', type=Path, default=ROOT)
L90: parser.add_argument('--component', required=True)
L91: parser.add_argument('--check', action='store_true')
```

## scripts/build-hud-reference.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--edge`, `--exclude-standard`, `--help`, `--others`, `--server`, `--tui`, `--watch`

```text
L43: if re.search(r'sys\.argv|Usage:|usage:|cmd ==|cmd in ',line):
L49: if re.search(r'(^\s*#.*(?:netclaw|--|Usage)|Usage:|case .* in|^\s*[\w|*-]+\)|--[\w-]+)',line):
L71: 'declarations':[{'line':n,'declaration':line.strip()} for n,line in enumerate(source.splitlines(),1) if re.search(r'process\.argv|Usage:|usage:',line)],
```

## scripts/build-pal-avatars.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--background`, `--factory-startup`, `--python`

```text
```

## scripts/check-dependency-pins.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--json`, `--warn-only`

```text
L353: argparse.ArgumentParser(description=__doc__.split("\n")[0])
L354: ap.add_argument("--json", action="store_true", dest="as_json")
L355: ap.add_argument("--warn-only", action="store_true")
```

## scripts/check-fastmcp-compat.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--catalogs`, `--probe`, `--python`

```text
L150: argparse.ArgumentParser(description=__doc__)
L151: parser.add_argument('--catalogs', type=Path, help='Run offline discovery and write evidence JSON')
L152: parser.add_argument('--python', default=sys.executable)
L153: parser.add_argument('--probe', help=argparse.SUPPRESS)
```

## scripts/check-fastmcp-external.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--components`, `--output`, `--python`, `--sources`, `--worker`

```text
L103: argparse.ArgumentParser(description=__doc__)
L104: parser.add_argument('--sources',type=Path,required=True)
L105: parser.add_argument('--python',default=sys.executable)
L106: parser.add_argument('--output',type=Path)
L107: parser.add_argument('--worker',choices=ENTRIES)
L108: parser.add_argument('--components',nargs='+',choices=ENTRIES)
L64: sys.argv=[str(base/source) if source else name]
```

## scripts/check-mcp-portability.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--config`, `--json`, `--repo`, `--warn-only`

```text
L121: argparse.ArgumentParser(description=__doc__.split("\n")[0])
L122: parser.add_argument("--config", default=DEFAULT_CONFIG,
                        help="path to openclaw.json (default: repo config)")
L124: parser.add_argument("--repo", default=REPO_ROOT,
                        help="repository root used to resolve relative paths")
L126: parser.add_argument("--warn-only", action="store_true",
                        help="print findings but always exit 0")
L128: parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit machine-readable results")
```

## scripts/check-mcp-tasks.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--catalogs`

```text
L58: argparse.ArgumentParser(description=__doc__)
L59: parser.add_argument('--catalogs',type=Path,help='fresh check-fastmcp-compat.py JSON evidence')
```

## scripts/check-meraki-capability-ids.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--warn-only`

```text
L108: argparse.ArgumentParser(description=__doc__)
L109: ap.add_argument("--warn-only", action="store_true", help="report findings but exit 0")
```

## scripts/check-mobile-bundle.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L34: argparse.ArgumentParser(description=__doc__)
L35: parser.add_argument('app', type=Path)
```

## scripts/check-package-references.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--refresh`, `--warn-only`

```text
L184: argparse.ArgumentParser(description=__doc__)
L185: ap.add_argument("--warn-only", action="store_true", help="report findings but exit 0")
L186: ap.add_argument("--refresh", action="store_true",
                    help="re-query the registries and rewrite the manifest (needs network)")
```

## scripts/check-server-startup.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--config`, `--directory`, `--only`, `--warn-only`, `--with`

```text
L236: argparse.ArgumentParser(description=__doc__)
L237: ap.add_argument("--warn-only", action="store_true",
                    help="report findings but exit 0")
L239: ap.add_argument("--only", help="check a single server by name")
L242: ap.add_argument("--config", default=CONFIG,
                    help=f"registration file to read (default: {CONFIG})")
L184: if cmd in ("npx", "uvx", "docker", "node", "npm") and not shutil.which(cmd):
```

## scripts/checkpoint-enable.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--version`

```text
L44: NODE_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
L46: log_error "Node.js >= 18 required. Found: $(node --version)"
L49: log_info "Node.js version: $(node --version)"
L133: echo "--- Management Server (most common) ---"
L163: echo "--- Reputation Service (threat intelligence) ---"
L168: echo "--- Harmony SASE (optional) ---"
L347: echo "  Usage:"
```

## scripts/chrome-devtools-enable.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--browserUrl`, `--channel`, `--executablePath`, `--headless`, `--help`, `--path`, `--remote-debugging-port`, `--user-data-dir`, `--version`

```text
L13: #      explicit --executablePath, then reload the MCP runtime.
L15: # Why --executablePath instead of --channel: chrome-devtools-mcp's --channel
L19: # post-implementation notes). Pinning --executablePath to a NetClaw-managed,
L42: # (see: npx chrome-devtools-mcp@latest --help). NetClaw does not override
L63: node_major="$(node --version | sed -E 's/^v([0-9]+).*/\1/')"
L65: log_error "Node.js 18+ is required. Found: $(node --version)"
L68: log_info "Node.js version: $(node --version)"
L108: install_output="$(npx -y @puppeteer/browsers install chrome@stable --path "$BROWSER_CACHE_DIR" 2>&1 | tail -1)"
L114: log_warn "chrome-devtools-mcp may still auto-download its own copy on first use, but this is unverified — pass --executablePath manually if it fails."
L123: HEADLESS_ARGS="[\"-y\",\"chrome-devtools-mcp@latest\",\"--headless=true\",\"--executablePath=$EXECUTABLE_PATH\"]"
L124: VISIBLE_ARGS="[\"-y\",\"chrome-devtools-mcp@latest\",\"--headless=false\",\"--executablePath=$EXECUTABLE_PATH\"]"
L126: HEADLESS_ARGS="[\"-y\",\"chrome-devtools-mcp@latest\",\"--headless=true\"]"
L127: VISIBLE_ARGS="[\"-y\",\"chrome-devtools-mcp@latest\",\"--headless=false\"]"
L148: log_info "Use this --executablePath: $EXECUTABLE_PATH"
L165: echo "    npx chrome-devtools-mcp@latest --headless=false${EXECUTABLE_PATH:+ --executablePath=\"$EXECUTABLE_PATH\"}"
L172: echo "       google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-devtools-signin-profile"
L177: echo "       npx chrome-devtools-mcp@latest --browserUrl=http://127.0.0.1:9222"
```

## scripts/cloudflared-transport.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--help`, `--lines`, `--no-pager`, `--now`, `--port`, `--property`, `--user`, `--version`

```text
L4: # Generates and manages a systemd --user unit for cloudflared tunnel transport.
L34: # Usage:
L35: #   ./scripts/cloudflared-transport.sh generate <tunnel-name> [--port PORT]
L39: #   ./scripts/cloudflared-transport.sh --help
L62: Usage:
L63: ${SCRIPT_NAME} generate <tunnel-name> [--port PORT]
L67: ${SCRIPT_NAME} --help | -h
L71: enable    Enable and start the unit (daemon-reload + enable --now)
L76: --port PORT   Local eN2N listener port (default: ${DEFAULT_PORT})
L77: --help, -h    Show this help
L80: # One-time setup for a tunnel named "netclaw-byrnbaker":
L88: ${SCRIPT_NAME} generate netclaw-byrnbaker --port 8179
L125: # Check that systemctl --user is functional
L128: systemctl --user show-environment >/dev/null 2>&1 || die "systemctl --user is not functional. Ensure XDG_RUNTIME_DIR is set and a user session is active (loginctl enable-linger \$USER)."
L225: echo "  systemctl --user daemon-reload"
L226: echo "  systemctl --user enable --now ${unit}"
L243: systemctl --user daemon-reload
L244: systemctl --user enable --now "${unit}"
L248: systemctl --user status "${unit}" --no-pager --lines=5 2>/dev/null || true
L250: info "Logs: journalctl --user -u ${unit} -f"
L262: state=$(systemctl --user is-active "${unit}" 2>/dev/null) || true
L269: systemctl --user show "${unit}" --property=MainPID,ActiveEnterTimestamp --no-pager 2>/dev/null | sed 's/^/  /'
L273: journalctl --user -u "${unit}" --no-pager --lines=10 2>/dev/null || true
L296: systemctl --user disable --now "${unit}" 2>/dev/null || true
L297: systemctl --user daemon-reload
L307: # Handle --help / -h / no args
L308: if [[ $# -eq 0 ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
L315: case "${cmd}" in
L316: generate|enable|status|disable)
L318: --version|-V)
L322: *)
L323: die "Unknown subcommand '${cmd}'. Use '${SCRIPT_NAME} --help' for usage."
L329: die "Missing <tunnel-name>. Usage: ${SCRIPT_NAME} ${cmd} <tunnel-name>"
L335: # Parse optional flags (only --port is supported, only for generate)
L338: case "$1" in
L339: --port)
L341: die "--port requires a value"
L346: *)
L347: die "Unknown option '$1'. Use '${SCRIPT_NAME} --help' for usage."
L353: case "${cmd}" in
L354: generate) cmd_generate "${tunnel_name}" "${local_port}" ;;
L355: enable)   cmd_enable "${tunnel_name}" ;;
L356: status)   cmd_status "${tunnel_name}" ;;
L357: disable)  cmd_disable "${tunnel_name}" ;;
```

## scripts/component-launch.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--add`, `--server`

```text
L111: argparse.ArgumentParser(description=__doc__)
L112: parser.add_argument('component', choices=sorted(CONTRACT))
L113: parser.add_argument('--server')
```

## scripts/defenseclaw-disable.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L5: # Usage: ./scripts/defenseclaw-disable.sh
```

## scripts/defenseclaw-enable.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--args`, `--command`, `--enable-guardrail`, `--mode`, `--skip-scan`, `--url`, `--version`

```text
L5: # Usage: ./scripts/defenseclaw-enable.sh
L96: NODE_VER=$(node --version | sed 's/v//' | cut -d. -f1)
L140: CURRENT_VERSION=$(defenseclaw --version 2>/dev/null || echo "unknown")
L171: defenseclaw init --enable-guardrail 2>/dev/null || log_warn "Guardrail init may have failed - check manually"
L176: "$HOME/.local/bin/defenseclaw" init --enable-guardrail 2>/dev/null || log_warn "Guardrail init may have failed"
L179: log_warn "Then run: defenseclaw init --enable-guardrail"
L220: CURRENT_VERSION=$(openshell --version 2>/dev/null || echo "unknown")
L298: cmd = [defenseclaw, 'mcp', 'set', name, '--skip-scan']
L301: cmd.extend(['--command', server_config['command']])
L306: cmd.extend(['--args', json.dumps(args)])
L308: cmd.extend(['--args', str(args)])
L317: cmd.extend(['--url', url])
L354: echo "  ---------------------------------------------------------"
L365: echo "  ----------------------------------------------------------"
L370: echo "    defenseclaw setup guardrail --mode action"
L381: echo "    openshell --version                # Check version"
L388: echo "    defenseclaw --version              # Check version"
L394: echo "    defenseclaw setup guardrail --mode action  # Enable blocking"
```

## scripts/defenseclaw-slack-guard.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--user`

```text
L21: # visible in `journalctl --user -u openclaw-gateway | grep slack-guard`.
```

## scripts/defenseclaw-slack-watch.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/deploy-skills.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--backups`, `--destination`, `--preview`, `--restore`, `--source`, `--state-base`

```text
L115: argparse.ArgumentParser(description=__doc__)
L116: parser.add_argument('--source', type=Path)
L117: parser.add_argument('--destination', type=Path)
L118: parser.add_argument('--backups', type=Path)
L119: parser.add_argument('--state-base', default='.openclaw')
L120: parser.add_argument('--restore', type=Path)
L121: parser.add_argument('--preview', action='store_true')
```

## scripts/dot-nginx-enable.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L2: # Add the /netclaw-dot/ location to the zoom vhost. Run with sudo. Backs up, validates, rolls back on failure.
```

## scripts/edge-enrollments.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--dry-run`, `--force`, `--older-than`, `--retire`, `--retire-stale`

```text
L138: argparse.ArgumentParser(
        description="List and retire NetClaw Mobile edge enrollments (FR-017).")
L140: ap.add_argument("--retire", metavar="MEMBER_ID",
                    help="retire this enrollment")
L142: ap.add_argument("--retire-stale", action="store_true",
                    help="retire every enrollment unseen beyond --older-than")
L144: ap.add_argument("--older-than", type=float, default=DEFAULT_STALE_DAYS,
                    metavar="DAYS",
                    help=f"staleness threshold in days (default {DEFAULT_STALE_DAYS})")
L147: ap.add_argument("--dry-run", action="store_true",
                    help="show what would be retired without doing it")
L149: ap.add_argument("--force", action="store_true",
                    help="retire a non-stale enrollment anyway (NOT reversible: "
                         "the pinned key is deleted and the device must re-enroll)")
L213: f"days. Retire with:  {os.path.basename(sys.argv[0])} --retire-stale")
```

## scripts/edge-heartbeat.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--all`, `--dry-run`, `--member`, `--no-pager`, `--since`, `--stale-after-days`, `--user`

```text
L197: argparse.ArgumentParser()
L198: ap.add_argument("--dry-run", action="store_true",
                    help="print the heartbeat instead of pushing it")
L200: ap.add_argument("--member", help="push to only this member_id")
L201: ap.add_argument("--stale-after-days", type=float, default=3.0,
                    help="skip unreachable devices unseen for longer than this "
                         "(abandoned enrollments); ignored for --member")
L204: ap.add_argument("--all", action="store_true",
                    help="push to every enrolled device, including stale ones")
```

## scripts/equinix-stdio.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--transport`

```text
```

## scripts/forward-enable.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--quiet`, `--tags`, `--verify`

```text
L56: git -C "$dir" fetch origin --tags
L62: if git -C "$dir" rev-parse --verify --quiet "origin/$ref" >/dev/null; then
```

## scripts/gait-stdio.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L34: os.execv(venv_python, [venv_python, os.path.abspath(__file__), *sys.argv[1:]])
```

## scripts/gait-venv-setup.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--restore`

```text
L2: # Create a verified isolated GAIT generation; retain prior runtime for --restore.
```

## scripts/godaddy-ddns.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--max-time`

```text
L16: #   DDNS_NAME     required   record name, e.g. netclaw  ("@" for the apex)
L36: ip="$(curl -fsS --max-time 10 "$url" 2>/dev/null | tr -d '[:space:]')"
L45: curl -fsS --max-time 15 \
L65: code="$(curl -fsS --max-time 20 -o /dev/null -w '%{http_code}' \
L70: case "$code" in
L71: 2*) log "updated ${DDNS_NAME}.${DDNS_DOMAIN} -> ${wanted} (ttl ${TTL})" ;;
L72: *)  log "ERROR GoDaddy PUT returned HTTP ${code}"; exit 1 ;;
```

## scripts/hud-launch.mjs

Node entry point; argument/source references only. npm wrapper commands are indexed separately.

Flags mentioned: `--add`, `--dry-run`, `--home`, `--installation`, `--port`, `--runtime`, `--source`

```text
L13: const args=process.argv.slice(2), env={...process.env};
L31: if(!['start','status','--dry-run'].includes(mode)) throw Error('Usage: netclaw hud [start|status|select KIND HOME] [--runtime KIND --home PATH] [--dry-run]');
```

## scripts/hud-node-version.mjs

Node entry point; argument/source references only. npm wrapper commands are indexed separately.

Flags mentioned: none

```text
L9: if(process.argv[1]===fileURLToPath(import.meta.url) && !supportsHudNode()) {
```

## scripts/import-env.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--runtime`, `--source`, `--target`

```text
L99: argparse.ArgumentParser(description=__doc__)
L100: parser.add_argument('--source', type=Path, default=ROOT / '.env')
L101: parser.add_argument('--target', type=Path, help='Override the runtime dotenv path')
L102: parser.add_argument('--runtime', choices=('openclaw', 'hermes'), default=os.environ.get('NETCLAW_RUNTIME', 'openclaw'))
L103: parser.add_argument('--apply', action='store_true', help='Write missing settings; default is preview only')
```

## scripts/in2n-border-workspace.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--live-workspace`, `--members`, `--on-demand`, `--out`, `--risk`

```text
L131: argparse.ArgumentParser()
L132: ap.add_argument("--risk", required=True)
L133: ap.add_argument("--members", default="", help="always-on member names, comma-sep")
L134: ap.add_argument("--on-demand", default="", help="on-demand member names, comma-sep")
L135: ap.add_argument("--live-workspace", default="~/.openclaw/workspace")
L136: ap.add_argument("--out", default=None)
L16: Usage:
```

## scripts/in2n-member-home.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--anthropic-key-from`, `--border-config`, `--local`, `--member`, `--model`, `--risk`

```text
L44: argparse.ArgumentParser()
L45: ap.add_argument("--risk", required=True)
L46: ap.add_argument("--member", required=True, help="profile/member name, e.g. ipfabric")
L47: ap.add_argument("--model", default=None, help="override model (default: profile tier)")
L48: ap.add_argument("--anthropic-key-from", default="~/.openclaw/.env")
L49: ap.add_argument("--border-config", default=f"{HOME}/.openclaw/openclaw.json")
L16: Usage: python3 scripts/in2n-member-home.py --risk johns-risk --member ipfabric \
```

## scripts/in2n-member.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--idle-exit`, `--local`, `--model`

```text
L148: argparse.ArgumentParser(description="iN2N lightweight member launcher")
L149: ap.add_argument("--idle-exit", type=int, default=int(os.environ.get("N2N_IDLE_EXIT_S", "0")),
                    help="exit after N idle seconds (cold/on-demand); 0 = always-on")
```

## scripts/in2n-migrate.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--border-endpoint`, `--hot`, `--idle-exit`, `--live-env`, `--local`, `--profile`, `--risk`, `--staging`

```text
L58: argparse.ArgumentParser(description="iN2N migration scaffold (generate-only)")
L59: ap.add_argument("--risk", default="johns-risk")
L60: ap.add_argument("--border-endpoint", default="127.0.0.1:11790")
L61: ap.add_argument("--staging", default=os.path.join(REPO, "migration-staging"))
L62: ap.add_argument("--hot", default="cml,pyats,ipfabric,viz",
                    help="comma-separated always-on members; the rest are cold/on-demand")
L64: ap.add_argument("--idle-exit", type=int, default=900,
                    help="idle seconds before a cold/on-demand member exits")
L66: ap.add_argument("--live-env", default="~/.openclaw/.env")
L22: Usage:
```

## scripts/in2n-profiles.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--all`

```text
L10: Usage:
L311: if cmd == "list":
L316: elif cmd == "show" and len(argv) > 1:
L322: elif cmd == "scope" and len(argv) > 1:
L333: sys.exit(_main(sys.argv[1:]))
```

## scripts/in2n-services.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--collect`, `--now`, `--quiet`, `--user`, `--wait`

```text
L332: argparse.ArgumentParser(description="iN2N durable-runtime service generator")
L333: ap.add_subparsers(dest="cmd", required=True)
L334: sub.add_parser("generate")
L335: sub.add_parser("enable")
L336: sub.add_parser("status")
L337: sub.add_parser("disable")
L338: d.add_argument("member", help="member id (<risk>/<name>) or bare name")
L22: Usage:
L249: for member_id, launch_cmd in _always_on_members(risk):
```

## scripts/install-hermes-hud-agent.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--branch`, `--depth`, `--home`, `--python`

```text
L11: argparse.ArgumentParser()
L11: parser.add_argument('--home',required=True)
```

## scripts/install-mcp-config.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--components`, `--config`, `--output`, `--repo`, `--runtime-root`

```text
L115: argparse.ArgumentParser(description=__doc__)
L116: parser.add_argument('--repo', type=Path, required=True)
L117: parser.add_argument('--runtime-root', type=Path, required=True)
L118: parser.add_argument('--components', required=True)
L119: parser.add_argument('--output', type=Path, required=True)
L120: parser.add_argument('--config', type=Path)
```

## scripts/install-pyats-genie.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--check-only`, `--disable-pip-version-check`, `--index-url`, `--isolated`, `--no-user`, `--prefix`, `--upgrade`, `--venv`, `--version`, `--yes`

```text
L127: argparse.ArgumentParser(description=__doc__)
L128: parser.add_argument('--venv', default=str(Path.home() / '.netclaw' / 'pyats-venv'))
L129: parser.add_argument('--version', default=DEFAULT_VERSION, help='Exact pyATS/Genie release (default: %(default)s)')
L130: parser.add_argument('--yes', action='store_true', help='Approve package installation without a prompt')
L131: parser.add_argument('--upgrade', action='store_true', help='Explicitly allow changing the managed environment release')
L132: parser.add_argument('--check-only', action='store_true', help='Validate an existing environment without installing anything')
```

## scripts/install.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--add`, `--all`, `--arch`, `--check-provider`, `--components`, `--config`, `--failed-components`, `--full`, `--help`, `--install-daemon`, `--list`, `--new`, `--os`, `--output`, `--platform-only`, `--preflight`, `--probe`, `--profile`, `--runtime`, `--runtime-root`, `--tui`, `--user`, `--version`

```text
L6: # recorded in ~/.openclaw/netclaw-components.conf so setup.sh only asks for
L10: #   ./scripts/install.sh --profile recommended
L11: #   ./scripts/install.sh --components "pyats netbox gait"   # exact set (replaces manifest)
L12: #   ./scripts/install.sh --add "gns3 cml"                   # add to what's installed
L13: #   ./scripts/install.sh --all
L14: #   ./scripts/install.sh --list
L38: # `netclaw` launcher inherit the same choice. --runtime / the TUI can change it.
L50: echo "Usage: ./scripts/install.sh [options]"
L53: echo "  --runtime <name>          agent runtime to install: openclaw (default) or hermes"
L55: echo "  --profile <name>          install a profile without the TUI"
L57: echo "  --components \"id id ...\"  install an exact component list (see --list);"
L59: echo "  --add \"id id ...\"         install components on top of an existing install;"
L61: echo "  --all                     install everything ($TOTAL_COMPONENTS components)"
L62: echo "  --preflight               check the selection without installing anything"
L63: echo "  --list                    list all components and profiles, then exit"
L64: echo "  --help                    this help"
L94: case "$1" in
L95: --runtime)
L96: [ $# -ge 2 ] || { log_error "--runtime needs a value (openclaw|hermes)"; usage; exit 1; }
L97: case "$2" in
L98: openclaw|hermes) NETCLAW_RUNTIME="$2"; NETCLAW_RUNTIME_EXPLICIT=1; define_runtime ;;
L99: *) log_error "Unknown runtime: $2 (valid: openclaw, hermes)"; exit 1 ;;
L102: --profile)
L103: [ $# -ge 2 ] || { log_error "--profile needs a value"; usage; exit 1; }
L106: --components)
L107: [ $# -ge 2 ] || { log_error "--components needs a value"; usage; exit 1; }
L109: catalog_has "$id" || { log_error "Unknown component: $id (run --list to see valid ids)"; exit 1; }
L113: --add)
L114: [ $# -ge 2 ] || { log_error "--add needs a value"; usage; exit 1; }
L116: catalog_has "$id" || { log_error "Unknown component: $id (run --list to see valid ids)"; exit 1; }
L121: --all|--full)
L124: --preflight) PREFLIGHT_ONLY=1; shift ;;
L125: --list)  list_components; exit 0 ;;
L126: --help|-h) usage; exit 0 ;;
L127: *) log_error "Unknown option: $1"; usage; exit 1 ;;
L135: --os "$NETCLAW_OS" --arch "$NETCLAW_ARCH" --platform-only)" || exit 1
L175: DETECTED_OPENCLAW="$(openclaw --version 2>/dev/null | head -1 || true)"
L186: [ "$(systemctl --user is-active openclaw-gateway.service 2>/dev/null || true)" = "active" ]; then
L249: # --runtime / NETCLAW_RUNTIME was already given explicitly.
L257: case "$TUI_CHOICE" in
L258: 0) NETCLAW_RUNTIME="openclaw" ;;
L259: 1) NETCLAW_RUNTIME="hermes" ;;
L354: log_info "  ./scripts/install.sh --profile recommended"
L355: log_info "  ./scripts/install.sh --components \"pyats netbox gait\""
L356: log_info "  ./scripts/install.sh --add \"gns3 cml\"       # add to an existing install"
L357: log_info "  ./scripts/install.sh --all"
L367: # selections. Install it explicitly with --runtime hermes --add hermes-hud.
L495: # --add merges into the existing manifest; every other path records the
L506: # Top-level `netclaw` command (menu: TUI / installer / protocol peering)
L577: case "$id" in
L578: pyats)           verify_file "$name" "$PYATS_MCP_DIR/pyats_mcp_server.py" ;;
L579: junos)           verify_dir  "$name" "$JUNOS_MCP_DIR" ;;
L580: arista-cvp)      verify_dir  "$name" "$CVP_MCP_DIR" ;;
L581: f5)              verify_file "$name" "$F5_MCP_DIR/F5MCPserver.py" ;;
L582: catalyst-center) verify_file "$name" "$CATC_MCP_DIR/catalyst-center-mcp.py" ;;
L583: aruba-cx)        verify_dir  "$name" "$ARUBA_CX_MCP_DIR" ;;
L584: gnmi)            verify_dir  "$name" "$GNMI_MCP_DIR" ;;
L585: radkit)          verify_dir  "$name" "$RADKIT_MCP_DIR" ;;
L586: netbox)          verify_file "$name" "$NETBOX_MCP_DIR/src/netbox_mcp_server/server.py" ;;
L587: nautobot)        verify_dir  "$name" "$NAUTOBOT_MCP_DIR" ;;
L588: infrahub)        verify_cmd_or_module "$name" infrahub-mcp infrahub_mcp "pip3 install infrahub-mcp" ;;
L589: infoblox)        verify_cmd_or_module "$name" infoblox-ddi-mcp infoblox_ddi_mcp "pip3 install infoblox-ddi-mcp" ;;
L590: aci)             verify_file "$name" "$ACI_MCP_DIR/aci_mcp/main.py" ;;
L591: nso)             verify_cmd_or_module "$name" cisco-nso-mcp-server cisco_nso_mcp_server "requires Python 3.12+, pip3 install cisco-nso-mcp-server" ;;
L592: itential)        verify_cmd_or_module "$name" itential-mcp itential_mcp "pip3 install itential-mcp" ;;
L593: meraki)          verify_dir  "$name" "$MERAKI_MCP_DIR" ;;
L594: sdwan)           verify_dir  "$name" "$SDWAN_MCP_DIR" ;;
L595: prisma-sdwan)    verify_dir  "$name" "$PRISMA_SDWAN_MCP_DIR" ;;
L596: aap)             verify_dir  "$name" "$AAP_MCP_DIR" ;;
L597: ise)             verify_file "$name" "$ISE_MCP_DIR/src/ise_mcp_server/server.py" ;;
L598: fmc)             verify_dir  "$name" "$FMC_MCP_DIR" ;;
L599: panorama)        verify_cmd_or_module "$name" palo-alto-mcp palo_alto_mcp "pip3 install iflow-mcp-cdot65-palo-alto-mcp" ;;
L600: fortinet)        verify_file "$name" "$FORTINET_MCP_DIR/server.py" ;;
L601: bgp-intel)       verify_file "$name" "$BGP_INTEL_MCP_DIR/server.py" ;;
L602: checkpoint)      verify_dir  "$name" "$CHECKPOINT_MCP_DIR" ;;
L603: claroty)         verify_dir  "$name" "$CLAROTY_MCP_DIR" ;;
L604: nvd-cve)         verify_file "$name" "$NVD_MCP_DIR/mcp_nvd/main.py" ;;
L605: nmap)            verify_file "$name" "$NMAP_MCP_DIR/server.py" ;;
L606: fwrule)          verify_dir  "$name" "$FWRULE_MCP_DIR" ;;
L607: aws)             verify_runner "$name" uvx "6 servers run via uvx" ;;
L608: azure)           verify_dir  "$name" "$AZURE_NET_MCP_DIR" ;;
L609: gcp|cloudflare|terraform|vault|zscaler|datadog|jenkins|kubeshark|ue5)
L611: grafana)         verify_runner "$name" uvx "runs via uvx mcp-grafana" ;;
L612: prometheus)      verify_runner "$name" prometheus-mcp-server "pip CLI entry point" ;;
L613: te-community)    verify_file "$name" "$TE_COMMUNITY_MCP_DIR/src/server.py" ;;
L614: te-official)     verify_runner "$name" npx "remote HTTP via npx mcp-remote" ;;
L615: forward)         verify_dir  "$name" "$FORWARD_MCP_DIR" ;;
L616: suzieq)          verify_dir  "$name" "$SUZIEQ_MCP_DIR" ;;
L617: gtrace)          verify_runner "$name" gtrace "standalone Go binary" ;;
L618: cml)             verify_cmd_or_module "$name" cml-mcp cml_mcp "requires Python 3.12+, pip3 install cml-mcp" ;;
L619: containerlab)    verify_file "$name" "$CLAB_MCP_DIR/clab_mcp_server.py" ;;
L620: batfish)         verify_dir  "$name" "$BATFISH_MCP_DIR" ;;
L621: protocol)        verify_file "$name" "$PROTOCOL_MCP_DIR/server.py" ;;
L622: servicenow)      verify_file "$name" "$SERVICENOW_MCP_DIR/src/servicenow_mcp/cli.py" ;;
L623: github)          verify_runner "$name" docker "runs the GitHub MCP Docker image" ;;
L624: gitlab|msgraph|drawio-rfc)
L626: packet-buddy)    verify_file "$name" "$PACKET_BUDDY_MCP_DIR/server.py" ;;
L627: markmap)         verify_file "$name" "$MARKMAP_INNER/dist/index.js" ;;
L628: uml)             verify_dir  "$name" "$UML_MCP_DIR" ;;
L629: subnet-calc)     verify_file "$name" "$SUBNET_MCP_DIR/servers/subnetcalculator_mcp.py" ;;
L630: wikipedia)       verify_file "$name" "$WIKIPEDIA_MCP_DIR/main.py" ;;
L631: tts)             verify_file "$name" "$TTS_MCP_DIR/server.py" ;;
L632: twitter)         verify_file "$name" "$TWITTER_MCP_DIR/server.py" ;;
L633: twilio)          verify_file "$name" "$TWILIO_MCP_DIR/server.py" ;;
L634: gait)            verify_file "$name" "$GAIT_MCP_DIR/gait_mcp.py" ;;
L635: mempalace)       verify_cmd_or_module "$name" mempalace-mcp mempalace.mcp_server "MemPalace module or console entry point missing" ;;
L636: humanrail)       verify_file "$name" "$HUMANRAIL_MCP_DIR/server.py" ;;
L637: *)               log_info "$name: configured (no local artifact to check)"
L739: python3 "$SCRIPT_DIR/installer-readiness.py" --runtime "$RUNTIME" \
L740: --runtime-root "$NETCLAW_RUNTIME_ROOT" --config "$RUNTIME_CONFIG" \
L741: --components "$SELECTED" --failed-components "$FAILED_COMPONENTS $VERIFY_FAILED_COMPONENTS" \
L742: --output "$INSTALL_LOG_DIR/readiness.json" --probe --check-provider || READINESS_FAILED=1
L752: echo "  3. hermes chat                      # Talk to NetClaw (or: hermes --tui)"
L753: echo "  4. netclaw hud                      # Shared HUD; install --add hermes-hud first"
L759: echo "    ./scripts/install.sh --runtime hermes   # Add or remove MCP servers"
L763: echo "  3. openclaw chat --new              # Talk to NetClaw"
L766: echo "    openclaw onboard --install-daemon  # AI provider, gateway, channels"
L801: echo "    ./scripts/install.sh --add \"$(echo $PROBLEM_COMPONENTS | tr '\n' ' ' | sed 's/ $//')\""
```

## scripts/installer-preflight.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--arch`, `--components`, `--format`, `--install`, `--json`, `--os`, `--platform-only`, `--python`, `--runtime`, `--validate-policy`, `--version`

```text
L203: argparse.ArgumentParser(description=__doc__)
L204: parser.add_argument('--os', default='')
L205: parser.add_argument('--arch', default='')
L206: parser.add_argument('--python', default=os.environ.get('NETCLAW_PY', sys.executable))
L207: parser.add_argument('--components', default='')
L208: parser.add_argument('--platform-only', action='store_true')
L209: parser.add_argument('--validate-policy', action='store_true')
L210: parser.add_argument('--json', action='store_true')
L211: parser.add_argument('--runtime', choices=['openclaw', 'hermes'], default='openclaw')
```

## scripts/installer-readiness.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--check-provider`, `--components`, `--config`, `--failed-components`, `--json`, `--output`, `--probe`, `--runtime`, `--runtime-root`, `--timeout`

```text
L242: argparse.ArgumentParser(description=__doc__)
L243: parser.add_argument('--runtime', choices=['openclaw','hermes'], default='openclaw')
L244: parser.add_argument('--runtime-root', type=Path, required=True)
L245: parser.add_argument('--config', type=Path, required=True)
L246: parser.add_argument('--components', required=True)
L247: parser.add_argument('--failed-components', default='')
L248: parser.add_argument('--output', type=Path, required=True)
L249: parser.add_argument('--probe', action='store_true')
L250: parser.add_argument('--check-provider', action='store_true')
L251: parser.add_argument('--timeout', type=float, default=25)
```

## scripts/ipfabric-enable.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--get`, `--header`, `--max-time`, `--user`, `--version`

```text
L52: NODE_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
L54: log_error "Node.js >= 18 required. Found: $(node --version)"
L57: log_info "Node.js version: $(node --version)"
L152: IPFABRIC_HOST="$(python3 "$NETCLAW_DIR/scripts/write-env.py" --get "$OPENCLAW_ENV" IPFABRIC_HOST)"
L153: IPFABRIC_API_TOKEN="$(python3 "$NETCLAW_DIR/scripts/write-env.py" --get "$OPENCLAW_ENV" IPFABRIC_API_TOKEN)"
L160: if curl -sf --max-time 10 -o /dev/null -w "%{http_code}" \
L192: echo '    "args": ["-y", "mcp-remote", "${IPFABRIC_HOST}/mcp", "--header", "Authorization:${IPFABRIC_AUTH_HEADER}"],'
L224: echo "  Usage:"
L231: echo "    1. Restart OpenClaw gateway: systemctl --user restart openclaw-gateway.service"
```

## scripts/jev-adopt.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--config`, `--env-file`, `--repo`, `--restore`

```text
L73: argparse.ArgumentParser(description=__doc__)
L74: parser.add_argument('--config', required=True, type=Path, help='Discovered active Border OpenClaw config')
L75: parser.add_argument('--env-file', type=Path, help='Chosen runtime env file; required except restore')
L76: parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
L77: parser.add_argument('--apply', action='store_true')
L78: parser.add_argument('--restore', action='store_true')
```

## scripts/jev-audit/build_findings.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/jev-audit/candidates.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/jev-audit/common.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/jev-audit/fix_failure_behavior.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/jev-audit/sweep1_skill_health.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/jev-audit/sweep2_overlap_matrix.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/jev-audit/sweep3_coverage_gaps.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/jev-border-adopt.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--restore`, `--workspace`

```text
L170: argparse.ArgumentParser(description=__doc__)
L171: parser.add_argument('--workspace', required=True, type=Path)
L173: group.add_argument('--apply', action='store_true')
L174: group.add_argument('--restore', type=Path, metavar='RECOVERY_JSON')
```

## scripts/jev-settings.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--case`, `--daily`, `--data-dir`, `--endpoint`, `--env-file`, `--expires-in`, `--task`

```text
L95: argparse.ArgumentParser(description=__doc__)
L96: parser.add_argument('--env-file', type=Path, default=Path.home()/'.openclaw/.env')
L97: parser.add_argument('--data-dir', type=Path)
L98: parser.add_subparsers(dest='command', required=True)
L99: subs.add_parser('setup')
L100: subs.add_parser('disable')
L101: subs.add_parser('status', help='Show local status without provider calls')
L102: subs.add_parser('task', help='Bind an originating task without resetting spending')
L103: bind.add_argument('task_id')
L104: subs.add_parser('limits', help='Set operator overrides; changes apply to subsequent calls')
L105: limits.add_argument('--daily', type=money)
L106: limits.add_argument('--case', type=money)
L107: limits.add_argument('--task', help='Bind --case override to this trusted runtime task ID')
L108: subs.add_parser('approve-disclosure', help='Approve the exact previewed request for one use')
L109: grant.add_argument('digest')
L110: grant.add_argument('--endpoint', required=True)
L111: grant.add_argument('--task', required=True)
L112: grant.add_argument('--expires-in', type=int, default=300)
```

## scripts/lib/catalog.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L179: case "$1" in
L180: minimal)        echo "$PROFILE_MINIMAL" ;;
L181: recommended)    echo "$PROFILE_RECOMMENDED" ;;
L182: cisco)          echo "$PROFILE_CISCO" ;;
L183: multivendor)    echo "$PROFILE_MULTIVENDOR" ;;
L184: cloud)          echo "$PROFILE_CLOUD" ;;
L185: security)       echo "$PROFILE_SECURITY" ;;
L186: labs)           echo "$PROFILE_LABS" ;;
L187: observability)  echo "$PROFILE_OBSERVABILITY" ;;
L188: full)           catalog_ids | tr '\n' ' ' ;;
L189: *)              return 1 ;;
```

## scripts/lib/common.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--detach`, `--field`, `--no-checkout`, `--runtime`, `--source`, `--target`

```text
L46: git clone --no-checkout "$url" "$dir" || return 1
L47: git -C "$dir" checkout --detach "$revision" || return 1
L73: # changes (e.g. after a --runtime flag or the TUI prompt).
L77: RUNTIME="$(python3 "$resolver" --field kind)" || return 1
L79: resolved_home="$(python3 "$resolver" --field home)" || return 1
L80: resolved_config="$(python3 "$resolver" --field configPath)" || return 1
L81: case "$RUNTIME" in
L82: openclaw)
L90: hermes)
L98: *)
L130: --source "$NETCLAW_DIR/.env" --target "$RUNTIME_ENV" --apply
L245: # re-derives after a --runtime flag or the TUI prompt. Idempotent.
```

## scripts/lib/equinix/policy.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/lib/fetch-lego.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--version`

```text
L12: echo "lego already installed at $DEST ($("$DEST" --version 2>/dev/null | head -1))"
L16: case "$(uname -m)" in
L17: x86_64|amd64) ARCH=amd64 ;;
L18: aarch64|arm64) ARCH=arm64 ;;
L19: *) echo "unsupported arch $(uname -m) — install lego manually into $DEST" >&2; exit 1 ;;
L27: case "$(uname -s)" in
L28: Linux) OS=linux ;;
L29: Darwin) OS=darwin ;;
L30: *) echo "unsupported OS $(uname -s) — install lego manually into $DEST" >&2; exit 1 ;;
```

## scripts/lib/godaddy-acme-hook.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--accept-tos`, `--dns`, `--domains`, `--email`, `--max-time`

```text
L11: #   lego --dns exec --domains netclaw.automateyournetwork.ca --email you@x --accept-tos run
L32: case "$ACTION" in
L33: present)
L34: curl -s -o /dev/null -w "%{http_code}" --max-time 30 "${hdr[@]}" -X PUT \
L39: cleanup)
L42: curl -s -o /dev/null --max-time 30 "${hdr[@]}" -X DELETE \
L45: *) echo "unknown action $ACTION" >&2; exit 1 ;;
```

## scripts/lib/install-steps.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--add`, `--apply`, `--args`, `--backups`, `--break-system-packages`, `--check`, `--command`, `--components`, `--config`, `--destination`, `--dns-provider`, `--domain`, `--dry-run`, `--edge`, `--enable-guardrail`, `--env`, `--env-file`, `--executablePath`, `--from`, `--global`, `--headless`, `--help`, `--home`, `--install-daemon`, `--listen`, `--mode`, `--no-pager`, `--no-test`, `--noconfirm`, `--node`, `--output`, `--path`, `--quiet`, `--repo`, `--restore`, `--reverse`, `--rm`, `--runtime`, `--runtime-root`, `--set`, `--sidecar`, `--source`, `--state-base`, `--tags`, `--target`, `--upgrade`, `--upstream`, `--user`, `--venv`, `--verify`, `--version`, `--vnc`, `--web`

```text
L37: case "$PKG_MGR:$id" in
L46: *)              out="$out $id" ;;
L55: case "$PKG_MGR" in
L56: apt)    echo "${sp}apt-get update && ${sp}apt-get install -y $pkgs" ;;
L57: dnf)    echo "${sp}dnf install -y $pkgs" ;;
L58: yum)    echo "${sp}yum install -y $pkgs" ;;
L59: pacman) echo "${sp}pacman -S --noconfirm $pkgs" ;;
L60: apk)    echo "${sp}apk add $pkgs" ;;
L61: brew)   echo "brew install $pkgs" ;;
L109: case "$PKG_MGR" in
L110: apt)     node_cmd="curl -fsSL https://deb.nodesource.com/setup_26.x | ${spe}bash - && ${sp}apt-get install -y nodejs" ;;
L111: dnf|yum) node_cmd="curl -fsSL https://rpm.nodesource.com/setup_26.x | ${spe}bash - && ${sp}${PKG_MGR} install -y nodejs" ;;
L112: brew)    node_cmd="brew install node" ;;
L145: if ! python3 "$NETCLAW_DIR/scripts/runtime-policy.py" --runtime "${RUNTIME:-openclaw}" --node "$(node --version)"; then
L149: log_info "Node.js version: $(node --version)"
L156: case " $MISSING_IDS " in
L158: *) MISSING_IDS="$MISSING_IDS npm" ;;
L174: case " ${SELECTED:-} " in
L184: log_info "Component Python: $NETCLAW_PY ($("$NETCLAW_PY" --version 2>&1))"
L241: case ":$PATH:" in
L243: *) export PATH="$HOME/.local/bin:$PATH" ;;
L260: if ! openclaw --version; then
L300: # openclaw's --install-daemon). Best-effort — the agent still
L323: log_info "Reconfigure provider/gateway/channels anytime: openclaw onboard --install-daemon"
L337: OPENCLAW_STATE_DIR="$RUNTIME_HOME" OPENCLAW_CONFIG_PATH="$RUNTIME_CONFIG" openclaw onboard --install-daemon || {
L339: log_warn "You can re-run it later: openclaw onboard --install-daemon"
L345: log_warn "After fixing your PATH, run: openclaw onboard --install-daemon"
L353: # `openclaw onboard --install-daemon` can report success while the gateway
L381: state="$(systemctl --user is-active openclaw-gateway.service 2>/dev/null || true)"
L382: case "$state" in
L383: active)                 break ;;
L384: activating|reloading)   sleep 1 ;;
L385: *)                      break ;;   # inactive/failed/no user bus
L409: if journalctl --user -u openclaw-gateway.service -n 10 --no-pager &> /dev/null; then
L412: journalctl --user -u openclaw-gateway.service -n 10 --no-pager 2>/dev/null | sed 's/^/    /'
L416: echo "    systemctl --user status openclaw-gateway.service"
L417: echo "    journalctl --user -u openclaw-gateway.service -n 50 --no-pager"
L421: echo "    openclaw onboard --install-daemon      # re-run the service install"
L432: openclaw onboard --install-daemon || log_warn "openclaw onboard exited with an error."
L475: python3 "$NETCLAW_DIR/scripts/setup-pyats-runtime.py" --target "$pyats_venv" || return 1
L479: --env-file "$RUNTIME_ENV" --repo "$NETCLAW_DIR" --venv "$pyats_venv" \
L480: --upstream "$PYATS_MCP_DIR/pyats_mcp_server.py" --apply; then
L484: python3 "$NETCLAW_DIR/scripts/setup-pyats-runtime.py" --target "$pyats_venv" --restore || return 1
L502: git -C "$JUNOS_MCP_DIR" pull --quiet 2>/dev/null || true
L512: # Spec 090: netclaw_pip_install handles PEP 668 itself now, so the inline
L513: # --break-system-packages retry is gone -- and stderr is no longer discarded.
L525: # only devices-template.json -- which contains placeholder credentials and a device
L588: log_warn "Fix the error, then retry with: ./scripts/install.sh --add \"markmap\""
L848: log_info "GitHub MCP ready: docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN ghcr.io/github/github-mcp-server"
L900: log_info "uv found: $(uv --version 2>/dev/null || echo 'version unknown')"
L922: log_info "tshark found: $(tshark --version 2>/dev/null | head -1)"
L1074: # memory, RAG, federation and GAIT stores are never readable from it -- a generic SQL
L1091: # NO upper bound -- Authlib, pygnmi, service-identity, sshsig -- and NetClaw's own
L1092: # federation TLS stack (spec 060) is built on it. Measured by `pip install --dry-run`
L1127: # Builder, which is ENTERPRISE-tier on self-managed -- so the supported path is paywalled
L1135: docker pull --quiet \
L1141: # there -- the registration adds host.docker.internal, so a local cluster is
L1165: # Ubuntu 26.04, and `suricata` needs root to install. Both images are pinned by DIGEST --
L1172: docker pull --quiet zeek/zeek@sha256:eca2b3915d3e067cbb4a904f23f4c4f461ea2b60613ab30f7ee77bbc707c87c7 \
L1174: docker pull --quiet jasonish/suricata@sha256:81468a22f0b685f3d7e0c1646ab4fdb9a67c1b3dfa3357c52b1434dd4f39dc49 \
L1191: if docker run --rm -v "$NSM_RULES:/var/lib/suricata/rules" \
L1193: suricata-update --no-test >/dev/null 2>&1 && [ -s "$NSM_RULES/suricata.rules" ]; then
L1213: # not start at all on a PEP 668 host -- one of the seven found by spec 088.
L1226: # DefenseClaw silently 403s outbound calls to unregistered domains -- this has cost this
L1533: uvx --help &>/dev/null || true
L1569: log_info "  Install: helm install kubeshark kubeshark/kubeshark --set mcp.enabled=true --set mcp.port=8898"
L1594: log_info "nmap already installed: $(nmap --version 2>&1 | head -1)"
L1709: log_info "gtrace MCP ready: $(gtrace --version 2>&1 | head -1) (6 tools: traceroute, mtr, globalping, asn_lookup, geo_lookup, reverse_dns)"
L1842: # `risk token --edge` answering "only a Border can issue enrollment tokens",
L1880: case "$TUI_CHOICE" in
L1881: 0)
L1885: 1)
L1892: case "$TUI_CHOICE" in
L1893: 0) _stacks=both ;; 1) _stacks=in2n ;; *) _stacks=en2n ;;
L1904: 2)
L1927: echo "  mesh daemon + always-on members durable systemd --user services."
L1946: if declare -f tui_confirm >/dev/null 2>&1 && tui_confirm "Generate + enable durable systemd --user services now?"; then
L1950: log_warn "service enable failed (systemctl --user may be unavailable on this host)"
L1994: if netclaw_pip_install -q --upgrade iflow-mcp-cdot65-palo-alto-mcp 2>/dev/null; then
L2329: # ── Step 50c: Install Token Optimization Library (netclaw_tokens)
L2559: git -C "$dir" fetch origin --tags
L2565: if git -C "$dir" rev-parse --verify --quiet "origin/$ref" >/dev/null; then
L2690: --repo "$NETCLAW_DIR" --runtime-root "$NETCLAW_RUNTIME_ROOT" \
L2691: --components "${SUCCESSFUL_COMPONENTS:-}" --output "$generated_config" || return 1
L2699: --source "$generated_config" \
L2700: --repo   "$NETCLAW_DIR" \
L2701: --env    "$RUNTIME_ENV" \
L2702: --config "$RUNTIME_CONFIG" \
L2703: --sidecar "$RUNTIME_HOME/netclaw-mcp-servers.yaml"; then
L2714: --repo "$NETCLAW_DIR" --runtime-root "$NETCLAW_RUNTIME_ROOT" \
L2715: --components "${SUCCESSFUL_COMPONENTS:-}" --output "$generated_config" \
L2716: --config "$RUNTIME_CONFIG" || return 1
L2725: --source "$NETCLAW_DIR/workspace/skills" \
L2726: --destination "$RUNTIME_SKILLS" \
L2727: --backups "$RUNTIME_HOME/skill-deployment-backups" \
L2728: --state-base "$(basename "$RUNTIME_HOME")" || return 1
L3039: NODE_VER=$(node --version | sed 's/v//' | cut -d. -f1)
L3061: defenseclaw init --enable-guardrail 2>/dev/null || log_warn "Guardrail init failed - run manually: defenseclaw init --enable-guardrail"
L3063: log_warn "defenseclaw CLI not in PATH. Add ~/.local/bin to PATH and run: defenseclaw init --enable-guardrail"
L3099: OPENSHELL_VERSION=$(openshell --version 2>/dev/null || echo "unknown")
L3124: echo "    openshell --version                    # Check OpenShell"
L3127: echo "    defenseclaw --version                  # Check DefenseClaw"
L3129: echo "    defenseclaw setup guardrail --mode action  # Enable blocking"
L3258: log_info "  hermes mcp add memory-mcp --command uvx --args '--from,netclaw-memory-mcp,memory-mcp-server' --env MEMORY_DATA_DIR=$MEMORY_DATA_DIR"
L3260: log_info "  openclaw mcp set memory-mcp '{\"command\":\"uvx\",\"args\":[\"--from\",\"netclaw-memory-mcp\",\"memory-mcp-server\"],\"env\":{\"MEMORY_DATA_DIR\":\"$MEMORY_DATA_DIR\"}}'"
L3320: log_info "Ollama found: $(ollama --version 2>/dev/null || echo 'version unknown')"
L3414: if ! git -C "$SKETCHFAB_MCP_DIR" apply --reverse --check "$SKETCHFAB_PATCH" 2>/dev/null; then
L3481: echo "  for the WSL2 mirrored-networking check and the --listen fallback."
L3563: install_output="$(npx -y @puppeteer/browsers install chrome@stable --path "$CHROME_DEVTOOLS_CACHE_DIR" 2>&1 | tail -1)"
L3576: HEADLESS_ARGS="[\"-y\",\"chrome-devtools-mcp@latest\",\"--headless=true\",\"--executablePath=$CHROME_DEVTOOLS_EXECUTABLE\"]"
L3577: VISIBLE_ARGS="[\"-y\",\"chrome-devtools-mcp@latest\",\"--headless=false\",\"--executablePath=$CHROME_DEVTOOLS_EXECUTABLE\"]"
L3579: HEADLESS_ARGS="[\"-y\",\"chrome-devtools-mcp@latest\",\"--headless=true\"]"
L3580: VISIBLE_ARGS="[\"-y\",\"chrome-devtools-mcp@latest\",\"--headless=false\"]"
L3585: hermes mcp add chrome-devtools-mcp --command npx >/dev/null 2>&1 \
L3587: || log_warn "Could not add chrome-devtools-mcp — add it manually: hermes mcp add chrome-devtools-mcp --command npx"
L3589: log_info "  args: [\"-y\", \"chrome-devtools-mcp@latest\", \"--headless=true\"]"
L3591: log_info "hermes CLI not found — add chrome-devtools-mcp later: hermes mcp add chrome-devtools-mcp --command npx"
L3605: log_info "Sign in once per target site: npx chrome-devtools-mcp@latest --headless=false${CHROME_DEVTOOLS_EXECUTABLE:+ --executablePath=\"$CHROME_DEVTOOLS_EXECUTABLE\"}"
L3623: case "$PKG_MGR" in
L3624: apt)
L3630: dnf|yum)
L3635: pacman)
L3637: sudo pacman -S --noconfirm $COMPUTER_USE_PACKAGES 2>/dev/null || \
L3640: *)
L3661: if openclaw skills install --global computer-use 2>&1 | tail -5; then
L3667: # (0644) -- confirmed live: every action script fails with "Permission
L3674: log_warn "Could not install the computer-use skill automatically — try manually: openclaw skills install --global computer-use"
L3677: log_warn "openclaw CLI not found — install the skill manually once OpenClaw is set up: openclaw skills install --global computer-use"
L3680: # The skill only ships its action scripts (click.sh, screenshot.sh, ...) --
L3692: # and the novnc unit's --listen has no bind address) -- a real exposure
L3696: # pattern, which this doesn't change -- it just makes it mandatory.
L3704: # wrapper the skill's script assumes -- confirmed missing live on
L3707: -e 's|ExecStart=.*novnc_proxy.*|ExecStart=/usr/share/novnc/utils/launch.sh --vnc localhost:5900 --listen 127.0.0.1:6080 --web /usr/share/novnc|' \
L3708: -e 's/--listen 6080\b/--listen 127.0.0.1:6080/' \
L3751: # but install it now so `--domain` works later without a second step).
L3781: log_info "Domain-verified identity (optional): scripts/patch-claw-certs.sh --domain <name> --dns-provider <id>"
L3840: # isolation from nothing. netclaw_pip_install, never bare pip — on a split
L4121: python3 "$NETCLAW_DIR/scripts/jev-settings.py" --env-file "$RUNTIME_ENV" setup || return 1
L4123: log_info "Enable and configure Jev: python3 scripts/jev-settings.py --env-file '$RUNTIME_ENV' setup"
L4143: [ "$RUNTIME" = "hermes" ] || { log_error "hermes-hud requires --runtime hermes"; return 1; }
L4146: python3 "$NETCLAW_DIR/scripts/install-hermes-hud-agent.py" --home "$RUNTIME_HOME" || return 1
```

## scripts/lib/make-logo-art.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L8: Usage: python3 scripts/lib/make-logo-art.py [cols] [rows]
L18: COLS = int(sys.argv[1]) if len(sys.argv) > 1 else 76
L19: ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
```

## scripts/lib/pip-helper.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--component`, `--python`, `--root`, `--seed`, `--upgrade`, `--version`

```text
L30: #   netclaw_pip_install <args...>                  # into NETCLAW_PY (default python3)
L31: #   NETCLAW_VENV=/path/to/.venv netclaw_pip_install <args...>   # into that venv
L32: #   netclaw_venv_create /path/to/.venv             # create a venv that actually works
L55: echo "NetClaw requires Python 3.10+ and the selected component's version bounds; unsupported interpreter: $1 ($("$1" --version 2>&1 || true))" >&2
L99: "$py" -m pip install --upgrade 'pip>=23' || return 1
L130: --root "$NETCLAW_DIR" --component "$NETCLAW_INSTALL_COMPONENT" || return 1
L151: if [ ! -x "$target/bin/python" ] || ! "$target/bin/python" -m pip --version >/dev/null 2>&1; then
L165: if ! "$py" -m pip --version >/dev/null 2>&1; then
L167: echo "  Remedy: $py -m ensurepip --upgrade   (or install the matching *-venv package)" >&2
L269: uv venv --seed --python "$base" "$dest" && return 0
```

## scripts/lib/preflight.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--arch`, `--components`, `--os`, `--python`, `--runtime`

```text
L7: case "$NETCLAW_ARCH" in aarch64) NETCLAW_ARCH=arm64 ;; amd64) NETCLAW_ARCH=x86_64 ;; esac
L42: python3 "$SCRIPT_DIR/installer-preflight.py" --os "$NETCLAW_OS" \
L43: --arch "$NETCLAW_ARCH" --python "$NETCLAW_PY" --components "$SELECTED" --runtime "${RUNTIME:-openclaw}"
```

## scripts/lib/render_md.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/lib/runtime-install.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--node`, `--npm`, `--prefix`, `--runtime`, `--version`

```text
L6: python3 "$policy" --runtime openclaw --node "$(node --version)" || return 1
L7: npm_options="$(python3 "$policy" --npm "$(npm --version)")" || return 1
L15: log_info "npm's global prefix is not writable; installing OpenClaw with --prefix $prefix"
L16: npm_args+=(--prefix "$prefix")
L20: log_info "For EACCES, use a user-owned Node version manager or npm --prefix \"\$HOME/.local\"."
L25: if ! command -v openclaw >/dev/null 2>&1 || ! openclaw --version; then
```

## scripts/lib/tui.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L21: # ANSI half-block rendering of netclaw.jpg — the lobster with its CCIE badge
L23: # lib/make-logo-art.py into lib/netclaw-logo.ans; shown on 256-color
L54: case "$rest" in
L59: *)    echo esc ;;
L62: case "$k" in
L65: k|K)     echo up ;;
L66: j|J)     echo down ;;
L67: a|A)     echo all ;;
L68: n|N)     echo none ;;
L69: q|Q)     echo quit ;;
L70: *)       echo "$k" ;;
L129: case "$key" in
L130: up)    cur=$(( (cur + total - 1) % total )) ;;
L131: down)  cur=$(( (cur + 1) % total )) ;;
L132: enter) TUI_CHOICE=$cur; printf '\033[?25h'; echo ""; return 0 ;;
L133: quit|esc) printf '\033[?25h'; echo ""; return 1 ;;
L200: case "$key" in
L201: up)
L205: down)
L209: space)
L211: all)
L213: none)
L215: enter)
L222: quit|esc)
```

## scripts/mcp-call.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--component`, `--list-tools`

```text
L4: Usage:
L106: if len(sys.argv) > 2 and sys.argv[1] == '--component':
L107: component = sys.argv.pop(2)
L108: sys.argv.pop(1)
L109: sys.argv.insert(1, component)
L110: if len(sys.argv) < 3:
L111: print(f"Usage: {sys.argv[0]} <server-command> <tool-name> [arguments-json]", file=sys.stderr)
L114: server_cmd = sys.argv[1]
L115: tool_name = sys.argv[2]
L117: if len(sys.argv) > 3:
L119: args_json = json.loads(sys.argv[3])
```

## scripts/mcp-probe.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/measure-turn-latency.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--json`, `--no-pager`, `--phone-sample-size`, `--since`, `--user`

```text
L143: argparse.ArgumentParser(description=__doc__)
L144: parser.add_argument("--phone-sample-size", type=int, default=20,
                         help="Number of recent phone-originated turns to sample (default 20, "
                              "matching the spec's original sample)")
L147: parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
L17: Usage:
```

## scripts/memory-enable.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--from`, `--help`, `--quiet`

```text
L4: # Usage: ./scripts/memory-enable.sh
L36: uv pip install -e . --quiet 2>/dev/null || {
L51: "args": ["--from", "netclaw-memory-mcp", "memory-mcp-server"],
L69: echo "To test: uvx --from netclaw-memory-mcp memory-mcp-server --help"
```

## scripts/mempalace-stdio.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L19: os.execv(python, [python, '-m', 'mempalace.mcp_server', *sys.argv[1:]])
```

## scripts/migrate-change-gates.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--env-file`, `--restore`

```text
L48: argparse.ArgumentParser(description=__doc__)
L48: p.add_argument('--env-file',default=str(Path.home()/'.openclaw/.env'))
L49: p.add_argument('--apply',action='store_true')
L49: p.add_argument('--restore',action='store_true')
```

## scripts/migrate-hud-access.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--api-port`, `--connect`, `--ssh-target`, `--ui-port`

```text
L32: argparse.ArgumentParser(description=__doc__)
L33: p.add_argument('--ssh-target', required=True, type=ssh_target)
L34: p.add_argument('--ui-port', type=tcp_port, default=3000, help='same local/remote HUD_UI_PORT (default 3000)')
L35: p.add_argument('--api-port', type=tcp_port, default=3001, help='same local/remote HUD_PORT (default 3001)')
L36: p.add_argument('--connect', action='store_true', help='open the tunnel; otherwise preview only')
```

## scripts/migrate-in2n-transport.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--bind`, `--ca-file`, `--cert`, `--env-file`, `--key`, `--restore`

```text
L53: argparse.ArgumentParser(description=__doc__)
L54: p.add_argument('--env-file',default=str(Path.home()/'.openclaw/.env'))
L55: p.add_argument('--bind',default='127.0.0.1')
L55: p.add_argument('--cert')
L55: p.add_argument('--key')
L55: p.add_argument('--ca-file')
L56: p.add_argument('--apply',action='store_true')
L56: p.add_argument('--restore',action='store_true')
```

## scripts/migrate-integration-tls.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--ca-bundle`, `--env-file`, `--lab-insecure`, `--restore`, `--service`

```text
L46: argparse.ArgumentParser(description=__doc__)
L47: p.add_argument('--env-file',default=str(Path.home()/'.openclaw/.env'))
L48: p.add_argument('--service',choices=('redfish','nautobot','anta'),default='redfish')
L49: p.add_argument('--ca-bundle')
L49: p.add_argument('--lab-insecure',action='store_true')
L50: p.add_argument('--apply',action='store_true')
L50: p.add_argument('--restore',action='store_true')
```

## scripts/migrate-local-file-permissions.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--journal`, `--path`, `--restore`

```text
L76: argparse.ArgumentParser(description=__doc__)
L77: parser.add_argument('--path', action='append', help='Override default target set; may repeat')
L78: parser.add_argument('--journal', default=str(home / 'local-permissions-backup.json'))
L79: parser.add_argument('--apply', action='store_true')
L80: parser.add_argument('--restore', action='store_true')
```

## scripts/migrate-pyats-http.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--env-file`, `--repo`, `--restore`, `--upstream`, `--venv`

```text
L53: argparse.ArgumentParser(description=__doc__)
L54: ap.add_argument('--env-file',default=str(Path.home()/'.openclaw/.env'))
L55: ap.add_argument('--repo',default=str(Path(__file__).resolve().parents[1]))
L56: ap.add_argument('--venv',default=str(Path.home()/'.openclaw/pyats-venv'))
L57: ap.add_argument('--upstream',help='Explicit verified managed server script; legacy repo path remains the default')
L58: ap.add_argument('--apply',action='store_true')
L58: ap.add_argument('--restore',action='store_true')
```

## scripts/migrate-ssh-trust.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--env-file`, `--known-hosts`, `--restore`

```text
L55: argparse.ArgumentParser(description=__doc__)
L56: parser.add_argument('--env-file', default=str(Path.home() / '.openclaw/.env'))
L57: parser.add_argument('--known-hosts')
L58: parser.add_argument('--apply', action='store_true')
L59: parser.add_argument('--restore', action='store_true')
```

## scripts/migrate-tls-registration.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--config`, `--repo`, `--restore`

```text
L61: argparse.ArgumentParser(description=__doc__)
L62: parser.add_argument('--config', default=str(Path.home() / '.openclaw/openclaw.json'))
L63: parser.add_argument('--repo', default=str(Path(__file__).resolve().parent.parent))
L64: parser.add_argument('--apply', action='store_true')
L65: parser.add_argument('--restore', action='store_true')
```

## scripts/migrate-voice-auth.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--env-file`, `--public-url`, `--restore`

```text
L148: argparse.ArgumentParser(description=__doc__)
L149: parser.add_argument('--env-file', default='.env')
L150: parser.add_argument('--public-url')
L151: parser.add_argument('--apply', action='store_true')
L152: parser.add_argument('--restore', action='store_true')
```

## scripts/migrate-zoom-auth.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--env-file`, `--restore`

```text
L43: argparse.ArgumentParser(description=__doc__)
L43: p.add_argument('--env-file',default=str(Path.home()/'.openclaw/.env'))
L44: p.add_argument('--apply',action='store_true')
L44: p.add_argument('--restore',action='store_true')
```

## scripts/mobile-release-archive.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--upload-app`

```text
L4: # Produces an App Store Connect-ready .ipa from mobile/netclaw-mobile's
L7: # Usage: ./scripts/mobile-release-archive.sh
L12: #   - mobile/netclaw-mobile/ExportOptions.plist's teamID filled in
L31: # Apple Developer Program under the SAME team ID (A49777FMJG) -- common for
L59: # Sensitive Notifications -- specs 111/114) and the widget extension target
L70: echo -e "${YELLOW}Next:${NC} upload via Transporter or 'xcrun altool --upload-app', then complete"
```

## scripts/netclaw

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--break-system-packages`, `--edge`, `--get`, `--help`, `--log`, `--log-format`, `--max-time`, `--since`, `--systemd`, `--tui`, `--user`, `--watch`

```text
L2: # netclaw — top-level NetClaw command.
L4: #   netclaw                 interactive menu (TUI launcher, installer, peering)
L5: #   netclaw tui             open the NetClaw chat TUI (openclaw tui)
L6: #   netclaw install [...]   run the component installer (flags pass through)
L7: #   netclaw peering [status|bgp|n2n|ngrok]    protocol peering status (non-interactive)
L8: #   netclaw peering up|down                   start/stop daemon + ngrok together
L9: #   netclaw peering announce                  print an endpoint message to relay to peers
L10: #   netclaw chats [id]       list N2N chat sessions, or tail one
L11: #   netclaw chats --watch    live-watch for new sessions/lines (Ctrl+C to stop)
L12: #   netclaw link            (re)create the ~/.local/bin/netclaw symlink
L15: #   netclaw risk enroll-mobile [device-label]     one command: checks, promotes to
L17: #   netclaw risk role border <risk-name> [in2n]   promote standalone → Border
L18: #   netclaw risk edge-check                       preflight every precondition
L19: #   netclaw risk token --edge <device-label>       mint the single-use QR
L20: #   See mobile/netclaw-mobile/MOBILE-ONBOARDING.md for the full procedure.
L44: # here so `netclaw tui` and .env reads follow the chosen runtime.
L47: RUNTIME_CMD="hermes"; RUNTIME_HOME="${HERMES_HOME:-$HOME/.hermes}"; RUNTIME_TUI=(hermes --tui)
L62: api_get() { curl -s --max-time 3 "$BGP_API$1" 2>/dev/null || true; }
L71: curl -s --max-time 30 -H 'Content-Type: application/json' -d "$body" "$BGP_API$1" 2>/dev/null || true
L74: ngrok_get() { curl -s --max-time 3 "$NGROK_API$1" 2>/dev/null || true; }
L81: # and looking at only the first file made `netclaw risk token --edge` fail with
L87: v="$(python3 "$NETCLAW_ROOT/scripts/write-env.py" --get "$f" "$1")" || return 1
L98: # 2026-08-19: `netclaw risk role border` succeeds (POST 200, `risk status`
L107: printf '%s' "$val" | python3 "$NETCLAW_ROOT/scripts/write-env.py" --systemd "$f" "$key"
L127: setsid nohup ngrok tcp "$port" --log /tmp/ngrok-mesh.log --log-format json \
L459: echo -e "  ${T_DIM}--- $(basename "$f" .txt) ---${T_NC}"
L484: case " ${days[*]-} " in *" $d "*) ;; *) days+=("$d") ;; esac
L497: case "$TUI_CHOICE" in
L498: 0) chats_watch; continue ;;
L499: 1) chat_tail "${CHAT_FILES[0]}"; continue ;;
L625: case "$role" in
L626: standalone|border|member) ;;
L627: *) echo "usage: netclaw risk role <standalone|border|member> [risk-name] [stacks]"
L651: case "$stacks" in
L652: in2n|both) ;;
L653: *) echo "  note: enabled_stacks='$stacks' does not include in2n —"
L670: print("    check:  systemctl --user status netclaw-mesh.service")
L686: echo "      systemctl --user restart netclaw-mesh.service"
L706: echo "                systemctl --user status netclaw-mesh.service"
L721: case "$stacks" in
L722: in2n|both) echo "  ✓ stack     : $stacks (in2n enabled)" ;;
L723: *) echo "  ✗ stack     : ${stacks:--} — the edge listener needs in2n"
L756: echo "                $mesh_py -m pip install --break-system-packages$missing"
L773: case "$lstate" in
L774: listening) echo "  ✓ listener  : bound" ;;
L776: *)         echo "  ✗ listener  : $lstate${lerr:+ — $lerr}"
L797: echo "                journalctl --user -u netclaw-mesh.service --since '2 min ago' | grep -i Edge"
L818: wan="$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || true)"
L833: echo "      $(basename "$0") risk token --edge <device-label>"
L836: echo "      systemctl --user restart netclaw-mesh.service"
L898: # (edge-check -> role border -> restart -> edge-check -> token --edge),
L910: # abort the WHOLE netclaw invocation right here, silently swallowed
L937: if systemctl --user restart netclaw-mesh.service 2>/dev/null; then
L941: echo "      systemctl --user restart netclaw-mesh.service"
L981: case "$TUI_CHOICE" in
L982: 0) risk_overview; pause ;;
L983: 1) risk_members; pause ;;
L984: 2) risk_health; pause ;;
L985: 3) risk_token; pause ;;
L986: 4) risk_edge_token; pause ;;
L987: 5) risk_edge_check; pause ;;
L988: 6) return 0 ;;
L1007: case "$TUI_CHOICE" in
L1008: 0) peering_overview; pause ;;
L1009: 1) peering_bgp; pause ;;
L1010: 2) peering_n2n; pause ;;
L1011: 3) peering_ngrok; pause ;;
L1012: 4) chats_menu ;;
L1013: 5) peering_start_all; pause ;;
L1014: 6) peering_stop_all; pause ;;
L1015: 7) peer_announce; pause ;;
L1016: 8) return 0 ;;
L1035: case "$TUI_CHOICE" in
L1036: 0) exec "${RUNTIME_TUI[@]}" ;;
L1037: 1) exec "$NETCLAW_ROOT/scripts/install.sh" ;;
L1038: 2) peering_menu ;;
L1039: 3) risk_menu ;;
L1040: 4) exit 0 ;;
L1053: case "${1:-}" in
L1055: tui)       exec "${RUNTIME_TUI[@]}" ;;
L1056: install)   shift; exec "$NETCLAW_ROOT/scripts/install.sh" "$@" ;;
L1057: peering)
L1058: case "${2:-status}" in
L1059: status)   peering_overview ;;
L1060: bgp)      peering_bgp ;;
L1061: n2n)      peering_n2n ;;
L1062: ngrok)    peering_ngrok ;;
L1063: up)       peering_start_all ;;
L1064: down)     peering_stop_all ;;
L1065: announce) peer_announce ;;
L1066: *)        echo "Usage: netclaw peering [status|bgp|n2n|ngrok|up|down|announce]"; exit 1 ;;
L1068: risk)
L1069: case "${2:-status}" in
L1070: status)   risk_overview ;;
L1071: members)  risk_members ;;
L1072: health)   risk_health ;;
L1073: add)      risk_add "${3:-}" "${4:-}" "${5:-}" ;;
L1074: remove)   risk_remove "${3:-}" ;;
L1075: role)     risk_role "${3:-}" "${4:-}" "${5:-}" ;;
L1076: edge-check|edge_check|preflight) risk_edge_check ;;
L1077: token)
L1078: if [ "${3:-}" = "--edge" ]; then
L1083: enroll-mobile|enroll_mobile) risk_enroll_mobile "${3:-}" ;;
L1084: route)    risk_route "${3:-}" "${4:-}" ;;
L1085: *)        echo "Usage: netclaw risk [status|members|health|role|edge-check|add|remove|token [--edge]|enroll-mobile [label]|route]"; exit 1 ;;
L1087: chats)
L1088: if [ "${2:-}" = "--watch" ] || [ "${2:-}" = "watch" ]; then
L1100: link)      do_link ;;
L1101: help|-h|--help)
L1103: *) echo "Unknown command: $1 (try: netclaw help)"; exit 1 ;;
```

## scripts/netclaw-secure-start.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--enable-guardrail`, `--from`, `--mode`, `--name`, `--policy`, `--version`, `--wait`

```text
L5: # Usage:
L6: #   ./scripts/netclaw-secure-start.sh          # Start everything
L7: #   ./scripts/netclaw-secure-start.sh stop     # Stop everything
L8: #   ./scripts/netclaw-secure-start.sh status   # Check status
L146: RUN openclaw --version
L150: openshell sandbox create --name "$SANDBOX_NAME" --from /tmp/netclaw-sandbox > /tmp/sandbox-build.log 2>&1 &
L715: if openshell policy set "$SANDBOX_NAME" --policy /tmp/netclaw-sandbox-policy.yaml --wait 2>&1; then
L867: defenseclaw init --enable-guardrail 2>/dev/null || true
L1024: echo "    defenseclaw setup guardrail --mode action"
L1036: case "${1:-start}" in
L1037: start)
L1040: stop)
L1043: status)
L1046: *)
L1047: echo "Usage: $0 {start|stop|status}"
```

## scripts/normalize-mcp-cwd.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--config`, `--dry-run`, `--repo`

```text
L51: argparse.ArgumentParser()
L52: ap.add_argument("--config", required=True)
L53: ap.add_argument("--repo", required=True)
L54: ap.add_argument("--dry-run", action="store_true")
L20: Usage:
```

## scripts/openclaw-to-hermes-mcp.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--config`, `--env`, `--repo`, `--sidecar`, `--source`

```text
L174: argparse.ArgumentParser(description=__doc__)
L175: ap.add_argument("--source", required=True, help="path to config/openclaw.json")
L176: ap.add_argument("--repo", required=True, help="NetClaw repo root (for absolute paths)")
L177: ap.add_argument("--env", default="", help="shared .env for ${VAR} resolution")
L178: ap.add_argument("--config", required=True, help="target ~/.hermes/config.yaml")
L179: ap.add_argument("--sidecar", default="", help="fallback file if config.yaml already has mcp_servers")
L23: Usage:
```

## scripts/pal-prepare-agent.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--enable-http`, `--home`

```text
L56: argparse.ArgumentParser(description=__doc__)
L57: parser.add_argument("--home",type=Path,default=Path(os.environ.get("OPENCLAW_HOME",str(Path.home()/".openclaw"))))
L58: parser.add_argument("--apply",action="store_true")
L59: parser.add_argument("--enable-http",action="store_true",help="Also enable the authenticated local chat compatibility endpoint")
```

## scripts/pal-settings.mjs

Node entry point; argument/source references only. npm wrapper commands are indexed separately.

Flags mentioned: `--face`, `--free-plan-confirmed`

```text
L13: const [command,...args]=process.argv.slice(2);
L19: if(args.length!==3 || args[0]!=='--face' || args[2]!=='--free-plan-confirmed') throw Error('Usage: provision --face STOCK_ID --free-plan-confirmed. Check account eligibility first; no upgrade is performed.');
L27: } else console.log('Usage: node scripts/pal-settings.mjs status|faces|provision --face STOCK_ID --free-plan-confirmed|verify');
```

## scripts/patch-claw-certs.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--all`, `--dns-provider`, `--domain`, `--enforce`, `--ff-only`, `--max-time`, `--no-legend`, `--systemd`, `--type`, `--user`, `--yes`

```text
L4: #   scripts/patch-claw-certs.sh [--domain <name>] [--dns-provider <id>] [--enforce] [--yes]
L20: case "$1" in
L21: --domain) DOMAIN="$2"; shift 2 ;;
L22: --dns-provider) PROVIDER="$2"; shift 2 ;;
L23: --enforce) ENFORCE="enforce"; shift ;;
L24: --yes|-y) ASSUME_YES=1; shift ;;
L25: *) echo "unknown arg: $1" >&2; exit 1 ;;
L31: # --- state counts BEFORE (integrity check) ---
L53: # --- 1. pull the release ---
L56: git -C "$REPO" pull --ff-only || say "WARN: git pull skipped (dirty tree or offline)"
L59: # --- 2. lego (only needed for the domain-verified path) ---
L64: # --- 3. migrate schema + generate credentials (opening the manager runs the
L65: #        additive v3 migration; RiskManager.ensure_risk_ca creates the CA) ---
L89: # --- 4. env: turn on secured channels ---
L90: # IMPORTANT: the systemd --user mesh daemon reads its own EnvironmentFile (feature
L95: ENVF="$(systemctl --user cat netclaw-mesh.service 2>/dev/null \
L101: printf '%s' "$2" | python3 "$REPO/scripts/write-env.py" --systemd "$ENVF" "$1"
L108: # --- 5. restart services in dependency order (feature 057) ---
L109: if command -v systemctl >/dev/null && systemctl --user list-units >/dev/null 2>&1; then
L111: systemctl --user restart openclaw-gateway.service 2>/dev/null || true
L112: systemctl --user restart netclaw-mesh.service 2>/dev/null || true
L113: for u in $(systemctl --user list-units --type=service --all --no-legend 'netclaw-member-*' 2>/dev/null | awk '{print $1}'); do
L114: systemctl --user restart "$u" 2>/dev/null || true
L117: say "no systemd --user manager — restart the daemon manually to apply"
L120: # --- 6. integrity check + posture ---
L129: if curl -s --max-time 3 http://127.0.0.1:8179/n2n/certs >/dev/null 2>&1; then
```

## scripts/peering-launch.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L20: env = environment(sys.argv[1])
L23: os.execve(sys.executable, [sys.executable, sys.argv[2]], env)
```

## scripts/peering-setup.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--get`

```text
L19: # TTY-aware yes/no (spec 119) -- this file's own ask()/ask_yn() below always
L34: python3 "$SCRIPT_DIR/write-env.py" --get "$OPENCLAW_ENV" "$1"
L56: case "$input" in
L59: *) echo -e "  ${YELLOW}Please answer y or n.${NC}" ;;
L139: case "${1:-}" in
L140: start)  daemon_start;  exit 0 ;;
L141: stop)   daemon_stop;   exit 0 ;;
L142: status) daemon_status; exit 0 ;;
L144: *) echo "Usage: $0 [start|stop|status]"; exit 1 ;;
L246: # Only worth asking once the mesh daemon is actually up -- an enrollment
L248: # running. Delegates entirely to `netclaw risk enroll-mobile` rather than
L255: # finished -- only this bonus step should stop, not the whole wizard.
```

## scripts/prepare-release.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--bump`, `--check`, `--spec`

```text
L82: argparse.ArgumentParser(description=__doc__)
L84: mode.add_argument("--bump", choices=("minor", "patch"))
L85: mode.add_argument("--check", action="store_true", help="Validate current version, notes and changelog")
L86: parser.add_argument("--spec", help="Number of the completed spec, e.g. 130")
L87: parser.add_argument("--apply", action="store_true", help="Write prepared files (default: preview only)")
```

## scripts/probe-mist-mcp.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--count`

```text
L157: if "--count" in sys.argv:
```

## scripts/pyats-stdio.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--add`

```text
```

## scripts/reconcile-mcp.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--help`, `--json`, `--quiet`, `--refresh`, `--surface`, `--warn-only`

```text
L144: argparse.ArgumentParser(
        description="Reconcile NetClaw's MCP registration surfaces.",
        epilog="Exit 0 = reconciled, 1 = inconsistent, 2 = check could not run.",
    )
L148: parser.add_argument("--surface", action="append", choices=sorted(SURFACES),
                        help="run only this surface (repeatable; default: all)")
L150: parser.add_argument("--warn-only", action="store_true",
                        help="print findings but always exit 0 (never use in CI)")
L152: parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit machine-readable results")
L154: parser.add_argument("--quiet", action="store_true",
                        help="suppress passing surfaces; print findings only")
```

## scripts/register-all-mcps.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--args`, `--command`, `--dry-run`, `--mcp-dir`, `--skip-scan`

```text
L72: argparse.ArgumentParser(description="Register ALL MCPs with DefenseClaw")
L73: parser.add_argument("--dry-run", action="store_true", help="Show commands without executing")
L74: parser.add_argument("--skip-scan", action="store_true", help="Skip security scan when registering")
L75: parser.add_argument("--mcp-dir", default="mcp-servers", help="MCP servers directory")
L7: Usage:
```

## scripts/register-mcps-with-defenseclaw.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--args`, `--command`, `--dry-run`, `--env`, `--filter`, `--skip-scan`, `--url`

```text
L65: argparse.ArgumentParser(description="Register MCPs with DefenseClaw")
L66: parser.add_argument("--dry-run", action="store_true", help="Show commands without executing")
L67: parser.add_argument("--skip-scan", action="store_true", help="Skip security scan when registering")
L68: parser.add_argument("--filter", help="Only register MCPs matching this prefix")
L7: Usage:
```

## scripts/run-contract-tests.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--json`, `--list`, `--matrix`, `--prepare`, `--python`, `--strict-capabilities`, `--suite`

```text
L809: argparse.ArgumentParser(description=__doc__)
L811: mode.add_argument("--list", action="store_true", help="list declared suites")
L812: mode.add_argument("--matrix", action="store_true", help="emit a GitHub Actions matrix")
L813: mode.add_argument("--suite", metavar="ID", help="suite id or 'all'")
L814: parser.add_argument("--prepare", action="store_true", help="prepare isolated dependencies before running")
L815: parser.add_argument("--strict-capabilities", action="store_true",
                        help="treat optional live/Docker gaps as exit 2")
L817: parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
L530: code = "import importlib.util,sys; missing=[x for x in sys.argv[1:] if importlib.util.find_spec(x) is None]; print('\\n'.join(missing))"
```

## scripts/runtime-policy.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--allow-scripts`, `--node`, `--npm`, `--runtime`

```text
L37: argparse.ArgumentParser(description=__doc__)
L38: parser.add_argument('--runtime', choices=['openclaw', 'hermes'], default='openclaw')
L39: parser.add_argument('--node')
L40: parser.add_argument('--npm')
```

## scripts/runtime-selection.mjs

Node entry point; argument/source references only. npm wrapper commands are indexed separately.

Flags mentioned: `--fixture`

```text
L81: if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
L83: if (process.argv[2] === '--fixture') {
```

## scripts/runtime-selection.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--field`

```text
L42: if len(sys.argv) == 3 and sys.argv[1] == '--field': print(value[sys.argv[2]])
```

## scripts/scan-all-mcp-source.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--json`, `--mcp-dir`, `--output`

```text
L215: argparse.ArgumentParser(description="Static security scan of MCP source code")
L216: parser.add_argument("--output", "-o", help="Output file (default: stdout)")
L217: parser.add_argument("--json", action="store_true", help="Output as JSON")
L218: parser.add_argument("--mcp-dir", default="mcp-servers", help="MCP servers directory")
L7: Usage:
```

## scripts/scan-all-mcps.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L42: echo "---" >> "$OUTPUT"
```

## scripts/scan-mcp-files.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/scan-mcp-source.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--json`

```text
L41: if result=$(defenseclaw skill scan "$server_dir" --json 2>&1); then
L93: echo "---" >> "$OUTPUT"
```

## scripts/setup-gait-runtime.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--component`, `--preview`, `--python`, `--rebuild`, `--restore`, `--root`, `--target`

```text
L107: argparse.ArgumentParser(description=__doc__)
L108: parser.add_argument('--restore', action='store_true')
L109: parser.add_argument('--preview', action='store_true')
L110: parser.add_argument('--rebuild', action='store_true')
L111: parser.add_argument('--target', default=os.environ.get('GAIT_VENV', str(Path.home() / '.openclaw/gait-venv')))
L112: parser.add_argument('--python', default=os.environ.get('NETCLAW_PY', sys.executable))
L78: "import sys, asyncio; sys.path.insert(0, sys.argv[1]); "
```

## scripts/setup-profile.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--template`

```text
L72: argparse.ArgumentParser(description=__doc__)
L73: parser.add_argument('kind', choices=['identity','voice'])
L74: parser.add_argument('path', type=Path)
L75: parser.add_argument('--template', type=Path)
```

## scripts/setup-pyats-runtime.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--detach`, `--no-checkout`, `--preview`, `--python`, `--rebuild`, `--restore`, `--target`

```text
L103: argparse.ArgumentParser(description=__doc__)
L104: parser.add_argument('--target', default=os.environ.get('PYATS_VENV', str(Path.home()/'.openclaw/pyats-venv')))
L105: parser.add_argument('--python', default=os.environ.get('PYATS_PYTHON', '3.12'))
L106: parser.add_argument('--preview', action='store_true')
L107: parser.add_argument('--restore', action='store_true')
L108: parser.add_argument('--rebuild', action='store_true')
```

## scripts/setup.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--new`, `--template`, `--tui`

```text
L74: # components was installed (per ~/.openclaw/netclaw-components.conf).
L170: # --- NetBox ---
L183: # --- Nautobot ---
L199: # --- OpsMill Infrahub ---
L219: # --- Infoblox DDI ---
L234: # --- Itential Automation Platform ---
L251: # --- Juniper JunOS ---
L265: # --- Arista CloudVision ---
L281: # --- ServiceNow ---
L296: # --- Cisco ACI ---
L311: # --- Cisco ISE ---
L326: # --- F5 BIG-IP ---
L345: # --- Catalyst Center ---
L360: # --- NVD CVE ---
L376: # --- Microsoft Graph (Office 365) ---
L400: # --- GitHub ---
L418: # --- Cisco Modeling Labs (CML) ---
L442: # --- Cisco NSO ---
L469: # --- Equinix Fabric + Network Edge ---
L492: # --- AWS Cloud ---
L511: # --- Google Cloud Platform ---
L536: # --- Cisco Meraki ---
L555: # --- Cisco FMC (Secure Firewall) ---
L579: # --- Palo Alto Panorama ---
L594: # --- FortiManager ---
L609: # --- Ansible Automation Platform (AAP) ---
L629: # --- Cisco ThousandEyes ---
L646: # --- Cisco RADKit ---
L665: # --- ContainerLab ---
L693: # --- HumanRail ---
L711: # --- Cisco WebEx ---
L795: --template "$NETCLAW_DIR/config/twilio-voice.json.example"
L894: echo -e "    ${CYAN}hermes chat${NC}              # or: hermes --tui"
L901: echo -e "    ${CYAN}openclaw chat --new${NC}       # Terminal 2"
```

## scripts/test-install-pyats-genie.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--isolated`, `--prefix`, `--upgrade`

```text
```

## scripts/test-prepare-release.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/trace-skill.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--json`

```text
L47: argparse.ArgumentParser(description=__doc__.split("\n")[0])
L48: parser.add_argument("skill", help="skill directory name under workspace/skills/")
L49: parser.add_argument("--json", action="store_true", dest="as_json")
```

## scripts/twilio_install.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--template`

```text
L166: printf '%s\0%s\0' "$whitelist_phone" "$whitelist_label" | python3 "$NETCLAW_DIR/scripts/setup-profile.py" voice "$CONFIG_FILE" --template "$NETCLAW_DIR/config/twilio-voice.json.example"
```

## scripts/twitter_install.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/twitter_oauth2_setup.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
L8: Usage:
```

## scripts/upgrade-hud.sh

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--apply`, `--check`, `--help`, `--input-type`, `--install-deps`, `--repo`

```text
L9: Usage: scripts/upgrade-hud.sh [--check | --apply] [--install-deps] [--repo PATH]
L10: --check         Check source, prerequisites and installed dependencies (default).
L11: --apply         Regenerate references and build all four HUD entry points.
L12: --install-deps  Run npm ci from the lockfile before building; requires --apply.
L13: --repo PATH     Use another existing NetClaw checkout.
L14: -h, --help      Show this help.
L23: case "$1" in
L24: --check) HUD_UPGRADE_APPLY=false ;;
L25: --apply) HUD_UPGRADE_APPLY=true ;;
L26: --install-deps) HUD_UPGRADE_INSTALL=true ;;
L27: --repo) [[ $# -ge 2 ]] || { echo 'Missing --repo path' >&2; exit 2; }; HUD_UPGRADE_ROOT="$2"; shift ;;
L28: -h|--help) usage; exit 0 ;;
L29: *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
L34: echo '--install-deps requires --apply; check mode never installs packages.' >&2
L55: (cd "$HUD_UPGRADE_UI" && node --input-type=module -e 'await import("vite"); await import("react"); await import("three");') || {
L56: echo 'HUD dependencies unavailable. Review --apply --install-deps.' >&2; exit 1;
L60: echo 'Check complete. No files or services changed. Use --apply to build this checkout.'
```

## scripts/verify-catalog-coverage.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/verify-inventory-counts.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## scripts/verify-spec-artifacts.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--specs-dir`, `--warn-only`

```text
L117: argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
L119: ap.add_argument("--warn-only", action="store_true",
                    help="report findings but exit 0")
L121: ap.add_argument("--specs-dir", default=os.path.join(REPO_ROOT, "specs"),
                    help="directory of spec folders (default: <repo>/specs)")
L28: Usage:
```

## scripts/write-env.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: `--get`, `--systemd`

```text
L92: systemd = '--systemd' in sys.argv
L94: sys.argv.remove('--systemd')
L95: if sys.argv[1] == '--get':
L96: print(values(Path(sys.argv[2]).read_text()).get(sys.argv[3], ''), end='')
L98: update(sys.argv[1], sys.argv[2], sys.stdin.read(), systemd=systemd)
```

## scripts/zabbix-stdio.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## ui/netclaw-visual/genie_parse.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

## ui/netclaw-visual/package.json

All package.json script commands. Arguments after -- are delegated to the underlying command.

Flags mentioned: none

```text
L1: npm run dev → concurrently "node server.js" "vite"
L1: npm run server → node server.js
L1: npm run build → vite build
L1: npm run preview → vite preview
L1: npm run test → node scripts/run-unit-tests.mjs
L1: npm run test:bundle → npm run build && node scripts/check-canvas-bundle.mjs
L1: npm run test:canvas → node test/run-canvas.mjs
L1: npm run test:terminal → node test/terminal-smoke.mjs
L1: npm run test:testbed → node test/testbed-editor.mjs
L1: npm run test:enrichment → node test/terminal-enrichment.mjs
L1: npm run test:enrichment-layout → node test/enrichment-layout.mjs
L1: npm run test:terminal-selection → node test/terminal-mouse-coordinates.mjs
L1: npm run test:topology → node test/topology.mjs
L1: npm run test:topology-facts → node test/topology-facts.mjs
L1: npm run test:topology-closest → node test/topology-closest.mjs
L1: npm run test:topology-api → node test/topology-api.mjs
L1: npm run test:ssh-policy → node test/terminal-ssh-policy.mjs
L1: npm run test:terminal-local → node test/terminal-local-request.mjs
L1: npm run test:terminal-credentials → node test/terminal-credentials.mjs
L1: npm run test:intent → node test/terminal-intent.mjs
L1: npm run test:intent-execution → node test/terminal-intent-execution.mjs
L1: npm run test:intent-live → node test/terminal-intent-live.mjs
L1: npm run test:intent-live-ui → node test/terminal-intent-live-ui.mjs
L1: npm run test:change-policy → node test/terminal-change-policy.mjs
L1: npm run test:artifacts → node test/artifact-formats.mjs
L1: npm run test:genie → node test/genie-parser.mjs
L1: npm run test:observability → node test/observability.mjs
```

## ui/netclaw-visual/server.js

Node entry point; argument/source references only. npm wrapper commands are indexed separately.

Flags mentioned: `--global`

```text
```

## ui/netclaw-visual/src/dashboard/preview-build.mjs

Node entry point; argument/source references only. npm wrapper commands are indexed separately.

Flags mentioned: none

```text
L10: const output = process.argv[2] || '/tmp/netclaw-hud127-preview.html';
```

## ui/netclaw-visual/test/genie_adapter_test.py

Static source declarations; lexical flags may include delegated commands. No execution performed.

Flags mentioned: none

```text
```

