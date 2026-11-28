#!/usr/bin/env node
// stdlib_bench.js — Node.js reference for the Lateralus stdlib micro-benchmarks.
//
// Line-for-line port of stdlib_bench.py.  Identical XorShift32 input generators
// (same seeds), identical algorithms, identical digest lines:
//
//     diff <(python3 stdlib_bench.py) <(node stdlib_bench.js)   # empty
//
// Five workloads exercising the pure-Lateralus stdlib modules:
//   1 xxhash64 (2 MB)   2 lz4 round-trip (4 MB)   3 chacha20 (1 MB)
//   4 aho_corasick (1,000 patterns / 1 MB)        5 radix_sort_u32 (100,000 keys)
//
// Correctness is pinned to published vectors (see selfCheck): xxh64(""),
// xxh64("abc"), xxh64("Nobody inspects the spammish repetition"),
// adler32("Wikipedia"), and the RFC 8439 §2.4.2 ChaCha20 block.
//
// MIT licensed.  Original work.
'use strict';

// ── 64-bit helpers via BigInt, masked to unsigned 64 ────────────────────────
const MASK64 = (1n << 64n) - 1n;
const MASK32 = 0xFFFFFFFF;

function u64(x) { return BigInt.asUintN(64, BigInt(x)); }

function rotl64(v, r) {
  v = BigInt.asUintN(64, BigInt(v));
  const rr = BigInt(r);
  return BigInt.asUintN(64, (v << rr) | (v >> (64n - rr)));
}

// ── deterministic input generation (XorShift32, identical in .py / .ltl) ────
class XorShift32 {
  constructor(seed) { this.s = seed >>> 0; }
  nextU32() {
    let x = this.s >>> 0;
    x ^= (x << 13) >>> 0;
    x ^= x >>> 17;
    x ^= (x << 5) >>> 0;
    this.s = x >>> 0;
    return this.s >>> 0;
  }
  nextByte() { return this.nextU32() & 0xFF; }
  bytes(n) {
    const out = Buffer.allocUnsafe(n);
    for (let i = 0; i < n; i++) out[i] = this.nextByte();
    return out;
  }
}

// ── 1. xxHash64 (canonical Cyan4973 XXH64, single-shot) ─────────────────────
const P1 = 0x9E3779B185EBCA87n;
const P2 = 0xC2B2AE3D27D4EB4Fn;
const P3 = 0x165667B19E3779F9n;
const P4 = 0x85EBCA77C2B2AE63n;
const P5 = 0x27D4EB2F165667C5n;

function round64(acc, inp) {
  acc = u64(BigInt(acc) + u64(BigInt(inp) * P2));
  acc = rotl64(acc, 31);
  return u64(acc * P1);
}

function mergeRound(acc, val) {
  val = round64(0, val);
  acc = BigInt(acc) ^ val;
  return u64(u64(acc * P1) + P4);
}

function xxh64(buf, seed = 0n) {
  const n = buf.length;
  let i = 0;
  let h;
  if (n >= 32) {
    let v1 = u64(seed + P1 + P2);
    let v2 = u64(seed + P2);
    let v3 = u64(seed + 0n);
    let v4 = u64(seed - P1);
    while (i + 32 <= n) {
      v1 = round64(v1, buf.readBigUInt64LE(i));
      v2 = round64(v2, buf.readBigUInt64LE(i + 8));
      v3 = round64(v3, buf.readBigUInt64LE(i + 16));
      v4 = round64(v4, buf.readBigUInt64LE(i + 24));
      i += 32;
    }
    h = u64(rotl64(v1, 1) + rotl64(v2, 7) + rotl64(v3, 12) + rotl64(v4, 18));
    h = mergeRound(h, v1);
    h = mergeRound(h, v2);
    h = mergeRound(h, v3);
    h = mergeRound(h, v4);
  } else {
    h = u64(seed + P5);
  }
  h = u64(h + BigInt(n));
  while (i + 8 <= n) {
    const k1 = round64(0, buf.readBigUInt64LE(i));
    h = rotl64(h ^ k1, 27);
    h = u64(u64(h * P1) + P4);
    i += 8;
  }
  if (i + 4 <= n) {
    h = u64(h ^ u64(BigInt(buf.readUInt32LE(i)) * P1));
    h = rotl64(h, 23);
    h = u64(u64(h * P2) + P3);
    i += 4;
  }
  while (i < n) {
    h = u64(h ^ u64(BigInt(buf[i]) * P5));
    h = u64(rotl64(h, 11) * P1);
    i += 1;
  }
  h = h ^ (h >> 33n);
  h = u64(h * P2);
  h = h ^ (h >> 29n);
  h = u64(h * P3);
  h = h ^ (h >> 32n);
  return h;
}

