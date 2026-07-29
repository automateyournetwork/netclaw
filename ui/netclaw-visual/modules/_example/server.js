/**
 * Reference backend half of a HUD module.
 *
 * Only called when every key in module.json's requiresEnv is set, so there is
 * no need to guard against missing configuration here.
 */
export function register(app, ctx) {
  app.get('/api/example/status', (req, res) => {
    res.json({
      ok: true,
      // ctx.env() resolves from process.env then the .env files
      target: ctx.env('EXAMPLE_MODULE_URL'),
      root: ctx.ROOT,
    });
  });
}
