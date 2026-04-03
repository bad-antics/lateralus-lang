# LATERALUS Language — Scheduled Advancement Roadmap

> *"Spiral out, keep going."* — The language that grows itself.

This document defines the **scheduled advancement system** for LATERALUS.
Each version builds on the last, with clear milestones and feature gates.

---

## Version History

### v1.0 — Genesis (Complete)
- Core lexer/parser/AST pipeline
- Python transpiler backend
- Bytecode VM (stack-based)
- Basic types: int, float, str, bool, nil
- Control flow: if/elif/else, while, loop, for..in, match
- Functions, closures, lambdas
- Pipelines: `|>`, `|?`
- Try/recover/ensure error handling

### v1.1 — Foundations (Complete)
- Structs with fields and defaults
- Enums with variants (tuple, record, valued)
- Type aliases
- Interfaces and impl blocks
- Generic parameters `<T>`
- Decorators (`@test`, `@memo`)
- `yield` / generators
- `spawn` / concurrency primitives
- `self` keyword
- `pub` visibility

### v1.2 — Polyglot Bridge (Complete)
- `foreign` blocks for Python/JS/R interop
- Polyglot runtime (LaterRuntime)
- VSCode extension with syntax highlighting
- REPL with `lateralus repl`
- `.ltasm` assembler
- 167 test suite

### v1.3 — Error Architecture (Complete)
- `throw` / structured error raising
- `emit` / event system
- `probe` / runtime introspection
- `measure` / timing blocks
- `TryExpr` (try as expression)
- Error DNA fingerprinting
- `pass` statement

### v1.4 — Mathematical Elegance (Complete)
- **Parser**: List comprehensions `[expr for x in iter if cond]`
- **Parser**: Ternary expressions `cond ? a : b`
- **Parser**: Spread operator `...expr`
- **Parser**: Guard clauses `guard cond else { fallback }`
- **Parser**: Where clauses `expr where { let x = val }`
- **Parser**: Pipeline assignment `|>=`
- **Parser**: Error propagation `expr?`
- **Math Engine**: Matrix algebra, FFT, signal processing, optimization
- **Crypto Engine**: SHA-3, BLAKE2, PBKDF2, Fernet encrypt/decrypt
- **Probability**: Distributions, combinatorics, secure random
- **Functional**: compose, pipe, curry, memoize
- **LTLM Markup**: Own markup language with parser + HTML/ANSI renderers
- **Binary Format**: `.ltlc` proprietary compiler/decompiler
- **Error Handler**: Stack traces, context windows, error chains, auto-suggest
- **Stdlib**: linalg.ltl, stats.ltl, crypto.ltl

---

## Upcoming Versions

### v1.5 — Type System & ADTs (Complete)
- [x] **AST**: `TypeMatchExpr`, `TypeMatchArm`, all `Pattern` subtypes, `ResultExpr`, `OptionExpr`
- [x] **Lexer**: `DOUBLE_COLON` token (`::`) for variant syntax
- [x] **Parser**: `_parse_pattern()`, `_parse_type_match_expr()` — match as expression
- [x] **Parser**: `Result::Ok(v)` / `Result::Err(e)` / `Option::Some(v)` / `Option::None` constructors
- [x] **Type System**: `occurs_check()`, `unify()` (Robinson HM), `substitute()`, `solve()`, `infer_pattern()`
- [x] **Codegen**: Python transpiler for all v1.5 constructs
- [x] **C Backend**: C99 transpiler with hosted and freestanding modes
- [x] **LateralusOS**: Bare-metal OS with preemptive scheduler, IPC message queues, 18 syscalls (~550KB kernel)
- [x] **Bootstrap**: Self-hosted IR code generator (`v2_ir_codegen.ltl`, ~500 lines, SSA-like IR from AST)
- [x] **Tests**: 1,304 tests passing, 0 failures
- [x] **Optional types**: `int?` syntax with compiler-enforced nil checks
- [x] **Generics with trait bounds**: `fn sort<T: Comparable>(items: list<T>)`
- [x] **Const generics**: `Matrix<N: int, M: int>` parameter syntax
- [x] **Type narrowing**: `TypeNarrower` for flow-sensitive nil/type analysis in conditionals
- [x] Gradual typing (typed + untyped interop)
- [x] Type error reporting integration in LSP

