const vscode=require('vscode'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
exports.run=async()=>{
  const phase=process.env.NETCLAW_PACKAGE_PHASE,extension=vscode.extensions.getExtension('NetClaw.netclaw');
  if(phase==='disabled'){assert.ok(!extension||!extension.isActive);return;}
  assert.ok(extension,'Packaged extension discovered');
  assert.ok(extension.extensionPath.startsWith(process.env.NETCLAW_PACKAGE_EXTENSIONS),'Running the installed VSIX, not source development code');
  assert.equal(extension.packageJSON.version,process.env.NETCLAW_PACKAGE_VERSION);
  const api=await extension.activate(),f=JSON.parse(process.env.NETCLAW_PACKAGE_FIXTURE);
  let profile;
  if(phase==='initial'){
    assert.equal(api.profiles.list().length,0);
    profile=await api.profiles.save({label:'Retained package qualification',transport:'local',nodePath:process.env.NETCLAW_TEST_NODE,launcherPath:path.join(process.env.NETCLAW_TEST_ROOT,'scripts/netclaw-operator.mjs'),home:f.home,harness:f.kind,installationId:f.installationId});
    fs.writeFileSync(process.env.NETCLAW_PACKAGE_RECEIPT,JSON.stringify({profileId:profile.id,installationId:f.installationId}));
  }else{
    const receipt=JSON.parse(fs.readFileSync(process.env.NETCLAW_PACKAGE_RECEIPT,'utf8'));
    const all=api.profiles.list();assert.equal(all.length,1);profile=all[0];assert.equal(profile.id,receipt.profileId);assert.equal(profile.installationId,receipt.installationId);
  }
  const identity=await api.connection.connect(profile);assert.equal(identity.installationId,f.installationId);
  const settings=await api.connection.call('operator_snapshot',{domain:'settings'});assert.ok(settings.data.revision);
  await api.connection.disconnect();
};
