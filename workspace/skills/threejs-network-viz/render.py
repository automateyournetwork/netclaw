#!/usr/bin/env python3
"""
Command-line entry point for the threejs-network-viz skill.

One command turns a topology into a self-contained HTML scene and prints the
absolute path of the written file on stdout (nothing else). Errors go to
stderr with a non-zero exit code, so a calling agent can tell success from
failure without parsing prose.

Usage:
    python3 render.py --describe "r1 is a router, r2 is a router, r1 connects to r2"
    python3 render.py --json topology.json --source cml
    cat topology.json | python3 render.py --json - --source gns3

JSON input shape (the same raw shape every live-source adapter accepts):
    {"source": "label",
     "devices": [{"hostname": "r1", "device_type": "router",
                  "interfaces": [{"name": "Gi0/0"}], "status": "healthy"}],
     "links": [{"source_device": "r1", "source_interface": "Gi0/0",
                "target_device": "r2", "target_interface": "Gi0/0"}]}

Exit codes: 0 written, 1 bad input or render failure, 2 usage error.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import output  # noqa: E402
import sources  # noqa: E402
from html_template import render_html  # noqa: E402
from scene_builder import build_scene_payload  # noqa: E402

JSON_SOURCES = {
    "cml": sources.from_cml,
    "gns3": sources.from_gns3,
    "containerlab": sources.from_containerlab,
    "eve_ng": sources.from_eve_ng,
    "nautobot": sources.from_nautobot,
    "netbox_infrahub": sources.from_netbox_infrahub,
    "ip_fabric": sources.from_ip_fabric,
    "forward_networks": sources.from_forward_networks,
}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="render.py",
        description="Render a network topology as a self-contained Three.js HTML file "
        "and print the file path.",
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--describe", metavar="TEXT",
                     help='plain-language topology, e.g. "r1 is a router, r1 connects to sw1"')
    src.add_argument("--json", metavar="FILE",
                     help="topology JSON file, or - to read it from stdin")
    p.add_argument("--source", choices=sorted(JSON_SOURCES), default="cml",
                   help="which source the JSON came from; sets the scene's source label "
                   "(default: cml)")
    p.add_argument("--output-dir", metavar="DIR",
                   help="write here instead of workspace/output/threejs-network-viz/")
    p.add_argument("--open", action="store_true",
                   help="also open the file in the default browser")
    return p


def _load_json(spec: str) -> dict:
    text = sys.stdin.read() if spec == "-" else Path(spec).read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get("devices"), list):
        raise ValueError('topology JSON must be an object with a "devices" list')
    return data


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.describe is not None:
            if not args.describe.strip():
                raise ValueError("--describe text is empty")
            snapshot = sources.from_freeform(args.describe)
        else:
            snapshot = JSON_SOURCES[args.source](_load_json(args.json))
        if not snapshot.devices:
            raise ValueError("the topology has no devices")
        html = render_html(build_scene_payload(snapshot))
        if args.output_dir:
            output.OUTPUT_DIR = Path(args.output_dir).expanduser().resolve()
        path = output.write_scene(html, snapshot.snapshot_id).resolve()
    except Exception as exc:  # report every failure the same way to the caller
        print(f"threejs-network-viz: error: {exc}", file=sys.stderr)
        return 1
    if args.open:
        output.open_in_browser(path)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
