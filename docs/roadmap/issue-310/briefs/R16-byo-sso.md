# R16 — Bring-your-own SSO

- **Roadmap item:** 9 — SSO
- **Depends on:** R15
- **Gate:** human review; IdP app registrations are human actions

## Specify input

An administrator configures one or more identity providers as data, with no code
changes: Microsoft Entra ID, Google, GitHub, and any standards-compliant OIDC
provider (Okta, Auth0, Keycloak, Ping, Authentik and similar). Users sign in with
their existing accounts. Access can be restricted by tenant, domain, organization
or group. Sessions expire, refresh, revoke and log out cleanly, work behind
reverse proxies, and are valid on every Border. Non-browser clients get a
supported sign-in flow. The provider layer stays open to future providers.

User stories:
- P1: An admin adds Entra ID, Google, GitHub or a generic OIDC provider from
  configuration and users sign in through it.
- P1: Users outside the allowed tenant, domain, organization or group are refused.
- P1: Logout and admin revocation take effect on all Borders within a stated bound.
- P2: CLI and VS Code users sign in without a browser redirect to localhost.

## Clarify: decisions (recommended default first)

1. Provider configuration: declarative file plus secret references, validated at
   start; secrets follow Constitution XIII.
2. Provisioning: just-in-time on first login, denied unless an allow rule matches.
3. SAML: not native; supported through an OIDC broker such as Keycloak or Dex.
4. Login hostname: one global login hostname with a single redirect URI per
   provider, versus registering every Border. [HUMAN]
5. Non-browser clients: device authorization grant (RFC 8628) for CLI and VS Code;
   native-app PKCE (RFC 8252) for Mobile; Zoom app evaluated separately. [HUMAN
   for scope]
6. Break-glass: a local owner path, disabled by default or network-restricted,
   always audited. [HUMAN]

## Plan notes (provider facts the design must handle)

- OIDC core: authorization code with PKCE (S256), state and nonce, issuer,
  audience and expiry validation, JWKS caching with rotation, bounded clock skew,
  discovery documents.
- Identity key is `(issuer, subject)`, never email. Email is display data. Linking
  accounts across providers is an explicit admin action.
- Entra ID: v2 endpoints; single-tenant issuer or a tenant-ID allowlist for
  multi-tenant apps; groups claim or app roles configured on the registration;
  handle group overage (the token signals it instead of listing groups) with a
  Microsoft Graph lookup; prefer certificate or `private_key_jwt` client auth.
- Google: OIDC; enforce Workspace domain by validating the `hd` claim server-side,
  not just the request parameter; groups are not in the ID token, so group mapping
  needs the Cloud Identity Groups or Admin SDK API.
- GitHub: OAuth 2.0, not OIDC, for user sign-in; there is no ID token. Key on the
  numeric user ID (the login name can change); read org and team membership
  through the API with `read:org`; support a configurable GitHub Enterprise Server
  base URL.
- Generic OIDC: discovery-driven, with a configurable claim path for groups or roles.
- Sessions: server-side store, `HttpOnly` `Secure` `SameSite` cookies, rotation on
  login, idle and absolute timeouts, front- or back-channel logout where offered,
  admin revocation, and group re-evaluation on refresh with a bounded staleness.
- Reverse proxies: trusted-proxy list for forwarded headers; origin and CSRF checks.
- Cross-Border validity: replicated session and revocation state from R15's store.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Providers | Successful sign-in through Entra ID, Google, GitHub and one generic OIDC provider in test tenants |
| Restrictions | Wrong tenant, domain, organization and group refused |
| Protocol attacks | Tampered state, nonce or PKCE verifier; replayed code or token; wrong audience; expired token: refused |
| Key rotation | JWKS rotation handled without outage |
| Entra overage | Group overage path exercised against Graph |
| GitHub identity | Renaming the GitHub login does not create a new principal |
| Sessions | Logout and revocation effective on all nine Borders within the stated bound |
| Proxy | Works behind a reverse proxy; spoofed forwarded headers ignored |
| Failure | IdP outage fails closed except the audited break-glass path |
