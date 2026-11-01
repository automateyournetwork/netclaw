"""scripts/defenseclaw-enable.sh: pinned, checksum-verified install and the
DefenseClaw 1.0.x non-interactive init/guardrail path (spec 167, findings F1/F6).

Runs the real script against a fixture HOME with fake curl/defenseclaw on PATH.
No network, no real installer."""
from pathlib import Path
import hashlib, json, os, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/defenseclaw-enable.sh'
SECRET = 'fixture-gateway-token-must-not-print'

FAKE_CURL = '''#!%s
import os, shutil, sys
args = sys.argv[1:]
dest = args[args.index('-o') + 1]
url = args[-1]
with open(os.environ['FIXTURE_CURL_LOG'], 'a') as fh:
    fh.write(' '.join(args) + '\\n')
name = url.rsplit('/', 1)[-1]
src = os.path.join(os.environ['FIXTURE_RELEASE'], name)
if not os.path.exists(src):
    sys.exit(22)
shutil.copy(src, dest)
''' % sys.executable

FAKE_DEFENSECLAW = '''#!/bin/sh
echo "$*" >> "$FIXTURE_DC_LOG"
case "$1" in
  --version) echo "defenseclaw 1.0.4";;
  init) [ -z "$FIXTURE_INIT_FAIL" ] || { echo "gateway defaults: str expected, not dict" >&2; exit 1; };;
esac
'''

INSTALLER = '''#!/bin/sh
echo "$*" > "$FIXTURE_INSTALL_ARGS"
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/defenseclaw" <<'EOF'
%s
EOF
chmod 755 "$HOME/.local/bin/defenseclaw"
''' % FAKE_DEFENSECLAW


def fixture(tmp_path, token=SECRET, checksums=None):
    home = tmp_path / 'home'
    (home / '.openclaw/config').mkdir(parents=True)
    (home / '.openclaw/config/openclaw.json').write_text(json.dumps({'keep': 1}))
    gateway = {'gateway': {'auth': {'token': token}},
               'models': {'providers': {'ollama-cloud': {'baseUrl': 'https://ollama.com', 'apiKey': SECRET}}}}
    (home / '.openclaw/openclaw.json').write_text(json.dumps(gateway))
    release = tmp_path / 'release'
    release.mkdir()
    (release / 'install.sh').write_text(INSTALLER)
    digest = hashlib.sha256(INSTALLER.encode()).hexdigest()
    (release / 'checksums.txt').write_text(
        checksums if checksums is not None else f'{"0" * 64}  defenseclaw_linux_amd64.tar.gz\n{digest}  install.sh\n')
    fakebin = tmp_path / 'bin'
    fakebin.mkdir()
    (fakebin / 'curl').write_text(FAKE_CURL)
    (fakebin / 'curl').chmod(0o755)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('OPENCLAW_', 'N2N_', 'DEFENSECLAW_', 'INSTALL_OPENSHELL', 'REGISTER_MCPS', 'NETCLAW_'))}
    env.update(HOME=str(home), PATH=f'{fakebin}:/usr/bin:/bin', FIXTURE_RELEASE=str(release),
               FIXTURE_CURL_LOG=str(tmp_path / 'curl.log'), FIXTURE_DC_LOG=str(tmp_path / 'dc.log'),
               FIXTURE_INSTALL_ARGS=str(tmp_path / 'install.args'),
               DEFENSECLAW_INSTALL_SHA256=digest)   # the fixture's "reviewed" installer
    return home, env


def run(env):
    return subprocess.run(['bash', str(SCRIPT)], env=env, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, timeout=60)


def test_bash_syntax():
    assert subprocess.run(['bash', '-n', str(SCRIPT)]).returncode == 0


def test_no_unpinned_pipe_to_shell():
    text = SCRIPT.read_text()
    assert '| bash' not in text and '| sh' not in text
    assert '/main/scripts/install.sh' not in text


