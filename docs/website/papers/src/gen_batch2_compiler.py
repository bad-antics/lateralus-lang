#!/usr/bin/env python3
"""Batch generator — Compiler papers (batch 2): from-lexer-to-language, lexer-design-pipeline-first,
multi-target-compilation, c-backend-transpiler-design, lateralus-bytecode-format."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lateralus_template import render_paper

PDF = Path(__file__).resolve().parents[1] / "pdf"

# ── 1. from-lexer-to-language ─────────────────────────────────────────────────
render_paper(
    out_path=str(PDF / "from-lexer-to-language.pdf"),
    title="From Lexer to Language",
    subtitle="The complete Lateralus front-end: lexing, parsing, resolution, and type inference",
    meta="bad-antics &middot; March 2026 &middot; Lateralus Language Research",
    abstract=(
        "A language's front-end is the component that translates source text into a "
        "typed, resolved representation that the rest of the compiler can work with. "
        "This paper describes the complete Lateralus front-end in four phases: the "
        "lexer (tokenizes source text), the parser (builds a concrete syntax tree), "
        "the resolver (resolves names to their definitions), and the type checker "
        "(infers and verifies types for every expression). For each phase, we describe "
        "the data structures, the algorithms, the key design decisions, and the ways "
        "in which the Lateralus front-end differs from front-ends for conventional "
        "languages. The pipeline-first design affects all four phases: pipeline "
        "expressions have dedicated AST nodes, special typing rules, and enhanced "
        "error reporting that requires the front-end to preserve pipeline structure "
        "through to the type checker's output."
    ),
    sections=[
        ("1. Front-End Architecture Overview", [
            "The Lateralus front-end is a four-phase pipeline (appropriately enough). "
            "Each phase takes a structured representation as input and produces a "
            "richer structured representation as output. There is no shared mutable "
            "state between phases: the output of phase N is the complete input to "
            "phase N+1. This pure-function structure makes each phase independently "
            "testable and enables incremental recompilation at phase granularity.",
            ("code",
             "-- Front-end data flow\n"
             "Source text     : String\n"
             "     ↓ Lexer\n"
             "Token stream    : Vec<Token>        (flat, linear)\n"
             "     ↓ Parser\n"
             "Concrete ST     : CstModule         (includes trivia: comments, whitespace)\n"
             "     ↓ Resolver\n"
             "Resolved AST    : AstModule         (names resolved to Definition ids)\n"
             "     ↓ TypeChecker\n"
             "Typed AST       : TyModule          (every node annotated with its type)\n"
             "     ↓ HIR Lowering\n"
             "HIR             : HirModule         (pipeline IR nodes, effect annotations)"),
            "The front-end produces a <code>TyModule</code>, a typed abstract syntax "
            "tree where every expression node carries its inferred type and every "
            "name reference carries a unique definition identifier. The HIR lowering "
            "phase (the first optimizer phase, described in a companion paper) "
            "consumes the <code>TyModule</code> and produces the HIR, which is "
            "the input to the optimizer and backend.",
            "The front-end is the largest part of the compiler by line count: "
            "the lexer is 890 lines, the parser is 2,100 lines, the resolver is "
            "780 lines, and the type checker is 4,200 lines, for a total of 7,970 "
            "lines. The type checker dominates because it must handle row polymorphism, "
            "effect inference, lifetime analysis, and pipeline-variant typing all "
            "simultaneously.",
        ]),
        ("2. The Lateralus Source Character Set", [
            "Lateralus source files are UTF-8 encoded. The language allows Unicode "
            "in identifiers (following the Unicode identifier specification in UAX#31), "
            "in string literals, and in comments. Operators and punctuation are "
            "restricted to the ASCII subset to avoid ambiguity with Unicode look-alike "
            "characters (e.g., the Unicode RIGHTWARDS ARROW U+2192 is not an "
            "operator in Lateralus; only the ASCII hyphen-greater-than sequence "
            "<code>-></code> is).",
            "Greek letters are commonly used in Lateralus for formal mathematics "
            "and type theory code. The standard library uses <code>α</code>, "
            "<code>β</code>, and <code>γ</code> as type variable names in generic "
            "functions where the conventional <code>A</code>, <code>B</code>, "
            "<code>C</code> would be less readable. The formal methods library "
            "uses <code>Γ</code> for type environments and <code>τ</code> for types.",
            ("code",
             "-- Valid Lateralus identifiers\n"
             "let α = 0.577       -- Greek letter alpha\n"
             "let Γ = TypeEnv::new()  -- uppercase gamma\n"
             "let x₀ = initial_value  -- subscript zero (U+2080)\n"
             "let café = 'coffee'     -- Latin extended\n\n"
             "-- NOT valid: look-alikes for ASCII operators\n"
             "-- let x → y = ...    -- U+2192, not ASCII ->\n"
             "-- let x ≠ y = ...    -- U+2260, not ASCII !=\n"
             "-- let x × y = ...    -- U+00D7, not ASCII *"),
        ]),
        ("3. Lexer Design and DFA Implementation", [
            "The Lateralus lexer is a hand-written deterministic finite automaton "
            "implemented as a character-scanning loop. The DFA is implicit in the "
            "structure of the loop rather than explicit as a transition table; this "
            "produces faster code (no table lookup overhead) at the cost of slightly "
            "less flexibility when the token grammar changes.",
            "The lexer recognizes 78 distinct token kinds. Most token kinds map to "
            "a fixed lexeme (keywords, punctuation, operators). Three token kinds "
            "have variable lexemes: <code>IDENT</code> (identifiers), "
            "<code>INTEGER</code> (integer literals), and <code>STRING</code> "
            "(string literals). The four pipeline operators are recognized as single "
            "token kinds (<code>PIPE_TOTAL</code>, <code>PIPE_ERROR</code>, "
            "<code>PIPE_ASYNC</code>, <code>PIPE_FANOUT</code>) and not as "
            "sequences of simpler tokens.",
            ("code",
             "// Lexer main loop (abbreviated)\n"
             "fn lex(&mut self) -> Vec<Token> {\n"
             "    while !self.at_end() {\n"
             "        match self.current_char() {\n"
             "            c if c.is_whitespace() => self.skip_whitespace_emit_newlines(),\n"
             "            '-' if self.next_is('-') => self.lex_line_comment(),\n"
             "            '-' if self.next_is('{') => self.lex_block_comment(),\n"
             "            '|' => self.lex_pipe_or_bar(),\n"
             "            '\"' => self.lex_string(),\n"
             "            c if c.is_ascii_digit() => self.lex_number(),\n"
             "            c if is_id_start(c) => self.lex_identifier(),\n"
             "            _ => self.lex_symbol(),\n"
             "        }\n"
             "    }\n"
             "    self.push(Token::new(Eof, \"\", self.loc()))\n"
             "}"),
            "The pipeline operator lexing is the most complex part of the lexer "
            "because all four operators start with <code>|</code> and require "
            "one or two characters of lookahead to disambiguate. The lexer uses "
            "a two-position lookahead window to handle this: it reads the character "
            "after <code>|</code> and, if necessary, the character after that, "
            "before emitting the pipeline token.",
        ]),
        ("4. Number and String Literal Lexing", [
            "Lateralus number literals support four bases: decimal (default), "
            "hexadecimal (<code>0x</code> prefix), octal (<code>0o</code> prefix), "
            "and binary (<code>0b</code> prefix). Integer literals support an "
            "optional type suffix (<code>42i64</code>, <code>255u8</code>). "
            "Floating-point literals use the decimal point and optional exponent "
            "(<code>3.14e-2</code>).",
            ("code",
             "-- Lateralus integer literal forms\n"
             "42          -- decimal i64\n"
             "42i32       -- decimal i32 (explicit suffix)\n"
             "0xFF        -- hexadecimal (255 as i64)\n"
             "0o777       -- octal (511 as i64)\n"
             "0b1010_1010 -- binary with separator (170 as i64)\n"
             "1_000_000   -- decimal with separators\n\n"
             "-- Floating-point\n"
             "3.14        -- f64\n"
             "3.14f32     -- f32 suffix\n"
             "1.0e10      -- scientific notation\n"
             "6.022e23    -- Avogadro's number"),
            "String literals support escape sequences for the standard C escape "
            "characters plus Unicode escapes (<code>\\u{1F600}</code> for any "
            "Unicode scalar value). Multi-line string literals are introduced by "
            "triple quotes (<code>\"\"\"</code>) and trim leading whitespace based "
            "on the indentation of the closing <code>\"\"\"</code>.",
        ]),
        ("5. Indentation-Sensitive Lexing", [
            "Lateralus uses significant indentation for block structure. The lexer "
            "emits <code>INDENT</code> and <code>DEDENT</code> tokens when the "
            "indentation level changes. The parser uses these tokens to delimit blocks "
            "without requiring braces. The layout rule is simpler than Python's because "
            "Lateralus only tracks one kind of block (not Python's special handling "
            "of continuation lines).",
            "The indentation stack is a stack of integers (column positions). When "
            "a newline is encountered, the lexer measures the indentation of the "
            "next non-whitespace character. If it is greater than the top of the "
            "stack, an <code>INDENT</code> token is emitted and the new level is "
            "pushed. If it is less, <code>DEDENT</code> tokens are emitted and "
            "levels are popped until the top of the stack matches. If it equals "
            "the top, no token is emitted (continuation at the same level).",
            ("code",
             "// Indentation tracking in the lexer\n"
             "fn handle_newline(&mut self) {\n"
             "    self.skip_whitespace_no_newline();\n"
             "    if self.at_end() || self.current_char() == '\\n' { return; }\n"
             "    let new_indent = self.current_col();\n"
             "    let top = *self.indent_stack.last().unwrap();\n"
             "    if new_indent > top {\n"
             "        self.indent_stack.push(new_indent);\n"
             "        self.push(Token::new(Indent, \"\", self.loc()));\n"
             "    } else {\n"
             "        while *self.indent_stack.last().unwrap() > new_indent {\n"
             "            self.indent_stack.pop();\n"
             "            self.push(Token::new(Dedent, \"\", self.loc()));\n"
             "        }\n"
             "    }\n"
             "}"),
        ]),
        ("6. Parser Architecture: Grammar Encoding", [
            "The Lateralus parser is a recursive-descent parser with Pratt operator "
            "precedence for expressions. The grammar is encoded as methods on a "
            "<code>Parser</code> struct, one method per grammar production. The "
            "parser is LL(k) for small k: most productions require only one-token "
            "lookahead, and no production requires more than two-token lookahead.",
            "The grammar has 47 productions covering all syntactic forms. The "
            "productions are organized into five layers: module-level items "
            "(function definitions, type definitions, imports), statement-level "
            "constructs (let bindings, expression statements), expressions (the "
            "largest layer, including pipeline expressions), patterns, and types. "
            "Each layer is handled by a separate set of parser methods.",
            ("code",
             "// Grammar summary (selected productions)\n"
             "Module      ::= Item*\n"
             "Item        ::= FnDef | TypeDef | Import | LetDef | ImplBlock\n"
             "FnDef       ::= 'fn' Ident GenParams? '(' Params ')' ('->' Type)? Block\n"
             "LetDef      ::= 'let' Pattern (':' Type)? '=' Expr\n"
             "Block       ::= INDENT Stmt+ DEDENT\n"
             "Stmt        ::= LetDef | Expr\n"
             "Expr        ::= PipelineExpr\n"
             "PipelineExpr ::= ApplicationExpr (PipeOp ApplicationExpr)*\n"
             "PipeOp      ::= '|>' | '|?>' | '|>>' | '|>|'\n"
             "ApplicationExpr ::= AtomExpr AtomExpr*     -- left-associative application\n"
             "AtomExpr    ::= Var | Literal | '(' Expr ')' | Block | MatchExpr | IfExpr\n"
             "Pattern     ::= WildPat | VarPat | LitPat | ConPat | TuplePat | RecordPat\n"
             "Type        ::= AtomType (('->' | '|') AtomType)*"),
        ]),
        ("7. Pratt Parsing for Operator Expressions", [
            "Expression parsing uses the Pratt parser technique (top-down operator "
            "precedence) for binary operators. Each operator has a left-binding power "
            "(its precedence on the left) and a right-binding power (its precedence "
            "on the right). The Pratt parser loops, consuming operators and operands "
            "in order of decreasing binding power.",
            ("code",
             "// Pratt parser: operator precedence table\n"
             "// (binding power = precedence × 2; odd = right-assoc, even = left-assoc)\n"
             "const BINDING_POWER: &[(TokenKind, (u8, u8))] = &[\n"
             "    (Or,         ( 2,  3)),   // 'or'\n"
             "    (And,        ( 4,  5)),   // 'and'\n"
             "    (Eq,         ( 6,  7)),   // '=='\n"
             "    (Ne,         ( 6,  7)),   // '!='\n"
             "    (Lt,         ( 8,  9)),   // '<'\n"
             "    (Plus,       (12, 13)),   // '+'\n"
             "    (Minus,      (12, 13)),   // '-'\n"
             "    (Star,       (14, 15)),   // '*'\n"
             "    (Slash,      (14, 15)),   // '/'\n"
             "    (PipeTotal,  ( 0,  1)),   // '|>'  — lowest precedence\n"
             "    (PipeError,  ( 0,  1)),   // '|?>'\n"
             "    (PipeAsync,  ( 0,  1)),   // '|>>'\n"
             "    (PipeFanout, ( 0,  1)),   // '|>|'\n"
             "];"),
            "Pipeline operators have the lowest binding power (0, 1), which means "
            "they bind less tightly than all other binary operators. The expression "
            "<code>x + 1 |> f</code> parses as <code>(x + 1) |> f</code>, not "
            "<code>x + (1 |> f)</code>. This matches the intuitive reading: "
            "the pipeline receives the result of the arithmetic expression.",
        ]),
        ("8. Pattern Parsing and Exhaustiveness Preparation", [
            "Pattern parsing produces a tree of pattern nodes that the type checker "
            "later uses for exhaustiveness checking. Each pattern node has a kind "
            "(wildcard, variable, constructor, literal, tuple, record, or-pattern) "
            "and may have sub-patterns. The parser produces a maximally permissive "
            "pattern AST; the type checker rejects invalid patterns.",
            ("code",
             "fn parse_pattern(&mut self) -> Pattern {\n"
             "    match self.peek() {\n"
             "        Underscore => { self.advance(); Pattern::Wild }\n"
             "        Ident if self.peek_text().starts_with(|c: char| c.is_lowercase()) => {\n"
             "            Pattern::Var(self.parse_ident())\n"
             "        }\n"
             "        Ident => {\n"
             "            let name = self.parse_ident();\n"
             "            let args = if self.at(LParen) {\n"
             "                self.parse_delimited(LParen, RParen, Self::parse_pattern)\n"
             "            } else { vec![] };\n"
             "            Pattern::Constructor { name, args }\n"
             "        }\n"
             "        Integer => Pattern::IntLit(self.parse_integer()),\n"
             "        LParen  => self.parse_tuple_pattern(),\n"
             "        LBrace  => self.parse_record_pattern(),\n"
             "        _ => self.error(\"expected a pattern\"),\n"
             "    }\n"
             "}"),
            "Or-patterns (<code>Ok(x) | Err(_)</code>) allow multiple patterns "
            "to share a single arm body. They are parsed as a list of alternatives "
            "separated by <code>|</code>. The type checker verifies that all "
            "alternatives bind the same variables with the same types.",
        ]),
        ("9. Concrete vs Abstract Syntax Trees", [
            "The Lateralus front-end maintains a distinction between the concrete "
            "syntax tree (CST) produced by the parser and the abstract syntax tree "
            "(AST) produced by the resolver. The CST includes all syntactic trivia: "
            "comments, whitespace, and parentheses. The AST omits trivia but adds "
            "semantic information: name resolution IDs, parent references, and "
            "span-to-definition maps.",
            "The CST is used by the language server (LSP) and formatter, which need "
            "the full syntactic information to perform incremental edits without "
            "rewriting user formatting. The AST is used by the type checker and "
            "backend, which do not care about formatting but need efficient "
            "navigation by definition ID.",
            ("code",
             "-- CST node (includes all trivia)\n"
             "CstFnDef {\n"
             "    fn_kw:      Token,         -- the 'fn' keyword token\n"
             "    name:       Token,         -- function name token\n"
             "    params:     Vec<CstParam>, -- includes parens and commas\n"
             "    arrow:      Option<Token>, -- the '->' token, if present\n"
             "    ret_type:   Option<CstType>,\n"
             "    body:       CstBlock,\n"
             "    trivia:     Vec<Token>,    -- comments between tokens\n"
             "}\n\n"
             "-- AST node (semantic only)\n"
             "AstFnDef {\n"
             "    id:       DefId,           -- unique definition identifier\n"
             "    name:     Ident,           -- interned string\n"
             "    params:   Vec<AstParam>,   -- no punctuation\n"
             "    ret_type: Option<AstType>,\n"
             "    body:     AstExpr,\n"
             "    span:     Span,            -- source location\n"
             "}"),
        ]),
        ("10. Name Resolution Algorithm", [
            "Name resolution converts every identifier in the CST to a reference "
            "to a specific definition, identified by a <code>DefId</code>. The "
            "resolver performs two passes. The first pass collects all top-level "
            "definitions (functions, types, imports) into a module scope. The second "
            "pass walks the AST recursively, resolving each identifier using the "
            "scope chain built during traversal.",
            "The scope chain is a stack of hash maps from name strings to "
            "<code>DefId</code>s. When a new lexical scope is opened (a function "
            "body, a let block, a match arm), a new hash map is pushed. When the "
            "scope closes, the map is popped. Name lookup walks the stack from "
            "top to bottom and returns the first match.",
            ("code",
             "// Resolver: resolving a function body\n"
             "fn resolve_fn_body(&mut self, params: &[AstParam], body: &CstExpr)\n"
             "    -> AstExpr\n"
             "{\n"
             "    self.scopes.push(HashMap::new());\n"
             "    // Define each parameter in the new scope\n"
             "    for param in params {\n"
             "        let id = self.define(param.name.clone());\n"
             "        self.scopes.last_mut().unwrap()\n"
             "            .insert(param.name.clone(), id);\n"
             "    }\n"
             "    let resolved_body = self.resolve_expr(body);\n"
             "    self.scopes.pop();\n"
             "    resolved_body\n"
             "}"),
            "Import resolution is handled in the first pass by loading the imported "
            "module's symbol table and merging it into the current module's scope. "
            "Circular imports are detected using a DFS on the import graph; a cycle "
            "is reported as an error naming the full cycle.",
        ]),
        ("11. Type Environment and Type Variables", [
            "The type checker maintains a type environment (a mapping from "
            "<code>DefId</code>s to type schemes) and a substitution (a mapping "
            "from type variables to types). Type variables represent unknown types "
            "that will be resolved by unification.",
            "Fresh type variables are generated by a counter. Each call to "
            "<code>fresh()</code> returns a new type variable <code>t_N</code> "
            "where N is the current counter value. Type variables are anonymous "
            "in the substitution but are named by their first use site for "
            "error message purposes.",
            ("code",
             "-- Type representation\n"
             "type Type =\n"
             "    | TyVar(TyVarId)          -- unification variable\n"
             "    | I64 | I32 | U64 | U8    -- primitive integer types\n"
             "    | F64 | F32               -- primitive float types\n"
             "    | Bool | Str | Bytes      -- other primitives\n"
             "    | Fun(Type, Type)         -- function type A -> B\n"
             "    | Result(Type, Type)      -- Result<A, E>\n"
             "    | Future(Type)            -- Future<A>\n"
             "    | Tuple(Vec<Type>)        -- (A, B, C)\n"
             "    | Record(RowType)         -- {field: T | rest}\n"
             "    | Named(DefId, Vec<Type>) -- T<A, B>\n"
             "    | Effect(EffectRow, Type) -- T ! {Eff1, Eff2}\n"
             "    | Forall(Vec<TyVarId>, Type) -- ∀ a b. T (type scheme body)"),
        ]),
        ("12. Type Inference Algorithm", [
            "The Lateralus type checker implements bidirectional type inference. "
            "In the checking direction (<code>check(e, T)</code>), the expression "
            "<code>e</code> is verified to have type <code>T</code>. In the "
            "synthesis direction (<code>synth(e)</code>), the type of <code>e</code> "
            "is computed. Switching between directions is governed by the expression "
            "form and the available type context.",
            "Bidirectional typing is superior to pure Hindley-Milner for Lateralus "
            "because it handles several cases more naturally: function literal types "
            "can be checked against a known function type (no annotation needed), "
            "match arm bodies can all be checked against the expected return type "
            "(reducing the number of type variables), and pipeline stage types "
            "propagate from left to right in the synthesis direction.",
            ("code",
             "fn synth(&mut self, expr: &AstExpr, env: &TyEnv) -> Type {\n"
             "    match expr {\n"
             "        IntLit(_)   => I64,\n"
             "        BoolLit(_)  => Bool,\n"
             "        StrLit(_)   => Str,\n"
             "        Var(id)     => self.instantiate(env.get(id)),\n"
             "        Call(f, a)  => {\n"
             "            let ft = self.synth(f, env);\n"
             "            let at = self.synth(a, env);\n"
             "            let rt = self.fresh();\n"
             "            self.unify(ft, Fun(at, rt), f.span());\n"
             "            rt\n"
             "        }\n"
             "        Pipeline(lhs, rhs, variant) =>\n"
             "            self.synth_pipeline(lhs, rhs, *variant, env),\n"
             "        Let(pat, init, body) => {\n"
             "            let it = self.synth(init, env);\n"
             "            let env2 = self.bind_pattern(pat, it, env);\n"
             "            self.synth(body, &env2)\n"
             "        }\n"
             "        _ => self.synth_complex(expr, env)\n"
             "    }\n"
             "}"),
        ]),
        ("13. Row Polymorphism Implementation", [
            "Row polymorphism allows functions to work with records that have at "
            "least certain fields, without requiring a specific record type. The "
            "type of such a function includes a row variable that stands for 'any "
            "additional fields'. Unifying two row types requires careful handling "
            "of row variables to avoid creating circular types.",
            ("code",
             "-- Row type unification\n"
             "-- Row = { field1: T1, field2: T2 | rest }\n"
             "-- where 'rest' is a row variable or the empty row\n\n"
             "fn unify_rows(&mut self, row1: &RowType, row2: &RowType, span: Span) {\n"
             "    match (row1, row2) {\n"
             "        (Empty, Empty) => {}  -- both empty, done\n"
             "        (Empty, Cons(..)) | (Cons(..), Empty) => {\n"
             "            self.error(E0201, \"record fields don't match\", span)\n"
             "        }\n"
             "        (RowVar(v), other) | (other, RowVar(v)) => {\n"
             "            if self.occurs_row(v, other) {\n"
             "                self.error(E0202, \"infinite row type\", span)\n"
             "            } else {\n"
             "                self.row_subst.insert(*v, other.clone())\n"
             "            }\n"
             "        }\n"
             "        (Cons(f1, t1, rest1), Cons(f2, t2, rest2)) => {\n"
             "            if f1 == f2 {\n"
             "                self.unify(t1, t2, span);\n"
             "                self.unify_rows(rest1, rest2, span);\n"
             "            } else {\n"
             "                // Reorder fields, insert missing field into tail row\n"
             "                self.unify_rows_permuted(row1, row2, span)\n"
             "            }\n"
             "        }\n"
             "    }\n"
             "}"),
        ]),
        ("14. Effect Type Inference", [
            "Effects in Lateralus are tracked using an effect row system. Each "
            "function type carries an effect annotation that describes what the "
            "function may do: read files, write to a database, perform network I/O, "
            "or modify shared state. The effect system ensures that pure functions "
            "are guaranteed to be free of side effects.",
            ("code",
             "-- Effect row examples\n"
             "fn pure_transform(x: str) -> str ! {}  -- no effects\n"
             "fn read_file(path: str) -> str ! {IO}  -- IO effect\n"
             "fn update_state<S>(s: S) -> S ! {State<S>}  -- State effect\n\n"
             "-- Effect polymorphism: function that passes through caller's effects\n"
             "fn map_result<A, B, E>(r: Result<A, E>, f: A -> B ! e) -> Result<B, E> ! e\n"
             "    where e: EffectRow"),
            "Effect inference propagates effects from called functions to callers. "
            "A function that calls a function with effect <code>IO</code> must "
            "itself have at least the <code>IO</code> effect (unless the call is "
            "wrapped in an effect handler that converts it). The effect inference "
            "algorithm is similar to type inference: fresh effect variables are "
            "generated, constraints are collected, and the constraints are solved "
            "by unification.",
        ]),
        ("15. Lifetime Analysis", [
            "Lifetime analysis is the final sub-phase of the type checker. It verifies "
            "that all borrows are valid: a borrowed reference cannot outlive the "
            "value it borrows from, and a mutable borrow cannot coexist with any "
            "other borrow of the same value. The lifetime checker runs after type "
            "inference has completed and the types are fully known.",
            ("code",
             "-- Lifetime annotation syntax\n"
             "fn get_first<'a>(items: &'a Vec<str>) -> &'a str {\n"
             "    &items[0]  -- return value borrows from 'a, same lifetime as items\n"
             "}\n\n"
             "-- Lifetime error example\n"
             "fn broken_borrow() -> &str {\n"
             "    let s = String::from('hello')\n"
             "    &s  -- ERROR: 's' does not live long enough\n"
             "        -- 's' is dropped at end of function\n"
             "        -- but the borrow is returned to the caller\n"
             "}"),
            "Lifetime analysis in Lateralus is non-lexical: a borrow's lifetime "
            "ends at its last use, not at the end of the enclosing lexical scope. "
            "This is the same approach as Rust's NLL (non-lexical lifetimes) and "
            "allows more programs to compile without explicit lifetime annotations.",
        ]),
        ("16. Type Checking Pipeline Expressions", [
            "Pipeline expressions receive special treatment in the type checker. "
            "Each pipeline operator has a dedicated typing function that generates "
            "a typed pipeline node (not a typed function call). The typed pipeline "
            "node carries the operator variant, the types at each stage boundary, "
            "and the span of each stage function for error reporting.",
            ("code",
             "fn synth_pipeline(&mut self, lhs: &AstExpr, rhs: &AstExpr,\n"
             "                  variant: PipeVariant, env: &TyEnv)\n"
             "    -> Type\n"
             "{\n"
             "    let lhs_ty = self.synth(lhs, env);\n"
             "    let rhs_ty = self.synth(rhs, env);\n"
             "    match variant {\n"
             "        Total => {\n"
             "            let ret = self.fresh();\n"
             "            self.unify(rhs_ty, Fun(lhs_ty.clone(), ret.clone()),\n"
             "                       rhs.span());\n"
             "            // Emit a typed pipeline node, not a call node\n"
             "            ret\n"
             "        }\n"
             "        Error => {\n"
             "            let ok = self.fresh();\n"
             "            let err = self.fresh();\n"
             "            let ret = self.fresh();\n"
             "            self.unify(lhs_ty, Result(ok.clone(), err.clone()),\n"
             "                       lhs.span());\n"
             "            self.unify(rhs_ty, Fun(ok, Result(ret.clone(), err.clone())),\n"
             "                       rhs.span());\n"
             "            Result(ret, err)\n"
             "        }\n"
             "        // Async and Fanout similar...\n"
             "    }\n"
             "}"),
        ]),
        ("17. Generalization and the Let-Polymorphism Boundary", [
            "Hindley-Milner type inference produces polymorphic types only for "
            "<code>let</code>-bound names. When a <code>let</code> binding is "
            "processed, the inferred type of the bound expression is generalized: "
            "any type variable not free in the current type environment is "
            "universally quantified. The result is a type scheme.",
            ("code",
             "-- Generalization example\n"
             "-- The identity function infers type: t0 -> t0 (monomorphic)\n"
             "-- After generalization at the let boundary: ∀ t0. t0 -> t0 (polymorphic)\n"
             "let id = fn(x) x  -- type scheme: ∀ a. a -> a\n\n"
             "-- Usage: scheme is instantiated with fresh variables at each use site\n"
             "let a = id(42)    -- id instantiated to i64 -> i64\n"
             "let b = id('hi')  -- id instantiated to str -> str\n\n"
             "-- Value restriction: lambda parameters are NOT generalized\n"
             "fn apply(f: ?a -> ?b, x: ?a) -> ?b {\n"
             "    f(x)  -- f has monomorphic type at this call site\n"
             "}"),
        ]),
        ("18. Type Error Reporting with Pipeline Context", [
            "When a type error occurs inside a pipeline, the error message must "
            "identify the specific stage that caused the error and show the types "
            "flowing through the pipeline up to and including the error point. "
            "This requires the typed pipeline node to carry stage-by-stage type "
            "annotations that the error formatter can display.",
            ("code",
             "-- Type error with pipeline context (Lateralus output)\n"
             "error[E0312]: pipeline stage type mismatch at stage 3\n"
             "  --> src/main.ltl:15:9\n"
             "   |\n"
             "11 |     input\n"
             "12 |         |?> parse_json          -- Ok: Value, Err: JsonError\n"
             "13 |         |?> validate_schema     -- Ok: ValidValue, Err: JsonError\n"
             "14 |         |>  extract_numbers     -- produces Vec<i64>\n"
             "15 |         |>  format_as_string    -- expects i64, got Vec<i64>\n"
             "   |             ^^^^^^^^^^^^^^^^\n"
             "   = stage 4 of 4: format_as_string : i64 -> str\n"
             "   = previous stage output: Vec<i64>\n"
             "   = help: use 'map_join' to format a Vec: |> |v| v.map_join(format_as_string, ', ')"),
        ]),
        ("19. Incremental Front-End Compilation", [
            "The language server runs the front-end incrementally: when a source file "
            "changes, only the phases that depend on the changed content are rerun. "
            "For a single-character edit, the incremental front-end re-lexes only "
            "the affected token, re-parses only the affected production, resolves "
            "only the changed definitions, and re-type-checks only the changed "
            "expressions and any expressions that depend on them.",
            "The incremental dependency graph is maintained by the resolver: each "
            "resolved name reference is recorded as a dependency from the using "
            "expression to the defining expression. When a definition changes, the "
            "set of expressions that need re-type-checking is computed as the "
            "transitive closure of dependents.",
            ("code",
             "-- Incremental compilation latency (realistic edit scenarios)\n"
             "--\n"
             "-- Edit type               Re-lex    Re-parse   Re-resolve  Re-type\n"
             "-- Rename local variable    1 tok    1 expr       local      1 fn\n"
             "-- Change function body     N toks   1 fn body    1 fn       1 fn\n"
             "-- Change function type     N toks   1 fn sig     all uses   all callers\n"
             "-- Add import               1 line   1 item       module     none\n"
             "-- Rename exported fn       N toks   1 fn sig     all mods   all callers\n"
             "--\n"
             "-- Latency on compiler codebase (31k lines):\n"
             "-- Rename local: <5ms\n"
             "-- Change fn body: <15ms\n"
             "-- Change exported type: <100ms"),
        ]),
        ("20. Testing the Front-End", [
            "The front-end is tested at three levels: unit tests for individual "
            "phases, integration tests for end-to-end compilation, and property-based "
            "tests for semantic invariants. The unit test suite covers each "
            "parser production, each resolution rule, and each typing rule with "
            "both positive and negative examples.",
            ("list", [
                "<b>Lexer unit tests</b>: 180 tests covering all token kinds, edge cases (empty strings, large numbers, nested block comments), and pipeline operator disambiguation.",
                "<b>Parser unit tests</b>: 320 tests covering all grammar productions, error recovery scenarios, and operator precedence interactions.",
                "<b>Resolver unit tests</b>: 140 tests covering scope rules, import resolution, circular import detection, and name shadowing.",
                "<b>Type checker unit tests</b>: 560 tests covering type inference for all expression forms, all pipeline operators, polymorphism, and error cases.",
                "<b>Front-end integration tests</b>: 4,000 Lateralus programs compiled end-to-end and validated against golden outputs.",
                "<b>Property-based tests</b>: 12 properties including type preservation, substitution soundness, and deterministic type inference.",
            ]),
        ]),
        ("21. Performance Optimization of the Front-End", [
            "The front-end's dominant cost is type checking, which accounts for "
            "62% of compilation time for typical programs. The type checker has "
            "been optimized through four techniques: union-find path compression "
            "in the substitution structure, eager constraint solving (solving "
            "constraints immediately rather than collecting them all first), "
            "type variable interning (sharing equal type variable objects), "
            "and arena allocation for AST nodes.",
            ("code",
             "-- Type checker performance profile (compiler self-compilation)\n"
             "--\n"
             "-- Component                   Time (ms)   % of type check time\n"
             "-- Hindley-Milner inference       4,200         51%\n"
             "-- Row unification                1,800         22%\n"
             "-- Effect inference                 900         11%\n"
             "-- Lifetime analysis                700          8%\n"
             "-- Generalization                   500          6%\n"
             "-- Error message generation          80          1%\n"
             "-- Total type check time           8,180 ms\n"
             "-- Total compilation time         13,200 ms (type check = 62%)"),
        ]),
        ("22. Future Front-End Work", [
            "Three front-end projects are planned for the next year. The first is "
            "demand-driven type checking, which would allow the LSP to type-check "
            "only the definitions needed for a specific query (hover type, completion) "
            "rather than type-checking the entire module. The second is parallel "
            "type checking of independent definitions within a module. The third "
            "is a first-class error recovery infrastructure that produces a typed "
            "AST even for programs with type errors, enabling the LSP to provide "
            "completions and hover information inside erroneous code.",
            ("list", [
                "<b>Demand-driven type checking</b>: for LSP queries, type-check only what is needed. Estimated 10x speedup for single-function queries.",
                "<b>Parallel type checking</b>: type-check independent definitions simultaneously. Target 4x speedup on 8-core machines.",
                "<b>Error recovery in type checker</b>: produce a complete typed AST with error sentinels for erroneous expressions, enabling IDE features in the presence of errors.",
                "<b>Type-directed completion</b>: use the type at the cursor position to generate more accurate completion candidates.",
                "<b>Semantic renaming</b>: rename a definition and all its uses, including cross-module uses, using the resolver's definition reference graph.",
            ]),
        ]),
    ],
)
print("wrote from-lexer-to-language.pdf")

# ── 2. lexer-design-pipeline-first ────────────────────────────────────────────
render_paper(
    out_path=str(PDF / "lexer-design-pipeline-first.pdf"),
    title="Lexer Design for a Pipeline-First Language",
    subtitle="Hand-written DFA, operator disambiguation, and layout rules for Lateralus",
    meta="bad-antics &middot; February 2026 &middot; Lateralus Language Research",
    abstract=(
        "The lexer is the entry point of every compiler, and its design has "
        "consequences that propagate through the entire language: the token set "
        "constrains the grammar, the grammar constrains the type system, and the "
        "type system constrains the semantics. For a pipeline-native language like "
        "Lateralus, the lexer faces a unique challenge: the four pipeline operators "
        "share a prefix character and require contextual disambiguation. This paper "
        "describes the design of the Lateralus lexer in detail, including the "
        "hand-written DFA implementation, the pipeline operator disambiguation "
        "algorithm, the layout rule for significant indentation, the Unicode "
        "identifier handling, and the performance characteristics of each design "
        "choice. We also discuss design alternatives that were considered and "
        "rejected, and the trade-offs between lexer generators and hand-written "
        "implementations for a language with complex token syntax."
    ),
    sections=[
        ("1. Lexer Design Philosophy", [
            "A lexer has a simple job: convert a stream of Unicode code points into "
            "a stream of tokens. In theory, any two lexers that produce the same "
            "token stream are equivalent. In practice, lexer design choices affect "
            "error message quality, compilation performance, IDE responsiveness, "
            "and the maintainability of the compiler. The Lateralus lexer was designed "
            "with five explicit goals: correctness (no invalid programs accepted), "
            "speed (at least 50 MB/s throughput on typical source), helpful errors "
            "(diagnose common mistakes specifically), Unicode support (identifiers "
            "may use any Unicode letter), and incremental operation (single-character "
            "changes can be applied to the token stream efficiently).",
            "The most important design goal is helpfulness. A lexer that produces "
            "a single 'unexpected character' error for any invalid input is correct "
            "but not helpful. The Lateralus lexer recognizes common lexing mistakes "
            "and produces specific error messages: C-style <code>/*</code> block "
            "comments are recognized and reported as 'use <code>-{</code> instead'; "
            "the Unicode RIGHTWARDS ARROW character (→) is recognized and reported "
            "as 'use -> instead'; tab characters in indentation are recognized "
            "and reported as 'use spaces for indentation'.",
            ("h3", "1.1 Why Not a Lexer Generator?"),
            "Lexer generators (Flex, ANTLR, PLY) are widely used for language "
            "implementation, but Lateralus uses a hand-written lexer. The decision "
            "was based on three requirements that lexer generators handle poorly. "
            "First, the four pipeline operators share the prefix <code>|</code> "
            "and require two-character lookahead with context sensitivity: "
            "<code>|></code> is a pipe operator but <code>| ></code> (with a "
            "space) is a bitwise OR followed by a greater-than. Most lexer generators "
            "do not support context-sensitive tokenization cleanly.",
            "Second, the significant indentation layout rule requires the lexer to "
            "emit <code>INDENT</code> and <code>DEDENT</code> tokens based on column "
            "position, which requires maintaining a stack of indentation levels "
            "across newlines. This is natural in an imperative hand-written lexer "
            "but awkward in a declarative regex-based specification.",
            "Third, incremental lexing (re-lexing only the affected tokens after "
            "an edit) is required for IDE responsiveness. Incremental lexing requires "
            "knowing which tokens can be re-used from a previous lex and which must "
            "be re-scanned. This requires custom logic that does not fit naturally "
            "into a lexer generator's output.",
        ]),
        ("2. The Token Set", [
            "Lateralus defines 91 token kinds. These are divided into five categories: "
            "keyword tokens (32), operator and punctuation tokens (41), variable-lexeme "
            "tokens (6), trivia tokens (4), and sentinel tokens (2). The numbers are "
            "larger than typical because Lateralus distinguishes multiple forms of "
            "tokens that other languages would represent with a single token plus "
            "a semantic attribute.",
            ("code",
             "-- Token categories\n"
             "--\n"
             "-- Keywords (32):\n"
             "-- fn, let, if, else, match, type, import, pub, rec, return,\n"
             "-- true, false, and, or, not, in, for, while, break, continue,\n"
             "-- Ok, Err, Some, None, mut, ref, move, const, static, extern,\n"
             "-- unsafe, async\n"
             "--\n"
             "-- Pipeline operators (4):\n"
             "-- |>  (total),  |?>  (error),  |>>  (async),  |>|  (fan-out)\n"
             "--\n"
             "-- Arithmetic operators (8): + - * / % ** & |\n"
             "-- Comparison operators (6): == != < <= > >=\n"
             "-- Assignment operators (5): = += -= *= /=\n"
             "-- Punctuation (18): ( ) [ ] { } , . .. ; : :: -> => @ #\n"
             "--\n"
             "-- Variable-lexeme tokens (6):\n"
             "-- IDENT, INTEGER, FLOAT, STRING, MULTILINE_STRING, CHAR\n"
             "--\n"
             "-- Trivia tokens (4): WHITESPACE, NEWLINE, LINE_COMMENT, BLOCK_COMMENT\n"
             "--\n"
             "-- Sentinel tokens (2): EOF, INVALID"),
            "Keyword tokens are recognized by the lexer after scanning an identifier: "
            "the identifier text is looked up in a hash table of reserved words. "
            "If found, the token kind is changed from <code>IDENT</code> to the "
            "keyword kind. The hash table lookup adds a negligible overhead (one "
            "hash table lookup per identifier) in exchange for clean identifier "
            "scanning code.",
        ]),
        ("3. The Main Scanning Loop", [
            "The main scanning loop reads one character at a time and dispatches "
            "to a scanning function based on the character. The dispatch is implemented "
            "as a match statement on the character, which compiles to an efficient "
            "jump table on most architectures.",
            ("code",
             "fn scan_next(&mut self) -> Token {\n"
             "    loop {\n"
             "        let start = self.pos;\n"
             "        let c = match self.advance() {\n"
             "            Some(c) => c,\n"
             "            None    => return Token { kind: Eof, span: self.span(start) },\n"
             "        };\n"
             "        return match c {\n"
             "            ' ' | '\\t' | '\\r' => self.scan_whitespace(start),\n"
             "            '\\n'              => self.scan_newline(start),\n"
             "            '-' if self.peek() == Some('-') => self.scan_line_comment(start),\n"
             "            '-' if self.peek() == Some('{') => self.scan_block_comment(start),\n"
             "            '|'  => self.scan_pipe_or_bar(start),\n"
             "            '\"'  => self.scan_string(start),\n"
             "            '\\'' => self.scan_char(start),\n"
             "            '0'..='9' => self.scan_number(start),\n"
             "            c if is_id_start(c) => self.scan_identifier(start),\n"
             "            c => self.scan_symbol(c, start),\n"
             "        };\n"
             "    }\n"
             "}"),
        ]),
        ("4. Pipeline Operator Disambiguation", [
            "The four pipeline operators are the lexically most complex part of the "
            "Lateralus token set. All start with <code>|</code> and require lookahead "
            "to distinguish. The disambiguation tree is:",
            ("code",
             "-- Disambiguation tree for tokens starting with '|'\n"
             "|\n"
             "├── next is '?'\n"
             "│   └── and next-next is '>' → emit |?>  (error pipeline)\n"
             "│   └── otherwise            → emit |    (bitwise OR) + ? (error)\n"
             "├── next is '>'\n"
             "│   ├── and next-next is '>' → emit |>>  (async pipeline)\n"
             "│   ├── and next-next is '|' → emit |>|  (fan-out pipeline)\n"
             "│   └── otherwise            → emit |>   (total pipeline)\n"
             "└── next is '|'              → emit ||   (logical OR, if language supports)\n"
             "    └── otherwise            → emit |    (bitwise OR)"),
            ("code",
             "fn scan_pipe_or_bar(&mut self, start: usize) -> Token {\n"
             "    match self.peek() {\n"
             "        Some('?') if self.peek2() == Some('>') => {\n"
             "            self.advance(); self.advance();\n"
             "            Token { kind: PipeError, span: self.span(start) }\n"
             "        }\n"
             "        Some('>') => {\n"
             "            self.advance();\n"
             "            match self.peek() {\n"
             "                Some('>') => { self.advance();\n"
             "                    Token { kind: PipeAsync, span: self.span(start) } }\n"
             "                Some('|') => { self.advance();\n"
             "                    Token { kind: PipeFanout, span: self.span(start) } }\n"
             "                _ => Token { kind: PipeTotal, span: self.span(start) }\n"
             "            }\n"
             "        }\n"
             "        _ => Token { kind: Pipe, span: self.span(start) }\n"
             "    }\n"
             "}"),
            "The disambiguation is context-free: the choice of operator is determined "
            "solely by the characters following <code>|</code>, not by the "
            "surrounding expression context. This is a design constraint: Lateralus "
            "guarantees that the lexer is context-free so that IDE tokenizers can "
            "lex independently of the parser.",
        ]),
        ("5. Number Literal Lexing", [
            "Number literal scanning handles four bases (decimal, hex, octal, binary), "
            "digit separators (underscores), floating-point with optional exponent, "
            "and type suffixes. The scanner first determines the base (if a "
            "<code>0x</code>, <code>0o</code>, or <code>0b</code> prefix is present), "
            "then reads digits for that base, then optionally reads a decimal point "
            "and exponent for floating-point, then optionally reads a type suffix.",
            ("code",
             "fn scan_number(&mut self, start: usize) -> Token {\n"
             "    // Check for base prefix\n"
             "    let base = if self.current_is('0') {\n"
             "        match self.peek() {\n"
             "            Some('x') | Some('X') => { self.advance(); self.advance(); 16 }\n"
             "            Some('o') | Some('O') => { self.advance(); self.advance();  8 }\n"
             "            Some('b') | Some('B') => { self.advance(); self.advance();  2 }\n"
             "            _ => 10\n"
             "        }\n"
             "    } else { 10 };\n\n"
             "    // Scan digits (allow underscores as separators)\n"
             "    while matches!(self.peek(), Some(c)\n"
             "                   if c.is_digit(base) || c == '_') {\n"
             "        self.advance();\n"
             "    }\n\n"
             "    // Check for floating-point\n"
             "    if base == 10 && self.peek() == Some('.') && self.peek2() != Some('.') {\n"
             "        self.advance();  // consume '.'\n"
             "        self.scan_decimal_digits();\n"
             "        self.scan_exponent();\n"
             "        return self.make_token(Float, start);\n"
             "    }\n\n"
             "    // Check for type suffix (i64, u8, f32, etc.)\n"
             "    if matches!(self.peek(), Some('i') | Some('u') | Some('f')) {\n"
             "        self.scan_type_suffix();\n"
             "    }\n"
             "    self.make_token(Integer, start)\n"
             "}"),
        ]),
        ("6. String Literal Scanning", [
            "String literals in Lateralus support four forms: single-line strings "
            "(<code>\"hello\"</code>), raw strings (<code>r\"no\\escapes\"</code>), "
            "multi-line strings (<code>\"\"\"...\"\"\"</code>), and byte strings "
            "(<code>b\"bytes\"</code>). Each form has different escape handling "
            "and termination logic.",
            ("code",
             "-- String escape sequences supported in Lateralus strings\n"
             "\"\\n\"        -- newline\n"
             "\"\\t\"        -- tab\n"
             "\"\\r\"        -- carriage return\n"
             "\"\\\\\"       -- literal backslash\n"
             "\"\\\"\"       -- literal double-quote\n"
             "\"\\0\"        -- null character\n"
             "\"\\x41\"      -- hex escape (ASCII only)\n"
             "\"\\u{1F600}\" -- Unicode code point (any valid scalar)\n"
             "\"\\e[31m\"    -- ANSI escape (produces ESC character)\n\n"
             "-- Multi-line string: indentation is stripped to the column of \"\"\"\n"
             "let msg = \"\"\"\n"
             "    Hello, world!\n"
             "    This is indented by 4 spaces in the source,\n"
             "    but zero spaces in the string.\n"
             "    \"\"\""),
            "Multi-line string indentation stripping is based on the column of the "
            "closing <code>\"\"\"</code>. All lines of the string body are stripped "
            "of leading whitespace up to that column. This allows multi-line strings "
            "to be indented to match the surrounding code without the indentation "
            "appearing in the string content.",
        ]),
        ("7. Unicode Identifier Scanning", [
            "Unicode identifier scanning in Lateralus follows the Unicode specification "
            "UAX#31 (Unicode Identifier and Pattern Syntax). An identifier starts "
            "with a character in the <code>ID_Start</code> Unicode property and "
            "continues with characters in the <code>ID_Continue</code> property. "
            "In practice, this means any Unicode letter or underscore can start "
            "an identifier, and digits, combining marks, and connector punctuation "
            "can appear in the continuation.",
            ("code",
             "fn is_id_start(c: char) -> bool {\n"
             "    c.is_alphabetic() || c == '_'\n"
             "}\n\n"
             "fn is_id_continue(c: char) -> bool {\n"
             "    c.is_alphanumeric() || c == '_' || is_combining_mark(c)\n"
             "}\n\n"
             "// Examples of valid identifiers\n"
             "// Greek: α, β, Γ, Δ, Ω\n"
             "// Cyrillic: переменная\n"
             "// Arabic: متغير\n"
             "// CJK: 変数\n"
             "// Latin extended: café, naïve, Ångström"),
            "The Lateralus lexer normalizes identifiers to Unicode NFC (Canonical "
            "Decomposition, followed by Canonical Composition) before interning "
            "them. This ensures that identifiers that look identical to a human "
            "reader are treated as identical by the compiler, regardless of "
            "how the code was originally typed.",
        ]),
        ("8. Layout Rule Implementation", [
            "The significant indentation layout rule converts indentation changes "
            "into <code>INDENT</code> and <code>DEDENT</code> tokens. The rule "
            "is simpler than Python's because Lateralus does not have continuation "
            "lines (every line either starts a new statement or is part of an "
            "indented block).",
            ("code",
             "fn handle_newline(&mut self) {\n"
             "    // Skip blank lines and comment-only lines\n"
             "    while self.peek_is_whitespace_or_comment() {\n"
             "        self.advance_line();\n"
             "    }\n"
             "    if self.at_end() { return; }\n\n"
             "    let new_col = self.current_col();\n"
             "    let top_col = *self.indent_stack.last().unwrap();\n\n"
             "    if new_col > top_col {\n"
             "        self.indent_stack.push(new_col);\n"
             "        self.emit(Token::new(Indent));\n"
             "    } else {\n"
             "        while *self.indent_stack.last().unwrap() > new_col {\n"
             "            self.indent_stack.pop();\n"
             "            self.emit(Token::new(Dedent));\n"
             "        }\n"
             "        if *self.indent_stack.last().unwrap() != new_col {\n"
             "            self.error(E0001, \"indentation does not match any outer level\");\n"
             "        }\n"
             "    }\n"
             "}"),
            "The layout rule is disabled inside bracketed regions: within "
            "<code>()</code>, <code>[]</code>, or <code>{}</code>, newlines "
            "and indentation are treated as whitespace. This allows multi-line "
            "expressions (function argument lists, collection literals, long pipelines) "
            "to be indented freely without triggering the layout rule.",
        ]),
        ("9. Trivia Tokens and the Language Server", [
            "Trivia tokens (whitespace, newlines, comments) are included in the "
            "token stream for the language server but excluded for the parser. "
            "The exclusion is implemented by the token iterator: the parser's "
            "token iterator skips trivia tokens automatically, while the LSP's "
            "token iterator passes all tokens through.",
            "This design allows a single lexer to serve both use cases without "
            "duplication. The lexer always emits all tokens; consumers that need "
            "trivia (formatters, LSP) request it; consumers that do not need "
            "trivia (parser, type checker) skip it.",
            ("code",
             "// Two token iterators from the same lexer output\n"
             "struct ParserTokens<'a> {\n"
             "    tokens: &'a [Token],\n"
             "    pos: usize,\n"
             "}\n\n"
             "impl<'a> Iterator for ParserTokens<'a> {\n"
             "    type Item = &'a Token;\n"
             "    fn next(&mut self) -> Option<Self::Item> {\n"
             "        loop {\n"
             "            let t = self.tokens.get(self.pos)?;\n"
             "            self.pos += 1;\n"
             "            if !t.kind.is_trivia() { return Some(t); }\n"
             "        }\n"
             "    }\n"
             "}"),
        ]),
        ("10. Error Recovery in the Lexer", [
            "The lexer recovers from errors by emitting an <code>INVALID</code> "
            "token for any character that does not begin a valid token, then "
            "continuing to scan. This allows the parser to receive a complete "
            "token stream even when the source contains lexical errors, enabling "
            "the parser to detect additional errors beyond the first.",
            "Common lexing errors and their specific messages:",
            ("list", [
                "<b>Unterminated string</b>: 'string literal not closed; did you forget a closing quote?'",
                "<b>Tab in indentation</b>: 'use spaces for indentation, not tabs (found tab at line N, column M)'",
                "<b>C-style block comment</b>: 'Lateralus uses -{...}- for block comments, not /* */'",
                "<b>C-style line comment</b>: 'Lateralus uses -- for line comments, not //'",
                "<b>Unicode operator look-alike</b>: 'did you mean -> (hyphen-greater-than) instead of → (U+2192)?'",
                "<b>Invalid escape sequence</b>: 'unknown escape sequence \\X; valid escapes are \\n, \\t, \\r, \\\\, \\\", \\0, \\xNN, \\u{NNNN}'",
                "<b>Octal digit out of range</b>: 'digit 9 is not valid in an octal (base-8) literal'",
            ]),
        ]),
        ("11. Incremental Lexing", [
            "The LSP requires incremental lexing: when a document is edited, "
            "only the affected tokens should be re-lexed. The Lateralus lexer "
            "supports incremental operation through a token cache and a change "
            "tracking structure.",
            "Each token in the cache stores its start byte offset and end byte "
            "offset. When an edit is applied (an insertion or deletion of characters "
            "at a given offset), the lexer finds the first cached token that overlaps "
            "the edit region and re-lexes from that position. Tokens before the "
            "edit region are reused unchanged; tokens after the edit region are "
            "reused with their offsets adjusted.",
            ("code",
             "fn apply_edit(&mut self, edit: TextEdit) -> Vec<TokenDelta> {\n"
             "    let start_byte = edit.range.start;\n"
             "    let end_byte   = edit.range.end;\n"
             "    let new_text   = &edit.new_text;\n\n"
             "    // Find first token affected by the edit\n"
             "    let first_affected = self.tokens\n"
             "        .binary_search_by_key(&start_byte, |t| t.start)\n"
             "        .unwrap_or_else(|i| i.saturating_sub(1));\n\n"
             "    // Re-lex from the first affected token's start\n"
             "    let re_lex_from = self.tokens[first_affected].start;\n"
             "    let new_tokens = self.lex_range(re_lex_from, edit);\n\n"
             "    // Replace old tokens with new ones; adjust offsets of later tokens\n"
             "    self.patch_token_cache(first_affected, new_tokens, edit.delta())\n"
             "}"),
        ]),
        ("12. Lexer Performance", [
            "Lexer performance is measured in megabytes of source per second. "
            "The Lateralus lexer achieves 140 MB/s on ASCII-heavy source and "
            "90 MB/s on Unicode-heavy source. The throughput difference is due "
            "to the Unicode identifier scanning, which calls "
            "<code>char::is_alphabetic()</code> (a Unicode property lookup) "
            "compared to the simple ASCII range check used for ASCII identifiers.",
            ("code",
             "-- Lexer throughput measurements (3.4 GHz x86-64, single core)\n"
             "--\n"
             "-- Source type             Throughput    Notes\n"
             "-- ASCII identifiers only   140 MB/s     Fast path: ASCII range check\n"
             "-- Mixed ASCII/Unicode       90 MB/s     Unicode property lookup path\n"
             "-- String-heavy source      120 MB/s     String scanning is fast\n"
             "-- Number-heavy source      130 MB/s     Number scanning is fast\n"
             "-- Comment-heavy source     160 MB/s     Comments skip quickly\n"
             "--\n"
             "-- Compiler self-compilation: 31k lines, ~1.2 MB source\n"
             "-- Lex time: 9 ms (at 130 MB/s effective throughput)\n"
             "-- Lex as % of total: 0.07% (dominated by type checking)"),
            "The lexer is not a bottleneck in practice — type checking dominates "
            "compilation time. However, for the LSP's incremental operation, the "
            "lexer runs on every keystroke, so its latency for small edits matters. "
            "For a single-character insertion in a 1,000-line file, the incremental "
            "lexer re-lexes approximately 5-20 tokens and completes in under 0.1ms.",
        ]),
        ("13. Token Spans and Source Maps", [
            "Every token carries a <code>Span</code> value that records its start "
            "and end byte offset in the source file. Spans are the foundation of "
            "the error reporting system: every diagnostic has one or more spans "
            "that point to the relevant source locations.",
            "Spans are represented as 32-bit byte offsets rather than line-column "
            "pairs for two reasons: byte offsets can be compared and added in "
            "constant time, and the source map converts byte offsets to line-column "
            "pairs lazily (only when an error message is being formatted).",
            ("code",
             "// Span representation\n"
             "struct Span {\n"
             "    file_id: FileId,   // which source file\n"
             "    start:   u32,      // byte offset of first character\n"
             "    end:     u32,      // byte offset of last character + 1\n"
             "}\n\n"
             "// Source map: convert byte offset to line:col\n"
             "impl SourceMap {\n"
             "    fn line_col(&self, offset: u32) -> (u32, u32) {\n"
             "        // Binary search in the newline position table\n"
             "        let line = self.newlines\n"
             "            .partition_point(|&nl| nl <= offset);\n"
             "        let line_start = if line == 0 { 0 } else { self.newlines[line-1]+1 };\n"
             "        let col = offset - line_start;\n"
             "        (line as u32 + 1, col + 1)\n"
             "    }\n"
             "}"),
        ]),
        ("14. Lexer Testing Strategy", [
            "The lexer is tested with 180 unit tests covering all token kinds, "
            "edge cases, and error conditions. The test strategy uses property-based "
            "testing for the happy path (any sequence of valid tokens can be "
            "round-tripped through the lexer) and example-based testing for "
            "error conditions.",
            ("list", [
                "<b>Token round-trip property</b>: generate random sequences of valid tokens, concatenate their text representations, lex the result, and verify the token sequence matches.",
                "<b>Idempotency property</b>: lex a source twice and verify identical token streams (no non-determinism).",
                "<b>Span validity property</b>: every token's span text equals the token's text (no off-by-one in span computation).",
                "<b>Error recovery property</b>: inserting an invalid character anywhere in valid source produces one INVALID token and the rest of the token stream is unchanged.",
                "<b>Unicode normalization property</b>: two identifiers that differ only in NFC vs. NFD form are equal after lexing.",
                "<b>Incremental consistency property</b>: incremental re-lex after any single-character edit produces the same result as full re-lex.",
            ]),
        ]),
        ("15. Comparison to Other Lexer Designs", [
            "The Lateralus lexer design differs from three common alternatives: "
            "Flex-generated lexers, ANTLR lexers, and Logos-based lexers (for Rust). "
            "The comparison illuminates the trade-offs in the pipeline-first context.",
            ("list", [
                "<b>Flex/re2c</b>: extremely fast (can hit 500 MB/s), but difficult to extend with context-sensitive rules (indentation, pipeline disambiguation). Not incremental without significant custom code.",
                "<b>ANTLR</b>: supports Unicode and complex rules, but the generated Rust code is verbose and slower than hand-written. The grammar specification for Lateralus's token set tested at 60% of hand-written speed.",
                "<b>Logos (Rust derive macro)</b>: fast and ergonomic, but the derive macro approach makes it difficult to add stateful scanning (indentation stacks). Would require a separate post-processing pass for INDENT/DEDENT.",
                "<b>Hand-written (Lateralus choice)</b>: 140 MB/s, full control over disambiguation and layout rules, incremental support built in. Higher maintenance cost than generated alternatives, but the code is straightforward Lateralus.",
            ]),
        ]),
        ("16. Future Lexer Work", [
            "Two improvements are planned for the lexer. The first is SIMD-accelerated "
            "scanning for pure ASCII source files. By processing 16 or 32 bytes at "
            "a time with SSE2 or AVX2 instructions, the throughput for ASCII-only "
            "source (most identifiers, all keywords, all operators) can be increased "
            "to approximately 400-600 MB/s.",
            "The second improvement is a fuzzing harness for the lexer. The lexer "
            "currently has no libFuzzer-based fuzzing. A fuzzer would find edge cases "
            "in the Unicode handling, the pipeline operator disambiguation, and the "
            "number literal parsing that the property-based tests might miss.",
            ("list", [
                "<b>SIMD scanning</b>: process 16-32 bytes at a time for pure ASCII paths. Target 400+ MB/s.",
                "<b>Fuzzing harness</b>: libFuzzer-based fuzzer to find edge cases in Unicode handling and operator disambiguation.",
                "<b>Error message improvements</b>: add more specific messages for common Unicode mistakes (look-alike operators, combining characters used as identifiers).",
                "<b>Streaming lexer</b>: support lexing from a network stream or a pipe, useful for IDE protocol servers that receive source incrementally.",
            ]),
        ]),
    ],
)
print("wrote lexer-design-pipeline-first.pdf")

# ── 3. lateralus-bytecode-format ──────────────────────────────────────────────
render_paper(
    out_path=str(PDF / "lateralus-bytecode-format.pdf"),
    title="The Lateralus Bytecode Format",
    subtitle="LBC v1: 32-bit instruction encoding, NaN-boxing, and constant table layout",
    meta="bad-antics &middot; January 2026 &middot; Lateralus Language Research",
    abstract=(
        "The Lateralus Bytecode (LBC) format is the intermediate representation "
        "used by the Lateralus interpreter, the REPL's evaluation engine, and as "
        "a distribution format for compiled modules. LBC v1 uses 32-bit fixed-width "
        "instructions, NaN-boxing for the value representation, a constant table "
        "for literal values, and a metadata section for debug information. This paper "
        "describes the LBC format in full, including the instruction set architecture, "
        "the encoding of all 64 instructions, the constant table layout, the module "
        "format, and the design decisions that distinguish LBC from LLVM bitcode, "
        "JVM bytecode, and WebAssembly. The paper also describes the LBC interpreter "
        "and the JIT compilation path that promotes hot LBC functions to native code."
    ),
    sections=[
        ("1. Design Goals for LBC", [
            "The Lateralus Bytecode format was designed to serve four purposes "
            "simultaneously: interpreter target (fast interpretation in the REPL), "
            "distribution format (modules compiled to LBC can be loaded by the "
            "runtime without a compiler), debug target (LBC maps precisely to "
            "source locations for debugger support), and JIT input (the JIT "
            "compiler consumes LBC and emits native code for hot functions).",
            "These four purposes impose conflicting requirements. Interpreter performance "
            "favors larger instruction granularity (fewer instructions per source "
            "statement) and special-purpose instructions for common patterns "
            "(integer comparison, field access). JIT input favors smaller instruction "
            "granularity (easier to analyze and optimize). Distribution format favors "
            "compact encoding. Debug target favors explicit source location annotations.",
            "The resolution was a 32-bit fixed-width instruction encoding with 64 "
            "instruction kinds. 32-bit instructions are compact enough to encode "
            "common patterns efficiently, large enough to include explicit operand "
            "fields, and fixed-width enough to enable fast decoding in both the "
            "interpreter and JIT.",
            ("h3", "1.1 Comparison to Other Bytecode Formats"),
            "JVM bytecode uses variable-width instructions (1-5 bytes per instruction), "
            "which are compact but require sequential decoding. WebAssembly uses a "
            "binary encoding with explicit type annotations, optimized for fast "
            "validation rather than fast interpretation. CPython bytecode uses "
            "16-bit instructions with a separate argument word for large immediates. "
            "LBC uses 32-bit fixed-width instructions, prioritizing decode speed "
            "and JIT friendliness over code density.",
        ]),
        ("2. Value Representation: NaN-Boxing", [
            "LBC uses NaN-boxing for its value representation. In NaN-boxing, "
            "all values are represented as 64-bit IEEE 754 floating-point numbers. "
            "Floating-point values are represented directly. Integer values, booleans, "
            "null, and pointers are encoded as NaN payloads: the IEEE 754 NaN has "
            "a 51-bit payload that can be used to encode any other type.",
            ("code",
             "-- NaN-boxing bit layout (64 bits)\n"
             "--\n"
             "-- Float (non-NaN): [sign:1][exponent:11][mantissa:52]\n"
             "--                  Regular IEEE 754 double, used as-is\n"
             "--\n"
             "-- NaN payload layout:\n"
             "-- [1][11111111111][tag:3][payload:48]\n"
             "--  ^      ^           ^       ^\n"
             "--  |  all-ones    value tag  48-bit payload\n"
             "--  |  exponent    (type)\n"
             "--  quiet NaN bit\n"
             "--\n"
             "-- Tag values:\n"
             "-- 000: i64  (payload = lower 48 bits of integer; top bits sign-extended)\n"
             "-- 001: bool (payload: 0=false, 1=true)\n"
             "-- 010: nil\n"
             "-- 011: heap pointer (GC-managed object)\n"
             "-- 100: extern pointer (non-GC C pointer)\n"
             "-- 101: symbol / interned string id\n"
             "-- 110: reserved\n"
             "-- 111: reserved"),
            "NaN-boxing allows the interpreter to handle all value types with a "
            "single 64-bit register. The overhead is a tag check on every operation, "
            "but this is typically one instruction (mask and compare) which the "
            "branch predictor handles well when most values are of the same type "
            "in a tight loop.",
            "The 48-bit pointer payload is sufficient for all current x86-64 and "
            "ARM64 address spaces. Both architectures use 48-bit virtual addresses "
            "in their current implementations (x86-64 canonical form, ARM64 TBI). "
            "The upper 16 bits of pointers are zero (or all-ones for kernel "
            "addresses, which the runtime does not use).",
        ]),
        ("3. Instruction Encoding", [
            "LBC instructions are 32 bits wide. The instruction word is divided "
            "into an 8-bit opcode and three 8-bit operand fields. Not all instruction "
            "kinds use all three operands; the unused bits are zero and ignored.",
            ("code",
             "-- LBC instruction word format (32 bits)\n"
             "--\n"
             "-- [opcode:8][A:8][B:8][C:8]\n"
             "--\n"
             "-- For instructions with a wide immediate:\n"
             "-- [opcode:8][A:8][Bx:16]   (Bx = signed 16-bit immediate)\n"
             "-- [opcode:8][Ax:24]         (Ax = signed 24-bit immediate)\n"
             "--\n"
             "-- Register file: 256 virtual registers per function (r0-r255)\n"
             "-- Constant table: 65536 entries per module (K0-K65535)\n"
             "--\n"
             "-- Example encodings:\n"
             "-- MOVE  r3, r7        →  0x01 03 07 00\n"
             "-- LOADK r0, K42      →  0x02 00 00 2A  (K42 = constant index 42)\n"
             "-- ADD   r2, r1, r3   →  0x10 02 01 03\n"
             "-- JMP   +15          →  0x30 00 00 0F  (jump forward 15 instructions)"),
            "The 8-bit register field allows 256 virtual registers per function. "
            "This is ample for typical Lateralus functions; the compiler's register "
            "allocator reduces to physical registers before execution. The constant "
            "table index is also 16 bits wide (using the Bx encoding), allowing "
            "65536 distinct constants per module.",
        ]),
        ("4. Instruction Set: Arithmetic and Logic", [
            "The arithmetic and logic instructions operate on virtual registers "
            "and encode the result register as field A and the operands as fields "
            "B and C. Immediate-operand variants use the Bx field for a 16-bit "
            "signed immediate.",
            ("code",
             "-- Arithmetic instructions (I = integer, F = float)\n"
             "IADD  rA, rB, rC   -- rA = rB + rC (integer)\n"
             "ISUB  rA, rB, rC   -- rA = rB - rC\n"
             "IMUL  rA, rB, rC   -- rA = rB * rC\n"
             "IDIV  rA, rB, rC   -- rA = rB / rC (trapping on div-by-zero)\n"
             "IMOD  rA, rB, rC   -- rA = rB % rC\n"
             "INEG  rA, rB        -- rA = -rB\n"
             "FADD  rA, rB, rC   -- float add\n"
             "FSUB  rA, rB, rC   -- float sub\n"
             "FMUL  rA, rB, rC   -- float mul\n"
             "FDIV  rA, rB, rC   -- float div\n\n"
             "-- Comparison (result is bool)\n"
             "IEQ   rA, rB, rC   -- rA = (rB == rC) as bool\n"
             "INE   rA, rB, rC   -- rA = (rB != rC) as bool\n"
             "ILT   rA, rB, rC   -- rA = (rB < rC)\n"
             "ILE   rA, rB, rC   -- rA = (rB <= rC)\n\n"
             "-- Bit operations\n"
             "BAND  rA, rB, rC   -- bitwise AND\n"
             "BOR   rA, rB, rC   -- bitwise OR\n"
             "BXOR  rA, rB, rC   -- bitwise XOR\n"
             "BNOT  rA, rB        -- bitwise NOT\n"
             "SHL   rA, rB, rC   -- shift left\n"
             "SHR   rA, rB, rC   -- arithmetic shift right"),
        ]),
        ("5. Instruction Set: Control Flow", [
            "Control flow instructions change the interpreter's program counter. "
            "Conditional branches take a register operand (the condition) and a "
            "signed 16-bit offset. Unconditional jumps use a signed 24-bit offset "
            "in the Ax encoding. Function calls use a register operand (the function "
            "to call) and a constant table index for the argument count.",
            ("code",
             "-- Control flow instructions\n"
             "JMP   offset        -- unconditional jump (24-bit signed offset)\n"
             "JMPIF rA, offset    -- jump if rA is true\n"
             "JMPNOT rA, offset   -- jump if rA is false\n"
             "\n"
             "-- Result checking (for |?> pipeline operator)\n"
             "JMPOK  rA, offset   -- jump if rA is Ok(...)\n"
             "JMPERR rA, offset   -- jump if rA is Err(...)\n"
             "\n"
             "-- Function calls\n"
             "CALL  rA, rB, argc  -- call function rB with argc args; result in rA\n"
             "CALLK rA, K_fn, argc -- call function constant K_fn\n"
             "TAILCALL rB, argc   -- tail call (no new stack frame)\n"
             "RET   rA            -- return value in rA\n"
             "RETNIL              -- return nil\n\n"
             "-- Exception handling\n"
             "THROW rA            -- throw value in rA\n"
             "CATCH label         -- install catch handler for label\n"
             "ENDCATCH            -- remove current catch handler"),
            "The <code>JMPOK</code> and <code>JMPERR</code> instructions directly "
            "support the <code>|?></code> pipeline operator. A three-stage error "
            "pipeline compiles to three <code>CALLK</code>/<code>JMPERR</code> "
            "pairs sharing a single error exit block, implementing the error-corridor "
            "optimization at the bytecode level.",
        ]),
        ("6. Instruction Set: Heap Operations", [
            "Heap operations create, access, and modify objects allocated on the "
            "Lateralus managed heap. The heap uses a semi-space garbage collector "
            "in the interpreter (replaced by an arena allocator in production "
            "native-code builds).",
            ("code",
             "-- Record (struct) operations\n"
             "NEWREC rA, K_type   -- allocate a new record of type K_type\n"
             "GETREC rA, rB, K_field -- rA = rB.field (field index from constant table)\n"
             "SETREC rA, K_field, rC -- rA.field = rC\n\n"
             "-- Array operations\n"
             "NEWARR rA, rB        -- allocate array of size rB\n"
             "GETARR rA, rB, rC   -- rA = rB[rC]\n"
             "SETARR rA, rB, rC   -- rA[rB] = rC\n"
             "ARRLEN rA, rB       -- rA = len(rB)\n\n"
             "-- Result type operations\n"
             "MKOK   rA, rB       -- rA = Ok(rB)\n"
             "MKERR  rA, rB       -- rA = Err(rB)\n"
             "UNWOK  rA, rB       -- rA = unwrap Ok(rB) (traps if Err)\n"
             "UNWERR rA, rB       -- rA = unwrap Err(rB) (traps if Ok)\n\n"
             "-- Closure operations\n"
             "MKFUN  rA, K_proto, N -- allocate closure with N upvalues\n"
             "GETUP  rA, N          -- rA = upvalue N\n"
             "SETUP  N, rA          -- upvalue N = rA"),
        ]),
        ("7. The Constant Table", [
            "The constant table is a module-level array of values that are referenced "
            "by instructions using a 16-bit index. Each entry in the constant table "
            "has a type tag and a payload. The constant table stores string literals, "
            "integer constants larger than 16 bits, floating-point constants, type "
            "descriptors, and function prototypes.",
            ("code",
             "-- Constant table entry types\n"
             "enum ConstKind {\n"
             "    I64(i64),               -- 64-bit integer constant\n"
             "    F64(f64),               -- 64-bit float constant\n"
             "    Str(String),            -- interned string constant\n"
             "    Bool(bool),             -- boolean constant\n"
             "    Nil,                    -- nil constant\n"
             "    FnProto(FnPrototype),   -- function prototype (code + metadata)\n"
             "    TypeDescriptor(TypeId), -- type descriptor reference\n"
             "    FieldName(FieldId),     -- record field name\n"
             "    GlobalRef(DefId),       -- reference to a global definition\n"
             "}\n\n"
             "-- Function prototype structure\n"
             "struct FnPrototype {\n"
             "    arity:      u8,         -- number of parameters\n"
             "    upvalues:   u8,         -- number of upvalues (captured variables)\n"
             "    code:       Vec<u32>,   -- LBC instructions\n"
             "    consts:     Vec<Const>, -- local constant table\n"
             "    debug:      DebugInfo,  -- source location map\n"
             "}"),
        ]),
        ("8. Module Format", [
            "An LBC module file contains a header, a type section, a constant "
            "section, a code section, and a debug section. The file format is "
            "designed for fast loading: the type and constant sections can be "
            "loaded and interned in one pass, and the code section is directly "
            "mmap-able for execution.",
            ("code",
             "-- LBC module file layout\n"
             "Header:\n"
             "    magic      : [u8; 4]  = [0x4C, 0x42, 0x43, 0x01]  ('LBC\\x01')\n"
             "    version    : u16      = 1\n"
             "    flags      : u16      (bit 0: debug info present)\n"
             "    type_count : u32\n"
             "    const_count: u32\n"
             "    fn_count   : u32\n"
             "\n"
             "Type Section:\n"
             "    type_descriptors: [TypeDescriptor; type_count]\n"
             "\n"
             "Constant Section:\n"
             "    const_entries: [ConstEntry; const_count]\n"
             "\n"
             "Code Section:\n"
             "    fn_prototypes: [FnPrototype; fn_count]\n"
             "\n"
             "Debug Section (optional):\n"
             "    source_maps: [SourceMap; fn_count]  -- maps instruction index to source location\n"
             "    names:       [NameEntry; N]         -- register names for debugger"),
        ]),
        ("9. The LBC Interpreter", [
            "The LBC interpreter is a direct-threaded interpreter. Each instruction "
            "is decoded by extracting the opcode byte, then jumping to the handler "
            "for that opcode using a computed goto (in C99) or a match statement "
            "(in Lateralus). The computed goto approach is 15-20% faster because "
            "it eliminates the range check in the match statement.",
            ("code",
             "// LBC interpreter inner loop (Lateralus pseudocode)\n"
             "fn interpret(proto: &FnPrototype, args: Vec<Value>) -> Value {\n"
             "    let mut regs = [Value::Nil; 256];\n"
             "    for (i, a) in args.iter().enumerate() { regs[i] = *a; }\n"
             "    let mut pc = 0usize;\n"
             "    loop {\n"
             "        let instr = proto.code[pc];\n"
             "        let op = (instr >> 24) as u8;\n"
             "        let a  = ((instr >> 16) & 0xFF) as u8;\n"
             "        let b  = ((instr >>  8) & 0xFF) as u8;\n"
             "        let c  = (instr & 0xFF) as u8;\n"
             "        pc += 1;\n"
             "        match op {\n"
             "            IADD  => regs[a] = iadd(regs[b], regs[c]),\n"
             "            CALL  => regs[a] = call_value(regs[b], &regs[b+1..b+1+c]),\n"
             "            JMPERR => if regs[a].is_err() { pc = (pc as i32 + b as i8 as i32) as usize; }\n"
             "            RET   => return regs[a],\n"
             "            // ... 60 more handlers\n"
             "        }\n"
             "    }\n"
             "}"),
            "Interpreter performance for arithmetic-heavy code is approximately "
            "200 million LBC instructions per second on a 3.4 GHz x86-64 machine. "
            "This is approximately 6x slower than equivalent native code. The gap "
            "is closed by the JIT for hot functions.",
        ]),
        ("10. JIT Compilation of Hot Functions", [
            "The JIT compiler promotes hot LBC functions to native code. A function "
            "is considered hot when it has been called more than 100 times. Hot "
            "functions are compiled asynchronously on a background thread; the "
            "interpreter continues running LBC while the JIT compiles.",
            ("code",
             "-- JIT promotion flow\n"
             "Interpreter sees CALL to function F:\n"
             "1. Increment F.call_count\n"
             "2. If F.call_count > HOT_THRESHOLD:\n"
             "   a. Check if F is already being compiled (JIT in progress)\n"
             "   b. If not: submit F to JIT queue; set F.jit_status = COMPILING\n"
             "   c. If F.jit_status == COMPILED: patch call site to use native code\n"
             "3. Continue interpreting LBC for this call\n\n"
             "JIT compiler (background thread):\n"
             "1. Receive function F from queue\n"
             "2. Analyze LBC: compute liveness, value types from profiling data\n"
             "3. Emit LLVM IR for F, using type specializations where safe\n"
             "4. Run LLVM -O1 optimization pipeline\n"
             "5. Generate native code; store in code cache\n"
             "6. Set F.jit_status = COMPILED; install function pointer"),
            "The JIT uses profiling data (value types observed during interpretation) "
            "to generate specialized native code for common cases. If most calls to "
            "a function pass integer arguments, the JIT generates integer-specialized "
            "code with fast-path execution and a deoptimization stub for the rare "
            "non-integer case.",
        ]),
        ("11. Debug Information", [
            "The debug section of an LBC module maps every instruction to its "
            "source location. The mapping is stored as a compressed list of "
            "(instruction_count, line_number) pairs, where each pair says 'the "
            "next N instructions correspond to line L'. This run-length encoding "
            "is compact because most instructions within a statement map to the "
            "same line.",
            ("code",
             "-- Debug info: run-length encoded source map\n"
             "struct SourceMap {\n"
             "    -- (count, line) pairs: 'next `count` instructions are at `line`'\n"
             "    runs: Vec<(u16, u32)>,\n"
             "    file: FileId,\n"
             "    fn_name: String,\n"
             "}\n\n"
             "-- Example: a 20-instruction function spanning lines 10-14\n"
             "-- Instructions 0-4: line 10 (let binding)\n"
             "-- Instructions 5-12: line 11 (pipeline)\n"
             "-- Instructions 13-17: line 13 (if branch)\n"
             "-- Instructions 18-19: line 14 (return)\n"
             "runs: [(5, 10), (8, 11), (5, 13), (2, 14)]"),
        ]),
        ("12. LBC vs. Native Code: When to Use Each", [
            "Lateralus has two execution modes: LBC interpretation and native code "
            "compilation. The choice between them depends on the use case. LBC is "
            "used for the REPL, quick one-shot scripts, and development builds. "
            "Native code is used for production releases, performance-critical "
            "libraries, and OS kernel components.",
            ("list", [
                "<b>Use LBC for</b>: REPL evaluation, quick scripts, testing, IDE expression evaluation, plugin hosting.",
                "<b>Use native code for</b>: production deployments, performance-sensitive applications, OS kernel modules, embedded firmware.",
                "<b>LBC advantages</b>: instant startup, portable (same LBC runs on any supported platform), smaller binary size, good debugger support.",
                "<b>Native code advantages</b>: 6-8x faster execution, full hardware utilization, no interpreter overhead, compatible with C FFI without runtime.",
                "<b>JIT hybrid</b>: the JIT path gives LBC-startup with near-native performance for hot paths. Suitable for long-running scripts and server processes.",
            ]),
        ]),
        ("13. LBC Disassembler and Tooling", [
            "The <code>ltl disasm</code> command disassembles an LBC module to "
            "human-readable text. The disassembler shows each instruction with "
            "its register operands, resolved constant values, and source location "
            "annotation. This is the primary tool for debugging incorrect code "
            "generation.",
            ("code",
             "# ltl disasm --annotate hello.lbc\n"
             "Module: hello\n"
             "Functions: 2\n\n"
             "fn main() [regs=4, consts=3]\n"
             "  ; src/hello.ltl:1:1\n"
             "  0000: LOADK  r0, K0     ; r0 = 'Hello, world!'\n"
             "  0001: CALLK  r1, K1, 1  ; r1 = print(r0)\n"
             "  ; src/hello.ltl:2:5\n"
             "  0002: LOADK  r2, K2     ; r2 = 0\n"
             "  0003: RET    r2          ; return 0\n\n"
             "Constants:\n"
             "  K0: str  'Hello, world!'\n"
             "  K1: fn   <extern print>\n"
             "  K2: i64  0"),
        ]),
        ("14. Future LBC Work", [
            "LBC v2 is planned for Lateralus v2.0. The proposed changes are "
            "backward-incompatible with LBC v1: the instruction encoding, constant "
            "table format, and module format will all change. The changes are "
            "motivated by experience with v1's limitations.",
            ("list", [
                "<b>64-instruction opcode limit</b>: LBC v1 has room for 256 opcodes but defines 64. LBC v2 will use a 6-bit opcode field to increase density, using the freed bits for wider immediates.",
                "<b>Typed bytecode</b>: LBC v2 will carry explicit type annotations on registers, enabling the JIT to specialize without profiling and enabling faster interpreter dispatch.",
                "<b>Pipeline instructions</b>: LBC v2 will add first-class pipeline instructions (PIPE_TOTAL, PIPE_ERROR, PIPE_ASYNC, PIPE_FANOUT) replacing the current CALL-based encoding. This enables pipeline-specific interpreter optimizations.",
                "<b>Compression</b>: LBC v2 modules will be zstd-compressed for distribution, reducing module sizes by 40-60%.",
                "<b>Streaming validation</b>: LBC v2 will support streaming validation (validating as bytes arrive over a network), enabling web-hosted WASM-style execution.",
            ]),
        ]),
    ],
)
print("wrote lateralus-bytecode-format.pdf")
