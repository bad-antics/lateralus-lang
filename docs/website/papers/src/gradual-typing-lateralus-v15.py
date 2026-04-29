#!/usr/bin/env python3
"""Render 'Gradual Typing in Lateralus v1.5' in canonical Lateralus style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "gradual-typing-lateralus-v15.pdf"

render_paper(
    out_path=str(OUT),
    title="Gradual Typing in Lateralus v1.5",
    subtitle="The dyn type, consistency relation, and type-safe interop with dynamic data",
    meta="bad-antics &middot; November 2024 &middot; Lateralus Language Research",
    abstract=(
        "Lateralus v1.5 introduces gradual typing via the <code>dyn</code> type: a "
        "value of type <code>dyn</code> can hold any Lateralus value and can be passed "
        "anywhere without a type error. Type casts from <code>dyn</code> to a concrete "
        "type are checked at runtime. The gradual type system is based on the "
        "consistency relation of Siek &amp; Taha (2006): a <code>dyn</code> value is "
        "consistent with any concrete type, and the consistency relation replaces "
        "equality in the type rules for expressions involving <code>dyn</code>. "
        "This paper specifies the gradual type system, explains its interaction with "
        "pipeline operators and error propagation, and evaluates the runtime overhead "
        "of cast checks."
    ),
    sections=[
        ("1. Motivation: Interop with Dynamic Data", [
            "Fully static type systems excel at enforcing invariants over data "
            "the programmer controls. They are less ergonomic for data whose "
            "structure is known only at runtime: JSON API responses, configuration "
            "files, plugin return values, and script-evaluated expressions.",
            "Rather than requiring the programmer to write a fully-typed decoder "
            "before using any external data, Lateralus v1.5 allows external data "
            "to enter the program as <code>dyn</code> and be cast to concrete "
            "types at the boundary where they are used. This shifts type checking "
            "from compile time to runtime for the dynamic portion, while preserving "
            "full static checking everywhere else.",
            ("code",
             "// Parse a JSON blob — value is dyn\n"
             "let data: dyn = json::parse(response_body)?;\n\n"
             "// Cast to a concrete type at the use site\n"
             "let name: str = data[\"name\"].cast::<str>()?;\n"
             "let age: u32  = data[\"age\"].cast::<u32>()?;\n\n"
             "// From here, name and age are statically typed"),
        ]),
        ("2. The Consistency Relation", [
            "Two types <code>A</code> and <code>B</code> are consistent "
            "(written <code>A ~ B</code>) if they can appear in place of each "
            "other in a context that expects either. The consistency relation "
            "is reflexive and symmetric but not transitive:",
            ("rule",
             "-- Reflexivity\n"
             "A ~ A     for any type A\n\n"
             "-- dyn is consistent with everything\n"
             "A ~ dyn   for any type A\n"
             "dyn ~ A   for any type A\n\n"
             "-- NOT transitive:\n"
             "str ~ dyn ~ u32  does NOT imply str ~ u32"),
            "The consistency relation replaces equality in the type rule for "
            "function application: if a function expects type <code>A</code> and "
            "the argument has type <code>B</code> where <code>A ~ B</code>, the "
            "application is type-correct at compile time. If <code>B = dyn</code>, "
            "the compiler inserts a runtime cast check.",
            ("rule",
             "-- Gradual function application\n"
             "Gamma |- f : A -> C    Gamma |- x : B    A ~ B\n"
             "------------------------------------------------\n"
             "         Gamma |- f(x) : C  (+ cast check if B = dyn)"),
        ]),
        ("3. dyn in Pipeline Stages", [
            "A pipeline stage that accepts <code>dyn</code> can receive any "
            "value from the previous stage. A stage that produces <code>dyn</code> "
            "can feed any downstream stage. The consistency relation handles "
            "the type rules:",
            ("code",
             "let result = json_data     // dyn\n"
             "    |> extract_fields      // dyn -> dyn (structural extraction)\n"
             "    |?> cast_to_user       // dyn -> Result<User, CastError>\n"
             "    |>  process_user       // User -> ProcessedUser (fully typed)"),
            "The pipeline transitions from dynamic to static at the "
            "<code>cast_to_user</code> stage. After that stage, the type is "
            "statically known as <code>User</code> and all subsequent stages "
            "are checked at compile time with no runtime overhead.",
            ("h3", "3.1 Dynamic Pipelines"),
            "A fully dynamic pipeline (all stages accept and return <code>dyn</code>) "
            "behaves like a dynamically typed language for that section of code. "
            "The compiler inserts cast checks at every stage boundary. This is "
            "useful for scripting-like DSLs or for pipeline stages loaded from "
            "plugins at runtime.",
        ]),
        ("4. Cast Semantics", [
            "A cast from <code>dyn</code> to type <code>T</code> checks whether "
            "the runtime tag of the value matches <code>T</code>. If it matches, "
            "the cast succeeds and returns <code>Ok(t)</code>. If it does not, "
            "the cast returns <code>Err(CastError { expected: T, actual: tag })</code>.",
            ("code",
             "fn cast<T>(v: dyn) -> Result<T, CastError> {\n"
             "    if v.tag() == TypeId::of::<T>() {\n"
             "        Ok(unsafe { v.into_inner::<T>() })\n"
             "    } else {\n"
             "        Err(CastError { expected: TypeId::of::<T>(), actual: v.tag() })\n"
             "    }\n"
             "}"),
            "The cast always returns <code>Result</code>, making it compatible "
            "with <code>|?></code>. A pipeline that casts at every stage and "
            "short-circuits on failure produces a clean error message that includes "
            "the expected and actual types at the stage where the cast failed.",
        ]),
        ("5. The Blame System", [
            "In gradual type systems, a cast failure at runtime may be caused by "
            "a type error at a definition site far from the cast. The blame system "
            "tracks which part of the code is responsible for a cast failure: the "
            "producer that put the wrong type into a <code>dyn</code> container, "
            "or the consumer that expected a type the producer cannot provide.",
            "Lateralus implements a lightweight blame system: every <code>dyn</code> "
            "value carries a source location tag that records where it was created. "
            "When a cast fails, the error includes both the cast location (the "
            "consumer) and the creation location (the producer).",
            ("code",
             "error[E0601]: cast failure\n"
             "  --> src/handler.lt:42:8\n"
             "   |\n"
             "42 |     |?> cast_to_user  // expected: User\n"
             "   |         ^^^^^^^^^^^ cast to User failed\n"
             "   |\n"
             "note: dyn value was created here with type XmlDoc\n"
             "  --> src/parser.lt:18:5\n"
             "18 |     let data: dyn = parse_xml(body)\n"
             "   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ XmlDoc introduced as dyn"),
        ]),
        ("6. Performance: Cast Check Overhead", [
            "Each runtime cast check is a pointer comparison between the value's "
            "type tag and the expected <code>TypeId</code>. On a modern processor, "
            "this is a single branch instruction with a predictable outcome for "
            "hot paths.",
            ("code",
             "Benchmark                    Cast overhead   Notes\n"
             "------------------------------------------------------\n"
             "Hot path (100% hit rate)       < 0.5 ns     branch predictor\n"
             "Mixed (80% hit rate)           ~1.2 ns      occasional mispredict\n"
             "Cold path (0% hit rate)        ~3.5 ns      type error, rare\n"
             "Dynamic pipeline (all dyn)    ~10 ns/stage  tag check at every boundary"),
            "The cast overhead is negligible for hot paths. For fully dynamic "
            "pipelines, the 10 ns/stage overhead accumulates: a 10-stage dynamic "
            "pipeline adds ~100 ns compared to a fully static one. This is "
            "acceptable for interop code but argues against using <code>dyn</code> "
            "in performance-critical inner loops.",
        ]),
        ("7. Migration Path: dyn to Static", [
            "The gradual type system is intended as a migration tool, not a "
            "permanent state. Code that begins with <code>dyn</code> boundaries "
            "should progressively narrow them as the data schema is understood "
            "and stabilized.",
            "The compiler provides a <code>--find-dyn</code> flag that reports "
            "all <code>dyn</code> expressions in a codebase, grouped by the number "
            "of times each one is cast to a specific type. When a <code>dyn</code> "
            "value is always cast to <code>T</code>, the compiler suggests "
            "replacing <code>dyn</code> with <code>T</code> at the source.",
        ]),
        ("8. Conclusion", [
            "Gradual typing via the <code>dyn</code> type and consistency relation "
            "extends Lateralus's static type system to accommodate dynamic data "
            "without abandoning static checking for fully-typed code. The blame "
            "system provides actionable runtime error messages. The cast overhead "
            "is negligible on hot paths.",
            "The gradual type system is compatible with all four pipeline operators: "
            "<code>dyn</code> can flow through total, error-propagating, async, "
            "and fan-out stages with appropriate cast checks inserted automatically. "
            "This makes the migration from dynamic to static typing a matter of "
            "adding type annotations, not rewriting pipeline structure.",
        ]),
    ],
)

print(f"wrote {OUT}")
