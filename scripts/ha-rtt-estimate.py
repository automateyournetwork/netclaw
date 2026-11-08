#!/usr/bin/env python3
"""Offline inter-region RTT ESTIMATE table and admission budget (spec 182, T003).

All values are estimates from typical public GCP numbers (source=estimate).
Authoritative numbers come from the measured probe after deploy (T033).
"""
import argparse
import itertools
import json
import sys

REGIONS = {"nne1": "northamerica-northeast1", "ew1": "europe-west1", "ase1": "asia-southeast1"}
# (a, b) -> estimated RTT ms (low, high); symmetric.
RTT_MS = {
    ("nne1", "ew1"): (85, 95),
    ("ew1", "ase1"): (160, 180),
    ("nne1", "ase1"): (220, 250),
}
SEQUENTIAL_ROUND_TRIPS = 10  # R08 model: an admission needs roughly ten quorum round trips (to be measured)


def rtt(a, b, which="high"):
    if a == b:
        return 0
    lo, hi = RTT_MS.get((a, b)) or RTT_MS[(b, a)]
    return hi if which == "high" else lo


def leader_budget(leader, n=SEQUENTIAL_ROUND_TRIPS, which="high"):
    """Quorum of 3: leader waits for the nearest follower."""
    nearest = min(rtt(leader, c, which) for c in REGIONS if c != leader)
    return {"leader": leader, "nearest_follower_rtt_ms": nearest,
            "admission_estimate_ms": nearest * n, "source": "estimate"}


def recommend_admission_ms(n=SEQUENTIAL_ROUND_TRIPS, margin=2.0, lo=100, hi=10000):
    worst_preferred = max(leader_budget(c, n)["admission_estimate_ms"] for c in ("nne1", "ew1"))
    return max(lo, min(hi, int(worst_preferred * margin)))


def table(n=SEQUENTIAL_ROUND_TRIPS):
    pairs = [{"a": a, "b": b, "rtt_ms_low": RTT_MS[(a, b)][0], "rtt_ms_high": RTT_MS[(a, b)][1], "source": "estimate"}
             for a, b in itertools.combinations(("nne1", "ew1", "ase1"), 2)]
    leaders = [leader_budget(c, n) for c in REGIONS]
    return {"pairs": pairs, "leaders": leaders, "round_trips": n,
            "recommended_admission_ms_if_estimates_hold": recommend_admission_ms(n),
            "note": "ESTIMATE ONLY. Replace with measured p50/p95 (T033) before setting admission_ms."}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--round-trips", type=int, default=SEQUENTIAL_ROUND_TRIPS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    data = table(args.round_trips)
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    print("source=estimate (not measured)")
    for p in data["pairs"]:
        print(f"  {p['a']:5s}<->{p['b']:5s} RTT {p['rtt_ms_low']}-{p['rtt_ms_high']} ms")
    for l in data["leaders"]:
        print(f"  leader {l['leader']:5s}: nearest follower {l['nearest_follower_rtt_ms']} ms -> ~{l['admission_estimate_ms']} ms per admission (N={data['round_trips']})")
    print(f"  admission_ms if estimates hold (NA/EU leader, 2x margin): {data['recommended_admission_ms_if_estimates_hold']} (manifest bound 100-10000)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
