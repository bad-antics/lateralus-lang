"""
lateralus_lang/query_engine.py
LATERALUS Query Language (LQL) — SQL-like query interface over LATERALUS collections.

Exposes a fluent Python API that can be called from the LATERALUS runtime:
    select("name", "age").from_(users).where(lambda r: r["age"] > 18).order_by("name").limit(10)

Also provides a string-based LQL parser so `.ltl` programs can write:
    lql("SELECT name, age FROM users WHERE age > 18 ORDER BY name LIMIT 10")
"""

from __future__ import annotations

import re
import operator
import itertools
from copy import deepcopy
from typing import Any, Callable, Iterable, Iterator, Optional, Union
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
Record = dict[str, Any]
Collection = list[Record]
Predicate = Callable[[Record], bool]
Key = Union[str, Callable[[Record], Any]]


# ---------------------------------------------------------------------------
# Aggregation functions
# ---------------------------------------------------------------------------

def _agg_count(rows: list[Any]) -> int:
    return len(rows)

def _agg_sum(rows: list[Any]) -> Any:
    return sum(rows) if rows else 0

def _agg_avg(rows: list[Any]) -> float:
    return sum(rows) / len(rows) if rows else 0.0

def _agg_min(rows: list[Any]) -> Any:
    return min(rows)

def _agg_max(rows: list[Any]) -> Any:
    return max(rows)

def _agg_first(rows: list[Any]) -> Any:
    return rows[0] if rows else None

def _agg_last(rows: list[Any]) -> Any:
    return rows[-1] if rows else None

def _agg_collect(rows: list[Any]) -> list[Any]:
    return rows

AGG_FUNCTIONS: dict[str, Callable] = {
    "count": _agg_count,
    "sum":   _agg_sum,
    "avg":   _agg_avg,
    "mean":  _agg_avg,
    "min":   _agg_min,
    "max":   _agg_max,
    "first": _agg_first,
    "last":  _agg_last,
    "collect": _agg_collect,
}


# ---------------------------------------------------------------------------
# Join helpers
# ---------------------------------------------------------------------------

@dataclass
class JoinClause:
    right: Collection
    on_left: str
    on_right: str
    kind: str = "inner"  # inner | left | right | cross


@dataclass
class LambdaJoinClause:
    right: Collection
    condition: Callable[[Record, Record], bool]
    kind: str = "inner"


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------

