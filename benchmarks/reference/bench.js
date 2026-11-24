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

const benchmarks = {
  fib: () => fib(32),
  sieve: () => sieve(50000),
  mandelbrot: () => mandelbrot(150, 100, 255),
  nbody: () => nbody(5, 5000),
  binary_trees: () => checkTree(makeTree(12)),
};

// ---------------------------------------------------------------------------
// stdlib micro-benchmark references (bounty: benchmark-ingest, issue #156).
// Each mirrors benchmarks/src/stdlib/*_driver.ltl exactly.
// ---------------------------------------------------------------------------

const M32 = 0xFFFFFFFF;
const M64 = 0xFFFFFFFFFFFFFFFFn;

function genByte(x) { return (x * 31 + 7) & 0xFF; }
function genKey(x) { return Math.imul(x, 2654435761) >>> 0; }

// --- xxhash64 (stdlib/xxhash.ltl) -----------------------------------------
const XXH_P1 = 0x9E3779B185EBCA87n;
const XXH_P2 = 0xC2B2AE3D27D4EB4Fn;
const XXH_P3 = 0x165667B19E3779F9n;
const XXH_P4 = 0x85EBCA77C2B2AE63n;
const XXH_P5 = 0x27D4EB2F165667C5n;

function rotl64(v, r) {
  v &= M64;
  return ((v << BigInt(r)) | (v >> BigInt(64 - r))) & M64;
}
function round64(acc, inp) {
  acc = (acc + inp * XXH_P2) & M64;
  acc = rotl64(acc, 31);
  return (acc * XXH_P1) & M64;
}
function mergeRound(acc, val) {
  val = round64(0n, val);
  acc ^= val;
  return ((acc * XXH_P1) & M64) + XXH_P4 & M64;
}
function readU64LE(buf, i) {
  return (BigInt(buf[i]) | (BigInt(buf[i + 1]) << 8n) | (BigInt(buf[i + 2]) << 16n)
    | (BigInt(buf[i + 3]) << 24n) | (BigInt(buf[i + 4]) << 32n)
    | (BigInt(buf[i + 5]) << 40n) | (BigInt(buf[i + 6]) << 48n)
    | (BigInt(buf[i + 7]) << 56n));
}
function readU32LE(buf, i) {
  return (buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24)) >>> 0;
}
function xxhash64(buf, seed) {
  const n = buf.length;
  let h;
  let i = 0;
  if (n >= 32) {
    let v1 = (BigInt(seed) + XXH_P1 + XXH_P2) & M64;
    let v2 = (BigInt(seed) + XXH_P2) & M64;
    let v3 = BigInt(seed) & M64;
    let v4 = (BigInt(seed) - XXH_P1) & M64;
    const limit = n - 32;
    while (i <= limit) {
      v1 = round64(v1, readU64LE(buf, i)); i += 8;
      v2 = round64(v2, readU64LE(buf, i)); i += 8;
      v3 = round64(v3, readU64LE(buf, i)); i += 8;
      v4 = round64(v4, readU64LE(buf, i)); i += 8;
    }
    h = (rotl64(v1, 1) + rotl64(v2, 7) + rotl64(v3, 12) + rotl64(v4, 18)) & M64;
    h = mergeRound(h, v1); h = mergeRound(h, v2);
    h = mergeRound(h, v3); h = mergeRound(h, v4);
  } else {
    h = (BigInt(seed) + XXH_P5) & M64;
  }
  h = (h + BigInt(n)) & M64;
  while (i + 8 <= n) {
    const k1 = round64(0n, readU64LE(buf, i));
    h ^= k1;
    h = (rotl64(h, 27) * XXH_P1 + XXH_P4) & M64;
    i += 8;
  }
  if (i + 4 <= n) {
    h ^= BigInt(readU32LE(buf, i)) * XXH_P1 & M64;
    h = (rotl64(h, 23) * XXH_P2 + XXH_P3) & M64;
    i += 4;
  }
  while (i < n) {
    h ^= BigInt(buf[i]) * XXH_P5 & M64;
    h = (rotl64(h, 11) * XXH_P1) & M64;
    i += 1;
  }
  h ^= h >> 33n; h = (h * XXH_P2) & M64;
  h ^= h >> 29n; h = (h * XXH_P3) & M64;
  h ^= h >> 32n;
  return h;
}
function benchXxhash() {
  const buf = new Array(2000000);
  for (let x = 0; x < 2000000; x++) buf[x] = genByte(x);
  return xxhash64(buf, 0).toString();
}

// --- lz4 compress + decompress round-trip (stdlib/lz4.ltl) ----------------
const LZ4_MINMATCH = 4;
const LZ4_HASH_BITS = 12;
const LZ4_HASH_SIZE = 1 << LZ4_HASH_BITS;
const LZ4_HASH_MASK = LZ4_HASH_SIZE - 1;
const LZ4_MF_LIMIT = 12;
const LZ4_LAST_LITS = 5;
const LZ4_MAXD = 65535;

