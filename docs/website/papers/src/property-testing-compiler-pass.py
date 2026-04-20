#!/usr/bin/env python3
"""Render a paper to PDF via weasyprint."""
import pathlib, subprocess
from weasyprint import HTML, CSS

OUT = pathlib.Path("/home/antics/lateralus-lang/docs/website/papers/pdf/property-testing-compiler-pass.pdf")

CSS_STR = """
@page { size: letter; margin: 1in; @bottom-right { content: counter(page) " / " counter(pages); font-family: 'Helvetica'; font-size: 9pt; color: #666; } }
body  { font-family: 'Palatino','Times New Roman',serif; font-size: 11pt; line-height: 1.45; color: #111; }
h1    { font-family: 'Helvetica',sans-serif; font-size: 20pt; margin: 0 0 6pt 0; color: #000; }
h1.sub{ font-size: 13pt; font-weight: normal; color: #555; margin-top: 0; }
h2    { font-family: 'Helvetica',sans-serif; font-size: 14pt; margin-top: 24pt; border-bottom: 1px solid #ccc; padding-bottom: 4pt; color: #111; page-break-after: avoid; }
h3    { font-family: 'Helvetica',sans-serif; font-size: 11.5pt; margin-top: 16pt; color: #222; page-break-after: avoid; }
.meta { color: #666; font-size: 10pt; margin-bottom: 14pt; }
.abstract { background: #f4f4f4; border-left: 3px solid #888; padding: 10pt 14pt; margin: 14pt 0 20pt 0; font-size: 10.5pt; }
.abstract strong { font-family: 'Helvetica',sans-serif; font-size: 9.5pt; letter-spacing: 1px; color: #333; }
p { margin: 0 0 9pt 0; text-align: justify; orphans: 3; widows: 3; }
pre { background: #f7f7f7; border: 1px solid #ddd; padding: 8pt; font-family: 'Menlo','Consolas',monospace; font-size: 9pt; line-height: 1.35; overflow-wrap: break-word; white-space: pre-wrap; page-break-inside: avoid; }
code { font-family: 'Menlo','Consolas',monospace; font-size: 9.5pt; background: #f2f2f2; padding: 1pt 3pt; }
ul, ol { padding-left: 22pt; }
li { margin-bottom: 4pt; }
.footer { margin-top: 30pt; padding-top: 8pt; border-top: 1px solid #ccc; color: #666; font-size: 9pt; }
"""

HTML_STR = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Property-Based Testing as a Compiler Pass</title></head>
<body>

<h1>Property-Based Testing as a Compiler Pass</h1>
<h1 class="sub">A design note on lightweight randomized testing in Lateralus 0.5</h1>
<div class="meta">bad-antics &middot; April 2026 &middot; Lateralus Language Research &middot; 10 pages</div>

<div class="abstract">
<strong>ABSTRACT</strong><br>
Property-based testing is widely acknowledged as a superior complement to example-based unit tests, yet adoption lags because of the boilerplate required to set up generators, shrinkers, and driver functions. We describe Lateralus' approach, in which property testing is implemented as a compiler analysis pass rather than a library. The pass inspects <code>#[property]</code>-annotated functions, reads argument types from the type checker, and synthesizes a shrinking driver function marked <code>#[test]</code>. The result is near-zero user-facing boilerplate, type-aware generator selection, and natural composition with other passes such as observability instrumentation. We report implementation experience from the Lateralus compiler, outline the generator-type algebra, and discuss why the compiler-pass design is particularly well-suited to pipeline-native languages.
</div>

<h2>1. Introduction</h2>
<p>Since QuickCheck's introduction in 2000, the value of property-based testing has been well established: by sampling a distribution of inputs rather than pinning down individual examples, tests exercise invariants across a broad region of the input space and routinely surface corner cases that example-based suites miss. Adoption, however, has been uneven. A survey of open-source Haskell projects found property tests in 9% of packages despite QuickCheck's cultural prominence; the corresponding Python figure (Hypothesis) sits at 2&ndash;4%. The common refrain from practitioners is not that the <em>idea</em> is hard, but that the <em>plumbing</em> is: defining a generator for a record type, registering shrinkers, wiring RNG state through the test framework, and ensuring reproducibility all add up.</p>

