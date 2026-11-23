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

// --- stdlib benchmarks (benchmark-ingest) ---
// Same deterministic inputs as benchmarks/src/*.ltl, same expected outputs.
// Independent JavaScript reference implementations of the same algorithms
// specified by stdlib/{xxhash,lz4,chacha20,aho_corasick,radix_sort}.ltl.
// They must agree byte-for-byte with the .ltl and Python outputs.
//
// Precision notes: the glibc LCG product (1103515245 * st) exceeds 2^53,
// so it is done with Math.imul (exact 32-bit) and masked to 31 bits.
// XXH64 needs exact 64-bit arithmetic, so it uses BigInt. ChaCha20 and
// the radix sort are 32-bit and use >>> 0 / Math.imul throughout.

const WORDS = ["the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog",
  "lateralus", "bench", "hash", "sort", "stream", "codec", "crypto",
  "search", "pattern", "text", "data", "node", "leaf", "tree",
  "graph", "queue", "stack", "buffer", "cache", "index", "token",
  "parse", "lexer", "parser", "codegen", "python", "node", "rust",
  "go", "fast", "slow", "small", "large", "green", "blue", "red",
  "river", "stone", "cloud", "storm", "flame", "ember", "frost",
  "iron", "gold", "sand", "wave", "spiral", "light", "dark", "zero",
  "prime", "delta"];

function lcgBytes(n, seed) {
  const out = new Uint8Array(n);
  let st = seed >>> 0;
  for (let i = 0; i < n; i++) {
    st = (Math.imul(1103515245, st) + 12345) >>> 0;
    st = st & 0x7fffffff;
    out[i] = (st >> 16) & 0xff;
  }
  return out;
}

function textChunk(nbytes, seed) {
  const out = new Uint8Array(nbytes);
  let st = seed >>> 0;
  let wp = 0;
  while (wp < nbytes) {
    st = (Math.imul(1103515245, st) + 12345) >>> 0;
    st = st & 0x7fffffff;
    const w = WORDS[(st >> 16) % WORDS.length];
    for (let k = 0; k < w.length && wp < nbytes; k++) {
      out[wp++] = w.charCodeAt(k);
    }
    if (wp < nbytes) out[wp++] = 32;
  }
  return out;
}

function textStr(n, seed) {
  let st = seed >>> 0;
  const words = [];
  let total = 0;
  while (total < n) {
    st = (Math.imul(1103515245, st) + 12345) >>> 0;
    st = st & 0x7fffffff;
    const w = WORDS[(st >> 16) % WORDS.length];
    words.push(w);
    total += w.length + 1;
  }
  return words.join(" ").slice(0, n);
}

function genPatterns() {
  let st = 31337 >>> 0;
  const pats = [];
  for (let i = 0; i < 1000; i++) {
    st = (Math.imul(1103515245, st) + 12345) >>> 0;
    st = st & 0x7fffffff;
    const nw = 2 + ((st >> 16) % 2);
    const ws = [];
    for (let j = 0; j < nw; j++) {
      st = (Math.imul(1103515245, st) + 12345) >>> 0;
      st = st & 0x7fffffff;
      ws.push(WORDS[(st >> 16) % WORDS.length]);
    }
    pats.push(ws.join(" "));
  }
  return pats;
}

// --- XXH64 (BigInt, exact 64-bit) ---
const M64 = (1n << 64n) - 1n;
const P1 = 11400714785074694791n;
const P2 = 14029467366897019727n;
const P3 = 1609587929392839161n;
const P4 = 9650029242287828579n;
const P5 = 2870177450012600261n;

