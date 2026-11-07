/** Read-only installed production HUD closure inventory; explicit copy is fresh-only. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire,isBuiltin} from 'node:module';
import {pathToFileURL} from 'node:url';
import {boundedFile,noSymlink,buildProtectedManifest} from '../../ui/netclaw-visual/src/hud-server/protected-assets.js';
import {strictJson} from '../../ui/netclaw-visual/src/hud-server/protected-client.js';
const hash=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const need=(yes,code)=>{if(!yes)throw Error(code);};
const canonical=v=>v===null||typeof v!=='object'?JSON.stringify(v):Array.isArray(v)?'['+v.map(canonical).join(',')+']':'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
const within=(root,file)=>file===root||file.startsWith(root+path.sep);
const packageName=name=>name.startsWith('@')?name.split('/').slice(0,2).join('/'):name.split('/')[0];
const privateDirectory=directory=>{noSymlink(directory);const s=fs.lstatSync(directory);need(s.isDirectory()&&s.uid===process.getuid()&&!(s.mode&0o077),'private_directory_required');};
function regular(file) {
  noSymlink(file);const s=fs.lstatSync(file);need(s.isFile()&&s.nlink===1&&[0,process.getuid()].includes(s.uid)&&!(s.mode&0o022),'regular_owned_source_required');
  return boundedFile(file,128*1024*1024);
}
function references(text) {
  // The selected production modules use literal imports. Dynamic expressions
  // cannot be inventoried safely and are refused instead of guessed.
  for(const match of text.matchAll(/\b(?:import|require)\s*\(\s*([^\s'"`])/g))throw Error('nonliteral_dependency_refused');
  const values=new Set();
  for(const pattern of [/\b(?:import|export)\s+(?:[^;'"\n]*?\s+from\s*)?['"]([^'"\n]+)['"]/g,/\b(?:import|require)\s*\(\s*['"]([^'"\n]+)['"]\s*\)/g])for(const match of text.matchAll(pattern))values.add(match[1]);
  return [...values].sort();
}
function installedPackage(name,from,modules,optional=false) {
  need(/^(?:@[a-z0-9._-]+\/)?[a-z0-9._-]+$/i.test(name),'package_name_refused');
  for(const directory of createRequire(from).resolve.paths(name)||[]) {
    const candidate=path.join(directory,name);
    if(!fs.existsSync(candidate)&&!fs.lstatSync(directory,{throwIfNoEntry:false})?.isSymbolicLink())continue;
    if(!fs.existsSync(candidate))continue;
    need(within(modules,candidate),'dependency_outside_hud');noSymlink(candidate);
    need(fs.lstatSync(candidate).isDirectory(),'dependency_directory_required');return candidate;
  }
  if(optional)return null;throw Error('installed_dependency_missing:'+name);
}

export function inventory(repository) {
  noSymlink(repository);need(path.isAbsolute(repository),'absolute_source_required');
  const ui=path.join(repository,'ui/netclaw-visual'),modules=path.join(ui,'node_modules');
  const lock=strictJson(regular(path.join(ui,'package-lock.json')).toString('utf8'));
  need(lock.packages&&[2,3].includes(lock.lockfileVersion),'installed_lock_required');
  const sourceFiles={},packages=[],seen=new Set(),sourceSeen=new Set();let total=0;
  const add=file=>{need(within(repository,file),'source_escape');const name=path.relative(repository,file).split(path.sep).join('/');const raw=regular(file),sha=hash(raw);if(Object.hasOwn(sourceFiles,name)){need(sourceFiles[name]===sha,'source_changed');return;}sourceFiles[name]=sha;total+=raw.length;need(Object.keys(sourceFiles).length<=20000&&total<=512*1024*1024,'closure_bound');};
  const visitPackage=directory=>{
    if(seen.has(directory))return;seen.add(directory);
    const packageFile=path.join(directory,'package.json'),pkg=strictJson(regular(packageFile).toString('utf8'));
    const relative=path.relative(ui,directory).split(path.sep).join('/'),record=lock.packages[relative];
    need(record&&record.version===pkg.version&&typeof pkg.name==='string','installed_package_lock_mismatch');
    packages.push({path:relative,name:pkg.name,version:pkg.version,lock_integrity:record.integrity||null});
    const walk=current=>{for(const entry of fs.readdirSync(current,{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name))){if(entry.name==='node_modules')continue;const file=path.join(current,entry.name);need(!entry.isSymbolicLink(),'dependency_alias_refused');if(entry.isDirectory())walk(file);else add(file);}};
    walk(directory);
    const required=pkg.dependencies||{},optional=pkg.optionalDependencies||{},peers=pkg.peerDependencies||{};
    for(const name of Object.keys({...required,...optional,...peers}).sort()){
      const isOptional=Object.hasOwn(optional,name)||!Object.hasOwn(required,name)&&Object.hasOwn(peers,name)&&pkg.peerDependenciesMeta?.[name]?.optional===true;
      const dependency=installedPackage(name,packageFile,modules,isOptional);if(dependency)visitPackage(dependency);
    }
  };
  const visitSource=file=>{
    if(sourceSeen.has(file))return;sourceSeen.add(file);add(file);
    if(!/\.[cm]?js$/.test(file))return;
    for(const specifier of references(regular(file).toString('utf8'))){
      if(isBuiltin(specifier))continue;
      if(specifier.startsWith('.')){const dependency=path.resolve(path.dirname(file),specifier);need(within(path.join(ui,'src'),dependency),'relative_import_outside_hud');visitSource(dependency);}
      else {need(!specifier.startsWith('/')&&!specifier.includes(':')&&!specifier.startsWith('#'),'module_reference_refused');visitPackage(installedPackage(packageName(specifier),file,modules));}
    }
  };
  visitSource(path.join(ui,'src/hud-server/protected-server.js'));
  add(path.join(ui,'package.json'));add(path.join(ui,'package-lock.json'));
  const dist=path.join(ui,'dist'),assets=buildProtectedManifest(dist);
  add(path.join(dist,'.vite/manifest.json'));for(const row of assets.files)add(path.join(dist,row.path));
  packages.sort((a,b)=>a.path.localeCompare(b.path));
  return {schema_version:1,classification:'SOURCE_ONLY',repository,packages,asset_manifest:assets,
    source_files:Object.fromEntries(Object.entries(sourceFiles).sort(([a],[b])=>a.localeCompare(b))),
    files:Object.keys(sourceFiles).length,bytes:total};
}

export function copyClosure(report,destination) {
  need(report.classification==='SOURCE_ONLY'&&path.isAbsolute(destination)&&!within(report.repository,destination)&&!within(destination,report.repository),'separate_destination_required');
  privateDirectory(path.dirname(destination));need(!fs.existsSync(destination),'fresh_destination_required');
  // Verify all reviewed bytes before the first write. No hard links or aliases.
  for(const [name,sha] of Object.entries(report.source_files)){need(!name.startsWith('/')&&name.split('/').every(p=>p&&p!=='.'&&p!=='..')&&!name.includes('\\'),'relative_source_required');need(hash(regular(path.join(report.repository,name)))===sha,'source_changed');}
  fs.mkdirSync(destination,{mode:0o700});
  for(const [name,sha] of Object.entries(report.source_files)){
    const raw=regular(path.join(report.repository,name));need(hash(raw)===sha,'source_changed');const target=path.join(destination,name);
    fs.mkdirSync(path.dirname(target),{recursive:true,mode:0o700});const fd=fs.openSync(target,fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_NOFOLLOW,0o400);
    try {fs.writeFileSync(fd,raw);fs.fsyncSync(fd);}finally {fs.closeSync(fd);}
  }
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {
    const [action,repository,out,...extra]=process.argv.slice(2);need(['inventory','copy'].includes(action)&&repository&&out&&extra.length===(action==='copy'?1:0),'arguments');
    privateDirectory(path.dirname(out));need(!fs.existsSync(out),'fresh_inventory_required');const report=inventory(repository);
    if(action==='copy')copyClosure(report,extra[0]);
    const fd=fs.openSync(out,fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_NOFOLLOW,0o600);try{fs.writeFileSync(fd,canonical(report));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
    console.log(JSON.stringify({classification:report.classification,packages:report.packages.length,files:report.files,bytes:report.bytes,copy:action==='copy'}));
  } catch(error){console.error('HUD source closure refused: '+String(error.message||error));process.exitCode=1;}
}
