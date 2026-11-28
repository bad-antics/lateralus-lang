#!/usr/bin/env node
/**
 * Stdlib micro-benchmark reference implementations (Node.js).
 *
 * Byte-for-byte twin of reference/stdlib_bench.py: same PRNG, same input
 * generators, same algorithms, same digest lines. Run both and `diff`:
 *
 *     python3 stdlib_bench.py all > py.txt
 *     node stdlib_bench.js all > js.txt
 *     diff py.txt js.txt && echo identical
 */
"use strict";

const M32 = 0xffffffffn;
const M64 = 0xffffffffffffffffn;
const P1 = 0x9e3779b185ebca87n;
const P2 = 0xc2b2ae3d27d4eb4fn;
const P3 = 0x165667b19e3779f9n;
const P4 = 0x85ebca77c2b2ae63n;
const P5 = 0x27d4eb2f165667c5n;

// ── deterministic input generators (mirror stdlib_bench.py) ────────────────
class XorShift32 {
  constructor(seed) {
    this.s = (seed >>> 0) || 0x9e3779b9;
  }
  next() {
    let x = this.s >>> 0;
    x ^= (x << 13) >>> 0;
    x = x >>> 0;
    x ^= x >>> 17;
    x = x >>> 0;
    x ^= (x << 5) >>> 0;
    this.s = x >>> 0;
    return this.s;
  }
}

function genBytes(n, seed) {
  const rng = new XorShift32(seed);
  const out = new Uint8Array(n);
  for (let i = 0; i < n; i += 4) {
    const w = rng.next();
    out[i] = w & 0xff;
    if (i + 1 < n) out[i + 1] = (w >>> 8) & 0xff;
    if (i + 2 < n) out[i + 2] = (w >>> 16) & 0xff;
    if (i + 3 < n) out[i + 3] = (w >>> 24) & 0xff;
  }
  return out;
}

function genU32(n, seed) {
  const rng = new XorShift32(seed);
  const out = new Uint32Array(n);
  for (let i = 0; i < n; i++) out[i] = rng.next();
  return out;
}

function genText(n, seed) {
  const rng = new XorShift32(seed);
  const out = new Uint8Array(n);
  for (let i = 0; i < n; i++) out[i] = 32 + (rng.next() % 95);
  return out;
}

function genPatterns(count, seed, text) {
  const rng = new XorShift32(seed);
  const pats = [];
  for (let i = 0; i < count; i++) {
    if (i % 4 !== 0 && text.length > 16) {
      const ln = 4 + (rng.next() % 9);
      const start = rng.next() % (text.length - ln);
      pats.push(text.slice(start, start + ln));
    } else {
      const ln = 4 + (rng.next() % 9);
      const p = new Uint8Array(ln);
      for (let k = 0; k < ln; k++) p[k] = 32 + (rng.next() % 95);
      pats.push(p);
    }
  }
  return pats;
}

// ── 1. xxHash64 ────────────────────────────────────────────────────────────
function rotl64(x, r) {
  const rr = BigInt(r);
  return ((x << rr) | (x >> (64n - rr))) & M64;
}

function round64(acc, lane) {
  let a = (acc + ((lane * P2) & M64)) & M64;
  a = rotl64(a, 31);
  return (a * P1) & M64;
}

function merge64(acc, val) {
  let a = acc ^ round64(0n, val);
  return ((a * P1) + P4) & M64;
}

function readU64LE(buf, off) {
  let v = 0n;
  for (let i = 7; i >= 0; i--) v = (v << 8n) | BigInt(buf[off + i]);
  return v;
}

