// GET /api/dev-pack/download?t=<token>
// Requires header: X-Dev-Pass: <per-link password set at mint time>
import {
  jsonResponse, getClientIP, SEC_HEADERS, ASSETS,
  parseAndVerifyToken, verifyPassword,
} from './_lib.js';

const perIpFail = new Map();
const MAX_FAIL = 8;
const WIN = 15 * 60 * 1000;
const LOCK = 60 * 60 * 1000;

function rate(ip) {
  const now = Date.now();
  const r = perIpFail.get(ip);
  if (!r) return true;
  if (r.lockedUntil && now < r.lockedUntil) return false;
  if (now - r.first > WIN) { perIpFail.delete(ip); return true; }
  if (r.count >= MAX_FAIL) { r.lockedUntil = now + LOCK; return false; }
  return true;
}
function fail(ip) {
  const now = Date.now();
  const r = perIpFail.get(ip);
  if (!r) perIpFail.set(ip, { count: 1, first: now, lockedUntil: null });
  else r.count++;
}

async function handleDownload(context, expectedAsset) {
  const { env, request } = context;
  const secret = env.DEV_PACK_SECRET;
  const kv = env.DEV_PACK_TOKENS;
  const bucket = env.DEV_PACK;
  const ip = getClientIP(request);

  if (!secret || !kv || !bucket) {
    return jsonResponse({ error: 'Server not configured' }, 500);
  }
  if (!rate(ip)) {
    return jsonResponse({ error: 'Too many attempts. Try again later.' }, 429);
  }

  const url = new URL(request.url);
  const token = url.searchParams.get('t');
  const pass = request.headers.get('x-dev-pass');

  if (!token || !pass) {
    fail(ip);
    await new Promise(r => setTimeout(r, 400 + Math.random() * 300));
    return jsonResponse({ error: 'Missing token or X-Dev-Pass header' }, 401);
  }
  if (pass.length > 256) {
    fail(ip);
    return jsonResponse({ error: 'Invalid password' }, 401);
  }

  const parsed = await parseAndVerifyToken(token, secret);
  if (!parsed) {
    fail(ip);
    await new Promise(r => setTimeout(r, 400 + Math.random() * 300));
    return jsonResponse({ error: 'Invalid or expired token' }, 401);
  }

  const raw = await kv.get(parsed.tokenId);
  if (!raw) {
    fail(ip);
    await new Promise(r => setTimeout(r, 400 + Math.random() * 300));
    return jsonResponse({ error: 'Token revoked or unknown' }, 401);
  }

  let rec;
  try { rec = JSON.parse(raw); } catch { return jsonResponse({ error: 'Corrupt record' }, 500); }

  if (Date.now() > rec.expires) {
    await kv.delete(parsed.tokenId);
    return jsonResponse({ error: 'Token expired' }, 401);
  }
  if (rec.asset !== 'both' && rec.asset !== expectedAsset) {
    return jsonResponse({ error: 'Token not valid for this asset' }, 403);
  }
  if (rec.uses >= rec.maxUses) {
    return jsonResponse({ error: 'Download limit reached' }, 403);
  }

  if (!(await verifyPassword(pass, rec.salt, rec.hash))) {
    fail(ip);
    await new Promise(r => setTimeout(r, 600 + Math.random() * 400));
    return jsonResponse({ error: 'Invalid password' }, 401);
  }

  if (rec.ipBind) {
    if (!rec.claimedIp) {
      rec.claimedIp = ip;
    } else if (rec.claimedIp !== ip) {
      return jsonResponse({ error: 'Token bound to different IP' }, 403);
    }
  }

  rec.uses += 1;
  await kv.put(parsed.tokenId, JSON.stringify(rec), {
    expirationTtl: Math.ceil((rec.expires - Date.now()) / 1000) + 3600,
  });

  const key = ASSETS[expectedAsset];
  const obj = await bucket.get(key);
  if (!obj) return jsonResponse({ error: 'Asset missing from storage' }, 404);

  const headers = new Headers();
  Object.entries(SEC_HEADERS).forEach(([k, v]) => headers.set(k, v));
  headers.set('Content-Type', expectedAsset === 'vm' ? 'application/octet-stream' : 'application/gzip');
  headers.set('Content-Disposition', `attachment; filename="${key}"`);
  if (obj.size) headers.set('Content-Length', String(obj.size));
  if (obj.httpEtag) headers.set('ETag', obj.httpEtag);

  return new Response(obj.body, { status: 200, headers });
}

export async function onRequestGet(context) {
  return handleDownload(context, 'pack');
}
export async function onRequestPost(context) {
  return handleDownload(context, 'pack');
}
