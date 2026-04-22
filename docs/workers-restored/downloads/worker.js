/**
 * LateralusOS / NullSec Downloads Worker
 * Serves ISOs and release assets from the lateralus-downloads R2 bucket
 * at https://downloads.lateralus.dev/<filename>
 *
 * Copyright (c) 2025 bad-antics. All rights reserved.
 */

// Known downloadable assets — anything not in this list is denied
const ALLOWED_FILES = new Set([
  // LateralusOS editions
  'lateralus-os-research-x86_64.iso',
  'lateralus-os-workstation-x86_64.iso',
  'lateralus-os-industrial-x86_64.iso',
  'lateralus-os-embedded-x86_64.iso',
  'lateralus-os-cloud-x86_64.iso',
  'lateralus-os-developer-x86_64.iso',
  'lateralus-os-daily-driver-x86_64.iso',
  // LateralusOS checksums
  'lateralus-os-checksums.txt',
  // NullSec Linux ISOs
  'nullsec-linux-desktop-2.1.0-x86_64.iso',
  'nullsec-linux-desktop-2.1.0-x86_64.iso.sha256',
  'nullsec-linux-server-2.1.0-x86_64.iso',
  'nullsec-linux-server-2.1.0-x86_64.iso.sha256',
  'nullsec-linux-arm64-2.1.0-aarch64.iso',
  'nullsec-linux-arm64-2.1.0-aarch64.iso.sha256',
  'nullsec-linux-pi-2.1.0-aarch64.img.xz',
  'nullsec-linux-pi-2.1.0-aarch64.img.xz.sha256',
  'nullsec-linux-micro-2.1.0-x86_64.iso',
  'nullsec-linux-micro-2.1.0-x86_64.iso.sha256',
  // NullSec checksums
  'nullsec-checksums.txt',
  // SDK tarballs
  'lateralus-sdk-0.5.0-linux-x86_64.tar.gz',
  'lateralus-sdk-0.5.0-macos-arm64.tar.gz',
  'lateralus-sdk-0.5.0-win-x64.zip',
]);

// Content types by extension
const MIME = {
  '.iso':     'application/octet-stream',
  '.img':     'application/octet-stream',
  '.img.xz':  'application/x-xz',
  '.xz':      'application/x-xz',
  '.tar.gz':  'application/gzip',
  '.tgz':     'application/gzip',
  '.zip':     'application/zip',
  '.txt':     'text/plain; charset=utf-8',
  '.sha256':  'text/plain; charset=utf-8',
};

function getMime(filename) {
  for (const [ext, type] of Object.entries(MIME)) {
    if (filename.endsWith(ext)) return type;
  }
  return 'application/octet-stream';
}

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
  'Access-Control-Allow-Headers': 'Range',
  'Access-Control-Expose-Headers': 'Content-Length, Content-Range, Accept-Ranges',
};

const SEC_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'no-referrer',
};

