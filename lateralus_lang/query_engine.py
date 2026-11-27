"""LQL: a tiny SQL-like query engine over lists of dicts.

Supported grammar (subset):

    SELECT <cols|*> FROM <table> [WHERE <condition>]
           [ORDER BY <col> [ASC|DESC]] [LIMIT <n>]

    condition := or_expr
    or_expr   := and_expr ( OR and_expr )*
    and_expr  := not_expr ( AND not_expr )*
    not_expr  := NOT not_expr | primary
    primary   := '(' or_expr ')' | comparison
    comparison:= operand OP operand
               | operand IS [NOT] NULL
               | operand [NOT] IN '(' value (',' value)* ')'
               | operand [NOT] LIKE string
               | operand [NOT] BETWEEN value AND value

Operator precedence follows SQL / SQLite: NOT > AND > OR, with parentheses
overriding precedence.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

Row = Dict[str, Any]
Predicate = Callable[[Row], bool]


class LQLError(ValueError):
    """Raised for malformed LQL queries."""


# ---------------------------------------------------------------------------
# Condition tokenizer
# ---------------------------------------------------------------------------

_KEYWORDS = {
    "AND", "OR", "NOT", "IN", "LIKE", "IS", "NULL", "BETWEEN", "TRUE", "FALSE",
}

_TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (?P<string>'(?:[^']|'')*'|"(?:[^"]|"")*")
      | (?P<number>[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?)
      | (?P<op><=|>=|<>|!=|==|=|<|>)
      | (?P<lparen>\()
      | (?P<rparen>\))
      | (?P<comma>,)
      | (?P<ident>[A-Za-z_][A-Za-z0-9_\.]*)
    )
    """,
    re.VERBOSE,
)


def _tokenize_condition(text: str) -> List[Tuple[str, Any]]:
    tokens: List[Tuple[str, Any]] = []
    pos = 0
    n = len(text)
    while pos < n:
        if text[pos:].strip() == "":
            break
        m = _TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            raise LQLError("Unexpected character in condition near: %r" % text[pos:pos + 10])
        pos = m.end()
        kind = m.lastgroup
        value = m.group(kind)
        if kind == "string":
            quote = value[0]
            inner = value[1:-1].replace(quote * 2, quote)
            tokens.append(("string", inner))
        elif kind == "number":
            if re.fullmatch(r"[-+]?\d+", value):
                tokens.append(("number", int(value)))
            else:
                tokens.append(("number", float(value)))
        elif kind == "ident":
            upper = value.upper()
            if upper in _KEYWORDS:
                tokens.append(("kw", upper))
            else:
                tokens.append(("ident", value))
        else:
            tokens.append((kind, value))
    return tokens


# ---------------------------------------------------------------------------
# Condition parser (recursive descent -> predicate closures)
# ---------------------------------------------------------------------------

def _like_to_regex(pattern: str) -> "re.Pattern[str]":
    out = []
    for ch in pattern:
        if ch == "%":
            out.append(".*")
        elif ch == "_":
            out.append(".")
        else:
            out.append(re.escape(ch))
    return re.compile("^" + "".join(out) + "$", re.IGNORECASE | re.DOTALL)


def _compare(op: str, left: Any, right: Any) -> bool:
    if left is None or right is None:
        return False
    try:
        if op in ("=", "=="):
            return left == right
        if op in ("!=", "<>"):
            return left != right
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        if op == ">=":
            return left >= right
    except TypeError:
        return False
    raise LQLError("Unknown operator %r" % op)


