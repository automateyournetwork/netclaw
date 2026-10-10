// Explicit live OpenClaw regression on the isolated HUD using the existing gateway.
// Requires operator authorization for provider calls; never points at port 3000.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
if(process.env.NETCLAW_LIVE_ACCEPTANCE!=='1')throw Error('Explicit live acceptance authorization required.');
const report={platform:process.platform,kind:'openclaw',checks:[],errors:[]};
(async()=>{
 const browser=await chromium.launch({headless:true});report.browser=browser.version();
 try {
  const context=await browser.newContext();context.setDefaultTimeout(20000);
  const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));
  const admissions=[];page.on('request',r=>{if(r.method()==='POST' && r.url().endsWith('/api/chat'))admissions.push(r.postDataJSON());});
  await page.goto('http://127.0.0.1:34020');await page.locator('#standard-chat-message').waitFor();
  const runtime=await page.evaluate(()=>fetch('/api/runtime').then(r=>r.json()));assert.equal(runtime.kind,'openclaw');
  await page.locator('#standard-chat-model').selectOption({label:'anthropic/claude-sonnet-4-6'});
  async function send(text){
   await page.locator('#standard-chat-message').fill(text);
   const pending=page.waitForResponse(r=>r.url().endsWith('/api/chat') && r.request().method()==='POST',{timeout:180000});
   await page.getByRole('button',{name:'Send message',exact:true}).click();
   const value=await (await pending).json();assert.equal(value.fromGateway,true);
   await page.waitForFunction(()=>!document.querySelector('#standard-chat-message').disabled);
   return value;
  }
  await send('HUD acceptance only, no tools or device access. Remember colour violet. Reply briefly.');
  assert.match((await send('What colour did I ask you to remember? Reply with one word, no tools.')).response,/violet/i);
  const count=admissions.length;
  await page.locator('#standard-chat-message').fill('OpenClaw saved draft');
  await page.getByRole('button',{name:'Avatar',exact:true}).click();
  await page.locator('[aria-label="Avatar selection"]').waitFor();
  await page.getByRole('button',{name:'Chat',exact:true}).click();
  assert.equal(await page.locator('#standard-chat-message').inputValue(),'OpenClaw saved draft');assert.equal(admissions.length,count);
  await page.reload();await page.locator('#standard-chat-message').waitFor();
  assert.match(await page.locator('.chat-transcript').innerText(),/violet/i);
  assert.equal(await page.locator('#standard-chat-message').inputValue(),'OpenClaw saved draft');
  const history=await page.evaluate(()=>fetch('/api/chat/conversations').then(r=>r.json()));assert.equal(history.sourceAvailable,true);assert.ok(history.conversations.length);
  report.checks.push('Live model selection, two contextual turns, local Avatar without inference, saved draft and owned history after refresh');
  await page.getByRole('button',{name:'Canvas',exact:true}).click();
  const frame=page.frameLocator('iframe'),lanes=frame.locator('.lane-in');
  await lanes.first().locator('input[data-composer="1"]').waitFor();
  async function canvas(index,text){
   const response=page.waitForResponse(r=>r.url().endsWith('/api/chat') && r.request().method()==='POST',{timeout:180000});
   await lanes.nth(index).locator('input[data-composer="1"]').fill(text);await lanes.nth(index).locator('input[data-composer="1"]').press('Enter');
   const value=await (await response).json();assert.equal(value.fromGateway,true);
   assert.match(value.response,/violet/i);
   await lanes.nth(index).locator('[title="thinking…"]').waitFor({state:'detached',timeout:180000});
  }
  await canvas(0,'HUD acceptance only. No tools, files or devices. Remember violet. Reply exactly CANVAS_OPENCLAW_VIOLET.');
  const answer=lanes.first().getByText(/violet/i).last();await answer.waitFor();
  await answer.evaluate(el=>{const range=document.createRange();range.selectNodeContents(el);const s=window.getSelection();s.removeAllRanges();s.addRange(range);el.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));});
  await frame.getByRole('button',{name:'⎇ Branch this →',exact:true}).click();await lanes.nth(1).getByTitle('expand',{exact:true}).click();
  await canvas(1,'Which colour is in the parent answer? Reply briefly without tools.');
  assert.match(await lanes.nth(1).innerText(),/violet/i);
  report.checks.push('Live OpenClaw Canvas parent and independent child preserve quoted parent context');
  await page.getByRole('button',{name:'Advanced',exact:true}).click();
  const before=admissions.length;
  for(const label of ['Settings','Configuration','Tokenomics','Integrations']){await page.locator('nav').getByRole('button',{name:new RegExp(label)}).click();await page.getByRole('heading',{name:new RegExp('^'+label+'\\.$')}).waitFor();}
  assert.equal(admissions.length,before);assert.deepEqual(report.errors,[]);
  report.checks.push('Existing OpenClaw panels render without chat dispatch or browser exception');
  report.passed=true;
 }catch(e){report.passed=false;report.failure=e.stack;process.exitCode=1;}
 finally{await browser.close();fs.writeFileSync(process.env.HUD_BROWSER_REPORT || 'openclaw-browser-report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));}
})().catch(e=>{console.error(e);process.exitCode=1;});
