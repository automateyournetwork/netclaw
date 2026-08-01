"""Credential resolution: Vault preferred, environment as documented fallback.

Spec 076 FR-018, FR-018a, FR-019, FR-020. Constitution Principle XIII.

Two rules define this module:

1. **Vault is preferred but NOT required.** An operator running an
   operator-authored inventory with no source of truth almost certainly has no
   Vault either. Requiring it would make this server stricter than every other
   NetClaw server (pyATS already supports env-var credentials alongside
   VAULT_ADDR) while excluding exactly the operators the inventory design just
   made first-class.

2. **A credential is NEVER read from an inventory file** — any of the three
   sources. Inventory carries a credential *reference*; this module turns that
   reference into a secret at runtime and never writes it anywhere.

Per-device, per-site and per-platform credentials are supported via that
reference (FR-020). A single global credential is not a realistic assumption for
a mixed network, which is the whole premise of this server.

The secret value never appears in a tool result, a log line, or an audit record.
Only the reference and which path resolved it (FR-018a) — enough to audit a
deployment's posture, never enough to leak it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum


class CredentialPath(str, Enum):
    VAULT = "vault"
    ENVIRONMENT = "environment"


class CredentialError(RuntimeError):
    """Resolution failed. Message names the reference and the paths tried —
    never any secret material."""


@dataclass
class Credential:
    """A resolved credential.

    `username`/`password`/`enable`/`key_file` are secret. `__repr__` is
    overridden so a stray log statement or traceback cannot leak them — a real
    failure mode, not a theoretical one.
    """
    username: str
    password: str | None = field(default=None, repr=False)
    enable: str | None = field(default=None, repr=False)
    key_file: str | None = None
    path: CredentialPath = CredentialPath.ENVIRONMENT
    ref: str = "default"

    def __repr__(self) -> str:  # pragma: no cover - defensive
        return (f"Credential(ref={self.ref!r}, path={self.path.value!r}, "
                f"username={self.username!r}, secrets=<redacted>)")

    __str__ = __repr__

    def posture(self) -> dict:
        """Inspectable, non-secret description for tool results (FR-018a)."""
        return {
            "credential_ref": self.ref,
            "credential_path": self.path.value,
            "username": self.username,
            "has_password": self.password is not None,
            "has_enable": self.enable is not None,
            "key_file": self.key_file,
        }


def _env(*names: str) -> str | None:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return None


def _from_environment(ref: str) -> Credential | None:
    """Resolve from environment variables.

    Reference-scoped variables are checked first so per-device, per-site and
    per-platform credentials work (FR-020): a ref of `edge-site` looks for
    MULTIVENDOR_EDGE_SITE_USERNAME before the generic
    MULTIVENDOR_USERNAME. That is what makes one inventory able to span
    devices with different credentials.
    """
    scoped = ref.replace("-", "_").replace(".", "_").upper()
    username = _env(f"MULTIVENDOR_{scoped}_USERNAME", "MULTIVENDOR_USERNAME")
    if not username:
        return None
    return Credential(
        username=username,
        password=_env(f"MULTIVENDOR_{scoped}_PASSWORD", "MULTIVENDOR_PASSWORD"),
        enable=_env(f"MULTIVENDOR_{scoped}_ENABLE", "MULTIVENDOR_ENABLE"),
        key_file=_env(f"MULTIVENDOR_{scoped}_KEY_FILE", "MULTIVENDOR_KEY_FILE"),
        path=CredentialPath.ENVIRONMENT,
        ref=ref,
    )


def _from_vault(ref: str) -> Credential | None:
    """Resolve from Vault, if configured and reachable.

    Returns None rather than raising when Vault is simply not configured —
    absence of Vault is an expected deployment, not an error (FR-018).

    Deliberately not implemented against a Vault client here: NetClaw already
    has a vault-mcp integration and the established pattern is to route secret
    access through it rather than embedding a second client. Wiring that up is
    a Phase 3 follow-up task; until then this returns None and resolution falls
    through to the environment, which is a documented supported path — not a
    silent downgrade, because `path` in the result says which was used.
    """
    if not os.environ.get("VAULT_ADDR"):
        return None
    return None


def resolve(ref: str | None = None) -> Credential:
    """Resolve a credential reference. Vault first, then environment.

    Raises CredentialError naming the reference and the paths tried when neither
    yields a credential. The message contains no secret material.
    """
    ref = ref or "default"

    cred = _from_vault(ref)
    if cred is not None:
        return cred

    cred = _from_environment(ref)
    if cred is not None:
        return cred

    vault_configured = bool(os.environ.get("VAULT_ADDR"))
    tried = "vault, environment" if vault_configured else "environment (VAULT_ADDR unset)"
    raise CredentialError(
        f"could not resolve credential reference {ref!r}; tried: {tried}. "
        f"Set MULTIVENDOR_USERNAME/MULTIVENDOR_PASSWORD (or the "
        f"MULTIVENDOR_{ref.replace('-', '_').upper()}_* variants for this "
        f"reference) in a gitignored .env, or configure Vault. "
        f"Credentials must never be placed in an inventory file."
    )


def looks_like_secret_field(name: str) -> bool:
    """Whether an inventory field name looks like credential material.

    Used to reject inventory records carrying secrets (FR-017d). Errs toward
    false positives: refusing a legitimately-named field costs one rename, while
    accepting a real secret on disk violates Principle XIII.
    """
    lowered = name.lower()
    return any(marker in lowered for marker in (
        "password", "passwd", "secret", "token", "apikey", "api_key",
        "private_key", "privatekey", "enable_password", "enable_secret",
        "credential", "passphrase",
    )) and lowered not in ("credential_ref", "credentialref")
