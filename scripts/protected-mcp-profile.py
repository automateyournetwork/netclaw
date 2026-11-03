#!/usr/bin/env python3
"""Freeze an existing installed MCP/skill binding; no process or API is invoked.

Run on the target native host after dependency/source staging. The source root
must be a closed directory containing only the selected upstream Python package.
Each exact argument selection gets its own profile; credential values are never
written to this profile or printed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'mcp-servers/protocol-mcp'))
from bgp.federation.protected_mcp import (SCRIPT, origin, validate_binding, source_bytes, need)
from bgp.federation.protected_runtime import canonical, sha, private_directory, private_write


def materialize(*, kind, python, source, skill, arguments, input_schema, output, netbox_origin=None, credential_file=None):
    output=Path(output).absolute();private_directory(output.parent)
    need(not output.exists() and not output.is_symlink(),'mcp_profile_exists')
    python=Path(python).absolute();venv=python.parent.parent
    need(python.parent.resolve()==python.parent,'mcp_python_refused')
    files,links={},{}
    for directory,dirs,names in os.walk(venv,followlinks=False):
        for name in dirs+names:
            path=Path(directory)/name;relative=str(path.relative_to(venv))
            if path.is_symlink():links[relative]=os.readlink(path)
            elif path.is_file():files[relative]=hashlib.sha256(source_bytes(str(path),128*1024*1024)).hexdigest()
    manifest={'files':files,'symlinks':links,'executable_sha256':hashlib.sha256(source_bytes(str(python.resolve()),128*1024*1024)).hexdigest()}
    manifest_path=output.with_name(output.stem+'-python-manifest.json')
    need(not manifest_path.exists() and not manifest_path.is_symlink(),'mcp_python_manifest_exists')
    private_write(manifest_path,canonical(manifest))
    source=Path(source).absolute();skill=Path(skill).absolute()
    source_files={str(p.relative_to(source)):hashlib.sha256(source_bytes(str(p))).hexdigest()
                  for p in source.rglob('*') if p.is_file() or p.is_symlink()}
    tool='netbox_get_object_by_id' if kind=='netbox' else 'subnet_calculator'
    result={'kind':kind,'tool':tool,'python':str(python),'python_manifest':str(manifest_path),
        'python_manifest_sha256':sha(manifest),'source_root':str(source),'source_sha256':source_files,
        'input_schema_sha256':sha(input_schema),'selection_sha256':sha({'tool':tool,'arguments':arguments}),
        'skill':{'path':str(skill),'sha256':hashlib.sha256(source_bytes(str(skill),65536)).hexdigest()}}
    if kind=='netbox':
        result.update(origin=origin(netbox_origin),credential_file=str(Path(credential_file).absolute()))
        result['endpoint_sha256']=sha({'kind':'netbox','origin':result['origin']})
    else:
        need(netbox_origin is None and credential_file is None,'subnet_credentials_refused')
        result['endpoint_sha256']=sha({'kind':'subnet','transport':'private-stdio'})
    validate_binding(result,arguments=arguments)
    private_write(output,canonical(result))
    return result


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=sorted(SCRIPT),required=True)
    parser.add_argument('--python',required=True)
    parser.add_argument('--source',required=True)
    parser.add_argument('--skill',required=True)
    parser.add_argument('--arguments',required=True,help='Complete non-secret approved tool arguments as JSON')
    parser.add_argument('--input-schema',type=Path,required=True,help='JSON inputSchema from actual MCP tools/list')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--origin')
    parser.add_argument('--credential-file')
    args=parser.parse_args()
    try:
        need(args.kind!='netbox' or args.credential_file is not None,'netbox_credential_file_required')
        config=materialize(kind=args.kind,python=args.python,source=args.source,skill=args.skill,
            arguments=json.loads(args.arguments),input_schema=json.loads(args.input_schema.read_text()),output=args.output,
            netbox_origin=args.origin,credential_file=args.credential_file)
        print(json.dumps({'created':str(args.output),'tool':config['tool'],'selection_sha256':config['selection_sha256']}))
    except Exception:
        print('Protected MCP profile refused; inspect paths and reviewed bindings.',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
