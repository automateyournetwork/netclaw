"""Contract tests for credential handling. Spec 080, FR-028/FR-029/FR-030, SC-012.

Principle XIII. The specific rule under test: a missing variable is reported **by
name, never by value** — including inside exception text, which is where
credentials usually leak, because the code that formats an error is written in a
hurry and never reviewed as a disclosure surface.

Runs with NO appliance.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers", "fortinet-mcp"))

import credentials  # noqa: E402
from credentials import MissingCredential, load, verify_ssl, writes_allowed  # noqa: E402
from envelope import Plane  # noqa: E402

FAILURES: list[str] = []
SECRET = "TOTALLYSECRETTOKEN9999"


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")


def clear_env() -> None:
    for host_var, token_var in credentials.PLANE_ENV.values():
        os.environ.pop(host_var, None)
        os.environ.pop(token_var, None)
    os.environ.pop(credentials.VERIFY_SSL_ENV, None)
    os.environ.pop(credentials.ALLOW_WRITES_ENV, None)


def test_missing_credential_names_the_variable() -> None:
    clear_env()
    try:
        load(Plane.MANAGER)
        check("missing credential raises", False, "no exception raised")
    except MissingCredential as exc:
        text = str(exc)
        check("names the host variable", "FORTIMANAGER_HOST" in text, text)
        check("names the token variable", "FORTIMANAGER_API_TOKEN" in text, text)
        check("names the plane", "manager" in text, text)


def test_no_secret_value_appears_in_any_error() -> None:
    """The half-configured case: a token IS set but the host is missing. The
    exception must still not echo the token."""
    clear_env()
    os.environ["FORTIMANAGER_API_TOKEN"] = SECRET
    try:
        load(Plane.MANAGER)
        check("half-configured raises", False, "no exception raised")
    except MissingCredential as exc:
        check("token value absent from error", SECRET not in str(exc), "SECRET LEAKED")
        check("still names the missing host var", "FORTIMANAGER_HOST" in str(exc))
    finally:
        clear_env()


def test_repr_does_not_leak_the_token() -> None:
    """Dataclasses print every field by default, so a traceback or a debug log
    would carry the token. repr/str are overridden; this asserts it stays that way."""
    clear_env()
    os.environ["FORTIGATE_HOST"] = "192.168.2.133"
    os.environ["FORTIGATE_API_TOKEN"] = SECRET
    creds = load(Plane.DEVICE)
    check("repr redacts the token", SECRET not in repr(creds), repr(creds))
    check("str redacts the token", SECRET not in str(creds), str(creds))
    check("f-string redacts the token", SECRET not in f"{creds}")
    check("host is still visible", "192.168.2.133" in repr(creds), repr(creds))
    check("bare host gains https scheme", creds.host.startswith("https://"), creds.host)
    clear_env()


def test_tls_verification_defaults_on() -> None:
    """FR-030. Fortinet appliances present self-signed certificates, so this is
    the tempting thing to switch off. It must be an explicit per-deployment
    choice, never a silent default."""
    clear_env()
    check("verify_ssl defaults True", verify_ssl() is True)
    for value in ("false", "FALSE", "0", "no", "off"):
        os.environ[credentials.VERIFY_SSL_ENV] = value
        check(f"verify_ssl honours {value!r}", verify_ssl() is False, value)
    os.environ[credentials.VERIFY_SSL_ENV] = "true"
    check("verify_ssl back on when true", verify_ssl() is True)
    clear_env()


def test_writes_default_off() -> None:
    """FR-019. Read-only is the default posture; enabling writes is only the
    first of three checks, not authorisation."""
    clear_env()
    check("writes_allowed defaults False", writes_allowed() is False)
    os.environ[credentials.ALLOW_WRITES_ENV] = "true"
    check("writes_allowed honours true", writes_allowed() is True)
    for value in ("yes", "maybe", "", "1 "):
        os.environ[credentials.ALLOW_WRITES_ENV] = value
        expected = value.strip().lower() in ("true", "1", "yes", "on")
        check(f"writes_allowed({value!r}) == {expected}", writes_allowed() is expected, value)
    clear_env()


def test_absent_plane_is_a_deployment_fact_not_a_failure() -> None:
    """Many estates run FortiGates with no FortiAnalyzer. An absent plane is
    legitimate; what matters is saying which planes were not consulted (FR-007)."""
    clear_env()
    check("no planes configured -> empty list", credentials.configured_planes() == [])
    os.environ["FORTIGATE_HOST"] = "fgt"
    os.environ["FORTIGATE_API_TOKEN"] = "t"
    check(
        "only the configured plane is reported",
        credentials.configured_planes() == [Plane.DEVICE],
        str(credentials.configured_planes()),
    )
    clear_env()


def main() -> int:
    print("credential contract tests (no appliance required)")
    for fn in (
        test_missing_credential_names_the_variable,
        test_no_secret_value_appears_in_any_error,
        test_repr_does_not_leak_the_token,
        test_tls_verification_defaults_on,
        test_writes_default_off,
        test_absent_plane_is_a_deployment_fact_not_a_failure,
    ):
        print(f"\n{fn.__name__}")
        fn()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all credential contract tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
