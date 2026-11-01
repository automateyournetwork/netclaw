"""iN2N production enforcement controls (feature 057).

Probes and applies the three production controls the Border's posture aggregates:

  * sandbox      → NVIDIA OpenShell   (containment; `openshell` CLI)
  * model-guard  → Cisco DefenseClaw  (containment; `defenseclaw` CLI + security.mode)
  * audit        → GAIT git trail     (audit; bgp.federation.gait)

Design (see specs/057 research R1/R2/R3):
  * Each probe is a cheap local check, cached ~3s so a burst of delegation
    preflights doesn't spawn a burst of CLI calls, yet a control that just
    dropped is reflected on the next delegation.
  * All probes return (available: bool, detail: str). `detail` is the human
    reason when unavailable, surfaced in the degraded posture.
  * model-guard availability requires BOTH the DefenseClaw guard being reachable
    AND security.mode == 'defenseclaw' — a merely-installed-but-disabled CLI is
    NOT available, so production can never falsely report 'enforced' (analyze I1).
  * Fail-closed is enforced at the delegation preflight (posture.py) and at member
    launch (gateway.py); this module only reports truthfully.

No new third-party packages — stdlib + the already-installed CLIs.
"""

import asyncio
import ipaddress
import json
import logging
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Tuple
from urllib.parse import urlsplit

logger = logging.getLogger("n2n.controls")

_CACHE_TTL_S = 3.0
_cache: dict = {}   # name -> (expiry_epoch, (available, detail))


def _security_config_path() -> Path:
    """The DefenseClaw security-mode config. Per CLAUDE.md this lives in
    ~/.openclaw/config/openclaw.json — NOT the gateway's ~/.openclaw/openclaw.json,
    whose `security` object has a different schema (writing 'mode' there makes the
    gateway fail startup with 'security: Invalid input')."""
    from .runtime import selected
    return selected().home/'config/openclaw.json'


def security_mode() -> str:
    """DefenseClaw's guardrail mode ('hobby' | 'defenseclaw'). Default 'hobby'.
    Read from the DefenseClaw config, not the gateway config."""
    try:
        cfg = json.loads(_security_config_path().read_text())
        return (cfg.get("security") or {}).get("mode", "hobby")
    except Exception:
        return "hobby"


def is_production() -> bool:
    """The 057 risk-level enforcement flag (independent of security.mode)."""
    return os.environ.get("N2N_RISK_MODE", "testing").strip().lower() == "production"


def strict_all() -> bool:
    """Operator override: block on ANY missing control, including audit (FR-019)."""
    return os.environ.get("N2N_STRICT_ALL", "").strip().lower() in ("1", "true", "yes")


