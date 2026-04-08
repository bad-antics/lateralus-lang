"""
tests/test_async_runtime.py — Tests for the LATERALUS async/concurrent runtime
"""
import threading
import time

from lateralus_lang.async_runtime import (
    AsyncPipelineExecutor,
    Channel,
    ParallelPipeline,
    RateLimiter,
    TaskGroup,
    parallel_filter,
    parallel_map,
    run_with_timeout,
)


class TestChannel:
    def test_send_recv(self):
        ch = Channel(capacity=5)
        ch.send("hello")
        assert ch.recv() == "hello"

    def test_fifo_order(self):
        ch = Channel(capacity=10)
        for i in range(5):
            ch.send(i)
        for i in range(5):
            assert ch.recv() == i

    def test_try_send_recv(self):
        ch = Channel(capacity=2)
        assert ch.try_send("a")
        assert ch.try_send("b")
        assert not ch.try_send("c")  # Full
        assert ch.try_recv() == "a"
        assert ch.try_recv() == "b"
        assert ch.try_recv() is None  # Empty

    def test_close(self):
        ch = Channel(capacity=5)
        ch.send("data")
        ch.close()
        assert ch.is_closed
        assert not ch.send("more")  # Closed
        assert ch.recv() == "data"  # Existing data still available

    def test_len(self):
        ch = Channel(capacity=10)
        ch.send(1)
        ch.send(2)
        assert len(ch) == 2

    def test_is_empty(self):
        ch = Channel(capacity=5)
        assert ch.is_empty
        ch.send(1)
        assert not ch.is_empty

    def test_threaded_communication(self):
        ch = Channel(capacity=10)
        results = []

        def producer():
            for i in range(5):
                ch.send(i)
            ch.close()

        def consumer():
            while True:
                val = ch.recv()
                if val is None and ch.is_closed:
                    break
                results.append(val)

        t1 = threading.Thread(target=producer)
        t2 = threading.Thread(target=consumer)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results == [0, 1, 2, 3, 4]


class TestTaskGroup:
    def test_spawn_and_wait(self):
        with TaskGroup(max_workers=2) as group:
            group.spawn(lambda: 42, task_id="answer")
            group.spawn(lambda: "hello", task_id="greeting")
            results = group.wait_all()

        assert len(results) == 2
        values = {r.task_id: r.value for r in results}
        assert values["answer"] == 42
        assert values["greeting"] == "hello"

    def test_all_completed(self):
        with TaskGroup() as group:
            group.spawn(lambda: 1)
            group.spawn(lambda: 2)
            group.spawn(lambda: 3)
            results = group.wait_all()

        assert all(r.is_ok for r in results)

    def test_failed_task(self):
        def failing():
            raise ValueError("oops")

        with TaskGroup() as group:
            group.spawn(failing, task_id="fail")
            results = group.wait_all()

        assert results[0].is_err
        assert isinstance(results[0].error, ValueError)

    def test_wait_first(self):
        def slow():
            time.sleep(0.5)
            return "slow"

        def fast():
            return "fast"

        with TaskGroup() as group:
            group.spawn(slow, task_id="slow")
            group.spawn(fast, task_id="fast")
            result = group.wait_first()

        assert result.is_ok
        assert result.value == "fast"

    def test_elapsed_time(self):
        def sleepy():
            time.sleep(0.05)
            return "done"

        with TaskGroup() as group:
            group.spawn(sleepy)
            results = group.wait_all()

        assert results[0].elapsed_ms > 0


class TestParallelPipeline:
    def test_parallel_map(self):
        with ParallelPipeline(max_workers=2) as pp:
            pp.map(lambda x: x * 2)
            result = pp.execute([1, 2, 3, 4, 5])

        assert result == [2, 4, 6, 8, 10]

    def test_parallel_filter(self):
        with ParallelPipeline(max_workers=2) as pp:
            pp.filter(lambda x: x % 2 == 0)
            result = pp.execute([1, 2, 3, 4, 5, 6])

        assert result == [2, 4, 6]

    def test_chained_stages(self):
        with ParallelPipeline(max_workers=2) as pp:
            pp.map(lambda x: x * 2)
            pp.filter(lambda x: x > 4)
            result = pp.execute([1, 2, 3, 4, 5])

        assert result == [6, 8, 10]


class TestRateLimiter:
    def test_acquire(self):
        rl = RateLimiter(rate=100, burst=5)
        # Should be able to acquire burst tokens immediately
        for _ in range(5):
            assert rl.try_acquire()
        # 6th should fail (no tokens left)
        assert not rl.try_acquire()

    def test_refill(self):
        rl = RateLimiter(rate=1000, burst=1)
        assert rl.try_acquire()
        assert not rl.try_acquire()
        time.sleep(0.01)  # Wait for refill
        assert rl.try_acquire()

    def test_blocking_acquire(self):
        rl = RateLimiter(rate=100, burst=1)
        rl.try_acquire()  # Drain
        start = time.monotonic()
        assert rl.acquire(timeout=1.0)
        elapsed = time.monotonic() - start
        assert elapsed < 0.5  # Should refill quickly at rate=100


class TestParallelMap:
    def test_basic(self):
        result = parallel_map(lambda x: x ** 2, [1, 2, 3, 4, 5], workers=2)
        assert result == [1, 4, 9, 16, 25]

    def test_empty(self):
        result = parallel_map(lambda x: x, [], workers=2)
        assert result == []


class TestParallelFilter:
    def test_basic(self):
        result = parallel_filter(lambda x: x > 3, [1, 2, 3, 4, 5], workers=2)
        assert result == [4, 5]


class TestRunWithTimeout:
    def test_completes(self):
        result = run_with_timeout(lambda: 42, timeout=1.0)
        assert result.is_ok
        assert result.value == 42

    def test_error(self):
        def bad():
            raise ValueError("broken")

        result = run_with_timeout(bad, timeout=1.0)
        assert result.is_err


class TestAsyncPipelineExecutor:
    def test_sync_execution(self):
        pipe = AsyncPipelineExecutor()
        pipe.add_stage(lambda x: x * 2)
        pipe.add_stage(lambda x: x + 10)
        pipe.add_stage(lambda x: x ** 2)
        result = pipe.execute_sync(5)
        assert result == (5 * 2 + 10) ** 2  # (20) ** 2 = 400

    def test_chaining(self):
        pipe = AsyncPipelineExecutor()
        pipe.add_stage(str)
        pipe.add_stage(lambda s: s + "!")
        result = pipe.execute_sync(42)
        assert result == "42!"
