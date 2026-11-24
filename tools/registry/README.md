# Static package registry

A Lateralus package registry is a directory. Not a service, not a daemon, not a
database — a directory that a static host serves over HTTP.

```
<registry-root>/
    index.json                                every package, every version
    packages/
        hello/
            hello-0.1.0.tar.gz
            hello-0.2.0.tar.gz
        another/
            another-1.0.0.tar.gz
```

Two files matter: `index.json`, and one `.tar.gz` per published version. Nothing
is generated at request time, so a bucket, a CDN, or a USB stick all work.

## Why no server

A registry that needs a server needs someone to run it, patch it, pay for it, and
get woken up when it falls over. A registry that is a bucket needs none of that,
and an S3 bucket is faster and cheaper than anything you would write in Python.

The trade-off is that publishing is not atomic: the archive is uploaded first,
then `index.json` is replaced. If the second step fails, the registry has an
orphaned archive that nothing references — harmless, and `build_index.py`
reconciles it.

## Commands

### Publish

```bash
# Preview the archive without touching the registry
lateralus publish --dry-run

# Publish into a directory (a mounted bucket, a git repo, a local path)
lateralus publish --registry-path /srv/lateralus-registry

# Publish over HTTP PUT
lateralus publish --registry-url https://pkg.example.com
```

Configure it once in `lateralus.toml` instead of passing flags:

```toml
[registry]
url = "https://pkg.example.com"
```

The auth token is **not** read from the manifest — a token in a committed file is
a leaked token. Set `LATERALUS_REGISTRY_TOKEN` in the environment; it is sent as
`Authorization: Bearer <token>`.

### Install

```bash
lateralus add hello                      # newest version
lateralus add hello --version "^0.1.0"   # semver constraint
```

`add` resolves the constraint against `index.json`, downloads the archive,
**verifies the SHA-256 digest recorded in the index**, and only then unpacks into
`vendor/<name>-<version>/`. A digest mismatch aborts before anything is written
to disk. The resolved version and digest are pinned in `lateralus-lock.json`.

Supported constraints: `*`, exact (`1.2.3`), `^1.2.3`, `~1.2.3`, `>=`, `>`,
`<=`, `<`, and conjunctions (`>=1.0.0 <2.0.0`). This is deliberately a subset —
anything more belongs in the resolver, not in the fetch path.

### Rebuild the index

```bash
python tools/registry/build_index.py /srv/lateralus-registry
python tools/registry/build_index.py /srv/lateralus-registry --check
```

Use it after copying a registry between hosts, after deleting a bad version by
hand, or in CI as a drift gate. `--check` exits non-zero when `index.json`
disagrees with the archives on disk, which catches a half-finished upload before
anyone installs from it.

### Local development server

```bash
python tools/registry/serve.py /tmp/registry --port 8777
```

Loopback only, development only, refuses to deploy — it exists so that
`--registry-url` can be exercised without provisioning a bucket.

## Determinism

The digest in `index.json` is only meaningful if the same source tree always
produces the same bytes. Five things have to be pinned, and all five are pinned
in `registry.py`:

| Field | Value | Why |
|---|---|---|
| entry order | sorted by path | filesystem iteration order differs by OS |
| `mtime` | `0` | checkout time, not content |
| `uid` / `gid` / `uname` / `gname` | `0` / empty | publishing machine identity |
| file mode | `0o644` | whether the author's umask had the exec bit |
| gzip header `mtime` | `0`, no embedded filename | same reason as tar `mtime` |

The consequence: publishing the same tree from two machines gives one digest,
and re-publishing unchanged content returns `unchanged` instead of churning the
index.

## What goes into an archive

An explicit include list, not "everything minus exclusions" — a stray 400 MB
fixture should not be publishable by putting it in the wrong directory:

```
lateralus.toml, lateralus.json,
README.md, README.*.md, LICENSE, LICENSE.*,
*.ltl, src/**/*.ltl, lib/**/*.ltl, tests/**/*.ltl, examples/**/*.ltl,
docs/**/*.md, docs/**/*.ltl, docs/**/*.ltlm
```

`vendor/`, `__pycache__/`, `.git/`, `node_modules/`, `dist/` and friends are
excluded even if a glob would reach them.

Note `*.ltl` at the root: the scaffolds put the entry point in `main.ltl` at the
project root, and a package that publishes everything except its own entry point
is not a package.

## Deploying

**Cloudflare R2 / Pages**

```bash
lateralus publish --registry-path ./registry
wrangler pages deploy ./registry
```

**AWS S3**

```bash
lateralus publish --registry-path ./registry
aws s3 sync ./registry s3://my-bucket --delete
```

Point consumers at the bucket URL:

```toml
[registry]
url = "https://my-bucket.s3.amazonaws.com"
```

**nginx**

```nginx
location / {
    root /srv/lateralus-registry;
    autoindex off;
}
```

Publishing over `--registry-url` requires the host to accept `PUT`. S3 and Pages
do not, by default — publish to a local path and sync, which is also what you
want in CI because it gives you a reviewable diff before anything goes public.

## Limits

- Extraction accepts regular files only. Symlinks, hardlinks, devices and
  directory records are rejected, and any path that resolves outside the
  destination aborts the whole unpack. A package that ships a symlink to
  `/etc/passwd` fails rather than succeeding dangerously.
- Unpacked size is capped at 64 MB per package.
- Real HTTP uploads are subject to that cap as well; `serve.py` rejects larger
  bodies with 413.
- There is no authentication story beyond a bearer token. If a registry must be
  private, use a private bucket and presigned URLs, not a token in a manifest.
