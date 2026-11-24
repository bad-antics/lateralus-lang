# LATERALUS Package Registry (MVP)

A **static**, S3 / R2 / Cloudflare-Pages-compatible package registry for
LATERALUS. No server required — the registry is a directory of files.

Implements the [`[bounty] package-registry-mvp`](../../BOUNTIES.md) scope.

## Layout

```
registry/
  index.json                         # catalog of every published version
  packages/
    <name>/
      <name>-<version>.tar.gz        # reproducible package tarball
```

`index.json`:

```json
{
  "registry_version": 1,
  "packages": {
    "math-ext": {
      "versions": {
        "1.2.0": {
          "tarball": "packages/math-ext/math-ext-1.2.0.tar.gz",
          "integrity": "sha256-0123…",
          "size": 4821,
          "dependencies": {},
          "lateralus_version": ">=1.7.0"
        }
      }
    }
  }
}
```

## Publishing

From a project directory containing a `lateralus.toml`:

```bash
# Publish to a local registry directory (also works with file:// URLs)
lateralus publish --registry ./registry

# Preview without writing anything
lateralus publish --registry ./registry --dry-run

# Publish to an S3 / R2 bucket (requires the AWS CLI, uses `aws s3 cp`)
LATERALUS_REGISTRY=s3://my-bucket/registry lateralus publish
```

`lateralus publish` packs the project into a **byte-for-byte reproducible**
`.tar.gz` (sorted file list, zeroed mtimes, normalised ownership, timestamp-free
gzip header), computes its SHA-256 digest, writes the tarball under
`packages/<name>/`, and records the version + integrity in `index.json`.

## Consuming

```bash
# Fetch math-ext, verify its SHA-256 against index.json, unpack into ./vendor
lateralus add math-ext

# Pin a version spec (semver: ^, ~, >=, exact, *)
lateralus add math-ext --version "^1.0.0" --registry ./registry
```

`lateralus add <name>`:

1. Reads `index.json` from the configured registry (`--registry`, else
   `$LATERALUS_REGISTRY`, else `https://registry.lateralus.dev`).
2. Resolves the highest version satisfying the requested spec.
3. Downloads the tarball and **verifies its SHA-256** against the pinned digest.
   A mismatch aborts the install with an integrity error.
4. Safely unpacks into `vendor/<name>/` (rejects absolute / `..` paths).
5. Records the resolved version + integrity in `lateralus-lock.json` so future
   installs are reproducible.

## Hosting

Because the output is 100% static:

* **Cloudflare Pages** — commit `registry/` to a Pages project.
* **Amazon S3** — `aws s3 sync registry/ s3://bucket/registry/`.
* **Cloudflare R2** — same as S3 with an R2 bucket + public URL.

Then point clients at it with `LATERALUS_REGISTRY=<url>` or `--registry <url>`.

## Helper script

`tools/registry/publish.py` is a thin wrapper around
`lateralus_lang.registry.main` so the registry can be driven straight from a
checkout without installing the package:

```bash
python3 tools/registry/publish.py publish --registry ./registry
python3 tools/registry/publish.py add math-ext --registry ./registry
```

## Tests

The end-to-end suite lives at `tests/test_registry.py` and exercises the full
`publish → add → integrity-verify` round-trip, determinism, tamper detection,
version resolution, and safe extraction.