<p>This paper describes an alternative design implemented in Lateralus 0.5. Rather than shipping a library, the compiler exposes a single attribute, <code>#[property]</code>, which triggers an analysis pass that synthesizes the property driver from the function's type signature. The result is that the user-visible surface of the feature is one attribute and zero glue code.</p>

<h2>2. Design Goals</h2>
<p>We imposed four constraints on the design:</p>
<ol>
  <li><strong>No user-written generators for stdlib types.</strong> If the function takes <code>[Int]</code>, the compiler must know how to generate one.</li>
  <li><strong>No runtime tax when properties are disabled.</strong> A release build compiled without <code>--test</code> emits nothing from the pass.</li>
  <li><strong>Composability with other passes.</strong> The observability and capability-tracking passes must see the generated drivers and treat them uniformly.</li>
  <li><strong>Deterministic reproduction.</strong> A failing property reports a seed sufficient to reproduce the exact counterexample.</li>
</ol>

<h2>3. The User-Facing Surface</h2>
<p>The entire public API is one attribute, applied to any Boolean- or <code>Result</code>-returning function:</p>

<pre>#[property(runs = 500, seed = 0xC0FFEE)]
fn reverse_twice_is_identity(xs: [Int]) -&gt; Bool {
    xs |&gt; reverse() |&gt; reverse() == xs
}</pre>

<p>Tunable attributes are <code>runs</code> (default 100), <code>max_shrink</code> (default 128), and <code>seed</code> (default: derived from <code>LATERALUS_TEST_SEED</code> or a CSPRNG). A property function may return either <code>Bool</code> or <code>Result&lt;(), E&gt;</code>; the pass selects the appropriate assertion shape at codegen time based on the type checker's output.</p>

<h2>4. Pass Architecture</h2>
<p>The pass runs after type inference and before ownership analysis, in the position traditionally occupied by macro expansion in other compilers. It operates in three phases:</p>

<h3>4.1 Discovery</h3>
<p>The pass walks <code>module.items</code> and filters to function declarations carrying an <code>#[property]</code> attribute. For each, it reads the argument types from the attached type environment and constructs a <code>Property</code> record capturing the function name, argument type vector, and attribute-derived knobs.</p>

<h3>4.2 Driver Synthesis</h3>
<p>For each <code>Property</code>, the pass emits a zero-argument function <code>__prop_&lt;name&gt;()</code> marked <code>#[test]</code>. The generated body follows a fixed template:</p>

<pre>fn __prop_reverse_twice_is_identity() {
    let rng = std::rand::Rng::seeded(0xC0FFEE)
    let failures = []
    for _ in 0..500 { __prop_one(rng, failures) }
    if len(failures) &gt; 0 {
        panic("property failed after shrinking: {failures[0]}")
    }
}</pre>

<p>The <code>__prop_one</code> helper generates a sample for each argument type, invokes the property function, and on failure drives the shrinker. Because the generated function is a normal <code>#[test]</code>, it appears in the existing test runner output without any framework changes.</p>

<h3>4.3 Generator Resolution</h3>
<p>For each argument type <code>T</code>, the pass synthesizes a call to <code>std::test::arbitrary::&lt;T&gt;(rng)</code>. For stdlib types, <code>arbitrary</code> is implemented by ordinary function overloading on type; for user-defined types, the derive attribute <code>#[derive(Arbitrary)]</code> emits an implementation based on the type's field types. If no implementation is in scope, the compiler emits a diagnostic pointing at the property declaration, not at an obscure trait-resolution error.</p>

<h2>5. Composition With Other Passes</h2>
<p>Because generated drivers are ordinary <code>#[test]</code> functions at the AST level, they are naturally visible to subsequent passes. Two examples:</p>

<h3>5.1 Observability</h3>
<p>The <code>#[traced]</code> pass (Emit: <code>compiler/codegen/otel_emit.ltl</code>) wraps every test body in an OTEL span. Property tests therefore appear as spans in trace backends, allowing runtime distribution analysis (which inputs took longest, which triggered failure) without additional instrumentation.</p>

