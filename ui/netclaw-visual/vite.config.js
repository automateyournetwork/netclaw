import { chatTimeouts } from './src/hud-server/chat-transport.js';
import { protectedDocumentHeaders } from './src/hud-server/protected-operations.js';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { hudPorts, hudHost, createLocalAccess, guardHudServer } from './src/security/local-access.js';

const ports = hudPorts();
const chatDeadlines = chatTimeouts();
const host = hudHost();
const allowed = createLocalAccess(ports, { host, allowRemote: true });
const protectedHeaders = process.env.N2N_PROTECTED_OPERATIONS === '1' ? { 'Cache-Control': 'no-store' } : {};
const localOnly = () => ({
  name: 'netclaw-local-access',
  configureServer(server) { guardHudServer(server, allowed); server.middlewares.use(protectedDocumentHeaders(process.env.N2N_PROTECTED_OPERATIONS === '1')); },
  configurePreviewServer(server) { guardHudServer(server, allowed); server.middlewares.use(protectedDocumentHeaders(process.env.N2N_PROTECTED_OPERATIONS === '1')); },
});

const rootDir = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  plugins: [localOnly(), react()],
  build: {
    manifest: true,
    rollupOptions: {
      input: {
        hud: resolve(rootDir, 'index.html'),
        classic: resolve(rootDir, 'classic.html'),
        canvas: resolve(rootDir, 'canvas.html'),
        assessment: resolve(rootDir, 'assessment.html'),
      },
    },
  },
  preview: { host, port: ports.ui, strictPort: true, headers: protectedHeaders },
  server: {
    host,
    port: ports.ui,
    strictPort: true,
    headers: protectedHeaders,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${ports.api}`,
        timeout: chatDeadlines.proxy,
        proxyTimeout: chatDeadlines.proxy,
        configure: (proxy) => {
          proxy.on('proxyReq', (_proxyReq, _req, res) => {
            // Let the API send its structured deadline response before the proxy closes.
            res.setTimeout(chatDeadlines.proxy);
          });
        },
      },
      '/ws': {
        target: `ws://127.0.0.1:${ports.api}`,
        ws: true,
      },
    },
  },
});
