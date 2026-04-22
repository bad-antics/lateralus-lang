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

const name = process.argv[2] || "fib";
console.log(benchmarks[name]());
