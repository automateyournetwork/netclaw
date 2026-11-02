import { createProtectedServer, readProtectedServerConfig } from './src/hud-server/protected-server.js';

try {
  if (process.argv.length !== 4 || process.argv[2] !== '--config') throw Error('arguments');
  const config = readProtectedServerConfig(process.argv[3]);
  const server = createProtectedServer(config);
  server.on('error', () => { console.error('Protected HUD listener unavailable.'); process.exitCode = 1; });
  server.listen(config.port, config.host, () => console.log('Protected HUD listening on the configured loopback endpoint.'));
  const stop = () => { server.close(); server.closeAllConnections(); };
  process.once('SIGTERM', stop); process.once('SIGINT', stop);
} catch { console.error('Protected HUD startup refused; verify the selected installation and pinned configuration.'); process.exitCode = 1; }
