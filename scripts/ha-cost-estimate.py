#!/usr/bin/env python3
"""Line-item monthly cost ESTIMATE for the spec 182 plan (T007). Prices are approximate list prices (+/-15%).

The owner removed the cost cap (G1, 2026-11-08): $300 is an informational WARNING, not a failure.
Use --fail-above N to make a threshold fatal. Anthropic API usage is billed separately and not included.
"""
import argparse
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ha_gcp_multiregion", os.path.join(HERE, "ha-gcp-multiregion.py"))
gcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gcp)

WARN_USD = 300.0
VM_MONTH = {"northamerica-northeast1": 26.0, "europe-west1": 25.0, "asia-southeast1": 28.0}   # e2-medium
DISK_GB_MONTH = {"northamerica-northeast1": 0.10, "europe-west1": 0.10, "asia-southeast1": 0.12}  # pd-balanced
IPV4_MONTH = 3.65          # in use
EGRESS_PER_BORDER = 6.0    # ~40 GB cross-region/continent, rough
HOURS = 730.0


def lines(plan=None):
    plan = plan or gcp.build_plan()
    out = []
    for it in plan:
        if it["kind"] == "instance":
            out.append((f"VM {gcp.MACHINE_TYPE} {it['name']}", VM_MONTH[it["region"]]))
            out.append((f"disk {it['disk_type']} {it['disk_gb']}GB {it['name']}", it["disk_gb"] * DISK_GB_MONTH[it["region"]]))
            out.append((f"egress estimate {it['name']}", EGRESS_PER_BORDER))
        elif it["kind"] == "address":
            out.append((f"static IPv4 {it['name']}", IPV4_MONTH))
    return out


def total(items):
    return round(sum(v for _, v in items), 2)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fail-above", type=float, default=None)
    args = ap.parse_args(argv)
    items = lines()
    t = total(items)
    for name, v in items:
        print(f"  {name:55s} ${v:7.2f}/mo")
    print(f"  {'TOTAL (estimate, 24/7 for a month)':55s} ${t:7.2f}/mo  (~${t / HOURS:.2f}/hour)")
    print("  NetBox is the hosted demo (no VM). Old VM (~$25/mo) and Anthropic API usage are not included.")
    if t > WARN_USD:
        print(f"WARNING: estimate exceeds the informational ${WARN_USD:.0f} figure (no cap in force).")
    if args.fail_above is not None and t > args.fail_above:
        print(f"FAIL: estimate exceeds --fail-above {args.fail_above}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
