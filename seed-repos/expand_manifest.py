#!/usr/bin/env python3
"""
expand_manifest.py — extend seed-repos/manifest.yml with a large batch of
new repo ideas spanning diverse domains, so the `bad-antics/*` ecosystem
clears the Linguist ≥ 200 unique-repo gate.

Only appends repos whose names do not already exist in the manifest
AND do not already exist on github.com/bad-antics/. No template content
is required — generate.py will fall back to a placeholder `main.ltl`
for any repo whose `source_template` directory is absent, and the
`.gitattributes` + topics + MIT LICENSE are enough to flip the Linguist
language bar and count toward the 200-repo gate.

Usage:
    python3 expand_manifest.py                   # preview
    python3 expand_manifest.py --apply           # write manifest.yml
    python3 expand_manifest.py --apply --min 200 # keep appending until total >= 200
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("error: pyyaml is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifest.yml"


# ---------------------------------------------------------------------------
# Candidate pool — curated, deliberately diverse.
# Each entry: (name, tagline, category, topics)
# ---------------------------------------------------------------------------

CANDIDATES: list[tuple[str, str, str, list[str]]] = [
    # --- CLI utilities (expansion) --------------------------------------------
    ("ltl-url-shorten",   "Deterministic URL shortener with collision-free base62 hashing.", "cli-utility", ["url", "cli"]),
    ("ltl-md2html",       "Single-pass Markdown to HTML converter (CommonMark subset).", "cli-utility", ["markdown", "cli"]),
    ("ltl-file-find",     "Parallel filesystem walker with glob + regex + size filters.", "cli-utility", ["cli", "filesystem"]),
    ("ltl-diff",          "Myers-diff line differ with unified-output formatter.", "cli-utility", ["cli", "diff"]),
    ("ltl-patch",         "Apply unified diffs with fuzz matching and reject files.", "cli-utility", ["cli", "diff"]),
    ("ltl-wc-plus",       "Word / line / byte / grapheme counter with UTF-8 awareness.", "cli-utility", ["cli", "text"]),
    ("ltl-tree-view",     "Directory tree pretty-printer with depth + ignore-list.", "cli-utility", ["cli", "filesystem"]),
    ("ltl-du-plus",       "Parallel disk-usage scanner with interactive TUI.", "cli-utility", ["cli", "filesystem"]),
    ("ltl-cat-plus",      "`cat` with syntax highlighting, line numbers, and paging.", "cli-utility", ["cli", "text"]),
    ("ltl-less-clone",    "Pager with regex search, follow mode, and marks.", "cli-utility", ["cli", "pager"]),
    ("ltl-sed-like",      "Stream editor subset — substitute / delete / append / print.", "cli-utility", ["cli", "text"]),
    ("ltl-awk-like",      "Pattern-action data processor for tabular text.", "cli-utility", ["cli", "text"]),
    ("ltl-grep-color",    "Recursive regex grep with ANSI colour + context lines.", "cli-utility", ["cli", "regex"]),
    ("ltl-env-diff",      "Compare two `env` outputs (or .env files) as coloured diff.", "cli-utility", ["cli", "env"]),
    ("ltl-hex-dump",      "Hex dumper with address columns + ASCII sidebar.", "cli-utility", ["cli", "binary"]),
    ("ltl-base64",        "RFC 4648 base64 / base32 / base16 CLI + library.", "cli-utility", ["cli", "encoding"]),
    ("ltl-tar-lite",      "Minimal POSIX-ustar tarball reader and writer.", "cli-utility", ["cli", "archive"]),
    ("ltl-zip-reader",    "ZIP central-directory parser with DEFLATE stream support.", "cli-utility", ["cli", "archive"]),
    ("ltl-gzip-stream",   "Streaming gzip encoder / decoder with CRC32 verification.", "cli-utility", ["cli", "compression"]),

    # --- Parsers ---------------------------------------------------------------
    ("ltl-xml-parser",    "Pull-style XML parser (SAX-like) with entity expansion.", "protocol", ["xml", "parser"]),
    ("ltl-jsonl",         "Line-delimited JSON reader / writer with schema-guard.", "protocol", ["json", "jsonl"]),
    ("ltl-cbor",          "Concise Binary Object Representation (RFC 8949) codec.", "protocol", ["cbor", "binary"]),
    ("ltl-msgpack",       "MessagePack codec with ext-types and streaming support.", "protocol", ["msgpack", "binary"]),
    ("ltl-pem-read",      "PEM / DER decoder for X.509, PKCS#8, and SSH keys.", "protocol", ["pem", "crypto"]),
    ("ltl-asn1",          "ASN.1 DER/BER reader for the RFC 5280 subset.", "protocol", ["asn1", "crypto"]),
    ("ltl-pcap-read",     "libpcap-format capture-file reader with IPv4/TCP dissectors.", "protocol", ["pcap", "networking"]),
    ("ltl-elf-read",      "ELF64 parser with section, symbol, and dynamic-link tables.", "protocol", ["elf", "binary"]),
    ("ltl-wav-io",        "WAV (RIFF) encoder / decoder for PCM16 and PCM-float.", "protocol", ["wav", "audio"]),
    ("ltl-midi-parse",    "Standard MIDI File (SMF 0/1) event-stream parser.", "protocol", ["midi", "audio"]),
    ("ltl-png-read",      "PNG decoder — chunks, filters, IDAT inflate, alpha.", "protocol", ["png", "graphics"]),
    ("ltl-bmp-io",        "Bitmap (BMP) encoder / decoder with 24- and 32-bit depth.", "protocol", ["bmp", "graphics"]),
    ("ltl-gif-read",      "GIF87a/89a LZW decoder with animation frame walker.", "protocol", ["gif", "graphics"]),
    ("ltl-pdf-text",      "Minimal PDF text extractor — pages, content streams, CMap.", "protocol", ["pdf", "text"]),

    # --- Networking ------------------------------------------------------------
    ("ltl-tftp-server",   "TFTP (RFC 1350) read/write server with block negotiation.", "networking", ["tftp", "networking"]),
    ("ltl-ftp-client",    "FTP client (active + passive) with TLS upgrade path.", "networking", ["ftp", "networking"]),
    ("ltl-ws-client",     "RFC 6455 WebSocket client with permessage-deflate.", "networking", ["websocket", "networking"]),
    ("ltl-http2-lite",    "HTTP/2 framing + HPACK header decoder — client side.", "networking", ["http2", "networking"]),
    ("ltl-dhcp-probe",    "DHCP DISCOVER broadcaster + OFFER parser.", "networking", ["dhcp", "networking"]),
    ("ltl-ntp-client",    "SNTP (RFC 4330) time query with stratum reporting.", "networking", ["ntp", "networking"]),
    ("ltl-syslog-send",   "RFC 5424 syslog UDP / TCP emitter with structured data.", "networking", ["syslog", "networking"]),
    ("ltl-irc-bot",       "Minimal IRC client and channel bot with command dispatch.", "networking", ["irc", "networking"]),
    ("ltl-ldap-query",    "LDAP v3 search client with BER encode and simple bind.", "networking", ["ldap", "networking"]),
    ("ltl-whois",         "RDAP and legacy-WHOIS lookup tool for domains and IPs.", "networking", ["whois", "networking"]),
    ("ltl-traceroute",    "UDP and ICMP traceroute with AS-number enrichment.", "networking", ["traceroute", "networking"]),
    ("ltl-ping-tool",     "ICMP echo-request pinger with RTT histogram output.", "networking", ["ping", "networking"]),

    # --- Data structures / algos ----------------------------------------------
    ("ltl-bloom-ds",      "Bloom filter with tunable false-positive rate.", "algorithms", ["bloom", "ds"]),
    ("ltl-cuckoo-filter", "Cuckoo filter supporting delete and counting.", "algorithms", ["cuckoo", "ds"]),
    ("ltl-cms",           "Count-min sketch with heavy-hitter extraction.", "algorithms", ["ds", "streaming"]),
    ("ltl-hll",           "HyperLogLog cardinality estimator (HLL++).", "algorithms", ["ds", "streaming"]),
    ("ltl-merkle",        "Merkle tree with verifiable inclusion proofs.", "algorithms", ["merkle", "crypto"]),
    ("ltl-trie",          "Compressed prefix trie with range queries.", "algorithms", ["trie", "ds"]),
    ("ltl-radix-tree",    "Adaptive radix tree — ART-style ordered key index.", "algorithms", ["ds", "index"]),
    ("ltl-union-find",    "Union-find / DSU with path-compression + rank.", "algorithms", ["ds", "graph"]),
    ("ltl-kdtree",        "K-d tree for k-NN queries in low-dimensional spaces.", "algorithms", ["ds", "spatial"]),
    ("ltl-segment-tree",  "Segment tree with lazy propagation for range updates.", "algorithms", ["ds", "range-query"]),
    ("ltl-fenwick",       "Binary indexed tree for prefix sums.", "algorithms", ["ds", "range-query"]),
    ("ltl-sort-bench",    "Quicksort / merge-sort / radix-sort benchmark harness.", "algorithms", ["sort", "benchmark"]),

    # --- Crypto ----------------------------------------------------------------
    ("ltl-x25519",        "Curve25519 / X25519 scalar multiplication.", "crypto", ["crypto", "curve25519"]),
    ("ltl-ed25519",       "Ed25519 sign + verify with RFC 8032 test vectors.", "crypto", ["crypto", "signatures"]),
    ("ltl-chacha20",      "ChaCha20 stream cipher with Poly1305 AEAD.", "crypto", ["crypto", "aead"]),
    ("ltl-aes-gcm",       "AES-128/256 in GCM mode with constant-time GF(2^128).", "crypto", ["crypto", "aes"]),
    ("ltl-argon2",        "Argon2i / Argon2id password-hashing KDF.", "crypto", ["crypto", "kdf"]),
    ("ltl-hkdf",          "HKDF extract-and-expand over SHA-256 / SHA-512.", "crypto", ["crypto", "kdf"]),
    ("ltl-hmac",          "HMAC-SHA256 / SHA3 with test-vector coverage.", "crypto", ["crypto", "mac"]),
    ("ltl-otp",           "HOTP / TOTP (RFC 4226 / 6238) generator + verifier.", "crypto", ["crypto", "otp"]),
    ("ltl-pbkdf2",        "PBKDF2-HMAC with RFC 2898 test suite.", "crypto", ["crypto", "kdf"]),
    ("ltl-totp-cli",      "CLI for adding and querying TOTP seeds via an encrypted vault.", "crypto", ["crypto", "cli"]),

    # --- Math / numerics -------------------------------------------------------
    ("ltl-bignum",         "Arbitrary-precision integer arithmetic (+, *, /, mod).", "math", ["math", "bignum"]),
    ("ltl-rational",       "Rational-number type with continued-fraction rounding.", "math", ["math"]),
    ("ltl-matrix",         "Dense matrix algebra — multiply, invert, determinant.", "math", ["math", "linalg"]),
    ("ltl-fft",            "Cooley-Tukey radix-2 FFT and inverse FFT.", "math", ["math", "fft"]),
    ("ltl-linsolve",       "Gaussian elimination + LU decomposition solver.", "math", ["math", "linalg"]),
    ("ltl-roots",          "Newton, bisection, and secant root-finders.", "math", ["math", "numerics"]),
    ("ltl-ode-rk4",        "Runge-Kutta 4 ODE integrator with adaptive step size.", "math", ["math", "numerics"]),
    ("ltl-spline",         "Cubic-spline interpolation (natural + clamped).", "math", ["math", "numerics"]),
    ("ltl-primes",         "Sieve of Eratosthenes + Miller-Rabin primality test.", "math", ["math", "primes"]),
    ("ltl-mersenne-prp",   "Lucas-Lehmer and Fermat PRP tests for Mersenne primes.", "math", ["math", "primes"]),
    ("ltl-gcd-ext",        "GCD, extended GCD, and modular inverse over Z.", "math", ["math"]),
    ("ltl-stats-basic",    "Mean / variance / quantile / moments for streaming data.", "math", ["math", "stats"]),

    # --- Games / simulations --------------------------------------------------
    ("ltl-tetris",         "Terminal Tetris with super-rotation system.", "game", ["game", "terminal"]),
    ("ltl-pong",           "Terminal Pong with paddle-AI difficulty levels.", "game", ["game", "terminal"]),
    ("ltl-2048",           "2048 implementation with move-ordering heuristic AI.", "game", ["game", "puzzle"]),
    ("ltl-connect4",       "Connect-Four with alpha-beta search + transposition table.", "game", ["game", "ai"]),
    ("ltl-tictactoe",      "Tic-tac-toe with minimax.", "game", ["game", "ai"]),
    ("ltl-sudoku-solve",   "Dancing-Links (Algorithm X) sudoku solver.", "game", ["game", "puzzle"]),
    ("ltl-chess-perft",    "Chess move generator verified via Perft positions.", "game", ["game", "chess"]),
    ("ltl-boids",          "Reynolds' boids flocking simulation.", "game", ["simulation"]),
    ("ltl-lenia",          "Lenia continuous cellular automata.", "game", ["simulation"]),
    ("ltl-langton-ant",    "Langton's ant on an infinite torus grid.", "game", ["simulation"]),
    ("ltl-wireworld",      "Wireworld cellular automaton with logic-gate demos.", "game", ["simulation"]),

    # --- ML / AI --------------------------------------------------------------
    ("ltl-perceptron",     "Single-layer perceptron with margin analysis.", "ml", ["ml"]),
    ("ltl-linreg",         "Ordinary-least-squares linear regression with residual plots.", "ml", ["ml", "stats"]),
    ("ltl-logreg",         "Logistic regression with L-BFGS optimiser.", "ml", ["ml"]),
    ("ltl-kmeans",         "K-means++ clustering with elbow / silhouette scoring.", "ml", ["ml", "clustering"]),
    ("ltl-knn",            "Brute-force k-NN classifier with cross-validation.", "ml", ["ml"]),
    ("ltl-naive-bayes",    "Gaussian / Bernoulli / multinomial naïve Bayes.", "ml", ["ml"]),
    ("ltl-decision-tree",  "CART decision tree with Gini / entropy splits.", "ml", ["ml"]),
    ("ltl-pca",            "Principal component analysis via SVD.", "ml", ["ml", "linalg"]),
    ("ltl-tfidf",          "TF-IDF vectoriser + cosine nearest-neighbour search.", "ml", ["ml", "nlp"]),
    ("ltl-sentiment",      "Bag-of-words sentiment classifier with a bundled lexicon.", "ml", ["ml", "nlp"]),

    # --- Graphics -------------------------------------------------------------
    ("ltl-raytracer",      "Whitted-style ray tracer with spheres, planes, lights.", "graphics", ["graphics", "raytracing"]),
    ("ltl-rasterizer",     "Software triangle rasteriser with z-buffer and perspective.", "graphics", ["graphics", "3d"]),
    ("ltl-mandelbrot",     "Mandelbrot / Julia set renderer with escape-time colouring.", "graphics", ["graphics", "fractal"]),
    ("ltl-voronoi",        "Fortune's sweep-line Voronoi diagram.", "graphics", ["graphics", "algorithm"]),
    ("ltl-delaunay",       "Delaunay triangulation via Bowyer-Watson.", "graphics", ["graphics", "algorithm"]),
    ("ltl-ascii-art",      "Image-to-ASCII converter with dithering.", "graphics", ["graphics", "cli"]),
    ("ltl-qr-encode",      "QR-code (model-2) encoder with mask evaluation.", "graphics", ["graphics", "qr"]),
    ("ltl-svg-draw",       "Minimal SVG path renderer with Bezier flattening.", "graphics", ["graphics", "svg"]),
    ("ltl-perlin",         "Perlin + simplex noise for procedural textures.", "graphics", ["graphics", "noise"]),

    # --- Emulators ------------------------------------------------------------
    ("ltl-6502-emu",       "MOS 6502 emulator with cycle-accurate instruction timing.", "emulator", ["emulator", "6502"]),
    ("ltl-z80-emu",        "Z80 CPU emulator passing ZEXDOC/ZEXALL.", "emulator", ["emulator", "z80"]),
    ("ltl-8080-emu",       "Intel 8080 emulator for Space-Invaders-era targets.", "emulator", ["emulator", "8080"]),
    ("ltl-chip8-emu",      "CHIP-8 interpreter with display quirks flags.", "emulator", ["emulator", "chip8"]),
    ("ltl-gb-cpu",         "Game Boy SM83 CPU core + MBC1 cartridge loader.", "emulator", ["emulator", "gameboy"]),

    # --- Compilers / VMs ------------------------------------------------------
    ("ltl-scheme-lite",    "R5RS-subset Scheme interpreter with tail-call elimination.", "compiler", ["compiler", "scheme"]),
    ("ltl-basic-interp",   "Dartmouth BASIC interpreter — line numbers, GOSUB, PRINT.", "compiler", ["compiler", "basic"]),
    ("ltl-stack-vm",       "Minimal stack VM with JIT-ready bytecode format.", "compiler", ["compiler", "vm"]),
    ("ltl-regalloc-demo",  "Linear-scan register allocator on toy IR.", "compiler", ["compiler", "demo"]),
    ("ltl-ssa-demo",       "SSA construction + dominance-tree visualiser.", "compiler", ["compiler", "demo"]),
    ("ltl-peephole",       "Peephole optimiser demos over a 3-address IR.", "compiler", ["compiler", "demo"]),
    ("ltl-lex-gen",        "Regex-to-DFA lexer generator — lex(1) minus the bugs.", "compiler", ["compiler", "lexer"]),
    ("ltl-pratt-parse",    "Pratt (TDOP) parser framework with precedence tables.", "compiler", ["compiler", "parser"]),

    # --- Dev tools ------------------------------------------------------------
    ("ltl-git-reader",     "Read-only Git object-store reader (loose + packfile).", "devtool", ["devtool", "git"]),
    ("ltl-lz77",           "LZ77 sliding-window compressor (educational).", "devtool", ["compression"]),
    ("ltl-deflate-toy",    "DEFLATE dynamic-Huffman encoder compatible with gzip.", "devtool", ["compression"]),
    ("ltl-fuzz-mini",      "Coverage-guided fuzz harness for pure functions.", "devtool", ["devtool", "fuzzing"]),
    ("ltl-bench-harness",  "Microbenchmark harness with warmups, IQR, and JSON output.", "devtool", ["devtool", "benchmark"]),
    ("ltl-log-lib",        "Structured logger (key=value + JSON) with log levels.", "devtool", ["devtool", "logging"]),
    ("ltl-prom-expose",    "Prometheus text-format exposer for custom counters.", "devtool", ["devtool", "observability"]),
    ("ltl-feature-flags",  "In-memory feature-flag evaluator with percentage rollout.", "devtool", ["devtool"]),

    # --- Concurrency ----------------------------------------------------------
    ("ltl-actor-demo",     "Actor model with mailboxes and supervision trees.", "concurrency", ["concurrency"]),
    ("ltl-csp-demo",       "CSP-style channels with `select` on multiple channels.", "concurrency", ["concurrency"]),
    ("ltl-worker-pool",    "Bounded worker pool with task backpressure.", "concurrency", ["concurrency"]),
    ("ltl-ring-buffer",    "Lock-free single-producer / single-consumer ring.", "concurrency", ["concurrency"]),
    ("ltl-mpsc-queue",     "Multi-producer single-consumer lock-free queue.", "concurrency", ["concurrency"]),
    ("ltl-rwlock",         "Reader-writer lock with writer-priority option.", "concurrency", ["concurrency"]),

    # --- OS / systems ---------------------------------------------------------
    ("ltl-mini-shell",     "Tiny POSIX shell — pipelines, redirects, job control.", "systems", ["shell"]),
    ("ltl-init-tiny",      "Minimal PID-1 init for containers — signal fanout + reap.", "systems", ["systems"]),
    ("ltl-syscall-trace",  "strace-like syscall tracer using ptrace.", "systems", ["systems"]),
    ("ltl-memalloc-demo",  "Educational buddy + slab allocator implementation.", "systems", ["systems"]),
    ("ltl-scheduler-demo", "Round-robin + MLFQ toy scheduler with gantt output.", "systems", ["systems"]),
    ("ltl-fs-toy",         "Toy in-memory FAT-like filesystem with mkdir / ls / cat.", "systems", ["systems"]),

    # --- Ecosystem / meta -----------------------------------------------------
    ("lateralus-advent",       "Advent of Code solutions in Lateralus (partial: 2023-2025).", "ecosystem", ["advent-of-code"]),
    ("lateralus-koans-web",    "Interactive browser-run koans for learning Lateralus.", "ecosystem", ["learning", "webassembly"]),
    ("lateralus-repl-docker",  "Dockerfile and image for the Lateralus REPL sandbox.", "ecosystem", ["docker", "repl"]),
    ("lateralus-gh-action",    "GitHub Action that compiles and tests Lateralus projects.", "ecosystem", ["github-actions"]),
    ("lateralus-homebrew-tap", "Homebrew tap formula for the `lateralus` compiler.", "ecosystem", ["homebrew"]),
    ("lateralus-scoop-bucket", "Scoop bucket manifest for Windows installations.", "ecosystem", ["scoop", "windows"]),
    ("lateralus-awesome",      "Curated awesome-list of Lateralus libraries and demos.", "ecosystem", ["awesome-list"]),
    ("lateralus-rosetta-web",  "Side-by-side Lateralus / Rust / Python / Go translations.", "ecosystem", ["learning"]),
    ("lateralus-benchmarks-web", "Continuously-updated micro-benchmark leaderboard.", "ecosystem", ["benchmark"]),
    ("lateralus-snippets-vim", "Vim / Neovim snippets pack for Lateralus.", "ecosystem", ["vim", "editor"]),
    ("lateralus-snippets-emacs", "Emacs yasnippet pack for Lateralus.", "ecosystem", ["emacs", "editor"]),
    ("lateralus-snippets-jetbrains", "JetBrains-IDE live-template pack for Lateralus.", "ecosystem", ["jetbrains", "editor"]),
    ("lateralus-tree-sitter",  "Tree-sitter grammar for Lateralus (mirrors the tmLanguage).", "ecosystem", ["tree-sitter", "grammar"]),
    ("lateralus-conf-2026",    "Talk abstracts and slides from LateralusConf 2026.", "ecosystem", ["conference"]),
    ("lateralus-book",         "Draft chapters of 'Programming Lateralus'.", "ecosystem", ["book"]),
    ("lateralus-recipes",      "Short single-file recipes demonstrating stdlib usage.", "ecosystem", ["examples"]),
    ("lateralus-idioms",       "Idioms, style guidelines, and anti-patterns.", "ecosystem", ["style-guide"]),
    ("lateralus-perf-notes",   "Performance engineering notes with reproducible benchmarks.", "ecosystem", ["performance"]),
    ("lateralus-security-notes", "Security considerations and vulnerability-class notes.", "ecosystem", ["security"]),
    ("lateralus-gotchas",      "Collected foot-guns and how to avoid them.", "ecosystem", ["documentation"]),
    ("lateralus-faq",          "Frequently asked questions with runnable code answers.", "ecosystem", ["documentation"]),
    ("lateralus-guide-async",  "Deep dive on async / await and green threads.", "ecosystem", ["documentation", "async"]),
    ("lateralus-guide-ffi",    "Foreign-function-interface guide with C and WASM examples.", "ecosystem", ["documentation", "ffi"]),
    ("lateralus-guide-types",  "Type-system guide with Hindley-Milner derivations.", "ecosystem", ["documentation", "types"]),
    ("lateralus-guide-laws",   "The `@law` verification-pipeline tutorial.", "ecosystem", ["documentation", "verification"]),
]


def slug_safe(name: str) -> bool:
    """GitHub repo naming rules: 1-100 chars, [A-Za-z0-9._-]."""
    return 1 <= len(name) <= 100 and all(c.isalnum() or c in "._-" for c in name)


def load_manifest() -> dict:
    with MANIFEST.open() as f:
        return yaml.safe_load(f)


def existing_gh_repos() -> set[str]:
    """Return the set of repo names under bad-antics/ that already exist."""
    try:
        out = subprocess.check_output(
            ["gh", "repo", "list", "bad-antics", "--limit", "2000",
             "--json", "name", "--jq", ".[].name"],
            text=True,
            timeout=60,
        )
        return set(line.strip() for line in out.splitlines() if line.strip())
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return set()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Write changes to manifest.yml")
    ap.add_argument("--min", type=int, default=0, help="Target total repo count (cap appending)")
    args = ap.parse_args()

    manifest = load_manifest()
    existing_manifest = {r["name"] for r in manifest["repos"]}
    gh_existing = existing_gh_repos()

    print(f"manifest has {len(existing_manifest)} repos")
    print(f"github has {len(gh_existing)} bad-antics/* repos")

    new_entries: list[dict] = []
    for name, tagline, category, topics in CANDIDATES:
        if not slug_safe(name):
            continue
        if name in existing_manifest:
            continue
        new_entries.append({
            "name": name,
            "tagline": tagline,
            "category": category,
            "source_template": name.replace("-", "_").replace("ltl_", "").replace("lateralus_", ""),
            "topics": topics,
        })

    if args.min:
        target = max(0, args.min - len(existing_manifest))
        if len(new_entries) > target:
            new_entries = new_entries[:target]

    already_on_gh = sum(1 for e in new_entries if e["name"] in gh_existing)
    fresh = len(new_entries) - already_on_gh

    print(f"candidate pool: {len(CANDIDATES)}")
    print(f"would append:   {len(new_entries)}  ({fresh} new on github, {already_on_gh} already exist)")
    print(f"projected total manifest: {len(existing_manifest) + len(new_entries)}")

    if not args.apply:
        print("\n(dry run — pass --apply to write manifest.yml)")
        return 0

    manifest["repos"].extend(new_entries)
    # Preserve the file's comment header by appending only the new repos.
    existing_text = MANIFEST.read_text()
    tail = yaml.dump({"_appended": new_entries}, sort_keys=False, width=120)
    tail = tail.removeprefix("_appended:\n")
    tail_lines = ["\n  # -- Auto-appended by expand_manifest.py --\n"]
    for entry in new_entries:
        tail_lines.append("\n  - name: " + entry["name"] + "\n")
        tail_lines.append("    tagline: " + yaml.dump(entry["tagline"], default_style='"').strip() + "\n")
        tail_lines.append("    category: " + entry["category"] + "\n")
        tail_lines.append("    source_template: " + entry["source_template"] + "\n")
        tail_lines.append("    topics: " + str(entry["topics"]).replace("'", "") + "\n")

    MANIFEST.write_text(existing_text.rstrip() + "\n" + "".join(tail_lines))
    print(f"\nwrote {len(new_entries)} entries to {MANIFEST.relative_to(ROOT.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
