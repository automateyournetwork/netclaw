import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';

for (const failure of ['launch', 'page', 'close', 'server-launch', 'connect', 'server-page', 'server-close', 'connect-and-close']) {
  test(`browser fixture releases manager and exits after injected ${failure} failure`, { timeout: 10000 }, t => {
    const root = mkdtempSync(join(resolve(process.env.NETCLAW_TEST_TMP || '.spec200-local/tests'), 'browser-cleanup-'));
    t.after(() => rmSync(root, { recursive: true, force: true }));
    const owned = join(root, 'owned');
    mkdirSync(owned, { mode: 0o700 });
    const script = join(root, 'probe.test.mjs');
    const helper = new URL('./browser-fixture.mjs', import.meta.url).href;
    writeFileSync(script, `
import test from 'node:test';
import { writeFileSync } from 'node:fs';
import { createBrowserFixture } from ${JSON.stringify(helper)};
test('injected browser failure', async t => {
  const serverMode = ${JSON.stringify(failure)}.startsWith('server-') || ${JSON.stringify(failure)}.startsWith('connect');
  const fakeBrowser = { newPage: async () => { throw new Error('injected-${failure}'); } };
  const { browser } = await createBrowserFixture(t, 'fixture-', {
    ...(serverMode ? {
      launchServer: async () => {
        if (${JSON.stringify(failure)} === 'server-launch') throw new Error('injected-server-launch');
        return {
          wsEndpoint: () => 'fixture-endpoint',
          close: async () => {
            writeFileSync(${JSON.stringify(join(root, 'server-closed'))}, 'closed');
            if (['server-close', 'connect-and-close'].includes(${JSON.stringify(failure)})) throw new Error('injected-${failure}');
          }
        };
      },
      connect: async () => {
        if (${JSON.stringify(failure)}.startsWith('connect')) throw new Error('injected-${failure}');
        return fakeBrowser;
      }
    } : {}),
    launch: async () => {
    if (${JSON.stringify(failure)} === 'launch') throw new Error('injected-launch');
    return {
      newPage: async () => { throw new Error('injected-page'); },
      close: async () => { if (${JSON.stringify(failure)} === 'close') throw new Error('injected-close'); }
    };
  }});
  if (['page', 'server-page'].includes(${JSON.stringify(failure)})) await browser.newPage();
});
`, { mode: 0o600 });
    const env = { ...process.env, NETCLAW_TEST_TMP: owned };
    delete env.NODE_TEST_CONTEXT; // Independent runner, not a recursive node:test worker.
    const result = spawnSync(process.execPath, ['--test', '--test-isolation=none', script], {
      env, encoding: 'utf8', timeout: 4000,
    });
    if (process.env.NETCLAW_BROWSER_EVIDENCE) {
      mkdirSync(process.env.NETCLAW_BROWSER_EVIDENCE, { recursive: true, mode: 0o700 });
      writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE, `cleanup-${failure}.log`),
        result.stdout + result.stderr, { mode: 0o600 });
    }
    assert.equal(result.error, undefined, `child must exit without timeout: ${result.error}`);
    assert.equal(result.signal, null);
    assert.equal(result.status, 1, 'original injected failure must remain visible');
    assert.match(result.stdout, new RegExp(`injected-${failure}`));
    assert.deepEqual(readdirSync(owned), [], 'all owned manager state removed after teardown');
    if (['connect', 'server-page', 'server-close', 'connect-and-close'].includes(failure))
      assert(readdirSync(root).includes('server-closed'), 'acquired server was closed even after failed connect');
  });
}

