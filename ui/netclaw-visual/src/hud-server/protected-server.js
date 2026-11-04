import path from 'node:path';
import http from 'node:http';
import crypto from 'node:crypto';
import express from 'express';
import { boundedFile, noSymlink, loadProtectedAssets } from './protected-assets.js';
import { strictJson, readProtectedDescriptor, createProtectedClient } from './protected-client.js';
import { mountProtectedOperations } from './protected-operations.js';
import { mountMobileEnrollment } from './mobile-enrollment.js';
import { readRemoteHudConfig, remoteHudRoute, createRemoteHud } from './remote-hud.js';

const LOOPBACK = new Set(['127.0.0.1', '::1', '::ffff:127.0.0.1']);
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.woff': 'font/woff', '.woff2': 'font/woff2' };
export const PROTECTED_CSP = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; frame-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'";
const exact = (v, keys) => v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === keys.length && keys.every(k => Object.hasOwn(v, k));
export function openLabAccess(installationId) {
  // UUIDv5 with the installation UUID as namespace: stable audit attribution,
  // not a login, credential or assertion about the person using this lab.
  const bytes = crypto.createHash('sha1').update(Buffer.from(installationId.replaceAll('-', ''), 'hex')).update('netclaw.open-lab.operator').digest().subarray(0, 16);
  bytes[6] = (bytes[6] & 0x0f) | 0x50; bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = bytes.toString('hex'), subject = [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16), hex.slice(16, 20), hex.slice(20)].join('-');
  return { mode: 'open-lab', principal: { issuer: 'open-lab', subject, display_name: 'Unauthenticated lab operator', roles: ['lab-operator'] } };
}
const privateJson = target => strictJson(boundedFile(target, 65536, true).toString('utf8'));
export function readProtectedServerConfig(file) {
  const config = privateJson(file);
  if (!exact(config, ['schemaVersion', 'installationId', 'home', 'kind', 'origin', 'host', 'port', 'dist', 'manifest', 'manifestSha256', ...('access' in config ? ['access'] : []), ...('workspace' in config ? ['workspace'] : [])]) || config.schemaVersion !== 1 || config.kind !== 'openclaw' || config.host !== '127.0.0.1' || !Number.isSafeInteger(config.port) || config.port < 1 || config.port > 65535 || !/^[a-f0-9-]{36}$/.test(config.installationId)) throw Error('invalid_configuration');
  if ('access' in config && (!exact(config.access, ['mode']) || config.access.mode !== 'open-lab')) throw Error('invalid_access');
  const origin = new URL(config.origin);
  if (origin.protocol !== 'https:' || origin.origin !== config.origin || origin.username || origin.password) throw Error('invalid_origin');
  noSymlink(config.home);
  const home = fs.lstatSync(config.home);
  if (!home.isDirectory() || home.uid !== process.getuid() || (home.mode & 0o777) !== 0o700) throw Error('invalid_home');
  const identity = privateJson(path.join(config.home, 'netclaw-hud/installation.json'));
  const profile = privateJson(path.join(config.home, 'netclaw-federation/protected-profile.json'));
  if (!exact(identity, ['schemaVersion', 'installationId']) || identity.schemaVersion !== 1 || identity.installationId !== config.installationId || !exact(profile, ['schemaVersion', 'role', 'identity', ...('access' in profile ? ['access'] : [])]) || profile.schemaVersion !== 1 || profile.role !== 'border' || profile.identity?.installation_id !== config.installationId) throw Error('invalid_installation');
  if (JSON.stringify(profile.access) !== JSON.stringify(config.access)) throw Error('access_mismatch');
  const installation = Object.freeze({ home: config.home, kind: config.kind, installationId: config.installationId });
  let workspace;
  if ('workspace' in config) {
    if (config.access?.mode !== 'open-lab' || !exact(config.workspace, ['path', 'sha256'])) throw Error('invalid_workspace');
    workspace = readRemoteHudConfig(config.workspace.path, installation, config.workspace.sha256);
    if (new URL(workspace.upstream).port === String(config.port)) throw Error('workspace_loop');
  }
  readProtectedDescriptor(installation); // Existing private binding is required, never initialized.
  return { ...config, ...('access' in config ? { access: openLabAccess(config.installationId) } : {}), authority: origin.host, installation, workspace, files: loadProtectedAssets({ ...config, workspace }) };
}

