#!/usr/bin/env python3
"""iN2N claw profiles — derived from the installed skill catalog (feature 056).

A "profile" is a focused bundle of skills that gives a member claw its specialty
(CML claw, pyATS claw, …). Profiles are derived by PREFIX/keyword match against
the live `workspace/skills/` tree so they never drift from what is actually
installed (FR-019). Every member also gets the mandatory base floor (FR-021a),
which is emitted tagged `base` and excluded from routing specificity (FR-021b).

Usage:
    python3 scripts/in2n-profiles.py list                 # profiles + skill counts
    python3 scripts/in2n-profiles.py show cml             # skills in the cml profile
    python3 scripts/in2n-profiles.py scope cml            # JSON scope (base + specialty)
    python3 scripts/in2n-profiles.py scope custom a,b,c   # custom skill set
    python3 scripts/in2n-profiles.py spec member.json [--border-config PATH] [--allow-dangerous-tools]
                                                          # validate a member spec (spec 184)
No third-party deps (stdlib only), matching scripts/register-all-mcps.py.
"""

import copy
import json
from urllib.parse import urlsplit
import importlib.util
from pathlib import Path
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(REPO,'mcp-servers/protocol-mcp'))
from bgp.federation.runtime import selected
_RUNTIME=selected()
DEFAULT_SKILLS_DIRS = [str(_RUNTIME.skills)] if _RUNTIME.kind=='hermes' else [os.path.join(REPO,'workspace','skills'),str(_RUNTIME.skills)]


# The mandatory base floor every member carries (mirror of bgp/federation/risk.py
# BASE_FLOOR — kept here so the installer/profile tool has no cross-import).
BASE_FLOOR = [
    {"name": "n2n-member-runtime", "type": "skill", "tier": "base"},
    {"name": "self-status",        "type": "skill", "tier": "base"},
    {"name": "member_heartbeat",   "type": "tool",  "tier": "base"},
    {"name": "member_report_audit","type": "tool",  "tier": "base"},
]

ENV_FILE = str(_RUNTIME.env_file)

# Profile definitions: skills (prefixes/exact) + `requires_env` (any-of). A
# profile is offered ONLY when its skills are installed AND its backend is
# configured — never advertise a member you cannot actually run. Profiles with
# no `requires_env` run locally and are always offered when their skills exist.
# Granularity principle (interview): ONE claw per vendor/platform/tool. Real
# integrations each get a dedicated, env-gated member; only UTILITIES stay grouped.
PROFILE_MATCHERS = {
    "convergence": {"exact": ["convergence-observations"],
                    "requires_env": ["CONVERGENCE_ENABLED", "CONVERGENCE_API_URL", "CONVERGENCE_API_TOKEN", "CONVERGENCE_SITE", "CONVERGENCE_EXPORTERS"],
                    "desc": "Convergence retained flow evidence for Border investigation"},
    "subnet": {"exact": ["subnet-calculator"], "desc": "Qualified read-only IPv4 subnet calculation"},
    # ── virtual environments / labs (each dedicated) ──
    "cml":          {"prefixes": ["cml-"], "requires_env": ["CML_URL"],
                     "desc": "Cisco Modeling Labs"},
    "eve-ng":       {"prefixes": ["eve-ng-", "eve-lab-"], "requires_env": ["EVE_NG_HOST", "EVENG_HOST"],
                     "desc": "EVE-NG lab environment"},
    "gns3":         {"prefixes": ["gns3-"], "requires_env": ["GNS3_HOST", "GNS3_URL"],
                     "desc": "GNS3 lab environment"},
    "containerlab": {"prefixes": ["clab-"], "requires_env": ["CLAB_MCP_SCRIPT"],
                     "desc": "Containerlab environment"},
    # ── test ──
    "pyats":    {"prefixes": ["pyats-"], "requires_env": ["PYATS_MCP_SCRIPT"],
                 "desc": "pyATS static/dynamic inventory; validate and activate inventory separately"},
    # ── assurance / analysis (each dedicated) ──
    "ipfabric": {"exact": ["ipfabric"], "requires_env": ["IPFABRIC_HOST"],
                 "desc": "IP Fabric network assurance"},
    "suzieq":   {"exact": ["suzieq-observability"], "desc": "SuzieQ network observability"},
    "batfish":  {"exact": ["batfish-config-analysis", "batfish-intent-validation"],
                 "desc": "Batfish config analysis + intent validation"},
    "forward":  {"exact": ["forward"], "requires_env": ["FORWARD_AUTH_BASE64"],
                 "desc": "Forward Networks path analysis"},
    "gtrace":   {"prefixes": ["gtrace-"], "requires_env": ["GTRACE_MCP_BIN"],
                 "desc": "gTrace IP path analysis + enrichment"},
    "packet":   {"exact": ["packet-analysis", "kubeshark-traffic"],
                 "requires_env": ["PACKET_BUDDY_MCP_SCRIPT"],
                 "desc": "Packet (pcap) capture + analysis"},
    # ── automation / orchestration (each dedicated) ──
    "itential": {"exact": ["itential-automation"], "requires_env": ["ITENTIAL_MCP_PLATFORM_HOST"],
                 "desc": "Itential Platform automation"},
    "aap":      {"prefixes": ["aap-"], "requires_env": ["AAP_MCP_DIR", "AAP_MCP_ANSIBLE_SCRIPT"],
                 "desc": "Ansible Automation Platform + EDA + lint"},
    "nso":      {"prefixes": ["nso-"], "requires_env": ["NSO_ADDRESS"],
                 "desc": "Cisco NSO device + service management"},
    "terraform": {"prefixes": ["terraform-"],
                  "requires_env": ["TERRAFORM_TOKEN", "TFE_TOKEN", "TF_TOKEN", "HCP_CLIENT_ID"],
                  "desc": "Terraform / HCP orchestration"},
    # ── vendor network platforms (each dedicated) ──
    "aci":      {"prefixes": ["aci-"], "requires_env": ["ACI_MCP_SCRIPT"],
                 "desc": "Cisco ACI fabric"},
    "catalyst-center": {"prefixes": ["catc-"], "requires_env": ["CATC_MCP_SCRIPT"],
                        "desc": "Cisco Catalyst Center"},
    "f5":       {"prefixes": ["f5-"], "requires_env": ["F5_MCP_SCRIPT"],
                 "desc": "F5 BIG-IP config/health/troubleshoot"},
    "meraki":   {"prefixes": ["meraki-"], "requires_env": ["MERAKI_API_KEY", "MERAKI_DASHBOARD_API_KEY"],
                 "desc": "Cisco Meraki dashboard"},
    "sdwan":    {"prefixes": ["sdwan-", "prisma-sdwan-"], "requires_env": ["SDWAN_MCP_SCRIPT"],
                 "desc": "SD-WAN (Cisco/Prisma) ops"},
    # ── security vendors (each dedicated — NOT bundled) ──
    "ise":         {"prefixes": ["ise-"], "requires_env": ["ISE_MCP_SCRIPT"],
                    "desc": "Cisco ISE posture + incident response"},
    "asa":         {"exact": ["pyats-asa-firewall"], "requires_env": ["ASA_MCP_CMD", "ASA_HOST"],
                    "desc": "Cisco ASA firewall"},
    "checkpoint":  {"prefixes": ["checkpoint"], "requires_env": ["CHECKPOINT_MCP_CMD", "CHKP_HOST"],
                    "desc": "Check Point firewall management"},
    "paloalto":    {"prefixes": ["paloalto-", "fmc-"], "requires_env": ["PANOS_MCP_CMD"],
                    "desc": "Palo Alto Panorama / FMC firewall ops"},
    "fortimanager": {"prefixes": ["fortimanager-", "fortigate-", "fortianalyzer-"],
                     "requires_env": ["FORTINET_MCP_CMD"],
                     "desc": "Fortinet: FortiManager intent, FortiGate state, FortiAnalyzer traffic"},
    "zscaler":     {"prefixes": ["zscaler-"], "requires_env": ["ZSCALER_CLIENT_ID", "ZIA_USERNAME"],
                    "desc": "Zscaler ZIA/ZPA/ZDX"},
    "claroty":     {"prefixes": ["claroty-"], "requires_env": ["CLAROTY_MCP_CMD", "CLAROTY_HOST"],
                    "desc": "Claroty OT/ICS security"},
    "nmap":        {"prefixes": ["nmap-"], "requires_env": ["NMAP_MCP_SCRIPT"],
                    "desc": "Nmap scanning + service detection"},
    "nvd":         {"exact": ["nvd-cve"], "requires_env": ["NVD_API_KEY"],
                    "desc": "NVD CVE lookup"},
    "fwrule":      {"exact": ["fwrule-analyzer"], "requires_env": ["FWRULE_MCP_DIR"],
                    "desc": "Firewall-rule analysis"},
    # ── clouds (each dedicated) ──
    "equinix": {"prefixes": ["equinix-"], "requires_env": ["EQUINIX_ENABLED"],
                "desc": "Equinix Fabric + Network Edge; OAuth and gated operations"},
    "aws":      {"prefixes": ["aws-"], "requires_env": ["AWS_ACCESS_KEY_ID"],
                 "desc": "AWS network/security/cost/architecture"},
    "azure":    {"prefixes": ["azure-"], "requires_env": ["AZURE_CLIENT_ID"],
                 "desc": "Azure network + security"},
    "gcp":      {"prefixes": ["gcp-"], "requires_env": ["GOOGLE_APPLICATION_CREDENTIALS", "GCP_PROJECT"],
                 "desc": "Google Cloud compute/monitoring/logging"},
    # ── source of truth / IPAM (each dedicated) ──
    "netbox":   {"exact": ["netbox-reconcile"], "requires_env": ["NETBOX_URL"],
                 "desc": "NetBox source of truth"},
    "nautobot": {"exact": ["nautobot-sot"], "requires_env": ["NAUTOBOT_URL", "NAUTOBOT_TOKEN"],
                 "desc": "Nautobot source of truth"},
    "infrahub": {"exact": ["infrahub-sot"], "requires_env": ["INFRAHUB_ADDRESS", "INFRAHUB_API_TOKEN"],
                 "desc": "Infrahub source of truth"},
    "infoblox": {"exact": ["infoblox-ddi"], "requires_env": ["INFOBLOX_MCP_CMD"],
                 "desc": "Infoblox DDI (DNS/DHCP/IPAM)"},
    # ── devops ──
    "github":   {"exact": ["github-ops"], "requires_env": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
                 "desc": "GitHub repository ops"},
    # ── UTILITIES: grouped, not split (interview: "maybe not utilities") ──
    "viz":      {"exact": ["threejs-network-viz", "ue5-network-viz", "blender-3d-viz",
                           "canvas-network-viz", "drawio-diagram", "markmap-viz",
                           "uml-diagram", "digital-twin-preflight", "aws-architecture-diagram"],
                 "desc": "Visualization utility (Three.js/UE5/Blender/Canvas + diagrams)"},
}

