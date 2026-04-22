// ===============================================================
// Link Generator API — POST /api/share
// Hardened: timing-safe auth, rate limiting, brute-force lockout
// ===============================================================

const ALLOWED_PAGES = ['me', 'resume'];
const DURATION_MAP = {
  '1h':  60 * 60 * 1000,
  '24h': 24 * 60 * 60 * 1000,
  '7d':  7 * 24 * 60 * 60 * 1000,
  '30d': 30 * 24 * 60 * 60 * 1000,
};

// In-memory rate limiter (per isolate — resets on deploy/cold start)
const attempts = new Map(); // IP -> { count, firstAttempt, lockedUntil }
const MAX_ATTEMPTS = 5;
const WINDOW_MS = 15 * 60 * 1000;    // 15-minute window
const LOCKOUT_MS = 60 * 60 * 1000;   // 1-hour lockout after max failures

function getClientIP(request) {
  return request.headers.get('cf-connecting-ip') ||
         request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
         'unknown';
}

function checkRateLimit(ip) {
  const now = Date.now();
  const record = attempts.get(ip);
  if (!record) return { allowed: true };
  if (record.lockedUntil && now < record.lockedUntil) {
    return { allowed: false, locked: true };
  }
  if (now - record.firstAttempt > WINDOW_MS) {
    attempts.delete(ip);
    return { allowed: true };
  }
  if (record.count >= MAX_ATTEMPTS) {
    record.lockedUntil = now + LOCKOUT_MS;
    return { allowed: false, locked: true };
  }
  return { allowed: true };
}

function recordFailure(ip) {
  const now = Date.now();
  const record = attempts.get(ip);
  if (!record) {
    attempts.set(ip, { count: 1, firstAttempt: now, lockedUntil: null });
  } else {
    record.count++;
  }
}

function clearFailures(ip) {
  attempts.delete(ip);
}

// Timing-safe string comparison via HMAC
async function timingSafeEqual(a, b) {
  const encoder = new TextEncoder();
  const keyData = crypto.getRandomValues(new Uint8Array(32));
  const key = await crypto.subtle.importKey(
    'raw', keyData, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const sigA = new Uint8Array(await crypto.subtle.sign('HMAC', key, encoder.encode(a)));
  const sigB = new Uint8Array(await crypto.subtle.sign('HMAC', key, encoder.encode(b)));
  if (sigA.length !== sigB.length) return false;
  let result = 0;
  for (let i = 0; i < sigA.length; i++) result |= sigA[i] ^ sigB[i];
  return result === 0;
}

// Security headers for all API responses
const SEC_HEADERS = {
  'Cache-Control': 'no-store, no-cache, must-revalidate',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-Robots-Tag': 'noindex, nofollow',
  'Referrer-Policy': 'no-referrer',
};

function jsonResponse(data, status = 200) {
  return Response.json(data, { status, headers: SEC_HEADERS });
}

export async function onRequestPost(context) {
  const secret = context.env.LINK_SECRET;
  const adminPass = context.env.ADMIN_PASS;
  const ip = getClientIP(context.request);

  if (!secret || !adminPass) {
    return jsonResponse({ error: 'Server not configured' }, 500);
  }

  // Rate limit check
  const rateCheck = checkRateLimit(ip);
  if (!rateCheck.allowed) {
    return jsonResponse({ error: 'Too many attempts. Try again later.' }, 429);
  }

  // Reject oversized payloads (> 1KB)
  const contentLength = parseInt(context.request.headers.get('content-length') || '0', 10);
  if (contentLength > 1024) {
    return jsonResponse({ error: 'Payload too large' }, 413);
  }

  let body;
  try {
    const text = await context.request.text();
    if (text.length > 1024) return jsonResponse({ error: 'Payload too large' }, 413);
    body = JSON.parse(text);
  } catch {
    return jsonResponse({ error: 'Invalid JSON' }, 400);
  }

  const { password, page, expiry } = body;

  // Validate types before comparison
  if (!password || typeof password !== 'string' || password.length > 256) {
    recordFailure(ip);
    await new Promise(r => setTimeout(r, 800 + Math.random() * 400));
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  // Timing-safe password comparison
  const passwordValid = await timingSafeEqual(password, adminPass);
  if (!passwordValid) {
    recordFailure(ip);
    await new Promise(r => setTimeout(r, 800 + Math.random() * 400));
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  // Auth passed — clear failure record
  clearFailures(ip);

  // Validate page
  if (!page || !ALLOWED_PAGES.includes(page)) {
    return jsonResponse({ error: 'Invalid page. Use: ' + ALLOWED_PAGES.join(', ') }, 400);
  }

  // Validate expiry
  if (!expiry || !DURATION_MAP[expiry]) {
    return jsonResponse({ error: 'Invalid expiry. Use: ' + Object.keys(DURATION_MAP).join(', ') }, 400);
  }

  // Generate token — page is bound into the signature to prevent cross-page reuse
  const expiresAt = Date.now() + DURATION_MAP[expiry];
  const payload = `${page}:${expiresAt}`;
  const payloadB64 = btoa(payload)
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(payloadB64));
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

  const token = `${payloadB64}.${sigB64}`;
  const url = `https://lateralus.dev/${page}/?t=${token}`;

  return jsonResponse({ url, page, expires: new Date(expiresAt).toISOString(), expiry });
}

// Block all other methods
export async function onRequestGet() {
  return jsonResponse({ error: 'Method not allowed' }, 405);
}
export async function onRequestPut() {
  return jsonResponse({ error: 'Method not allowed' }, 405);
}
export async function onRequestDelete() {
  return jsonResponse({ error: 'Method not allowed' }, 405);
}
