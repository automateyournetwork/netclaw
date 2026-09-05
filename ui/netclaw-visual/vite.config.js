import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const rootDir = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        hud: resolve(rootDir, 'index.html'),
        canvas: resolve(rootDir, 'canvas.html'),
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        timeout: 300000,
        configure: (proxy) => {
          proxy.on('proxyReq', (_proxyReq, _req, res) => {
            // Keep socket alive for 5 minutes (gateway may run many tools)
            res.setTimeout(300000);
          });
        },
      },
      '/ws': {
        target: 'ws://localhost:3001',
        ws: true,
      },
    },
  },
});
