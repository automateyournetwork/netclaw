/** Session authority remains in memory; browser persistence holds identifiers only. */
export function createProtectedOperationsApi(installationId, onSessionLost = () => {}) {
  let csrf = null;
  const request = async (path, method = 'GET', body, bootstrap = false) => {
    const headers = { 'X-NetClaw-Installation': installationId };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (bootstrap) headers['X-NetClaw-Owner-Bootstrap'] = '1';
    else if (method !== 'GET') headers['X-NetClaw-CSRF'] = csrf || '';
    let response, value;
    try {
      response = await fetch(path, { method, headers, credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(35000), ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
      value = await response.json();
    } catch {
      throw Object.assign(Error('The response was not confirmed. Check this operation’s status; nothing was resent.'), { uncertain: true });
    }
    if (!response.ok) {
      if (response.status === 401 || response.status === 409 && value.code === 'installation_changed') { csrf = null; onSessionLost(); }
      const prepareNotSubmitted = path === '/api/hud/operations' && method === 'POST' && value.admission === 'not_submitted';
      const message = prepareNotSubmitted ? 'The review was rejected before submission. Nothing was executed.' : response.status === 401 ? 'Your owner session expired. Sign in again to recover this operation.' : response.status === 403 ? 'The request was refused. Check your owner session and configured HUD origin.' : response.status === 404 ? 'No owned operation was found. Nothing was resent.' : response.status === 429 ? 'Too many sign-in attempts. Wait one minute before trying again.' : 'The request was not confirmed. Check the same operation’s status before continuing.';
      throw Object.assign(Error(message), { status: response.status, code: value.code, uncertain: response.status >= 500, prepareNotSubmitted });
    }
    return value;
  };
  const retainSession = value => {
    if (value?.authenticated !== true || value.installation_id !== installationId || typeof value.csrf_token !== 'string') throw Error('The selected owner session is unavailable.');
    csrf = value.csrf_token;
    const { csrf_token: _private, ...publicState } = value;
    return publicState;
  };
  return {
    inspect: async () => retainSession(await request('/api/hud/owner/session')),
    login: async ticket => retainSession(await request('/api/hud/owner/session', 'POST', { ticket }, true)),
    logout: async () => { try { return await request('/api/hud/owner/session', 'DELETE', {}); } finally { csrf = null; onSessionLost(); } },
    forget: () => { csrf = null; },
    catalog: () => request('/api/hud/operations/catalog'),
    prepare: body => request('/api/hud/operations', 'POST', body),
    status: record => request(record.operation_id ? '/api/hud/operations/' + encodeURIComponent(record.operation_id) : '/api/hud/operations?client_nonce=' + encodeURIComponent(record.client_nonce)),
    decision: (id, body) => request('/api/hud/operations/' + encodeURIComponent(id) + '/decision', 'POST', body),
    reconcile: id => request('/api/hud/operations/' + encodeURIComponent(id) + '/reconcile', 'POST', {}),
    revoke: id => request('/api/hud/operations/' + encodeURIComponent(id) + '/revoke', 'POST', {}),
  };
}

export function operationReference(installationId, storage = globalThis.sessionStorage) {
  const key = `netclaw.protected.${installationId}.operation`;
  const valid = value => typeof value === 'string' && /^[A-Za-z0-9_.:-]{1,200}$/.test(value);
  return {
    read() {
      try {
        const value = JSON.parse(storage.getItem(key));
        if (!value || Object.keys(value).some(key => !['client_nonce', 'operation_id'].includes(key)) || !valid(value.client_nonce) || value.operation_id !== undefined && !valid(value.operation_id)) return null;
        return value;
      } catch { return null; }
    },
    write(value) {
      if (!valid(value.client_nonce) || value.operation_id !== undefined && !valid(value.operation_id)) throw Error('Operation identity is unavailable.');
      storage.setItem(key, JSON.stringify({ client_nonce: value.client_nonce, ...(value.operation_id ? { operation_id: value.operation_id } : {}) }));
    },
    clear() { storage.removeItem(key); },
  };
}
