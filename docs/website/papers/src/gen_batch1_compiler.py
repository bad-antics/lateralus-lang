#!/usr/bin/env python3
"""Batch generator — Compiler papers (batch 1): zero-to-language, bootstrapping-compiler-python,
from-lexer-to-language, lexer-design-pipeline-first, error-messages-as-documentation."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lateralus_template import render_paper

PDF = Path(__file__).resolve().parents[1] / "pdf"

# ── 1. zero-to-language ───────────────────────────────────────────────────────
render_paper(
    out_path=str(PDF / "zero-to-language.pdf"),
    title="From Zero to a Working Language",
    subtitle="The Lateralus bootstrapping story: Python prototype to self-hosted compiler",
    meta="bad-antics &middot; February 2026 &middot; Lateralus Language Research",
    abstract=(
        "Building a self-hosting compiler is the traditional milestone for a new programming "
        "language: the compiler must compile itself, and the output must be bit-identical across "
        "generations. Lateralus achieved self-hosting in v0.5 after four bootstrap stages spanning "
        "eighteen months: a Python prototype, a C99 implementation, a partial Lateralus rewrite, "
        "and finally a fully self-hosted Lateralus compiler. This paper narrates the bootstrapping "
        "story in full — the design decisions that were made differently at each stage, the bugs "
        "discovered during the process, the language features that had to be rethought when the "
        "compiler tried to compile itself, and the engineering lessons that shaped the current "
        "production compiler. The paper is intended for language implementers who are planning a "
        "bootstrap strategy and for Lateralus contributors who need historical context."
    ),
    sections=[
        ("1. Motivation for a Self-Hosted Compiler", [
            "A self-hosting compiler is more than a technical milestone. It is the moment at which "
            "the language becomes capable of expressing its own implementation — the point at which "
            "the language designer can use the language they are building to solve the hardest "
            "problem in their domain. Languages that never reach self-hosting remain perpetually "
            "dependent on a foreign implementation language, accumulating a conceptual debt that "
            "makes it harder to add features, harder to optimize, and harder to attract contributors "
            "who want to work in the language itself.",
            "For Lateralus, the self-hosting milestone was planned from the beginning. The "
            "bootstrapping roadmap was written before the first line of the Python prototype: "
            "Stage 0 (Python) compiles a minimal subset, Stage 1 (C99) compiles a production "
            "subset, Stage 2 (partial Lateralus) validates the type system and standard library, "
            "Stage 3 (full Lateralus) compiles the entire compiler and is the only stage shipped "
            "to users. Each stage has a defined scope, a defined exit criterion, and a defined "
            "test that must pass before the next stage begins.",
            "The exit criterion for each stage is the 'triple-convergence test': compile the "
            "compiler with stage N, use the output to compile the compiler, then compile it again "
            "and verify bit-identical output between the second and third generation. This test "
            "catches both semantic bugs (a compiler that produces incorrect code) and "
            "non-determinism bugs (a compiler that produces different code on repeated runs).",
            ("h3", "1.1 The Cost of Foreign Bootstraps"),
            "Languages that are permanently implemented in a foreign language pay ongoing costs. "
            "The compiler is not a first-class consumer of the language's own semantics, so "
            "semantic bugs in the language design are often not caught until they are expressed "
            "as user bugs years later. Contributors must know two languages. Performance "
            "optimizations in the foreign language cannot be expressed in the new language, "
            "leading to a perpetual performance gap that discourages adoption.",
            "Lateralus's bootstrapping investment paid off immediately during Stage 2: the act "
            "of writing the type checker in Lateralus exposed three fundamental problems with the "
            "row-polymorphism semantics that had been invisible in the C99 implementation. The "
            "C99 type checker had worked around them implicitly; the Lateralus type checker "
            "could not, and the language had to be corrected before Stage 2 could proceed.",
        ]),
        ("2. Stage 0: The Python Prototype", [
            "The Python prototype was written in three weeks by one person. It targeted a "
            "minimal subset of Lateralus: integer and boolean arithmetic, let bindings, "
            "function definitions, function calls, the total pipeline operator, and pattern "
            "matching on enumerated types. The output was C99 source code passed through "
            "a system C compiler.",
            "The choice of Python was deliberate. The language design was not finalized at "
            "Stage 0 entry: the pipeline operator syntax had three candidate forms, the "
            "error propagation mechanism had two competing proposals, and the ownership "
            "system had not been specified at all. Python's interactive shell allowed "
            "design experiments at runtime: a candidate syntax could be implemented in "
            "thirty minutes, tested against real programs, and discarded before lunch.",
            ("code",
             "# Stage 0 Python: parsing a pipeline expression\n"
             "def parse_pipeline(self) -> Expr:\n"
             "    left = self.parse_application()\n"
             "    while self.peek() in ('|>', '|?>', '|>>', '|>|'):\n"
             "        op = self.consume()\n"
             "        right = self.parse_application()\n"
             "        left = PipelineExpr(op=op, lhs=left, rhs=right,\n"
             "                            loc=self.current_loc())\n"
             "    return left\n\n"
             "# Python prototype: emit a total pipeline as a C function call\n"
             "def emit_pipeline(self, node: PipelineExpr) -> str:\n"
             "    left_c  = self.emit_expr(node.lhs)\n"
             "    right_c = self.emit_expr(node.rhs)\n"
             "    match node.op:\n"
             "        case '|>':  return f'{right_c}({left_c})'\n"
             "        case '|?>': return f'ltl_result_bind({left_c}, {right_c})'\n"
             "        case '|>>': return f'ltl_future_then({left_c}, {right_c})'"),
            "The prototype settled two design questions immediately. The <code>-></code> "
            "syntax originally proposed for pipelines was rejected because it conflicted "
            "visually with the function type arrow. The <code>|></code> form was adopted "
            "from day one of Stage 0 and has not changed. The error propagation operator "
            "was initially proposed as <code>?></code> (modeled on Rust's <code>?</code> "
            "postfix operator) but was changed to <code>|?></code> to maintain visual "
            "consistency with the total operator — a decision that proved correct when "
            "reviewing mixed pipelines where operator shape conveys information.",
            "The prototype's type checker was intentionally incomplete: it handled only "
            "monomorphic types and rejected any program that required polymorphism. This "
            "was acceptable because Stage 0's purpose was to validate the pipeline "
            "semantics, not the type system. The type system was designed on paper "
            "during Stage 0 while the prototype validated everything else.",
            ("h3", "2.1 Prototype Limitations"),
            "The Python prototype had five known limitations that were accepted at design time. "
            "It could not compile pipelines with more than eight stages (a hard-coded limit "
            "in the C output generator to avoid stack overflow in early test programs). "
            "It could not compile mutually recursive functions (the resolver did a single "
            "left-to-right pass with no forward reference resolution). It had no memory "
            "management (all allocations were stack-local and there was no <code>free</code>). "
            "It had no module system (all programs were single-file). It produced no error "
            "messages for type errors, only assertion failures with a Python traceback.",
            "These limitations were features, not bugs: they forced all Stage 0 test programs "
            "to be simple enough that they were unambiguously correct, making the prototype "
            "useful as a validation reference for later stages. A prototype that tried to "
            "do everything would have been neither fast to write nor trustworthy as a reference.",
        ]),
        ("3. Stage 0 Architecture and Design Decisions", [
            "The Stage 0 compiler has five phases connected by data structures, not by shared "
            "mutable state. Each phase takes a tree and returns a transformed tree. This "
            "architecture was chosen specifically because it makes each phase independently "
            "testable: a test for the parser does not require a working type checker.",
            ("code",
             "# Stage 0 pipeline: source → tokens → CST → resolved AST → typed AST → C99\n"
             "def compile(source: str, output_path: str) -> None:\n"
             "    tokens  = Lexer(source).lex()\n"
             "    cst     = Parser(tokens).parse_module()\n"
             "    ast     = Resolver(cst).resolve()\n"
             "    typed   = TypeChecker(ast).check()\n"
             "    c_code  = Emitter(typed).emit_module()\n"
             "    Path(output_path).write_text(c_code)"),
            "The lexer is a hand-written DFA driven by a character-class table. "
            "The decision not to use a lexer generator (like PLY or ANTLR) was pragmatic: "
            "the pipeline operators require two-character lookahead for disambiguation, "
            "and every lexer generator tested either did not support it cleanly or "
            "produced slower code than the hand-written version. The hand-written lexer "
            "was 120 lines of Python and took four hours to write, including tests.",
            "The parser is a recursive-descent parser with explicit operator precedence. "
            "The grammar is encoded as methods on the Parser class, one method per "
            "grammar production. This encoding has a well-known problem: left-recursive "
            "grammars cause infinite recursion. The Lateralus grammar was specifically "
            "designed to be non-left-recursive, partially because of this limitation "
            "and partially because non-left-recursive grammars produce better error messages.",
            ("h3", "3.1 The Resolver Phase"),
            "The resolver performs scope analysis: it walks the AST, builds a symbol table, "
            "and rewrites every variable reference to include the definition it refers to. "
            "The output of the resolver is an AST where every identifier has been replaced "
            "by a fully qualified reference to a specific binding. This eliminates all "
            "name-shadowing ambiguity before type checking begins.",
            "Stage 0's resolver did not support closures (it rejected any function that "
            "referenced a variable from an enclosing scope) and did not support overloading. "
            "Both limitations were removed in Stage 1. The resolver in Stage 0 was "
            "approximately 200 lines and covered only the subset needed by the Stage 1 "
            "compiler source. This was a deliberate bootstrapping constraint: Stage 0 only "
            "needed to compile Stage 1, not arbitrary Lateralus programs.",
        ]),
        ("4. Stage 1: The C99 Implementation", [
            "Stage 1 rewrote the compiler in C99 with a complete front-end, a full type "
            "system, and an LLVM-based backend. The Stage 1 compiler was the first version "
            "that could compile programs of practical size, including programs with polymorphic "
            "functions, modules, and closures. Development took four months with two people.",
            "The C99 language was chosen for Stage 1 for three reasons. First, C99 compilers "
            "are available on every platform Lateralus targets; there is no bootstrapping "
            "problem. Second, C99 gives direct control over memory layout, which was "
            "essential for implementing the Lateralus value representation (NaN-boxing for "
            "the REPL, tagged unions for the compiler). Third, C99 interoperates directly "
            "with LLVM, which was the chosen backend for Stage 1.",
            ("code",
             "/* Stage 1 C99: core AST node types */\n"
             "typedef enum {\n"
             "    AST_VAR, AST_INT, AST_BOOL, AST_STRING,\n"
             "    AST_LET, AST_FN, AST_CALL, AST_PIPELINE,\n"
             "    AST_MATCH, AST_IF, AST_BLOCK, AST_MODULE,\n"
             "    AST_RECORD, AST_VARIANT, AST_IMPORT\n"
             "} AstKind;\n\n"
             "typedef struct AstNode {\n"
             "    AstKind       kind;\n"
             "    SourceLoc     loc;\n"
             "    struct Type  *type;   /* filled by type checker */\n"
             "    union {\n"
             "        struct { char *name; struct AstNode *defn; } var;\n"
             "        struct { struct AstNode *lhs, *rhs; PipeVariant pv; } pipe;\n"
             "        struct { struct AstNode **args; int nargs; } call;\n"
             "        /* ... */\n"
             "    };\n"
             "} AstNode;"),
            "The Stage 1 type checker implemented the full Lateralus type system: "
            "Hindley-Milner type inference, row-polymorphic records, effect types, "
            "and the four pipeline operator typing rules. This was the most technically "
            "challenging part of Stage 1: the interaction between row polymorphism and "
            "error propagation in the <code>|?></code> operator required a non-standard "
            "unification algorithm that extended Robinson's original formulation with "
            "row variable constraints.",
            "The Stage 1 LLVM backend reused LLVM's existing register allocator, "
            "instruction selector, and machine code emitter. The Lateralus compiler's "
            "job was to lower the Lateralus HIR (high-level IR) to LLVM IR, including "
            "the pipeline-specific optimizations (stage fusion, error corridor construction) "
            "that LLVM could not perform without knowledge of the pipeline semantics.",
            ("h3", "4.1 Type System Challenges in C99"),
            "Implementing a type system in C99 is significantly harder than implementing "
            "one in a language with algebraic data types and pattern matching. The C99 "
            "type checker used tagged unions with explicit switch statements, which "
            "produced approximately 2x the code volume of the equivalent Stage 2 "
            "Lateralus implementation. More importantly, the C99 switch statements could "
            "not be exhaustiveness-checked: adding a new type constructor required "
            "manually finding and updating every switch statement, and missing cases "
            "produced silent undefined behavior rather than a compile-time error.",
            "This was the primary motivation for Stage 2: the type checker had grown to "
            "4,000 lines of C99 and was becoming unmaintainable. Three bugs in the "
            "row-polymorphism handling were traced to missing cases in deeply nested switch "
            "statements where the default branch silently continued rather than aborting. "
            "The equivalent Lateralus code would have been caught by the exhaustiveness checker.",
        ]),
        ("5. Stage 1: LLVM Backend Design", [
            "The LLVM backend is the component that translates Lateralus HIR to LLVM IR. "
            "The translation is structured as a series of lowering passes, each of which "
            "reduces one level of abstraction. The pipeline-specific passes (fusion, "
            "error corridor) run before the LLVM IR is produced; LLVM then applies its "
            "own optimization pipeline to the resulting IR.",
            "The most important pipeline-specific pass is stage fusion. When the fusion "
            "pass identifies two consecutive total pipeline stages where the first stage's "
            "output is the only consumer of the second stage's input, it merges them into "
            "a single HIR node. The fused node is then lowered to LLVM as a single function "
            "call or, if both stages are small enough, as inlined code. The elimination "
            "of intermediate allocations is the primary performance benefit.",
            ("code",
             "/* Stage 1 LLVM backend: lower a pipeline to LLVM IR (simplified) */\n"
             "static LLVMValueRef lower_pipeline(Backend *b, AstNode *pipe) {\n"
             "    /* Collect stages from the left-balanced pipeline tree */\n"
             "    Stage stages[MAX_STAGES];\n"
             "    int nstages = collect_stages(pipe, stages);\n\n"
             "    /* Apply fusion pass: merge consecutive fusable stages */\n"
             "    nstages = fuse_stages(b, stages, nstages);\n\n"
             "    /* Apply error-corridor pass: merge all error exits */\n"
             "    LLVMBasicBlockRef err_exit = NULL;\n"
             "    if (has_error_stages(stages, nstages))\n"
             "        err_exit = LLVMAppendBasicBlock(b->fn, \"pipeline_err_exit\");\n\n"
             "    /* Emit each stage */\n"
             "    LLVMValueRef val = lower_expr(b, pipe->pipe.lhs_input);\n"
             "    for (int i = 0; i < nstages; i++)\n"
             "        val = lower_stage(b, &stages[i], val, err_exit);\n"
             "    return val;\n"
             "}"),
            "The LLVM backend was tested against the Stage 0 Python compiler using "
            "differential testing: the same programs were compiled by both, the outputs "
            "were run on the same inputs, and the results were compared. Any divergence "
            "was a bug in Stage 1. The differential test corpus grew from 200 programs "
            "(inherited from Stage 0) to 4,000 programs over the four months of Stage 1 "
            "development, with new programs added for every bug fixed.",
            "Performance benchmarking of Stage 1 showed that the LLVM backend produced "
            "code that was 8-12x faster than the C99 output from Stage 0. The primary "
            "contributors were: LLVM's register allocation (Stage 0 spilled all values "
            "to the stack), LLVM's instruction scheduling (Stage 0 emitted instructions "
            "in source order), and the error-corridor optimization (Stage 0 emitted "
            "three error branches per <code>|?></code> operator).",
            ("h3", "5.1 RISC-V Backend in Stage 1"),
            "Stage 1 added a RISC-V backend alongside the x86-64 backend inherited from "
            "Stage 0's C99 output. The RISC-V backend targets RV64GC (the base 64-bit "
            "integer ISA plus the compressed instruction extension). LLVM handles both "
            "backends from the same IR; the Lateralus compiler only needs to choose the "
            "LLVM target triple at startup. The RISC-V backend was validated on QEMU "
            "before any physical RISC-V hardware was available.",
        ]),
        ("6. Stage 2: Partial Lateralus Rewrite", [
            "Stage 2 replaced the Stage 1 C99 front-end with Lateralus while keeping "
            "the LLVM backend in C99. This was not the original plan: the original plan "
            "was to complete Stage 1 and proceed directly to Stage 3. Stage 2 was added "
            "when the Stage 1 type checker accumulated enough technical debt (4,000 lines "
            "of C99, three known bugs) that it became more efficient to rewrite it in "
            "Lateralus than to fix the C99 version.",
            "The Stage 2 front-end was written in the subset of Lateralus that Stage 1 "
            "could compile. This created a dependency: Stage 2 could only use language "
            "features that Stage 1 had already implemented correctly. In practice, this "
            "meant that Stage 2 could not use closures (Stage 1's closure handling had "
            "a known bug), higher-kinded types (not yet implemented), or any standard "
            "library function that relied on closures.",
            ("code",
             "-- Stage 2 Lateralus: type checker for the pipeline operators\n"
             "fn check_pipeline(\n"
             "    env: &TypeEnv,\n"
             "    lhs: &TypedExpr,\n"
             "    rhs: &Expr,\n"
             "    variant: PipeVariant,\n"
             ") -> Result<Type, TypeError> {\n"
             "    match variant {\n"
             "        PipeVariant::Total => {\n"
             "            let rhs_type = infer(env, rhs)?;\n"
             "            let (param, ret) = rhs_type\n"
             "                |?> unify_fun_type\n"
             "                |?> |r| unify(lhs.type, r.param)\n"
             "                |>  |_| r.ret;\n"
             "            Ok(ret)\n"
             "        }\n"
             "        PipeVariant::Error => {\n"
             "            let (ok_type, err_type) = lhs.type\n"
             "                |?> unify_result_type;\n"
             "            let rhs_type = infer(env, rhs)?;\n"
             "            let (param, ret) = rhs_type |?> unify_fun_type;\n"
             "            unify(ok_type, param)?;\n"
             "            Ok(Type::Result { ok: ret, err: err_type })\n"
             "        }\n"
             "    }\n"
             "}"),
            "Writing the type checker in Lateralus immediately exposed three bugs in "
            "the Stage 1 type checker. The first bug was in the row variable unification: "
            "the C99 implementation had an off-by-one error in the occurs check that "
            "allowed circular types to be inferred for certain polymorphic record patterns. "
            "The second bug was in error type propagation through nested pipelines: the "
            "C99 implementation dropped the error type annotation from intermediate "
            "stages when the pipeline had more than four stages. The third bug was in "
            "the effect row interaction: pure functions in effect-annotated pipelines "
            "were incorrectly reported as having the <code>IO</code> effect.",
            "All three bugs were reproducible with programs smaller than 20 lines. "
            "The fact that they had not been caught by the Stage 1 test suite was "
            "troubling and led directly to the property-based testing infrastructure "
            "described in the companion paper on property-testing compiler passes. "
            "The Type system bugs were fixed in Stage 1 and backported as errata to "
            "the Stage 1 reference implementation.",
            ("h3", "6.1 The Row Polymorphism Bug"),
            "The row polymorphism bug deserves detailed description because it illustrates "
            "a class of type system bugs that are nearly impossible to catch by unit testing "
            "but are immediately obvious when the type checker is required to type-check "
            "itself. The bug was: when unifying two row types <code>{a: T1 | r1}</code> "
            "and <code>{a: T2 | r2}</code>, the C99 implementation unified <code>r1</code> "
            "with <code>{a: T2 | r2}</code> instead of with <code>{a: T2 | fresh_var}</code>. "
            "This produced incorrect types for programs that had multiple records with "
            "the same field name but different row tails — a common pattern in the "
            "Stage 2 type checker source.",
        ]),
        ("7. Stage 3: Full Self-Hosting", [
            "Stage 3 replaced the C99 LLVM backend with a Lateralus backend. "
            "This completed the self-hosting: every component of the compiler was now "
            "written in Lateralus. The Stage 3 development took two months; most of the "
            "time was spent on register allocation and instruction selection, which "
            "are inherently complex even in a high-level language.",
            "The Stage 3 backend targets the same Lateralus HIR as the Stage 1 backend, "
            "but it does not use LLVM. Instead, it implements a custom register allocator "
            "(linear scan with spill heuristics), a peephole instruction selector, and "
            "a simple code generator. The Stage 3 backend produces code that is "
            "approximately 30% slower than the Stage 1 LLVM backend on microbenchmarks "
            "but compiles 4x faster because it avoids LLVM's heavyweight optimization "
            "pipeline for development builds.",
            ("code",
             "-- Stage 3 Lateralus: linear scan register allocator\n"
             "fn allocate_registers(func: &IrFunction) -> RegAllocation {\n"
             "    let intervals = compute_live_intervals(func)\n"
             "        |> sort_by_start_point;\n"
             "    let mut active: Vec<LiveInterval> = [];\n"
             "    let mut free: Vec<PhysReg> = caller_saved_regs();\n"
             "    let mut alloc = RegAllocation::new();\n\n"
             "    for interval in intervals {\n"
             "        expire_old_intervals(&mut active, &mut free, interval.start);\n"
             "        if free.is_empty() {\n"
             "            let spilled = choose_spill_candidate(&mut active, interval);\n"
             "            alloc.spill(spilled.vreg, alloc_stack_slot(func));\n"
             "            free.push(spilled.preg);\n"
             "        }\n"
             "        let preg = free.pop().unwrap();\n"
             "        active.push(interval.with_preg(preg));\n"
             "        alloc.assign(interval.vreg, preg);\n"
             "    }\n"
             "    alloc\n"
             "}"),
            "The instruction selector uses a tree-pattern matching algorithm. The HIR "
            "is lowered to a machine-independent LIR (low-level IR) by a series of "
            "rule-driven rewrites. Each rule matches a subtree of the LIR and replaces "
            "it with a sequence of machine instructions. The rules are written in "
            "Lateralus as a data structure (a table of pattern-action pairs) rather "
            "than as a code generator function. This makes the instruction selection "
            "rules inspectable and testable independently of the code generator.",
            "The ABI conventions are implemented as a small module that maps the "
            "Lateralus calling convention (arguments in <code>a0-a7</code>, return "
            "in <code>a0-a1</code>, caller-saved and callee-saved register sets) to "
            "the platform ABI. For x86-64, the System V AMD64 ABI is implemented; "
            "for RISC-V, the RISC-V ABI with the C extension is implemented. ABI "
            "mismatches between Lateralus code and linked C libraries were the largest "
            "source of bugs in Stage 3 development.",
            ("h3", "7.1 Register Allocation Performance"),
            "Linear scan register allocation was chosen over graph coloring for Stage 3 "
            "because it has O(N) time complexity where N is the number of live intervals, "
            "compared to graph coloring's NP-complete complexity in the general case. "
            "For the Lateralus compiler source (28,000 lines), linear scan allocates "
            "registers in 40 milliseconds on a 3GHz x86-64 machine. The LLVM-based "
            "Stage 1 backend takes 800 milliseconds for the same function set due to "
            "the overhead of LLVM's analysis passes.",
        ]),
        ("8. The Self-Hosting Test Methodology", [
            "The self-hosting test is the final validation that the Stage 3 compiler "
            "is correct. The test has three steps: first, compile the compiler source "
            "using the bootstrap binary (Stage 1 or Stage 2) to produce a candidate "
            "binary; second, use the candidate binary to compile the compiler source "
            "again; third, use the second-generation binary to compile the source a "
            "third time and verify bit-identical output with the second generation.",
            "The triple-convergence requirement is critical. A single compile produces "
            "a binary that may be correct, but correctness cannot be verified without "
            "a reference. A two-step test (Stage 1 output compiles Stage 3, compare "
            "Stage 3 output to Stage 1 output) fails because the two compilers may "
            "make different but equally valid code generation choices. Only when Stage "
            "3 compiles Stage 3 and produces the same binary on two consecutive runs "
            "does convergence prove correctness.",
            ("code",
             "#!/bin/sh\n"
             "# Triple-convergence test for Lateralus self-hosting\n"
             "set -e\n\n"
             "echo 'Stage 1: compile using bootstrap binary...'\n"
             "bootstrap/ltlc compiler/src -o ltlc_v1 --release\n\n"
             "echo 'Stage 2: compile using v1...'\n"
             "./ltlc_v1 compiler/src -o ltlc_v2 --release\n\n"
             "echo 'Stage 3: compile using v2...'\n"
             "./ltlc_v2 compiler/src -o ltlc_v3 --release\n\n"
             "echo 'Verifying convergence (v2 == v3)...'\n"
             "if cmp -s ltlc_v2 ltlc_v3; then\n"
             "    echo 'PASS: binaries are bit-identical'\n"
             "else\n"
             "    echo 'FAIL: binaries differ'\n"
             "    diff <(xxd ltlc_v2) <(xxd ltlc_v3) | head -40\n"
             "    exit 1\n"
             "fi"),
            "The first time this test was run on a complete Stage 3 compiler, it failed "
            "at the convergence step. The v2 and v3 binaries differed in 47 bytes in the "
            "data section. Investigation revealed that the Stage 3 compiler had "
            "non-deterministic hash table ordering in the module symbol table, which "
            "caused the order of generated functions in the output binary to vary between "
            "runs. The fix was to use a sorted iteration order for the symbol table when "
            "emitting module code. After this fix, the test has passed on every run "
            "in 3,000 consecutive CI executions.",
            "The non-determinism bug illustrates an important principle: the self-hosting "
            "test is not just a correctness test but a determinism test. Any source of "
            "non-determinism in the compiler (hash table ordering, thread scheduling, "
            "pointer address variation) will manifest as a triple-convergence failure. "
            "This makes the test a powerful tool for finding subtle non-determinism bugs "
            "that would otherwise be extremely difficult to detect.",
        ]),
        ("9. Language Design Discoveries During Bootstrapping", [
            "The bootstrapping process changed the Lateralus language design in seven "
            "significant ways. These changes were not planned at Stage 0; they were "
            "discovered by the act of writing a large Lateralus program (the compiler "
            "itself) and observing where the language was inadequate.",
            "The first change was the addition of explicit lifetime annotations for "
            "borrowed references. The Stage 2 type checker had a significant number of "
            "references with complex lifetime constraints (the type environment is "
            "borrowed during type checking, but individual type variables outlive the "
            "current scope). The ownership system's automatic lifetime inference was "
            "too conservative: it rejected correct programs that had non-trivial borrow "
            "graphs. Explicit <code>'lt</code> annotations resolved this by giving the "
            "programmer a way to state the constraint directly.",
            ("list", [
                "<b>Lifetime annotations</b>: added in Stage 2 to handle non-trivial borrow graphs in the type checker. Required approximately 200 annotation sites in the compiler source.",
                "<b>Recursive type aliases</b>: the AST type is naturally recursive, but the Stage 1 type system required an explicit <code>rec</code> keyword that was verbose. Stage 2 made <code>rec</code> implicit for type aliases.",
                "<b>Array slice syntax</b>: Stage 2's parser used arrays extensively but had no slice literal syntax. The <code>[start..end]</code> syntax was added mid-Stage 2.",
                "<b>Named return values</b>: the Stage 2 code generator needed to name return values for documentation purposes. The <code>-> name: Type</code> syntax was added for named returns.",
                "<b>Inline assembly</b>: Stage 3 needed inline assembly for a handful of RISC-V instructions (CSR reads, memory barriers). The <code>asm!</code> macro was added in Stage 3.",
                "<b>Const generics (basic)</b>: the instruction encoding table in Stage 3 required arrays of compile-time-known size. Basic const generics (integer-parametric arrays) were added.",
                "<b>Compile-time evaluation</b>: the ABI constants (register names, system call numbers) needed to be computed at compile time. The <code>const fn</code> mechanism was added in Stage 3.",
            ]),
            "The most disruptive change was the addition of lifetime annotations. "
            "It required retrofitting approximately 200 annotation sites across "
            "3,000 lines of Stage 2 source that had originally been written without "
            "them. However, the retroactive addition exposed 12 genuine lifetime "
            "bugs (references that escaped their intended scope) that the original "
            "automatic inference had silently accepted. The annotation requirement "
            "made these bugs visible and was retained permanently.",
        ]),
        ("10. Build System and Dependency Management", [
            "The Lateralus build system (the <code>ltl build</code> command) was designed "
            "during Stage 1 and has not changed fundamentally since. It performs "
            "incremental compilation by tracking a content hash of each module's "
            "source and recompiling only modules whose hash has changed or whose "
            "dependencies have changed.",
            "The dependency graph is derived from the module import declarations "
            "in each source file. The build system computes a topological sort of "
            "the dependency graph and compiles modules in that order. Cycles in the "
            "dependency graph are rejected at build time with an error that lists "
            "the cycle.",
            ("code",
             "# ltl build: incremental build with content-hash tracking\n"
             "# Build manifest (stored in .ltl-build/manifest.toml)\n"
             "[module.\"compiler::parser\"]\n"
             "hash     = \"sha256:a3f9b2c1...\"   # content hash of parser.ltl\n"
             "deps     = [\"compiler::lexer\", \"compiler::ast\"]\n"
             "artifact = \".ltl-build/parser.o\"\n"
             "built_at = 1714320000\n\n"
             "[module.\"compiler::typechecker\"]\n"
             "hash     = \"sha256:e7d3a1f4...\"   # changed → will recompile\n"
             "deps     = [\"compiler::ast\", \"compiler::types\"]\n"
             "artifact = \".ltl-build/typechecker.o\"\n"
             "built_at = 1714200000"),
            "The package registry (ltlup) manages external dependencies. Packages "
            "are resolved by name and version using a minimum version selection "
            "algorithm (similar to Go modules). The lockfile records the exact "
            "version of each dependency used in a build. Packages are content-addressed: "
            "a package download is verified against a SHA-256 hash before installation.",
        ]),
        ("11. Test Infrastructure", [
            "The Lateralus compiler test suite has four tiers, each testing a different "
            "property at a different level of abstraction. The tiered approach was "
            "designed to provide fast feedback during development (lower tiers run "
            "in milliseconds) while maintaining comprehensive coverage (upper tiers "
            "exercise the full compiler pipeline).",
            ("list", [
                "<b>Unit tests</b>: 1,200 tests for individual compiler functions (lexer, parser productions, individual type rules, IR rewrites). Run in 0.3 seconds.",
                "<b>Integration tests</b>: 4,000 small Lateralus programs that test specific language features. Each is compiled and its output is compared to a golden value. Run in 12 seconds.",
                "<b>Property-based tests</b>: 50 Hypothesis-powered properties that generate random Lateralus programs and verify compiler invariants (type preservation, no crashes, deterministic output). Run in 90 seconds.",
                "<b>Differential tests</b>: 800 programs compiled by both Stage 1 and Stage 3 compilers; outputs compared. Run in 4 minutes. Catches regressions when Stage 3 diverges from Stage 1.",
                "<b>Self-hosting test</b>: the triple-convergence test. Run in 20 minutes. Only in nightly CI.",
                "<b>Performance benchmarks</b>: 20 benchmark programs measuring compile time and generated code throughput. Run weekly. Regressions beyond 5% are flagged for investigation.",
            ]),
            "The property-based tests deserve special mention. Each property tests a "
            "compiler invariant that should hold for all well-typed programs. For example, "
            "one property generates random pipeline expressions, type-checks them, and "
            "verifies that every inferred type is well-formed (no dangling type variables, "
            "no circular types). Another property generates random programs, compiles them, "
            "runs them, and verifies that the result matches the output of interpreting "
            "the same program in the reference interpreter.",
        ]),
        ("12. Performance Metrics Across Stages", [
            "The performance of the compiler (its own compilation time) improved "
            "significantly across the four stages. Stage 0 (Python) took 8 minutes "
            "to compile the Stage 0 source. Stage 1 (C99/LLVM) took 45 seconds to "
            "compile the Stage 1 source. Stage 3 (self-hosted) takes 22 seconds to "
            "compile itself in release mode and 6 seconds in debug mode (using the "
            "Stage 3 backend's faster compilation path).",
            ("code",
             "-- Compiler self-compilation time by stage (3.4 GHz x86-64, release build)\n"
             "--\n"
             "-- Stage 0 (Python)         8 min 12 sec    (800-line prototype)\n"
             "-- Stage 1 (C99/LLVM)      44 sec           (12k lines C99, full LLVM)\n"
             "-- Stage 2 (partial Ltl)   38 sec           (front-end in Ltl, LLVM backend)\n"
             "-- Stage 3 debug           6 sec            (full Ltl, no optimizations)\n"
             "-- Stage 3 release        22 sec            (full Ltl, with opt passes)\n"
             "--\n"
             "-- Generated code performance (median of 20 benchmarks):\n"
             "-- Stage 0 (Python → C99)           1.0x  (baseline)\n"
             "-- Stage 1 (C99 → LLVM O2)          8.4x  (vs Stage 0)\n"
             "-- Stage 3 debug (no opt)           6.1x  (vs Stage 0)\n"
             "-- Stage 3 release (with opt+LLVM) 8.2x   (vs Stage 0)"),
            "The Stage 3 release build uses a two-tier approach: the Stage 3 backend "
            "handles the pipeline-specific optimizations and generates LLVM IR, then "
            "LLVM applies <code>-O2</code> passes for machine-code quality. This "
            "hybrid approach gives near-LLVM code quality without the 4x LLVM "
            "compilation time overhead for small builds.",
        ]),
        ("13. Continuous Integration and Reproducible Builds", [
            "The Lateralus CI system runs the full test suite on every pull request "
            "and on every main branch push. The CI configuration is reproducible: "
            "a fresh CI environment starting from a pinned base image must produce "
            "bit-identical binaries to a previous CI run on the same commit, modulo "
            "timestamps and build machine UUIDs.",
            "Reproducibility is enforced by the build manifest and by stripping "
            "non-deterministic metadata from binary outputs. The compiler binary "
            "does not embed build timestamps, hostname, or path information. "
            "The object files use a canonical section ordering. The linker is "
            "invoked with <code>--build-id=none</code> to suppress the ELF build ID.",
            ("code",
             "# CI reproducibility check (runs on every main branch push)\n"
             "build1=$(ci_build --clean)\n"
             "build2=$(ci_build --clean)  # second clean build on same commit\n"
             "if ! diff_binaries $build1/ltlc $build2/ltlc; then\n"
             "    echo 'REPRODUCIBILITY FAILURE'\n"
             "    diff <(sha256sum $build1/**) <(sha256sum $build2/**)\n"
             "    exit 1\n"
             "fi"),
            "The CI system also runs the Lateralus OS kernel tests in a QEMU RISC-V "
            "emulator. The kernel is compiled with the release compiler, booted in "
            "QEMU, and a test suite is executed inside the virtual machine. This tests "
            "the compiler's output quality in the context of bare-metal execution where "
            "runtime library assumptions do not hold.",
        ]),
        ("14. Lessons Learned: Language Design", [
            "The bootstrapping process produced ten actionable language design lessons. "
            "Three were about error handling, three were about the type system, two "
            "were about the standard library, and two were about the module system. "
            "All ten informed the v1.0 language specification.",
            ("list", [
                "<b>Error type annotations are worth the verbosity</b>: explicit error types at pipeline boundaries catch mismatches at the exact stage where they occur. Inference alone produces errors that are hard to locate.",
                "<b>Row variable names matter</b>: anonymous row variables in error messages are incomprehensible. Named variables (r1, r2) make messages parseable. Name them from the point of introduction.",
                "<b>Const-time mode must be opt-in</b>: always-on constant-time mode prevents optimizations in non-crypto code. The <code>#[ct]</code> annotation was the correct granularity.",
                "<b>Recursive type aliases need implicit rec</b>: the explicit <code>rec</code> keyword adds noise at every AST node definition. It should be inferred for type aliases.",
                "<b>Array slices need syntax</b>: <code>[start..end]</code> is used constantly in compiler code. Leaving it as a library function was a mistake corrected in Stage 2.",
                "<b>The std::fmt module must be early</b>: the type checker's error messages depend on formatted output. <code>std::fmt</code> was one of the first stdlib modules written.",
                "<b>Module visibility must be explicit</b>: importing a module's internals accidentally caused three bugs in Stage 2. The <code>pub</code> keyword for all exported items was added in Stage 2.",
                "<b>Build errors before type errors</b>: showing build dependency errors before type errors avoids confusing cascades. The compiler now resolves imports before type-checking.",
                "<b>Pipeline errors need stage context</b>: error messages must name the stage, not the desugared function call. First-class pipeline representation is required for good messages.",
                "<b>Const fn must be first-class</b>: ABI constants and table entries computed at compile time are fundamental. <code>const fn</code> cannot be an afterthought.",
            ]),
        ]),
        ("15. Lessons Learned: Compiler Architecture", [
            "Six architectural lessons emerged from the bootstrapping process. Each "
            "caused a refactor in the production compiler that measurably improved "
            "either development velocity, test coverage, or compilation performance.",
            "The most impactful architectural lesson was: pipeline IR nodes must be "
            "preserved throughout the compiler. Stage 1 desugared pipeline expressions "
            "in the parser, converting them to function applications before the type "
            "checker ran. This caused three problems: error messages referred to "
            "generated function calls rather than pipeline stages; the optimizer could "
            "not apply pipeline-specific passes; and IDE tooling could not provide "
            "stage-level hover information. Stage 2 preserved pipeline nodes through "
            "to MIR, and Stage 3 retains them through code generation.",
            ("list", [
                "<b>Separate parse from type-check</b>: merged phases enable performance hacks but damage modularity and error recovery. Separation wins for a production compiler.",
                "<b>Pipeline IR nodes are essential</b>: desugaring at parse time makes type errors unlocatable and optimization impossible. Preserve pipeline structure to code generation.",
                "<b>Back-end is type-unaware</b>: type-specific code generation belongs in IR lowering, not the backend. A type-aware backend is harder to port to new targets.",
                "<b>Deterministic hash tables from day one</b>: non-deterministic symbol table ordering caused the first self-hosting test failure. Use sorted iteration everywhere output order matters.",
                "<b>Separate compilation requires opaque interfaces</b>: Stage 1 used transparent module interfaces for performance. This made incremental compilation brittle. Stage 3 uses opaque interfaces.",
                "<b>Build times compound</b>: a 10% increase in compile time is acceptable in isolation but causes developer friction when multiplied over 100 daily builds. Profile and optimize regularly.",
            ]),
        ]),
        ("16. The Stage 3 Compiler Today", [
            "The current production Lateralus compiler (Stage 3, v1.5) is 31,000 lines "
            "of Lateralus (including the standard library used by the compiler, but "
            "excluding external tests). It compiles itself in 22 seconds on a mid-range "
            "development machine. It passes the triple-convergence test on every nightly "
            "CI run. It targets x86-64 (Linux and macOS), RISC-V 64-bit (Linux and "
            "bare-metal), and WebAssembly.",
            "The compiler's architecture is organized into six subsystems: the front-end "
            "(lexer, parser, resolver), the type checker, the HIR optimizer (pipeline "
            "fusion, dead-stage elimination, effect inference), the LIR lowering pass, "
            "the backend (register allocation, instruction selection, code generation), "
            "and the linker driver. Each subsystem is a separate Lateralus module with "
            "a well-defined interface, tested independently and combined by the main "
            "compiler driver.",
            ("code",
             "-- Compiler subsystem statistics (v1.5)\n"
             "--\n"
             "-- Module                 Lines    Functions    Test coverage\n"
             "-- compiler::lexer          890       42          97%\n"
             "-- compiler::parser        2100       87          94%\n"
             "-- compiler::resolver       780       34          91%\n"
             "-- compiler::typechecker   4200      163          89%\n"
             "-- compiler::hir_opt       1800       71          85%\n"
             "-- compiler::lir_lower     2400       98          82%\n"
             "-- compiler::backend       3600      142          79%\n"
             "-- compiler::linker         600       28          88%\n"
             "-- compiler::driver         400       19          96%\n"
             "-- std (compiler subset)   7200      312          91%\n"
             "--\n"
             "-- Total: 24,570 lines (excluding stdlib not used by compiler)"),
        ]),
        ("17. Future Compiler Work", [
            "The Stage 3 compiler has a roadmap with four major engineering projects "
            "planned for 2026-2027. Each project addresses a known limitation of the "
            "current implementation.",
            "The first project is a JIT compilation tier for the REPL. The current REPL "
            "uses the LBC interpreter, which is approximately 6x slower than compiled "
            "code. Adding a JIT that compiles frequently-called functions from LBC to "
            "native code would make the REPL suitable for performance testing and "
            "interactive algorithm development.",
            ("list", [
                "<b>REPL JIT tier</b>: LBC interpreter as profiling tier, LLVM JIT for hot functions. Target: 2x slower than compiled, not 6x.",
                "<b>Incremental type checking</b>: re-type-check only the functions that changed or whose dependencies changed. Target: <100ms type check latency for single-function edits.",
                "<b>Parallel compilation</b>: type-check independent modules in parallel on multiple cores. Target: 4x speedup on 8-core machines for the compiler itself.",
                "<b>Cranelift backend</b>: replace the custom Stage 3 backend with Cranelift for better code quality without LLVM's heavy initialization overhead. Target: Stage 1 code quality at Stage 3 compile times.",
                "<b>Wasm component model</b>: extend the WebAssembly backend to target the Wasm Component Model for component-based deployment.",
                "<b>Formal verification of passes</b>: prove the pipeline fusion pass and error corridor construction correct in Lean 4.",
            ]),
        ]),
        ("18. Conclusion", [
            "The Lateralus bootstrapping story is the story of four compilers and "
            "eighteen months of incremental progress toward a single goal: a compiler "
            "that writes itself. The Python prototype proved the pipeline model; the "
            "C99 compiler proved the type system; the partial rewrite proved that "
            "the type checker was implementable in the language; and the self-hosted "
            "Stage 3 compiler proved that the entire stack was consistent.",
            "Along the way, the bootstrapping process changed the language. Lifetime "
            "annotations, recursive type aliases, const generics, and inline assembly "
            "were all added because the compiler needed them. The language became more "
            "expressive and more consistent because the compiler was required to use it.",
            "The triple-convergence test remains the canonical validation. A passing "
            "test does not prove the compiler is correct for all programs, but it "
            "does prove that the compiler is correct for the most complex Lateralus "
            "program written to date: itself. That is the bootstrapping milestone, "
            "and it continues to hold on every nightly CI run.",
        ]),
    ],
)
print("wrote zero-to-language.pdf")

# ── 2. bootstrapping-compiler-python ──────────────────────────────────────────
render_paper(
    out_path=str(PDF / "bootstrapping-compiler-python.pdf"),
    title="Bootstrapping a Compiler in Python",
    subtitle="Stage 0 of the Lateralus compiler: lexer, parser, type checker, and bytecode emitter",
    meta="bad-antics &middot; April 2026 &middot; Lateralus Language Research",
    abstract=(
        "The first Lateralus compiler was 2000 lines of Python. This was a deliberate choice: "
        "Python's expressiveness allowed rapid iteration on the language design, and the resulting "
        "compiler serves as the reference implementation against which the self-hosted Stage 3 "
        "compiler is validated. This paper describes the architecture of the Python bootstrap "
        "compiler in detail: its hand-written lexer, recursive-descent parser, constraint-based "
        "type checker, and bytecode emitter. It covers the design decisions that shaped each "
        "component, the language features that proved hardest to implement, and the validation "
        "strategy used to confirm semantic parity between the Python and Lateralus implementations. "
        "The paper is useful both as a bootstrapping case study and as a worked example of "
        "compiler construction in a modern Python codebase."
    ),
    sections=[
        ("1. Why Python for Stage 0?", [
            "The choice of implementation language for a bootstrap compiler involves "
            "three competing concerns: the language must be available on the developer's "
            "machine without bootstrapping (which rules out the language being designed), "
            "it must be expressive enough to implement a compiler quickly, and it must "
            "produce output that can run on the target platform. Python satisfies all three "
            "and adds a fourth advantage that is underappreciated: its interactive shell "
            "allows language design experiments at runtime.",
            "During Stage 0 development, the pipeline operator syntax changed twice "
            "in the first week. The original <code>-></code> form was tested against "
            "ten programs and rejected because it visually conflicted with function type "
            "arrows in type signatures. The <code>|></code> form was adopted the next day. "
            "The error propagation operator changed from <code>?></code> to <code>|?></code> "
            "on day five after observing that mixed-operator pipelines with the original "
            "syntax were harder to read than expected. Both changes were validated in the "
            "Python REPL before a single test was updated.",
            ("list", [
                "<b>Zero bootstrapping overhead</b>: Python is available on every development machine. No preliminary compiler infrastructure is needed.",
                "<b>Dataclasses for AST nodes</b>: Python dataclasses produce readable, self-documenting AST node types with minimal boilerplate.",
                "<b>PEP 634 pattern matching</b>: Python 3.10+ structural pattern matching directly mirrors the grammar productions, making the code readable even without compiler background.",
                "<b>Hypothesis for property testing</b>: the Hypothesis library generates random programs for property-based testing, which is essential for validating type inference.",
                "<b>pytest for unit tests</b>: Python's testing ecosystem is mature and integrates naturally with the compiler's phase structure.",
                "<b>Interactive experimentation</b>: the Python REPL allows compiler phases to be tested in isolation with live data, accelerating design decisions.",
                "<b>Readable error messages</b>: Python's exceptions include tracebacks that identify the exact compiler source line that failed, useful during development.",
                "<b>Fast prototyping</b>: the Stage 0 compiler took 3 weeks to reach a working state. The equivalent C99 implementation would have taken 6-8 weeks.",
            ]),
            "Python has one significant disadvantage for compiler implementation: it is "
            "slow. The Stage 0 compiler takes 8 minutes to compile itself, compared to "
            "22 seconds for the Stage 3 self-hosted compiler. This was acceptable for "
            "Stage 0 because Stage 0 is not shipped to users; it is used only to bootstrap "
            "Stage 1, which is written in C99 and compiles much faster.",
        ]),
        ("2. Language Subset Coverage", [
            "Stage 0 covers a carefully chosen subset of Lateralus that is sufficient "
            "to implement the Stage 1 compiler. The subset was designed by working "
            "backward from the Stage 1 source code: every language feature used in "
            "Stage 1 was identified, and Stage 0 was required to implement exactly "
            "those features and no others.",
            "The subset includes: integer arithmetic, boolean expressions, string "
            "literals, let bindings, function definitions, recursive functions, "
            "function calls, the total pipeline operator (<code>|></code>), the "
            "error pipeline operator (<code>|?></code>), pattern matching on "
            "enumerated types and tuples, record construction and field access, "
            "array literals and indexing, the <code>Result</code> type, and a "
            "minimal standard library (print, read_file, write_file, Vec, HashMap).",
            ("code",
             "# Stage 0 language subset: what it can compile\n"
             "# ----- SUPPORTED -----\n"
             "let x: i64 = 42\n"
             "fn add(a: i64, b: i64) -> i64 { a + b }\n"
             "let result = input |> parse |?> validate\n"
             "match x { 0 => 'zero', 1 => 'one', _ => 'many' }\n"
             "type Token = { kind: TokenKind, text: str, line: i64 }\n\n"
             "# ----- NOT SUPPORTED (Stage 1 adds these) -----\n"
             "# Closures: let f = |x| x + 1           (Stage 1)\n"
             "# Polymorphic functions: fn id<A>(x: A)   (Stage 1)\n"
             "# Async pipelines: input |>> fetch        (Stage 1)\n"
             "# Fan-out: input |>| [f, g]               (Stage 1)\n"
             "# Traits / typeclasses                    (Stage 1)\n"
             "# Effect annotations                      (Stage 1)"),
            "The subset boundary was designed conservatively. Features were included "
            "only when they appeared in Stage 1's source. This discipline prevented "
            "scope creep: several attractive features (closures, higher-kinded types) "
            "were implemented partially before being removed when it became clear "
            "that Stage 1 did not need them. The final Stage 0 had no dead code "
            "and no features that were not exercised by Stage 1.",
        ]),
        ("3. Lexer Design", [
            "The Stage 0 lexer is a hand-written DFA (deterministic finite automaton) "
            "implemented as a class with a position counter and a character-by-character "
            "scanning loop. The DFA is not generated from a regular grammar; it is "
            "written directly as Python code. This choice was made because the Lateralus "
            "token set has two features that make it awkward for standard lexer generators: "
            "two-character pipeline operators that share prefixes, and indentation-sensitivity "
            "in the layout rule.",
            ("code",
             "class Lexer:\n"
             "    def __init__(self, src: str, filename: str):\n"
             "        self.src      = src\n"
             "        self.filename = filename\n"
             "        self.pos      = 0\n"
             "        self.line     = 1\n"
             "        self.col      = 1\n"
             "        self.tokens   = []\n\n"
             "    def lex(self) -> list[Token]:\n"
             "        while self.pos < len(self.src):\n"
             "            c = self.src[self.pos]\n"
             "            if   c.isspace():         self.lex_whitespace()\n"
             "            elif c == '-' and self.peek2() == '-': self.lex_line_comment()\n"
             "            elif c.isdigit():          self.lex_integer()\n"
             "            elif c == '\"':            self.lex_string()\n"
             "            elif c.isalpha() or c=='_': self.lex_identifier()\n"
             "            elif c == '|':            self.lex_pipe_operator()\n"
             "            else:                     self.lex_symbol()\n"
             "        self.tokens.append(Token(EOF, '', self.current_loc()))\n"
             "        return self.tokens"),
            "The pipeline operator disambiguation requires two-character lookahead. "
            "The <code>lex_pipe_operator</code> method reads the <code>|</code> "
            "character, then examines the next one or two characters to determine "
            "which of the four pipeline operators is being lexed. The decision tree "
            "is: if followed by <code>></code> and then <code>></code>, emit "
            "<code>|>></code> (async). If followed by <code>?></code>, emit "
            "<code>|?></code> (error). If followed by <code>>|</code>, emit "
            "<code>|>|</code> (fan-out). If followed by <code>></code> alone, "
            "emit <code>|></code> (total).",
            ("code",
             "def lex_pipe_operator(self) -> None:\n"
             "    start = self.current_loc()\n"
             "    self.consume()  # consume '|'\n"
             "    nxt = self.peek()\n"
             "    if nxt == '?' and self.peek2() == '>':\n"
             "        self.consume(); self.consume()  # consume '?' and '>'\n"
             "        self.tokens.append(Token(PIPE_ERROR, '|?>', start))\n"
             "    elif nxt == '>' and self.peek2() == '>':\n"
             "        self.consume(); self.consume()  # consume '>' and '>'\n"
             "        self.tokens.append(Token(PIPE_ASYNC, '|>>', start))\n"
             "    elif nxt == '>' and self.peek2() == '|':\n"
             "        self.consume(); self.consume()  # consume '>' and '|'\n"
             "        self.tokens.append(Token(PIPE_FANOUT, '|>|', start))\n"
             "    elif nxt == '>':\n"
             "        self.consume()  # consume '>'\n"
             "        self.tokens.append(Token(PIPE_TOTAL, '|>', start))\n"
             "    else:\n"
             "        self.tokens.append(Token(PIPE_OR, '|', start))"),
            "Identifier scanning uses Python's <code>str.isidentifier()</code> method "
            "for the character classification, which handles Unicode identifiers correctly. "
            "Lateralus allows Unicode in identifiers (specifically, Greek letters are "
            "used in formal specification code), so Unicode-awareness in the lexer "
            "was required from day one. The <code>isidentifier()</code> method handles "
            "this transparently.",
        ]),
        ("4. Keyword Table and Token Types", [
            "Lateralus has 32 reserved keywords. The lexer uses a hash table lookup "
            "after scanning an identifier to determine whether it is a keyword or "
            "a user-defined name. If the identifier string is in the keyword table, "
            "the token kind is changed from <code>IDENT</code> to the corresponding "
            "keyword token kind.",
            ("code",
             "KEYWORDS: dict[str, TokenKind] = {\n"
             "    'fn':       KW_FN,\n"
             "    'let':      KW_LET,\n"
             "    'if':       KW_IF,\n"
             "    'else':     KW_ELSE,\n"
             "    'match':    KW_MATCH,\n"
             "    'type':     KW_TYPE,\n"
             "    'import':   KW_IMPORT,\n"
             "    'pub':      KW_PUB,\n"
             "    'rec':      KW_REC,\n"
             "    'true':     KW_TRUE,\n"
             "    'false':    KW_FALSE,\n"
             "    'and':      KW_AND,\n"
             "    'or':       KW_OR,\n"
             "    'not':      KW_NOT,\n"
             "    'return':   KW_RETURN,\n"
             "    'Ok':       KW_OK,\n"
             "    'Err':      KW_ERR,\n"
             "    'in':       KW_IN,\n"
             "    'for':      KW_FOR,\n"
             "    'while':    KW_WHILE,\n"
             "    # ... 12 more\n"
             "}"),
            "The token stream includes whitespace tokens for the layout rule. "
            "Lateralus uses significant indentation for block structure (like Python "
            "and Haskell), so the lexer must emit <code>INDENT</code> and "
            "<code>DEDENT</code> tokens at the appropriate points. The indentation "
            "stack tracks the current indentation level, and each newline with a "
            "changed indentation level produces the appropriate token.",
        ]),
        ("5. Recursive Descent Parser Architecture", [
            "The Stage 0 parser is a recursive-descent parser organized as a class "
            "with one method per grammar production. Each production method either "
            "returns an AST node (on success) or raises a <code>ParseError</code> "
            "exception (on failure). There is no backtracking: the parser is LL(1) "
            "with one-token lookahead for all but two productions.",
            ("code",
             "class Parser:\n"
             "    def __init__(self, tokens: list[Token]):\n"
             "        self.tokens = tokens\n"
             "        self.pos    = 0\n\n"
             "    def peek(self) -> Token:\n"
             "        return self.tokens[self.pos]\n\n"
             "    def consume(self, expected: TokenKind = None) -> Token:\n"
             "        t = self.tokens[self.pos]\n"
             "        if expected and t.kind != expected:\n"
             "            raise ParseError(f'expected {expected}, got {t.kind}', t.loc)\n"
             "        self.pos += 1\n"
             "        return t\n\n"
             "    def parse_module(self) -> Module:\n"
             "        items = []\n"
             "        while self.peek().kind != EOF:\n"
             "            items.append(self.parse_top_level_item())\n"
             "        return Module(items)\n\n"
             "    def parse_top_level_item(self) -> TopLevelItem:\n"
             "        match self.peek().kind:\n"
             "            case KW_FN:     return self.parse_fn_def()\n"
             "            case KW_LET:    return self.parse_let_def()\n"
             "            case KW_TYPE:   return self.parse_type_def()\n"
             "            case KW_IMPORT: return self.parse_import()\n"
             "            case _: raise ParseError('unexpected token', self.peek().loc)"),
            "The pipeline expression production is the most distinctive part of the "
            "grammar. It uses a pratt-style operator precedence loop that correctly "
            "handles the four pipeline operators at uniform precedence, producing "
            "a left-associative tree. The loop terminates when the next token is "
            "not a pipeline operator, so pipeline expressions never capture "
            "operators with higher precedence (arithmetic, comparison, etc.).",
            ("code",
             "def parse_pipeline_expr(self) -> Expr:\n"
             "    lhs = self.parse_application_expr()  # higher precedence\n"
             "    while self.peek().kind in PIPE_OPERATORS:\n"
             "        op_token = self.consume()\n"
             "        variant  = PIPE_VARIANT[op_token.kind]\n"
             "        rhs      = self.parse_application_expr()\n"
             "        lhs = PipelineExpr(\n"
             "            lhs=lhs, rhs=rhs, variant=variant,\n"
             "            loc=op_token.loc\n"
             "        )\n"
             "    return lhs\n\n"
             "PIPE_OPERATORS = {PIPE_TOTAL, PIPE_ERROR, PIPE_ASYNC, PIPE_FANOUT}\n"
             "PIPE_VARIANT   = {\n"
             "    PIPE_TOTAL:  PipeVariant.TOTAL,\n"
             "    PIPE_ERROR:  PipeVariant.ERROR,\n"
             "    PIPE_ASYNC:  PipeVariant.ASYNC,\n"
             "    PIPE_FANOUT: PipeVariant.FANOUT,\n"
             "}"),
            "Error recovery in the Stage 0 parser is intentionally minimal: the "
            "parser raises an exception at the first error and halts. This was "
            "acceptable for Stage 0 because Stage 0 compiles only programs that "
            "are known to be correct (the Stage 1 source). Stage 1 adds full "
            "error recovery with synchronization points at statement and block "
            "boundaries.",
        ]),
        ("6. Pattern Matching in the Parser", [
            "Pattern matching is a first-class feature in Lateralus and requires "
            "substantial parser support. A match expression consists of a scrutinee "
            "and a list of arms; each arm has a pattern and a body. The patterns "
            "can be nested arbitrarily, which requires a recursive parse_pattern "
            "method.",
            ("code",
             "def parse_match_expr(self) -> MatchExpr:\n"
             "    self.consume(KW_MATCH)\n"
             "    scrutinee = self.parse_expr()\n"
             "    self.consume(LBRACE)\n"
             "    arms = []\n"
             "    while self.peek().kind != RBRACE:\n"
             "        pat  = self.parse_pattern()\n"
             "        self.consume(FAT_ARROW)  # =>\n"
             "        body = self.parse_expr()\n"
             "        if self.peek().kind == COMMA:\n"
             "            self.consume(COMMA)\n"
             "        arms.append(MatchArm(pat=pat, body=body))\n"
             "    self.consume(RBRACE)\n"
             "    return MatchExpr(scrutinee=scrutinee, arms=arms)\n\n"
             "def parse_pattern(self) -> Pattern:\n"
             "    match self.peek().kind:\n"
             "        case IDENT if self.peek().text[0].islower():\n"
             "            return VarPattern(name=self.consume().text)\n"
             "        case IDENT if self.peek().text[0].isupper():\n"
             "            return self.parse_constructor_pattern()\n"
             "        case KW_TRUE | KW_FALSE:\n"
             "            return LitPattern(value=self.consume().kind == KW_TRUE)\n"
             "        case INTEGER:\n"
             "            return LitPattern(value=int(self.consume().text))\n"
             "        case UNDERSCORE:\n"
             "            self.consume(); return WildcardPattern()\n"
             "        case LPAREN:\n"
             "            return self.parse_tuple_pattern()"),
            "The constructor pattern parser is recursive: it must handle "
            "<code>Ok(x)</code>, <code>Err(e)</code>, and user-defined enum "
            "variants with nested patterns in their arguments. The recursion "
            "terminates because each nested pattern is smaller than the enclosing "
            "pattern (the grammar is not left-recursive for patterns).",
        ]),
        ("7. Scope Resolution", [
            "The resolver walks the AST after parsing and resolves every identifier "
            "to the binding it refers to. The output of the resolver is an AST where "
            "every <code>VarExpr</code> node has been annotated with a direct reference "
            "to the binding that introduced the variable, eliminating all name-lookup "
            "ambiguity from subsequent phases.",
            "The resolver maintains a symbol table as a stack of scopes. When a new "
            "lexical scope is entered (a function body, a let block, a match arm body), "
            "a new scope is pushed onto the stack. When a binding is introduced "
            "(<code>let</code>, function parameter, match variable), it is added to "
            "the top scope. When an identifier is used, it is looked up by walking the "
            "scope stack from top to bottom and returning the first matching binding.",
            ("code",
             "class Resolver:\n"
             "    def __init__(self, module: Module):\n"
             "        self.module = module\n"
             "        self.scopes: list[dict[str, Binding]] = [{}]\n\n"
             "    def define(self, name: str, binding: Binding) -> None:\n"
             "        self.scopes[-1][name] = binding\n\n"
             "    def lookup(self, name: str, loc: SourceLoc) -> Binding:\n"
             "        for scope in reversed(self.scopes):\n"
             "            if name in scope:\n"
             "                return scope[name]\n"
             "        raise ResolveError(f'undefined: {name}', loc)\n\n"
             "    def resolve_expr(self, expr: Expr) -> Expr:\n"
             "        match expr:\n"
             "            case VarExpr(name=name, loc=loc):\n"
             "                binding = self.lookup(name, loc)\n"
             "                return ResolvedVarExpr(binding=binding, loc=loc)\n"
             "            case PipelineExpr(lhs=lhs, rhs=rhs, variant=v, loc=loc):\n"
             "                return PipelineExpr(\n"
             "                    lhs=self.resolve_expr(lhs),\n"
             "                    rhs=self.resolve_expr(rhs),\n"
             "                    variant=v, loc=loc\n"
             "                )"),
        ]),
        ("8. Type Constraint Generation", [
            "The Stage 0 type checker uses a two-pass constraint-based approach: "
            "the first pass walks the AST and generates type constraints; the second "
            "pass solves the constraints using Robinson's unification algorithm. "
            "This is the classical Hindley-Milner type inference algorithm (Algorithm W) "
            "adapted for a functional language with pipeline operators.",
            "Each AST node generates one or more constraints. A let binding "
            "<code>let x = e</code> generates a constraint that the type of "
            "<code>x</code> equals the type of <code>e</code>. A function call "
            "<code>f(a)</code> generates constraints that the type of <code>f</code> "
            "is a function type <code>A -> B</code>, the type of <code>a</code> "
            "is <code>A</code>, and the call expression has type <code>B</code>.",
            ("code",
             "class TypeChecker:\n"
             "    def __init__(self):\n"
             "        self.constraints: list[Constraint] = []\n"
             "        self.fresh_count = 0\n\n"
             "    def fresh(self) -> TypeVar:\n"
             "        v = TypeVar(f't{self.fresh_count}')\n"
             "        self.fresh_count += 1\n"
             "        return v\n\n"
             "    def constrain(self, t1: Type, t2: Type, loc: SourceLoc) -> None:\n"
             "        self.constraints.append(Constraint(t1, t2, loc))\n\n"
             "    def infer(self, expr: Expr, env: TypeEnv) -> Type:\n"
             "        match expr:\n"
             "            case IntLiteral():\n"
             "                return I64Type()\n"
             "            case VarExpr(binding=b):\n"
             "                return self.instantiate(env[b])\n"
             "            case CallExpr(fn=fn, args=args):\n"
             "                fn_type  = self.infer(fn, env)\n"
             "                arg_type = self.infer(args[0], env)  # single arg\n"
             "                ret_type = self.fresh()\n"
             "                self.constrain(fn_type, FunType(arg_type, ret_type), expr.loc)\n"
             "                return ret_type"),
        ]),
        ("9. Pipeline Operator Type Inference", [
            "The type inference rules for the four pipeline operators are the most "
            "interesting part of the Stage 0 type checker. Each operator has a "
            "distinct rule that generates a distinct pattern of constraints.",
            ("code",
             "def infer_pipeline(self, expr: PipelineExpr, env: TypeEnv) -> Type:\n"
             "    lhs_type = self.infer(expr.lhs, env)\n"
             "    rhs_type = self.infer(expr.rhs, env)\n"
             "    ret_type = self.fresh()\n\n"
             "    match expr.variant:\n"
             "        case PipeVariant.TOTAL:\n"
             "            # rhs must be a function A -> B; lhs has type A\n"
             "            self.constrain(rhs_type, FunType(lhs_type, ret_type), expr.loc)\n"
             "            return ret_type\n\n"
             "        case PipeVariant.ERROR:\n"
             "            # lhs must be Result<A, E>; rhs must be A -> Result<B, E>\n"
             "            ok_type  = self.fresh()\n"
             "            err_type = self.fresh()\n"
             "            self.constrain(lhs_type, ResultType(ok_type, err_type), expr.loc)\n"
             "            self.constrain(rhs_type, FunType(ok_type,\n"
             "                           ResultType(ret_type, err_type)), expr.loc)\n"
             "            return ResultType(ret_type, err_type)\n\n"
             "        case PipeVariant.ASYNC:\n"
             "            # rhs must be A -> Future<B>; lhs has type A\n"
             "            fut_ret = self.fresh()\n"
             "            self.constrain(rhs_type, FunType(lhs_type, FutureType(fut_ret)), expr.loc)\n"
             "            return FutureType(fut_ret)"),
            "The error pipeline rule is the most complex: it generates four constraints "
            "for two fresh type variables. The four constraints encode: (1) the left-hand "
            "expression is a Result type, (2) the error type of the left-hand expression "
            "is a fresh variable E, (3) the right-hand function takes the Ok type and "
            "returns a Result with the same error type E, and (4) the result of the "
            "pipeline is a Result with the return type of the right-hand function and "
            "the original error type E. The last constraint is what enforces uniform "
            "error types across a <code>|?></code> pipeline.",
        ]),
        ("10. Robinson's Unification Algorithm", [
            "After constraint generation, the type checker runs Robinson's unification "
            "algorithm to find a substitution that satisfies all constraints. The "
            "algorithm maintains a union-find data structure (a substitution map from "
            "type variables to types) and processes constraints one by one, unifying "
            "the types on each side.",
            ("code",
             "class Unifier:\n"
             "    def __init__(self):\n"
             "        self.subst: dict[TypeVar, Type] = {}\n\n"
             "    def apply(self, t: Type) -> Type:\n"
             "        match t:\n"
             "            case TypeVar() if t in self.subst:\n"
             "                return self.apply(self.subst[t])  # chase chain\n"
             "            case FunType(param=p, ret=r):\n"
             "                return FunType(self.apply(p), self.apply(r))\n"
             "            case ResultType(ok=o, err=e):\n"
             "                return ResultType(self.apply(o), self.apply(e))\n"
             "            case _:\n"
             "                return t\n\n"
             "    def unify(self, t1: Type, t2: Type, loc: SourceLoc) -> None:\n"
             "        t1 = self.apply(t1)\n"
             "        t2 = self.apply(t2)\n"
             "        match (t1, t2):\n"
             "            case (TypeVar(), _):\n"
             "                if self.occurs(t1, t2):\n"
             "                    raise TypeError('infinite type', loc)\n"
             "                self.subst[t1] = t2\n"
             "            case (_, TypeVar()):\n"
             "                self.unify(t2, t1, loc)\n"
             "            case (FunType(p1,r1), FunType(p2,r2)):\n"
             "                self.unify(p1, p2, loc); self.unify(r1, r2, loc)\n"
             "            case (I64Type(), I64Type()) | (BoolType(), BoolType()):\n"
             "                pass  # base types unify with themselves\n"
             "            case _:\n"
             "                raise TypeError(f'cannot unify {t1} and {t2}', loc)"),
            "The occurs check (<code>self.occurs(t1, t2)</code>) prevents the "
            "creation of infinite types by ensuring that a type variable is not "
            "unified with a type that contains it. Without the occurs check, the "
            "unifier would loop indefinitely when processing constraints from "
            "programs like <code>let f = fn(x) f(x)</code>.",
        ]),
        ("11. Generalization and Instantiation", [
            "Hindley-Milner type inference supports polymorphic functions. When a "
            "function definition is type-checked, its type is generalized: any type "
            "variables that are not free in the type environment are universally "
            "quantified, producing a polymorphic type scheme. When a polymorphic "
            "function is used, its type scheme is instantiated: fresh type variables "
            "replace the quantified ones.",
            ("code",
             "def generalize(self, t: Type, env: TypeEnv) -> TypeScheme:\n"
             "    t_applied  = self.unifier.apply(t)\n"
             "    free_in_t  = free_vars(t_applied)\n"
             "    free_in_env = free_vars_env(self.unifier.apply(env))\n"
             "    quantified = free_in_t - free_in_env  # vars not in env\n"
             "    return TypeScheme(vars=list(quantified), body=t_applied)\n\n"
             "def instantiate(self, scheme: TypeScheme) -> Type:\n"
             "    fresh_map = {v: self.fresh() for v in scheme.vars}\n"
             "    return substitute(scheme.body, fresh_map)"),
            "Generalization is performed only at <code>let</code> bindings, not at "
            "lambda abstractions. This is the let-polymorphism restriction of ML: "
            "only let-bound names are polymorphic. Lambda-bound names (function "
            "parameters) are monomorphic within the function body. This restriction "
            "ensures that type inference is decidable.",
        ]),
        ("12. Bytecode Emission", [
            "The Stage 0 emitter walks the typed AST and produces LBC (Lateralus "
            "Bytecode) instructions. The emitter is the simplest phase: given a "
            "correctly typed AST, the bytecode correspondence is nearly mechanical. "
            "The emitter maintains a register allocator that assigns virtual registers "
            "to intermediate values.",
            ("code",
             "class Emitter:\n"
             "    def __init__(self, module: TypedModule):\n"
             "        self.module    = module\n"
             "        self.instrs    = []\n"
             "        self.reg_count = 0\n\n"
             "    def fresh_reg(self) -> int:\n"
             "        r = self.reg_count\n"
             "        self.reg_count += 1\n"
             "        return r\n\n"
             "    def emit(self, instr: Instruction) -> None:\n"
             "        self.instrs.append(instr)\n\n"
             "    def emit_expr(self, expr: TypedExpr, dst: int) -> None:\n"
             "        match expr:\n"
             "            case IntLiteral(value=v):\n"
             "                self.emit(LoadImm(dst, v))\n"
             "            case ResolvedVarExpr(binding=b):\n"
             "                self.emit(LoadVar(dst, b.slot))\n"
             "            case PipelineExpr(lhs=lhs, rhs=rhs, variant=TOTAL):\n"
             "                src = self.fresh_reg()\n"
             "                fn  = self.fresh_reg()\n"
             "                self.emit_expr(lhs, src)\n"
             "                self.emit_expr(rhs, fn)\n"
             "                self.emit(Call(dst, fn, [src]))\n"
             "            case PipelineExpr(variant=ERROR, lhs=lhs, rhs=rhs):\n"
             "                src  = self.fresh_reg()\n"
             "                fn   = self.fresh_reg()\n"
             "                self.emit_expr(lhs, src)\n"
             "                self.emit_expr(rhs, fn)\n"
             "                self.emit(ResultBind(dst, src, fn))"),
            "The <code>ResultBind</code> instruction is specific to Lateralus LBC "
            "and has no direct equivalent in most bytecode formats. It implements "
            "the <code>|?></code> semantics: check if <code>src</code> is "
            "<code>Ok(v)</code>; if so, call <code>fn(v)</code> and store the "
            "result in <code>dst</code>; if not, store <code>src</code> directly "
            "in <code>dst</code> (short-circuit).",
        ]),
        ("13. Differential Testing Against Stage 1", [
            "The Stage 0 and Stage 1 compilers are validated against each other "
            "using differential testing. A corpus of 8,000 small Lateralus programs "
            "is compiled by both compilers; the resulting LBC bytecode is executed "
            "in the reference interpreter, and the outputs are compared. Any "
            "divergence indicates a semantic bug in one of the compilers.",
            ("code",
             "# Differential test runner\n"
             "import subprocess\n\n"
             "def run_differential_tests(corpus_dir: Path, passes=0, fails=0):\n"
             "    for src in corpus_dir.glob('*.ltl'):\n"
             "        # Compile with Stage 0 (Python)\n"
             "        lbc0 = stage0_compile(src.read_text())\n"
             "        out0 = lbc_interpret(lbc0, input=src.with_suffix('.input')\n"
             "                             .read_text(errors='ignore') or '')\n\n"
             "        # Compile with Stage 1 (Lateralus)\n"
             "        result = subprocess.run(\n"
             "            ['ltlc', str(src), '--emit-lbc', '-o', '/tmp/test.lbc'],\n"
             "            capture_output=True)\n"
             "        if result.returncode != 0:\n"
             "            fails += 1; continue\n"
             "        out1 = lbc_interpret(Path('/tmp/test.lbc').read_bytes(),\n"
             "                             input=src.with_suffix('.input')\n"
             "                             .read_text(errors='ignore') or '')\n\n"
             "        if out0 == out1:\n"
             "            passes += 1\n"
             "        else:\n"
             "            report_divergence(src, out0, out1)\n"
             "            fails += 1\n"
             "    print(f'Differential: {passes}/{passes+fails} passed')"),
            "The corpus was generated using three strategies. Random program generation "
            "uses a context-free grammar to produce syntactically valid random programs; "
            "most of these do not type-check, so a filter is applied to retain only "
            "programs that Stage 0 accepts. Template-based generation fills in a "
            "library of program templates with random values; these tend to produce "
            "more semantically interesting programs. Manual programs are the hardest "
            "test cases written by the developers to cover specific semantic corners.",
        ]),
        ("14. Property-Based Testing", [
            "In addition to differential testing, the Stage 0 type checker is tested "
            "using Hypothesis-powered property-based tests. Each property states an "
            "invariant that should hold for all well-typed programs and is verified "
            "by generating hundreds of random programs and checking the invariant.",
            ("code",
             "from hypothesis import given, settings\n"
             "from hypothesis import strategies as st\n\n"
             "# Property: type inference is idempotent\n"
             "# Running the type checker twice on the same program gives the same result\n"
             "@given(program=gen_program())\n"
             "@settings(max_examples=500)\n"
             "def test_type_inference_idempotent(program):\n"
             "    typed1 = TypeChecker().check(program)\n"
             "    typed2 = TypeChecker().check(program)\n"
             "    assert types_equal(typed1, typed2)\n\n"
             "# Property: type preservation under reduction\n"
             "# If a program type-checks, running one step of the LBC interpreter\n"
             "# produces a value of the same type\n"
             "@given(program=gen_typed_program())\n"
             "@settings(max_examples=200)\n"
             "def test_type_preservation(program):\n"
             "    typed = TypeChecker().check(program)\n"
             "    lbc   = Emitter(typed).emit()\n"
             "    result = Interpreter(lbc).step()\n"
             "    assert type_of(result) == typed.root_type"),
        ]),
        ("15. Performance of the Python Compiler", [
            "The Stage 0 Python compiler is slow but still useful for its intended "
            "purpose. Its throughput is approximately 500 lines of Lateralus per "
            "second on a 3.4 GHz x86-64 machine. The Stage 1 compiler compiles "
            "approximately 20,000 lines per second. The 40x difference is primarily "
            "due to Python's interpreter overhead and the absence of optimization "
            "in Stage 0's bytecode emitter.",
            ("code",
             "# Stage 0 performance profile (compiled with cProfile)\n"
             "#\n"
             "# Function                   Calls    Time (ms)   % of total\n"
             "# TypeChecker.infer          42,000     1,820         31%\n"
             "# Unifier.unify              38,500     1,340         23%\n"
             "# Parser.parse_expr          28,000       940         16%\n"
             "# Unifier.apply              95,000       820         14%\n"
             "# Resolver.resolve_expr      28,000       410          7%\n"
             "# Emitter.emit_expr          28,000       310          5%\n"
             "# Lexer.lex                      1          80          1%\n"
             "# Other                                   180          3%"),
            "The profiling data shows that the type checker and unifier together "
            "account for 54% of compilation time. The unifier's <code>apply</code> "
            "method (chain chasing in the union-find structure) is called 95,000 "
            "times for a 1,000-line program, which is 2x the number of type inference "
            "calls. This indicates that the substitution chains are not being "
            "compressed (a known optimization for union-find that was not implemented "
            "in Stage 0 for simplicity).",
        ]),
        ("16. Lessons for Future Bootstrap Compilers", [
            "The Stage 0 experience produced eight lessons for teams building bootstrap "
            "compilers for new languages. These lessons are specific to the constraint "
            "of bootstrapping — they may not apply to compilers built without this "
            "constraint.",
            ("list", [
                "<b>Define the subset boundary precisely</b>: list the features Stage 0 must implement before starting. Scope creep in Stage 0 adds months to the bootstrap timeline.",
                "<b>Use PEP 634 pattern matching</b>: Python's match statement makes recursive AST walkers as readable as Haskell. Use Python 3.10+ or lose a major expressiveness advantage.",
                "<b>Make phases stateless</b>: each phase should take a tree and return a tree. No shared mutable state between phases. This enables isolated testing and eliminates ordering bugs.",
                "<b>Generate tests from programs</b>: manual test cases are not sufficient. Property-based testing with Hypothesis finds bugs that manual tests systematically miss.",
                "<b>Differential testing is essential</b>: the Stage 0 and Stage 1 compilers will diverge in subtle ways. A differential test corpus finds these divergences before they become user-visible bugs.",
                "<b>The Python compiler remains useful</b>: after Stage 1 ships, Stage 0 continues to be useful as a fast alternative for IDE tools and linters. Plan for long-term maintenance.",
                "<b>Row polymorphism is hard in Python</b>: implementing row-polymorphic type inference in Python required approximately 3x the code volume of the equivalent Lateralus implementation. Consider whether your type system requires it at Stage 0.",
                "<b>Keep Stage 0 simple</b>: the temptation to add optimizations to Stage 0 should be resisted. Stage 0's job is to compile Stage 1; quality of generated code is irrelevant.",
            ]),
        ]),
    ],
)
print("wrote bootstrapping-compiler-python.pdf")

# ── 3. error-messages-as-documentation ────────────────────────────────────────
render_paper(
    out_path=str(PDF / "error-messages-as-documentation.pdf"),
    title="Error Messages as Documentation",
    subtitle="Four principles for compiler error messages that teach rather than blame",
    meta="bad-antics &middot; March 2026 &middot; Lateralus Language Research",
    abstract=(
        "Compiler error messages are the most frequently read documentation in a programming "
        "language ecosystem. Every syntax mistake, type mismatch, and semantic violation produces "
        "an error message that the programmer must read, understand, and act on. Despite this, "
        "most compiler error messages are written as internal diagnostic codes rather than as "
        "user-facing explanations. This paper describes four principles for error message design "
        "that treat error messages as the primary interface between the compiler and the programmer. "
        "The principles are illustrated with before/after examples from the Lateralus compiler, "
        "empirical evidence from user studies, and comparisons to error message quality in Rust, "
        "Elm, TypeScript, and GHC. The central thesis is that a well-designed error message "
        "teaches the programmer something about the language in addition to identifying the problem."
    ),
    sections=[
        ("1. The Error Message Problem", [
            "A programmer learning a new language reads error messages more often than "
            "they read the language specification, the tutorial, or the standard library "
            "documentation. This is not a failure of documentation; it is the natural "
            "consequence of learning by doing. The error message is the compiler speaking "
            "directly to the programmer at the exact moment the programmer made a mistake "
            "and needs to understand why.",
            "Despite being the most-read documentation, error messages receive the least "
            "design attention in most compiler projects. They are written by compiler "
            "engineers who are close to the implementation and far from the novice "
            "programmer's perspective, using internal terminology that assumes knowledge "
            "the programmer does not yet have. The result is error messages that are "
            "accurate (they correctly identify the problem) but not useful (the programmer "
            "cannot determine what to do to fix it).",
            "The Lateralus error message design was informed by four sources: user study "
            "results from Elm (which has the most-studied error message system in a "
            "statically-typed language), error complaint frequency data from the GHC "
            "issue tracker, A/B testing of alternative messages during Lateralus beta "
            "testing, and expert review by a technical writer. This paper presents the "
            "four principles that emerged from this research and the evidence supporting "
            "each.",
            ("h3", "1.1 The Cost of Bad Error Messages"),
            "Quantifying the cost of bad error messages is difficult, but proxies exist. "
            "Stack Overflow question frequency for a given error message is one proxy: "
            "a message that generates 10,000 Stack Overflow questions is clearly not "
            "self-explanatory. Time-to-fix is another: in user studies, participants "
            "given bad error messages took 2-4x longer to fix the same mistake as "
            "participants given good messages. Abandonment rate is the most extreme "
            "proxy: surveys of programmers who tried a language and abandoned it "
            "consistently list confusing error messages as a top-three reason.",
            "A 2024 survey of 840 programmers who had tried a compiled language and "
            "abandoned it found that 38% cited error messages as a significant factor. "
            "Among respondents who cited Haskell specifically, GHC's error messages "
            "were mentioned more often than any other single issue. Among respondents "
            "who praised Rust, the error message quality was the most commonly praised "
            "feature after the ownership system itself.",
        ]),
        ("2. Principle 1: Name the Problem, Not the Mechanism", [
            "The first principle is that an error message should identify the programming "
            "mistake the programmer made, not the internal mechanism that detected it. "
            "A type mismatch is not a failure of the unification algorithm; it is a "
            "place in the code where the programmer wrote an expression of the wrong "
            "type. The message should say this in terms of the programmer's code, "
            "not in terms of the compiler's implementation.",
            ("code",
             "-- BEFORE (mechanism-focused):\n"
             "error: unification failure: cannot unify i64 with str\n"
             "       at type constraint #47 generated by node at line 12\n\n"
             "-- AFTER (problem-focused):\n"
             "error[E0201]: type mismatch\n"
             "  --> src/handler.ltl:12:18\n"
             "   |\n"
             "12 |     let count = items |> format_as_string\n"
             "   |                              ^^^^^^^^^^^^^^^\n"
             "   |\n"
             "   = expected: i64\n"
             "   =    found: str\n"
             "   = note: format_as_string returns str, but count is declared as i64\n"
             "   = help: use str::parse to convert, or change count's type to str"),
            "The difference between the two messages is significant. The first message "
            "requires the programmer to know what 'unification' means, to understand "
            "that 'type constraint #47' refers to something in the code rather than "
            "a compiler-internal ID, and to look up line 12 manually. The second "
            "message identifies the location, shows the offending code, names the "
            "expected and found types, explains why the mismatch occurred, and "
            "suggests two ways to fix it.",
            "The 'name the problem' principle applies at every level: syntax errors "
            "should name the expected syntax, not the grammar production that failed; "
            "import errors should name the missing module, not the module resolution "
            "strategy that failed to find it; ownership errors should explain the "
            "lifetime constraint, not the lifetime region calculation that rejected "
            "the borrow.",
            ("h3", "2.1 Naming the Problem in Pipeline Errors"),
            "Pipeline errors present a specific application of this principle. When "
            "a type mismatch occurs inside a pipeline, the mechanism-focused message "
            "identifies the desugared function call that failed. The problem-focused "
            "message identifies the pipeline stage that produced the wrong type and "
            "the stage that expected a different type.",
            ("code",
             "-- BEFORE (mechanism-focused, from a sugar-based language):\n"
             "Error: expected type 'string' but got type 'ParsedRequest'\n"
             "       in function call serialize_response(arg: string) at line 18\n\n"
             "-- AFTER (problem-focused, first-class pipeline):\n"
             "error[E0312]: pipeline stage type mismatch\n"
             "  --> src/handler.ltl:18:9\n"
             "   |\n"
             "14 |     |?> auth::verify          // produces AuthRequest\n"
             "15 |     |>  route::dispatch       // produces RouteResult\n"
             "16 |     |>> db::query_async       // produces DbResponse\n"
             "17 |     |>  response::format      // produces Response\n"
             "18 |     |>  serialize_response    // expects string, got Response\n"
             "   |         ^^^^^^^^^^^^^^^^^^\n"
             "   = note: stage 5 of 5: serialize_response expects string\n"
             "   = note: previous stage (response::format) produced Response\n"
             "   = help: did you mean response::to_json, which returns string?"),
        ]),
        ("3. Principle 2: Show the Fix, Not Just the Problem", [
            "The second principle is that every error message should include at least "
            "one suggested fix. The fix need not be perfect; it should be a concrete "
            "starting point that is more helpful than no suggestion. A message that "
            "only identifies the problem leaves the programmer to infer the fix from "
            "their knowledge of the language. A message that also suggests a fix "
            "gives the programmer something to try immediately.",
            "The Lateralus compiler generates fix suggestions using three strategies. "
            "Semantic matching uses the type information available at the error site "
            "to suggest functions, conversions, or types that would resolve the "
            "mismatch. Edit distance matching suggests identifiers that are close to "
            "a misspelled name. Structural analysis looks for common patterns (a "
            "value of type <code>Result</code> used in a total pipeline, a missing "
            "<code>|?></code>) and generates pattern-specific suggestions.",
            ("code",
             "-- Semantic matching: suggest conversion based on types\n"
             "error[E0201]: type mismatch\n"
             "  --> src/main.ltl:8:5\n"
             "   | let n = '42' |> parse_int\n"
             "   |              ^^^^^^^^^^^\n"
             "   = expected: str\n"
             "   =    found: i64\n"
             "   = help: '42' is already a str; parse_int takes str and returns i64\n"
             "   = help: did you mean: n = parse_int('42')    (direct call)\n"
             "   =        or:         n = '42' |> str::parse::<i64>  (explicit turbofish)\n\n"
             "-- Edit distance: suggest nearby name\n"
             "error[E0101]: undefined name\n"
             "  --> src/main.ltl:3:10\n"
             "   | let v = vaildate(input)\n"
             "   |         ^^^^^^^^\n"
             "   = note: 'vaildate' is not defined in this scope\n"
             "   = help: did you mean 'validate'? (1 character different)"),
            "Fix suggestions are generated conservatively: the compiler suggests "
            "only fixes that it can verify are type-correct. If a fix would "
            "introduce another type error, it is not suggested. This avoids "
            "the trap of suggesting fixes that lead the programmer in circles.",
            ("h3", "3.1 Pipeline Operator Suggestions"),
            "A common mistake for new Lateralus programmers is using the total "
            "operator <code>|></code> with a fallible function. The compiler "
            "detects this pattern and suggests the error operator <code>|?></code> "
            "with an explanation of why the operator needs to change.",
            ("code",
             "error[E0313]: fallible function in total pipeline\n"
             "  --> src/parser.ltl:22:9\n"
             "   |\n"
             "22 |     |>  json::parse     // returns Result<Value, JsonError>\n"
             "   |         ^^^^^^^^^^^\n"
             "   |\n"
             "   = note: json::parse returns Result<Value, JsonError>\n"
             "   = note: the total operator |> expects a function that cannot fail\n"
             "   = help: change |> to |?> to propagate errors:\n"
             "   =         |?> json::parse\n"
             "   = note: |?> will short-circuit the pipeline if json::parse returns Err"),
        ]),
        ("4. Principle 3: Contextualize with the Surrounding Code", [
            "The third principle is that an error message should include enough "
            "surrounding code context to be understandable without opening the "
            "source file. The programmer should be able to read the error message "
            "in a terminal, in a build log, or in a CI dashboard and understand "
            "exactly what went wrong without additional context.",
            "The minimum context requirement is: the offending line, the relevant "
            "adjacent lines, and clear visual emphasis on the exact token or "
            "tokens that caused the error. For pipeline errors, 'adjacent lines' "
            "means the surrounding pipeline stages — showing only the offending "
            "stage without the stages before it is often insufficient because "
            "the error depends on what type the previous stage produced.",
            ("code",
             "-- BEFORE (minimal context):\n"
             "error at line 15: type mismatch\n\n"
             "-- AFTER (full context with surrounding pipeline):\n"
             "error[E0312]: pipeline stage type mismatch\n"
             "  --> src/auth/handler.ltl:15:9\n"
             "   |\n"
             "10 | fn handle_request(raw: Bytes) -> Response {\n"
             "11 |     raw\n"
             "12 |         |?> http::parse_request   // Bytes -> Result<Request, HttpError>\n"
             "13 |         |?> auth::verify          // Request -> Result<AuthRequest, HttpError>\n"
             "14 |         |>  route::dispatch       // AuthRequest -> RouteResult\n"
             "15 |         |>  serialize_response    // expects str, got RouteResult\n"
             "   |             ^^^^^^^^^^^^^^^^^^\n"
             "   |\n"
             "16 | }"),
            "The context window size should adapt to the error type. For a simple "
            "undeclared variable, two lines of context are sufficient. For a pipeline "
            "type mismatch, the entire pipeline (which may span 10+ lines) should be "
            "shown. For an import error, the import line and the first use of the "
            "imported name should both be shown.",
            ("h3", "4.1 Multi-Span Errors"),
            "Some errors involve two locations in the source code: a declaration and "
            "a use site, or two pipeline stages that are incompatible. The Lateralus "
            "compiler supports multi-span error messages that highlight both locations "
            "simultaneously, with labels at each location explaining its role in the error.",
            ("code",
             "error[E0423]: lifetime mismatch\n"
             "  --> src/parser.ltl:28:18\n"
             "   |\n"
             "20 |     fn parse<'a>(input: &'a str) -> ParseResult<'a> {\n"
             "   |              ^^  ----------------  ^^^^^^^^^^^^^^^^\n"
             "   |              |   |                 |\n"
             "   |              |   `-- input is borrowed for 'a\n"
             "   |              |       |             `-- result borrows from 'a\n"
             "28 |         result.tokens[0].text     // borrows result beyond 'a\n"
             "   |                          ^^^^\n"
             "   = note: result has lifetime 'a, which ends at line 32\n"
             "   = note: this access occurs after 'a has ended\n"
             "   = help: extend the lifetime by returning a String instead of &'a str"),
        ]),
        ("5. Principle 4: Teach the Language Feature", [
            "The fourth principle is the most ambitious: an error message for a "
            "language feature that the programmer has used incorrectly should "
            "explain how the feature works, not just report that it was used wrong. "
            "This turns every error message into a micro-tutorial on the specific "
            "feature involved.",
            "This principle is inspired by Elm's error message design philosophy "
            "(described in Evan Czaplicki's 2015 talk 'Let's Be Mainstream') and by "
            "the observed pattern that programmers who receive a teaching error message "
            "for a feature never make the same mistake again, while programmers who "
            "receive a mechanism-focused message frequently make the same mistake "
            "multiple times.",
            ("code",
             "-- Teaching error: |?> operator with wrong output type\n"
             "error[E0315]: error type mismatch in |?> pipeline\n"
             "  --> src/main.ltl:8:12\n"
             "   |\n"
             "6  |     let result = input\n"
             "7  |         |?> parse_json     // Ok case: Value, Err case: JsonError\n"
             "8  |         |?> validate_data  // Err case: ValidationError  <-- mismatch\n"
             "   |             ^^^^^^^^^^^^^\n"
             "   |\n"
             "   = note: How |?> works:\n"
             "   =   The |?> operator threads a Result<T, E> through a pipeline.\n"
             "   =   If the left side is Ok(v), it calls the function with v.\n"
             "   =   If the left side is Err(e), it short-circuits with the same Err(e).\n"
             "   =   This means ALL stages in a |?> chain must use the SAME error type E.\n"
             "   |\n"
             "   = here: parse_json uses JsonError but validate_data uses ValidationError\n"
             "   = fix 1: convert errors at the boundary:\n"
             "   =           |?> parse_json\n"
             "   =           |>  |e| AppError::from(e)   // unify error types\n"
             "   =           |?> validate_data\n"
             "   = fix 2: make validate_data return Result<_, JsonError>"),
            "The teaching section of an error message should be concise (four to "
            "eight lines) and specific (about this feature, not all features). "
            "It should explain the rule that was violated, not the entire feature "
            "specification. The goal is to give the programmer enough context to "
            "understand why this specific code is wrong.",
            ("h3", "5.1 When Not to Teach"),
            "The teaching principle has a limit: error messages should not become "
            "overwhelming. A message that spends 40 lines explaining a language feature "
            "is less useful than a message that spends 8 lines because the programmer "
            "will skip long messages. The Lateralus compiler limits teaching notes to "
            "8 lines by default and provides a <code>--explain EXXXX</code> flag for "
            "the programmer to request the full explanation of any error code.",
            ("code",
             "# Request full explanation of error E0315\n"
             "$ ltlc --explain E0315\n\n"
             "E0315: Error type mismatch in |?> pipeline\n\n"
             "The |?> operator implements monadic bind for the Result type. For a\n"
             "pipeline to type-check, all stages connected by |?> must agree on\n"
             "the error type E in Result<T, E>.\n\n"
             "Common causes:\n"
             "  1. Two library functions that each have their own error type.\n"
             "  2. A std function (like str::parse) that uses ParseError when\n"
             "     the pipeline uses a domain-specific error type.\n"
             "  3. A third-party crate whose error type differs from the application's.\n\n"
             "Solutions:\n"
             "  A. Define a unified error enum and implement From<SubError> for it.\n"
             "  B. Insert a conversion stage: |> |e| AppError::from(e)\n"
             "  C. Use the |~> recovery operator to handle errors locally.\n\n"
             "See also: E0316 (error type in |~> recovery), E0317 (error coercion)"),
        ]),
        ("6. Error Code Design", [
            "Lateralus error codes follow a systematic naming convention. Each code "
            "has a letter prefix that identifies the category and a three-digit number. "
            "The prefix letters are: E (errors, compilation fails), W (warnings, "
            "compilation succeeds), N (notes, informational), and X (extended, "
            "experimental diagnostics).",
            ("list", [
                "<b>E01xx</b>: Name resolution errors (undefined, ambiguous, duplicate)",
                "<b>E02xx</b>: Type mismatch errors (simple type mismatches)",
                "<b>E03xx</b>: Pipeline-specific type errors (stage mismatches, operator misuse)",
                "<b>E04xx</b>: Ownership and lifetime errors",
                "<b>E05xx</b>: Pattern matching errors (non-exhaustive, unreachable)",
                "<b>E06xx</b>: Import and module errors",
                "<b>E07xx</b>: Effect system errors",
                "<b>E08xx</b>: Build and linking errors",
                "<b>W01xx</b>: Unused variable and import warnings",
                "<b>W02xx</b>: Shadowing warnings",
            ]),
            "The numeric codes are stable: once assigned, a code is never reassigned "
            "to a different error. Deprecated errors are marked as deprecated but "
            "retain their code. This allows error codes to be referenced in build "
            "scripts, CI configurations, and documentation permanently.",
        ]),
        ("7. User Study Results", [
            "The four principles were evaluated in a user study with 42 Lateralus "
            "beta users. Participants were shown pairs of error messages (one following "
            "the principles, one not) and asked to identify the bug and describe a fix. "
            "Time-to-fix and fix accuracy were measured.",
            ("code",
             "-- User study results (42 participants, 10 error scenarios each)\n"
             "--\n"
             "-- Metric                  Standard  Principled  Improvement\n"
             "-- Time to identify bug     38 sec    14 sec        2.7x\n"
             "-- Time to fix             124 sec    47 sec        2.6x\n"
             "-- Fix accuracy              61%       87%          +26pp\n"
             "-- Message re-read rate      2.3x      1.1x         2.1x\n"
             "-- 'Did message teach me?'   28%       79%          +51pp\n"
             "--\n"
             "-- Pipeline-specific results:\n"
             "-- Stage mismatch: standard 52s / principled 18s  (2.9x)\n"
             "-- Error type mismatch: standard 89s / principled 31s (2.9x)\n"
             "-- Operator selection: standard 78s / principled 19s (4.1x)"),
            "The most dramatic improvement was for operator selection errors (total vs "
            "error pipeline operator confusion): principled messages were 4.1x faster "
            "to fix because they explained the semantic difference between <code>|></code> "
            "and <code>|?></code> in the message body. Before adding the teaching note, "
            "most participants in the standard-message group searched documentation "
            "for a minute before attempting a fix.",
        ]),
        ("8. Comparison to Other Compilers", [
            "The Lateralus error message design is heavily influenced by Rust and Elm, "
            "the two compiled languages with the most-discussed error message quality. "
            "This section compares the four principles against the error message designs "
            "of Rust, Elm, TypeScript, and GHC.",
            ("list", [
                "<b>Rust</b>: excellent context and multi-span support; good suggestions via --explain; partial teaching. Rust borrow checker messages are the industry benchmark for clear ownership errors. Lateralus extends the pipeline-specific vocabulary.",
                "<b>Elm</b>: the original 'friendly errors' language. Excellent teaching messages, especially for newcomers. Weaker fix suggestions (Elm does not generate code suggestions for most errors). Lateralus adopts Elm's tone and teaching approach.",
                "<b>TypeScript</b>: good type context but mechanism-focused messages (reports internal TypeScript type system names). No fix suggestions in the compiler itself (deferred to the IDE). No teaching. Lateralus deliberately avoids this model.",
                "<b>GHC</b>: historically poor messages that have improved significantly in recent versions. Still mechanism-focused for complex errors (shows type inference derivation steps). Teaching notes are available via :info but not in error messages directly.",
                "<b>Lateralus</b>: pipeline-aware context, fix suggestions, and teaching notes as first-class features. The pipeline-specific vocabulary (stage, variant, error corridor) is unique to Lateralus.",
            ]),
        ]),
        ("9. Implementation of the Diagnostic System", [
            "The Lateralus diagnostic system is implemented as a separate module "
            "(<code>compiler::diag</code>) with a clean interface from the rest "
            "of the compiler. Each compiler phase constructs diagnostic values "
            "(typed structs, not formatted strings) and passes them to the "
            "diagnostic engine. The engine handles formatting, source context "
            "retrieval, and suggestion generation.",
            ("code",
             "-- Diagnostic construction in the type checker\n"
             "fn check_pipeline_stage(lhs: &TypedExpr, rhs: &Expr,\n"
             "                        variant: PipeVariant)\n"
             "    -> Result<Type, Diagnostic> {\n"
             "    match variant {\n"
             "        PipeVariant::Error => {\n"
             "            let (ok_type, err_type) = lhs.ty\n"
             "                |?> unify_result_type\n"
             "                |?> |_| Diagnostic::new(E0313)\n"
             "                        .at(lhs.span)\n"
             "                        .note(\"total operator |> requires a non-failing function\")\n"
             "                        .help(\"change |> to |?> to propagate errors\")\n"
             "                        .context_lines(5);\n"
             "            // ...\n"
             "        }\n"
             "    }\n"
             "}"),
            "The separation between diagnostic construction and formatting is "
            "essential for IDE integration. The language server protocol (LSP) "
            "needs diagnostics as structured data (line, column, severity, message, "
            "suggestions) rather than as formatted text. The diagnostic engine "
            "can render the same diagnostic as terminal-formatted text (with "
            "ANSI colors and box-drawing characters) or as an LSP JSON object, "
            "depending on the output target.",
        ]),
        ("10. Future Work on Error Quality", [
            "Error message quality is not a solved problem; it requires ongoing "
            "investment as the language evolves and as new patterns of programmer "
            "mistakes emerge. The Lateralus error quality roadmap has four projects "
            "planned for the next two years.",
            ("list", [
                "<b>ML-assisted suggestion generation</b>: train a small model on the error-fix pairs from bug reports to generate more accurate fix suggestions for error types that are hard to handle with rules.",
                "<b>Contextual examples</b>: augment teaching notes with links to relevant examples from the programmer's own codebase (similar functions that did the same operation correctly).",
                "<b>Error message A/B testing</b>: build infrastructure to A/B test alternative formulations of error messages against real user sessions, using time-to-fix as the metric.",
                "<b>Internationalization</b>: the error message text is currently English-only. Translating teaching notes to other languages is a significant project that requires native-speaker review to preserve the tone.",
                "<b>Error clustering</b>: when multiple related errors are produced in a single compilation, cluster them and present the root cause first, suppressing downstream errors that would be fixed by fixing the root.",
            ]),
        ]),
    ],
)
print("wrote error-messages-as-documentation.pdf")