# Security posture (interview): a risk-wide MODE, not regular profiles. DefenseClaw
# (Cisco) + OpenShell (NVIDIA sandbox) are optional security members enabled in
# PRODUCTION mode and off in TESTING mode. See risk-deployment-design.md.
SECURITY_POSTURE = {
    "defenseclaw": {"exact": ["defenseclaw-ops", "codeguard"],
                    "desc": "DefenseClaw guardrails + CodeGuard (production mode)"},
    "openshell":   {"desc": "NVIDIA OpenShell sandbox — members run sandboxed (production mode)"},
}


# Per-member .env SLICE (least privilege): the env-key prefixes each member gets.
# A member receives ONLY its integration's secrets + the base-member keys below +
# its iN2N/model vars. The Border gets comms secrets and ZERO device creds.
ENV_PREFIXES = {
    "convergence": ["CONVERGENCE_"],
    "equinix": ["EQUINIX_"],
    "cml": ["CML_"], "containerlab": ["CLAB_"], "pyats": ["PYATS_"],
    "ipfabric": ["IPFABRIC_"], "suzieq": ["SUZIEQ_"], "batfish": ["BATFISH_"],
    "forward": ["FORWARD_"], "gtrace": ["GTRACE_"],
    "packet": ["PACKET_BUDDY_", "KUBESHARK_"],
    "itential": ["ITENTIAL_"], "aap": ["AAP_"], "nso": ["NSO_"], "terraform": ["TERRAFORM_", "TF_", "TFE_"],
    "aci": ["ACI_"], "catalyst-center": ["CATC_"], "f5": ["F5_"], "meraki": ["MERAKI_"],
    "sdwan": ["SDWAN_", "PRISMA_"],
    "ise": ["ISE_"], "asa": ["ASA_"], "checkpoint": ["CHECKPOINT_", "CHKP_"],
    "paloalto": ["PANOS_", "FMC_"],
    "fortimanager": ["FORTINET_", "FORTIMANAGER_", "FORTIGATE_", "FORTIANALYZER_"],
    "zscaler": ["ZSCALER_", "ZIA_", "ZPA_", "ZDX_"], "claroty": ["CLAROTY_"],
    "nmap": ["NMAP_"], "nvd": ["NVD_"], "fwrule": ["FWRULE_"],
    "aws": ["AWS_"], "azure": ["AZURE_"], "gcp": ["GOOGLE_", "GCP_"],
    "netbox": ["NETBOX_"], "nautobot": ["NAUTOBOT_"], "infrahub": ["INFRAHUB_"],
    "infoblox": ["INFOBLOX_"], "github": ["GITHUB_"],
    "viz": ["BLENDER_", "UE5_", "SKETCHFAB_", "MARKMAP_", "DRAWIO_"],
}
# Base floor every member gets (memory + GAIT + humanrail per the interview).
# MCP_CALL is the shared non-secret MCP-invoke helper path every profile's
# skills shell out through; without it in the slice, skills fall back to the
# Border's master .env — which member units mask (InaccessiblePaths, enforced
# for real since Ubuntu 26.04's systemd).
BASE_MEMBER_ENV_PREFIXES = ["MEMPALACE_", "GAIT_", "HUMANRAIL_", "MEMORY_", "MCP_CALL"]


# ${NAME}, and the NAME of ${NAME:-default} / ${NAME-default}. A nested default
# ${A:-${B}} references both. Only string VALUES are scanned: dict keys (an env
# block's keys) name what the server sees, not what the runtime resolves. There is no
# escape: $${A} still contains ${A}, as scripts/lib/mcp_environment.py's BARE reads it.
_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)")

