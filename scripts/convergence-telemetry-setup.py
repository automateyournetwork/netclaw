#!/usr/bin/env python3
"""Convergence telemetry setup wizard (Phase 10 PR2 — T129).

Modes:
  manual   — prompt or --csv name=ip[,…]
  nautobot — list devices from Nautobot, select set
  netbox   — list devices from NetBox (same schema)
  yaml     — import targets file or convergence.yaml fragment

Writes device_telemetry.snmp.targets into convergence.yaml (or --out).
Optional --apply chains scripts/convergence-telemetry-apply.sh.

Usage:
  python3 scripts/convergence-telemetry-setup.py --mode nautobot --select all --dry-run
  python3 scripts/convergence-telemetry-setup.py --mode manual --csv 'SW1=10.0.0.1:cisco'
  python3 scripts/convergence-telemetry-setup.py --mode yaml --import deploy/convergence/adapters/device-snmp/targets.example.yml
  python3 scripts/convergence-telemetry-setup.py   # interactive
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from lib.convergence_telemetry_inventory import (  # noqa: E402
    format_targets_table,
    list_nautobot_devices,
    list_netbox_devices,
    load_convergence,
    load_dotenv_files,
    merge_targets_into_config,
    parse_csv_targets,
    select_by_spec,
    sort_targets,
    targets_from_yaml_file,
    write_convergence,
    write_targets_yaml,
)


def resolve_config_path(explicit: str | None, *, for_write: bool = False) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("CONVERGENCE_CONFIG")
    if env:
        return Path(env).expanduser().resolve()
    site = Path.home() / ".openclaw" / "convergence.yaml"
    repo = REPO_ROOT / "config" / "convergence.yaml"
    example = REPO_ROOT / "config" / "convergence.example.yaml"
    # Prefer live site config; never default *writes* to the example template
    if site.is_file():
        return site
    if repo.is_file():
        return repo
    if for_write:
        return site
    if example.is_file():
        return example
    return site


def prompt(msg: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"{msg}{suffix}: ").strip()
    except EOFError:
        return default
    return val or default


def prompt_yes(msg: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    try:
        val = input(f"{msg} [{d}]: ").strip().lower()
    except EOFError:
        return default
    if not val:
        return default
    return val in ("y", "yes", "1", "true")


def interactive_manual() -> list[dict]:
    print("Enter devices (empty name to finish). Optional vendor: cisco|pfsense|generic")
    targets: list[dict] = []
    while True:
        name = prompt("  device name (blank=done)")
        if not name:
            break
        ip = prompt("  IP")
        if not ip:
            print("  skip (no IP)")
            continue
        vendor = prompt("  vendor/template", "cisco")
        role = prompt("  role", "switch")
        from lib.convergence_telemetry_inventory import normalize_target

        t = normalize_target(
            {"name": name, "ip": ip, "role": role, "vendor": vendor, "template": vendor}
        )
        if t:
            targets.append(t)
            print(f"  + {t['name']} {t['ip']} ({t['template']})")
    return sort_targets(targets)


def interactive_select(candidates: list[dict]) -> list[dict]:
    print(format_targets_table(candidates))
    print()
    print("Select: all | comma indices (1,2,3) | name substrings")
    spec = prompt("Selection", "all")
    return select_by_spec(candidates, spec)


def run_apply(config_path: Path, dry_run: bool = False) -> int:
    apply = REPO_ROOT / "scripts" / "convergence-telemetry-apply.sh"
    if not apply.is_file():
        print(f"apply script missing: {apply}", file=sys.stderr)
        return 1
    cmd = [str(apply), "--config", str(config_path)]
    if dry_run:
        cmd.append("--dry-run")
    print(f"Running: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Convergence telemetry inventory setup (Phase 10)"
    )
    ap.add_argument(
        "--mode",
        choices=("manual", "nautobot", "netbox", "yaml", "interactive"),
        default="interactive",
        help="inventory source (default: interactive menu)",
    )
    ap.add_argument("--config", help="convergence.yaml to read/write")
    ap.add_argument(
        "--out",
        help="write config here (default: same as --config or ~/.openclaw/convergence.yaml)",
    )
    ap.add_argument(
        "--out-targets",
        help="also write standalone targets YAML",
    )
    ap.add_argument("--csv", help="manual mode: name=ip[:vendor][,…]")
    ap.add_argument(
        "--import",
        dest="import_path",
        help="yaml mode: path to targets or convergence yaml",
    )
    ap.add_argument(
        "--select",
        default="",
        help="SoT select: all | 1,2,3 | name substrings",
    )
    ap.add_argument(
        "--include-wireless",
        action="store_true",
        help="include wireless AP roles from SoT (default: exclude)",
    )
    ap.add_argument(
        "--include-servers",
        action="store_true",
        help="include server/k3s/hypervisor roles from SoT (default: exclude)",
    )
    ap.add_argument(
        "--role-filter",
        default=None,
        help="substring filter on SoT role/name",
    )
    ap.add_argument(
        "--merge",
        action="store_true",
        help="merge with existing targets instead of replace",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print targets / would-write path; do not write config",
    )
    ap.add_argument(
        "--write",
        action="store_true",
        help="write config (default true for non-dry-run non-interactive)",
    )
    ap.add_argument(
        "--no-write",
        action="store_true",
        help="never write config (list/select only)",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="after write, run convergence-telemetry-apply.sh",
    )
    ap.add_argument(
        "--enabled",
        action="store_true",
        default=True,
        help="set device_telemetry.snmp.enabled true (default)",
    )
    ap.add_argument(
        "--site",
        default=None,
        help="override site label in standalone targets out",
    )
    args = ap.parse_args()

    load_dotenv_files(
        [
            REPO_ROOT / ".env",
            REPO_ROOT / "deploy" / "convergence" / ".env",
            Path.home() / ".openclaw" / ".env",
        ]
    )

    # Read seed may be example; writes go to --out or ~/.openclaw/convergence.yaml
    config_path = resolve_config_path(args.config, for_write=False)
    if args.out:
        out_path = Path(args.out).expanduser().resolve()
    else:
        out_path = resolve_config_path(args.config, for_write=True)
        # If we only found the example template for read, still write to site path
        if out_path.name == "convergence.example.yaml":
            out_path = Path.home() / ".openclaw" / "convergence.yaml"

    mode = args.mode
    if mode == "interactive":
        print("Convergence telemetry setup — inventory source")
        print("  1) manual")
        print("  2) nautobot")
        print("  3) netbox")
        print("  4) yaml import")
        choice = prompt("Mode", "2" if os.environ.get("NAUTOBOT_URL") else "1")
        mode = {
            "1": "manual",
            "2": "nautobot",
            "3": "netbox",
            "4": "yaml",
            "manual": "manual",
            "nautobot": "nautobot",
            "netbox": "netbox",
            "yaml": "yaml",
        }.get(choice, "manual")

    targets: list[dict] = []
    try:
        if mode == "manual":
            if args.csv:
                targets = parse_csv_targets(args.csv)
            elif sys.stdin.isatty() and not args.no_write:
                targets = interactive_manual()
            else:
                print("manual mode needs --csv or interactive TTY", file=sys.stderr)
                return 2

        elif mode == "nautobot":
            candidates = list_nautobot_devices(
                include_wireless=args.include_wireless,
                include_servers=args.include_servers,
                role_filter=args.role_filter,
            )
            if not candidates:
                print("No SNMP-candidate devices from Nautobot", file=sys.stderr)
                return 1
            if args.select:
                targets = select_by_spec(candidates, args.select)
            elif sys.stdin.isatty() and not args.dry_run:
                print(f"Nautobot candidates ({len(candidates)}):")
                targets = interactive_select(candidates)
            else:
                # non-interactive default: all candidates
                targets = candidates if not args.select else select_by_spec(
                    candidates, args.select or "all"
                )
                if not args.select and args.dry_run:
                    targets = candidates

        elif mode == "netbox":
            candidates = list_netbox_devices(
                include_wireless=args.include_wireless,
                include_servers=args.include_servers,
                role_filter=args.role_filter,
            )
            if not candidates:
                print("No SNMP-candidate devices from NetBox", file=sys.stderr)
                return 1
            if args.select:
                targets = select_by_spec(candidates, args.select)
            elif sys.stdin.isatty() and not args.dry_run:
                print(f"NetBox candidates ({len(candidates)}):")
                targets = interactive_select(candidates)
            else:
                targets = candidates

        elif mode == "yaml":
            if not args.import_path:
                if sys.stdin.isatty():
                    args.import_path = prompt(
                        "Path to targets YAML",
                        str(
                            REPO_ROOT
                            / "deploy/convergence/adapters/device-snmp/targets.example.yml"
                        ),
                    )
                else:
                    print("yaml mode needs --import PATH", file=sys.stderr)
                    return 2
            path = Path(args.import_path).expanduser()
            if not path.is_file():
                print(f"import not found: {path}", file=sys.stderr)
                return 1
            targets = targets_from_yaml_file(path)
        else:
            print(f"unknown mode {mode}", file=sys.stderr)
            return 2
    except Exception as e:
        print(f"SoT/inventory error: {e}", file=sys.stderr)
        return 1

    targets = sort_targets(targets)
    print()
    print(f"Selected {len(targets)} target(s):")
    print(format_targets_table(targets))
    print()

    do_write = (not args.dry_run) and (not args.no_write)
    if args.write:
        do_write = True
    if args.dry_run:
        do_write = False
    if args.no_write:
        do_write = False

    if args.dry_run:
        print(f"[dry-run] would write {len(targets)} target(s) → {out_path}")
        if args.out_targets:
            print(f"[dry-run] would write targets YAML → {args.out_targets}")
        # Emit YAML targets to stdout for smoke/tests
        try:
            import yaml

            print("---")
            print(
                yaml.dump(
                    {"targets": targets},
                    default_flow_style=False,
                    sort_keys=False,
                ),
                end="",
            )
        except Exception:
            pass
        if args.apply:
            print("[dry-run] skip --apply")
        return 0

    if not do_write:
        print("No write (--no-write). Done.")
        return 0 if targets else 1

    # interactive confirm
    if sys.stdin.isatty() and not args.write and mode != "yaml":
        if not prompt_yes(f"Write inventory to {out_path}?", True):
            print("Aborted.")
            return 0

    cfg = load_convergence(config_path if config_path.is_file() else out_path)
    # If reading example but writing elsewhere, start from example content already loaded
    if config_path != out_path and config_path.is_file() and not out_path.is_file():
        cfg = load_convergence(config_path)
    cfg = merge_targets_into_config(
        cfg,
        targets,
        enabled=True,
        replace=not args.merge,
    )
    if args.site:
        cfg["site"] = args.site

    write_convergence(out_path, cfg)
    print(f"Wrote {out_path} ({len(targets)} targets, snmp.enabled=true)")

    if args.out_targets:
        site = args.site or str(cfg.get("site") or "home")
        write_targets_yaml(Path(args.out_targets), targets, site=site)
        print(f"Wrote {args.out_targets}")

    # convenience site targets for apply --targets
    site_targets = (
        REPO_ROOT / "deploy/convergence/adapters/device-snmp/targets.site.yml"
    )
    try:
        write_targets_yaml(
            site_targets, targets, site=str(cfg.get("site") or "home")
        )
        print(f"Wrote {site_targets}")
    except OSError as e:
        print(f"(warn) could not write targets.site.yml: {e}", file=sys.stderr)

    if args.apply:
        # Prefer writing config path that apply can find
        rc = run_apply(out_path, dry_run=False)
        return rc

    print()
    print("Next:")
    print(f"  ./scripts/convergence-telemetry-apply.sh --config {out_path}")
    print("  ./deploy/convergence/smoke-device-snmp.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