async def _run(cmd, timeout_s: float = 12.0) -> Tuple[int, str]:
    """Run a probe command; return (returncode, combined_output). -1 on error."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
        return proc.returncode, (out.decode(errors="replace") if out else "")
    except FileNotFoundError:
        return -1, "not found"
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return -1, "probe timed out"
    except Exception as e:  # pragma: no cover - defensive
        return -1, f"probe error: {e}"


def _cached(name: str):
    hit = _cache.get(name)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    return None


def _store(name: str, value: Tuple[bool, str]) -> Tuple[bool, str]:
    _cache[name] = (time.monotonic() + _CACHE_TTL_S, value)
    return value


def invalidate_cache():
    """Drop cached probe results (tests / after a known state change)."""
    global _pidns_probe, _coldstart_probe
    _cache.clear()
    _pidns_probe = None
    _coldstart_probe = None


SYSTEM_UNIT_DIR = "/etc/systemd/system"
_pidns_probe = None   # host property: a definitive probe result is kept per process (spec 165)
_SYSTEM_REMEDIATION = ("run always-on members as system units: python3 scripts/in2n-services.py "
                       "generate --system && python3 scripts/in2n-services.py enable --system")
_COLD_START_GAP = ("on-demand (cold-start) members still use user-scope confinement, which "
                   "cannot run OpenClaw on this host")
_COLDSTART_INSTALL = "python3 scripts/in2n-services.py coldstart install"
_COLD_START_FIX = ("install the confined system cold-start template (" + _COLDSTART_INSTALL +
                   "), make them always-on system units (on_demand=false, then generate "
                   "--system and enable --system) or run them on a host where user-scope "
                   "confinement can stat /proc/self/ns/pid")
# Spec 166: on-demand members cold-started as instances of a confined system
# template the operator may start through a narrow polkit rule.
COLDSTART_TEMPLATE = "netclaw-coldmember@.service"
COLDSTART_PROBE_UNIT = "netclaw-coldmember@probe.service"
_COLD_START_SYSTEM = ("on-demand members cold-start as confined system instances "
                      "(netclaw-coldmember@)")
_coldstart_probe = None   # (template stat signature, True) once authorization is proven


def _cold_start_clause(system_ok: bool) -> str:
    """How on-demand members cold-start where user-scope confinement fails."""
    return _COLD_START_SYSTEM if system_ok else f"{_COLD_START_GAP} (fix: {_COLDSTART_INSTALL})"


_PIDNS_REFUSED = 3


async def user_scope_pidns_readable() -> bool:
    """Can a mount-namespaced `systemd --user` unit stat /proc/self/ns/pid?
    OpenClaw 2026.10.9+ keys its gateway lock on that inode and refuses to run
    (GatewayLockNamespaceError) where the stat is EACCES — systemd 255 user units
    with PrivateTmp/ProtectSystem/ProtectHome/InaccessiblePaths (spec 165).
    Applies the generated units' mount directives. Only a definitive exit code is
    cached; a timeout/launch error reports False now and is re-probed next call."""
    global _pidns_probe
    if _pidns_probe is not None:
        return _pidns_probe
    if not shutil.which("systemd-run"):
        return False
    # The child exits 3 only for the stat refusal, so a systemd-run failure (also
    # non-zero) is not mistaken for a definitive answer.
    rc, _ = await _run(["systemd-run", "--user", "--wait", "--collect", "--pipe", "--quiet",
                        "-p", "PrivateTmp=yes", "-p", "ProtectSystem=strict", sys.executable,
                        "-c", "import os,sys\ntry: os.stat('/proc/self/ns/pid')\n"
                              "except PermissionError: sys.exit(3)"], timeout_s=20)
    if rc not in (0, _PIDNS_REFUSED):
        return False
    _pidns_probe = rc == 0
    return _pidns_probe


async def system_coldstart_available() -> bool:
    """Can this (unprivileged) process cold-start on-demand members as confined
    system instances (spec 166)? True iff the template is installed AND starting
    the reserved no-op instance `netclaw-coldmember@probe.service` succeeds without
    sudo or a password prompt — i.e. the polkit rule authorizes this user.

    Only the definitive success is kept, keyed on the template file's identity,
    so `coldstart install`/`remove` is picked up without a restart. A refusal is
    cached for the usual ~3s (polkitd may be starting); a timeout or launch error
    is not cached at all. invalidate_cache() / forget_system_coldstart() reset it."""
    global _coldstart_probe
    try:
        st = os.stat(os.path.join(SYSTEM_UNIT_DIR, COLDSTART_TEMPLATE))
    except OSError:
        return False
    signature = (st.st_dev, st.st_ino, st.st_mtime_ns, st.st_size)
    if _coldstart_probe is not None and _coldstart_probe[0] == signature:
        return _coldstart_probe[1]
    cached = _cached("coldstart")
    if cached is not None:
        return cached[0]
    if not shutil.which("systemctl"):
        return False
    rc, _ = await _run(["systemctl", "--no-ask-password", "start", COLDSTART_PROBE_UNIT],
                       timeout_s=30)
    if rc == -1:
        return False
    if rc == 0:
        _coldstart_probe = (signature, True)
        return True
    return _store("coldstart", (False, f"systemctl start {COLDSTART_PROBE_UNIT} exit {rc}"))[0]


def forget_system_coldstart():
    """Drop the cached system cold-start authorization (a start just failed)."""
    global _coldstart_probe
    _coldstart_probe = None
    _cache.pop("coldstart", None)


async def openclaw_user_scope_ok() -> bool:
    """Can user-scope confinement (member user units, confined_cold_start) run this
    Risk's runtime? Hermes is unaffected by the OpenClaw pid-namespace check."""
    return _runtime_kind() != "openclaw" or await user_scope_pidns_readable()


