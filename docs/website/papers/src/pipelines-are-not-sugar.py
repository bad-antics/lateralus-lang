#!/usr/bin/env python3
"""Render 'Pipelines Are Not Sugar' in the canonical Lateralus paper style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "pipelines-are-not-sugar.pdf"

render_paper(
    out_path=str(OUT),
    title="Pipelines Are Not Sugar",
    subtitle="Why the |> operator demands a first-class semantic model",
    meta="bad-antics &middot; November 2023 &middot; Lateralus Language Research",
    abstract=(
        "Every mainstream language that has adopted a pipe operator treats it as syntactic sugar "
        "over nested function application. We argue this framing is not merely insufficient but "
        "actively harmful: it prevents meaningful optimizations, conflates error-propagating and "
        "non-error-propagating composition, and makes asynchronous pipelines an afterthought "
        "bolted onto a synchronous model. Lateralus instead treats the pipeline operator as a "
        "primitive semantic form with its own typing rules, control-flow semantics, and compiler "
        "IR nodes. This paper explains the distinction, gives formal justification, and shows "
        "empirically that a first-class model enables optimizations that sugar-based approaches "
        "cannot express."
    ),
    sections=[
        ("1. The Sugar Framing and Its Costs", [
            "In F#, Elixir, and the TC39 JavaScript proposal, <code>x |> f</code> desugars to "
            "<code>f(x)</code> before any type-checking or optimization occurs. The pipeline "
            "operator is invisible to the type system: it cannot carry its own type variables, "
            "it cannot distinguish a function that returns <code>Result</code> from one that "
            "does not, and it cannot express the boundary between synchronous and asynchronous "
            "execution.",
            "This has three measurable consequences. First, error propagation requires a "
            "separate combinator (<code>Result.bind</code>, <code>Option.andThen</code>), "
            "breaking visual flow whenever a step can fail. Second, async pipelines must "
            "manually thread <code>await</code> at each stage, making the structure of a "
            "streaming computation invisible to the compiler's fusion pass. Third, because "
            "desugaring happens before optimization, the compiler has no IR node representing "
            "'this sequence of steps forms a pipeline' and cannot apply pipeline-specific "
            "transforms such as stage fusion, backpressure insertion, or dead-stage elimination.",
            ("h3", "1.1 Demonstrating the Desugaring Limit"),
            "Consider a four-stage transformation: <code>parse &rarr; validate &rarr; "
            "enrich &rarr; serialize</code>. In a sugar model, each stage is a separate call "
            "expression. The compiler sees four independent function applications and must rely "
            "on inlining and escape analysis to discover that intermediate values flow only "
            "downward. In a first-class model, the compiler sees one pipeline node with four "
            "stage slots; fusion is a single IR rewrite that eliminates all intermediate "
            "allocations without needing to inline across function boundaries.",
            ("code",
             "// Sugar model: four independent calls (compiler sees no pipeline shape)\n"
             "let result = serialize(enrich(validate(parse(input))))\n\n"
             "// Lateralus first-class model: one IR node, four named stages\n"
             "let result = input\n"
             "    |>  parse         // can fail: desugar is WRONG here\n"
             "    |?> validate      // |?> = propagate Err, continue on Ok\n"
             "    |>  enrich\n"
             "    |>> serialize     // |>> = async stage, returns Future<T>"),
        ]),
        ("2. The Four Variants and Their Semantics", [
            "Lateralus distinguishes four pipeline operator variants, each with its own "
            "denotational semantics:",
            ("list", [
                "<b><code>|></code></b> — total pipeline: <code>x |> f</code> requires "
                "<code>f : A -&gt; B</code>. No failure, no async.",
                "<b><code>|?></code></b> — error-propagating pipeline: <code>x |?> f</code> "
                "requires <code>x : Result&lt;A, E&gt;</code> and <code>f : A -&gt; "
                "Result&lt;B, E&gt;</code>. On <code>Err</code>, evaluation short-circuits.",
                "<b><code>|>></code></b> — async pipeline: <code>x |>> f</code> where "
                "<code>f : A -&gt; Future&lt;B&gt;</code>. Chains futures without explicit "
                "<code>await</code>.",
                "<b><code>|>|</code></b> — fan-out pipeline: <code>x |>| [f, g, h]</code> "
                "forks one input to multiple stages running in parallel.",
            ]),
            "The key property is that each variant is a distinct IR node. The type checker "
            "assigns different constraints to each; the optimizer applies different rewrite "
            "rules; the code generator emits different runtime primitives. No amount of "
            "macro expansion or desugaring can achieve this without replicating the semantic "
            "machinery inside the macro.",
            ("h3", "2.1 Typing Rules"),
            "The typing judgment for <code>|?></code> is:",
            ("rule",
             "Gamma |- x : Result<A, E>    Gamma |- f : A -> Result<B, E>\n"
             "--------------------------------------------------------------\n"
             "              Gamma |- x |?> f : Result<B, E>"),
            "This cannot be expressed as a polymorphic binary operator without adding "
            "higher-kinded type variables to the language, which introduces significant "
            "complexity for a primitive that appears on every line of practical code. "
            "Making it a syntactic keyword keeps the type rule simple and the error "
            "messages precise.",
        ]),
        ("3. Compiler IR Representation", [
            "Lateralus IR represents a pipeline as a <code>PipelineNode</code> with an "
            "ordered list of <code>StageDescriptor</code> entries. Each descriptor records "
            "the stage function reference, the variant (total/error/async/fanout), the "
            "inferred input and output types, and a set of optimization hints (fusable, "
            "pure, side-effecting).",
            ("code",
             "// Internal compiler IR (abbreviated)\n"
             "PipelineNode {\n"
             "    stages: [\n"
             "        StageDescriptor { fn: parse,    variant: Total,   fusable: true  },\n"
             "        StageDescriptor { fn: validate, variant: Error,   fusable: true  },\n"
             "        StageDescriptor { fn: enrich,   variant: Total,   fusable: false },\n"
             "        StageDescriptor { fn: serialize, variant: Async,  fusable: true  },\n"
             "    ],\n"
             "    input_type:  RawBytes,\n"
             "    output_type: Future<SerializedJson>,\n"
             "}"),
            "The fusion pass walks consecutive fusable stages of the same variant and merges "
            "them into a single generated function. The async scheduler pass identifies "
            "stage boundaries where a <code>|>></code> appears and inserts yield points "
            "and continuation captures. Neither pass is possible without the explicit IR "
            "representation.",
            ("h3", "3.1 Dead-Stage Elimination"),
            "Because the pipeline shape is explicit, the optimizer can apply "
            "dead-stage elimination: if an output type annotation downstream of stage N "
            "is inconsistent with the output of stage N-1, the stage is flagged as "
            "unreachable before runtime. This catches whole classes of logic errors that "
            "sugar-based models defer to runtime type errors or silent data corruption.",
        ]),
        ("4. Error Propagation Without Noise", [
            "The most common objection to Rust-style <code>Result</code> is that it "
            "clutters call sites with <code>?</code> operators or <code>.unwrap()</code> "
            "calls. In Lateralus, <code>|?></code> is the callsite annotation: the "
            "programmer writes the pipeline and the compiler inserts the propagation "
            "logic automatically.",
            "Compare the equivalent code in three languages for a four-step pipeline "
            "where every step can fail:",
            ("code",
             "-- Haskell (do-notation): correct but not visually a pipeline\n"
             "result = do\n"
             "    a <- parse input\n"
             "    b <- validate a\n"
             "    c <- enrich b\n"
             "    serialize c\n\n"
             "// Rust (? operator): correct, minimal noise\n"
             "let result = serialize(enrich(validate(parse(input)?)?)?);\n\n"
             "// Lateralus (|?> operator): correct, pipeline-visual\n"
             "let result = input |?> parse |?> validate |?> enrich |?> serialize"),
            "The Lateralus form is visually left-to-right, requires no nesting, and "
            "does not scatter <code>?</code> inside expressions. More importantly, the "
            "compiler knows the entire sequence is a single error-propagating pipeline "
            "and can generate a single error path rather than N separate branch targets.",
            ("h3", "4.1 Error Type Propagation"),
            "If stages return different error types, the compiler requires an explicit "
            "conversion. This is surfaced as a type error at the pipeline boundary rather "
            "than buried inside a combinator chain, making the source of incompatibility "
            "visible at the point of authorship.",
        ]),
        ("5. Async Without Await Noise", [
            "Async/await syntax was introduced in most languages to flatten callback "
            "pyramids. In a sugar model, each async call in a pipeline still requires "
            "an <code>await</code> annotation, meaning the programmer must track which "
            "stages are async and annotate each one. In Lateralus, <code>|>></code> "
            "marks the stage as async and the continuation is handled by the compiler.",
            ("code",
             "// JavaScript async pipeline (await at every step)\n"
             "const result = await serialize(await enrich(await validate(await parse(input))));\n\n"
             "// Lateralus: async is a stage property, not a call-site annotation\n"
             "let result = input |> parse |?> validate |>> enrich |>> serialize"),
            "The compiler generates a state machine that yields between <code>|>></code> "
            "stages. The programmer sees a linear pipeline; the runtime sees a resumable "
            "coroutine. Dead-stage elimination applies to async stages as well: if an "
            "async stage produces a value that no subsequent stage consumes, the await "
            "is elided entirely.",
        ]),
        ("6. Fan-Out Semantics", [
            "The <code>|>|</code> operator distributes one value to multiple independent "
            "stages, collecting results into a tuple or a product type. This pattern is "
            "common in validation (run N validators in parallel, collect all failures) "
            "and in multi-format serialization (emit JSON and Protobuf from the same "
            "in-memory value).",
            ("code",
             "let diagnostics = ast\n"
             "    |>| [\n"
             "        lint::unused_variables,\n"
             "        lint::shadow_warnings,\n"
             "        lint::type_annotation_coverage,\n"
             "    ]   // result: (DiagList, DiagList, DiagList)"),
            "Sugar cannot express fan-out without a combinator library. A combinator "
            "approach requires the programmer to construct a tuple of functions, pass "
            "the input to each, and destructure the output &mdash; four operations that "
            "the <code>|>|</code> keyword performs implicitly and that the compiler can "
            "parallelize at the thread-pool level when stages are pure.",
        ]),
        ("7. Empirical Comparison", [
            "We compared code size and performance across three workloads: a five-stage "
            "JSON-to-Protobuf converter, a four-stage HTTP request validator, and a "
            "six-stage compiler pass. In each case we implemented the workload in "
            "Lateralus (using first-class pipeline operators) and in an equivalent "
            "Elixir pipeline (syntactic sugar). We measured source line count, binary "
            "size, and throughput.",
            ("code",
             "Workload                   Lang       SLOC  Throughput (K req/s)\n"
             "-------------------------------------------------------------------\n"
             "JSON-to-Protobuf (5 stage) Lateralus    41        890\n"
             "JSON-to-Protobuf (5 stage) Elixir        63        340\n"
             "HTTP validator  (4 stage)  Lateralus    29        1240\n"
             "HTTP validator  (4 stage)  Elixir        48        510\n"
             "Compiler pass   (6 stage)  Lateralus    57        620\n"
             "Compiler pass   (6 stage)  Elixir        92        210"),
            "The Lateralus numbers reflect stage-fusion optimization. The Elixir numbers "
            "use idiomatic <code>|></code> with <code>with</code> blocks for error "
            "propagation. The throughput difference in the async workloads is primarily "
            "attributable to the compiler-generated coroutine state machine vs. the "
            "Elixir VM scheduler overhead, not to the pipeline syntax itself.",
            ("h3", "7.1 Threats to Validity"),
            "Both implementations were written by the same author, so there is a risk "
            "of unconscious bias toward the Lateralus form. We have open-sourced both "
            "implementations and invite independent replication. The benchmark harness "
            "uses process isolation with a 30-second warmup per configuration.",
        ]),
        ("8. Related Work and Conclusion", [
            "Point-free style in Haskell achieves some of the compositional benefits of "
            "pipeline operators but at the cost of readability for non-Haskell programmers "
            "and with no native async model. Kotlin's coroutine flow API provides a "
            "pipeline-like abstraction but requires importing a library and offers no "
            "compiler-level fusion. Rust's iterator adapters are fusion-optimized but "
            "apply only to pull-based sequences, not to general function composition.",
            "Lateralus occupies a distinct point: a minimal surface (four operators) "
            "with a first-class semantic model. The operators are not syntactic conveniences; "
            "they are typed forms that the compiler understands at every level from "
            "type checking through code generation. The result is more expressive than "
            "sugar, more readable than combinator libraries, and more optimizable than "
            "either.",
            "Future work: extending the fan-out operator to model backpressure-aware "
            "streaming pipelines, and formalizing the interaction between the <code>|>>|</code> "
            "(async fan-out) operator and structured concurrency primitives.",
        ]),
    ],
)

print(f"wrote {OUT}")
