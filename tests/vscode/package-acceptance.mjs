import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {installationFixture} from '../operator/fixtures.mjs';

const root=fileURLToPath(new URL('../../',import.meta.url)),extension=path.join(root,'extensions/netclaw-vscode');
const require=createRequire(path.join(extension,'package.json'));
const {download,runTests,resolveCliArgsFromVSCodeExecutablePath}=require('@vscode/test-electron');
const {createVSIX,listFiles,PackageManager}=require('@vscode/vsce');
const exec=promisify(execFile),fixture=installationFixture();
const temporary=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'netclaw150-vsix-'))),user=path.join(temporary,'user'),extensions=path.join(temporary,'extensions'),driver=path.join(temporary,'driver');
const current=path.resolve(process.env.NETCLAW_TEST_VSIX||path.join(extension,'netclaw-0.1.0.vsix'));
const manifest=JSON.parse(fs.readFileSync(path.join(extension,'package.json')));
const baseline=fs.readFileSync(fixture.configPath),environment=fs.readFileSync(path.join(fixture.home,'.env'));
for(const directory of [path.join(user,'User'),extensions,driver])fs.mkdirSync(directory,{recursive:true});
fs.writeFileSync(path.join(user,'User/settings.json'),JSON.stringify({'telemetry.telemetryLevel':'off','update.mode':'none','extensions.autoUpdate':false,'workbench.startupEditor':'none','security.workspace.trust.startupPrompt':'never'}));
fs.writeFileSync(path.join(driver,'package.json'),JSON.stringify({name:'netclaw-package-driver',publisher:'netclaw-tests',version:'0.0.1',engines:{vscode:'^1.102.0'},main:'index.js',activationEvents:['onStartupFinished']}));
fs.writeFileSync(path.join(driver,'index.js'),'exports.activate=()=>{};');
const vscodeExecutablePath=await download({version:'1.102.0',cachePath:path.join(extension,'.vscode-test')});
const [cli,...cliArgs]=resolveCliArgsFromVSCodeExecutablePath(vscodeExecutablePath);
async function command(args){return exec(cli,[...cliArgs,'--user-data-dir',user,'--extensions-dir',extensions,...args],{env:{...process.env,ELECTRON_RUN_AS_NODE:'1'},maxBuffer:1024*1024,timeout:30000});}
async function phase(name,version){
  await runTests({vscodeExecutablePath,extensionDevelopmentPath:driver,extensionTestsPath:path.join(root,'tests/vscode/package-editor.cjs'),reuseMachineInstall:false,
    extensionTestsEnv:{NETCLAW_PACKAGE_PHASE:name,NETCLAW_PACKAGE_VERSION:version,NETCLAW_PACKAGE_EXTENSIONS:extensions,NETCLAW_PACKAGE_FIXTURE:JSON.stringify(fixture),NETCLAW_PACKAGE_RECEIPT:path.join(temporary,'receipt.json'),NETCLAW_TEST_ROOT:root,NETCLAW_TEST_NODE:process.execPath},
    launchArgs:['--user-data-dir',user,'--extensions-dir',extensions,'--skip-welcome','--skip-release-notes','--disable-telemetry',...(name==='disabled'?['--disable-extension','NetClaw.netclaw']:[])]});
  assert.deepEqual(fs.readFileSync(fixture.configPath),baseline);assert.deepEqual(fs.readFileSync(path.join(fixture.home,'.env')),environment);
}
try{
  // A previous-candidate fixture, not a fictional previous public release.
  const previous=path.join(temporary,'previous');fs.mkdirSync(previous);
  for(const file of await listFiles({cwd:extension,packageManager:PackageManager.None})){const target=path.join(previous,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(path.join(extension,file),target);}
  fs.writeFileSync(path.join(previous,'package.json'),JSON.stringify({...manifest,version:'0.0.1',scripts:{}}));
  fs.copyFileSync(path.join(extension,'.vscodeignore'),path.join(previous,'.vscodeignore'));
  const old=path.join(temporary,'previous.vsix');
  await createVSIX({cwd:previous,packagePath:old,dependencies:false,readmePath:path.join(previous,'README.md'),changelogPath:path.join(previous,'CHANGELOG.md'),baseContentUrl:'https://github.com/automateyournetwork/netclaw/blob/150-vscode-extension-implementation/extensions/netclaw-vscode',baseImagesUrl:'https://raw.githubusercontent.com/automateyournetwork/netclaw/150-vscode-extension-implementation/extensions/netclaw-vscode'});
  await command(['--install-extension',old,'--force']);await phase('initial','0.0.1');
  await command(['--install-extension',current,'--force']);await phase('upgrade',manifest.version);
  await phase('disabled',manifest.version);
  await command(['--uninstall-extension','NetClaw.netclaw']);
  assert.ok(!(await command(['--list-extensions'])).stdout.toLowerCase().includes('netclaw.netclaw'));
  assert.deepEqual(fs.readFileSync(fixture.configPath),baseline);assert.deepEqual(fs.readFileSync(path.join(fixture.home,'.env')),environment);
  await command(['--install-extension',old,'--force']);await phase('rollback','0.0.1');
  await command(['--uninstall-extension','NetClaw.netclaw']);
  const report={passed:true,source:JSON.parse(fs.readFileSync(path.join(extension,'out/package.json'),'utf8')).source,sha256:createHash('sha256').update(fs.readFileSync(current)).digest('hex'),editor:'1.102.0',platform:process.platform,architecture:process.arch,phases:['clean candidate installation','upgrade 0.0.1 fixture to 0.1.0','disabled extension','uninstall','rollback and retained profile'],scope:'Actual VSIX and desktop editor, synthetic installation; no live owner service or WSL qualification.'};
  fs.writeFileSync(path.join(temporary,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({...report,report:path.join(temporary,'report.json')},null,2));
}finally{fixture.cleanup();}