def _runtime_kind() -> str:
    try:
        from .runtime import selected
        return selected().kind
    except (OSError, ValueError):
        return "openclaw"


def _member_units(unit_dir: str) -> list:
    try:
        return sorted(f for f in os.listdir(unit_dir)
                      if f.startswith("netclaw-member-") and f.endswith(".service"))
    except OSError:
        return []


async def openshell_available() -> Tuple[bool, str]:
    """Back-compat alias → sandbox confinement probe (see sandbox_available)."""
    return await sandbox_available()


async def sandbox_available(on_demand_members=()) -> Tuple[bool, str]:
    """(True, "") if member CONFINEMENT is in effect; else (False, reason).

    Feature 057 US2 sandbox = HOST-LEVEL kernel confinement of each member process
    via systemd sandboxing directives (the member keeps its real home/tools/network
    but runs with reduced privileges + a read-only system + hidden master secrets).
    This replaces the earlier OpenShell-container approach, which could not run a
    live-infrastructure member (empty container: no tools, no network egress).

    Probe: `systemctl --user` is available AND the generated member units carry the
    confinement directives (NoNewPrivileges + ProtectSystem). On a host without a
    systemd user manager the confinement cannot be applied → unavailable → the
    posture honestly reports the sandbox control degraded.

    Spec 165: system-scope member units (/etc/systemd/system, `--system`) count
    too. Where OpenClaw cannot run under user-scope confinement (see
    user_scope_pidns_readable) user units — or no units at all — are reported
    unavailable with the --system remediation, never as working confinement.
    `on_demand_members` (spawnable cold-start member ids, from the caller that
    holds the risk) degrade an otherwise confined system-only setup on such a
    host: user-scope confined_cold_start cannot run them.

    Spec 166: unless the confined system cold-start template is installed and
    authorized (system_coldstart_available) — then they cold-start as system
    instances with the same confinement as system member units."""
    ok, detail = await _sandbox_units()
    if ok and on_demand_members and not await openclaw_user_scope_ok():
        if await system_coldstart_available():
            return True, detail if _COLD_START_SYSTEM in detail else _COLD_START_SYSTEM
        return False, (f"on-demand members ({', '.join(on_demand_members)}) cannot be cold-started: "
                       f"{_COLD_START_GAP} (a mount-namespaced user unit cannot stat "
                       f"/proc/self/ns/pid, GatewayLockNamespaceError) — {_COLD_START_FIX}")
    return ok, detail


