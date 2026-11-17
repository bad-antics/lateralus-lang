// Node.js reference implementations matching benchmarks/src/*.ltl exactly.

function fib(n) {
  if (n < 2) return n;
  return fib(n - 1) + fib(n - 2);
}

function sieve(n) {
  const isPrime = new Uint8Array(n + 1);
  isPrime.fill(1);
  isPrime[0] = 0;
  isPrime[1] = 0;
  for (let p = 2; p * p <= n; p++) {
    if (isPrime[p]) {
      for (let j = p * p; j <= n; j += p) isPrime[j] = 0;
    }
  }
  let count = 0;
  for (let i = 0; i <= n; i++) if (isPrime[i]) count++;
  return count;
}

function mandelbrot(width, height, maxIter) {
  let total = 0;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const cx = -2.0 + (x / width) * 3.0;
      const cy = -1.5 + (y / height) * 3.0;
      let zx = 0.0, zy = 0.0, i = 0;
      while (i < maxIter) {
        const zx2 = zx * zx, zy2 = zy * zy;
        if (zx2 + zy2 > 4.0) break;
        const newZx = zx2 - zy2 + cx;
        zy = 2.0 * zx * zy + cy;
        zx = newZx;
        i++;
      }
      total += i;
    }
  }
  return total;
}

function nbody(nBodies, iterations) {
  const xs = [0.0, 4.84, 8.34, 12.89, 15.37];
  const ys = [0.0, 1.16, 4.12, 11.73, 25.92];
  const vxs = [0.0, 0.00166, 0.00277, 0.00296, 0.00268];
  const vys = [0.0, 0.00769, 0.00499, 0.00237, 0.00150];
  const ms = [39.47, 0.0377, 0.113, 0.0349, 0.0534];
  for (let it = 0; it < iterations; it++) {
    for (let i = 0; i < nBodies; i++) {
      for (let j = i + 1; j < nBodies; j++) {
        const dx = xs[i] - xs[j];
        const dy = ys[i] - ys[j];
        const d2 = dx * dx + dy * dy + 0.0001;
        const d = Math.sqrt(d2);
        const mag = 0.01 / (d2 * d);
        vxs[i] -= dx * ms[j] * mag;
        vys[i] -= dy * ms[j] * mag;
        vxs[j] += dx * ms[i] * mag;
        vys[j] += dy * ms[i] * mag;
      }
    }
    for (let k = 0; k < nBodies; k++) {
      xs[k] += 0.01 * vxs[k];
      ys[k] += 0.01 * vys[k];
    }
  }
  return xs.reduce((a, b) => a + b, 0) + ys.reduce((a, b) => a + b, 0);
}

function makeTree(depth) {
  if (depth === 0) return 0;
  return { left: makeTree(depth - 1), right: makeTree(depth - 1) };
}
function checkTree(node) {
  if (node === 0) return 1;
  return 1 + checkTree(node.left) + checkTree(node.right);
}

// ---------------------------------------------------------------------------
// stdlib micro-benchmark references (matching benchmarks/src/stdlib_*.ltl).
// Pure JS implementations, no third-party packages.
//   - xxhash64  : real XXH64 (byte-identical to the Lateralus stdlib hash64)
//   - lz4       : simple hash-chain LZ77 round-trip (not the LZ4 block format)
//   - chacha20  : RFC 8439 stream cipher (matches the Lateralus stdlib xor)
//   - aho_corasick : naive multi-pattern search (indexOf per pattern)
//   - radix_sort: LSD byte radix sort over u32
// ---------------------------------------------------------------------------

const MASK64 = 0xFFFFFFFFFFFFFFFFn;
const XXH_P1 = 0x9E3779B185EBCA87n;
const XXH_P2 = 0xC2B2AE3D27D4EB4Fn;
const XXH_P3 = 0x165667B19E3779F9n;
const XXH_P4 = 0x85EBCA77C2B2AE63n;
const XXH_P5 = 0x27D4EB2F165667C5n;

function rotl64(x, r) {
  return ((x << BigInt(r)) | (x >> BigInt(64 - r))) & MASK64;
}

function readU64LE(data, i) {
  let v = 0n;
  for (let k = 0; k < 8; k++) v |= BigInt(data[i + k]) << BigInt(8 * k);
  return v;
}

function readU32LE(data, i) {
  let v = 0;
  for (let k = 0; k < 4; k++) v |= data[i + k] << (8 * k);
  return v >>> 0;
}

function xxhRound(acc, inp) {
  acc = (acc + ((inp * XXH_P2) & MASK64)) & MASK64;
  acc = rotl64(acc, 31);
  return (acc * XXH_P1) & MASK64;
}

