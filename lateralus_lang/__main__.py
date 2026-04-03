"""
lateralus_lang/__main__.py  ─  Entry point for `python -m lateralus_lang`
"""
import sys
from .compiler import Compiler, Target
from .repl     import start_repl
from .repl_enhanced import start_repl as start_repl_enhanced
from .markup   import parse as _ltlm_parse, to_html as _ltlm_html, to_ansi as _ltlm_ansi


def main(argv=None) -> int:
    import argparse
    from . import __version__
    p = argparse.ArgumentParser(
        prog="python -m lateralus_lang",
        description="Lateralus Language toolchain  v" + __version__,
    )
    p.add_argument("--version", action="version",
                   version=f"lateralus-lang {__version__}")
    sub = p.add_subparsers(dest="cmd")

    # run
    run_p = sub.add_parser("run",  help="Execute a .ltl file")
    run_p.add_argument("file")
    run_p.add_argument("args", nargs="*", help="Script arguments")
    run_p.add_argument("--ipc", action="store_true",
                       help="JSON IPC mode: read params from stdin, write result to stdout")

    # build
    build_p = sub.add_parser("build", help="Compile .ltl → .ltbc bytecode")
    build_p.add_argument("file")
    build_p.add_argument("-o", "--output")
    build_p.add_argument("--profile", default="debug",
                         help="Build profile: debug, release, bench")

    # py  (transpile)
    py_p = sub.add_parser("py", help="Transpile .ltl → Python 3")
    py_p.add_argument("file")
    py_p.add_argument("-o", "--output")

    # c  (transpile to C99)
    c_p = sub.add_parser("c", help="Transpile .ltl → C99")
    c_p.add_argument("file")
    c_p.add_argument("-o", "--output")
    c_p.add_argument("--freestanding", action="store_true",
                     help="Emit freestanding C (no libc, for OS/embedded)")
    c_p.add_argument("--arch", default="x86_64",
                     help="Target architecture (default: x86_64)")

    # js  (transpile to JavaScript ES2022+)
    js_p = sub.add_parser("js", help="Transpile .ltl → JavaScript ES2022+")
    js_p.add_argument("file")
    js_p.add_argument("-o", "--output")
    js_p.add_argument("--format", default="esm", choices=["esm", "cjs", "iife"],
                      help="Module format (default: esm)")

    # wasm  (compile to WebAssembly)
    wasm_p = sub.add_parser("wasm", help="Compile .ltl → WebAssembly (.wat)")
    wasm_p.add_argument("file")
    wasm_p.add_argument("-o", "--output")

    # check
    chk_p = sub.add_parser("check", help="Type-check only")
    chk_p.add_argument("file")

    # repl
    repl_p = sub.add_parser("repl", help="Interactive REPL")
    repl_p.add_argument("--enhanced", "-e", action="store_true",
                        help="Use enhanced REPL (syntax highlighting, completions)")
    repl_p.add_argument("--no-color", action="store_true",
                        help="Disable ANSI color output")
    repl_p.add_argument("--timing", action="store_true",
                        help="Show execution timing for each evaluation")

    # asm
    asm_p = sub.add_parser("asm", help="Assemble .ltasm → .ltbc")
    asm_p.add_argument("file")
    asm_p.add_argument("-o", "--output")

    # ast  (new in v1.1)
    ast_p = sub.add_parser("ast", help="Dump the parsed AST as text")
    ast_p.add_argument("file")
    ast_p.add_argument("--json", action="store_true",
                       help="Output as JSON (requires pprint-compatible repr)")

    # ir  (new in v1.1)
    ir_p = sub.add_parser("ir", help="Dump the three-address IR")
    ir_p.add_argument("file")

    # test  (v1.4)
    test_p = sub.add_parser("test", help="Run @test functions in a .ltl file")
    test_p.add_argument("file")
    test_p.add_argument("--verbose", "-v", action="store_true")

    # doc  (v1.4)
    doc_p = sub.add_parser("doc", help="Render a .ltlm document (HTML or terminal)")
    doc_p.add_argument("file")
    doc_p.add_argument("--html",   action="store_true", help="Emit HTML instead of terminal output")
    doc_p.add_argument("-o", "--output", help="Write output to file")

    # compile  (v1.4 — .ltl → .ltlc binary)
    comp_p = sub.add_parser("compile", help="Compile .ltl → .ltlc proprietary binary")
    comp_p.add_argument("file")
    comp_p.add_argument("-o", "--output", help="Output .ltlc path")

    # decompile  (v1.4 — .ltlc → .ltl source)
    decomp_p = sub.add_parser("decompile", help="Decompile .ltlc → .ltl source")
    decomp_p.add_argument("file")
    decomp_p.add_argument("-o", "--output", help="Write decompiled source to file")

    # inspect  (v1.4 — show .ltlc metadata)
    insp_p = sub.add_parser("inspect", help="Show .ltlc binary metadata")
    insp_p.add_argument("file")

    # info  (v1.4)
    sub.add_parser("info", help="Print version, stdlib modules, and feature flags")

    # fmt  (v1.5)
    fmt_p = sub.add_parser("fmt", help="Format .ltl source files")
    fmt_p.add_argument("files", nargs="*", default=["."])
    fmt_p.add_argument("--check", action="store_true", help="Check formatting without modifying")
    fmt_p.add_argument("--diff", action="store_true", help="Show diff of formatting changes")
    fmt_p.add_argument("--indent", type=int, default=4, help="Indentation size")

    # lint  (v1.5)
    lint_p = sub.add_parser("lint", help="Run static analysis on .ltl files")
    lint_p.add_argument("files", nargs="+")
    lint_p.add_argument("--strict", action="store_true", help="Enable strict mode")

    # lsp  (v1.5)
    sub.add_parser("lsp", help="Start the Language Server Protocol server")

    # dap  (v1.5)
    dap_p = sub.add_parser("dap", help="Start the Debug Adapter Protocol server")
    dap_p.add_argument("--port", type=int, default=0, help="TCP port (0 = stdin/stdout)")

    # init  (v1.7)
    init_p = sub.add_parser("init", help="Create a new LATERALUS project")
    init_p.add_argument("name", nargs="?", default="my-lateralus-project")
    init_p.add_argument("--template", default="default",
                        choices=["default", "lib", "app"])

    # add  (v1.7)
    add_p = sub.add_parser("add", help="Add a dependency to the project")
    add_p.add_argument("package")
    add_p.add_argument("--version", default="*")
    add_p.add_argument("--path", default=None)
    add_p.add_argument("--git", default=None)
    add_p.add_argument("--dev", action="store_true")

    # publish  (v1.7)
    pub_p = sub.add_parser("publish", help="Publish package to registry")
    pub_p.add_argument("--dry-run", action="store_true",
                       help="Preview without uploading")

    # serve  (v2.2)
    serve_p = sub.add_parser("serve", help="Serve .ltlml docs as HTML pages")
    serve_p.add_argument("--port", "-p", type=int, default=8400,
                         help="Port to listen on (default: 8400)")
    serve_p.add_argument("--dir", "-d", default=None,
                         help="Docs directory (default: docs/)")
    serve_p.add_argument("--no-reload", action="store_true",
                         help="Disable live reload")

    # bench  (v2.4)
    bench_p = sub.add_parser("bench", help="Run performance benchmarks")
    bench_p.add_argument("--suite", "-s", nargs="*", default=None,
                         help="Specific suites to run (math, crypto, markup, bytecode, optimizer, types, compiler)")
    bench_p.add_argument("--iterations", "-n", type=int, default=500,
                         help="Number of iterations per benchmark (default: 500)")
    bench_p.add_argument("--json", action="store_true",
                         help="Output results as JSON")

    # profile  (v2.4)
    profile_p = sub.add_parser("profile", help="Profile compilation of a .ltl file")
    profile_p.add_argument("file")
    profile_p.add_argument("--target", default="python",
                           choices=["python", "c", "js", "wasm", "check"],
                           help="Compilation target (default: python)")
    profile_p.add_argument("--repeat", type=int, default=10,
                           help="Number of repetitions (default: 10)")

    # disasm  (v2.4)
    disasm_p = sub.add_parser("disasm", help="Disassemble .ltbc bytecode → .ltasm text")
    disasm_p.add_argument("file")
    disasm_p.add_argument("-o", "--output", help="Output .ltasm file")

    # clean  (v2.4)
    clean_p = sub.add_parser("clean", help="Remove build artifacts")
    clean_p.add_argument("--all", action="store_true",
                         help="Also remove dist/ and .egg-info/")

    ns = p.parse_args(argv)
    c  = Compiler()

    if ns.cmd == "run":
        # JSON IPC mode — read params from stdin, emit result JSON to stdout
        # (used by lateralus.polyglot.LaterRuntime)
        ipc = getattr(ns, "ipc", False)
        params = {}
        if ipc:
            import json as _json
            raw = sys.stdin.read().strip()
            if raw:
                try:
                    params = _json.loads(raw)
                except Exception:
                    params = {}
        result = c.run_file(ns.file)
        if ipc:
            import json as _json
            out = {
                "ok":          result.ok,
                "exit_code":   result.exit_code,
                "stdout":      result.stdout if hasattr(result, "stdout") else "",
                "log":         [str(e) for e in result.errors],
            }
            print(_json.dumps(out))
            return result.exit_code
        if not result.ok:
            for e in result.errors:
                print(e.render() if hasattr(e, "render") else str(e), file=sys.stderr)
        return result.exit_code

    elif ns.cmd == "build":
        result = c.compile_file(ns.file, target=Target.BYTECODE)
        if result.ok:
            import pickle, pathlib
            out = ns.output or (pathlib.Path(ns.file).stem + ".ltbc")
            pathlib.Path(out).write_bytes(pickle.dumps(result.bytecode))
            print(f"Built → {out}")
        else:
            _print_errors(result)
        return 0 if result.ok else 1

    elif ns.cmd == "py":
        result = c.compile_file(ns.file, target=Target.PYTHON)
        if result.ok:
            import pathlib
            out = ns.output or (pathlib.Path(ns.file).stem + ".py")
            pathlib.Path(out).write_text(result.python_src, encoding="utf-8")
            print(f"Transpiled → {out}")
        else:
            _print_errors(result)
        return 0 if result.ok else 1

    elif ns.cmd == "c":
        if getattr(ns, "freestanding", False):
            c.freestanding = True
        result = c.compile_file(ns.file, target=Target.C)
        if result.ok:
            import pathlib
            out = ns.output or (pathlib.Path(ns.file).stem + ".c")
            pathlib.Path(out).write_text(result.c_src, encoding="utf-8")
            print(f"Transpiled → {out}")
        else:
            _print_errors(result)
        return 0 if result.ok else 1

    elif ns.cmd == "js":
        result = c.compile_file(ns.file, target=Target.JAVASCRIPT)
        if result.ok:
            import pathlib
            out = ns.output or (pathlib.Path(ns.file).stem + ".js")
            pathlib.Path(out).write_text(result.js_src, encoding="utf-8")
            print(f"Transpiled → {out}")
        else:
            _print_errors(result)
        return 0 if result.ok else 1

    elif ns.cmd == "wasm":
        result = c.compile_file(ns.file, target=Target.WASM)
        if result.ok:
            import pathlib
            out = ns.output or (pathlib.Path(ns.file).stem + ".wat")
            pathlib.Path(out).write_text(result.wasm_src, encoding="utf-8")
            print(f"Compiled → {out}")
        else:
            _print_errors(result)
        return 0 if result.ok else 1

    elif ns.cmd == "check":
        result = c.compile_file(ns.file, target=Target.CHECK)
        _print_errors(result)
        if result.ok:
            print(f"✓ {ns.file}: OK")
        return 0 if result.ok else 1

    elif ns.cmd == "repl":
        if getattr(ns, "enhanced", False):
            start_repl_enhanced(
                color=not getattr(ns, "no_color", False),
                timing=getattr(ns, "timing", False),
            )
        else:
            start_repl()
        return 0

    elif ns.cmd == "asm":
        result = c.compile_file(ns.file, target=Target.ASSEMBLE)
        if result.ok:
            import pickle, pathlib
            out = ns.output or (pathlib.Path(ns.file).stem + ".ltbc")
            pathlib.Path(out).write_bytes(pickle.dumps(result.bytecode))
            print(f"Assembled → {out}")
        else:
            _print_errors(result)
        return 0 if result.ok else 1

    elif ns.cmd == "ast":
        import pathlib, pprint
        from .lexer  import lex, LexError
        from .parser import parse, ParseError
        src = pathlib.Path(ns.file).read_text(encoding="utf-8")
        try:
            tree = parse(src, ns.file)
        except (LexError, ParseError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if getattr(ns, "json", False):
            import json
            def _to_dict(n):
                if hasattr(n, "__dataclass_fields__"):
                    return {k: _to_dict(v) for k, v in vars(n).items()}
                if isinstance(n, list):
                    return [_to_dict(i) for i in n]
                return n
            print(json.dumps(_to_dict(tree), indent=2, default=str))
        else:
            pprint.pprint(tree, indent=2, width=120)
        return 0

    elif ns.cmd == "ir":
        import pathlib
        from .lexer   import lex, LexError
        from .parser  import parse, ParseError
        from .ir      import analyze
        src = pathlib.Path(ns.file).read_text(encoding="utf-8")
        try:
            tree = parse(src, ns.file)
        except (LexError, ParseError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        ir_module, errors = analyze(tree, ns.file)
        for fn in ir_module.functions:
            print(f"\nfn {fn.name}({', '.join(fn.params)}):")
            for bb in fn.blocks:
                print(f"  [{bb.label}]")
                for instr in bb.instrs:
                    print(f"    {instr}")
        if errors:
            for e in errors:
                print(str(e), file=sys.stderr)
        return 0

    elif ns.cmd == "test":
        import pathlib, time as _time2

        result = c.compile_file(ns.file, target=Target.PYTHON)
        if not result.ok:
            _print_errors(result)
            return 1
        # Inject a test-runner tail into the generated Python
        runner = """
import time as _test_time
_passed = _failed = 0
for _fn in _LATERALUS_TESTS:
    _t0 = _test_time.perf_counter()
    try:
        _fn()
        _ms = (_test_time.perf_counter() - _t0) * 1000
        print(f"  \033[92m✓\033[0m  {_fn.__name__}  ({_ms:.2f}ms)")
        _passed += 1
    except Exception as _e:
        _ms = (_test_time.perf_counter() - _t0) * 1000
        print(f"  \033[91m✗\033[0m  {_fn.__name__}  ({_ms:.2f}ms)  →  {_e}")
        _failed += 1
print(f"\n  {_passed} passed  {_failed} failed")
"""
        py_src = result.code + "\n" + runner
        import tempfile, subprocess, pathlib
        tmp = tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w")
        tmp.write(py_src); tmp.close()
        ret = subprocess.run([sys.executable, tmp.name]).returncode
        pathlib.Path(tmp.name).unlink(missing_ok=True)
        return ret

    elif ns.cmd == "doc":
        import pathlib
        path = pathlib.Path(ns.file)
        if not path.exists():
            print(f"error: file not found: {ns.file}", file=sys.stderr)
            return 1
        raw = path.read_text(encoding="utf-8")
        doc = _ltlm_parse(raw)
        if ns.html:
            out_str = _ltlm_html(doc)
        else:
            out_str = _ltlm_ansi(doc)
        if ns.output:
            pathlib.Path(ns.output).write_text(out_str, encoding="utf-8")
            print(f"Written → {ns.output}")
        else:
            print(out_str)
        return 0

    elif ns.cmd == "compile":
        from .binary import compile_file_to_ltlc
        out = compile_file_to_ltlc(ns.file, ns.output)
        print(f"Compiled → {out}")
        return 0

    elif ns.cmd == "decompile":
        import pathlib
        from .binary import decompile_ltlc_to_source
        source = decompile_ltlc_to_source(ns.file)
        if ns.output:
            pathlib.Path(ns.output).write_text(source, encoding="utf-8")
            print(f"Decompiled → {ns.output}")
        else:
            print(source)
        return 0

    elif ns.cmd == "inspect":
        from .binary import ltlc_info
        info = ltlc_info(ns.file)
        for k, v in info.items():
            print(f"  {k}: {v}")
        return 0

    elif ns.cmd == "info":
        from . import __version__
        import pathlib
        stdlib_dir = pathlib.Path(__file__).parent.parent / "stdlib"
        stdlib_modules = sorted(p.stem for p in stdlib_dir.glob("*.ltl")) if stdlib_dir.exists() else []
        print(f"Lateralus Language  v{__version__}")
        print(f"Python backend:     {sys.version.split()[0]}")
        print(f"Stdlib modules:     {len(stdlib_modules)} ({', '.join(stdlib_modules[:12])}{'...' if len(stdlib_modules) > 12 else ''})")
        print(f"Targets:            Python 3 · C99 (hosted/freestanding) · JavaScript (ESM/CJS/IIFE)")
        print(f"                    WebAssembly (WAT) · Bytecode/IR · .ltlc binary")
        print(f"Features (v1.5):    Result/Option · HM type inference · match expressions")
        print(f"                    complex · Matrix · statistics · crypto · LTLM markup")
        print(f"Features (v1.6):    nursery · channels · select · async-for · structured concurrency")
        print(f"Features (v1.7):    lateralus.toml · workspaces · build profiles · @cfg")
        print(f"Features (v1.8):    macro! · comptime · #[derive] · @foreign · metaprogramming")
        print(f"Features (v1.9):    FFI · Jupyter kernel · enhanced REPL · source maps")
        print(f"Features (v2.0):    C99 backend · DAP debugger · optimizer (O0–O3)")
        print(f"Features (v2.1):    JS backend · WASM backend · polyglot runtime")
        print(f"Features (v2.2):    12 new stdlib · 4 linter rules · OS apps (ltlc/chat/edit/pkg)")
        print(f"Features (v2.3):    6 new stdlib · 5 linter rules · LSP code actions/rename")
        print(f"Tooling:            LSP server · DAP server · formatter · linter · benchmarks")
        return 0

    elif ns.cmd == "fmt":
        from .formatter import LateralusFormatter, FormatConfig, format_file
        import pathlib
        config = FormatConfig(indent_size=getattr(ns, "indent", 4))
        files = []
        for f in ns.files:
            p_path = pathlib.Path(f)
            if p_path.is_file() and p_path.suffix == ".ltl":
                files.append(p_path)
            elif p_path.is_dir():
                files.extend(sorted(p_path.rglob("*.ltl")))
        if not files:
            print("No .ltl files found.")
            return 0
        all_ok = True
        for fp in files:
            if not format_file(fp, config, check=getattr(ns, "check", False),
                               diff=getattr(ns, "diff", False)):
                all_ok = False
        if getattr(ns, "check", False):
            if all_ok:
                print("All files are properly formatted.")
            else:
                return 1
        return 0

    elif ns.cmd == "lint":
        from .linter import LateralusLinter
        import pathlib
        linter = LateralusLinter(strict=getattr(ns, "strict", False))
        total_issues = 0
        for f in ns.files:
            p_path = pathlib.Path(f)
            paths = [p_path] if p_path.is_file() else sorted(p_path.rglob("*.ltl"))
            for fp in paths:
                src = fp.read_text(encoding="utf-8")
                result = linter.lint(src, str(fp))
                for issue in result.issues:
                    sev = issue.severity.name
                    print(f"  {fp}:{issue.line}:{issue.col}  [{sev}]  {issue.message}  ({issue.rule})")
                total_issues += len(result.issues)
        if total_issues:
            print(f"\n{total_issues} issue(s) found.")
            return 1
        else:
            print("No issues found.")
            return 0

    elif ns.cmd == "lsp":
        from .lsp_server import main as lsp_main
        lsp_main()
        return 0

    elif ns.cmd == "dap":
        from .dap_server import main as dap_main
        dap_main()
        return 0

    elif ns.cmd == "init":
        from .package_manager import scaffold_project
        import pathlib
        project = scaffold_project(ns.name, pathlib.Path.cwd(),
                                   template=getattr(ns, "template", "default"))
        print(f"Created LATERALUS project: {project}")
        print(f"  cd {ns.name}")
        print(f"  lateralus run src/main.ltl")
        return 0

    elif ns.cmd == "add":
        from .package_manager import (_find_manifest, ProjectManifest,
                                      Dependency)
        manifest_path = _find_manifest()
        if not manifest_path:
            print("No lateralus.toml found. Run 'lateralus init' first.",
                  file=sys.stderr)
            return 1
        manifest = ProjectManifest.from_file(manifest_path)
        dep = Dependency(
            name=ns.package,
            version=getattr(ns, "version", "*"),
            path=getattr(ns, "path", None),
            git=getattr(ns, "git", None),
        )
        if getattr(ns, "dev", False):
            manifest.dev_dependencies[ns.package] = dep
        else:
            manifest.dependencies[ns.package] = dep
        manifest.save(manifest_path)
        print(f"Added {ns.package}@{dep.version}")
        return 0

    elif ns.cmd == "publish":
        from .package_manager import (_find_manifest, ProjectManifest,
                                      PackageBundle)
        manifest_path = _find_manifest()
        if not manifest_path:
            print("No lateralus.toml found.", file=sys.stderr)
            return 1
        manifest = ProjectManifest.from_file(manifest_path)
        bundle = PackageBundle.create(manifest_path.parent, manifest)
        if getattr(ns, "dry_run", False):
            print(f"Would publish {bundle.name}@{bundle.version}")
            print(f"  Files: {len(bundle.files)}")
            print(f"  Size:  {bundle.size:,} bytes")
            print(f"  Integrity: {bundle.integrity}")
            for f in bundle.files[:10]:
                print(f"    {f}")
            if len(bundle.files) > 10:
                print(f"    ... and {len(bundle.files) - 10} more")
        else:
            print(f"Publishing {bundle.name}@{bundle.version}")
            print(f"  (Registry not yet available — use --dry-run to preview)")
        return 0

    elif ns.cmd == "serve":
        import pathlib
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
        from serve_docs import serve as _serve_docs
        docs_dir = pathlib.Path(ns.dir) if ns.dir else None
        _serve_docs(
            port=ns.port,
            docs_dir=docs_dir,
            reload=not getattr(ns, "no_reload", False),
        )
        return 0

    elif ns.cmd == "bench":
        from .bench import run_all_benchmarks
        suites = getattr(ns, "suite", None)
        iterations = getattr(ns, "iterations", 500)
        as_json = getattr(ns, "json", False)
        results = run_all_benchmarks(
            iterations=iterations,
            suites=suites,
            as_json=as_json,
        )
        if as_json:
            import json
            print(json.dumps(results, indent=2))
        else:
            print(results)
        return 0

    elif ns.cmd == "profile":
        import pathlib, time as _ptime
        target_map = {
            "python": Target.PYTHON, "c": Target.C, "js": Target.JAVASCRIPT,
            "wasm": Target.WASM, "check": Target.CHECK,
        }
        target = target_map.get(getattr(ns, "target", "python"), Target.PYTHON)
        repeat = getattr(ns, "repeat", 10)
        src = pathlib.Path(ns.file).read_text(encoding="utf-8")
        fname = pathlib.Path(ns.file).name

        # Phase timing
        from .lexer import lex
        from .parser import parse
        from .ir import analyze

        times_lex = []
        times_parse = []
        times_ir = []
        times_codegen = []
        times_total = []

        for _ in range(repeat):
            t0 = _ptime.perf_counter()
            tokens = lex(src)
            t1 = _ptime.perf_counter()
            tree = parse(src, fname)
            t2 = _ptime.perf_counter()
            ir_mod, _ = analyze(tree, fname)
            t3 = _ptime.perf_counter()
            _result = c.compile_source(src, target=target, filename=fname)
            t4 = _ptime.perf_counter()

            times_lex.append((t1 - t0) * 1000)
            times_parse.append((t2 - t1) * 1000)
            times_ir.append((t3 - t2) * 1000)
            times_codegen.append((t4 - t0) * 1000)
            times_total.append((t4 - t0) * 1000)

        import statistics as _stats
        def _fmt_stat(name, vals):
            return f"  {name:<20} {_stats.mean(vals):>8.3f}ms  ±{_stats.stdev(vals) if len(vals) > 1 else 0:.3f}ms  (min {min(vals):.3f}, max {max(vals):.3f})"

        print(f"Profile: {fname}  ({repeat} iterations, target={getattr(ns, 'target', 'python')})")
        print(f"  {'Source lines:':<20} {len(src.splitlines())}")
        print()
        print(_fmt_stat("Lexer", times_lex))
        print(_fmt_stat("Parser", times_parse))
        print(_fmt_stat("IR Analysis", times_ir))
        print(_fmt_stat("Full Pipeline", times_total))
        return 0

    elif ns.cmd == "disasm":
        import pathlib, pickle
        bc_path = pathlib.Path(ns.file)
        if not bc_path.exists():
            print(f"error: file not found: {ns.file}", file=sys.stderr)
            return 1
        bc = pickle.loads(bc_path.read_bytes())
        from .vm.disassembler import disassemble
        asm_text = disassemble(bc)
        if ns.output:
            pathlib.Path(ns.output).write_text(asm_text, encoding="utf-8")
            print(f"Disassembled → {ns.output}")
        else:
            print(asm_text)
        return 0

    elif ns.cmd == "clean":
        import pathlib, shutil
        root = pathlib.Path(__file__).resolve().parent.parent
        removed = []
        for pat in ["build/", "__pycache__", "*.pyc"]:
            for p in root.rglob(pat):
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    p.unlink(missing_ok=True)
                removed.append(str(p.relative_to(root)))
        if getattr(ns, "all", False):
            for d in ["dist", "lateralus_lang.egg-info"]:
                dp = root / d
                if dp.exists():
                    shutil.rmtree(dp, ignore_errors=True)
                    removed.append(d)
        print(f"Cleaned {len(removed)} items.")
        return 0

    else:
        p.print_help()
        return 0


def _print_errors(result):
    for e in result.errors:
        msg = e.render() if hasattr(e, "render") else str(e)
        print(msg, file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
