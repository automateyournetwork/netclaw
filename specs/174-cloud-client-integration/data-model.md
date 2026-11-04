# Client state

Profile: mode(local/edge or cloud-owner), stable profile ID, label, canonical HTTPS origin and expected installation UUID. Changing identity creates a distinct namespace.
Session: exact owner cookie bound to profile/installation, secure-store key, transient CSRF, expiry. Bootstrap ticket is transient; revocation/expiry stops private output/actions.
Reference: origin, installation, client nonce persisted before prepare; optional operation ID after response. Bounded retained list with no request arguments/results/credentials. Uncertain prepare retains nonce. Recovery queries by nonce/ID; unknown never triggers prepare replay.
Review: operation ID, revision, review digest and full server review. Decision uses the exact displayed revision/digest once. Uncertain decision retains reference and requires status/reconcile, never automatic approve.
Results: render server status, source/member attribution, verified result and durable ACK/audit reference. No stronger verification claim than server evidence.