function xxhMerge(acc, val) {
  val = xxhRound(0n, val);
  acc ^= val;
  return ((acc * XXH_P1) + XXH_P4) & MASK64;
}

function xxh64(data, seed) {
  seed = BigInt(seed === undefined ? 0 : seed);
  const n = data.length;
  let h = 0n;
  let i = 0;
  if (n >= 32) {
    let v1 = (seed + XXH_P1 + XXH_P2) & MASK64;
    let v2 = (seed + XXH_P2) & MASK64;
    let v3 = seed & MASK64;
    let v4 = (seed - XXH_P1) & MASK64;
    while (i + 32 <= n) {
      v1 = xxhRound(v1, readU64LE(data, i));
      v2 = xxhRound(v2, readU64LE(data, i + 8));
      v3 = xxhRound(v3, readU64LE(data, i + 16));
      v4 = xxhRound(v4, readU64LE(data, i + 24));
      i += 32;
    }
    h = (rotl64(v1, 1) + rotl64(v2, 7) + rotl64(v3, 12) + rotl64(v4, 18)) & MASK64;
    h = xxhMerge(h, v1);
    h = xxhMerge(h, v2);
    h = xxhMerge(h, v3);
    h = xxhMerge(h, v4);
  } else {
    h = (seed + XXH_P5) & MASK64;
  }
  h = (h + BigInt(n)) & MASK64;
  while (i + 8 <= n) {
    const k1 = xxhRound(0n, readU64LE(data, i));
    h = rotl64(h ^ k1, 27);
    h = ((h * XXH_P1) + XXH_P4) & MASK64;
    i += 8;
  }
  if (i + 4 <= n) {
    h = (h ^ ((BigInt(readU32LE(data, i)) * XXH_P1) & MASK64)) & MASK64;
    h = rotl64(h, 23);
    h = ((h * XXH_P2) + XXH_P3) & MASK64;
    i += 4;
  }
  while (i < n) {
    h = (h ^ ((BigInt(data[i]) * XXH_P5) & MASK64)) & MASK64;
    h = (rotl64(h, 11) * XXH_P1) & MASK64;
    i += 1;
  }
  h ^= h >> 33n;
  h = (h * XXH_P2) & MASK64;
  h ^= h >> 29n;
  h = (h * XXH_P3) & MASK64;
  h ^= h >> 32n;
  return h & MASK64;
}

function checksum64(xs) {
  let s = 0n;
  for (let i = 0; i < xs.length; i++) s += BigInt(xs[i]) * BigInt(i + 1);
  return (s & MASK64).toString();
}

const LZ_MIN_MATCH = 4;
const LZ_MAX_OFFSET = 65535;
const LZ_MAX_MATCH = 65535;

function lzKey(data, i) {
  return (data[i] | (data[i + 1] << 8) | (data[i + 2] << 16) | (data[i + 3] << 24)) >>> 0;
}

function lz77Compress(data) {
  const n = data.length;
  const out = [];
  const table = new Map();
  let i = 0;
  while (i < n) {
    let off = -1;
    let mlen = 0;
    if (i + LZ_MIN_MATCH <= n) {
      const key = lzKey(data, i);
      const j = table.has(key) ? table.get(key) : -1;
      if (j >= 0 && i - j <= LZ_MAX_OFFSET) {
        let m = 0;
        const limit = Math.min(LZ_MAX_MATCH, n - i);
        while (m < limit && data[j + m] === data[i + m]) m++;
        if (m >= LZ_MIN_MATCH) { off = i - j; mlen = m; }
      }
    }
    if (off > 0) {
      out.push(1, off & 0xff, (off >> 8) & 0xff, mlen & 0xff, (mlen >> 8) & 0xff);
      for (let k = 1; k < mlen; k++) {
        if (i + k + LZ_MIN_MATCH <= n) table.set(lzKey(data, i + k), i + k);
      }
      i += mlen;
    } else {
      out.push(0, data[i]);
      if (i + LZ_MIN_MATCH <= n) table.set(lzKey(data, i), i);
      i++;
    }
  }
  return Uint8Array.from(out);
}

function lz77Decompress(comp) {
  const out = [];
  let i = 0;
  while (i < comp.length) {
    if (comp[i] === 0) {
      out.push(comp[i + 1]);
      i += 2;
    } else {
      const off = comp[i + 1] | (comp[i + 2] << 8);
      const mlen = comp[i + 3] | (comp[i + 4] << 8);
      let start = out.length - off;
      for (let m = 0; m < mlen; m++) { out.push(out[start]); start++; }
      i += 5;
    }
  }
  return Uint8Array.from(out);
}

function rotl32(x, r) {
  return ((x << r) | (x >>> (32 - r))) >>> 0;
}

