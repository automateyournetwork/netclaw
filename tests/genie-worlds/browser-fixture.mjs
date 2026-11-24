import { mkdtempSync, realpathSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createManager } from '../../scripts/genie-worlds/manager.mjs';
import { chromium } from '../../scripts/genie-worlds/node_modules/playwright-core/index.mjs';

// Test-only resource ownership; this is not part of the live source closure.
export async function createBrowserFixture(t, prefix, {
  launch = options => chromium.launch(options),
  launchServer,
  connect = endpoint => chromium.connect(endpoint),
  snapshotRegistryPath = null,
} = {}) {
  const root = mkdtempSync(join(process.env.NETCLAW_TEST_TMP || realpathSync(tmpdir()), prefix));
  let m, browser, server;
  t.after(async () => {
    try {
      // The server owns the browser process even if connect/newPage fails.
      if (server) await server.close();
      else await browser?.close();
    } finally {
      try {
        await m?.close();
      } finally {
        rmSync(root, { recursive: true, force: true });
      }
    }
  });
  m = await createManager({ root, snapshotRegistryPath });
  const options = { executablePath: process.env.NETCLAW_BROWSER_EXECUTABLE, headless: true };
  if (launchServer) {
    server = await launchServer(options);
    browser = await connect(server.wsEndpoint());
  } else browser = await launch(options);
  return { root, m, browser, server };
}
