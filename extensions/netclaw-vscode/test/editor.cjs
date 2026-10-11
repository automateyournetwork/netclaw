const vscode=require('vscode');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
exports.run=async()=>{
  const extension=vscode.extensions.getExtension('NetClaw.netclaw');assert.ok(extension,'NetClaw extension discovered');
  const api=await extension.activate();assert.ok(extension.isActive,'extension activated');
  const commands=await vscode.commands.getCommands(true);for(const name of ['addConnection','selectConnection','disconnect','openOverview','prepareChange','reviewProposal'])assert.ok(commands.includes('netclaw.'+name));
  const fixtures=JSON.parse(process.env.NETCLAW_TEST_FIXTURES),root=process.env.NETCLAW_TEST_ROOT;
  const context=`${vscode.env.remoteName||'local'}:${os.hostname()}:${os.userInfo().uid}`;
  const profiles=[];let count=0;
  for(const fixture of fixtures){
    const profile=await api.profiles.save({label:'Same label',transport:'local',context,nodePath:process.env.NETCLAW_TEST_NODE,launcherPath:path.join(root,'scripts/netclaw-operator.mjs'),home:fixture.home,harness:fixture.kind,installationId:fixture.installationId});profiles.push(profile);
    const identity=await api.connection.connect(profile);assert.equal(identity.installationId,fixture.installationId);assert.equal(identity.harness.type,fixture.kind);count++;
    const response=await api.connection.call('operator_resources',{kind:'integration',limit:3});assert.equal(response.data.items.length,3);count++;
    assert.equal(api.connection.ready,true);
  }
  assert.equal(api.profiles.list().length,2,JSON.stringify({saved:profiles.map(p=>({id:p.id,context:p.context})),listed:api.profiles.list().map(p=>({id:p.id,context:p.context}))}));assert.notEqual(profiles[0].id,profiles[1].id);
  await assert.rejects(api.connection.connect({...profiles[0],installationId:fixtures[1].installationId}));count++;
  await api.connection.connect(profiles[0]);
  const initialOperations=(await api.connection.call('operator_resources',{kind:'overview'})).data.operations.length;
  await vscode.commands.executeCommand('netclaw.openOverview');count++;
  const rendered=[];
  if(process.env.NETCLAW_TEST_CDP_PORT){
    const {chromium}=require(process.env.NETCLAW_TEST_PLAYWRIGHT);
    const browser=await chromium.connectOverCDP('http://127.0.0.1:'+process.env.NETCLAW_TEST_CDP_PORT);
    try{
      const page=browser.contexts()[0].pages()[0];fs.mkdirSync(process.env.NETCLAW_TEST_SCREENSHOTS,{recursive:true});
      async function frameFor(selector){
        for(let attempt=0;attempt<80;attempt++){for(const frame of page.frames()){try{if(!frame.isDetached()&&await frame.locator(selector).count())return frame;}catch(error){if(!frame.isDetached())throw error;}}await new Promise(resolve=>setTimeout(resolve,100));}
        throw Error('Webview did not render '+selector);
      }
      await vscode.commands.executeCommand('netclaw.openChat');
      const chat=await frameFor('#composer');await chat.locator('#prompt').fill('An unsent draft');
      assert.equal(await chat.locator('#send').textContent(),'Send to NetClaw');rendered.push('Chat composer');
      await page.screenshot({path:path.join(process.env.NETCLAW_TEST_SCREENSHOTS,'chat.png')});
      await vscode.commands.executeCommand('netclaw.openCanvas');
      const canvas=await frameFor('.canvas-lane');await canvas.getByRole('button',{name:'Branch this conversation'}).first().click();
      assert.equal(await canvas.locator('.canvas-lane').count(),2);rendered.push('Canvas branch without dispatch');
      await page.screenshot({path:path.join(process.env.NETCLAW_TEST_SCREENSHOTS,'canvas.png')});
      await vscode.commands.executeCommand('netclaw.openAvatar');
      const avatar=await frameFor('#avatar-character');await avatar.locator('#avatar-character').selectOption('lobster');
      assert.equal(await avatar.locator('#prompt').count(),1);rendered.push('Existing local Avatar and independent text composer');
      await page.screenshot({path:path.join(process.env.NETCLAW_TEST_SCREENSHOTS,'avatar.png')});
      await vscode.commands.executeCommand('netclaw.openRag');
      const rag=await frameFor('#rag-search');assert.match(await rag.locator('h1').textContent(),/RAG/);
      if(process.env.NETCLAW_TEST_REAL_RAG==='1'){
        await rag.locator('#documents').getByRole('heading',{name:'editor-qualification.md'}).waitFor({timeout:30000});
        await rag.locator('#query').fill('When is the lab change window?');await rag.getByRole('button',{name:'Search knowledge'}).click();
        await rag.locator('#results article').first().waitFor({timeout:60000});
        assert.match(await rag.locator('#results').textContent(),/violet Thursday/);assert.match(await rag.locator('#results').textContent(),/ingested/);
        rendered.push('RAG collection and cited retrieval through real cached local embeddings');
      }else rendered.push('RAG panel entry point; backend retrieval not exercised');
      await page.screenshot({path:path.join(process.env.NETCLAW_TEST_SCREENSHOTS,'rag.png')});
      const operations=await api.connection.call('operator_resources',{kind:'overview'});assert.equal(operations.data.operations.length,initialOperations);rendered.push('No backend dispatch from opening views, draft text, branching or retrieval');count+=5;
    }finally{await browser.close();}
  }
  await api.connection.disconnect();assert.equal(api.connection.ready,false);count++;
  await assert.rejects(api.connection.call('operator_identity'));count++;
  for(const profile of profiles)await api.profiles.remove(profile.id);
  fs.writeFileSync(process.env.NETCLAW_TEST_REPORT,JSON.stringify({editor:vscode.version,platform:process.platform,architecture:process.arch,osRelease:os.release(),extensionVersion:extension.packageJSON.version,backendNode:process.env.NETCLAW_TEST_NODE,assertionGroups:count,rendered,screenshots:process.env.NETCLAW_TEST_SCREENSHOTS,passed:true}));
};
