// ===============================================================
// GET /api/packages — Lateralus Package Registry Index
// Returns stdlib modules, community packages, and metadata
// ===============================================================

const SEC = {
  'Content-Type': 'application/json; charset=utf-8',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
};

const STDLIB_MODULES = [
  {
    name: 'std.io',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Standard I/O operations — println, print, eprintln, read_line',
    exports: ['println', 'print', 'eprintln', 'read_line', 'read_file', 'write_file'],
    since: '1.0.0',
  },
  {
    name: 'std.collections',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Core collection types — Vec, HashMap, HashSet, BTreeMap, Deque',
    exports: ['Vec', 'HashMap', 'HashSet', 'BTreeMap', 'Deque', 'PriorityQueue'],
    since: '1.0.0',
  },
  {
    name: 'std.math',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Mathematical functions and constants',
    exports: ['PI', 'E', 'TAU', 'abs', 'sqrt', 'pow', 'sin', 'cos', 'tan', 'log', 'log2', 'floor', 'ceil', 'round', 'min', 'max', 'clamp'],
    since: '1.0.0',
  },
  {
    name: 'std.string',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'String manipulation and formatting',
    exports: ['format', 'join', 'split', 'trim', 'pad_left', 'pad_right', 'replace', 'regex_match', 'to_upper', 'to_lower'],
    since: '1.0.0',
  },
  {
    name: 'std.iter',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Iterator adapters and lazy evaluation',
    exports: ['map', 'filter', 'fold', 'reduce', 'take', 'skip', 'zip', 'enumerate', 'chain', 'flat_map', 'any', 'all', 'sum', 'product', 'collect'],
    since: '1.0.0',
  },
  {
    name: 'std.net',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Networking primitives — TCP, UDP, DNS resolution',
    exports: ['TcpListener', 'TcpStream', 'UdpSocket', 'resolve', 'IpAddr'],
    since: '1.2.0',
  },
  {
    name: 'std.http',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'HTTP client and server with TLS support',
    exports: ['Server', 'Client', 'Request', 'Response', 'StatusCode', 'Header', 'get', 'post'],
    since: '2.0.0',
  },
  {
    name: 'std.json',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'JSON parsing and serialization',
    exports: ['parse', 'stringify', 'from_str', 'to_str', 'Value'],
    since: '1.0.0',
  },
  {
    name: 'std.fs',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Filesystem operations with path safety',
    exports: ['read', 'write', 'append', 'remove', 'mkdir', 'exists', 'walk', 'glob', 'Path'],
    since: '1.0.0',
  },
  {
    name: 'std.crypto',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Cryptographic primitives — hashing, HMAC, AES, key derivation',
    exports: ['sha256', 'sha512', 'hmac', 'aes_encrypt', 'aes_decrypt', 'pbkdf2', 'random_bytes', 'constant_time_eq'],
    since: '1.4.0',
  },
  {
    name: 'std.async',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Async runtime — green threads, channels, select',
    exports: ['spawn', 'sleep', 'timeout', 'Channel', 'Mutex', 'RwLock', 'select', 'join_all', 'race'],
    since: '2.0.0',
  },
  {
    name: 'std.time',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Date, time, duration, and timezone handling',
    exports: ['now', 'Duration', 'Instant', 'DateTime', 'parse_rfc3339', 'format', 'sleep'],
    since: '1.0.0',
  },
  {
    name: 'std.env',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Environment variables and process info',
    exports: ['get', 'set', 'vars', 'args', 'current_dir', 'exit'],
    since: '1.0.0',
  },
  {
    name: 'std.log',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Structured logging with levels and sinks',
    exports: ['debug', 'info', 'warn', 'error', 'Logger', 'set_level', 'Level'],
    since: '1.2.0',
  },
  {
    name: 'std.regex',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Regular expression engine',
    exports: ['Regex', 'match', 'find', 'find_all', 'replace', 'split', 'captures'],
    since: '1.0.0',
  },
  {
    name: 'std.testing',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Test framework — assertions, benchmarks, fuzzing',
    exports: ['assert', 'assert_eq', 'assert_ne', 'assert_throws', 'bench', 'fuzz', 'describe', 'it'],
    since: '1.0.0',
  },
  {
    name: 'std.encoding',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Base64, hex, URL encoding/decoding',
    exports: ['base64_encode', 'base64_decode', 'hex_encode', 'hex_decode', 'url_encode', 'url_decode'],
    since: '1.4.0',
  },
  {
    name: 'std.result',
    version: '3.0.1',
    kind: 'stdlib',
    description: 'Result and Option types for error handling',
    exports: ['Ok', 'Err', 'Some', 'None', 'Result', 'Option', 'unwrap', 'unwrap_or', 'map', 'and_then'],
    since: '1.0.0',
  },
];

