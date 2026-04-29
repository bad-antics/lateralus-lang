#!/usr/bin/env python3
"""Render 'Pattern Matching and ADTs in Lateralus' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "pattern-matching-adts.pdf"

render_paper(
    out_path=str(OUT),
    title="Pattern Matching and ADTs in Lateralus",
    subtitle="Sum types, exhaustiveness checking, and guard expressions",
    meta="bad-antics &middot; December 2024 &middot; Lateralus Language Research",
    abstract=(
        "Algebraic data types (ADTs) and pattern matching are the primary tools for "
        "modeling domain concepts in Lateralus. This paper describes the "
        "<code>enum</code> declaration form for sum types, the <code>match</code> "
        "expression for exhaustive pattern matching, the guard expression extension, "
        "and how ADTs integrate with the four pipeline operators. We pay particular "
        "attention to exhaustiveness checking &mdash; the compiler analysis that ensures "
        "every possible value of an ADT is handled &mdash; and to the interaction between "
        "patterns and the error propagation operator."
    ),
    sections=[
        ("1. Algebraic Data Types", [
            "An algebraic data type in Lateralus is declared with the <code>enum</code> "
            "keyword. Each variant can carry zero or more fields:",
            ("code",
             "enum Shape {\n"
             "    Circle { radius: f64 },\n"
             "    Rectangle { width: f64, height: f64 },\n"
             "    Triangle { base: f64, height: f64 },\n"
             "    Point,   // unit variant: no fields\n"
             "}\n\n"
             "enum ParseResult<T> {\n"
             "    Ok(T),\n"
             "    Err(ParseError),\n"
             "    Incomplete { needed: usize },\n"
             "}"),
            "ADTs are the canonical way to represent data that can take one of "
            "several distinct forms. The compiler tracks which variant a value has "
            "at compile time and flags any code that accesses a variant's fields "
            "without first matching to determine which variant is present.",
        ]),
        ("2. Pattern Matching: The match Expression", [
            "The <code>match</code> expression destructures a value against a list "
            "of patterns. The first matching pattern wins; its bound variables are "
            "in scope in the body:",
            ("code",
             "let area = match shape {\n"
             "    Shape::Circle { radius }       => math::pi * radius * radius,\n"
             "    Shape::Rectangle { width, height } => width * height,\n"
             "    Shape::Triangle { base, height }   => 0.5 * base * height,\n"
             "    Shape::Point                   => 0.0,\n"
             "}"),
            "Patterns can bind values, ignore values with <code>_</code>, and "
            "use range patterns for numeric types.",
            ("h3", "2.1 Nested Patterns"),
            "Patterns can be arbitrarily nested: a pattern for a "
            "<code>Result&lt;Shape, Error&gt;</code> can simultaneously match "
            "the outer variant and destructure the inner value:",
            ("code",
             "let result = match parse_shape(input) {\n"
             "    Ok(Shape::Circle { radius }) if radius > 0.0 => process_circle(radius),\n"
             "    Ok(Shape::Circle { .. })                      => Err(\"zero radius\"),\n"
             "    Ok(other)                                     => process_other(other),\n"
             "    Err(e)                                        => Err(e.to_string()),\n"
             "}"),
        ]),
        ("3. Exhaustiveness Checking", [
            "The compiler checks that every match expression covers all possible "
            "values of the matched type. A match is exhaustive if for every possible "
            "constructor and field combination, at least one arm matches.",
            "The exhaustiveness checker uses the 'useful' algorithm from Maranget "
            "(2007): a matrix of patterns is checked for usefulness, where a "
            "pattern is useful if it covers at least one case not covered by "
            "earlier patterns.",
            ("code",
             "// Compiler error: non-exhaustive match\n"
             "let area = match shape {\n"
             "    Shape::Circle { radius }    => math::pi * radius * radius,\n"
             "    Shape::Rectangle { width, height } => width * height,\n"
             "    // missing: Triangle and Point\n"
             "};\n"
             "// error[E0301]: non-exhaustive match on Shape\n"
             "// not covered: Triangle { .. }, Point"),
            "The error message lists exactly which constructors are missing, "
            "making the fix obvious. Adding a wildcard arm (<code>_ => ...</code>) "
            "makes the match exhaustive but loses the compile-time guarantee that "
            "new variants will be handled when added.",
            ("h3", "3.1 Sealed Enums and Exhaustiveness"),
            "A <code>sealed enum</code> cannot be extended by downstream code, "
            "guaranteeing that the set of variants is fixed. The exhaustiveness "
            "checker relies on this property: if an enum is not sealed, the checker "
            "cannot prove exhaustiveness for code outside the defining module.",
        ]),
        ("4. Guard Expressions", [
            "A guard is a boolean expression attached to a match arm that further "
            "refines which values the arm matches. If the guard evaluates to false, "
            "the arm is skipped and the next arm is tried:",
            ("code",
             "let classification = match n {\n"
             "    n if n < 0    => \"negative\",\n"
             "    0             => \"zero\",\n"
             "    n if n < 100  => \"small positive\",\n"
             "    n if n < 1000 => \"medium positive\",\n"
             "    _             => \"large positive\",\n"
             "}"),
            "Guards interact with exhaustiveness checking: a match arm with a "
            "guard is not considered to fully cover the pattern it matches. "
            "A match that covers all constructors but with guards on every arm "
            "is still non-exhaustive.",
        ]),
        ("5. ADTs and Pipeline Operators", [
            "The <code>|?></code> operator's error type is a special case of ADTs: "
            "<code>Result&lt;T, E&gt;</code> is the ADT <code>enum Result { Ok(T), Err(E) }</code>. "
            "The error operator short-circuits on <code>Err</code>, which is equivalent "
            "to matching the <code>Err</code> arm and returning early.",
            "General ADTs can be used as pipeline values. A function that transforms "
            "a <code>Shape</code> to another <code>Shape</code> is a valid "
            "<code>|></code> stage. A function that fails on degenerate cases "
            "(zero-radius circles) can return <code>Result&lt;Shape, ShapeError&gt;</code> "
            "and be used as a <code>|?></code> stage.",
            ("code",
             "fn normalize_shape(s: Shape) -> Result<Shape, ShapeError> {\n"
             "    match s {\n"
             "        Shape::Circle { radius } if radius <= 0.0 =>\n"
             "            Err(ShapeError::DegenerateRadius),\n"
             "        Shape::Rectangle { width, height } if width <= 0.0 || height <= 0.0 =>\n"
             "            Err(ShapeError::DegenerateDimension),\n"
             "        valid => Ok(valid),\n"
             "    }\n"
             "}\n\n"
             "let area = input_shape\n"
             "    |?> normalize_shape\n"
             "    |>  compute_area"),
        ]),
        ("6. Or-Patterns and Pattern Binding", [
            "Multiple patterns can be combined with <code>|</code> to match "
            "any of several cases with the same arm body. All branches of an "
            "or-pattern must bind the same set of variables with the same types:",
            ("code",
             "let is_degenerate = match shape {\n"
             "    Shape::Circle { radius: r }   if r <= 0.0 => true,\n"
             "    Shape::Rectangle { width: w, .. } if w <= 0.0 => true,\n"
             "    Shape::Rectangle { height: h, .. } if h <= 0.0 => true,\n"
             "    _ => false,\n"
             "}"),
            "Or-patterns at the top level of a match arm are supported; "
            "nested or-patterns (inside a tuple or struct pattern) are also "
            "supported and interact with exhaustiveness checking as expected.",
        ]),
        ("7. ADTs in the Type System", [
            "ADT variants are types: <code>Shape::Circle</code> is a type with "
            "a single constructor and fields <code>{ radius: f64 }</code>. "
            "This makes the type system consistent: pattern matching is "
            "structural decomposition, and the exhaustiveness checker works "
            "over the same type information that the rest of the type system uses.",
            "Generic ADTs follow the same rules. A "
            "<code>Result&lt;T, E&gt;</code> is exhaustively matched by "
            "<code>Ok(t)</code> and <code>Err(e)</code> for any T and E. "
            "The type parameters are inferred from context.",
        ]),
        ("8. Practical Patterns", [
            "Two ADT patterns that appear frequently in Lateralus codebases:",
            ("h3", "8.1 The Newtype Pattern"),
            "Wrapping a primitive in a unit-variant enum to distinguish "
            "semantically different values with the same underlying type:",
            ("code",
             "enum UserId(u64);\n"
             "enum SessionId(u64);\n\n"
             "// Compiler prevents swapping UserId and SessionId even though\n"
             "// both are u64 underneath\n"
             "fn find_user(id: UserId) -> Option<User> { ... }"),
            ("h3", "8.2 The Builder ADT Pattern"),
            "Using an ADT to represent the states of a builder, making "
            "it impossible to call <code>build()</code> without providing "
            "required fields:",
            ("code",
             "enum RequestBuilder {\n"
             "    Empty,\n"
             "    WithUrl { url: str },\n"
             "    WithUrlAndMethod { url: str, method: HttpMethod },\n"
             "}\n\n"
             "// Only WithUrlAndMethod can be built\n"
             "fn build(b: RequestBuilder::WithUrlAndMethod) -> Request { ... }"),
        ]),
    ],
)

print(f"wrote {OUT}")