async def _sandbox_units() -> Tuple[bool, str]:
    """Unit/manager half of sandbox_available, cached ~3s."""
    cached = _cached("sandbox")
    if cached is not None:
        return cached
    if not shutil.which("systemctl"):
        return _store("sandbox", (False, "systemctl not found — cannot confine members"))
    # Is a systemd --user manager reachable?
    rc, _ = await _run(["systemctl", "--user", "show-environment"], timeout_s=10)
    if rc != 0:
        return _store("sandbox", (False, "systemd --user manager unavailable"))
    # Are member units confined? Check every generated member unit (user scope,
    # and system scope from `in2n-services.py --system`) for the directives.
    members = _member_units(os.path.expanduser("~/.config/systemd/user"))
    system_members = _member_units(SYSTEM_UNIT_DIR)
    for scope, units in ((["--user"], members), ([], system_members)):
        for unit in units:
            rc, out = await _run(["systemctl", *scope, "show", unit,
                                  "-p", "NoNewPrivileges,ProtectSystem"], timeout_s=10)
            if "NoNewPrivileges=yes" not in out or "ProtectSystem=" not in out or "ProtectSystem=no" in out:
                flag = " --system" if not scope else ""
                return _store("sandbox", (False, f"member unit {unit} is not confined "
                                                  f"(regenerate: scripts/in2n-services.py generate{flag})"))
    # Spec 165: user-scope confinement (mount namespaces) breaks OpenClaw members
    # on some hosts. Hermes is unaffected; system units keep the full hardening.
    pidns_ok = await openclaw_user_scope_ok()
    # Spec 166: the system cold-start template is a working mechanism for
    # on-demand members even before any member unit exists.
    system_cold = not pidns_ok and await system_coldstart_available()
    if not pidns_ok and (members or not (system_members or system_cold)):
        where, fix = "systemd --user confinement", _SYSTEM_REMEDIATION
        if members:
            where = f"user-scope member units ({', '.join(members)})"
            fix = f"disable them (scripts/in2n-services.py disable <member>), then {fix}"
        return _store("sandbox", (False, f"{where} cannot run OpenClaw members: a mount-namespaced "
                                          f"user unit cannot stat /proc/self/ns/pid "
                                          f"(GatewayLockNamespaceError) — {fix}; "
                                          f"{_cold_start_clause(system_cold)}"))
    if not members and not system_members:
        # No member units yet — the mechanism is available; confinement applies on
        # generate. Report available so a fresh Border isn't falsely degraded.
        return _store("sandbox", (True, "systemd confinement available (no member units yet)"
                                        + ("" if pidns_ok else f"; {_COLD_START_SYSTEM}")))
    return _store("sandbox", (True, "" if pidns_ok else
                              f"system-scope member units confined; {_cold_start_clause(system_cold)}"))


DEFENSECLAW_GUARD_PORT = int(os.environ.get("DEFENSECLAW_GUARD_PORT", "4000"))


DEFENSECLAW_PLUGIN_ID = "defenseclaw"
_PLUGIN_ABSENT = "DefenseClaw OpenClaw plugin is not configured"


def _defenseclaw_plugin_paths(plugins) -> list:
    """Absolute `plugins.load.paths` directories named `defenseclaw` that hold the
    DefenseClaw plugin manifest (openclaw.plugin.json with id `defenseclaw`)."""
    load = plugins.get("load")
    paths = load.get("paths") if isinstance(load, dict) else None
    if not isinstance(paths, list):
        return []
    found = []
    for raw in paths:
        if not isinstance(raw, str) or not raw.strip():
            continue
        path = Path(os.path.expanduser(raw))
        if not (path.is_absolute() and path.name == DEFENSECLAW_PLUGIN_ID and path.is_dir()):
            continue
        try:
            manifest = json.loads((path / "openclaw.plugin.json").read_text())
        except (OSError, ValueError):
            continue
        if isinstance(manifest, dict) and manifest.get("id") == DEFENSECLAW_PLUGIN_ID:
            found.append(raw)
    return found


def _defenseclaw_guardrail() -> Tuple[bool, str]:
    """Does DefenseClaw's own config send the OpenClaw connector's traffic to the
    guard port probed here? The plugin entry carries no target; the plugin reads
    `guardrail` from $DEFENSECLAW_HOME/config.yaml (default ~/.defenseclaw). Only
    the top-level `guardrail:` block's scalar keys are read (no YAML dependency):
    enabled must be true, connector must be openclaw, and port, when set, must
    equal DEFENSECLAW_GUARD_PORT (DefenseClaw's default is 4000)."""
    home = Path(os.environ.get("DEFENSECLAW_HOME") or os.path.expanduser("~/.defenseclaw"))
    try:
        lines = (home / "config.yaml").read_text().splitlines()
    except OSError:
        return False, "DefenseClaw config.yaml is unavailable"
    block, inside = {}, False
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            inside = line.split("#", 1)[0].strip() == "guardrail:"
            continue
        if inside and line.startswith("  ") and not line.startswith("   ") and ":" in line:
            key, _, value = line.strip().partition(":")
            block[key.strip()] = value.split("#", 1)[0].strip().strip("'\"")
    if block.get("enabled", "").lower() != "true":
        return False, "DefenseClaw guardrail is not enabled in config.yaml"
    if block.get("connector") != "openclaw":
        return False, "DefenseClaw guardrail connector is not openclaw"
    port = block.get("port")
    if port and port != str(DEFENSECLAW_GUARD_PORT):
        return False, f"DefenseClaw guardrail port {port} is not the probed guard port {DEFENSECLAW_GUARD_PORT}"
    return True, ""


