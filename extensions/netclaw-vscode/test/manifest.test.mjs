import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
const manifest=JSON.parse(fs.readFileSync(new URL('../package.json',import.meta.url),'utf8'));
test('desktop workspace placement, minimum API and exact mobile logo',()=>{
  assert.deepEqual(manifest.extensionKind,['workspace']);assert.equal(manifest.engines.vscode,'^1.102.0');assert.equal(manifest.publisher,'NetClaw');
  const hash=url=>createHash('sha256').update(fs.readFileSync(url)).digest('hex');
  assert.equal(hash(new URL('../resources/icon.png',import.meta.url)),hash(new URL('../../../mobile/netclaw-mobile/assets/icon/icon.png',import.meta.url)));
  assert.equal(manifest.capabilities.untrustedWorkspaces.supported,'limited');assert.equal(manifest.browser,undefined);
});
