"""
lateralus_lang/lexer.py  -  LATERALUS Language Lexer
===========================================================================
Converts raw .ltl / .ltasm source text into a token stream.

Supports
--------
  · Keywords: module import fn async let const return if elif else
              match while loop for break continue try recover ensure
              true false nil pub typeof sizeof as
  · Operators: + - * / % ** | & ^ ~ << >> |> -> => == != <= >= && ||
               = += -= *= /= %= **=
  · Delimiters: ( ) { } [ ] , ; : .  ..  ..<
  · Literals:   integer, hex (0x), binary (0b), float, string (with \\-escapes
                and {interpolation}), raw string r"…", char 'c'
  · Comments:   // single-line, /* multi-line */, # hash (scripting compat)

All tokens carry file, line, col for error reporting.
===========================================================================
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Iterator, List, Optional


# -----------------------------------------------------------------------------
# Token kinds
# -----------------------------------------------------------------------------

class TK(Enum):
    # Literals
    INT        = auto()
    FLOAT      = auto()
    STRING     = auto()
    RAW_STRING = auto()
    CHAR       = auto()
    BOOL       = auto()
    NIL        = auto()

    # Identifiers / keywords
    IDENT      = auto()
    KW_MODULE  = auto()
    KW_IMPORT  = auto()
    KW_FN      = auto()
    KW_ASYNC   = auto()
    KW_AWAIT   = auto()
    KW_LET     = auto()
    KW_CONST   = auto()
    KW_RETURN  = auto()
    KW_IF      = auto()
    KW_ELIF    = auto()
    KW_ELSE    = auto()
    KW_MATCH   = auto()
    KW_WHILE   = auto()
    KW_LOOP    = auto()
    KW_FOR     = auto()
    KW_IN      = auto()
    KW_BREAK   = auto()
    KW_CONTINUE= auto()
    KW_TRY     = auto()
    KW_RECOVER = auto()
    KW_ENSURE  = auto()
    KW_PUB     = auto()
    KW_TYPEOF  = auto()
    KW_SIZEOF  = auto()
    KW_AS      = auto()
    KW_MUT     = auto()
    KW_FROM    = auto()

    # Arithmetic
    PLUS       = auto()   # +
    MINUS      = auto()   # -
    STAR       = auto()   # *
    SLASH      = auto()   # /
    PERCENT    = auto()   # %
    STARSTAR   = auto()   # **

    # Bitwise
    AMP        = auto()   # &
    PIPE       = auto()   # |
    CARET      = auto()   # ^
    TILDE      = auto()   # ~
    LSHIFT     = auto()   # <<
    RSHIFT     = auto()   # >>

    # Logical
    AMPAMP     = auto()   # &&
    PIPEPIPE   = auto()   # ||
    BANG       = auto()   # !

    # Comparison
    EQ         = auto()   # ==
    NEQ        = auto()   # !=
    LT         = auto()   # <
    GT         = auto()   # >
    LTE        = auto()   # <=
    GTE        = auto()   # >=

    # Assignment
    ASSIGN     = auto()   # =
    PLUS_EQ    = auto()   # +=
    MINUS_EQ   = auto()   # -=
    STAR_EQ    = auto()   # *=
    SLASH_EQ   = auto()   # /=
    PERCENT_EQ = auto()   # %=
    STAR2_EQ   = auto()   # **=

    # Special operators
    PIPELINE   = auto()   # |>
    ARROW      = auto()   # ->
    FAT_ARROW  = auto()   # =>

    # Delimiters
    LPAREN     = auto()   # (
    RPAREN     = auto()   # )
    LBRACE     = auto()   # {
    RBRACE     = auto()   # }
    LBRACKET   = auto()   # [
    RBRACKET   = auto()   # ]
    COMMA      = auto()   # ,
    SEMICOLON    = auto()   # ;
    COLON        = auto()   # :
    DOUBLE_COLON = auto()   # ::  (scope / ADT variant separator)
    DOT          = auto()   # .
    DOTDOT     = auto()   # ..
    DOTDOTLT   = auto()   # ..<

    # Meta
    EOF        = auto()
    NEWLINE    = auto()   # significant in some contexts
    INDENT     = auto()
    DEDENT     = auto()

    # New language constructs (v1.1+)
    KW_STRUCT    = auto()   # struct
    KW_ENUM      = auto()   # enum
    KW_TYPE      = auto()   # type  (alias)
    KW_IMPL      = auto()   # impl
    KW_INTERFACE = auto()   # interface
    KW_SELF      = auto()   # self
    KW_WHERE     = auto()   # where  (generic constraints)
    KW_YIELD     = auto()   # yield
    KW_SPAWN     = auto()   # spawn  (concurrency)
    KW_NOT       = auto()   # not    (word-form logical not)
    KW_AND       = auto()   # and    (word-form logical and)
    KW_OR        = auto()   # or     (word-form logical or)
    KW_FOREIGN   = auto()   # foreign  (polyglot block)

    # v1.3 additions
    KW_THROW   = auto()   # throw  (raise an exception)
    KW_EMIT    = auto()   # emit   (event emission)
    KW_PROBE   = auto()   # probe  (runtime introspection)
    KW_MEASURE = auto()   # measure (timing block)
    KW_PASS    = auto()   # pass

    # New single-char tokens
    AT       = auto()   # @  (decorator)
    QUESTION = auto()   # ?  (nullable / option)

    # v1.3 two-char operators
    PIPE_OPT   = auto()   # |?  (optional pipeline — skip nil)

    # v1.4 tokens
    SPREAD     = auto()   # ...  (spread operator)
    PIPE_ASSIGN= auto()   # |>=  (pipeline assignment)
    KW_GUARD   = auto()   # guard  (early return guard clause)

    # v1.6 low-level / OS-dev tokens
    KW_UNSAFE    = auto()   # unsafe   (unchecked block)
    KW_EXTERN    = auto()   # extern   (foreign declaration)
    KW_VOLATILE  = auto()   # volatile (no-elide read/write)
    KW_ASM       = auto()   # asm      (inline assembly block)
    KW_STATIC    = auto()   # static   (module-level mutable)
    KW_ADDR_OF   = auto()   # addr_of  (take address)
    KW_DEREF     = auto()   # deref    (dereference pointer)
    KW_ALIGNOF   = auto()   # alignof  (alignment query)
    KW_OFFSETOF  = auto()   # offsetof (field offset query)

    # v1.6 concurrency tokens
    KW_SELECT    = auto()   # select   (channel multiplexing)
    KW_NURSERY   = auto()   # nursery  (structured concurrency block)
    KW_CANCEL    = auto()   # cancel   (cancellation token)

    # v1.8 metaprogramming tokens
    KW_MACRO     = auto()   # macro    (macro declaration)
    KW_COMPTIME  = auto()   # comptime (compile-time block)
    KW_DERIVE    = auto()   # derive   (auto-derive attribute — also works as decorator ident)
    KW_REFLECT   = auto()   # reflect  (compile-time type introspection)


_KEYWORDS: dict[str, TK] = {
    "module":   TK.KW_MODULE,
    "import":   TK.KW_IMPORT,
    "from":     TK.KW_FROM,
    "fn":       TK.KW_FN,
    "async":    TK.KW_ASYNC,
    "await":    TK.KW_AWAIT,
    "let":      TK.KW_LET,
    "const":    TK.KW_CONST,
    "mut":      TK.KW_MUT,
    "return":   TK.KW_RETURN,
    "if":       TK.KW_IF,
    "elif":     TK.KW_ELIF,
    "else":     TK.KW_ELSE,
    "match":    TK.KW_MATCH,
    "while":    TK.KW_WHILE,
    "loop":     TK.KW_LOOP,
    "for":      TK.KW_FOR,
    "in":       TK.KW_IN,
    "break":    TK.KW_BREAK,
    "continue": TK.KW_CONTINUE,
    "try":      TK.KW_TRY,
    "recover":  TK.KW_RECOVER,
    "ensure":   TK.KW_ENSURE,
    "pub":      TK.KW_PUB,
    "typeof":   TK.KW_TYPEOF,
    "sizeof":   TK.KW_SIZEOF,
    "as":       TK.KW_AS,
    "true":     TK.BOOL,
    "false":    TK.BOOL,
    "nil":      TK.NIL,
    # v1.1 additions
    "struct":    TK.KW_STRUCT,
    "enum":      TK.KW_ENUM,
    "type":      TK.KW_TYPE,
    "impl":      TK.KW_IMPL,
    "interface": TK.KW_INTERFACE,
    "self":      TK.KW_SELF,
    "where":     TK.KW_WHERE,
    "yield":     TK.KW_YIELD,
    "spawn":     TK.KW_SPAWN,
    "not":       TK.KW_NOT,
    "and":       TK.KW_AND,
    "or":        TK.KW_OR,
    "foreign":   TK.KW_FOREIGN,
    # v1.3 additions
    "throw":     TK.KW_THROW,
    "emit":      TK.KW_EMIT,
    "probe":     TK.KW_PROBE,
    "measure":   TK.KW_MEASURE,
    "pass":      TK.KW_PASS,
    # v1.4 additions
    "guard":     TK.KW_GUARD,
    # v1.6 low-level / OS-dev additions
    "unsafe":    TK.KW_UNSAFE,
    "extern":    TK.KW_EXTERN,
    "volatile":  TK.KW_VOLATILE,
    "asm":       TK.KW_ASM,
    "static":    TK.KW_STATIC,
    "addr_of":   TK.KW_ADDR_OF,
    "deref":     TK.KW_DEREF,
    "alignof":   TK.KW_ALIGNOF,
    "offsetof":  TK.KW_OFFSETOF,    # v1.6 concurrency keywords
    "select":     TK.KW_SELECT,
    "nursery":    TK.KW_NURSERY,
    "cancel":     TK.KW_CANCEL,
    # v1.8 metaprogramming keywords
    "macro":      TK.KW_MACRO,
    "comptime":   TK.KW_COMPTIME,
    "derive":     TK.KW_DERIVE,
    "reflect":    TK.KW_REFLECT,
}


# -----------------------------------------------------------------------------
# Token
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Token:
    kind:  TK
    value: object          # raw string value or parsed Python value
    file:  str
    line:  int
    col:   int

    def __repr__(self) -> str:
        return f"Token({self.kind.name}, {self.value!r}, {self.line}:{self.col})"


# -----------------------------------------------------------------------------
# Lexer errors
# -----------------------------------------------------------------------------

class LexError(Exception):
    def __init__(self, message: str, file: str, line: int, col: int):
        super().__init__(f"{file}:{line}:{col}  LexError: {message}")
        self.file, self.line, self.col = file, line, col


# -----------------------------------------------------------------------------
# Lexer
# -----------------------------------------------------------------------------

class Lexer:
    """
    Single-pass lexer for Lateralus source (.ltl or .ltasm).
    Call tokenize() to get the full list, or iterate via __iter__.
    """

    def __init__(self, source: str, filename: str = "<source>"):
        self._src   = source
        self._file  = filename
        self._pos   = 0
        self._line  = 1
        self._col   = 1
        self._tokens: List[Token] = []

    # -- public API ------------------------------------------------------------

    def tokenize(self) -> List[Token]:
        while self._pos < len(self._src):
            self._scan_one()
        self._tokens.append(Token(TK.EOF, None, self._file, self._line, self._col))
        return self._tokens

    # -- internal scanner ------------------------------------------------------

    def _cur(self) -> str:
        return self._src[self._pos] if self._pos < len(self._src) else "\0"

    def _peek(self, offset: int = 1) -> str:
        p = self._pos + offset
        return self._src[p] if p < len(self._src) else "\0"

    def _advance(self) -> str:
        ch = self._src[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col   = 1
        else:
            self._col  += 1
        return ch

    def _emit(self, kind: TK, value: object, line: int, col: int) -> None:
        self._tokens.append(Token(kind, value, self._file, line, col))

    def _scan_one(self) -> None:
        ch   = self._cur()
        line = self._line
        col  = self._col

        # Skip whitespace (non-newline)
        if ch in " \t\r":
            self._advance()
            return

        # Newline (kept as NEWLINE token for optional grammar use)
        if ch == "\n":
            self._advance()
            # emit but callers can strip; parser decides significance
            return

        # Comments
        if ch == "/" and self._peek() == "/":
            self._skip_line_comment()
            return
        if ch == "/" and self._peek() == "*":
            self._skip_block_comment(line, col)
            return
        if ch == "#":
            self._skip_line_comment()
            return

        # Raw string r"…"
        if ch == "r" and self._peek() == '"':
            self._advance()  # skip 'r'
            self._read_raw_string(line, col)
            return

        # String
        if ch == '"':
            self._read_string(line, col)
            return

        # Char literal
        if ch == "'":
            self._read_char(line, col)
            return

        # Numbers
        if ch.isdigit() or (ch == "-" and self._peek().isdigit()
                            and not self._tokens
                            or ch == "0" and self._peek() in "xXbB"):
            self._read_number(line, col)
            return
        if ch.isdigit():
            self._read_number(line, col)
            return

        # Identifiers & keywords
        if ch.isalpha() or ch == "_":
            self._read_ident(line, col)
            return

        # Multi-char operators (order matters — longest match first)
        two = ch + self._peek()
        three = two + self._peek(2)

        if three == "**=":
            self._advance(); self._advance(); self._advance()
            self._emit(TK.STAR2_EQ, "**=", line, col); return

        if three == "|>=":
            self._advance(); self._advance(); self._advance()
            self._emit(TK.PIPE_ASSIGN, "|>=", line, col); return

        if three == "...":
            self._advance(); self._advance(); self._advance()
            self._emit(TK.SPREAD, "...", line, col); return

        _two_map = {
            "**": TK.STARSTAR,  "|>": TK.PIPELINE,
            "|?": TK.PIPE_OPT,
            "->": TK.ARROW,     "=>": TK.FAT_ARROW,
            "==": TK.EQ,        "!=": TK.NEQ,
            "<=": TK.LTE,       ">=": TK.GTE,
            "&&": TK.AMPAMP,    "||": TK.PIPEPIPE,
            "<<": TK.LSHIFT,    ">>": TK.RSHIFT,
            "+=": TK.PLUS_EQ,   "-=": TK.MINUS_EQ,
            "*=": TK.STAR_EQ,   "/=": TK.SLASH_EQ,
            "%=": TK.PERCENT_EQ,
            "..": TK.DOTDOT,
            "::": TK.DOUBLE_COLON,
        }
        if two in _two_map:
            # special: check for "..<"
            if two == ".." and self._peek(2) == "<":
                self._advance(); self._advance(); self._advance()
                self._emit(TK.DOTDOTLT, "..<", line, col); return
            self._advance(); self._advance()
            self._emit(_two_map[two], two, line, col); return

        _one_map = {
            "+": TK.PLUS,     "-": TK.MINUS,   "*": TK.STAR,
            "/": TK.SLASH,    "%": TK.PERCENT, "|": TK.PIPE,
            "&": TK.AMP,      "^": TK.CARET,   "~": TK.TILDE,
            "!": TK.BANG,     "<": TK.LT,      ">": TK.GT,
            "=": TK.ASSIGN,   "(": TK.LPAREN,  ")": TK.RPAREN,
            "{": TK.LBRACE,   "}": TK.RBRACE,  "[": TK.LBRACKET,
            "]": TK.RBRACKET, ",": TK.COMMA,   ";": TK.SEMICOLON,
            ":": TK.COLON,    ".": TK.DOT,
            "@": TK.AT,       "?": TK.QUESTION,
        }
        if ch in _one_map:
            self._advance()
            self._emit(_one_map[ch], ch, line, col)
            return

        raise LexError(f"Unexpected character {ch!r}", self._file, line, col)

    # -- helpers ---------------------------------------------------------------

    def _skip_line_comment(self) -> None:
        while self._pos < len(self._src) and self._src[self._pos] != "\n":
            self._pos += 1

    def _skip_block_comment(self, line: int, col: int) -> None:
        self._advance(); self._advance()   # consume /*
        depth = 1
        while self._pos < len(self._src) and depth > 0:
            two = self._cur() + self._peek()
            if two == "/*":
                depth += 1; self._advance(); self._advance()
            elif two == "*/":
                depth -= 1; self._advance(); self._advance()
            else:
                self._advance()
        if depth != 0:
            raise LexError("Unterminated block comment", self._file, line, col)

    def _read_ident(self, line: int, col: int) -> None:
        start = self._pos
        while self._cur().isalnum() or self._cur() == "_":
            self._advance()
        name = self._src[start:self._pos]
        kind = _KEYWORDS.get(name, TK.IDENT)
        value: object = name
        if kind == TK.BOOL:
            value = (name == "true")
        elif kind == TK.NIL:
            value = None
        self._emit(kind, value, line, col)

    def _read_number(self, line: int, col: int) -> None:
        start = self._pos
        if self._cur() == "0" and self._peek() in "xX":
            self._advance(); self._advance()
            while self._cur() in "0123456789abcdefABCDEF_":
                self._advance()
            raw = self._src[start:self._pos].replace("_", "")
            self._emit(TK.INT, int(raw, 16), line, col)
            return
        if self._cur() == "0" and self._peek() in "bB":
            self._advance(); self._advance()
            while self._cur() in "01_":
                self._advance()
            raw = self._src[start:self._pos].replace("_", "")
            self._emit(TK.INT, int(raw[2:], 2), line, col)
            return
        is_float = False
        while self._cur().isdigit() or self._cur() == "_":
            self._advance()
        if self._cur() == "." and self._peek().isdigit():
            is_float = True
            self._advance()
            while self._cur().isdigit() or self._cur() == "_":
                self._advance()
        if self._cur() in "eE":
            is_float = True
            self._advance()
            if self._cur() in "+-":
                self._advance()
            while self._cur().isdigit():
                self._advance()
        raw = self._src[start:self._pos].replace("_", "")
        if is_float:
            self._emit(TK.FLOAT, float(raw), line, col)
        else:
            self._emit(TK.INT, int(raw), line, col)

    def _read_string(self, line: int, col: int) -> None:
        self._advance()   # opening "
        parts: list = []
        buf = ""
        while self._pos < len(self._src):
            ch = self._cur()
            if ch == '"':
                self._advance(); break
            if ch == "\\":
                self._advance()
                esc = self._advance()
                buf += {"n": "\n", "t": "\t", "r": "\r", "\\": "\\",
                        '"': '"', "0": "\0"}.get(esc, esc)
            elif ch == "{" and self._peek() != "{":
                # interpolation
                parts.append(("str", buf)); buf = ""
                self._advance()
                # collect until matching }, handling escaped chars inside expr
                depth = 1; expr_src = ""
                while self._pos < len(self._src) and depth > 0:
                    c = self._cur()
                    if c == "\\" and self._peek() in ('"', "'", "\\"):
                        # unescape inside expression slot
                        self._advance()
                        expr_src += self._advance()
                        continue
                    if c == "{": depth += 1
                    if c == "}": depth -= 1
                    if depth > 0: expr_src += c
                    self._advance()
                parts.append(("expr", expr_src))
            elif ch == "{{":
                buf += "{"; self._advance(); self._advance()
            else:
                buf += self._advance()
        parts.append(("str", buf))
        if len(parts) == 1 and parts[0][0] == "str":
            self._emit(TK.STRING, parts[0][1], line, col)
        else:
            self._emit(TK.STRING, parts, line, col)   # list = interpolated

    def _read_raw_string(self, line: int, col: int) -> None:
        self._advance()   # opening "
        buf = ""
        while self._pos < len(self._src):
            ch = self._cur()
            if ch == '"':
                self._advance(); break
            buf += self._advance()
        self._emit(TK.RAW_STRING, buf, line, col)

    def _read_char(self, line: int, col: int) -> None:
        self._advance()   # opening '
        if self._cur() == "\\":
            self._advance()
            esc = self._advance()
            ch = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\",
                  "'": "'", "0": "\0"}.get(esc, esc)
        else:
            ch = self._advance()
        if self._cur() != "'":
            raise LexError("Unterminated char literal", self._file, line, col)
        self._advance()
        self._emit(TK.CHAR, ch, line, col)


# -----------------------------------------------------------------------------
# Convenience
# -----------------------------------------------------------------------------

def lex(source: str, filename: str = "<source>") -> List[Token]:
    """Tokenize *source* and return the full token list."""
    return Lexer(source, filename).tokenize()
