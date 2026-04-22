// ===============================================================
// Site Middleware — Full Hardening
// 1. Block sensitive file paths (.git, .env, dotfiles)
// 2. Token-gated access for /me/ and /resume/
// ===============================================================

// --- Sensitive Path Blocking -----------------------------------
const BLOCKED_PATTERNS = [
  /^\/\.git(\/|$)/,       // .git directory
  /^\/\.env$/,            // .env file
  /^\/\.gitignore$/,      // .gitignore
  /^\/\.gitmodules$/,     // .gitmodules
  /^\/\.ds_store$/,       // macOS artifact
  /^\/\.wrangler(\/|$)/,  // wrangler build dir
  /^\/node_modules(\/|$)/,// node_modules
  /^\/\.npmrc$/,          // npm config
  /^\/\.yarnrc$/,         // yarn config
  /^\/\.prettierrc/,      // prettier config
  /^\/\.eslintrc/,        // eslint config
  /^\/tsconfig\.json$/,   // typescript config
  /^\/package\.json$/,    // package.json
  /^\/package-lock\.json$/,// lockfile
  /^\/yarn\.lock$/,       // lockfile
  /^\/wrangler\.toml$/,   // wrangler config
  /^\/\.htaccess$/,       // apache config
  /^\/wp-admin(\/|$)/,    // wordpress probes
  /^\/wp-login/,          // wordpress probes
  /^\/wp-content(\/|$)/,  // wordpress probes
  /^\/xmlrpc\.php$/,      // wordpress probes
  /^\/administrator(\/|$)/, // joomla probes
  /^\/phpmyadmin(\/|$)/i, // phpmyadmin probes
];

function isBlockedPath(pathname) {
  const lower = pathname.toLowerCase();
  return BLOCKED_PATTERNS.some(p => p.test(lower));
}

// --- Token-Gated Access ---------------------------------------
const PROTECTED = ['/me', '/resume'];

function isProtected(pathname) {
  return PROTECTED.some(p =>
    pathname === p || pathname === p + '/' || pathname.startsWith(p + '/')
  );
}

function getPage(pathname) {
  for (const p of PROTECTED) {
    if (pathname === p || pathname === p + '/' || pathname.startsWith(p + '/')) {
      return p.slice(1);
    }
  }
  return null;
}

async function verifyToken(token, secret, expectedPage) {
  if (!token || !secret) return false;

  const parts = token.split('.');
  if (parts.length !== 2) return false;

  const [payloadB64, sigB64] = parts;

  let payload;
  try {
    payload = atob(payloadB64.replace(/-/g, '+').replace(/_/g, '/'));
  } catch { return false; }

  const colonIdx = payload.indexOf(':');
  if (colonIdx === -1) return false;

  const page = payload.slice(0, colonIdx);
  const expiry = parseInt(payload.slice(colonIdx + 1), 10);

  if (page !== expectedPage) return false;
  if (isNaN(expiry) || Date.now() > expiry) return false;

  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(payloadB64));
  const expectedSig = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

  // Timing-safe comparison
  if (sigB64.length !== expectedSig.length) return false;
  let diff = 0;
  for (let i = 0; i < sigB64.length; i++) {
    diff |= sigB64.charCodeAt(i) ^ expectedSig.charCodeAt(i);
  }
  return diff === 0;
}

// --- Security Headers -----------------------------------------
const SEC_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-Robots-Tag': 'noindex, nofollow',
  'Referrer-Policy': 'no-referrer',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
};

// --- API Rate Tracking (per-isolate) --------------------------
const apiAttempts = new Map();
const API_RATE_WINDOW = 60_000;
const API_RATE_LIMITS = {
  '/api/run':      30,
  '/api/share':    10,
  '/api/version':  120,
  '/api/health':   60,
  '/api/packages': 120,
};

function apiRateCheck(ip, path) {
  const limit = API_RATE_LIMITS[path];
  if (!limit) return true;

  const key = ip + ':' + path;
  const now = Date.now();
  const rec = apiAttempts.get(key);
  if (!rec || now - rec.start > API_RATE_WINDOW) {
    apiAttempts.set(key, { count: 1, start: now });
    return true;
  }
  rec.count++;
  return rec.count <= limit;
}