for (const scenario of ['receipt recovery: final_response_loss', 'final recorder flush during manager shutdown: 0ms', 'recording failure: constructor']) {
  test(`recording harness exits after launch failure: ${scenario}`, { timeout: 10000 }, t => {
    const root = mkdtempSync(join(resolve(process.env.NETCLAW_TEST_TMP || '.spec200-local/tests'), 'recording-cleanup-'));
    t.after(() => rmSync(root, { recursive: true, force: true }));
    const env = { ...process.env, NETCLAW_TEST_TMP: root, NETCLAW_BROWSER_EXECUTABLE: join(root, 'missing-chrome') };
    delete env.NODE_TEST_CONTEXT;
    const result = spawnSync(process.execPath, ['--test', '--test-isolation=none', `--test-name-pattern=${scenario}`,
      new URL('./recording.test.mjs', import.meta.url).pathname], { env, encoding: 'utf8', timeout: 4000 });
    if (process.env.NETCLAW_BROWSER_EVIDENCE) writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE,
      `recording-cleanup-${scenario.split(':')[0].replaceAll(' ', '-')}.log`), result.stdout + result.stderr, { mode: 0o600 });
    assert.equal(result.error, undefined, `child must exit without timeout: ${result.error}`);
    assert.equal(result.signal, null);
    assert.equal(result.status, 1);
    assert.match(result.stdout, /executable doesn't exist/);
    assert.deepEqual(readdirSync(root), [], 'failed launch must remove manager state');
  });
}

for (const failure of ['launch', 'page']) {
  test(`member browser harness exits after ${failure} failure`, { timeout: 10000 }, t => {
    const root = mkdtempSync(join(resolve(process.env.NETCLAW_TEST_TMP || '.spec200-local/tests'), 'member-cleanup-'));
    t.after(() => rmSync(root, { recursive: true, force: true }));
    const owned = join(root, 'owned');
    mkdirSync(owned, { mode: 0o700 });
    const preload = join(root, 'fault.mjs');
    const playwright = new URL('../../scripts/genie-worlds/node_modules/playwright-core/index.mjs', import.meta.url).href;
    writeFileSync(preload, `
import { chromium } from ${JSON.stringify(playwright)};
import { writeFileSync } from 'node:fs';
chromium.launch = async () => {
  if (${JSON.stringify(failure)} === 'launch') throw new Error('injected-member-launch');
  return {
    newPage: async () => { throw new Error('injected-member-page'); },
    close: async () => writeFileSync(${JSON.stringify(join(root, 'browser-closed'))}, 'closed'),
  };
};
`, { mode: 0o600 });
    const env = { ...process.env, NETCLAW_TEST_TMP: owned,
      NETCLAW_BROWSER_EXECUTABLE: 'synthetic-no-launch', NETCLAW_MCP_PYTHON: process.execPath };
    delete env.NODE_TEST_CONTEXT;
    delete env.NETCLAW_TEST_SNAPSHOT_REGISTRY;
    delete env.NETCLAW_BROWSER_EVIDENCE;
    // Exercise setup once: suite growth must not accumulate one shutdown grace
    // per evidence scenario under this single bounded child-process deadline.
    const result = spawnSync(process.execPath, ['--import', preload, '--test', '--test-isolation=none',
      '--test-name-pattern=^actual Chrome/stdio MCP original-ID evidence: none$',
      new URL('./member-browser.test.mjs', import.meta.url).pathname], { env, encoding: 'utf8', timeout: 4000 });
    if (process.env.NETCLAW_BROWSER_EVIDENCE) {
      mkdirSync(process.env.NETCLAW_BROWSER_EVIDENCE, { recursive: true, mode: 0o700 });
      writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE, `member-cleanup-${failure}.log`),
        JSON.stringify({ status: result.status, signal: result.signal, error: result.error?.code }) + '\n' + result.stdout + result.stderr,
        { mode: 0o600 });
    }
    assert.equal(result.error, undefined, `child must exit without timeout: ${result.error}`);
    assert.equal(result.signal, null);
    assert.equal(result.status, 1, 'original setup failure remains visible');
    assert.match(result.stdout, new RegExp(`injected-member-${failure}`));
    assert.deepEqual(readdirSync(owned), [], 'member manager root removed after setup failure');
    if (failure === 'page') assert(readdirSync(root).includes('browser-closed'), 'acquired browser closed');
  });
}