# Shared credentials a kept server's ${NAME} never pulls into a member slice: the
# ServiceNow account (write-capable; fortinet-mcp, claroty-mcp and gnmi-mcp refuse
# production changes without it, so leaving it out fails closed) and every comms
# secret (exact keys from config/components/comms.json, plus these prefixes). An
# operator who wants a member to have one grants it through ENV_PREFIXES.
DERIVED_DENY_PREFIXES = ("SERVICENOW_", "SLACK_", "DISCORD_", "WEBEX_", "TWILIO_",
                         "TWITTER_", "MSTEAMS_", "TEAMS_", "TELEGRAM_")


def _comms_keys():
    try:
        text = Path(REPO, "config/components/comms.json").read_text()
    except OSError:
        return frozenset()
    return frozenset(re.findall(r'"key":\s*"([A-Z][A-Z0-9_]*)"', text))


DERIVED_DENY_KEYS = _comms_keys()


def derived_ref_allowed(name):
    return not (name.startswith(DERIVED_DENY_PREFIXES) or name in DERIVED_DENY_KEYS)


def _kept(names, servers):
    keep = set(names) | {"memory-mcp"}
    return {k: v for k, v in (servers or {}).items() if k in keep}


def member_servers(profile, servers):
    """The Border mcp.servers entries a generic OpenClaw member of `profile` keeps
    (scripts/in2n-member-home.py): its MCP_SERVERS list plus memory-mcp. Servers the
    Border has not registered are skipped."""
    return _kept(MCP_SERVERS.get(profile, []), servers)


def server_env_refs(entry):
    """Every NAME referenced as ${NAME} anywhere in one server entry (command, args,
    env, url, headers, ...)."""
    found = set()
    def walk(value):
        if isinstance(value, str):
            found.update(_ENV_REF.findall(value))
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
    walk(entry)
    return found


def env_slice_keys(profile, env_keys, servers=None):
    """Return the env-key NAMES a member of `profile` should receive (least
    privilege): its integration prefixes + the base-member prefixes + every variable
    its kept MCP servers reference as ${NAME} or, for a component-launched server,
    read from its env file (component_env_keys, spec 184), except shared credentials
    (derived_ref_allowed). `servers` is the Border template's mcp.servers map;
    without it only the prefixes apply. A key no kept server references and no
    prefix matches (comms secrets, other integrations) is never included. Values
    are the caller's concern (never logged)."""
    return _slice(ENV_PREFIXES.get(profile, []), member_servers(profile, servers), env_keys)


def _slice(prefixes, kept, env_keys):
    prefixes = tuple(list(prefixes) + BASE_MEMBER_ENV_PREFIXES)
    refs = set()
    for server, entry in kept.items():
        if server in BORDER_ONLY_SERVERS or launched_component(entry) in BORDER_ONLY_COMPONENTS:
            continue
        names = server_env_refs(entry) | component_env_keys(entry)
        refs |= {name for name in names if derived_ref_allowed(name)}
    return sorted(k for k in env_keys if k.startswith(prefixes) or k in refs)


def launched_component(entry):
    """The component a scripts/component-launch.py entry starts, else None."""
    args = [str(a) for a in (entry.get("args") or [])] if isinstance(entry, dict) else []
    for i, arg in enumerate(args[:-1]):
        if Path(arg).name == "component-launch.py":
            return args[i + 1]
    return None


def _read_json(relative):
    try:
        return json.loads(Path(REPO, relative).read_text())
    except (OSError, ValueError):
        return {}


# ── Border-only components (spec 184 review): never a member's ──
# HUD-private components (installer-access.json `access: hud-private`), the federation
# and control plane (protocol daemon, n2n tools), netconverter (bound to the Border
# installation's identity and API key), the Convergence reader (provisioned only by
# provision_convergence, with its own runtime paths) and the comms components
# config/components/comms.json binds (twilio, zoom-rtms). A member spec may not keep
# their servers, and their settings are never derived into any member's slice.
FEDERATION_CONTROL_COMPONENTS = frozenset({"protocol", "n2n", "netconverter", "convergence-read"})


def _border_only():
    contract = (_read_json("config/installer-access.json").get("components") or {})
    components = {c for c, rule in contract.items()
                  if isinstance(rule, dict) and rule.get("access") == "hud-private"}
    components |= FEDERATION_CONTROL_COMPONENTS
    components |= {e["component"] for e in (_read_json("config/components/comms.json").get("entries") or [])
                   if isinstance(e, dict) and isinstance(e.get("component"), str)}
    servers = set()
    for component in _read_json("config/components/catalog.json").get("components") or []:
        if isinstance(component, dict) and component.get("id") in components:
            servers.update(s for s in component.get("servers") or [] if isinstance(s, str))
    for component, rule in contract.items():
        if component in components and isinstance(rule, dict):
            servers.update(s for s in rule.get("servers") or [] if isinstance(s, str))
    return frozenset(components), frozenset(servers)


BORDER_ONLY_COMPONENTS, BORDER_ONLY_SERVERS = _border_only()


def _component_env_index():
    """component id -> the env keys it reads from its env file: the installer catalog's
    settings (config/components/catalog.json components[].settings[].key) plus what
    scripts/component-launch.py itself reads (config/installer-access.json required_env,
    script_env, command_env). Border-only components contribute nothing. Unreadable
    files contribute nothing."""
    index = {}
    try:
        catalog = json.loads(Path(REPO, "config/components/catalog.json").read_text())
        for component in catalog.get("components", []):
            index.setdefault(component["id"], set()).update(
                s["key"] for s in component.get("settings", []) if isinstance(s.get("key"), str))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    try:
        contract = json.loads(Path(REPO, "config/installer-access.json").read_text())["components"]
        for component, rule in contract.items():
            keys = index.setdefault(component, set())
            keys.update(k for k in rule.get("required_env") or [] if isinstance(k, str))
            keys.update(rule[k] for k in ("script_env", "command_env") if isinstance(rule.get(k), str))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return {component: frozenset(keys) for component, keys in index.items()
            if component not in BORDER_ONLY_COMPONENTS}


COMPONENT_ENV_KEYS = _component_env_index()


def component_env_keys(entry):
    """Env keys a component-launched server reads from NETCLAW_RUNTIME_ENV without naming
    them as ${NAME} in its entry (e.g. pyats-mcp's PYATS_TESTBED_PATH and device logins)."""
    return set(COMPONENT_ENV_KEYS.get(launched_component(entry), ()))


# ── Member spec (spec 184): a declarative member, no profile, no NetClaw patch ──
#
# {"version": 1, "name": ..., "description": ..., "servers": [...], "skills": [...],
#  "tools": {"allow": [...]}, "model": null}
# The member keeps `servers` plus the base servers (memory-mcp, gait-mcp), loads its
# skills plus the base skills from its own workspace, and its OpenClaw tool policy is
# `tools.allow` plus what those base skills need (spec_tool_policy). Validation is strict.

MEMBER_SPEC_VERSION = 1
MEMBER_SPEC_REQUIRED = ("version", "name", "servers", "tools")
MEMBER_SPEC_KEYS = frozenset(MEMBER_SPEC_REQUIRED + ("description", "skills", "model", "auth"))
# Spec 185: built-in providers a member may reach with its own subscription login
# ("auth": "subscription"); OpenClaw keeps that login in the member home's auth profiles.
SUBSCRIPTION_PROVIDERS = frozenset({"anthropic", "openai"})
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
# convergence has its own provisioning path; custom and spec are `netclaw risk add` keywords.
# Every profile id is refused too (reserved_member_names), so a spec member never shares a
# staged directory, home or --hot entry with a profile member.
RESERVED_MEMBER_NAMES = frozenset({"convergence", "custom", "spec"})