class Query:
    """
    Fluent LQL query builder.

    Usage:
        result = (Query()
            .from_(records)
            .where(lambda r: r["score"] >= 90)
            .select("name", "score")
            .order_by("score", descending=True)
            .limit(5)
            .execute())
    """

    def __init__(self) -> None:
        self._source: Collection = []
        self._columns: list = []          # [] means all
        self._predicates: list[Predicate] = []
        self._joins: list[JoinClause] = []
        self._group_by_keys: list[str] = []
        self._aggregations: dict[str, tuple[str, str]] = {}  # alias -> (fn, field)
        self._having: list[Predicate] = []
        self._order_keys: list[tuple[str, bool]] = []        # (key, descending)
        self._limit_val: Optional[int] = None
        self._offset_val: int = 0
        self._distinct: bool = False
        self._transforms: list[Callable[[Collection], Collection]] = []

    # -- Source --------------------------------------------------------------

    def from_(self, source: Iterable[Any]) -> "Query":
        """Set the data source."""
        self._source = list(source)
        return self

    # -- Column selection ----------------------------------------------------

    def select(self, *columns) -> "Query":
        """Select specific columns (strings) or transform functions (callables)."""
        self._columns = list(columns)
        return self

    def select_all(self) -> "Query":
        self._columns = []
        return self

    def add_column(self, alias: str, expr: Callable[[Record], Any]) -> "Query":
        """Add a computed column."""
        self._transforms.append(
            lambda rows, a=alias, e=expr: [{**r, a: e(r)} for r in rows]
        )
        return self

    # -- Filtering -----------------------------------------------------------

    def where(self, predicate: Union[Predicate, str]) -> "Query":
        """Add a WHERE filter."""
        if isinstance(predicate, str):
            predicate = _parse_condition(predicate)
        self._predicates.append(predicate)
        return self

    def filter(self, predicate: Predicate) -> "Query":
        """Alias for where()."""
        return self.where(predicate)

    def where_not(self, predicate: Predicate) -> "Query":
        self._predicates.append(lambda r: not predicate(r))
        return self

    # -- Joins ---------------------------------------------------------------

    def join(self, right: Collection, condition_or_on_left, on_right: str = "",
             kind: str = "inner") -> "Query":
        """Add a join. Second arg can be a lambda(l, r)->bool or a field name string."""
        if callable(condition_or_on_left):
            self._joins.append(LambdaJoinClause(right, condition_or_on_left, kind))
        else:
            self._joins.append(JoinClause(right, condition_or_on_left, on_right, kind))
        return self

    def left_join(self, right: Collection, on_left: str, on_right: str) -> "Query":
        return self.join(right, on_left, on_right, "left")

    def cross_join(self, right: Collection) -> "Query":
        return self.join(right, "", "", "cross")

    # -- Grouping & aggregation ----------------------------------------------

    def group_by(self, *keys: str) -> "Query":
        """Group results by one or more keys."""
        self._group_by_keys = list(keys)
        return self

    def aggregate(self, alias: str, fn: str, field: str = "*") -> "Query":
        """
        Add an aggregation.
        e.g. .aggregate("total", "sum", "price")
             .aggregate("count", "count", "*")
        """
        self._aggregations[alias] = (fn.lower(), field)
        return self

    def having(self, predicate: Predicate) -> "Query":
        """Filter after grouping."""
        self._having.append(predicate)
        return self

    def count_as(self, alias: str = "count") -> "Query":
        return self.aggregate(alias, "count", "*")

    def sum_as(self, field: str, alias: Optional[str] = None) -> "Query":
        return self.aggregate(alias or f"sum_{field}", "sum", field)

    def avg_as(self, field: str, alias: Optional[str] = None) -> "Query":
        return self.aggregate(alias or f"avg_{field}", "avg", field)

    # -- Ordering ------------------------------------------------------------

    def order_by(self, key, descending: bool = False,
                 ascending: Optional[bool] = None) -> "Query":
        """Sort results. key can be a field name string or a callable."""
        if ascending is not None:
            descending = not ascending
        self._order_keys.append((key, descending))
        return self

    def order_by_desc(self, key: str) -> "Query":
        return self.order_by(key, descending=True)

    # -- Pagination ----------------------------------------------------------

    def limit(self, n: int) -> "Query":
        self._limit_val = n
        return self

    def offset(self, n: int) -> "Query":
        self._offset_val = n
        return self

    def page(self, page_num: int, page_size: int) -> "Query":
        """Convenience: paginate by page number (1-indexed)."""
        self._offset_val = (page_num - 1) * page_size
        self._limit_val = page_size
        return self

    def distinct(self) -> "Query":
        self._distinct = True
        return self

    # -- Execution -----------------------------------------------------------

    def execute(self) -> Collection:
        """Run the query and return results."""
        rows: Collection = list(self._source)

        # Apply joins
        for join in self._joins:
            rows = _apply_join(rows, join)

        # Apply custom transforms (computed columns)
        for transform in self._transforms:
            rows = transform(rows)

        # Apply WHERE predicates
        for pred in self._predicates:
            rows = [r for r in rows if pred(r)]

        # Apply GROUP BY + aggregations
        if self._group_by_keys or self._aggregations:
            rows = self._apply_group(rows)

        # Apply HAVING
        for pred in self._having:
            rows = [r for r in rows if pred(r)]

        # Apply callable column transforms before DISTINCT (so distinct works on projected values)
        callable_columns = [col for col in self._columns if callable(col)]
        if callable_columns:
            projected = []
            for r in rows:
                out: Record = {}
                for col in self._columns:
                    if callable(col):
                        result = col(r)
                        if isinstance(result, dict):
                            out.update(result)
                        else:
                            out["_value"] = result
                    else:
                        out[col] = _get_field(r, col)
                projected.append(out)
            rows = projected

        # Apply DISTINCT
        if self._distinct:
            seen: list = []
            unique = []
            for r in rows:
                if isinstance(r, dict):
                    key = tuple(sorted(r.items()))
                else:
                    key = r
                if key not in seen:
                    seen.append(key)
                    unique.append(r)
            rows = unique

        # Apply ORDER BY
        for key, desc in reversed(self._order_keys):
            if callable(key):
                rows = sorted(rows, key=key, reverse=desc)
            else:
                rows = sorted(rows, key=lambda r, k=key: _get_field(r, k), reverse=desc)

        # Apply OFFSET
        if self._offset_val:
            rows = rows[self._offset_val:]

        # Apply LIMIT
        if self._limit_val is not None:
            rows = rows[:self._limit_val]

        # Apply string-only column projection (callable columns already handled above)
        if self._columns and not callable_columns:
            rows = [_project(r, self._columns) for r in rows]

        return rows

    def first(self) -> Optional[Record]:
        results = self.limit(1).execute()
        return results[0] if results else None

    def one_or_none(self) -> Optional[Record]:
        results = self.execute()
        if len(results) == 0:
            return None
        if len(results) > 1:
            raise QueryError(f"Expected at most 1 result, got {len(results)}")
        return results[0]

    def count(self) -> int:
        return len(self.execute())

    def pluck(self, field: str) -> list[Any]:
        """Return a flat list of values for a single field."""
        return [r.get(field) for r in self.execute()]

    def exists(self) -> bool:
        return self.first() is not None

    def __iter__(self) -> Iterator[Record]:
        return iter(self.execute())

    def __len__(self) -> int:
        return self.count()

    def _apply_group(self, rows: Collection) -> Collection:
        """Apply GROUP BY + aggregations."""
        if not self._group_by_keys:
            # Global aggregation (no group keys)
            group: dict[tuple, list] = {(): rows}
        else:
            group = {}
            for r in rows:
                key = tuple(r.get(k) for k in self._group_by_keys)
                group.setdefault(key, []).append(r)

        result = []
        for key_vals, group_rows in group.items():
            out: Record = {}
            # Restore group key fields
            for k, v in zip(self._group_by_keys, key_vals):
                out[k] = v
            # Add _group convenience key for easy access
            if len(self._group_by_keys) == 1:
                out["_group"] = key_vals[0]
            elif len(self._group_by_keys) > 1:
                out["_group"] = key_vals
            # Apply aggregations
            for alias, (fn_name, field) in self._aggregations.items():
                fn = AGG_FUNCTIONS.get(fn_name)
                if fn is None:
                    raise QueryError(f"Unknown aggregation function: {fn_name!r}")
                if field == "*":
                    vals = list(range(len(group_rows)))
                elif callable(field):
                    vals = [field(r) for r in group_rows]
                else:
                    vals = [r.get(field) for r in group_rows if r.get(field) is not None]
                out[alias] = fn(vals)
            result.append(out)
        return result


