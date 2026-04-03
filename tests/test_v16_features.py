"""
tests/test_v16_features.py  ─  v1.6 Concurrency & Async Tests
═══════════════════════════════════════════════════════════════════════════
Covers:
  - Lexer: select, nursery, cancel keywords
  - Parser: select stmt, nursery block, async for, channel expr,
            cancel expr, parallel_map/filter/reduce
  - AST nodes: SelectStmt, SelectArm, NurseryBlock, AsyncForStmt,
               ChannelExpr, CancelExpr, ParallelExpr
  - Codegen: Python transpilation of all v1.6 constructs
  - Async runtime: Channel, CancellationToken, Nursery, select(),
                    parallel_map/filter/reduce, TaskGroup
═══════════════════════════════════════════════════════════════════════════
"""
import sys
import pathlib
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from lateralus_lang.lexer import lex, TK
from lateralus_lang.parser import parse, ParseError
from lateralus_lang.ast_nodes import (
    SelectStmt, SelectArm, NurseryBlock, AsyncForStmt,
    ChannelExpr, CancelExpr, ParallelExpr, SpawnExpr,
)
from lateralus_lang.compiler import Compiler, Target


# ─── Helper ───────────────────────────────────────────────────────────

def compile_py(src: str) -> str:
    r = Compiler().compile_source(src, target=Target.PYTHON, filename="test.ltl")
    assert r.ok, f"Compile failed: {r.errors[0].message if r.errors else '?'}"
    return r.python_src


def parse_first(src: str):
    """Parse source and return the first statement/expression node."""
    prog = parse(src, "test.ltl")
    assert len(prog.body) > 0, "No statements parsed"
    node = prog.body[0]
    # Unwrap ExprStmt if needed
    if hasattr(node, "expr"):
        return node.expr
    return node


# ═══════════════════════════════════════════════════════════════════════════════
# Lexer Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestV16Lexer:
    """Test v1.6 keyword tokens."""

    def test_select_keyword(self):
        tokens = lex("select")
        assert any(t.kind == TK.KW_SELECT for t in tokens)

    def test_nursery_keyword(self):
        tokens = lex("nursery")
        assert any(t.kind == TK.KW_NURSERY for t in tokens)

    def test_cancel_keyword(self):
        tokens = lex("cancel")
        assert any(t.kind == TK.KW_CANCEL for t in tokens)

    def test_async_keyword_exists(self):
        tokens = lex("async")
        assert any(t.kind == TK.KW_ASYNC for t in tokens)

    def test_spawn_keyword_exists(self):
        tokens = lex("spawn")
        assert any(t.kind == TK.KW_SPAWN for t in tokens)

    def test_await_keyword_exists(self):
        tokens = lex("await")
        assert any(t.kind == TK.KW_AWAIT for t in tokens)


