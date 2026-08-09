"""One module per data source.

Split by source rather than by capability because each has its own endpoint shape,
failure mode and cache TTL — and FR-021 requires per-element provenance, which is
natural when each module owns its own attribution.

    rpki       rpki-validator.ripe.net (primary), RIPEstat (fallback)
    rdap       IANA bootstrap -> responsible RIR -> rdap.org fallback
    routing    RIPEstat as-overview and routing-status
    peeringdb  PeeringDB net / netixlan / netfac
    atlas      RIPE Atlas anchors and per-AS probe counts ONLY
"""
