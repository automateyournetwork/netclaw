#!/usr/bin/env python3
"""Reproducible managed compatibility for the existing NetBox MCP client."""
import argparse
import hashlib
from pathlib import Path
import shutil


def apply(source):
    target = Path(source) / 'src/netbox_mcp_server/netbox_client.py'
    text = target.read_text()
    replacements = [
        ('import requests\n', 'import requests\nfrom netbox_mcp_server.netclaw_http import auth_header, create_session\n'),
        ('self.session = requests.Session()', 'self.session = create_session(token)'),
        ('"Authorization": f"Token {token}"', '"Authorization": auth_header(token)'),
    ]
    original = text
    for old, new in reversed(replacements):
        if new in original: original = original.replace(new, old)
    if hashlib.sha256(original.encode()).hexdigest() != '4ecd4349b45cee844784216bb9e96724668b307785d37874a5aeee9007240b3a':
        raise ValueError('unreviewed_netbox_client_source')
    for old, new in replacements:
        if new in text: continue
        if text.count(old) != 1: raise ValueError('unreviewed_netbox_client_source')
        text = text.replace(old, new)
    target.write_text(text)
    shutil.copyfile(Path(__file__).parent / 'lib/netbox_http.py', target.with_name('netclaw_http.py'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    apply(parser.parse_args().source)