const COMMUNITY_PACKAGES = [
  {
    name: 'lateralus-web',
    version: '1.3.0',
    kind: 'community',
    description: 'Full-stack web framework with routing, middleware, and templating',
    author: 'lateralus-lang',
    repository: 'https://github.com/lateralus-lang/lateralus-web',
    downloads: 12840,
    license: 'MIT',
  },
  {
    name: 'lateralus-orm',
    version: '0.9.2',
    kind: 'community',
    description: 'Type-safe ORM supporting SQLite, PostgreSQL, and MySQL',
    author: 'lateralus-lang',
    repository: 'https://github.com/lateralus-lang/lateralus-orm',
    downloads: 8620,
    license: 'MIT',
  },
  {
    name: 'lateralus-cli',
    version: '2.1.0',
    kind: 'community',
    description: 'CLI argument parser with auto-generated help and completions',
    author: 'lateralus-lang',
    repository: 'https://github.com/lateralus-lang/lateralus-cli',
    downloads: 15230,
    license: 'MIT',
  },
  {
    name: 'lateralus-test',
    version: '1.5.1',
    kind: 'community',
    description: 'Advanced testing framework with snapshot testing and coverage',
    author: 'lateralus-lang',
    repository: 'https://github.com/lateralus-lang/lateralus-test',
    downloads: 11450,
    license: 'MIT',
  },
  {
    name: 'lateralus-toml',
    version: '1.0.3',
    kind: 'community',
    description: 'TOML parser and serializer',
    author: 'community',
    repository: 'https://github.com/lateralus-lang/lateralus-toml',
    downloads: 6280,
    license: 'MIT',
  },
  {
    name: 'lateralus-yaml',
    version: '1.1.0',
    kind: 'community',
    description: 'YAML 1.2 parser and emitter',
    author: 'community',
    repository: 'https://github.com/lateralus-lang/lateralus-yaml',
    downloads: 4950,
    license: 'MIT',
  },
  {
    name: 'lateralus-ws',
    version: '0.8.0',
    kind: 'community',
    description: 'WebSocket client and server with auto-reconnect',
    author: 'lateralus-lang',
    repository: 'https://github.com/lateralus-lang/lateralus-ws',
    downloads: 3710,
    license: 'MIT',
  },
  {
    name: 'lateralus-graphql',
    version: '0.5.2',
    kind: 'community',
    description: 'GraphQL schema builder, resolver, and client',
    author: 'community',
    repository: 'https://github.com/lateralus-lang/lateralus-graphql',
    downloads: 2190,
    license: 'Apache-2.0',
  },
];

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const kind = url.searchParams.get('kind');     // stdlib | community
  const search = url.searchParams.get('q');       // search term
  const module = url.searchParams.get('module');  // specific module name

  let results = [...STDLIB_MODULES, ...COMMUNITY_PACKAGES];

  // Filter by kind
  if (kind === 'stdlib') results = results.filter(p => p.kind === 'stdlib');
  else if (kind === 'community') results = results.filter(p => p.kind === 'community');

  // Filter by search query
  if (search) {
    const q = search.toLowerCase();
    results = results.filter(p =>
      p.name.toLowerCase().includes(q) ||
      p.description.toLowerCase().includes(q) ||
      (p.exports && p.exports.some(e => e.toLowerCase().includes(q)))
    );
  }

  // Return single module detail
  if (module) {
    const found = results.find(p => p.name === module);
    if (!found) {
      return Response.json({ error: 'Module not found: ' + module }, {
        status: 404,
        headers: SEC,
      });
    }
    return Response.json({ package: found }, {
      status: 200,
      headers: { ...SEC, 'Cache-Control': 'public, max-age=3600' },
    });
  }

  return Response.json({
    total: results.length,
    stdlib_count: results.filter(p => p.kind === 'stdlib').length,
    community_count: results.filter(p => p.kind === 'community').length,
    packages: results,
    registry: {
      install: 'pip install lateralus-lang',
      add_package: 'lateralus pkg add <name>',
      publish: 'lateralus pkg publish',
      docs: 'https://lateralus.dev/docs/packages',
    },
  }, {
    status: 200,
    headers: { ...SEC, 'Cache-Control': 'public, max-age=3600, s-maxage=7200' },
  });
}

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: { ...SEC, 'Access-Control-Max-Age': '86400' } });
}
export async function onRequestPost() {
  return Response.json({ error: 'Method not allowed' }, { status: 405, headers: SEC });
}
export async function onRequestPut() {
  return Response.json({ error: 'Method not allowed' }, { status: 405, headers: SEC });
}
export async function onRequestDelete() {
  return Response.json({ error: 'Method not allowed' }, { status: 405, headers: SEC });
}
