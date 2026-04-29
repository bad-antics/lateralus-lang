#!/usr/bin/env python3
"""Render 'Lateralus Language Specification v1.0' to PDF."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "lateralus-spec-v1.0.pdf"

TITLE = "Lateralus Language Specification v1.0"
SUBTITLE = "Formal grammar, type system, and standard library for Lateralus v1.0"
META = "bad-antics &middot; December 2023 &middot; Lateralus Language Research"
ABSTRACT = (
    "This document defines the initial formal grammar, primitive and compound types, "
    "function definitions, pipeline operator (|>) semantics, pattern matching syntax, "
    "and the minimal standard library for Lateralus v1.0."
)

SECTIONS = [
    ("1. Document Scope and Conventions", [
        "This specification is the normative reference for Lateralus v1.0. It defines what programs "
        "are syntactically valid, what types they may have, and what they mean when executed. "
        "Any conforming implementation must accept every program the grammar permits and must "
        "assign those programs the semantics described in sections 7 through 14.",
        "Grammar productions are written in extended Backus-Naur Form (EBNF). Terminals appear in "
        "<code>fixed-width</code> type. The symbol <code>::=</code> separates a non-terminal "
        "from its definition; <code>|</code> separates alternatives; <code>*</code> and "
        "<code>+</code> are Kleene star and plus; <code>?</code> is optional.",
        "Type judgments are written in natural-deduction style: hypotheses appear above a horizontal "
        "rule and the conclusion below. The typing environment is denoted <code>Gamma</code>; "
        "the turnstile <code>|-</code> reads 'entails'. Metavariables: <code>e</code> for "
        "expressions, <code>t</code> for types, <code>x</code> for identifiers.",
        "Normative requirements use the keyword <b>MUST</b>; guidance uses <b>SHOULD</b>; "
        "permissions use <b>MAY</b>. Sections marked <b>(informative)</b> are not normative "
        "but provide rationale. All section cross-references are to sections within this document "
        "unless otherwise noted.",
        "v1.0 targets a single-pass tree-walking interpreter. No multi-file compilation, no "
        "separate linking step, and no unsafe blocks exist in v1.0. Subsequent versions "
        "extend this baseline; this document is the stable reference for v1.0 only.",
    ]),
    ("2. Lexical Grammar", [
        "The lexer consumes a UTF-8 byte stream and emits a flat token sequence. Whitespace "
        "(space, tab, carriage return, newline) is insignificant except as a token separator "
        "and inside string literals. Comments begin with <code>#</code> and extend to the end "
        "of the line; they produce no tokens.",
        ("h3", "2.1 Identifier and Keyword Tokens"),
        "An identifier matches the pattern <code>[a-zA-Z_][a-zA-Z0-9_]*</code>. The following "
        "identifiers are reserved as keywords and may not be used as user-defined names:",
        ("code",
         "fn       let      if       else     match    case     return\n"
         "enum     import   pub      use      true     false    and\n"
         "or       not      in       for      while    break    continue"),
        ("h3", "2.2 Literals"),
        "Integer literals are one or more ASCII digits, optionally prefixed with <code>0x</code> "
        "for hexadecimal or <code>0b</code> for binary. Float literals contain exactly one "
        "decimal point and match <code>[0-9]+\\.[0-9]+</code>. String literals are delimited "
        "by double quotes and support the escape sequences "
        "<code>\\n \\t \\\\ \\\" \\0</code>. Boolean literals are <code>true</code> and "
        "<code>false</code>.",
        ("h3", "2.3 Operator Tokens"),
        ("code",
         "|>   |?>   +    -    *    /    %    ==   !=   <    <=   >   >=\n"
         "=    ->   =>   ::   ,    ;    :    .    (    )    [    ]    {    }"),
    ]),
    ("3. Expression Grammar (BNF)", [
        "The expression grammar is presented in order of decreasing precedence. Lower-numbered "
        "levels bind more tightly. Section 10 lists the complete precedence table.",
        ("code",
         "expr        ::= pipe_expr\n"
         "pipe_expr   ::= cmp_expr (('|>' | '|?>') cmp_expr)*\n"
         "cmp_expr    ::= add_expr (('==' | '!=' | '<' | '<=' | '>' | '>=') add_expr)*\n"
         "add_expr    ::= mul_expr (('+' | '-') mul_expr)*\n"
         "mul_expr    ::= unary_expr (('*' | '/' | '%') unary_expr)*\n"
         "unary_expr  ::= ('-' | 'not') unary_expr | call_expr\n"
         "call_expr   ::= primary_expr ('(' arg_list? ')')*\n"
         "primary_expr::= literal | ident | '(' expr ')' | block | match_expr\n"
         "               | list_expr | if_expr\n"
         "block       ::= '{' stmt* '}'\n"
         "arg_list    ::= expr (',' expr)*\n"
         "list_expr   ::= '[' arg_list? ']'"),
        "The grammar is LL(1) after disambiguation: <code>if</code> and <code>match</code> are "
        "keywords consumed by <code>primary_expr</code>; block ambiguity is resolved by requiring "
        "that a statement-level block must follow a keyword.",
        "A <code>call_expr</code> is left-recursive in the grammar above but the parser flattens "
        "this into a loop: each <code>(arg_list)</code> suffix wraps the accumulated callee in a "
        "new <code>CallNode</code>. Chained calls <code>f(a)(b)</code> are valid.",
        "The expression grammar does not include assignment; assignment is a statement-level "
        "construct (Section 4). An expression used as a statement is followed by an optional "
        "semicolon; omitting the semicolon on the last expression in a block makes that "
        "expression the block's value.",
    ]),
    ("4. Statement Grammar", [
        "Statements are the top-level structural unit within a block. A program is a sequence "
        "of top-level declarations (Section 5); there is no implicit top-level block in v1.0.",
        ("code",
         "stmt        ::= let_stmt | return_stmt | while_stmt | for_stmt\n"
         "              | break_stmt | continue_stmt | expr_stmt\n"
         "let_stmt    ::= 'let' ident (':' type)? '=' expr ';'\n"
         "return_stmt ::= 'return' expr? ';'\n"
         "while_stmt  ::= 'while' expr block\n"
         "for_stmt    ::= 'for' ident 'in' expr block\n"
         "break_stmt  ::= 'break' ';'\n"
         "continue_stmt::= 'continue' ';'\n"
         "expr_stmt   ::= expr ';'?"),
        "A <code>let_stmt</code> introduces a new binding in the current scope. The optional type "
        "annotation is checked against the inferred type of the initializer expression; a mismatch "
        "is a compile-time error. Shadowing a name from an outer scope is permitted.",
        "A <code>for_stmt</code> binds the loop variable to successive elements of the iterable "
        "expression. In v1.0 the iterable MUST be a <code>list</code>; iterator traits are a v2.0 "
        "feature. The loop variable is immutable within the loop body.",
        "A <code>return_stmt</code> with no expression returns <code>unit</code>. Inside a "
        "function whose declared return type is not <code>unit</code>, a bare <code>return;</code> "
        "is a type error. At the top level (outside a function), <code>return</code> is not "
        "permitted and the parser MUST reject it.",
    ]),
    ("5. Declaration Grammar", [
        "Declarations appear at module scope. In v1.0 the module scope is the file. "
        "A declaration is either a function definition, an enum declaration, an import, "
        "or a top-level <code>let</code> binding.",
        ("code",
         "decl      ::= fn_decl | enum_decl | import_decl | let_decl\n"
         "fn_decl   ::= 'fn' ident '(' param_list? ')' ('->' type)? block\n"
         "param_list::= param (',' param)*\n"
         "param     ::= ident ':' type\n"
         "let_decl  ::= 'let' ident (':' type)? '=' expr ';'\n"
         "enum_decl ::= 'enum' ident '{' variant (',' variant)* '}'\n"
         "variant   ::= ident ('(' type_list ')')?"),
        "A function declaration introduces a name in module scope before any code runs; "
        "forward references within the same file are therefore valid. This is the only form of "
        "forward reference in v1.0; enum variants and module-level <code>let</code> bindings "
        "are evaluated in order.",
        "A function without a declared return type implicitly returns the type of its last "
        "expression. If the function contains a <code>return</code> statement, all return paths "
        "MUST agree on a common type. The inference algorithm described in Section 13 resolves "
        "the type of recursive functions by initializing the return type to a fresh unification "
        "variable before descending into the body.",
        "Enum variants without a payload have type <code>EnumName</code> directly. Variants "
        "with a payload are constructor functions of type <code>t1 -> ... -> EnumName</code>. "
        "The variant name is always qualified by the enum name at use sites: "
        "<code>Option::Some(x)</code>, not <code>Some(x)</code>.",
    ]),
    ("6. Type Grammar", [
        "The v1.0 type grammar is intentionally small. Compound types are built from primitives "
        "by application.",
        ("code",
         "type      ::= 'int' | 'float' | 'str' | 'bool' | 'unit'\n"
         "            | ident                        # user-defined enum\n"
         "            | type '[' type_list ']'       # generic application\n"
         "            | '(' type_list ')' '->' type  # function type\n"
         "            | '(' type ')'                 # grouping\n"
         "type_list ::= type (',' type)*"),
        "Generic applications in v1.0 are limited to the standard library types "
        "<code>list[T]</code>, <code>option[T]</code>, and <code>result[T, E]</code>. "
        "User-defined generic enums are introduced in v2.0.",
        "Function types are right-associative: <code>(int) -> (int) -> int</code> is "
        "<code>(int) -> ((int) -> int)</code>. In v1.0, all functions are uncurried at the "
        "surface level; currying is achieved through explicit lambda-returning functions. "
        "Partial application is not automatic.",
        "The type <code>unit</code> has exactly one value, written <code>()</code> at the "
        "expression level. It is used as the return type of functions that produce side effects "
        "only, and as the element type of <code>option[unit]</code> when signaling presence "
        "versus absence.",
        "Recursive types are not expressible in v1.0 type annotations; the interpreter handles "
        "recursive values internally via its heap. A future version will expose nominal recursive "
        "types through <code>rec</code> bindings.",
    ]),
    ("7. Function Definition Semantics", [
        "A function definition creates a closure over the environment at its definition site. "
        "In v1.0 all closures are immutable: the captured environment is snapshot at closure "
        "creation and cannot be mutated through the closure.",
        ("code",
         "fn add(x: int, y: int) -> int {\n"
         "    x + y\n"
         "}\n"
         "\n"
         "fn make_adder(n: int) -> (int) -> int {\n"
         "    fn inner(x: int) -> int { x + n }\n"
         "    inner\n"
         "}"),
        "Parameters are passed by value. For primitive types (int, float, bool, str, unit) this "
        "is a shallow copy. For list values, it is a shallow copy of the list spine; the elements "
        "themselves are shared (copy-on-write semantics are deferred to v2.0). For enum values, "
        "it is a copy of the tag and all payload fields recursively.",
        "A function may call itself recursively by name; the name is in scope within the function "
        "body for this purpose. Mutual recursion between top-level functions is supported because "
        "all top-level names are hoisted before evaluation begins. Mutual recursion between "
        "nested functions requires explicit forward declaration via a <code>let</code> binding "
        "initialized to an error-throwing stub, which is replaced by the real function.",
        "Higher-order functions are fully supported: functions may be passed as arguments, "
        "returned from other functions, stored in lists, and bound with <code>let</code>. "
        "The type of a function value is its function type; the runtime representation is a "
        "closure record containing the code pointer and the captured environment.",
    ]),
    ("8. The |> Pipeline Operator", [
        "The pipeline operator is the defining feature of Lateralus. It threads a value through "
        "a sequence of transformations without nesting function calls. Formally:",
        ("rule",
         "Reduction rule (|>):\n"
         "\n"
         "    e1 |> e2\n"
         "\n"
         "reduces to:\n"
         "\n"
         "    e2(e1)\n"
         "\n"
         "where e2 MUST evaluate to a function of arity >= 1."),
        "The operator is left-associative and has lower precedence than comparison operators "
        "but higher precedence than logical <code>and</code>/<code>or</code>. A chain "
        "<code>a |> f |> g |> h</code> is parsed as <code>((a |> f) |> g) |> h</code> "
        "and reduces to <code>h(g(f(a)))</code>.",
        ("code",
         "# Pipeline example: process a list of integers\n"
         "let result =\n"
         "    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]\n"
         "    |> std::list::filter(fn(x: int) -> bool { x % 2 == 0 })\n"
         "    |> std::list::map(fn(x: int) -> int { x * x })\n"
         "    |> std::list::sum;\n"
         "# result: 220"),
        "When the right-hand side of <code>|></code> is a partial application "
        "<code>f(a, b)</code> (not a plain identifier), the reduction is "
        "<code>f(a, b, e1)</code> -- the left-hand value is appended as the final argument. "
        "This convention means <code>xs |> std::list::map(f)</code> reads naturally as "
        "'map f over xs'.",
        "Type rule for the pipeline operator: if <code>e1 : A</code> and "
        "<code>e2 : (A) -> B</code>, then <code>e1 |> e2 : B</code>. The type checker "
        "unifies the first parameter type of <code>e2</code> with the type of <code>e1</code>; "
        "a failure is reported as a pipeline type mismatch with both sides displayed.",
    ]),
    ("9. The |?> Error Pipe", [
        "The error pipe <code>|?></code> is a variant of <code>|></code> designed for "
        "functions that return <code>result[T, E]</code>. It short-circuits on the "
        "<code>result::Err</code> variant, propagating the error without executing the "
        "remainder of the pipeline.",
        ("rule",
         "Reduction rule (|?>):\n"
         "\n"
         "    e1 |?> e2\n"
         "\n"
         "  case e1 = result::Ok(v)  => e2(v)\n"
         "  case e1 = result::Err(e) => result::Err(e)   (short-circuit)"),
        "The containing function MUST have a return type of <code>result[T2, E]</code> where "
        "<code>E</code> is the same error type as the Err variant of <code>e1</code>. This "
        "is enforced by the type checker. In v1.0, the error type must match exactly; "
        "covariant error types are a v2.0 feature.",
        ("code",
         "fn parse_and_double(s: str) -> result[int, str] {\n"
         "    s\n"
         "    |?> std::string::parse_int\n"
         "    |?> fn(n: int) -> result[int, str] { result::Ok(n * 2) }\n"
         "}"),
        "When a pipeline chain mixes <code>|></code> and <code>|?></code>, they can appear "
        "in any order. A <code>|></code> step after a <code>|?></code> receives the unwrapped "
        "OK value because the error already short-circuited. The programmer is responsible for "
        "re-wrapping the final value in <code>result::Ok</code> if the chain is expected to "
        "return a result type.",
    ]),
    ("10. Arithmetic and Comparison Operators", [
        "The arithmetic operators <code>+ - * / %</code> are defined on <code>int</code> and "
        "<code>float</code>. Mixed-type arithmetic (int + float) is a type error in v1.0; "
        "explicit conversion via <code>std::math::int_to_float</code> is required.",
        ("code",
         "# Operator precedence (highest to lowest)\n"
         "# Level 1:  unary  -  not\n"
         "# Level 2:  *  /  %\n"
         "# Level 3:  +  -\n"
         "# Level 4:  ==  !=  <  <=  >  >=\n"
         "# Level 5:  and\n"
         "# Level 6:  or\n"
         "# Level 7:  |>  |?>\n"
         "# All binary operators are left-associative at the same level."),
        "Integer division <code>/</code> performs truncating division toward zero. The remainder "
        "operator <code>%</code> satisfies <code>(a / b) * b + (a % b) == a</code> for all "
        "nonzero <code>b</code>. Division by zero is a runtime error that raises "
        "<code>DivisionByZero</code>; there is no static check in v1.0.",
        "Comparison operators return <code>bool</code>. They are defined on <code>int</code>, "
        "<code>float</code>, and <code>str</code> (lexicographic). Comparing values of "
        "different types is a type error. Equality (<code>==</code>, <code>!=</code>) is "
        "additionally defined on <code>bool</code> and on enum values; structural equality "
        "for lists requires <code>std::list::equal</code>.",
        "The logical operators <code>and</code> and <code>or</code> are short-circuit: the "
        "right operand is not evaluated if the result is determined by the left operand. "
        "They take and return <code>bool</code>; implicit coercion from other types is not "
        "supported.",
    ]),
    ("11. Let Bindings and Scoping", [
        "Lateralus uses lexical (static) scoping throughout. A <code>let</code> binding "
        "introduces a new name in the innermost enclosing scope; the name is visible from "
        "immediately after the binding to the end of that scope.",
        ("code",
         "let x = 10;\n"
         "{\n"
         "    let x = 20;    # shadows outer x\n"
         "    let y = x + 1; # y = 21\n"
         "}\n"
         "# x = 10 here; y is not in scope"),
        "Bindings are immutable in v1.0. There is no <code>let mut</code> or reassignment "
        "statement. Loops that accumulate a result do so by passing an accumulator as a "
        "function argument or by building up a list and reducing it at the end.",
        "The value semantics of v1.0 make immutability unambiguous: assigning a list to a new "
        "name copies the list spine. Two bindings can share elements (since elements are "
        "heap-allocated), but mutating one through a future mutable operation (v2.0) would not "
        "affect the other's spine.",
        "Bindings introduced in the initializer of another binding are not in scope for that "
        "initializer. In other words, <code>let x = x + 1</code> refers to the outer "
        "<code>x</code>, not a recursive self-reference. The exception is function declarations "
        "using <code>fn</code>, which are automatically recursive (Section 7).",
    ]),
    ("12. Recursive Functions", [
        "Any function declared with <code>fn</code> at either module scope or local scope may "
        "call itself by name within its body. The name is bound before the body is entered, so "
        "the self-reference is always valid.",
        ("code",
         "fn factorial(n: int) -> int {\n"
         "    if n <= 1 { 1 } else { n * factorial(n - 1) }\n"
         "}\n"
         "\n"
         "fn fib(n: int) -> int {\n"
         "    if n <= 1 { n } else { fib(n - 1) + fib(n - 2) }\n"
         "}"),
        "Tail recursion is not optimized in v1.0. A program that recurses deeply enough will "
        "exhaust the call stack and produce a <code>StackOverflow</code> runtime error. The "
        "recommended workaround is to use explicit loops (<code>while</code> or <code>for</code>) "
        "for tail-recursive patterns. Tail-call optimization is planned for v1.1.",
        "Mutually recursive top-level functions are supported without any special syntax because "
        "top-level names are hoisted. Two functions <code>even</code> and <code>odd</code> "
        "may call each other freely.",
        ("code",
         "fn even(n: int) -> bool {\n"
         "    if n == 0 { true } else { odd(n - 1) }\n"
         "}\n"
         "fn odd(n: int) -> bool {\n"
         "    if n == 0 { false } else { even(n - 1) }\n"
         "}"),
    ]),
    ("13. Algebraic Data Types (Enum)", [
        "Lateralus v1.0 supports sum types through the <code>enum</code> declaration. Each "
        "variant is either a unit tag or a tuple-like constructor carrying one or more typed "
        "fields.",
        ("code",
         "enum Shape {\n"
         "    Circle(float),           # radius\n"
         "    Rectangle(float, float), # width, height\n"
         "    Triangle(float, float, float)\n"
         "}\n"
         "\n"
         "enum Tree {\n"
         "    Leaf,\n"
         "    Node(int, Tree, Tree)\n"
         "}"),
        "Variants are constructed using the qualified form <code>EnumName::Variant(args)</code>. "
        "Unit variants are referenced as <code>EnumName::Variant</code> without parentheses. "
        "The type of a unit variant is <code>EnumName</code>; the type of a constructor "
        "variant is a function type <code>(T1, T2, ...) -> EnumName</code>.",
        "Enum types in v1.0 are monomorphic; the type parameters visible in the standard "
        "library (<code>option[T]</code>, <code>result[T, E]</code>) are built-in generics "
        "handled by the compiler. User-defined generics arrive in v2.0.",
        "The memory layout of an enum value is a tag word (8-bit in the interpreter) followed "
        "by a payload appropriate to the variant. Pattern matching (Section 14) deconstructs "
        "the tag and binds the payload fields.",
    ]),
    ("14. Pattern Matching", [
        "Pattern matching is the primary mechanism for consuming enum values. The <code>match</code> "
        "expression evaluates a scrutinee, then tries each arm in order, binding the first "
        "matching pattern.",
        ("code",
         "match_expr ::= 'match' expr '{' arm+ '}'\n"
         "arm        ::= pattern '=>' (expr | block) ','\n"
         "pattern    ::= '_'                    # wildcard\n"
         "             | literal                # literal pattern\n"
         "             | ident                  # binding pattern\n"
         "             | EnumName '::' Variant '(' pattern_list? ')'\n"
         "             | EnumName '::' Variant  # unit variant"),
        ("code",
         "fn area(s: Shape) -> float {\n"
         "    match s {\n"
         "        Shape::Circle(r)      => 3.14159 * r * r,\n"
         "        Shape::Rectangle(w, h)=> w * h,\n"
         "        Shape::Triangle(a, b, c) => {\n"
         "            let p = (a + b + c) / 2.0;\n"
         "            std::math::sqrt(p * (p-a) * (p-b) * (p-c))\n"
         "        },\n"
         "    }\n"
         "}"),
        "Match arms are checked for exhaustiveness: the compiler MUST report a warning if "
        "the set of patterns does not cover all variants of the scrutinee type. In v1.0 "
        "exhaustiveness is checked only for enum scrutinees; match on <code>int</code> or "
        "<code>str</code> requires a wildcard or literal-covering arm.",
        "Patterns bind new names in the arm body. A binding pattern (a bare identifier) matches "
        "any value and introduces the identifier as a local binding. The wildcard <code>_</code> "
        "matches any value without introducing a binding. Guard expressions are not supported "
        "in v1.0; they arrive in v2.0.",
        "All arms of a <code>match</code> expression MUST produce the same type. The type of "
        "the overall match expression is that common type. If arms produce incompatible types, "
        "the type checker reports a mismatch at the first diverging arm.",
    ]),
    ("15. The Module System (v1.0)", [
        "In v1.0 the module system is rudimentary: each file is a module and modules are "
        "identified by their file path relative to the project root. There is no hierarchical "
        "namespace; all modules exist at one level.",
        ("code",
         "import_decl ::= 'import' module_path ('use' ident_list)?\n"
         "module_path ::= string_literal\n"
         "ident_list  ::= ident (',' ident)*"),
        "An import makes the named module's <code>pub</code>-marked declarations available "
        "under the module's basename. For example, <code>import \"utils\"</code> makes "
        "<code>utils::helper()</code> available. The <code>use</code> clause selectively "
        "imports names into the current scope without qualification: "
        "<code>import \"utils\" use helper</code> makes <code>helper</code> available "
        "directly.",
        "Circular imports are detected at load time and produce a fatal error. The import "
        "resolver performs a DFS; if a module is encountered while its own resolution is still "
        "in progress, the cycle is reported with the full chain.",
        "The module system is substantially redesigned in v3.0. This section describes v1.0 "
        "only. Implementers building v1.0 tooling should treat the module system as minimal "
        "scaffolding rather than a production feature.",
    ]),
    ("16. Standard Library (v1.0)", [
        "The v1.0 standard library is intentionally minimal. It is distributed as part of the "
        "interpreter and is always available without an explicit import.",
        ("h3", "16.1 std::io"),
        ("code",
         "# std::io\n"
         "fn print(s: str) -> unit\n"
         "fn println(s: str) -> unit\n"
         "fn read_line() -> str\n"
         "fn read_file(path: str) -> result[str, str]\n"
         "fn write_file(path: str, content: str) -> result[unit, str]"),
        ("h3", "16.2 std::string"),
        ("code",
         "# std::string\n"
         "fn len(s: str) -> int\n"
         "fn concat(a: str, b: str) -> str\n"
         "fn slice(s: str, start: int, end: int) -> str\n"
         "fn split(s: str, sep: str) -> list[str]\n"
         "fn contains(s: str, sub: str) -> bool\n"
         "fn parse_int(s: str) -> result[int, str]\n"
         "fn parse_float(s: str) -> result[float, str]\n"
         "fn to_upper(s: str) -> str\n"
         "fn to_lower(s: str) -> str\n"
         "fn trim(s: str) -> str"),
        ("h3", "16.3 std::list"),
        ("code",
         "# std::list\n"
         "fn map(f: (A) -> B, xs: list[A]) -> list[B]\n"
         "fn filter(f: (A) -> bool, xs: list[A]) -> list[A]\n"
         "fn fold(f: (B, A) -> B, init: B, xs: list[A]) -> B\n"
         "fn len(xs: list[A]) -> int\n"
         "fn append(xs: list[A], ys: list[A]) -> list[A]\n"
         "fn head(xs: list[A]) -> option[A]\n"
         "fn tail(xs: list[A]) -> list[A]\n"
         "fn nth(xs: list[A], i: int) -> option[A]\n"
         "fn sum(xs: list[int]) -> int\n"
         "fn join(xs: list[str], sep: str) -> str"),
        ("h3", "16.4 std::option and std::result"),
        ("code",
         "# std::option\n"
         "fn is_some(o: option[A]) -> bool\n"
         "fn is_none(o: option[A]) -> bool\n"
         "fn unwrap(o: option[A]) -> A    # runtime error if None\n"
         "fn unwrap_or(o: option[A], default: A) -> A\n"
         "fn map_opt(f: (A) -> B, o: option[A]) -> option[B]\n"
         "\n"
         "# std::result\n"
         "fn is_ok(r: result[T, E]) -> bool\n"
         "fn is_err(r: result[T, E]) -> bool\n"
         "fn unwrap_ok(r: result[T, E]) -> T\n"
         "fn unwrap_err(r: result[T, E]) -> E\n"
         "fn map_ok(f: (T) -> U, r: result[T, E]) -> result[U, E]"),
    ]),
    ("17. Type Inference Rules", [
        "The following judgment forms define the static semantics of v1.0. "
        "<code>Gamma |- e : t</code> reads 'under environment Gamma, expression e has type t'.",
        ("rule",
         "-- Var\n"
         "(x : t) in Gamma\n"
         "----------------\n"
         "Gamma |- x : t\n"
         "\n"
         "-- Int literal\n"
         "----------------\n"
         "Gamma |- n : int\n"
         "\n"
         "-- Application\n"
         "Gamma |- e1 : (t1) -> t2    Gamma |- e2 : t1\n"
         "---------------------------------------------\n"
         "Gamma |- e1(e2) : t2\n"
         "\n"
         "-- Pipeline\n"
         "Gamma |- e1 : A    Gamma |- e2 : (A) -> B\n"
         "------------------------------------------\n"
         "Gamma |- e1 |> e2 : B\n"
         "\n"
         "-- Let\n"
         "Gamma |- e1 : t1    Gamma, x:generalize(Gamma, t1) |- e2 : t2\n"
         "---------------------------------------------------------------\n"
         "Gamma |- let x = e1 in e2 : t2"),
        "The function and pattern-match rules are omitted for space but follow standard "
        "HM conventions. The generalize function abstracts type variables free in t1 but "
        "not free in Gamma, producing a type scheme.",
        "The error pipe rule adds a result-unwrapping step: if "
        "<code>e1 : result[A, E]</code> and <code>e2 : (A) -> result[B, E]</code>, "
        "then <code>e1 |?> e2 : result[B, E]</code>. The error type <code>E</code> must "
        "unify across all <code>|?></code> steps in a chain.",
    ]),
    ("18. Operational Semantics (Selected Rules)", [
        "Operational semantics are given as a small-step reduction relation "
        "<code>e --> e'</code> on closed expressions. The full set of rules is 47; we "
        "present the most distinctive ones.",
        ("rule",
         "-- E-Pipe (|>)\n"
         "v is a value    f is a function value\n"
         "--------------------------------------\n"
         "v |> f --> f(v)\n"
         "\n"
         "-- E-PipeErr-Ok (|?>)\n"
         "result::Ok(v) |?> f --> f(v)\n"
         "\n"
         "-- E-PipeErr-Err (|?>)\n"
         "result::Err(e) |?> f --> result::Err(e)\n"
         "\n"
         "-- E-Match-Hit\n"
         "pattern p matches value v with bindings sigma\n"
         "---------------------------------------------\n"
         "match v { p => e, ... } --> e[sigma]\n"
         "\n"
         "-- E-Match-Miss\n"
         "pattern p does not match value v\n"
         "-------------------------------------------\n"
         "match v { p => e1, rest } --> match v { rest }"),
        "Congruence rules (reducing sub-expressions in context) are standard and not "
        "listed here. Values in v1.0 are: integer literals, float literals, boolean literals, "
        "string literals, unit <code>()</code>, list literals with value elements, enum "
        "constructors applied to value arguments, and closures.",
    ]),
    ("19. Memory Model (Value Semantics)", [
        "The v1.0 memory model is value semantics throughout. When a value is passed to a "
        "function or bound with <code>let</code>, the receiving binding holds an independent "
        "copy of the value. Primitive types (int, float, bool, unit) are copied by value at "
        "the machine level.",
        "String values are immutable in v1.0. The interpreter may share string data between "
        "bindings (interning), but no operation can observe sharing: the language model is "
        "always a fresh copy. Operations like <code>std::string::concat</code> always return "
        "new strings.",
        "List values copy the spine (the array of element references) on each binding. "
        "Elements themselves are shared as heap references. Since no mutation of elements "
        "is exposed in v1.0, this sharing is unobservable and the model is still pure "
        "value semantics.",
        "Enum values copy the tag and recursively copy all payload fields. For deeply nested "
        "tree-shaped data this copying has O(n) cost where n is the number of nodes. "
        "A persistent data structure library is planned for v2.0 to address this.",
        "There is no explicit memory management in v1.0. The interpreter uses reference "
        "counting for heap objects (strings, lists, enum payloads). Cycles are not possible "
        "because v1.0 has no mutable references. The reference-counting cost is amortized "
        "into allocation and deallocation; it is not visible at the language level.",
    ]),
    ("20. REPL Mode", [
        "The Lateralus v1.0 distribution includes an interactive read-eval-print loop. "
        "The REPL evaluates statements and expressions one at a time and prints the result "
        "after each successful evaluation.",
        ("code",
         "$ lateralus\n"
         "Lateralus v1.0 REPL — type :help for commands\n"
         "ltl> let x = [1, 2, 3];\n"
         "ltl> x |> std::list::map(fn(n: int) -> int { n * 2 })\n"
         "[2, 4, 6]\n"
         "ltl> :type x\n"
         "list[int]\n"
         "ltl> :quit"),
        "REPL commands are prefixed with <code>:</code> and are not valid Lateralus syntax. "
        "Available REPL commands in v1.0: <code>:type expr</code> (print inferred type), "
        "<code>:load file</code> (load a file into scope), <code>:reset</code> (clear the "
        "environment), <code>:help</code>, <code>:quit</code>.",
        "The REPL environment persists across evaluations within a session. A binding introduced "
        "in one evaluation is available in all subsequent evaluations. Shadowing a previous "
        "REPL binding is allowed and works identically to shadowing in source files.",
        "Error messages in the REPL include the source position within the submitted line and "
        "the inferred types of subexpressions when relevant. The REPL does not crash on error; "
        "it prints the error and waits for the next input.",
    ]),
    ("21. Known Limitations in v1.0", [
        "The following limitations are known and are addressed in later versions:",
        ("list", [
            "<b>No user-defined generics.</b> Only the built-in generic types (list, option, result) support type parameters.",
            "<b>No tail-call optimization.</b> Deep recursion will stack-overflow.",
            "<b>No mutable references.</b> Stateful algorithms require functional patterns or explicit accumulator passing.",
            "<b>Single-file module system.</b> Multi-file projects require manual concatenation or the rudimentary import mechanism.",
            "<b>No async or concurrency primitives.</b> The runtime is single-threaded.",
            "<b>No FFI.</b> Interoperability with C or Python libraries is not supported.",
            "<b>No type classes or traits.</b> Ad-hoc polymorphism is not expressible.",
            "<b>Integer overflow is undefined behavior</b> in the interpreter on platforms where the host Python interpreter wraps or truncates.",
        ]),
    ]),
    ("22. Versioning Policy", [
        "Lateralus follows semantic versioning (SemVer 2.0). A version number is "
        "<code>MAJOR.MINOR.PATCH</code>. The MAJOR version increments on breaking "
        "changes to the grammar, type system, or standard library. MINOR increments on "
        "new features that are backward-compatible. PATCH increments on bug fixes.",
        "This document specifies v1.0.0. All v1.x.y versions MUST accept every program "
        "that v1.0.0 accepts and MUST assign it the same semantics. New features added "
        "in v1.x.y MUST NOT conflict with the grammar or semantics defined here.",
        "v2.0 is a planned breaking release. Programs written for v1.0 may require "
        "syntactic updates when migrated to v2.0, particularly around the module system "
        "and the introduction of mutable bindings. A migration guide will accompany the "
        "v2.0 release.",
    ]),
    ("Appendix A: Reserved Keywords", [
        "The following identifiers are reserved in v1.0 and may not be used as user-defined names:",
        ("code",
         "fn       let      if       else     match    case     return\n"
         "enum     import   pub      use      true     false    and\n"
         "or       not      in       for      while    break    continue\n"
         "unit     int      float    str      bool"),
        "The type names <code>unit</code>, <code>int</code>, <code>float</code>, <code>str</code>, "
        "and <code>bool</code> are reserved identifiers even though they appear in the type "
        "grammar position rather than the expression grammar position. Future versions may "
        "relax this restriction for type-level namespacing.",
    ]),
    ("Appendix B: Operator Precedence Table", [
        "Operators are listed from highest to lowest binding power. All binary operators at "
        "the same level are left-associative.",
        ("code",
         "Level  Operator(s)           Associativity\n"
         "----------------------------------------------\n"
         "1      - (unary)  not        right\n"
         "2      *  /  %               left\n"
         "3      +  -                  left\n"
         "4      ==  !=  <  <=  >  >= left\n"
         "5      and                   left\n"
         "6      or                    left\n"
         "7      |>  |?>               left"),
        "Function application (call syntax) binds tighter than all binary operators and is "
        "evaluated left-to-right for chained calls. Grouping with parentheses overrides all "
        "precedence rules.",
    ]),
]

if __name__ == "__main__":
    render_paper(
        out_path=str(OUT),
        title=TITLE,
        subtitle=SUBTITLE,
        meta=META,
        abstract=ABSTRACT,
        sections=SECTIONS,
    )
    print(f"wrote {OUT}")