# File-backed base skills match the migration scope. Runtime/status capabilities
# are daemon methods, not installed SKILL.md directories. HumanRail is included as
# escalation guidance, but no exec or paid external-dispatch permission is implicit.
SPEC_BASE_SKILL_NAMES = ("memory", "gait-session-tracking", "humanrail-escalation")
SPEC_BASE_SKILLS = (("memory", "memory-mcp"), ("gait-session-tracking", "gait-mcp"))

# OpenClaw's core tool ids (CORE_TOOL_DEFINITIONS and CORE_TOOL_GROUPS in OpenClaw
# 2026.10.9, dist/tool-catalog-*.mjs; every id passes its isKnownCoreToolId). Group
# names, "*" and "bundle-mcp" are refused: they grant whole families of tools.
OPENCLAW_BUILTIN_TOOLS = frozenset((
    "agents_list", "agents_wait", "apply_patch", "ask_user", "automations", "browser",
    "canvas", "code_execution", "computer", "conversations_list", "conversations_send",
    "conversations_turn", "create_goal", "dashboard", "decision_evaluate", "dismiss_task",
    "edit", "exec", "gateway", "get_goal", "github_identity_status", "github_publish",
    "heartbeat_respond", "image_generate", "ls", "memory_get", "memory_search", "message",
    "mobile_ui", "music_generate", "nodes", "openclaw", "pdf", "personal_instructions",
    "plugins", "portal", "presence", "process", "progress_card", "read", "screen", "secrets",
    "session_status", "sessions", "sessions_history", "sessions_list", "sessions_search",
    "sessions_send", "sessions_spawn", "sessions_yield", "show_widget", "skill_workshop",
    "skills_read", "skills_search", "subagents", "suggest_task", "terminal", "theme", "tts",
    "update_goal", "video_generate", "view_image", "web_fetch", "web_search", "write",
    "x_search"))
# The built-ins a spec member may use without --allow-dangerous-tools (review round 2:
# an explicit SAFE list, not a list of known-dangerous tools, so a tool OpenClaw adds
# later, or one whose reach is not obvious, needs the opt-in):
# - read: OpenClaw tells the agent to read a skill's SKILL.md before using it, and
#   tools.fs.workspaceOnly (set by spec_tool_policy) confines it to the member's own
#   workspace, which holds only the member's copied skills.
# - session_status: this session's status, model and usage; it reaches nothing else.
# Every other built-in is dangerous, among them web_fetch/web_search/x_search (network),
# the media generators and tts (paid external APIs), memory_get/memory_search and
# personal_instructions (read OpenClaw's memory files and memorySearch.extraPaths), ls
# (not covered by tools.fs.workspaceOnly), exec/process/code_execution/secrets, the fs
# writers, automation, nodes, messaging, and session/agent/publishing tools.
SAFE_BUILTINS = frozenset({"read", "session_status"})
DANGEROUS_BUILTINS = OPENCLAW_BUILTIN_TOOLS - SAFE_BUILTINS
# OpenClaw names an MCP tool <safe server>__<tool> (agent-bundle-mcp-names): a server
# name outside [A-Za-z0-9_-], not starting with a letter, or over 30 characters is
# renamed, so an allowlist written with the configured name would never match.
OPENCLAW_SAFE_SERVER = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,29}")
# The tool part: OpenClaw's tool-name characters, plus "*" (its only glob character).
ALLOW_TOOL_PART = re.compile(r"[A-Za-z0-9_*-]+")
MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}")


class MemberSpecError(ValueError):
    """A member spec failed validation; str() lists every problem, one per line."""


def reserved_member_names():
    return RESERVED_MEMBER_NAMES | set(PROFILE_MATCHERS) | set(MCP_SERVERS)