function u64(x) { return x & M64; }
function rotl64(v, r) {
  v &= M64;
  return ((v << BigInt(r)) | (v >> BigInt(64 - r))) & M64;
}
function r32(buf, i) {
  // BigInt arithmetic throughout: the JS `<< 24` on a byte >= 128 yields a
  // negative signed 32-bit int, which would corrupt the word. Building the
  // word from BigInt bytes is exact.
  return BigInt(buf[i]) | (BigInt(buf[i + 1]) << 8n)
    | (BigInt(buf[i + 2]) << 16n) | (BigInt(buf[i + 3]) << 24n);
}
function r64(buf, i) { return r32(buf, i) | (r32(buf, i + 4) << 32n); }
function round64(acc, lane) {
  acc = u64(acc + lane * P2);
  acc = rotl64(acc, 31);
  return u64(acc * P1);
}
function mergeRound(acc, v) {
  v = round64(0n, v);
  acc ^= v;
  return u64(acc * P1 + P4);
}
function xxh64(buf, seed = 0) {
  const n = buf.length;
  const s = BigInt(seed);
  let h;
  let i = 0;
  if (n >= 32) {
    let v1 = u64(s + P1 + P2);
    let v2 = u64(s + P2);
    let v3 = u64(s);
    let v4 = u64(s - P1);
    while (i + 32 <= n) {
      v1 = round64(v1, r64(buf, i));
      v2 = round64(v2, r64(buf, i + 8));
      v3 = round64(v3, r64(buf, i + 16));
      v4 = round64(v4, r64(buf, i + 24));
      i += 32;
    }
    h = u64(rotl64(v1, 1) + rotl64(v2, 7) + rotl64(v3, 12) + rotl64(v4, 18));
    h = mergeRound(h, v1);
    h = mergeRound(h, v2);
    h = mergeRound(h, v3);
    h = mergeRound(h, v4);
  } else {
    h = u64(s + P5);
  }
  h = u64(h + BigInt(n));
  while (i + 8 <= n) {
    const k = round64(0n, r64(buf, i));
    h ^= k;
    h = u64(rotl64(h, 27) * P1 + P4);
    i += 8;
  }
  if (i + 4 <= n) {
    h ^= u64(r32(buf, i) * P1);
    h = u64(rotl64(h, 23) * P2 + P3);
    i += 4;
  }
  while (i < n) {
    h ^= u64(BigInt(buf[i]) * P5);
    h = u64(rotl64(h, 11) * P1);
    i += 1;
  }
  h ^= h >> 33n;
  h = u64(h * P2);
  h ^= h >> 29n;
  h = u64(h * P3);
  h ^= h >> 32n;
  return h;
}

// --- LZ4 block codec ---
const LZ_MINMATCH = 4;
const LZ_HASH_BITS = 12;
const LZ_HASH_SIZE = 4096;
const LZ_HASH_MASK = 4095;
const LZ_MF_LIMIT = 12;
const LZ_LAST_LITS = 5;
const LZ_MAXD = 65535;

function lzHash4(buf, i) {
  const v = buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24);
  return ((Math.imul(v, 2654435761) >>> (32 - LZ_HASH_BITS)) & LZ_HASH_MASK);
}
function lzEmit(out, v) {
  while (v >= 255) { out.push(255); v -= 255; }
  out.push(v);
}
function lz4Compress(src) {
  const n = src.length;
  const out = [];
  let anchor = 0;
  let i = 0;
  if (n < LZ_MF_LIMIT + LZ_LAST_LITS) {
    const litLen = n;
    if (litLen >= 15) { out.push(0xf0); lzEmit(out, litLen - 15); }
    else out.push((litLen << 4) & 0xff);
    for (let k = 0; k < n; k++) out.push(src[k]);
    return out;
  }
  const htab = new Int32Array(LZ_HASH_SIZE).fill(-1);
  const endLimit = n - LZ_MF_LIMIT - LZ_LAST_LITS;
  while (i <= endLimit) {
    const hv = lzHash4(src, i);
    const refPos = htab[hv];
    htab[hv] = i;
    if (refPos >= 0 && i - refPos <= LZ_MAXD
        && src[refPos] === src[i] && src[refPos + 1] === src[i + 1]
        && src[refPos + 2] === src[i + 2] && src[refPos + 3] === src[i + 3]) {
      let mlen = 4;
      while (i + mlen < n - LZ_LAST_LITS && src[refPos + mlen] === src[i + mlen]) mlen++;
      const litLen = i - anchor;
      const mlenT = mlen - LZ_MINMATCH;
      const tLit = litLen <= 15 ? litLen : 15;
      const tM = mlenT <= 15 ? mlenT : 15;
      out.push(((tLit << 4) | tM) & 0xff);
      if (litLen >= 15) lzEmit(out, litLen - 15);
      for (let k = 0; k < litLen; k++) out.push(src[anchor + k]);
      const off = i - refPos;
      out.push(off & 0xff);
      out.push((off >> 8) & 0xff);
      if (mlenT >= 15) lzEmit(out, mlenT - 15);
      i += mlen;
      anchor = i;
    } else {
      i++;
    }
  }
  const litLen = n - anchor;
  if (litLen >= 15) { out.push(0xf0); lzEmit(out, litLen - 15); }
  else out.push((litLen << 4) & 0xff);
  for (let k = 0; k < litLen; k++) out.push(src[anchor + k]);
  return out;
}
function lz4Decompress(src) {
  const n = src.length;
  const out = [];
  let i = 0;
  while (i < n) {
    const tok = src[i++];
    let litLen = (tok >> 4) & 0x0f;
    if (litLen === 15) {
      for (;;) {
        const b = src[i++];
        litLen += b;
        if (b !== 255) break;
      }
    }
    for (let k = 0; k < litLen; k++) out.push(src[i + k]);
    i += litLen;
    if (i >= n) return out;
    const off = src[i] | (src[i + 1] << 8);
    i += 2;
    let mlen = tok & 0x0f;
    if (mlen === 15) {
      for (;;) {
        const b2 = src[i++];
        mlen += b2;
        if (b2 !== 255) break;
      }
    }
    mlen += LZ_MINMATCH;
    const start = out.length - off;
    for (let m = 0; m < mlen; m++) out.push(out[start + m]);
  }
  return out;
}