function adler32(buf) {
  let a = 1;
  let b = 0;
  for (let i = 0; i < buf.length; i++) {
    a = (a + buf[i]) % 65521;
    b = (b + a) % 65521;
  }
  return ((b << 16) | a) >>> 0;
}

// ── 2. LZ4 block format (greedy hash-chain matcher, "fast" mode) ────────────
const LZ4_MINMATCH = 4;
const LZ4_HASH_BITS = 12;
const LZ4_HASH_SIZE = 1 << LZ4_HASH_BITS;
const LZ4_HASH_MASK = LZ4_HASH_SIZE - 1;
const LZ4_MF_LIMIT = 12;
const LZ4_LAST_LITS = 5;
const LZ4_MAXD = 65535;

function lz4Hash4(buf, i) {
  const v = (buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24)) >>> 0;
  // Knuth multiplicative hash; wrap to 32 bits BEFORE the shift so the bucket
  // index matches the Python / Lateralus crawler exactly.
  const prod = Math.imul(v, 2654435761) >>> 0;
  return (prod >>> (32 - LZ4_HASH_BITS)) & LZ4_HASH_MASK;
}

function lz4Compress(src) {
  const n = src.length;
  const out = [];
  let anchor = 0;
  let i = 0;
  if (n < LZ4_MF_LIMIT + LZ4_LAST_LITS) {
    const litLen = n;
    if (litLen >= 15) {
      out.push(0xf0);
      let v = litLen - 15;
      while (v >= 255) { out.push(255); v -= 255; }
      out.push(v);
    } else {
      out.push((litLen << 4) & 0xff);
    }
    for (let k = 0; k < n; k++) out.push(src[k]);
    return Buffer.from(out);
  }
  const htab = new Int32Array(LZ4_HASH_SIZE).fill(-1);
  const endLimit = n - LZ4_MF_LIMIT - LZ4_LAST_LITS;
  while (i <= endLimit) {
    const hv = lz4Hash4(src, i);
    const refPos = htab[hv];
    htab[hv] = i;
    if (refPos >= 0 && i - refPos <= LZ4_MAXD
        && src[refPos] === src[i] && src[refPos + 1] === src[i + 1]
        && src[refPos + 2] === src[i + 2] && src[refPos + 3] === src[i + 3]) {
      let mlen = 4;
      while (i + mlen < n - LZ4_LAST_LITS && src[refPos + mlen] === src[i + mlen]) mlen++;
      const litLen = i - anchor;
      const mlenT = mlen - LZ4_MINMATCH;
      const tLit = litLen > 15 ? 15 : litLen;
      const tM = mlenT > 15 ? 15 : mlenT;
      out.push(((tLit << 4) | tM) & 0xff);
      if (litLen >= 15) {
        let v = litLen - 15;
        while (v >= 255) { out.push(255); v -= 255; }
        out.push(v);
      }
      for (let k = 0; k < litLen; k++) out.push(src[anchor + k]);
      const off = i - refPos;
      out.push(off & 0xff);
      out.push((off >> 8) & 0xff);
      if (mlenT >= 15) {
        let v = mlenT - 15;
        while (v >= 255) { out.push(255); v -= 255; }
        out.push(v);
      }
      i += mlen;
      anchor = i;
    } else {
      i++;
    }
  }
  const litLen = n - anchor;
  if (litLen >= 15) {
    out.push(0xf0);
    let v = litLen - 15;
    while (v >= 255) { out.push(255); v -= 255; }
    out.push(v);
  } else {
    out.push((litLen << 4) & 0xff);
  }
  for (let k = 0; k < litLen; k++) out.push(src[anchor + k]);
  return Buffer.from(out);
}