function xxh64(data, seed = 0n) {
  const n = data.length;
  let i = 0;
  let h;
  if (n >= 32) {
    let v1 = (seed + P1 + P2) & M64;
    let v2 = (seed + P2) & M64;
    let v3 = seed & M64;
    let v4 = (seed - P1) & M64;
    while (i + 32 <= n) {
      v1 = round64(v1, readU64LE(data, i));
      v2 = round64(v2, readU64LE(data, i + 8));
      v3 = round64(v3, readU64LE(data, i + 16));
      v4 = round64(v4, readU64LE(data, i + 24));
      i += 32;
    }
    h = (rotl64(v1, 1) + rotl64(v2, 7) + rotl64(v3, 12) + rotl64(v4, 18)) & M64;
    h = merge64(h, v1);
    h = merge64(h, v2);
    h = merge64(h, v3);
    h = merge64(h, v4);
  } else {
    h = (seed + P5) & M64;
  }
  h = (h + BigInt(n)) & M64;
  while (i + 8 <= n) {
    h ^= round64(0n, readU64LE(data, i));
    h = ((rotl64(h, 27) * P1) + P4) & M64;
    i += 8;
  }
  if (i + 4 <= n) {
    const w = BigInt(
      data[i] | (data[i + 1] << 8) | (data[i + 2] << 16) | (data[i + 3] << 24)
    ) & M64;
    h ^= (w * P1) & M64;
    h = ((rotl64(h, 23) * P2) + P3) & M64;
    i += 4;
  }
  while (i < n) {
    h ^= (BigInt(data[i]) * P5) & M64;
    h = (rotl64(h, 11) * P1) & M64;
    i += 1;
  }
  h ^= h >> 33n;
  h = (h * P2) & M64;
  h ^= h >> 29n;
  h = (h * P3) & M64;
  h ^= h >> 32n;
  return h;
}

// ── 2. LZ4 block ───────────────────────────────────────────────────────────
const MIN_MATCH = 4;
const HASH_BITS = 12;
const MAX_OFFSET = 65535;

function lz4Compress(src) {
  const n = src.length;
  const out = [];
  const table = new Map();
  let anchor = 0;
  let i = 0;
  const push = (b) => out.push(b & 0xff);

  while (i + MIN_MATCH <= n) {
    const word =
      (src[i] | (src[i + 1] << 8) | (src[i + 2] << 16) | (src[i + 3] << 24)) >>> 0;
    const key = Math.imul(word, 2654435761) >>> (32 - HASH_BITS);
    const cand = table.has(key) ? table.get(key) : -1;
    table.set(key, i);
    let matched = false;
    if (
      cand >= 0 &&
      i - cand <= MAX_OFFSET &&
      src[cand] === src[i] &&
      src[cand + 1] === src[i + 1] &&
      src[cand + 2] === src[i + 2] &&
      src[cand + 3] === src[i + 3]
    ) {
      matched = true;
      let ml = MIN_MATCH;
      while (i + ml < n && cand + ml < i && src[cand + ml] === src[i + ml]) ml++;
      const lit = i - anchor;
      const tokenLit = Math.min(lit, 15);
      const tokenMl = ml - MIN_MATCH;
      push((tokenLit << 4) | Math.min(tokenMl, 15));
      if (lit >= 15) {
        let rem = lit - 15;
        while (rem >= 255) {
          push(255);
          rem -= 255;
        }
        push(rem);
      }
      for (let k = anchor; k < i; k++) push(src[k]);
      const off = i - cand;
      push(off & 0xff);
      push((off >> 8) & 0xff);
      if (tokenMl >= 15) {
        let rem = tokenMl - 15;
        while (rem >= 255) {
          push(255);
          rem -= 255;
        }
        push(rem);
      }
      i += ml;
      anchor = i;
    }
    if (!matched) i += 1;
  }

  const lit = n - anchor;
  const tokenLit = Math.min(lit, 15);
  push(tokenLit << 4);
  if (lit >= 15) {
    let rem = lit - 15;
    while (rem >= 255) {
      push(255);
      rem -= 255;
    }
    push(rem);
  }
  for (let k = anchor; k < n; k++) push(src[k]);
  return Uint8Array.from(out);
}

function lz4Decompress(src, outLen) {
  const out = new Uint8Array(outLen);
  let o = 0;
  let i = 0;
  const n = src.length;
  while (i < n && o < outLen) {
    const token = src[i++];
    let lit = token >> 4;
    if (lit === 15) {
      for (;;) {
        const b = src[i++];
        lit += b;
        if (b !== 255) break;
      }
    }
    for (let k = 0; k < lit; k++) out[o++] = src[i++];
    if (i >= n || o >= outLen) break;
    const off = src[i] | (src[i + 1] << 8);
    i += 2;
    if (off === 0) throw new Error("bad offset");
    let ml = token & 0x0f;
    if (ml === 15) {
      for (;;) {
        const b = src[i++];
        ml += b;
        if (b !== 255) break;
      }
    }
    ml += MIN_MATCH;
    let start = o - off;
    for (let k = 0; k < ml; k++) out[o++] = out[start + k];
  }
  if (o !== outLen) throw new Error(`length mismatch ${o} != ${outLen}`);
  return out;
}

