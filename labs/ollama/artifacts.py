#!/usr/bin/env python3
"""Prepare fresh NetClaw model artifacts from hash-pinned public Ollama bytes.

The model/CPU manifests record official upstream artifacts previously verified by
Thermidor Spec004. No Thermidor runtime, private state or transport is imported.
Preparation never starts a model, downloads weights or alters an existing home.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

HERE = Path(__file__).resolve().parent


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def safe_root(path):
    path = Path(path).absolute()
    if path != path.resolve() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError('artifact_symlink_refused')
    return path


def verified_file(path, expected, size=None):
    path = safe_root(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or size is not None and info.st_size != size or sha(path) != expected:
        raise ValueError('artifact_digest_mismatch')


def load_lock():
    return json.loads((HERE / 'model-lock.json').read_bytes())


def verify_cpu(directory, architecture):
    root = safe_root(directory)
    lock = load_lock()
    manifest = HERE / ('cpu-' + architecture + '.json')
    verified_file(manifest, lock['runner']['cpu_artifacts'][architecture])
    expected = json.loads(manifest.read_bytes())
    if expected['architecture'] != architecture or expected['official_image'] != 'ollama/ollama@sha256:' + lock['runner']['manifests'][architecture]:
        raise ValueError('cpu_manifest_identity_changed')
    actual = {}
    for path in sorted(root.rglob('*')):
        name = str(path.relative_to(root))
        if path.is_symlink():
            if not path.resolve(strict=True).is_relative_to(root):
                raise ValueError('foreign_cpu_symlink')
            actual[name] = {'link': os.readlink(path)}
        elif path.is_file():
            actual[name] = {'sha256': sha(path), 'size': path.stat().st_size}
        elif not path.is_dir():
            raise ValueError('cpu_special_file')
    if actual != expected['files']:
        raise ValueError('cpu_artifact_closure_changed')
    return expected


def verify_store(directory):
    root = safe_root(directory)
    model = load_lock()['model']
    files = {model['manifest_path']: (model['manifest_sha256'], None)}
    files.update({'blobs/sha256-' + row['sha256']: (row['sha256'], row['size']) for row in model['blobs']})
    paths = list(root.rglob('*'))
    if len(paths) > 64 or any(path.is_symlink() for path in paths) or {str(p.relative_to(root)) for p in paths if p.is_file()} != set(files):
        raise ValueError('model_store_closure_changed')
    if not (root / 'manifests-v2').is_dir() or any((root / 'manifests-v2').iterdir()):
        raise ValueError('alternate_model_manifest_refused')
    for rel, (digest, size) in files.items():
        verified_file(root / rel, digest, size)
    return files


def prepare(source_store, cpu_directory, architecture, destination):
    """Copy only immutable public artifacts to a fresh owned directory."""
    target = safe_root(destination)
    if target.exists() or not target.parent.is_dir():
        raise ValueError('fresh_existing_parent_required')
    source = safe_root(source_store)
    files = verify_store(source)
    cpu = verify_cpu(cpu_directory, architecture)
    lock = load_lock()
    verified_file(HERE / 'Ollama-LICENSE', lock['runner']['license_sha256'])
    target.mkdir(mode=0o700)
    try:
        models = target / 'models'
        models.mkdir()
        for rel in files:
            dest = models / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / rel, dest)
            dest.chmod(0o444)
        (models / 'manifests-v2').mkdir()
        for path in sorted(models.rglob('*'), reverse=True):
            if path.is_dir():
                path.chmod(0o555)
        models.chmod(0o555)
        context = target / 'context'
        context.mkdir(mode=0o700)
        shutil.copytree(cpu_directory, context / 'cpu', symlinks=True)
        verify_cpu(context / 'cpu', architecture)
        for name in ('Ollama-LICENSE', 'model-lock.json', 'Dockerfile.model'):
            shutil.copyfile(HERE / name, context / name)
        # Only CPU public bytes are copied; no product package or runtime state.
        receipt = {'schema_version': 1, 'architecture': architecture, 'product': 'netclaw',
                   'runner_version': lock['runner']['version'], 'official_image': cpu['official_image'],
                   'model_manifest_sha256': lock['model']['manifest_sha256'],
                   'cpu_manifest_sha256': lock['runner']['cpu_artifacts'][architecture],
                   'files': {str(p.relative_to(target)): sha(p) for p in target.rglob('*') if p.is_file() and not p.is_symlink()}}
        path = target / 'prepared.json'
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(receipt, stream, indent=2)
        verify_store(models)
        return receipt
    except BaseException:
        # Preserve partial preparation for diagnosis; never silently clean/retry.
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-store', type=Path, required=True)
    parser.add_argument('--cpu-directory', type=Path, required=True)
    parser.add_argument('--architecture', choices=['arm64', 'amd64'], required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    value = prepare(args.source_store, args.cpu_directory, args.architecture, args.destination)
    print(json.dumps({key: value[key] for key in ['schema_version', 'architecture', 'product', 'runner_version', 'model_manifest_sha256', 'cpu_manifest_sha256']}))


if __name__ == '__main__':
    main()