### v1.6 — Concurrency & Async (Complete)
- [x] Structured concurrency (nursery model)
- [x] Channels: `let ch = channel<int>(10)`
- [x] Select statement for channel multiplexing
- [x] Async iterators / async for
- [x] Cancellation tokens
- [x] Parallel map/filter/reduce
- [x] **AST**: `SelectStmt`, `SelectArm`, `ChannelExpr`, `NurseryBlock`, `CancelExpr`, `AsyncForStmt`, `ParallelExpr`
- [x] **Lexer**: `KW_SELECT`, `KW_NURSERY`, `KW_CANCEL` keywords
- [x] **Parser**: `select { recv | send | timeout | default }`, `nursery { ... }`, `async for`, `channel<T>(cap)`, `cancel`, `parallel_*`
- [x] **Runtime**: `CancellationToken`, `Nursery` (structured concurrency), `select()`, `parallel_reduce()`
- [x] **Codegen**: Python transpiler for all v1.6 constructs
- [x] **Tests**: 1,372 tests passing, 0 failures

### v1.7 — Package Manager & Build System (Complete)
- [x] `lateralus.toml` package manifest (with bundled TOML parser)
- [x] Dependency resolution (semver with compound constraints, dep graph, cycle detection)
- [x] Package registry support (lateralus.dev/packages)
- [x] `lateralus init`, `lateralus add`, `lateralus publish` CLI commands
- [x] Workspaces (multi-package projects with glob member resolution)
- [x] Build profiles (debug/release/bench + custom)
- [x] Conditional compilation (`@cfg(target, "python")`, `cfg!(key, "value")`)
- [x] **AST**: `CfgAttr`, `CfgExpr` nodes
- [x] **Parser**: `cfg!(key, "value")` compile-time boolean
- [x] **Codegen**: `@cfg` decorator stripping, `cfg!()` evaluation via `CfgContext`
- [x] **Package Manager**: `ProjectManifest`, `SemVer`, `DepGraph`, `DependencyResolver`, `PackageBundle`, `LockFile`
- [x] **Tests**: 1,443 tests passing, 28 compiling examples

### v1.8 — Metaprogramming ✅
- [x] Compile-time evaluation (`const fn`)
- [x] Procedural macros (`macro name!(params) { body }`)
- [x] AST transformation hooks (`quote { ... }`, `$ident` unquote)
- [x] Code generation from schemas (`@derive(Debug, Clone, Eq, Hash, Default, Serialize, Deserialize, Display)`)
- [x] Reflection API (`reflect!(Type)` → `_type_info`)
- [x] Custom attributes/decorators with compile-time effects (`comptime { ... }`)
- [x] **Tests**: 56 new tests covering lexer, parser, codegen, and integration

### v1.9 — FFI & Ecosystem (Complete)
- [x] **C FFI Bridge**: `load_library()`, `FFIFunction`, `FFIRegistry`, `define_ffi_struct()`, memory utilities (alloc/free/read/write)
- [x] **WASM Target**: `lateralus wasm file.ltl` — compile to WebAssembly Text Format (.wat)
- [x] **JavaScript Target**: `lateralus js file.ltl` — transpile to JS (ESM/CJS/IIFE formats)
- [x] **Jupyter Kernel**: `LateralusKernel` with execute, complete, inspect, `install_kernel()`, ipykernel integration
- [x] **C Backend v1.7/v1.8 Visitors**: const fn, macros, comptime, cfg, nursery, async for, channels, cancel, derive, reflect, quote/unquote
- [x] **AST/Compiler**: `Target.JAVASCRIPT`, `Target.WASM` in enum; `js_src`, `wasm_src` in `CompileResult`
- [x] **CLI**: `lateralus js`, `lateralus wasm` subcommands with output file support
- [x] **LateralusOS**: Network shell commands — `ifconfig`, `ping`, `netstat`, `arp` (21 total commands)
- [x] **Tests**: 1,549 tests passing, 30 compiling examples, 0 failures
- [x] Language server protocol (LSP) v2
- [x] Debugger adapter protocol (DAP)