function hash4(buf, i) {
  const v = (buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24)) >>> 0;
  return (Math.imul(v, 2654435761) >>> (32 - LZ4_HASH_BITS)) & LZ4_HASH_MASK;
}
function emitVarLen(out, v) {
  while (v >= 255) { out.push(255); v -= 255; }
  out.push(v);
}
function lz4Compress(src) {
  const n = src.length;
  const out = [];
  let anchor = 0;
  let i = 0;
  if (n < LZ4_MF_LIMIT + LZ4_LAST_LITS) {
    const litLen = n;
    if (litLen >= 15) {
      out.push(0xF0);
      emitVarLen(out, litLen - 15);
    } else {
      out.push((litLen << 4) & 0xFF);
    }
    for (let k = 0; k < n; k++) out.push(src[k]);
    return out;
  }
  const htab = new Int32Array(LZ4_HASH_SIZE).fill(-1);
  const endLimit = n - LZ4_MF_LIMIT - LZ4_LAST_LITS;
  while (i <= endLimit) {
    const hv = hash4(src, i);
    const refPos = htab[hv];
    htab[hv] = i;
    if (refPos >= 0 && i - refPos <= LZ4_MAXD
        && src[refPos] === src[i]
        && src[refPos + 1] === src[i + 1]
        && src[refPos + 2] === src[i + 2]
        && src[refPos + 3] === src[i + 3]) {
      let mlen = 4;
      while (i + mlen < n - LZ4_LAST_LITS && src[refPos + mlen] === src[i + mlen]) mlen++;
      const litLen = i - anchor;
      const mlenT = mlen - LZ4_MINMATCH;
      const tLit = Math.min(litLen, 15);
      const tM = Math.min(mlenT, 15);
      out.push(((tLit << 4) | tM) & 0xFF);
      if (litLen >= 15) emitVarLen(out, litLen - 15);
      for (let k = 0; k < litLen; k++) out.push(src[anchor + k]);
      const off = i - refPos;
      out.push(off & 0xFF);
      out.push((off >> 8) & 0xFF);
      if (mlenT >= 15) emitVarLen(out, mlenT - 15);
      i += mlen;
      anchor = i;
    } else {
      i += 1;
    }
  }
  const litLen = n - anchor;
  if (litLen >= 15) {
    out.push(0xF0);
    emitVarLen(out, litLen - 15);
  } else {
    out.push((litLen << 4) & 0xFF);
  }
  for (let k = 0; k < litLen; k++) out.push(src[anchor + k]);
  return out;
}
function lz4Decompress(src) {
  const n = src.length;
  const out = [];
  let i = 0;
  while (i < n) {
    const tok = src[i]; i++;
    let litLen = (tok >> 4) & 0x0F;
    if (litLen === 15) {
      let b;
      do { b = src[i]; i++; litLen += b; } while (b === 255);
    }
    for (let k = 0; k < litLen; k++) out.push(src[i + k]);
    i += litLen;
    if (i >= n) return out;
    const off = src[i] | (src[i + 1] << 8); i += 2;
    let mlen = tok & 0x0F;
    if (mlen === 15) {
      let b;
      do { b = src[i]; i++; mlen += b; } while (b === 255);
    }
    mlen += LZ4_MINMATCH;
    const start = out.length - off;
    for (let m = 0; m < mlen; m++) out.push(out[start + m]);
  }
  return out;
}
function benchLz4() {
  const src = new Array(100000);
  for (let x = 0; x < 100000; x++) src[x] = genByte(x);
  const c = lz4Compress(src);
  const d = lz4Decompress(c);
  return `${src.length} ${c.length} ${d.length}`;
}

