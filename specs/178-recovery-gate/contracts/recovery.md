# Recovery contracts

1. Routing changes are explicit and revision-aware; existing pinned TLS/application
   identity remains the verifier. Wrong identity, untrusted TLS, redirects and
   stale revisions refuse without erasing prior binding or evidence.
2. Durable revocation precedes asynchronous close. Check current enrollment
   generation/key/state and certificate validity before admission and after
   await before result delivery/acceptance. Earlier effects are not undone.
3. Task/protected operation submissions deduplicate original request identities
   across races/restart. Unknown synchronous calls are never automatically replayed.
   Cancellation distinguishes no-dispatch from uncertain or completed effects.
4. Client send markers persist before I/O and only advance. Exact-ID/nonce/parent
   recovery cannot authorize a new prepare/decision or clear uncertain markers.
   Bounded reference transfer excludes cookies/secrets/reviews/results and validates
   installation/principal; malformed/conflicting/unbounded input refuses.
5. Endpoint replacement retains profile/enrollment identity. VS Code destination
   discovery must prove same installation and execution mode before local commit;
   owner sessions remain origin-bound. Mobile port change uses retained device-key
   challenge, same TLS name/path/installation/principal/HTTPS origin and stable
   operation namespace. New trust identity is separate enrollment, not migration.
6. Detection and restoration-to-recovery timings are separate. Measure native,
   provider, result and ACK counts; a client timeout does not prove zero effects.
7. Real local sockets, native client with controlled provider, actual guarded MCP
   workload and inherited cloud evidence are distinct. Never relabel a fixture.
8. Preserve prior deadlines/state/receipts. No claim replay or database rollback.
   Export private evidence before owned disposable cleanup.