// ── 3. ChaCha20 ────────────────────────────────────────────────────────────
const rotl32 = (v, c) => ((v << c) | (v >>> (32 - c))) >>> 0;

function quarter(s, a, b, c, d) {
  s[a] = (s[a] + s[b]) >>> 0;
  s[d] = rotl32(s[d] ^ s[a], 16);
  s[c] = (s[c] + s[d]) >>> 0;
  s[b] = rotl32(s[b] ^ s[c], 12);
  s[a] = (s[a] + s[b]) >>> 0;
  s[d] = rotl32(s[d] ^ s[a], 8);
  s[c] = (s[c] + s[d]) >>> 0;
  s[b] = rotl32(s[b] ^ s[c], 7);
}

const readU32LE = (b, i) =>
  ((b[i] | (b[i + 1] << 8) | (b[i + 2] << 16) | (b[i + 3] << 24)) >>> 0);

function chacha20Block(key, counter, nonce) {
  const c = new Uint32Array(16);
  c[0] = 0x61707865;
  c[1] = 0x3320646e;
  c[2] = 0x79622d32;
  c[3] = 0x6b206574;
  for (let i = 0; i < 8; i++) c[4 + i] = readU32LE(key, i * 4);
  c[12] = counter >>> 0;
  c[13] = 0;
  c[14] = 0;
  c[15] = 0;
  // nonce occupies words 13..15 in the RFC layout (counter at 12)
  c[13] = readU32LE(nonce, 0);
  c[14] = readU32LE(nonce, 4);
  c[15] = readU32LE(nonce, 8);
  const w = Uint32Array.from(c);
  for (let i = 0; i < 10; i++) {
    quarter(w, 0, 4, 8, 12);
    quarter(w, 1, 5, 9, 13);
    quarter(w, 2, 6, 10, 14);
    quarter(w, 3, 7, 11, 15);
    quarter(w, 0, 5, 10, 15);
    quarter(w, 1, 6, 11, 12);
    quarter(w, 2, 7, 8, 13);
    quarter(w, 3, 4, 9, 14);
  }
  const out = new Uint8Array(64);
  for (let i = 0; i < 16; i++) {
    const v = (w[i] + c[i]) >>> 0;
    out[i * 4] = v & 0xff;
    out[i * 4 + 1] = (v >>> 8) & 0xff;
    out[i * 4 + 2] = (v >>> 16) & 0xff;
    out[i * 4 + 3] = (v >>> 24) & 0xff;
  }
  return out;
}

function chacha20Keystream(n, key, nonce) {
  const out = new Uint8Array(n);
  let o = 0;
  let ctr = 1;
  while (o < n) {
    const blk = chacha20Block(key, ctr++, nonce);
    const take = Math.min(64, n - o);
    out.set(blk.subarray(0, take), o);
    o += take;
  }
  return out;
}

// ── 4. Aho–Corasick ────────────────────────────────────────────────────────
function acScan(text, patterns) {
  const goto = [new Map()];
  const fail = [0];
  const cnt = [0];
  for (const p of patterns) {
    let cur = 0;
    for (const ch of p) {
      let nxt = goto[cur].get(ch);
      if (nxt === undefined) {
        goto.push(new Map());
        fail.push(0);
        cnt.push(0);
        nxt = goto.length - 1;
        goto[cur].set(ch, nxt);
      }
      cur = nxt;
    }
    cnt[cur] += 1;
  }
  const q = [];
  for (const [, s] of goto[0]) {
    fail[s] = 0;
    q.push(s);
  }
  let head = 0;
  while (head < q.length) {
    const r = q[head++];
    for (const [ch, s] of goto[r]) {
      q.push(s);
      let f = fail[r];
      while (f && !goto[f].has(ch)) f = fail[f];
      fail[s] = goto[f].has(ch) ? goto[f].get(ch) : 0;
      if (fail[s] === s) fail[s] = 0;
      cnt[s] += cnt[fail[s]];
    }
  }
  let state = 0;
  let total = 0;
  for (const ch of text) {
    while (state && !goto[state].has(ch)) state = fail[state];
    state = goto[state].has(ch) ? goto[state].get(ch) : 0;
    total += cnt[state];
  }
  return total;
}

