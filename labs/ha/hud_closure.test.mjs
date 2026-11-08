import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
import {inventory,copyClosure} from './hud_closure.mjs';
function fixture() {
 const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'netclaw-r08-closure-')));fs.chmodSync(root,0o700);const repo=path.join(root,'source'),ui=path.join(repo,'ui/netclaw-visual');
 const write=(relative,value)=>{const file=path.join(ui,relative);fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o700});fs.writeFileSync(file,typeof value==='string'?value:JSON.stringify(value),{mode:0o600});};
 write('package.json',{name:'hud',type:'module'});
 write('src/hud-server/protected-server.js',"import express from 'express'; import './other.js';\n");
 write('src/hud-server/other.js',"import crypto from 'node:crypto'; export const value=1;\n");
 write('package-lock.json',{lockfileVersion:3,packages:{'node_modules/express':{version:'1.0.0'},'node_modules/express/node_modules/dep':{version:'2.0.0'}}});
 write('node_modules/express/package.json',{name:'express',version:'1.0.0',dependencies:{dep:'2.0.0'}});write('node_modules/express/index.js',"module.exports=require('dep');");
 write('node_modules/express/node_modules/dep/package.json',{name:'dep',version:'2.0.0'});write('node_modules/express/node_modules/dep/index.js','module.exports=2;');
 write('node_modules/unrelated-dev/package.json',{name:'unrelated-dev',version:'99'});write('node_modules/unrelated-dev/private.txt','not in runtime closure');
 write('dist/index.html','<html><script src="/assets/entry.js"></script></html>');write('dist/assets/entry.js','window.sourceFixture=true;');
 write('dist/.vite/manifest.json',{'index.html':{isEntry:true,file:'assets/entry.js'}});write('dist/unrelated.txt','not in asset closure');
 return {root,repo,ui,write,close:()=>fs.rmSync(root,{recursive:true})};
}
test('deterministic source/assets plus exact installed nested production dependency closure',()=>{
 const f=fixture();try{const a=inventory(f.repo),b=inventory(f.repo);assert.deepEqual(a,b);assert.equal(a.packages.length,2);assert.ok(a.source_files['ui/netclaw-visual/node_modules/express/node_modules/dep/index.js']);assert.ok(a.source_files['ui/netclaw-visual/src/hud-server/other.js']);assert.ok(a.source_files['ui/netclaw-visual/dist/assets/entry.js']);assert.ok(!Object.keys(a.source_files).some(p=>p.includes('unrelated')));}finally{f.close();}
});
for(const [name,change] of [
 ['installed version drift',f=>f.write('node_modules/express/package.json',{name:'express',version:'2.0.0'})],
 ['nonliteral import',f=>f.write('src/hud-server/other.js','const n="unknown"; import(n);')],
 ['remote module',f=>f.write('src/hud-server/other.js','import x from "https://example.invalid/x.js";')],
 ['relative escape',f=>f.write('src/hud-server/other.js','import "../../../../outside.js";')],
 ['symlink dependency file',f=>fs.symlinkSync('package.json',path.join(f.ui,'node_modules/express/alias.json'))],
 ['hardlinked dependency file',f=>fs.linkSync(path.join(f.ui,'node_modules/express/index.js'),path.join(f.ui,'node_modules/express/linked.js'))],
 ['dependency outside source',f=>{fs.rmSync(path.join(f.ui,'node_modules/express'),{recursive:true});fs.mkdirSync(path.join(f.repo,'node_modules/express'),{recursive:true});fs.writeFileSync(path.join(f.repo,'node_modules/express/package.json'),'{}');}],
])test('inventory refuses '+name,()=>{const f=fixture();try{change(f);assert.throws(()=>inventory(f.repo));}finally{f.close();}});
test('fresh copy keeps exact bytes without aliasing or overwrite',()=>{
 const f=fixture();try{const report=inventory(f.repo),destination=path.join(f.root,'copied');copyClosure(report,destination);for(const name of Object.keys(report.source_files)){const a=path.join(f.repo,name),b=path.join(destination,name);assert.deepEqual(fs.readFileSync(a),fs.readFileSync(b));assert.notEqual(fs.statSync(a).ino,fs.statSync(b).ino);assert.equal(fs.statSync(b).nlink,1);assert.equal(fs.statSync(b).mode&0o777,0o400);}assert.throws(()=>copyClosure(report,destination));}finally{f.close();}
});
test('changed source is refused before fresh copy creates a destination',()=>{
 const f=fixture();try{const report=inventory(f.repo),destination=path.join(f.root,'copied');f.write('dist/assets/entry.js','changed');assert.throws(()=>copyClosure(report,destination));assert.equal(fs.existsSync(destination),false);}finally{f.close();}
});