# ---------------------------------------------------------------------------
# Join execution
# ---------------------------------------------------------------------------

def _apply_join(left: Collection, clause) -> Collection:
    if isinstance(clause, LambdaJoinClause):
        result = []
        for l in left:
            for r in clause.right:
                if clause.condition(l, r):
                    result.append({**l, **r})
        return result
    right = clause.right
    kind = clause.kind

    if kind == "cross":
        return [{**l, **r} for l in left for r in right]

    right_idx: dict[Any, list[Record]] = {}
    for r in right:
        k = r.get(clause.on_right)
        right_idx.setdefault(k, []).append(r)

    result = []
    matched_right: set[int] = set()

    for l in left:
        lk = l.get(clause.on_left)
        matches = right_idx.get(lk, [])
        if matches:
            for r in matches:
                result.append({**l, **r})
                matched_right.add(id(r))
        elif kind == "left":
            # Left join: keep left row with nulls for right
            result.append({**l, **{k: None for k in (right[0].keys() if right else [])}})

    if kind == "right":
        # Add unmatched right rows
        for r in right:
            if id(r) not in matched_right:
                result.append({**{k: None for k in (left[0].keys() if left else [])}, **r})

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_field(record: Record, key: str) -> Any:
    """Get a field value, supporting nested dot notation."""
    parts = key.split(".")
    val: Any = record
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        else:
            val = getattr(val, p, None)
    return val


def _project(record: Record, columns: list[str]) -> Record:
    """Project a record to selected columns."""
    return {col: _get_field(record, col) for col in columns}


# ---------------------------------------------------------------------------
# Simple expression parser (for string-based WHERE clauses)
# ---------------------------------------------------------------------------

_COMPARE_OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    "<=": operator.le,
    ">":  operator.gt,
    "<":  operator.lt,
}