def load_member_spec(source, servers, installed=None, allow_dangerous=False, providers=None):
    """Validate a member spec against the Border template's mcp.servers.

    `source` is a path or an already-parsed dict. Returns (spec, warnings): `spec`
    is the normalized spec plus "scope" (the specialty skills the existing `scope
    custom` path yields; `installed` defaults to the installed skills), "base_skills"
    and "base_servers" (SPEC_BASE_SKILLS whose server the Border has) and
    "dangerous_tools" (allowed only with `allow_dangerous`). `providers` is the Border's
    models.providers (spec 185): a `<provider>/<model>` model must name one of them, or use
    "auth": "subscription" with a built-in provider. The result also carries "provider"
    (None for NetClaw's built-in Anthropic API-key provider) and "auth". Raises
    MemberSpecError naming every problem."""
    if not isinstance(source, (str, os.PathLike)):
        data, where = source, "member spec"
    else:
        where = str(source)
        try:
            data = json.loads(Path(source).read_text())
        except OSError as error:
            raise MemberSpecError(f"{where}: cannot read ({type(error).__name__})") from None
        except ValueError as error:
            raise MemberSpecError(f"{where}: not valid JSON ({error})") from None
    if not isinstance(data, dict):
        raise MemberSpecError(f"{where}: must be a JSON object")
    errors, warnings = [], []
    unknown = sorted(set(data) - MEMBER_SPEC_KEYS)
    if unknown:
        errors.append("unknown keys: " + ", ".join(unknown))
    for key in MEMBER_SPEC_REQUIRED:
        if key not in data:
            errors.append(f"missing required key: {key}")

    version = data.get("version")
    if "version" in data and (type(version) is not int or version != MEMBER_SPEC_VERSION):
        errors.append(f"version must be {MEMBER_SPEC_VERSION}, not {version!r}")

    name = data.get("name")
    if "name" in data:
        if not isinstance(name, str) or not SAFE_NAME.fullmatch(name):
            errors.append("name must match [A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
        elif name in RESERVED_MEMBER_NAMES:
            errors.append(f"name {name!r} is reserved")
        elif name in reserved_member_names():
            errors.append(f"name {name!r} is a member profile id; choose another name")

    description = data.get("description")
    if description is not None and not isinstance(description, str):
        errors.append("description must be a string")

    template = servers if isinstance(servers, dict) else {}
    base = [(skill, server) for skill, server in SPEC_BASE_SKILLS if server in template]
    names = data.get("servers")
    kept = set()
    if "servers" in data:
        if not isinstance(names, list) or not all(isinstance(s, str) and s for s in names):
            errors.append("servers must be a list of server names")
        else:
            if len(set(names)) != len(names):
                errors.append("servers lists a server more than once")
            border_only = sorted(s for s in names if s in BORDER_ONLY_SERVERS or
                                 launched_component(template.get(s)) in BORDER_ONLY_COMPONENTS)
            if border_only:
                errors.append("Border-only servers cannot be kept by a member: " + ", ".join(border_only)
                              + (" (the Convergence member is provisioned with --member convergence)"
                                 if "convergence-read-mcp" in border_only else ""))
            missing = sorted(set(names) - set(template) - BORDER_ONLY_SERVERS)
            if missing:
                errors.append("servers not in the Border template's mcp.servers: " + ", ".join(missing))
            kept = (set(names) | {"memory-mcp"} | {s for _, s in base}) & set(template)
            kept -= BORDER_ONLY_SERVERS
            renamed = sorted(s for s in kept if not OPENCLAW_SAFE_SERVER.fullmatch(s))
            if renamed:
                errors.append("OpenClaw renames these servers' tools, so no allowlist entry can name "
                              "them: " + ", ".join(renamed))

    skills = data.get("skills", [])
    if not isinstance(skills, list) or not all(isinstance(s, str) and SAFE_NAME.fullmatch(s) for s in skills):
        errors.append("skills must be a list of skill names")
        skills = []
    elif len(set(skills)) != len(skills):
        errors.append("skills lists a skill more than once")

    tools = data.get("tools")
    allow, dangerous = [], []
    if "tools" in data:
        if not isinstance(tools, dict) or set(tools) != {"allow"}:
            errors.append('tools must be {"allow": [...]} and nothing else')
        elif not isinstance(tools["allow"], list) or not tools["allow"]:
            errors.append("tools.allow must be a non-empty list")
        else:
            allow = tools["allow"]
            seen = set()
            for entry in allow:
                problem = _allow_entry_problem(entry, kept)
                if problem:
                    errors.append(f"tools.allow {entry!r}: {problem}")
                elif entry.lower() in seen:
                    errors.append(f"tools.allow {entry!r}: listed more than once")
                else:
                    seen.add(entry.lower())
                    if entry in DANGEROUS_BUILTINS:
                        dangerous.append(entry)
            if dangerous and not allow_dangerous:
                errors.append("tools.allow names built-in tools outside the safe set ("
                              + ", ".join(sorted(SAFE_BUILTINS)) + "): " + ", ".join(dangerous)
                              + "; refused unless --allow-dangerous-tools is passed")
            elif dangerous:
                warnings.append("--allow-dangerous-tools: this member may use " + ", ".join(dangerous))

    model, provider, auth = data.get("model"), None, data.get("auth", "api-key")
    if auth not in ("api-key", "subscription"):
        errors.append("auth must be 'api-key' (the default) or 'subscription'")
        auth = "api-key"
    prefix, _, rest = model.partition("/") if isinstance(model, str) else ("", "", "")
    if model is None:
        if auth == "subscription":
            errors.append("auth 'subscription' needs a model: 'anthropic/<id>' or 'openai/<id>'")
    elif not isinstance(model, str):
        errors.append("model must be null or a string")
    elif auth == "subscription":
        # Spec 185: a built-in provider, signed in on the member home itself; no key.
        if prefix not in SUBSCRIPTION_PROVIDERS or not MODEL_ID.fullmatch(rest):
            errors.append("with auth 'subscription', model must be 'anthropic/<id>' or 'openai/<id>'")
        else:
            provider, model = prefix, rest
    elif not rest or prefix == "anthropic":
        bare = rest if rest else model
        if not MODEL_ID.fullmatch(bare):
            errors.append("model must be null, an Anthropic model id (optionally 'anthropic/<id>') "
                          "or '<provider>/<model>' for a provider the Border configures")
        else:
            model = bare
    else:
        # Spec 185: a provider the Border configures (models.providers), by reference only.
        problem = provider_problem(providers, prefix, rest)
        if problem:
            errors.append(f"model {model!r}: {problem}")
        else:
            provider, model = prefix, rest

    if errors:
        raise MemberSpecError(f"{where}: invalid member spec:\n  - " + "\n  - ".join(errors))
    available = set(_all_installed_skills() if installed is None else installed)
    absent = [s for s in skills if s not in available]
    if absent:
        warnings.append("skills not installed: " + ", ".join(absent))
    scope_skills = [e["name"] for e in scope("custom", custom_skills=skills,
                                             installed=sorted(available)) if e["tier"] == "specialty"]
    spec = {"version": version, "name": name, "description": description or "",
            "servers": list(names), "skills": list(skills), "tools": {"allow": list(allow)},
            "model": model, "provider": provider, "auth": auth, "scope": scope_skills,
            "base_skills": [skill for skill in SPEC_BASE_SKILL_NAMES if skill not in skills],
            "base_servers": [server for _, server in base],
            "dangerous_tools": dangerous}
    return spec, warnings


# Spec 185 review round 1: a provider member's entry is BUILT from these fields of the
# Border's entry, never copied whole; anything else is refused with its name.
PROVIDER_FIELDS = ("api", "baseUrl", "apiKey", "authHeader", "headers", "timeoutSeconds", "models")
PROVIDER_MODEL_FIELDS = ("id", "name", "api", "reasoning", "input", "cost", "contextWindow", "maxTokens", "compat")
# Model ids of a Border provider may contain '/' (e.g. openrouter's anthropic/claude-...).
PROVIDER_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}")
_EXACT_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_HEADER_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,63}")


class _ProviderRefused(ValueError):
    pass


def _ref_or_text(field, value):
    """`value` is exactly one ${NAME} reference, or text holding no reference at all."""
    if not isinstance(value, str) or not value:
        raise _ProviderRefused(f"{field} must be non-empty text")
    if "${" in value and not _EXACT_REF.fullmatch(value):
        raise _ProviderRefused(f"{field} must be one ${{NAME}} reference or plain text")


def _provider_entry(name, entry, model):
    """The member's copy of the Border provider `entry` with only `model`; raises
    _ProviderRefused naming the problem (never a value)."""
    if not isinstance(entry, dict):
        raise _ProviderRefused(f"the Border's provider {name!r} is not an object")
    if "localService" in entry:
        raise _ProviderRefused(f"the Border's provider {name!r} starts a local service (localService); "
                               "a member does not run provider processes")
    unknown = sorted(set(entry) - set(PROVIDER_FIELDS))
    if unknown:
        raise _ProviderRefused(f"the Border's provider {name!r} has fields a member entry does not carry: "
                               + ", ".join(map(str, unknown)) + " (supported: " + ", ".join(PROVIDER_FIELDS[:-1]) + ")")
    built = {}
    if "api" in entry:
        _ref_or_text("api", entry["api"])
        built["api"] = entry["api"]
    if "baseUrl" in entry:
        url = entry["baseUrl"]
        _ref_or_text("baseUrl", url)
        if not _EXACT_REF.fullmatch(url):
            parts = urlsplit(url)
            if (parts.scheme not in ("http", "https") or not parts.hostname or parts.username is not None
                    or parts.password is not None or parts.query or parts.fragment):
                raise _ProviderRefused("baseUrl must be an http(s) URL without credentials, query or fragment "
                                       "(or one ${NAME} reference)")
        built["baseUrl"] = url
    if "apiKey" in entry:
        key = entry["apiKey"]
        if isinstance(key, dict):
            if (set(key) != {"source", "provider", "id"} or key.get("source") != "env"
                    or key.get("provider") != "default" or not isinstance(key.get("id"), str)
                    or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key["id"])):
                raise _ProviderRefused("apiKey must be a ${NAME} reference or a default env SecretRef "
                                       "(file, exec and vault SecretRefs would resolve the Border's secret)")
        elif not (isinstance(key, str) and _EXACT_REF.fullmatch(key)):
            raise _ProviderRefused("apiKey must be a ${NAME} reference or a default env SecretRef, not a literal")
        built["apiKey"] = copy.deepcopy(key)
    if "authHeader" in entry:
        if not isinstance(entry["authHeader"], bool):
            raise _ProviderRefused("authHeader must be true or false")
        built["authHeader"] = entry["authHeader"]
    if "headers" in entry:
        headers = entry["headers"]
        if not isinstance(headers, dict):
            raise _ProviderRefused("headers must be an object")
        for header, value in headers.items():
            if not isinstance(header, str) or not _HEADER_NAME.fullmatch(header):
                raise _ProviderRefused("a header name is not valid")
            # Every header value carries its content only through references, whatever its name.
            if not isinstance(value, str) or not _referenced(value):
                raise _ProviderRefused(f"header {header!r} must hold only ${{NAME}} references "
                                       "(optionally after an auth scheme such as Bearer)")
        built["headers"] = dict(headers)
    if "timeoutSeconds" in entry:
        timeout = entry["timeoutSeconds"]
        if type(timeout) not in (int, float) or not 0 < timeout <= 3600:
            raise _ProviderRefused("timeoutSeconds must be a number of seconds up to 3600")
        built["timeoutSeconds"] = timeout
    models = [m for m in entry.get("models") or [] if isinstance(m, dict) and m.get("id") == model]
    if not models:
        ids = [m.get("id") for m in entry.get("models") or [] if isinstance(m, dict)]
        raise _ProviderRefused(f"the Border's provider {name!r} does not list model {model!r} "
                               f"(it lists: {', '.join(map(str, ids)) or 'none'})")
    built["models"] = [{k: copy.deepcopy(v) for k, v in models[0].items() if k in PROVIDER_MODEL_FIELDS}]
    literal = literal_secrets(built, name)
    if literal:
        raise _ProviderRefused("the Border's provider holds literal secrets (move each into the .env and "
                               "reference it as ${NAME}): " + ", ".join(literal))
    denied = sorted(r for r in provider_entry_refs(built)
                    if not derived_ref_allowed(r) or r in SPEC_MEMBER_STORE_KEYS)
    if denied:
        raise _ProviderRefused("the Border's provider references variables a member never receives: "
                               + ", ".join(denied))
    return built