### v2.0 — Self-Hosting (Complete)
- [x] **Bootstrap Compiler**: 5 compiler modules written in Lateralus (`v2_lexer.ltl`, `v2_parser.ltl`, `v2_codegen.ltl`, `v2_ir_codegen.ltl`, `v2_python_codegen.ltl`) — all compile with the production compiler
- [x] **Bootstrap Parser**: 55 node types, 15+ parse functions (struct, enum, match, trait, impl, for, while, try, lambda, pipe, spread, decorators, async/await)
- [x] **Bootstrap Codegen**: Python code generator (~500 lines) with full AST visitor, expression/statement/declaration handling
- [x] **Grammar Specification**: Formal EBNF grammar (`docs/grammar.ebnf`) updated to v2.0 — 458 lines covering all v1.0–v1.9 features (structured concurrency, metaprogramming, FFI, traits, type aliases)
- [x] **v2.0 Showcase**: `v20_showcase.ltl` (310 lines) — self-hosting compiler pipeline with tokenizer, parser, multi-target code generator, verification suite
- [x] **LateralusOS v0.2.0**: 7 new shell commands (`whoami`, `hostname`, `date`, `ps`, `sysinfo`, `cal`, `write`) — 28 total; CMOS RTC date/time, CPUID vendor detection, ramfs file writing
- [x] **Tests**: 1,638 tests passing, 30 compiling examples, 0 failures

### v2.1 — Kernel Decomposition & Network Stack (Complete)
- [x] **Heap Module**: Extracted heap allocator into `kernel/heap.{h,c}` — kmalloc/kcalloc/krealloc/kfree with free-list, block splitting (MIN_SPLIT=64), 16-byte alignment, double-free detection
- [x] **VFS Layer**: Full virtual file system in `fs/vfs.{h,c}` (~460 lines) — 32 fd/task, FILE/CONSOLE/PIPE_READ/PIPE_WRITE/NULL types, open/read/write/close/seek/dup/dup2/pipe, auto-allocates fd 0/1/2
- [x] **Syscall Expansion**: 23 handlers in `kernel/syscall.{h,c}` — VFS-backed file ops, sys_pipe, sys_dup, sys_spawn, sys_wait, sys_kill
- [x] **Shell Pipe & Redirect**: Capture buffer infrastructure in k_putc; pipe (`|`) with grep/wc/head/tail targets; redirect `>` (overwrite) and `>>` (append) to ramfs files
- [x] **IPv4/ARP/UDP/ICMP/DHCP Stack**: Full network implementation in `net/ip.{h,c}` (~930 lines) — ARP cache, IPv4 routing, ICMP echo, UDP port binding, DHCP client with auto-discover at boot
- [x] **DNS Resolver**: Domain name resolution in `net/dns.{h,c}` — 16-entry LRU cache, UDP query builder, response parser, `nslookup` and `dns` shell commands
- [x] **Process Table & Scheduler Upgrade**: Extended SchedTask with parent-child tracking (parent_tid, wait_tid). New: `sched_wait()` (blocks parent, returns exit code), `sched_reap()` (frees dead task stacks), `sched_get_task()`. Fixed sys_getpid/sys_sleep/sys_yield to use scheduler. Periodic dead-task reaping (~1s).
- [x] **TCP Transport Layer**: Full TCP/IP in `net/tcp.{h,c}` (~650 lines) — RFC 793 state machine (11 states), 8 connections, 4KB circular recv buffers, connect/listen/send/read/close, pseudo-header checksum, retransmit timer (3s, 5 retries), TIME_WAIT cleanup, `tcp` shell command
- [x] **Shell `spawn` Command**: Spawn background tasks from shell — heartbeat, counter, netpoll daemons with priority control
- [x] **Live `ps` Rewrite**: Real scheduler data with TID/STATE/PRIO/NAME, color-coded states
- [x] **Netpoll Daemon**: Auto-spawned at boot (PRIO_HIGH), drives ip_poll() + tcp_tick() at 10Hz
- [x] **Upgraded Commands**: `ifconfig`, `ping`, `arp`, `dhcp`, `nslookup`, `dns`, `tcp`, `spawn`, `ps` — 33+ total shell commands
- [x] **Codegen Fixes**: Block lambda transpilation, interface ABC generation, type annotation mapping, stdlib shims, C backend _temp() fix
- [x] **v2.1 Showcase**: `v21_showcase.ltl` (401 lines) — enum pattern matching, interface dispatch, pipelines, result types, state machines
- [x] **LateralusOS v0.3.0**: 22-step build pipeline, ~696KB kernel, zero warnings, all subsystems boot successfully
- [x] **Tests**: 1,670 tests passing, 30+ compiling examples, 0 failures