// --- ChaCha20 (RFC 8439) ---
function ccRotl(v, r) { return ((v << r) | (v >>> (32 - r))) >>> 0; }
function ccR32(buf, i) {
  return (buf[i] | (buf[i + 1] << 8) | (buf[i + 2] << 16) | (buf[i + 3] << 24)) >>> 0;
}
function ccQr(s, a, b, c, d) {
  s[a] = (s[a] + s[b]) >>> 0; s[d] = ccRotl(s[d] ^ s[a], 16);
  s[c] = (s[c] + s[d]) >>> 0; s[b] = ccRotl(s[b] ^ s[c], 12);
  s[a] = (s[a] + s[b]) >>> 0; s[d] = ccRotl(s[d] ^ s[a], 8);
  s[c] = (s[c] + s[d]) >>> 0; s[b] = ccRotl(s[b] ^ s[c], 7);
}
function ccBlock(key, nonce, counter) {
  const s = [
    0x61707865, 0x3320646e, 0x79622d32, 0x6b206574,
    ccR32(key, 0), ccR32(key, 4), ccR32(key, 8), ccR32(key, 12),
    ccR32(key, 16), ccR32(key, 20), ccR32(key, 24), ccR32(key, 28),
    counter >>> 0,
    ccR32(nonce, 0), ccR32(nonce, 4), ccR32(nonce, 8),
  ];
  const w = s.slice();
  for (let r = 0; r < 10; r++) {
    ccQr(w, 0, 4, 8, 12); ccQr(w, 1, 5, 9, 13);
    ccQr(w, 2, 6, 10, 14); ccQr(w, 3, 7, 11, 15);
    ccQr(w, 0, 5, 10, 15); ccQr(w, 1, 6, 11, 12);
    ccQr(w, 2, 7, 8, 13); ccQr(w, 3, 4, 9, 14);
  }
  const out = [];
  for (let k = 0; k < 16; k++) {
    const v = (w[k] + s[k]) >>> 0;
    out.push(v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff, (v >> 24) & 0xff);
  }
  return out;
}
function chacha20Xor(key, nonce, initialCounter, data) {
  const out = [];
  const n = data.length;
  let i = 0;
  let counter = initialCounter;
  while (i < n) {
    const ks = ccBlock(key, nonce, counter);
    const take = Math.min(64, n - i);
    for (let j = 0; j < take; j++) out.push(data[i + j] ^ ks[j]);
    i += 64;
    counter++;
  }
  return out;
}

