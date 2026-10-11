import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const cwd=fileURLToPath(new URL('../',import.meta.url)),root=path.resolve(cwd,'../..');
const require=createRequire(new URL('../package.json',import.meta.url));
const {createVSIX}=require('@vscode/vsce');
const source=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim();
if(!/^[a-f\d]{40}$/.test(source))throw Error('A committed source reference is required.');
const dirty=execFileSync('git',['status','--porcelain'],{cwd:root,encoding:'utf8'}).trim();
if(dirty)throw Error('Commit the reviewed source before packaging so Marketplace links and provenance identify the actual files.');
const manifest=JSON.parse(fs.readFileSync(path.join(cwd,'package.json'),'utf8'));
const packagePath=path.join(cwd,`netclaw-${manifest.version}.vsix`);
await createVSIX({cwd,packagePath,dependencies:false,
  baseContentUrl:`https://github.com/automateyournetwork/netclaw/blob/${source}/extensions/netclaw-vscode`,
  baseImagesUrl:`https://raw.githubusercontent.com/automateyournetwork/netclaw/${source}/extensions/netclaw-vscode`});
const bytes=fs.readFileSync(packagePath),sha256=createHash('sha256').update(bytes).digest('hex');
fs.mkdirSync(path.join(cwd,'out'),{recursive:true});
fs.writeFileSync(path.join(cwd,'out/package.json'),JSON.stringify({publisher:manifest.publisher,name:manifest.name,version:manifest.version,source,sha256,bytes:bytes.length,artifact:path.basename(packagePath),qualification:'Development candidate; see Spec150 evidence. Publication not performed.'},null,2)+'\n');
console.log(JSON.stringify({artifact:packagePath,source,sha256,bytes:bytes.length}));
