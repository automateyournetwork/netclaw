/**
 * Convergence module — backend half.
 *
 * Proxies /api/home/* through to convergence-api (or a pilot Network Guardian
 * during a dual-run). The browser never talks to convergence-api directly, so
 * its URL and token stay server-side.
 *
 * Only called when CONVERGENCE_API_URL is set (see module.json requiresEnv), so
 * there is no "not configured" branch to write here — an unconfigured install
 * registers none of this and renders no tab.
 */

/**
 * Resolve the upstream API. CONVERGENCE_API_* is preferred; HOME_API_* and
 * NETWORK_GUARDIAN_* are accepted as aliases for dual-run and legacy installs.
 */
function convergenceApiConfig(ctx) {
  const base = (
    ctx.env('CONVERGENCE_API_URL')
    || ctx.env('HOME_API_URL')
    || ctx.env('NETWORK_GUARDIAN_URL')
    || ''
  ).replace(/\/$/, '');
  const token = (
    ctx.env('CONVERGENCE_API_TOKEN')
    || ctx.env('HOME_API_TOKEN')
    || ctx.env('NETWORK_GUARDIAN_TOKEN')
    || ''
  );
  return { base, token };
}

export function register(app, ctx) {
  // Configuration probe. The UI calls this before mounting so it can show a
  // useful state rather than a blank panel when the token is missing.
  app.get('/api/home/status', (req, res) => {
    const { base, token } = convergenceApiConfig(ctx);
    res.json({
      configured: Boolean(base && token),
      base: base || null,
      tokenConfigured: Boolean(token),
      dualRun: Boolean(base && /network-guardian|guardian/i.test(base)),
    });
  });

  // Mount: browser /api/home/health?site=home  ->  upstream /api/health?site=home
  app.use('/api/home', async (req, res, next) => {
    if (req.path === '/status' || req.path === 'status') return next();

    const { base, token } = convergenceApiConfig(ctx);
    if (!base) {
      // Unreachable in practice (requiresEnv gates registration), but a clear
      // error beats a confusing proxy failure if the env is emptied at runtime.
      return res.status(503).json({
        error: 'Convergence API not configured',
        hint: 'Set CONVERGENCE_API_URL (+ CONVERGENCE_API_TOKEN) and restart the HUD.',
      });
    }

    const rel = req.url.startsWith('/') ? req.url : `/${req.url}`;
    const url = `${base}/api${rel}`;
    try {
      const headers = {
        Accept: 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      const hasBody = !['GET', 'HEAD'].includes(req.method)
        && req.body && Object.keys(req.body).length > 0;
      if (hasBody) headers['Content-Type'] = 'application/json';

      const upstream = await fetch(url, {
        method: req.method,
        headers,
        body: hasBody ? JSON.stringify(req.body) : undefined,
        signal: AbortSignal.timeout(20000),
      });
      const text = await upstream.text();
      res.status(upstream.status);
      res.setHeader('Content-Type', upstream.headers.get('content-type') || 'application/json');
      return res.send(text);
    } catch (err) {
      return res.status(502).json({
        error: 'Convergence API unreachable',
        detail: err.message,
        target: base,
      });
    }
  });
}
