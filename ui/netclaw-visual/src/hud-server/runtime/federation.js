/** Display readiness is tied to the selected installation, never a nearby port. */
export function federationEndpoint(environment = {}) {
  const url = new URL(environment.NETCLAW_BGP_API || `http://127.0.0.1:${environment.BGP_API_PORT || 8179}`);
  if (url.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(url.hostname) || url.username || url.password || url.search || url.hash || url.pathname !== '/') throw Error('Selected federation must use its local control endpoint.');
  return url.origin;
}
export async function federationReadiness(installation, endpoint, fetcher = fetch) {
  try {
    const response = await fetcher(`${endpoint}/status`, { signal: AbortSignal.timeout(2000), redirect: 'error' });
    const value = await response.json();
    if (!response.ok || value.installation_id !== installation.installationId || value.harness_type !== installation.kind) return { ready: false, code: 'federation_owner_mismatch' };
    return { ready: value.federation_ready === true, code: value.federation_ready ? 'ready' : 'federation_stopped', harness: value.harness_type };
  } catch { return { ready: false, code: 'federation_unavailable' }; }
}
