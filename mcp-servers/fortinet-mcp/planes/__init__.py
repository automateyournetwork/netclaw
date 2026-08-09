"""One module per Fortinet plane.

manager  — FortiManager, JSON-RPC. Intent: what policy *should* be.
device   — FortiGate, REST.     Observed state: what a box is *actually* doing.
analyzer — FortiAnalyzer, JSON-RPC. Observed traffic: what *hit* the policy.

The split is by plane because that is the distinction the feature exists to
protect; the transports underneath split differently (manager and analyzer share
one — research R2).
"""