def provider_entry_refs(entry):
    """Variable names a built provider entry references (${NAME} anywhere, env SecretRef ids)."""
    refs = set(server_env_refs(entry))
    key = entry.get("apiKey")
    if isinstance(key, dict) and key.get("source") == "env":
        refs.add(key["id"])
    return refs


def provider_problem(providers, name, model):
    """Why a spec member may not use model `model` of the Border provider `name`, or None."""
    if not isinstance(providers, dict) or name not in providers:
        return (f"provider {name!r} is not configured on the Border (models.providers); "
                "configure it there first")
    if not SAFE_NAME.fullmatch(name):
        return f"provider name {name!r} is not a safe name"
    if not PROVIDER_MODEL_ID.fullmatch(model) or ".." in model:
        return "the model id is not valid"
    try:
        _provider_entry(name, providers[name], model)
    except _ProviderRefused as error:
        return str(error)
    return None


def spec_provider_entry(spec, providers):
    """The one models.providers entry a spec member registers (spec 185), built from
    PROVIDER_FIELDS of the Border's entry with only its model; None for the built-in
    providers (Anthropic API key, subscriptions)."""
    if not spec.get("provider") or spec.get("auth") == "subscription":
        return None
    return _provider_entry(spec["provider"], providers[spec["provider"]], spec["model"])


def spec_model_binding(spec, tier):
    """`<provider>/<model>` the member runs: its --model and its config's primary model."""
    return f"{spec.get('provider') or 'anthropic'}/{spec.get('model') or tier}"


def _allow_entry_problem(entry, kept):
    if not isinstance(entry, str) or not entry or entry != entry.strip():
        return "must be a non-empty string"
    if "__" in entry:
        server, tool = entry.split("__", 1)
        if "*" in server:
            return "the server part must be a literal server name"
        if server not in kept:
            return f"{server!r} is not one of this member's servers"
        if not ALLOW_TOOL_PART.fullmatch(tool):
            return "the tool part may use only letters, digits, '_', '-' and the glob '*'"
        return None
    if entry not in OPENCLAW_BUILTIN_TOOLS:
        return ("not an OpenClaw built-in tool name or <server>__<tool> pattern "
                "(groups, '*' and 'bundle-mcp' are not accepted)")
    return None


def spec_skills(spec):
    """Every skill a spec member loads: its own, then the base skills."""
    return list(dict.fromkeys(list(spec["skills"]) + list(SPEC_BASE_SKILL_NAMES)))


def spec_member_servers(spec, servers):
    """The Border mcp.servers entries a spec member keeps: spec.servers, memory-mcp and
    the base skills' servers; never a Border-only server."""
    kept = _kept(list(spec["servers"]) + list(spec.get("base_servers", [])), servers)
    return {k: v for k, v in kept.items() if k not in BORDER_ONLY_SERVERS}


# Literal secrets in a kept server entry (review round 3). The env slice filters
# variable NAMES; a value written literally into the Border template (instead of a
# ${VAR} reference) would be copied into the member's openclaw.json as is. A spec
# member refuses such an entry; the operator moves the value into the .env.
_SECRET_KEY = re.compile(r"(?i)(token|secret|passw(or)?d|(^|[_-])pwd$|^auth$|api[_-]?key|apikey|"
                         r"access[_-]?key|credential|authori[sz]ation|bearer|private[_-]?key|"
                         r"session[_-]?key|cookie)")
# Names that hold where or how a secret is used, not the secret itself.
_NOT_SECRET_NAME = re.compile(r"(?i)([_-]?(file|path|dir|ttl|url|uri|domain|header|name|type|mode|"
                              r"expir\w*|timeout|refresh|scope|algorithm|endpoint))$")
_URL_USERINFO = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://([^/@\s]+)@")
_PLAIN_SETTING = re.compile(r"(?i)^(\d+(\.\d+)?[smhd]?|true|false|yes|no|on|off|none|bearer|basic)$")
_ANY_ENV_REF = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*(?::?[-=]([^}]*))?\}")
_AUTH_SCHEME = re.compile(r"(?i)^(bearer|basic|token|bot|apikey|api-key|key|digest|sso-key)?$")


def _referenced(value):
    """True when `value` carries its secret only through ${NAME} references with no
    literal default, e.g. '${TOKEN}', 'Bearer ${TOKEN}', '${USER}:${PASS}'."""
    refs = list(_ANY_ENV_REF.finditer(value))
    if not refs or any((m.group(1) or "").strip() for m in refs):
        return False
    return bool(_AUTH_SCHEME.match(_ANY_ENV_REF.sub("", value).replace(":", " ").strip()))


def _secret_name(name):
    name = str(name)
    return bool(_SECRET_KEY.search(name)) and not _NOT_SECRET_NAME.search(name)


def _url_has_literal_credentials(value):
    """A URL with user:password@ whose password is literal, or a bare user@ (a token
    used as the user name) that is literal. A literal user name with a ${NAME}
    password is fine."""
    match = _URL_USERINFO.match(value)
    if not match:
        return False
    user, sep, password = match.group(1).partition(":")
    return not _referenced(password if sep else user)


def literal_secrets(entry, where=""):
    """Paths (never values) in `entry` that hold a literal secret: a secret-looking key
    whose string value is not a ${VAR} reference, a URL with embedded credentials, or a
    secret-looking command-line flag followed by a literal argument."""
    found = []
    if isinstance(entry, dict):
        for key, value in entry.items():
            path = f"{where}.{key}" if where else str(key)
            if isinstance(value, str):
                if (value and _secret_name(key) and not _referenced(value)
                        and not _PLAIN_SETTING.match(value)):
                    found.append(path)
                elif _url_has_literal_credentials(value):
                    found.append(f"{path} (URL credentials)")
            elif key == "args" and isinstance(value, list):
                for i, arg in enumerate(value):
                    if not isinstance(arg, str):
                        continue
                    if _url_has_literal_credentials(arg):
                        found.append(f"{path}[{i}] (URL credentials)")
                    flag, _, inline = arg.partition("=")
                    if flag.startswith("-") and _secret_name(flag.lstrip("-")):
                        literal = inline if inline else (value[i + 1] if i + 1 < len(value) else "")
                        if isinstance(literal, str) and literal and not literal.startswith("-") \
                                and not _referenced(literal) \
                                and not _PLAIN_SETTING.match(literal):
                            found.append(f"{path}[{i}]")
            else:
                found.extend(literal_secrets(value, path))
    elif isinstance(entry, list):
        for i, item in enumerate(entry):
            found.extend(literal_secrets(item, f"{where}[{i}]"))
    return found


