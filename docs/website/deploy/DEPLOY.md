# Deploying lateralus.dev with the Lateralus Server

This document covers deploying the hardened Lateralus-native web server
(`server.ltl`) so the site resolves correctly for all visitors.

---

## Prerequisites

```
pip install lateralus-lang
```

## 1. Compile the Server

```bash
lateralus compile server.ltl --target c99 -o lateralus-server
```

This produces a statically linked binary with no external dependencies.

## 2. Prepare the Server

```bash
# Create service user
sudo useradd -r -s /usr/sbin/nologin lateralus

# Create directory structure
sudo mkdir -p /srv/lateralus.dev/{public,logs}
sudo cp lateralus-server /srv/lateralus.dev/
sudo cp -r *.html *.css *.js *.svg *.xml sitemap.xml robots.txt \
           blog/ os/ playground/ papers/ me/ resume/ share/ \
           /srv/lateralus.dev/public/

# Configure secrets
sudo cp deploy/.env.example /srv/lateralus.dev/.env
sudo chmod 600 /srv/lateralus.dev/.env
sudo nano /srv/lateralus.dev/.env   # fill in LINK_SECRET and ADMIN_PASS
```

## 3. TLS Certificates

### Option A: Direct TLS (server.ltl handles TLS)

```bash
sudo certbot certonly --standalone -d lateralus.dev -d www.lateralus.dev
```

Set `TLS_CERT` and `TLS_KEY` in `.env` to the cert paths.

### Option B: Caddy reverse proxy (recommended for auto-renewal)

```bash
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl restart caddy
```

Remove `TLS_CERT` / `TLS_KEY` from `.env` and bind to a high port instead.

## 4. DNS Records

Point your domain at the server so browsers resolve it:

| Type  | Name              | Value           | Proxy  |
|-------|-------------------|-----------------|--------|
| A     | lateralus.dev     | `<SERVER_IP>`   | —      |
| A     | www.lateralus.dev | `<SERVER_IP>`   | —      |
| AAAA  | lateralus.dev     | `<SERVER_IPv6>` | —      |
| AAAA  | www.lateralus.dev | `<SERVER_IPv6>` | —      |

If staying on Cloudflare, orange-cloud the records and set SSL mode to **Full (Strict)**.

## 5. Install & Start the Service

```bash
sudo cp deploy/lateralus-dev.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lateralus-dev
sudo systemctl status lateralus-dev
```

## 6. Verify

```bash
# Should return 200 with all security headers
curl -I https://lateralus.dev/

# Check HSTS
curl -sI https://lateralus.dev/ | grep Strict

# Check CSP
curl -sI https://lateralus.dev/ | grep Content-Security-Policy

# Protected page without token should be 403
curl -sI https://lateralus.dev/me/

# Generate a token and verify access
curl -s -X POST https://lateralus.dev/api/share \
  -H 'Content-Type: application/json' \
  -d '{"password":"YOUR_ADMIN_PASS","page":"me","expiry":"1h"}'
```

## Security Summary

| Layer | Protection |
|-------|-----------|
| Transport | TLS 1.2/1.3 only, strong cipher suites, HSTS preload, OCSP stapling |
| Headers | CSP (no unsafe-inline), COOP, CORP, COEP, X-Frame-Options DENY |
| Auth | HMAC-SHA256 signed, page-bound, time-limited tokens |
| Passwords | Timing-safe comparison via double-HMAC |
| Rate limit | Per-IP, 5 attempts / 15 min, 1-hour lockout |
| Traversal | Path canonicalization + realpath jail |
| Methods | Strict allowlist (GET, HEAD, POST, OPTIONS) |
| Payload | 1KB limit on API, 64KB global limit |
| Process | systemd sandboxing, no-new-privs, read-only filesystem |
| Bots | robots.txt blocks all AI scrapers |
| Redirect | HTTP→HTTPS, www→apex, legacy paths |
