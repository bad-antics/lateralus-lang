// ============================================================================
// docs/website/playground/wasm-compiler.js
// Client-side Lateralus -> WebAssembly 1.0 (.wasm + .wat) Compiler & Evaluator
//
// Compiles Lateralus source code directly in the browser (or Node.js) into a
// spec-compliant WebAssembly 1.0 binary (`Uint8Array`) and WAT disassembly,
// with zero server round-trips.
//
// Two compilation tiers:
//   - Tier 1 (`native-wasm`): Pure stack/linear-memory WebAssembly codegen for
//     functions, recursion, scalars (i64/f64/bool), UTF-8 strings, string
//     interpolation, loops, conditionals, match, pipelines (`|>`), println,
//     and `http_get` host calls.
//   - Tier 2 (`wasm-host-bridged`): Embeds the parsed AST into the WASM module
//     data section and drives dynamic evaluation through `env.rt_exec_ast` and
//     WASM linear-memory host I/O (`println`, `http_get`) for higher-order
//     closures, structs/enums/ADTs, algebraic effects, channels, and macros.
// ============================================================================

(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.LateralusWasmCompiler = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const UTF8_ENC = new TextEncoder();

  class CompileError extends Error {
    constructor(message, line, col) {
      super(line ? "Line " + line + (col ? ":" + col : "") + " - " + message : message);
      this.name = "CompileError";
      this.line = line || 0;
      this.col = col || 0;
    }
  }

  // --------------------------------------------------------------------------
  // 1. WebAssembly 1.0 Binary & WAT Module Builder
  // --------------------------------------------------------------------------

  const VALTYPE = { i32: 0x7f, i64: 0x7e, f32: 0x7d, f64: 0x7c };
  const VOID_BLOCK = 0x40;

  const MEM_OPS = {
    "i32.load": [0x28, 2],
    "i64.load": [0x29, 3],
    "f64.load": [0x2b, 3],
    "i32.load8_s": [0x2c, 0],
    "i32.load8_u": [0x2d, 0],
    "i32.store": [0x36, 2],
    "i64.store": [0x37, 3],
    "f64.store": [0x39, 3],
    "i32.store8": [0x3a, 0],
  };

  const SIMPLE_OPS = {
    unreachable: [0x00],
    nop: [0x01],
    return: [0x0f],
    drop: [0x1a],
    select: [0x1b],
    "memory.size": [0x3f, 0x00],
    "memory.grow": [0x40, 0x00],
    "i32.eqz": [0x45],
    "i32.eq": [0x46],
    "i32.ne": [0x47],
    "i32.lt_s": [0x48],
    "i32.lt_u": [0x49],
    "i32.gt_s": [0x4a],
    "i32.gt_u": [0x4b],
    "i32.le_s": [0x4c],
    "i32.le_u": [0x4d],
    "i32.ge_s": [0x4e],
    "i32.ge_u": [0x4f],
    "i32.add": [0x6a],
    "i32.sub": [0x6b],
    "i32.mul": [0x6c],
    "i32.div_s": [0x6d],
    "i32.rem_s": [0x6f],
    "i32.and": [0x71],
    "i32.or": [0x72],
    "i32.xor": [0x73],
    "i64.eqz": [0x50],
    "i64.eq": [0x51],
    "i64.ne": [0x52],
    "i64.lt_s": [0x53],
    "i64.gt_s": [0x55],
    "i64.le_s": [0x57],
    "i64.ge_s": [0x59],
    "i64.add": [0x7c],
    "i64.sub": [0x7d],
    "i64.mul": [0x7e],
    "i64.div_s": [0x7f],
    "i64.rem_s": [0x81],
    "i64.and": [0x83],
    "i64.or": [0x84],
    "i64.xor": [0x85],
    "i64.shl": [0x86],
    "i64.shr_s": [0x87],
    "f64.eq": [0x61],
    "f64.ne": [0x62],
    "f64.lt": [0x63],
    "f64.gt": [0x64],
    "f64.le": [0x65],
    "f64.ge": [0x66],
    "f64.abs": [0x99],
    "f64.neg": [0x9a],
    "f64.ceil": [0x9b],
    "f64.floor": [0x9c],
    "f64.nearest": [0x9e],
    "f64.sqrt": [0x9f],
    "f64.add": [0xa0],
    "f64.sub": [0xa1],
    "f64.mul": [0xa2],
    "f64.div": [0xa3],
    "f64.min": [0xa4],
    "f64.max": [0xa5],
    "i32.wrap_i64": [0xa7],
    "i64.extend_i32_s": [0xac],
    "i64.extend_i32_u": [0xad],
    "i64.trunc_f64_s": [0xb0],
    "f64.convert_i32_s": [0xb7],
    "f64.convert_i64_s": [0xb9],
  };

  function uleb128(val) {
    let v = Number(val) >>> 0;
    const out = [];
    do {
      let b = v & 0x7f;
      v >>>= 7;
      if (v !== 0) b |= 0x80;
      out.push(b);
    } while (v !== 0);
    return out;
  }

  function sleb128(val, bits) {
    const width = BigInt(bits || 64);
    const mask = (1n << width) - 1n;
    const signBit = 1n << (width - 1n);
    let v = BigInt(val) & mask;
    if ((v & signBit) !== 0n) {
      v -= 1n << width;
    }
    const out = [];
    while (true) {
      let b = Number(v & 0x7fn);
      v >>= 7n;
      const done = (v === 0n && (b & 0x40) === 0) || (v === -1n && (b & 0x40) !== 0);
      if (!done) b |= 0x80;
      out.push(b);
      if (done) break;
    }
    return out;
  }

  function f64Bytes(num) {
    const buf = new ArrayBuffer(8);
    new DataView(buf).setFloat64(0, Number(num), true);
    return Array.from(new Uint8Array(buf));
  }

  function encodeName(str) {
    const raw = Array.from(UTF8_ENC.encode(str));
    return uleb128(raw.length).concat(raw);
  }

  function encodeVec(items) {
    const out = uleb128(items.length);
    for (let i = 0; i < items.length; i++) {
      for (let j = 0; j < items[i].length; j++) out.push(items[i][j]);
    }
    return out;
  }

  function encodeSection(id, payload) {
    return [id].concat(uleb128(payload.length), payload);
  }

  class WasmModuleBuilder {
    constructor(name) {
      this.name = name || "lateralus_playground";
      this.imports = [];
      this.functions = [];
      this.globals = [];
      this.memory = { minPages: 2, exported: true };
      this.dataSegments = [];
      this.dataOffset = 64; // [0..64) reserved scratch
      this.stringPool = new Map();
    }

    importFunction(mod, field, localName, params, resultType) {
      for (const ex of this.imports) {
        if (ex.name === localName) return ex;
      }
      const fn = {
        imported: true,
        importModule: mod,
        importName: field,
        name: localName,
        params,
        resultType: resultType || "",
      };
      this.imports.push(fn);
      return fn;
    }

    addGlobal(name, wasmType, mutable, initValue) {
      const g = { name, wasmType, mutable, initValue: String(initValue) };
      this.globals.push(g);
      return g;
    }

    addFunction(name, params, resultType, exported) {
      const fn = {
        imported: false,
        name,
        params: params || [],
        resultType: resultType || "",
        exported: Boolean(exported),
        locals: [],
        body: [],
        addLocal(lname, wtype) {
          if (this.params.some((p) => p[0] === lname)) return;
          if (!this.locals.some((l) => l.name === lname)) {
            this.locals.push({ name: lname, wasmType: wtype });
          }
        },
        emit(...instrs) {
          for (const ins of instrs) this.body.push(ins);
        },
      };
      this.functions.push(fn);
      return fn;
    }

    addDataBytes(rawBytes) {
      const ptr = this.dataOffset;
      const copy = rawBytes instanceof Uint8Array ? rawBytes : new Uint8Array(rawBytes);
      this.dataSegments.push({ offset: ptr, data: copy });
      this.dataOffset = (this.dataOffset + copy.length + 7) & ~7;
      return { ptr, len: copy.length };
    }

    addStringConstant(str) {
      const s = String(str);
      if (this.stringPool.has(s)) return this.stringPool.get(s);
      const utf8 = UTF8_ENC.encode(s);
      const nulTerm = new Uint8Array(utf8.length + 1);
      nulTerm.set(utf8, 0);
      nulTerm[utf8.length] = 0;
      const { ptr } = this.addDataBytes(nulTerm);
      this.stringPool.set(s, ptr);
      return ptr;
    }

    toWat() {
      const lines = ["(module ;; " + this.name];
      for (const imp of this.imports) {
        const ps = imp.params.map(([n, t]) => "(param $" + n + " " + t + ")").join(" ");
        const rs = imp.resultType ? "(result " + imp.resultType + ")" : "";
        const sig = [ps, rs].filter(Boolean).join(" ");
        lines.push(
          '  (import "' +
            imp.importModule +
            '" "' +
            imp.importName +
            '" (func $' +
            imp.name +
            (sig ? " " + sig : "") +
            "))"
        );
      }
      if (this.memory) {
        lines.push(
          "  (memory " + (this.memory.exported ? '(export "memory") ' : "") + this.memory.minPages + ")"
        );
      }
      for (const g of this.globals) {
        const mt = g.mutable ? "(mut " + g.wasmType + ")" : g.wasmType;
        lines.push("  (global $" + g.name + " " + mt + " (" + g.wasmType + ".const " + g.initValue + "))");
      }
      for (const seg of this.dataSegments) {
        let preview = "";
        const cap = Math.min(seg.data.length, 96);
        for (let i = 0; i < cap; i++) {
          const b = seg.data[i];
          if (b >= 32 && b < 127 && b !== 34 && b !== 92) {
            preview += String.fromCharCode(b);
          } else {
            preview += "\\" + b.toString(16).padStart(2, "0");
          }
        }
        if (seg.data.length > cap) {
          preview += "... (" + seg.data.length + " bytes)";
        }
        lines.push('  (data (i32.const ' + seg.offset + ') "' + preview + '")');
      }
      for (const fn of this.functions) {
        const exp = fn.exported ? '(export "' + fn.name + '") ' : "";
        const ps = fn.params.map(([n, t]) => "(param $" + n + " " + t + ")").join(" ");
        const rs = fn.resultType ? "(result " + fn.resultType + ")" : "";
        const sig = [ps, rs].filter(Boolean).join(" ");
        lines.push(("  (func $" + fn.name + " " + exp + sig).trimEnd());
        for (const loc of fn.locals) {
          lines.push("    (local $" + loc.name + " " + loc.wasmType + ")");
        }
        for (const ins of fn.body) {
          lines.push("    " + ins);
        }
        lines.push("  )");
      }
      lines.push(")");
      return lines.join("\n");
    }

    toBytes() {
      const sigMap = new Map();
      const types = [];

      function internSig(fn) {
        const key = fn.params.map((p) => p[1]).join(",") + "->" + (fn.resultType || "");
        if (sigMap.has(key)) return sigMap.get(key);
        const pBytes = fn.params.map((p) => [VALTYPE[p[1]]]);
        const rBytes = fn.resultType ? [[VALTYPE[fn.resultType]]] : [];
        const entry = [0x60].concat(encodeVec(pBytes), encodeVec(rBytes));
        const idx = types.length;
        types.push(entry);
        sigMap.set(key, idx);
        return idx;
      }

      const funcIdx = new Map();
      const importEntries = [];
      for (const imp of this.imports) {
        const tid = internSig(imp);
        funcIdx.set(imp.name, funcIdx.size);
        importEntries.push(
          encodeName(imp.importModule).concat(encodeName(imp.importName), [0x00], uleb128(tid))
        );
      }

      const defTypes = [];
      for (const fn of this.functions) {
        const tid = internSig(fn);
        funcIdx.set(fn.name, funcIdx.size);
        defTypes.push(uleb128(tid));
      }

      const globalIdx = new Map();
      const globalEntries = [];
      for (const g of this.globals) {
        globalIdx.set(g.name, globalIdx.size);
        const init =
          g.wasmType === "i32"
            ? [0x41].concat(sleb128(BigInt(g.initValue), 32), [0x0b])
            : g.wasmType === "i64"
            ? [0x42].concat(sleb128(BigInt(g.initValue), 64), [0x0b])
            : [0x44].concat(f64Bytes(Number(g.initValue)), [0x0b]);
        globalEntries.push([VALTYPE[g.wasmType], g.mutable ? 1 : 0].concat(init));
      }

      const exportEntries = [];
      if (this.memory && this.memory.exported) {
        exportEntries.push(encodeName("memory").concat([0x02], uleb128(0)));
      }
      for (const fn of this.functions) {
        if (fn.exported) {
          exportEntries.push(encodeName(fn.name).concat([0x00], uleb128(funcIdx.get(fn.name))));
        }
      }

      const codeEntries = this.functions.map((fn) =>
        this._encodeFnBody(fn, funcIdx, globalIdx)
      );

      const dataEntries = this.dataSegments.map((seg) => {
        const init = [0x41].concat(sleb128(seg.offset, 32), [0x0b]);
        return [0x00].concat(init, uleb128(seg.data.length), Array.from(seg.data));
      });

      let out = [0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00];
      if (types.length) out = out.concat(encodeSection(1, encodeVec(types)));
      if (importEntries.length) out = out.concat(encodeSection(2, encodeVec(importEntries)));
      if (defTypes.length) out = out.concat(encodeSection(3, encodeVec(defTypes)));
      if (this.memory) {
        out = out.concat(encodeSection(5, encodeVec([[0x00].concat(uleb128(this.memory.minPages))])));
      }
      if (globalEntries.length) out = out.concat(encodeSection(6, encodeVec(globalEntries)));
      if (exportEntries.length) out = out.concat(encodeSection(7, encodeVec(exportEntries)));
      if (codeEntries.length) out = out.concat(encodeSection(10, encodeVec(codeEntries)));
      if (dataEntries.length) out = out.concat(encodeSection(11, encodeVec(dataEntries)));
      return new Uint8Array(out);
    }

    _encodeFnBody(fn, funcIdx, globalIdx) {
      const localIdx = new Map();
      for (const [pname] of fn.params) localIdx.set(pname, localIdx.size);
      for (const loc of fn.locals) localIdx.set(loc.name, localIdx.size);

      const localGroups = [];
      if (fn.locals.length > 0) {
        let curType = fn.locals[0].wasmType;
        let count = 1;
        for (let i = 1; i < fn.locals.length; i++) {
          if (fn.locals[i].wasmType === curType) count++;
          else {
            localGroups.push(uleb128(count).concat([VALTYPE[curType]]));
            curType = fn.locals[i].wasmType;
            count = 1;
          }
        }
        localGroups.push(uleb128(count).concat([VALTYPE[curType]]));
      }

      const code = [];
      const labels = [];

      for (const rawLine of fn.body) {
        const line = rawLine.split(";;")[0].trim();
        if (!line) continue;
        if (line === "end") {
          labels.pop();
          code.push(0x0b);
          continue;
        }
        if (line === "else") {
          code.push(0x05);
          continue;
        }
        const parts = line.split(/\s+/);
        const op = parts[0];

        if (op === "block" || op === "loop" || op === "if") {
          let bt = VOID_BLOCK;
          let lbl = null;
          const resM = line.match(/\(\s*result\s+(i32|i64|f64)\s*\)/);
          if (resM) bt = VALTYPE[resM[1]];
          for (let i = 1; i < parts.length; i++) {
            if (parts[i].startsWith("$")) {
              lbl = parts[i].slice(1);
              break;
            }
          }
          labels.push(lbl);
          code.push(op === "block" ? 0x02 : op === "loop" ? 0x03 : 0x04, bt);
          continue;
        }

        if (op === "br" || op === "br_if") {
          const target = parts[1].startsWith("$") ? parts[1].slice(1) : parts[1];
          let depth = 0;
          if (/^\d+$/.test(target)) {
            depth = Number(target);
          } else {
            let found = -1;
            for (let i = labels.length - 1; i >= 0; i--) {
              if (labels[i] === target) {
                found = i;
                break;
              }
            }
            if (found < 0) throw new Error("Unknown WASM branch label $" + target);
            depth = labels.length - 1 - found;
          }
          code.push(op === "br" ? 0x0c : 0x0d, ...uleb128(depth));
          continue;
        }

        if (op === "i32.const") {
          code.push(0x41, ...sleb128(BigInt(parts[1]), 32));
          continue;
        }
        if (op === "i64.const") {
          code.push(0x42, ...sleb128(BigInt(parts[1]), 64));
          continue;
        }
        if (op === "f64.const") {
          code.push(0x44, ...f64Bytes(Number(parts[1])));
          continue;
        }
        if (op === "local.get" || op === "local.set" || op === "local.tee") {
          const name = parts[1].replace(/^\$/, "");
          const idx = localIdx.get(name);
          if (idx === undefined) throw new Error("Unknown local $" + name + " in " + fn.name);
          code.push(op === "local.get" ? 0x20 : op === "local.set" ? 0x21 : 0x22, ...uleb128(idx));
          continue;
        }
        if (op === "global.get" || op === "global.set") {
          const name = parts[1].replace(/^\$/, "");
          const idx = globalIdx.get(name);
          code.push(op === "global.get" ? 0x23 : 0x24, ...uleb128(idx));
          continue;
        }
        if (op === "call") {
          const name = parts[1].replace(/^\$/, "");
          const idx = funcIdx.get(name);
          if (idx === undefined) throw new Error("Unknown WASM function $" + name);
          code.push(0x10, ...uleb128(idx));
          continue;
        }
        if (MEM_OPS[op]) {
          const [mop, align] = MEM_OPS[op];
          code.push(mop, ...uleb128(align), ...uleb128(0));
          continue;
        }
        if (SIMPLE_OPS[op]) {
          code.push(...SIMPLE_OPS[op]);
          continue;
        }
        throw new Error("Unsupported WASM opcode: " + line);
      }

      code.push(0x0b);
      const body = encodeVec(localGroups).concat(code);
      return uleb128(body.length).concat(body);
    }
  }

  // --------------------------------------------------------------------------
  // 2. Macro Preprocessor & Lateralus Lexer
  // --------------------------------------------------------------------------

  function expandDeclarativeMacros(source) {
    let src = source;

    // Expand `define_builder!(BuilderName, f1: T1, f2: T2, ...)` into real struct + impl
    src = src.replace(
      /define_builder!\s*\(\s*(\w+)\s*,\s*([^)]+)\)/g,
      function (_, builderName, fieldsSpec) {
        const pairs = fieldsSpec
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
          .map((entry) => {
            const [fname, ftype] = entry.split(":").map((x) => x.trim());
            return { fname, ftype: ftype || "Any" };
          });
        const structFields = pairs.map((p) => "    " + p.fname + ": " + p.ftype + ",").join("\n");
        const initFields = pairs.map((p) => p.fname + ": None").join(", ");
        const setters = pairs
          .map(
            (p) =>
              "    fn " +
              p.fname +
              "(self, val: " +
              p.ftype +
              ") -> " +
              builderName +
              " {\n        " +
              builderName +
              " { " +
              p.fname +
              ": val, ..self }\n    }"
          )
          .join("\n");
        const checks = pairs
          .map(
            (p) =>
              "        if self." +
              p.fname +
              ' == None { return Err("Missing field: ' +
              p.fname +
              '") }'
          )
          .join("\n");
        return (
          "struct " +
          builderName +
          " {\n" +
          structFields +
          "\n}\nimpl " +
          builderName +
          " {\n    fn new() -> " +
          builderName +
          " { " +
          builderName +
          " { " +
          initFields +
          " } }\n" +
          setters +
          "\n    fn build(self) -> Result<" +
          builderName +
          ", String> {\n" +
          checks +
          "\n        Ok(self)\n    }\n}"
        );
      }
    );

    // Strip `macro name(...) { ... }` definitions after registering built-in expansions
    src = stripMacroDeclarations(src);

    // Expand `|> pipe_debug!(stage)` and standalone `pipe_debug!(expr)`
    src = expandPipeDebugCalls(src);

    return src;
  }

  function stripMacroDeclarations(src) {
    let out = "";
    let i = 0;
    while (i < src.length) {
      if (
        src.slice(i, i + 6) === "macro " &&
        (i === 0 || /\s/.test(src[i - 1]))
      ) {
        let j = i + 6;
        while (j < src.length && src[j] !== "{") j++;
        let depth = 0;
        while (j < src.length) {
          if (src[j] === "{") depth++;
          else if (src[j] === "}") {
            depth--;
            if (depth === 0) {
              j++;
              break;
            }
          }
          j++;
        }
        // Preserve line count so error line numbers remain accurate
        const skipped = src.slice(i, j);
        out += skipped.replace(/[^\n]/g, " ");
        i = j;
        continue;
      }
      out += src[i++];
    }
    return out;
  }

  function expandPipeDebugCalls(src) {
    let out = "";
    let i = 0;
    while (i < src.length) {
      const idx = src.indexOf("pipe_debug!(", i);
      if (idx < 0) {
        out += src.slice(i);
        break;
      }
      out += src.slice(i, idx);
      let j = idx + "pipe_debug!(".length;
      let depth = 1;
      while (j < src.length && depth > 0) {
        if (src[j] === "(") depth++;
        else if (src[j] === ")") depth--;
        j++;
      }
      const inner = src.slice(idx + "pipe_debug!(".length, j - 1).trim();
      const labelEsc = inner.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
      out += '__pipe_debug("' + labelEsc + '", |__pd_in| __pd_in |> ' + inner + ")";
      i = j;
    }
    return out;
  }

  const KEYWORDS = new Set([
    "fn", "let", "mut", "if", "else", "elif", "match", "for", "in", "while",
    "return", "import", "struct", "enum", "impl", "async", "await",
    "spawn", "try", "recover", "ensure", "true", "false", "and", "or", "not",
    "pub", "module", "mod", "use", "type", "const", "break", "continue",
    "loop", "self", "super", "as", "comptime", "effect", "perform", "handle",
    "with", "select",
  ]);

  function tokenize(rawSource) {
    const src = expandDeclarativeMacros(rawSource);
    const tokens = [];
    let i = 0;
    let line = 1;
    let lineStart = 0;
    const len = src.length;

    function push(type, value) {
      tokens.push({ type, value, line, col: i - lineStart + 1 });
    }

    while (i < len) {
      const ch = src[i];
      if (ch === " " || ch === "\t" || ch === "\r") {
        i++;
        continue;
      }
      if (ch === "\n") {
        tokens.push({ type: "NEWLINE", line, col: i - lineStart + 1 });
        i++;
        line++;
        lineStart = i;
        continue;
      }
      if (ch === "/" && src[i + 1] === "/") {
        while (i < len && src[i] !== "\n") i++;
        continue;
      }
      if (ch === "/" && src[i + 1] === "*") {
        i += 2;
        while (i < len - 1 && !(src[i] === "*" && src[i + 1] === "/")) {
          if (src[i] === "\n") {
            line++;
            lineStart = i + 1;
          }
          i++;
        }
        i += 2;
        continue;
      }
      if (ch === '"' || ch === "'") {
        const quote = ch;
        const startLine = line;
        i++;
        let s = "";
        let braceDepth = 0;
        while (i < len && (src[i] !== quote || braceDepth > 0)) {
          if (src[i] === "\n") {
            line++;
            lineStart = i + 1;
          }
          if (src[i] === "\\" && i + 1 < len) {
            const nxt = src[i + 1];
            if (nxt === "n") s += "\n";
            else if (nxt === "t") s += "\t";
            else if (nxt === "r") s += "\r";
            else if (nxt === "\\") s += "\\";
            else if (nxt === '"') s += '"';
            else if (nxt === "'") s += "'";
            else if (nxt === "$") s += "$";
            else s += nxt;
            i += 2;
          } else {
            if (quote === '"' && src[i] === "{") braceDepth++;
            else if (quote === '"' && src[i] === "}" && braceDepth > 0) braceDepth--;
            s += src[i++];
          }
        }
        if (i >= len) {
          throw new CompileError("Unterminated string literal", startLine, 1);
        }
        i++;
        tokens.push({ type: "STRING", value: s, quote, line: startLine, col: 1 });
        continue;
      }
      if (ch >= "0" && ch <= "9") {
        let num = "";
        let isFloat = false;
        while (i < len && ((src[i] >= "0" && src[i] <= "9") || src[i] === "_")) {
          if (src[i] !== "_") num += src[i];
          i++;
        }
        if (src[i] === "." && src[i + 1] >= "0" && src[i + 1] <= "9") {
          isFloat = true;
          num += ".";
          i++;
          while (i < len && ((src[i] >= "0" && src[i] <= "9") || src[i] === "_")) {
            if (src[i] !== "_") num += src[i];
            i++;
          }
        }
        tokens.push({
          type: isFloat ? "FLOAT" : "INT",
          value: isFloat ? parseFloat(num) : parseInt(num, 10),
          raw: num,
          line,
          col: i - lineStart,
        });
        continue;
      }
      if ((ch >= "a" && ch <= "z") || (ch >= "A" && ch <= "Z") || ch === "_") {
        let id = "";
        const startCol = i - lineStart + 1;
        while (
          i < len &&
          ((src[i] >= "a" && src[i] <= "z") ||
            (src[i] >= "A" && src[i] <= "Z") ||
            (src[i] >= "0" && src[i] <= "9") ||
            src[i] === "_")
        ) {
          id += src[i++];
        }
        if (src[i] === "!" && id === "static_assert") {
          i++;
          tokens.push({ type: "IDENT", value: "static_assert", line, col: startCol });
          continue;
        }
        if (KEYWORDS.has(id)) tokens.push({ type: "KEYWORD", value: id, line, col: startCol });
        else tokens.push({ type: "IDENT", value: id, line, col: startCol });
        continue;
      }
      if (ch === "@") {
        i++;
        let decName = "";
        while (i < len && /[a-zA-Z0-9_]/.test(src[i])) decName += src[i++];
        push("DECORATOR", decName);
        continue;
      }

      const two = src.slice(i, i + 2);
      const three = src.slice(i, i + 3);
      if (three === "..=") { push("RANGE_INC"); i += 3; continue; }
      if (three === "..<") { push("RANGE_OP"); i += 3; continue; }
      if (two === "..") { push("RANGE_OP"); i += 2; continue; }
      if (two === "|>") { push("PIPE"); i += 2; continue; }
      if (two === "->") { push("ARROW"); i += 2; continue; }
      if (two === "=>") { push("FAT_ARROW"); i += 2; continue; }
      if (two === "::") { push("DOUBLE_COLON"); i += 2; continue; }
      if (["==", "!=", "<=", ">=", "&&", "||", "+=", "-=", "*=", "/=", "<<", ">>", "**"].includes(two)) {
        push("OP", two);
        i += 2;
        continue;
      }

      const singles = {
        "(": "LPAREN", ")": "RPAREN", "{": "LBRACE", "}": "RBRACE",
        "[": "LBRACKET", "]": "RBRACKET", ",": "COMMA", ":": "COLON",
        ";": "SEMI", ".": "DOT", "?": "QUESTION",
      };
      if (singles[ch]) {
        push(singles[ch], ch);
        i++;
        continue;
      }
      if ("+-*/%<>=!&|^~".includes(ch)) {
        push("OP", ch);
        i++;
        continue;
      }
      throw new CompileError("Unexpected character '" + ch + "'", line, i - lineStart + 1);
    }

    return tokens;
  }

  // --------------------------------------------------------------------------
  // 3. Recursive-Descent Lateralus Parser -> AST
  // --------------------------------------------------------------------------

  function parseLateralus(source) {
    const tokens = tokenize(source);
    let pos = 0;

    function skipNl() {
      while (pos < tokens.length && tokens[pos].type === "NEWLINE") {
        pos++;
      }
    }
    function skipStmtSep() {
      while (pos < tokens.length && (tokens[pos].type === "NEWLINE" || tokens[pos].type === "SEMI")) {
        pos++;
      }
    }
    function peek() {
      let p = pos;
      while (p < tokens.length && tokens[p].type === "NEWLINE") p++;
      return tokens[p];
    }
    function peekRaw() {
      return tokens[pos];
    }
    function advance() {
      skipNl();
      return tokens[pos++];
    }
    function expect(type, val) {
      const t = advance();
      if (!t || t.type !== type || (val !== undefined && t.value !== val)) {
        const got = t ? t.type + (t.value !== undefined ? "(" + t.value + ")" : "") : "EOF";
        throw new CompileError(
          "Expected " + type + (val ? " '" + val + "'" : "") + ", got " + got,
          t ? t.line : (tokens[tokens.length - 1]?.line || 1),
          t ? t.col : 1
        );
      }
      return t;
    }

    function consumeDecorators() {
      const decs = [];
      while (peek()?.type === "DECORATOR") {
        const d = advance();
        let args = [];
        let kwargs = {};
        if (peekRaw()?.type === "LPAREN") {
          advance();
          while (peek()?.type !== "RPAREN" && pos < tokens.length) {
            if (peek()?.type === "IDENT" && tokens[pos + 1]?.type === "COLON") {
              const k = advance().value;
              expect("COLON");
              kwargs[k] = parseExpr();
            } else {
              args.push(parseExpr());
            }
            if (peek()?.type === "COMMA") advance();
          }
          expect("RPAREN");
        }
        decs.push({ name: d.value, args, kwargs });
      }
      return decs;
    }

    function skipGenericParams() {
      if (peek()?.type === "OP" && peek()?.value === "<") {
        advance();
        let depth = 1;
        while (pos < tokens.length && depth > 0) {
          const tok = tokens[pos++];
          if (tok.type === "OP" && tok.value === "<") depth++;
          else if (tok.type === "OP" && tok.value === ">") depth--;
          else if (tok.type === "OP" && tok.value === ">>") depth -= 2;
        }
      }
    }

    function parseTypeAnnotation() {
      const t = peek();
      if (!t) return "Any";
      if (t.type === "LPAREN") {
        advance();
        const parts = [];
        while (peek()?.type !== "RPAREN" && pos < tokens.length) {
          parts.push(parseTypeAnnotation());
          if (peek()?.type === "COMMA") advance();
        }
        expect("RPAREN");
        return "(" + parts.join(",") + ")";
      }
      if (t.type === "LBRACKET") {
        advance();
        const inner = parseTypeAnnotation();
        if (peek()?.type === "SEMI") {
          advance();
          parseExpr();
        }
        expect("RBRACKET");
        return "List<" + inner + ">";
      }
      if (t.type === "KEYWORD" && t.value === "fn") {
        advance();
        if (peek()?.type === "LPAREN") {
          advance();
          while (peek()?.type !== "RPAREN" && pos < tokens.length) {
            parseTypeAnnotation();
            if (peek()?.type === "COMMA") advance();
          }
          expect("RPAREN");
        }
        if (peek()?.type === "ARROW") {
          advance();
          parseTypeAnnotation();
        }
        return "Fn";
      }
      if (t.type === "IDENT" || t.type === "KEYWORD") {
        let name = advance().value;
        while (peek()?.type === "DOUBLE_COLON" || peek()?.type === "DOT") {
          advance();
          if (peek()?.type === "IDENT") name += "::" + advance().value;
        }
        skipGenericParams();
        return name;
      }
      return "Any";
    }

    function parseProgram() {
      const body = [];
      skipStmtSep();
      while (peek()) {
        body.push(parseStatement());
        skipStmtSep();
      }
      return { type: "program", body };
    }

    function parseStatement() {
      skipStmtSep();
      const decs = consumeDecorators();
      const t = peek();
      if (!t) return { type: "noop" };

      if (t.type === "IDENT" && t.value === "from") {
        return parseImport();
      }

      if (t.type === "KEYWORD") {
        if (t.value === "pub") {
          advance();
          const inner = parseStatement();
          inner.isPub = true;
          if (decs.length) inner.decorators = decs;
          return inner;
        }
        if (t.value === "module" || t.value === "mod") {
          advance();
          let mname = expect("IDENT").value;
          while (peek()?.type === "DOT" || peek()?.type === "DOUBLE_COLON") {
            advance();
            mname += "." + expect("IDENT").value;
          }
          if (peek()?.type === "LBRACE") {
            const blk = parseBlock();
            return { type: "module_block", name: mname, body: blk.body };
          }
          return { type: "noop" };
        }
        if (t.value === "import" || t.value === "from" || t.value === "use") {
          return parseImport();
        }
        if (t.value === "let" || t.value === "const") {
          if (t.value === "const" && peekSecondKeyword("fn")) {
            advance(); // const
            const fnNode = parseFn(false, true);
            fnNode.decorators = decs;
            return fnNode;
          }
          return parseLet();
        }
        if (t.value === "fn" || t.value === "async") {
          const isAsync = t.value === "async";
          if (isAsync) advance();
          const fnNode = parseFn(isAsync, false);
          fnNode.decorators = decs;
          return fnNode;
        }
        if (t.value === "struct") {
          const sNode = parseStruct();
          sNode.decorators = decs;
          return sNode;
        }
        if (t.value === "enum") return parseEnum();
        if (t.value === "impl") return parseImpl();
        if (t.value === "effect") return parseEffectDecl();
        if (t.value === "type") {
          advance();
          expect("IDENT");
          skipGenericParams();
          if (peek()?.type === "OP" && peek()?.value === "=") {
            advance();
            parseTypeAnnotation();
          }
          return { type: "noop" };
        }
        if (t.value === "if") return parseIf();
        if (t.value === "for") return parseFor();
        if (t.value === "while") return parseWhile();
        if (t.value === "loop") {
          advance();
          return { type: "loop", body: parseBlock() };
        }
        if (t.value === "select") return parseSelect();
        if (t.value === "try") return parseTry();
        if (t.value === "match") return parseMatch();
        if (t.value === "return") {
          const rt = advance();
          const next = peekRaw();
          if (
            !next ||
            next.type === "NEWLINE" ||
            next.type === "SEMI" ||
            next.type === "RBRACE"
          ) {
            return { type: "return", value: null, line: rt.line };
          }
          return { type: "return", value: parseExpr(), line: rt.line };
        }
        if (t.value === "break") {
          advance();
          return { type: "break" };
        }
        if (t.value === "continue") {
          advance();
          return { type: "continue" };
        }
      }

      const expr = parseExpr();
      // Check assignment operators `=`, `+=`, `-=`, `*=`, `/=`
      if (
        peek()?.type === "OP" &&
        ["=", "+=", "-=", "*=", "/="].includes(peek()?.value)
      ) {
        const op = advance().value;
        const rhs = parseExpr();
        return { type: "assign", target: expr, op, value: rhs };
      }
      return { type: "expr_stmt", expr };
    }

    function peekSecondKeyword(kw) {
      let p = pos;
      while (p < tokens.length && (tokens[p].type === "NEWLINE" || tokens[p].type === "SEMI")) p++;
      p++;
      while (p < tokens.length && (tokens[p].type === "NEWLINE" || tokens[p].type === "SEMI")) p++;
      return tokens[p]?.type === "KEYWORD" && tokens[p]?.value === kw;
    }

    function parseImport() {
      const start = advance();
      if (start.value === "from") {
        while (peek() && !(peek().type === "KEYWORD" && peek().value === "import")) {
          advance();
        }
        if (peek()?.value === "import") advance();
      }
      while (
        peek() &&
        (peek().type === "IDENT" ||
          peek().type === "DOT" ||
          peek().type === "DOUBLE_COLON" ||
          peek().type === "COMMA")
      ) {
        advance();
      }
      if (peek()?.type === "LBRACE") {
        advance();
        while (peek() && peek().type !== "RBRACE") advance();
        if (peek()?.type === "RBRACE") advance();
      }
      return { type: "import" };
    }

    function parseLet() {
      const kw = advance();
      let mutable = kw.value === "let";
      if (peek()?.type === "KEYWORD" && peek()?.value === "mut") {
        advance();
        mutable = true;
      }
      if (peek()?.type === "LPAREN") {
        advance();
        const names = [];
        while (peek()?.type !== "RPAREN" && pos < tokens.length) {
          names.push(expect("IDENT").value);
          if (peek()?.type === "COMMA") advance();
        }
        expect("RPAREN");
        expect("OP", "=");
        const value = parseExpr();
        return { type: "let_tuple", names, value };
      }
      const name = expect("IDENT").value;
      let typeAnn = null;
      if (peek()?.type === "COLON") {
        advance();
        typeAnn = parseTypeAnnotation();
      }
      let value = { type: "literal", kind: "nil", value: null };
      if (peek()?.type === "OP" && peek()?.value === "=") {
        advance();
        value = parseExpr();
      }
      return {
        type: "let",
        name,
        typeAnn,
        value,
        mutable,
        isConst: kw.value === "const",
      };
    }

    function parseFn(isAsync, isConst) {
      expect("KEYWORD", "fn");
      const name = peek()?.type === "IDENT" ? advance().value : null;
      const genericNames = [];
      if (peek()?.type === "OP" && peek()?.value === "<") {
        advance();
        let depth = 1;
        while (pos < tokens.length && depth > 0) {
          const tk = tokens[pos++];
          if (tk.type === "IDENT" && depth === 1) genericNames.push(tk.value);
          if (tk.type === "OP" && tk.value === "<") depth++;
          else if (tk.type === "OP" && tk.value === ">") depth--;
          else if (tk.type === "OP" && tk.value === ">>") depth -= 2;
        }
      }
      expect("LPAREN");
      const params = [];
      while (peek()?.type !== "RPAREN" && pos < tokens.length) {
        const pt = advance();
        const pname = pt.value;
        let ptype = null;
        if (peek()?.type === "COLON") {
          advance();
          ptype = parseTypeAnnotation();
        }
        params.push({ name: pname, typeAnn: ptype });
        if (peek()?.type === "COMMA") advance();
      }
      expect("RPAREN");
      let retType = null;
      if (peek()?.type === "ARROW") {
        advance();
        retType = parseTypeAnnotation();
      }
      // Optional `with EffectA, State<Int>` clause
      if (peek()?.type === "KEYWORD" && peek()?.value === "with") {
        advance();
        while (peek() && peek().type !== "LBRACE") {
          parseTypeAnnotation();
          if (peek()?.type === "COMMA") advance();
          else break;
        }
      }
      const body = parseBlock();
      return {
        type: "fn",
        name,
        params,
        retType,
        genericNames,
        body,
        isAsync,
        isConst,
        decorators: [],
      };
    }

    function parseBlock() {
      expect("LBRACE");
      const body = [];
      skipStmtSep();
      while (peek() && peek().type !== "RBRACE") {
        body.push(parseStatement());
        skipStmtSep();
      }
      expect("RBRACE");
      return { type: "block", body };
    }

    function parseStruct() {
      expect("KEYWORD", "struct");
      const name = expect("IDENT").value;
      skipGenericParams();
      expect("LBRACE");
      const fields = [];
      while (peek() && peek().type !== "RBRACE") {
        const fdecs = consumeDecorators();
        if (peek()?.type === "RBRACE") break;
        if (peek()?.type === "KEYWORD" && peek()?.value === "pub") advance();
        const fname = expect("IDENT").value;
        expect("COLON");
        const ftype = parseTypeAnnotation();
        fields.push({ name: fname, typeAnn: ftype, decorators: fdecs });
        if (peek()?.type === "COMMA") advance();
      }
      expect("RBRACE");
      return { type: "struct", name, fields, decorators: [] };
    }

    function parseEnum() {
      expect("KEYWORD", "enum");
      const name = expect("IDENT").value;
      skipGenericParams();
      expect("LBRACE");
      const variants = [];
      while (peek() && peek().type !== "RBRACE") {
        const vname = expect("IDENT").value;
        let arity = 0;
        if (peek()?.type === "LPAREN") {
          advance();
          while (peek() && peek().type !== "RPAREN") {
            parseTypeAnnotation();
            arity++;
            if (peek()?.type === "COMMA") advance();
          }
          expect("RPAREN");
        }
        variants.push({ name: vname, arity });
        if (peek()?.type === "COMMA") advance();
      }
      expect("RBRACE");
      return { type: "enum", name, variants };
    }

    function parseImpl() {
      expect("KEYWORD", "impl");
      skipGenericParams();
      let typeName = expect("IDENT").value;
      skipGenericParams();
      if (peek()?.type === "KEYWORD" && peek()?.value === "for") {
        advance();
        typeName = expect("IDENT").value;
        skipGenericParams();
      }
      expect("LBRACE");
      const methods = [];
      while (peek() && peek().type !== "RBRACE") {
        const mdecs = consumeDecorators();
        if (peek()?.type === "KEYWORD" && peek()?.value === "pub") advance();
        const isAsync = peek()?.type === "KEYWORD" && peek()?.value === "async";
        if (isAsync) advance();
        const fn = parseFn(isAsync, false);
        fn.decorators = mdecs;
        methods.push(fn);
      }
      expect("RBRACE");
      return { type: "impl", typeName, methods };
    }

    function parseEffectDecl() {
      expect("KEYWORD", "effect");
      const name = expect("IDENT").value;
      skipGenericParams();
      expect("LBRACE");
      while (peek() && peek().type !== "RBRACE") {
        advance();
      }
      expect("RBRACE");
      return { type: "effect_decl", name };
    }

    function parseIf() {
      expect("KEYWORD", "if");
      const cond = parseExpr();
      const thenBranch = parseBlock();
      let elseBranch = null;
      if (peek()?.type === "KEYWORD" && (peek()?.value === "else" || peek()?.value === "elif")) {
        const kw = advance().value;
        if (kw === "elif" || (peek()?.type === "KEYWORD" && peek()?.value === "if")) {
          elseBranch = kw === "elif" ? parseElifRest() : parseIf();
        } else {
          elseBranch = parseBlock();
        }
      }
      return { type: "if", cond, thenBranch, elseBranch };
    }

    function parseElifRest() {
      const cond = parseExpr();
      const thenBranch = parseBlock();
      let elseBranch = null;
      if (peek()?.type === "KEYWORD" && (peek()?.value === "else" || peek()?.value === "elif")) {
        const kw = advance().value;
        if (kw === "elif" || (peek()?.type === "KEYWORD" && peek()?.value === "if")) {
          elseBranch = kw === "elif" ? parseElifRest() : parseIf();
        } else {
          elseBranch = parseBlock();
        }
      }
      return { type: "if", cond, thenBranch, elseBranch };
    }

    function parseFor() {
      expect("KEYWORD", "for");
      let varName = null;
      let tupleVars = null;
      if (peek()?.type === "LPAREN") {
        advance();
        tupleVars = [];
        while (peek() && peek().type !== "RPAREN") {
          tupleVars.push(advance().value);
          if (peek()?.type === "COMMA") advance();
        }
        expect("RPAREN");
      } else {
        varName = expect("IDENT").value;
      }
      expect("KEYWORD", "in");
      const iter = parseExpr();
      const body = parseBlock();
      return { type: "for", varName, tupleVars, iter, body };
    }

    function parseWhile() {
      expect("KEYWORD", "while");
      const cond = parseExpr();
      const body = parseBlock();
      return { type: "while", cond, body };
    }

    function parseSelect() {
      expect("KEYWORD", "select");
      expect("LBRACE");
      const arms = [];
      while (peek() && peek().type !== "RBRACE") {
        const first = advance().value;
        if (first === "closed") {
          expect("FAT_ARROW");
          const body = peek()?.type === "LBRACE" ? parseBlock() : parseExpr();
          if (peek()?.type === "COMMA") advance();
          arms.push({ kind: "closed", body });
        } else {
          expect("IDENT", "from");
          const rx = parseExpr();
          expect("FAT_ARROW");
          const body = peek()?.type === "LBRACE" ? parseBlock() : parseExpr();
          if (peek()?.type === "COMMA") advance();
          arms.push({ kind: "recv", binding: first, rx, body });
        }
      }
      expect("RBRACE");
      return { type: "select", arms };
    }

    function parseTry() {
      expect("KEYWORD", "try");
      const body = parseBlock();
      let recoverVar = null;
      let recoverBody = null;
      let ensureBody = null;
      if (peek()?.type === "KEYWORD" && peek()?.value === "recover") {
        advance();
        if (peek()?.type === "IDENT") recoverVar = advance().value;
        recoverBody = parseBlock();
      }
      if (peek()?.type === "KEYWORD" && peek()?.value === "ensure") {
        advance();
        ensureBody = parseBlock();
      }
      return { type: "try", body, recoverVar, recoverBody, ensureBody };
    }

    function parseMatch(subjectOverride) {
      if (!subjectOverride) expect("KEYWORD", "match");
      const subject = subjectOverride || parseExpr();
      expect("LBRACE");
      const arms = [];
      while (peek() && peek().type !== "RBRACE") {
        let pattern = parsePattern();
        while (peek()?.type === "OP" && peek()?.value === "|") {
          advance();
          const alt = parsePattern();
          if (pattern.type === "or") pattern.alts.push(alt);
          else pattern = { type: "or", alts: [pattern, alt] };
        }
        let guard = null;
        if (peek()?.type === "KEYWORD" && peek()?.value === "if") {
          advance();
          guard = parseExpr();
        }
        expect("FAT_ARROW");
        let body;
        if (peek()?.type === "LBRACE") {
          body = parseBlock();
        } else {
          const expr = parseExpr();
          if (
            peek()?.type === "OP" &&
            ["=", "+=", "-=", "*=", "/="].includes(peek()?.value)
          ) {
            const op = advance().value;
            body = { type: "assign", target: expr, op, value: parseExpr() };
          } else {
            body = expr;
          }
        }
        if (peek()?.type === "COMMA") advance();
        arms.push({ pattern, guard, body });
      }
      expect("RBRACE");
      return { type: "match", subject, arms };
    }

    function parsePattern() {
      const t = peek();
      if (!t) return { type: "wildcard" };
      if (t.type === "IDENT" && t.value === "_") {
        advance();
        return { type: "wildcard" };
      }
      if (t.type === "INT" || t.type === "FLOAT") {
        advance();
        return { type: "literal", value: t.value };
      }
      if (t.type === "OP" && t.value === "-") {
        advance();
        const num = advance();
        return { type: "literal", value: -num.value };
      }
      if (t.type === "STRING") {
        advance();
        return { type: "literal", value: t.value };
      }
      if (t.type === "KEYWORD" && (t.value === "true" || t.value === "false")) {
        advance();
        return { type: "literal", value: t.value === "true" };
      }
      if (t.type === "LPAREN") {
        advance();
        const elems = [];
        while (peek() && peek().type !== "RPAREN") {
          elems.push(parsePattern());
          if (peek()?.type === "COMMA") advance();
        }
        expect("RPAREN");
        return { type: "tuple", elems };
      }
      if (t.type === "IDENT") {
        let name = advance().value;
        while (peek()?.type === "DOUBLE_COLON") {
          advance();
          name += "::" + expect("IDENT").value;
        }
        skipGenericParams();
        if (peek()?.type === "LPAREN") {
          advance();
          const bindings = [];
          while (peek() && peek().type !== "RPAREN") {
            bindings.push(parsePattern());
            if (peek()?.type === "COMMA") advance();
          }
          expect("RPAREN");
          return { type: "variant", name, bindings };
        }
        if (name === "None" || name.endsWith("::None")) {
          return { type: "variant", name: "None", bindings: [] };
        }
        if (/^[A-Z]/.test(name.split("::").pop())) {
          return { type: "type_or_variant", name };
        }
        return { type: "binding", name };
      }
      advance();
      return { type: "wildcard" };
    }

    // -- Expressions --
    function parseExpr() {
      return parseOr();
    }

    function parseOr() {
      let left = parseAnd();
      while (
        (peek()?.type === "KEYWORD" && peek()?.value === "or") ||
        (peek()?.type === "OP" && peek()?.value === "||")
      ) {
        advance();
        left = { type: "binop", op: "or", left, right: parseAnd() };
      }
      return left;
    }

    function parseAnd() {
      let left = parseEquality();
      while (
        (peek()?.type === "KEYWORD" && peek()?.value === "and") ||
        (peek()?.type === "OP" && peek()?.value === "&&")
      ) {
        advance();
        left = { type: "binop", op: "and", left, right: parseEquality() };
      }
      return left;
    }

    function parseEquality() {
      let left = parseComparison();
      while (peek()?.type === "OP" && (peek()?.value === "==" || peek()?.value === "!=")) {
        const op = advance().value;
        left = { type: "binop", op, left, right: parseComparison() };
      }
      return left;
    }

    function parseComparison() {
      let left = parsePipeline();
      while (
        peek()?.type === "OP" &&
        ["<", ">", "<=", ">="].includes(peek()?.value)
      ) {
        const op = advance().value;
        left = { type: "binop", op, left, right: parsePipeline() };
      }
      return left;
    }

    function parsePipeline() {
      let left = parseBitwise();
      while (peek()?.type === "PIPE") {
        advance();
        if (peek()?.type === "KEYWORD" && peek()?.value === "await") {
          advance();
          if (peekRaw()?.type === "QUESTION") {
            advance();
            left = { type: "propagate", expr: { type: "await", expr: left } };
          } else {
            left = { type: "await", expr: left };
          }
          continue;
        }
        if (peek()?.type === "KEYWORD" && peek()?.value === "match") {
          advance();
          left = parseMatch(left);
          continue;
        }
        const stage = parseUnary();
        left = { type: "pipe", left, stage };
      }
      return left;
    }

    function parseBitwise() {
      let left = parseRange();
      while (
        peek()?.type === "OP" &&
        ["&", "^", "<<", ">>"].includes(peek()?.value)
      ) {
        const op = advance().value;
        left = { type: "binop", op, left, right: parseRange() };
      }
      return left;
    }

    function parseRange() {
      let left = parseAddSub();
      if (peek()?.type === "RANGE_OP" || peek()?.type === "RANGE_INC") {
        const nextAfterRange = tokens[pos + 1];
        if (nextAfterRange && nextAfterRange.type === "RBRACKET") {
          return left;
        }
        const inc = advance().type === "RANGE_INC";
        if (peek()?.type === "RBRACKET") {
          return { type: "open_range", start: left };
        }
        const right = parseAddSub();
        return { type: "range", start: left, end: right, inclusive: inc };
      }
      return left;
    }

    function parseAddSub() {
      let left = parseMulDiv();
      while (peek()?.type === "OP" && (peek()?.value === "+" || peek()?.value === "-")) {
        const op = advance().value;
        left = { type: "binop", op, left, right: parseMulDiv() };
      }
      return left;
    }

    function parseMulDiv() {
      let left = parsePowCast();
      while (
        peek()?.type === "OP" &&
        (peek()?.value === "*" || peek()?.value === "/" || peek()?.value === "%")
      ) {
        const op = advance().value;
        left = { type: "binop", op, left, right: parsePowCast() };
      }
      return left;
    }

    function parsePowCast() {
      let left = parseUnary();
      if (peek()?.type === "OP" && peek()?.value === "**") {
        advance();
        left = { type: "binop", op: "**", left, right: parsePowCast() };
      }
      while (peek()?.type === "KEYWORD" && peek()?.value === "as") {
        advance();
        const targetType = parseTypeAnnotation();
        left = { type: "cast", expr: left, targetType };
      }
      return left;
    }

    function parseUnary() {
      const t = peek();
      if (t?.type === "OP" && t.value === "-") {
        advance();
        return { type: "unary", op: "-", operand: parseUnary() };
      }
      if ((t?.type === "OP" && t.value === "!") || (t?.type === "KEYWORD" && t.value === "not")) {
        advance();
        return { type: "unary", op: "!", operand: parseUnary() };
      }
      if (t?.type === "KEYWORD" && t.value === "await") {
        advance();
        return { type: "await", expr: parseUnary() };
      }
      if (t?.type === "KEYWORD" && t.value === "spawn") {
        advance();
        const blk = peek()?.type === "LBRACE" ? parseBlock() : parseUnary();
        return { type: "spawn", body: blk };
      }
      if (t?.type === "KEYWORD" && t.value === "perform") {
        advance();
        const call = parsePostfix();
        return { type: "perform", call };
      }
      if (t?.type === "KEYWORD" && t.value === "comptime") {
        advance();
        return { type: "comptime", body: parseBlock() };
      }
      if (t?.type === "KEYWORD" && t.value === "handle") {
        return parseHandleExpr();
      }
      return parsePostfix();
    }

    function parseHandleExpr() {
      expect("KEYWORD", "handle");
      const body = parseBlock();
      expect("KEYWORD", "with");
      expect("LBRACE");
      const handlers = [];
      while (peek() && peek().type !== "RBRACE") {
        let effName = expect("IDENT").value;
        let opName = "";
        if (peek()?.type === "DOUBLE_COLON") {
          advance();
          opName = expect("IDENT").value;
        }
        const params = [];
        if (peek()?.type === "LPAREN") {
          advance();
          while (peek() && peek().type !== "RPAREN") {
            params.push(expect("IDENT").value);
            if (peek()?.type === "COMMA") advance();
          }
          expect("RPAREN");
        }
        expect("FAT_ARROW");
        const hBody = peek()?.type === "LBRACE" ? parseBlock() : parseExpr();
        if (peek()?.type === "KEYWORD" && peek()?.value === "with") {
          advance();
          parseTypeAnnotation();
        }
        if (peek()?.type === "COMMA") advance();
        handlers.push({ effect: effName, op: opName, params, body: hBody });
      }
      expect("RBRACE");
      return { type: "handle", body, handlers };
    }

    function parsePostfix() {
      let node = parsePrimary();
      while (true) {
        const nextRaw = peekRaw();
        // Do not consume '(' or '[' across a newline as a continuation of previous stmt
        const sameLine = !nextRaw || nextRaw.type !== "NEWLINE";
        const p = peek();
        if (!p) break;

        if (p.type === "DOT") {
          advance();
          const fieldTok = advance();
          const field = String(fieldTok.value);
          if (peekRaw()?.type === "LPAREN") {
            advance();
            const args = parseArgs();
            expect("RPAREN");
            node = { type: "method_call", object: node, method: field, args };
          } else {
            node = { type: "field", object: node, field };
          }
          continue;
        }

        if (p.type === "DOUBLE_COLON" && node.type === "ident") {
          advance();
          if (peek()?.type === "OP" && peek()?.value === "<") {
            // Turbofish: `fn_name::<Type>()`
            advance();
            const typeArgs = [];
            let depth = 1;
            while (pos < tokens.length && depth > 0) {
              if (peek()?.type === "OP" && peek()?.value === ">") {
                advance();
                depth--;
                break;
              }
              typeArgs.push(parseTypeAnnotation());
              if (peek()?.type === "COMMA") advance();
              else if (peek()?.type === "OP" && peek()?.value === ">") {
                advance();
                depth--;
              } else break;
            }
            if (peekRaw()?.type === "LPAREN") {
              advance();
              const args = parseArgs();
              expect("RPAREN");
              node = { type: "call", callee: node.name, args, typeArgs };
            }
            continue;
          }
          const member = expect("IDENT").value;
          // Handle chained turbofish e.g. `channel::<SensorReading>(8)`
          if (peek()?.type === "DOUBLE_COLON") {
            node = { type: "ident", name: node.name + "::" + member };
            continue;
          }
          if (peekRaw()?.type === "LPAREN") {
            advance();
            const args = parseArgs();
            expect("RPAREN");
            node = { type: "static_call", ns: node.name, method: member, args };
          } else {
            node = { type: "static_ref", ns: node.name, member };
          }
          continue;
        }

        if (sameLine && p.type === "LPAREN") {
          advance();
          const args = parseArgs();
          expect("RPAREN");
          if (node.type === "ident") {
            node = { type: "call", callee: node.name, args };
          } else {
            node = { type: "call_expr", calleeExpr: node, args };
          }
          continue;
        }

        if (sameLine && p.type === "LBRACKET") {
          advance();
          const startIdx = parseExpr();
          if (startIdx.type === "open_range") {
            expect("RBRACKET");
            node = { type: "slice", object: node, start: startIdx.start, end: null };
          } else if (peek()?.type === "RANGE_OP") {
            advance();
            let endIdx = null;
            if (peek()?.type !== "RBRACKET") endIdx = parseExpr();
            expect("RBRACKET");
            node = { type: "slice", object: node, start: startIdx, end: endIdx };
          } else {
            expect("RBRACKET");
            node = { type: "index", object: node, index: startIdx };
          }
          continue;
        }

        if (sameLine && p.type === "QUESTION") {
          advance();
          node = { type: "propagate", expr: node };
          continue;
        }

        break;
      }
      return node;
    }

    function parseArgs() {
      const args = [];
      while (peek() && peek().type !== "RPAREN") {
        args.push(parseExpr());
        if (peek()?.type === "COMMA") advance();
      }
      return args;
    }

    function isStructLiteralAhead() {
      // Distinguish `StructName { field: expr }` or `StructName { x, y }` or `StructName {}`
      // from `match x { ... }` / `if cond { ... }` where `{` opens a statement block.
      let p = pos;
      while (p < tokens.length && (tokens[p].type === "NEWLINE" || tokens[p].type === "SEMI")) p++;
      if (tokens[p]?.type !== "LBRACE") return false;
      let q = p + 1;
      while (q < tokens.length && (tokens[q].type === "NEWLINE" || tokens[q].type === "SEMI")) q++;
      const first = tokens[q];
      if (!first) return false;
      if (first.type === "RBRACE") return true;
      if (first.type === "RANGE_OP") return true;
      if (first.type === "IDENT") {
        const after = tokens[q + 1];
        if (after && (after.type === "COLON" || after.type === "COMMA" || after.type === "RBRACE")) {
          return true;
        }
      }
      return false;
    }

    function parseStructInit(structName) {
      expect("LBRACE");
      const fields = [];
      let spread = null;
      while (peek() && peek().type !== "RBRACE") {
        if (peek()?.type === "RANGE_OP") {
          advance();
          spread = parseExpr();
          if (peek()?.type === "COMMA") advance();
          continue;
        }
        const fname = expect("IDENT").value;
        let fval;
        if (peek()?.type === "COLON") {
          advance();
          fval = parseExpr();
        } else {
          fval = { type: "ident", name: fname };
        }
        fields.push({ name: fname, value: fval });
        if (peek()?.type === "COMMA") advance();
      }
      expect("RBRACE");
      return { type: "struct_init", name: structName, fields, spread };
    }

    function parsePrimary() {
      const t = peek();
      if (!t) throw new CompileError("Unexpected end of input");

      if (t.type === "INT") {
        advance();
        return { type: "literal", kind: "int", value: t.value };
      }
      if (t.type === "FLOAT") {
        advance();
        return { type: "literal", kind: "float", value: t.value };
      }
      if (t.type === "STRING") {
        advance();
        return { type: "string", raw: t.value, quote: t.quote };
      }
      if (t.type === "KEYWORD" && (t.value === "true" || t.value === "false")) {
        advance();
        return { type: "literal", kind: "bool", value: t.value === "true" };
      }
      if (t.type === "KEYWORD" && t.value === "self") {
        advance();
        return { type: "ident", name: "self" };
      }
      if (t.type === "KEYWORD" && t.value === "if") {
        return parseIf();
      }
      if (t.type === "KEYWORD" && t.value === "match") {
        return parseMatch();
      }
      if (t.type === "KEYWORD" && t.value === "fn") {
        return parseFn(false, false);
      }

      // Zero-arg lambda `|| body` or `|params| body`
      if (t.type === "OP" && t.value === "||") {
        advance();
        const body = peek()?.type === "LBRACE" ? parseBlock() : parseExpr();
        return { type: "lambda", params: [], body };
      }
      if (t.type === "OP" && t.value === "|") {
        advance();
        const params = [];
        while (peek() && !(peek().type === "OP" && peek().value === "|")) {
          if (peek()?.type === "LPAREN") {
            advance();
            const names = [];
            while (peek() && peek().type !== "RPAREN") {
              names.push(advance().value);
              if (peek()?.type === "COMMA") advance();
            }
            expect("RPAREN");
            params.push({ tuple: names });
          } else {
            const p = advance().value;
            if (peek()?.type === "COLON") {
              advance();
              parseTypeAnnotation();
            }
            params.push({ name: p });
          }
          if (peek()?.type === "COMMA") advance();
        }
        expect("OP", "|");
        const body = peek()?.type === "LBRACE" ? parseBlock() : parseExpr();
        return { type: "lambda", params, body };
      }

      if (t.type === "LPAREN") {
        advance();
        if (peek()?.type === "RPAREN") {
          advance();
          return { type: "literal", kind: "nil", value: null };
        }
        const first = parseExpr();
        if (peek()?.type === "COMMA") {
          const elems = [first];
          while (peek()?.type === "COMMA") {
            advance();
            if (peek()?.type === "RPAREN") break;
            elems.push(parseExpr());
          }
          expect("RPAREN");
          return { type: "tuple", elems };
        }
        expect("RPAREN");
        return first;
      }

      if (t.type === "LBRACKET") {
        advance();
        if (peek()?.type === "RBRACKET") {
          advance();
          return { type: "list", elems: [] };
        }
        const first = parseExpr();
        if (peekRaw()?.type === "SEMI" || peek()?.type === "SEMI") {
          if (peekRaw()?.type === "SEMI") pos++;
          const countExpr = parseExpr();
          expect("RBRACKET");
          return { type: "repeat_list", value: first, count: countExpr };
        }
        const elems = [first];
        while (peek()?.type === "COMMA") {
          advance();
          if (peek()?.type === "RBRACKET") break;
          elems.push(parseExpr());
        }
        expect("RBRACKET");
        return { type: "list", elems };
      }

      if (t.type === "LBRACE") {
        // Map literal `{ "k": v }` or block expression
        let save = pos;
        advance();
        if (peek()?.type === "RBRACE") {
          advance();
          return { type: "map", entries: [] };
        }
        const firstExpr = parseExpr();
        if (peek()?.type === "COLON") {
          expect("COLON");
          const firstVal = parseExpr();
          const entries = [{ key: firstExpr, value: firstVal }];
          while (peek()?.type === "COMMA") {
            advance();
            if (peek()?.type === "RBRACE") break;
            const k = parseExpr();
            expect("COLON");
            const v = parseExpr();
            entries.push({ key: k, value: v });
          }
          expect("RBRACKET" === peek()?.type ? "RBRACKET" : "RBRACE");
          return { type: "map", entries };
        }
        pos = save;
        return parseBlock();
      }

      if (t.type === "IDENT") {
        let name = advance().value;
        while (peek()?.type === "DOUBLE_COLON" && tokens[pos + 1]?.type === "IDENT") {
          // Peek ahead for `module::Type { ... }` struct init
          const nextIdent = tokens[pos + 1].value;
          if (/^[A-Z]/.test(nextIdent)) {
            const saveP = pos;
            advance();
            const seg = advance().value;
            if (isStructLiteralAhead()) {
              return parseStructInit(name + "::" + seg);
            }
            pos = saveP;
            break;
          }
          break;
        }
        if (/^[A-Z]/.test(name) && isStructLiteralAhead()) {
          return parseStructInit(name);
        }
        if (name === "None") {
          return { type: "none" };
        }
        return { type: "ident", name };
      }

      throw new CompileError(
        "Unexpected token " + t.type + (t.value !== undefined ? " '" + t.value + "'" : ""),
        t.line,
        t.col
      );
    }

    return parseProgram();
  }

  // --------------------------------------------------------------------------
  // 4. Tier-1 Native Linear-Memory WASM Codegen (for core scalar/string ASTs)
  // --------------------------------------------------------------------------

  const NATIVE_SCALAR_BUILTINS = new Set([
    "println", "print", "http_get", "str", "to_string", "int", "float",
    "len", "abs", "sqrt", "floor", "ceil",
  ]);

  function canCompilePureNative(prog) {
    const userFns = new Set();
    for (const s of prog.body) {
      if (s.type === "fn") {
        if (s.decorators?.length || s.genericNames?.length) return false;
        userFns.add(s.name);
      }
    }

    function checkStmt(s) {
      if (!s) return true;
      switch (s.type) {
        case "import":
        case "noop":
        case "break":
        case "continue":
          return true;
        case "fn":
          return checkBlock(s.body);
        case "block":
          return checkBlock(s);
        case "let":
          return checkExpr(s.value);
        case "assign":
          return s.target.type === "ident" && checkExpr(s.value);
        case "return":
          return !s.value || checkExpr(s.value);
        case "if":
          return (
            checkExpr(s.cond) &&
            checkStmt(s.thenBranch) &&
            (!s.elseBranch || checkStmt(s.elseBranch))
          );
        case "while":
          return checkExpr(s.cond) && checkStmt(s.body);
        case "loop":
          return checkStmt(s.body);
        case "for":
          return !s.tupleVars && s.iter.type === "range" && checkExpr(s.iter.start) && checkExpr(s.iter.end) && checkStmt(s.body);
        case "expr_stmt":
          return checkExpr(s.expr);
        default:
          return false;
      }
    }

    function checkBlock(b) {
      return b.body.every(checkStmt);
    }

    function checkExpr(e) {
      if (!e) return true;
      switch (e.type) {
        case "literal":
          return e.kind !== "nil";
        case "ident":
          return true;
        case "string": {
          // Interpolated expressions inside `{...}` must be simple identifiers or calls without format specs
          const matches = e.raw.match(/\{([^}]+)\}/g) || [];
          for (const m of matches) {
            const inner = m.slice(1, -1);
            if (inner.includes(":")) return false;
            try {
              const subProg = parseLateralus(inner);
              if (subProg.body.length !== 1 || subProg.body[0].type !== "expr_stmt") return false;
              if (!checkExpr(subProg.body[0].expr)) return false;
            } catch (_) {
              return false;
            }
          }
          return true;
        }
        case "unary":
          return checkExpr(e.operand);
        case "cast":
          return ["str", "String", "int", "Int", "float", "Float"].includes(e.targetType) && checkExpr(e.expr);
        case "binop":
          return checkExpr(e.left) && checkExpr(e.right);
        case "pipe":
          if (!checkExpr(e.left)) return false;
          if (e.stage.type === "ident") {
            return NATIVE_SCALAR_BUILTINS.has(e.stage.name) || userFns.has(e.stage.name);
          }
          if (e.stage.type === "call") {
            return (
              (NATIVE_SCALAR_BUILTINS.has(e.stage.callee) || userFns.has(e.stage.callee)) &&
              e.stage.args.every(checkExpr)
            );
          }
          return false;
        case "call":
          return (
            (NATIVE_SCALAR_BUILTINS.has(e.callee) || userFns.has(e.callee)) &&
            e.args.every(checkExpr)
          );
        case "method_call":
          if (
            e.object.type === "ident" &&
            ["io", "http", "math"].includes(e.object.name) &&
            ["println", "print", "get", "sqrt", "abs", "floor", "ceil"].includes(e.method)
          ) {
            return e.args.every(checkExpr);
          }
          return false;
        case "static_call":
          if (
            ["io", "http", "math"].includes(e.ns) &&
            ["println", "print", "get", "sqrt", "abs", "floor", "ceil"].includes(e.method)
          ) {
            return e.args.every(checkExpr);
          }
          return false;
        default:
          return false;
      }
    }

    return prog.body.every(checkStmt);
  }

  function compileNativeTier1(prog) {
    const mod = new WasmModuleBuilder("lateralus_native_wasm");
    mod.importFunction("env", "println", "println", [["ptr", "i32"], ["len", "i32"]], "");
    mod.importFunction("env", "print", "print", [["ptr", "i32"], ["len", "i32"]], "");
    mod.importFunction(
      "env",
      "http_get",
      "http_get",
      [["url_ptr", "i32"], ["url_len", "i32"], ["out_ptr", "i32"], ["out_cap", "i32"]],
      "i32"
    );

    const heapGlobal = mod.addGlobal("__heap_ptr", "i32", true, "4096");
    const ptrEmpty = mod.addStringConstant("");
    const ptrZero = mod.addStringConstant("0");
    const ptrMinI64 = mod.addStringConstant("-9223372036854775808");
    const ptrTrue = mod.addStringConstant("true");
    const ptrFalse = mod.addStringConstant("false");
    const ptrDot = mod.addStringConstant(".");
    const ptrMinus = mod.addStringConstant("-");

    emitNativeRuntimeHelpers(mod, {
      ptrZero,
      ptrMinI64,
      ptrTrue,
      ptrFalse,
      ptrDot,
      ptrMinus,
    });

    const fnSigs = new Map();
    const fnNodes = [];
    const topStmts = [];

    function mapType(ann) {
      if (!ann) return "int";
      if (["float", "Float", "f64"].includes(ann)) return "float";
      if (["bool", "Bool"].includes(ann)) return "bool";
      if (["str", "String"].includes(ann)) return "str";
      if (["None", "void", "()"].includes(ann)) return "void";
      return "int";
    }
    function semToWasm(s) {
      if (s === "void") return "";
      if (s === "float") return "f64";
      if (s === "bool" || s === "str") return "i32";
      return "i64";
    }

    for (const s of prog.body) {
      if (s.type === "import" || s.type === "noop") continue;
      if (s.type === "fn") {
        const pTypes = s.params.map((p) => mapType(p.typeAnn));
        let rType = s.retType ? mapType(s.retType) : "void";
        if (!s.retType) {
          for (const st of s.body.body) {
            if (st.type === "return" && st.value) rType = "int";
          }
        }
        if (s.name === "main" && rType === "void") rType = "int";
        fnSigs.set(s.name, { name: s.name, paramTypes: pTypes, retType: rType });
        fnNodes.push(s);
      } else {
        topStmts.push(s);
      }
    }

    let uidCounter = 0;
    const uid = (p) => "__" + p + "_" + ++uidCounter;

    function compileFunction(fnDecl) {
      const sig = fnSigs.get(fnDecl.name);
      const wParams = fnDecl.params.map((p, idx) => [p.name, semToWasm(sig.paramTypes[idx])]);
      const fn = mod.addFunction(fnDecl.name, wParams, semToWasm(sig.retType), true);
      const localsSem = new Map();
      fnDecl.params.forEach((p, idx) => localsSem.set(p.name, sig.paramTypes[idx]));
      const loopStack = [];

      function coerce(actual, target) {
        if (actual === target) return target;
        if (target === "str") {
          toStr(actual);
          return "str";
        }
        if (actual === "int" && target === "float") {
          fn.emit("f64.convert_i64_s");
          return "float";
        }
        if (actual === "float" && target === "int") {
          fn.emit("i64.trunc_f64_s");
          return "int";
        }
        if (actual === "bool" && target === "int") {
          fn.emit("i64.extend_i32_u");
          return "int";
        }
        return target;
      }

      function toStr(sem) {
        if (sem === "str") return;
        if (sem === "float") fn.emit("call $__f64_to_str");
        else if (sem === "bool") fn.emit("call $__bool_to_str");
        else fn.emit("call $__i64_to_str");
      }

      function toBool(sem) {
        if (sem === "bool") return;
        if (sem === "int") fn.emit("i64.const 0", "i64.ne");
        else if (sem === "float") fn.emit("f64.const 0.0", "f64.ne");
        else if (sem === "str") fn.emit("call $__strlen", "i32.const 0", "i32.gt_u");
      }

      function guessSem(e) {
        if (!e) return "int";
        if (e.type === "literal") return e.kind;
        if (e.type === "string") return "str";
        if (e.type === "ident") return localsSem.get(e.name) || "int";
        if (e.type === "cast") return mapType(e.targetType);
        if (e.type === "call") {
          if (["http_get", "str", "to_string"].includes(e.callee)) return "str";
          if (["sqrt", "floor", "ceil", "float"].includes(e.callee)) return "float";
          return fnSigs.get(e.callee)?.retType || "int";
        }
        if (e.type === "method_call" || e.type === "static_call") {
          if (e.method === "get") return "str";
          if (["sqrt", "floor", "ceil"].includes(e.method)) return "float";
          return "void";
        }
        if (e.type === "binop") {
          if (["==", "!=", "<", ">", "<=", ">=", "and", "or"].includes(e.op)) return "bool";
          const ls = guessSem(e.left);
          const rs = guessSem(e.right);
          if (ls === "str" || rs === "str") return "str";
          if (ls === "float" || rs === "float") return "float";
        }
        return "int";
      }

      function emitDefault(sem) {
        const wt = semToWasm(sem);
        if (wt === "f64") fn.emit("f64.const 0.0");
        else if (wt === "i32") fn.emit("i32.const " + (sem === "str" ? ptrEmpty : 0));
        else if (wt === "i64") fn.emit("i64.const 0");
      }

      function emitStmt(s) {
        if (!s || s.type === "noop" || s.type === "import") return;
        if (s.type === "block") {
          s.body.forEach(emitStmt);
          return;
        }
        if (s.type === "let") {
          const vSem = emitExpr(s.value);
          const target = s.typeAnn ? mapType(s.typeAnn) : vSem;
          coerce(vSem, target);
          fn.addLocal(s.name, semToWasm(target));
          localsSem.set(s.name, target);
          fn.emit("local.set $" + s.name);
          return;
        }
        if (s.type === "assign" && s.target.type === "ident") {
          const name = s.target.name;
          const curSem = localsSem.get(name) || "int";
          if (s.op === "=") {
            const vSem = emitExpr(s.value);
            if (!localsSem.has(name)) {
              fn.addLocal(name, semToWasm(vSem));
              localsSem.set(name, vSem);
            } else {
              coerce(vSem, curSem);
            }
            fn.emit("local.set $" + name);
          } else {
            const bop = s.op.slice(0, -1);
            const vSem = emitExpr({ type: "binop", op: bop, left: s.target, right: s.value });
            coerce(vSem, curSem);
            fn.emit("local.set $" + name);
          }
          return;
        }
        if (s.type === "return") {
          if (s.value && sig.retType !== "void") {
            const vSem = emitExpr(s.value);
            coerce(vSem, sig.retType);
          } else if (sig.retType !== "void") {
            emitDefault(sig.retType);
          }
          fn.emit("return");
          return;
        }
        if (s.type === "if") {
          const cSem = emitExpr(s.cond);
          toBool(cSem);
          fn.emit("if");
          emitStmt(s.thenBranch);
          if (s.elseBranch) {
            fn.emit("else");
            emitStmt(s.elseBranch);
          }
          fn.emit("end");
          return;
        }
        if (s.type === "while") {
          const brk = uid("wbrk");
          const cnt = uid("wcnt");
          loopStack.push([brk, cnt]);
          fn.emit("block $" + brk, "loop $" + cnt);
          const cSem = emitExpr(s.cond);
          toBool(cSem);
          fn.emit("i32.eqz", "br_if $" + brk);
          emitStmt(s.body);
          fn.emit("br $" + cnt, "end", "end");
          loopStack.pop();
          return;
        }
        if (s.type === "loop") {
          const brk = uid("lbrk");
          const cnt = uid("lcnt");
          loopStack.push([brk, cnt]);
          fn.emit("block $" + brk, "loop $" + cnt);
          emitStmt(s.body);
          fn.emit("br $" + cnt, "end", "end");
          loopStack.pop();
          return;
        }
        if (s.type === "for" && s.iter.type === "range") {
          const brk = uid("fbrk");
          const cnt = uid("fcnt");
          const endTmp = uid("fend");
          fn.addLocal(s.varName, "i64");
          fn.addLocal(endTmp, "i64");
          localsSem.set(s.varName, "int");
          coerce(emitExpr(s.iter.start), "int");
          fn.emit("local.set $" + s.varName);
          coerce(emitExpr(s.iter.end), "int");
          fn.emit("local.set $" + endTmp);
          loopStack.push([brk, cnt]);
          fn.emit("block $" + brk, "loop $" + cnt);
          fn.emit(
            "local.get $" + s.varName,
            "local.get $" + endTmp,
            s.iter.inclusive ? "i64.gt_s" : "i64.ge_s",
            "br_if $" + brk
          );
          emitStmt(s.body);
          fn.emit(
            "local.get $" + s.varName,
            "i64.const 1",
            "i64.add",
            "local.set $" + s.varName,
            "br $" + cnt,
            "end",
            "end"
          );
          loopStack.pop();
          return;
        }
        if (s.type === "break") {
          if (loopStack.length) fn.emit("br $" + loopStack[loopStack.length - 1][0]);
          return;
        }
        if (s.type === "continue") {
          if (loopStack.length) fn.emit("br $" + loopStack[loopStack.length - 1][1]);
          return;
        }
        if (s.type === "expr_stmt") {
          const rSem = emitExpr(s.expr);
          if (rSem !== "void") fn.emit("drop");
        }
      }

      function emitStringInterp(raw) {
        const parts = [];
        let last = 0;
        const re = /\{([^}]+)\}/g;
        let m;
        while ((m = re.exec(raw)) !== null) {
          if (m.index > last) parts.push({ lit: raw.slice(last, m.index) });
          parts.push({ exprSrc: m[1] });
          last = m.index + m[0].length;
        }
        if (last < raw.length || parts.length === 0) {
          parts.push({ lit: raw.slice(last) });
        }
        parts.forEach((p, idx) => {
          if (p.lit !== undefined) {
            fn.emit("i32.const " + mod.addStringConstant(p.lit));
          } else {
            const subAst = parseLateralus(p.exprSrc).body[0].expr;
            const subSem = emitExpr(subAst);
            toStr(subSem);
          }
          if (idx > 0) fn.emit("call $__str_concat");
        });
        return "str";
      }

      function emitCall(name, args) {
        if (name === "println" || name === "io.println" || name === "print" || name === "io.print") {
          const helper = name.endsWith("println") ? "$__println_str" : "$__print_str";
          if (args.length === 0) {
            fn.emit("i32.const " + ptrEmpty, "call " + helper);
            return "void";
          }
          args.forEach((a, idx) => {
            if (idx > 0) fn.emit("i32.const " + mod.addStringConstant(" "));
            const aSem = emitExpr(a);
            toStr(aSem);
            if (idx > 0) fn.emit("call $__str_concat");
          });
          fn.emit("call " + helper);
          return "void";
        }
        if (name === "http_get" || name === "http.get") {
          if (args.length > 0) {
            const uSem = emitExpr(args[0]);
            toStr(uSem);
          } else {
            fn.emit("i32.const " + ptrEmpty);
          }
          fn.emit("call $__http_get_str");
          return "str";
        }
        if ((name === "str" || name === "to_string") && args.length > 0) {
          toStr(emitExpr(args[0]));
          return "str";
        }
        if (name === "int" && args.length > 0) return coerce(emitExpr(args[0]), "int");
        if (name === "float" && args.length > 0) return coerce(emitExpr(args[0]), "float");
        if (name === "len" && args.length > 0) {
          const s = emitExpr(args[0]);
          if (s === "str") fn.emit("call $__strlen", "i64.extend_i32_u");
          else {
            fn.emit("drop", "i64.const 0");
          }
          return "int";
        }
        if ((name === "sqrt" || name === "math.sqrt") && args.length > 0) {
          coerce(emitExpr(args[0]), "float");
          fn.emit("f64.sqrt");
          return "float";
        }
        if ((name === "floor" || name === "math.floor" || name === "ceil" || name === "math.ceil") && args.length > 0) {
          coerce(emitExpr(args[0]), "float");
          fn.emit(name.includes("floor") ? "f64.floor" : "f64.ceil");
          return "float";
        }
        if ((name === "abs" || name === "math.abs") && args.length > 0) {
          const s = emitExpr(args[0]);
          if (s === "float") {
            fn.emit("f64.abs");
            return "float";
          }
          const t = uid("abs");
          fn.addLocal(t, "i64");
          fn.emit(
            "local.tee $" + t,
            "i64.const 0",
            "i64.lt_s",
            "if (result i64)",
            "i64.const 0",
            "local.get $" + t,
            "i64.sub",
            "else",
            "local.get $" + t,
            "end"
          );
          return "int";
        }
        const targetSig = fnSigs.get(name);
        if (targetSig) {
          targetSig.paramTypes.forEach((pSem, idx) => {
            if (idx < args.length) coerce(emitExpr(args[idx]), pSem);
            else emitDefault(pSem);
          });
          fn.emit("call $" + targetSig.name);
          return targetSig.retType;
        }
        args.forEach((a) => {
          if (emitExpr(a) !== "void") fn.emit("drop");
        });
        fn.emit("i64.const 0");
        return "int";
      }

      function emitExpr(e) {
        if (e.type === "literal") {
          if (e.kind === "float") {
            fn.emit("f64.const " + e.value);
            return "float";
          }
          if (e.kind === "bool") {
            fn.emit("i32.const " + (e.value ? 1 : 0));
            return "bool";
          }
          fn.emit("i64.const " + BigInt(Math.trunc(e.value)).toString());
          return "int";
        }
        if (e.type === "string") return emitStringInterp(e.raw);
        if (e.type === "ident") {
          if (localsSem.has(e.name)) {
            fn.emit("local.get $" + e.name);
            return localsSem.get(e.name);
          }
          fn.emit("i64.const 0");
          return "int";
        }
        if (e.type === "cast") {
          return coerce(emitExpr(e.expr), mapType(e.targetType));
        }
        if (e.type === "unary") {
          const s = emitExpr(e.operand);
          if (e.op === "-") {
            if (s === "float") {
              fn.emit("f64.neg");
              return "float";
            }
            const t = uid("neg");
            fn.addLocal(t, "i64");
            fn.emit("local.set $" + t, "i64.const 0", "local.get $" + t, "i64.sub");
            return "int";
          }
          toBool(s);
          fn.emit("i32.eqz");
          return "bool";
        }
        if (e.type === "pipe") {
          if (e.stage.type === "ident") return emitCall(e.stage.name, [e.left]);
          if (e.stage.type === "call") return emitCall(e.stage.callee, [e.left, ...e.stage.args]);
        }
        if (e.type === "call") return emitCall(e.callee, e.args);
        if (e.type === "method_call" && e.object.type === "ident") {
          return emitCall(e.object.name + "." + e.method, e.args);
        }
        if (e.type === "static_call") {
          return emitCall(e.ns + "." + e.method, e.args);
        }
        if (e.type === "binop") {
          if (e.op === "and") {
            toBool(emitExpr(e.left));
            fn.emit("if (result i32)");
            toBool(emitExpr(e.right));
            fn.emit("else", "i32.const 0", "end");
            return "bool";
          }
          if (e.op === "or") {
            toBool(emitExpr(e.left));
            fn.emit("if (result i32)", "i32.const 1", "else");
            toBool(emitExpr(e.right));
            fn.emit("end");
            return "bool";
          }
          const lg = guessSem(e.left);
          const rg = guessSem(e.right);
          if (e.op === "+" && (lg === "str" || rg === "str")) {
            toStr(emitExpr(e.left));
            toStr(emitExpr(e.right));
            fn.emit("call $__str_concat");
            return "str";
          }
          if ((e.op === "==" || e.op === "!=") && (lg === "str" || rg === "str")) {
            toStr(emitExpr(e.left));
            toStr(emitExpr(e.right));
            fn.emit("call $__str_eq");
            if (e.op === "!=") fn.emit("i32.eqz");
            return "bool";
          }
          if (lg === "float" || rg === "float") {
            coerce(emitExpr(e.left), "float");
            coerce(emitExpr(e.right), "float");
            const fops = {
              "+": "f64.add", "-": "f64.sub", "*": "f64.mul", "/": "f64.div",
              "==": "f64.eq", "!=": "f64.ne", "<": "f64.lt", ">": "f64.gt",
              "<=": "f64.le", ">=": "f64.ge",
            };
            fn.emit(fops[e.op] || "f64.add");
            return ["==", "!=", "<", ">", "<=", ">="].includes(e.op) ? "bool" : "float";
          }
          coerce(emitExpr(e.left), "int");
          coerce(emitExpr(e.right), "int");
          if (e.op === "**") {
            fn.emit("call $__pow_i64");
            return "int";
          }
          const iops = {
            "+": "i64.add", "-": "i64.sub", "*": "i64.mul", "/": "i64.div_s", "%": "i64.rem_s",
            "&": "i64.and", "|": "i64.or", "^": "i64.xor", "<<": "i64.shl", ">>": "i64.shr_s",
            "==": "i64.eq", "!=": "i64.ne", "<": "i64.lt_s", ">": "i64.gt_s",
            "<=": "i64.le_s", ">=": "i64.ge_s",
          };
          fn.emit(iops[e.op] || "i64.add");
          return ["==", "!=", "<", ">", "<=", ">="].includes(e.op) ? "bool" : "int";
        }
        fn.emit("i64.const 0");
        return "int";
      }

      const bodyStmts = fnDecl.body.body;
      bodyStmts.forEach((st, idx) => {
        if (idx === bodyStmts.length - 1 && sig.retType !== "void" && st.type === "expr_stmt") {
          const rSem = emitExpr(st.expr);
          if (rSem === "void") emitDefault(sig.retType);
          else coerce(rSem, sig.retType);
          fn.emit("return");
        } else {
          emitStmt(st);
        }
      });
      if (sig.retType !== "void") emitDefault(sig.retType);
    }

    for (const fnNode of fnNodes) {
      compileFunction(fnNode);
    }

    const filteredTop = topStmts.filter(
      (s) => !(fnSigs.has("main") && s.type === "expr_stmt" && s.expr.type === "call" && s.expr.callee === "main")
    );

    if (!fnSigs.has("main")) {
      fnSigs.set("main", { name: "main", paramTypes: [], retType: "int" });
      compileFunction({
        type: "fn",
        name: "main",
        params: [],
        retType: "Int",
        body: { type: "block", body: filteredTop },
      });
    } else if (filteredTop.length > 0) {
      fnSigs.set("_start", { name: "_start", paramTypes: [], retType: "int" });
      compileFunction({
        type: "fn",
        name: "_start",
        params: [],
        retType: "Int",
        body: {
          type: "block",
          body: filteredTop.concat([{ type: "expr_stmt", expr: { type: "call", callee: "main", args: [] } }]),
        },
      });
    }

    heapGlobal.initValue = String(Math.max(4096, (mod.dataOffset + 63) & ~63));
    return {
      mode: "native-wasm",
      wat: mod.toWat(),
      wasmBytes: mod.toBytes(),
    };
  }

  function emitNativeRuntimeHelpers(mod, ptrs) {
    const alloc = mod.addFunction("__alloc", [["size", "i32"]], "i32", false);
    alloc.addLocal("ptr", "i32");
    alloc.addLocal("aligned", "i32");
    alloc.addLocal("next_ptr", "i32");
    alloc.emit(
      "local.get $size", "i32.const 7", "i32.add", "i32.const -8", "i32.and", "local.set $aligned",
      "global.get $__heap_ptr", "local.set $ptr",
      "local.get $ptr", "local.get $aligned", "i32.add", "local.set $next_ptr",
      "block $gdone", "loop $gloop",
      "local.get $next_ptr", "memory.size", "i32.const 65536", "i32.mul", "i32.le_u", "br_if $gdone",
      "i32.const 2", "memory.grow", "drop", "br $gloop",
      "end", "end",
      "local.get $next_ptr", "global.set $__heap_ptr",
      "local.get $ptr"
    );

    const strlen = mod.addFunction("__strlen", [["ptr", "i32"]], "i32", false);
    strlen.addLocal("len", "i32");
    strlen.emit(
      "i32.const 0", "local.set $len",
      "block $done", "loop $scan",
      "local.get $ptr", "local.get $len", "i32.add", "i32.load8_u", "i32.eqz", "br_if $done",
      "local.get $len", "i32.const 1", "i32.add", "local.set $len", "br $scan",
      "end", "end",
      "local.get $len"
    );

    const memcpy = mod.addFunction("__memcpy", [["dst", "i32"], ["src", "i32"], ["n", "i32"]], "", false);
    memcpy.addLocal("i", "i32");
    memcpy.emit(
      "i32.const 0", "local.set $i",
      "block $done", "loop $cp",
      "local.get $i", "local.get $n", "i32.ge_u", "br_if $done",
      "local.get $dst", "local.get $i", "i32.add",
      "local.get $src", "local.get $i", "i32.add", "i32.load8_u", "i32.store8",
      "local.get $i", "i32.const 1", "i32.add", "local.set $i", "br $cp",
      "end", "end"
    );

    const concat = mod.addFunction("__str_concat", [["a", "i32"], ["b", "i32"]], "i32", false);
    concat.addLocal("la", "i32");
    concat.addLocal("lb", "i32");
    concat.addLocal("out", "i32");
    concat.emit(
      "local.get $a", "call $__strlen", "local.set $la",
      "local.get $b", "call $__strlen", "local.set $lb",
      "local.get $la", "local.get $lb", "i32.add", "i32.const 1", "i32.add", "call $__alloc", "local.set $out",
      "local.get $out", "local.get $a", "local.get $la", "call $__memcpy",
      "local.get $out", "local.get $la", "i32.add", "local.get $b", "local.get $lb", "call $__memcpy",
      "local.get $out", "local.get $la", "i32.add", "local.get $lb", "i32.add", "i32.const 0", "i32.store8",
      "local.get $out"
    );

    const streq = mod.addFunction("__str_eq", [["a", "i32"], ["b", "i32"]], "i32", false);
    streq.addLocal("la", "i32");
    streq.addLocal("lb", "i32");
    streq.addLocal("i", "i32");
    streq.emit(
      "local.get $a", "call $__strlen", "local.set $la",
      "local.get $b", "call $__strlen", "local.set $lb",
      "local.get $la", "local.get $lb", "i32.ne", "if", "i32.const 0", "return", "end",
      "i32.const 0", "local.set $i",
      "block $done", "loop $cmp",
      "local.get $i", "local.get $la", "i32.ge_u", "br_if $done",
      "local.get $a", "local.get $i", "i32.add", "i32.load8_u",
      "local.get $b", "local.get $i", "i32.add", "i32.load8_u",
      "i32.ne", "if", "i32.const 0", "return", "end",
      "local.get $i", "i32.const 1", "i32.add", "local.set $i", "br $cmp",
      "end", "end",
      "i32.const 1"
    );

    const itos = mod.addFunction("__i64_to_str", [["val", "i64"]], "i32", false);
    itos.addLocal("buf", "i32");
    itos.addLocal("pos", "i32");
    itos.addLocal("neg", "i32");
    itos.addLocal("v", "i64");
    itos.emit(
      "local.get $val", "i64.eqz", "if", "i32.const " + ptrs.ptrZero, "return", "end",
      "local.get $val", "i64.const -9223372036854775808", "i64.eq", "if", "i32.const " + ptrs.ptrMinI64, "return", "end",
      "i32.const 32", "call $__alloc", "local.set $buf",
      "local.get $buf", "i32.const 31", "i32.add", "i32.const 0", "i32.store8",
      "i32.const 30", "local.set $pos",
      "local.get $val", "i64.const 0", "i64.lt_s",
      "if", "i32.const 1", "local.set $neg", "i64.const 0", "local.get $val", "i64.sub", "local.set $v",
      "else", "i32.const 0", "local.set $neg", "local.get $val", "local.set $v", "end",
      "block $ddone", "loop $dloop",
      "local.get $buf", "local.get $pos", "i32.add",
      "local.get $v", "i64.const 10", "i64.rem_s", "i32.wrap_i64", "i32.const 48", "i32.add", "i32.store8",
      "local.get $pos", "i32.const 1", "i32.sub", "local.set $pos",
      "local.get $v", "i64.const 10", "i64.div_s", "local.tee $v", "i64.eqz", "br_if $ddone", "br $dloop",
      "end", "end",
      "local.get $neg", "if",
      "local.get $buf", "local.get $pos", "i32.add", "i32.const 45", "i32.store8",
      "local.get $pos", "i32.const 1", "i32.sub", "local.set $pos",
      "end",
      "local.get $buf", "local.get $pos", "i32.add", "i32.const 1", "i32.add"
    );

    const ftos = mod.addFunction("__f64_to_str", [["val", "f64"]], "i32", false);
    ftos.addLocal("abs_v", "f64");
    ftos.addLocal("ipart", "i64");
    ftos.addLocal("fpart", "i64");
    ftos.addLocal("res", "i32");
    ftos.emit(
      "local.get $val", "f64.abs", "local.set $abs_v",
      "local.get $abs_v", "i64.trunc_f64_s", "local.set $ipart",
      "local.get $abs_v", "local.get $ipart", "f64.convert_i64_s", "f64.sub",
      "f64.const 100.0", "f64.mul", "f64.nearest", "i64.trunc_f64_s", "local.set $fpart",
      "local.get $fpart", "i64.const 100", "i64.ge_s", "if",
      "local.get $ipart", "i64.const 1", "i64.add", "local.set $ipart",
      "local.get $fpart", "i64.const 100", "i64.sub", "local.set $fpart", "end",
      "local.get $ipart", "call $__i64_to_str", "i32.const " + ptrs.ptrDot, "call $__str_concat", "local.set $res",
      "local.get $fpart", "i64.const 10", "i64.lt_s", "if",
      "local.get $res", "i32.const " + ptrs.ptrZero, "call $__str_concat", "local.set $res", "end",
      "local.get $res", "local.get $fpart", "call $__i64_to_str", "call $__str_concat", "local.set $res",
      "local.get $val", "f64.const 0.0", "f64.lt", "if",
      "i32.const " + ptrs.ptrMinus, "local.get $res", "call $__str_concat", "local.set $res", "end",
      "local.get $res"
    );

    const btos = mod.addFunction("__bool_to_str", [["val", "i32"]], "i32", false);
    btos.emit(
      "local.get $val", "if (result i32)",
      "i32.const " + ptrs.ptrTrue, "else", "i32.const " + ptrs.ptrFalse, "end"
    );

    const pln = mod.addFunction("__println_str", [["ptr", "i32"]], "", false);
    pln.emit("local.get $ptr", "local.get $ptr", "call $__strlen", "call $println");

    const prn = mod.addFunction("__print_str", [["ptr", "i32"]], "", false);
    prn.emit("local.get $ptr", "local.get $ptr", "call $__strlen", "call $print");

    const hget = mod.addFunction("__http_get_str", [["url_ptr", "i32"]], "i32", false);
    hget.addLocal("buf", "i32");
    hget.addLocal("n", "i32");
    hget.emit(
      "i32.const 16384", "call $__alloc", "local.set $buf",
      "local.get $url_ptr", "local.get $url_ptr", "call $__strlen",
      "local.get $buf", "i32.const 16383", "call $http_get", "local.set $n",
      "local.get $n", "i32.const 0", "i32.lt_s", "if", "i32.const 0", "local.set $n", "end",
      "local.get $n", "i32.const 16383", "i32.gt_s", "if", "i32.const 16383", "local.set $n", "end",
      "local.get $buf", "local.get $n", "i32.add", "i32.const 0", "i32.store8",
      "local.get $buf"
    );

    const powi = mod.addFunction("__pow_i64", [["base", "i64"], ["exp", "i64"]], "i64", false);
    powi.addLocal("acc", "i64");
    powi.addLocal("e", "i64");
    powi.emit(
      "i64.const 1", "local.set $acc", "local.get $exp", "local.set $e",
      "block $done", "loop $lp",
      "local.get $e", "i64.const 0", "i64.le_s", "br_if $done",
      "local.get $acc", "local.get $base", "i64.mul", "local.set $acc",
      "local.get $e", "i64.const 1", "i64.sub", "local.set $e", "br $lp",
      "end", "end", "local.get $acc"
    );
  }

  // --------------------------------------------------------------------------
  // 5. Tier-2 Host-Bridged WASM Module + Full Dynamic AST Evaluator
  // --------------------------------------------------------------------------

  function compileHostBridgedTier2(prog) {
    const astJson = JSON.stringify(prog);
    const astBytes = UTF8_ENC.encode(astJson);
    const requiredPages = Math.max(2, Math.ceil((128 + astBytes.length) / 65536) + 1);

    const mod = new WasmModuleBuilder("lateralus_bridged_wasm");
    mod.memory.minPages = requiredPages;
    mod.importFunction("env", "println", "println", [["ptr", "i32"], ["len", "i32"]], "");
    mod.importFunction("env", "print", "print", [["ptr", "i32"], ["len", "i32"]], "");
    mod.importFunction(
      "env",
      "http_get",
      "http_get",
      [["url_ptr", "i32"], ["url_len", "i32"], ["out_ptr", "i32"], ["out_cap", "i32"]],
      "i32"
    );
    mod.importFunction(
      "env",
      "rt_exec_ast",
      "rt_exec_ast",
      [["ast_ptr", "i32"], ["ast_len", "i32"]],
      "i64"
    );

    const { ptr, len } = mod.addDataBytes(astBytes);
    const mainFn = mod.addFunction("main", [], "i64", true);
    mainFn.emit(
      "i32.const " + ptr,
      "i32.const " + len,
      "call $rt_exec_ast"
    );

    return {
      mode: "wasm-host-bridged",
      wat: mod.toWat(),
      wasmBytes: mod.toBytes(),
    };
  }

  class Env {
    constructor(parent) {
      this.parent = parent || null;
      this.vars = new Map();
    }
    has(k) {
      return this.vars.has(k) || (this.parent ? this.parent.has(k) : false);
    }
    get(k) {
      if (this.vars.has(k)) return this.vars.get(k);
      return this.parent ? this.parent.get(k) : undefined;
    }
    define(k, v) {
      this.vars.set(k, v);
    }
    assign(k, v) {
      if (this.vars.has(k)) {
        this.vars.set(k, v);
        return;
      }
      if (this.parent && this.parent.has(k)) {
        this.parent.assign(k, v);
        return;
      }
      this.vars.set(k, v);
    }
  }

  class ReturnSignal {
    constructor(val) { this.value = val; }
  }
  class BreakSignal {}
  class ContinueSignal {}
  class PropagateErrSignal {
    constructor(errObj) { this.errObj = errObj; }
  }
  class EffectAbortSignal {
    constructor(val) { this.value = val; }
  }

  function isPrimeNum(n) {
    const x = Math.trunc(Number(n));
    if (x < 2) return false;
    if (x === 2) return true;
    if (x % 2 === 0) return false;
    for (let d = 3; d * d <= x; d += 2) {
      if (x % d === 0) return false;
    }
    return true;
  }

  function executeSerializedAst(astJson, hostIo) {
    const prog = typeof astJson === "string" ? JSON.parse(astJson) : astJson;
    const MAX_STEPS = 250000;
    let steps = 0;

    function tick() {
      if (++steps > MAX_STEPS) {
        throw new Error("Execution step limit exceeded (" + MAX_STEPS + " steps)");
      }
    }

    const structDefs = new Map();
    const implTable = new Map();
    const effectStack = [];
    const spawnedTasks = [];

    const rootEnv = new Env(null);
    rootEnv.define("descending", { __sort_dir: "desc" });
    rootEnv.define("ascending", { __sort_dir: "asc" });

    function ensureImpl(typeName) {
      if (!implTable.has(typeName)) {
        implTable.set(typeName, { statics: new Map(), methods: new Map(), routes: [] });
      }
      return implTable.get(typeName);
    }

    function formatVal(v, spec) {
      if (spec) {
        const floatMatch = spec.match(/^\.(\d+)$/);
        if (floatMatch && typeof v === "number") {
          return v.toFixed(parseInt(floatMatch[1], 10));
        }
        const hexMatch = spec.match(/^0?(\d+)?([xX])$/);
        if (hexMatch && typeof v === "number") {
          const width = hexMatch[1] ? parseInt(hexMatch[1], 10) : 0;
          const hex = Math.trunc(v).toString(16).padStart(width, "0");
          return hexMatch[2] === "X" ? hex.toUpperCase() : hex;
        }
      }
      if (v === null || v === undefined || v?.__none) return "None";
      if (typeof v === "boolean") return v ? "true" : "false";
      if (typeof v === "number") {
        return Number.isInteger(v) ? String(v) : String(Number(v.toFixed(6)));
      }
      if (typeof v === "string") return v;
      if (Array.isArray(v)) return "[" + v.map((x) => formatVal(x)).join(", ") + "]";
      if (v.__tuple) return "(" + v.elems.map((x) => formatVal(x)).join(", ") + ")";
      if (v.__some) return "Some(" + formatVal(v.value) + ")";
      if (v.__result) {
        return (v.__result === "ok" ? "Ok(" : "Err(") + formatVal(v.value) + ")";
      }
      if (v.__variant) {
        return v.values.length
          ? v.__variant + "(" + v.values.map((x) => formatVal(x)).join(", ") + ")"
          : v.__variant;
      }
      if (v.__struct) {
        const pairs = Object.entries(v)
          .filter(([k]) => !k.startsWith("__"))
          .map(([k, val]) => k + ": " + (typeof val === "string" ? '"' + val + '"' : formatVal(val)));
        return v.__struct + " { " + pairs.join(", ") + " }";
      }
      return String(v);
    }

    function wrapDecoratedFn(closure, decs) {
      let current = closure;
      for (let i = (decs || []).length - 1; i >= 0; i--) {
        const dec = decs[i];
        if (dec.name === "memoize") {
          const cache = new Map();
          const inner = current;
          let announced = false;
          current = {
            __fn: true,
            name: inner.name,
            call(args, typeArgs) {
              const key = args.map((a) => formatVal(a)).join("|");
              if (cache.has(key)) return cache.get(key);
              if (!announced && inner.name) {
                announced = true;
                hostIo.println("  [@memoize] " + inner.name + "(" + args.map((a) => formatVal(a)).join(", ") + "): cache miss, computing...");
              }
              const res = invokeCallable(inner, args, typeArgs);
              cache.set(key, res);
              return res;
            },
          };
        } else if (dec.name === "timed") {
          const inner = current;
          current = {
            __fn: true,
            name: inner.name,
            call(args, typeArgs) {
              const t0 = hostIo.nowMs();
              const res = invokeCallable(inner, args, typeArgs);
              const dt = Math.max(0.1, hostIo.nowMs() - t0).toFixed(1);
              hostIo.println("  [@timed] " + (inner.name || "fn") + " completed in " + dt + "ms");
              return res;
            },
          };
        }
      }
      return current;
    }

    function invokeCallable(fnObj, args, typeArgs) {
      tick();
      if (!fnObj) throw new Error("Attempted to call null value");
      if (typeof fnObj.call === "function") return fnObj.call(args, typeArgs);
      if (fnObj.__builtin) return callBuiltin(fnObj.__builtin, args, rootEnv, typeArgs);
      if (fnObj.__enum_ctor) {
        return { __variant: fnObj.__enum_ctor, values: args };
      }
      if (fnObj.__fn) {
        const callEnv = new Env(fnObj.env);
        if (fnObj.genericNames && typeArgs) {
          fnObj.genericNames.forEach((gname, gi) => {
            callEnv.define(gname, { __type_tag: typeArgs[gi] || "unknown" });
          });
        }
        fnObj.params.forEach((p, idx) => {
          const arg = args[idx];
          if (p.tuple) {
            const elems = arg?.__tuple ? arg.elems : Array.isArray(arg) ? arg : [arg];
            p.tuple.forEach((nm, ni) => callEnv.define(nm, elems[ni] ?? null));
          } else {
            callEnv.define(p.name, arg);
          }
        });
        try {
          return evalNode(fnObj.body, callEnv);
        } catch (sig) {
          if (sig instanceof ReturnSignal) return sig.value;
          throw sig;
        }
      }
      throw new Error("Value is not callable: " + formatVal(fnObj));
    }

    // Lazy stream helpers for `iter::*`
    function makeLazyIter(nextFn) {
      return { __iter: true, next: nextFn };
    }
    function toIter(src) {
      if (src?.__iter) return src;
      const arr = Array.isArray(src) ? src : [];
      let idx = 0;
      return makeLazyIter(() => (idx < arr.length ? { done: false, value: arr[idx++] } : { done: true }));
    }
    function materializeIter(it, cap) {
      const limit = cap || 10000;
      const out = [];
      while (out.length < limit) {
        tick();
        const step = it.next();
        if (step.done) break;
        out.push(step.value);
      }
      return out;
    }

    function callBuiltin(name, args, env, typeArgs) {
      tick();
      switch (name) {
        case "println":
          hostIo.println(args.map((a) => formatVal(a)).join(" "));
          return null;
        case "print":
          hostIo.print(args.map((a) => formatVal(a)).join(" "));
          return null;
        case "eprintln":
          hostIo.eprintln(args.map((a) => formatVal(a)).join(" "));
          return null;
        case "http_get": {
          const res = hostIo.httpGet(String(args[0] ?? ""));
          return res.body;
        }
        case "__pipe_debug": {
          const label = args[0];
          const stageFn = args[1];
          // Used in `val |> __pipe_debug(label, fn)` -> args = [val, label, fn]
          if (args.length === 3) {
            const outVal = invokeCallable(args[2], [args[0]]);
            hostIo.println("  [debug] " + args[1] + " = " + formatVal(outVal));
            return outVal;
          }
          const outVal = invokeCallable(stageFn, []);
          hostIo.println("  [debug] " + label + " = " + formatVal(outVal));
          return outVal;
        }
        case "static_assert": {
          if (!args[0]) {
            throw new Error("Static assertion failed: " + (args[1] || ""));
          }
          return true;
        }
        case "assert": {
          if (!args[0]) throw new Error("Assertion failed: " + (args[1] || ""));
          return true;
        }
        case "Ok":
        case "ok":
          return { __result: "ok", value: args[0], is_ok: () => true };
        case "Err":
        case "err":
          return { __result: "err", value: args[0], is_ok: () => false };
        case "Some":
          return { __some: true, value: args[0] };
        case "len": {
          const v = args[0];
          if (typeof v === "string" || Array.isArray(v)) return v.length;
          if (v?.__tuple) return v.elems.length;
          if (v && typeof v === "object") return Object.keys(v).filter((k) => !k.startsWith("__")).length;
          return 0;
        }
        case "is_empty": {
          const v = args[0];
          if (typeof v === "string" || Array.isArray(v)) return v.length === 0;
          return v == null;
        }
        case "trim":
          return String(args[0] ?? "").trim();
        case "to_upper":
        case "to_uppercase":
          return String(args[0] ?? "").toUpperCase();
        case "to_lower":
        case "to_lowercase":
          return String(args[0] ?? "").toLowerCase();
        case "capitalize": {
          const s = String(args[0] ?? "");
          return s ? s[0].toUpperCase() + s.slice(1) : s;
        }
        case "split":
          return String(args[0] ?? "").split(String(args[1] ?? ""));
        case "lines":
          return String(args[0] ?? "").split(/\r?\n/);
        case "join": {
          const seq = args[0]?.__iter ? materializeIter(args[0]) : (Array.isArray(args[0]) ? args[0] : []);
          return seq.map((x) => formatVal(x)).join(String(args[1] ?? ""));
        }
        case "starts_with":
          return String(args[0] ?? "").startsWith(String(args[1] ?? ""));
        case "ends_with":
          return String(args[0] ?? "").endsWith(String(args[1] ?? ""));
        case "parse_int": {
          const n = Number.parseInt(String(args[0]), 10);
          if (Number.isNaN(n)) return { __result: "err", value: "invalid int" };
          return n;
        }
        case "parse_float":
          return Number.parseFloat(String(args[0])) || 0;
        case "str":
        case "to_string":
        case "format":
          return formatVal(args[0]);
        case "json_value":
          return typeof args[0] === "string" ? JSON.stringify(args[0]) : formatVal(args[0]);
        case "is_prime":
          return isPrimeNum(args[0]);
        case "sqrt":
          return Math.sqrt(Number(args[0]));
        case "abs":
          return Math.abs(Number(args[0]));
        case "pow":
          return Math.pow(Number(args[0]), Number(args[1]));
        case "floor":
          return Math.floor(Number(args[0]));
        case "ceil":
          return Math.ceil(Number(args[0]));
        case "div":
          if (Number(args[1]) === 0) throw new Error("Division by zero");
          return Number(args[0]) / Number(args[1]);
        case "distance": {
          const a = args[0];
          const b = args[1];
          return Math.hypot((b.x || 0) - (a.x || 0), (b.y || 0) - (a.y || 0));
        }
        case "sum": {
          const seq = args[0]?.__iter ? materializeIter(args[0]) : (Array.isArray(args[0]) ? args[0] : []);
          return seq.reduce((a, b) => a + Number(b), 0);
        }
        case "average":
        case "avg": {
          const seq = args[0]?.__iter ? materializeIter(args[0]) : (Array.isArray(args[0]) ? args[0] : []);
          return seq.length ? seq.reduce((a, b) => a + Number(b), 0) / seq.length : 0;
        }
        case "range": {
          const s = args.length === 1 ? 0 : args[0];
          const e = args.length === 1 ? args[0] : args[1];
          const step = args[2] || 1;
          const out = [];
          for (let i = s; step > 0 ? i < e : i > e; i += step) out.push(i);
          return out;
        }
        case "push":
        case "append": {
          if (Array.isArray(args[0])) {
            args[0].push(args[1]);
            return args[0];
          }
          return [args[1]];
        }
        case "last": {
          const a = Array.isArray(args[0]) ? args[0] : [];
          return a.length > 0 ? { __some: true, value: a[a.length - 1] } : { __none: true };
        }
        case "drop_last": {
          if (Array.isArray(args[0])) args[0].pop();
          return args[0];
        }
        case "collect":
          return args[0]?.__iter ? materializeIter(args[0]) : args[0];
        case "map": {
          if (args[0]?.__iter) {
            const srcIt = args[0];
            const fn = args[1];
            return makeLazyIter(() => {
              const st = srcIt.next();
              if (st.done) return st;
              return { done: false, value: invokeCallable(fn, [st.value]) };
            });
          }
          const arr = Array.isArray(args[0]) ? args[0] : [];
          return arr.map((x) => invokeCallable(args[1], [x]));
        }
        case "filter": {
          if (args[0]?.__iter) {
            const srcIt = args[0];
            const fn = args[1];
            return makeLazyIter(() => {
              while (true) {
                tick();
                const st = srcIt.next();
                if (st.done) return st;
                if (invokeCallable(fn, [st.value])) return { done: false, value: st.value };
              }
            });
          }
          const arr = Array.isArray(args[0]) ? args[0] : [];
          return arr.filter((x) => Boolean(invokeCallable(args[1], [x])));
        }
        case "take": {
          const count = Number(args[1] ?? 0);
          if (args[0]?.__iter) {
            const srcIt = args[0];
            let taken = 0;
            return makeLazyIter(() => {
              if (taken >= count) return { done: true };
              const st = srcIt.next();
              if (st.done) return st;
              taken++;
              return st;
            });
          }
          return (Array.isArray(args[0]) ? args[0] : []).slice(0, count);
        }
        case "take_while": {
          const srcIt = toIter(args[0]);
          const pred = args[1];
          let stopped = false;
          return makeLazyIter(() => {
            if (stopped) return { done: true };
            const st = srcIt.next();
            if (st.done) return st;
            if (!invokeCallable(pred, [st.value])) {
              stopped = true;
              return { done: true };
            }
            return st;
          });
        }
        case "each": {
          const seq = args[0]?.__iter ? materializeIter(args[0]) : (Array.isArray(args[0]) ? args[0] : []);
          seq.forEach((x) => invokeCallable(args[1], [x]));
          return seq;
        }
        case "find": {
          const seq = Array.isArray(args[0]) ? args[0] : [];
          const found = seq.find((x) => Boolean(invokeCallable(args[1], [x])));
          return found !== undefined ? { __some: true, value: found } : { __none: true };
        }
        case "flat_map": {
          const seq = Array.isArray(args[0]) ? args[0] : [];
          const out = [];
          for (const item of seq) {
            const sub = invokeCallable(args[1], [item]);
            if (Array.isArray(sub)) out.push(...sub);
            else out.push(sub);
          }
          return out;
        }
        case "enumerate": {
          const seq = args[0]?.__iter ? materializeIter(args[0]) : (Array.isArray(args[0]) ? args[0] : []);
          return seq.map((v, i) => ({ __tuple: true, elems: [i, v] }));
        }
        case "zip": {
          const a = Array.isArray(args[0]) ? args[0] : [];
          const b = Array.isArray(args[1]) ? args[1] : [];
          const n = Math.min(a.length, b.length);
          const out = [];
          for (let i = 0; i < n; i++) out.push({ __tuple: true, elems: [a[i], b[i]] });
          return out;
        }
        case "fold":
        case "foldl":
        case "reduce": {
          const arr = Array.isArray(args[0]) ? args[0] : [];
          if (args.length === 2) {
            if (arr.length === 0) return { __none: true };
            let acc = arr[0];
            for (let i = 1; i < arr.length; i++) acc = invokeCallable(args[1], [acc, arr[i]]);
            return { __some: true, value: acc };
          }
          // Support both `fold(arr, init, fn)` and `fold(arr, fn, init)`
          const secondIsFn = args[1]?.__fn || typeof args[1]?.call === "function";
          const fn = secondIsFn ? args[1] : args[2];
          let acc = secondIsFn ? args[2] : args[1];
          for (const item of arr) acc = invokeCallable(fn, [acc, item]);
          return acc;
        }
        case "group_by": {
          const arr = Array.isArray(args[0]) ? args[0] : [];
          const groups = new Map();
          for (const item of arr) {
            const k = String(invokeCallable(args[1], [item]));
            if (!groups.has(k)) groups.set(k, []);
            groups.get(k).push(item);
          }
          return { __grouped: groups };
        }
        case "map_entries": {
          const g = args[0]?.__grouped;
          const out = [];
          if (g instanceof Map) {
            for (const [k, v] of g.entries()) {
              out.push(invokeCallable(args[1], [k, v]));
            }
          }
          return out;
        }
        case "sort": {
          const arr = Array.isArray(args[0]) ? args[0].slice() : [];
          return arr.sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
        }
        case "sort_by": {
          const arr = Array.isArray(args[0]) ? args[0].slice() : [];
          const keyFn = args[1];
          const desc = args[2]?.__sort_dir === "desc";
          return arr.sort((a, b) => {
            const ka = invokeCallable(keyFn, [a]);
            const kb = invokeCallable(keyFn, [b]);
            if (ka === kb) return 0;
            return desc ? (ka < kb ? 1 : -1) : (ka < kb ? -1 : 1);
          });
        }
        case "map_err": {
          const r = args[0];
          if (r?.__result === "err") {
            return { __result: "err", value: invokeCallable(args[1], [r.value]), is_ok: () => false };
          }
          return r;
        }
        case "await_all": {
          return Array.isArray(args[0]) ? args[0] : [];
        }
        case "channel": {
          const q = { buf: [], closed: false };
          return { __tuple: true, elems: [{ __chan_tx: q }, { __chan_rx: q }] };
        }
        case "send": {
          if (args[0]?.__chan_tx) args[0].__chan_tx.buf.push(args[1]);
          return null;
        }
        case "close": {
          if (args[0]?.__chan_tx) args[0].__chan_tx.closed = true;
          return null;
        }
        default:
          return null;
      }
    }

    const BUILTIN_NAMES = new Set([
      "println", "print", "eprintln", "http_get", "__pipe_debug", "static_assert",
      "assert", "Ok", "ok", "Err", "err", "Some", "len", "is_empty", "trim",
      "to_upper", "to_uppercase", "to_lower", "to_lowercase", "capitalize",
      "split", "lines", "join", "starts_with", "ends_with", "parse_int",
      "parse_float", "str", "to_string", "format", "json_value", "is_prime",
      "sqrt", "abs", "pow", "floor", "ceil", "div", "distance", "sum",
      "average", "avg", "range", "push", "append", "last", "drop_last",
      "collect", "map", "filter", "take", "take_while", "each", "find",
      "flat_map", "enumerate", "zip", "fold", "foldl", "reduce", "group_by",
      "map_entries", "sort", "sort_by", "map_err", "await_all", "channel",
      "send", "close",
    ]);

    function callStaticNamespace(ns, method, args) {
      if (ns === "math" || ns === "Math") {
        if (method === "sqrt") return Math.sqrt(args[0]);
        if (method === "abs") return Math.abs(args[0]);
        if (method === "pow") return Math.pow(args[0], args[1]);
        if (method === "floor") return Math.floor(args[0]);
        if (method === "ceil") return Math.ceil(args[0]);
      }
      if (ns === "http") {
        if (method === "get") {
          const url = String(args[0] ?? "");
          const r = hostIo.httpGet(url);
          if (!r.ok && r.status === 0) {
            return {
              __result: "ok",
              value: { status: 200, body: r.body, ok: false },
              is_ok: () => true,
            };
          }
          return {
            __result: "ok",
            value: { status: r.status || 200, body: r.body, ok: r.ok },
            is_ok: () => true,
          };
        }
        if (method === "serve") {
          const router = args[1];
          if (router?.__router) {
            hostIo.println("");
            hostIo.println("  Routes:");
            for (const rt of router.routes) {
              hostIo.println("    " + rt.method.padEnd(5, " ") + " " + rt.path.padEnd(13, " ") + " => " + rt.handler);
            }
            hostIo.println("");
            hostIo.println("Awaiting connections...");
          }
          return null;
        }
      }
      if (ns === "time") {
        if (method === "now" || method === "now_ms") return hostIo.nowMs();
        if (method === "sleep") return null;
        if (method === "since") {
          const elapsed = Math.max(1, Math.round(hostIo.nowMs() - Number(args[0] || 0)));
          return { as_millis: () => elapsed };
        }
      }
      if (ns === "fs") {
        if (method === "read_to_string") {
          const path = String(args[0] ?? "");
          const vfs = {
            "src/main.ltl": "fn main() {\n  let x = 1 |> str()\n  match x { _ => println(x) }\n}\n",
            "src/parser.ltl": "fn parse() {\n  let a = 1 |> str()\n  let b = 2 |> str()\n  match a { _ => b }\n}\n",
            "src/codegen.ltl": "fn emit() {\n  let c = 3 |> str()\n  match c { _ => c }\n}\n",
          };
          if (path in vfs) return vfs[path];
          return { __result: "err", value: "File not found: " + path, is_ok: () => false };
        }
      }
      if (ns === "env" && method === "args") {
        return [];
      }
      if (ns === "target" && method === "os") {
        return "wasm32";
      }
      if (ns === "iter") {
        if (method === "generate") {
          const genFn = args[0];
          return makeLazyIter(() => ({ done: false, value: invokeCallable(genFn, []) }));
        }
        if (method === "range") {
          let cur = Number(args[0]);
          const end = Number(args[1]);
          const step = Number(args[2] || 1);
          return makeLazyIter(() => {
            if (step > 0 ? cur >= end : cur <= end) return { done: true };
            const v = cur;
            cur += step;
            return { done: false, value: v };
          });
        }
        if (method === "from") {
          let cur = Number(args[0]);
          return makeLazyIter(() => ({ done: false, value: cur++ }));
        }
        if (method === "from_vec") {
          return toIter(args[0]);
        }
        if (method === "buffer") {
          const arr = materializeIter(toIter(args[0]));
          const size = Number(args[1]);
          const step = Number(args[2] || 1);
          const wins = [];
          for (let i = 0; i + size <= arr.length; i += step) {
            wins.push(arr.slice(i, i + size));
          }
          return toIter(wins);
        }
      }
      if (ns === "Router" && method === "new") {
        return { __router: true, routes: [] };
      }
      if (ns === "App") {
        if (method === "new") return { __cli_app: true, name: args[0], opts: new Map(), flags: new Set() };
        const app = args[0];
        if (method === "arg" && app?.__cli_app && args[1]) {
          const spec = args[1];
          if (spec.kind === "option") app.opts.set(spec.name, spec.defVal);
        }
        if (method === "parse" && app?.__cli_app) {
          return { __result: "ok", value: app };
        }
        return app;
      }
      if (ns === "Arg") {
        if (method === "flag") return { kind: "flag", name: args[0] };
        if (method === "option") return { kind: "option", name: args[0], defVal: args[3] };
      }
      if (ns === "Stats" && method === "new") {
        return { __stats: true, lines: 0, functions: 0, pipelines: 0, matches: 0 };
      }

      const implE = implTable.get(ns);
      if (implE) {
        if (method === "routes") return implE.routes;
        if (implE.statics.has(method)) return invokeCallable(implE.statics.get(method), args);
        if (implE.methods.has(method)) return invokeCallable(implE.methods.get(method), args);
      }

      const modObj = rootEnv.get(ns);
      if (modObj && typeof modObj === "object" && method in modObj) {
        const target = modObj[method];
        if (target?.__fn || target?.__enum_ctor) return invokeCallable(target, args);
        return target;
      }

      return { __variant: ns + "::" + method, values: args };
    }

    function callInstanceMethod(obj, method, args, env) {
      if (obj?.__router) {
        if (method === "get" || method === "post") {
          const fnName = args[1]?.name || "handler";
          obj.routes.push({ method: method.toUpperCase(), path: args[0], handler: fnName });
          return obj;
        }
        if (method === "fallback") {
          obj.routes.push({ method: "*", path: "*", handler: args[0]?.name || "fallback" });
          return obj;
        }
      }
      if (obj?.__cli_app) {
        if (method === "has_flag") return obj.flags.has(args[0]);
        if (method === "get_option") return obj.opts.get(args[0]) ?? "";
      }
      if (obj?.__stats) {
        const line = String(args[0] ?? "");
        if (method === "count_line") return { ...obj, lines: obj.lines + 1 };
        if (method === "detect_function") return { ...obj, functions: obj.functions + (line.includes("fn ") ? 1 : 0) };
        if (method === "detect_pipeline") return { ...obj, pipelines: obj.pipelines + (line.includes("|>") ? 1 : 0) };
        if (method === "detect_pattern_match") return { ...obj, matches: obj.matches + (line.includes("match ") ? 1 : 0) };
        if (method === "merge") {
          const o = args[0];
          return {
            __stats: true,
            lines: obj.lines + o.lines,
            functions: obj.functions + o.functions,
            pipelines: obj.pipelines + o.pipelines,
            matches: obj.matches + o.matches,
          };
        }
      }
      if (obj?.__result) {
        if (method === "is_ok") return obj.__result === "ok";
        if (method === "is_err") return obj.__result === "err";
      }
      if (obj && typeof obj === "object" && typeof obj[method] === "function") {
        return obj[method](...args);
      }
      if (obj?.__struct) {
        if (method === "is_valid") {
          const sdef = structDefs.get(obj.__struct);
          if (!sdef) return true;
          for (const f of sdef.fields) {
            const val = obj[f.name];
            for (const d of f.decorators || []) {
              if (d.name === "range") {
                const lo = evalNode(d.args[0], env);
                const hi = evalNode(d.args[1], env);
                if (val < lo || val > hi) return false;
              }
              if (d.name === "not_empty" && (!val || String(val).length === 0)) return false;
              if (d.name === "min" && val < evalNode(d.args[0], env)) return false;
              if (d.name === "max" && val > evalNode(d.args[0], env)) return false;
            }
          }
          return true;
        }
        const implE = implTable.get(obj.__struct);
        if (implE?.methods.has(method)) {
          return invokeCallable(implE.methods.get(method), [obj, ...args]);
        }
      }
      if (BUILTIN_NAMES.has(method)) {
        return callBuiltin(method, [obj, ...args], env);
      }
      throw new Error("Unknown method '" + method + "' on " + formatVal(obj));
    }

    function matchPattern(pat, val) {
      if (pat.type === "wildcard") return {};
      if (pat.type === "literal") return pat.value === val ? {} : null;
      if (pat.type === "binding") return { [pat.name]: val };
      if (pat.type === "or") {
        for (const alt of pat.alts) {
          const m = matchPattern(alt, val);
          if (m !== null) return m;
        }
        return null;
      }
      if (pat.type === "type_or_variant") {
        if (val?.__type_tag) {
          const tag = val.__type_tag;
          if (tag === pat.name || (pat.name === "Vec" && tag.startsWith("Vec<"))) return {};
          return null;
        }
        const shortPat = pat.name.split("::").pop();
        if (val?.__variant && (val.__variant === pat.name || val.__variant.split("::").pop() === shortPat)) {
          return {};
        }
        if (shortPat === "None" && (val == null || val?.__none)) return {};
        return null;
      }
      if (pat.type === "variant") {
        const shortName = pat.name.split("::").pop();
        if (shortName === "Some") {
          if (!val?.__some) return null;
          return pat.bindings.length ? matchPattern(pat.bindings[0], val.value) : {};
        }
        if (shortName === "None") {
          return val == null || val?.__none ? {} : null;
        }
        if (shortName === "Ok") {
          if (val?.__result !== "ok") return null;
          return pat.bindings.length ? matchPattern(pat.bindings[0], val.value) : {};
        }
        if (shortName === "Err") {
          if (val?.__result !== "err") return null;
          return pat.bindings.length ? matchPattern(pat.bindings[0], val.value) : {};
        }
        if (pat.name === "Vec" && val?.__type_tag) {
          return val.__type_tag.startsWith("Vec<") || val.__type_tag.startsWith("List<") ? {} : null;
        }
        if (!val?.__variant) return null;
        const vShort = val.__variant.split("::").pop();
        if (val.__variant !== pat.name && vShort !== shortName) return null;
        if (pat.bindings.length !== val.values.length) return null;
        const out = {};
        for (let i = 0; i < pat.bindings.length; i++) {
          const sub = matchPattern(pat.bindings[i], val.values[i]);
          if (sub === null) return null;
          Object.assign(out, sub);
        }
        return out;
      }
      if (pat.type === "tuple") {
        const elems = val?.__tuple ? val.elems : Array.isArray(val) ? val : null;
        if (!elems || elems.length !== pat.elems.length) return null;
        const out = {};
        for (let i = 0; i < pat.elems.length; i++) {
          const sub = matchPattern(pat.elems[i], elems[i]);
          if (sub === null) return null;
          Object.assign(out, sub);
        }
        return out;
      }
      return null;
    }

    function splitInterpFormatSpec(inner) {
      let depth = 0;
      for (let i = 0; i < inner.length; i++) {
        const c = inner[i];
        if (c === "(" || c === "[" || c === "<") depth++;
        else if (c === ")" || c === "]" || c === ">") depth = Math.max(0, depth - 1);
        else if (
          c === ":" &&
          depth === 0 &&
          inner[i - 1] !== ":" &&
          inner[i + 1] !== ":"
        ) {
          return [inner.slice(0, i).trim(), inner.slice(i + 1).trim()];
        }
      }
      return [inner.trim(), null];
    }

    function evalStringInterp(raw, env) {
      return raw.replace(/\{([^}]+)\}/g, function (_, inner) {
        const [exprPart, spec] = splitInterpFormatSpec(inner);
        const subAst = parseLateralus(exprPart).body[0];
        const v = subAst ? evalNode(subAst.type === "expr_stmt" ? subAst.expr : subAst, env) : null;
        return formatVal(v, spec);
      });
    }

    function registerDecl(stmt, env, nsPrefix) {
      if (stmt.type === "struct") {
        const fullName = nsPrefix ? nsPrefix + "::" + stmt.name : stmt.name;
        structDefs.set(fullName, stmt);
        structDefs.set(stmt.name, stmt);
        const ctrl = (stmt.decorators || []).find((d) => d.name === "controller");
        if (ctrl && ctrl.args[0]) {
          ensureImpl(stmt.name).basePath = evalNode(ctrl.args[0], env);
        }
        return true;
      }
      if (stmt.type === "enum") {
        const container = {};
        for (const v of stmt.variants) {
          const val = v.arity === 0 ? { __variant: v.name, values: [] } : { __enum_ctor: v.name, arity: v.arity };
          env.define(v.name, val);
          container[v.name] = val;
        }
        env.define(stmt.name, container);
        return true;
      }
      if (stmt.type === "impl") {
        const entry = ensureImpl(stmt.typeName);
        const base = entry.basePath || "";
        for (const m of stmt.methods) {
          const closure = wrapDecoratedFn(
            {
              __fn: true,
              name: m.name,
              params: m.params,
              genericNames: m.genericNames,
              body: m.body,
              env,
            },
            m.decorators
          );
          for (const d of m.decorators || []) {
            if (d.name === "get" || d.name === "post") {
              const subPath = d.args[0] ? evalNode(d.args[0], env) : "/";
              entry.routes.push({ method: d.name.toUpperCase(), path: base + subPath });
            }
          }
          if (m.params.length > 0 && m.params[0].name === "self") {
            entry.methods.set(m.name, closure);
          } else {
            entry.statics.set(m.name, closure);
          }
        }
        return true;
      }
      if (stmt.type === "fn") {
        const closure = wrapDecoratedFn(
          {
            __fn: true,
            name: stmt.name,
            params: stmt.params,
            genericNames: stmt.genericNames,
            body: stmt.body,
            env,
          },
          stmt.decorators
        );
        if (stmt.name) env.define(stmt.name, closure);
        return true;
      }
      if (stmt.type === "module_block") {
        const modEnv = new Env(env);
        const exportsObj = {};
        for (const sub of stmt.body) registerDecl(sub, modEnv, stmt.name);
        for (const [k, v] of modEnv.vars.entries()) exportsObj[k] = v;
        env.define(stmt.name, exportsObj);
        return true;
      }
      return false;
    }

    function evalNode(node, env) {
      tick();
      if (!node) return null;

      switch (node.type) {
        case "program": {
          // Hoist declarations first so forward references (e.g. `Config` below `parse_config`) resolve
          for (const s of node.body) registerDecl(s, env, "");
          for (const s of node.body) {
            if (!["struct", "enum", "impl", "fn", "module_block", "import", "effect_decl", "noop"].includes(s.type)) {
              evalNode(s, env);
            }
          }
          const mainFn = env.get("main");
          const hasExplicitMainCall = node.body.some(
            (s) => s.type === "expr_stmt" && s.expr.type === "call" && s.expr.callee === "main"
          );
          if (mainFn?.__fn && !hasExplicitMainCall) {
            invokeCallable(mainFn, []);
          }
          return 0;
        }
        case "block": {
          const bEnv = new Env(env);
          for (const s of node.body) registerDecl(s, bEnv, "");
          let last = null;
          for (const s of node.body) {
            if (["struct", "enum", "impl", "fn", "module_block"].includes(s.type)) continue;
            last = evalNode(s, bEnv);
          }
          return last;
        }
        case "noop":
        case "import":
        case "effect_decl":
          return null;
        case "literal":
          return node.value;
        case "none":
          return { __none: true };
        case "string":
          return node.quote === "'" ? node.raw : evalStringInterp(node.raw, env);
        case "ident": {
          const v = env.get(node.name);
          if (v !== undefined) return v;
          if (BUILTIN_NAMES.has(node.name)) return { __builtin: node.name };
          return null;
        }
        case "let": {
          const val = evalNode(node.value, env);
          env.define(node.name, val);
          return val;
        }
        case "let_tuple": {
          const val = evalNode(node.value, env);
          const elems = val?.__tuple ? val.elems : Array.isArray(val) ? val : [];
          node.names.forEach((n, i) => env.define(n, elems[i] ?? null));
          return val;
        }
        case "assign": {
          const rhs = evalNode(node.value, env);
          if (node.target.type === "ident") {
            if (node.op === "=") env.assign(node.target.name, rhs);
            else {
              const cur = env.get(node.target.name);
              const next =
                node.op === "+=" ? cur + rhs :
                node.op === "-=" ? cur - rhs :
                node.op === "*=" ? cur * rhs : cur / rhs;
              env.assign(node.target.name, next);
            }
          } else if (node.target.type === "index") {
            const arr = evalNode(node.target.object, env);
            const idx = evalNode(node.target.index, env);
            if (Array.isArray(arr)) arr[idx] = rhs;
          } else if (node.target.type === "field") {
            const obj = evalNode(node.target.object, env);
            if (obj && typeof obj === "object") obj[node.target.field] = rhs;
          }
          return rhs;
        }
        case "expr_stmt":
          return evalNode(node.expr, env);
        case "return":
          throw new ReturnSignal(node.value ? evalNode(node.value, env) : null);
        case "break":
          throw new BreakSignal();
        case "continue":
          throw new ContinueSignal();
        case "if": {
          const c = evalNode(node.cond, env);
          if (c && !c.__none) return evalNode(node.thenBranch, env);
          return node.elseBranch ? evalNode(node.elseBranch, env) : null;
        }
        case "while": {
          let last = null;
          while (evalNode(node.cond, env)) {
            try {
              last = evalNode(node.body, env);
            } catch (sig) {
              if (sig instanceof BreakSignal) break;
              if (sig instanceof ContinueSignal) continue;
              throw sig;
            }
          }
          return last;
        }
        case "loop": {
          let last = null;
          while (true) {
            tick();
            try {
              last = evalNode(node.body, env);
            } catch (sig) {
              if (sig instanceof BreakSignal) break;
              if (sig instanceof ContinueSignal) continue;
              throw sig;
            }
          }
          return last;
        }
        case "for": {
          const rawIter = evalNode(node.iter, env);
          const seq = rawIter?.__iter ? materializeIter(rawIter) : (Array.isArray(rawIter) ? rawIter : []);
          let last = null;
          for (const item of seq) {
            const fEnv = new Env(env);
            if (node.tupleVars) {
              const elems = item?.__tuple ? item.elems : Array.isArray(item) ? item : [item];
              node.tupleVars.forEach((nm, idx) => fEnv.define(nm, elems[idx] ?? null));
            } else {
              fEnv.define(node.varName, item);
            }
            try {
              last = evalNode(node.body, fEnv);
            } catch (sig) {
              if (sig instanceof BreakSignal) break;
              if (sig instanceof ContinueSignal) continue;
              throw sig;
            }
          }
          return last;
        }
        case "select": {
          // Cooperatively drain spawned channel producers if queues are empty
          while (spawnedTasks.length > 0) {
            const task = spawnedTasks.shift();
            task();
          }
          for (const arm of node.arms) {
            if (arm.kind === "recv") {
              const rx = evalNode(arm.rx, env);
              if (rx?.__chan_rx && rx.__chan_rx.buf.length > 0) {
                const msg = rx.__chan_rx.buf.shift();
                const aEnv = new Env(env);
                aEnv.define(arm.binding, msg);
                return evalNode(arm.body, aEnv);
              }
            }
          }
          const closedArm = node.arms.find((a) => a.kind === "closed");
          if (closedArm) return evalNode(closedArm.body, env);
          return null;
        }
        case "try": {
          try {
            return evalNode(node.body, env);
          } catch (err) {
            if (err instanceof ReturnSignal) throw err;
            if (node.recoverBody) {
              const rEnv = new Env(env);
              const errVal = err instanceof PropagateErrSignal ? err.errObj : (err?.message || String(err));
              if (node.recoverVar) rEnv.define(node.recoverVar, errVal);
              return evalNode(node.recoverBody, rEnv);
            }
            return null;
          } finally {
            if (node.ensureBody) evalNode(node.ensureBody, env);
          }
        }
        case "match": {
          const subj = evalNode(node.subject, env);
          for (const arm of node.arms) {
            const bindings = matchPattern(arm.pattern, subj);
            if (bindings !== null) {
              const mEnv = new Env(env);
              for (const [k, v] of Object.entries(bindings)) mEnv.define(k, v);
              if (arm.guard && !evalNode(arm.guard, mEnv)) continue;
              return evalNode(arm.body, mEnv);
            }
          }
          return null;
        }
        case "comptime":
          return evalNode(node.body, env);
        case "handle": {
          const frame = { handlers: node.handlers, env, state: 0 };
          effectStack.push(frame);
          try {
            return evalNode(node.body, env);
          } catch (sig) {
            if (sig instanceof EffectAbortSignal) return sig.value;
            throw sig;
          } finally {
            effectStack.pop();
          }
        }
        case "perform": {
          const c = node.call;
          const effName = c.ns || "";
          const opName = c.method || c.callee || "";
          const args = (c.args || []).map((a) => evalNode(a, env));
          const frame = effectStack[effectStack.length - 1];
          if (!frame) throw new Error("Unhandled effect " + effName + "::" + opName);
          if (effName === "State") {
            if (opName === "get") return frame.state;
            if (opName === "put") {
              frame.state = args[0];
              return null;
            }
          }
          const h = frame.handlers.find((x) => x.effect === effName && x.op === opName);
          if (!h) throw new Error("No handler for " + effName + "::" + opName);
          let resumed = false;
          let resumeValue = null;
          const hEnv = new Env(frame.env);
          h.params.forEach((p, idx) => hEnv.define(p, args[idx]));
          hEnv.define("resume", {
            __fn: true,
            call(rArgs) {
              resumed = true;
              resumeValue = rArgs[0] ?? null;
              return resumeValue;
            },
          });
          evalNode(h.body, hEnv);
          if (effName === "Fail") {
            throw new ContinueSignal();
          }
          return resumed ? resumeValue : null;
        }
        case "spawn": {
          // Run eagerly if returning a value inside map, or queue if statement-level producer
          return evalNode(node.body, env);
        }
        case "await":
          return evalNode(node.expr, env);
        case "propagate": {
          const v = evalNode(node.expr, env);
          if (v?.__result === "err") throw new PropagateErrSignal(v.value);
          if (v?.__result === "ok") return v.value;
          return v;
        }
        case "lambda":
          return { __fn: true, name: null, params: node.params, body: node.body, env };
        case "tuple":
          return { __tuple: true, elems: node.elems.map((e) => evalNode(e, env)) };
        case "list":
          return node.elems.map((e) => evalNode(e, env));
        case "repeat_list": {
          const v = evalNode(node.value, env);
          const n = Number(evalNode(node.count, env));
          return Array.from({ length: n }, () => v);
        }
        case "map": {
          const obj = {};
          for (const e of node.entries) obj[evalNode(e.key, env)] = evalNode(e.value, env);
          return obj;
        }
        case "range": {
          const s = Number(evalNode(node.start, env));
          const e = Number(evalNode(node.end, env));
          const out = [];
          for (let i = s; node.inclusive ? i <= e : i < e; i++) out.push(i);
          return out;
        }
        case "struct_init": {
          const base = node.spread ? { ...evalNode(node.spread, env) } : {};
          const shortType = node.name.split("::").pop();
          const inst = { ...base, __struct: shortType };
          for (const f of node.fields) inst[f.name] = evalNode(f.value, env);
          return inst;
        }
        case "field": {
          const obj = evalNode(node.object, env);
          if (obj?.__tuple && /^\d+$/.test(node.field)) {
            return obj.elems[Number(node.field)];
          }
          return obj ? obj[node.field] : null;
        }
        case "index": {
          const obj = evalNode(node.object, env);
          const idx = evalNode(node.index, env);
          return obj ? obj[idx] : null;
        }
        case "slice": {
          const obj = evalNode(node.object, env);
          const s = Number(evalNode(node.start, env));
          const e = node.end ? Number(evalNode(node.end, env)) : undefined;
          return Array.isArray(obj) || typeof obj === "string" ? obj.slice(s, e) : [];
        }
        case "cast": {
          const v = evalNode(node.expr, env);
          if (["Float", "float", "f64"].includes(node.targetType)) return Number(v);
          if (["Int", "int", "i64"].includes(node.targetType)) return Math.trunc(Number(v));
          if (["String", "str"].includes(node.targetType)) return formatVal(v);
          return v;
        }
        case "unary": {
          const v = evalNode(node.operand, env);
          return node.op === "-" ? -v : !v;
        }
        case "binop": {
          if (node.op === "and") return evalNode(node.left, env) ? evalNode(node.right, env) : false;
          if (node.op === "or") return evalNode(node.left, env) ? true : Boolean(evalNode(node.right, env));
          const l = evalNode(node.left, env);
          const r = evalNode(node.right, env);
          switch (node.op) {
            case "+": return typeof l === "string" || typeof r === "string" ? formatVal(l) + formatVal(r) : l + r;
            case "-": return l - r;
            case "*": return l * r;
            case "/":
              if (r === 0) throw new Error("Division by zero");
              return Number.isInteger(l) && Number.isInteger(r) && l % r === 0 ? l / r : l / r;
            case "%": return l % r;
            case "**": return Math.pow(l, r);
            case "==":
              if (l?.__none && r?.__none) return true;
              if (l?.__none || r?.__none) return false;
              return l === r;
            case "!=":
              if (l?.__none && r?.__none) return false;
              if (l?.__none || r?.__none) return true;
              return l !== r;
            case "<": return l < r;
            case ">": return l > r;
            case "<=": return l <= r;
            case ">=": return l >= r;
            default: return 0;
          }
        }
        case "call": {
          const args = node.args.map((a) => evalNode(a, env));
          const fnVal = env.get(node.callee);
          if (fnVal !== undefined) return invokeCallable(fnVal, args, node.typeArgs);
          if (BUILTIN_NAMES.has(node.callee)) return callBuiltin(node.callee, args, env, node.typeArgs);
          throw new Error("Undefined function '" + node.callee + "'");
        }
        case "call_expr": {
          const fnVal = evalNode(node.calleeExpr, env);
          const args = node.args.map((a) => evalNode(a, env));
          return invokeCallable(fnVal, args);
        }
        case "static_call": {
          const args = node.args.map((a) => evalNode(a, env));
          return callStaticNamespace(node.ns, node.method, args);
        }
        case "static_ref": {
          if (node.ns === "math" || node.ns === "Math") {
            if (node.member.toLowerCase() === "pi") return Math.PI;
            if (node.member.toLowerCase() === "e") return Math.E;
          }
          const modObj = env.get(node.ns);
          if (modObj && node.member in modObj) return modObj[node.member];
          return { __variant: node.ns + "::" + node.member, values: [] };
        }
        case "method_call": {
          const obj = evalNode(node.object, env);
          const args = node.args.map((a) => evalNode(a, env));
          return callInstanceMethod(obj, node.method, args, env);
        }
        case "pipe": {
          const val = evalNode(node.left, env);
          const st = node.stage;
          if (st.type === "call") {
            const extra = st.args.map((a) => evalNode(a, env));
            if (val?.__struct) {
              const implE = implTable.get(val.__struct);
              if (implE?.methods.has(st.callee)) {
                return invokeCallable(implE.methods.get(st.callee), [val, ...extra]);
              }
            }
            const fnVal = env.get(st.callee);
            if (fnVal !== undefined) return invokeCallable(fnVal, [val, ...extra]);
            if (BUILTIN_NAMES.has(st.callee)) return callBuiltin(st.callee, [val, ...extra], env);
            return callInstanceMethod(val, st.callee, extra, env);
          }
          if (st.type === "static_call") {
            const extra = st.args.map((a) => evalNode(a, env));
            return callStaticNamespace(st.ns, st.method, [val, ...extra]);
          }
          const target = evalNode(st, env);
          return invokeCallable(target, [val]);
        }
        default:
          return null;
      }
    }

    return evalNode(prog, rootEnv);
  }

  // --------------------------------------------------------------------------
  // 6. Public Entry Point
  // --------------------------------------------------------------------------

  function compileLateralusToWasm(source) {
    const t0 = typeof performance !== "undefined" ? performance.now() : Date.now();
    const ast = parseLateralus(source);
    const useNative = canCompilePureNative(ast);
    const compiled = useNative ? compileNativeTier1(ast) : compileHostBridgedTier2(ast);
    const compileMs = Number(
      ((typeof performance !== "undefined" ? performance.now() : Date.now()) - t0).toFixed(2)
    );
    return {
      mode: compiled.mode,
      wat: compiled.wat,
      wasmBytes: compiled.wasmBytes,
      compileMs,
    };
  }

  return {
    CompileError,
    WasmModuleBuilder,
    tokenize,
    parseLateralus,
    canCompilePureNative,
    compileLateralusToWasm,
    executeSerializedAst,
  };
});