# Providers that are local by default when no baseUrl is declared.
_LOCAL_PROVIDERS = {"ollama", "lmstudio", "lm_studio", "vllm", "llamacpp", "llama-cpp"}


def _local_model_provider(cfg, models) -> str:
    """The first selected model whose provider endpoint is loopback, private or
    link-local (or a local-by-default provider without a baseUrl), else ''. The
    plugin route is not trusted for those: an interceptor need not route local
    traffic through the proxy, and the proxy's unknown-domain block cannot help."""
    providers = ((cfg.get("models") or {}).get("providers") or {}) if isinstance(cfg, dict) else {}
    for model in models:
        if not isinstance(model, str) or "/" not in model:
            continue
        name = model.split("/", 1)[0]
        decl = providers.get(name) if isinstance(providers, dict) else None
        base = decl.get("baseUrl") if isinstance(decl, dict) else None
        if not base:
            if name.lower() in _LOCAL_PROVIDERS:
                return model
            continue
        host = (urlsplit(base).hostname or "").lower()
        if host == "localhost" or host.endswith((".local", ".localhost", ".internal")):
            return model
        try:
            addr = ipaddress.ip_address(host)
        except ValueError:
            continue
        if addr.is_loopback or addr.is_private or addr.is_link_local:
            return model
    return ""


def defenseclaw_plugin_route(cfg) -> Tuple[bool, str]:
    """Is the DefenseClaw 1.x OpenClaw plugin connector configured (spec 167 F3)?

    `defenseclaw setup guardrail --connector openclaw` does not add a
    `defenseclaw/<model>` provider; it installs an OpenClaw plugin (installed at
    ~/.openclaw/extensions/defenseclaw) whose fetch interceptor sends every model
    request through the guardrail proxy. Accepted only when ALL hold in the
    effective OpenClaw config:
      * `plugins.enabled` is not false (the global plugin switch);
      * `plugins.entries.defenseclaw.enabled` is true;
      * `plugins.allow`, if present, is a list that includes "defenseclaw";
      * `plugins.deny`, if present, is a list that does not include it;
      * `plugins.load.paths` contains an existing absolute directory whose
        basename is `defenseclaw`.
    Anything malformed is rejected (fail-closed). Returns (ok, detail)."""
    plugins = cfg.get("plugins") if isinstance(cfg, dict) else None
    if not isinstance(plugins, dict):
        return False, _PLUGIN_ABSENT
    entries = plugins.get("entries")
    entry = entries.get(DEFENSECLAW_PLUGIN_ID) if isinstance(entries, dict) else None
    if entry is None:
        return False, _PLUGIN_ABSENT
    if plugins.get("enabled") is False:
        return False, "OpenClaw plugins are disabled (plugins.enabled=false)"
    if not isinstance(entry, dict) or entry.get("enabled") is not True:
        return False, "DefenseClaw OpenClaw plugin is not enabled (plugins.entries.defenseclaw.enabled)"
    allow = plugins.get("allow")
    if allow is not None and (not isinstance(allow, list) or DEFENSECLAW_PLUGIN_ID not in allow):
        return False, "DefenseClaw OpenClaw plugin is not in plugins.allow"
    deny = plugins.get("deny")
    if deny is not None and (not isinstance(deny, list) or DEFENSECLAW_PLUGIN_ID in deny):
        return False, "DefenseClaw OpenClaw plugin is denied (plugins.deny)"
    if not _defenseclaw_plugin_paths(plugins):
        return False, ("DefenseClaw OpenClaw plugin is not loaded: plugins.load.paths has no "
                       "defenseclaw extension directory with its plugin manifest")
    guard_ok, guard_detail = _defenseclaw_guardrail()
    if not guard_ok:
        return False, guard_detail
    return True, "guarded via DefenseClaw OpenClaw plugin"


