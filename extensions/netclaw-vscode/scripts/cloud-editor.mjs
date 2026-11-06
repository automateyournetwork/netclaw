import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import net from 'node:net';
import { once } from 'node:events';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

// Private operator-created config and tickets only; never credentials on argv.
const config = process.env.NETCLAW_CLOUD_CONFIG, executable = process.env.VSCODE_EXECUTABLE;
if (!config || !executable || !process.env.NETCLAW_TEST_PLAYWRIGHT) throw Error('Supply private NETCLAW_CLOUD_CONFIG, VSCODE_EXECUTABLE and NETCLAW_TEST_PLAYWRIGHT paths.');
const stat = fs.lstatSync(config);
if (!stat.isFile() || stat.isSymbolicLink() || stat.uid !== process.getuid() || stat.mode & 0o077) throw Error('Cloud test config must be an owned private file.');
const scenario = process.env.NETCLAW_CLOUD_SCENARIO || 'single';
if (!['single', 'combined', 'federation'].includes(scenario)) throw Error('Unknown native cloud scenario.');
const extension = fileURLToPath(new URL('../', import.meta.url));
const root = process.env.NETCLAW_CLOUD_EDITOR_PROFILE || fs.mkdtempSync(path.join(os.tmpdir(), 'netclaw-cloud-editor-'));
fs.mkdirSync(root, { recursive: true, mode: 0o700 });
const rootStat = fs.lstatSync(root);
if (!rootStat.isDirectory() || rootStat.isSymbolicLink() || rootStat.uid !== process.getuid() || rootStat.mode & 0o077) throw Error('Editor evidence/profile directory must be private and owned.');
const driver = path.join(root, 'observer'), user = process.env.NETCLAW_CLOUD_EDITOR_USER || path.join(root, 'user'), report = path.join(root, 'result-' + Date.now() + '.json');
if (process.env.NETCLAW_CLOUD_EDITOR_USER) { const state = fs.lstatSync(user); if (!path.isAbsolute(user) || !state.isDirectory() || state.isSymbolicLink() || state.uid !== process.getuid() || state.mode & 0o077) throw Error('Retained qualification user data must be an existing private directory.'); }
fs.mkdirSync(driver, { recursive: true }); fs.mkdirSync(path.join(user, 'User'), { recursive: true });
if (!fs.existsSync(path.join(user, 'User/settings.json'))) fs.writeFileSync(path.join(user, 'User/settings.json'), JSON.stringify({ 'telemetry.telemetryLevel': 'off', 'update.mode': 'none', 'extensions.autoUpdate': false, 'workbench.startupEditor': 'none', 'window.dialogStyle': 'custom', 'security.workspace.trust.enabled': true, 'security.workspace.trust.startupPrompt': 'never' }));
fs.writeFileSync(path.join(driver, 'package.json'), JSON.stringify({ name: 'netclaw-cloud-owner-observer', publisher: 'fixture', version: '0.0.0', engines: { vscode: '^1.109.0' }, activationEvents: ['onStartupFinished'], main: 'index.cjs' }));
const testFile = scenario === 'federation' ? 'test/editor-federation.cjs' : scenario === 'combined' ? 'test/editor-combined.cjs' : 'test/editor-cloud.cjs';
fs.writeFileSync(path.join(driver, 'index.cjs'), `const vscode=require('vscode'), fs=require('node:fs'); exports.activate=()=>setImmediate(async()=>{try{await require(${JSON.stringify(path.join(extension, testFile))}).run();}catch(e){let prior={};try{prior=JSON.parse(fs.readFileSync(${JSON.stringify(report)},'utf8'));}catch{}fs.writeFileSync(${JSON.stringify(report)},JSON.stringify({...prior,complete:false,error:String(e.message||'Cloud qualification failed'),stack:String(e.stack||'')}),{mode:0o600});}finally{await vscode.commands.executeCommand('workbench.action.quit');}});`);
const listener = net.createServer(); listener.listen(0, '127.0.0.1'); await once(listener, 'listening');
const port = listener.address().port; await new Promise(resolve => listener.close(resolve));
const child = spawn(executable, ['--user-data-dir', user, '--extensions-dir', path.join(root, 'extensions'), '--extensionDevelopmentPath=' + extension, '--extensionDevelopmentPath=' + driver,
  '--skip-welcome', '--skip-release-notes', '--disable-telemetry', '--remote-debugging-port=' + port], {
  env: { ...process.env, SHELL: '/bin/bash', ELECTRON_RUN_AS_NODE: undefined, NETCLAW_CLOUD_CONFIG: path.resolve(config), NETCLAW_TEST_REPORT: report, NETCLAW_TEST_CDP_PORT: String(port) }, stdio: 'ignore',
});
const timer = setTimeout(() => child.kill(), 360000);
const [code, signal] = await once(child, 'exit'); clearTimeout(timer);
if (signal || code !== 0 || !fs.existsSync(report)) throw Error('Cloud editor did not confirm completion. Preserve its profile and recover; do not repeat execution.');
const result = JSON.parse(fs.readFileSync(report, 'utf8'));
console.log(JSON.stringify({ complete: result.complete === true, mode: result.mode, editor: result.editor, profile: root, report }));
if (result.complete !== true) process.exitCode = 1;
