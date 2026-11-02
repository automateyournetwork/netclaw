"""ACME (Let's Encrypt) domain-verified credentials via lego (feature 060, US1).

Drives the vendored `lego` binary (single Go executable) to obtain and renew a
publicly-trusted certificate for this claw's domain over the DNS-01 challenge —
no inbound reachability, so it works behind changing tunnels/NAT (FR-004). DNS
automation is provider-agnostic (Cloudflare, Route53, GoDaddy, acme-dns
delegation, …); the provider + its credentials come from the environment per
lego's convention (FR-004a). The mesh launchers pass only NETCLAW_/N2N_/BGP_
settings from the runtime env files to the daemon, so the provider's own
variables (named by `lego dnshelp`) are read from those files here and given
to lego alone (spec 170). We drive an existing, proven ACME client rather than
implementing RFC 8555.

Config (see .env.example):
  N2N_CLAW_DOMAIN        e.g. netclaw.automateyournetwork.ca
  N2N_ACME_DNS_PROVIDER  lego provider id (godaddy | cloudflare | acme-dns | …)
  N2N_ACME_EMAIL         ACME account contact
  provider creds         per lego (GODADDY_API_KEY/SECRET, CLOUDFLARE_DNS_API_TOKEN, …)
  N2N_ACME_STAGING=1     use the LE staging endpoint (for testing)
  N2N_LEGO_BIN           override the lego path (default ~/.openclaw/n2n/bin/lego)
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import re
import signal
from pathlib import Path
from typing import Optional

logger = logging.getLogger("n2n.acme")

_LE_PROD = "https://acme-v02.api.letsencrypt.org/directory"
_LE_STAGING = "https://acme-staging-v02.api.letsencrypt.org/directory"
# `lego dnshelp` lists each variable as `  - "NAME":  description`.
_DNSHELP_NAME = re.compile(r'^\s*-\s*"([A-Z][A-Z0-9_]*)":', re.M)


def lego_bin() -> str:
    return os.environ.get("N2N_LEGO_BIN",
                          os.path.expanduser("~/.openclaw/n2n/bin/lego"))


def _lego_dir(base_dir) -> Path:
    d = Path(base_dir) / "keys" / "acme"
    d.mkdir(parents=True, exist_ok=True)
    return d


def configured() -> bool:
    """True when this claw is set up for domain-verified identity."""
    return bool(os.environ.get("N2N_CLAW_DOMAIN") and
                os.environ.get("N2N_ACME_DNS_PROVIDER"))


def _argv(base_dir, domain: str, action: str) -> list:
    provider = os.environ["N2N_ACME_DNS_PROVIDER"]
    email = os.environ.get("N2N_ACME_EMAIL", "")
    server = _LE_STAGING if os.environ.get("N2N_ACME_STAGING") in ("1", "true", "yes") else _LE_PROD
    argv = [lego_bin(), "--accept-tos", "--server", server,
            "--email", email, "--dns", provider, "--domains", domain,
            "--path", str(_lego_dir(base_dir))]
    # Point the propagation check at the zone's authoritative nameservers so lego
    # waits for the record to be live where the CA will look (GoDaddy takes ~30s;
    # the local resolver otherwise passes too early → CA gets NXDOMAIN). Set
    # N2N_ACME_RESOLVERS to a comma-separated list (e.g. ns51.domaincontrol.com:53).
    for r in filter(None, os.environ.get("N2N_ACME_RESOLVERS", "").split(",")):
        argv += ["--dns.resolvers", r.strip()]
    argv.append(action)
    return argv


async def _run(argv: list, timeout_s: float = 180.0, env: Optional[dict] = None):
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        env=os.environ.copy() if env is None else env, start_new_session=(os.name == "posix"))
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
        return proc.returncode, (out.decode(errors="replace") if out else "")
    except BaseException:
        try:
            if os.name == "posix":
                os.killpg(proc.pid, signal.SIGKILL)
            elif proc.returncode is None:
                proc.kill()
        except ProcessLookupError:
            pass
        await proc.communicate()  # drain and reap before reporting timeout/cancellation
        raise


async def _provider_names(provider: str) -> set:
    """Variables lego reads for `provider`, plus their `_FILE` forms."""
    try:
        rc, out = await _run([lego_bin(), "dnshelp", "--code", provider], timeout_s=15.0)
    except (OSError, asyncio.TimeoutError):
        return set()
    if rc != 0:
        logger.warning("acme: lego has no DNS provider %r", provider)
        return set()
    names = set(_DNSHELP_NAME.findall(out))
    return names | {n + "_FILE" for n in names}


def _env_file_values() -> dict:
    """Literal assignments from the runtime env files, mesh.systemd.env last
    (the launchers' order). Nothing is expanded or executed."""
    runtime_env = os.environ.get("NETCLAW_RUNTIME_ENV")
    if not runtime_env:
        return {}
    spec = importlib.util.spec_from_file_location(
        "_netclaw_env_writer", Path(__file__).resolve().parents[4] / "scripts" / "write-env.py")
    writer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(writer)
    values = {}
    for path in (Path(runtime_env), Path(runtime_env).with_name("mesh.systemd.env")):
        try:
            values.update(writer.values(path.read_text()))
        except FileNotFoundError:
            continue
        except (OSError, ValueError) as e:
            logger.warning("acme: cannot read %s: %s", path, type(e).__name__)
    return values


async def _lego_env() -> dict:
    """The daemon's environment plus the DNS provider's variables from the
    runtime env files. A variable already in the environment wins."""
    env = os.environ.copy()
    names = await _provider_names(os.environ["N2N_ACME_DNS_PROVIDER"])
    values = _env_file_values() if names else {}
    for name in names:
        if name not in env and values.get(name):
            env[name] = values[name]
    return env


def _cert_path(base_dir, domain: str) -> Path:
    # lego writes <domain>.crt (fullchain) + <domain>.key under <path>/certificates/
    return _lego_dir(base_dir) / "certificates" / f"{domain}.crt"


def _read_cert(base_dir, domain: str) -> Optional[str]:
    p = _cert_path(base_dir, domain)
    return p.read_text() if p.exists() else None


async def issue(domain: str, base_dir) -> Optional[str]:
    """Obtain a new certificate for `domain` (first issuance). Returns the
    fullchain PEM, or None on failure (logged)."""
    if not os.path.exists(lego_bin()):
        logger.warning("acme: lego not installed (%s) — run scripts/lib/fetch-lego.sh", lego_bin())
        return None
    rc, out = await _run(_argv(base_dir, domain, "run"), env=await _lego_env())
    if rc != 0:
        logger.warning("acme: issuance for %s failed (rc=%s): %s", domain, rc, out[-500:])
        return None
    return _read_cert(base_dir, domain)


async def renew(domain: str, base_dir) -> Optional[str]:
    """Renew an existing certificate (idempotent; lego no-ops if not yet due
    unless forced). Returns the current fullchain PEM."""
    if not os.path.exists(lego_bin()):
        return None
    # The rotation schedule decides when renewal is due, and operator rotation
    # waits for the result, so skip lego's random pre-renewal sleep (up to
    # 8 minutes), which outlasts the run timeout.
    rc, out = await _run(_argv(base_dir, domain, "renew") + ["--days", "30", "--reuse-key", "--no-random-sleep"],
                         env=await _lego_env())
    if rc != 0:
        logger.warning("acme: renew for %s failed (rc=%s): %s", domain, rc, out[-500:])
        # Fall back to the on-disk cert if present (renew may no-op yet succeed).
    return _read_cert(base_dir, domain)


async def ensure_domain_credential(service) -> Optional[str]:
    """Called at daemon startup when N2N_CLAW_DOMAIN is set: obtain the cert if
    absent, register it for rotation, and record the claw's own domain-verified
    trust on its identity. Returns the cert PEM or None."""
    if not configured():
        return None
    domain = os.environ["N2N_CLAW_DOMAIN"]
    base = service.manager.base_dir
    cert = _read_cert(base, domain) or await issue(domain, base)
    if not cert:
        return None
    try:
        from .rotation import RotationManager
        RotationManager(service).register("acme", domain, cert, issuer="ACME")
    except Exception as e:
        logger.debug("acme: rotation registration skipped: %s", e)
    logger.info("acme: domain-verified credential ready for %s", domain)
    return cert