def defenseclaw_plugin_config(cfg):
    """Only the DefenseClaw plugin configuration from `cfg` (a fresh `plugins`
    object), or None when defenseclaw_plugin_route(cfg) does not accept it. Other
    plugins' entries, allow-list items and load paths are never included."""
    if not defenseclaw_plugin_route(cfg)[0]:
        return None
    plugins = cfg["plugins"]
    out = {"entries": {DEFENSECLAW_PLUGIN_ID: json.loads(json.dumps(plugins["entries"][DEFENSECLAW_PLUGIN_ID]))},
           "load": {"paths": _defenseclaw_plugin_paths(plugins)}}
    if isinstance(plugins.get("allow"), list):
        out["allow"] = [DEFENSECLAW_PLUGIN_ID]
    return out


def _selected_models(cfg, model_override=None) -> list:
    """Primary (or override), agent fallbacks and inherited default fallbacks for
    N2N_AGENT_ID. Raises ValueError when the fallback configuration is invalid."""
    agents = cfg.get("agents") or {}
    model = (agents.get("defaults") or {}).get("model")
    inherited_fallbacks = model.get("fallbacks", []) if isinstance(model, dict) else []
    agent_id = os.environ.get("N2N_AGENT_ID", "main")
    for agent in agents.get("list") or []:
        if agent.get("id") == agent_id and agent.get("model") is not None:
            model = agent["model"]
    primary = model.get("primary") if isinstance(model, dict) else model
    fallbacks = model.get("fallbacks", []) if isinstance(model, dict) else []
    if not isinstance(fallbacks, list) or not isinstance(inherited_fallbacks, list):
        raise ValueError("model fallback configuration is invalid")
    return [model_override if model_override is not None else primary, *fallbacks, *inherited_fallbacks]


def _provider_model_route(cfg, model_override=None) -> Tuple[bool, str]:
    """Every selected model uses the `defenseclaw/<model>` loopback provider."""
    try:
        try:
            selected = _selected_models(cfg, model_override)
        except ValueError as e:
            return False, str(e)
        if not all(isinstance(m, str) and m.startswith("defenseclaw/") and m.split("/", 1)[1]
                   for m in selected):
            return False, "primary, override and fallback models must use the defenseclaw provider"
        provider = ((cfg.get("models") or {}).get("providers") or {}).get("defenseclaw") or {}
        url = urlsplit(provider.get("baseUrl", ""))
        if (url.scheme not in ("http", "https") or url.hostname not in ("localhost", "127.0.0.1", "::1")
                or url.port != DEFENSECLAW_GUARD_PORT or url.username or url.password):
            return False, "defenseclaw provider must target the configured loopback guard port"
        return True, "guarded model route configured"
    except (ValueError, TypeError, AttributeError):
        return False, "effective model route configuration is unavailable or invalid"


def guarded_model_route(model_override=None) -> Tuple[bool, str]:
    """Check the effective local configuration; never rewrite provider settings.

    Two OpenClaw routes are accepted:
      * provider route: primary, override and every fallback model use a
        `defenseclaw/<model>` provider whose baseUrl is the loopback guard port;
      * plugin route (DefenseClaw 1.x, spec 167): the DefenseClaw OpenClaw
        plugin is enabled, allowed, not denied and loaded from an existing
        `defenseclaw` extension directory (defenseclaw_plugin_route). The plugin
        intercepts every model request, so any model/override is routed through
        the proxy, provided DefenseClaw's own guardrail config targets this guard
        port for the openclaw connector and the extension holds the plugin
        manifest. A model whose provider domain DefenseClaw does not know cannot
        bypass the guard: the proxy blocks unknown provider domains fail-closed
        (403), so it needs `defenseclaw setup provider add` to work at all. Models
        on loopback/private/local providers are refused on this route: a fetch
        interceptor need not send local traffic through the proxy.
    Proxy reachability and security.mode are checked by defenseclaw_available.
    Hermes is not qualified for either route."""
    from .runtime import selected as selected_runtime
    runtime=selected_runtime()
    if runtime.kind=='hermes':return False, 'Hermes model-guard integration is not qualified; production delegation is unavailable'
    try:
        state = Path(os.environ.get("OPENCLAW_STATE_DIR") or os.environ.get("OPENCLAW_HOME")
                     or os.path.expanduser("~/.openclaw"))
        config = Path(os.environ.get("OPENCLAW_CONFIG_PATH") or state / "openclaw.json")
        cfg = json.loads(config.read_text())
        if not isinstance(cfg, dict):
            raise ValueError("config is not an object")
    except (OSError, ValueError, TypeError, AttributeError):
        return False, "effective model route configuration is unavailable or invalid"
    ok, detail = _provider_model_route(cfg, model_override)
    if ok:
        return ok, detail
    plugin_ok, plugin_detail = defenseclaw_plugin_route(cfg)
    if plugin_ok:
        try:
            local = _local_model_provider(cfg, _selected_models(cfg, model_override))
        except (ValueError, TypeError, AttributeError):
            return False, "effective model route configuration is unavailable or invalid"
        if local:
            return False, (f"model {local} uses a local or private provider endpoint; the "
                           "DefenseClaw plugin route is not trusted for it (use the defenseclaw provider route)")
        return plugin_ok, plugin_detail
    # A present-but-unusable plugin explains the failure better than the provider.
    if plugin_detail != _PLUGIN_ABSENT:
        return False, f"{detail}; {plugin_detail}"
    return False, detail