### v2.2 — Stdlib Expansion & Linter Intelligence (Complete)
- [x] **12 New Stdlib Modules** (total: 49): `fmt`, `encoding`, `csv`, `logging`, `filepath`, `uuid`, `hash`, `color`, `queue`, `stack`, `base64`, `bitset`
- [x] **4 New Linter Rules**: `unreachable-code` (dead code after return/break/continue), `duplicate-import` (repeated module imports), `shadowed-variable` (variable shadows earlier definition), `todo-comment` (surfaces TODO/FIXME/HACK/XXX)
- [x] **IR**: Added `COND_SELECT` opcode for ternary conditional selection
- [x] **LateralusOS**: /proc filesystem (9 virtual files: version, uptime, meminfo, cpuinfo, loadavg, tasks, net, mounts, cmdline), /dev filesystem (5 device files: null, zero, random, serial, fb0), signal infrastructure, shell $VAR expansion, alias system, bang history, load average tracking
- [x] **v22 Showcase**: `v22_showcase.ltl` demonstrating hashing, color manipulation, UUID generation, pipelines, pattern matching, struct methods
- [x] **Tests**: 1,734 tests passing, 0 failures

### v2.3 — Tooling & OS Expansion (Complete)
- [x] **6 New Stdlib Modules** (total: 52): `sort`, `set`, `ringbuf`, `semver`, `event`, `template`
- [x] **5 New Linter Rules** (total: 21+): `constant-condition`, `unused-import`, `deep-nesting`, `string-concat-in-loop`, `mutable-default`
- [x] **Formatter**: Trailing comma normalization (phase 7), blank line collapse (phase 8)
- [x] **LSP Server**: 4 code action quick-fixes, rename symbol, prepare rename
- [x] **Examples**: `v23_showcase.ltl`, `game_of_life.ltl`, `interpreter_demo.ltl` (total: 37)
- [x] **LateralusOS**: 7 new shell commands (`top`, `df`, `id`, `seq`, `tr`, `tac`, `nl`) — total: 55+
- [x] **Tests**: 1,769 tests passing, 0 failures

### v2.4 — Deep Internals, Optimizer & Stdlib Expansion (Complete)
- [x] **VM Disassembler** (`vm/disassembler.py`, ~300 lines): Full bytecode-to-assembly decompiler with round-trip verification
- [x] **4 New CLI Subcommands** (total: 26): `bench`, `profile`, `disasm`, `clean`
- [x] **Enhanced REPL**: 3 new commands (`:save`, `:doc`, `:profile`), 51 builtin doc entries, profiler
- [x] **3 New Optimizer Passes** (total: 10): dead branch elimination, algebraic simplification (20 identities), function inlining analysis
- [x] **7 New Stdlib Modules** (total: 59): `heap`, `deque`, `trie`, `ini`, `arena`, `pool`, `lru`
- [x] **207 New Tests** (total: 1,976): 52 DAP server, 47 REPL, 61 VM expanded, 47 optimizer
- [x] **Tests**: 1,976 tests passing, 0 failures

---

## Advancement Rules

1. **No version ships with failing tests.** Ever.
2. **Every feature gets at least 3 tests** before merge.
3. **Backward compatibility** is sacred — old .ltl files must always work.
4. **The Python transpiler is the reference implementation** until v2.0.
5. **Version bumps follow semver** within the 1.x series.
6. **Feature flags** gate experimental features: `@experimental("async_iterators")`

---

## Feature Flag Registry

