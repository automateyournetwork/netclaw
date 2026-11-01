// Resolve only local environment references supported by native setup. Never
// stringify a SecretRef object or fall back after an explicit reference fails.
export function gatewayBearerToken(config, env = process.env) {
  const auth = config.gateway?.auth || {};
  if (auth.mode === 'password') return '';
  let value = auth.token;
  if (value == null) value = env.OPENCLAW_GATEWAY_TOKEN;
  else if (typeof value === 'string') {
    const reference = value.match(/^\$\{([A-Z_][A-Z0-9_]*)\}$/);
    if (reference) value = env[reference[1]];
  } else if (value?.source === 'env' && value.provider === 'default' &&
             /^[A-Z_][A-Z0-9_]*$/.test(value.id || '')) value = env[value.id];
  else return '';
  return typeof value === 'string' && value.length > 0 && !/[\r\n\0]/.test(value) ? value : '';
}