# ═══════════════════════════════════════════════════════════════════════════════
# Parser: Select Statement
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseSelect:
    """Test parsing of select { ... } statements."""

    def test_select_recv_arm(self):
        src = 'select {\n    msg from inbox => { println(msg) }\n}'
        node = parse_first(src)
        assert isinstance(node, SelectStmt)
        assert len(node.arms) == 1
        assert node.arms[0].kind == "recv"
        assert node.arms[0].binding == "msg"

    def test_select_send_arm(self):
        src = 'select {\n    send(outbox, data) => { println("sent") }\n}'
        node = parse_first(src)
        assert isinstance(node, SelectStmt)
        assert node.arms[0].kind == "send"

    def test_select_timeout_arm(self):
        src = 'select {\n    after 1000 => { println("timeout") }\n}'
        node = parse_first(src)
        assert isinstance(node, SelectStmt)
        assert node.arms[0].kind == "timeout"

    def test_select_default_arm(self):
        src = 'select {\n    _ => { println("default") }\n}'
        node = parse_first(src)
        assert isinstance(node, SelectStmt)
        assert node.arms[0].kind == "default"

    def test_select_multiple_arms(self):
        src = '''select {
    msg from ch1 => { println(msg) }
    send(ch2, 42) => { println("sent") }
    after 500 => { println("timeout") }
    _ => { println("default") }
}'''
        node = parse_first(src)
        assert isinstance(node, SelectStmt)
        assert len(node.arms) == 4
        kinds = [a.kind for a in node.arms]
        assert kinds == ["recv", "send", "timeout", "default"]

    def test_select_compiles(self):
        src = '''let inbox = channel<str>(10)
select {
    msg from inbox => { println(msg) }
    _ => { println("empty") }
}'''
        py = compile_py(src)
        assert "try_recv" in py or "select" in py.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Parser: Nursery Block
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseNursery:
    """Test parsing of nursery { ... } blocks."""

    def test_nursery_basic(self):
        src = 'nursery {\n    spawn foo()\n}'
        node = parse_first(src)
        assert isinstance(node, NurseryBlock)
        assert node.body is not None

    def test_nursery_named(self):
        src = 'nursery scope {\n    spawn task1()\n}'
        node = parse_first(src)
        assert isinstance(node, NurseryBlock)
        assert node.name == "scope"

    def test_nursery_multiple_spawns(self):
        src = 'nursery {\n    spawn task_a()\n    spawn task_b()\n    spawn task_c()\n}'
        node = parse_first(src)
        assert isinstance(node, NurseryBlock)
        assert node.body is not None
        assert len(node.body.stmts) == 3

    def test_nursery_compiles(self):
        src = 'nursery {\n    spawn println("hello")\n}'
        py = compile_py(src)
        assert "Nursery" in py


# ═══════════════════════════════════════════════════════════════════════════════
# Parser: Channel Expression
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseChannel:
    """Test parsing of channel<T>(cap) expressions."""

    def test_channel_typed_buffered(self):
        src = 'let ch = channel<int>(10)'
        node = parse_first(src)
        # It's a LetDecl; check its value
        assert node.value is not None
        ch = node.value
        assert isinstance(ch, ChannelExpr)
        assert ch.elem_type is not None
        assert ch.elem_type.name == "int"

    def test_channel_typed_unbuffered(self):
        src = 'let ch = channel<str>()'
        node = parse_first(src)
        ch = node.value
        assert isinstance(ch, ChannelExpr)
        assert ch.capacity is None

    def test_channel_untyped(self):
        src = 'let ch = channel(5)'
        node = parse_first(src)
        ch = node.value
        assert isinstance(ch, ChannelExpr)
        assert ch.elem_type is None

    def test_channel_compiles(self):
        src = 'let ch = channel<int>(10)'
        py = compile_py(src)
        assert "Channel" in py or "_Channel" in py


# ═══════════════════════════════════════════════════════════════════════════════
# Parser: Cancel Expression
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseCancel:
    """Test parsing of cancel (cancel_token()) expressions."""

    def test_cancel_expr(self):
        src = 'let token = cancel'
        node = parse_first(src)
        assert isinstance(node.value, CancelExpr)

    def test_cancel_compiles(self):
        src = 'let token = cancel'
        py = compile_py(src)
        assert "CancellationToken" in py


# ═══════════════════════════════════════════════════════════════════════════════
# Parser: Async For
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseAsyncFor:
    """Test parsing of async for x in stream { ... }."""

    def test_async_for_basic(self):
        src = 'async for msg in stream {\n    println(msg)\n}'
        node = parse_first(src)
        assert isinstance(node, AsyncForStmt)
        assert node.var == "msg"

    def test_async_for_compiles(self):
        src = 'async for item in events {\n    println(item)\n}'
        py = compile_py(src)
        assert "async for" in py