class _ConditionParser:
    def __init__(self, tokens: List[Tuple[str, Any]]):
        self.tokens = tokens
        self.i = 0

    # -- helpers ----------------------------------------------------------
    def _peek(self) -> Optional[Tuple[str, Any]]:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def _next(self) -> Tuple[str, Any]:
        tok = self._peek()
        if tok is None:
            raise LQLError("Unexpected end of condition")
        self.i += 1
        return tok

    def _accept_kw(self, name: str) -> bool:
        tok = self._peek()
        if tok and tok[0] == "kw" and tok[1] == name:
            self.i += 1
            return True
        return False

    def _expect(self, kind: str) -> Tuple[str, Any]:
        tok = self._next()
        if tok[0] != kind:
            raise LQLError("Expected %s but found %r" % (kind, tok[1]))
        return tok

    # -- grammar ----------------------------------------------------------
    def parse(self) -> Predicate:
        pred = self._or_expr()
        if self._peek() is not None:
            raise LQLError("Unexpected token in condition: %r" % (self._peek()[1],))
        return pred

    def _or_expr(self) -> Predicate:
        parts = [self._and_expr()]
        while self._accept_kw("OR"):
            parts.append(self._and_expr())
        if len(parts) == 1:
            return parts[0]
        return lambda row, _p=tuple(parts): any(p(row) for p in _p)

    def _and_expr(self) -> Predicate:
        parts = [self._not_expr()]
        while self._accept_kw("AND"):
            parts.append(self._not_expr())
        if len(parts) == 1:
            return parts[0]
        return lambda row, _p=tuple(parts): all(p(row) for p in _p)

    def _not_expr(self) -> Predicate:
        if self._accept_kw("NOT"):
            inner = self._not_expr()
            return lambda row, _i=inner: not _i(row)
        return self._primary()

    def _primary(self) -> Predicate:
        tok = self._peek()
        if tok is not None and tok[0] == "lparen":
            self.i += 1
            inner = self._or_expr()
            self._expect("rparen")
            return inner
        return self._comparison()

    def _operand(self) -> Callable[[Row], Any]:
        tok = self._next()
        kind, val = tok
        if kind in ("string", "number"):
            return lambda row, _v=val: _v
        if kind == "kw":
            if val == "NULL":
                return lambda row: None
            if val == "TRUE":
                return lambda row: True
            if val == "FALSE":
                return lambda row: False
            raise LQLError("Unexpected keyword %r in operand position" % val)
        if kind == "ident":
            name = val
            return lambda row, _n=name: row.get(_n)
        raise LQLError("Unexpected token %r in operand position" % (val,))

    def _value_list(self) -> List[Callable[[Row], Any]]:
        self._expect("lparen")
        items = [self._operand()]
        while self._peek() is not None and self._peek()[0] == "comma":
            self.i += 1
            items.append(self._operand())
        self._expect("rparen")
        return items

    def _comparison(self) -> Predicate:
        left = self._operand()
        tok = self._peek()
        if tok is None:
            # bare operand: truthiness
            return lambda row, _l=left: bool(_l(row))

        if tok[0] == "op":
            self.i += 1
            op = tok[1]
            right = self._operand()
            return lambda row, _l=left, _r=right, _o=op: _compare(_o, _l(row), _r(row))

        if tok[0] == "kw":
            if tok[1] == "IS":
                self.i += 1
                negate = self._accept_kw("NOT")
                if not self._accept_kw("NULL"):
                    raise LQLError("Expected NULL after IS")
                if negate:
                    return lambda row, _l=left: _l(row) is not None
                return lambda row, _l=left: _l(row) is None

            negate = False
            if tok[1] == "NOT":
                nxt = self.tokens[self.i + 1] if self.i + 1 < len(self.tokens) else None
                if nxt and nxt[0] == "kw" and nxt[1] in ("IN", "LIKE", "BETWEEN"):
                    self.i += 1
                    negate = True
                    tok = self._peek()
                else:
                    return lambda row, _l=left: bool(_l(row))

            if tok[1] == "IN":
                self.i += 1
                items = self._value_list()

                def in_pred(row, _l=left, _it=items, _n=negate):
                    v = _l(row)
                    if v is None:
                        return False
                    res = any(v == i(row) for i in _it)
                    return (not res) if _n else res

                return in_pred

            if tok[1] == "LIKE":
                self.i += 1
                pat = self._operand()

                def like_pred(row, _l=left, _p=pat, _n=negate):
                    v, p = _l(row), _p(row)
                    if v is None or p is None:
                        return False
                    res = bool(_like_to_regex(str(p)).match(str(v)))
                    return (not res) if _n else res

                return like_pred

            if tok[1] == "BETWEEN":
                self.i += 1
                lo = self._operand()
                if not self._accept_kw("AND"):
                    raise LQLError("Expected AND in BETWEEN expression")
                hi = self._operand()

                def between_pred(row, _l=left, _lo=lo, _hi=hi, _n=negate):
                    v = _l(row)
                    a, b = _lo(row), _hi(row)
                    if v is None or a is None or b is None:
                        return False
                    try:
                        res = a <= v <= b
                    except TypeError:
                        return False
                    return (not res