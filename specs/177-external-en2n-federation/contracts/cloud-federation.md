# Existing eN2N Cloud Contract

1. Existing NCFED wire and hello/inventory/chat/tools/tasks methods unchanged; no new transit protocol.
2. Local C<A<B connection order, three authenticated channels/six directions; strict schema2 TLS registry and separate iN2N/eN2N listeners.
3. Verified identity/key, bilateral consent, explicit capability grant, applicable exact request-bound approval, rate/budget admission; revalidate after waits.
4. Only safe subnet tool/skill and peer conversation exported; configure visibility separately. No member topology/secrets in peer inventory.
5. Direct tool selection uses selected runtime config/environment/cwd, both supported config layouts, no global/repo fallback; cleanup/reap only owned subprocess on timeout/cancel.
6. Locally configured external gateway agent lacks federation/admin/shell/filesystem/browser/unrelated tools. Operator agent remains separate. Peer text cannot choose agent identity.
7. Bilateral trust never confers transit/re-export or operator authority; ordinary outcomes are not protected-operation receipts.
8. Preserve original request/task ownership and outcomes through loss; lookup never resubmits unknown work.
9. Real native/provider evidence and external-agent negative capability checks required.
10. Only fresh ordinary homes; existing protected profiles/markers/guards untouched.

The optional local deployment setting `N2N_EXTERNAL_AGENT_ID` selects the native
OpenClaw gateway agent only for `untrusted=True` gateway turns. Its value is a
bounded native agent identifier from the selected installation's configuration;
it never comes from peer input. An explicitly configured invalid/missing agent
fails closed. Unset preserves existing non-cloud behavior; the R06 deployment
requires it and verifies the actual agent tool allowlist before qualification.
Embedded execution and existing protected/Hermes authority are unchanged.