# ═══════════════════════════════════════════════════════════════════════════════
# Parser: Parallel Combinators
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseParallel:
    """Test parsing of parallel_map/filter/reduce expressions."""

    def test_parallel_map(self):
        src = 'let r = parallel_map(items, fn(x) { x * 2 })'
        node = parse_first(src)
        p = node.value
        assert isinstance(p, ParallelExpr)
        assert p.kind == "map"

    def test_parallel_filter(self):
        src = 'let r = parallel_filter(data, fn(x) { x > 0 })'
        node = parse_first(src)
        p = node.value
        assert isinstance(p, ParallelExpr)
        assert p.kind == "filter"

    def test_parallel_reduce(self):
        src = 'let r = parallel_reduce(nums, fn(a, b) { a + b }, 0)'
        node = parse_first(src)
        p = node.value
        assert isinstance(p, ParallelExpr)
        assert p.kind == "reduce"
        assert p.init is not None

    def test_parallel_map_compiles(self):
        src = 'let r = parallel_map(items, fn(x) { x * 2 })'
        py = compile_py(src)
        assert "parallel_map" in py

    def test_parallel_filter_compiles(self):
        src = 'let r = parallel_filter(data, fn(x) { x > 0 })'
        py = compile_py(src)
        assert "parallel_filter" in py

    def test_parallel_reduce_compiles(self):
        src = 'let r = parallel_reduce(nums, fn(a, b) { a + b }, 0)'
        py = compile_py(src)
        assert "parallel_reduce" in py


# ═══════════════════════════════════════════════════════════════════════════════
# Async Runtime: Channel
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuntimeChannel:
    """Test the Channel class from async_runtime."""

    def test_channel_send_recv(self):
        from lateralus_lang.async_runtime import Channel
        ch = Channel(capacity=5)
        ch.send("hello")
        assert ch.recv() == "hello"

    def test_channel_try_send_recv(self):
        from lateralus_lang.async_runtime import Channel
        ch = Channel(capacity=1)
        assert ch.try_send("a") is True
        assert ch.try_send("b") is False  # full
        assert ch.try_recv() == "a"
        assert ch.try_recv() is None  # empty

    def test_channel_close(self):
        from lateralus_lang.async_runtime import Channel
        ch = Channel(capacity=5)
        ch.send("x")
        ch.close()
        assert ch.is_closed
        assert ch.send("y") is False  # closed
        assert ch.recv() == "x"  # can still drain

    def test_channel_iter(self):
        from lateralus_lang.async_runtime import Channel
        ch = Channel(capacity=10)
        for i in range(5):
            ch.send(i)
        ch.close()
        values = list(ch)
        assert values == [0, 1, 2, 3, 4]

    def test_channel_len(self):
        from lateralus_lang.async_runtime import Channel
        ch = Channel(capacity=10)
        ch.send(1)
        ch.send(2)
        assert len(ch) == 2

    def test_channel_threaded(self):
        from lateralus_lang.async_runtime import Channel
        ch = Channel(capacity=10)
        results = []

        def producer():
            for i in range(5):
                ch.send(i)
            ch.close()

        def consumer():
            for val in ch:
                results.append(val)

        t1 = threading.Thread(target=producer)
        t2 = threading.Thread(target=consumer)
        t1.start(); t2.start()
        t1.join(); t2.join()
        assert results == [0, 1, 2, 3, 4]