async def defenseclaw_available() -> Tuple[bool, str]:
    """(True, "") if DefenseClaw model-I/O guarding is actually in effect; else (False, reason).

    DefenseClaw guards model I/O via its **LLM guardrail proxy** (a Go proxy,
    default port 4000, enabled by `defenseclaw setup guardrail`) that every prompt
    and response is routed through for inspection — NOT via a per-call CLI command
    (there is no `defenseclaw tool inspect`). So "available" requires ALL of:
    `defenseclaw` on PATH, `security.mode == 'defenseclaw'`, AND the guardrail
    proxy reachable. A merely-installed CLI with the proxy down is NOT available —
    this is what prevents a false 'enforced' (the 056 "silent bypass to direct
    provider" bug). To reach enforced, run `defenseclaw setup guardrail --mode
    action` and route members through the proxy."""
    # Recheck configuration before even a cached liveness result: a live proxy
    # does not mean the configured model actually uses it.
    mode_ok, detail = require_defenseclaw_mode()
    if not mode_ok:
        return False, detail
    route_ok, detail = guarded_model_route()
    if not route_ok:
        return False, detail
    cached = _cached("model-guard")
    if cached is not None:
        return cached
    if not shutil.which("defenseclaw"):
        return _store("model-guard", (False, "defenseclaw CLI not found on PATH"))
    # The authoritative signal is the guardrail PROXY being up — that is the guard
    # (every prompt/response routed through it for inspection). A reachable proxy
    # means guarding is actually happening; a down proxy means it is not (no false
    # 'enforced').
    if not await _guard_proxy_up():
        return _store("model-guard",
                      (False, f"DefenseClaw guardrail proxy not reachable on :"
                              f"{DEFENSECLAW_GUARD_PORT} (run: defenseclaw setup guardrail "
                              f"then defenseclaw-gateway start)"))
    return _store("model-guard", (True, ""))


async def _guard_proxy_up() -> bool:
    """Is the DefenseClaw guardrail proxy accepting connections?"""
    try:
        fut = asyncio.open_connection("127.0.0.1", DEFENSECLAW_GUARD_PORT)
        reader, writer = await asyncio.wait_for(fut, timeout=3)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


def gait_recording() -> Tuple[bool, str]:
    """(True, "") if the GAIT git trail is initialized and writable; else (False, reason)."""
    cached = _cached("audit")
    if cached is not None:
        return cached
    try:
        from . import gait
        ok, detail = gait.ensure_repo()
        return _store("audit", (ok, detail))
    except Exception as e:
        return _store("audit", (False, f"GAIT unavailable: {e}"))


# ---- application helpers (used by gateway.py / service.py) ----------------