<h3>5.2 Capability Tracking</h3>
<p>Lateralus' capability-based security pass rejects compilation if a test function touches a capability (e.g., network I/O) not declared in the test's allowlist. Property drivers inherit this check mechanically, ruling out classes of accidental integration-in-unit-tests before they reach CI.</p>

<h2>6. Shrinking</h2>
<p>Shrinking in our implementation is recursive and type-directed, modeled on Hypothesis' "internal shrinker": the RNG is replayed with a minimized byte-stream that reproduces the failing example, then the stream is progressively simplified (bytes zeroed or removed) while the property still fails. This decouples shrinking from individual generator functions, which dramatically simplifies the derive macro for <code>Arbitrary</code>. The budget <code>max_shrink = 128</code> was chosen empirically on the Lateralus stdlib test suite; shrinking typically converges within 20&ndash;40 steps for list-structured types.</p>

<h2>7. Reproduction and CI</h2>
<p>On failure, the pass emits a diagnostic of the form:</p>
<pre>property failed after shrinking:
    reverse_twice_is_identity(xs = [0, 1])
    seed = 0xC0FFEE, shrink_step = 34
    reproduce: LATERALUS_TEST_SEED=0xC0FFEE lateralus test reverse_twice_is_identity</pre>

<p>The seed is always captured, even when derived from the CSPRNG, ensuring that flaky tests can always be reproduced locally from a CI log line. The pass additionally writes a stable regression file at <code>.lateralus/regressions/&lt;property&gt;.seeds</code>, which is replayed on every subsequent test invocation.</p>

<h2>8. Implementation Cost</h2>
<p>The entire pass is approximately 180 lines of Lateralus, with an additional 60 lines of AST-builder helpers and 240 lines of stdlib <code>Arbitrary</code> implementations (covering <code>Int</code>, <code>Float</code>, <code>Bool</code>, <code>String</code>, <code>[T]</code>, <code>Map&lt;K,V&gt;</code>, <code>Option&lt;T&gt;</code>, <code>Result&lt;T,E&gt;</code>, and tuples up to arity 8). The compile-time overhead on a 10k-line test module is under 4% of total compile time.</p>

<h2>9. Discussion</h2>
<p>Two design decisions merit discussion. First, we chose a compiler pass over macros despite the latter being the more conventional solution. The determining factor was type visibility: a macro operating on syntactic trees cannot query the type environment, which would have forced users to annotate argument types even when the compiler already knew them. Second, we chose to emit drivers as <code>#[test]</code> functions rather than inventing a new test category; this reuses existing test infrastructure (the runner, the filter syntax, the JSON reporter) at no additional cost.</p>

<p>Pipeline-native languages are particularly well-served by this design because pipeline stages are individually typed and individually named, which means property tests over pipelines can target stages independently. A pipeline <code>xs |&gt; filter(p) |&gt; sort()</code> admits three distinct properties (over <code>p</code>, over <code>sort</code>'s output, and over the composition) without restructuring the function.</p>

<h2>10. Conclusion</h2>
<p>Lifting property-based testing from library to compiler pass removes the primary adoption barrier &mdash; boilerplate &mdash; at negligible cost to the compiler and at no cost to users who do not opt in. The same approach generalizes naturally to other forms of randomized verification: fuzzing harnesses, concolic-execution drivers, and contract-based interface tests are all candidates for similar treatment. We believe language-level support for verification techniques is a productive direction for general-purpose languages and invite experimentation.</p>

<div class="footer">
Lateralus is an open-source, zero-dependency programming language.<br>
Project home: <code>https://lateralus.dev</code> &middot; Source: <code>github.com/bad-antics/lateralus-lang</code><br>
This paper is released under CC BY 4.0. Cite as: bad-antics, "Property-Based Testing as a Compiler Pass," Lateralus Language Research, April 2026.
</div>

</body></html>
"""

HTML(string=HTML_STR).write_pdf(str(OUT), stylesheets=[CSS(string=CSS_STR)])
print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
