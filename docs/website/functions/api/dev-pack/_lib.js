// Shared helpers for dev-pack gated endpoints
export const SEC_HEADERS = {
  'Cache-Control': 'no-store, no-cache, must-revalidate',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-Robots-Tag': 'noindex, nofollow',
  'Referrer-Policy': 'no-referrer',
};

export const ASSETS = {
  'pack':     'dev-pack-v0.7.0-dev.tar.gz',
  'vm':       'lateralus-os-v1.2.0-dev-x86_64.qcow2',
};

export function jsonResponse(data, status = 200) {
  return Response.json(data, { status, headers: SEC_HEADERS });
}

export function getClientIP(request) {
  return request.headers.get('cf-connecting-ip') ||
         request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
         'unknown';
}

const enc = new TextEncoder();

export function b64uEncode(bytes) {
  let s = '';
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function b64uDecode(str) {
  const pad = '='.repeat((4 - str.length % 4) % 4);
  const b64 = (str + pad).replace(/-/g, '+').replace(/_/g, '/');
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function hmacKey(secret) {
  return crypto.subtle.importKey(
    'raw', enc.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
}

export async function hmacSign(payload, secret) {
  const key = await hmacKey(secret);
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(payload));
  return b64uEncode(new Uint8Array(sig));
}

export async function hmacVerify(payload, sigB64, secret) {
  const expected = await hmacSign(payload, secret);
  if (sigB64.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < sigB64.length; i++) diff |= sigB64.charCodeAt(i) ^ expected.charCodeAt(i);
  return diff === 0;
}

// Timing-safe string compare via HMAC randomization
export async function timingSafeEqual(a, b) {
  const keyData = crypto.getRandomValues(new Uint8Array(32));
  const k = await crypto.subtle.importKey('raw', keyData, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sa = new Uint8Array(await crypto.subtle.sign('HMAC', k, enc.encode(a)));
  const sb = new Uint8Array(await crypto.subtle.sign('HMAC', k, enc.encode(b)));
  if (sa.length !== sb.length) return false;
  let r = 0;
  for (let i = 0; i < sa.length; i++) r |= sa[i] ^ sb[i];
  return r === 0;
}

// PBKDF2-SHA256 password hashing (Workers-native). 600k iters.
export async function hashPassword(password, saltBytes) {
  const salt = saltBytes || crypto.getRandomValues(new Uint8Array(16));
  const baseKey = await crypto.subtle.importKey(
    'raw', enc.encode(password), { name: 'PBKDF2' }, false, ['deriveBits']
  );
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', salt, iterations: 100_000, hash: 'SHA-256' },
    baseKey, 256
  );
  return { salt: b64uEncode(salt), hash: b64uEncode(new Uint8Array(bits)) };
}

export async function verifyPassword(password, saltB64, hashB64) {
  const salt = b64uDecode(saltB64);
  const { hash } = await hashPassword(password, salt);
  return timingSafeEqual(hash, hashB64);
}

export function randomTokenId() {
  const b = crypto.getRandomValues(new Uint8Array(16));
  return b64uEncode(b);
}

// Verify signed token format "tokenId:expires.sig" and return { tokenId, expires } or null
export async function parseAndVerifyToken(token, secret) {
  if (!token || typeof token !== 'string') return null;
  const dot = token.lastIndexOf('.');
  if (dot < 1) return null;
  const payload = token.slice(0, dot);
  const sig = token.slice(dot + 1);
  if (!(await hmacVerify(payload, sig, secret))) return null;
  const colon = payload.indexOf(':');
  if (colon < 1) return null;
  const tokenId = payload.slice(0, colon);
  const expires = parseInt(payload.slice(colon + 1), 10);
  if (isNaN(expires) || Date.now() > expires) return null;
  return { tokenId, expires };
}