function lz4Decompress(src) {
  const n = src.length;
  const out = [];
  let i = 0;
  while (i < n) {
    const tok = src[i];
    i++;
    let litLen = (tok >> 4) & 0x0f;
    if (litLen === 15) {
      let b;
      do { b = src[i]; i++; litLen += b; } while (b === 255);
    }
    for (let k = 0; k < litLen; k++) out.push(src[i + k]);
    i += litLen;
    if (i >= n) return Buffer.from(out);
    const off = src[i] | (src[i + 1] << 8);
    i += 2;
    let mlen = tok & 0x0f;
    if (mlen === 15) {
      let b;
      do { b = src[i]; i++; mlen += b; } while (b === 255);
    }
    mlen += LZ4_MINMATCH;
    const start = out.length - off;
    for (let m = 0; m < mlen; m++) out.push(out[start + m]);
  }
  return Buffer.from(out);
}

// ── 3. ChaCha20 (RFC 8439) ──────────────────────────────────────────────────
function rotl32(v, n) {
  v = v >>> 0;
  return ((v << n) | (v >>> (32 - n))) >>> 0;
}

function quarterRound(s, a, b, c, d) {
  s[a] = (s[a] + s[b]) >>> 0; s[d] = rotl32(s[d] ^ s[a], 16);
  s[c] = (s[c] + s[d]) >>> 0; s[b] = rotl32(s[b] ^ s[c], 12);
  s[a] = (s[a] + s[b]) >>> 0; s[d] = rotl32(s[d] ^ s[a], 8);
  s[c] = (s[c] + s[d]) >>> 0; s[b] = rotl32(s[b] ^ s[c], 7);
}

function chacha20Block(key, counter, nonce) {
  const state = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574];
  for (let i = 0; i < 8; i++) state.push(key.readUInt32LE(i * 4));
  state.push(counter >>> 0);            // word 12
  for (let i = 0; i < 3; i++) state.push(nonce.readUInt32LE(i * 4)); // 13,14,15
  const working = state.slice();
  for (let r = 0; r < 10; r++) {
    quarterRound(working, 0, 4, 8, 12);
    quarterRound(working, 1, 5, 9, 13);
    quarterRound(working, 2, 6, 10, 14);
    quarterRound(working, 3, 7, 11, 15);
    quarterRound(working, 0, 5, 10, 15);
    quarterRound(working, 1, 6, 11, 12);
    quarterRound(working, 2, 7, 8, 13);
    quarterRound(working, 3, 4, 9, 14);
  }
  const out = Buffer.allocUnsafe(64);
  for (let i = 0; i < 16; i++) out.writeUInt32LE((working[i] + state[i]) >>> 0, i * 4);
  return out;
}

function chacha20Encrypt(key, nonce, data) {
  const out = Buffer.allocUnsafe(data.length);
  let offset = 0;
  let counter = 0;
  const n = data.length;
  while (offset < n) {
    const ks = chacha20Block(key, counter, nonce);
    counter = (counter + 1) >>> 0;
    const blockLen = Math.min(64, n - offset);
    for (let i = 0; i < blockLen; i++) out[offset + i] = data[offset + i] ^ ks[i];
    offset += blockLen;
  }
  return out;
}