def _parse_condition(expr: str) -> Predicate:
    """
    Parse a simple condition string into a predicate function.
    Supports: field op value, AND, OR, NOT, parentheses.
    Examples:
        "age > 18"
        "status == 'active' AND score >= 90"
        "NOT archived"
    """
    expr = expr.strip()

    # Try AND / OR splitting (simple, not nested)
    if " AND " in expr.upper():
        parts = re.split(r'\bAND\b', expr, flags=re.IGNORECASE)
        preds = [_parse_condition(p) for p in parts]
        return lambda r, ps=preds: all(p(r) for p in ps)

    if " OR " in expr.upper():
        parts = re.split(r'\bOR\b', expr, flags=re.IGNORECASE)
        preds = [_parse_condition(p) for p in parts]
        return lambda r, ps=preds: any(p(r) for p in ps)

    if expr.upper().startswith("NOT "):
        inner = _parse_condition(expr[4:])
        return lambda r, p=inner: not p(r)

    # Try comparison
    for op_str, op_fn in sorted(_COMPARE_OPS.items(), key=lambda x: -len(x[0])):
        if op_str in expr:
            lhs, rhs = expr.split(op_str, 1)
            lhs = lhs.strip()
            rhs = rhs.strip()
            rhs_val = _parse_literal(rhs)
            return lambda r, l=lhs, o=op_fn, rv=rhs_val: o(_get_field(r, l), rv)

    # IN operator
    m = re.match(r'(\w+)\s+IN\s+\((.+)\)', expr, re.IGNORECASE)
    if m:
        field_name = m.group(1)
        vals = [_parse_literal(v.strip()) for v in m.group(2).split(",")]
        return lambda r, f=field_name, vs=vals: _get_field(r, f) in vs

    # IS NULL / IS NOT NULL
    m = re.match(r'(\w+)\s+IS\s+NOT\s+NULL', expr, re.IGNORECASE)
    if m:
        f = m.group(1)
        return lambda r, fn=f: _get_field(r, fn) is not None

    m = re.match(r'(\w+)\s+IS\s+NULL', expr, re.IGNORECASE)
    if m:
        f = m.group(1)
        return lambda r, fn=f: _get_field(r, fn) is None

    # LIKE (simple glob-style)
    m = re.match(r'(\w+)\s+LIKE\s+[\'"](.+)[\'"]', expr, re.IGNORECASE)
    if m:
        f = m.group(1)
        pattern = m.group(2).replace("%", ".*").replace("_", ".")
        regex = re.compile(f"^{pattern}$", re.IGNORECASE)
        return lambda r, fn=f, rx=regex: bool(rx.match(str(_get_field(r, fn) or "")))

    # Truthy field reference
    return lambda r, fn=expr: bool(_get_field(r, fn))


def _parse_literal(s: str) -> Any:
    """Parse a literal value from a string."""
    s = s.strip()
    if s.lower() == "null" or s.lower() == "none":
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


# ---------------------------------------------------------------------------
# LQL string parser — parses "SELECT ... FROM ... WHERE ... ORDER BY ... LIMIT ..."
# ---------------------------------------------------------------------------

@dataclass
class LQLStatement:
    columns: list[str]
    source_name: str
    where_clause: Optional[str] = None
    group_by: list[str] = field(default_factory=list)
    order_by: list[tuple[str, bool]] = field(default_factory=list)
    limit: Optional[int] = None
    offset: int = 0
    distinct: bool = False


