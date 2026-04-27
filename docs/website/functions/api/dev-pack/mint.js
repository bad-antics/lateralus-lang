// POST /api/dev-pack/mint
// Admin-only. Creates a per-link password-gated download token.
// Body: { admin_pass, download_pass, asset: 'pack'|'vm'|'both',
//         expiry: '1h'|'24h'|'7d'|'30d', ip_bind?: bool, max_uses?: int }
import {
  jsonResponse, getClientIP, ASSETS, hmacSign,
  hashPassword, randomTokenId, timingSafeEqual,
} from './_lib.js';

const DURATION_MAP = {
  '1h':  60 * 60 * 1000,
  '24h': 24 * 60 * 60 * 1000,
  '7d':  7 * 24 * 60 * 60 * 1000,
  '30d': 30 * 24 * 60 * 60 * 1000,
};

const attempts = new Map();
const MAX_ATTEMPTS = 5;
const WINDOW_MS = 15 * 60 * 1000;
const LOCKOUT_MS = 60 * 60 * 1000;

function checkRate(ip) {
  const now = Date.now();
  const r = attempts.get(ip);
  if (!r) return true;
  if (r.lockedUntil && now < r.lockedUntil) return false;
  if (now - r.first > WINDOW_MS) { attempts.delete(ip); return true; }
  if (r.count >= MAX_ATTEMPTS) { r.lockedUntil = now + LOCKOUT_MS; return false; }
  return true;
}
function recordFail(ip) {
  const now = Date.now();
  const r = attempts.get(ip);
  if (!r) attempts.set(ip, { count: 1, first: now, lockedUntil: null });
  else r.count++;
}
function clearFail(ip) { attempts.delete(ip); }

export async function onRequestPost(context) {
  const { env, request } = context;
  const secret = env.DEV_PACK_SECRET;
  const adminPass = env.DEV_PACK_ADMIN_PASS;
  const kv = env.DEV_PACK_TOKENS;
  const ip = getClientIP(request);

  if (!secret || !adminPass || !kv) {
    return jsonResponse({ error: 'Server not configured' }, 500);
  }
  if (!checkRate(ip)) {
    return jsonResponse({ error: 'Too many attempts. Try again later.' }, 429);
  }

  const len = parseInt(request.headers.get('content-length') || '0', 10);
  if (len > 2048) return jsonResponse({ error: 'Payload too large' }, 413);

  let body;
  try {
    const text = await request.text();
    if (text.length > 2048) return jsonResponse({ error: 'Payload too large' }, 413);
    body = JSON.parse(text);
  } catch { return jsonResponse({ error: 'Invalid JSON' }, 400); }

  const { admin_pass, download_pass, asset, expiry, ip_bind, max_uses } = body;

  if (!admin_pass || typeof admin_pass !== 'string' || admin_pass.length > 256) {
    recordFail(ip);
    await new Promise(r => setTimeout(r, 800 + Math.random() * 400));
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }
  if (!(await timingSafeEqual(admin_pass, adminPass))) {
    recordFail(ip);
    await new Promise(r => setTimeout(r, 800 + Math.random() * 400));
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }
  clearFail(ip);

  if (!download_pass || typeof download_pass !== 'string' || download_pass.length < 8 || download_pass.length > 256) {
    return jsonResponse({ error: 'download_pass must be 8-256 chars' }, 400);
  }
  const assetKey = asset === 'both' ? 'both' : asset;
  if (!['pack', 'vm', 'both'].includes(assetKey)) {
    return jsonResponse({ error: 'asset must be pack|vm|both' }, 400);
  }
  if (!expiry || !DURATION_MAP[expiry]) {
    return jsonResponse({ error: 'expiry must be 1h|24h|7d|30d' }, 400);
  }
  const uses = Number.isInteger(max_uses) && max_uses > 0 && max_uses <= 100 ? max_uses : 10;
  const ipBind = !!ip_bind;

  const tokenId = randomTokenId();
  const expiresAt = Date.now() + DURATION_MAP[expiry];
  const { salt, hash } = await hashPassword(download_pass);

  const record = {
    v: 1, asset: assetKey, salt, hash,
    ipBind, claimedIp: null,
    uses: 0, maxUses: uses,
    created: Date.now(), expires: expiresAt,
  };
  await kv.put(tokenId, JSON.stringify(record), {
    expirationTtl: Math.ceil((expiresAt - Date.now()) / 1000) + 3600,
  });

  const payload = `${tokenId}:${expiresAt}`;
  const sig = await hmacSign(payload, secret);
  const token = `${payload}.${sig}`;

  const origin = new URL(request.url).origin;
  const packUrl = (assetKey === 'pack' || assetKey === 'both')
    ? `${origin}/api/dev-pack/download?t=${token}` : null;
  const vmUrl = (assetKey === 'vm' || assetKey === 'both')
    ? `${origin}/api/dev-pack/vm-image?t=${token}` : null;

  return jsonResponse({
    tokenId,
    asset: assetKey,
    expires: new Date(expiresAt).toISOString(),
    max_uses: uses,
    ip_bind: ipBind,
    urls: { pack: packUrl, vm: vmUrl },
    curl_example: packUrl
      ? `curl -H 'X-Dev-Pass: <your-password>' '${packUrl}' -o dev-pack.tar.gz`
      : `curl -H 'X-Dev-Pass: <your-password>' '${vmUrl}' -o lateralus-os.qcow2`,
    note: 'Supply download_pass via X-Dev-Pass header on GET. Link is bound to the password you chose; sharing the URL alone will not grant access.',
  });
}

export async function onRequestGet() {
  return jsonResponse({ error: 'Method not allowed' }, 405);
}
