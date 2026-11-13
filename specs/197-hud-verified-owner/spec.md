# Verified HUD sessions for local owners and HTTPS reviewers

**Status** Proposed for maintainer review. The browser view proposal in [#356](https://github.com/automateyournetwork/netclaw/pull/356) can proceed independently.

A trusted locally installed HUD view sometimes needs to ask a companion service for private data or submit a user-authorized action. Today built-in routes can recheck the installation-bound HUD owner around asynchronous work. A downstream adapter needs the same host check without handling NetClaw cookies or opening access to existing routes. The companion service owns its own user sign-in, permissions, data, audit and side effects.

## Required behavior

1. A stock HUD has no adapter routes. An administrator explicitly selects a trusted local server adapter and its fixed operations. Selection confers server-process trust. A browser, remote URL or request header cannot register code or enable a route.
2. In local owner mode, the host verifies an eligible local deployment, the request origin policy, exactly one installation selection, and the matching live HUD owner. Two owner sessions on the same installation receive different opaque handles. Handles are also distinct across adapters, installations, runtimes and server restarts. The host never sends these handles to the browser.
3. A handler may store an external credential in its own server-side session. NetClaw provides a per-request ownership recheck and lifecycle signals. The host rechecks ownership before invoking the handler and before releasing private output. The caller receives a generic denial if the owner expires or is revoked during a read.
4. Mutating operations require a separate explicit declaration, a matching exact browser origin, JSON and an owner-bound anti-CSRF proof, including sign-in and sign-out. The companion service verifies the user and authorization at its own write boundary and supplies a way to reconcile uncertain outcomes. An operation accepted before revocation can complete.
5. The existing remote workspace, public lab and protected operations profiles do not register this adapter. Standalone preview builds make zero adapter requests and must be isolated from the enabled origin. A browser using a remotely exposed UI proxy cannot use a loopback hop to qualify for local-only access.
6. A reviewer on a separate workstation can open a dedicated HTTPS HUD reviewer origin, sign in to the selected companion service, and use its explicitly allowed view. This is a separate opt-in listener and document entry point. An authenticated reviewer receives an application-scoped session. It grants no NetClaw owner privileges. Opening the ordinary network HUD, forwarding its cookies, or presenting a peer grant cannot establish that session. Two reviewers must remain independently identifiable to the service.
7. Disabling the adapter removes its route family and invalidates local associations. Existing built-in reads, legacy-cookie migration, chat, Canvas, remote profiles and standalone services retain their behavior.

## Scope decision

Maintainer review is requested on operation-scoped dispatch, verified local owner handles, and a distinct HTTPS reviewer profile that renders only an explicitly selected view. Maintainers can accept these in independent slices. The reviewer profile needs explicit eligibility in any future view registry. Existing draft #356 covers local owners only. Each application supplies its own named commands and business authorization. The initial upstream implementation would exercise a synthetic private read and a synthetic CSRF-protected mutation.
