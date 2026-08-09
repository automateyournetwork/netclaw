"""Transports, split by protocol rather than by plane.

Research R2 found FortiManager and FortiAnalyzer speak the *same* JSON-RPC
dialect on the same `/jsonrpc` endpoint with the same `exec /sys/login/user`
login. They differ in the methods called, not the protocol — so two of the three
planes share one client. Treating them as separate integrations, as the roadmap's
line items implied, would have duplicated the whole transport.

FortiOS is the odd one out: plain REST with a bearer token.
"""
