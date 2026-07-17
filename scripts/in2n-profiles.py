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
No third-party deps (stdlib only), matching scripts/register-all-mcps.py.
"""

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SKILLS_DIRS = [
    os.path.join(REPO, "workspace", "skills"),
    os.path.expanduser("~/.openclaw/workspace/skills"),
]

# The mandatory base floor every member carries (mirror of bgp/federation/risk.py
# BASE_FLOOR — kept here so the installer/profile tool has no cross-import).
BASE_FLOOR = [
    {"name": "n2n-member-runtime", "type": "skill", "tier": "base"},
    {"name": "self-status",        "type": "skill", "tier": "base"},
    {"name": "member_heartbeat",   "type": "tool",  "tier": "base"},
    {"name": "member_report_audit","type": "tool",  "tier": "base"},
]

ENV_FILE = os.path.expanduser("~/.openclaw/.env")

# Profile definitions: skills (prefixes/exact) + `requires_env` (any-of). A
# profile is offered ONLY when its skills are installed AND its backend is
# configured — never advertise a member you cannot actually run. Profiles with
# no `requires_env` run locally and are always offered when their skills exist.
# Granularity principle (interview): ONE claw per vendor/platform/tool. Real
# integrations each get a dedicated, env-gated member; only UTILITIES stay grouped.
PROFILE_MATCHERS = {
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
    "pyats":    {"prefixes": ["pyats-"], "requires_env": ["PYATS_MCP_SCRIPT", "PYATS_TESTBED_PATH"],
                 "desc": "pyATS network test/validation"},
    # ── assurance / analysis (each dedicated) ──
    "ipfabric": {"exact": ["ipfabric"], "requires_env": ["IPFABRIC_HOST"],
                 "desc": "IP Fabric network assurance"},
    "suzieq":   {"exact": ["suzieq-observability"], "desc": "SuzieQ network observability"},
    "batfish":  {"exact": ["batfish-config-analysis", "batfish-intent-validation"],
                 "desc": "Batfish config analysis + intent validation"},
    "forward":  {"exact": ["forward"], "requires_env": ["FORWARD_API_KEY"],
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
    "fortimanager": {"prefixes": ["fortimanager-"], "requires_env": ["FORTIMANAGER_MCP_CMD"],
                     "desc": "FortiManager"},
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
    "cml": ["CML_"], "containerlab": ["CLAB_"], "pyats": ["PYATS_"],
    "ipfabric": ["IPFABRIC_"], "suzieq": ["SUZIEQ_"], "batfish": ["BATFISH_"],
    "forward": ["FORWARD_"], "gtrace": ["GTRACE_"],
    "packet": ["PACKET_BUDDY_", "KUBESHARK_"],
    "itential": ["ITENTIAL_"], "aap": ["AAP_"], "nso": ["NSO_"], "terraform": ["TERRAFORM_", "TF_", "TFE_"],
    "aci": ["ACI_"], "catalyst-center": ["CATC_"], "f5": ["F5_"], "meraki": ["MERAKI_"],
    "sdwan": ["SDWAN_", "PRISMA_"],
    "ise": ["ISE_"], "asa": ["ASA_"], "checkpoint": ["CHECKPOINT_", "CHKP_"],
    "paloalto": ["PANOS_", "FMC_"], "fortimanager": ["FORTIMANAGER_"],
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


def env_slice_keys(profile, env_keys):
    """Return the env-key NAMES a member of `profile` should receive (least
    privilege): its integration prefixes + the base-member prefixes. Values are
    the caller's concern (never logged)."""
    prefixes = tuple(ENV_PREFIXES.get(profile, []) + BASE_MEMBER_ENV_PREFIXES)
    return sorted(k for k in env_keys if k.startswith(prefixes))


# Profile → OpenClaw mcp.servers names to keep in a member's scoped config
# (many integrations are skill-driven with no MCP server → empty list is fine;
# the member still gets its workspace skills + .env creds). memory-mcp is always
# added as base floor by the provisioner.
MCP_SERVERS = {
    "ipfabric": ["ipfabric-mcp"], "suzieq": ["suzieq-mcp"], "batfish": ["batfish-mcp"],
    "forward": ["forward-mcp"], "gns3": ["gns3-mcp"], "azure": ["azure-network-mcp"],
    "sdwan": ["prisma-sdwan-mcp"], "splunk": ["splunk-mcp"], "github": ["gitlab-mcp"],
    "gnmi": ["gnmi-mcp"], "checkpoint": ["chkp-management", "chkp-management-logs",
        "chkp-policy-insights", "chkp-threat-prevention", "chkp-quantum-gaia"],
    "viz": ["blender-mcp", "sketchfab-mcp"],
    # skill-driven (no dedicated MCP server): cml, pyats, aci, catalyst-center,
    # f5, ise, nso, netbox, infoblox, nmap, gtrace, itential, aap, packet, etc.
}

# Model tier per member (interview: Border=Opus; heavy members=Sonnet; trivial=Haiku).
_HEAVY = {"cml", "pyats", "itential", "aap", "nso", "aci", "catalyst-center", "f5",
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


def _match_profile(profile_id, installed):
    m = PROFILE_MATCHERS.get(profile_id)
    if not m:
        return []
    prefixes = tuple(m.get("prefixes", []))
    exact = set(m.get("exact", []))
    return [s for s in installed
            if s in exact or (prefixes and s.startswith(prefixes))]


def profiles(skills_dir=None, include_unconfigured=False):
    """Profiles whose skills are installed AND whose backend is configured.

    A profile is offered only when you can actually run it (FR-019 + the operator
    rule: never advertise a member with no configured backend). Pass
    include_unconfigured=True to also see profiles gated out for missing env."""
    installed = _installed_skills(skills_dir)
    env_keys = _configured_env()
    out = {}
    for pid, meta in PROFILE_MATCHERS.items():
        skills = _match_profile(pid, installed)
        if not skills:
            continue
        configured = _env_satisfied(meta, env_keys)
        if configured or include_unconfigured:
            out[pid] = {"description": meta["desc"], "skills": skills,
                        "configured": configured,
                        "requires_env": meta.get("requires_env")}
    return out


def scope(profile_id=None, custom_skills=None, skills_dir=None):
    """Return a member scope: base floor (tier=base) + specialty (tier=specialty)."""
    out = list(BASE_FLOOR)
    specialty = []
    if profile_id and profile_id != "custom":
        specialty = _match_profile(profile_id, _installed_skills(skills_dir))
    elif custom_skills:
        installed = set(_installed_skills(skills_dir))
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
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