def test_verified_install_init_guardrail_and_mode(tmp_path):
    home, env = fixture(tmp_path)
    proc = run(env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (tmp_path / 'install.args').read_text().split() == ['--yes', '--connector', 'openclaw']
    urls = (tmp_path / 'curl.log').read_text()
    assert 'releases/download/1.0.4/install.sh' in urls and 'releases/download/1.0.4/checksums.txt' in urls
    assert "--proto =https --tlsv1.2" in urls and 'OpenShell' not in urls
    calls = (tmp_path / 'dc.log').read_text().splitlines()
    assert 'init --connector openclaw --non-interactive --yes --scanner-mode local' in calls
    assert ('setup guardrail --connector openclaw --mode observe --scanner-mode local '
            '--detection-strategy regex_only --non-interactive --no-restart') in calls
    assert json.loads((home / '.openclaw/config/openclaw.json').read_text()) == {'keep': 1, 'security': {'mode': 'defenseclaw'}}
    out = proc.stdout + proc.stderr
    assert SECRET not in out
    assert 'defenseclaw setup provider add' in out and 'ollama.com' in out and 'openclaw gateway restart' in out
    assert 'do not edit it' in out
    assert 'in2n-services.py generate' in out


def test_version_and_mode_overrides(tmp_path):
    home, env = fixture(tmp_path)
    env.update(DEFENSECLAW_VERSION='1.0.5', DEFENSECLAW_GUARDRAIL_MODE='action')
    proc = run(env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert 'releases/download/1.0.5/install.sh' in (tmp_path / 'curl.log').read_text()
    assert any(' --mode action ' in c for c in (tmp_path / 'dc.log').read_text().splitlines())


def assert_refused_before_install(tmp_path, home, proc):
    assert proc.returncode != 0
    assert not (tmp_path / 'install.args').exists()
    assert not (tmp_path / 'dc.log').exists()
    assert json.loads((home / '.openclaw/config/openclaw.json').read_text()) == {'keep': 1}


def test_checksum_mismatch_fails_closed(tmp_path):
    home, env = fixture(tmp_path, checksums=f'{"a" * 64}  install.sh\n')
    proc = run(env)
    assert_refused_before_install(tmp_path, home, proc)
    assert 'mismatch' in proc.stderr


def test_missing_checksum_entry_fails_closed(tmp_path):
    home, env = fixture(tmp_path, checksums=f'{"a" * 64}  other.tar.gz\n')
    proc = run(env)
    assert_refused_before_install(tmp_path, home, proc)
    assert 'no single entry for install.sh' in proc.stderr


def test_secretref_gateway_token_stops_before_install(tmp_path):
    home, env = fixture(tmp_path, token={'source': 'file', 'provider': 'vault', 'id': SECRET})
    before = (home / '.openclaw/openclaw.json').read_text()
    proc = run(env)
    assert_refused_before_install(tmp_path, home, proc)
    assert not (tmp_path / 'curl.log').exists()
    assert 'SecretRef' in proc.stderr and 'str expected, not dict' in proc.stderr
    assert SECRET not in proc.stdout + proc.stderr
    assert (home / '.openclaw/openclaw.json').read_text() == before


def test_init_failure_is_reported_and_mode_unchanged(tmp_path):
    home, env = fixture(tmp_path)
    env['FIXTURE_INIT_FAIL'] = '1'
    proc = run(env)
    assert proc.returncode != 0
    assert 'str expected, not dict' in proc.stderr and "'defenseclaw init' failed" in proc.stderr
    assert not any(c.startswith('setup guardrail') for c in (tmp_path / 'dc.log').read_text().splitlines())
    assert json.loads((home / '.openclaw/config/openclaw.json').read_text()) == {'keep': 1}


def test_invalid_version_rejected(tmp_path):
    home, env = fixture(tmp_path)
    env['DEFENSECLAW_VERSION'] = '1.0.4/../../evil'
    proc = run(env)
    assert_refused_before_install(tmp_path, home, proc)
    assert not (tmp_path / 'curl.log').exists()



def test_default_version_requires_the_pinned_reviewed_installer(tmp_path):
    # Spec 167: checksums.txt comes from the same release; the reviewed 1.0.4 bytes
    # are pinned in the script, so a replaced asset with a matching checksums.txt fails.
    home, env = fixture(tmp_path)
    del env['DEFENSECLAW_INSTALL_SHA256']
    proc = run(env)
    assert_refused_before_install(tmp_path, home, proc)
    assert 'does not match the reviewed SHA-256' in proc.stdout + proc.stderr


def test_other_version_needs_an_operator_reviewed_digest(tmp_path):
    home, env = fixture(tmp_path)
    del env['DEFENSECLAW_INSTALL_SHA256']
    env['DEFENSECLAW_VERSION'] = '1.0.5'
    proc = run(env)
    assert_refused_before_install(tmp_path, home, proc)
    assert 'No reviewed SHA-256' in proc.stdout + proc.stderr and 'DEFENSECLAW_INSTALL_SHA256=' in proc.stdout + proc.stderr


def test_reviewed_digest_mismatch_fails_closed(tmp_path):
    home, env = fixture(tmp_path)
    env['DEFENSECLAW_INSTALL_SHA256'] = 'f' * 64
    proc = run(env)
    assert_refused_before_install(tmp_path, home, proc)
