#!/usr/bin/env python3
"""
expand_manifest_v2.py — second wave of candidate repos.

Adds ~150 new entries in domains NOT heavily covered by v1, including:
retro computing, DSP, bioinformatics, finance, geo, databases, observability,
kubernetes tooling, game engine building blocks, and more ecosystem meta repos.

Usage:
    python3 expand_manifest_v2.py            # preview
    python3 expand_manifest_v2.py --apply    # append to manifest.yml
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("error: pyyaml required", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifest.yml"

CANDIDATES: list[tuple[str, str, str, list[str]]] = [
    # --- Databases / storage -------------------------------------------------
    ("ltl-kv-store",        "Persistent append-only KV store with compaction.", "storage", ["database", "kv"]),
    ("ltl-lsm-demo",        "Educational log-structured merge tree implementation.", "storage", ["database", "lsm"]),
    ("ltl-btree-mem",       "In-memory B-tree index with range cursors.", "storage", ["database", "btree"]),
    ("ltl-wal-demo",        "Write-ahead log with checkpoint and recovery.", "storage", ["database", "wal"]),
    ("ltl-mvcc-toy",        "Multi-version concurrency control demo on toy rows.", "storage", ["database", "mvcc"]),
    ("ltl-sqlparse-mini",   "Mini SQL parser — SELECT / WHERE / JOIN / GROUP BY.", "storage", ["database", "sql"]),
    ("ltl-query-planner",   "Volcano-style query planner with rule-based optimisation.", "storage", ["database", "query"]),
    ("ltl-skiplist",        "Probabilistic skip list with concurrent read path.", "storage", ["database", "ds"]),

    # --- Observability / tracing --------------------------------------------
    ("ltl-otel-spans",      "OpenTelemetry-compatible span emitter over OTLP/HTTP.", "observability", ["tracing", "otel"]),
    ("ltl-pprof-lite",      "pprof-format CPU profile writer with flame graph export.", "observability", ["profiling"]),
    ("ltl-statsd-client",   "StatsD UDP emitter with counters, gauges, and timers.", "observability", ["metrics", "statsd"]),
    ("ltl-loki-push",       "Grafana Loki push-API client for log shipping.", "observability", ["logging", "loki"]),
    ("ltl-jaeger-export",   "Jaeger Thrift over UDP span exporter.", "observability", ["tracing", "jaeger"]),
    ("ltl-health-check",    "HTTP health / readiness / liveness endpoint harness.", "observability", ["health"]),

    # --- DSP / audio ---------------------------------------------------------
    ("ltl-iir-filter",      "IIR biquad filter designer — LP / HP / BP / notch.", "dsp", ["dsp", "audio"]),
    ("ltl-fir-filter",      "FIR windowed-sinc filter with zero-phase option.", "dsp", ["dsp", "audio"]),
    ("ltl-wavelet",         "Discrete Haar / Daubechies wavelet transforms.", "dsp", ["dsp", "wavelet"]),
    ("ltl-mp3-decode-stub", "MP3 frame-header and side-info parser.", "dsp", ["dsp", "mp3"]),
    ("ltl-opus-stub",       "Opus packet parser with TOC byte decoder.", "dsp", ["dsp", "opus"]),
    ("ltl-flac-read",       "FLAC metadata block + frame header reader.", "dsp", ["dsp", "flac"]),
    ("ltl-pitch-yin",       "YIN algorithm pitch detector for monophonic audio.", "dsp", ["dsp", "pitch"]),
    ("ltl-mfcc",            "Mel-frequency cepstral coefficients extractor.", "dsp", ["dsp", "speech"]),

    # --- Geo / mapping -------------------------------------------------------
    ("ltl-geohash",         "Geohash encoder / decoder with neighbour lookup.", "geo", ["geo", "geohash"]),
    ("ltl-h3-stub",         "Uber H3 hex-grid wrapper — cell-to-latlon and ring.", "geo", ["geo", "h3"]),
    ("ltl-s2-stub",         "S2 geometry cell-id decoder and area estimator.", "geo", ["geo", "s2"]),
    ("ltl-geojson",         "GeoJSON RFC 7946 parser / validator / pretty-printer.", "geo", ["geo", "geojson"]),
    ("ltl-kml-read",        "KML 2.2 placemark and polygon parser.", "geo", ["geo", "kml"]),
    ("ltl-haversine",       "Haversine / great-circle distance and bearing library.", "geo", ["geo", "math"]),
    ("ltl-mbtiles",         "MBTiles (SQLite-backed tile-set) reader.", "geo", ["geo", "tiles"]),

    # --- Bioinformatics ------------------------------------------------------
    ("ltl-fasta",           "FASTA reader / writer with sequence-stats helpers.", "bio", ["bio", "fasta"]),
    ("ltl-fastq",           "FASTQ reader with quality-score histograms.", "bio", ["bio", "fastq"]),
    ("ltl-smith-waterman",  "Smith-Waterman local alignment (affine gap).", "bio", ["bio", "alignment"]),
    ("ltl-needleman-wunsch","Needleman-Wunsch global alignment.", "bio", ["bio", "alignment"]),
    ("ltl-phred",           "Phred-quality converter for Sanger / Illumina encodings.", "bio", ["bio", "quality"]),
    ("ltl-kmer-count",      "K-mer frequency counter with Bloom pre-filter.", "bio", ["bio", "kmer"]),
    ("ltl-dna-stats",       "GC content / codon / reverse-complement utilities.", "bio", ["bio", "dna"]),

    # --- Finance / markets ---------------------------------------------------
    ("ltl-ohlc",            "OHLC bar builder with tick aggregation windows.", "finance", ["finance", "markets"]),
    ("ltl-fin-indicators",  "SMA / EMA / RSI / MACD / Bollinger-band indicators.", "finance", ["finance", "ta"]),
    ("ltl-orderbook",       "Price-time-priority limit-order book in pure Lateralus.", "finance", ["finance", "orderbook"]),
    ("ltl-black-scholes",   "Black-Scholes option pricer with greeks.", "finance", ["finance", "options"]),
    ("ltl-montecarlo-price","Monte-Carlo path-dependent option pricer.", "finance", ["finance", "montecarlo"]),
    ("ltl-portfolio-stats", "Sharpe / Sortino / max-drawdown portfolio statistics.", "finance", ["finance", "stats"]),
    ("ltl-rtp-quotes",      "Real-time-protocol quote consumer stub (ITCH-ish).", "finance", ["finance", "feeds"]),

    # --- Container / k8s tooling --------------------------------------------
    ("ltl-k8s-probe",       "Kubernetes liveness / readiness probe helper lib.", "container", ["k8s", "devtool"]),
    ("ltl-helm-render",     "Minimal Helm-chart template renderer (Go-template subset).", "container", ["k8s", "helm"]),
    ("ltl-oci-manifest",    "OCI image-manifest v1.0 reader / writer.", "container", ["oci", "container"]),
    ("ltl-dockerfile-parse","Dockerfile parser producing a structured IR.", "container", ["docker", "parser"]),
    ("ltl-compose-expand",  "docker-compose v3 expander — env vars + extends.", "container", ["docker", "compose"]),
    ("ltl-kustomize-lite",  "Kustomize patch/overlay demo resolver.", "container", ["k8s", "kustomize"]),

    # --- Protocols (continued) ----------------------------------------------
    ("ltl-protobuf-lite",   "Protocol-buffer wire-format encoder / decoder (proto3).", "protocol", ["protobuf"]),
    ("ltl-flatbuf-demo",    "FlatBuffers offset-table reader — zero-copy.", "protocol", ["flatbuffers"]),
    ("ltl-bencode",         "BitTorrent bencode reader / writer.", "protocol", ["bencode", "bittorrent"]),
    ("ltl-avro-read",       "Apache Avro binary-format decoder with schema.", "protocol", ["avro"]),
    ("ltl-thrift-read",     "Apache Thrift compact-protocol decoder.", "protocol", ["thrift"]),
    ("ltl-edn",             "Clojure EDN (extensible data notation) reader.", "protocol", ["edn"]),
    ("ltl-toml-writer",     "Round-trip TOML writer — preserves comments and order.", "protocol", ["toml"]),
    ("ltl-yaml-lite",       "YAML 1.2 flow-style reader (subset).", "protocol", ["yaml"]),

    # --- Networking (continued) ---------------------------------------------
    ("ltl-quic-frame",      "QUIC frame header parser (RFC 9000).", "networking", ["quic", "networking"]),
    ("ltl-dns-server",      "Toy authoritative DNS server with A / AAAA / MX.", "networking", ["dns", "networking"]),
    ("ltl-dns-resolver",    "Recursive DNS resolver — root hints to final answer.", "networking", ["dns", "networking"]),
    ("ltl-stun-client",     "STUN (RFC 5389) binding-request client for NAT discovery.", "networking", ["stun"]),
    ("ltl-ice-lite",        "ICE-lite candidate generator for WebRTC peers.", "networking", ["webrtc"]),
    ("ltl-gopher",          "Gopher protocol (RFC 1436) client and server.", "networking", ["gopher", "retro"]),
    ("ltl-finger",          "Finger protocol (RFC 1288) server.", "networking", ["finger", "retro"]),
    ("ltl-nntp-read",       "NNTP (RFC 3977) article reader — GROUP + ARTICLE.", "networking", ["nntp", "retro"]),
    ("ltl-smtp-send",       "SMTP client — EHLO / STARTTLS / AUTH-PLAIN.", "networking", ["smtp"]),
    ("ltl-pop3-read",       "POP3 (RFC 1939) client for fetching mailbox items.", "networking", ["pop3"]),
    ("ltl-imap-list",       "IMAP4rev1 LIST / SELECT / FETCH client.", "networking", ["imap"]),

    # --- Crypto (continued) -------------------------------------------------
    ("ltl-rsa-toy",         "Textbook RSA key-gen / encrypt / decrypt for teaching.", "crypto", ["crypto", "rsa"]),
    ("ltl-dsa-toy",         "Textbook DSA signatures — FIPS 186 parameters.", "crypto", ["crypto", "dsa"]),
    ("ltl-shamir",          "Shamir secret-sharing over GF(256).", "crypto", ["crypto", "shamir"]),
    ("ltl-ssss-cli",        "CLI wrapper for splitting and recombining secrets.", "crypto", ["crypto", "cli"]),
    ("ltl-scrypt",          "scrypt KDF (RFC 7914) with tuneable parameters.", "crypto", ["crypto", "kdf"]),
    ("ltl-bcrypt",          "bcrypt password-hashing with cost selection.", "crypto", ["crypto", "kdf"]),
    ("ltl-ripemd160",       "RIPEMD-160 hash implementation with test vectors.", "crypto", ["crypto", "hash"]),
    ("ltl-blake2",          "BLAKE2b / BLAKE2s keyed-hash implementation.", "crypto", ["crypto", "hash"]),
    ("ltl-blake3",          "BLAKE3 parallel hashing over a binary tree.", "crypto", ["crypto", "hash"]),
    ("ltl-secp256k1",       "Bitcoin-compatible secp256k1 curve ops.", "crypto", ["crypto", "secp256k1"]),

    # --- ML (continued) ------------------------------------------------------
    ("ltl-mlp-tiny",        "Tiny multi-layer perceptron with backprop demo.", "ml", ["ml"]),
    ("ltl-cnn-demo",        "Toy CNN on MNIST — convolution + pooling + softmax.", "ml", ["ml", "cnn"]),
    ("ltl-rnn-demo",        "Vanilla RNN character-level language model.", "ml", ["ml", "rnn"]),
    ("ltl-attention-toy",   "Scaled dot-product attention over toy embeddings.", "ml", ["ml", "attention"]),
    ("ltl-hmm",             "Hidden Markov Model — forward / Viterbi / Baum-Welch.", "ml", ["ml", "hmm"]),
    ("ltl-dtw",             "Dynamic time-warping for time-series similarity.", "ml", ["ml", "timeseries"]),
    ("ltl-svm-linear",      "Linear SVM with hinge loss + SGD trainer.", "ml", ["ml", "svm"]),
    ("ltl-random-forest",   "Random-forest classifier with out-of-bag scoring.", "ml", ["ml"]),
    ("ltl-gradient-boost",  "Gradient-boosted trees (toy, for teaching).", "ml", ["ml"]),

    # --- Games (continued) --------------------------------------------------
    ("ltl-snake-ai",        "Snake with hamiltonian-cycle path-planning AI.", "game", ["game", "ai"]),
    ("ltl-minesweeper",     "Terminal Minesweeper with flood-fill and CSP hints.", "game", ["game", "puzzle"]),
    ("ltl-rogue-lite",      "ASCII roguelike with FOV + A* + procedural dungeons.", "game", ["game", "roguelike"]),
    ("ltl-hangman",         "Hangman with word-list frequency analysis.", "game", ["game"]),
    ("ltl-wordle",          "Wordle clone with entropy-based solver hints.", "game", ["game", "puzzle"]),
    ("ltl-nonogram",        "Nonogram / picross solver via constraint propagation.", "game", ["game", "puzzle"]),
    ("ltl-kakuro",          "Kakuro solver with sum + uniqueness constraints.", "game", ["game", "puzzle"]),
    ("ltl-astar-demo",      "A* pathfinding visualiser with obstacle editor.", "game", ["game", "ai"]),

    # --- Graphics (continued) -----------------------------------------------
    ("ltl-marching-cubes",  "Marching-cubes iso-surface extraction.", "graphics", ["graphics", "isosurface"]),
    ("ltl-dda-line",        "DDA / Bresenham line / circle rasterisers.", "graphics", ["graphics", "rasterise"]),
    ("ltl-color-spaces",    "sRGB / Lab / LCh / XYZ colour-space conversions.", "graphics", ["graphics", "color"]),
    ("ltl-pdf-render-toy",  "Minimal PDF rasteriser (text + simple vector paths).", "graphics", ["graphics", "pdf"]),
    ("ltl-font-truetype",   "TrueType 'glyf' outline reader with Bezier flattening.", "graphics", ["graphics", "font"]),
    ("ltl-layout-engine",   "Flexbox-inspired 2-D layout engine with min/max sizing.", "graphics", ["graphics", "layout"]),

    # --- Retrocomputing ------------------------------------------------------
    ("ltl-apple2-emu",      "Partial Apple II 6502 system emulator — RAM + TEXT mode.", "emulator", ["apple2", "emulator"]),
    ("ltl-nes-cpu-only",    "NES CPU + PPU stub — CPU passes nestest.", "emulator", ["nes", "emulator"]),
    ("ltl-atari2600-cpu",   "Atari 2600 6507 core with TIA skeleton.", "emulator", ["atari", "emulator"]),
    ("ltl-c64-basic-lite",  "C64-flavoured BASIC interpreter over ASCII.", "emulator", ["c64", "retro"]),
    ("ltl-brainfck-jit",    "Brainfuck interpreter + threaded-code optimiser.", "emulator", ["brainfuck"]),

    # --- Compilers (continued) ----------------------------------------------
    ("ltl-wasm-asm",        "WebAssembly text-format (wat) assembler to wasm bytes.", "compiler", ["wasm", "compiler"]),
    ("ltl-wasm-interp",     "Wasm interpreter for the MVP instruction set.", "compiler", ["wasm", "compiler"]),
    ("ltl-bf-to-c",         "Brainfuck-to-C transpiler with loop-pattern matching.", "compiler", ["compiler", "brainfuck"]),
    ("ltl-lambda-reduce",   "Untyped lambda-calculus beta-reducer with call-by-need.", "compiler", ["compiler", "lambda"]),
    ("ltl-prolog-lite",     "Tiny Prolog interpreter with unification and DCG.", "compiler", ["compiler", "prolog"]),
    ("ltl-lisp-macros",     "Common-Lisp-flavoured macro expander over a small core.", "compiler", ["compiler", "lisp"]),
    ("ltl-forth-lite",      "Indirect-threaded Forth interpreter with IMMEDIATE words.", "compiler", ["compiler", "forth"]),

    # --- Dev tools (continued) ----------------------------------------------
    ("ltl-semver",          "SemVer 2.0.0 parser, comparator, and range evaluator.", "devtool", ["semver"]),
    ("ltl-changelog-lint",  "Keep-a-Changelog format linter and generator.", "devtool", ["changelog", "devtool"]),
    ("ltl-license-detect",  "Heuristic SPDX license detector for source files.", "devtool", ["license"]),
    ("ltl-dep-graph",       "Dependency-graph analyser — cycle detect + DOT export.", "devtool", ["dep-graph"]),
    ("ltl-dot-render",      "Graphviz DOT layout engine (force-directed fallback).", "devtool", ["graphviz"]),
    ("ltl-ci-emit",         "CI log-emit helper — GHA groups + annotations + summaries.", "devtool", ["ci"]),
    ("ltl-secret-scan",     "Regex + entropy based secret scanner for git history.", "devtool", ["security", "devtool"]),
    ("ltl-commit-lint",     "Conventional-Commits linter with configurable scopes.", "devtool", ["git", "lint"]),

    # --- Parsers (continued) ------------------------------------------------
    ("ltl-ini-parse",       "INI + properties-file parser with type coercion.", "protocol", ["ini"]),
    ("ltl-cue-lite",        "CUE lang value+constraint language subset parser.", "protocol", ["cue"]),
    ("ltl-hcl-read",        "HashiCorp HCL2 reader for Terraform-style configs.", "protocol", ["hcl"]),
    ("ltl-nginx-parse",     "nginx.conf parser producing a structured AST.", "protocol", ["nginx"]),
    ("ltl-apache-parse",    "Apache httpd configuration parser.", "protocol", ["apache"]),
    ("ltl-opensearch-dsl",  "OpenSearch/Elasticsearch query-DSL builder.", "protocol", ["search"]),
    ("ltl-graphql-parse",   "GraphQL document parser — operations, fragments, directives.", "protocol", ["graphql"]),
    ("ltl-yang-lite",       "YANG 1.1 module parser subset for NETCONF configs.", "protocol", ["yang"]),

    # --- Systems (continued) ------------------------------------------------
    ("ltl-epoll-demo",      "epoll-based reactor — accept / read / write fan-out.", "systems", ["epoll", "systems"]),
    ("ltl-cgroup-read",     "cgroup v2 stat reader for CPU / memory / io.", "systems", ["cgroup", "systems"]),
    ("ltl-procfs-walk",     "Walker over /proc with per-pid stats collector.", "systems", ["procfs", "systems"]),
    ("ltl-netlink-demo",    "Netlink (rtnetlink) link + address enumerator.", "systems", ["netlink", "systems"]),
    ("ltl-seccomp-demo",    "seccomp-bpf filter builder for syscall allow-lists.", "systems", ["seccomp", "systems"]),
    ("ltl-capabilities",    "Linux capabilities bit-set introspection library.", "systems", ["capabilities"]),

    # --- Concurrency (continued) --------------------------------------------
    ("ltl-select-demo",     "Multi-way select across channels with timeouts.", "concurrency", ["concurrency"]),
    ("ltl-backpressure",    "Token-bucket + leaky-bucket backpressure primitives.", "concurrency", ["concurrency"]),
    ("ltl-supervisor",      "OTP-flavoured supervisor tree with restart strategies.", "concurrency", ["concurrency"]),
    ("ltl-deadlock-detect", "Waits-for-graph deadlock detector for educational use.", "concurrency", ["concurrency"]),

    # --- Ecosystem / meta (continued) ---------------------------------------
    ("lateralus-cheatsheet",  "One-page PDF + MD cheat-sheet for Lateralus syntax.", "ecosystem", ["documentation"]),
    ("lateralus-playground",  "Browser playground that runs Lateralus via WebAssembly.", "ecosystem", ["webassembly", "playground"]),
    ("lateralus-katas",       "Performance-oriented coding katas with reference solutions.", "ecosystem", ["katas"]),
    ("lateralus-interviews",  "Mock-interview problems solved idiomatically in Lateralus.", "ecosystem", ["interviews"]),
    ("lateralus-puzzles",     "Logic + algorithm puzzles with Lateralus solutions.", "ecosystem", ["puzzles"]),
    ("lateralus-eurorave",    "Generative music patches written in Lateralus.", "ecosystem", ["music"]),
    ("lateralus-art",         "Generative visual-art pieces in Lateralus + SVG.", "ecosystem", ["art"]),
    ("lateralus-shaders",     "GLSL-to-Lateralus shader-style DSL experiments.", "ecosystem", ["graphics"]),
    ("lateralus-ebook",       "eBook assets for the 'Programming Lateralus' draft.", "ecosystem", ["book"]),
    ("lateralus-streaming",   "Twitch / VoD stream-of-consciousness Lateralus sessions.", "ecosystem", ["streaming"]),
    ("lateralus-style-bot",   "Discord / Matrix bot answering style-guide questions.", "ecosystem", ["bot"]),
    ("lateralus-docker-ci",   "Docker-based CI reference images for Lateralus projects.", "ecosystem", ["ci", "docker"]),
    ("lateralus-gh-templates","Repo / issue / PR templates starter for Lateralus projects.", "ecosystem", ["templates"]),
    ("lateralus-branding",    "Logo, colour palette, typography kit — brand guidelines.", "ecosystem", ["branding"]),
    ("lateralus-press-kit",   "Press kit — screenshots, headlines, boilerplate copy.", "ecosystem", ["press"]),
    ("lateralus-meetups",     "Local meetup slide decks and talk recordings index.", "ecosystem", ["meetups"]),
    ("lateralus-roadmap-web", "Public roadmap renderer driven by a YAML source file.", "ecosystem", ["roadmap"]),
    ("lateralus-survey-2026", "Results of the 2026 Lateralus community survey.", "ecosystem", ["survey"]),
    ("lateralus-rfcs",        "Request-For-Comments documents for language evolution.", "ecosystem", ["rfcs"]),
    ("lateralus-versions",    "Historical changelog + release-binary manifests.", "ecosystem", ["releases"]),
]


def slug_safe(name: str) -> bool:
    return 1 <= len(name) <= 100 and all(c.isalnum() or c in "._-" for c in name)


def load_manifest() -> dict:
    with MANIFEST.open() as f:
        return yaml.safe_load(f)


def existing_gh_repos() -> set[str]:
    try:
        out = subprocess.check_output(
            ["gh", "repo", "list", "bad-antics", "--limit", "2000",
             "--json", "name", "--jq", ".[].name"],
            text=True, timeout=60,
        )
        return set(line.strip() for line in out.splitlines() if line.strip())
    except Exception:
        return set()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    manifest = load_manifest()
    existing = {r["name"] for r in manifest["repos"]}
    gh = existing_gh_repos()

    new_entries: list[dict] = []
    for name, tagline, category, topics in CANDIDATES:
        if not slug_safe(name) or name in existing:
            continue
        new_entries.append({
            "name": name,
            "tagline": tagline,
            "category": category,
            "source_template": name.replace("-", "_").replace("ltl_", "").replace("lateralus_", ""),
            "topics": topics,
        })

    print(f"manifest has {len(existing)} repos; candidate pool {len(CANDIDATES)}")
    print(f"would append {len(new_entries)}  (projected total: {len(existing) + len(new_entries)})")
    already = sum(1 for e in new_entries if e["name"] in gh)
    print(f"  of which {already} already exist on github (will be no-op on publish)")

    if not args.apply:
        print("\n(dry run — pass --apply)")
        return 0

    existing_text = MANIFEST.read_text()
    tail_lines = ["\n  # -- Auto-appended by expand_manifest_v2.py --\n"]
    for entry in new_entries:
        tail_lines.append("\n  - name: " + entry["name"] + "\n")
        tail_lines.append("    tagline: " + yaml.dump(entry["tagline"], default_style='"').strip() + "\n")
        tail_lines.append("    category: " + entry["category"] + "\n")
        tail_lines.append("    source_template: " + entry["source_template"] + "\n")
        tail_lines.append("    topics: " + str(entry["topics"]).replace("'", "") + "\n")
    MANIFEST.write_text(existing_text.rstrip() + "\n" + "".join(tail_lines))
    print(f"\nwrote {len(new_entries)} entries to manifest.yml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