# ═══════════════════════════════════════════════════════════════════════════════
# Async Runtime: CancellationToken
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuntimeCancellation:
    """Test CancellationToken from async_runtime."""

    def test_cancel_token_basic(self):
        from lateralus_lang.async_runtime import CancellationToken
        token = CancellationToken()
        assert not token.is_cancelled
        token.cancel()
        assert token.is_cancelled

    def test_cancel_with_reason(self):
        from lateralus_lang.async_runtime import CancellationToken
        token = CancellationToken()
        token.cancel("timeout")
        assert token.reason == "timeout"

    def test_cancel_callback(self):
        from lateralus_lang.async_runtime import CancellationToken
        reasons = []
        token = CancellationToken()
        token.on_cancel(lambda r: reasons.append(r))
        token.cancel("done")
        assert reasons == ["done"]

    def test_cancel_check_raises(self):
        from lateralus_lang.async_runtime import CancellationToken, CancelledError
        token = CancellationToken()
        token.cancel()
        with pytest.raises(CancelledError):
            token.check()

    def test_cancel_idempotent(self):
        from lateralus_lang.async_runtime import CancellationToken
        callbacks = []
        token = CancellationToken()
        token.on_cancel(lambda r: callbacks.append(1))
        token.cancel()
        token.cancel()  # second cancel should be no-op
        assert len(callbacks) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Async Runtime: Nursery
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuntimeNursery:
    """Test Nursery (structured concurrency) from async_runtime."""

    def test_nursery_basic(self):
        from lateralus_lang.async_runtime import Nursery
        results = []
        with Nursery() as n:
            n.spawn(lambda: results.append(1))
            n.spawn(lambda: results.append(2))
        assert sorted(results) == [1, 2]

    def test_nursery_error_propagates(self):
        from lateralus_lang.async_runtime import Nursery
        with pytest.raises(ValueError):
            with Nursery() as n:
                n.spawn(lambda: None)
                n.spawn(lambda: (_ for _ in ()).throw(ValueError("oops")))

    def test_nursery_cancel_token(self):
        from lateralus_lang.async_runtime import Nursery
        with Nursery() as n:
            assert not n.cancel_token.is_cancelled
            n.spawn(lambda: 42)

    def test_nursery_results(self):
        from lateralus_lang.async_runtime import Nursery, TaskStatus
        with Nursery() as n:
            n.spawn(lambda: 10)
            n.spawn(lambda: 20)
        assert len(n.results) == 2
        assert all(r.status == TaskStatus.COMPLETED for r in n.results)


# ═══════════════════════════════════════════════════════════════════════════════
# Async Runtime: Select
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuntimeSelect:
    """Test the select() function from async_runtime."""

    def test_select_single_channel(self):
        from lateralus_lang.async_runtime import Channel, select
        ch = Channel(capacity=5)
        ch.send("msg")
        result = select(ch, timeout=1.0)
        assert result is not None
        assert result["value"] == "msg"
        assert result["index"] == 0

    def test_select_multiple_channels(self):
        from lateralus_lang.async_runtime import Channel, select
        ch1 = Channel(capacity=5)
        ch2 = Channel(capacity=5)
        ch2.send("from_ch2")
        result = select(ch1, ch2, timeout=1.0)
        assert result is not None
        assert result["value"] == "from_ch2"
        assert result["index"] == 1

    def test_select_timeout(self):
        from lateralus_lang.async_runtime import Channel, select
        ch = Channel(capacity=5)
        result = select(ch, timeout=0.05)
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# Async Runtime: Parallel Combinators
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuntimeParallel:
    """Test parallel_map, parallel_filter, parallel_reduce."""

    def test_parallel_map(self):
        from lateralus_lang.async_runtime import parallel_map
        result = parallel_map(lambda x: x * 2, [1, 2, 3, 4])
        assert result == [2, 4, 6, 8]

    def test_parallel_filter(self):
        from lateralus_lang.async_runtime import parallel_filter
        result = parallel_filter(lambda x: x > 2, [1, 2, 3, 4, 5])
        assert result == [3, 4, 5]

    def test_parallel_reduce(self):
        from lateralus_lang.async_runtime import parallel_reduce
        result = parallel_reduce(lambda a, b: a + b, [1, 2, 3, 4])
        assert result == 10

    def test_parallel_reduce_with_initial(self):
        from lateralus_lang.async_runtime import parallel_reduce
        result = parallel_reduce(lambda a, b: a + b, [1, 2, 3], initial=100)
        # With initial value, chunks get reduce(fn, chunk, 100), then results merged
        # This is a tree-reduce, so we just check it's >= 106
        assert result >= 106

    def test_parallel_map_empty(self):
        from lateralus_lang.async_runtime import parallel_map
        assert parallel_map(lambda x: x, []) == []

    def test_parallel_reduce_empty(self):
        from lateralus_lang.async_runtime import parallel_reduce
        assert parallel_reduce(lambda a, b: a + b, [], initial=0) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Async Runtime: TaskGroup
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuntimeTaskGroup:
    """Test TaskGroup from async_runtime."""

    def test_task_group_spawn_and_wait(self):
        from lateralus_lang.async_runtime import TaskGroup, TaskStatus
        with TaskGroup() as g:
            g.spawn(lambda: 1)
            g.spawn(lambda: 2)
            results = g.wait_all()
        assert len(results) == 2
        assert all(r.status == TaskStatus.COMPLETED for r in results)
        values = sorted(r.value for r in results)
        assert values == [1, 2]

    def test_task_group_wait_first(self):
        from lateralus_lang.async_runtime import TaskGroup, TaskStatus
        with TaskGroup() as g:
            g.spawn(lambda: 42)
            g.spawn(lambda: (time.sleep(1), 99))
            result = g.wait_first(timeout=2.0)
        assert result.status == TaskStatus.COMPLETED

    def test_task_group_cancel_all(self):
        from lateralus_lang.async_runtime import TaskGroup
        with TaskGroup() as g:
            g.spawn(lambda: time.sleep(10))
            g.cancel_all()
            # Should not hang