// ── 5. radix sort u32 ──────────────────────────────────────────────────────
function radixSortU32(a) {
  const n = a.length;
  let src = Uint32Array.from(a);
  let dst = new Uint32Array(n);
  for (const shift of [0, 8, 16, 24]) {
    const cnt = new Uint32Array(256);
    for (let i = 0; i < n; i++) cnt[(src[i] >>> shift) & 0xff]++;
    let total = 0;
    for (let i = 0; i < 256; i++) {
      const c = cnt[i];
      cnt[i] = total;
      total += c;
    }
    for (let i = 0; i < n; i++) {
      const b = (src[i] >>> shift) & 0xff;
      dst[cnt[b]++] = src[i];
    }
    const t = src;
    src = dst;
    dst = t;
  }
  return src;
}

// ── checksum ───────────────────────────────────────────────────────────────
function adler32(data) {
  let a = 1;
  let b = 0;
  for (let i = 0; i < data.length; i++) {
    a = (a + data[i]) % 65521;
    b = (b + a) % 65521;
  }
  return (((b << 16) | a) >>> 0).toString(16).padStart(8, "0");
}

// ── workloads ──────────────────────────────────────────────────────────────
const bench = {
  xxhash() {
    const data = genBytes(2 * 1024 * 1024, 0x12345678);
    return xxh64(data).toString(16).padStart(16, "0");
  },
  lz4() {
    const data = genBytes(4 * 1024 * 1024, 0x2468ace0);
    const packed = lz4Compress(data);
    const back = lz4Decompress(packed, data.length);
    for (let i = 0; i < data.length; i++) {
      if (back[i] !== data[i]) throw new Error("lz4 round-trip mismatch");
    }
    return `ok:${data.length}:${adler32(packed)}:${packed.length}`;
  },
  chacha20() {
    const data = genBytes(1024 * 1024, 0x0badf00d);
    const key = Uint8Array.from({ length: 32 }, (_, i) => i);
    const nonce = Uint8Array.from({ length: 12 }, (_, i) => i);
    const ks = chacha20Keystream(data.length, key, nonce);
    const ct = new Uint8Array(data.length);
    for (let i = 0; i < data.length; i++) ct[i] = data[i] ^ ks[i];
    const head = Array.from(ct.slice(0, 8), (b) => b.toString(16).padStart(2, "0")).join("");
    return `${head}:${adler32(ct)}`;
  },
  aho_corasick() {
    const text = genText(1024 * 1024, 0x5eed1234);
    const pats = genPatterns(1000, 0xc0ffee11, text);
    return `${acScan(text, pats)}`;
  },
  radix_sort_u32() {
    const keys = genU32(100000, 0xdeadbeef);
    const s = radixSortU32(keys);
    const raw = new Uint8Array(s.length * 4);
    for (let i = 0; i < s.length; i++) {
      raw[i * 4] = s[i] & 0xff;
      raw[i * 4 + 1] = (s[i] >>> 8) & 0xff;
      raw[i * 4 + 2] = (s[i] >>> 16) & 0xff;
      raw[i * 4 + 3] = (s[i] >>> 24) & 0xff;
    }
    const hex = (v) => (v >>> 0).toString(16).padStart(8, "0");
    return `${hex(s[0])}:${hex(s[s.length - 1])}:${adler32(raw)}`;
  },
};

// RFC 8439 §2.4.2 test vector for the block function
(function selfTest() {
  const key = Uint8Array.from({ length: 32 }, (_, i) => i);
  const nonce = Uint8Array.from([0, 0, 0, 9, 0, 0, 0, 0x4a, 0, 0, 0, 0]);
  const blk = chacha20Block(key, 1, nonce);
  const want = "10f1e7e4d13b5915500fdd1fa32071c4";
  const got = Array.from(blk.slice(0, 16), (b) => b.toString(16).padStart(2, "0")).join("");
  if (got !== want) {
    console.error(`chacha20 block != RFC 8439 vector: ${got}`);
    process.exit(3);
  }
})();

const which = process.argv[2] || "all";
if (which === "all") {
  for (const [name, fn] of Object.entries(bench)) console.log(`${name} ${fn()}`);
} else if (bench[which]) {
  console.log(`${which} ${bench[which]()}`);
} else {
  console.error(`unknown benchmark ${which}`);
  process.exit(2);
}