| Flag | Version | Status |
|------|---------|--------|
| `comprehensions` | 1.4 | Stable |
| `ternary` | 1.4 | Stable |
| `spread` | 1.4 | Stable |
| `guard` | 1.4 | Stable |
| `where_clause` | 1.4 | Stable |
| `pipe_assign` | 1.4 | Stable |
| `propagation` | 1.4 | Stable |
| `ltlm_markup` | 1.4 | Stable |
| `ltlc_binary` | 1.4 | Stable |
| `type_inference` | 1.5 | Stable |
| `adt_patterns`   | 1.5 | Stable |
| `optional_types` | 1.5 | Stable |
| `trait_bounds`   | 1.5 | Stable |
| `const_generics` | 1.5 | Stable |
| `type_narrowing` | 1.5 | Stable |
| `c_backend`      | 1.5 | Stable |
| `wasm_backend`   | 1.5 | Stable |
| `js_backend`     | 1.5 | Stable |
| `os_scheduler`   | 1.5 | Stable |
| `os_ipc`         | 1.5 | Stable |
| `bootstrap_ir`   | 1.5 | Experimental |
| `channels` | 1.6 | Stable |
| `select` | 1.6 | Stable |
| `nursery` | 1.6 | Stable |
| `cancel_token` | 1.6 | Stable |
| `async_for` | 1.6 | Stable |
| `parallel_combinators` | 1.6 | Stable |
| `packages` | 1.7 | Stable |
| `macros` | 1.8 | Stable |
| `const_fn` | 1.8 | Stable |
| `derive` | 1.8 | Stable |
| `reflect` | 1.8 | Stable |
| `ffi` | 1.9 | Stable |
| `js_target` | 1.9 | Stable |
| `wasm_target` | 1.9 | Stable |
| `jupyter_kernel` | 1.9 | Stable |
| `self_hosting` | 2.0 | Stable |
| `os_heap_module` | 2.1 | Stable |
| `os_vfs` | 2.1 | Stable |
| `os_pipe_redirect` | 2.1 | Stable |
| `os_ip_stack` | 2.1 | Stable |
| `os_dhcp` | 2.1 | Stable |
| `stdlib_fmt` | 2.2 | Stable |
| `stdlib_encoding` | 2.2 | Stable |
| `stdlib_csv` | 2.2 | Stable |
| `stdlib_logging` | 2.2 | Stable |
| `stdlib_filepath` | 2.2 | Stable |
| `lint_unreachable` | 2.2 | Stable |
| `lint_duplicate_import` | 2.2 | Stable |
| `lint_shadowed_var` | 2.2 | Stable |
| `lint_todo_comment` | 2.2 | Stable |
| `os_signals` | 2.2 | Stable |
| `os_aliases` | 2.2 | Stable |
| `os_load_average` | 2.2 | Stable |
| `os_procfs` | 2.2 | Stable |
| `os_devfs` | 2.2 | Stable |
| `stdlib_uuid` | 2.2 | Stable |
| `stdlib_hash` | 2.2 | Stable |
| `stdlib_color` | 2.2 | Stable |
| `stdlib_queue` | 2.2 | Stable |
| `stdlib_stack` | 2.2 | Stable |
| `stdlib_base64` | 2.2 | Stable |
| `stdlib_bitset` | 2.2 | Stable |
| `stdlib_sort` | 2.3 | Stable |
| `stdlib_set` | 2.3 | Stable |
| `stdlib_ringbuf` | 2.3 | Stable |
| `stdlib_semver` | 2.3 | Stable |
| `stdlib_event` | 2.3 | Stable |
| `stdlib_template` | 2.3 | Stable |
| `lint_constant_condition` | 2.3 | Stable |
| `lint_unused_import` | 2.3 | Stable |
| `lint_deep_nesting` | 2.3 | Stable |
| `lint_string_concat_loop` | 2.3 | Stable |
| `lint_mutable_default` | 2.3 | Stable |
| `lsp_code_actions` | 2.3 | Stable |
| `lsp_rename` | 2.3 | Stable |
| `fmt_trailing_comma` | 2.3 | Stable |
| `fmt_blank_collapse` | 2.3 | Stable |
| `vm_disassembler` | 2.4 | Stable |
| `cli_bench` | 2.4 | Stable |
| `cli_profile` | 2.4 | Stable |
| `cli_disasm` | 2.4 | Stable |
| `cli_clean` | 2.4 | Stable |
| `repl_save` | 2.4 | Stable |
| `repl_doc` | 2.4 | Stable |
| `repl_profile` | 2.4 | Stable |
| `opt_dead_branch` | 2.4 | Stable |
| `opt_algebraic` | 2.4 | Stable |
| `opt_inline_analysis` | 2.4 | Stable |
| `stdlib_heap` | 2.4 | Stable |
| `stdlib_deque` | 2.4 | Stable |
| `stdlib_trie` | 2.4 | Stable |
| `stdlib_ini` | 2.4 | Stable |
| `stdlib_arena` | 2.4 | Stable |
| `stdlib_pool` | 2.4 | Stable |
| `stdlib_lru` | 2.4 | Stable |

---

## Contributing

LATERALUS is a solo project by **antics**. Contributions welcome after v1.5.

*Last updated: v2.4.0*