function chachaQr(s, a, b, c, d) {
  s[a] = (s[a] + s[b]) >>> 0; s[d] = rotl32((s[d] ^ s[a]) >>> 0, 16);
  s[c] = (s[c] + s[d]) >>> 0; s[b] = rotl32((s[b] ^ s[c]) >>> 0, 12);
  s[a] = (s[a] + s[b]) >>> 0; s[d] = rotl32((s[d] ^ s[a]) >>> 0, 8);
  s[c] = (s[c] + s[d]) >>> 0; s[b] = rotl32((s[b] ^ s[c]) >>> 0, 7);
}

function le32(arr, i) {
  return (arr[i] | (arr[i + 1] << 8) | (arr[i + 2] << 16) | (arr[i + 3] << 24)) >>> 0;
}

function chacha20Block(key, counter, nonce) {
  const s = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574];
  for (let i = 0; i < 8; i++) s.push(le32(key, i * 4));
  s.push(counter >>> 0);
  for (let i = 0; i < 3; i++) s.push(le32(nonce, i * 4));
  const w = s.slice();
  for (let r = 0; r < 10; r++) {
    chachaQr(w, 0, 4, 8, 12); chachaQr(w, 1, 5, 9, 13);
    chachaQr(w, 2, 6, 10, 14); chachaQr(w, 3, 7, 11, 15);
    chachaQr(w, 0, 5, 10, 15); chachaQr(w, 1, 6, 11, 12);
    chachaQr(w, 2, 7, 8, 13); chachaQr(w, 3, 4, 9, 14);
  }
  const out = new Uint8Array(64);
  for (let i = 0; i < 16; i++) {
    const v = (w[i] + s[i]) >>> 0;
    out[i * 4] = v & 0xff;
    out[i * 4 + 1] = (v >>> 8) & 0xff;
    out[i * 4 + 2] = (v >>> 16) & 0xff;
    out[i * 4 + 3] = (v >>> 24) & 0xff;
  }
  return out;
}

function chacha20Encrypt(key, nonce, counter, plaintext) {
  const out = new Uint8Array(plaintext.length);
  let i = 0;
  let ctr = counter;
  while (i < plaintext.length) {
    const ks = chacha20Block(key, ctr, nonce);
    const take = Math.min(64, plaintext.length - i);
    for (let j = 0; j < take; j++) out[i + j] = plaintext[i + j] ^ ks[j];
    i += 64;
    ctr++;
  }
  return out;
}

function multiPatternCount(text, patterns) {
  let total = 0;
  for (const p of patterns) {
    let idx = text.indexOf(p);
    while (idx !== -1) { total++; idx = text.indexOf(p, idx + p.length); }
  }
  return total;
}

function radixSortU32(xs) {
  for (let shift = 0; shift < 32; shift += 8) {
    const buckets = Array.from({ length: 256 }, () => []);
    for (const v of xs) buckets[(v >>> shift) & 0xff].push(v);
    xs = [].concat(...buckets);
  }
  return xs;
}

function stdlibPattern() {
  return Uint8Array.from({ length: 256 }, (_, i) => i);
}

function repeatU8(base, reps) {
  const r = new Uint8Array(base.length * reps);
  for (let i = 0; i < reps; i++) r.set(base, i * base.length);
  return r;
}

const benchmarks = {
  fib: () => fib(32),
  sieve: () => sieve(50000),
  mandelbrot: () => mandelbrot(150, 100, 255),
  nbody: () => nbody(5, 5000),
  binary_trees: () => checkTree(makeTree(12)),
  stdlib_xxhash: () => xxh64(repeatU8(stdlibPattern(), 8192), 0n).toString(),
  stdlib_lz4: () => checksum64(lz77Decompress(lz77Compress(repeatU8(stdlibPattern(), 16384)))),
  stdlib_chacha20: () => {
    const key = Uint8Array.from({ length: 32 }, (_, i) => i);
    const nonce = Uint8Array.from([0, 0, 0, 9, 0, 0, 0, 0x4a, 0, 0, 0, 0]);
    const ct = chacha20Encrypt(key, nonce, 1, repeatU8(stdlibPattern(), 4096));
    return checksum64(ct);
  },
  stdlib_aho_corasick: () => {
    const patterns = [];
    for (let i = 0; i < 1000; i++) patterns.push("needle" + String(i).padStart(4, "0"));
    const filler = "the quick brown fox jumps over the lazy dog ";
    const text = filler.repeat(23000) + patterns.join(" ") + " ";
    return multiPatternCount(text, patterns);
  },
  stdlib_radix_sort: () => {
    const keys = [];
    for (let i = 0; i < 100000; i++) keys.push((i * 2654435761) >>> 0);
    return checksum64(radixSortU32(keys));
  },
};

const name = process.argv[2] || "fib";
console.log(benchmarks[name]());
