"""Spec 170: lego receives the DNS provider's credentials from the runtime env
files, and nothing else from them, without the daemon's environment gaining them."""

import asyncio
import json
import os
import stat
import sys

import pytest

from bgp.federation import acme, certs

DOMAIN = "netclaw.example.net"
HELP = '''Configuration for Cloudflare.
Code:   'cloudflare'

Credentials:
  - "CF_DNS_API_TOKEN":           API token with DNS:Edit permission
  - "CLOUDFLARE_DNS_API_TOKEN":   Alias to CF_DNS_API_TOKEN
  - "CLOUDFLARE_ZONE_API_TOKEN":  Alias to CF_ZONE_API_TOKEN

Additional Configuration:
  - "CLOUDFLARE_TTL":  The TTL of the TXT record
'''


@pytest.fixture
def lego(tmp_path, monkeypatch):
    """Fake lego: `dnshelp --code cloudflare` prints lego's help layout; any
    other provider fails like lego. `renew` records argv and the provider-looking
    environment, then writes a certificate."""
    cert_pem, _ = certs.create_self_signed(DOMAIN, days=90)
    record = tmp_path / "record.json"
    binp = tmp_path / "lego"
    binp.write_text(f"""#!{sys.executable}
import json, os, sys
args = sys.argv[1:]
if args[0] == "dnshelp":
    if args[args.index("--code") + 1] != "cloudflare":
        sys.exit("unknown provider")
    sys.stdout.write({HELP!r})
    sys.exit(0)
env = {{k: v for k, v in os.environ.items() if k.startswith(("CF_", "CLOUDFLARE", "OTHER_"))}}
json.dump({{"argv": args, "env": env}}, open({str(record)!r}, "w"))
d = os.path.join(args[args.index("--path") + 1], "certificates")
os.makedirs(d, exist_ok=True)
open(os.path.join(d, {DOMAIN!r} + ".crt"), "w").write({cert_pem!r})
""")
    binp.chmod(binp.stat().st_mode | stat.S_IEXEC)
    home = tmp_path / "home"
    home.mkdir()
    for key in [k for k in os.environ if k.startswith(("CF_", "CLOUDFLARE", "OTHER_"))]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("N2N_LEGO_BIN", str(binp))
    monkeypatch.setenv("N2N_ACME_DNS_PROVIDER", "cloudflare")
    monkeypatch.setenv("N2N_ACME_EMAIL", "ops@example.net")
    monkeypatch.setenv("NETCLAW_RUNTIME_ENV", str(home / ".env"))

    def renew():
        cert = asyncio.run(acme.renew(DOMAIN, tmp_path / "n2n"))
        assert cert and "BEGIN CERTIFICATE" in cert
        return json.loads(record.read_text())
    return home, renew


def test_provider_credentials_reach_lego_only(lego):
    home, renew = lego
    (home / ".env").write_text("CLOUDFLARE_DNS_API_TOKEN=from-dotenv\n"
                               "OTHER_SECRET=never-passed\n"
                               "CLOUDFLARE_TTL='120'\n")
    (home / "mesh.systemd.env").write_text("CLOUDFLARE_ZONE_API_TOKEN=from-mesh\n")
    seen = renew()
    assert seen["env"] == {"CLOUDFLARE_DNS_API_TOKEN": "from-dotenv",
                           "CLOUDFLARE_ZONE_API_TOKEN": "from-mesh",
                           "CLOUDFLARE_TTL": "120"}
    assert "CLOUDFLARE_DNS_API_TOKEN" not in os.environ
    argv = seen["argv"]
    assert argv[argv.index("renew"):] == ["renew", "--days", "30", "--reuse-key", "--no-random-sleep"]


def test_file_form_is_passed(lego):
    home, renew = lego
    (home / ".env").write_text("CF_DNS_API_TOKEN_FILE=/run/secrets/cf\n")
    assert renew()["env"] == {"CF_DNS_API_TOKEN_FILE": "/run/secrets/cf"}


def test_precedence_environment_then_mesh_file_then_dotenv(lego, monkeypatch):
    home, renew = lego
    (home / ".env").write_text("CLOUDFLARE_DNS_API_TOKEN=dotenv\nCLOUDFLARE_ZONE_API_TOKEN=dotenv\n")
    (home / "mesh.systemd.env").write_text("CLOUDFLARE_DNS_API_TOKEN=mesh\nCLOUDFLARE_ZONE_API_TOKEN=mesh\n")
    monkeypatch.setenv("CLOUDFLARE_DNS_API_TOKEN", "service")
    assert renew()["env"] == {"CLOUDFLARE_DNS_API_TOKEN": "service", "CLOUDFLARE_ZONE_API_TOKEN": "mesh"}


def test_unknown_provider_or_no_runtime_env_passes_nothing(lego, monkeypatch):
    home, renew = lego
    (home / ".env").write_text("CLOUDFLARE_DNS_API_TOKEN=from-dotenv\n")
    monkeypatch.delenv("NETCLAW_RUNTIME_ENV")
    assert renew()["env"] == {}
    monkeypatch.setenv("NETCLAW_RUNTIME_ENV", str(home / ".env"))
    monkeypatch.setenv("N2N_ACME_DNS_PROVIDER", "nosuchprovider")
    assert renew()["env"] == {}


def test_unreadable_env_file_is_skipped_without_its_content(lego, caplog):
    home, renew = lego
    (home / ".env").write_text("CLOUDFLARE_DNS_API_TOKEN='unterminated secret\n")
    (home / "mesh.systemd.env").write_text("CLOUDFLARE_ZONE_API_TOKEN=from-mesh\n")
    assert renew()["env"] == {"CLOUDFLARE_ZONE_API_TOKEN": "from-mesh"}
    assert "secret" not in caplog.text
