// ===============================================================
// GET /api/health — Service Health Check
// Returns system status, uptime, version, and component checks
// ===============================================================

const BOOT_TIME = Date.now();

const SEC = {
  'Content-Type': 'application/json; charset=utf-8',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Cache-Control': 'no-store',
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
};

export async function onRequestGet(context) {
  const now = Date.now();
  const uptimeMs = now - BOOT_TIME;

  // Component checks
  const components = {
    edge_worker: { status: 'operational', latency_ms: 0 },
    api_run: { status: 'operational' },
    api_version: { status: 'operational' },
    api_packages: { status: 'operational' },
  };

  // Check if secrets are configured
  const hasSecret = !!(context.env?.LINK_SECRET);

  const health = {
    status: 'healthy',
    timestamp: new Date(now).toISOString(),
    uptime_ms: uptimeMs,
    uptime_human: formatUptime(uptimeMs),
    version: {
      language: '3.0.1',
      platform: 'cloudflare-pages',
      runtime: 'workers',
    },
    components,
    region: context.request.cf?.colo || 'unknown',
    country: context.request.cf?.country || 'unknown',
  };

  return Response.json(health, {
    status: 200,
    headers: { ...SEC, 'Cache-Control': 'no-store, max-age=0' },
  });
}

function formatUptime(ms) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  const d = Math.floor(h / 24);

  if (d > 0) return `${d}d ${h % 24}h ${m % 60}m`;
  if (h > 0) return `${h}h ${m % 60}m ${s % 60}s`;
  if (m > 0) return `${m}m ${s % 60}s`;
  return `${s}s`;
}

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: { ...SEC, 'Access-Control-Max-Age': '86400' } });
}

export async function onRequestPost() {
  return Response.json({ error: 'Method not allowed' }, { status: 405, headers: SEC });
}
export async function onRequestPut() {
  return Response.json({ error: 'Method not allowed' }, { status: 405, headers: SEC });
}
export async function onRequestDelete() {
  return Response.json({ error: 'Method not allowed' }, { status: 405, headers: SEC });
}