// ── 4. Aho-Corasick multi-pattern search ────────────────────────────────────
function acBuild(patterns) {
  const goto = [new Map()];
  const fail = [0];
  const output = [[]];
  for (let pi = 0; pi < patterns.length; pi++) {
    const p = patterns[pi];
    let node = 0;
    for (let j = 0; j < p.length; j++) {
      const c = p.charCodeAt(j);
      if (goto[node].has(c)) {
        node = goto[node].get(c);
      } else {
        goto.push(new Map());
        fail.push(0);
        output.push([]);
        const newId = goto.length - 1;
        goto[node].set(c, newId);
        node = newId;
      }
    }
    output[node].push(pi);
  }
  const queue = [];
  for (const [, child] of goto[0]) { fail[child] = 0; queue.push(child); }
  let head = 0;
  while (head < queue.length) {
    const u = queue[head++];
    for (const [c, v] of goto[u]) {
      queue.push(v);
      let f = fail[u];
      while (f > 0 && !goto[f].has(c)) f = fail[f];
      let fallback = goto[f].get(c) || 0;
      if (fallback === v) fallback = 0;
      fail[v] = fallback;
      output[v] = output[v].concat(output[fallback]);
    }
  }
  return { goto, fail, output };
}

function acFindAll(auto, text) {
  const { goto, fail, output } = auto;
  let hits = 0;
  let node = 0;
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i);
    while (node > 0 && !goto[node].has(c)) node = fail[node];
    if (goto[node].has(c)) node = goto[node].get(c);
    hits += output[node].length;
  }
  return hits;
}

// ── 5. radix_sort_u32 (LSD byte radix, 4 passes) ────────────────────────────
function radixSortU32(xs) {
  let out = Uint32Array.from(xs);
  const tmp = new Uint32Array(out.length);
  for (const shift of [0, 8, 16, 24]) {
    const counts = new Uint32Array(256);
    for (let i = 0; i < out.length; i++) counts[(out[i] >>> shift) & 0xff]++;
    let total = 0;
    for (let b = 0; b < 256; b++) { const c = counts[b]; counts[b] = total; total += c; }
    for (let i = 0; i < out.length; i++) {
      const v = out[i];
      const b = (v >>> shift) & 0xff;
      tmp[counts[b]++] = v;
    }
    out = tmp.slice();
  }
  return out;
}

// ── correctness self-check (published vectors) ──────────────────────────────
function selfCheck() {
  const assert = (cond, msg) => { if (!cond) throw new Error("self-check failed: " + msg); };
  assert(xxh64(Buffer.alloc(0)) === 0xEF46DB3751D8E999n, "xxh64('')");
  assert(xxh64(Buffer.from("abc")) === 0x44BC2CF5AD770999n, "xxh64('abc')");
  assert(xxh64(Buffer.from("Nobody inspects the spammish repetition")) === 0xFBCEA83C8A378BF1n, "xxh64(spam)");
  assert(adler32(Buffer.from("Wikipedia")) === 0x11E60398, "adler32(Wikipedia)");
  // RFC 8439 §2.4.2 ChaCha20 block: key 00..1f, nonce 000000000000004a00000000,
  // counter 1 -> first 16 keystream bytes 224f51f3401bd9e12fde276fb8631ded.
  const key = Buffer.alloc(32);
  for (let i = 0; i < 32; i++) key[i] = i;
  const nonce = Buffer.from("000000000000004a00000000", "hex");
  const ks = chacha20Block(key, 1, nonce);
  assert(ks.slice(0, 16).toString("hex") === "224f51f3401bd9e12fde276fb8631ded", "chacha20 block");
}

// ── formatting helpers ──────────────────────────────────────────────────────
function hex64(v) { return BigInt.asUintN(64, v).toString(16).padStart(16, "0"); }
function hex32(v) { return BigInt.asUintN(32, BigInt(v)).toString(16).padStart(8, "0"); }

