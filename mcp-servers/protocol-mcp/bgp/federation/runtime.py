"""Local installation selection and display-only harness metadata (spec 149).

Remote cards never select an executable. Identity is shared with the HUD; mutable
federation state lives under its own owner-private directory.
"""
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import uuid

ROOT = Path(__file__).resolve().parents[4]


def private_dir(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    info = directory.lstat()
    if directory.is_symlink() or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('owner_invalid: private directory required')
    return directory


def read_private(file):
    fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size > 8192:
            raise ValueError('owner_invalid: private file required')
        return json.load(stream)


def write_private(file, value):
    file = Path(file)
    private_dir(file.parent)
    if file.exists() or file.is_symlink():
        read_private(file)
    temporary = file.with_name(file.name + '.' + str(uuid.uuid4()) + '.tmp')
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, file)


@dataclass(frozen=True)
class Runtime:
    kind: str
    home: Path
    config: Path
    installation: str | None

    @property
    def base(self): return self.home / 'n2n'
    @property
    def state(self): return self.home / 'netclaw-federation'
    @property
    def skills(self): return self.home / ('skills' if self.kind == 'hermes' else 'workspace/skills')
    @property
    def env_file(self): return self.home / '.env'

    def fence(self, initialize=False):
        if not self.installation:
            raise ValueError('owner_invalid: installation is not initialized')
        private_dir(self.state)
        identity = self.state / 'owner.json'
        expected = {'schemaVersion': 1, 'installationId': self.installation, 'kind': self.kind, 'home': str(self.home)}
        try:
            if read_private(identity) != expected: raise ValueError('owner_invalid: federation belongs to another installation')
        except FileNotFoundError:
            if not initialize: raise
            write_private(identity, expected)
        return self

    def environment(self, env=None):
        value = dict(os.environ if env is None else env)
        for key in ('HERMES_HOME', 'OPENCLAW_HOME', 'OPENCLAW_STATE_DIR', 'OPENCLAW_CONFIG_PATH'):
            value.pop(key, None)
        value.update(NETCLAW_RUNTIME=self.kind, NETCLAW_INSTALLATION_ID=self.installation or '',
                     N2N_BASE_DIR=str(self.base), NETCLAW_RUNTIME_ROOT=str(self.home/'python-runtimes'),
                     NETCLAW_RUNTIME_ENV=str(self.env_file))
        if self.kind == 'hermes': value['HERMES_HOME'] = str(self.home)
        else: value.update(OPENCLAW_HOME=str(self.home), OPENCLAW_STATE_DIR=str(self.home), OPENCLAW_CONFIG_PATH=str(self.config))
        return value


def selected(env=None, *, initialize=False):
    spec = importlib.util.spec_from_file_location('_netclaw_selection', ROOT/'scripts/runtime-selection.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    value = module.resolve(env)
    home = Path(value['home'])
    if home.exists() or home.is_symlink():
        if home.is_symlink() or not home.is_dir() or home.stat().st_uid != os.getuid():
            raise ValueError('selection_invalid: owned home required')
        home = home.resolve()
    identity = home/'netclaw-hud/installation.json'
    try: saved = read_private(identity)
    except FileNotFoundError:
        saved = None
        if initialize:
            private_dir(identity.parent)
            proposed = {'schemaVersion': 1, 'installationId': str(uuid.uuid4())}
            try:
                fd = os.open(identity, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'w') as stream:
                    json.dump(proposed, stream); stream.flush(); os.fsync(stream.fileno())
            except FileExistsError: pass
            saved = read_private(identity)
    if saved and (saved.get('schemaVersion') != 1 or not re.fullmatch(r'[a-f0-9-]{36}', str(saved.get('installationId', '')))):
        raise ValueError('owner_invalid: invalid installation identity')
    return Runtime(value['kind'], home, Path(value['configPath']), saved['installationId'] if saved else None)


def project_harness(value, *, source='peer-advertised', observed_at=None):
    """Treat hostile/missing fields as unknown, retaining bounded unknown names."""
    value = value if isinstance(value, dict) else {}
    kind = value.get('type')
    if not isinstance(kind, str) or not re.fullmatch(r'[a-z][a-z0-9_.-]{0,63}', kind): kind = 'unknown'
    version = value.get('version')
    if not isinstance(version, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+\-]{0,127}', version): version = None
    if kind == 'unknown': version = None
    return {'type': kind, 'version': version, 'status': 'known' if kind in ('hermes','openclaw') else ('unknown' if kind == 'unknown' else 'unrecognized'),
            'source': source, 'observed_at': observed_at}


def local_harness(runtime=None):
    runtime = runtime or selected()
    version = None
    if runtime.kind == 'hermes':
        # Only report the selected source if its full qualified manifest matches.
        record=runtime.home/'python-runtimes/records/hermes-hud-agent-source'
        source = Path(record.read_text().strip()) if record.exists() else runtime.home/'python-runtimes/hermes-hud-agent/source'
        manifest = json.loads((ROOT/'config/hermes-hud-compatibility.json').read_text())
        try:
            if all(hashlib.sha256((source/name).read_bytes()).hexdigest() == expected for name, expected in manifest['files'].items()):
                version = manifest['release'].removeprefix('v')
        except OSError: pass
    return project_harness({'type': runtime.kind, 'version': version}, source='local-selected')