def parse_lql(lql_string: str) -> LQLStatement:
    """
    Parse a LQL query string into a structured statement.

    Syntax:
        SELECT [DISTINCT] col1, col2, ...
        FROM   source_name
        WHERE  condition
        GROUP BY col1, col2
        ORDER BY col1 [DESC], col2 [ASC]
        LIMIT  n
        OFFSET n
    """
    s = lql_string.strip()

    # Extract LIMIT
    limit = None
    m = re.search(r'\bLIMIT\s+(\d+)', s, re.IGNORECASE)
    if m:
        limit = int(m.group(1))
        s = s[:m.start()] + s[m.end():]

    # Extract OFFSET
    offset = 0
    m = re.search(r'\bOFFSET\s+(\d+)', s, re.IGNORECASE)
    if m:
        offset = int(m.group(1))
        s = s[:m.start()] + s[m.end():]

    # Extract ORDER BY
    order_by: list[tuple[str, bool]] = []
    m = re.search(r'\bORDER\s+BY\s+(.+?)(?=\bWHERE\b|\bGROUP\b|\bHAVING\b|$)', s, re.IGNORECASE)
    if m:
        for part in m.group(1).split(","):
            part = part.strip()
            desc = part.upper().endswith(" DESC")
            key = re.sub(r'\s+(ASC|DESC)$', '', part, flags=re.IGNORECASE).strip()
            order_by.append((key, desc))
        s = s[:m.start()] + s[m.end():]

    # Extract GROUP BY
    group_by: list[str] = []
    m = re.search(r'\bGROUP\s+BY\s+(.+?)(?=\bWHERE\b|\bHAVING\b|$)', s, re.IGNORECASE)
    if m:
        group_by = [k.strip() for k in m.group(1).split(",")]
        s = s[:m.start()] + s[m.end():]

    # Extract WHERE
    where_clause = None
    m = re.search(r'\bWHERE\s+(.+?)(?=\bGROUP\b|\bORDER\b|\bHAVING\b|$)', s, re.IGNORECASE)
    if m:
        where_clause = m.group(1).strip()
        s = s[:m.start()] + s[m.end():]

    # Extract FROM
    source_name = ""
    m = re.search(r'\bFROM\s+(\w+)', s, re.IGNORECASE)
    if m:
        source_name = m.group(1)
        s = s[:m.start()] + s[m.end():]

    # Extract SELECT [DISTINCT] columns
    distinct = False
    m = re.match(r'\s*SELECT\s+', s, re.IGNORECASE)
    if m:
        s = s[m.end():]
    if s.upper().startswith("DISTINCT "):
        distinct = True
        s = s[9:]
    columns_str = s.strip()
    if columns_str == "*":
        columns: list[str] = []
    else:
        columns = [c.strip() for c in columns_str.split(",")]

    return LQLStatement(
        columns=columns,
        source_name=source_name,
        where_clause=where_clause,
        group_by=group_by,
        order_by=order_by,
        limit=limit,
        offset=offset,
        distinct=distinct,
    )


def lql(query_string: str, context: Optional[dict[str, Collection]] = None) -> Collection:
    """
    Execute a LQL query string against a context of named collections.

    Example:
        users = [{"name": "alice", "age": 30}, {"name": "bob", "age": 17}]
        result = lql("SELECT name FROM users WHERE age >= 18", {"users": users})
    """
    stmt = parse_lql(query_string)
    ctx = context or {}

    source = ctx.get(stmt.source_name, [])

    q = Query().from_(source)

    if stmt.where_clause:
        # Normalize SQL-style single = to == for equality comparisons
        normalized = re.sub(r'(?<![!<>=])=(?!=)', '==', stmt.where_clause)
        q = q.where(normalized)

    if stmt.group_by:
        q = q.group_by(*stmt.group_by)

    for col in (stmt.columns or []):
        # Detect aggregations like "COUNT(*) AS total"
        m = re.match(r'(\w+)\((\w+|\*)\)\s+AS\s+(\w+)', col, re.IGNORECASE)
        if m:
            fn, field, alias = m.group(1), m.group(2), m.group(3)
            q = q.aggregate(alias, fn, field)

    for key, desc in stmt.order_by:
        q = q.order_by(key, descending=desc)

    if stmt.distinct:
        q = q.distinct()

    if stmt.offset:
        q = q.offset(stmt.offset)

    if stmt.limit is not None:
        q = q.limit(stmt.limit)

    if stmt.columns and stmt.columns != ["*"]:
        plain_cols = [c for c in stmt.columns if not re.search(r'\(', c)]
        if plain_cols:
            q = q.select(*plain_cols)

    return q.execute()


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def select(*columns: str) -> Query:
    """Start a fluent query with column selection."""
    return Query().select(*columns)


def from_(source: Iterable[Any]) -> Query:
    """Start a fluent query from a data source."""
    return Query().from_(source)


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class QueryError(Exception):
    """Raised when a LQL query cannot be executed."""


# ---------------------------------------------------------------------------
# LATERALUS runtime builtins — these get injected by engines.py
# ---------------------------------------------------------------------------

def get_query_builtins() -> dict:
    """Return builtins for the LATERALUS runtime."""
    return {
        "lql":     lql,
        "select":  select,
        "from_":   from_,
        "Query":   Query,
        "QueryError": QueryError,
    }
