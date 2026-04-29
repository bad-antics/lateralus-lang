#!/usr/bin/env python3
"""Render 'Pipeline Calculus and Category Theory' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "pipeline-calculus-category-theory.pdf"

render_paper(
    out_path=str(OUT),
    title="Pipeline Calculus and Category Theory",
    subtitle="Arrows, profunctors, and the categorical structure of Lateralus pipelines",
    meta="bad-antics &middot; October 2025 &middot; Lateralus Language Research",
    abstract=(
        "The Lateralus pipeline model has a precise categorical structure that goes "
        "beyond the denotational semantics given in earlier papers. In this paper "
        "we show that the total pipeline category is a Cartesian closed category "
        "(CCC), that the error pipeline category forms a Kleisli category over "
        "the Result monad, and that the fan-out operator corresponds to a "
        "product in the pipeline category. We additionally show that Lateralus "
        "pipelines are a special case of Hughes's Arrows, specifically "
        "ArrowChoice, and identify the profunctor structure that enables "
        "bidirectional pipeline composition."
    ),
    sections=[
        ("1. Cartesian Closed Category of Total Pipelines", [
            "The category <b>Lat</b><sub>tot</sub> of total Lateralus pipelines "
            "is Cartesian closed: it has finite products (encoded as record types) "
            "and exponentials (encoded as pipeline function types).",
            ("rule",
             "-- Terminal object: unit type ()\n"
             "A × ()  ≅  A\n\n"
             "-- Product: record type\n"
             "A × B  ≅  { first: A, second: B }\n\n"
             "-- Exponential: Pipeline<A, B>\n"
             "C^A  ≅  Pipeline<A, C>"),
            "The CCC structure implies that the pipeline model is computationally "
            "complete for total computations: any function that can be expressed "
            "as a lambda calculus term can be expressed as a Lateralus total "
            "pipeline. The converse also holds by the Church-Rosser theorem "
            "for CCCs.",
        ]),
        ("2. The Result Monad and Kleisli Category", [
            "The error pipeline operator <code>|?></code> is Kleisli composition "
            "in the Result monad. We review the monad laws and verify that the "
            "Lateralus Result type satisfies them:",
            ("rule",
             "-- Left identity\n"
             "return a >>= f  =  f a\n"
             "i.e.: Ok(a) |?> f  =  f(a)\n\n"
             "-- Right identity\n"
             "m >>= return  =  m\n"
             "i.e.: p |?> Ok  =  p\n\n"
             "-- Associativity\n"
             "(m >>= f) >>= g  =  m >>= (fun x -> f(x) >>= g)\n"
             "i.e.: (p |?> f) |?> g  =  p |?> (fun x -> f(x) |?> g)"),
            "These laws are provable by structural induction on the "
            "<code>Result</code> variants. The Kleisli category "
            "<b>Lat</b><sub>Result</sub> has objects that are Lateralus types "
            "and arrows from A to B that are Lateralus functions "
            "<code>A -&gt; Result&lt;B, E&gt;</code> for a fixed error type E.",
        ]),
        ("3. The Fan-Out Operator as a Product", [
            "The fan-out operator <code>|>|</code> corresponds to the "
            "diagonal morphism in a category with finite products. For "
            "an object A and morphisms f : A → B and g : A → C, the "
            "product of f and g is a morphism <code>(f, g) : A → B × C</code>:",
            ("rule",
             "-- Fan-out as diagonal/product morphism\n"
             "x |>| [f, g]  ≅  ⟨f, g⟩(x)  =  (f(x), g(x)) : B × C"),
            "The universal property of the product says that any morphism "
            "from A to a product B × C factors uniquely through the projections. "
            "This means that the fan-out operator is the unique morphism "
            "that makes the following diagram commute:",
            ("rule",
             "        A\n"
             "       / \\\n"
             "      f   g\n"
             "     /     \\\n"
             "    B   ×   C\n"
             "    |       |\n"
             "   π1      π2"),
        ]),
        ("4. Hughes's Arrows", [
            "Hughes (2000) introduced Arrows as a generalization of monads that "
            "captures more programming patterns. An Arrow is a type class with "
            "operations: <code>arr</code> (lift a function to an arrow), "
            "<code>&gt;&gt;&gt;</code> (sequential composition), and "
            "<code>first</code> (apply an arrow to the first component of a pair).",
            "Lateralus pipelines are Arrows. The correspondence is:",
            ("code",
             "Arrow operation     Lateralus equivalent\n"
             "-------------------------------------------\n"
             "arr f               pipe { |> f }         (lift to pipeline)\n"
             "p >>> q             p >> q                (compose)\n"
             "first p             x |>| [p, identity]   (apply to first component)"),
            "Furthermore, Lateralus pipelines satisfy ArrowChoice: the "
            "<code>left</code> operation (apply an arrow to the Left branch "
            "of an Either) corresponds to the recovery operator <code>|~></code> "
            "applied to the error component of a Result.",
        ]),
        ("5. Profunctors and Bidirectional Pipelines", [
            "A profunctor P : C^op × D → Set is a bifunctor contravariant in "
            "the first argument and covariant in the second. Profunctors "
            "generalize functions by allowing both 'input preprocessing' "
            "(contravariant) and 'output postprocessing' (covariant).",
            "Lateralus pipeline values are profunctors: a value "
            "<code>p : Pipeline&lt;A, B&gt;</code> can be pre-composed with "
            "a function <code>f : C -&gt; A</code> (covariant in the output, "
            "contravariant in the input) to get "
            "<code>p.dimap(f, identity) : Pipeline&lt;C, B&gt;</code>.",
            ("code",
             "// dimap: bidirectional pipeline adapter\n"
             "fn dimap<C, D>(p: Pipeline<A, B>, f: fn(C) -> A, g: fn(B) -> D)\n"
             "    -> Pipeline<C, D>\n\n"
             "// Usage: adapt a pipeline to different input/output types\n"
             "let adapted = my_pipeline.dimap(\n"
             "    |raw: &str| RawRequest::parse(raw),   // pre-process input\n"
             "    |resp: Response| resp.to_json()       // post-process output\n"
             ")"),
            "The profunctor structure makes pipeline adapters principled: "
            "any adapter that preserves the pipeline shape (not just function "
            "composition) can be expressed as a <code>dimap</code>.",
        ]),
        ("6. Monoidal Categories and Stage Parallelism", [
            "The fan-out operator gives the pipeline category a monoidal structure. "
            "A monoidal category has a tensor product ⊗ (here: parallel composition) "
            "and a unit object (here: the unit pipeline). The associativity and "
            "unit laws of a monoidal category correspond to the algebraic laws "
            "of the fan-out operator.",
            ("rule",
             "-- Monoidal laws for fan-out\n"
             "(p |>| q) |>| r  ≅  p |>| (q |>| r)  (associativity)\n"
             "unit |>| p       ≅  p                  (left unit)\n"
             "p |>| unit       ≅  p                  (right unit)"),
            "The monoidal structure is the categorical foundation for the "
            "scheduler's ability to run fan-out stages in parallel: "
            "parallel composition is monoidal product, and the scheduler "
            "exploits commutativity of independent products.",
        ]),
        ("7. Enriched Categories and Pipeline Metrics", [
            "For performance analysis, we can enrich the pipeline category "
            "over the category of real numbers with addition: each morphism "
            "(pipeline) is assigned a cost (execution time), and composition "
            "adds costs. This enriched category model is the foundation for "
            "the pipeline profiler.",
            "The profiler measures the actual execution cost of each stage "
            "and annotates the pipeline IR with the measured costs. The "
            "optimizer then uses these costs to decide which stages to "
            "fuse (fusion reduces cost if the combined stage avoids intermediate "
            "allocation overhead) and which to parallelize (parallel stages "
            "reduce wall-clock time if the CPU has spare cores).",
        ]),
        ("8. Implications for Language Design", [
            "The categorical structure of Lateralus pipelines has practical "
            "implications for language design:",
            ("list", [
                "The CCC structure implies the pipeline model is as expressive "
                "as the lambda calculus for total computations. No additional "
                "control flow operators are needed for the total fragment.",
                "The Kleisli structure implies the error operator is the unique "
                "correct way to compose Result-returning functions. Alternative "
                "designs (e.g., exceptions) do not form a Kleisli category.",
                "The Arrow structure implies that pipeline values can be "
                "transformed by the full Arrow combinator library, giving "
                "pipeline library authors a principled foundation for "
                "combinators.",
                "The profunctor structure implies that bidirectional adapters "
                "are always expressible without losing the pipeline kind.",
            ]),
            "These implications guided several design decisions in Lateralus: "
            "the decision to make pipelines first-class values (necessary for "
            "the CCC exponential), the decision to fix the error type within "
            "a pipeline (necessary for the Kleisli category), and the decision "
            "to support <code>dimap</code> as a built-in pipeline operation "
            "(the profunctor structure).",
        ]),
    ],
)

print(f"wrote {OUT}")