// --- Main Handler ----------------------------------------------
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const pathname = url.pathname;

  // -- 1. Block sensitive paths with a generic 404 --
  if (isBlockedPath(pathname)) {
    return new Response('<!DOCTYPE html><html><head><title>404</title></head><body><h1>404 — Not Found</h1></body></html>', {
      status: 404,
      headers: {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff',
        'X-Robots-Tag': 'noindex, nofollow',
      },
    });
  }

  // -- 2. API rate limiting --
  if (pathname.startsWith('/api/')) {
    const ip = context.request.headers.get('cf-connecting-ip') ||
               context.request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
               'unknown';
    const routeKey = Object.keys(API_RATE_LIMITS).find(k => pathname.startsWith(k)) || pathname;
    if (!apiRateCheck(ip, routeKey)) {
      return Response.json(
        { error: 'Rate limit exceeded. Try again shortly.' },
        {
          status: 429,
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-store',
            'Retry-After': '60',
            ...SEC_HEADERS,
          },
        }
      );
    }
  }

  // -- 3. Token-gated pages --
  if (isProtected(pathname)) {
    const token = url.searchParams.get('t');
    const secret = context.env.LINK_SECRET;
    const expectedPage = getPage(pathname);

    if (!secret) {
      return new Response('Access configuration error', {
        status: 500,
        headers: { ...SEC_HEADERS, 'Cache-Control': 'no-store' },
      });
    }

    if (await verifyToken(token, secret, expectedPage)) {
      const response = await context.next();
      const newHeaders = new Headers(response.headers);
      Object.entries(SEC_HEADERS).forEach(([k, v]) => newHeaders.set(k, v));
      newHeaders.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
      newHeaders.set('Referrer-Policy', 'no-referrer');
      return new Response(response.body, {
        status: response.status,
        headers: newHeaders,
      });
    }

    return new Response(DENIED_HTML, {
      status: 403,
      headers: {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-store',
        ...SEC_HEADERS,
      },
    });
  }

  // -- 3. Pass through all other requests --
  return context.next();
}

const DENIED_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Access Restricted — lateralus.dev</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Share+Tech+Mono&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:#0a0a1a;color:#e0e0e0;
  font-family:'Inter',sans-serif;
  overflow:hidden;
}
.scanlines{
  position:fixed;inset:0;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,255,255,.015) 2px,rgba(0,255,255,.015) 4px);
  pointer-events:none;z-index:100;
}
.container{
  text-align:center;padding:3rem;
  background:rgba(17,17,40,.7);
  border:1px solid rgba(0,255,255,.12);
  border-radius:16px;
  backdrop-filter:blur(12px);
  max-width:480px;
}
.lock{font-size:4rem;margin-bottom:1rem;filter:drop-shadow(0 0 20px rgba(0,255,255,.3))}
h1{
  font-family:'Orbitron',monospace;font-size:1.5rem;font-weight:900;
  background:linear-gradient(135deg,#a855f7,#06b6d4);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;margin-bottom:.5rem;
}
.code{
  font-family:'Share Tech Mono',monospace;font-size:3rem;font-weight:700;
  color:rgba(0,255,255,.25);margin-bottom:1rem;
}
p{color:#8888aa;font-size:.9rem;line-height:1.6;margin-bottom:1.5rem}
.home{
  display:inline-block;padding:.6rem 1.5rem;
  font-family:'Share Tech Mono',monospace;font-size:.85rem;
  color:#06b6d4;border:1px solid rgba(6,182,212,.3);border-radius:8px;
  text-decoration:none;transition:all .2s;
}
.home:hover{background:rgba(6,182,212,.08);border-color:#06b6d4}
</style>
</head>
<body>
<div class="scanlines"></div>
<div class="container">
  <div class="lock">🔒</div>
  <div class="code">403</div>
  <h1>ACCESS RESTRICTED</h1>
  <p>This page requires an authorized link.<br>If you were given a link and it has expired, please request a new one.</p>
  <a href="/" class="home">← lateralus.dev</a>
</div>
</body>
</html>`;
