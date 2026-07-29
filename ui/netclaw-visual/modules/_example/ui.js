/**
 * Reference browser half of a HUD module.
 *
 * Import module-owned CSS from here. index.html only <link>s src/styles.css, so
 * a stylesheet with no JS import silently does nothing.
 */
// import './example.css';

export async function registerUI(ctx) {
  const res = await fetch('/api/example/status');
  const data = await res.json();
  console.log('[example] backend says', data);
  // Real modules would render here, using ctx.dom / ctx.setDetail / ctx.state.
}
