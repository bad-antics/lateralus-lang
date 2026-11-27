# Lateralus Static Package Registry (`tools/registry/`)

A zero-server, static-file package registry for Lateralus designed to be hosted directly on **Cloudflare Pages**, **Cloudflare R2**, **Amazon S3**, or any static file server.

## Directory Layout

```text
tools/registry/
  _headers                                  # Cloudflare Pages / R2 CORS & caching rules
  index.json                                # Global package index with SHA-256 pins
  packages/
    <name>/
      <name>-<version>.tar.gz               # Reproducible PAX/gzip tarball (mtime=0)
```

## Commands

### 1. Publish a Package (`lateralus publish`)

Reads `lateralus.toml`, packs the project deterministically (`mtime=0`, sorted entries, normalized tar permissions), computes its reproducible `sha256-<hex>` digest, and uploads both the tarball and updated `index.json` to the configured registry:

```bash
# Preview bundle contents and reproducible SHA-256 without uploading
python -m lateralus_lang publish --dry-run

# Publish to a local static directory, S3 bucket, or HTTP/R2 endpoint
python -m lateralus_lang publish --registry ./tools/registry
python -m lateralus_lang publish --registry s3://my-lateralus-registry
python -m lateralus_lang publish --registry https://registry.lateralus.dev
```

You can also configure the registry URL via `LATERALUS_REGISTRY_URL` or in `lateralus.toml`:

```toml
[registry]
url = "https://registry.lateralus.dev"
```

### 2. Add & Vendor a Dependency (`lateralus add <name>`)

Fetches `index.json` from the registry, resolves the highest compatible SemVer version, downloads the `.tar.gz` archive, verifies its SHA-256 digest against the pinned hash, unpacks it into `vendor/<name>/`, and records the pinned SHA-256 in `lateralus-lock.json`:

```bash
python -m lateralus_lang add ltl-hello --registry ./tools/registry
```

### 3. Rebuild Static Index

```bash
python -m tools.registry.registry rebuild ./tools/registry
```