// Two size profiles.  "full" is the headline benchmark (issue #865 table).
// "verify" is a reduced size at which the pure-Lateralus tree-walking
// interpreter can run in a few seconds while still producing digest lines
// that match CPython and Node.js *exactly* (same seeds, same algorithms).
const PROFILES = {
  full:   { xxhash: 2 * 1024 * 1024, lz4: 4 * 1024 * 1024, chacha: 1 * 1024 * 1024, acPatterns: 1000, acText: 1 * 1024 * 1024, radix: 100000 },
  verify: { xxhash: 512, lz4: 2048, chacha: 512, acPatterns: 40, acText: 2048, radix: 2000 },
};

function run(which, profile) {
  selfCheck();
  const selected = which || "all";
  const sz = PROFILES[profile || "full"];

  if (selected === "all" || selected === "xxhash") {
    const data = new XorShift32(0x1234ABCD).bytes(sz.xxhash);
    console.log("xxhash " + hex64(xxh64(data, 0n)));
  }

  if (selected === "all" || selected === "lz4") {
    const src = new XorShift32(0xFEEDFACE).bytes(sz.lz4);
    const packed = lz4Compress(src);
    const back = lz4Decompress(packed);
    const ok = Buffer.compare(Buffer.from(back), src) === 0 ? "ok" : "BAD";
    console.log(`lz4 ${ok}:${src.length}:${hex32(adler32(back))}:${packed.length}`);
  }

  if (selected === "all" || selected === "chacha20") {
    const key = new XorShift32(0x0BADF00D).bytes(32);
    const nonce = new XorShift32(0x00C0FFEE).bytes(12);
    const data = new XorShift32(0xDEADBEEF).bytes(sz.chacha);
    const ct = chacha20Encrypt(key, nonce, data);
    const h1 = xxh64(ct, 0n);
    const h2 = xxh64(ct, 1n);
    console.log(`chacha20 ${hex64(h1)}:${hex32(h2)}`);
  }

  if (selected === "all" || selected === "aho_corasick") {
    const rng = new XorShift32(0x5EED1234);
    const alphabet = "ACGT";
    const patterns = [];
    for (let p = 0; p < sz.acPatterns; p++) {
      const plen = 4 + (rng.nextU32() % 5);
      let s = "";
      for (let k = 0; k < plen; k++) s += alphabet[rng.nextU32() % 4];
      patterns.push(s);
    }
    const total = sz.acText;
    let text = "";
    const chunk = [];
    for (let i = 0; i < total; i++) {
      chunk.push(alphabet[rng.nextU32() % 4]);
      if (chunk.length === 8192) { text += chunk.join(""); chunk.length = 0; }
    }
    if (chunk.length) text += chunk.join("");
    const auto = acBuild(patterns);
    const hits = acFindAll(auto, text);
    console.log(`aho_corasick ${hits}`);
  }

  if (selected === "all" || selected === "radix_sort") {
    const rng = new XorShift32(0x0BADCAFE);
    const keys = new Array(sz.radix);
    for (let i = 0; i < sz.radix; i++) keys[i] = rng.nextU32();
    const srt = radixSortU32(keys);
    const first = srt.length ? srt[0] : 0;
    const last = srt.length ? srt[srt.length - 1] : 0;
    let acc = 0;
    for (let i = 0; i < srt.length; i++) acc = (acc ^ srt[i]) >>> 0;
    console.log(`radix_sort_u32 ${hex32(first)}:${hex32(last)}:${hex32(acc)}`);
  }
}

function main(argv) {
  const which = argv[2] || "all";
  const profile = argv[3] || "full";
  const t0 = process.hrtime.bigint();
  run(which, profile);
  const dt = Number(process.hrtime.bigint() - t0) / 1e9;
  console.error(`# node ${process.version} profile=${profile} elapsed ${dt.toFixed(3)}s`);
  return 0;
}

process.exit(main(process.argv));