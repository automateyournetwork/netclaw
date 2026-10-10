// Real-browser smoke against serve_browser_fixture.py; never use an owner HUD.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {execFileSync}=require('node:child_process');
const path=require('node:path');
const url = process.env.HUD_TEST_URL || 'http://localhost:34010';
if (!/^http:\/\/(localhost|127\.0\.0\.1):34010$/.test(url)) throw Error('Use the dedicated controlled fixture on port 34010.');
if(process.env.HUD_UPGRADE_REPO && fs.realpathSync(process.env.HUD_UPGRADE_REPO)===fs.realpathSync(path.join(__dirname,'../..')))throw Error('Upgrade acceptance requires a separate owned test checkout.');
const report = {platform:process.platform, checks:[], errors:[]};
(async()=>{
  const browser=await chromium.launch({headless:true, executablePath:process.env.BROWSER_EXECUTABLE || undefined});
  report.browser=browser.version();
  try {
    const context=await browser.newContext();context.setDefaultTimeout(15000);
    const page=await context.newPage();
    page.on('pageerror',e=>report.errors.push(e.message));
    const requests=[];
    page.on('request',r=>{if(r.method()==='POST')requests.push({url:r.url(),body:r.postData()});});
    await page.goto(url);
    await page.locator('#standard-chat-message').waitFor();
    const runtime=await page.evaluate(()=>fetch('/api/runtime').then(r=>r.json()));
    assert.equal(runtime.kind,'hermes'); assert.equal(runtime.readiness.ready,true);
    assert.ok(runtime.readiness.tools.some(t=>t.includes('subnet_calculator')));
    await page.getByText('Hermes ready',{exact:true}).waitFor();
    report.checks.push('Browser loopback, protected selected runtime and truthful Hermes ready badge');
    async function send(message) {
      await page.locator('#standard-chat-message').fill(message);
      const admission=page.waitForResponse(r=>r.url().endsWith('/api/chat/requests') && r.request().method()==='POST');
      await page.getByRole('button',{name:'Send message',exact:true}).click();
      assert.equal((await admission).status(),202);
      await page.waitForFunction(()=>document.querySelector('.chat-composer textarea')?.disabled===false,null,{timeout:60000});
      assert.equal(await page.locator('#standard-chat-message').inputValue(),'');
    }
    await send('remember violet');
    await send('what was the colour?');
    assert.match(await page.locator('.chat-transcript').innerText(),/violet/);
    const before=requests.filter(r=>/\/api\/(chat\/requests|chat|pal\/sessions)$/.test(r.url)).length;
    await page.locator('#standard-chat-message').fill('preserved browser draft');
    await page.getByRole('button',{name:'Avatar',exact:true}).click();
    await page.locator('[aria-label="Avatar selection"]').waitFor();
    await page.getByRole('button',{name:/Lobster/}).click();
    await page.getByRole('button',{name:'Chat',exact:true}).click();
    assert.equal(await page.locator('#standard-chat-message').inputValue(),'preserved browser draft');
    assert.equal(requests.filter(r=>/\/api\/(chat\/requests|chat|pal\/sessions)$/.test(r.url)).length,before);
    report.checks.push('Contextual Chat and local Avatar switch preserve draft without inference');
    await send('SUBNET'); await send('continue'); await send('finish');
    const conversations=await page.evaluate(()=>fetch('/api/chat/conversations').then(r=>r.json()));
    assert.equal(conversations.conversations.length,1);
    const id=conversations.conversations[0].id;
    const foreign=await browser.newContext(); const other=await foreign.newPage();await other.goto(url);
    await other.locator('#standard-chat-message').waitFor();
    const denied=await other.evaluate(async id=>{await fetch('/api/hud/session',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});return (await fetch('/api/chat/conversations/'+id+'/open',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status;},id);
    assert.equal(denied,404);await foreign.close();
    await page.reload();await page.locator('#standard-chat-message').waitFor();
    const restored=await page.evaluate(id=>fetch('/api/chat/conversations/'+id+'/open',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}).then(r=>r.json()),id);
    assert.equal(restored.messages.length,10);
    report.checks.push('Five turns, owned history after refresh, second browser profile denied');
    const rejected=await page.evaluate(async()=>{
      const call=(route,body,headers={})=>fetch(route,{method:'POST',headers:{'Content-Type':'application/json',...headers},body:JSON.stringify(body)}).then(r=>r.status);
      return {
        attachment:await call('/api/chat/requests',{hudThread:'attachment-test',message:'do not send',attachments:[{name:'test.txt'}]}),
        stale:await call('/api/chat/requests',{hudThread:'stale-test',message:'do not send'},{'X-NetClaw-Installation':'different-installation'}),
        legacy:(await fetch('/api/sessions')).status,
      };
    });
    assert.deepEqual(rejected,{attachment:400,stale:409,legacy:404});
    const cookies=await context.cookies();assert.ok(cookies.some(c=>c.httpOnly));
    assert.ok(!JSON.stringify(await page.evaluate(()=>({local:{...localStorage},session:{...sessionStorage}}))).includes('fixture-only-key'));
    assert.ok(!requests.some(r=>/8645/.test(r.url)||/fixture-only-key/.test(r.body||'')));
    report.checks.push('Attachment/stale-installation/legacy routes denied; private cookie; no fixture provider key in browser');
    await page.getByRole('button',{name:'Canvas',exact:true}).click();
    const frame=page.frameLocator('iframe');await frame.locator('body').waitFor();
    const lanes=frame.locator('.lane-in');
    await lanes.first().locator('input[data-composer="1"]').waitFor();
    async function canvasSend(index, message) {
      const lane=lanes.nth(index);
      const input=lane.locator('input[data-composer="1"]');
      await input.fill(message);
      const admitted=page.waitForResponse(r=>r.url().endsWith('/api/chat/requests') && r.request().method()==='POST');
      await input.press('Enter');
      assert.equal((await admitted).status(),202);
      await lane.getByText(/^HERMES FIXTURE violet/).last().waitFor({timeout:60000});
      await lane.locator('[title="thinking…"]').waitFor({state:'detached',timeout:60000});
    }
    async function selectAnswer(index) {
      await lanes.nth(index).getByText(/^HERMES FIXTURE violet/).last().evaluate(el=>{
        const range=document.createRange();range.selectNodeContents(el);
        const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);
        el.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));
      });
    }
    await canvasSend(0,'remember violet CANVAS_ROOT_INITIAL');
    await selectAnswer(0);await frame.getByRole('button',{name:'⎇ Branch this →',exact:true}).click();
    await lanes.nth(1).getByTitle('expand',{exact:true}).click();
    await canvasSend(0,'CANVAS_PARENT_LATER');
    await selectAnswer(0);await frame.getByRole('button',{name:'⎇ Branch this →',exact:true}).click();
    await lanes.nth(2).getByTitle('expand',{exact:true}).click();
    await canvasSend(1,'CANVAS_CHILD_ONE');
    await canvasSend(2,'CANVAS_CHILD_TWO');
    const firstChild=JSON.parse(requests.find(r=>r.url.endsWith('/api/chat/requests') && JSON.parse(r.body).message?.includes('CANVAS_CHILD_ONE')).body);
    const secondChild=JSON.parse(requests.find(r=>r.url.endsWith('/api/chat/requests') && JSON.parse(r.body).message?.includes('CANVAS_CHILD_TWO')).body);
    assert.ok(JSON.stringify(firstChild.messages).includes('CANVAS_ROOT_INITIAL'));
    assert.ok(!JSON.stringify(firstChild.messages).includes('CANVAS_PARENT_LATER'));
    assert.ok(JSON.stringify(secondChild.messages).includes('CANVAS_PARENT_LATER'));
    assert.ok(!JSON.stringify(secondChild.messages).includes('CANVAS_CHILD_ONE'));
    await lanes.nth(1).locator('input[data-composer="1"]').fill('saved Canvas draft');
    await selectAnswer(1);await frame.getByRole('button',{name:'❝ Quote as context',exact:true}).click();
    // Poll from Node: this browser transport may return an unresolved predicate
    // Promise as truthy from waitForFunction; inspect the actual IDB rows instead.
    const saved = async () => page.evaluate(async()=>{
      for(const {name} of await indexedDB.databases()) {
        if(!name.startsWith('netclaw.hermes.') || !name.endsWith('.netclaw-canvas'))continue;
        const rows=await new Promise((resolve,reject)=>{
          const open=indexedDB.open(name);open.onerror=()=>reject(open.error);
          open.onsuccess=()=>{const db=open.result;const req=db.transaction('sessions').objectStore('sessions').getAll();req.onsuccess=()=>{db.close();resolve(req.result);};req.onerror=()=>{db.close();reject(req.error);};};
        });
        if(rows.some(row=>Object.values(row.drafts||{}).includes('saved Canvas draft') && Object.values(row.quotes||{}).some(q=>q.includes('HERMES FIXTURE violet')) && row.nodes.length===3))return true;
      }
      return false;
    });
    const saveDeadline=Date.now()+15000;
    while(!await saved() && Date.now()<saveDeadline)await new Promise(r=>setTimeout(r,100));
    assert.equal(await saved(),true,'Canvas autosave must settle before refresh');
    await page.reload();await page.getByRole('button',{name:'Canvas',exact:true}).click();
    await frame.locator('input[data-composer="1"]').first().waitFor();
    assert.equal(await lanes.count(),3);
    await lanes.nth(1).locator('input[data-composer="1"]').evaluate(el=>el.scrollIntoView());
    report.canvasRestoredDrafts=await frame.locator('input[data-composer="1"]').evaluateAll(els=>els.map(el=>el.value));
    assert.equal(await lanes.nth(1).locator('input[data-composer="1"]').inputValue(),'saved Canvas draft');
    assert.ok((await lanes.nth(1).innerText()).includes('HERMES FIXTURE violet'));
    assert.deepEqual(report.errors,[]);
    report.checks.push('Canvas two branch creation-point contexts exclude later parent/sibling messages; graph and draft survive refresh');
    // Unsupported files remain locally attached; no admission leaves the browser.
    const postsBeforeAttachment=requests.filter(r=>r.url.endsWith('/api/chat/requests')).length;
    await lanes.nth(1).locator('input[type=file]').setInputFiles({name:'acceptance.txt',mimeType:'text/plain',buffer:Buffer.from('synthetic attachment')});
    await lanes.nth(1).locator('input[data-composer="1"]').press('Enter');
    await lanes.nth(1).getByText(/Attachments are unavailable/).waitFor();
    assert.equal(await lanes.nth(1).locator('input[data-composer="1"]').inputValue(),'saved Canvas draft');
    assert.match(await lanes.nth(1).innerText(),/acceptance.txt/);
    assert.equal(requests.filter(r=>r.url.endsWith('/api/chat/requests')).length,postsBeforeAttachment);
    report.checks.push('Unsupported Canvas attachment preserves draft, quote and file without admission');
    const metadata=process.env.HUD_FIXTURE_METADATA && JSON.parse(fs.readFileSync(process.env.HUD_FIXTURE_METADATA));
    if(process.env.HUD_UPGRADE_REPO && metadata) {
      const env={...process.env,NETCLAW_RUNTIME:'hermes',HERMES_HOME:metadata.home};
      for(const mode of ['--check','--apply','--apply']) {
        execFileSync('bash',[process.env.HUD_UPGRADE_REPO+'/scripts/upgrade-hud.sh',mode,'--repo',process.env.HUD_UPGRADE_REPO],{env,timeout:120000,maxBuffer:8*1024*1024});
      }
      await page.reload();await page.getByRole('button',{name:'Canvas',exact:true}).click();
      await lanes.nth(1).locator('input[data-composer="1"]').waitFor();
      assert.equal(await lanes.nth(1).locator('input[data-composer="1"]').inputValue(),'saved Canvas draft');
      assert.match(await lanes.nth(1).innerText(),/acceptance.txt/);
      assert.equal(await lanes.count(),3);
      report.checks.push('Actual upgrade check and repeated apply preserve browser graph, draft, quote and attachment on the same origin');
      // Exercise the prior HUD source with the saved workspace, then restore
      // the candidate. This temporary checkout is owned by the test fixture.
      if(process.env.HUD_ROLLBACK_REF) {
        const file=process.env.HUD_UPGRADE_REPO+'/ui/netclaw-visual/src/dashboard/Dashboard.jsx';
        const candidate=fs.readFileSync(file);
        try {
          fs.writeFileSync(file,execFileSync('git',['-C',process.env.HUD_UPGRADE_REPO,'show',process.env.HUD_ROLLBACK_REF+':ui/netclaw-visual/src/dashboard/Dashboard.jsx']));
          await page.reload();await page.getByRole('button',{name:'Canvas',exact:true}).click();
          await lanes.nth(1).locator('input[data-composer="1"]').waitFor();
          assert.equal(await lanes.nth(1).locator('input[data-composer="1"]').inputValue(),'saved Canvas draft');
          assert.equal(await lanes.count(),3);
          assert.match(await lanes.nth(1).innerText(),/acceptance.txt/);
        } finally {fs.writeFileSync(file,candidate);}
        await page.reload();await page.getByRole('button',{name:'Canvas',exact:true}).click();
        await lanes.nth(1).locator('input[data-composer="1"]').waitFor();
        assert.equal(await lanes.nth(1).locator('input[data-composer="1"]').inputValue(),'saved Canvas draft');
        report.checks.push('Prior Mac HUD dashboard rollback/reapply preserves saved Canvas graph, draft, quote and file');
      }
    }
    const inferenceCount=async()=>metadata?(await (await fetch(metadata.provider+'/__fixture/count')).json()).inferences:null;
    const beforePanels=await inferenceCount();
    await page.getByRole('button',{name:'Advanced',exact:true}).click();
    for(const label of ['Settings','Configuration','Tokenomics','Integrations','External neighbours']) {
      await page.locator('nav').getByRole('button',{name:new RegExp(label)}).click();
      await page.getByRole('heading',{name:new RegExp('^'+label+'\\.$')}).waitFor();
    }
    assert.equal(await inferenceCount(),beforePanels);
    await page.locator('nav').getByRole('button',{name:/Settings/}).click();
    await page.getByText('Hermes', {exact:true}).first().waitFor();
    report.checks.push('Selected-runtime settings/configuration/usage/catalogue/federation panels perform zero inference');
    await page.getByRole('button',{name:'Chat',exact:true}).click();
    // Switching the observed installation while this tab is open must fence sends.
    const postsBeforeSwitch=requests.filter(r=>r.url.endsWith('/api/chat/requests')).length;
    await page.route('**/api/runtime',route=>route.fulfill({json:{...runtime,installationId:'33333333-3333-4333-8333-333333333333'}}));
    await page.locator('#standard-chat-message').fill('preserve on runtime switch');
    await page.getByRole('button',{name:'Send message',exact:true}).click();
    await page.getByRole('alert').filter({hasText:'selected runtime changed'}).waitFor();
    assert.equal(await page.locator('#standard-chat-message').inputValue(),'preserve on runtime switch');
    assert.equal(requests.filter(r=>r.url.endsWith('/api/chat/requests')).length,postsBeforeSwitch);
    await page.unroute('**/api/runtime');
    report.checks.push('Changed runtime identity refuses stale-tab submission and retains draft (controlled identity response)');
    if(metadata) {
      await page.locator('#standard-chat-message').fill('WAIT_FOR_TEST browser pending stop');
      const admission=page.waitForResponse(r=>r.url().endsWith('/api/chat/requests') && r.request().method()==='POST');
      await page.getByRole('button',{name:'Send message',exact:true}).click();
      assert.equal((await admission).status(),202);
      const admittedCount=requests.filter(r=>r.url.endsWith('/api/chat/requests')).length;
      await page.reload();await page.getByRole('button',{name:'Check status',exact:true}).waitFor();
      assert.equal(requests.filter(r=>r.url.endsWith('/api/chat/requests')).length,admittedCount);
      await page.getByRole('button',{name:'Request stop',exact:true}).click();
      await fetch(metadata.provider+'/__fixture/release',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
      await page.getByRole('button',{name:'Check status',exact:true}).click();
      await page.waitForFunction(()=>document.querySelector('.chat-composer textarea')?.disabled===false,null,{timeout:60000});
      assert.equal(requests.filter(r=>r.url.endsWith('/api/chat/requests')).length,admittedCount);
      report.checks.push('Actual pending browser refresh and cooperative stop recover status with zero replay');
    }
    assert.deepEqual(report.errors,[]);
    report.passed=true;
  } catch(e) {report.passed=false;report.failure=e.stack;process.exitCode=1;}
  finally {await browser.close();fs.writeFileSync(process.env.HUD_BROWSER_REPORT || 'browser-report.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));}
})().catch(e=>{console.error(e);process.exitCode=1;});