export function createProtectedServer(config, { client = createProtectedClient(config.installation) } = {}) {
  const remote = config.workspace ? createRemoteHud(config.workspace, config.installation) : null;
  const csp = remote ? PROTECTED_CSP.replace("style-src 'self'", "style-src 'self' 'unsafe-inline'").replace("img-src 'self' data:", "img-src 'self' data: blob:").replace("frame-src 'none'", "frame-src 'self'").replace("frame-ancestors 'none'", "frame-ancestors 'self'") : PROTECTED_CSP;
  const app = express(); app.disable('x-powered-by'); app.disable('etag'); app.set('strict routing', true); app.set('case sensitive routing', true);
  const once = (req, name) => req.rawHeaders.filter((_, i) => i % 2 === 0 && req.rawHeaders[i].toLowerCase() === name).length === 1;
  app.use((req, res, next) => {
    res.set({ 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'X-Frame-Options': remote ? 'SAMEORIGIN' : 'DENY', 'Content-Security-Policy': csp });
    if (!LOOPBACK.has(req.socket.remoteAddress) || !once(req, 'host') || req.headers.host !== config.authority || req.headers.origin !== undefined && (!once(req, 'origin') || req.headers.origin !== config.origin) || req.headers['sec-fetch-site'] === 'cross-site') return res.status(403).json({ code: 'ingress_refused' });
    if (typeof req.url !== 'string' || !req.url.startsWith('/') || req.url.startsWith('//') || /[\\#\u0000-\u0020\u007f]/.test(req.url) || req.url.split('?')[0].includes('%') && !(remote && remoteHudRoute(req.method, req.url, config.workspace.features))) return res.status(404).json({ code: 'route_unavailable' });
    if (req.method === 'HEAD' && req.path.startsWith('/api/') || !['GET', 'HEAD', 'POST', 'DELETE'].includes(req.method)) return res.status(405).json({ code: 'method_refused' });
    if (req.path.startsWith('/api/')) {
      const id = '[A-Za-z0-9_.:-]{1,200}', pathname = req.url.split('?')[0];
      const allowed = req.method === 'GET' && (['/api/runtime', '/api/hud/owner/session', '/api/hud/operations', '/api/hud/operations/catalog', '/api/hud/mobile/enrollment'].includes(pathname) || new RegExp(`^/api/hud/operations/${id}$`).test(pathname) || /^\/api\/hud\/mobile\/enrollment\/[a-f0-9-]{36}$/.test(pathname))
        || req.method === 'POST' && (['/api/hud/owner/session', '/api/hud/operations', '/api/hud/mobile/enrollment'].includes(pathname) || new RegExp(`^/api/hud/operations/${id}/(?:decision|reconcile|revoke)$`).test(pathname))
        || req.method === 'DELETE' && pathname === '/api/hud/owner/session';
      if (config.access?.mode === 'open-lab' && pathname === '/api/hud/owner/session') return res.status(404).json({ code: 'route_unavailable' });
      if (remote && remoteHudRoute(req.method, req.url, config.workspace.features) && req.method !== 'GET' && (!once(req, 'origin') || req.headers.origin !== config.origin)) return res.status(403).json({ code: 'origin_refused' });
      if (!allowed && !(remote && remoteHudRoute(req.method, req.url, config.workspace.features))) return res.status(404).json({ code: 'route_unavailable' });
    }
    next();
  });
  app.get('/api/runtime', async (req, res) => {
    if (req.url !== '/api/runtime') return res.status(400).json({ code: 'invalid_argument' });
    if (remote) { try { await remote.verify(); } catch { return res.status(503).json({ code: 'workspace_unavailable' }); } }
    res.json({ ...(config.access ? { access: config.access } : {}), installationId: config.installation.installationId, kind: 'openclaw', role: 'border', label: remote ? 'NetClaw Border' : 'Control-only Border', readiness: { ready: true, executionVerified: false }, capabilities: { mobileEnrollment: { schema: 1 }, protectedProfile: true, protectedOperations: true, protectedProduction: true, ...(remote ? { remoteHud: { schema: 1, features: config.workspace.features } } : {}), convergence: false, attachments: Boolean(remote), modelSelection: Boolean(remote), effort: Boolean(remote), federation: true, hostedAvatar: false, writes: false } });
  });
  mountProtectedOperations(app, { installation: config.installation, config: { enabled: true, secure: true, exactRoutes: true, access: config.access, contentSecurityPolicy: csp, origins: [config.origin] }, client });
  mountMobileEnrollment(app, { installation: config.installation, client,
    config: { enabled: config.access?.mode === 'open-lab', origins: [config.origin],
              access: config.access, reason: 'owner_issuance_unqualified' } });
  if (remote) app.use(async (req, res, next) => { if (!await remote.handle(req, res)) next(); });
  app.use((req, res) => {
    if (!['GET', 'HEAD'].includes(req.method)) return res.status(405).json({ code: 'method_refused' });
    const target = req.url === '/' ? '/index.html' : remote && req.url === '/canvas.html?embedded=1' ? '/canvas.html' : req.url, body = config.files.get(target);
    if (!body) return res.status(404).json({ code: 'route_unavailable' });
    res.set('Content-Type', TYPES[path.extname(target)]).send(body);
  });
  app.use((_error, _req, res, _next) => { if (!res.headersSent) res.status(503).json({ code: 'protected_service_unavailable' }); else res.destroy(); });
  const server = http.createServer({ maxHeaderSize: 16 * 1024, headersTimeout: 10000, requestTimeout: 30000, keepAliveTimeout: 5000, connectionsCheckingInterval: 1000 }, app);
  server.maxConnections = 64;
  server.on('request', (_req, res) => { const timer = setTimeout(() => res.destroy(), remote ? 600000 : 30000); timer.unref(); res.once('close', () => clearTimeout(timer)); });
  server.on('upgrade', (_req, socket) => socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n'));
  server.on('clientError', (_error, socket) => { if (socket.writable) socket.end('HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n'); });
  return server;
}
import fs from 'node:fs';
