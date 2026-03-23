/**
 * TheDailyBrown Secrets Worker
 *
 * Serves credentials stored in Cloudflare KV as a .env file.
 * Protected by a one-time-use install token.
 *
 * KV Namespace binding: SECRETS
 */

const ENV_KEYS = [
  { key: 'CACHE_SCHEDULE_HOUR', default: '4' },
  { key: 'CACHE_SCHEDULE_MINUTE', default: '0' },
  { key: 'TIMEZONE', default: 'Australia/Brisbane' },
  { key: 'OPENWEATHERMAP_API_KEY' },
  { key: 'MS_CLIENT_ID' },
  { key: 'MS_CLIENT_SECRET' },
  { key: 'MS_TENANT_ID' },
  { key: 'ICLOUD_USERNAME' },
  { key: 'ICLOUD_APP_PASSWORD' },
  { key: 'GOOGLE_MAPS_API_KEY' },
  { key: 'WORK_ADDRESS' },
  { key: 'API_BEARER_TOKEN' },
  { key: 'DASHBOARD_DOMAIN' },
  { key: 'CLOUDFLARE_TUNNEL_TOKEN' },
];

/**
 * Generate a cryptographically random hex string.
 */
function randomHex(bytes) {
  const buf = new Uint8Array(bytes);
  crypto.getRandomValues(buf);
  return Array.from(buf)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Validate the Authorization: Bearer <token> header against the stored INSTALL_TOKEN.
 * Returns { valid: boolean, token: string | null }.
 */
async function validateToken(request, env) {
  const authHeader = request.headers.get('Authorization');
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return { valid: false, token: null };
  }

  const token = authHeader.slice(7).trim();
  if (!token) {
    return { valid: false, token: null };
  }

  const storedToken = await env.SECRETS.get('INSTALL_TOKEN');
  if (!storedToken || token !== storedToken) {
    return { valid: false, token };
  }

  return { valid: true, token };
}

/**
 * Build a .env formatted string from KV values.
 */
async function buildEnvString(env) {
  const lines = ['# TheDailyBrown .env — fetched from Cloudflare KV', `# Generated: ${new Date().toISOString()}`, ''];

  for (const entry of ENV_KEYS) {
    let value = await env.SECRETS.get(entry.key);
    if (value) value = value.trim();

    // Auto-generate API_BEARER_TOKEN if missing
    if (entry.key === 'API_BEARER_TOKEN' && !value) {
      value = randomHex(32);
      await env.SECRETS.put('API_BEARER_TOKEN', value);
    }

    // Fall back to default, then empty string
    if (value === null || value === undefined) {
      value = entry.default || '';
    }

    lines.push(`${entry.key}=${value}`);
  }

  lines.push('');
  return lines.join('\n');
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Only handle the root path
    if (url.pathname !== '/' && url.pathname !== '') {
      return new Response('Not Found', { status: 404 });
    }

    if (request.method === 'GET') {
      const { valid } = await validateToken(request, env);
      if (!valid) {
        return new Response('Unauthorized', { status: 401 });
      }

      const envString = await buildEnvString(env);
      return new Response(envString, {
        status: 200,
        headers: { 'Content-Type': 'text/plain' },
      });
    }

    if (request.method === 'DELETE') {
      const { valid } = await validateToken(request, env);
      if (!valid) {
        return new Response('Unauthorized', { status: 401 });
      }

      // Invalidate the install token (one-time use)
      await env.SECRETS.delete('INSTALL_TOKEN');
      return new Response('Token invalidated', { status: 200 });
    }

    return new Response('Method Not Allowed', { status: 405 });
  },
};
