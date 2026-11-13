#!/usr/bin/env python3
"""Validate canonical metadata, exact joins, field classifications and local links."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/lib'))
from mcp_environment import load_mcp_template
from setup_schema import loads, validate


def check(catalog, root=ROOT):
    errors = []
    schema = loads((root / 'config/components/schema.json').read_bytes(), 16 * 1024 * 1024)
    errors.extend(f"schema:{e['pointer']}:{e['code']}" for e in validate(catalog, schema))
    components = {c['id']: c for c in catalog['components']}
    skills = {s['id']: s for s in catalog['skills']}
    if len(components) != len(catalog['components']) or len(skills) != len(catalog['skills']):
        errors.append('duplicate_descriptor')
    actual = {p.parent.name for p in (root / 'workspace/skills').glob('*/SKILL.md')}
    if set(skills) != actual:
        errors.append('skill_inventory_mismatch')
    registered = set(load_mcp_template((root / 'config/openclaw.json').read_bytes(), 16 * 1024 * 1024))
    joined = {s for c in components.values() for s in c['servers']}
    if registered != joined:
        errors.append('server_join_mismatch')
    functions = set(re.findall(r'^(component_install_\w+)\(\)', (root / 'scripts/lib/install-steps.sh').read_text(), re.M))
    for index, c in enumerate(catalog['components']):
        if c['order'] != index or c['installer']['function'] not in functions:
            errors.append(c['id'] + ':installer_or_order')
        if not set(c['dependencies']) <= set(components) or not set(c['skills']) <= set(skills):
            errors.append(c['id'] + ':invalid_join')
        if len({f['key'] for f in c['settings']}) != len(c['settings']):
            errors.append(c['id'] + ':duplicate_setting')
    for skill in skills.values():
        source = root / skill['path']
        if source != root / 'workspace/skills' / skill['id'] / 'SKILL.md' or not source.is_file():
            errors.append(skill['id'] + ':skill_path')
        elif hashlib.sha256(source.read_bytes()).hexdigest() != skill['sha256']:
            errors.append(skill['id'] + ':skill_hash')
        if not set(skill['components']) <= set(components) or not set(skill['servers']) <= registered:
            errors.append(skill['id'] + ':invalid_join')
    for group in ('profiles', 'memberProfiles', 'surfaceAliases', 'externalIntegrations'):
        for item in catalog.get(group, []):
            if not set(item['components']) <= set(components):
                errors.append(group + ':invalid_join')
    for entry in [*components.values(), *skills.values(), *catalog['choices']]:
        for field in entry.get('settings', []):
            if field['classification'] == 'secret' and field['example']:
                errors.append(entry['id'] + ':secret_example')
            if (field['required'] == 'conditional') != (field['condition'] is not None):
                errors.append(entry['id'] + ':condition')
            if not set(field['sharedWith']) <= set(components):
                errors.append(entry['id'] + ':shared_setting_join')
        for link in entry['links']:
            target = link['target']
            if not target:
                if not link['unavailableReason']:
                    errors.append(entry['id'] + ':missing_link_reason')
            elif target.startswith('https://'):
                parsed = urlsplit(target)
                if not parsed.hostname or parsed.username or parsed.password or '*' in target or '${' in target:
                    errors.append(entry['id'] + ':invalid_url')
            elif '://' in target or target.startswith('/') or '..' in Path(target.split('#')[0]).parts:
                errors.append(entry['id'] + ':unsafe_link')
            elif not (root / target.split('#')[0]).exists():
                errors.append(entry['id'] + ':missing_local_link')
    # External integrations use explicit dispositions; no fuzzy keyword fallback.
    module = ast.parse((root / 'scripts/verify-inventory-counts.py').read_text())
    expected = next(ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'EXTERNAL_INTEGRATIONS' for t in n.targets))
    if set(expected) != {e['name'] for e in catalog.get('externalIntegrations', [])}:
        errors.append('external_inventory_mismatch')
    return errors


def main():
    catalog = loads((ROOT / 'config/components/catalog.json').read_bytes(), 16 * 1024 * 1024)
    errors = check(catalog)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f"Catalog metadata: PASS ({len(catalog['components'])} components, {len(catalog['skills'])} skills)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
