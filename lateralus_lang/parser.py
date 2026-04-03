"""
lateralus_lang/parser.py  ─  LATERALUS Language Recursive-Descent Parser
═══════════════════════════════════════════════════════════════════════════
Converts the token stream produced by lexer.py into a full AST.

Grammar overview (simplified EBNF)
────────────────────────────────────
  program        = module_decl? import* stmt*
  stmt           = fn_decl | let_decl | if_stmt | match_stmt
                 | while_stmt | loop_stmt | for_stmt
                 | try_stmt | return_stmt | break | continue
                 | assign_or_expr_stmt
  fn_decl        = pub? async? "fn" IDENT "(" params ")" ("->" type)? block
  let_decl       = "let" mut? IDENT (":" type)? ("=" expr)? ";"
  if_stmt        = "if" expr block ("elif" expr block)* ("else" block)?
  match_stmt     = "match" expr "{" match_arm* "}"
  try_stmt       = "try" block recover* ensure?
  recover        = "recover" (IDENT "(" IDENT ")" | "*" "(" IDENT ")") block
  ensure         = "ensure" block
  expr           = pipeline
  pipeline       = logical ("|>" logical)*
  logical        = comparison (("&&"|"||") comparison)*
  comparison     = bitwise (("=="|"!="|"<"|">"|"<="|">=") bitwise)*
  bitwise        = shift  (("&"|"|"|"^") shift)*
  shift          = additive (("<<"|">>") additive)*
  additive       = multiplicative (("+"|"-") multiplicative)*
  multiplicative = power (("*"|"/"|"%") power)*
  power          = unary ("**" unary)*
  unary          = ("!"|"-"|"~"|typeof|sizeof) unary | postfix
  postfix        = primary ("(" args ")" | "[" expr "]" | "." IDENT | await)*
  primary        = INT | FLOAT | STRING | BOOL | NIL | IDENT
                 | "(" expr ")" | "[" (expr ",")* "]" | "{" map_pairs "}"
                 | fn_lambda | "await" expr | "(" expr "as" type ")"
═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from .ast_nodes import (
    AssignStmt, AwaitExpr, BinOp, BlockStmt, BreakStmt, CallExpr, CastExpr,
    ChainExpr, ComprehensionExpr, ContinueStmt, Decorator, EmitStmt,
    EnumDecl, EnumVariant, ExprStmt,
    FieldExpr, FnDecl,
    ForeignBlock, ForeignParam,
    ForStmt, GuardExpr, Ident, IfStmt, ImplBlock, ImportStmt, IndexExpr,
    InterfaceDecl,
    InterpolatedStr, LambdaExpr, LetDecl, ListExpr, Literal, LoopStmt, MapExpr,
    MatchArm, MatchStmt, MeasureBlock, Node, Param, PipelineAssign, Program,
    ProbeExpr, PropagateExpr,
    RangeExpr, RecoverClause,
    ReturnStmt, SelfExpr, SourceSpan, SpawnExpr, SpreadExpr, StructDecl,
    StructField, StructLiteral, TernaryExpr, ThrowStmt, TryExpr, TryStmt,
    TupleExpr, TypeAlias, TypeRef, UnaryOp, WhereClause, WhileStmt,
    YieldExpr,
    # v1.5 — type pattern matching, ADT constructors
    BindingPattern, EnumVariantPattern, ListPattern, LiteralPattern,
    OptionExpr, OrPattern, ResultExpr,
    TuplePattern, TypeMatchArm, TypeMatchExpr, TypePattern, WildcardPattern,
    # v1.6 — low-level / OS-dev constructs
    AddrOfExpr, AlignofExpr, DerefExpr, ExternDecl, InlineAsm,
    OffsetofExpr, StaticDecl, UnsafeBlock, VolatileExpr,
    # v1.6 — concurrency constructs
    AsyncForStmt, CancelExpr, ChannelExpr, NurseryBlock,
    ParallelExpr, SelectArm, SelectStmt,
    # v1.7 — conditional compilation
    CfgExpr,
    # v1.8 — metaprogramming
    CompTimeBlock, ConstFnDecl, DeriveAttr, MacroDecl, MacroInvocation,
    QuoteExpr, ReflectExpr, UnquoteExpr,
)
from .lexer import TK, Lexer, Token, LexError


# ─────────────────────────────────────────────────────────────────────────────
# ParseError
# ─────────────────────────────────────────────────────────────────────────────

class ParseError(Exception):
    def __init__(self, message: str, token: Token):
        loc = f"{token.file}:{token.line}:{token.col}"
        super().__init__(f"{loc}  ParseError: {message}  (got {token.kind.name} {token.value!r})")
        self.token = token


# ─────────────────────────────────────────────────────────────────────────────
# Parser
# ─────────────────────────────────────────────────────────────────────────────

_ASSIGN_OPS = {TK.ASSIGN, TK.PLUS_EQ, TK.MINUS_EQ,
               TK.STAR_EQ, TK.SLASH_EQ, TK.PERCENT_EQ, TK.STAR2_EQ,
               TK.PIPE_ASSIGN}

_CMP_OPS = {TK.EQ: "==", TK.NEQ: "!=", TK.LT: "<",
            TK.GT: ">",  TK.LTE: "<=", TK.GTE: ">="}

_ADD_OPS = {TK.PLUS: "+", TK.MINUS: "-"}

_MUL_OPS = {TK.STAR: "*", TK.SLASH: "/", TK.PERCENT: "%"}

_SHIFT_OPS = {TK.LSHIFT: "<<", TK.RSHIFT: ">>"}

_BITWISE_OPS = {TK.AMP: "&", TK.PIPE: "|", TK.CARET: "^"}


class Parser:
    def __init__(self, tokens: List[Token]):
        # Strip EOF if multiple, keep one
        self._tokens = [t for t in tokens if t.kind != TK.EOF]
        self._tokens.append(next((t for t in tokens if t.kind == TK.EOF),
                                 Token(TK.EOF, None, "<unknown>", 0, 0)))
        self._pos = 0

    # ── token navigation ──────────────────────────────────────────────────────

    def _cur(self) -> Token:
        return self._tokens[self._pos]

    def _peek(self, offset: int = 1) -> Token:
        p = self._pos + offset
        return self._tokens[min(p, len(self._tokens) - 1)]

    def _advance(self) -> Token:
        t = self._tokens[self._pos]
        if self._pos < len(self._tokens) - 1:
            self._pos += 1
        return t

    def _check(self, *kinds: TK) -> bool:
        return self._cur().kind in kinds

    def _peek_next_is(self, kind: TK) -> bool:
        """Check if the NEXT token (after current) matches the given kind."""
        return self._peek(1).kind == kind

    def _match(self, *kinds: TK) -> Optional[Token]:
        if self._cur().kind in kinds:
            return self._advance()
        return None

    def _expect(self, kind: TK, msg: str = "") -> Token:
        if self._cur().kind != kind:
            raise ParseError(msg or f"expected {kind.name}", self._cur())
        return self._advance()

    def _span(self, tok: Token) -> SourceSpan:
        return SourceSpan(tok.file, tok.line, tok.col)

    # ── top-level ─────────────────────────────────────────────────────────────

    def parse(self) -> Program:
        t0 = self._cur()
        prog = Program(span=self._span(t0))
        prog.source_file = t0.file

        if self._check(TK.KW_MODULE):
            self._advance()
            parts = [self._expect(TK.IDENT, "expected module name").value]
            while self._match(TK.DOT):
                parts.append(self._expect(TK.IDENT, "expected module name segment").value)
            prog.module = ".".join(parts)
            self._match(TK.SEMICOLON)

        while self._check(TK.KW_IMPORT):
            prog.imports.append(self._parse_import())

        # Also collect 'from X import Y' declarations before the body
        # (they may be intermixed with 'import' lines in practice)
        while not self._check(TK.EOF):
            if self._check(TK.KW_FROM):
                prog.imports.append(self._parse_from_import())
            elif self._check(TK.KW_IMPORT):
                prog.imports.append(self._parse_import())
            else:
                prog.body.append(self._parse_stmt())

        return prog

    def _parse_import(self) -> ImportStmt:
        t = self._expect(TK.KW_IMPORT)
        span = self._span(t)
        parts = [self._expect(TK.IDENT, "expected module name").value]
        while self._match(TK.DOT):
            parts.append(self._expect(TK.IDENT, "expected identifier").value)
        path = ".".join(parts)
        alias = None
        if self._match(TK.KW_AS):
            alias = self._expect(TK.IDENT, "expected alias").value
        self._match(TK.SEMICOLON)
        return ImportStmt(span=span, path=path, alias=alias)

    # ── statements ───────────────────────────────────────────────────────────

    def _parse_stmt(self):
        t = self._cur()

        # Decorators — collect before the decorated item
        if t.kind == TK.AT:
            return self._parse_decorated()

        # pub prefix — apply to next construct
        if t.kind == TK.KW_PUB:
            return self._parse_pub()

        if t.kind in (TK.KW_PUB, TK.KW_FN):
            return self._parse_fn_decl()
        if t.kind == TK.KW_ASYNC:
            # async for x in stream { ... }
            if self._peek_next_is(TK.KW_FOR):
                return self._parse_async_for()
            return self._parse_fn_decl()
        if t.kind == TK.KW_LET:
            return self._parse_let()
        if t.kind == TK.KW_CONST:
            # const fn name(...) { ... }  — compile-time function
            if self._peek_next_is(TK.KW_FN):
                return self._parse_const_fn()
            return self._parse_let(is_const=True)
        if t.kind == TK.KW_RETURN:
            return self._parse_return()
        if t.kind == TK.KW_IF:
            return self._parse_if()
        if t.kind == TK.KW_MATCH:
            return self._parse_match()
        if t.kind == TK.KW_WHILE:
            return self._parse_while()
        if t.kind == TK.KW_LOOP:
            return self._parse_loop()
        if t.kind == TK.KW_FOR:
            return self._parse_for()
        if t.kind == TK.KW_TRY:
            return self._parse_try()
        if t.kind == TK.KW_BREAK:
            self._advance()
            value = None
            if not self._check(TK.SEMICOLON, TK.RBRACE, TK.EOF):
                value = self._parse_expr()    # loop { break computed_value }
            self._match(TK.SEMICOLON)
            return BreakStmt(span=self._span(t), value=value)
        if t.kind == TK.KW_CONTINUE:
            self._advance(); self._match(TK.SEMICOLON)
            return ContinueStmt(span=self._span(t))
        if t.kind == TK.KW_IMPORT:
            return self._parse_import()
        if t.kind == TK.KW_FROM:
            return self._parse_from_import()
        # v1.1 constructs
        if t.kind == TK.KW_STRUCT:
            return self._parse_struct()
        if t.kind == TK.KW_ENUM:
            return self._parse_enum()
        if t.kind == TK.KW_TYPE:
            return self._parse_type_alias()
        if t.kind == TK.KW_IMPL:
            return self._parse_impl()
        if t.kind == TK.KW_INTERFACE:
            return self._parse_interface()
        # v1.2 constructs
        if t.kind == TK.KW_FOREIGN:
            return self._parse_foreign()

        # v1.3 constructs
        if t.kind == TK.KW_THROW:
            return self._parse_throw()
        if t.kind == TK.KW_EMIT:
            return self._parse_emit()
        if t.kind == TK.KW_MEASURE:
            return self._parse_measure()
        if t.kind == TK.KW_PASS:
            self._advance(); self._match(TK.SEMICOLON)
            return ExprStmt(span=self._span(t), expr=Literal(span=self._span(t), kind="nil", value=None))

        # v1.4: guard <cond> else { <body> }
        if t.kind == TK.KW_GUARD:
            return self._parse_guard()

        # v1.6 low-level constructs
        if t.kind == TK.KW_UNSAFE:
            return self._parse_unsafe()
        if t.kind == TK.KW_EXTERN:
            return self._parse_extern()
        if t.kind == TK.KW_STATIC:
            return self._parse_static()

        # v1.6 concurrency constructs
        if t.kind == TK.KW_SELECT:
            return self._parse_select()
        if t.kind == TK.KW_NURSERY:
            return self._parse_nursery()

        # v1.8 metaprogramming constructs
        if t.kind == TK.KW_MACRO:
            return self._parse_macro_decl()
        if t.kind == TK.KW_COMPTIME:
            return self._parse_comptime_block()

        return self._parse_assign_or_expr()

    def _parse_fn_decl(self) -> FnDecl:
        t = self._cur()
        span = self._span(t)
        is_pub   = bool(self._match(TK.KW_PUB))
        is_async = bool(self._match(TK.KW_ASYNC))
        self._expect(TK.KW_FN, "expected 'fn'")
        name = self._expect(TK.IDENT, "expected function name").value
        generics = self._parse_generic_params()
        self._expect(TK.LPAREN)
        params = self._parse_params()
        self._expect(TK.RPAREN)
        ret_type = None
        if self._match(TK.ARROW):
            ret_type = self._parse_type()
        body = self._parse_block()
        return FnDecl(span=span, name=name, params=params,
                      ret_type=ret_type, body=body, generics=generics,
                      is_async=is_async, is_pub=is_pub)

    def _parse_params(self) -> List[Param]:
        params = []
        while not self._check(TK.RPAREN, TK.EOF):
            t = self._cur()
            vararg = bool(self._match(TK.STAR))
            # Allow 'self' (KW_SELF) as a special first parameter name
            if self._cur().kind == TK.KW_SELF:
                name = self._advance().value   # consume 'self'
            else:
                name = self._expect(TK.IDENT, "expected param name").value
            type_ = None
            if self._match(TK.COLON):
                type_ = self._parse_type()
            default = None
            if self._match(TK.ASSIGN):
                default = self._parse_expr()
            params.append(Param(name=name, type_=type_, default=default,
                                span=self._span(t), vararg=vararg))
            if not self._match(TK.COMMA):
                break
        return params

    def _parse_let(self, is_const: bool = False) -> LetDecl:
        t = self._advance()   # consume 'let' or 'const'
        span = self._span(t)
        mutable = bool(self._match(TK.KW_MUT))
        name = self._expect(TK.IDENT, "expected variable name").value
        type_ = None
        if self._match(TK.COLON):
            type_ = self._parse_type()
        value = None
        if self._match(TK.ASSIGN):
            value = self._parse_expr()
        self._match(TK.SEMICOLON)
        return LetDecl(span=span, name=name, type_=type_,
                       value=value, mutable=mutable, is_const=is_const)

    def _parse_return(self) -> ReturnStmt:
        t = self._advance()
        span = self._span(t)
        value = None
        if not self._check(TK.SEMICOLON, TK.RBRACE, TK.EOF):
            value = self._parse_expr()
        self._match(TK.SEMICOLON)
        return ReturnStmt(span=span, value=value)

    def _parse_if(self) -> IfStmt:
        t = self._expect(TK.KW_IF)
        span = self._span(t)
        cond = self._parse_expr()
        then_block = self._parse_block()
        elif_arms = []
        else_block = None
        while self._check(TK.KW_ELIF):
            self._advance()
            ec = self._parse_expr()
            eb = self._parse_block()
            elif_arms.append((ec, eb))
        if self._match(TK.KW_ELSE):
            # Support `else if` as syntactic sugar for `elif`
            if self._check(TK.KW_IF):
                self._advance()
                ec = self._parse_expr()
                eb = self._parse_block()
                elif_arms.append((ec, eb))
                # Continue parsing more elif / else if chains
                while self._check(TK.KW_ELIF) or (self._check(TK.KW_ELSE) and self._peek_next_is(TK.KW_IF)):
                    if self._match(TK.KW_ELIF):
                        ec2 = self._parse_expr()
                        eb2 = self._parse_block()
                        elif_arms.append((ec2, eb2))
                    elif self._match(TK.KW_ELSE):
                        self._expect(TK.KW_IF)
                        ec2 = self._parse_expr()
                        eb2 = self._parse_block()
                        elif_arms.append((ec2, eb2))
                if self._match(TK.KW_ELSE):
                    else_block = self._parse_block()
            else:
                else_block = self._parse_block()
        return IfStmt(span=span, condition=cond, then_block=then_block,
                      elif_arms=elif_arms, else_block=else_block)

    def _parse_match(self) -> MatchStmt:
        t = self._expect(TK.KW_MATCH)
        span = self._span(t)
        subject = self._parse_expr()
        self._expect(TK.LBRACE)
        arms = []
        while not self._check(TK.RBRACE, TK.EOF):
            pattern = self._parse_expr()
            guard = None
            if self._match(TK.KW_IF):
                guard = self._parse_expr()
            self._expect(TK.FAT_ARROW, "expected '=>' in match arm")
            if self._check(TK.LBRACE):
                body = self._parse_block()
                arms.append(MatchArm(pattern=pattern, guard=guard, body=body))
            else:
                val = self._parse_expr()
                arms.append(MatchArm(pattern=pattern, guard=guard, value=val))
            self._match(TK.COMMA)
        self._expect(TK.RBRACE)
        return MatchStmt(span=span, subject=subject, arms=arms)

    # ── v1.5 pattern parsing ──────────────────────────────────────────────────

    def _parse_pattern(self) -> "Node":
        """Parse a single match-arm pattern (v1.5).

        Grammar::

            pattern = '_'                           # wildcard
                    | literal                       # literal value
                    | IDENT                         # binding
                    | IDENT '(' pattern* ')'        # type destructure
                    | IDENT '::' IDENT ('(' pattern* ')')?  # enum variant
                    | '(' pattern (',' pattern)* ')'         # tuple
                    | '[' pattern* (',' '...' IDENT)? ']'    # list/head-tail
                    | pattern '|' pattern           # alternation
        """
        span = self._span(self._cur())
        pat = self._parse_pattern_atom()
        # Handle alternation: pat1 | pat2 | ...
        while self._check(TK.PIPE):
            self._advance()
            right = self._parse_pattern_atom()
            pat = OrPattern(span=span, left=pat, right=right)
        return pat

    def _parse_pattern_atom(self) -> "Node":
        """Parse a single non-alternation pattern."""
        t   = self._cur()
        span = self._span(t)

        # Wildcard: _
        if self._check(TK.IDENT) and t.value == "_":
            self._advance()
            return WildcardPattern(span=span)

        # Literal pattern
        if self._check(TK.INT, TK.FLOAT, TK.STRING, TK.BOOL, TK.NIL):
            lit = self._parse_primary()
            if isinstance(lit, Literal):
                return LiteralPattern(span=span, value=lit)
            return LiteralPattern(span=span,
                                  value=Literal(span=span, value=None, kind="nil"))

        # Named pattern: IDENT, IDENT(...), or IDENT::VARIANT(...)
        if self._check(TK.IDENT):
            name = self._advance().value
            # Enum variant: Name::Variant(...)
            if self._check(TK.DOUBLE_COLON):
                self._advance()   # consume ::
                variant = self._expect(TK.IDENT,
                                       "expected variant name after '::'").value
                fields: list = []
                if self._match(TK.LPAREN):
                    while not self._check(TK.RPAREN, TK.EOF):
                        fields.append(self._parse_pattern())
                        if not self._match(TK.COMMA):
                            break
                    self._expect(TK.RPAREN)
                return EnumVariantPattern(span=span, enum_name=name,
                                          variant_name=variant, fields=fields)
            # Type destructure: Name(pat, pat, ...)
            if self._check(TK.LPAREN):
                self._advance()
                fields = []
                while not self._check(TK.RPAREN, TK.EOF):
                    fields.append(self._parse_pattern())
                    if not self._match(TK.COMMA):
                        break
                self._expect(TK.RPAREN)
                return TypePattern(span=span, type_name=name, fields=fields)
            # Plain binding
            return BindingPattern(span=span, name=name)

        # Tuple pattern: (pat, pat, ...)
        if self._match(TK.LPAREN):
            elements = []
            while not self._check(TK.RPAREN, TK.EOF):
                elements.append(self._parse_pattern())
                if not self._match(TK.COMMA):
                    break
            self._expect(TK.RPAREN)
            return TuplePattern(span=span, elements=elements)

        # List pattern: [pat, pat, ...rest]
        if self._match(TK.LBRACKET):
            head = []
            rest = None
            while not self._check(TK.RBRACKET, TK.EOF):
                if self._check(TK.SPREAD):
                    self._advance()
                    rest = self._expect(TK.IDENT,
                                        "expected rest binding after '...'").value
                    break
                head.append(self._parse_pattern())
                if not self._match(TK.COMMA):
                    break
            self._expect(TK.RBRACKET)
            return ListPattern(span=span, head=head, rest=rest)

        # Fallback — treat as wildcard to avoid hard failure
        self._advance()
        return WildcardPattern(span=span)

    def _parse_type_match_expr(self) -> TypeMatchExpr:
        """Parse a match expression (v1.5) — usable as both stmt and expr.

        Grammar::

            type_match_expr = 'match' expr '{'
                                  (pattern ['if' expr] '=>' (expr | block) ','?)*
                              '}'
        """
        t    = self._expect(TK.KW_MATCH)
        span = self._span(t)
        subject = self._parse_expr()
        self._expect(TK.LBRACE)
        arms: list = []
        while not self._check(TK.RBRACE, TK.EOF):
            pattern = self._parse_pattern()
            guard   = None
            if self._match(TK.KW_IF):
                guard = self._parse_expr()
            self._expect(TK.FAT_ARROW, "expected '=>' in match arm")
            if self._check(TK.LBRACE):
                body = self._parse_block()
                arms.append(TypeMatchArm(pattern=pattern, guard=guard, body=body))
            else:
                val = self._parse_expr()
                arms.append(TypeMatchArm(pattern=pattern, guard=guard, value=val))
            self._match(TK.COMMA)
        self._expect(TK.RBRACE)
        return TypeMatchExpr(span=span, subject=subject, arms=arms)

    def _parse_while(self) -> WhileStmt:
        t = self._expect(TK.KW_WHILE)
        cond = self._parse_expr()
        body = self._parse_block()
        return WhileStmt(span=self._span(t), condition=cond, body=body)

    def _parse_loop(self) -> LoopStmt:
        t = self._expect(TK.KW_LOOP)
        body = self._parse_block()
        return LoopStmt(span=self._span(t), body=body)

    def _parse_for(self) -> ForStmt:
        t = self._expect(TK.KW_FOR)
        var = self._expect(TK.IDENT, "expected loop variable").value
        self._expect(TK.KW_IN, "expected 'in'")
        iter_expr = self._parse_expr()
        body = self._parse_block()
        return ForStmt(span=self._span(t), var=var, iter=iter_expr, body=body)

    def _parse_try(self) -> TryStmt:
        t = self._expect(TK.KW_TRY)
        body = self._parse_block()
        recoveries = []
        while self._check(TK.KW_RECOVER):
            rt = self._advance()
            error_type = None
            binding = None
            if self._check(TK.STAR):
                self._advance()
                self._expect(TK.LPAREN)
                binding = self._expect(TK.IDENT).value
                self._expect(TK.RPAREN)
            elif self._check(TK.IDENT):
                error_type = self._advance().value
                self._expect(TK.LPAREN)
                binding = self._expect(TK.IDENT).value
                self._expect(TK.RPAREN)
            rb = self._parse_block()
            recoveries.append(RecoverClause(error_type=error_type,
                                             binding=binding, body=rb,
                                             span=self._span(rt)))
        ensure = None
        if self._match(TK.KW_ENSURE):
            ensure = self._parse_block()
        return TryStmt(span=self._span(t), body=body,
                       recoveries=recoveries, ensure=ensure)

    # ── v1.3 statement parsers ────────────────────────────────────────────────

    def _parse_throw(self) -> ThrowStmt:
        """throw <expr> ;"""
        t = self._expect(TK.KW_THROW)
        value = self._parse_expr()
        self._match(TK.SEMICOLON)
        return ThrowStmt(span=self._span(t), value=value)

    def _parse_emit(self) -> EmitStmt:
        """emit <event_name>(<args...>) ;"""
        t = self._expect(TK.KW_EMIT)
        event = self._expect(TK.IDENT, "expected event name after 'emit'").value
        self._expect(TK.LPAREN)
        args = []
        while not self._check(TK.RPAREN, TK.EOF):
            args.append(self._parse_expr())
            if not self._match(TK.COMMA):
                break
        self._expect(TK.RPAREN)
        self._match(TK.SEMICOLON)
        return EmitStmt(span=self._span(t), event=event, args=args)

    def _parse_measure(self) -> MeasureBlock:
        """measure ["label"] { <body> }"""
        t = self._expect(TK.KW_MEASURE)
        label = None
        if self._check(TK.STRING):
            tok = self._advance()
            lv = tok.value
            label = lv if isinstance(lv, str) else (lv[0][1] if lv else "")
        body = self._parse_block()
        return MeasureBlock(span=self._span(t), label=label, body=body)

    def _parse_assign_or_expr(self):
        t = self._cur()
        expr = self._parse_expr()
        if self._cur().kind == TK.PIPE_ASSIGN:
            self._advance()
            rhs = self._parse_expr()
            self._match(TK.SEMICOLON)
            return PipelineAssign(span=self._span(t), target=expr, value=rhs)
        if self._cur().kind in _ASSIGN_OPS:
            op_tok = self._advance()
            rhs = self._parse_expr()
            self._match(TK.SEMICOLON)
            return AssignStmt(span=self._span(t), target=expr,
                              op=op_tok.value, value=rhs)
        self._match(TK.SEMICOLON)
        return ExprStmt(span=self._span(t), expr=expr)

    def _parse_block(self) -> BlockStmt:
        t = self._expect(TK.LBRACE, "expected '{'")
        stmts = []
        while not self._check(TK.RBRACE, TK.EOF):
            stmts.append(self._parse_stmt())
        self._expect(TK.RBRACE, "expected '}'")
        return BlockStmt(span=self._span(t), stmts=stmts)

    # ── types ─────────────────────────────────────────────────────────────────

    def _parse_type(self) -> TypeRef:
        t = self._cur()
        if self._check(TK.IDENT):
            name = self._advance().value
        elif self._cur().kind in (TK.KW_FN, TK.KW_ASYNC):
            name = self._advance().value
        elif self._check(TK.STAR):
            # *T  pointer shorthand → Ptr<T>
            self._advance()
            inner = self._parse_type()
            return TypeRef(name="Ptr", params=[inner], nullable=False,
                           span=self._span(t))
        else:
            raise ParseError("expected type name", t)
        params = []
        if self._match(TK.LT):
            while not self._check(TK.GT, TK.EOF):
                params.append(self._parse_type())
                self._match(TK.COMMA)
            self._expect(TK.GT)
        nullable = bool(self._match(TK.QUESTION))  # type? → optional/nullable
        return TypeRef(name=str(name), params=params, nullable=nullable,
                       span=self._span(t))

    # ── expressions (Pratt-style precedence climbing) ─────────────────────────

    def _parse_expr(self):
        return self._parse_ternary()

    def _parse_ternary(self):
        """Ternary: expr ? true_expr : false_expr"""
        node = self._parse_range()
        if self._match(TK.QUESTION):
            true_expr = self._parse_range()
            self._expect(TK.COLON, "expected ':' in ternary expression")
            false_expr = self._parse_range()
            return TernaryExpr(span=node.span, condition=node,
                               then_val=true_expr, else_val=false_expr)
        return node

    def _parse_range(self):
        """
        Range expressions (lowest precedence, right of pipeline):
          start..end   — inclusive  (DOTDOT)
          start..<end  — exclusive  (DOTDOTLT)
          start..      — open-ended (end omitted)
        """
        left = self._parse_pipeline()
        if self._check(TK.DOTDOT, TK.DOTDOTLT):
            inclusive = (self._cur().kind == TK.DOTDOT)
            self._advance()
            # Open range: a..  with nothing following
            if self._check(TK.SEMICOLON, TK.RBRACE, TK.RBRACKET,
                           TK.RPAREN, TK.COMMA, TK.EOF):
                right: "Node" = Literal(span=left.span, value=None, kind="nil")
            else:
                right = self._parse_pipeline()
            return RangeExpr(span=left.span, start=left, end=right, inclusive=inclusive)
        return left

    def _parse_pipeline(self):
        left = self._parse_logical()
        while self._cur().kind in (TK.PIPELINE, TK.PIPE_OPT):
            opt = self._cur().kind == TK.PIPE_OPT
            self._advance()
            right = self._parse_logical()
            span = left.span
            op = "|?" if opt else "|>"
            left = BinOp(span=span, op=op, left=left, right=right)
        # where clause: expr where { let x = val; ... }
        if self._check(TK.KW_WHERE):
            wt = self._advance()
            bindings_block = self._parse_block()
            left = WhereClause(span=self._span(wt), expr=left, bindings=bindings_block)
        return left

    def _parse_logical(self):
        left = self._parse_comparison()
        while self._cur().kind in (TK.AMPAMP, TK.PIPEPIPE,
                                   TK.KW_AND, TK.KW_OR):
            t = self._cur()
            if t.kind in (TK.AMPAMP, TK.KW_AND):
                self._advance()
                right = self._parse_comparison()
                left = BinOp(span=left.span, op="&&", left=left, right=right)
            else:
                self._advance()
                right = self._parse_comparison()
                left = BinOp(span=left.span, op="||", left=left, right=right)
        return left

    def _parse_comparison(self):
        left = self._parse_bitwise()
        while self._cur().kind in _CMP_OPS:
            op = _CMP_OPS[self._cur().kind]
            self._advance()
            right = self._parse_bitwise()
            left = BinOp(span=left.span, op=op, left=left, right=right)
        return left

    def _parse_bitwise(self):
        left = self._parse_shift()
        while self._cur().kind in _BITWISE_OPS:
            op = _BITWISE_OPS[self._cur().kind]
            self._advance()
            right = self._parse_shift()
            left = BinOp(span=left.span, op=op, left=left, right=right)
        return left

    def _parse_shift(self):
        left = self._parse_additive()
        while self._cur().kind in _SHIFT_OPS:
            op = _SHIFT_OPS[self._cur().kind]
            self._advance()
            right = self._parse_additive()
            left = BinOp(span=left.span, op=op, left=left, right=right)
        return left

    def _parse_additive(self):
        left = self._parse_multiplicative()
        while self._cur().kind in _ADD_OPS:
            op = _ADD_OPS[self._cur().kind]
            self._advance()
            right = self._parse_multiplicative()
            left = BinOp(span=left.span, op=op, left=left, right=right)
        return left

    def _parse_multiplicative(self):
        left = self._parse_power()
        while self._cur().kind in _MUL_OPS:
            op = _MUL_OPS[self._cur().kind]
            self._advance()
            right = self._parse_power()
            left = BinOp(span=left.span, op=op, left=left, right=right)
        return left

    def _parse_power(self):
        left = self._parse_unary()
        if self._match(TK.STARSTAR):
            right = self._parse_power()   # truly right-associative: a**b**c → a**(b**c)
            left = BinOp(span=left.span, op="**", left=left, right=right)
        return left

    def _parse_unary(self):
        t = self._cur()
        if self._check(TK.BANG, TK.KW_NOT):   # !expr  or  not expr
            self._advance(); operand = self._parse_unary()
            return UnaryOp(span=self._span(t), op="!", operand=operand)
        if self._check(TK.MINUS):
            self._advance(); operand = self._parse_unary()
            return UnaryOp(span=self._span(t), op="-", operand=operand)
        if self._check(TK.TILDE):
            self._advance(); operand = self._parse_unary()
            return UnaryOp(span=self._span(t), op="~", operand=operand)
        if self._check(TK.KW_TYPEOF):
            self._advance(); operand = self._parse_unary()
            return UnaryOp(span=self._span(t), op="typeof", operand=operand)
        if self._check(TK.KW_SIZEOF):
            self._advance(); operand = self._parse_unary()
            return UnaryOp(span=self._span(t), op="sizeof", operand=operand)
        # v1.6: addr_of(expr), deref(expr), volatile(expr), alignof(T), offsetof(S, f)
        if self._check(TK.KW_ADDR_OF):
            self._advance()
            self._expect(TK.LPAREN, "expected '(' after addr_of")
            operand = self._parse_expr()
            self._expect(TK.RPAREN, "expected ')' after addr_of operand")
            return AddrOfExpr(span=self._span(t), operand=operand)
        if self._check(TK.KW_DEREF):
            self._advance()
            self._expect(TK.LPAREN, "expected '(' after deref")
            operand = self._parse_expr()
            self._expect(TK.RPAREN, "expected ')' after deref operand")
            return DerefExpr(span=self._span(t), operand=operand)
        if self._check(TK.KW_VOLATILE):
            self._advance()
            self._expect(TK.LPAREN, "expected '(' after volatile")
            operand = self._parse_expr()
            self._expect(TK.RPAREN, "expected ')' after volatile operand")
            return VolatileExpr(span=self._span(t), operand=operand)
        if self._check(TK.KW_ALIGNOF):
            self._advance()
            self._expect(TK.LPAREN, "expected '(' after alignof")
            type_name = self._expect(TK.IDENT, "expected type name in alignof").value
            self._expect(TK.RPAREN, "expected ')' after alignof type")
            return AlignofExpr(span=self._span(t), type_name=type_name)
        if self._check(TK.KW_OFFSETOF):
            self._advance()
            self._expect(TK.LPAREN, "expected '(' after offsetof")
            sname = self._expect(TK.IDENT, "expected struct name in offsetof").value
            self._expect(TK.COMMA, "expected ',' in offsetof")
            fname = self._expect(TK.IDENT, "expected field name in offsetof").value
            self._expect(TK.RPAREN, "expected ')' after offsetof")
            return OffsetofExpr(span=self._span(t), struct_name=sname, field_name=fname)
        return self._parse_postfix()

    def _parse_postfix(self):
        node = self._parse_primary()
        while True:
            t = self._cur()
            if self._check(TK.LPAREN):
                self._advance()
                args, kwargs = self._parse_call_args()
                self._expect(TK.RPAREN)
                node = CallExpr(span=self._span(t), callee=node,
                                args=args, kwargs=kwargs)
            elif self._match(TK.LBRACKET):
                idx = self._parse_expr()
                self._expect(TK.RBRACKET)
                node = IndexExpr(span=self._span(t), obj=node, index=idx)
            elif self._match(TK.DOT):
                field_name = self._expect(TK.IDENT, "expected field name").value
                node = FieldExpr(span=self._span(t), obj=node, field=field_name)
            elif self._check(TK.KW_AS):
                self._advance()
                target = self._parse_type()
                node = CastExpr(span=self._span(t), value=node, target=target)
            elif self._check(TK.QUESTION):
                # Disambiguate: expr? (propagation) vs expr ? a : b (ternary)
                # Propagation: ? followed by statement-ending tokens
                # Ternary: ? followed by expression start
                nxt = self._peek().kind
                if nxt in (TK.RPAREN, TK.RBRACE, TK.RBRACKET, TK.SEMICOLON,
                           TK.EOF, TK.COMMA, TK.PIPE_ASSIGN):
                    self._advance()
                    node = PropagateExpr(span=self._span(t), value=node)
                else:
                    break  # leave ? for ternary parser
            else:
                break
        return node

    def _parse_call_args(self):
        args = []; kwargs = []
        while not self._check(TK.RPAREN, TK.EOF):
            # named arg: ident = expr
            if self._check(TK.IDENT) and self._peek().kind == TK.ASSIGN:
                name = self._advance().value
                self._advance()
                val = self._parse_expr()
                kwargs.append((name, val))
            else:
                args.append(self._parse_expr())
            if not self._match(TK.COMMA):
                break
        return args, kwargs

    def _parse_primary(self):
        t = self._cur()
        span = self._span(t)

        if self._check(TK.INT):
            self._advance(); return Literal(span=span, value=t.value, kind="int")
        if self._check(TK.FLOAT):
            self._advance(); return Literal(span=span, value=t.value, kind="float")
        if self._check(TK.BOOL):
            self._advance(); return Literal(span=span, value=t.value, kind="bool")
        if self._check(TK.NIL):
            self._advance(); return Literal(span=span, value=None, kind="nil")
        if self._check(TK.STRING, TK.RAW_STRING):
            self._advance()
            if isinstance(t.value, list):   # interpolated
                return InterpolatedStr(span=span, parts=t.value)
            return Literal(span=span, value=t.value, kind="str")

        # 'self' keyword
        if self._check(TK.KW_SELF):
            self._advance(); return SelfExpr(span=span)

        # Identifier — may start a struct literal: Name { field: val, … }
        if self._check(TK.IDENT):
            # Result::Ok / Result::Err / Option::Some / Option::None  (v1.5)
            if (self._peek().kind == TK.DOUBLE_COLON and
                    t.value in ("Result", "Option")):
                adt_name = self._advance().value          # consume "Result"/"Option"
                self._advance()                           # consume "::"
                variant  = self._expect(TK.IDENT, f"expected variant after '{adt_name}::'").value
                if adt_name == "Result":
                    if self._match(TK.LPAREN):
                        val = self._parse_expr()
                        self._expect(TK.RPAREN)
                    else:
                        val = Literal(span=span, value=None, kind="nil")
                    return ResultExpr(span=span, variant=variant, value=val)
                else:  # Option
                    if variant == "None":
                        return OptionExpr(span=span, variant="None", value=None)
                    if self._match(TK.LPAREN):
                        val = self._parse_expr()
                        self._expect(TK.RPAREN)
                    else:
                        val = Literal(span=span, value=None, kind="nil")
                    return OptionExpr(span=span, variant=variant, value=val)

            # v1.6 — channel<T>(capacity) expression
            if t.value == "channel":
                self._advance()  # consume 'channel'
                elem_type = None
                if self._match(TK.LT):
                    elem_type = self._parse_type()
                    self._expect(TK.GT, "expected '>' after channel type")
                capacity = None
                if self._match(TK.LPAREN):
                    if not self._check(TK.RPAREN):
                        capacity = self._parse_expr()
                    self._expect(TK.RPAREN)
                return ChannelExpr(span=span, elem_type=elem_type,
                                   capacity=capacity)

            # v1.6 — parallel_map/parallel_filter/parallel_reduce
            if t.value in ("parallel_map", "parallel_filter", "parallel_reduce"):
                kind = t.value.split("_", 1)[1]  # "map" / "filter" / "reduce"
                self._advance()
                self._expect(TK.LPAREN, f"expected '(' after {t.value}")
                items = self._parse_expr()
                self._expect(TK.COMMA, f"expected ',' in {t.value}(items, fn)")
                func = self._parse_expr()
                init = None
                if kind == "reduce" and self._match(TK.COMMA):
                    init = self._parse_expr()
                self._expect(TK.RPAREN)
                return ParallelExpr(span=span, kind=kind, items=items,
                                    func=func, init=init)

            # v1.7 — cfg!(key, "value") compile-time boolean
            if t.value == "cfg" and self._peek().kind == TK.BANG:
                self._advance()  # consume 'cfg'
                self._advance()  # consume '!'
                self._expect(TK.LPAREN, "expected '(' after cfg!")
                key_tok = self._expect(TK.IDENT, "expected key identifier in cfg!(key, \"value\")")
                self._expect(TK.COMMA, "expected ',' in cfg!(key, \"value\")")
                val_tok = self._expect(TK.STRING, "expected string value in cfg!(key, \"value\")")
                self._expect(TK.RPAREN, "expected ')' after cfg! expression")
                return CfgExpr(span=span, key=key_tok.value, value=val_tok.value)

            # v1.8 — reflect!(TypeName) compile-time type introspection
            if t.value == "reflect" and self._peek().kind == TK.BANG:
                self._advance()  # consume 'reflect'
                self._advance()  # consume '!'
                self._expect(TK.LPAREN, "expected '(' after reflect!")
                type_tok = self._expect(TK.IDENT, "expected type name in reflect!(Type)")
                self._expect(TK.RPAREN, "expected ')' after reflect! expression")
                return ReflectExpr(span=span, target=type_tok.value)

            # v1.8 — quote { expr } — AST quoting
            if t.value == "quote" and self._peek().kind == TK.LBRACE:
                self._advance()  # consume 'quote'
                body = self._parse_block()
                return QuoteExpr(span=span, body=body)

            # v1.8 — generic macro invocation: name!(args)
            if self._peek().kind == TK.BANG and self._peek(2).kind == TK.LPAREN:
                macro_name = self._advance().value  # consume name
                self._advance()  # consume '!'
                self._advance()  # consume '('
                args: list = []
                while not self._check(TK.RPAREN, TK.EOF):
                    args.append(self._parse_expr())
                    self._match(TK.COMMA)
                self._expect(TK.RPAREN, "expected ')' after macro invocation")
                return MacroInvocation(span=span, name=macro_name, args=args)

            # Struct-literal lookahead: IDENT LBRACE IDENT COLON
            # NOTE: we require at least one field (IDENT COLON) — never treat
            # an empty block { } as a struct literal, to avoid conflicts with
            # if/for/while bodies that follow a bare identifier condition.
            if (self._peek().kind == TK.LBRACE and
                    self._peek(2).kind == TK.IDENT and
                    self._peek(3).kind == TK.COLON):
                sname = self._advance().value   # consume name
                return self._parse_struct_literal(sname, span)
            self._advance(); return Ident(span=span, name=t.value)

        # Parenthesised expr or tuple
        if self._match(TK.LPAREN):
            expr = self._parse_expr()
            if self._match(TK.COMMA):   # tuple
                elems = [expr]
                while not self._check(TK.RPAREN, TK.EOF):
                    elems.append(self._parse_expr())
                    if not self._match(TK.COMMA):
                        break
                self._expect(TK.RPAREN)
                return TupleExpr(span=span, elements=elems)
            self._expect(TK.RPAREN)
            return expr

        # List or comprehension
        if self._match(TK.LBRACKET):
            if self._check(TK.RBRACKET):
                self._advance()
                return ListExpr(span=span, elements=[])
            first = self._parse_expr()
            # Comprehension: [expr for var in iter] or [expr for var in iter if cond]
            if self._check(TK.KW_FOR):
                self._advance()
                var = self._expect(TK.IDENT, "expected loop variable in comprehension").value
                self._expect(TK.KW_IN, "expected 'in' in comprehension")
                iter_expr = self._parse_expr()
                cond = None
                if self._check(TK.KW_IF):
                    self._advance()
                    cond = self._parse_expr()
                self._expect(TK.RBRACKET, "expected ']' to close comprehension")
                return ComprehensionExpr(span=span, kind="list", expr=first,
                                         var=var, iter=iter_expr, condition=cond)
            # Regular list
            elems = [first]
            while self._match(TK.COMMA):
                if self._check(TK.RBRACKET):
                    break  # trailing comma
                elems.append(self._parse_expr())
            self._expect(TK.RBRACKET)
            return ListExpr(span=span, elements=elems)

        # Map / block — { key: val, … }
        if self._check(TK.LBRACE):
            # Peek to decide: is it a block or a map literal?
            # Map literal starts with  { expr : expr
            if self._peek().kind == TK.IDENT and self._peek(2).kind == TK.COLON:
                return self._parse_map(span)
            return self._parse_inline_block(span)

        # Lambda: fn(params) expr  or  fn(params) { block }
        if self._check(TK.KW_FN, TK.KW_ASYNC):
            return self._parse_lambda(span)

        # Spread: ...expr
        if self._check(TK.SPREAD):
            self._advance()
            operand = self._parse_expr()
            return SpreadExpr(span=span, value=operand)

        # Await
        if self._match(TK.KW_AWAIT):
            val = self._parse_expr()
            return AwaitExpr(span=span, value=val)

        # Yield
        if self._match(TK.KW_YIELD):
            val = None
            if not self._check(TK.SEMICOLON, TK.RBRACE, TK.EOF, TK.COMMA,
                               TK.RPAREN, TK.RBRACKET):
                val = self._parse_expr()
            return YieldExpr(span=span, value=val)

        # Spawn
        if self._match(TK.KW_SPAWN):
            call = self._parse_expr()
            return SpawnExpr(span=span, call=call)

        # cancel_token()  — v1.6 cancellation
        if self._match(TK.KW_CANCEL):
            return CancelExpr(span=span)

        # probe <expr>  — v1.3 runtime introspection
        if self._match(TK.KW_PROBE):
            val = self._parse_expr()
            return ProbeExpr(span=span, value=val)

        # asm { "template" }  — v1.6 inline assembly
        if self._check(TK.KW_ASM):
            return self._parse_inline_asm(span)

        # try { ... } as an expression (v1.3) — parsed same as TryStmt
        if self._check(TK.KW_TRY):
            stmt = self._parse_try()
            return TryExpr(span=span, body=stmt.body,
                           recoveries=stmt.recoveries, ensure=stmt.ensure)

        # match expr { ... } as an expression (v1.5)
        if self._check(TK.KW_MATCH):
            return self._parse_type_match_expr()

        # v1.8 — reflect!(Type) as an expression
        if self._check(TK.KW_REFLECT):
            self._advance()  # consume 'reflect'
            self._expect(TK.BANG, "expected '!' after reflect")
            self._expect(TK.LPAREN, "expected '(' after reflect!")
            type_tok = self._expect(TK.IDENT, "expected type name in reflect!(Type)")
            self._expect(TK.RPAREN, "expected ')' after reflect! expression")
            return ReflectExpr(span=span, target=type_tok.value)

        # v1.8 — comptime as expression (last expr of block is the value)
        if self._check(TK.KW_COMPTIME):
            self._advance()
            body = self._parse_block()
            return CompTimeBlock(span=span, body=body)

        raise ParseError("unexpected token in expression", t)

    # ── v1.1 – pub prefix ─────────────────────────────────────────────────────

    def _parse_pub(self) -> "Stmt":
        """Consume 'pub' then delegate to the appropriate declaration parser."""
        t = self._advance()   # consume 'pub'
        cur = self._cur()
        if cur.kind == TK.KW_FN:
            node = self._parse_fn_decl()
            node.is_pub = True
            return node
        if cur.kind == TK.KW_ASYNC:
            node = self._parse_fn_decl()
            node.is_pub = True
            return node
        if cur.kind == TK.KW_STRUCT:
            node = self._parse_struct()
            node.is_pub = True
            return node
        if cur.kind == TK.KW_ENUM:
            node = self._parse_enum()
            node.is_pub = True
            return node
        if cur.kind == TK.KW_TYPE:
            node = self._parse_type_alias()
            node.is_pub = True
            return node
        if cur.kind == TK.KW_INTERFACE:
            node = self._parse_interface()
            node.is_pub = True
            return node
        if cur.kind == TK.KW_IMPL:
            # impl blocks are always accessible; 'pub impl' is a no-op marker
            return self._parse_impl()
        if cur.kind == TK.KW_LET:
            node = self._parse_let()
            node.mutable = True
            return node
        if cur.kind == TK.KW_CONST:
            node = self._parse_let(is_const=True)
            return node
        raise ParseError("expected declaration after 'pub'", self._cur())

    # ── v1.1 – @decorator ─────────────────────────────────────────────────────

    def _parse_decorated(self) -> "Stmt":
        """Parse one or more @decorator lines then the statement they annotate."""
        decorators = []
        while self._check(TK.AT):
            t = self._advance()   # consume '@'
            # Accept both plain IDENT and keyword-tokens (e.g. @foreign) as decorator names
            cur = self._cur()
            if cur.kind == TK.IDENT or cur.kind.name.startswith('KW_'):
                name = self._advance().value
            else:
                raise ParseError("expected decorator name", cur)
            args = []
            if self._match(TK.LPAREN):
                while not self._check(TK.RPAREN, TK.EOF):
                    args.append(self._parse_expr())
                    if not self._match(TK.COMMA):
                        break
                self._expect(TK.RPAREN)
            decorators.append(Decorator(span=self._span(t), name=name, args=args))
        # Parse the decorated statement
        stmt = self._parse_stmt()
        if hasattr(stmt, "decorators"):
            stmt.decorators = decorators + stmt.decorators
        return stmt

    # ── v1.1 – from-import ────────────────────────────────────────────────────

    def _parse_from_import(self) -> ImportStmt:
        """from stdlib.math import sqrt, PI"""
        t = self._expect(TK.KW_FROM)
        span = self._span(t)
        parts = [self._expect(TK.IDENT, "expected module name").value]
        while self._match(TK.DOT):
            parts.append(self._expect(TK.IDENT, "expected identifier").value)
        path = ".".join(parts)
        self._expect(TK.KW_IMPORT, "expected 'import'")
        items: list = []
        # from X import { a, b, c }   or   from X import a, b, c
        if self._match(TK.LBRACE):
            while not self._check(TK.RBRACE, TK.EOF):
                items.append(self._expect(TK.IDENT).value)
                if not self._match(TK.COMMA):
                    break
            self._expect(TK.RBRACE)
        else:
            while self._check(TK.IDENT):
                items.append(self._advance().value)
                if not self._match(TK.COMMA):
                    break
        alias = None
        if self._match(TK.KW_AS):
            alias = self._expect(TK.IDENT, "expected alias").value
        self._match(TK.SEMICOLON)
        return ImportStmt(span=span, path=path, alias=alias, items=items)

    # ── v1.1 – struct ─────────────────────────────────────────────────────────

    def _parse_struct(self) -> StructDecl:
        """struct Point { x: int, y: int = 0 }"""
        t = self._expect(TK.KW_STRUCT)
        span = self._span(t)
        name = self._expect(TK.IDENT, "expected struct name").value
        generics = self._parse_generic_params()
        interfaces: list = []
        # Support both:  struct X: Iface   and   struct X implements Iface
        if self._match(TK.COLON) or (self._check(TK.IDENT) and self._cur().value == "implements"):
            if self._cur().kind == TK.IDENT and self._cur().value == "implements":
                self._advance()   # consume 'implements'
            interfaces.append(self._expect(TK.IDENT).value)
            while self._match(TK.COMMA):
                interfaces.append(self._expect(TK.IDENT).value)
        self._expect(TK.LBRACE, "expected '{'")
        fields: list = []
        while not self._check(TK.RBRACE, TK.EOF):
            # skip optional comma between fields
            if self._check(TK.COMMA):
                self._advance(); continue
            ft = self._cur()
            fname = self._expect(TK.IDENT, "expected field name").value
            self._expect(TK.COLON, "expected ':' after field name")
            ftype = self._parse_type()
            fdefault = None
            if self._match(TK.ASSIGN):
                fdefault = self._parse_expr()
            fields.append(StructField(name=fname, type_=ftype,
                                      default=fdefault, span=self._span(ft)))
            self._match(TK.COMMA)
        self._expect(TK.RBRACE)
        return StructDecl(span=span, name=name, fields=fields,
                          generics=generics, interfaces=interfaces)

    # ── v1.1 – enum ───────────────────────────────────────────────────────────

    def _parse_enum(self) -> EnumDecl:
        """enum Color { Red, Green, Blue(r: int, g: int, b: int) }"""
        t = self._expect(TK.KW_ENUM)
        span = self._span(t)
        name = self._expect(TK.IDENT, "expected enum name").value
        generics = self._parse_generic_params()
        self._expect(TK.LBRACE, "expected '{'")
        variants: list = []
        while not self._check(TK.RBRACE, TK.EOF):
            if self._check(TK.COMMA):
                self._advance(); continue
            vt = self._cur()
            vname = self._expect(TK.IDENT, "expected variant name").value
            vfields: list = []
            vvalue = None
            if self._match(TK.LPAREN):
                while not self._check(TK.RPAREN, TK.EOF):
                    fft = self._cur()
                    ffname = self._expect(TK.IDENT).value
                    self._expect(TK.COLON)
                    fftype = self._parse_type()
                    vfields.append(StructField(name=ffname, type_=fftype,
                                               span=self._span(fft)))
                    if not self._match(TK.COMMA): break
                self._expect(TK.RPAREN)
            elif self._match(TK.LBRACE):
                # Record variant: VariantName { field: type, ... }
                while not self._check(TK.RBRACE, TK.EOF):
                    fft = self._cur()
                    ffname = self._expect(TK.IDENT).value
                    self._expect(TK.COLON)
                    fftype = self._parse_type()
                    vfields.append(StructField(name=ffname, type_=fftype,
                                               span=self._span(fft)))
                    if not self._match(TK.COMMA): break
                self._expect(TK.RBRACE)
            elif self._match(TK.ASSIGN):
                vvalue = self._parse_expr()
            variants.append(EnumVariant(name=vname, fields=vfields,
                                        value=vvalue, span=self._span(vt)))
            self._match(TK.COMMA)
        self._expect(TK.RBRACE)
        return EnumDecl(span=span, name=name, variants=variants,
                        generics=generics)

    # ── v1.1 – type alias ─────────────────────────────────────────────────────

    def _parse_type_alias(self) -> TypeAlias:
        """type Callback = fn(int) -> str"""
        t = self._expect(TK.KW_TYPE)
        span = self._span(t)
        name = self._expect(TK.IDENT, "expected type name").value
        generics = self._parse_generic_params()
        self._expect(TK.ASSIGN, "expected '='")
        target = self._parse_type()
        self._match(TK.SEMICOLON)
        return TypeAlias(span=span, name=name, target=target, generics=generics)

    # ── v1.1 – impl ───────────────────────────────────────────────────────────

    def _parse_impl(self) -> ImplBlock:
        """impl Point { … }  or  impl Drawable for Shape { … }"""
        t = self._expect(TK.KW_IMPL)
        span = self._span(t)
        generics = self._parse_generic_params()
        first_name = self._expect(TK.IDENT, "expected type name").value
        interface = None
        type_name = first_name
        # impl Interface for Type { ... }
        if self._check(TK.KW_FOR) or (self._check(TK.IDENT) and
                                       self._cur().value == "for"):
            self._advance()   # consume 'for' (identifier or keyword)
            type_name = self._expect(TK.IDENT).value
            interface = first_name
        self._expect(TK.LBRACE, "expected '{'")
        methods: list = []
        while not self._check(TK.RBRACE, TK.EOF):
            methods.append(self._parse_fn_decl())
        self._expect(TK.RBRACE)
        return ImplBlock(span=span, type_name=type_name, interface=interface,
                         methods=methods, generics=generics)

    # ── v1.1 – interface ──────────────────────────────────────────────────────

    def _parse_interface(self) -> InterfaceDecl:
        """interface Drawable { fn draw(self) }"""
        t = self._expect(TK.KW_INTERFACE)
        span = self._span(t)
        name = self._expect(TK.IDENT, "expected interface name").value
        generics = self._parse_generic_params()
        extends: list = []
        # Support both:  interface X: Y   and   interface X extends Y
        if self._match(TK.COLON) or (self._check(TK.IDENT) and self._cur().value == "extends"):
            if self._cur().kind == TK.IDENT and self._cur().value == "extends":
                self._advance()   # consume 'extends'
            extends.append(self._expect(TK.IDENT).value)
            while self._match(TK.COMMA):
                extends.append(self._expect(TK.IDENT).value)
        self._expect(TK.LBRACE, "expected '{'")
        methods: list = []
        while not self._check(TK.RBRACE, TK.EOF):
            # Interface methods may be abstract (no body) or have a default body
            fn = self._parse_fn_sig_or_decl()
            methods.append(fn)
        self._expect(TK.RBRACE)
        return InterfaceDecl(span=span, name=name, extends=extends,
                             methods=methods, generics=generics)

    def _parse_fn_sig_or_decl(self) -> FnDecl:
        """Parse a function declaration, accepting an absent body (abstract method)."""
        t = self._cur()
        span = self._span(t)
        is_pub   = bool(self._match(TK.KW_PUB))
        is_async = bool(self._match(TK.KW_ASYNC))
        self._expect(TK.KW_FN, "expected 'fn'")
        name = self._expect(TK.IDENT, "expected function name").value
        generics = self._parse_generic_params()
        self._expect(TK.LPAREN)
        params = self._parse_params()
        self._expect(TK.RPAREN)
        ret_type = None
        if self._match(TK.ARROW):
            ret_type = self._parse_type()
        # Body is optional for abstract methods in interfaces
        body = None
        if self._check(TK.LBRACE):
            body = self._parse_block()
        else:
            # No body — abstract / signature-only
            self._match(TK.SEMICOLON)
        return FnDecl(span=span, name=name, params=params,
                      ret_type=ret_type, body=body, generics=generics,
                      is_async=is_async, is_pub=is_pub)

    # ── generic param helpers ─────────────────────────────────────────────────

    def _parse_generic_params(self) -> list:
        """Parse optional <T, U, V> or <T: Bound, N: int> generic type parameters.

        Returns list of strings (plain params) or dicts with bounds info.
        Plain identifiers remain as strings for backward compatibility.
        Bounded params become {"name": str, "bound": str} dicts.
        """
        if not self._check(TK.LT):
            return []
        self._advance()   # consume '<'
        params = []
        while not self._check(TK.GT, TK.EOF):
            name = self._expect(TK.IDENT, "expected type param").value
            if self._match(TK.COLON):
                # Trait bound or const generic: <T: Comparable> or <N: int>
                bound = self._expect(TK.IDENT, "expected bound/type").value
                params.append({"name": name, "bound": bound})
            else:
                params.append(name)
            if not self._match(TK.COMMA):
                break
        self._expect(TK.GT, "expected '>' to close generic params")
        return params

    def _parse_struct_literal(self, name: str, span) -> StructLiteral:
        """Parse  { field: expr, … }  after the struct name has been consumed."""
        self._expect(TK.LBRACE, "expected '{'")
        fields: list = []
        while not self._check(TK.RBRACE, TK.EOF):
            fname = self._expect(TK.IDENT, "expected field name").value
            self._expect(TK.COLON, "expected ':'")
            fval = self._parse_expr()
            fields.append((fname, fval))
            self._match(TK.COMMA)
        self._expect(TK.RBRACE)
        return StructLiteral(span=span, name=name, fields=fields)

    def _parse_map(self, span) -> MapExpr:
        self._expect(TK.LBRACE)
        pairs = []
        while not self._check(TK.RBRACE, TK.EOF):
            k = self._parse_expr()
            self._expect(TK.COLON)
            v = self._parse_expr()
            pairs.append((k, v))
            if not self._match(TK.COMMA):
                break
        self._expect(TK.RBRACE)
        return MapExpr(span=span, pairs=pairs)

    def _parse_inline_block(self, span):
        """Used when a '{' appears in expression position — return the last expr."""
        block = self._parse_block()
        # Wrap in a synthetic call if needed; for now surface the block
        return block   # parser consumers deal with this

    def _parse_lambda(self, span) -> LambdaExpr:
        is_async = bool(self._match(TK.KW_ASYNC))
        self._expect(TK.KW_FN)
        params = []
        if self._match(TK.LPAREN):
            params = self._parse_params()
            self._expect(TK.RPAREN)
        ret_type = None
        if self._match(TK.ARROW):
            ret_type = self._parse_type()
        if self._check(TK.LBRACE):
            block = self._parse_block()
            return LambdaExpr(span=span, params=params, ret_type=ret_type,
                              block=block, is_async=is_async)
        body = self._parse_expr()
        return LambdaExpr(span=span, params=params, ret_type=ret_type,
                          body=body, is_async=is_async)

    # ── v1.2: foreign polyglot block ─────────────────────────────────────────

    def _parse_foreign(self) -> ForeignBlock:
        """
        Parse::

            foreign "<lang>" { "<source>" }
            foreign "<lang>" (<name>: <expr>, ...) { "<source>" }

        The body brace block must contain exactly one string literal, which
        becomes the source code passed to the polyglot runtime.
        """
        t = self._cur()
        span = self._span(t)
        self._expect(TK.KW_FOREIGN)

        # language name — must be a string literal
        lang_tok = self._expect(TK.STRING, "expected language name string after 'foreign'")
        lang = lang_tok.value

        # Optional params: (name: expr, ...)
        params: List[ForeignParam] = []
        if self._match(TK.LPAREN):
            while not self._check(TK.RPAREN) and not self._check(TK.EOF):
                name = self._expect(TK.IDENT, "expected param name").value
                self._expect(TK.COLON)
                value = self._parse_expr()
                params.append(ForeignParam(name=name, value=value))
                if not self._match(TK.COMMA):
                    break
            self._expect(TK.RPAREN)

        # Body block must contain a single string or raw-string literal as source
        self._expect(TK.LBRACE, "expected '{' for foreign block body")
        while self._match(TK.SEMICOLON):
            pass
        if self._cur().kind not in (TK.STRING, TK.RAW_STRING):
            raise ParseError(
                "expected a string or raw-string literal inside foreign block",
                self._cur(),
            )
        src_tok = self._advance()
        source = src_tok.value
        while self._match(TK.SEMICOLON):
            pass
        self._expect(TK.RBRACE)
        self._match(TK.SEMICOLON)

        return ForeignBlock(span=span, lang=lang, source=source, params=params)


    # ── v1.4 – guard ──────────────────────────────────────────────────────────

    def _parse_guard(self) -> GuardExpr:
        """guard <condition> else { <body> }"""
        t = self._expect(TK.KW_GUARD)
        span = self._span(t)
        condition = self._parse_expr()
        self._expect(TK.KW_ELSE, "expected 'else' after guard condition")
        else_body = self._parse_block()
        return GuardExpr(span=span, condition=condition, else_body=else_body)

    # v1.6 helpers — low-level constructs
    def _parse_unsafe(self) -> Stmt:
        t = self._advance()  # consume 'unsafe'
        body = self._parse_block()
        return UnsafeBlock(span=self._span(t), body=body)

    def _parse_extern(self) -> Stmt:
        t = self._advance()  # consume 'extern'
        # extern fn NAME(params) -> Type  (no body — just a declaration)
        if self._check(TK.KW_FN):
            self._advance()  # consume 'fn'
        name = self._expect(TK.IDENT, "expected identifier after extern").value
        params = []
        ret = None
        if self._match(TK.LPAREN):
            while not self._check(TK.RPAREN, TK.EOF):
                # simple param: ident : Type
                pname = self._expect(TK.IDENT).value
                self._expect(TK.COLON)
                ptype = self._parse_type()
                params.append(Param(name=pname, type_=ptype))
                self._match(TK.COMMA)
            self._expect(TK.RPAREN)
        if self._match(TK.ARROW):
            ret = self._parse_type()
        self._match(TK.SEMICOLON)
        return ExternDecl(span=self._span(t), name=name, params=params, return_type=(ret.name if ret else None))

    def _parse_static(self) -> Stmt:
        t = self._advance()  # consume 'static'
        mutable = False
        if self._check(TK.KW_MUT):
            self._advance(); mutable = True
        name = self._expect(TK.IDENT, "expected identifier after static").value
        type_ann = None
        value = None
        if self._match(TK.COLON):
            tref = self._parse_type(); type_ann = tref.name
        if self._match(TK.ASSIGN):
            value = self._parse_expr()
        self._match(TK.SEMICOLON)
        return StaticDecl(span=self._span(t), name=name, type_ann=type_ann, value=value, mutable=mutable)

    def _parse_inline_asm(self, span) -> Expr:
        t = self._advance()  # consume 'asm'
        self._expect(TK.LBRACE, "expected '{' after asm")
        # Collect raw string(s) until closing brace
        parts = []
        while not self._check(TK.RBRACE, TK.EOF):
            if self._check(TK.STRING):
                parts.append(self._advance().value)
            else:
                # allow bare identifiers / tokens inside asm template
                parts.append(self._advance().value if self._cur().value is not None else "")
        self._expect(TK.RBRACE)
        template = "\n".join(str(p) for p in parts)
        return InlineAsm(span=self._span(t), template=template)

    # ── v1.6 concurrency parsers ──────────────────────────────────────────────

    def _parse_select(self) -> SelectStmt:
        """
        select {
            msg from ch    => { ... }
            send(ch, val)  => { ... }
            after <ms>     => { ... }
            _              => { ... }
        }
        """
        t = self._expect(TK.KW_SELECT)
        self._expect(TK.LBRACE, "expected '{' after select")
        arms: List[SelectArm] = []
        while not self._check(TK.RBRACE, TK.EOF):
            arm_span = self._span(self._cur())
            # default arm: _ => { ... }
            if self._check(TK.IDENT) and self._cur().value == "_":
                self._advance()
                self._expect(TK.FAT_ARROW, "expected '=>' after '_'")
                body = self._parse_block()
                arms.append(SelectArm(kind="default", body=body, span=arm_span))
            # timeout arm: after <expr> => { ... }
            elif self._check(TK.IDENT) and self._cur().value == "after":
                self._advance()
                ms_expr = self._parse_expr()
                self._expect(TK.FAT_ARROW, "expected '=>' after timeout expr")
                body = self._parse_block()
                arms.append(SelectArm(kind="timeout", value=ms_expr,
                                      body=body, span=arm_span))
            # send arm: send(ch, val) => { ... }
            elif self._check(TK.IDENT) and self._cur().value == "send":
                self._advance()
                self._expect(TK.LPAREN, "expected '(' after send")
                ch_expr = self._parse_expr()
                self._expect(TK.COMMA, "expected ',' in send(ch, val)")
                val_expr = self._parse_expr()
                self._expect(TK.RPAREN)
                self._expect(TK.FAT_ARROW, "expected '=>' after send(...)")
                body = self._parse_block()
                arms.append(SelectArm(kind="send", channel=ch_expr,
                                      value=val_expr, body=body, span=arm_span))
            # recv arm: <ident> from <expr> => { ... }
            else:
                binding = self._expect(TK.IDENT, "expected binding or '_'").value
                # 'from' may be KW_FROM or an IDENT – accept either
                is_from = ((self._check(TK.KW_FROM)) or
                           (self._check(TK.IDENT) and self._cur().value == "from"))
                if not is_from:
                    raise ParseError("expected 'from' in select recv arm", self._cur())
                self._advance()  # consume 'from'
                ch_expr = self._parse_expr()
                self._expect(TK.FAT_ARROW, "expected '=>' after recv arm")
                body = self._parse_block()
                arms.append(SelectArm(kind="recv", channel=ch_expr,
                                      binding=binding, body=body, span=arm_span))
            self._match(TK.COMMA)
        self._expect(TK.RBRACE)
        return SelectStmt(span=self._span(t), arms=arms)

    def _parse_nursery(self) -> NurseryBlock:
        """nursery { spawn task1(); spawn task2() }"""
        t = self._expect(TK.KW_NURSERY)
        name = None
        if self._check(TK.IDENT):
            name = self._advance().value
        body = self._parse_block()
        return NurseryBlock(span=self._span(t), body=body, name=name)

    def _parse_async_for(self) -> AsyncForStmt:
        """async for x in stream { ... }"""
        t = self._cur()
        self._advance()  # consume 'async'
        self._expect(TK.KW_FOR, "expected 'for' after 'async'")
        var = self._expect(TK.IDENT, "expected loop variable").value
        self._expect(TK.KW_IN, "expected 'in'")
        iter_expr = self._parse_expr()
        body = self._parse_block()
        return AsyncForStmt(span=self._span(t), var=var, iter=iter_expr, body=body)

    # ── v1.8 — Metaprogramming ──────────────────────────────────────────

    def _parse_const_fn(self) -> ConstFnDecl:
        """const fn name(params) -> T { body }"""
        t = self._cur()
        span = self._span(t)
        is_pub = False
        self._expect(TK.KW_CONST)
        self._expect(TK.KW_FN, "expected 'fn' after 'const'")
        name = self._expect(TK.IDENT, "expected function name").value
        generics = self._parse_generic_params()
        self._expect(TK.LPAREN)
        params = self._parse_params()
        self._expect(TK.RPAREN)
        ret_type = None
        if self._match(TK.ARROW):
            ret_type = self._parse_type()
        body = self._parse_block()
        return ConstFnDecl(span=span, name=name, params=params,
                           ret_type=ret_type, body=body, generics=generics,
                           is_pub=is_pub)

    def _parse_macro_decl(self) -> MacroDecl:
        """macro name!(params) { body }"""
        t = self._cur()
        span = self._span(t)
        is_pub = False
        self._expect(TK.KW_MACRO)
        name = self._expect(TK.IDENT, "expected macro name").value
        self._expect(TK.BANG, "expected '!' after macro name")
        params: list[str] = []
        if self._match(TK.LPAREN):
            while not self._check(TK.RPAREN, TK.EOF):
                params.append(self._expect(TK.IDENT, "expected parameter name").value)
                self._match(TK.COMMA)
            self._expect(TK.RPAREN)
        body = self._parse_block()
        return MacroDecl(span=span, name=name, params=params, body=body,
                         is_pub=is_pub)

    def _parse_comptime_block(self) -> CompTimeBlock:
        """comptime { stmts }"""
        t = self._expect(TK.KW_COMPTIME)
        body = self._parse_block()
        return CompTimeBlock(span=self._span(t), body=body)


# ─────────────────────────────────────────────────────────────────────────────
# Convenience
# ─────────────────────────────────────────────────────────────────────────────

def parse(source: str, filename: str = "<source>") -> Program:
    """Lex and parse *source*, returning the root Program AST node."""
    from .lexer import lex
    tokens = lex(source, filename)
    return Parser(tokens).parse()