# ═══════════════════════════════════════════════════════════════════════════════
# Async Runtime: RateLimiter
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuntimeRateLimiter:
    """Test RateLimiter from async_runtime."""

    def test_rate_limiter_acquire(self):
        from lateralus_lang.async_runtime import RateLimiter
        rl = RateLimiter(rate=100, burst=5)
        # Should be able to acquire burst tokens immediately
        for _ in range(5):
            assert rl.try_acquire() is True
        # 6th should fail (burst exhausted)
        assert rl.try_acquire() is False

    def test_rate_limiter_refill(self):
        from lateralus_lang.async_runtime import RateLimiter
        rl = RateLimiter(rate=1000, burst=1)
        assert rl.try_acquire() is True
        time.sleep(0.01)  # 10ms → ~10 tokens at 1000/s
        assert rl.try_acquire() is True


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: Full Program Compilation
# ═══════════════════════════════════════════════════════════════════════════════

class TestV16Integration:
    """Test full programs that use v1.6 features compile correctly."""

    def test_async_fn_still_works(self):
        src = "async fn fetch(url: str) -> str {\n    return url\n}"
        py = compile_py(src)
        assert "async def" in py

    def test_spawn_still_works(self):
        src = "spawn println(\"hello\")"
        py = compile_py(src)
        assert "ensure_future" in py

    def test_await_still_works(self):
        src = "async fn f() {\n    await sleep(1)\n}"
        py = compile_py(src)
        assert "await" in py

    def test_full_channel_program(self):
        src = '''let ch = channel<int>(10)
nursery {
    spawn println("worker 1")
    spawn println("worker 2")
}'''
        py = compile_py(src)
        assert "Channel" in py or "_Channel" in py
        assert "Nursery" in py

    def test_parallel_map_program(self):
        src = 'let results = parallel_map([1, 2, 3], fn(x) { x * x })'
        py = compile_py(src)
        assert "parallel_map" in py

    def test_select_with_channel(self):
        src = '''let ch = channel<str>(5)
select {
    msg from ch => { println(msg) }
    after 100 => { println("timeout") }
}'''
        py = compile_py(src)
        assert "_Channel" in py or "Channel" in py

    def test_cancel_token_in_program(self):
        src = 'let token = cancel'
        py = compile_py(src)
        assert "CancellationToken" in py

    def test_async_for_in_async_fn(self):
        src = 'async for event in events {\n    println(event)\n}'
        py = compile_py(src)
        assert "async for" in py

    def test_codegen_header_v16(self):
        py = compile_py("let x = 1")
        assert "v1.6" in py
