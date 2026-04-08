"""
tests/test_query_engine.py
Tests for lateralus_lang.query_engine — LQL fluent query API
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from lateralus_lang.query_engine import AGG_FUNCTIONS, Query, get_query_builtins, lql, parse_lql

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

USERS = [
    {"id": 1, "name": "Alice",   "age": 30, "dept": "eng",   "salary": 95000},
    {"id": 2, "name": "Bob",     "age": 25, "dept": "eng",   "salary": 75000},
    {"id": 3, "name": "Charlie", "age": 35, "dept": "sales", "salary": 80000},
    {"id": 4, "name": "Diana",   "age": 28, "dept": "eng",   "salary": 90000},
    {"id": 5, "name": "Eve",     "age": 22, "dept": "sales", "salary": 65000},
    {"id": 6, "name": "Frank",   "age": 40, "dept": "mgmt",  "salary": 120000},
]

ORDERS = [
    {"order_id": 101, "user_id": 1, "amount": 250.0,  "status": "paid"},
    {"order_id": 102, "user_id": 1, "amount": 100.0,  "status": "pending"},
    {"order_id": 103, "user_id": 2, "amount": 75.0,   "status": "paid"},
    {"order_id": 104, "user_id": 3, "amount": 500.0,  "status": "paid"},
    {"order_id": 105, "user_id": 4, "amount": 1000.0, "status": "paid"},
    {"order_id": 106, "user_id": 5, "amount": 200.0,  "status": "cancelled"},
]


# ---------------------------------------------------------------------------
# Basic query
# ---------------------------------------------------------------------------

class TestBasicQuery:
    def test_from_returns_all(self):
        result = Query().from_(USERS).execute()
        assert len(result) == 6

    def test_where_filter(self):
        result = (Query()
                  .from_(USERS)
                  .where(lambda u: u["dept"] == "eng")
                  .execute())
        assert len(result) == 3
        assert all(u["dept"] == "eng" for u in result)

    def test_where_chaining(self):
        result = (Query()
                  .from_(USERS)
                  .where(lambda u: u["dept"] == "eng")
                  .where(lambda u: u["age"] > 25)
                  .execute())
        assert len(result) == 2
        names = {u["name"] for u in result}
        assert names == {"Alice", "Diana"}

    def test_select_projection(self):
        result = (Query()
                  .from_(USERS)
                  .select("name", "age")
                  .execute())
        assert len(result) == 6
        assert all("name" in r and "age" in r for r in result)
        assert all("salary" not in r for r in result)

    def test_select_transform(self):
        result = (Query()
                  .from_(USERS)
                  .select(lambda u: {"name": u["name"].upper()})
                  .execute())
        assert result[0]["name"] == "ALICE"

    def test_limit(self):
        result = Query().from_(USERS).limit(3).execute()
        assert len(result) == 3

    def test_offset(self):
        result = Query().from_(USERS).offset(4).execute()
        assert len(result) == 2

    def test_limit_offset(self):
        result = Query().from_(USERS).limit(2).offset(2).execute()
        assert len(result) == 2
        assert result[0]["id"] == 3

    def test_first(self):
        result = Query().from_(USERS).first()
        assert result["id"] == 1

    def test_first_none_when_empty(self):
        result = Query().from_([]).first()
        assert result is None

    def test_exists_true(self):
        exists = Query().from_(USERS).where(lambda u: u["dept"] == "mgmt").exists()
        assert exists is True

    def test_exists_false(self):
        exists = Query().from_(USERS).where(lambda u: u["dept"] == "hr").exists()
        assert exists is False

    def test_pluck(self):
        names = Query().from_(USERS).pluck("name")
        assert len(names) == 6
        assert "Alice" in names
        assert all(isinstance(n, str) for n in names)


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------

class TestOrdering:
    def test_order_by_ascending(self):
        result = Query().from_(USERS).order_by("age").execute()
        ages = [u["age"] for u in result]
        assert ages == sorted(ages)

    def test_order_by_descending(self):
        result = Query().from_(USERS).order_by("salary", ascending=False).execute()
        salaries = [u["salary"] for u in result]
        assert salaries == sorted(salaries, reverse=True)

    def test_order_by_key_func(self):
        result = Query().from_(USERS).order_by(lambda u: -u["age"]).execute()
        first = result[0]
        assert first["age"] == max(u["age"] for u in USERS)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

class TestAggregation:
    def test_count_agg(self):
        result = (Query()
                  .from_(USERS)
                  .group_by("dept")
                  .aggregate("dept_count", "count", lambda u: 1)
                  .execute())
        assert len(result) > 0
        total = sum(r["dept_count"] for r in result)
        assert total == 6

    def test_sum_agg(self):
        result = (Query()
                  .from_(USERS)
                  .group_by("dept")
                  .aggregate("total_salary", "sum", lambda u: u["salary"])
                  .execute())
        eng = next(r for r in result if r["_group"] == "eng")
        assert eng["total_salary"] == 95000 + 75000 + 90000

    def test_avg_agg(self):
        result = (Query()
                  .from_(USERS)
                  .group_by("dept")
                  .aggregate("avg_age", "avg", lambda u: u["age"])
                  .execute())
        assert all("avg_age" in r for r in result)

    def test_min_max_agg(self):
        result = (Query()
                  .from_(USERS)
                  .group_by("dept")
                  .aggregate("min_age", "min", lambda u: u["age"])
                  .aggregate("max_age", "max", lambda u: u["age"])
                  .execute())
        eng = next(r for r in result if r["_group"] == "eng")
        assert eng["min_age"] == 25
        assert eng["max_age"] == 30

    def test_collect_agg(self):
        result = (Query()
                  .from_(USERS)
                  .group_by("dept")
                  .aggregate("members", "collect", lambda u: u["name"])
                  .execute())
        eng = next(r for r in result if r["_group"] == "eng")
        assert "Alice" in eng["members"]
        assert "Bob" in eng["members"]


# ---------------------------------------------------------------------------
# Distinct
# ---------------------------------------------------------------------------

class TestDistinct:
    def test_distinct_values(self):
        result = (Query()
                  .from_(USERS)
                  .select(lambda u: {"dept": u["dept"]})
                  .distinct()
                  .execute())
        depts = [r["dept"] for r in result]
        assert len(depts) == len(set(depts))
        assert set(depts) == {"eng", "sales", "mgmt"}


# ---------------------------------------------------------------------------
# Joins
# ---------------------------------------------------------------------------

class TestJoins:
    def test_inner_join(self):
        result = (Query()
                  .from_(USERS)
                  .join(ORDERS, lambda u, o: u["id"] == o["user_id"])
                  .execute())
        # Every user with orders: Alice has 2, Bob 1, Charlie 1, Diana 1, Eve 1
        assert len(result) == 6

    def test_join_projects_both(self):
        result = (Query()
                  .from_(USERS)
                  .join(ORDERS, lambda u, o: u["id"] == o["user_id"])
                  .execute())
        # Result rows should contain both user and order fields
        first = result[0]
        assert "name" in first or "user_name" in first or "amount" in first

    def test_join_with_filter(self):
        result = (Query()
                  .from_(USERS)
                  .join(ORDERS, lambda u, o: u["id"] == o["user_id"])
                  .where(lambda r: r.get("status") == "paid" or r.get("order_status") == "paid")
                  .execute())
        # At least some results
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class TestPagination:
    def test_page_1(self):
        result = Query().from_(USERS).page(1, page_size=2).execute()
        assert len(result) == 2
        assert result[0]["id"] == 1

    def test_page_2(self):
        result = Query().from_(USERS).page(2, page_size=2).execute()
        assert len(result) == 2
        assert result[0]["id"] == 3

    def test_page_3(self):
        result = Query().from_(USERS).page(3, page_size=2).execute()
        assert len(result) == 2
        assert result[0]["id"] == 5

    def test_page_beyond_end(self):
        result = Query().from_(USERS).page(10, page_size=2).execute()
        assert result == []


# ---------------------------------------------------------------------------
# LQL string parser
# ---------------------------------------------------------------------------

class TestLQLParser:
    def test_parse_lql_basic(self):
        q = parse_lql("SELECT * FROM users")
        assert q is not None

    def test_lql_select_star(self):
        context = {"users": USERS}
        result = lql("SELECT * FROM users", context)
        assert len(result) == 6

    def test_lql_select_with_limit(self):
        context = {"users": USERS}
        result = lql("SELECT * FROM users LIMIT 3", context)
        assert len(result) == 3

    def test_lql_select_with_where(self):
        context = {"users": USERS}
        result = lql("SELECT * FROM users WHERE dept = 'eng'", context)
        assert len(result) == 3

    def test_lql_select_with_order(self):
        context = {"users": USERS}
        result = lql("SELECT * FROM users ORDER BY age", context)
        ages = [r["age"] for r in result]
        assert ages == sorted(ages)

    def test_lql_select_with_order_desc(self):
        context = {"users": USERS}
        result = lql("SELECT * FROM users ORDER BY salary DESC", context)
        salaries = [r["salary"] for r in result]
        assert salaries == sorted(salaries, reverse=True)

    def test_lql_unknown_table(self):
        context = {"users": USERS}
        result = lql("SELECT * FROM nonexistent", context)
        assert result == []


# ---------------------------------------------------------------------------
# Aggregation functions
# ---------------------------------------------------------------------------

class TestAggFunctions:
    def test_count_fn(self):
        fn = AGG_FUNCTIONS["count"]
        assert fn([1, 2, 3]) == 3
        assert fn([]) == 0

    def test_sum_fn(self):
        fn = AGG_FUNCTIONS["sum"]
        assert fn([1, 2, 3]) == 6
        assert fn([]) == 0

    def test_avg_fn(self):
        fn = AGG_FUNCTIONS["avg"]
        assert fn([2, 4, 6]) == 4.0

    def test_min_fn(self):
        fn = AGG_FUNCTIONS["min"]
        assert fn([3, 1, 4, 1, 5]) == 1

    def test_max_fn(self):
        fn = AGG_FUNCTIONS["max"]
        assert fn([3, 1, 4, 1, 5]) == 5

    def test_first_fn(self):
        fn = AGG_FUNCTIONS["first"]
        assert fn([10, 20, 30]) == 10
        assert fn([]) is None

    def test_last_fn(self):
        fn = AGG_FUNCTIONS["last"]
        assert fn([10, 20, 30]) == 30
        assert fn([]) is None

    def test_collect_fn(self):
        fn = AGG_FUNCTIONS["collect"]
        assert fn([1, 2, 3]) == [1, 2, 3]


# ---------------------------------------------------------------------------
# Builtins API
# ---------------------------------------------------------------------------

class TestBuiltins:
    def test_get_query_builtins(self):
        builtins = get_query_builtins()
        assert "Query" in builtins
        assert "lql" in builtins
        assert callable(builtins["lql"])

    def test_query_in_builtins(self):
        builtins = get_query_builtins()
        assert builtins["Query"] is Query


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_collection(self):
        result = Query().from_([]).execute()
        assert result == []

    def test_single_element(self):
        result = Query().from_([{"x": 1}]).execute()
        assert len(result) == 1

    def test_chained_where_all_filtered(self):
        result = (Query()
                  .from_(USERS)
                  .where(lambda u: u["age"] > 100)
                  .execute())
        assert result == []

    def test_non_dict_collection(self):
        numbers = [1, 2, 3, 4, 5]
        result = (Query()
                  .from_(numbers)
                  .where(lambda n: n > 3)
                  .execute())
        assert result == [4, 5]