# Where the base servers keep their data (review round 2). A spec member's memory-mcp
# and gait-mcp entries point into its own home (in2n-member-home.py
# spec_store_overrides), so the Border's values of these never enter its slice.
SPEC_MEMBER_STORE_KEYS = frozenset({"MEMORY_DATA_DIR", "GAIT_DIR", "GAIT_ROOT", "GAIT_MCP_STICKY_FILE"})
# The one model provider a spec member registers, referenced as ${ANTHROPIC_API_KEY}
# from its openclaw.json (never a literal key), so the key joins its slice.
SPEC_MEMBER_PROVIDER_KEYS = ("ANTHROPIC_API_KEY",)


def spec_env_slice_keys(spec, env_keys, servers, providers=None):
    """A spec member's env slice: every variable its kept servers reference or, when
    component-launched, read from their env file (same deny lists as env_slice_keys),
    plus BASE_MEMBER_ENV_PREFIXES and its provider key; no profile prefixes, and never
    the Border's memory/GAIT store locations (SPEC_MEMBER_STORE_KEYS)."""
    keys = set(_slice([], spec_member_servers(spec, servers), env_keys)) - SPEC_MEMBER_STORE_KEYS
    if spec.get("auth") == "subscription":
        pass  # the member's own login, in its home; no key in its environment (spec 185)
    elif spec.get("provider"):
        # Spec 185: the variables the copied provider entry references, e.g. ${OLLAMA_API_KEY}.
        # Filtered like server references (provider_problem already refuses denied ones).
        entry = spec_provider_entry(spec, providers or {}) or {}
        keys |= {k for k in provider_entry_refs(entry)
                 if k in env_keys and derived_ref_allowed(k) and k not in SPEC_MEMBER_STORE_KEYS}
    else:
        keys |= {k for k in SPEC_MEMBER_PROVIDER_KEYS if k in env_keys}
    return sorted(keys)


def spec_tool_policy(spec):
    """The member home's top-level OpenClaw `tools` section (the mechanism the
    Convergence member's native_tool_policy uses). allow = tools.allow plus:
    - `read` when the member has any skill: OpenClaw's system prompt tells the agent to
      read a matching skill's SKILL.md at its <location> (system-prompt-skills);
    - `<server>__*` for each base skill's server (memory-mcp for memory, gait-mcp for
      gait-session-tracking): those skills call nothing else.
    fs.workspaceOnly, elevated off and toolSearch off match the qualified Convergence
    policy. The sandbox layer (tools.sandbox.tools) is set by the member home."""
    allow = list(spec["tools"]["allow"])
    present = {entry.lower() for entry in allow}
    extra = (["read"] if spec_skills(spec) else []) + [
        server + "__*" for skill, server in SPEC_BASE_SKILLS if skill in spec_skills(spec)
        and server in spec.get("base_servers", [])]
    allow += [entry for entry in extra if entry.lower() not in present]
    return {"allow": allow, "fs": {"workspaceOnly": True},
            "elevated": {"enabled": False}, "toolSearch": False}


# Profile → OpenClaw mcp.servers names to keep in a member's scoped config
# (scripts/in2n-member-home.py adds memory-mcp; Convergence uses only the
# protocol base floor). Each list is the set of registered servers whose tools
# the profile's skills call, from the skill→server binding in
# config/components/catalog.json and the skills' own "MCP Server" sections
# (audit: specs/183-member-mcp-mappings/research.md). Every name is registered in
# config/openclaw.json, except ipfabric-mcp, which scripts/ipfabric-enable.sh has
# the operator add.
#
# Profiles with no entry have no registered server for their skills; those
# skills launch their server through $MCP_CALL with an env-provided command:
# eve-ng, containerlab, aci, f5, ise, infoblox, and paloalto's Panorama skill.
# asa is unmapped pending a decision (see research.md); checkpoint keeps a
# deliberate subset of the 15 servers its skill composes.
MCP_SERVERS = {
    "convergence": ["convergence-read-mcp"],
    "subnet": ["subnet-calc-mcp"],
    "equinix": ["equinix-mcp"],
    # labs + test
    "cml": ["cml-mcp"], "gns3": ["gns3-mcp"], "pyats": ["pyats-mcp"],
    # assurance / analysis
    "ipfabric": ["ipfabric-mcp"], "suzieq": ["suzieq-mcp"], "batfish": ["batfish-mcp"],
    "forward": ["forward-official-mcp"], "gtrace": ["gtrace-mcp"],
    "packet": ["packet-buddy-mcp", "kubeshark-mcp"],
    # automation / orchestration
    "itential": ["itential-mcp"],
    "aap": ["aap-ansible-mcp", "aap-docs-mcp", "aap-eda-mcp", "aap-lint-mcp"],
    "nso": ["nso-mcp"], "terraform": ["terraform-mcp"],
    # vendor platforms
    "catalyst-center": ["catc-mcp"], "meraki": ["meraki-mcp"], "sdwan": ["prisma-sdwan-mcp"],
    # security
    "checkpoint": ["chkp-management", "chkp-management-logs",
        "chkp-policy-insights", "chkp-threat-prevention", "chkp-quantum-gaia"],
    "paloalto": ["cisco-fmc-mcp"], "fortimanager": ["fortinet-mcp"], "zscaler": ["zscaler-mcp"],
    "claroty": ["claroty-mcp"], "nmap": ["nmap-mcp"], "nvd": ["nvd-cve-mcp"], "fwrule": ["fwrule-mcp"],
    # clouds
    "aws": ["aws-network-mcp", "aws-iam-mcp", "aws-cloudtrail-mcp", "aws-cloudwatch-mcp",
            "aws-cost-explorer-mcp", "aws-diagram-mcp"],
    "azure": ["azure-network-mcp"],
    "gcp": ["gcp-compute-mcp", "gcp-logging-mcp", "gcp-monitoring-mcp", "gcp-resource-manager-mcp"],
    # source of truth
    "netbox": ["netbox-mcp"], "nautobot": ["nautobot-mcp"], "infrahub": ["infrahub-mcp"],
    # devops
    "github": ["github-mcp"],
    # utilities
    "viz": ["blender-mcp", "sketchfab-mcp", "drawio-mcp", "markmap-mcp", "uml-mcp",
            "unreal-mcp", "aws-diagram-mcp"],
    # No PROFILE_MATCHERS entry; used by `in2n-member-home.py --member splunk|gnmi`.
    "splunk": ["splunk-mcp"], "gnmi": ["gnmi-mcp"],
}

# Model tier per member (interview: Border=Opus; heavy members=Sonnet; trivial=Haiku).
_HEAVY = {"equinix", "cml", "pyats", "itential", "aap", "nso", "aci", "catalyst-center", "f5",
          "paloalto", "ise", "forward", "ipfabric", "sdwan", "azure", "netbox",
          "checkpoint", "fortimanager", "batfish"}
