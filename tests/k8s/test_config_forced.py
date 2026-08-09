"""NetClaw's configuration, not upstream's defaults. Spec 084, FR-019..FR-022, SC-014/016/017.

Upstream's defaults are wrong in two ways that matter: `denied_resources` is empty, so
SECRETS ARE READABLE; and the default toolset is 21 tools / 5,716 tokens, which busts the
manifest ceiling. Neither is a preference — both must be overridden by NetClaw.
"""
from __future__ import annotations
import json, os, re
from _harness import FAILURES, check, read, repo, run  # noqa: F401

DISABLED = ["nodes_log", "nodes_stats_summary", "nodes_top", "pods_top", "pods_log", "projects_list"]

def _toml():
    return read("mcp-servers", "k8s-mcp", "config.toml")

def test_read_only_is_forced():
    t = _toml()
    check("read_only is set true in NetClaw's own config", re.search(r"^read_only\s*=\s*true", t, re.M) is not None,
          "absent — the integration would inherit whatever upstream defaults to")
    check("the config explains that enforcement is at registration time",
          "registration" in t.lower(), "a future maintainer needs to know filtered tools are unreachable, not just hidden")

def test_toolset_is_trimmed():
    t = _toml()
    check("toolsets is restricted to core", 'toolsets = ["core"]' in t, "the default surface busts the ceiling")
    for tool in DISABLED:
        check(f"{tool} is disabled", tool in t, "missing from disabled_tools")
    check("the config records WHY trimming is required",
          "5,716" in t or "5716" in t or "ceiling" in t.lower(),
          "without the reason someone will 'simplify' this back to the default and bust the ceiling")

def test_secrets_are_denied():
    t = _toml()
    check("a denied_resources block exists", "[[denied_resources]]" in t,
          "upstream defaults this to empty — SECRETS WOULD BE READABLE")
    check("Secret is the denied kind", re.search(r'kind\s*=\s*"Secret"', t) is not None, "not denied")
    check("the config notes upstream's default is permissive",
          "default" in t.lower() and "secret" in t.lower(), "the hazard is unstated")

def test_registration_is_explicit_not_ambient():
    cfg = json.loads(read("config", "openclaw.json"))["mcpServers"]["k8s-mcp"]
    args = " ".join(cfg.get("args", []))
    check("the config file is passed explicitly", "--config" in args, "would fall back to upstream defaults")
    check("a kubeconfig is passed explicitly", "--kubeconfig" in args,
          "AMBIENT CONTEXT RISK — without this it talks to whatever cluster the operator last used, "
          "possibly production")
    env = cfg.get("env", {})
    check("the kubeconfig comes from an env var, not a literal path",
          any("${" in str(v) for v in env.values()), "a literal path is not portable")
    check("no literal token or cert material in the registration",
          not any(re.search(r"(BEGIN |eyJ[A-Za-z0-9_-]{10,})", str(v)) for v in env.values()),
          "credential material in config/openclaw.json")

def test_no_context_switching_tool_is_configured():
    t = _toml()
    for bad in ("configuration_switch", "contexts_set", "kubectl_context"):
        check(f"no {bad} enabled", bad not in t, "the model must not be able to change clusters")

def test_no_mutation_toolsets():
    t = _toml()
    for bad in ("helm", "config_write", "write"):
        check(f"toolset '{bad}' not enabled", f'"{bad}"' not in t.split("disabled_tools")[0], "mutation surface")

TESTS = [test_read_only_is_forced, test_toolset_is_trimmed, test_secrets_are_denied,
         test_registration_is_explicit_not_ambient, test_no_context_switching_tool_is_configured,
         test_no_mutation_toolsets]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "config enforcement"))
