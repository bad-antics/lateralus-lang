// ============================================================================
// docs/website/playground/wasm-shim.js
// Browser-friendly WebAssembly Host Runtime Shim for Lateralus (`lateralus wasm`)
//
// Maps Lateralus WASM host imports (`println`, `print`, `eprintln`, `http_get`,
// numeric print helpers, timing, and dynamic AST host intrinsics) to JavaScript
// and browser APIs without sending source code off the user's machine.
// ============================================================================

(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.LateralusWasmShim = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const UTF8_DECODER = new TextDecoder("utf-8");
  const UTF8_ENCODER = new TextEncoder();

  const DEFAULT_MAX_LINES = 500;
  const DEFAULT_MAX_BYTES = 65536;
  const DEFAULT_HTTP_TIMEOUT_MS = 6000;
  const DEFAULT_MAX_HTTP_REPLAYS = 16;

  class HttpSuspenseSignal extends Error {
    constructor(url) {
      super("Suspending WASM execution to fetch " + url);
      this.name = "HttpSuspenseSignal";
      this.url = url;
    }
  }

  class RuntimeLimitError extends Error {
    constructor(message) {
      super(message);
      this.name = "RuntimeLimitError";
    }
  }

  function nowMillis() {
    if (typeof performance !== "undefined" && typeof performance.now === "function") {
      return performance.now();
    }
    return Date.now();
  }

  /**
   * Create an isolated host shim instance for a single WebAssembly instantiation.
   *
   * @param {Object} [options]
   * @param {Map<string, {ok:boolean, status:number, body:string}>} [options.httpCache]
   * @param {boolean} [options.suspendOnUncachedHttp=true]
   * @param {number} [options.maxLines=500]
   * @param {number} [options.maxBytes=65536]
   * @param {(line: string, stream: "stdout"|"stderr") => void} [options.onLine]
   * @param {(astJson: string, ioBridge: Object) => number|bigint} [options.astExecutor]
   */
  function createLateralusHostShim(options) {
    const opts = options || {};
    const maxLines = opts.maxLines || DEFAULT_MAX_LINES;
    const maxBytes = opts.maxBytes || DEFAULT_MAX_BYTES;
    const httpCache = opts.httpCache instanceof Map ? opts.httpCache : new Map();
    const suspendOnUncachedHttp = opts.suspendOnUncachedHttp !== false;

    let wasmMemory = null;
    let totalBytes = 0;
    let partialLine = "";
    let lastHttpStatus = 0;
    const stdoutLines = [];
    const stderrLines = [];
    const httpRequests = [];

    function ensureMemory() {
      if (!wasmMemory) {
        throw new Error("WASM linear memory has not been bound to the host shim");
      }
      return new Uint8Array(wasmMemory.buffer);
    }

    function readUtf8(ptr, len) {
      const p = Number(ptr) >>> 0;
      const n = Number(len) >>> 0;
      if (n === 0) return "";
      const bytes = ensureMemory();
      const end = Math.min(bytes.length, p + n);
      return UTF8_DECODER.decode(bytes.subarray(p, end));
    }

    function readCString(ptr) {
      const p = Number(ptr) >>> 0;
      const bytes = ensureMemory();
      let end = p;
      while (end < bytes.length && bytes[end] !== 0) {
        end++;
      }
      return UTF8_DECODER.decode(bytes.subarray(p, end));
    }

    function writeUtf8(ptr, cap, text) {
      const p = Number(ptr) >>> 0;
      const maxLen = Math.max(0, Number(cap) | 0);
      if (maxLen === 0) return 0;
      const encoded = UTF8_ENCODER.encode(String(text ?? ""));
      const bytes = ensureMemory();
      const writable = Math.min(encoded.length, maxLen, Math.max(0, bytes.length - p));
      bytes.set(encoded.subarray(0, writable), p);
      return writable;
    }

    function pushLine(text, stream) {
      const fullText = partialLine + String(text ?? "");
      partialLine = "";
      const segments = fullText.split("\n");
      for (let i = 0; i < segments.length; i++) {
        if (stdoutLines.length + stderrLines.length >= maxLines) {
          throw new RuntimeLimitError("Output limit exceeded (max " + maxLines + " lines)");
        }
        const seg = segments[i];
        totalBytes += seg.length + 1;
        if (totalBytes > maxBytes) {
          throw new RuntimeLimitError("Output byte limit exceeded (max " + maxBytes + " bytes)");
        }
        if (stream === "stderr") {
          stderrLines.push(seg);
        } else {
          stdoutLines.push(seg);
        }
        if (typeof opts.onLine === "function") {
          opts.onLine(seg, stream);
        }
      }
    }

    function appendPrint(text) {
      const chunk = String(text ?? "");
      totalBytes += chunk.length;
      if (totalBytes > maxBytes) {
        throw new RuntimeLimitError("Output byte limit exceeded (max " + maxBytes + " bytes)");
      }
      const combined = partialLine + chunk;
      const parts = combined.split("\n");
      partialLine = parts.pop() || "";
      for (let i = 0; i < parts.length; i++) {
        if (stdoutLines.length + stderrLines.length >= maxLines) {
          throw new RuntimeLimitError("Output limit exceeded (max " + maxLines + " lines)");
        }
        stdoutLines.push(parts[i]);
        if (typeof opts.onLine === "function") {
          opts.onLine(parts[i], "stdout");
        }
      }
    }

    function flush() {
      if (partialLine.length > 0) {
        stdoutLines.push(partialLine);
        if (typeof opts.onLine === "function") {
          opts.onLine(partialLine, "stdout");
        }
        partialLine = "";
      }
    }

    function performHttpGet(url, outPtr, outCap) {
      const cleanUrl = String(url || "").trim();
      if (!cleanUrl) {
        lastHttpStatus = 400;
        return writeUtf8(outPtr, outCap, "");
      }

      if (!httpCache.has(cleanUrl)) {
        if (suspendOnUncachedHttp) {
          throw new HttpSuspenseSignal(cleanUrl);
        }
        lastHttpStatus = 0;
        return -1;
      }

      const cached = httpCache.get(cleanUrl);
      httpRequests.push({
        url: cleanUrl,
        status: cached.status,
        ok: cached.ok,
        bytes: UTF8_ENCODER.encode(cached.body || "").length,
      });
      lastHttpStatus = cached.status;

      if (!cached.ok && opts.returnNegativeOnHttpError) {
        writeUtf8(outPtr, outCap, cached.body || "");
        return -1;
      }
      return writeUtf8(outPtr, outCap, cached.body || "");
    }

    // Scratch region at [0..64) in linear memory is reserved header space in WasmModule,
    // used when dynamic Tier-2 intrinsics marshal strings through WASM memory exports.
    function emitStringThroughLinearMemory(str, isStderr, newline) {
      const text = String(str ?? "");
      if (wasmMemory) {
        const encoded = UTF8_ENCODER.encode(text);
        const memBytes = ensureMemory();
        // If string fits in reserved scratch [0..64), round-trip via WASM memory
        if (encoded.length <= 64 && memBytes.length >= 64) {
          memBytes.set(encoded, 0);
          if (isStderr) {
            imports.env.eprintln(0, encoded.length);
          } else if (newline) {
            imports.env.println(0, encoded.length);
          } else {
            imports.env.print(0, encoded.length);
          }
          return;
        }
      }
      if (isStderr) {
        pushLine(text, "stderr");
      } else if (newline) {
        pushLine(text, "stdout");
      } else {
        appendPrint(text);
      }
    }

    const imports = {
      env: {
        println(ptr, len) {
          pushLine(readUtf8(ptr, len), "stdout");
        },
        print(ptr, len) {
          appendPrint(readUtf8(ptr, len));
        },
        eprintln(ptr, len) {
          pushLine(readUtf8(ptr, len), "stderr");
        },
        println_i64(val) {
          pushLine(String(val), "stdout");
        },
        ltl_println_i64(val) {
          pushLine(String(val), "stdout");
        },
        println_f64(val) {
          const n = Number(val);
          pushLine(Number.isInteger(n) ? n.toFixed(1) : String(n), "stdout");
        },
        ltl_println_f64(val) {
          const n = Number(val);
          pushLine(Number.isInteger(n) ? n.toFixed(1) : String(n), "stdout");
        },
        println_bool(val) {
          pushLine(Number(val) !== 0 ? "true" : "false", "stdout");
        },
        http_get(urlPtr, urlLen, outPtr, outCap) {
          const url = readUtf8(urlPtr, urlLen);
          return performHttpGet(url, outPtr, outCap);
        },
        http_status() {
          return lastHttpStatus | 0;
        },
        now_ms() {
          return BigInt(Math.round(nowMillis()));
        },
        rt_exec_ast(astPtr, astLen) {
          if (typeof opts.astExecutor !== "function") {
            throw new Error("Dynamic AST host executor is not configured on this shim");
          }
          const astJson = readUtf8(astPtr, astLen);
          const rc = opts.astExecutor(astJson, {
            println(line) {
              emitStringThroughLinearMemory(line, false, true);
            },
            print(chunk) {
              emitStringThroughLinearMemory(chunk, false, false);
            },
            eprintln(line) {
              emitStringThroughLinearMemory(line, true, true);
            },
            httpGet(url) {
              const cleanUrl = String(url || "").trim();
              if (!httpCache.has(cleanUrl)) {
                if (suspendOnUncachedHttp) {
                  throw new HttpSuspenseSignal(cleanUrl);
                }
                return { ok: false, status: 0, body: "Offline: HTTP disabled" };
              }
              const entry = httpCache.get(cleanUrl);
              httpRequests.push({
                url: cleanUrl,
                status: entry.status,
                ok: entry.ok,
                bytes: UTF8_ENCODER.encode(entry.body || "").length,
              });
              lastHttpStatus = entry.status;
              return entry;
            },
            nowMs: nowMillis,
          });
          return BigInt(typeof rc === "number" ? rc : 0);
        },
      },
    };

    return {
      imports,
      httpCache,
      bindMemory(mem) {
        wasmMemory = mem;
      },
      readUtf8,
      readCString,
      writeUtf8,
      flush,
      getOutput() {
        return stdoutLines.slice();
      },
      getStderr() {
        return stderrLines.slice();
      },
      getHttpRequests() {
        return httpRequests.slice();
      },
      getLastHttpStatus() {
        return lastHttpStatus;
      },
    };
  }

  /**
   * Fetch a URL on behalf of `env.http_get` with timeout and offline safety.
   */
  async function fetchForHost(url, fetchImpl, timeoutMs) {
    if (typeof fetchImpl !== "function") {
      return {
        ok: false,
        status: 0,
        body: "[http_get offline: fetch API unavailable]",
      };
    }

    const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    const timer = controller
      ? setTimeout(function () {
          controller.abort();
        }, timeoutMs || DEFAULT_HTTP_TIMEOUT_MS)
      : null;

    try {
      const resp = await fetchImpl(url, {
        method: "GET",
        signal: controller ? controller.signal : undefined,
      });
      const text = await resp.text();
      return {
        ok: Boolean(resp.ok),
        status: Number(resp.status) || (resp.ok ? 200 : 500),
        body: text,
      };
    } catch (err) {
      const reason = err && err.name === "AbortError"
        ? "request timed out"
        : (err && err.message ? err.message : String(err));
      return {
        ok: false,
        status: 0,
        body: "[http_get error: " + reason + "]",
      };
    } finally {
      if (timer) clearTimeout(timer);
    }
  }

  /**
   * Validate, instantiate, and run a compiled Lateralus `.wasm` binary in-browser
   * (or in Node.js V8), resolving any `http_get` host calls asynchronously.
   *
   * @param {Uint8Array|ArrayBuffer} wasmBytes
   * @param {Object} [options]
   */
  async function runLateralusWasm(wasmBytes, options) {
    const opts = options || {};
    const bytes = wasmBytes instanceof Uint8Array ? wasmBytes : new Uint8Array(wasmBytes);

    if (!WebAssembly.validate(bytes)) {
      throw new Error("Generated module failed WebAssembly.validate()");
    }

    const httpCache = opts.httpCache instanceof Map ? opts.httpCache : new Map();
    if (opts.httpFixtures && typeof opts.httpFixtures === "object") {
      for (const [k, v] of Object.entries(opts.httpFixtures)) {
        if (typeof v === "string") {
          httpCache.set(k, { ok: true, status: 200, body: v });
        } else if (v && typeof v === "object") {
          httpCache.set(k, {
            ok: v.ok !== false,
            status: v.status ?? 200,
            body: String(v.body ?? ""),
          });
        }
      }
    }

    const fetchImpl = opts.fetchImpl !== undefined
      ? opts.fetchImpl
      : (typeof globalThis.fetch === "function" ? globalThis.fetch.bind(globalThis) : null);
    const maxReplays = opts.maxHttpReplays || DEFAULT_MAX_HTTP_REPLAYS;

    const t0 = nowMillis();
    let replays = 0;

    while (true) {
      const shim = createLateralusHostShim({
        httpCache,
        maxLines: opts.maxLines,
        maxBytes: opts.maxBytes,
        returnNegativeOnHttpError: opts.returnNegativeOnHttpError,
        astExecutor: opts.astExecutor,
      });

      const instantiated = await WebAssembly.instantiate(bytes, shim.imports);
      const instance = instantiated.instance || instantiated;
      if (instance.exports && instance.exports.memory) {
        shim.bindMemory(instance.exports.memory);
      }

      try {
        let rawExit = 0;
        if (instance.exports._start) {
          rawExit = instance.exports._start();
        } else if (instance.exports.main) {
          rawExit = instance.exports.main();
        }
        shim.flush();

        const output = shim.getOutput();
        if (typeof opts.onLine === "function") {
          for (let i = 0; i < output.length; i++) {
            opts.onLine(output[i], "stdout");
          }
        }

        const elapsedMs = Number((nowMillis() - t0).toFixed(2));
        return {
          ok: true,
          output,
          stderr: shim.getStderr(),
          exitCode: typeof rawExit === "bigint" ? Number(rawExit) : (rawExit || 0),
          elapsedMs,
          httpRequests: shim.getHttpRequests(),
          memoryBytes: instance.exports.memory ? instance.exports.memory.buffer.byteLength : 0,
          wasmByteLength: bytes.byteLength,
          exports: instance.exports,
        };
      } catch (err) {
        if (err instanceof HttpSuspenseSignal) {
          replays++;
          if (replays > maxReplays) {
            throw new RuntimeLimitError(
              "Exceeded maximum HTTP host roundtrips (" + maxReplays + ")"
            );
          }
          const fetched = await fetchForHost(err.url, fetchImpl, opts.httpTimeoutMs);
          httpCache.set(err.url, fetched);
          continue;
        }
        throw err;
      }
    }
  }

  return {
    HttpSuspenseSignal,
    RuntimeLimitError,
    createLateralusHostShim,
    runLateralusWasm,
  };
});
