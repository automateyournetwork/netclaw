# Third-Party Notice — `kubernetes-mcp-server`

NetClaw **adopts a third-party binary it does not own and does not modify**.

| | |
|---|---|
| **Upstream** | https://github.com/containers/kubernetes-mcp-server |
| **Pinned release** | **v0.0.66** — published 2026-07-31 |
| **Licence** | **Apache-2.0** — identical to NetClaw's own |
| **Artifact** | `kubernetes-mcp-server-linux-amd64`, a **statically linked** ELF binary (74,928,290 bytes) |
| **Relationship** | A separate program invoked over stdio |
| **Adopted by** | spec 084 / roadmap R14 |

## Provenance and the checksum limitation

```
SHA-256  692a7b283a96140311fd46f13b8373657b2e9bfe660a36bb6434e8c42d899dbc
```

**Upstream publishes no checksums.** Verified: the v0.0.66 release carries 15 assets and **zero** `sha` or
`checksum` files. So the hash above is **NetClaw's own record of the artifact it adopted** — trust on first
use, not upstream attestation.

That is a real limitation and is stated rather than implied. What it does buy: the installer refuses to
proceed if the downloaded bytes ever differ, which detects a re-tagged or altered asset. What it does not
buy: any assurance that the artifact was what upstream intended *at the moment we first fetched it*.

## Why a binary rather than vendored source

- **No Go toolchain is assumed** on a NetClaw host, so building from source would add a dependency.
- **`@latest` was rejected.** An unpinned fetch is exactly how a 7-tool surface silently becomes 21 and
  busts the 5,000-token manifest ceiling. The pin is load-bearing, not hygiene.
- The binary is **not committed** — it is 75 MB and is downloaded at install time. `.gitignore` re-ignores it
  beneath the directory negation.

## Why this candidate

**A statically linked Go binary has zero runtime dependencies** (`ldd` → *not a dynamic executable*). It
therefore **cannot** collide with the `fastmcp<3` pins carried by five NetClaw servers — the conflict that
blocked spec 083's first candidate. Dependency safety here is structural, not careful.

## Do not modify

Nothing in this directory beyond NetClaw's own `config.toml`, `README.md` and this notice is authored here.
If upstream behaviour needs changing, it goes upstream.

**One upstream behaviour NetClaw deliberately works around rather than patches** — see `README.md`: given a
credential without cluster-wide list permission, the server silently rewrites a cluster-wide query to a
single namespace and returns the result with no error and no caveat
(`pkg/kubernetes/resources.go:34-38`). NetClaw's answer is a mandated cluster-wide-read ServiceAccount plus a
skill-level preflight, not a fork.