function errorResponse(status, message) {
  return new Response(
    `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${status} — downloads.lateralus.dev</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&family=JetBrains+Mono:wght@400;700&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --lime:#00ff41;--hot-pink:#ff00aa;--cyber-blue:#00ccff;
  --yellow:#ffee00;--purple:#6600cc;--bg:#0a001a;--bg2:#110028;
  --border:#9966ff;--text:#e0e0ff;--text2:#9999bb;
}
body{
  min-height:100vh;display:flex;flex-direction:column;align-items:center;
  justify-content:center;background:var(--bg);color:var(--text);
  font-family:'VT323',monospace;font-size:18px;
}
/* scanlines */
body::before{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:9999;
  background:repeating-linear-gradient(0deg,transparent 0px,transparent 2px,rgba(0,0,0,.12) 2px,rgba(0,0,0,.12) 4px);
}
/* grid bg */
body::after{
  content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;
  background:linear-gradient(90deg,rgba(0,255,65,.03) 1px,transparent 1px),
             linear-gradient(0deg,rgba(0,255,65,.03) 1px,transparent 1px);
  background-size:40px 40px;
}
/* topbar */
.topbar{
  position:fixed;top:0;left:0;right:0;z-index:999;height:48px;
  background:linear-gradient(180deg,#2a0055,#1a0033);
  border-bottom:2px solid;
  border-image:linear-gradient(90deg,var(--hot-pink),var(--cyber-blue),var(--lime)) 1;
  display:flex;align-items:center;padding:0 20px;justify-content:space-between;
}
.topbar-logo{
  font-family:'Press Start 2P',monospace;font-size:11px;color:var(--lime);
  text-decoration:none;text-shadow:0 0 10px rgba(0,255,65,.6);
}
.topbar-logo .pipe{color:var(--yellow)}
.topbar-links{display:flex;gap:4px}
.topbar-links a{
  font-family:'Press Start 2P',monospace;font-size:8px;color:var(--text2);
  padding:5px 9px;border:1px solid transparent;text-decoration:none;transition:all .15s;
}
.topbar-links a:hover{color:var(--lime);border-color:var(--lime);background:rgba(0,255,65,.05)}
@media(max-width:700px){.topbar-links{display:none}}
/* rainbow bar */
.rainbow{height:3px;width:100%;
  background:linear-gradient(90deg,var(--lime),var(--cyber-blue),var(--hot-pink),var(--yellow),var(--lime));
  background-size:200% 100%;animation:shift 3s linear infinite}
@keyframes shift{0%{background-position:0 50%}50%{background-position:100% 50%}100%{background-position:0 50%}}
/* main wrap */
.wrap{
  flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:80px 24px 40px;text-align:center;width:100%;max-width:660px;
}
/* 404 number */
.code{
  font-family:'Press Start 2P',monospace;
  font-size:clamp(56px,14vw,112px);line-height:1;margin-bottom:8px;
  background:linear-gradient(90deg,var(--hot-pink),var(--cyber-blue),var(--yellow),var(--lime));
  background-size:300% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;animation:shift 3s linear infinite;
  filter:drop-shadow(0 0 24px rgba(255,0,170,.3));position:relative;
}
.code::before,.code::after{
  content:'${status}';position:absolute;top:0;left:0;right:0;
  background:inherit;-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.code::before{animation:ga 2.4s steps(2) infinite;clip-path:polygon(0 15%,100% 15%,100% 35%,0 35%)}
.code::after{animation:gb 2.8s steps(2) infinite;clip-path:polygon(0 55%,100% 55%,100% 75%,0 75%)}
@keyframes ga{0%,100%{transform:translate(0)}20%{transform:translate(-4px,1px)}40%{transform:translate(4px,-1px)}60%{transform:translate(-2px,2px)}80%{transform:translate(3px,-2px)}}
@keyframes gb{0%,100%{transform:translate(0)}15%{transform:translate(3px,-2px)}45%{transform:translate(-3px,1px)}65%{transform:translate(2px,-1px)}85%{transform:translate(-2px,2px)}}
.subtitle{
  font-family:'Press Start 2P',monospace;font-size:clamp(9px,2vw,14px);
  color:var(--yellow);text-shadow:0 0 10px rgba(255,238,0,.5);
  margin-bottom:6px;letter-spacing:2px;
}
.label{font-size:20px;color:var(--text2);margin-bottom:36px}
/* window */
.window{
  width:100%;background:#1a0033;border:2px solid var(--border);
  box-shadow:inset 1px 1px 0 rgba(255,255,255,.08),4px 4px 0 rgba(0,0,0,.5);
  margin-bottom:32px;text-align:left;
}
.win-title{
  background:linear-gradient(90deg,#3300aa,#6600cc,#3300aa);
  padding:5px 12px;display:flex;align-items:center;justify-content:space-between;
  font-family:'Press Start 2P',monospace;font-size:9px;color:#fff;
  border-bottom:2px solid var(--border);
}
.win-btns{display:flex;gap:4px}
.win-btns span{
  width:13px;height:13px;display:inline-block;border:1px solid rgba(255,255,255,.3);
  background:#110028;font-size:9px;text-align:center;line-height:11px;color:var(--text2);
}
.win-body{
  padding:18px 22px;font-family:'JetBrains Mono',monospace;font-size:13px;line-height:1.9;color:var(--text2);
}
.p{color:var(--lime)}.c{color:var(--cyber-blue)}.e{color:var(--hot-pink)}.g{color:var(--lime)}.d{color:#555577}
/* cursor */
.cur{
  display:inline-block;width:9px;height:14px;background:var(--lime);
  animation:blink 1s step-end infinite;vertical-align:text-bottom;margin-left:2px;
}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
/* nav grid */
.nav{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));
  gap:10px;width:100%;margin-bottom:28px;
}
.nav a{
  font-family:'Press Start 2P',monospace;font-size:8px;padding:11px 6px;
  border:2px solid var(--border);background:#110028;color:var(--text2);
  text-align:center;text-decoration:none;transition:all .15s;
  box-shadow:3px 3px 0 rgba(0,0,0,.4);
}
.nav a:hover{border-color:var(--lime);color:var(--lime);background:rgba(0,255,65,.05);text-shadow:0 0 5px rgba(0,255,65,.5)}
/* buttons */
.btn{
  display:inline-block;font-family:'Press Start 2P',monospace;font-size:10px;
  padding:11px 22px;border:2px outset var(--border);
  background:linear-gradient(180deg,#3a0077,#220044);color:var(--lime);
  cursor:pointer;text-decoration:none;transition:all .15s;
  text-shadow:0 0 6px rgba(0,255,65,.4);
}
.btn:hover{border-style:inset;color:var(--yellow);text-shadow:0 0 10px rgba(255,238,0,.6)}
.btn.pink{color:var(--hot-pink);text-shadow:0 0 6px rgba(255,0,170,.4)}
.btn.pink:hover{color:var(--yellow)}
.btns{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:36px}
/* Y2K strip */
.strip{display:flex;align-items:center;justify-content:center;gap:20px;flex-wrap:wrap}
.starburst{
  display:inline-flex;align-items:center;justify-content:center;
  width:48px;height:48px;
  clip-path:polygon(50% 0%,61% 35%,98% 35%,68% 57%,79% 91%,50% 70%,21% 91%,32% 57%,2% 35%,39% 35%);
  color:#000;font-family:'Press Start 2P',monospace;font-size:5px;
  animation:spin 10s linear infinite;text-align:center;line-height:1.1;flex-shrink:0;
}
@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
.hit{display:inline-flex;align-items:center;gap:8px;font-family:'Press Start 2P',monospace;font-size:7px;color:var(--text2)}
.hit .ctr{background:#000;border:2px inset #666;padding:2px 10px;font-family:'VT323',monospace;font-size:20px;color:var(--lime);letter-spacing:4px}
/* footer */
footer{border-top:1px solid #330066;padding:20px;text-align:center;width:100%}
footer .links{display:flex;justify-content:center;flex-wrap:wrap;gap:16px;margin-bottom:10px}
footer .links a{font-family:'Press Start 2P',monospace;font-size:8px;color:var(--text2);text-decoration:none}
footer .links a:hover{color:var(--lime)}
footer p{font-size:14px;color:var(--text2)}
/* floaters */
.fl{position:fixed;pointer-events:none;z-index:1;opacity:.06;color:var(--border);animation:fy 18s ease-in-out infinite}
@keyframes fy{0%,100%{transform:translateY(0) rotate(0deg)}33%{transform:translateY(-14px) rotate(3deg)}66%{transform:translateY(10px) rotate(-2deg)}}
</style>
</head>
<body>
<div class="fl" style="top:14%;left:3%;font-size:38px">✦</div>
<div class="fl" style="top:62%;right:4%;font-size:28px;animation-delay:5s">◇</div>
<div class="fl" style="top:80%;left:7%;font-size:32px;animation-delay:9s">◉</div>
<div class="fl" style="top:38%;right:3%;font-size:24px;animation-delay:2s">⬡</div>
<nav class="topbar">
  <a href="https://lateralus.dev/" class="topbar-logo"><span class="pipe">|&gt;</span> LATERALUS</a>
  <div class="topbar-links">
    <a href="https://lateralus.dev/">HOME</a>
    <a href="https://lateralus.dev/playground/">PLAYGROUND</a>
    <a href="https://lateralus.dev/os/">OS</a>
    <a href="https://lateralus.dev/download/">DOWNLOAD</a>
    <a href="https://lateralus.dev/blog/">BLOG</a>
    <a href="https://github.com/bad-antics/lateralus-lang" target="_blank" rel="noopener">GITHUB</a>
  </div>
</nav>
<div class="rainbow"></div>
<div class="wrap">
  <div class="code" aria-label="${status}">${status}</div>
  <div class="subtitle">FILE NOT FOUND</div>
  <div class="label">${message.toLowerCase()} — the requested asset is not available</div>
  <div class="rainbow" style="width:100%;max-width:540px;margin:0 auto 28px"></div>
  <div class="window">
    <div class="win-title">
      ◇ ltlsh — downloads.lateralus.dev
      <div class="win-btns"><span>—</span><span>□</span><span>×</span></div>
    </div>
    <div class="win-body">
      <div><span class="p">$</span> <span class="c">fetch downloads.lateralus.dev</span></div>
      <div><span class="e">✘ HTTP ${status} — ${message}</span></div>
      <div><span class="d">  at r2::resolve() → object not found in bucket</span></div>
      <div>&nbsp;</div>
      <div><span class="p">$</span> <span class="c">suggest --fix</span></div>
      <div><span class="g">→ check the URL for typos</span></div>
      <div><span class="g">→ browse all releases at lateralus.dev/download/</span></div>
      <div>&nbsp;</div>
      <div><span class="p">$</span> <span class="cur"></span></div>
    </div>
  </div>
  <div class="nav">
    <a href="https://lateralus.dev/download/">↓ DOWNLOAD</a>
    <a href="https://lateralus.dev/">⌂ HOME</a>
    <a href="https://lateralus.dev/os/">⬡ OS</a>
    <a href="https://lateralus.dev/playground/">▶ PLAY</a>
  </div>
  <div class="btns">
    <a href="https://lateralus.dev/download/" class="btn">↓ ALL DOWNLOADS</a>
    <a href="https://lateralus.dev/" class="btn pink">⌂ HOME</a>
  </div>
  <div class="strip">
    <div class="starburst" style="background:#ffee00">NEW<br>SOON</div>
    <div class="hit">ERRORS TODAY <span class="ctr">000${status}</span></div>
    <div class="starburst" style="background:#ff00aa;animation-direction:reverse">${status}<br>ERR</div>
  </div>
</div>
<footer>
  <div class="links">
    <a href="https://lateralus.dev/playground/">PLAYGROUND</a>
    <a href="https://lateralus.dev/blog/">BLOG</a>
    <a href="https://lateralus.dev/os/">OS</a>
    <a href="https://lateralus.dev/download/">DOWNLOAD</a>
    <a href="https://github.com/bad-antics/lateralus-lang">GITHUB</a>
  </div>
  <p>© 2024 lateralus.dev — Made with <span style="color:#ff00aa">♥</span> and pipelines</p>
</footer>
</body>
</html>`,
    {
      status,
      headers: {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-store',
        ...SEC_HEADERS,
      },
    }
  );
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const method = request.method.toUpperCase();

    // Handle CORS preflight
    if (method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    // Only allow GET and HEAD
    if (method !== 'GET' && method !== 'HEAD') {
      return errorResponse(405, 'Method Not Allowed');
    }

    // Root: redirect to download page
    const path = url.pathname;
    if (path === '/' || path === '') {
      return Response.redirect('https://lateralus.dev/download/', 302);
    }

    // Extract filename (strip leading /)
    const filename = path.slice(1);

    // Block directory traversal attempts
    if (filename.includes('..') || filename.includes('/') || filename.startsWith('.')) {
      return errorResponse(400, 'Invalid Request');
    }

    // Only serve allowed files
    if (!ALLOWED_FILES.has(filename)) {
      return errorResponse(404, 'File Not Found');
    }

    // Look up in R2 — try direct object first, then chunked manifest
    let object;
    try {
      object = await env.DOWNLOADS.get(filename);
    } catch (e) {
      console.error('R2 error:', e);
      return errorResponse(503, 'Storage Unavailable');
    }

    // ── Chunked file serving ─────────────────────────────────────────────────
    // If direct object not found, check for a split-upload manifest
    if (!object) {
      let manifest;
      try {
        const mObj = await env.DOWNLOADS.get(`${filename}.manifest`);
        if (mObj) manifest = JSON.parse(await mObj.text());
      } catch (_) {}

      if (!manifest) return errorResponse(404, 'File Not Found');

      // Serve all parts concatenated as a single stream
      const { parts, size: totalSize } = manifest;
      const contentType = getMime(filename);

      const headers = new Headers({
        'Content-Type': contentType,
        'Content-Length': String(totalSize),
        'Content-Disposition': `attachment; filename="${filename}"`,
        'Accept-Ranges': 'none',
        'Cache-Control': 'public, max-age=86400',
        ...CORS_HEADERS,
        ...SEC_HEADERS,
      });

      if (method === 'HEAD') return new Response(null, { status: 200, headers });

      // Create a ReadableStream that yields all parts sequentially
      const { readable, writable } = new TransformStream();
      const writer = writable.getWriter();

      (async () => {
        for (let i = 0; i < parts; i++) {
          const partKey = `${filename}.part${i}`;
          const part = await env.DOWNLOADS.get(partKey);
          if (!part) { writer.close(); return; }
          const reader = part.body.getReader();
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            await writer.write(value);
          }
        }
        writer.close();
      })();

      return new Response(readable, { status: 200, headers });
    }
    // ── End chunked serving ──────────────────────────────────────────────────

    const contentType = getMime(filename);
    const size = object.size;

    // Build response headers
    const headers = new Headers({
      'Content-Type': contentType,
      'Content-Length': String(size),
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'public, max-age=86400',
      'ETag': object.etag ?? `"${filename}"`,
      'Last-Modified': object.uploaded?.toUTCString() ?? new Date().toUTCString(),
      ...CORS_HEADERS,
      ...SEC_HEADERS,
    });

    // Support Range requests (important for large ISOs / resume support)
    const rangeHeader = request.headers.get('Range');
    if (rangeHeader && method === 'GET') {
      const match = rangeHeader.match(/^bytes=(\d+)-(\d*)$/);
      if (match) {
        const start = parseInt(match[1], 10);
        const end = match[2] ? parseInt(match[2], 10) : size - 1;
        if (start > end || end >= size) {
          return new Response(null, {
            status: 416,
            headers: { 'Content-Range': `bytes */${size}` },
          });
        }
        const rangeObj = await env.DOWNLOADS.get(filename, {
          range: { offset: start, length: end - start + 1 },
        });
        if (!rangeObj) return errorResponse(503, 'Storage Unavailable');
        headers.set('Content-Range', `bytes ${start}-${end}/${size}`);
        headers.set('Content-Length', String(end - start + 1));
        return new Response(rangeObj.body, { status: 206, headers });
      }
    }

    // HEAD request — headers only
    if (method === 'HEAD') {
      return new Response(null, { status: 200, headers });
    }

    // Full GET
    return new Response(object.body, { status: 200, headers });
  },
};
