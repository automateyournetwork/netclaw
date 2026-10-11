import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../../',import.meta.url)),extension=path.join(root,'extensions/netclaw-vscode');
const require=createRequire(path.join(extension,'package.json')),{listFiles,PackageManager}=require('@vscode/vsce');
const expected=new Set(['package.json','README.md','CHANGELOG.md','LICENSE','PRIVACY.md','dist/extension.cjs','dist/extension.cjs.LEGAL.txt','dist/avatar.js','dist/avatar.js.LEGAL.txt','dist/canvas.js','resources/icon.png','resources/activity.svg','resources/workbench.css','resources/chat.js','resources/rag.js','resources/pal/john.glb','resources/pal/john.png','resources/pal/lobster.glb','resources/pal/lobster.png','resources/pal/manifest.json','resources/screenshots/rag.png','resources/screenshots/canvas.png']);

test('VSIX file discovery includes only the exact runtime allowlist and excludes synthetic private material',async()=>{
  const probes=['.env.package-leak-fixture','credentials.fixture.json','private-installation.fixture.sqlite'];
  for(const name of probes)fs.writeFileSync(path.join(extension,name),'SYNTHETIC_PACKAGE_SECRET_MUST_NOT_SHIP_150',{flag:'wx',mode:0o600});
  try{
    const files=await listFiles({cwd:extension,packageManager:PackageManager.None});
    assert.deepEqual(new Set(files),expected);
    for(const file of files){
      assert.ok(!fs.lstatSync(path.join(extension,file)).isSymbolicLink());
      const data=fs.readFileSync(path.join(extension,file));assert.ok(!data.includes(Buffer.from('SYNTHETIC_PACKAGE_SECRET_MUST_NOT_SHIP_150')));
    }
    const manifest=JSON.parse(fs.readFileSync(path.join(extension,'package.json')));
    assert.equal(manifest.publisher,'NetClaw');assert.equal(manifest.name,'netclaw');
    assert.equal(manifest.browser,undefined);assert.equal(manifest.enabledApiProposals,undefined);
  }finally{for(const name of probes)fs.unlinkSync(path.join(extension,name));}
});
