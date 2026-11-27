"""
tests/test_wasm_playground_live.py - End-to-End WASM Backend & Offline Playground Tests
=======================================================================================
Verifies:
  1. Spec-compliant WebAssembly 1.0 binary (.wasm) generation in Python without
     requiring external `wat2wasm`.
  2. CLI `lateralus wasm` support for both `.wat` text and `--binary` / `.wasm` output.
  3. Real V8 execution (`WebAssembly.validate` + `WebAssembly.instantiate`) of Python-
     generated `.wasm` modules via the browser host shim (`println`, `print`, `http_get`).
  4. In-browser offline compilation (`wasm-compiler.js` + `wasm-shim.js`) across all
     Playground examples, plus dynamic input-mutation recomputation proofs and zero
     server-side `/api/run` calls.
=======================================================================================
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lateralus_lang.__main__ import main as cli_main  # noqa: E402
from lateralus_lang.codegen.wasm import (  # noqa: E402
    WasmModule,
    compile_to_wasm,
    compile_to_wasm_bytes,
)
from lateralus_lang.codegen.wasm_binary import (  # noqa: E402
    WASM_MAGIC,
    WASM_VERSION,
    encode_sleb128,
    encode_uleb128,
)
from lateralus_lang.compiler import Compiler, Target  # noqa: E402

PLAYGROUND_DIR = REPO_ROOT / "docs" / "website" / "playground"
HEADERS_FILE = REPO_ROOT / "docs" / "website" / "_headers"
NODE_BIN = shutil.which("node")

requires_node = pytest.mark.skipif(
    NODE_BIN is None, reason="Node.js runtime required for V8 WebAssembly execution"
)


def _decode_uleb128(buf: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    pos = offset
    while True:
        byte = buf[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            return result, pos
        shift += 7


def _run_node_json(script: str, payload: dict) -> dict:
    assert NODE_BIN is not None
    proc = subprocess.run(
        [NODE_BIN, "-e", script],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"Node V8 harness failed (rc={proc.returncode}):\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return json.loads(proc.stdout.strip().splitlines()[-1])


# ===========================================================================
# 1. Pure-Python WebAssembly 1.0 Binary Encoding & CLI Tests
# ===========================================================================


class TestWasmBinaryEncoding:
    """Validate LEB128 primitives, binary section ordering, and CLI flags."""

    def test_uleb128_vectors(self) -> None:
        assert encode_uleb128(0) == b"\x00"
        assert encode_uleb128(127) == b"\x7f"
        assert encode_uleb128(128) == b"\x80\x01"
        assert encode_uleb128(624485) == b"\xe5\x8e\x26"

    def test_sleb128_vectors(self) -> None:
        assert encode_sleb128(0, 64) == b"\x00"
        assert encode_sleb128(-1, 64) == b"\x7f"
        assert encode_sleb128(63, 64) == b"\x3f"
        assert encode_sleb128(64, 64) == b"\xc0\x00"
        assert encode_sleb128(-64, 64) == b"\x40"
        assert encode_sleb128(-123456, 32) == b"\xc0\xbb\x78"

    def test_binary_header_and_monotonic_sections(self) -> None:
        src = """
        fn square(x: int) -> int {
            return x * x
        }
        fn main() {
            println("sq=" + str(square(9)))
        }
        """
        wasm_bytes = compile_to_wasm_bytes(src)
        assert wasm_bytes[:4] == WASM_MAGIC
        assert wasm_bytes[4:8] == WASM_VERSION

        # Verify section IDs strictly ascend and section sizes match exact byte length
        pos = 8
        seen_sections: list[int] = []
        while pos < len(wasm_bytes):
            sec_id = wasm_bytes[pos]
            pos += 1
            sec_len, pos = _decode_uleb128(wasm_bytes, pos)
            seen_sections.append(sec_id)
            pos += sec_len

        assert pos == len(wasm_bytes)
        assert seen_sections == sorted(seen_sections)
        assert len(set(seen_sections)) == len(seen_sections)

    def test_wat_balanced_parentheses_for_compiled_program(self) -> None:
        mod = compile_to_wasm(
            """
            fn fact(n: int) -> int {
                if n <= 1 { return 1 }
                return n * fact(n - 1)
            }
            fn main() {
                println(str(fact(6)))
            }
            """
        )
        wat = mod.to_wat()
        assert wat.count("(") == wat.count(")")
        assert '(import "env" "println"' in wat
        assert '(import "env" "http_get"' in wat
        assert '(export "main")' in wat

    def test_compiler_and_cli_binary_and_wat_outputs(self, tmp_path: pathlib.Path) -> None:
        ltl_file = tmp_path / "demo.ltl"
        ltl_file.write_text(
            'fn main() {\n    println("hello wasm")\n}\n',
            encoding="utf-8",
        )

        cc = Compiler()
        res = cc.compile_file(str(ltl_file), target=Target.WASM)
        assert res.ok
        assert res.wasm_src is not None and "(module" in res.wasm_src
        assert res.wasm_bytes is not None and res.wasm_bytes.startswith(b"\x00asm\x01\x00\x00\x00")

        wat_out = tmp_path / "demo.wat"
        wasm_out = tmp_path / "demo.wasm"
        flag_out = tmp_path / "demo_flag.bin"

        assert cli_main(["wasm", str(ltl_file), "-o", str(wat_out)]) == 0
        assert wat_out.read_text(encoding="utf-8").startswith("(module")

        assert cli_main(["wasm", str(ltl_file), "-o", str(wasm_out)]) == 0
        assert wasm_out.read_bytes()[:8] == b"\x00asm\x01\x00\x00\x00"

        assert cli_main(["wasm", str(ltl_file), "--binary", "-o", str(flag_out)]) == 0
        assert flag_out.read_bytes()[:8] == b"\x00asm\x01\x00\x00\x00"

    def test_manual_wasm_module_to_bytes(self) -> None:
        mod = WasmModule("adder")
        fn = mod.add_function("add", [("a", "i64"), ("b", "i64")], "i64", exported=True)
        fn.emit("local.get $a", "local.get $b", "i64.add")
        raw = mod.to_bytes()
        assert raw[:8] == b"\x00asm\x01\x00\x00\x00"


# ===========================================================================
# 2. Python `lateralus wasm` -> Node V8 Execution via `wasm-shim.js`
# ===========================================================================


@requires_node
class TestPythonWasmV8Execution:
    """Execute Python-compiled `.wasm` binaries inside V8 using `wasm-shim.js`."""

    @staticmethod
    def _exec_python_ltl_in_v8(
        source: str, http_fixtures: dict[str, str] | None = None
    ) -> dict:
        wasm_bytes = compile_to_wasm_bytes(source)
        node_script = """
        const fs = require("fs");
        const shim = require("./docs/website/playground/wasm-shim.js");
        const payload = JSON.parse(fs.readFileSync(0, "utf8"));
        const bytes = Uint8Array.from(payload.wasm);
        shim.runLateralusWasm(bytes, {
          fetchImpl: async (url) => {
            if (payload.fixtures && Object.prototype.hasOwnProperty.call(payload.fixtures, url)) {
              return { ok: true, status: 200, text: async () => payload.fixtures[url] };
            }
            return { ok: false, status: 404, text: async () => "not-found" };
          }
        }).then(res => {
          const exportedFib = typeof res.exports.fib === "function" ? Number(res.exports.fib(12n)) : null;
          console.log(JSON.stringify({
            ok: res.ok,
            output: res.output,
            exitCode: res.exitCode,
            httpRequests: res.httpRequests,
            exportedFib
          }));
        }).catch(err => {
          console.error(err);
          process.exit(1);
        });
        """
        return _run_node_json(
            node_script,
            {"wasm": list(wasm_bytes), "fixtures": http_fixtures or {}},
        )

    def test_recursion_loops_and_exported_function(self) -> None:
        res = self._exec_python_ltl_in_v8(
            """
            fn fib(n: int) -> int {
                if n <= 1 { return n }
                return fib(n - 1) + fib(n - 2)
            }

            fn main() {
                let mut acc = 0
                for i in 1..5 {
                    acc += i * i
                }
                println("sum_sq=" + str(acc))
                println("fib10=" + str(fib(10)))
            }
            """
        )
        assert res["ok"] is True
        assert res["exportedFib"] == 144
        assert res["output"] == ["sum_sq=55", "fib10=55"]

    def test_pipeline_strings_floats_and_match(self) -> None:
        res = self._exec_python_ltl_in_v8(
            """
            fn triple(x: int) -> int { return x * 3 }
            fn offset(x: int, d: int) -> int { return x + d }

            fn classify(code: int) -> str {
                return match code {
                    200 | 204 => "ok",
                    404 => "missing",
                    _ => "other"
                }
            }

            fn main() {
                let v = 7 |> triple |> offset(4)
                let hyp = sqrt(9.0 + 16.0)
                println("piped={v} hyp={hyp} tag={classify(204)}")
            }
            """
        )
        assert res["output"] == ["piped=25 hyp=5.00 tag=ok"]

    def test_lists_structs_and_methods_in_linear_memory(self) -> None:
        res = self._exec_python_ltl_in_v8(
            """
            struct Pair {
                a: int
                b: int
            }

            impl Pair {
                fn sum(self) -> int {
                    return self.a + self.b
                }
            }

            fn main() {
                let nums = [10, 20, 35, 5]
                let p = Pair { a: nums[1], b: nums[2] }
                println("len=" + str(len(nums)) + " total=" + str(sum(nums)) + " pair=" + str(p.sum()))
            }
            """
        )
        assert res["output"] == ["len=4 total=70 pair=55"]

    def test_host_shim_http_get_replay_into_linear_memory(self) -> None:
        res = self._exec_python_ltl_in_v8(
            """
            fn main() {
                let body = http_get("https://example.test/status")
                println("resp=" + body + " bytes=" + str(len(body)))
            }
            """,
            http_fixtures={"https://example.test/status": "SPIRAL_OK"},
        )
        assert res["output"] == ["resp=SPIRAL_OK bytes=9"]
        assert len(res["httpRequests"]) == 1
        assert res["httpRequests"][0]["url"] == "https://example.test/status"
        assert res["httpRequests"][0]["status"] == 200


# ===========================================================================
# 3. Browser Playground Offline Compiler & Anti-Cheat Mutation Tests
# ===========================================================================


class TestPlaygroundStaticHygiene:
    """Verify static Playground HTML & CSP headers enforce local WASM execution."""

    def test_playground_html_has_no_server_api_calls_or_fake_simulator(self) -> None:
        html = (PLAYGROUND_DIR / "index.html").read_text(encoding="utf-8")
        assert "/api/run" not in html
        assert "simulateRun" not in html
        assert "./wasm-shim.js" in html
        assert "./wasm-compiler.js" in html

    def test_csp_headers_allow_wasm_instantiation(self) -> None:
        headers_txt = HEADERS_FILE.read_text(encoding="utf-8")
        assert "'wasm-unsafe-eval'" in headers_txt

    def test_no_banned_box_drawing_characters_in_touched_files(self) -> None:
        paths = [
            REPO_ROOT / "lateralus_lang" / "codegen" / "wasm.py",
            REPO_ROOT / "lateralus_lang" / "codegen" / "wasm_binary.py",
            PLAYGROUND_DIR / "wasm-shim.js",
            PLAYGROUND_DIR / "wasm-compiler.js",
            PLAYGROUND_DIR / "index.html",
            HEADERS_FILE,
        ]
        for path in paths:
            text = path.read_text(encoding="utf-8")
            bad = [ch for ch in text if 0x2500 <= ord(ch) <= 0x257F]
            assert not bad, f"Banned box-drawing char(s) {bad!r} found in {path}"


@requires_node
class TestBrowserPlaygroundWasmSuite:
    """Validate `wasm-compiler.js` + `wasm-shim.js` across all examples and mutations."""

    def test_all_builtin_playground_examples_compile_and_execute_in_v8(self) -> None:
        script = """
        const fs = require("fs");
        const vm = require("vm");
        const shim = require("./docs/website/playground/wasm-shim.js");
        const compiler = require("./docs/website/playground/wasm-compiler.js");

        const html = fs.readFileSync("./docs/website/playground/index.html", "utf8");
        const sIdx = html.indexOf("const EXAMPLES = {");
        const eIdx = html.indexOf("// -- In-Browser WASM Compiler");
        const EXAMPLES = vm.runInNewContext(html.slice(sIdx, eIdx) + "\\n; EXAMPLES;", {});

        (async () => {
          const summary = {};
          for (const [name, src] of Object.entries(EXAMPLES)) {
            const c = compiler.compileLateralusToWasm(src);
            if (!WebAssembly.validate(c.wasmBytes)) {
              throw new Error("Invalid WASM binary for example: " + name);
            }
            const r = await shim.runLateralusWasm(c.wasmBytes, {
              astExecutor: compiler.executeSerializedAst,
              fetchImpl: async (url) => ({
                ok: true,
                status: 200,
                text: async () => JSON.stringify({ name: "lateralus", url }),
              }),
            });
            if (!r.output || r.output.length === 0) {
              throw new Error("Example produced zero output: " + name);
            }
            summary[name] = { mode: c.mode, bytes: c.wasmBytes.length, lines: r.output.length };
          }
          console.log(JSON.stringify({ count: Object.keys(summary).length, wasmLiveMode: summary.wasm_live.mode }));
        })().catch(err => { console.error(err); process.exit(1); });
        """
        res = _run_node_json(script, {})
        assert res["count"] >= 20
        assert res["wasmLiveMode"] == "native-wasm"

    def test_dynamic_input_mutations_recompute_real_outputs(self) -> None:
        script = """
        const fs = require("fs");
        const vm = require("vm");
        const shim = require("./docs/website/playground/wasm-shim.js");
        const compiler = require("./docs/website/playground/wasm-compiler.js");

        const html = fs.readFileSync("./docs/website/playground/index.html", "utf8");
        const sIdx = html.indexOf("const EXAMPLES = {");
        const eIdx = html.indexOf("// -- In-Browser WASM Compiler");
        const EXAMPLES = vm.runInNewContext(html.slice(sIdx, eIdx) + "\\n; EXAMPLES;", {});

        async function runSrc(src, fixtures) {
          const c = compiler.compileLateralusToWasm(src);
          return shim.runLateralusWasm(c.wasmBytes, {
            astExecutor: compiler.executeSerializedAst,
            httpFixtures: fixtures || { "/manifest.json": "{}" },
          });
        }

        (async () => {
          // 1. Mutate Tier-1 native WASM pipeline: 11 |> fib (89) |> scale_and_offset(4) => 363
          const modWasm = EXAMPLES.wasm_live.replace(
            "10 |> fib |> scale_and_offset(3)",
            "11 |> fib |> scale_and_offset(4)"
          );
          const rWasm = await runSrc(modWasm, { "/manifest.json": "1234567890" });

          // 2. Mutate pipeline example threshold: > 100.0 leaves only 199.99 + 549.00 = 748.99
          const modPipe = EXAMPLES.pipeline.replace("t.amount > 20.0", "t.amount > 100.0");
          const rPipe = await runSrc(modPipe);

          // 3. Mutate pattern matching radius: Circle(10.0) => 314.16
          const modPat = EXAMPLES.pattern.replace("Circle(5.0)", "Circle(10.0)");
          const rPat = await runSrc(modPat);

          // 4. Mutate comptime factorial(10) -> factorial(6) = 720
          const modComp = EXAMPLES.comptime
            .replace("factorial(10)", "factorial(6)")
            .replace("3628800", "720");
          const rComp = await runSrc(modComp);

          // 5. Verify syntax errors genuinely fail compilation
          let syntaxThrew = false;
          try {
            compiler.compileLateralusToWasm("fn broken( { println(1) }");
          } catch (e) {
            syntaxThrew = e.name === "CompileError";
          }

          console.log(JSON.stringify({
            wasmOut: rWasm.output,
            pipeOut: rPipe.output,
            patFirst: rPat.output[0],
            compOut: rComp.output,
            syntaxThrew
          }));
        })().catch(err => { console.error(err); process.exit(1); });
        """
        res = _run_node_json(script, {})
        assert any("363" in line for line in res["wasmOut"])
        assert any("10 bytes" in line for line in res["wasmOut"])
        assert any("$748.99 (2 transactions)" in line for line in res["pipeOut"])
        assert res["patFirst"] == "Circle (r=10) => area = 314.16"
        assert any("= 720" in line for line in res["compOut"])
        assert res["syntaxThrew"] is True