# Portable systemd confinement props applied to a member process (feature 057).
# Mirrors scripts/in2n-services.py _hardening_block portable set; used for
# cold-started (on-demand) members via `systemd-run --user` so even non-service
# members run confined in production. Capability/namespace props are added by the
# service generator only where the manager supports them (native Linux).
_CONFINE_PROPS = [
    "NoNewPrivileges=yes", "PrivateTmp=yes", "ProtectSystem=strict",
    "ReadWritePaths=%h", "InaccessiblePaths=-%h/.openclaw/.env",
]


_INSTANCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")


def confined_cold_start(launch_cmd: str, member_id: str, system: bool = False) -> list:
    """Return an argv that cold-starts a member CONFINED via a transient
    `systemd-run --user` unit (feature 057). Falls back to the bare command if
    systemd-run is unavailable (the posture will report the sandbox degraded).

    system=True (spec 166; the caller has established system_coldstart_available):
    start the member's instance of the confined system template instead. The
    instance launcher resolves the member's own launch command from the Risk
    registry, so launch_cmd is not passed. --no-ask-password: never a prompt."""
    slug = member_id.replace("/", "-")
    if system:
        if not _INSTANCE.fullmatch(slug) or slug == "probe":   # probe: reserved no-op
            raise ValueError(f"member id {member_id!r} is not a valid cold-start instance name")
        return ["systemctl", "start", "--no-block", "--no-ask-password",
                f"netclaw-coldmember@{slug}.service"]
    if not shutil.which("systemd-run"):
        return ["/bin/sh", "-c", launch_cmd]
    argv = ["systemd-run", "--user", "--collect",
            "--unit", f"netclaw-coldmember-{slug}"]
    # systemd-run sends -p properties over D-Bus, where %-specifiers are NOT
    # expanded (unlike unit files) — %h must be resolved here or the transient
    # unit is rejected with "Invalid ReadWritePaths".
    home = os.path.expanduser("~")
    for p in _CONFINE_PROPS:
        argv += ["-p", p.replace("%h", home)]
    argv += ["/bin/sh", "-c", launch_cmd]
    return argv


async def component_scan(skills: list) -> Tuple[bool, str]:
    """DefenseClaw component scan of a member's scoped skills before it runs
    (FR-008). Returns (ok, verdict): ok=True → 'pass'; ok=False → 'flagged:<name>'
    (a component was flagged) or 'error:<detail>' (scan could not run → fail-closed
    in production). An empty skill list passes trivially."""
    if not skills:
        return True, "pass"
    if not shutil.which("defenseclaw"):
        return False, "error:defenseclaw CLI not found"
    for name in skills:
        rc, out = await _run(["defenseclaw", "skill", "scan", str(name)], timeout_s=60.0)
        if rc == -1:
            return False, f"error:scan failed for {name}"
        low = out.lower()
        # DefenseClaw exits non-zero on a flag. Match verdicts, not bare
        # substrings: 0.8.x prints "blocked=0" in EVERY summary (even CLEAN)
        # and the word "critical" can appear in finding descriptions, so the
        # old substring checks flagged clean scans.
        if (rc != 0
                or re.search(r"verdict:\s*(critical|high)", low)
                or re.search(r"\bblocked=[1-9]", low)
                or "high severity" in low):
            return False, f"flagged:{name}"
    return True, "pass"


def require_defenseclaw_mode() -> Tuple[bool, str]:
    """Require (verify, do NOT mutate) security.mode='defenseclaw' on entering
    production (T019a / FR-007). This is what guards the BORDER's own model turns,
    which run through the OpenClaw gateway.

    Returns (ok, detail). This is deliberately CHECK-ONLY: a daemon must never
    silently rewrite the host's security configuration (an earlier auto-write into
    the wrong file broke the gateway). If mode isn't 'defenseclaw', the operator
    enables it via the DefenseClaw tooling (./scripts/defenseclaw-enable.sh); until
    then model-guard probes unavailable → posture honestly degraded, never a false
    'enforced'."""
    mode = security_mode()
    if mode == "defenseclaw":
        return True, "security.mode=defenseclaw (Border model turns guarded)"
    return (False, f"security.mode is '{mode}' — enable DefenseClaw "
                   f"(./scripts/defenseclaw-enable.sh) to reach production-enforced")
