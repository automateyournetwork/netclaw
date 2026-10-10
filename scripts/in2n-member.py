#!/usr/bin/env python3
"""iN2N member launcher — the lightweight member runtime (feature 056).

A member claw is NOT a full OpenClaw + gateway. This launcher runs ONLY the iN2N
client: it dials its Border, enrolls (first run, with a token) or re-authenticates
against its pinned self-signed key, and on each delegated task executes the skill
via `openclaw agent --local --model <member-model>` over the member's OWN scoped
MCP config + provider/model. No BGP speaker, no gateway, no comms, no 195-skill
catalog. Works for a FRESH member install and for a migrated member alike.

Config (from the member's scoped .env / env):
  N2N_ROLE=member
  N2N_RISK_NAME=<risk>
  N2N_MEMBER_ID=<risk>/<name>
  N2N_BORDER_ENDPOINT=host:port          # loopback when co-located, or a reachable
                                         # Border endpoint (VPN/overlay/ngrok) when remote
  N2N_ENROLLMENT_TOKEN=<token>           # first run only (single-use); dropped after enroll
  N2N_MEMBER_MODEL=<provider/model>      # this member's LLM (any provider incl local/Ollama)
  N2N_MEMBER_SCOPE=<json list of capability names>   # what this member will run
  N2N_MEMBER_BASE=<dir>                  # member's own ~/.openclaw-members/<name>/n2n

Cold / on-demand:
  --idle-exit <seconds>   exit cleanly after this long with no delegated task, so
                          the Border can spin the member down and cold-start it
                          again on the next route. Omit for an always-on member.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "mcp-servers", "protocol-mcp"))


logging.basicConfig(level=os.environ.get("N2N_LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("in2n-member")


async def _dial_loop(svc, host, port, token):
    """Dial the Border with bounded backoff; re-dial on drop. First dial enrolls
    with the token; once pinned, reconnects use the pinned-key hello path."""
    backoff, used_token = 5, token
    while True:
        ch = svc.border_channel
        if ch is None or getattr(ch, "_closed", True):
            try:
                await svc.dial_border(host, port, enrollment_token=used_token)
                used_token = ""          # token is single-use / spent after enroll
                backoff = 5
            except Exception as e:
                if used_token:
                    log.info("enroll failed (%s); retrying via pinned-key hello", e)
                    used_token = ""
                else:
                    log.info("dial to Border %s:%d failed (%s) — retry in %ds",
                             host, port, e, backoff)
                    backoff = min(backoff * 2, 60)
        await asyncio.sleep(10 if svc.border_channel is not None else backoff)


async def _idle_watch(svc, idle_exit):
    """Cold/on-demand: exit when idle past the threshold and no task is running."""
    while True:
        await asyncio.sleep(5)
        in_flight = any(not t.done() for t in svc.tasks._workers.values())
        idle = time.time() - svc.member_last_activity
        if not in_flight and idle >= idle_exit:
            log.info("idle %ds ≥ %ds and no in-flight task — exiting for cold/on-demand",
                     int(idle), idle_exit)
            # close the channel so the Border deregisters us promptly
            if svc.border_channel is not None:
                try:
                    await svc.border_channel.close()
                except Exception:
                    pass
            return


def _load_env_file():
    """A member receives only its explicit private environment, never Border secrets."""
    from pathlib import Path
    import importlib.util
    file=os.environ.get('N2N_MEMBER_ENV_FILE')
    if not file:raise ValueError('N2N_MEMBER_ENV_FILE is required; refusing inherited Border environment')
    source=Path(file).expanduser()
    if source.is_symlink() or not source.is_file() or source.stat().st_uid!=os.getuid() or source.stat().st_mode&0o077:
        raise ValueError('owner-private member environment required')
    spec=importlib.util.spec_from_file_location('literal_env',Path(__file__).with_name('write-env.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    values=module.values(source.read_text())
    safe={key:value for key,value in os.environ.items() if key in ('HOME','PATH','LANG','LC_ALL','TMPDIR','SYSTEMROOT')}
    safe.update(values);safe['N2N_MEMBER_ENV_FILE']=str(source.resolve());safe['PYTHON_DOTENV_DISABLED']='1'
    os.environ.clear();os.environ.update(safe)



async def _run(idle_exit):
    _load_env_file()
    from bgp.federation.service import FederationService
    from bgp.federation.manager import FederationManager
    from bgp.federation.runtime import selected,private_dir
    import fcntl
    runtime=selected(initialize=True)
    private_dir(runtime.state)
    fd=os.open(runtime.state/'member.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    lock=os.fdopen(fd,'w')
    try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:lock.close();raise RuntimeError('member already running for this installation')
    member_id = os.environ.get("N2N_MEMBER_ID", "risk/member")
    base = os.path.expanduser(os.environ.get("N2N_MEMBER_BASE", str(runtime.base)))
    mgr = FederationManager(base_dir=base)
    svc = FederationService(
        local_as=int(os.environ.get("NETCLAW_LOCAL_AS", "0") or 0),
        router_id=os.environ.get("NETCLAW_ROUTER_ID", "0.0.0.0"),
        display_name=member_id, manager=mgr)
    # Record our member role/config (idempotent) so the service knows it's a member.
    svc.risk.set_role("member",
                      risk_name=os.environ.get("N2N_RISK_NAME"),
                      border_endpoint=os.environ.get("N2N_BORDER_ENDPOINT"),
                      self_member_id=member_id)
    try:
        svc.member_scope = set(json.loads(os.environ.get("N2N_MEMBER_SCOPE", "[]")))
    except (ValueError, TypeError):
        svc.member_scope = set()

    endpoint = os.environ.get("N2N_BORDER_ENDPOINT", "")
    if ":" not in endpoint:
        log.error("N2N_BORDER_ENDPOINT (host:port) is required"); return 2
    host, _, port = endpoint.rpartition(":")
    token = os.environ.get("N2N_ENROLLMENT_TOKEN", "")

    log.info("iN2N member %s starting — Border %s, scope=%s, model=%s, idle_exit=%s",
             member_id, endpoint, sorted(svc.member_scope) or "(none; execution denied)",
             os.environ.get("N2N_MEMBER_MODEL", "(default)"),
             idle_exit if idle_exit else "never (always-on)")

    await svc.start_runtime()
    dialer = asyncio.create_task(_dial_loop(svc, host, int(port), token))
    try:
        if idle_exit:
            await _idle_watch(svc, idle_exit)
        else:
            await dialer
    finally:
        dialer.cancel()
        await asyncio.gather(dialer,return_exceptions=True)
        await svc.stop_runtime()
        mgr.close()
        lock.close()
    return 0


def main():
    ap = argparse.ArgumentParser(description="iN2N lightweight member launcher")
    ap.add_argument("--idle-exit", type=int, default=int(os.environ.get("N2N_IDLE_EXIT_S", "0")),
                    help="exit after N idle seconds (cold/on-demand); 0 = always-on")
    args = ap.parse_args()
    try:
        sys.exit(asyncio.run(_run(args.idle_exit)))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