// --- chacha20 (stdlib/chacha20.ltl) ---------------------------------------
function rotl32(x, n) {
  return ((x << n) | (x >>> (32 - n))) >>> 0;
}
function qr(s, a, b, c, d) {
  s[a] = (s[a] + s[b]) >>> 0; s[d] ^= s[a]; s[d] = rotl32(s[d], 16);
  s[c] = (s[c] + s[d]) >>> 0; s[b] ^= s[c]; s[b] = rotl32(s[b], 12);
  s[a] = (s[a] + s[b]) >>> 0; s[d] ^= s[a]; s[d] = rotl32(s[d], 8);
  s[c] = (s[c] + s[d]) >>> 0; s[b] ^= s[c]; s[b] = rotl32(s[b], 7);
}
function u32ToLE(v) {
  return [v & 0xFF, (v >>> 8) & 0xFF, (v >>> 16) & 0xFF, (v >>> 24) & 0xFF];
}
function ccBlock(key, nonce, counter) {
  const s = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574];
  for (let i = 0; i < 32; i += 4) s.push(readU32LE(key, i));
  s.push(counter >>> 0);
  for (let i = 0; i < 12; i += 4) s.push(readU32LE(nonce, i));
  const w = s.slice();
  for (let r = 0; r < 10; r++) {
    qr(w, 0, 4, 8, 12); qr(w, 1, 5, 9, 13);
    qr(w, 2, 6, 10, 14); qr(w, 3, 7, 11, 15);
    qr(w, 0, 5, 10, 15); qr(w, 1, 6, 11, 12);
    qr(w, 2, 7, 8, 13); qr(w, 3, 4, 9, 14);
  }
  const out = [];
  for (let i = 0; i < 16; i++) out.push(...u32ToLE((w[i] + s[i]) >>> 0));
  return out;
}
function chacha20Xor(key, nonce, counter, data) {
  const out = [];
  const n = data.length;
  let i = 0;
  while (i < n) {
    const ks = ccBlock(key, nonce, counter);
    const take = Math.min(64, n - i);
    for (let j = 0; j < take; j++) out.push(data[i + j] ^ ks[j]);
    i += 64;
    counter++;
  }
  return out;
}
function benchChacha20() {
  const key = new Array(32);
  const nonce = new Array(12);
  const data = new Array(150000);
  for (let x = 0; x < 32; x++) key[x] = genByte(x);
  for (let x = 0; x < 12; x++) nonce[x] = genByte(x);
  for (let x = 0; x < 150000; x++) data[x] = genByte(x);
  const ct = chacha20Xor(key, nonce, 0, data);
  return `${ct.length} ${ct[12345]}`;
}

// --- aho_corasick (stdlib/aho_corasick.ltl) -------------------------------
function acBuild(patterns) {
  const goto_ = [new Map()];
  const fail = [0];
  const output = [[]];
  for (let pid = 0; pid < patterns.length; pid++) {
    let node = 0;
    for (const ch of patterns[pid]) {
      if (!goto_[node].has(ch)) {
        goto_.push(new Map()); fail.push(0); output.push([]);
        goto_[node].set(ch, goto_.length - 1);
      }
      node = goto_[node].get(ch);
    }
    output[node].push(pid);
  }
  const dq = [];
  for (const nx of goto_[0].values()) dq.push(nx);
  let head = 0;
  while (head < dq.length) {
    const r = dq[head++];
    for (const [ch, nx] of goto_[r]) {
      dq.push(nx);
      let f = fail[r];
      while (f > 0 && !goto_[f].has(ch)) f = fail[f];
      if (goto_[f].has(ch) && goto_[f].get(ch) !== nx) fail[nx] = goto_[f].get(ch);
      output[nx] = output[nx].concat(output[fail[nx]]);
    }
  }
  return { goto: goto_, fail, output };
}
function acFindAll(auto, text) {
  const hits = [];
  let node = 0;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    while (node > 0 && !auto.goto[node].has(ch)) node = auto.fail[node];
    if (auto.goto[node].has(ch)) node = auto.goto[node].get(ch);
    for (const pid of auto.output[node]) hits.push([pid, i + 1]);
  }
  return hits;
}
function benchAhoCorasick() {
  const pats = ["the", "quick", "brown", "fox", "jumps", "lazy", "dog",
    "hello", "world", "lateralus"];
  const auto = acBuild(pats);
  const text = "the quick brown fox jumps over the lazy dog hello world lateralus ";
  const big = text.repeat(3000);
  const hits = acFindAll(auto, big);
  return `${big.length} ${hits.length}`;
}

// --- radix_sort_u32 (stdlib/radix_sort.ltl) -------------------------------
function radixPass(xs, shift) {
  const counts = new Array(256).fill(0);
  const out = new Array(xs.length);
  for (const x of xs) counts[(x >>> shift) & 0xFF]++;
  let s = 0;
  for (let i = 0; i < 256; i++) { const c = counts[i]; counts[i] = s; s += c; }
  for (const x of xs) {
    const b = (x >>> shift) & 0xFF;
    out[counts[b]] = x;
    counts[b]++;
  }
  return out;
}
function radixSortU32(xs) {
  for (const sh of [0, 8, 16, 24]) xs = radixPass(xs, sh);
  return xs;
}
function benchRadixSort() {
  const xs = new Array(100000);
  for (let x = 0; x < 100000; x++) xs[x] = genKey(x);
  const s = radixSortU32(xs);
  return `${s.length} ${s[0]} ${s[99999]}`;
}

const stdlibBenchmarks = {
  xxhash: benchXxhash,
  lz4: benchLz4,
  chacha20: benchChacha20,
  aho_corasick: benchAhoCorasick,
  radix_sort: benchRadixSort,
};

const name = process.argv[2] || "fib";
if (stdlibBenchmarks[name]) {
  console.log(stdlibBenchmarks[name]());
} else {
  console.log(benchmarks[name]());
}