def model_tier(profile: str) -> str:
    """Default Claude model id for a member of this profile (operator-overridable)."""
    return "claude-sonnet-5" if profile in _HEAVY else "claude-haiku-4-5-20251001"


def _configured_env():
    """Env keys present in ~/.openclaw/.env plus the process environment."""
    keys = set(os.environ.keys())
    try:
        with open(ENV_FILE) as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    keys.add(line.split("=", 1)[0].strip())
    except OSError:
        pass
    return keys


def _env_satisfied(meta, env_keys):
    req = meta.get("requires_env")
    return (not req) or any(k in env_keys for k in req)


def _installed_skills(skills_dir=None):
    dirs = [skills_dir] if skills_dir else DEFAULT_SKILLS_DIRS
    for d in dirs:
        if d and os.path.isdir(d):
            out = []
            for name in sorted(os.listdir(d)):
                p = os.path.join(d, name)
                if os.path.isdir(p) and os.path.exists(os.path.join(p, "SKILL.md")):
                    out.append(name)
            return out
    return []


def _all_installed_skills(dirs=None):
    """Every skill installed in any of `dirs` (default: the repository's and the selected
    runtime's). A member spec's skills are copied from the Border's workspace as well as
    the repository (in2n-member-home.py), so its scope must count both: a skill added to
    the Border alone, e.g. by an integration, is still installed."""
    names = set()
    for d in (DEFAULT_SKILLS_DIRS if dirs is None else dirs):
        names.update(_installed_skills(d) if d and os.path.isdir(d) else [])
    return sorted(names)


def _match_profile(profile_id, installed):
    m = PROFILE_MATCHERS.get(profile_id)
    if not m:
        return []
    prefixes = tuple(m.get("prefixes", []))
    exact = set(m.get("exact", []))
    return [s for s in installed
            if s in exact or (prefixes and s.startswith(prefixes))]


def _equinix_enabled():
    """An example .env containing false must not advertise an enabled member."""
    value = os.environ.get("EQUINIX_ENABLED")
    if value is None:
        try:
            with open(ENV_FILE) as handle:
                for line in handle:
                    key, sep, val = line.strip().partition("=")
                    if sep and key == "EQUINIX_ENABLED":
                        value = val.strip().strip("\"'")
        except OSError:
            pass
    return str(value).lower() == "true"


def convergence_settings(env):
    """Use the connector's canonical validator without importing HTTP/MCP deps."""
    name = '_netclaw_convergence_settings'
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, Path(REPO)/'mcp-servers/convergence-read-mcp/settings.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module.Settings.from_env(env)


def configured_values(env_file=None, *, include_process=True):
    """Read literal selected values; process overrides match component-launch."""
    spec = importlib.util.spec_from_file_location('_profile_dotenv', Path(REPO)/'scripts/write-env.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    path = Path(env_file or ENV_FILE)
    values = module.values(path.read_text()) if path.is_file() else {}
    if include_process:
        values.update(os.environ)
    return values


def _convergence_configured():
    try:
        convergence_settings(configured_values())
        return True
    except (ValueError, OSError):
        return False
    except Exception as error:
        # ReadError exposes only static messages; never print credentials or config.
        if getattr(error, 'code', None) in ('disabled', 'not_configured'):
            return False
        raise


def profiles(skills_dir=None, include_unconfigured=False):
    """Profiles whose skills are installed AND whose backend is configured.

    A profile is offered only when you can actually run it (FR-019 + the operator
    rule: never advertise a member with no configured backend). Pass
    include_unconfigured=True to also see profiles gated out for missing env."""
    installed = _installed_skills(skills_dir)
    env_keys = _configured_env()
    out = {}
    for pid, meta in PROFILE_MATCHERS.items():
        if _RUNTIME.kind == "hermes" and pid != "subnet":continue
        skills = _match_profile(pid, installed)
        if not skills:
            continue
        configured = _env_satisfied(meta, env_keys)
        if pid == "convergence":
            configured = _convergence_configured()
        if pid == "equinix":
            configured = configured and _equinix_enabled()
        if configured or include_unconfigured:
            out[pid] = {"description": meta["desc"], "skills": skills,
                        "configured": configured,
                        "requires_env": meta.get("requires_env")}
    return out


def scope(profile_id=None, custom_skills=None, skills_dir=None, installed=None):
    """Return a member scope: base floor (tier=base) + specialty (tier=specialty).
    `installed` overrides the installed-skill listing (a member spec passes it)."""
    out = list(BASE_FLOOR)
    specialty = []
    if installed is None:
        installed = _installed_skills(skills_dir)
    if profile_id and profile_id != "custom":
        specialty = _match_profile(profile_id, installed)
    elif custom_skills:
        installed = set(installed)
        specialty = [s for s in custom_skills if s in installed] or list(custom_skills)
    for s in specialty:
        out.append({"name": s, "type": "skill", "tier": "specialty"})
    return out


def _main(argv):
    cmd = argv[0] if argv else "list"
    if cmd == "list":
        show_all = "--all" in argv
        for pid, info in profiles(include_unconfigured=show_all).items():
            mark = "" if info.get("configured", True) else "  [backend not configured]"
            print(f"{pid:16s} {len(info['skills']):3d} skills  — {info['description']}{mark}")
    elif cmd == "show" and len(argv) > 1:
        info = profiles().get(argv[1])
        if not info:
            print(f"no such profile (or no installed skills match): {argv[1]}", file=sys.stderr)
            return 1
        print("\n".join(info["skills"]))
    elif cmd == "scope" and len(argv) > 1:
        pid = argv[1]
        custom = argv[2].split(",") if pid == "custom" and len(argv) > 2 else None
        print(json.dumps(scope(profile_id=pid, custom_skills=custom), indent=2))
    elif cmd == "spec" and len(argv) > 1:
        config = argv[argv.index("--border-config") + 1] if "--border-config" in argv[:-1] else str(_RUNTIME.config)
        try:
            servers = border_template_servers(config)
            spec, warnings = load_member_spec(argv[1], servers,
                                              allow_dangerous="--allow-dangerous-tools" in argv,
                                              providers=border_template_providers(config))
        except MemberSpecError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
        spec["kept_servers"] = sorted(spec_member_servers(spec, servers))
        spec["skill_allowlist"] = spec_skills(spec)
        spec["tool_policy"] = spec_tool_policy(spec)
        print(json.dumps(spec, indent=2))
    else:
        print(__doc__)
        return 1
    return 0


def border_template_providers(config):
    """The Border template's models.providers (spec 185); {} when it has none."""
    try:
        providers = (json.loads(Path(config).read_text()).get("models") or {}).get("providers")
    except (OSError, ValueError, AttributeError):
        return {}
    return providers if isinstance(providers, dict) else {}


def border_template_servers(config):
    """The Border template's mcp.servers a member spec is checked against."""
    try:
        servers = (json.loads(Path(config).read_text()).get("mcp") or {}).get("servers")
    except OSError as error:
        raise MemberSpecError(f"Border config {config} could not be read ({type(error).__name__})") from None
    except (ValueError, AttributeError):
        raise MemberSpecError(f"Border config {config} is not valid JSON") from None
    if not isinstance(servers, dict):
        raise MemberSpecError(f"Border config {config} has no mcp.servers")
    return servers


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