// --- Aho-Corasick ---
function acBuild(patterns) {
  const auto = { goto: [new Map()], fail: [0], output: [[]], patterns };
  for (let pid = 0; pid < patterns.length; pid++) {
    const p = patterns[pid];
    let node = 0;
    for (const ch of p) {
      let nxt = auto.goto[node].get(ch);
      if (nxt === undefined) {
        nxt = auto.goto.length;
        auto.goto.push(new Map());
        auto.fail.push(0);
        auto.output.push([]);
        auto.goto[node].set(ch, nxt);
      }
      node = nxt;
    }
    auto.output[node].push(pid);
  }
  const queue = [];
  for (const [ch, nxt] of auto.goto[0]) {
    auto.fail[nxt] = 0;
    queue.push(nxt);
  }
  let head = 0;
  while (head < queue.length) {
    const r = queue[head++];
    for (const [ch, s] of auto.goto[r]) {
      queue.push(s);
      let state = auto.fail[r];
      while (state !== 0 && !auto.goto[state].has(ch)) state = auto.fail[state];
      auto.fail[s] = auto.goto[state].get(ch) ?? 0;
      auto.output[s] = auto.output[s].concat(auto.output[auto.fail[s]]);
    }
  }
  return auto;
}
function acFindAll(auto, text) {
  const hits = [];
  let state = 0;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    while (state !== 0 && !auto.goto[state].has(ch)) state = auto.fail[state];
    state = auto.goto[state].get(ch) ?? 0;
    for (const pid of auto.output[state]) hits.push([pid, i + 1]);
  }
  return hits;
}

// --- LSD radix sort (base 256) ---
function radixSortU32(arr) {
  let cur = Array.from(arr);
  for (let byteIdx = 0; byteIdx < 4; byteIdx++) {
    const counts = new Uint32Array(256);
    for (const v of cur) counts[(v >>> (byteIdx * 8)) & 0xff]++;
    const starts = new Uint32Array(256);
    let acc = 0;
    for (let b = 0; b < 256; b++) { starts[b] = acc; acc += counts[b]; }
    const out = new Uint32Array(cur.length);
    for (const v of cur) {
      const b = (v >>> (byteIdx * 8)) & 0xff;
      out[starts[b]++] = v;
    }
    cur = out;
  }
  return cur;
}

function benchXxhash64() {
  return xxh64(lcgBytes(2097152, 777), 0).toString();
}
function benchLz4Rt() {
  const data = textChunk(4194304, 12345);
  const comp = lz4Compress(data);
  const dec = lz4Decompress(comp);
  return `${comp.length} ${xxh64(comp, 0)} ${xxh64(dec, 0)}`;
}
function benchChacha20() {
  const data = lcgBytes(1048576, 999);
  const key = Array.from({ length: 32 }, (_, k) => k);
  const ct = chacha20Xor(key, new Array(12).fill(0), 1, data);
  return xxh64(ct, 0).toString();
}
function benchAhoCorasick() {
  const text = textStr(1048576, 12345);
  const pats = genPatterns();
  const auto = acBuild(pats);
  const hits = acFindAll(auto, text);
  let sumPid = 0, sumEnd = 0;
  for (const h of hits) { sumPid += h[0]; sumEnd += h[1]; }
  const first = hits[0], last = hits[hits.length - 1];
  return `${hits.length} ${first[0]} ${first[1]} ${last[0]} ${last[1]} ${sumPid} ${sumEnd}`;
}
function benchRadixSortU32() {
  let st = 2024 >>> 0;
  const keys = new Uint32Array(100000);
  for (let i = 0; i < 100000; i++) {
    st = (Math.imul(1664525, st) + 1013904223) >>> 0;
    keys[i] = st;
  }
  const srt = radixSortU32(keys);
  let total = 0;
  for (const v of srt) total += v;
  const first5 = Array.from(srt.slice(0, 5)).join(" ");
  const last5 = Array.from(srt.slice(-5)).join(" ");
  return `${first5} ${last5} ${total}`;
}

const benchmarks = {
  fib: () => fib(32),
  sieve: () => sieve(50000),
  mandelbrot: () => mandelbrot(150, 100, 255),
  nbody: () => nbody(5, 5000),
  binary_trees: () => checkTree(makeTree(12)),
  xxhash64: benchXxhash64,
  lz4_rt: benchLz4Rt,
  chacha20: benchChacha20,
  aho_corasick: benchAhoCorasick,
  radix_sort_u32: benchRadixSortU32,
};

const name = process.argv[2] || "fib";
console.log(benchmarks[name]());
