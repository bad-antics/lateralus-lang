// ===============================================================
// GET /api/version — Lateralus Language Version Info
// Public, cacheable, no auth required
// ===============================================================

const VERSION_DATA = {
  language: "Lateralus",
  version: "3.0.1",
  compiler: {
    name: "lateralus-lang",
    version: "3.0.1",
    targets: ["python", "c99", "freestanding-c"],
    install: "pip install lateralus-lang",
  },
  stdlib: {
    version: "3.0.1",
    modules: 18,
  },
  vm: {
    name: "Lateralus VM",
    version: "3.0.1",
  },
  release: {
    date: "2026-03-28",
    channel: "stable",
    changelog: "https://github.com/bad-antics/lateralus-lang/releases/tag/v3.0.1",
  },
  repository: "https://github.com/bad-antics/lateralus-lang",
  homepage: "https://lateralus.dev",
  file_extension: ".ltl",
};

const HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'public, max-age=300, s-maxage=600',
  'X-Content-Type-Options': 'nosniff',
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
};

export async function onRequestGet() {
  return Response.json(VERSION_DATA, { status: 200, headers: HEADERS });
}

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      ...HEADERS,
      'Access-Control-Max-Age': '86400',
    },
  });
}

// Block everything else
export async function onRequestPost() {
  return Response.json({ error: 'Method not allowed' }, { status: 405, headers: HEADERS });
}
export async function onRequestPut() {
  return Response.json({ error: 'Method not allowed' }, { status: 405, headers: HEADERS });
}
export async function onRequestDelete() {
  return Response.json({ error: 'Method not allowed' }, { status: 405, headers: HEADERS });
}
